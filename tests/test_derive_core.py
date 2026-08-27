"""The core record derived from the full record (#694)."""
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/VOICE_d4d.yaml"


class DeriveCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from data_sheets_schema.d4d_pair_consistency import load_pair_schema
        cls.ps = load_pair_schema()

    def test_shared_slots_are_copied_and_pair_holds_by_construction(self):
        from data_sheets_schema.d4d_pair_consistency import validate_pair_data
        from data_sheets_schema.derive_core import derive_core
        full = {"id": "https://x/ds", "name": "x", "title": "T", "description": "d",
                "keywords": ["a"], "version": "1.0", "citation": "c",
                "file_collections": [{"id": "https://x/ds#fc1", "name": "raw",
                                      "collection_type": "raw", "path": "raw/",
                                      "file_count": 3, "description": "the raw files"}]}
        core = derive_core(full, self.ps)
        for k in ("id", "name", "title", "description", "keywords", "version"):
            self.assertEqual(core[k], full[k])
        self.assertNotIn("file_collections", core)          # full-only
        self.assertNotIn("citation", core) if "citation" not in self.ps.identity_slots else None
        self.assertEqual(core["conforms_to_class"], "CoreDataset")
        self.assertFalse(validate_pair_data(full, core, self.ps).errors)

    def test_distributions_come_from_collections_and_their_files(self):
        """#704 review F1: the full keeps bytes/hashes/formats on File
        entries under file_collections[].resources; a derived core that drops
        them loses facts the full states."""
        from data_sheets_schema.derive_core import derive_core
        full = {"id": "https://x/ds", "name": "x",
                "file_collections": [{"id": "https://x/ds#fc1", "name": "raw", "path": "raw/",
                                      "collection_type": "raw", "file_count": 2,
                                      "total_bytes": 10, "description": "the raw files",
                                      "compression": "gzip",
                                      "resources": [
                                          {"id": "https://x/ds#f1", "name": "a.tsv", "path": "raw/a.tsv",
                                           "bytes": 6, "md5": "0" * 32, "format": "TSV",
                                           "media_type": "text/tab-separated-values",
                                           "dialect": {"delimiter": "\t", "header": True}},
                                          {"id": "https://x/ds#f2", "name": "b.tsv", "path": "raw/b.tsv",
                                           "bytes": 4, "sha256": "f" * 64,
                                           "dialect": {"delimiter": "\t", "header": True}}]}]}
        core = derive_core(full, self.ps)
        d = core["distributions"]
        self.assertEqual(d[0], {"id": "https://x/ds#fc1", "name": "raw", "path": "raw/",
                                "description": "the raw files", "compression": "gzip",
                                "bytes": 10})                       # total_bytes → bytes
        self.assertEqual(d[1]["md5"], "0" * 32); self.assertEqual(d[1]["format"], "TSV")
        self.assertEqual(d[1]["bytes"], 6); self.assertEqual(d[2]["sha256"], "f" * 64)
        self.assertNotIn("dialect", d[1])                    # not a CoreDistribution slot
        # both files agree on one dialect → the dataset-level slot is derived
        self.assertEqual(core["dialect"], {"delimiter": "\t", "header": True})

    def test_dialect_is_absent_when_files_disagree_or_say_nothing(self):
        from data_sheets_schema.derive_core import derive_core
        base = {"id": "https://x/ds", "name": "x"}
        self.assertNotIn("dialect", derive_core(base, self.ps))
        two = {**base, "file_collections": [{"id": "c", "name": "c", "resources": [
            {"id": "f1", "name": "f1", "dialect": {"delimiter": ","}},
            {"id": "f2", "name": "f2", "dialect": {"delimiter": "\t"}}]}]}
        self.assertNotIn("dialect", derive_core(two, self.ps))

    def test_nested_resources_get_their_own_distributions(self):
        from data_sheets_schema.derive_core import derive_core
        full = {"id": "https://x/ds", "name": "x",
                "resources": [{"id": "https://x/sub", "name": "sub",
                               "file_collections": [{"id": "https://x/sub#fc", "name": "f", "path": "p/",
                                                     "collection_type": "processed"}]}]}
        core = derive_core(full, self.ps)
        self.assertEqual(core["resources"][0]["distributions"],
                         [{"id": "https://x/sub#fc", "name": "f", "path": "p/"}])
        self.assertNotIn("file_collections", core["resources"][0])

    def test_derivation_is_deterministic(self):
        from data_sheets_schema.derive_core import derive_core
        full = yaml.safe_load(FULL.read_text()) if FULL.exists() else {"id": "https://x", "name": "n"}
        self.assertEqual(derive_core(full, self.ps), derive_core(full, self.ps))

    @unittest.skipUnless(FULL.exists(), "corpus record absent")
    def test_a_real_full_record_derives_a_valid_pair(self):
        from data_sheets_schema.d4d_pair_consistency import validate_pair_data
        from data_sheets_schema.derive_core import derivation_facts, write_core
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "VOICE_d4d_core.yaml"
            facts = write_core(FULL, out, self.ps)
            text = out.read_text()
            self.assertTrue(text.startswith("# D4D Core Datasheet for VOICE Dataset"))
            self.assertIn("# Generation Method: derived by projection", text)
            self.assertIn(f"# Sources: {FULL}", text)
            core = yaml.safe_load(text)
            full = yaml.safe_load(FULL.read_text())
            self.assertFalse(validate_pair_data(full, core, self.ps).errors)
            self.assertEqual(facts["identity_slots"], len(self.ps.identity_slots))
            self.assertEqual(facts["from"]["path"], str(FULL))
            self.assertEqual(derivation_facts(FULL, self.ps)["from"]["md5"], facts["from"]["md5"])
            self.assertIn("dialect", facts["conditional"])

    def test_the_cli_writes_and_validates(self):
        """`d4d derive core` end to end, including the validate gate."""
        import click.testing

        from data_sheets_schema.cli import derive as derive_cli
        runner = click.testing.CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            full = Path(tmp) / "P_d4d.yaml"
            full.write_text("# D4D Datasheet for P Dataset\n# Generation Method: schema-grounded agentic, phase 1\n\n"
                            "id: https://x/ds\nname: x\ntitle: T\ndescription: d\nkeywords: [a]\n")
            out = Path(tmp) / "P_d4d_core.yaml"
            r = runner.invoke(derive_cli.derive, ["core", "--full", str(full), "--out", str(out)])
            self.assertEqual(r.exit_code, 0, r.output)
            self.assertIn("No issues found", r.output)
            self.assertTrue(out.read_text().startswith("# D4D Core Datasheet for P Dataset"))
            self.assertIn("# Sources:", out.read_text())


if __name__ == "__main__":
    unittest.main()
