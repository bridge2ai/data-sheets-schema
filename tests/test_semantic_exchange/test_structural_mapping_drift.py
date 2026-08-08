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



class TestCompositionSubjectsDoNotCollide(unittest.TestCase):
    """#410. `_map_composition_paths` named its subject after the last segment
    of the path, so `anomalies.id` became `d4d:Dataset/id` — which is also the
    identifier of `Dataset`'s *own* `id` slot. The row then asserted that the
    Dataset's id closely matches an anomaly, which is false. What distinguished
    them survived only in the free-text `structural_notes` column.
    """

    @classmethod
    def setUpClass(cls):
        import csv
        cls.rows = list(csv.DictReader(
            COMMITTED.read_text(encoding="utf-8").splitlines(), delimiter="\t"))
        cls.comp = [r for r in cls.rows
                    if "Composition path" in (r.get("structural_notes") or "")]

    def test_composition_rows_carry_the_whole_path_in_the_subject(self):
        self.assertTrue(self.comp, "no composition rows found")
        for r in self.comp:
            path = r["structural_notes"].split("Composition path:", 1)[1].strip()
            with self.subTest(subject=r["subject_id"]):
                self.assertTrue(r["subject_id"].endswith("/" + path),
                                f"{r['subject_id']} does not encode {path!r}")

    def test_no_composition_row_claims_a_class_own_slot(self):
        """The falsehood the collision produced: `Dataset/id` is a real slot of
        `Dataset`, and it does not closely match an anomaly."""
        for own in ("d4d:Dataset/id", "d4d:Dataset/name",
                    "d4d:Dataset/description", "d4d:Dataset/notes",
                    "d4d:Dataset/source_caveats"):
            with self.subTest(subject=own):
                self.assertNotIn(own, {r["subject_id"] for r in self.comp})

    def test_subject_ids_are_unique(self):
        subs = [r["subject_id"] for r in self.rows]
        dupes = {s for s in subs if subs.count(s) > 1}
        self.assertEqual(set(), dupes)


class TestTheCheckCoversBothArtifacts(unittest.TestCase):
    """`make gen-sssom-structural` writes two files; the check reads two (#295).

    Today the summary regenerates byte-for-byte and the mapping does not, so
    they were committed from different generator states and the summary does
    not describe the file beside it. That is the confusing direction — the
    artifact that is correct is the one nobody thinks to distrust.
    """

    @classmethod
    def setUpClass(cls):
        cls.stdout = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            cwd=REPO, capture_output=True, text=True).stdout

    def test_the_check_reports_on_the_summary_too(self):
        self.assertIn("summary", self.stdout.lower())

    def test_the_summary_is_currently_the_fresh_one(self):
        """Pinned so that fixing #294 cannot silently leave them swapped."""
        self.assertIn("describes the generator's output", self.stdout)


class TestMalformedInputIsNamed(unittest.TestCase):
    """#296: a bare KeyError sends the reader to the code, not the file."""

    def setUp(self):
        sys.path.insert(0, str(REPO / "src" / "semantic_exchange"))

    def test_a_missing_column_names_the_file_and_the_column(self):
        import tempfile
        from generate_structural_mapping import read_sssom_rows
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "partial.tsv"
            p.write_text("subject_id\tobject_id\na\tb\n")
            with self.assertRaises(ValueError) as ctx:
                read_sssom_rows(p)
            self.assertIn("predicate_id", str(ctx.exception))
            self.assertIn("partial.tsv", str(ctx.exception))

    def test_a_headerless_file_is_an_error_not_zero_rows(self):
        import tempfile
        from generate_structural_mapping import read_sssom_rows
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "comments.tsv"
            p.write_text("# only comments\n")
            with self.assertRaises(ValueError):
                read_sssom_rows(p)

    def test_a_well_formed_file_still_reads(self):
        from generate_structural_mapping import read_sssom_rows
        self.assertGreater(len(read_sssom_rows(COMMITTED)), 100)

if __name__ == "__main__":
    unittest.main()
