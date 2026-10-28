"""Tests for checking reconciliation reports' stated finding totals against structured audit (#4766)."""

import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

from data_sheets_schema import api_runner
from data_sheets_schema.api_runner import PHASE_INSTRUCTIONS
from data_sheets_schema.report_audit_totals import (
    INSTRUMENT_VERSION,
    check_report_audit_totals,
    extract_report_audit_totals,
    parse_number,
)
from tests.test_download.test_api_runner import FakeMessages, FakeResponse, spec

FULL = {"id": "x", "title": "T", "keywords": ["a"]}
CORE = {"id": "x", "title": "T", "keywords": ["a"]}


def _make_v10g_audit() -> str:
    """13 entries: 2 high, 4 medium, 7 low. Summary says 12."""
    findings = []
    # 2 high
    for i in range(2):
        findings.append({"severity": "high", "record": "full", "slot": f"h_{i}", "issue": f"high issue {i}"})
    # 4 medium
    for i in range(4):
        findings.append({"severity": "medium", "record": "core", "slot": f"m_{i}", "issue": f"medium issue {i}"})
    # 7 low
    for i in range(7):
        findings.append({"severity": "low", "record": "both", "slot": f"l_{i}", "issue": f"low issue {i}"})
    audit_data = {
        "summary": "Phase 3 source audit produced 12 findings.",
        "findings": findings,
    }
    return json.dumps(audit_data)


class TestReportAuditTotalsUnit(unittest.TestCase):
    def test_parse_number(self):
        self.assertEqual(parse_number("0"), 0)
        self.assertEqual(parse_number("zero"), 0)
        self.assertEqual(parse_number("12"), 12)
        self.assertEqual(parse_number("twelve"), 12)
        self.assertEqual(parse_number("twenty-three"), 23)
        self.assertIsNone(parse_number("none"))
        self.assertIsNone(parse_number("no"))
        self.assertIsNone(parse_number("unknown"))

    def test_synthetic_v10g_shape_with_mismatches(self):
        """13 entries (2 high, 4 medium, 7 low), audit summary saying 12,

        report saying 'twelve findings' and 'six low' -> exactly 2 mismatches (total and low).
        """
        audit_json = _make_v10g_audit()
        report = (
            "# Reconciliation Report\n\n"
            "The audit identified twelve findings against the record: 2 high, 4 medium, and six low.\n\n"
            "## Dispositions\n"
            "| slot | disposition | record | reason |\n"
            "|---|---|---|---|\n"
            "| `keywords` | retained | full | kept |\n"
        )
        res = check_report_audit_totals(report, audit_json)
        self.assertTrue(res["checked"])
        self.assertEqual(res["instrument_version"], INSTRUMENT_VERSION)
        self.assertEqual(res["status"], "mismatch")
        self.assertEqual(res["stated_total"], 12)
        self.assertEqual(res["computed_total"], 13)
        self.assertEqual(res["stated_by_severity"], {"high": 2, "medium": 4, "low": 6})
        self.assertEqual(res["computed_by_severity"], {"high": 2, "medium": 4, "low": 7})

        mismatches = res["mismatches"]
        self.assertEqual(len(mismatches), 2)

        # 1. Total mismatch
        tot_m = next(m for m in mismatches if m["kind"] == "finding_total_mismatch")
        self.assertEqual(tot_m["stated"], 12)
        self.assertEqual(tot_m["computed"], 13)
        self.assertEqual(tot_m["record"], "report")

        # 2. Low severity mismatch
        low_m = next(m for m in mismatches if m["kind"] == "finding_severity_mismatch")
        self.assertEqual(low_m["severity"], "low")
        self.assertEqual(low_m["stated"], 6)
        self.assertEqual(low_m["computed"], 7)
        self.assertEqual(low_m["record"], "report")

    def test_conflicting_totals_within_same_report_detected(self):
        """A report stating 13 findings in its header but twelve findings in body prose
        is flagged with finding_total_contradiction even when the primary total (13) matches."""
        audit_json = _make_v10g_audit()
        report = (
            "# Reconciliation Report\n\n"
            "**Findings received:** 13 (2 high, 4 medium, 7 low)\n\n"
            "In summary, the Phase 3 audit returned twelve findings.\n\n"
            "## Dispositions\n"
            "| slot | disposition | record | reason |\n"
            "|---|---|---|---|\n"
            "| `keywords` | retained | full | kept |\n"
        )
        res = check_report_audit_totals(report, audit_json)
        self.assertTrue(res["checked"])
        self.assertEqual(res["status"], "mismatch")
        self.assertEqual(res["stated_total"], 13)
        self.assertEqual(res["stated_totals"], [13, 12])
        self.assertEqual(res["computed_total"], 13)
        contradiction = next(m for m in res["mismatches"] if m["kind"] == "finding_total_contradiction")
        self.assertEqual(contradiction["stated_totals"], [13, 12])
        self.assertEqual(contradiction["computed"], 13)

    def test_synthetic_v10g_shape_matching(self):
        """Report with 13, 2, 4, 7 -> 0 mismatches."""
        audit_json = _make_v10g_audit()
        report = (
            "# Reconciliation Report\n\n"
            "The audit identified 13 findings against the record: 2 high, 4 medium, and 7 low.\n\n"
            "## Dispositions\n"
            "| slot | disposition | record | reason |\n"
            "|---|---|---|---|\n"
            "| `keywords` | retained | full | kept |\n"
        )
        res = check_report_audit_totals(report, audit_json)
        self.assertTrue(res["checked"])
        self.assertEqual(res["status"], "consistent")
        self.assertEqual(res["stated_total"], 13)
        self.assertEqual(res["computed_total"], 13)
        self.assertEqual(res["mismatches"], [])
        self.assertEqual(res["findings"], [])

    def test_malformed_or_missing_audit(self):
        """Malformed audit -> checked: False, with specific reason from _audit_shape_problem."""
        report = "# Reconciliation Report\n\nThe audit identified 12 findings.\n"
        res_none = check_report_audit_totals(report, None)
        self.assertFalse(res_none["checked"])
        self.assertEqual(res_none["reason"], "missing audit")
        self.assertEqual(res_none["status"], "not_checked")

        res_invalid = check_report_audit_totals(report, "{not valid json}")
        self.assertFalse(res_invalid["checked"])
        self.assertEqual(res_invalid["reason"], "malformed audit JSON")
        self.assertEqual(res_invalid["status"], "not_checked")

        # Audit missing summary
        res_no_sum = check_report_audit_totals(report, json.dumps({"findings": []}))
        self.assertFalse(res_no_sum["checked"])
        self.assertEqual(res_no_sum["reason"], "audit.summary must be a non-empty JSON string")
        self.assertEqual(res_no_sum["status"], "not_checked")

    def test_report_stating_no_total_recorded_as_no_total_stated(self):
        """Reports stating no total recorded as status: 'no_total_stated' with stated_total: None (never as consistent)."""
        audit_json = _make_v10g_audit()
        report = (
            "# Reconciliation Report\n\n"
            "Here is the reconciliation narrative without mentioning any total finding count.\n\n"
            "## Dispositions\n"
            "| slot | disposition | record | reason |\n"
            "|---|---|---|---|\n"
            "| `keywords` | retained | full | kept |\n"
        )
        res = check_report_audit_totals(report, audit_json)
        self.assertTrue(res["checked"])
        self.assertEqual(res["status"], "no_total_stated")
        self.assertIsNone(res["stated_total"])
        self.assertEqual(res["mismatches"], [])
        self.assertEqual(res["findings"], [])

    def test_severity_mismatch_detected_even_when_no_total_stated(self):
        """Per-severity subtotals are checked even when no overall finding total is stated."""
        audit_json = _make_v10g_audit()
        report = (
            "# Reconciliation Report\n\n"
            "The reconciliation addressed 2 high-severity findings, 4 medium-severity findings, and 10 low-severity findings.\n\n"
            "## Dispositions\n"
            "| slot | disposition | record | reason |\n"
            "|---|---|---|---|\n"
            "| `keywords` | retained | full | kept |\n"
        )
        res = check_report_audit_totals(report, audit_json)
        self.assertTrue(res["checked"])
        self.assertIsNone(res["stated_total"])
        self.assertEqual(res["stated_by_severity"], {"high": 2, "medium": 4, "low": 10})
        self.assertEqual(res["status"], "mismatch")
        self.assertEqual(len(res["mismatches"]), 1)
        self.assertEqual(res["mismatches"][0]["kind"], "finding_severity_mismatch")
        self.assertEqual(res["mismatches"][0]["severity"], "low")
        self.assertEqual(res["mismatches"][0]["stated"], 10)
        self.assertEqual(res["mismatches"][0]["computed"], 7)

    def test_subset_counts_and_historical_false_positives_rejected(self):
        """Subset counts, combined severity buckets, and section numbers are not misparsed."""
        text = (
            "# Reconciliation\n\n"
            "Six findings were deliberately left as-is because the core record is immutable. "
            "Fourteen findings produced edits to the full record. "
            "Three findings were raised for the record without recommending change. "
            "No findings were raised against the core record.\n\n"
            "### 2.1 High severity\n"
            "## 6. Additional changes not driven by audit findings\n"
            "1. First item\n"
        )
        stated_total, sevs = extract_report_audit_totals(text)
        self.assertIsNone(stated_total)
        self.assertEqual(sevs, {})

        # Combined buckets and 'N high-severity pairs'
        combined = (
            "**Audit findings addressed:** 23 (2 high/medium-severity structural, 21 medium and low)\n"
            "We grouped 2 high-severity pairs into one section.\n"
        )
        total2, sevs2 = extract_report_audit_totals(combined)
        self.assertEqual(total2, 23)
        self.assertEqual(sevs2, {})

    def test_v10_chorus_canary_phrasing_supported(self):
        """Supports inline bold 'N findings: M medium, L low' phrasing from v10 CHORUS canaries."""
        t1, s1 = extract_report_audit_totals(
            "The computed audit counts record **14 findings: 2 medium, 12 low** (no high)."
        )
        self.assertEqual(t1, 14)
        self.assertEqual(s1, {"medium": 2, "low": 12, "high": 0})

        t2, s2 = extract_report_audit_totals(
            "The computed audit counts give **12 findings: 6 medium, 6 low** (no high)."
        )
        self.assertEqual(t2, 12)
        self.assertEqual(s2, {"medium": 6, "low": 6, "high": 0})


class _ReportTotalsFake(FakeMessages):
    def __init__(self, first_report: str, second_report: str, audit_str: str):
        super().__init__()
        self.first_report = first_report
        self.second_report = second_report
        self.audit_str = audit_str

    def create(self, **kw):
        blob = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
        if PHASE_INSTRUCTIONS["report_regate"] in blob:
            self.calls.append(kw)
            return FakeResponse(self.second_report)
        if PHASE_INSTRUCTIONS["report"] in blob:
            self.calls.append(kw)
            return FakeResponse(self.first_report)
        if PHASE_INSTRUCTIONS["audit"] in blob:
            self.calls.append(kw)
            return FakeResponse(self.audit_str)
        return super().create(**kw)


class TestReportAuditTotalsGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "out"
        self._client = api_runner._client
        self.addCleanup(lambda: setattr(api_runner, "_client", self._client))

    def _run(self, fake):
        client = type("C", (), {})()
        client.messages = fake
        api_runner._client = lambda: client
        s = spec(out_dir=self.out)
        with unittest.mock.patch.object(api_runner, "_validator_lines", lambda *a: ([], None)):
            res = api_runner.execute(s)
        return s, res, yaml.safe_load((self.out / "CHORUS_provenance.yaml").read_text())

    def test_audit_total_mismatch_triggers_report_regate(self):
        audit_json = _make_v10g_audit()
        bad_report = (
            "# Reconciliation\n\n"
            "The audit identified twelve findings.\n\n"
            "## Dispositions\n"
            "| slot | disposition | record | reason |\n"
            "|---|---|---|---|\n"
            "| `keywords` | retained | full | kept |\n"
        )
        fixed_report = (
            "# Reconciliation\n\n"
            "The audit identified 13 findings.\n\n"
            "## Dispositions\n"
            "| slot | disposition | record | reason |\n"
            "|---|---|---|---|\n"
            "| `keywords` | retained | full | kept |\n"
        )
        fake = _ReportTotalsFake(bad_report, fixed_report, audit_json)
        s, res, d = self._run(fake)

        self.assertEqual([u["phase"] for u in res["usage"]],
                         ["full", "audit", "reconcile_full", "report", "report_regate"])
        g = d["report_gate"]
        self.assertTrue(g["regenerated"])
        self.assertTrue(g["findings_include_report_audit_totals"])
        self.assertEqual(g["findings_before"], 1)
        self.assertEqual(g["findings_after"], 0)
        self.assertEqual(g["report_audit_totals_before"]["status"], "mismatch")
        self.assertEqual(g["report_audit_totals_after"]["status"], "consistent")

        # Provenance record check
        self.assertIn("report_audit_totals", d)
        self.assertEqual(d["report_audit_totals"]["status"], "consistent")
        self.assertEqual(d["report_audit_totals"]["stated_total"], 13)
        self.assertEqual(d["report_audit_totals"]["computed_total"], 13)

        # Regate prompt included the mismatch
        regate = next(c for c in fake.calls if PHASE_INSTRUCTIONS["report_regate"] in
                      " ".join(p.get("text", "") for p in c["messages"][0]["content"]))
        blob = " ".join(p.get("text", "") for p in regate["messages"][0]["content"])
        self.assertIn("finding_total_mismatch", blob)
        self.assertIn("report states 12 findings; structured audit has 13", blob)

    def test_regate_rollback_when_core_report_claims_contradictions_increase(self):
        """A rewrite that fixes 2 audit-totals mismatches but introduces 1 disposition contradiction
        is rolled back even though combined findings dropped from 2 to 1."""
        audit_json = _make_v10g_audit()
        initial_report = (
            "# Reconciliation\n\n"
            "The audit identified twelve findings: 2 high, 4 medium, and six low.\n\n"
            "## Dispositions\n"
            "| slot | disposition | record | reason |\n"
            "|---|---|---|---|\n"
            "| `keywords` | retained | full | kept |\n"
        )
        worse_core_report = (
            "# Reconciliation\n\n"
            "The audit identified 13 findings: 2 high, 4 medium, and 7 low.\n\n"
            "## Dispositions\n"
            "| slot | disposition | record | reason |\n"
            "|---|---|---|---|\n"
            "| `keywords` | removed | full | gone |\n"
        )
        fake = _ReportTotalsFake(initial_report, worse_core_report, audit_json)
        s, res, d = self._run(fake)
        g = d["report_gate"]
        self.assertFalse(g["regenerated"])
        self.assertIn("worse", g["reason"])
        self.assertEqual(g["findings_before"], 2)
        self.assertEqual(g["findings_after"], 2)
        self.assertIn("| `keywords` | retained | full |", s.report_path.read_text())


if __name__ == "__main__":
    unittest.main()


# D57: retain externally observed journal heads across fixture resumes.
import pytest
pytestmark = pytest.mark.usefixtures("journal_launch_monitor")
