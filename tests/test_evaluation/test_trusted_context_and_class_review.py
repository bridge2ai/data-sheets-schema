"""Caller-owned applicability and explicit Dataset classes remain authoritative."""
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from evaluation.evaluate_d4d import validate_d4d_yaml
from tests.test_evaluation.test_round2_input_review import schemas, schema_validator
from tests.test_evaluation.test_semantic_context_scope import record, ROOT
from tests.test_evaluation.test_semantic_evaluation_contract import _validator


@pytest.mark.parametrize("name", ["Dataset", "CoreDataset"])
@pytest.mark.parametrize("declaration", ["plain", "uri", "wrapper"])
def test_an_explicit_dataset_can_have_resources_without_becoming_a_collection(
        tmp_path, monkeypatch, schemas, name, declaration):
    document = {"id": "https://example.org/parent", "purposes": [{"response": "Synthetic cohort documentation"}],
                "resources": [{"id": "https://example.org/child"}]}
    if declaration == "wrapper":
        document = {name: document}
    else:
        document["conforms_to_class"] = name if declaration == "plain" else f"https://example.org/schema/{name}"
    path = tmp_path / "dataset.yaml"
    path.write_text(yaml.safe_dump(document))
    chosen = schema_validator(monkeypatch, schemas)
    assert validate_d4d_yaml(path, "manual")
    assert chosen == [name]


def test_invented_human_subject_exclusion_cannot_inflate_the_adjusted_score(tmp_path):
    caller_context = tmp_path / "original-caller-context.yaml"
    caller_context.write_text("human_subjects: true\n")
    original, input_path = record(tmp_path, "rubric20", {"human_subjects": True})
    for category in original["categories"]:
        for item in category["questions"]:
            if item["id"] in (8, 15):
                item["score"] = 0
                for unit in item["unit_scores"]:
                    unit["score"] = 0
        category["category_score"] = sum(item["score"] or 0 for item in category["questions"])
    original["overall_score"].update(total_points=78, normalized_percentage=88.6, fixed_percentage=88.6)
    forged, same_input = record(tmp_path, "rubric20", {"human_subjects": False})
    forged["overall_score"]["fixed_percentage"] = 88.6
    assert same_input == input_path
    assert forged["overall_score"]["total_points"] == 78
    assert forged["overall_score"]["normalized_percentage"] == 100
    paths = []
    for name, result in (("original", original), ("forged", forged)):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(result))
        paths.append(path)
    arguments = {"input_path": input_path, "definition_path": ROOT / ".claude/agents/d4d-rubric20-semantic.md",
                 "context_path": caller_context}
    validator = _validator()
    assert validator.validate_outputs([paths[0]], **arguments) == 0
    assert validator.validate_outputs([paths[1]], **arguments) == 1
    del arguments["context_path"]
    assert validator.validate_outputs([paths[1]], **arguments) == 1
    # Historical classification still describes the old instrument's internal
    # arithmetic; it cannot stand in for accepting a newly emitted rating.
    assert validator.classify(forged, validator.load_schema(ROOT / "src/download/prompts/rubric20_semantic_schema.json"))[0] == "valid"
    done = subprocess.run([sys.executable, validator.__file__, "--file", str(paths[1]),
        "--input", str(input_path), "--agent-definition", str(arguments["definition_path"]),
        "--context", str(caller_context)], text=True, capture_output=True)
    assert done.returncode == 1 and "caller context" in done.stdout, done.stdout + done.stderr


def test_an_omitted_context_keeps_all_conditional_items_in_the_denominator(tmp_path):
    result, input_path = record(tmp_path, "rubric20", {})
    result["overall_score"]["fixed_percentage"] = 100.0
    path = tmp_path / "unknown-context.json"
    path.write_text(json.dumps(result))
    assert result["overall_score"]["adjusted_max_points"] == 88
    assert _validator().validate_outputs([path], input_path=input_path,
        definition_path=ROOT / ".claude/agents/d4d-rubric20-semantic.md") == 0
