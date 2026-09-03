"""Is the schema a run is generated against the schema this repo holds?

The digest sent to the model, the schema records are validated against and the
identity slots the pair checker uses are all read from the *merged* schemas,
which are generated artifacts. A module edited without regenerating makes every
record in an arm attest to a digest describing an older schema — and no field
in the record can reveal it, because the record correctly hashes the merged
file it actually read.

Nothing checked this before a generation run. `make check-sync` exists and is
not on the generation path; #521 records a period when it reported staleness
and the remedy it named was a silent no-op.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from data_sheets_schema import schema_digest
from data_sheets_schema.schema_sync import (
    IN_SYNC,
    MERGED_SCHEMAS,
    STALE,
    blocking,
    check,
    check_one,
)


class DigestIsAFunctionOfContentTest(unittest.TestCase):
    """The digest must not depend on where the file sits.

    It did: the rendered digest names the schema it came from, so identical
    bytes in a temp directory fingerprinted differently. That silently broke
    the check this module exists to perform, because rebuild-and-compare builds
    into a temp directory — three digests for one schema:
    `44d29023` in place, `2c93af56` rebuilt, `173abe3e` copied.
    """

    SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")

    def test_identical_bytes_elsewhere_fingerprint_the_same(self):
        if not self.SCHEMA.exists():
            self.skipTest("merged schema not present in this checkout")
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / self.SCHEMA.name
            shutil.copy2(self.SCHEMA, copy)
            here = schema_digest.fingerprint(
                schema_digest.digest_text("Dataset", self.SCHEMA))
            there = schema_digest.fingerprint(
                schema_digest.digest_text("Dataset", copy))
            self.assertEqual(here, there)

    def test_the_committed_digest_did_not_move(self):
        """A digest move must be a deliberate act, acknowledged here.

        This constant is the acknowledgment. When it fails, either the schema
        moved by accident — investigate before touching this — or it moved on
        purpose, in which case updating the constant is the record that
        someone meant it.

        Moves so far: `44d29023` → `580992ed` on 2026-08-21, anchoring the
        `doi` pattern (#646), after the v5 arm completed. Both study arms were
        re-validated under the new schema (24 records, all valid — they write
        bare DOIs); every non-bare doi value in the corpus (~100–122 by
        file scope; the count is scope-dependent, the location is not) lives
        in labels from 2026-08-12 or earlier,
        which keep the verdicts they were pinned with (#426).

        `580992ed` → `163c7e4d` on 2026-09-03: the digest renders two levels
        of object range (`NESTING_DEPTH`, #900, v8 plan step A) reached
        through inlined attributes — Grant, Organization, Person (via
        `committee_members`) and File join the 67 — and marks the eight
        class-ranged attributes that are references, not inlined objects
        (`principal_investigator: Person (reference — a string, not an
        object)`, #805), with no change to the schema itself, so no
        record's validity moves; the slot inventory recorded under the new
        digest is identical to the old one. Every run from here records the
        new digest; the v7 arm keeps `580992ed`, which is one of the things
        v7-vs-v8 measures.
        """
        if not self.SCHEMA.exists():
            self.skipTest("merged schema not present in this checkout")
        self.assertEqual(
            schema_digest.fingerprint(schema_digest.digest_text("Dataset")),
            "163c7e4db1d637e1cc458047813cd2c4")


class SyncCheckTest(unittest.TestCase):

    def test_the_repository_is_in_sync(self):
        """If this fails, do not generate — regenerate and commit first."""
        rows = check()
        self.assertEqual(blocking(rows), [],
                         "a merged schema is not built from current source")
        self.assertTrue(all(r["status"] == IN_SYNC for r in rows))

    def test_a_tampered_merged_schema_is_caught(self):
        """A check that never fails is indistinguishable from no check."""
        merged, source, cls, marker = MERGED_SCHEMAS[0]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        original = merged.read_bytes()
        try:
            merged.write_bytes(original + b"\n# not a line any rebuild emits\n")
            row = check_one(merged, source, cls, marker)
            self.assertEqual(row["status"], STALE)
            self.assertIn("differs from a fresh build", row["reason"])
            # The evidence is kept rather than deleted with the temp dir.
            self.assertTrue(Path(row["rebuilt_at"]).exists())
        finally:
            merged.write_bytes(original)
        self.assertEqual(check_one(merged, source, cls, marker)["status"],
                         IN_SYNC, "the fixture must restore the schema")

    def test_a_missing_source_is_unchecked_and_still_blocks(self):
        """A gate that could not run has not passed."""
        row = check_one(Path("nope_all.yaml"), Path("nope.yaml"), "Dataset")
        self.assertEqual(row["status"], "unchecked")
        self.assertEqual(blocking([row]), [row])


class GateTest(unittest.TestCase):

    def test_execute_refuses_to_start_when_the_schema_is_stale(self):
        """Fatal, unlike every other check on this path.

        The others describe records that remain usable evidence; this one
        corrupts the run's central input before a token is spent.
        """
        import inspect

        from data_sheets_schema.api_runner import execute
        source = inspect.getsource(execute)
        self.assertIn("schema_sync", source)
        # Before the client is built, or the check is decoration.
        self.assertLess(source.index("schema_sync"), source.index("_client()"))


if __name__ == "__main__":
    unittest.main()
