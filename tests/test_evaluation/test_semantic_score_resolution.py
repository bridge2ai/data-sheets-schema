"""Current output contracts must enforce the rubric's discrete decisions."""
import json
import re

import jsonschema
import pytest

from tests.test_evaluation.test_semantic_evaluation_contract import (
    REPO, _rubric10_record, _rubric20_record, _schema,
)


@pytest.mark.parametrize("rubric,make_record", [
    ("rubric10-semantic", _rubric10_record),
    ("rubric20-semantic", _rubric20_record),
])
def test_fractional_individual_totals_and_items_are_rejected(rubric, make_record):
    record = make_record()
    record["overall_score"]["total_points"] = 38.5
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(record, _schema(rubric))
    record = make_record()
    if "elements" in record:
        record["elements"][0]["sub_elements"][0]["score"] = 0.5
    else:
        record["categories"][0]["questions"][0]["score"] = 4.5
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(record, _schema(rubric))


def test_fractional_category_sum_is_rejected():
    record = _rubric20_record()
    record["categories"][0]["category_score"] = 19.5
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(record, _schema("rubric20-semantic"))


@pytest.mark.parametrize("score,applicable,valid", [
    (0, "true", True), (3, "true", True), (5, "true", True),
    (None, "false", False), (0, "false", False), (2, "true", False),
])
def test_q14_has_no_circular_exclusion_or_interpolated_band(score, applicable, valid):
    record = _rubric20_record()
    question = next(q for c in record["categories"] for q in c["questions"] if q["id"] == 14)
    question.update(score=score, applicable=applicable)
    validator = jsonschema.Draft7Validator(_schema("rubric20-semantic"))
    assert validator.is_valid(record) == valid


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_individual_json_examples_use_integer_sums_and_correct_percentages(rubric):
    text = (REPO / f".claude/agents/d4d-{rubric}-semantic.md").read_text()
    examples = [json.loads(raw) for raw in re.findall(r"```json\n(.*?)\n```", text, re.S)]
    records = [j for j in examples if "overall_score" in j]
    assert records
    for record in records:
        overall = record["overall_score"]
        assert float(overall["total_points"]).is_integer()
        assert overall["normalized_percentage"] == round(
            overall["total_points"] / overall["adjusted_max_points"] * 100, 1)
        for category in record.get("categories", []):
            assert float(category["category_score"]).is_integer()


def test_citation_applicability_is_consistent_between_table_and_question():
    text = (REPO / ".claude/agents/d4d-rubric10-semantic.md").read_text()
    rows = [line for line in text.splitlines() if line.strip().startswith("|")]
    assert not any("Publication identified" in line for line in rows)
    assert any("Datasets shared" in line and "Element 10 (all)" in line for line in rows)
    citation = text.split("2. **Citation and DOI for Cross-referencing**", 1)[1].split("3. **", 1)[0]
    assert "exactly as for the other Element 10 sub-elements" in citation
    assert "neither citation nor DOI earns 0" in citation
    text = (REPO / ".claude/agents/d4d-rubric20-semantic.md").read_text()
    assert not any("Q14" in line.split("|")[-2]
                   for line in text.splitlines() if line.strip().startswith("|"))
    q14 = text.split("#### Question 14:", 1)[1].split("---", 1)[0]
    assert "Always applicable" in q14
    assert "Non-publication external resources" in q14
    assert "Three such resources without a formal dataset citation earn 3" in q14
