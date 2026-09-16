"""The full and core schemas declare one release identity (#1874).

Through 2026-09-16 the full schema kept `version: 2.0.0` across the
narrative scalarization, Person inlining, DataGovernance, data-standard
vocabulary and anchored-DOI changes, and the core entry point declared no
version at all. Content hashes distinguished the instruments; the human
label did not. 3.0.0 names the definitions as they now stand, the core
declares the same version, the generated artifacts carry it, and the
provenance record states both.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "src" / "data_sheets_schema" / "schema"
RELEASE = "3.0.0"


def _declared(path: Path) -> str | None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    value = doc.get("version")
    return None if value is None else str(value)


class TestReleaseIdentity(unittest.TestCase):
    def test_full_and_core_declare_the_same_release(self):
        self.assertEqual(_declared(SCHEMA / "data_sheets_schema.yaml"), RELEASE)
        self.assertEqual(_declared(SCHEMA / "data_sheets_schema_core.yaml"), RELEASE)

    def test_the_release_is_semantic_and_past_the_two_line(self):
        """2.0.0 was declared on 2026-08-06 and kept through incompatible
        changes; the release that names the current definitions must be a
        later major."""
        major, minor, patch = (int(x) for x in RELEASE.split("."))
        self.assertGreaterEqual(major, 3)
        self.assertTrue(re.fullmatch(r"\d+\.\d+\.\d+", RELEASE))

    def test_the_generated_artifacts_carry_it(self):
        for merged in ("data_sheets_schema_all.yaml", "data_sheets_schema_core_all.yaml"):
            path = SCHEMA / merged
            if not path.exists():
                self.skipTest(f"{merged} not present in this checkout")
            head = path.read_text(encoding="utf-8")[:4000]
            self.assertIn(f"version: {RELEASE}", head, merged)
        model = ROOT / "src" / "data_sheets_schema" / "datamodel" / "data_sheets_schema.py"
        self.assertIn(f'version = "{RELEASE}"', model.read_text(encoding="utf-8"))
        jsonschema = ROOT / "project" / "jsonschema" / "data_sheets_schema.schema.json"
        if jsonschema.exists():
            self.assertIn(f'"version": "{RELEASE}"', jsonschema.read_text(encoding="utf-8"))

    def test_provenance_reads_both_declarations(self):
        from data_sheets_schema import provenance
        self.assertEqual(provenance.declared_schema_version(), RELEASE)
        self.assertEqual(provenance.declared_schema_version(provenance.CORE_SOURCE_SCHEMA), RELEASE)
        facts = provenance.schema_facts()
        self.assertEqual(facts["declared_version"], RELEASE)
        self.assertEqual(facts["core_declared_version"], RELEASE)
        self.assertEqual(facts["core_declared_in"], str(provenance.CORE_SOURCE_SCHEMA))
        self.assertTrue(facts["merged_schema_carries_version"])
        self.assertNotIn("note", facts)

    def test_a_core_that_disagrees_is_a_stated_fact(self):
        """The note is the only place a disagreement would surface; a
        recorder that silently reported the full version for both would hide
        exactly the drift #1874 found."""
        from unittest import mock
        from data_sheets_schema import provenance
        real = provenance.declared_schema_version

        def fake(source=provenance.SOURCE_SCHEMA):
            return "2.0.0" if source == provenance.CORE_SOURCE_SCHEMA else real(source)
        with mock.patch.object(provenance, "declared_schema_version", side_effect=fake):
            facts = provenance.schema_facts()
        self.assertEqual(facts["core_declared_version"], "2.0.0")
        self.assertIn("core entry point declares 2.0.0", facts["note"])

    def test_the_record_contract_declares_the_core_version(self):
        doc = yaml.safe_load((SCHEMA / "d4d_generation_record.yaml").read_text(encoding="utf-8"))
        attrs = doc["classes"]["SchemaFacts"]["attributes"]
        self.assertIn("core_declared_version", attrs)
        self.assertIn("core_declared_in", attrs)
        self.assertFalse(attrs["core_declared_version"].get("required", False))


if __name__ == "__main__":
    unittest.main()
