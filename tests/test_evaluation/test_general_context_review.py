"""Behavioral regressions from independent evaluation review #1450–#1453."""
import json
from pathlib import Path
import re

import pytest

from tests.test_evaluation.test_general_context import evaluator
from tests.test_evaluation.test_semantic_context_scope import record
from tests.test_evaluation.test_semantic_evaluation_contract import _validator

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
@pytest.mark.parametrize("version", ["1.0", "2.0"])
def test_new_output_gate_never_trusts_a_version_downgrade(tmp_path, rubric, version):
    result, input_path = record(tmp_path, rubric)
    result["version"] = version
    result["metadata"].update(input_sha256="0" * 64, instrument_sha256="0" * 64)
    path = tmp_path / "assessment.json"
    path.write_text(json.dumps(result))
    assert _validator().validate_outputs(
        [path], input_path=input_path,
        definition_path=ROOT / f".claude/agents/d4d-{rubric}-semantic.md") == 1


@pytest.mark.parametrize("count,expected", [(1, 0), (2, 3), (4, 5)])
def test_full_and_core_distributions_have_equal_type_counts(count, expected):
    formats = [("CSV", "text/csv"), ("JSON", "application/json"),
               ("XML", "application/xml"), ("PNG", "image/png")][:count]
    entries = [{"format": name, "media_type": mime} for name, mime in formats]
    obj = evaluator()
    question = next(q for q in obj.rubric20["d4d_evaluation_rubric"]["rubric"] if q["id"] == 4)
    full = obj._score_rubric20_question({"distribution_formats": entries}, question)
    core = obj._score_rubric20_question({"distributions": entries}, question)
    assert full.score == core.score == expected


def test_equivalent_media_and_format_aliases_are_one_type_and_size_is_not_a_format():
    obj = evaluator()
    question = next(q for q in obj.rubric20["d4d_evaluation_rubric"]["rubric"] if q["id"] == 4)
    result = obj._score_rubric20_question({"distributions": [
        {"format": "CSV"}, {"media_type": "text/csv; charset=utf-8"}]}, question)
    assert result.score == 0
    assert not obj._is_field_present({"distributions": [{"bytes": 1234}]}, ["distribution_formats"])[0]


def test_semantic_scoring_standards_only_offer_the_accepted_numeric_bands():
    path = ROOT / ".claude/agents/d4d-rubric20-semantic.md"
    standards = path.read_text().split("#### For Numeric Questions", 1)[1].split("#### For Pass/Fail Questions", 1)[0]
    bands = {int(value) for value in re.findall(r"- \*\*([0-5]):\*\*", standards)}
    assert bands == {0, 3, 5}


def rubric10_items(path):
    text = path.read_text().split("## Rubric10 Specification", 1)[1].split("## Output Format", 1)[0]
    result = {}
    for number, section in re.findall(r"### Element (\d+):(.*?)(?=### Element |\Z)", text, re.S):
        for index, body in re.findall(r"^([1-5])\. \*\*(.*?)(?=^[1-5]\. \*\*|\Z)", section, re.S | re.M):
            fields = re.search(r"- Fields: (.*)", body).group(1)
            criterion = re.search(r"- Look for: (.*)", body).group(1)
            result[f"E{number}.{index}"] = (set(re.findall(r"`([^`]+)`", fields)), criterion, body)
    return result


def test_quality_and_semantic_agents_share_the_audited_source_item_criteria():
    quality = rubric10_items(ROOT / ".claude/agents/d4d-rubric10.md")
    semantic = rubric10_items(ROOT / ".claude/agents/d4d-rubric10-semantic.md")
    assert len(quality) == len(semantic) == 50
    for key in quality:
        assert quality[key][:2] == semantic[key][:2], key
    # Counterexamples for the renamed concepts: affiliation is not a dataset
    # relationship, and a code repository is not guidance on permissible use.
    for items in (quality, semantic):
        assert items["E1.5"][0] == {"parent_datasets", "related_datasets"}
        assert "typed relationships" in items["E1.5"][1]
        assert "project" not in items["E1.5"][1].lower()
        assert items["E3.5"][0] == {"intended_uses", "prohibited_uses", "discouraged_uses"}
        assert "allowed, prohibited, and discouraged uses" in items["E3.5"][1]
        assert "software" not in items["E3.5"][1].lower()
        assert "Split flags alone do not report a count" in items["E5.2"][1]
        assert "contact alone is not an ethics review" in items["E4.1"][1]
        assert "does not describe its characteristics" in items["E5.1"][1]
        assert "alone do not describe provenance or derivation" in items["E6.5"][1]
        assert "alone does not describe an acquisition method" in items["E8.2"][1]
        assert "alone does not categorize bias" in items["E9.2"][1]
