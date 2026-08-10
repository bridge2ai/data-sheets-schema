"""A validation verdict is a claim about a record *against a schema* (#426).

`validation.artifacts` pinned only the record. So `validation_status()`
re-hashed the artifacts, found them unchanged, and reported VALID for a record
that may never have been checked against the schema now in the tree — a schema
change that tightened a constraint made every prior verdict a claim about a
check that no longer existed, and nothing noticed.

Raised reviewing #423, which mitigated half of it: a verdict *carried forward*
across a re-record already compared the record's schema block. A verdict
written once and never re-recorded had no binding at all.
"""

import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.provenance import CORE_SCHEMA, FULL_SCHEMA, _sha256
from data_sheets_schema.runs import STALE, VALID, validation_status


class TestTheVerdictCarriesItsSchema(unittest.TestCase):

    def test_a_fresh_verdict_pins_both_schemas(self):
        from data_sheets_schema.api_runner import RunSpec, validation_block
        spec = RunSpec(project="VOICE", arm="x", method="claudecode_agent",
                       bundle=Path("bundle.txt"), label="2026-08-11_x_rep1")
        block = validation_block(spec, [], recorded_by="test")
        self.assertEqual(_sha256(FULL_SCHEMA), block["schema"]["full_sha256"])
        self.assertEqual(_sha256(CORE_SCHEMA), block["schema"]["core_sha256"])


class TestStatusHonoursThePin(unittest.TestCase):
    LABEL, METHOD, PROJECT = "2026-08-11_schema_rep1", "claudecode_agent", "VOICE"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.concat = Path(self.tmp.name) / "data/d4d_concatenated"
        d = self.concat / f"{self.METHOD}_core" / self.LABEL
        d.mkdir(parents=True)
        self.artifact = d / f"{self.PROJECT}_d4d_core.yaml"
        self.artifact.write_text("id: x\n")
        self.record = d / f"{self.PROJECT}_provenance.yaml"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, schema):
        v = {"passed": True,
             "artifacts": {"core": {
                 "path": str(self.artifact),
                 "md5": hashlib.md5(self.artifact.read_bytes()).hexdigest()}}}
        if schema is not None:
            v["schema"] = schema
        self.record.write_text(yaml.safe_dump({"validation": v}, sort_keys=False))

    def _status(self):
        return validation_status(self.METHOD, self.LABEL, self.PROJECT, self.concat)

    def test_an_unchanged_schema_stays_valid(self):
        self._write({"full_sha256": _sha256(FULL_SCHEMA),
                     "core_sha256": _sha256(CORE_SCHEMA)})
        self.assertEqual(VALID, self._status())

    def test_a_moved_full_schema_is_stale(self):
        self._write({"full_sha256": "0" * 64,
                     "core_sha256": _sha256(CORE_SCHEMA)})
        self.assertEqual(STALE, self._status())

    def test_a_moved_core_schema_is_stale(self):
        self._write({"full_sha256": _sha256(FULL_SCHEMA),
                     "core_sha256": "0" * 64})
        self.assertEqual(STALE, self._status())

    def test_a_verdict_without_a_pin_is_left_alone(self):
        """Absent is not stale. Every verdict in the corpus predates the pin,
        and failing them would discard the lot to enforce a rule that postdates
        them — the same reasoning as the live-provenance cutoff."""
        self._write(None)
        self.assertEqual(VALID, self._status())

    def test_a_partial_pin_checks_what_it_has(self):
        """A block naming one schema and not the other is still evidence about
        the one it names."""
        self._write({"full_sha256": "0" * 64})
        self.assertEqual(STALE, self._status())

    def test_an_edited_artifact_is_still_stale(self):
        """The pin must not displace the check it was added beside."""
        self._write({"full_sha256": _sha256(FULL_SCHEMA),
                     "core_sha256": _sha256(CORE_SCHEMA)})
        self.artifact.write_text("id: x\n# edited after validating\n")
        self.assertEqual(STALE, self._status())


if __name__ == "__main__":
    unittest.main()
