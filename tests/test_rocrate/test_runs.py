"""Tests for run tracking and replicate comparison."""

import tempfile
import unittest
from pathlib import Path

from data_sheets_schema.runs import (
    LEGACY_REVISION_RE, REPLICATE_RE, ReplicateMismatch, check_replicate,
    compare, discover, procedure_fingerprint,
)

HEADER = """# D4D Datasheet for X Dataset
# Generation Method: {method}
# Model: {model}
# Mode: four-phase project agent
id: x
name: X
"""


class TestLabelParsing(unittest.TestCase):
    def test_rep_marker_parses(self):
        m = REPLICATE_RE.match("2026-07-27_claude-opus-5_rep2")
        self.assertEqual(m.group("config"), "2026-07-27_claude-opus-5")
        self.assertEqual(m.group("replicate"), "2")

    def test_legacy_hyphen_is_a_revision_not_a_replicate(self):
        label = "2026-07-23_gpt-5.5-high-fast-r3"
        self.assertIsNone(REPLICATE_RE.match(label))
        self.assertEqual(LEGACY_REVISION_RE.match(label).group("revision"), "3")

    def test_underscore_r_is_no_longer_a_replicate_marker(self):
        """The old _r{N} form was one character from the revision form."""
        self.assertIsNone(REPLICATE_RE.match("2026-07-27_claude-opus-5_r1"))

    def test_bare_label_has_no_suffix(self):
        self.assertIsNone(REPLICATE_RE.match("2026-04-10_sonnet-4.6"))
        self.assertIsNone(LEGACY_REVISION_RE.match("2026-04-10_sonnet-4.6"))


class TestProcedureFingerprint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, method_dir, label, project, gen_method, model="opus-5",
             complete=True):
        """Create a run. Complete means full + core + report, as on disk."""
        d = self.root / method_dir / label
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{project}_d4d.yaml").write_text(
            HEADER.format(method=gen_method, model=model))
        if complete:
            base = method_dir[:-5] if method_dir.endswith("_core") else method_dir
            c = self.root / f"{base}_core" / label
            c.mkdir(parents=True, exist_ok=True)
            (c / f"{project}_d4d_core.yaml").write_text("id: x\n")
            (c / f"{project}_reconciliation.md").write_text("# report\n")
        return d

    def test_fingerprint_reads_procedure_fields(self):
        d = self._run("claudecode_agent", "L_r1", "P", "schema-grounded agentic")
        fp = procedure_fingerprint(d / "P_d4d.yaml")
        self.assertEqual(fp["Generation Method"], "schema-grounded agentic")
        self.assertEqual(fp["Model"], "opus-5")

    def test_identical_procedures_are_replicates(self):
        self._run("claudecode_agent", "L_r1", "P", "same")
        self._run("claudecode_agent", "L_r2", "P", "same")
        r = compare("claudecode_agent", "P", ["L_r1", "L_r2"], self.root)
        self.assertTrue(r["same_procedure"])

    def test_differing_procedures_are_flagged_not_replicates(self):
        """The gpt-5.5 -r2/-r3 case: same label family, different pipeline."""
        self._run("claudecode_agent", "L_r1", "P", "Claude Code Agent Deterministic")
        self._run("claudecode_agent", "L_r2", "P", "Codex CLI Agentic")
        r = compare("claudecode_agent", "P", ["L_r1", "L_r2"], self.root)
        self.assertFalse(r["same_procedure"])

    def test_compare_needs_two_runs(self):
        self._run("claudecode_agent", "L_r1", "P", "same")
        r = compare("claudecode_agent", "P", ["L_r1"], self.root)
        self.assertIn("error", r)

    def test_check_replicate_accepts_matching_procedure(self):
        self._run("claudecode_agent", "C_rep1", "P", "same proc")
        self._run("claudecode_agent", "C_rep2", "P", "same proc")
        r = check_replicate("claudecode_agent", "C", "C_rep2", "P", self.root)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["compared_to"], ["C_rep1"])

    def test_check_replicate_rejects_changed_procedure(self):
        """A changed pipeline is a revision; refuse to call it a replicate."""
        self._run("claudecode_agent", "C_rep1", "P", "Claude Code Agent")
        self._run("claudecode_agent", "C_rep2", "P", "Codex CLI Agentic")
        with self.assertRaises(ReplicateMismatch):
            check_replicate("claudecode_agent", "C", "C_rep2", "P", self.root)

    def test_check_replicate_rejects_changed_model(self):
        self._run("claudecode_agent", "C_rep1", "P", "same", model="opus-5")
        self._run("claudecode_agent", "C_rep2", "P", "same", model="sonnet-5")
        with self.assertRaises(ReplicateMismatch):
            check_replicate("claudecode_agent", "C", "C_rep2", "P", self.root)

    def test_omitted_optional_field_is_variance_not_mismatch(self):
        """rep1 wrote '# Reasoning effort: …'; rep2 omitted the line.

        Same model, runtime, mode and prompt — that is header wording, not a
        changed pipeline, and must not invalidate the replicate.
        """
        self._run("claudecode_agent", "C_rep1", "P", "same")
        d2 = self._run("claudecode_agent", "C_rep2", "P", "same")
        # rep2 omits the optional line entirely
        (d2 / "P_d4d.yaml").write_text(
            "# Generation Method: same\n# Model: opus-5\nid: x\n")
        (self.root / "claudecode_agent" / "C_rep1" / "P_d4d.yaml").write_text(
            "# Generation Method: same\n# Model: opus-5\n"
            "# Reasoning effort: high\nid: x\n")
        r = check_replicate("claudecode_agent", "C", "C_rep2", "P", self.root)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["header_variance"][0]["fields"], ["Reasoning effort"])

    def test_shared_field_with_different_value_still_fails(self):
        """The relaxation must not weaken the real check."""
        d1 = self._run("claudecode_agent", "D_rep1", "P", "same")
        (d1 / "P_d4d.yaml").write_text(
            "# Generation Method: same\n# Reasoning effort: high\nid: x\n")
        d2 = self._run("claudecode_agent", "D_rep2", "P", "same")
        (d2 / "P_d4d.yaml").write_text(
            "# Generation Method: same\n# Reasoning effort: low\nid: x\n")
        with self.assertRaises(ReplicateMismatch):
            check_replicate("claudecode_agent", "D", "D_rep2", "P", self.root)

    def test_placeholder_effort_values_do_not_break_replicates(self):
        """'default' vs 'not applicable' is invented wording, not a procedure."""
        d1 = self._run("claudecode_agent", "E_rep1", "P", "same")
        (d1 / "P_d4d.yaml").write_text(
            "# Generation Method: same\n# Reasoning effort: default\nid: x\n")
        d2 = self._run("claudecode_agent", "E_rep2", "P", "same")
        (d2 / "P_d4d.yaml").write_text(
            "# Generation Method: same\n# Reasoning effort: not applicable\nid: x\n")
        r = check_replicate("claudecode_agent", "E", "E_rep2", "P", self.root)
        self.assertEqual(r["status"], "ok")

    def test_real_effort_values_still_discriminate(self):
        """'high' vs 'low' is a genuine configuration difference."""
        d1 = self._run("claudecode_agent", "F_rep1", "P", "same")
        (d1 / "P_d4d.yaml").write_text(
            "# Generation Method: same\n# Reasoning effort: high\nid: x\n")
        d2 = self._run("claudecode_agent", "F_rep2", "P", "same")
        (d2 / "P_d4d.yaml").write_text(
            "# Generation Method: same\n# Reasoning effort: low\nid: x\n")
        with self.assertRaises(ReplicateMismatch):
            check_replicate("claudecode_agent", "F", "F_rep2", "P", self.root)

    def test_incomplete_run_is_excluded_from_comparison(self):
        """A full record without core+report is mid-flight, not a result."""
        from data_sheets_schema.runs import is_complete
        self._run("claudecode_agent", "G_rep1", "P", "same", complete=False)
        self.assertFalse(is_complete("claudecode_agent", "G_rep1", "P", self.root))
        c = self.root / "claudecode_agent_core" / "G_rep1"; c.mkdir(parents=True)
        (c / "P_d4d_core.yaml").write_text("id: x\n")
        self.assertFalse(is_complete("claudecode_agent", "G_rep1", "P", self.root))
        (c / "P_reconciliation.md").write_text("# report\n")
        self.assertTrue(is_complete("claudecode_agent", "G_rep1", "P", self.root))

    def test_different_input_bytes_reject_the_replicate(self):
        """Same prompt over a changed bundle is a condition, not a replicate."""
        import yaml as _y
        self._run("claudecode_agent", "H_rep1", "P", "same")
        self._run("claudecode_agent", "H_rep2", "P", "same")
        for lab, md5 in (("H_rep1", "aaa111"), ("H_rep2", "bbb222")):
            rec = self.root / "claudecode_agent_core" / lab / "P_provenance.yaml"
            rec.write_text(_y.safe_dump({"inputs": {"bundle_md5": md5}}))
        with self.assertRaises(ReplicateMismatch):
            check_replicate("claudecode_agent", "H", "H_rep2", "P", self.root)

    def test_identical_input_bytes_accept_the_replicate(self):
        import yaml as _y
        self._run("claudecode_agent", "I_rep1", "P", "same")
        self._run("claudecode_agent", "I_rep2", "P", "same")
        for lab in ("I_rep1", "I_rep2"):
            rec = self.root / "claudecode_agent_core" / lab / "P_provenance.yaml"
            rec.write_text(_y.safe_dump({"inputs": {"bundle_md5": "same999"}}))
        r = check_replicate("claudecode_agent", "I", "I_rep2", "P", self.root)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["input_md5"], "same999")
        self.assertIsNone(r["input_unverified_against"])

    def test_unknown_input_hash_is_reported_not_assumed_equal(self):
        """An absent hash must never be read as agreement."""
        self._run("claudecode_agent", "J_rep1", "P", "same")
        self._run("claudecode_agent", "J_rep2", "P", "same")
        r = check_replicate("claudecode_agent", "J", "J_rep2", "P", self.root)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["input_unverified_against"], ["J_rep1"])

    def test_discover_marks_deterministic_arms(self):
        self._run("rocrate_static_map", "2026-07-27_ourmap-v2", "P", "static map")
        runs = discover(self.root)
        self.assertTrue(runs[0].deterministic)
        self.assertIsNone(runs[0].replicate)


if __name__ == "__main__":
    unittest.main()


class TestValidityIsSeparateFromCompleteness(unittest.TestCase):
    """`is_complete()` answers a different question from "does this validate".

    Completeness is "did all three files get written". A record that fails
    LinkML validation is complete by that definition, so analysis paths would
    happily compare a valid record against a broken one — which measures the
    breakage rather than the arm.
    """

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _run(self, label, project="P", method="m", validation=None):
        import yaml as _yaml
        base = self.root / method / label
        core = self.root / f"{method}_core" / label
        base.mkdir(parents=True, exist_ok=True)
        core.mkdir(parents=True, exist_ok=True)
        (base / f"{project}_d4d.yaml").write_text("id: x\nname: X\n")
        (core / f"{project}_d4d_core.yaml").write_text("id: x\n")
        (core / f"{project}_reconciliation.md").write_text("# r\n")
        if validation is not None:
            (core / f"{project}_provenance.yaml").write_text(
                _yaml.safe_dump({"validation": validation}))

    def test_absent_provenance_is_unverified_not_valid(self):
        from data_sheets_schema.runs import UNVERIFIED, validation_status
        self._run("a")
        self.assertEqual(validation_status("m", "a", "P", self.root), UNVERIFIED)

    def test_provenance_without_a_validation_field_is_unverified(self):
        from data_sheets_schema.runs import UNVERIFIED, validation_status
        self._run("a", validation={})
        self.assertEqual(validation_status("m", "a", "P", self.root), UNVERIFIED)

    def test_recorded_pass_and_fail_are_read(self):
        from data_sheets_schema.runs import INVALID, VALID, validation_status
        self._run("good", validation={"passed": True})
        self._run("bad", validation={"passed": False})
        self.assertEqual(validation_status("m", "good", "P", self.root), VALID)
        self.assertEqual(validation_status("m", "bad", "P", self.root), INVALID)

    def test_an_invalid_record_is_still_complete(self):
        """The gap this closes: complete does not imply usable."""
        from data_sheets_schema.runs import INVALID, is_complete, validation_status
        self._run("bad", validation={"passed": False})
        self.assertTrue(is_complete("m", "bad", "P", self.root))
        self.assertEqual(validation_status("m", "bad", "P", self.root), INVALID)

    def test_compare_excludes_invalid_records(self):
        from data_sheets_schema.runs import compare
        self._run("a", validation={"passed": True})
        self._run("b", validation={"passed": True})
        self._run("c", validation={"passed": False})
        r = compare("m", "P", ["a", "b", "c"], self.root)
        self.assertEqual(r["excluded_invalid"], ["c"])
        self.assertNotIn("c", r["labels"])

    def test_compare_declares_unverified_input(self):
        """An agreement figure over unchecked records must say so."""
        from data_sheets_schema.runs import compare
        self._run("a")
        self._run("b")
        r = compare("m", "P", ["a", "b"], self.root)
        self.assertEqual(sorted(r["unverified"]), ["a", "b"])
        self.assertFalse(r["all_verified"])

    def test_compare_reports_all_verified_when_it_is(self):
        from data_sheets_schema.runs import compare
        self._run("a", validation={"passed": True})
        self._run("b", validation={"passed": True})
        self.assertTrue(compare("m", "P", ["a", "b"], self.root)["all_verified"])

    def test_compare_errors_name_the_invalid_exclusions(self):
        from data_sheets_schema.runs import compare
        self._run("a", validation={"passed": True})
        self._run("b", validation={"passed": False})
        r = compare("m", "P", ["a", "b"], self.root)
        self.assertIn("error", r)
        self.assertIn("invalid", r["error"])

    def test_exclude_invalid_can_be_disabled_deliberately(self):
        from data_sheets_schema.runs import compare
        self._run("a", validation={"passed": True})
        self._run("b", validation={"passed": False})
        r = compare("m", "P", ["a", "b"], self.root, exclude_invalid=False)
        self.assertIn("b", r["labels"])
        self.assertEqual(r["excluded_invalid"], ["b"])


class TestStaleVerdictsAreDetected(unittest.TestCase):
    """A verdict is a claim about specific bytes, not about a filename.

    Validity is recorded rather than recomputed, because validating inside an
    analysis hot path would cost seconds per record across a 100-record corpus.
    The price is that an edited record keeps its old verdict — unless the
    verdict is bound to the artifacts' hashes, which is what this checks.
    """

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.full = self.root / "m" / "L" / "P_d4d.yaml"
        self.core = self.root / "m_core" / "L" / "P_d4d_core.yaml"
        for p in (self.full, self.core):
            p.parent.mkdir(parents=True, exist_ok=True)
        self.full.write_text("id: x\nname: X\n")
        self.core.write_text("id: x\n")
        (self.core.parent / "P_reconciliation.md").write_text("# r\n")

    def _record(self, passed=True, with_hashes=True):
        import hashlib
        import yaml as _yaml
        block = {"passed": passed}
        if with_hashes:
            block["artifacts"] = {
                name: {"path": str(p),
                       "md5": hashlib.md5(p.read_bytes()).hexdigest()}
                for name, p in (("full", self.full), ("core", self.core))}
        (self.core.parent / "P_provenance.yaml").write_text(
            _yaml.safe_dump({"validation": block}))

    def test_unedited_record_stays_valid(self):
        from data_sheets_schema.runs import VALID, validation_status
        self._record()
        self.assertEqual(validation_status("m", "L", "P", self.root), VALID)

    def test_editing_the_full_record_makes_the_verdict_stale(self):
        from data_sheets_schema.runs import STALE, validation_status
        self._record()
        self.full.write_text("id: x\nname: EDITED\n")
        self.assertEqual(validation_status("m", "L", "P", self.root), STALE)

    def test_editing_the_core_record_makes_the_verdict_stale(self):
        from data_sheets_schema.runs import STALE, validation_status
        self._record()
        self.core.write_text("id: y\n")
        self.assertEqual(validation_status("m", "L", "P", self.root), STALE)

    def test_stale_beats_a_recorded_pass(self):
        """A `passed: true` about bytes that changed is not a pass."""
        from data_sheets_schema.runs import STALE, validation_status
        self._record(passed=True)
        self.full.write_text("something else entirely\n")
        self.assertNotEqual(validation_status("m", "L", "P", self.root), "valid")
        self.assertEqual(validation_status("m", "L", "P", self.root), STALE)

    def test_a_verdict_without_hashes_cannot_be_checked(self):
        """Older records carry no hashes; they are read at face value.

        Documented rather than silently tolerated: staleness detection only
        applies to verdicts written with artifact hashes.
        """
        from data_sheets_schema.runs import VALID, validation_status
        self._record(with_hashes=False)
        self.full.write_text("edited but undetectable\n")
        self.assertEqual(validation_status("m", "L", "P", self.root), VALID)

    def test_compare_reports_stale_runs_as_unverified(self):
        from data_sheets_schema.runs import compare
        self._record()
        # a second, untouched run to compare against
        f2 = self.root / "m" / "L2" / "P_d4d.yaml"
        c2 = self.root / "m_core" / "L2" / "P_d4d_core.yaml"
        for p in (f2, c2):
            p.parent.mkdir(parents=True, exist_ok=True)
        f2.write_text("id: x\nname: X\n")
        c2.write_text("id: x\n")
        (c2.parent / "P_reconciliation.md").write_text("# r\n")
        self.full.write_text("id: x\nname: EDITED\n")     # make L stale
        r = compare("m", "P", ["L", "L2"], self.root)
        self.assertFalse(r["all_verified"])
        self.assertTrue(any("stale" in u for u in r["unverified"]))


class TestProvenanceModeReportingAndArchive(unittest.TestCase):
    """Excluding reconstructed runs is a real loss, so it is opt-in and reported."""

    def test_compare_reports_reconstructed_without_being_asked(self):
        """A permissive result must never look uniform."""
        from data_sheets_schema.runs import compare
        r = compare("claudecode_agent", "CM4AI",
                    [f"2026-07-27_claude-opus-5_rep{n}" for n in (1, 2, 3)])
        if "error" in r:
            self.skipTest("tuned arm not present")
        self.assertIn("provenance_modes", r)
        self.assertFalse(r["all_live"])
        self.assertEqual(len(r["reconstructed"]), 3)
        self.assertEqual(r["excluded_not_live"], [],
                         "nothing excluded unless require_live is set")

    def test_require_live_excludes_them(self):
        from data_sheets_schema.runs import compare
        r = compare("claudecode_agent", "CM4AI",
                    [f"2026-07-27_claude-opus-5_rep{n}" for n in (1, 2, 3)],
                    require_live=True)
        self.assertIn("error", r, "the whole tuned arm is reconstructed")

    def test_archive_moves_full_and_core_together(self):
        """Splitting a run's full record from its core leaves it permanently
        incomplete, since is_complete() requires both plus the report."""
        from data_sheets_schema.runs import archive_runs
        r = archive_runs(["2026-07-27_claude-opus-5_rep1"], reason="t",
                         dry_run=True)
        dirs = {Path(a).parent.name for a, _ in r["moved"]}
        self.assertIn("claudecode_agent", dirs)
        self.assertIn("claudecode_agent_core", dirs)

    def test_archive_preserves_layout_so_restore_is_the_inverse(self):
        from data_sheets_schema.runs import archive_runs
        r = archive_runs(["2026-07-27_claude-opus-5_rep1"], reason="t",
                         dry_run=True)
        for src, dest in r["moved"]:
            self.assertTrue(dest.endswith(
                f"{Path(src).parent.name}/{Path(src).name}"))

    def test_dry_run_moves_nothing(self):
        from data_sheets_schema.runs import archive_runs
        before = sorted(Path("data/d4d_concatenated").rglob("*_d4d.yaml"))
        archive_runs(["2026-07-27_claude-opus-5_rep1"], reason="t", dry_run=True)
        self.assertEqual(before,
                         sorted(Path("data/d4d_concatenated").rglob("*_d4d.yaml")))

    def test_archive_roundtrips(self):
        import tempfile
        from data_sheets_schema.runs import archive_runs, restore_runs
        with tempfile.TemporaryDirectory() as td:
            concat, attic = Path(td) / "concat", Path(td) / "attic"
            run = concat / "m" / "L"
            run.mkdir(parents=True)
            (run / "P_d4d.yaml").write_text("id: x\n")
            archive_runs(["L"], reason="t", concat_dir=concat, attic=attic,
                         dry_run=False)
            self.assertFalse(run.exists())
            self.assertTrue((attic / "d4d_concatenated_archived" /
                             "README.md").exists())
            restore_runs(["L"], concat_dir=concat, attic=attic, dry_run=False)
            self.assertTrue((run / "P_d4d.yaml").exists())
