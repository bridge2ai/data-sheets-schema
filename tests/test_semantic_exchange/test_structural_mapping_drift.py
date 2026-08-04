"""The committed structural mapping does not regenerate, and that is pinned.

`make gen-sssom-structural` emits 150 rows against the committed 160 (#234). A
mapping nobody can rebuild is a mapping nobody can safely change, so the ten
missing rows are enumerated here with what is actually wrong with each.

The point is not to bless the gap. It is that **new** drift should fail while the
known gap does not, because a check that has been red since the day it was
written is a check nobody reads.

## Why each row is missing

The issue guessed the `Core*` rows were lost because the core schema is not a
declared input. That is wrong, and the accounting says so cleanly:

| dropped | target | reason |
|---|---|---|
| 4 class-level rows | `schema:` | the generator emits **no** class-level rows at all |
| 2 `…/resources` | `schema:hasPart` | it produces no `schema:` targets |
| 3 file/collection attrs | `d4d:` | 21 `d4d:` rows committed, 18 regenerated |
| 1 `total_bytes` | `dcat:byteSize` | it produces no `dcat:` targets |

`class_uri` is parsed into `SchemaClass` and never used to emit a mapping —
every `StructuralMapping(...)` is constructed from `slot.parent_class`, so
`DataSubset` is missing for the same reason `CoreDataset` is, and it lives in
the full schema. Adding the core schema as an input would recover nothing.

`_map_slot_uris` only emits a row when the RO-Crate input carries a matching
property. `fileType`, `collectionType`, `fileCount` and `byteSize` are not in
`full-ro-crate-metadata.json`, so those rows cannot come from that strategy
either.

So the committed file is the output of a more capable generator than the one in
the tree, or was partly written by hand. Either way the ten rows are assertions
no declared input supports.
"""

import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "src" / "semantic_exchange" / "generate_structural_mapping.py"
COMMITTED = (REPO / "data" / "semantic_exchange"
             / "d4d_rocrate_structural_mapping.sssom.tsv")

#: Rows the committed file asserts that regeneration does not produce.
#: Shrinking this set is progress. Growing it without a reason is the drift
#: this test exists to catch.
KNOWN_UNDERIVABLE = {
    # No class-level strategy exists — `class_uri` is parsed and never used.
    ("d4d:CoreDataset", "skos:exactMatch", "schema:Dataset"),
    ("d4d:CoreDatasetCollection", "skos:exactMatch", "schema:Dataset"),
    ("d4d:CoreDistribution", "skos:exactMatch", "schema:DataDownload"),
    ("d4d:DataSubset", "skos:exactMatch", "schema:Dataset"),
    # No `schema:` targets are produced.
    ("d4d:DatasetCollection/resources", "skos:exactMatch", "schema:hasPart"),
    ("d4d:FileCollection/resources", "skos:exactMatch", "schema:hasPart"),
    # Target absent from the RO-Crate input, so `_map_slot_uris` cannot match.
    ("d4d:File/file_type", "skos:exactMatch", "d4d:fileType"),
    ("d4d:FileCollection/collection_type", "skos:exactMatch", "d4d:collectionType"),
    ("d4d:FileCollection/file_count", "skos:exactMatch", "d4d:fileCount"),
    # Also disagrees with the schema, which declares `slot_uri: d4d:total_bytes`.
    ("d4d:FileCollection/total_bytes", "skos:exactMatch", "dcat:byteSize"),
}


@unittest.skipUnless(COMMITTED.exists(), "structural mapping not present")
class TestStructuralMappingDrift(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(REPO / "src" / "semantic_exchange"))
        import tempfile
        from generate_structural_mapping import (  # noqa: E402
            D4DSchemaParser, ROCrateSchemaParser, StructuralMappingGenerator,
            check_drift,
        )
        import io
        from contextlib import redirect_stdout
        d4d = D4DSchemaParser(
            REPO / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
        roc = ROCrateSchemaParser(
            REPO / "data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json")
        gen = StructuralMappingGenerator(d4d, roc)
        with redirect_stdout(io.StringIO()):
            gen.generate_mappings()
            cls._tmp = tempfile.TemporaryDirectory()
            scratch = Path(cls._tmp.name) / "regenerated.tsv"
            gen.export_sssom(scratch)
            cls.lost, cls.gained = check_drift(COMMITTED, scratch)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_the_gap_is_exactly_the_known_one(self):
        """New drift fails; the documented gap does not."""
        self.assertEqual(
            set(self.lost), KNOWN_UNDERIVABLE,
            "the set of rows that will not regenerate has changed — if rows "
            "were fixed, shrink KNOWN_UNDERIVABLE; if new ones appeared, they "
            "are drift and need a reason")

    def test_regeneration_invents_nothing(self):
        """The other direction. Rows the generator produces that the committed
        file lacks would mean the file is stale rather than hand-extended, and
        that is a different problem with a different fix."""
        self.assertEqual(self.gained, [],
                         "regeneration produces rows the committed file lacks")

    def test_check_mode_writes_nothing(self):
        """A check that regenerates in place becomes the thing it detects."""
        before = COMMITTED.read_bytes()
        subprocess.run([sys.executable, str(SCRIPT), "--check"],
                       cwd=REPO, capture_output=True)
        self.assertEqual(COMMITTED.read_bytes(), before)

    def test_check_mode_fails_while_the_gap_stands(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--check"],
                                cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not regenerate", result.stdout)


if __name__ == "__main__":
    unittest.main()
