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
        self.assertTrue(f["full_sha256"])
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


class TestSharedConfigConvergence(unittest.TestCase):
    """The API path and the GitHub assistant must not drift into two procedures.

    Both read model settings from the assistant's deterministic config. If they
    disagree, the record says so rather than presenting the run as conforming.
    """

    def test_shared_config_is_readable(self):
        from data_sheets_schema.provenance import load_generation_config
        cfg = load_generation_config()
        self.assertIn("model", cfg, "assistant deterministic config not loadable")
        self.assertIsNotNone(cfg["model"].get("name"))

    def test_missing_config_degrades_quietly(self):
        from pathlib import Path
        from data_sheets_schema.provenance import load_generation_config
        self.assertEqual(load_generation_config(Path("/nonexistent/x.config")), {})

    def test_prompt_files_are_hashed(self):
        from pathlib import Path
        from data_sheets_schema.provenance import prompt_facts
        p = Path("src/download/prompts/d4d_generic_arm_prompt.md")
        facts = prompt_facts([p])
        self.assertEqual(facts["hash_algorithm"], "sha256")
        self.assertTrue(facts["files"][0]["exists"])
        self.assertEqual(len(facts["files"][0]["sha256"]), 64)

    def test_absent_prompt_declaration_is_stated_not_implied(self):
        """A run with no declared prompt must say so — silence reads as 'none'."""
        from data_sheets_schema.provenance import prompt_facts
        facts = prompt_facts(None)
        self.assertIsNone(facts["paths"])
        self.assertIn("not recoverable", facts["note"])


class TestCuratedIsNotAReference(unittest.TestCase):
    """`curated` was asserted to be a manual gold standard. It is not.

    These records came from a ChatGPT chat session. The claim mattered because
    REFERENCE_METHODS is read programmatically — scoring or validation work
    would have treated a generation arm as ground truth.
    """

    def test_reference_methods_is_empty(self):
        from data_sheets_schema.constants import REFERENCE_METHODS
        self.assertEqual(REFERENCE_METHODS, [],
                         "nothing in this repo has earned a reference tier")

    def test_curated_is_not_claimed_as_a_reference(self):
        from data_sheets_schema.constants import REFERENCE_METHODS
        self.assertNotIn("curated", REFERENCE_METHODS)

    def test_curated_remains_a_known_method(self):
        """It is still a comparison arm; only its status changed."""
        from data_sheets_schema.constants import METHODS
        self.assertIn("curated", METHODS)

    def test_provenance_note_records_what_it_actually_is(self):
        from data_sheets_schema.constants.methods import CURATED_PROVENANCE_NOTE
        low = CURATED_PROVENANCE_NOTE.lower()
        self.assertIn("chatgpt", low)
        self.assertIn("not hand-curated", low)
        self.assertIn("superseded", low)

    def test_every_curated_record_has_a_provenance_file(self):
        from pathlib import Path
        import yaml as _yaml
        d = Path("data/d4d_concatenated/curated")
        if not d.exists():
            self.skipTest("curated records not present")
        for f in d.glob("*_curated.yaml"):
            prov = f.parent / f"{f.name.split('_curated')[0]}_curated_provenance.yaml"
            self.assertTrue(prov.exists(), f"no provenance for {f.name}")
            rec = _yaml.safe_load(prov.read_text())
            self.assertEqual(rec["record_mode"], "reconstructed")
            self.assertEqual(rec["model"]["provider"], "OpenAI")
            # the things that cannot be known must be named, not guessed
            fields = {u["field"] for u in rec["unrecoverable"]}
            self.assertIn("model.model", fields)
            self.assertIn("prompts", fields)
            self.assertIsNone(rec["model"]["model"])


class TestHashUnification(unittest.TestCase):
    """One algorithm for new records, both readable for old ones (#168).

    The format used sha256 for prompts and md5 for inputs, artifacts and
    schemas. Switching the writer alone would have been a silent corpus-wide
    regression: 82 of 89 records carried md5-bound validation verdicts and
    `validation_status` re-hashes to detect staleness, so every one would have
    reported STALE.
    """

    def test_new_artifacts_are_hashed_with_sha256(self):
        import tempfile
        from data_sheets_schema.provenance import _artifact
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "x.yaml"
            f.write_text("id: x\n")
            art = _artifact(f)
            self.assertIn("sha256", art)
            self.assertNotIn("md5", art)

    def test_a_reader_accepts_either_algorithm(self):
        from data_sheets_schema.provenance import recorded_hash
        self.assertEqual(recorded_hash({"sha256": "a"}), ("sha256", "a"))
        self.assertEqual(recorded_hash({"md5": "b"}), ("md5", "b"))
        self.assertEqual(recorded_hash({"sha256": "a", "md5": "b"}),
                         ("sha256", "a"), "sha256 preferred when both present")
        self.assertIsNone(recorded_hash({"path": "p"}))

    def test_verification_uses_the_algorithm_the_record_carries(self):
        import hashlib
        import tempfile
        from data_sheets_schema.provenance import verify_entry
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "x.txt"
            f.write_bytes(b"content")
            md5 = hashlib.md5(b"content").hexdigest()
            sha = hashlib.sha256(b"content").hexdigest()
            self.assertTrue(verify_entry({"path": str(f), "md5": md5}))
            self.assertTrue(verify_entry({"path": str(f), "sha256": sha}))
            self.assertFalse(verify_entry({"path": str(f), "md5": "wrong"}))
            self.assertIsNone(verify_entry({"path": str(f)}),
                              "no hash recorded is unknowable, not false")

    def test_migration_refuses_to_rehash_a_stale_entry(self):
        """Re-hashing without verifying would launder a stale verdict.

        The record would gain a correct sha256 for content that no longer
        matches the verdict attached to it, erasing exactly the staleness
        `validation_status` exists to surface.
        """
        import tempfile
        import yaml as _yaml
        from data_sheets_schema.provenance import migrate_record_hashes
        with tempfile.TemporaryDirectory() as td:
            art = Path(td) / "a.yaml"
            art.write_text("changed since the hash was taken\n")
            rec = Path(td) / "P_provenance.yaml"
            rec.write_text(_yaml.safe_dump({
                "outputs": {"full": {"path": str(art), "md5": "staleandwrong"}}}))
            r = migrate_record_hashes(rec, dry_run=True)
            self.assertEqual(r["migrated"], [])
            self.assertEqual(len(r["skipped"]), 1)
            self.assertIn("no longer matches", r["skipped"][0]["why"])

    def test_migration_rewrites_a_verified_entry(self):
        import hashlib
        import tempfile
        import yaml as _yaml
        from data_sheets_schema.provenance import migrate_record_hashes
        with tempfile.TemporaryDirectory() as td:
            art = Path(td) / "a.yaml"
            art.write_bytes(b"stable")
            rec = Path(td) / "P_provenance.yaml"
            rec.write_text(_yaml.safe_dump({"outputs": {"full": {
                "path": str(art), "md5": hashlib.md5(b"stable").hexdigest()}}}))
            migrate_record_hashes(rec, dry_run=False)
            out = _yaml.safe_load(rec.read_text())["outputs"]["full"]
            self.assertEqual(out["sha256"], hashlib.sha256(b"stable").hexdigest())
            self.assertNotIn("md5", out)

    def test_the_corpus_carries_no_stale_verdicts_after_migration(self):
        from data_sheets_schema.runs import STALE, discover, validation_status
        stale = [(r.method, r.label, p) for r in discover()
                 if not r.is_core and not r.deterministic
                 for p in r.projects
                 if validation_status(r.method, r.label, p) == STALE]
        self.assertEqual(stale, [], f"migration introduced staleness: {stale}")


class TestMd5IsDeprecatedInTheSchema(unittest.TestCase):
    """#125: md5 is not collision-resistant and should not be the default."""

    def test_the_md5_slot_is_marked_deprecated(self):
        from linkml_runtime import SchemaView
        sv = SchemaView("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
        self.assertTrue(sv.get_slot("md5").deprecated)

    def test_sha256_is_not_deprecated(self):
        from linkml_runtime import SchemaView
        sv = SchemaView("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
        self.assertFalse(sv.get_slot("sha256").deprecated)

    def test_the_generic_hash_slot_asks_for_the_algorithm(self):
        """A bare digest cannot be verified without knowing what produced it."""
        from linkml_runtime import SchemaView
        sv = SchemaView("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
        self.assertIn("algorithm", (sv.get_slot("hash").description or "").lower())
