"""Accepted API scores retain both denominators in their HTML reports."""
import copy
import hashlib
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.judge_contract import evaluation_contract, validate_result
from data_sheets_schema.resources import resource_path
from data_sheets_schema.semantic_comparison import score_bases
from tests.judge_fixtures import judge_reply


def accepted_api_result(rubric):
    raw = resource_path(f"data/rubric/{rubric}.txt").read_bytes()
    contract = evaluation_contract(rubric, yaml.safe_load(raw), {"human_subjects": False}, {"id": "clinical"})
    result = judge_reply(contract, rubric, perfect=True)
    result["metadata"]["rubric_hash"] = hashlib.sha256(raw).hexdigest()
    validate_result(result, rubric, "P", "method", contract)
    return result, contract


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
@pytest.mark.parametrize("older_output", [False, True])
def test_fixed_and_adjusted_totals_survive_rendering(rubric, older_output, tmp_path):
    from data_sheets_schema.rendering import rubric10_semantic, rubric20_semantic
    result, contract = accepted_api_result(rubric)
    if older_output:
        for group in result["elements" if rubric == "rubric10" else "categories"]:
            for item in group["sub_elements" if rubric == "rubric10" else "questions"]:
                item.pop("fixed_max_score", None)
    before = copy.deepcopy(result)
    fixed = sum(item["fixed_max_score"] for item in contract["items"].values())
    adjusted = sum(item["max_score"] for item in contract["items"].values())
    assert 0 < adjusted < fixed
    bases = score_bases(result, fixed)
    assert (bases.total, bases.fixed_max, bases.adjusted_max) == (adjusted, fixed, adjusted)
    renderer = rubric10_semantic if rubric == "rubric10" else rubric20_semantic
    target = tmp_path / "report.html"
    renderer.generate_evaluation_html(result, target)
    html = target.read_text()
    assert f"Fixed: {adjusted}/{fixed} ({100*adjusted/fixed:.1f}%)" in html
    assert f"N/A-adjusted: {adjusted}/{adjusted} (100.0%)" in html
    if rubric == "rubric20":
        assert "Fixed: 78/88 (88.6%)" in html
        # Q8 is excluded from Q6–10, whose fixed maximum remains 25.
        assert "Fixed: 20/25 (80.0%)" in html
        assert "N/A-adjusted: 20/20 (100.0%)" in html
    assert result == before, "rendering must not rewrite the measured result"


def test_older_api_item_maxima_require_the_recorded_rubric(tmp_path):
    from data_sheets_schema.rendering.rubric20_semantic import generate_evaluation_html
    result, _ = accepted_api_result("rubric20")
    for group in result["categories"]:
        for item in group["questions"]:
            item.pop("fixed_max_score", None)
    result["metadata"]["rubric_hash"] = "0" * 64
    with pytest.raises(ValueError, match="rubric"):
        generate_evaluation_html(result, tmp_path / "report.html")
