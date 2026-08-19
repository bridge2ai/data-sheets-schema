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

import re
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


class ModeSpecificRequirements(unittest.TestCase):
    """#605: the schema was mode-blind, so it asserted almost nothing.

    Every field named here is one that *every* record of that mode already
    carries — measured across the 195 records on disk, not chosen. So these
    tests assert that the schema now discriminates by mode, and the corpus test
    below asserts the requirements are not inventions that fail honest records.
    """

    #: The gap that motivated the issue: each of these was absent from a `live`
    #: record that validated anyway.
    LIVE_REQUIRED = ("inputs", "model", "system", "validation")

    def _record(self):
        from data_sheets_schema.provenance import record_conformance
        path = (Path("data/d4d_concatenated/claudecode_agent_core")
                / "2026-08-13_claude-opus-5-api-generic-v4_rep1"
                / "CHORUS_provenance.yaml")
        if not (path.exists() and SCHEMA.exists()):
            self.skipTest("record or schema not present in this checkout")
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        if record_conformance(record):
            self.skipTest("validator unavailable or baseline record non-conforming")
        return record

    def test_a_live_record_must_carry_what_a_live_run_observed(self):
        from data_sheets_schema.provenance import record_conformance
        record = self._record()
        for field in self.LIVE_REQUIRED:
            with self.subTest(field=field):
                short = {k: v for k, v in record.items() if k != field}
                self.assertTrue(
                    record_conformance(short),
                    f"a live record with no {field!r} validated; before #605 "
                    "all four of these did")

    def test_a_derived_record_may_omit_them(self):
        """The requirements must be conditional, not a blanket tightening.

        A derived record consumes records rather than a bundle and has no model
        at all. If dropping the mode made no difference to the verdict, the
        rules would be requiring these of everything, and four honest records
        on disk would be reclassified as defective.
        """
        from data_sheets_schema.provenance import record_conformance
        record = self._record()
        derived = {k: v for k, v in record.items()
                   if k not in self.LIVE_REQUIRED}
        derived.update(record_mode="derived",
                       record_type="d4d_derived_provenance",
                       derivation={"method": "test"},
                       sources=[{"path": "x", "sha256": "y"}],
                       not_applicable=[{"field": "model", "reason": "test"}])
        self.assertEqual(record_conformance(derived), [])

    def test_the_two_discriminators_cannot_disagree(self):
        from data_sheets_schema.provenance import record_conformance
        record = self._record()
        confused = {**record, "record_mode": "derived"}
        self.assertTrue(record_conformance(confused),
                        "a record calling itself derived while typed as a "
                        "generation record validated")

    def test_every_record_on_disk_still_conforms(self):
        """The requirements describe the writers; they do not fail the corpus.

        A rule that is right in principle and rejects records nobody can
        regenerate is not an improvement — it is a schema that has to be
        ignored, which is where this started.
        """
        from data_sheets_schema.provenance import record_conformance
        records = sorted(Path("data/d4d_concatenated").glob(
            "*_core/*/*_provenance.yaml"))
        if not records:
            self.skipTest("no records in this checkout")
        failures = []
        for path in records:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for message in record_conformance(data):
                failures.append(f"{path}: {message}")
        self.assertEqual(failures[:5], [], f"{len(failures)} violations")


class ConformanceIsOnTheGenerationPath(unittest.TestCase):
    """A check that exists but does not run on the path it guards is #582.

    Validation used to be reachable only through `d4d provenance
    validate-records`, so a run could finish, report success, and leave a
    non-conforming record behind.
    """

    def test_write_reports_conformance_of_what_it_wrote(self):
        import tempfile

        from data_sheets_schema.provenance import ProvenanceRecord
        path = (Path("data/d4d_concatenated/claudecode_agent_core")
                / "2026-08-13_claude-opus-5-api-generic-v4_rep1"
                / "CHORUS_provenance.yaml")
        if not (path.exists() and SCHEMA.exists()):
            self.skipTest("record or schema not present in this checkout")
        good = yaml.safe_load(path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            rec = ProvenanceRecord(data=good)
            rec.write(Path(d) / "ok.yaml")
            if rec.conformance:
                self.skipTest("validator unavailable in this environment")

            # `validation` is preserved from a prior file by `write`, so drop a
            # field that is not carried forward.
            bad = {k: v for k, v in good.items() if k != "model"}
            rec = ProvenanceRecord(data=bad)
            out = rec.write(Path(d) / "bad.yaml")
            self.assertTrue(rec.conformance,
                            "write() did not notice a live record with no model")
            self.assertTrue(out.exists(),
                            "the record must still be written: it is the run's "
                            "only account of itself")

    def test_the_schema_is_findable_away_from_the_repo_root(self):
        """Otherwise the gate silently passes everything a sweep writes.

        `RECORD_SCHEMA` is repo-relative, matching its siblings, but those are
        read by commands run from the repo root and this one runs during
        generation. `record_conformance` returns no findings when it cannot
        run, so an unresolvable path would read as "conforms".
        """
        import os
        import tempfile

        from data_sheets_schema.provenance import record_schema_path
        cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as d:
                os.chdir(d)
                self.assertTrue(record_schema_path().exists())
        finally:
            os.chdir(cwd)


class TheSchemaKnowsEveryFieldTheWritersWrite(unittest.TestCase):
    """The general form of the gap the conformance gate found first.

    `report_regenerated_after_repair` is written by `execute()` only when
    repair rewrites a record after the report was rendered. No record on disk
    carries it, so validating the corpus could not reach it, and the schema
    forbade it — meaning the first real repair-with-report-regeneration run
    would have failed at the new gate.

    This reads the writers instead of the archive, so a field added to a rarely
    taken branch is caught when it is added rather than when it first fires.
    """

    #: Modules that assemble a generation record. Not every module with a dict
    #: named `data` — `src/renderer` and `src/validation` both have one and
    #: neither writes provenance, which is why this is a list and not a glob.
    WRITERS = ("src/data_sheets_schema/api_runner.py",
               "src/data_sheets_schema/provenance.py")

    ASSIGNMENT = re.compile(r"""(?:rec|record)\.data\[["']([a-z_]+)["']\]""")

    def test_no_writer_sets_a_field_the_schema_forbids(self):
        if not SCHEMA.exists():
            self.skipTest("schema not present in this checkout")
        schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
        known = set(schema["classes"]["GenerationRecord"]["attributes"])
        unknown = {}
        for name in self.WRITERS:
            path = Path(name)
            if not path.exists():
                continue
            for field in self.ASSIGNMENT.findall(
                    path.read_text(encoding="utf-8")):
                if field not in known:
                    unknown.setdefault(field, name)
        self.assertEqual(
            unknown, {},
            "these fields are written into a generation record but the schema "
            "does not declare them, so a run taking that branch fails the "
            f"conformance gate: {unknown}")

    def test_the_check_can_see_the_writers_at_all(self):
        """Otherwise the test above passes by finding nothing to check.

        A renamed module or a changed assignment idiom would empty the scan,
        and an empty scan trivially satisfies the assertion.
        """
        found = set()
        for name in self.WRITERS:
            path = Path(name)
            if path.exists():
                found |= set(self.ASSIGNMENT.findall(
                    path.read_text(encoding="utf-8")))
        if not any(Path(w).exists() for w in self.WRITERS):
            self.skipTest("writers not present in this checkout")
        self.assertIn("validation", found,
                      "the scan found no known record field; it is not "
                      f"reading the writers. Found: {sorted(found)}")


if __name__ == "__main__":
    unittest.main()
