"""Current field definitions have a distinct, immutable acceptance contract."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest
import yaml

from data_sheets_schema.evaluation.validate import validate_outputs
from data_sheets_schema.evaluation_context import context_digest, normalize_context, unwrap_document
from data_sheets_schema.field_agent_contract import validate_output, validate_result
from data_sheets_schema.judge_contract import evaluation_contract

ROOT = Path(__file__).resolve().parents[2]
PROJECT, METHOD = "independent-clinical-example", "author-supplied-method"


def fixture(tmp_path, rubric="rubric10", document=None, context=None):
    definition = ROOT / f".claude/agents/d4d-{rubric}.md"
    result = json.loads(re.search(r"```json\n(.*?)\n```", definition.read_text(), re.S).group(1))
    document = document if document is not None else {"id": "https://example.org/patient-records", "conforms_to_class": "Dataset"}
    context = normalize_context(context)
    source = yaml.safe_load((ROOT / f"data/rubric/{rubric}.txt").read_bytes())
    contract = evaluation_contract(rubric, source, context, unwrap_document(document))
    result.update(project=PROJECT, method=METHOD, applicability_context=context, evaluation_scope=contract["scope"])
    raw = yaml.safe_dump(document).encode()
    result["metadata"].update(instrument_sha256=hashlib.sha256(definition.read_bytes()).hexdigest(),
                              input_sha256=hashlib.sha256(raw).hexdigest(), context_sha256=context_digest(context))
    is10 = rubric == "rubric10"
    for group in result["elements" if is10 else "categories"]:
        for item in group["sub_elements" if is10 else "questions"]:
            key = item["item_id"] if is10 else f"Q{item['id']}"
            rule = contract["items"][key]
            item.update(applicable=rule["applicable"], applicability_status=rule["status"],
                        applicability_evidence=rule["evidence"], score=0 if rule["applicable"] else None)
            item["unit_scores"] = [{"path": unit["path"], "score": item["score"],
                                    "evidence": "Documentation evidence or an explicit gap."} for unit in contract["scope"]["units"]]
        if is10:
            group["element_max"] = sum(item["applicable"] for item in group["sub_elements"])
    recalculate(result)
    input_path = tmp_path / "input.yaml"
    input_path.write_bytes(raw)
    context_path = tmp_path / "context.yaml"
    context_path.write_text(yaml.safe_dump(context))
    args = dict(rubric=rubric, project=PROJECT, method=METHOD, input_path=input_path,
                definition_path=definition, context_path=context_path)
    return result, args


def recalculate(result):
    is10 = result["rubric"] == "rubric10"
    groups = result["elements" if is10 else "categories"]
    items = [item for group in groups for item in group["sub_elements" if is10 else "questions"]]
    fixed = 50 if is10 else 88
    total = sum(item["score"] or 0 for item in items)
    excluded = sum(1 if is10 else item["max_score"] for item in items if not item["applicable"])
    for group in groups:
        group["element_score" if is10 else "category_score"] = sum(item["score"] or 0 for item in group["sub_elements" if is10 else "questions"])
    result["overall_score"].update(total_points=total, max_points=fixed,
        excluded_max_points=excluded, adjusted_max_points=fixed - excluded,
        normalized_percentage=100 * total / (fixed - excluded),
        fixed_percentage=100 * total / fixed, percentage=100 * total / fixed)
    result["overall_score"]["sub_elements_not_applicable" if is10 else "questions_not_applicable"] = sum(not item["applicable"] for item in items)


def write_and_validate(tmp_path, result, args):
    path = tmp_path / "answer.json"
    path.write_text(json.dumps(result))
    before = path.read_bytes()
    try:
        return validate_output(path, **args)
    finally:
        assert path.read_bytes() == before


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_actual_definition_examples_pass_without_mutation(tmp_path, rubric):
    definition = ROOT / f".claude/agents/d4d-{rubric}.md"
    result = json.loads(re.search(r"```json\n(.*?)\n```", definition.read_text(), re.S).group(1))
    result["metadata"]["instrument_sha256"] = hashlib.sha256(definition.read_bytes()).hexdigest()
    before = deepcopy(result)
    report = validate_result(result, rubric=rubric, project=result["project"], method=result["method"],
        document={"id": "https://example.org/synthetic-dataset"},
        input_sha256=hashlib.sha256(b"id: https://example.org/synthetic-dataset\n").hexdigest(),
        definition=definition.read_bytes(), context={key: {"value": False,
        "evidence": "Explicit caller declaration for this structural example."} for key in ("human_subjects", "regulated_access")})
    assert report["items_checked"] == (50 if rubric == "rubric10" else 20)
    assert result == before


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
@pytest.mark.parametrize("kind", ["Dataset", "CoreDataset"])
@pytest.mark.parametrize("declaration", ["plain", "uri", "wrapper"])
@pytest.mark.parametrize("predicate", [True, False, None])
def test_classes_components_and_trusted_context(tmp_path, rubric, kind, declaration, predicate):
    document = {"id": "parent", "resources": [{"id": "component"}]}
    if declaration == "wrapper":
        document = {kind: document}
    else:
        document["conforms_to_class"] = kind if declaration == "plain" else "https://example.org/" + kind
    result, args = fixture(tmp_path, rubric, document, {"human_subjects": predicate})
    assert result["evaluation_scope"]["units"] == [{"path": "#", "id": "parent"}]
    assert write_and_validate(tmp_path, result, args)["units_checked"] == 1


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
@pytest.mark.parametrize("kind", ["DatasetCollection", "CoreDatasetCollection"])
def test_nested_collections_minimum_and_explicit_dataset_boundary(tmp_path, rubric, kind):
    leaf = "CoreDataset" if kind.startswith("Core") else "Dataset"
    document = {kind: {"id": "collection", "resources": [
        {leaf: {"id": "one", "resources": [{"id": "component"}]}},
        {kind: {"resources": [{leaf: {"id": "two"}}]}}]}}
    result, args = fixture(tmp_path, rubric, document)
    assert result["evaluation_scope"]["units"] == [
        {"path": "#/resources/0", "id": "one"}, {"path": "#/resources/1/resources/0", "id": "two"}]
    first = result["elements"][0]["sub_elements"][0] if rubric == "rubric10" else result["categories"][0]["questions"][0]
    first["unit_scores"][0]["score"] = 1
    assert write_and_validate(tmp_path, result, args)["total_points"] == 0
    first["score"] = 1
    recalculate(result)
    with pytest.raises(ValueError, match="score"):
        write_and_validate(tmp_path, result, args)


@pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
def test_field_numeric_quality_levels_are_not_semantic_domain(tmp_path, score):
    result, args = fixture(tmp_path, "rubric20", context={"human_subjects": False})
    question = result["categories"][0]["questions"][0]
    question["score"] = question["unit_scores"][0]["score"] = score
    recalculate(result)
    assert write_and_validate(tmp_path, result, args)["total_points"] == score
    assert result["overall_score"]["fixed_percentage"] != result["overall_score"]["normalized_percentage"]


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
@pytest.mark.parametrize("change", ["version", "rubric", "project", "method", "instrument_sha256", "input_sha256", "context_sha256", "rubric_sha256", "wrong_definition"])
def test_identity_mismatch_is_refused(tmp_path, rubric, change):
    result, args = fixture(tmp_path, rubric)
    if change in result:
        result[change] = "wrong"
    elif change == "wrong_definition":
        args["definition_path"] = ROOT / f".claude/agents/d4d-{rubric}-semantic.md"
        result["metadata"]["instrument_sha256"] = hashlib.sha256(args["definition_path"].read_bytes()).hexdigest()
    else:
        result["metadata"][change] = "0" * 64
    with pytest.raises(ValueError):
        write_and_validate(tmp_path, result, args)


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_self_declared_na_cannot_replace_independent_unknown_context(tmp_path, rubric):
    result, args = fixture(tmp_path, rubric, context={"human_subjects": False})
    args["context_path"] = None
    with pytest.raises(ValueError, match="caller context"):
        write_and_validate(tmp_path, result, args)


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
@pytest.mark.parametrize("mutation", ["missing_item", "duplicate_item", "wrong_name", "wrong_group", "missing_unit", "duplicate_unit", "wrong_path", "inherited", "wrong_unit_id", "wrong_total", "wrong_fixed", "wrong_adjusted", "wrong_percentage", "no_fixed_percentage", "no_quality_note", "false_applicable", "wrong_status", "numeric_applicable", "null_score", "bool_score", "fractional_score", "negative_score", "high_score", "empty_evidence", "nonobject_item", "nonobject_unit"])
def test_contract_mutations_fail_without_repair(tmp_path, rubric, mutation):
    result, args = fixture(tmp_path, rubric)
    groups = result["elements" if rubric == "rubric10" else "categories"]
    items = groups[0]["sub_elements" if rubric == "rubric10" else "questions"]
    item = items[0]
    if mutation == "missing_item": items.pop()
    elif mutation == "duplicate_item": items[-1] = deepcopy(item)
    elif mutation == "wrong_name": item["name"] = "invented heading"
    elif mutation == "wrong_group":
        if rubric == "rubric10": item["item_id"] = "E2.1"
        else: item["id"] = 6
    elif mutation == "missing_unit": item["unit_scores"].clear()
    elif mutation == "duplicate_unit": item["unit_scores"].append(deepcopy(item["unit_scores"][0]))
    elif mutation == "wrong_path": item["unit_scores"][0]["path"] = "#/resources/0"
    elif mutation == "inherited": result["evaluation_scope"]["collection_metadata_inherited"] = True
    elif mutation == "wrong_unit_id": result["evaluation_scope"]["units"][0]["id"] = "another dataset"
    elif mutation == "wrong_total": result["overall_score"]["total_points"] = 1
    elif mutation == "wrong_fixed": result["overall_score"]["max_points"] = 84
    elif mutation == "wrong_adjusted": result["overall_score"]["adjusted_max_points"] = 0
    elif mutation == "wrong_percentage": result["overall_score"]["percentage"] = 25
    elif mutation == "no_fixed_percentage": del result["overall_score"]["fixed_percentage"]
    elif mutation == "no_quality_note": del item["quality_note"]
    elif mutation == "false_applicable": item["applicable"] = False
    elif mutation == "wrong_status": item["applicability_status"] = "not_applicable"
    elif mutation == "numeric_applicable": item["applicable"] = 1
    elif mutation in ("null_score", "bool_score", "fractional_score", "negative_score", "high_score"):
        item["score"] = item["unit_scores"][0]["score"] = {"null_score": None, "bool_score": True, "fractional_score": 2.5, "negative_score": -1, "high_score": 6}[mutation]
    elif mutation == "empty_evidence": item["unit_scores"][0]["evidence"] = " "
    elif mutation == "nonobject_item": items[0] = None
    elif mutation == "nonobject_unit": item["unit_scores"][0] = None
    before = deepcopy(result)
    with pytest.raises(ValueError):
        write_and_validate(tmp_path, result, args)
    assert result == before


@pytest.mark.parametrize("mutation", ["score_type", "max_score", "category_max", "duplicate_category"])
def test_rubric20_fixed_maxima_and_types(tmp_path, mutation):
    result, args = fixture(tmp_path, "rubric20", context={"human_subjects": False})
    if mutation == "score_type": result["categories"][0]["questions"][0]["score_type"] = "pass_fail"
    elif mutation == "max_score": result["categories"][1]["questions"][2]["max_score"] = 0
    elif mutation == "category_max": result["categories"][1]["category_max"] -= 5
    else: result["categories"][1] = deepcopy(result["categories"][0])
    with pytest.raises(ValueError): write_and_validate(tmp_path, result, args)


@pytest.mark.parametrize("bad", ['{"rubric":"rubric10","rubric":"rubric10"}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}', 'null', '[]', '{broken'])
def test_strict_json_rejects_ambiguous_or_nonobject_output(tmp_path, bad):
    _, args = fixture(tmp_path)
    path = tmp_path / "bad.json";path.write_text(bad)
    with pytest.raises(ValueError): validate_output(path, **args)


@pytest.mark.parametrize("bad", ['id: one\nid: two\n', 'DatasetCollection: {resources: []}\n', 'resources: [null]\n', 'Dataset: []\n', 'resources: &cycle [{resources: *cycle}]\n'])
def test_input_keys_class_and_resources_are_not_repaired(tmp_path, bad):
    result, args = fixture(tmp_path)
    args["input_path"].write_text(bad)
    result["metadata"]["input_sha256"] = hashlib.sha256(bad.encode()).hexdigest()
    with pytest.raises(ValueError): write_and_validate(tmp_path, result, args)


@pytest.mark.parametrize("human,regulated,expected", [(False, False, "not_applicable"), (False, None, "unknown"), (True, None, "applicable"), (None, True, "applicable")])
def test_source_any_applicability_is_three_valued(tmp_path, human, regulated, expected):
    result, args = fixture(tmp_path, context={"human_subjects": human, "regulated_access": regulated})
    item = result["elements"][3]["sub_elements"][0]
    assert item["applicability_status"] == expected
    write_and_validate(tmp_path, result, args)
    item["applicability_status"] = "not_applicable" if expected != "not_applicable" else "unknown"
    with pytest.raises(ValueError, match="applicability"): write_and_validate(tmp_path, result, args)


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_false_scope_must_be_boolean_and_na_cannot_retain_a_score(tmp_path, rubric):
    result, args = fixture(tmp_path, rubric, context={"human_subjects": False})
    result["evaluation_scope"]["collection_metadata_inherited"] = 0
    with pytest.raises(ValueError, match="scope"): write_and_validate(tmp_path, result, args)
    result["evaluation_scope"]["collection_metadata_inherited"] = False
    items = [i for g in result["elements" if rubric == "rubric10" else "categories"] for i in g["sub_elements" if rubric == "rubric10" else "questions"]]
    excluded = next(item for item in items if not item["applicable"])
    excluded["unit_scores"][0]["score"] = 0
    with pytest.raises(ValueError, match="excluded resource"): write_and_validate(tmp_path, result, args)
    excluded["unit_scores"][0]["score"] = None;excluded["score"] = 0
    with pytest.raises(ValueError, match="excluded item"): write_and_validate(tmp_path, result, args)


def test_bad_context_yaml_and_missing_model_temperature_are_refused(tmp_path):
    result, args = fixture(tmp_path)
    args["context_path"].write_text("human_subjects: true\nhuman_subjects: false\n")
    with pytest.raises(ValueError, match="duplicate"): write_and_validate(tmp_path, result, args)
    args["context_path"].write_text("{}\n")
    del result["model"]["temperature"]
    with pytest.raises(ValueError, match="temperature"): write_and_validate(tmp_path, result, args)


def test_huge_numeric_summary_is_a_validation_error_not_overflow(tmp_path):
    result, args = fixture(tmp_path)
    result["overall_score"]["fixed_percentage"] = 10 ** 500
    with pytest.raises(ValueError, match="fixed_percentage"):
        write_and_validate(tmp_path, result, args)


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_exact_file_cli_ignores_sibling_and_keeps_historical_behavior(tmp_path, rubric):
    result, args = fixture(tmp_path, rubric)
    path = tmp_path / "answer.json";path.write_text(json.dumps(result))
    sibling = tmp_path / "other_evaluation.json";sibling.write_text("unreadable sibling rating")
    command = [sys.executable, str(ROOT / "scripts/validate_evaluation_schema.py"), "--file", str(path),
        "--rubric", rubric, "--input", str(args["input_path"]), "--agent-definition", str(args["definition_path"]),
        "--context", str(args["context_path"]), "--project", PROJECT, "--method", METHOD]
    completed = subprocess.run(command, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "VALID" in completed.stdout and sibling.name not in completed.stdout
    assert validate_outputs([path], rubric=rubric, input_path=args["input_path"], definition_path=args["definition_path"] , context_path=args["context_path"]) == 1
    result["version"] = "1.0";path.write_text(json.dumps(result))
    assert subprocess.run(command, capture_output=True).returncode == 1


def test_historical_plain_rubric_still_reported_unjudged(tmp_path, capsys):
    from data_sheets_schema.evaluation.validate import main
    path = tmp_path / "historical_evaluation.json"
    path.write_bytes((ROOT / "data/evaluation_llm/rubric20/concatenated/CHORUS_claudecode_agent_evaluation.json").read_bytes())
    assert main(eval_base=tmp_path) == 0
    assert "rubric20 1" in capsys.readouterr().out
