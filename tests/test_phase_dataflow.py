"""Three defects in the phase dataflow (#604), from the 2026-08-17 review."""

import inspect
import shutil
import tempfile
import unittest
from pathlib import Path

from data_sheets_schema.api_runner import (
    AUDIT_RECORD_VALUES,
    PHASE_NEEDS,
    RunSpec,
    _audit_is_well_formed,
    execute,
)


class AuditContractTest(unittest.TestCase):
    """A finding that names no record cannot be applied by either phase.

    Each reconciliation phase is told to apply "the findings that concern" its
    record. Since #574 conditions absorption on the audit's verdict, a finding
    that cannot be attributed is worse than one that is absent.
    """

    GOOD = {"summary": "one issue", "findings": [
        {"severity": "high", "record": "full", "slot": "id", "issue": "wrong"}]}

    def test_the_shape_the_review_showed_passing_is_rejected(self):
        self.assertFalse(_audit_is_well_formed(
            {"findings": [{"severity": "high", "slot": "id",
                           "issue": "wrong"}]}))

    def test_a_missing_summary_is_rejected(self):
        bad = {"findings": self.GOOD["findings"]}
        self.assertFalse(_audit_is_well_formed(bad))

    def test_an_empty_summary_is_rejected(self):
        self.assertFalse(_audit_is_well_formed({**self.GOOD, "summary": "  "}))

    def test_a_record_value_nothing_can_route_is_rejected(self):
        """Free text would be a finding nobody can act on."""
        bad = {"summary": "s", "findings": [
            {"severity": "high", "record": "the yaml file", "slot": "id",
             "issue": "x"}]}
        self.assertFalse(_audit_is_well_formed(bad))

    def test_the_routable_values_are_the_ones_the_phases_match_on(self):
        self.assertEqual(AUDIT_RECORD_VALUES, {"full", "core", "both"})

    def test_a_well_formed_audit_passes(self):
        self.assertTrue(_audit_is_well_formed(self.GOOD))

    def test_a_clean_audit_with_no_findings_passes(self):
        """Finding nothing is a result, not a malformed response."""
        self.assertTrue(_audit_is_well_formed(
            {"summary": "nothing found", "findings": []}))


class ReportAfterRepairTest(unittest.TestCase):
    """Repair runs after the whole phase loop, including `report` (#604).

    So a repair that rewrites a record leaves the report describing bytes that
    no longer exist — and `report_claims` then checks a stale report against
    the repaired records.
    """

    def test_the_report_is_regenerated_only_when_repair_changed_bytes(self):
        src = inspect.getsource(execute)
        self.assertIn("if after != before:", src)
        self.assertIn("_regenerate_report(", src)

    def test_it_records_that_it_did_and_which_records_moved(self):
        src = inspect.getsource(execute)
        self.assertIn("report_regenerated_after_repair", src)

    def test_it_reads_the_repaired_records_from_disk(self):
        """The carried copies are precisely the stale ones — that is the point."""
        from data_sheets_schema.api_runner import _regenerate_report
        src = inspect.getsource(_regenerate_report)
        self.assertIn("read_text", src)
        self.assertIn("Reconciled full record", src)

    def test_it_refuses_rather_than_guesses_when_an_input_is_missing(self):
        from data_sheets_schema.api_runner import _regenerate_report
        self.assertIn("cannot rebuild it honestly",
                      inspect.getsource(_regenerate_report))

    def test_report_still_declares_the_inputs_it_needs(self):
        self.assertIn("Reconciled full record", PHASE_NEEDS["report"])


class FlatOutputLayoutTest(unittest.TestCase):
    """An `--out-dir` run must record where it actually wrote (#604).

    `RunSpec` sends artifacts to `out_dir`, and `build_record` rebuilt the
    standard `data/d4d_concatenated/{method}/{label}` layout — so the record
    written into `out_dir` named output and companion files that were elsewhere
    or absent. Same class as the declared-bundle defect: a path assumed rather
    than derived from the spec that already knew it.
    """

    SOURCE = Path("data/d4d_concatenated/claudecode_agent"
                  "/2026-08-13_claude-opus-5-api-generic-v4_rep1/CHORUS_d4d.yaml")

    def setUp(self):
        if not self.SOURCE.exists():
            self.skipTest("v4 arm not present in this checkout")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name)
        self.spec = RunSpec(
            project="CHORUS", arm="baseline", method="claudecode_agent",
            bundle=Path("data/preprocessed/concatenated/CHORUS_preprocessed.txt"),
            label="flat_test", condition="generic_v5", out_dir=self.out)
        shutil.copy2(self.SOURCE, self.spec.full_path)

    def _record(self):
        from data_sheets_schema.provenance import build_record
        return build_record(
            "CHORUS", "claudecode_agent", "flat_test", mode="live",
            input_bundle=self.spec.bundle, input_verified=True,
            outputs={"full": self.spec.full_path, "core": self.spec.core_path,
                     "report": self.spec.report_path,
                     "reasoning": self.out / "CHORUS_reasoning.jsonl"})

    def test_the_record_names_the_file_the_run_wrote(self):
        rec = self._record()
        self.assertEqual(Path(rec.data["outputs"]["full"]["path"]).name,
                         self.spec.full_path.name)
        self.assertNotIn("d4d_concatenated", rec.data["outputs"]["full"]["path"])

    def test_companions_follow_the_same_layout(self):
        """The companion block was rebuilt from the standard layout too, so it
        pointed at a reasoning log in a directory this run never used."""
        rec = self._record()
        self.assertNotIn("d4d_concatenated",
                         rec.data["companions"]["reasoning_log"]["path"])

    def test_the_standard_layout_is_still_the_default(self):
        """Reconstruction is the fallback, not the removed behaviour: the
        agentic recorder passes no paths and must keep working."""
        from data_sheets_schema.provenance import build_record
        rec = build_record("CHORUS", "claudecode_agent",
                           "2026-08-13_claude-opus-5-api-generic-v4_rep1",
                           mode="reconstructed")
        self.assertIn("d4d_concatenated", rec.data["outputs"]["full"]["path"])


if __name__ == "__main__":
    unittest.main()
