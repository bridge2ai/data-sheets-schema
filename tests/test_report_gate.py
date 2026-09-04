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

    def test_a_record_cell_outside_the_vocabulary_reads_as_invalid_and_an_empty_one_as_either(self):
        rows = disposition_rows("| slot | disposition | record |\n|---|---|---|\n| `keywords` | changed | all |\n"
                                "| `keywords` | changed | |\n")
        self.assertEqual([r["record"] for r in rows], ["invalid", "either"])


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

    def test_both_on_a_slot_the_core_does_not_declare_reads_as_full(self):
        """#990: `retained | both` on `citation` cannot be satisfied — CoreDataset has no such slot."""
        out = check_report(_report(self.dir, "| `funders` | retained | both | kept |\n"), FULL, CORE, DECLARED)
        self.assertEqual(out["findings"], [])                     # funders is not a CoreDataset slot in DECLARED
        out = check_report(_report(self.dir, "| `keywords` | retained | both | kept |\n"), FULL, {"id": "x"}, DECLARED)
        self.assertEqual([f["kind"] for f in out["findings"]], ["retention_not_shown"])   # declared on both, absent from core
        out = check_report(_report(self.dir, "| `funders` | retained | core | kept |\n"), FULL, CORE, DECLARED)
        self.assertEqual([f["kind"] for f in out["findings"]], ["retention_not_shown"])   # `core` stays literal

    def test_a_row_naming_no_record_is_a_finding_only_when_neither_record_carries_it(self):
        out = check_report(_report(self.dir, "| `license` | retained | | kept |\n"), FULL, CORE, DECLARED)
        self.assertEqual([f["kind"] for f in out["findings"]], ["retention_not_shown"])

    def test_removal_rows_honour_the_record_column(self):
        """#964: `removed | both` with the slot still in full is a finding; `removed | full` is read against full."""
        out = check_report(_report(self.dir, "| `funders` | removed | both | gone |\n"), FULL, CORE, DECLARED)
        self.assertEqual([(f["kind"], f["record"]) for f in out["findings"]], [("removal_not_performed", "both")])
        out = check_report(_report(self.dir, "| `funders` | removed | core | gone |\n"), FULL, CORE, DECLARED)
        self.assertEqual(out["findings"], [])                     # core has no funders: performed
        out = check_report(_report(self.dir, "| `funders` | removed | full | gone |\n"), FULL, CORE, DECLARED)
        self.assertEqual([f["record"] for f in out["findings"]], ["full"])

    def test_an_unnamed_retention_is_present_if_either_record_carries_it(self):
        """#963: a full-only slot is legitimately absent from the derived core."""
        out = check_report(_report(self.dir, "| `funders` | retained | | kept |\n"), FULL, CORE, DECLARED)
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["claims_checked"], 1)

    def test_a_record_cell_outside_the_vocabulary_is_unnamed_not_guessed(self):
        out = check_report(_report(self.dir, "| `funders` | retained | full only | kept |\n"), FULL, CORE, DECLARED)
        self.assertEqual((out["findings"], out["claims_checked"], out["claims_unnamed"]), ([], 0, 1))

    def test_a_reason_cell_beginning_with_a_removal_verb_is_not_a_removal_claim(self):
        """#962: the generic table scan must not read the free-text reason column."""
        out = check_report(_report(self.dir, "| `funders` | retained | full | Dropped the duplicate second entry; slot kept |\n"),
                           FULL, CORE, DECLARED)
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["claims_checked"], 1)

    def test_a_numbered_finding_table_with_a_disposition_column_yields_no_claim(self):
        """#962: the bare-name fallback must not accept digits."""
        p = self.dir / "r.md"
        p.write_text("| # | Finding | Disposition | Notes |\n|---|---|---|---|\n| 1 | dup | Changed: replaced | x |\n"
                     "| 2 | odd | Retained | y |\n", encoding="utf-8")
        out = check_report(p, FULL, CORE, DECLARED)
        self.assertEqual((out["findings"], out["claims_checked"]), ([], 0))

    def test_an_arrow_slot_cell_claims_the_destination(self):
        out = check_report(_report(self.dir, "| `license` -> `keywords` | changed | full | moved |\n"), FULL, CORE, DECLARED)
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["claims_checked"], 1)

    def test_a_retained_indexed_entry_is_checked(self):
        out = check_report(_report(self.dir, "| `funders[0]` | retained | full | kept |\n| `funders[4]` | retained | full | kept |\n"),
                           FULL, CORE, DECLARED)
        self.assertEqual([f["slot"] for f in out["findings"]], ["funders[4]"])
        self.assertEqual(out["claims_checked"], 2)

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

    def test_the_blind_row_says_why(self):
        v = canary.verdict({**self.BLOCKS, "report": {"checked": True, "findings": [], "claims_checked": 0,
                                                       "dispositions_expected": True}}, self.BASE)
        row = next(r for r in v["rows"] if r["metric"] == "report findings")
        self.assertIn("asked for a dispositions table", row["note"])

    def test_a_measured_row_is_gated_as_before(self):
        checks = {**self.BLOCKS, "report": {"checked": True, "findings": [{"kind": "retention_not_shown"}],
                                            "claims_checked": 2, "dispositions_expected": True}}
        self.assertEqual(canary.verdict(checks, self.BASE)["status"], canary.REGRESSED)

    def test_a_vacuous_baseline_is_a_floor_with_its_basis_but_an_unchecked_one_is_not(self):
        base = dict(self.BASE); base["report findings"] = None
        checks = {**self.BLOCKS, "report": {"checked": True, "findings": [], "claims_checked": 2,
                                            "dispositions_expected": True}}
        v = canary.verdict(checks, base, report_basis={"measured": 0, "vacuous": 3, "unchecked": 0})
        self.assertEqual(v["status"], canary.OK)
        row = next(r for r in v["rows"] if r["metric"] == "report findings")
        self.assertEqual(row["baseline_worst"], 0)
        self.assertIn("floor 0", row["baseline_basis"])
        self.assertNotIn("report findings", v["unbaselined"])
        checks["report"]["findings"] = [{"kind": "retention_not_shown"}]
        self.assertEqual(canary.verdict(checks, base, report_basis={"measured": 0, "vacuous": 3, "unchecked": 0})["status"],
                         canary.REGRESSED)
        # #599's distinction: a baseline whose checker never ran is not a floor of zero.
        checks["report"]["findings"] = []
        self.assertEqual(canary.verdict(checks, base, report_basis={"measured": 0, "vacuous": 0, "unchecked": 3})["status"],
                         canary.UNMEASURABLE)
        self.assertEqual(canary.verdict(checks, base)["status"], canary.UNMEASURABLE)   # no basis given

    def test_a_baseline_that_resolved_nothing_is_still_unmeasurable(self):
        """#599: a mistyped prefix must not become a floor of 0 on every metric."""
        base = {n: None for n, _, _ in canary.METRICS}
        v = canary.verdict({**self.BLOCKS, "report": {"checked": True, "findings": [], "claims_checked": 2}}, base)
        self.assertEqual(v["status"], canary.UNMEASURABLE)

    def test_report_basis_counts_measured_vacuous_and_unchecked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rep, block in (("rep1", {"checked": True, "findings": []}),
                               ("rep2", {"checked": True, "findings": [], "claims_checked": 4}),
                               ("rep3", {"checked": False, "reason": "no report"})):
                d = root / "m_core" / f"2026-01-01_x_{rep}"; d.mkdir(parents=True)
                (d / "P_provenance.yaml").write_text(yaml.safe_dump({"report_claims": block}))
            self.assertEqual(canary.report_basis("P", "2026-01-01_x", method="m", concat_dir=root),
                             {"measured": 1, "vacuous": 1, "unchecked": 1})

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

    def test_a_prior_invocations_regeneration_is_not_repeated(self):
        """#965: once per run, not once per invocation."""
        s = spec(out_dir=self.out)
        s.provenance_path.parent.mkdir(parents=True, exist_ok=True)
        s.full_path.write_text(yaml.safe_dump(FULL)); s.core_path.write_text(yaml.safe_dump(CORE))
        s.report_path.write_text("# R\n\n## Dispositions\n\n| slot | disposition | record | reason |\n|---|---|---|---|\n"
                                 "| `keywords` | removed | full | gone |\n")
        s.provenance_path.write_text(yaml.safe_dump({"report_gate": {"regenerated": True, "findings_after": 1}}))
        class Boom:
            messages = property(lambda self: (_ for _ in ()).throw(AssertionError("must not call")))
        out = api_runner._gate_report(s, Boom(), {"name": "m", "max_tokens": 10, "temperature": None,
                                                   "temperature_applies": False}, [], {})
        self.assertFalse(out["regenerated"])
        self.assertIn("prior invocation", out["reason"])
        self.assertEqual(out["prior"]["regenerated"], True)

    def test_a_report_without_the_table_is_regenerated_once(self):
        """The table is itself a claim the gate checks; its absence is a contradiction."""
        fake = _ReportFake("unused", "| `keywords` | retained | full | kept |\n")
        _orig = fake.create
        def create(**kw):
            blob = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
            if PHASE_INSTRUCTIONS["report"] in blob and PHASE_INSTRUCTIONS["report_regate"] not in blob:
                fake.calls.append(kw); return FakeResponse("# Reconciliation\n\nNo discrepancies.\n")
            return _orig(**kw)
        fake.create = create
        s, res, d = self._run(fake)
        g = d["report_gate"]
        self.assertTrue(g["table_missing_before"])
        self.assertEqual((g["findings_before"], g["regenerated"], g["findings_after"]), (0, True, 0))
        self.assertEqual(d["report_claims"]["claims_checked"], 1)
        regate = next(c for c in fake.calls if PHASE_INSTRUCTIONS["report_regate"] in
                      " ".join(p.get("text", "") for p in c["messages"][0]["content"]))
        self.assertIn("dispositions_table_missing", " ".join(p.get("text", "") for p in regate["messages"][0]["content"]))

    def test_a_worse_rewrite_is_rolled_back(self):
        fake = _ReportFake("| `keywords` | removed | full | gone |\n",
                           "| `keywords` | removed | full | gone |\n| `license` | retained | full | kept |\n")
        s, res, d = self._run(fake)
        g = d["report_gate"]
        self.assertFalse(g["regenerated"])
        self.assertIn("worse", g["reason"])
        self.assertEqual(g["findings_after"], 1)
        self.assertNotIn("license", s.report_path.read_text())

    def test_a_truncated_rewrite_is_not_written(self):
        fake = _ReportFake("| `keywords` | removed | full | gone |\n", "| `keywords` | retained | full | kept |\n")
        _orig = fake.create
        def create(**kw):
            resp = _orig(**kw)
            blob = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
            if PHASE_INSTRUCTIONS["report_regate"] in blob:
                resp.stop_reason = "max_tokens"
            return resp
        fake.create = create
        s, res, d = self._run(fake)
        self.assertFalse(d["report_gate"]["regenerated"])
        self.assertIn("| `keywords` | removed |", s.report_path.read_text())
        self.assertEqual(d["report_gate"]["findings_after"], 1)

    def test_a_prose_answer_restores_the_report_as_written(self):
        """#965: a reply that drops the table is not a report."""
        fake = _ReportFake("| `keywords` | removed | full | gone |\n", "unused")
        _orig = fake.create
        def create(**kw):
            blob = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
            if PHASE_INSTRUCTIONS["report_regate"] in blob:
                fake.calls.append(kw); return FakeResponse("You are right, keywords was not removed.\n")
            return _orig(**kw)
        fake.create = create
        s, res, d = self._run(fake)
        g = d["report_gate"]
        self.assertFalse(g["regenerated"])
        self.assertIn("worse", g["reason"])
        self.assertIn("| `keywords` | removed |", s.report_path.read_text())
        self.assertEqual(g["findings_after"], 1)

    def test_a_backfill_keeps_the_expectation(self):
        """#961: the flag lives on inputs, and a rebuilt block carries it again."""
        from data_sheets_schema import backfill_checks
        fake = _ReportFake("| `keywords` | retained | full | kept |\n", "unused")
        s, res, d = self._run(fake)
        self.assertTrue(d["inputs"]["dispositions_expected"])
        blocks = backfill_checks.compute(s.provenance_path, only={"report_claims"})
        self.assertTrue(blocks["report_claims"]["dispositions_expected"])
        # and never added to a record that lacks it
        rec = yaml.safe_load(s.provenance_path.read_text())
        rec["inputs"].pop("dispositions_expected"); rec["report_claims"].pop("dispositions_expected")
        s.provenance_path.write_text(yaml.safe_dump(rec))
        blocks = backfill_checks.compute(s.provenance_path, only={"report_claims"})
        self.assertNotIn("dispositions_expected", blocks["report_claims"])

    def test_the_companions_hash_is_of_the_log_as_it_ends(self):
        """#652: at record build the md5 was of a prefix of the reasoning log."""
        fake = _ReportFake("| `keywords` | removed | full | gone |\n", "| `keywords` | retained | full | kept |\n")
        s, res, d = self._run(fake)
        log = api_runner._reasoning_path(s)
        self.assertEqual(d["companions"]["reasoning_log"]["md5"], hashlib.md5(log.read_bytes()).hexdigest())


class TestTheAssemblyDigestCoversIt(unittest.TestCase):
    def test_the_instructions_exist_and_editing_either_moves_the_digest(self):
        self.assertIn("## Dispositions", PHASE_INSTRUCTIONS["report"])
        self.assertIn("report_regate", PHASE_INSTRUCTIONS)
        self.assertIn("#929", api_runner.ASSEMBLY_LAYOUT)
        before = api_runner.assembly_digest()["sha256"]
        for key in ("report", "report_regate"):
            with unittest.mock.patch.dict(PHASE_INSTRUCTIONS, {key: "changed"}):
                self.assertNotEqual(api_runner.assembly_digest()["sha256"], before)


if __name__ == "__main__":
    unittest.main()
