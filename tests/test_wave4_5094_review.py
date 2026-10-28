"""Causal offline review cases for #5094 at 8ff18d2e5, 2026-10-28.

Inputs are synthetic report prose and the existing 13-finding audit fixture.
No provider calls or historical data writes. These assert intended behavior,
so a failure is a retained adversarial finding rather than an expected xfail.
"""
import json
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
    audit = json.loads(_make_v10g_audit())
    for finding in audit["findings"]:
        finding["record"] = "full"
    result = check_report_audit_totals(
        "The audit identified 13 findings: 2 high, 4 medium, 7 low. "
        "Zero findings against the core record were found.", audit)
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
    assert result["stated_severity_summaries"] == [
        {"high": 2, "medium": 4, "low": 7}, {"high": 3, "medium": 3, "low": 7}]


@pytest.mark.parametrize("changed_artifact", ["report", "audit"])
def test_resume_reading_refreshes_current_version_after_input_change(tmp_path, changed_artifact):
    selected = spec(out_dir=tmp_path / "out")
    selected.report_path.parent.mkdir(parents=True, exist_ok=True)
    selected.report_path.write_text("The audit identified 13 findings.", encoding="utf-8")
    audit_path = api._intermediate_dir(selected) / f"{selected.project}_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(_make_v10g_audit(), encoding="utf-8")
    prior = api.report_audit_totals_block(selected)
    assert prior["status"] == "consistent"
    if changed_artifact == "report":
        selected.report_path.write_text("The audit identified 12 findings.", encoding="utf-8")
    else:
        audit = json.loads(_make_v10g_audit())
        audit["findings"].append({"severity": "low", "record": "full", "slot": "extra", "issue": "extra"})
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
    current = api._current_report_audit_totals(selected, {"report_audit_totals": prior})
    assert current["stated_total"] == (12 if changed_artifact == "report" else 13)
    assert current["computed_total"] == (13 if changed_artifact == "report" else 14)
    assert current["status"] == "mismatch"


@pytest.mark.parametrize("historical_version", [1, 2, 3])
def test_resume_preserves_measurement_when_source_is_unavailable(tmp_path, historical_version):
    selected = spec(out_dir=tmp_path / "missing")
    prior = check_report_audit_totals("The audit identified 13 findings.", _make_v10g_audit())
    prior["instrument_version"] = historical_version
    assert api._current_report_audit_totals(selected, {"report_audit_totals": prior}) == prior


@pytest.mark.parametrize("report", [
    "**Audit findings:** 13 (2 high, 4 medium, 7 low)",
    "The audit identified 13 findings: 2 high, 4 medium, 7 low.\n"
    "Deferred items (3 findings: 2 medium, 1 low) are listed below.",
    "The audit identified 13 findings: 2 high, 4 medium, 7 low; of which 2 medium were deferred.",
    "Deferred items (3 findings: 2 medium, 1 low); the audit identified 13 findings: 2 high, 4 medium, 7 low.",
    "The audit identified 13 findings: 2 high, 4 medium, 7 low.\n"
    "The audit returned 13 findings: 2 high, 4 medium, 7 low.",
])
def test_correct_global_breakdowns_still_measure_consistent(report):
    result = check_report_audit_totals(report, _make_v10g_audit())
    assert result["status"] == "consistent"
    assert result["stated_by_severity"] == {"high": 2, "medium": 4, "low": 7}
    assert result["stated_severity_summaries"] == [{"high": 2, "medium": 4, "low": 7}]


def test_subset_after_global_total_does_not_trigger_regate(tmp_path, monkeypatch):
    selected = spec(out_dir=tmp_path / "out")
    selected.report_path.parent.mkdir(parents=True, exist_ok=True)
    selected.report_path.write_text(
        "The audit identified 13 findings.\nDeferred items (3 findings: 2 medium, 1 low) follow.", encoding="utf-8")
    monkeypatch.setattr(api, "report_claims_block", lambda _: {
        "checked": True, "disposition_rows": 1, "claims_checked": 1, "findings": []})
    def refuse_regate(*args, **kwargs):
        pytest.fail("A subset count must not trigger a billed report regeneration")
    monkeypatch.setattr(api, "_regenerate_report", refuse_regate)
    result = api._gate_report(selected, None, {}, [], {"Audit findings": _make_v10g_audit()})
    assert result["findings_before"] == 0
    assert result["regenerated"] is False


def test_backfill_v2_upgrade_preserves_unavailable_checked_reading(tmp_path):
    import yaml
    from data_sheets_schema import backfill_checks as backfill
    path = tmp_path / "provenance.yaml"
    prior = check_report_audit_totals("The audit identified 13 findings.", _make_v10g_audit())
    prior["instrument_version"] = 2
    path.write_text(yaml.safe_dump({"report_audit_totals": prior}), encoding="utf-8")
    original = path.read_bytes()
    withheld = []
    assert not backfill.apply(path, {"report_audit_totals": check_report_audit_totals(None, None)}, withheld=withheld)
    assert path.read_bytes() == original
    assert withheld == ["report_audit_totals"]
    fresh = check_report_audit_totals("The audit identified 12 findings.", _make_v10g_audit())
    assert backfill.apply(path, {"report_audit_totals": fresh})
    assert yaml.safe_load(path.read_text())["report_audit_totals"]["instrument_version"] == 3


@pytest.mark.parametrize("breakdown", [
    "2 high, 4 medium, 6 low",
    "2 high,\n4 medium,\n6 low",
    "- 2 high\n- 4 medium\n- 6 low",
])
def test_wrapped_breakdown_retains_wrong_count(breakdown):
    result = check_report_audit_totals("The audit identified 13 findings:\n" + breakdown, _make_v10g_audit())
    assert result["stated_by_severity"] == {"high": 2, "medium": 4, "low": 6}
    assert result["status"] == "mismatch"
    assert len(result["findings"]) == 1
    assert result["findings"][0]["severity"] == "low"


@pytest.mark.parametrize("summary", [
    "Audit severity summary: 3 high, 3 medium, 7 low.",
    "Audit severity summary:\n3 high, 3 medium, 7 low.\n",
    "Audit totals: 3 high, 3 medium, 7 low.",
])
def test_labeled_summary_without_repeating_total_still_compares(summary):
    result = check_report_audit_totals(
        "The audit identified 13 findings: 2 high, 4 medium, 7 low.\n" + summary, _make_v10g_audit())
    assert result["status"] == "mismatch"
    assert {row["severity"] for row in result["findings"]} == {"high", "medium"}


@pytest.mark.parametrize("counts", [
    "2 high, 4 medium, 7 low; later restated as 3 high, 3 medium, 7 low",
    "3 high, 3 medium, 7 low; later restated as 2 high, 4 medium, 7 low",
])
def test_conflicting_counts_within_one_statement_are_not_overwritten(counts):
    result = check_report_audit_totals("The audit identified 13 findings: " + counts + ".", _make_v10g_audit())
    assert result["status"] == "mismatch"
    assert set(result["stated_severity_counts"]["high"]) == {2, 3}
    assert {row["severity"] for row in result["findings"]} == {"high", "medium"}


@pytest.mark.parametrize("subset", [
    "Deferred audit severity summary: 2 medium, 1 low.",
    "Core record audit severity summary: 2 medium, 1 low.",
    "Deferred items: 2 medium, 1 low.",
])
def test_subset_summary_and_prose_are_not_a_severity_continuation(subset):
    result = check_report_audit_totals("The audit identified 13 findings:\n" + subset, _make_v10g_audit())
    assert result["stated_by_severity"] == {}
    assert result["status"] == "consistent"
