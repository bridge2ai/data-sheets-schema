"""Exercise the reported bases, N/A identities and real HTML consumers (#829)."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from data_sheets_schema.semantic_comparison import (
    comparison_warnings, excluded_items, score_bases,
)
from tests.test_evaluation.test_semantic_evaluation_contract import (
    _rubric10_record, _rubric20_record,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def record(total=70, adjusted=78, excluded=(11, 12)):
    return {"project": "CHORUS", "rubric": "rubric20-semantic",
            "overall_score": {"total_points": total, "max_points": 88,
                              "adjusted_max_points": adjusted,
                              "excluded_max_points": 88 - adjusted,
                              "normalized_percentage": round(100 * total / adjusted, 1)},
            "categories": [{"questions": [{"id": i, "score": None, "applicable": False}
                                           for i in excluded]}]}


def test_each_percentage_names_its_actual_denominator():
    fixed, adjusted = score_bases(record(), 88).labels()
    assert fixed == "Fixed: 70/88 (79.5%)"
    assert adjusted == "N/A-adjusted: 70/78 (89.7%)"


def test_equal_denominators_with_different_exclusions_are_flagged():
    warnings = comparison_warnings([record(excluded=(11, 12)), record(excluded=(11, 15))])
    assert len(warnings) == 1
    assert "mixed denominators or excluded items" in warnings[0]
    assert "CHORUS" in warnings[0]


def test_different_denominators_are_flagged_even_with_missing_item_details():
    a, b = record(excluded=()), record(adjusted=83, excluded=())
    del b["overall_score"]["excluded_max_points"]
    assert excluded_items(b) is None
    warnings = comparison_warnings([a, b])
    assert any("unknown" in w for w in warnings)
    assert any("mixed" in w for w in warnings)


def test_same_basis_has_no_denominator_warning():
    assert comparison_warnings([record(total=65), record(total=70)]) == []


def test_legacy_zero_and_current_zero_survive():
    old = {"summary_scores": {"total_score": 0, "total_max_score": 50,
                              "overall_percentage": 0.0}}
    assert score_bases(old, 50).labels() == ("Fixed: 0/50 (0.0%)", "N/A-adjusted: 0/50 (0.0%)")
    assert score_bases(record(total=0), 88).adjusted_percentage == 0


def test_no_applicable_points_are_undefined_not_zero_percent():
    doc = {"overall_score": {"total_points": 0, "max_points": 50, "adjusted_max_points": 0}}
    assert score_bases(doc, 50).labels()[1] == "N/A-adjusted: 0/0 (undefined)"


@pytest.mark.parametrize("bad", [None, True, float("nan"), float("inf"), -1, 90])
def test_invalid_totals_do_not_become_plausible_percentages(bad):
    doc = record()
    doc["overall_score"]["total_points"] = bad
    with pytest.raises((ValueError, TypeError)):
        score_bases(doc, 88)


def test_conflicting_denominators_are_rejected():
    doc = record()
    doc["overall_score"]["excluded_max_points"] = 1
    with pytest.raises(ValueError, match="disagree"):
        score_bases(doc, 88)


def test_full_current_rubric10_renders_names_scores_and_na_without_mutating(tmp_path):
    from render_evaluation_html_rubric10_semantic import generate_evaluation_html
    doc = _rubric10_record()
    before = copy.deepcopy(doc)
    out = tmp_path / "r10.html"
    generate_evaluation_html(doc, out)
    html = out.read_text()
    assert "Fixed: 38/50 (76.0%)" in html
    assert "N/A-adjusted: 38/48 (79.2%)" in html
    assert "Element 8: Element 8" in html
    assert "N/A-adjusted: 3/3 (100.0%)" in html
    assert "N/A (excluded)" in html
    assert "None/1" not in html and "Element None" not in html
    assert doc == before


def test_full_current_rubric20_renders_na_and_both_category_bases(tmp_path):
    from render_evaluation_html_rubric20_semantic import generate_evaluation_html
    doc = _rubric20_record()
    before = copy.deepcopy(doc)
    out = tmp_path / "r20.html"
    generate_evaluation_html(doc, out)
    html = out.read_text()
    assert "Fixed: 83/88 (94.3%)" in html
    assert "N/A-adjusted: 83/83 (100.0%)" in html
    assert "Fixed: 20/25 (80.0%)" in html
    assert "N/A-adjusted: 20/20 (100.0%)" in html
    assert "N/A (excluded)" in html
    assert doc == before


@pytest.mark.parametrize("legacy", [False, True])
def test_interleaved_zero_and_current_percentage_are_visible(legacy):
    from render_interleaved_evaluation import render_html
    r10 = {"overall_score": {"total_points": 0, "max_points": 50,
                              "normalized_percentage": 0}}
    if legacy:
        r10 = {"summary_scores": {"total_score": 0, "total_max_score": 50,
                                  "overall_percentage": 0}}
    r20 = record(total=0)
    text = render_html({}, r10, r20, {})
    assert "Fixed: 0/50 (0.0%)" in text
    assert "N/A-adjusted: 0/78 (0.0%)" in text
    assert "None/88" not in text


def test_comparison_report_keeps_input_hashes_and_flags_bases(tmp_path):
    from report_semantic_comparison import report
    paths = []
    for i, doc in enumerate([record(), record(adjusted=83, excluded=(11,))]):
        path = tmp_path / f"{i}_evaluation.json"
        path.write_text(json.dumps(doc))
        paths.append(path)
    before = [p.read_bytes() for p in paths]
    text = report(paths)
    assert "mixed denominators" in text
    assert "70/88 (79.5%)" in text and "70/78 (89.7%)" in text and "70/83 (84.3%)" in text
    assert all(hashlib.sha256(raw).hexdigest() in text for raw in before)
    assert [p.read_bytes() for p in paths] == before
    run = subprocess.run([sys.executable, str(ROOT / "scripts/report_semantic_comparison.py"),
                          str(paths[0]), "--output", str(paths[0])], capture_output=True, text=True)
    assert run.returncode != 0
    assert paths[0].read_bytes() == before[0]
