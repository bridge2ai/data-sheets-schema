"""Causal offline review cases for #5094 at 8ff18d2e5, 2026-10-28.

Inputs are synthetic report prose and the existing 13-finding audit fixture.
No provider calls or historical data writes. These assert intended behavior,
so a failure is a retained adversarial finding rather than an expected xfail.
"""
import pytest

from data_sheets_schema import api_runner as api
from data_sheets_schema.report_audit_totals import check_report_audit_totals
from tests.test_report_audit_totals import _make_v10g_audit
from tests.test_report_gate import spec


@pytest.mark.parametrize("suffix", [
    "\nDeferred items (3 findings: 2 medium, 1 low) are listed below.",
    " Deferred items (3 findings: 2 medium, 1 low) are listed below.",
])
def test_subset_after_total_does_not_become_global_severity_count(suffix):
    result = check_report_audit_totals("The audit identified 13 findings." + suffix, _make_v10g_audit())
    assert result["stated_total"] == 13
    assert result["stated_by_severity"] == {}
    assert result["status"] == "consistent"


def test_core_subset_does_not_conflict_with_whole_audit_total():
    result = check_report_audit_totals(
        "The audit identified 13 findings: 2 high, 4 medium, 7 low. "
        "Zero findings against the core record were found.", _make_v10g_audit())
    assert result["stated_totals"] == [13]
    assert result["status"] == "consistent"


def test_numbered_finding_heading_does_not_create_total():
    result = check_report_audit_totals(
        "## Audit findings:\n\n1. Correct the title.\n2. Preserve source attribution.\n", _make_v10g_audit())
    assert result["stated_total"] is None
    assert result["status"] == "no_total_stated"


def test_later_explicit_severity_summary_is_checked():
    result = check_report_audit_totals(
        "The audit identified 13 findings: 2 high, 4 medium, 7 low.\n"
        "The audit returned 13 findings: 3 high, 3 medium, 7 low.\n", _make_v10g_audit())
    assert result["stated_total"] == 13
    assert result["status"] == "mismatch"
    assert any(row["kind"] == "finding_severity_mismatch" for row in result["findings"])


def test_resume_reading_refreshes_current_version_after_report_change(tmp_path):
    selected = spec(out_dir=tmp_path / "out")
    selected.report_path.parent.mkdir(parents=True, exist_ok=True)
    selected.report_path.write_text("The audit identified 13 findings.", encoding="utf-8")
    audit_path = api._intermediate_dir(selected) / f"{selected.project}_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(_make_v10g_audit(), encoding="utf-8")
    prior = api.report_audit_totals_block(selected)
    assert prior["status"] == "consistent"
    selected.report_path.write_text("The audit identified 12 findings.", encoding="utf-8")
    current = api._current_report_audit_totals(selected, {"report_audit_totals": prior})
    assert current["stated_total"] == 12
    assert current["status"] == "mismatch"


def test_resume_preserves_measurement_when_source_is_unavailable(tmp_path):
    selected = spec(out_dir=tmp_path / "missing")
    prior = check_report_audit_totals("The audit identified 13 findings.", _make_v10g_audit())
    prior["instrument_version"] = 1
    assert api._current_report_audit_totals(selected, {"report_audit_totals": prior}) == prior
