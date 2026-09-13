"""Agent examples carry complete v2 context and match the acceptance contract."""
import hashlib
import json
from pathlib import Path
import re

import jsonschema
import pytest
import yaml

from data_sheets_schema.semantic_scope import validate_scope

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
@pytest.mark.parametrize("semantic", [False, True])
def test_examples_are_complete_and_do_not_teach_circular_na(rubric, semantic):
    definition = ROOT / f".claude/agents/d4d-{rubric}{'-semantic' if semantic else ''}.md"
    match = re.search(r"```json\n(.*?)\n```", definition.read_text(), re.S)
    result = json.loads(match.group(1))
    assert result["version"] == "2.0"
    assert result["project"] == "EXAMPLE_NONHUMAN"
    assert result["model"]["temperature"] is None
    groups = result["elements" if rubric == "rubric10" else "categories"]
    items = [item for group in groups for item in group["sub_elements" if rubric == "rubric10" else "questions"]]
    assert len(items) == (50 if rubric == "rubric10" else 20)
    assert all(len(item["unit_scores"]) == 1 for item in items)
    assert any(item["score"] is None for item in items)
    if semantic:
        # Replace the explicitly marked example placeholder with the actual
        # file bytes, just as an evaluator must before accepting a result.
        result["metadata"]["instrument_sha256"] = hashlib.sha256(definition.read_bytes()).hexdigest()
        schema = json.loads((ROOT / f"src/download/prompts/{rubric}_semantic_schema.json").read_text())
        jsonschema.validate(result, schema)
        raw = b"id: https://example.org/synthetic-dataset\n"
        validate_scope(result, document=yaml.safe_load(raw), input_sha256=hashlib.sha256(raw).hexdigest())
