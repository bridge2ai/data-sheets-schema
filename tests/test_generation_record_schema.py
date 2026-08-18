"""The generation record has a schema of its own.

This repository schematises metadata about datasets. Its own generation
metadata was a hand-built Python dictionary written as YAML — 25 top-level
keys, `record_version: 1`, and nothing that could validate it. The one artifact
that *did* carry a LinkML schema, `d4d_run_telemetry.yaml`, is the derived
report rather than the authoritative record.

The schema describes today's record rather than a tidier one. Across 195
records the shape genuinely varies by `record_mode`, and requiring a field an
honest record cannot have would make the schema a fiction.
"""

import subprocess
import unittest
from pathlib import Path

import yaml

SCHEMA = Path("src/data_sheets_schema/schema/d4d_generation_record.yaml")
CORPUS = Path("data/d4d_concatenated")


class SchemaShapeTest(unittest.TestCase):

    def setUp(self):
        if not SCHEMA.exists():
            self.skipTest("schema not present in this checkout")
        self.schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))

    def test_it_is_not_imported_by_the_dataset_schema(self):
        """Importing it would move the `Dataset` digest an arm is frozen
        against, and it describes the pipeline rather than a dataset."""
        main = yaml.safe_load(
            Path("src/data_sheets_schema/schema/data_sheets_schema.yaml")
            .read_text(encoding="utf-8"))
        self.assertNotIn("d4d_generation_record", main.get("imports") or [])

    def test_only_universal_fields_are_required(self):
        """A `derived` record has no `inputs`, `model` or `system`; requiring
        them would make the schema describe a record that does not exist."""
        attrs = self.schema["classes"]["GenerationRecord"]["attributes"]
        required = {k for k, v in attrs.items() if v.get("required")}
        for optional in ("inputs", "model", "system", "api_usage",
                         "playbooks", "prompts", "derivation", "sources"):
            with self.subTest(field=optional):
                self.assertNotIn(optional, required)
        for universal in ("record_type", "record_version", "record_mode",
                          "run", "schema", "outputs"):
            with self.subTest(field=universal):
                self.assertIn(universal, required)

    def test_the_three_record_modes_are_enumerated(self):
        values = self.schema["enums"]["RecordMode"]["permissible_values"]
        self.assertEqual(set(values), {"live", "reconstructed", "derived"})

    def test_variable_blocks_are_declared_as_such(self):
        """`AnyBlock` says a block exists and what it is for without freezing
        an interior that is still being added to — `grounding` gained a finding
        kind this week. A schema needing an edit before an additive change can
        be recorded would be a brake rather than a contract."""
        self.assertEqual(
            self.schema["classes"]["AnyBlock"]["class_uri"], "linkml:Any")


class CompanionReferenceTest(unittest.TestCase):
    """Everything else a reader needs, by reference (#596 and this thread)."""

    def test_the_record_points_at_its_companions(self):
        from data_sheets_schema.provenance import companion_facts
        c = companion_facts("CHORUS", "claudecode_agent",
                            "2026-08-13_claude-opus-5-api-generic-v4_rep1")
        self.assertEqual(set(c), {"reasoning_log", "telemetry_report",
                                  "prompt_registry", "digest_inventory"})

    def test_absence_is_recorded_rather_than_omitted(self):
        """An absent reasoning log is a fact about the runtime (#400), not a
        gap in the record — so the reference exists and says `present: false`.
        """
        from data_sheets_schema.provenance import companion_facts
        c = companion_facts("NO_SUCH_PROJECT", "claudecode_agent", "nope")
        self.assertFalse(c["reasoning_log"]["present"])
        self.assertTrue(c["reasoning_log"]["path"])

    def test_registries_are_referenced_by_hash_not_copied(self):
        """A registry is shared and appended to over time: copying it into
        every record would multiply it and still not say which version was in
        force. A hash does say."""
        from data_sheets_schema.provenance import companion_facts
        c = companion_facts("CHORUS", "claudecode_agent",
                            "2026-08-13_claude-opus-5-api-generic-v4_rep1")
        if not c["prompt_registry"]["present"]:
            self.skipTest("registry not present in this checkout")
        self.assertTrue(c["prompt_registry"]["md5"])


class CorpusValidatesTest(unittest.TestCase):

    def test_a_real_record_validates(self):
        """One record, run through the real validator. The corpus-wide pass is
        `d4d provenance validate-records --strict`, too slow for a unit test at
        one linkml-validate invocation per record."""
        p = (CORPUS / "claudecode_agent_core"
             / "2026-08-13_claude-opus-5-api-generic-v4_rep1"
             / "CHORUS_provenance.yaml")
        if not (p.exists() and SCHEMA.exists()):
            self.skipTest("record or schema not present in this checkout")
        r = subprocess.run(
            ["poetry", "run", "linkml-validate", "-s", str(SCHEMA),
             "-C", "GenerationRecord", str(p)],
            capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-500:])

    def test_a_record_missing_a_required_field_is_rejected(self):
        """Otherwise the schema is decorative."""
        import tempfile
        if not SCHEMA.exists():
            self.skipTest("schema not present in this checkout")
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.yaml"
            bad.write_text(yaml.safe_dump(
                {"record_type": "d4d_generation_provenance",
                 "record_version": 1, "record_mode": "live"}),
                encoding="utf-8")
            r = subprocess.run(
                ["poetry", "run", "linkml-validate", "-s", str(SCHEMA),
                 "-C", "GenerationRecord", str(bad)],
                capture_output=True, text=True, timeout=300)
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
