"""Version-2 semantic output acceptance is tied to its input and context."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation_context import context_digest, load_document
from data_sheets_schema.judge_contract import evaluation_contract
from data_sheets_schema.semantic_scope import validate_scope
from tests.test_evaluation.test_semantic_evaluation_contract import (
    _rubric10_record, _rubric20_record, _schema, _validator,
)

ROOT = Path(__file__).resolve().parents[2]


def record(tmp_path, rubric):
    input_path = tmp_path / "external.yaml"
    input_path.write_text("CoreDatasetCollection:\n  resources:\n    - id: example:a\n    - id: example:b\n")
    document, digest = load_document(input_path)
    raw = (ROOT / f"data/rubric/{rubric}.txt").read_bytes()
    specification = yaml.safe_load(raw)
    contract = evaluation_contract(rubric, specification, {"human_subjects": False}, document)
    result = _rubric10_record() if rubric == "rubric10" else _rubric20_record()
    result.update(version="2.0", project="EXTERNAL_CLINICAL", method="manual",
                  d4d_file=str(input_path), applicability_context=contract["context"],
                  evaluation_scope=contract["scope"],
                  metadata={"context_sha256": context_digest(contract["context"]),
                            "input_sha256": digest, "rubric_sha256": hashlib.sha256(raw).hexdigest(),
                            "instrument_sha256": hashlib.sha256((ROOT / f".claude/agents/d4d-{rubric}-semantic.md").read_bytes()).hexdigest()})
    total = adjusted = excluded = 0
    for group in result["elements" if rubric == "rubric10" else "categories"]:
        points = cap = fixed = 0
        for index, item in enumerate(group["sub_elements" if rubric == "rubric10" else "questions"], 1):
            key = f"E{group['id']}.{index}" if rubric == "rubric10" else f"Q{item['id']}"
            rule = contract["items"][key]
            score = rule["fixed_max_score"] if rule["applicable"] else None
            item.update(name=rule["name"], applicable=rule["applicable"], applicability_status=rule["status"],
                        applicability_evidence=rule["evidence"], score=score,
                        unit_scores=[{"path": unit["path"], "score": score, "evidence": "Synthetic fixture evidence"}
                                     for unit in contract["scope"]["units"]])
            if rubric == "rubric10":
                item["item_id"] = key
            else:
                item["max_score"] = rule["fixed_max_score"]
            points += score or 0
            cap += rule["max_score"]
            fixed += rule["fixed_max_score"]
            excluded += not rule["applicable"]
        if rubric == "rubric10":
            group.update(element_score=points, element_max=cap)
        else:
            group.update(category_score=points, category_max=fixed)
        total += points
        adjusted += cap
    maximum = 50 if rubric == "rubric10" else 88
    result["overall_score"].update(
        total_points=total, adjusted_max_points=adjusted, excluded_max_points=maximum-adjusted,
        normalized_percentage=round(total / adjusted * 100, 1),
        **{"sub_elements_not_applicable" if rubric == "rubric10" else "questions_not_applicable": excluded})
    return result, input_path


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_complete_external_assessment_accepts_every_resource_and_explicit_na(tmp_path, rubric):
    result, input_path = record(tmp_path, rubric)
    status, errors = _validator().classify(result, _schema(rubric + "-semantic"))
    assert status == "valid", errors
    path = tmp_path / "assessment.json"
    path.write_text(json.dumps(result))
    assert _validator().validate_outputs([path], input_path=input_path, definition_path=ROOT / f".claude/agents/d4d-{result['rubric']}.md") == 0


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
@pytest.mark.parametrize("mutation", ["missing_resource", "duplicate_resource", "incorrect_minimum",
                                    "wrong_context", "unjustified_na", "wrong_total", "wrong_rubric", "wrong_name"])
def test_semantic_acceptance_rejects_coverage_applicability_and_arithmetic_errors(tmp_path, rubric, mutation):
    result, input_path = record(tmp_path, rubric)
    item = result["elements"][0]["sub_elements"][0] if rubric == "rubric10" else result["categories"][0]["questions"][0]
    if mutation == "missing_resource":
        item["unit_scores"].pop()
    elif mutation == "duplicate_resource":
        item["unit_scores"][1]["path"] = item["unit_scores"][0]["path"]
    elif mutation == "incorrect_minimum":
        item["unit_scores"][0]["score"] = 0
    elif mutation == "wrong_context":
        result["applicability_context"]["human_subjects"]["value"] = True
    elif mutation == "unjustified_na":
        item.update(applicable=False, score=None, applicability_status="not_applicable")
    elif mutation == "wrong_total":
        result["overall_score"]["total_points"] -= 1
    elif mutation == "wrong_name":
        item["name"] = "A different criterion"
    else:
        result["metadata"]["rubric_sha256"] = "0" * 64
    status, errors = _validator().classify(result, _schema(rubric + "-semantic"))
    assert status == "invalid" and errors


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_cli_validation_requires_and_verifies_the_original_input(tmp_path, rubric):
    result, input_path = record(tmp_path, rubric)
    path = tmp_path / "assessment.json"
    path.write_text(json.dumps(result))
    validator = _validator()
    assert validator.validate_outputs([path]) == 1
    input_path.write_text("id: example:another\n")
    assert validator.validate_outputs([path], input_path=input_path, definition_path=ROOT / f".claude/agents/d4d-{result['rubric']}.md") == 1


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_a_model_cannot_omit_a_child_from_both_scope_and_item_scores(tmp_path, rubric):
    result, input_path = record(tmp_path, rubric)
    result["evaluation_scope"]["units"].pop()
    result["evaluation_scope"]["policy"] = "single_dataset"
    for group in result["elements" if rubric == "rubric10" else "categories"]:
        for item in group["sub_elements" if rubric == "rubric10" else "questions"]:
            item["unit_scores"].pop()
    path = tmp_path / "assessment.json"
    path.write_text(json.dumps(result))
    assert _validator().validate_outputs([path], input_path=input_path, definition_path=ROOT / f".claude/agents/d4d-{result['rubric']}.md") == 1


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_cli_validation_refuses_a_stale_or_unspecified_definition(tmp_path, rubric):
    result, input_path = record(tmp_path, rubric)
    path = tmp_path / "assessment.json"
    path.write_text(json.dumps(result))
    validator = _validator()
    assert validator.validate_outputs([path], input_path=input_path) == 1
    changed = tmp_path / "another-definition.md"
    changed.write_text("Another evaluator definition.\n")
    assert validator.validate_outputs([path], input_path=input_path, definition_path=changed) == 1
