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

    def test_require_live_is_too_strict_for_the_tuned_arm(self):
        """Documents why `live` is the wrong gate.

        The tuned arm pins its bundle by verified md5, its schema, its model and
        every output hash. `require_live` drops all 24 records anyway, over a
        hardware field that cannot affect a generation.
        """
        from data_sheets_schema.runs import compare
        r = compare("claudecode_agent", "CM4AI",
                    [f"2026-07-27_claude-opus-5_rep{n}" for n in (1, 2, 3)],
                    require_live=True)
        self.assertIn("error", r)

    def test_require_attested_keeps_the_tuned_arm(self):
        from data_sheets_schema.runs import compare
        r = compare("claudecode_agent", "CM4AI",
                    [f"2026-07-27_claude-opus-5_rep{n}" for n in (1, 2, 3)],
                    require_attested=True)
        if "error" in r:
            self.skipTest("tuned arm not present")
        self.assertEqual(len(r["labels"]), 3)
        self.assertTrue(r["all_attested"])
        self.assertFalse(r["all_live"], "attested without being live")

    def test_attestation_levels(self):
        from data_sheets_schema.runs import (
            ATTESTED, LIVE, NO_RECORD, PARTIAL, attestation)
        self.assertEqual(
            attestation("claudecode_agent",
                        "2026-07-28_claude-opus-5-generic_rep1", "CM4AI"), LIVE)
        self.assertEqual(
            attestation("claudecode_agent",
                        "2026-07-27_claude-opus-5_rep1", "CM4AI"), ATTESTED)
        self.assertEqual(
            attestation("claudecode_agent", "no-such-label", "CM4AI"), NO_RECORD)

    def test_unverified_input_hash_is_not_attested(self):
        """A bundle md5 computed today says nothing about the bytes consumed."""
        import tempfile, yaml as _yaml
        from data_sheets_schema.runs import PARTIAL, attestation
        with tempfile.TemporaryDirectory() as td:
            concat = Path(td)
            d = concat / "m_core" / "L"
            d.mkdir(parents=True)
            (d / "P_provenance.yaml").write_text(_yaml.safe_dump({
                "record_mode": "reconstructed",
                "inputs": {"bundle_md5": "abc"},      # no verified hash_basis
                "schema": {"full_md5": "d"},
                "model": {"model": "m"},
                "outputs": {"full": {}}}))
            self.assertEqual(attestation("m", "L", "P", concat), PARTIAL)

    def test_archive_targets_partial_not_merely_reconstructed(self):
        """Archiving on record_mode would remove 24 placeable tuned-arm records."""
        from data_sheets_schema.runs import ATTESTED, attestation, discover
        labels = {r.label for r in discover() if not r.is_core
                  and not r.deterministic
                  for p in r.projects
                  if attestation(r.method, r.label, p) == ATTESTED}
        self.assertIn("2026-07-27_claude-opus-5_rep1", labels)

    def test_archive_moves_full_and_core_together(self):
        """Splitting a run's full record from its core leaves it permanently
        incomplete, since is_complete() requires both plus the report."""
        from data_sheets_schema.runs import archive_runs
        # allow_partial_labels: this exercises the move mechanics, not the
        # policy. The label is fully attested, so the collateral guard would
        # (correctly) refuse it.
        r = archive_runs(["2026-07-27_claude-opus-5_rep1"], reason="t",
                         dry_run=True, allow_partial_labels=True)
        # Files now, not directories: the method is two levels up.
        methods = {Path(a).parent.parent.name for a, _ in r["moved"]}
        self.assertIn("claudecode_agent", methods)
        self.assertIn("claudecode_agent_core", methods)

    def test_archive_preserves_layout_so_restore_is_the_inverse(self):
        from data_sheets_schema.runs import archive_runs
        # allow_partial_labels: this exercises the move mechanics, not the
        # policy. The label is fully attested, so the collateral guard would
        # (correctly) refuse it.
        r = archive_runs(["2026-07-27_claude-opus-5_rep1"], reason="t",
                         dry_run=True, allow_partial_labels=True)
        for src, dest in r["moved"]:
            # Layout preserved: method/label/file mirrored under the archive.
            self.assertTrue(dest.endswith(
                f"{Path(src).parent.parent.name}/{Path(src).parent.name}/"
                f"{Path(src).name}"))

    def test_dry_run_moves_nothing(self):
        from data_sheets_schema.runs import archive_runs
        before = sorted(Path("data/d4d_concatenated").rglob("*_d4d.yaml"))
        archive_runs(["2026-07-27_claude-opus-5_rep1"], reason="t",
                     dry_run=True, allow_partial_labels=True)
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


class TestAttestationRigour(unittest.TestCase):
    """The checks must mean what they say (#184, #185, #186)."""

    def _record(self, tmp, **overrides):
        import yaml as _yaml
        data = {"record_mode": "reconstructed",
                "inputs": {"bundle_md5": "a",
                           "hash_basis": "verified identical to the bytes consumed"},
                "schema": {"full_md5": "s"},
                "model": {"model": "m"},
                "outputs": {"full": {"md5": "x"}}}
        data.update(overrides)
        d = tmp / "m_core" / "L"
        d.mkdir(parents=True, exist_ok=True)
        (d / "P_provenance.yaml").write_text(_yaml.safe_dump(data))
        return tmp

    def test_outputs_block_that_hashes_nothing_is_partial(self):
        """A truthy dict of empty artifacts pins nothing (#184)."""
        import tempfile
        from data_sheets_schema.runs import PARTIAL, attestation
        with tempfile.TemporaryDirectory() as td:
            c = self._record(Path(td), outputs={"full": None, "core": None})
            self.assertEqual(attestation("m", "L", "P", c), PARTIAL)

    def test_outputs_with_an_md5_is_attested(self):
        import tempfile
        from data_sheets_schema.runs import ATTESTED, attestation
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(
                attestation("m", "L", "P", self._record(Path(td))), ATTESTED)

    def test_unverified_hash_basis_is_not_verified(self):
        """`"verified" in "unverified"` is True — the substring test inverted
        the intent for the two phrasings most likely to be written (#185)."""
        import tempfile
        from data_sheets_schema.runs import PARTIAL, attestation
        for basis in ("unverified", "not verified against the run",
                      "unverified — file changed since"):
            with self.subTest(basis=basis), tempfile.TemporaryDirectory() as td:
                c = self._record(Path(td),
                                 inputs={"bundle_md5": "a", "hash_basis": basis})
                self.assertEqual(attestation("m", "L", "P", c), PARTIAL)

    def test_unrecognised_hash_basis_is_not_trusted(self):
        import tempfile
        from data_sheets_schema.runs import PARTIAL, attestation
        with tempfile.TemporaryDirectory() as td:
            c = self._record(Path(td),
                             inputs={"bundle_md5": "a",
                                     "hash_basis": "looked about right"})
            self.assertEqual(attestation("m", "L", "P", c), PARTIAL)

    def test_restore_refuses_to_nest_into_an_existing_label(self):
        """shutil.move puts the source *inside* an existing destination (#186)."""
        import tempfile
        from data_sheets_schema.runs import archive_runs, restore_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = Path(td) / "c", Path(td) / "a"
            run = c / "m" / "L"
            run.mkdir(parents=True)
            (run / "P_d4d.yaml").write_text("archived\n")
            archive_runs(["L"], reason="t", concat_dir=c, attic=a, dry_run=False)
            run.mkdir(parents=True)
            (run / "P_d4d.yaml").write_text("regenerated\n")
            with self.assertRaises(FileExistsError):
                restore_runs(["L"], concat_dir=c, attic=a, dry_run=False)
            self.assertFalse((run / "L").exists(), "nothing was nested")
            self.assertEqual((run / "P_d4d.yaml").read_text(), "regenerated\n")

    def test_archive_refuses_to_overwrite_an_existing_archive(self):
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = Path(td) / "c", Path(td) / "a"
            for _ in range(2):
                run = c / "m" / "L"
                run.mkdir(parents=True)
                (run / "P_d4d.yaml").write_text("x\n")
                if _ == 0:
                    archive_runs(["L"], reason="t", concat_dir=c, attic=a,
                                 dry_run=False)
            with self.assertRaises(FileExistsError):
                archive_runs(["L"], reason="t", concat_dir=c, attic=a,
                             dry_run=False)

    def test_dry_run_reports_collisions_without_raising(self):
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = Path(td) / "c", Path(td) / "a"
            run = c / "m" / "L"
            run.mkdir(parents=True)
            (run / "P_d4d.yaml").write_text("x\n")
            # Collisions are per-file now, so the fixture must pre-place a file.
            dest = a / "d4d_concatenated_archived" / "m" / "L"
            dest.mkdir(parents=True)
            (dest / "P_d4d.yaml").write_text("older\n")
            r = archive_runs(["L"], reason="t", concat_dir=c, attic=a,
                             dry_run=True)
            self.assertTrue(r["collisions"])


class TestArchiveDoesNotTakeCollateral(unittest.TestCase):
    """A label is not a unit of attestation.

    One run directory holds several projects and they can differ:
    2026-07-28_claude-opus-5-crateonly has CHORUS and VOICE live while CM4AI is
    partial. Archiving by label moves every project it holds, so an unguarded
    sweep would have moved six placeable records out with three unplaceable
    ones and reported success.
    """

    def _tree(self, td, attestations):
        """attestations: {project: 'live'|'partial'} for one label."""
        import yaml as _yaml
        concat = Path(td) / "concat"
        for proj, level in attestations.items():
            full = concat / "m" / "L"
            core = concat / "m_core" / "L"
            full.mkdir(parents=True, exist_ok=True)
            core.mkdir(parents=True, exist_ok=True)
            (full / f"{proj}_d4d.yaml").write_text("id: x\n")
            (core / f"{proj}_d4d_core.yaml").write_text("id: x\n")
            (core / f"{proj}_reconciliation.md").write_text("ok\n")
            rec = {"record_mode": "live" if level == "live" else "reconstructed",
                   "inputs": {"bundle_md5": "a",
                              "hash_basis": "verified identical to the bytes consumed"},
                   "schema": {"full_md5": "s"}, "model": {"model": "m"},
                   "outputs": {"full": {"md5": "x"}}}
            if level == "partial":
                rec["inputs"] = {"bundle_md5": "a", "hash_basis": "unverified"}
            (core / f"{proj}_provenance.yaml").write_text(_yaml.safe_dump(rec))
        return concat

    def test_a_mixed_label_is_refused(self):
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            concat = self._tree(td, {"KEEP": "live", "DROP": "partial"})
            with self.assertRaises(ValueError) as ctx:
                archive_runs(["L"], reason="t", concat_dir=concat,
                             attic=Path(td) / "attic", dry_run=True)
            self.assertIn("do not agree", str(ctx.exception))

    def test_a_uniformly_partial_label_is_archived(self):
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            concat = self._tree(td, {"A": "partial", "B": "partial"})
            r = archive_runs(["L"], reason="t", concat_dir=concat,
                             attic=Path(td) / "attic", dry_run=True)
            # Four files per project (full, core, report, provenance) x2.
            self.assertEqual(r["count"], 8)

    def test_collateral_can_be_accepted_explicitly(self):
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            concat = self._tree(td, {"KEEP": "live", "DROP": "partial"})
            r = archive_runs(["L"], reason="t", concat_dir=concat,
                             attic=Path(td) / "attic", dry_run=True,
                             allow_partial_labels=True)
            self.assertGreater(r["count"], 0)


class TestLiveProvenanceRequirement(unittest.TestCase):
    """Required for new runs, not applied retroactively."""

    def test_the_cutoff_is_read_from_the_label_date(self):
        from data_sheets_schema.runs import LIVE_REQUIRED_FROM, requires_live
        self.assertFalse(requires_live("2026-07-28_claude-opus-5-generic_rep1"))
        self.assertTrue(requires_live(f"{LIVE_REQUIRED_FROM}_anything_rep1"))
        self.assertTrue(requires_live("2027-01-01_later_rep1"))

    def test_an_undated_label_is_subject_to_the_rule(self):
        """Exempting anything unparseable is an exemption taken by accident."""
        from data_sheets_schema.runs import requires_live
        self.assertTrue(requires_live("no-date-here"))
        self.assertTrue(requires_live(""))

    def test_pre_cutoff_runs_pass_without_live_provenance(self):
        from data_sheets_schema.runs import check_provenance
        r = check_provenance("claudecode_agent",
                             "2026-07-27_claude-opus-5_rep1", "CM4AI")
        if r["record_mode"] == "none":
            self.skipTest("tuned arm not present")
        self.assertTrue(r["ok"])
        self.assertFalse(r["required"])

    def test_a_post_cutoff_run_without_provenance_fails(self):
        import tempfile
        from data_sheets_schema.runs import check_provenance
        with tempfile.TemporaryDirectory() as td:
            r = check_provenance("m", "2099-01-01_future_rep1", "P",
                                 Path(td))
            self.assertFalse(r["ok"])
            self.assertIn("no provenance record", r["reason"])


class TestAnExplicitRecordPathIsStillEvidence(unittest.TestCase):
    """Passing the record's path says where it is, not that it attests anything.

    The exemption these guard was added for a real reason — a record written
    moments ago has no validation block, because `d4d runs validate` adds one
    afterwards. But `execute()` writes its validation block *before* calling
    the gate, so the exemption bought nothing and cost the gate its purpose.
    """

    def _write(self, td, data):
        import yaml
        p = Path(td) / "prov.yaml"
        p.write_text(yaml.safe_dump(data) if isinstance(data, dict) else data)
        return p

    def test_a_record_with_no_artifacts_does_not_pass(self):
        import tempfile
        from data_sheets_schema.runs import check_provenance
        with tempfile.TemporaryDirectory() as td:
            rec = self._write(td, {
                "record_mode": "live",
                "run": {"method": "claudecode_agent", "label": "2026-07-31_x_rep1",
                        "project": "P"}})
            out = check_provenance("claudecode_agent", "2026-07-31_x_rep1", "P",
                                   record=rec)
            self.assertFalse(out["ok"])
            self.assertIn("nothing to verify", out["reason"])

    def test_a_bare_mode_line_does_not_pass(self):
        """The minimal case: one line asserting liveness and nothing else."""
        import tempfile
        from data_sheets_schema.runs import check_provenance
        with tempfile.TemporaryDirectory() as td:
            rec = self._write(td, "record_mode: live\n")
            self.assertFalse(
                check_provenance("m", "2026-07-31_x_rep1", "P", record=rec)["ok"])

    def test_a_record_for_another_run_does_not_pass(self):
        """Otherwise the hashes verify — against the other run's files."""
        import tempfile
        from data_sheets_schema.runs import check_provenance
        with tempfile.TemporaryDirectory() as td:
            rec = self._write(td, {
                "record_mode": "live",
                "run": {"method": "claudecode_agent",
                        "label": "2026-07-31_SOMEONE_ELSE_rep1", "project": "Z"},
                "validation": {"artifacts": {}}})
            out = check_provenance("claudecode_agent", "2026-07-31_mine_rep1",
                                   "P", record=rec)
            self.assertFalse(out["ok"])
            self.assertIn("different run", out["reason"])

    def test_a_record_that_names_no_run_does_not_pass(self):
        import tempfile
        from data_sheets_schema.runs import check_provenance
        with tempfile.TemporaryDirectory() as td:
            rec = self._write(td, {"record_mode": "live",
                                   "validation": {"artifacts": {}}})
            out = check_provenance("m", "2026-07-31_x_rep1", "P", record=rec)
            self.assertFalse(out["ok"])
            self.assertIn("does not identify", out["reason"])

    def test_an_unreadable_record_fails_rather_than_raising(self):
        """This gate runs *after* all six phases are billed.

        So a record truncated by a full disk or an interrupted write turned a
        completed, fully-paid run into a traceback — when the gate's whole job
        is to turn "cannot be attested" into a clean failure with a reason.
        """
        import tempfile
        from data_sheets_schema.runs import check_provenance
        for name, body in (("malformed", "record_mode: live\n  bad: [indent\n"),
                           ("not a mapping", "- a\n- b\n"),
                           ("a bare scalar", "just a string\n")):
            with self.subTest(record=name):
                with tempfile.TemporaryDirectory() as td:
                    rec = self._write(td, body)
                    out = check_provenance("m", "2026-07-31_x_rep1", "P",
                                           record=rec)
                    self.assertFalse(out["ok"])
                    self.assertIn("could not be read", out["reason"])

    def test_identity_mismatch_does_not_pollute_unverifiable(self):
        """`unverifiable` answers "which artifacts could not be checked".

        Run-identity field names in that list mean anything counting
        unverifiable artifacts silently counts field names too.
        """
        import tempfile
        from data_sheets_schema.runs import check_provenance
        with tempfile.TemporaryDirectory() as td:
            rec = self._write(td, {
                "record_mode": "live",
                "run": {"method": "OTHER", "label": "L2", "project": "P2"},
                "validation": {"artifacts": {}}})
            out = check_provenance("m", "2026-07-31_x_rep1", "P", record=rec)
            self.assertFalse(out["ok"])
            self.assertEqual(out["unverifiable"], [])
            self.assertEqual(out["identity_mismatch"],
                             ["label", "method", "project"])

    def test_a_matching_record_with_verifiable_artifacts_passes(self):
        """The gate must still admit the case it exists to admit."""
        import hashlib
        import tempfile
        from data_sheets_schema.runs import check_provenance
        with tempfile.TemporaryDirectory() as td:
            art = Path(td) / "P_d4d.yaml"
            art.write_text("id: x\n")
            rec = self._write(td, {
                "record_mode": "live",
                "run": {"method": "claudecode_agent",
                        "label": "2026-07-31_x_rep1", "project": "P"},
                "validation": {"artifacts": {"full": {
                    "path": str(art),
                    "sha256": hashlib.sha256(art.read_bytes()).hexdigest()}}}})
            out = check_provenance("claudecode_agent", "2026-07-31_x_rep1", "P",
                                   record=rec)
            self.assertTrue(out["ok"], out["reason"])


class TestImplausibleDatesAreNotExemptions(unittest.TestCase):
    """An exemption anyone can take by writing a wrong date is not a rule (#194)."""

    def test_a_pre_project_date_is_treated_as_malformed(self):
        from data_sheets_schema.runs import requires_live
        for label in ("0001-01-01_x", "1970-01-01_x", "2016-07-30_x"):
            with self.subTest(label=label):
                self.assertTrue(requires_live(label))

    def test_a_real_pre_cutoff_date_is_still_exempt(self):
        from data_sheets_schema.runs import requires_live
        self.assertFalse(requires_live("2026-07-28_claude-opus-5-generic_rep1"))
        self.assertFalse(requires_live("2026-04-10_sonnet-4.6"))

    def test_the_floor_sits_below_the_earliest_real_run(self):
        from data_sheets_schema.runs import (
            EARLIEST_PLAUSIBLE_RUN, LIVE_REQUIRED_FROM)
        self.assertLess(EARLIEST_PLAUSIBLE_RUN, LIVE_REQUIRED_FROM)
        self.assertLess(EARLIEST_PLAUSIBLE_RUN, "2026-04-10")


class TestProjectGranularArchive(unittest.TestCase):
    """A mixed label needs the project named, not the label skipped.

    Skipping mixed labels left CM4AI's crateonly records in the corpus because
    CHORUS and VOICE share their label — the guard prevented data loss but also
    prevented the archive from doing its job.
    """

    def _tree(self, td):
        c = Path(td) / "c"
        for proj in ("KEEP", "DROP"):
            (c / "m" / "L").mkdir(parents=True, exist_ok=True)
            (c / "m_core" / "L").mkdir(parents=True, exist_ok=True)
            (c / "m" / "L" / f"{proj}_d4d.yaml").write_text(f"{proj}\n")
            (c / "m_core" / "L" / f"{proj}_d4d_core.yaml").write_text(f"{proj}\n")
        return c, Path(td) / "a"

    def test_only_the_named_project_moves(self):
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = self._tree(td)
            archive_runs(["L"], reason="t", projects=["DROP"], concat_dir=c,
                         attic=a, dry_run=False)
            remaining = sorted(f.name for f in c.rglob("*") if f.is_file())
            self.assertEqual(remaining, ["KEEP_d4d.yaml", "KEEP_d4d_core.yaml"])

    def test_per_project_archive_round_trips(self):
        import tempfile
        from data_sheets_schema.runs import archive_runs, restore_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = self._tree(td)
            before = sorted(f.name for f in c.rglob("*") if f.is_file())
            archive_runs(["L"], reason="t", projects=["DROP"], concat_dir=c,
                         attic=a, dry_run=False)
            restore_runs(["L"], projects=["DROP"], concat_dir=c, attic=a,
                         dry_run=False)
            self.assertEqual(sorted(f.name for f in c.rglob("*") if f.is_file()),
                             before)

    def test_naming_a_project_needs_no_collateral_guard(self):
        """The guard exists for whole-label moves; naming projects is precise."""
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = self._tree(td)
            r = archive_runs(["L"], reason="t", projects=["DROP"],
                             concat_dir=c, attic=a, dry_run=True)
            self.assertEqual(r["count"], 2)

    def test_emptied_directories_are_pruned(self):
        """An empty label directory reads as a run with no records."""
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = self._tree(td)
            archive_runs(["L"], reason="t", projects=["KEEP", "DROP"],
                         concat_dir=c, attic=a, dry_run=False)
            self.assertFalse((c / "m" / "L").exists())


class TestDerivedIsItsOwnLevel(unittest.TestCase):
    """A derived record is not a defective generation record."""

    def _derived(self, td, **overrides):
        import yaml as _yaml
        d = Path(td) / "m_core" / "L"
        d.mkdir(parents=True, exist_ok=True)
        body = {"record_mode": "derived",
                "sources": [{"label": "r1", "md5": "abc"}],
                "derivation": {"rule": "union"},
                "outputs": {"full": {"md5": "x"}}}
        body.update(overrides)
        (d / "P_provenance.yaml").write_text(_yaml.safe_dump(body))
        return Path(td)

    def test_a_well_formed_derived_record_reports_derived(self):
        import tempfile
        from data_sheets_schema.runs import DERIVED, attestation
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(attestation("m", "L", "P", self._derived(td)),
                             DERIVED)

    def test_a_derived_record_without_sources_is_partial(self):
        import tempfile
        from data_sheets_schema.runs import PARTIAL, attestation
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(
                attestation("m", "L", "P", self._derived(td, sources=[])),
                PARTIAL)

    def test_a_derived_record_without_a_hashed_output_is_partial(self):
        import tempfile
        from data_sheets_schema.runs import PARTIAL, attestation
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(
                attestation("m", "L", "P",
                            self._derived(td, outputs={"full": None})),
                PARTIAL)

    def test_the_real_merged_records_report_derived(self):
        from data_sheets_schema.runs import DERIVED, attestation
        got = attestation("claudecode_agent_merged", "2026-07-29_guarded-union",
                          "CHORUS")
        if got == "none":
            self.skipTest("guarded merges not present")
        self.assertEqual(got, DERIVED)

    def test_compare_excludes_derived_records_unconditionally(self):
        """A derived record is an order statistic over the runs being measured,
        so including it would bias the variance it was built from."""
        from data_sheets_schema.runs import compare
        r = compare("claudecode_agent_merged", "CHORUS",
                    ["2026-07-29_guarded-union"])
        self.assertIn("error", r, "one label cannot form a comparison anyway")


class TestPruneScopeAndEmptySelection(unittest.TestCase):
    """An operation must not have effects outside what it was asked to do."""

    def _tree(self, td, projects=("P", "KEEP")):
        c, a = Path(td) / "c", Path(td) / "a"
        (c / "m" / "L").mkdir(parents=True)
        for proj in projects:
            (c / "m" / "L" / f"{proj}_d4d.yaml").write_text(f"{proj}\n")
        return c, a

    def test_unrelated_empty_directories_survive(self):
        """Pruning the corpus root deleted directories the move never touched,
        so the result depended on what else happened to be empty (#196)."""
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = self._tree(td)
            (c / "other_method" / "pending_run").mkdir(parents=True)
            archive_runs(["L"], reason="t", projects=["P"], concat_dir=c,
                         attic=a, dry_run=False)
            self.assertTrue((c / "other_method" / "pending_run").exists())

    def test_a_shared_label_directory_is_kept(self):
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = self._tree(td)
            r = archive_runs(["L"], reason="t", projects=["P"], concat_dir=c,
                             attic=a, dry_run=False)
            self.assertEqual(r["would_empty"], [])
            self.assertTrue((c / "m" / "L").exists())

    def test_a_fully_emptied_label_directory_is_removed(self):
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = self._tree(td, projects=("P",))
            r = archive_runs(["L"], reason="t", projects=["P"], concat_dir=c,
                             attic=a, dry_run=False)
            self.assertTrue(r["would_empty"])
            self.assertFalse((c / "m" / "L").exists())

    def test_dry_run_previews_the_directories_too(self):
        """A preview that omits part of the effect is weaker than it looks (#198)."""
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = self._tree(td, projects=("P",))
            r = archive_runs(["L"], reason="t", projects=["P"], concat_dir=c,
                             attic=a, dry_run=True)
            self.assertTrue(r["would_empty"])
            self.assertTrue((c / "m" / "L").exists(), "dry run changed nothing")

    def test_an_empty_selection_writes_no_note(self):
        """A mistyped project archived nothing and left a note claiming
        otherwise (#197)."""
        import tempfile
        from data_sheets_schema.runs import archive_runs
        with tempfile.TemporaryDirectory() as td:
            c, a = self._tree(td)
            r = archive_runs(["L"], reason="t", projects=["MISTYPED"],
                             concat_dir=c, attic=a, dry_run=False)
            self.assertTrue(r["matched_nothing"])
            self.assertEqual(r["count"], 0)
            self.assertFalse((a / "d4d_concatenated_archived").exists())

    def test_restore_also_reports_an_empty_selection(self):
        import tempfile
        from data_sheets_schema.runs import restore_runs
        with tempfile.TemporaryDirectory() as td:
            r = restore_runs(["nope"], concat_dir=Path(td) / "c",
                             attic=Path(td) / "a", dry_run=True)
            self.assertTrue(r["matched_nothing"])
