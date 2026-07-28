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
