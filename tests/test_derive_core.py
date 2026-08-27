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

    def test_distributions_come_from_file_collections_over_shared_slots(self):
        from data_sheets_schema.derive_core import derive_core
        full = {"id": "https://x/ds", "name": "x",
                "file_collections": [{"id": "https://x/ds#fc1", "name": "raw", "path": "raw/",
                                      "collection_type": "raw", "file_count": 3,
                                      "total_bytes": 10, "description": "the raw files",
                                      "compression": "gzip"}]}
        core = derive_core(full, self.ps)
        self.assertEqual(core["distributions"],
                         [{"id": "https://x/ds#fc1", "name": "raw", "path": "raw/",
                           "description": "the raw files", "compression": "gzip"}])
        self.assertNotIn("dialect", core)                    # not derivable, by rule

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


if __name__ == "__main__":
    unittest.main()
