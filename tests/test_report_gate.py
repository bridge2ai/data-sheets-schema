"""The reconciliation report is checked before the run completes (#929,
v8 step E), its dispositions table gives the checker claims it can read
(#684), and the gate reads an unmeasured report row as unmeasured.

The v7 production arm's report metric was vacuous on 11 of 12 records: the
reports carried neither claim form the checker reads, so `report findings
0` sat in every canary table as a held floor over `claims_checked: 0`. The
v8 report phase ends with a `## Dispositions` table whose rows are claims of
removal or presence; a report that contradicts the records is regenerated
once with the contradictions named; and the gate treats a report with no
readable claim as unmeasured rather than as zero findings.
"""

import hashlib
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

from data_sheets_schema import api_runner, canary
from data_sheets_schema.api_runner import PHASE_INSTRUCTIONS
from data_sheets_schema.report_claims import check_report, disposition_rows
from tests.test_download.test_api_runner import FakeMessages, FakeResponse, spec

FULL = {"id": "x", "title": "T", "keywords": ["a"], "funders": [{"name": "NIH"}]}
CORE = {"id": "x", "title": "T", "keywords": ["a"]}
DECLARED = {"Dataset": {"id", "title", "keywords", "funders", "license"},
            "CoreDataset": {"id", "title", "keywords", "license"}}


def _report(tmp: Path, table: str) -> Path:
    p = tmp / "r.md"
    p.write_text("# Reconciliation\n\nProse.\n\n## Dispositions\n\n"
                 "| slot | disposition | record | reason |\n|---|---|---|---|\n" + table, encoding="utf-8")
    return p


class TestDispositionRows(unittest.TestCase):
    def test_rows_are_read_from_a_table_with_a_disposition_column(self):
        rows = disposition_rows("| slot | disposition | record | reason |\n|---|---|---|---|\n"
                                "| `keywords` | retained | full | fine |\n| `license` | removed | core | absent |\n"
                                "\n| a | b |\n|---|---|\n| `x` | y |\n")
        self.assertEqual([(r["slot"], r["disposition"], r["record"]) for r in rows],
                         [("keywords", "retained", "full"), ("license", "removed", "core")])

    def test_a_record_cell_outside_the_vocabulary_reads_as_either(self):
        rows = disposition_rows("| slot | disposition | record |\n|---|---|---|\n| `keywords` | changed | all |\n")
        self.assertEqual(rows[0]["record"], "either")


class TestPresenceClaims(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_a_retained_slot_the_record_lacks_is_a_finding(self):
        """#914: AI_READI v7 rep3 claimed extension_mechanism was retained; neither record had it."""
        out = check_report(_report(self.dir, "| `license` | retained | both | kept |\n"), FULL, CORE, DECLARED)
        self.assertEqual([(f["kind"], f["slot"]) for f in out["findings"]], [("retention_not_shown", "license")])
        self.assertEqual(out["claims_checked"], 1)
        self.assertEqual(out["disposition_rows"], 1)

    def test_a_retained_slot_the_record_carries_is_a_checked_claim_with_no_finding(self):
        out = check_report(_report(self.dir, "| `keywords` | retained | full | kept |\n| `funders` | changed | full | fixed |\n"),
                           FULL, CORE, DECLARED)
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["claims_checked"], 2)

    def test_a_removed_row_is_still_read_by_the_removal_check(self):
        out = check_report(_report(self.dir, "| `keywords` | removed | full | gone |\n"), FULL, CORE, DECLARED)
        self.assertEqual([f["kind"] for f in out["findings"]], ["removal_not_performed"])
        self.assertEqual(out["claims_checked"], 1)

    def test_a_row_naming_no_record_is_read_against_the_core(self):
        out = check_report(_report(self.dir, "| `funders` | retained | | kept |\n"), FULL, CORE, DECLARED)
        self.assertEqual([f["kind"] for f in out["findings"]], ["retention_not_shown"])

    def test_a_report_without_the_table_still_reads_zero_claims(self):
        p = self.dir / "r.md"; p.write_text("# Reconciliation\nNo discrepancies.\n", encoding="utf-8")
        out = check_report(p, FULL, CORE, DECLARED)
        self.assertEqual((out["claims_checked"], out["disposition_rows"], out["findings"]), (0, 0, []))


class TestTheGateReading(unittest.TestCase):
    """#684: findings 0 over claims_checked 0 is unmeasured, not a held floor."""

    BLOCKS = {"pair": {"ran": True, "errors": 0}, "grounding": {"checked": True},
              "form": {"checked": True}}
    BASE = {n: 0 for n, _, _ in canary.METRICS}

    def test_vacuity_is_no_finding_over_no_readable_claim(self):
        self.assertTrue(canary.report_vacuous({"checked": True, "findings": [], "claims_checked": 0}))
        self.assertTrue(canary.report_vacuous({"checked": True, "findings": []}))        # legacy block
        self.assertFalse(canary.report_vacuous({"checked": True, "findings": [], "claims_checked": 3}))
        self.assertFalse(canary.report_vacuous({"checked": True, "findings": [{"kind": "false_schema_claim"}],
                                                "claims_checked": 0}))                    # a finding is a finding
        self.assertFalse(canary.report_vacuous({"checked": False}))

    def test_an_earlier_records_vacuous_row_is_unmeasured_and_not_gated(self):
        v = canary.verdict({**self.BLOCKS, "report": {"checked": True, "findings": []}}, self.BASE)
        self.assertEqual(v["status"], canary.OK)
        row = next(r for r in v["rows"] if r["metric"] == "report findings")
        self.assertIsNone(row["run"])
        self.assertIn("unmeasured", row["note"])
        self.assertNotIn("report findings", v["blind"])

    def test_a_run_asked_for_the_table_that_reads_no_claim_is_blind(self):
        v = canary.verdict({**self.BLOCKS, "report": {"checked": True, "findings": [], "claims_checked": 0,
                                                       "dispositions_expected": True}}, self.BASE)
        self.assertEqual(v["status"], canary.UNMEASURABLE)
        self.assertIn("report findings", v["blind"])

    def test_a_measured_row_is_gated_as_before(self):
        checks = {**self.BLOCKS, "report": {"checked": True, "findings": [{"kind": "retention_not_shown"}],
                                            "claims_checked": 2, "dispositions_expected": True}}
        self.assertEqual(canary.verdict(checks, self.BASE)["status"], canary.REGRESSED)

    def test_a_baseline_that_resolved_but_never_measured_the_report_is_a_floor_with_its_basis(self):
        base = dict(self.BASE); base["report findings"] = None
        checks = {**self.BLOCKS, "report": {"checked": True, "findings": [], "claims_checked": 2,
                                            "dispositions_expected": True}}
        v = canary.verdict(checks, base)
        self.assertEqual(v["status"], canary.OK)
        row = next(r for r in v["rows"] if r["metric"] == "report findings")
        self.assertEqual(row["baseline_worst"], 0)
        self.assertIn("floor 0", row["baseline_basis"])
        self.assertNotIn("report findings", v["unbaselined"])
        checks["report"]["findings"] = [{"kind": "retention_not_shown"}]
        self.assertEqual(canary.verdict(checks, base)["status"], canary.REGRESSED)

    def test_a_baseline_that_resolved_nothing_is_still_unmeasurable(self):
        """#599: a mistyped prefix must not become a floor of 0 on every metric."""
        base = {n: None for n, _, _ in canary.METRICS}
        v = canary.verdict({**self.BLOCKS, "report": {"checked": True, "findings": [], "claims_checked": 2}}, base)
        self.assertEqual(v["status"], canary.UNMEASURABLE)

    def test_the_baseline_skips_vacuous_replicates(self):
        """The v7 production arm: 11 of 12 reports carry no readable claim."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rep, block in (("rep1", {"checked": True, "findings": []}),
                               ("rep2", {"checked": True, "findings": [], "claims_checked": 0})):
                d = root / "m_core" / f"2026-01-01_x_{rep}"; d.mkdir(parents=True)
                (d / "P_provenance.yaml").write_text(yaml.safe_dump({
                    "pair_consistency": {"ran": True, "errors": 1}, "report_claims": block,
                    "grounding": {"checked": True}, "form": {"checked": True}}))
            bar = canary.baseline_for("P", "2026-01-01_x", method="m", concat_dir=root)
        self.assertEqual(bar["pair errors"], 1)
        self.assertIsNone(bar["report findings"])


class _ReportFake(FakeMessages):
    """The first report contradicts the record; the re-check answer does not."""

    def __init__(self, first_table, second_table):
        super().__init__(); self.first, self.second = first_table, second_table

    def create(self, **kw):
        blob = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
        if PHASE_INSTRUCTIONS["report_regate"] in blob:
            self.calls.append(kw)
            return FakeResponse("# Reconciliation\n\n## Dispositions\n\n| slot | disposition | record | reason |\n"
                                "|---|---|---|---|\n" + self.second)
        if PHASE_INSTRUCTIONS["report"] in blob:
            self.calls.append(kw)
            return FakeResponse("# Reconciliation\n\n## Dispositions\n\n| slot | disposition | record | reason |\n"
                                "|---|---|---|---|\n" + self.first)
        return super().create(**kw)


class TestTheRunnerGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "out"
        self._client = api_runner._client
        self.addCleanup(lambda: setattr(api_runner, "_client", self._client))

    def _run(self, fake):
        client = type("C", (), {})(); client.messages = fake
        api_runner._client = lambda: client
        s = spec(out_dir=self.out)
        with unittest.mock.patch.object(api_runner, "_validator_lines", lambda *a: ([], None)):
            res = api_runner.execute(s)
        return s, res, yaml.safe_load((self.out / "CHORUS_provenance.yaml").read_text())

    def test_a_contradicting_report_is_regenerated_once_with_the_contradiction_named(self):
        fake = _ReportFake("| `keywords` | removed | full | gone |\n",
                           "| `keywords` | retained | full | kept |\n")
        s, res, d = self._run(fake)
        self.assertEqual([u["phase"] for u in res["usage"]], ["full", "audit", "reconcile_full", "report", "report_regate"])
        g = d["report_gate"]
        self.assertEqual((g["findings_before"], g["regenerated"], g["findings_after"]), (1, True, 0))
        self.assertEqual((g["claims_checked_before"], g["claims_checked_after"]), (1, 1))
        self.assertEqual(d["report_claims"]["findings"], [])
        self.assertEqual(d["report_claims"]["claims_checked"], 1)
        self.assertTrue(d["report_claims"]["dispositions_expected"])
        regate = next(c for c in fake.calls if PHASE_INSTRUCTIONS["report_regate"] in
                      " ".join(p.get("text", "") for p in c["messages"][0]["content"]))
        blob = " ".join(p.get("text", "") for p in regate["messages"][0]["content"])
        self.assertIn("removal_not_performed", blob)
        self.assertIn("# Reconciliation report as written", blob)
        self.assertTrue((s.provenance_path.parent / "intermediate" / "CHORUS_report_before_regate.md").exists())
        self.assertEqual(d["model"]["max_tokens_by_phase"]["report_regate"], api_runner.PHASE_MAX_TOKENS["report"])

    def test_a_report_that_still_contradicts_after_the_re_check_is_recorded_as_such(self):
        fake = _ReportFake("| `keywords` | removed | full | gone |\n", "| `keywords` | removed | full | gone |\n")
        s, res, d = self._run(fake)
        g = d["report_gate"]
        self.assertEqual((g["findings_before"], g["regenerated"], g["findings_after"]), (1, True, 1))
        self.assertEqual(g["remaining"][0]["kind"], "removal_not_performed")
        self.assertEqual(len(d["report_claims"]["findings"]), 1)

    def test_a_clean_report_makes_no_extra_call(self):
        fake = _ReportFake("| `keywords` | retained | full | kept |\n", "unused")
        s, res, d = self._run(fake)
        self.assertEqual([u["phase"] for u in res["usage"]], ["full", "audit", "reconcile_full", "report"])
        self.assertEqual((d["report_gate"]["findings_before"], d["report_gate"]["regenerated"]), (0, False))

    def test_the_companions_hash_is_of_the_log_as_it_ends(self):
        """#652: at record build the md5 was of a prefix of the reasoning log."""
        fake = _ReportFake("| `keywords` | removed | full | gone |\n", "| `keywords` | retained | full | kept |\n")
        s, res, d = self._run(fake)
        log = api_runner._reasoning_path(s)
        self.assertEqual(d["companions"]["reasoning_log"]["md5"], hashlib.md5(log.read_bytes()).hexdigest())


class TestTheAssemblyDigestCoversIt(unittest.TestCase):
    def test_editing_either_instruction_moves_the_digest(self):
        before = api_runner.assembly_digest()["sha256"]
        for key in ("report", "report_regate"):
            with unittest.mock.patch.dict(PHASE_INSTRUCTIONS, {key: "changed"}):
                self.assertNotEqual(api_runner.assembly_digest()["sha256"], before)


if __name__ == "__main__":
    unittest.main()
