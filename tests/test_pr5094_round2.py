"""Offline regression guards for PR #5094 F1–F6/F9, 2026-10-28.

Inputs: committed report/audit fixtures and synthetic scope/snapshot cases.
Outputs: causal assertions; never edit historical evidence or call providers.
"""
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import api_runner as api
from data_sheets_schema.report_audit_totals import (
    INSTRUMENT_VERSION, check_report_audit_totals, parse_number,
)
from tests.test_report_audit_totals import _make_v10g_audit
from tests.test_report_gate import spec

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/d4d_concatenated"
GOOD = "The audit returned 13 findings: 2 high, 4 medium, 7 low."


def corpus_read(directory, project):
    return check_report_audit_totals(
        directory / f"{project}_reconciliation.md",
        directory / "intermediate" / f"{project}_audit.json",
    )


@pytest.mark.parametrize("arm,run,project,total,status", [
    ("claudecode_agent_core", "2026-09-01_claude-opus-5-api-generic-v7_rep3", "CM4AI", 22, "mismatch"),
    ("claudecode_api_core", "2026-09-04f_claude-opus-5-api-generic-v8_rep1", "AI_READI", 17, "consistent"),
])
def test_full_record_corpus_total(arm, run, project, total, status):
    result = corpus_read(DATA / arm / run, project)
    assert result["stated_total"] == total
    assert result["stated_totals"] == [total]
    assert result["status"] == status


@pytest.mark.parametrize("report", [
    "The audit returned 13 findings against the full record: 2 high, 4 medium, 7 low.",
    "Full record findings by severity: 2 high, 4 medium, 6 low.",
    GOOD + "\nFull record severity summary: 2 high, 4 medium, 6 low.",
])
def test_full_record_is_global_in_each_reader(report):
    result = check_report_audit_totals(report, _make_v10g_audit())
    assert result["stated_by_severity"]
    assert result["status"] == ("mismatch" if "6 low" in report else "consistent")


@pytest.mark.parametrize("report", [
    "Two findings produced no change beyond what is described above.",
    "Twelve findings resulted in changes.",
])
def test_disposition_fallback_is_not_a_total(report):
    result = check_report_audit_totals(report, _make_v10g_audit())
    assert result["stated_total"] is None
    assert result["findings"] == []


@pytest.mark.parametrize("report,expected", [
    ("The audit returned 13 findings: 2 high, 4 medium, 7 low; 2 medium were deferred.", {}),
    ("The audit returned 13 findings: 2 high (1 high withdrawn on re-check), 4 medium, 7 low.", {}),
    ("The audit returned 13 findings: 2 high, 4 medium, 7 low, touching 3 high-priority slots.", {}),
    ("**Audit input:** 13 findings — 2 high, 3 medium (core), 1 medium (full), 7 low.", {"medium": 3}),
    ("Findings by severity: 2 high, 4 medium, 7 low.\n"
     "Findings still open after reconciliation: 0 high, 1 medium, 2 low.", {}),
])
def test_later_subset_counts_do_not_add_mismatches(report, expected):
    result = check_report_audit_totals(report, _make_v10g_audit())
    assert {row["severity"]: row["stated"] for row in result["findings"]} == expected
    assert len(result["findings"]) == len(expected)
    assert result["stated_by_severity"] == {"high": 2, "medium": expected.get("medium", 4), "low": 7}


@pytest.mark.parametrize("directory,project,severity,excluded", [
    (DATA / "claudecode_agent_core/2026-08-22c_claude-opus-5-api-generic-v5_rep2", "VOICE", "medium", 2),
    (ROOT / "data/ATTIC/canary_retries/2026-09-01_claude-opus-5-api-generic-v7_rep1_AI_READI_attempt2/core", "AI_READI", "high", 1),
])
def test_corpus_subset_does_not_enter_regate(directory, project, severity, excluded):
    result = corpus_read(directory, project)
    assert result["status"] == "mismatch"  # preserve the real discrepancies
    assert excluded not in result["stated_severity_counts"].get(severity, [])


@pytest.mark.parametrize("report", [
    "It returned 13 findings: 2 high, 4 medium,\n6 low. No fabricated facts were found.",
    "The audit identified 13 findings:\n- 2 high (identifiers)\n- 4 medium (placement)\n- 6 low (shape)",
    "The audit returned 13 findings, including 2 high, 4 medium and 6 low.",
    "The audit returned 13 findings (all resolved): 2 high, 4 medium, 6 low.",
    "The audit returned 13 findings, e.g. 2 high, 4 medium, 6 low.",
    "The audit returned 13 findings, i.e. 2 high, 4 medium, 6 low.",
])
def test_global_breakdown_after_wrap_or_intro(report):
    result = check_report_audit_totals(report, _make_v10g_audit())
    assert result["stated_by_severity"] == {"high": 2, "medium": 4, "low": 6}
    assert [(r["severity"], r["stated"], r["computed"]) for r in result["findings"]] == [("low", 6, 7)]


def test_corpus_wrapped_low_mismatch_is_kept():
    result = corpus_read(DATA / "claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1", "AI_READI")
    assert any(r.get("severity") == "low" and r["stated"] == 12 and r["computed"] == 13
               for r in result["findings"])


@pytest.mark.parametrize("scope", ["### Core record\n", "### Core record\n\n", "Core record:\n", "### Deferred findings\n"])
@pytest.mark.parametrize("global_total", ["", GOOD + "\n\n"])
def test_heading_or_paragraph_scoped_summary(scope, global_total):
    result = check_report_audit_totals(global_total + scope + "Findings summary: 0 high, 4 medium, 0 low.", _make_v10g_audit())
    assert result["findings"] == []
    assert result["status"] == ("consistent" if global_total else "no_total_stated")


def test_heading_scope_ends_at_next_peer_heading():
    report = GOOD + "\n### Core record\nFindings summary: 0 high, 4 medium, 0 low.\n"
    report += "### Global distribution\nFindings summary: 3 high, 4 medium, 7 low."
    result = check_report_audit_totals(report, _make_v10g_audit())
    assert [(r["severity"], r["stated"]) for r in result["findings"]] == [("high", 3)]


def test_no_total_compares_two_global_clauses():
    result = check_report_audit_totals(
        "Findings by severity: 2 high, 4 medium, 7 low.\n"
        "Findings by severity: 3 high, 4 medium, 7 low.", _make_v10g_audit())
    assert result["stated_total"] is None
    assert [(r["severity"], r["stated"]) for r in result["findings"]] == [("high", 3)]


def saved_sources(tmp_path):
    selected = spec(out_dir=tmp_path / "out")
    selected.report_path.parent.mkdir(parents=True, exist_ok=True)
    selected.report_path.write_text(GOOD, encoding="utf-8")
    first = api._intermediate_dir(selected) / f"{selected.project}_audit.json"
    first.parent.mkdir(parents=True, exist_ok=True)
    first.write_text(_make_v10g_audit(), encoding="utf-8")
    return selected, first


@pytest.mark.parametrize("report_total", [14, 13])
def test_resume_reads_attested_second_snapshot(tmp_path, report_total):
    selected, first = saved_sources(tmp_path)
    second = first.with_name(f"{selected.project}_audit_2.json")
    audit = json.loads(_make_v10g_audit())
    audit["findings"].append({"severity": "low", "record": "full", "slot": "extra", "issue": "extra"})
    second.write_text(json.dumps(audit), encoding="utf-8")
    selected.report_path.write_text("The audit returned 14 findings.", encoding="utf-8")
    prior = api.report_audit_totals_block(selected, {"Audit findings": second.read_text()})
    # Use the real portable snapshot resolver, with both retained snapshots.
    from data_sheets_schema import usage_ledger
    generation = "round2-test-generation"
    existing = {"report_audit_totals": prior,
                "run": {**usage_ledger.run_identity(selected), "generation_id": generation},
                "intermediates": [{"phase": first.name, "path": str(p), "generation_id": generation,
                                   "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                                  for p in (first, second)]}
    selected.report_path.write_text(f"The audit returned {report_total} findings.", encoding="utf-8")
    result = api._current_report_audit_totals(selected, existing)
    assert result["status"] == ("consistent" if report_total == 14 else "mismatch")
    assert result["computed_total"] == 14


def test_legacy_ambiguous_snapshots_preserve_checked_prior(tmp_path):
    selected, first = saved_sources(tmp_path)
    second = first.with_name(f"{selected.project}_audit_2.json")
    audit = json.loads(_make_v10g_audit())
    audit["findings"].append({"severity": "low", "record": "full", "slot": "extra", "issue": "extra"})
    second.write_text(json.dumps(audit), encoding="utf-8")
    selected.report_path.write_text("The audit returned 14 findings.", encoding="utf-8")
    prior = api.report_audit_totals_block(selected, {"Audit findings": second.read_text()})
    assert api._current_report_audit_totals(selected, {"report_audit_totals": prior}) == prior


def test_resume_keeps_newer_instrument_with_sources_present(tmp_path):
    selected, _ = saved_sources(tmp_path)
    prior = api.report_audit_totals_block(selected)
    prior["instrument_version"] = INSTRUMENT_VERSION + 1
    selected.report_path.write_text("The audit returned 12 findings.", encoding="utf-8")
    assert api._current_report_audit_totals(selected, {"report_audit_totals": prior}) == prior


def test_resume_recomputes_noninteger_instrument(tmp_path):
    selected, _ = saved_sources(tmp_path)
    prior = api.report_audit_totals_block(selected)
    prior["instrument_version"] = str(INSTRUMENT_VERSION)
    selected.report_path.write_text("The audit returned 12 findings.", encoding="utf-8")
    result = api._current_report_audit_totals(selected, {"report_audit_totals": prior})
    assert result["instrument_version"] == INSTRUMENT_VERSION
    assert result["status"] == "mismatch"


@pytest.mark.parametrize("number", ["9" * 5000, "9" * 10, "²"], ids=["5000-digits", "10-digits", "superscript"])
def test_unparseable_or_oversized_counts_are_bounded(number):
    assert parse_number(number) is None
    result = check_report_audit_totals(f"The audit returned 13 findings: {number} high, 4 medium, 7 low.", _make_v10g_audit())
    assert result["findings"] == []
    assert check_report_audit_totals(f"{number} findings", _make_v10g_audit())["stated_total"] is None


@pytest.mark.parametrize("missing", ["no-report", "report-path", "no-audit", "audit-path", "invalid-audit"])
def test_unchecked_blocks_have_uniform_shape(tmp_path, missing):
    cases = {"no-report": (None, None), "report-path": (tmp_path / "missing.md", None),
             "no-audit": (GOOD, None), "audit-path": (GOOD, tmp_path / "missing.json"),
             "invalid-audit": (GOOD, "not JSON")}
    result = check_report_audit_totals(*cases[missing])
    checked = check_report_audit_totals(GOOD, _make_v10g_audit())
    assert result.keys() == checked.keys()
    assert result["stated_severity_summaries"] == []
    assert result["stated_severity_counts"] == {}
