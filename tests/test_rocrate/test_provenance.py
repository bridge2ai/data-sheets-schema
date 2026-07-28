"""Tests for D4D generation provenance records."""

import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.provenance import (
    RECORD_VERSION, build_record, parse_header, record_path_for,
    schema_facts, system_facts,
)

HEADER = """# D4D Datasheet for P Dataset
# Generation Method: schema-grounded agentic, phase 1
# Agent runtime: Claude Code
# Provider: Anthropic
# Model: claude-opus-5[1m]
# Mode: four-phase project agent
# Temperature: 0.0
# Source bundle: data/preprocessed/concatenated/P_preprocessed.txt
id: x
name: X
"""

BARE = "# D4D Datasheet for P Dataset\n# Generation Method: legacy\nid: x\n"


class TestProvenance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, label, header=HEADER, project="P"):
        d = self.root / "claudecode_agent" / label
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{project}_d4d.yaml").write_text(header)
        c = self.root / "claudecode_agent_core" / label
        c.mkdir(parents=True, exist_ok=True)
        (c / f"{project}_d4d_core.yaml").write_text("id: x\n")
        (c / f"{project}_reconciliation.md").write_text("# r\n")

    def test_header_parsing_extracts_model_identity(self):
        self._run("L_rep1")
        h = parse_header(self.root / "claudecode_agent" / "L_rep1" / "P_d4d.yaml")
        self.assertEqual(h["Model"], "claude-opus-5[1m]")
        self.assertEqual(h["Provider"], "Anthropic")

    def test_reconstructed_withholds_input_hash_by_default(self):
        """Hashing a since-regenerated bundle would be a false claim."""
        self._run("L_rep1")
        rec = build_record("P", "claudecode_agent", "L_rep1",
                           mode="reconstructed", concat_dir=self.root)
        self.assertIsNone(rec.data["inputs"]["bundle_md5"])
        fields = {u["field"] for u in rec.data["unrecoverable"]}
        self.assertIn("inputs.bundle_md5", fields)

    def test_verified_input_records_the_hash(self):
        self._run("L_rep1")
        bundle = self.root / "bundle.txt"
        bundle.write_text("payload")
        rec = build_record("P", "claudecode_agent", "L_rep1",
                           mode="reconstructed", input_bundle=bundle,
                           input_verified=True, concat_dir=self.root)
        self.assertIsNotNone(rec.data["inputs"]["bundle_md5"])
        self.assertIn("verified", rec.data["inputs"]["hash_basis"])

    def test_reconstructed_does_not_claim_current_hardware(self):
        self._run("L_rep1")
        rec = build_record("P", "claudecode_agent", "L_rep1",
                           mode="reconstructed", concat_dir=self.root)
        self.assertIn("note", rec.data["system"])
        self.assertIn("system", {u["field"] for u in rec.data["unrecoverable"]})

    def test_live_record_captures_hardware_and_software(self):
        self._run("L_rep1")
        bundle = self.root / "bundle.txt"
        bundle.write_text("payload")
        rec = build_record("P", "claudecode_agent", "L_rep1", mode="live",
                           input_bundle=bundle, input_verified=True,
                           concat_dir=self.root)
        self.assertIn("platform", rec.data["system"])
        self.assertIn("linkml", rec.data["software"])
        self.assertIsNone(rec.data["unrecoverable"])

    def test_live_mode_refuses_an_unreadable_input(self):
        """A live run knows its input; failing to hash it is a capture defect."""
        self._run("L_rep1")
        with self.assertRaises(FileNotFoundError):
            build_record("P", "claudecode_agent", "L_rep1", mode="live",
                         input_verified=True, concat_dir=self.root)

    def test_missing_model_is_flagged_not_guessed(self):
        self._run("L_rep1", header=BARE)
        rec = build_record("P", "claudecode_agent", "L_rep1",
                           mode="reconstructed", concat_dir=self.root)
        self.assertIn("model.model", {u["field"] for u in rec.data["unrecoverable"]})

    def test_schema_version_is_declared_and_recorded(self):
        from data_sheets_schema.provenance import declared_schema_version
        self.assertIsNotNone(declared_schema_version())
        f = schema_facts()
        self.assertEqual(f["declared_version"], declared_schema_version())
        self.assertTrue(f["full_md5"])
        self.assertIn("data_sheets_schema.yaml", f["declared_in"])

    def test_record_flags_when_merged_schema_lacks_the_version(self):
        """The merged artefacts are generated; they lag the source until rebuilt."""
        f = schema_facts()
        if not f["merged_schema_carries_version"]:
            self.assertIn("merged artefacts predate it", f["note"])

    def test_record_round_trips_as_yaml(self):
        self._run("L_rep1")
        rec = build_record("P", "claudecode_agent", "L_rep1",
                           mode="reconstructed", concat_dir=self.root)
        out = rec.write(self.root / "prov.yaml")
        loaded = yaml.safe_load(out.read_text())
        self.assertEqual(loaded["record_version"], RECORD_VERSION)
        self.assertEqual(loaded["record_mode"], "reconstructed")
        self.assertEqual(loaded["run"]["replicate"], 1)

    def test_record_path_lands_beside_the_core_outputs(self):
        p = record_path_for("P", "claudecode_agent", "L_rep1", self.root)
        self.assertTrue(str(p).endswith(
            "claudecode_agent_core/L_rep1/P_provenance.yaml"))

    def test_system_facts_report_cpu_and_memory(self):
        f = system_facts()
        self.assertIsNotNone(f["cpu_count"])
        self.assertIn("platform", f)


if __name__ == "__main__":
    unittest.main()
