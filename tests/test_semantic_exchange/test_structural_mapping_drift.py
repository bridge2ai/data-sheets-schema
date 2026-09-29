"""The committed structural mapping does not regenerate, and that is pinned.

`make gen-sssom-structural` emits 155 rows against the committed 165 (#234). A
mapping nobody can rebuild is a mapping nobody can safely change, so the ten
missing rows are enumerated here with what is actually wrong with each. Both
counts, and the `d4d:` counts in the table below, are compared with the files
by `test_the_module_docstring_states_the_current_counts` (#3000).

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
| 3 file/collection attrs | `d4d:` | 25 `d4d:` rows committed, 22 regenerated |
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
            check_column_drift, check_drift,
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
            cls.compared, cls.column_drift = check_column_drift(
                COMMITTED, scratch)

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

    def test_rows_both_files_carry_agree_column_by_column(self):
        """#2936. The triple check could not see sixteen rows whose range,
        cardinality and compatibility were generator placeholders, because
        the triple was right. Every regenerated row is also committed, so
        every one of them is compared."""
        self.assertGreater(self.compared, 100)
        self.assertEqual(self.column_drift, [],
                         "a row both files carry states a different range, "
                         "cardinality or compatibility in each")

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

    def test_the_check_says_which_columns_it_compared(self):
        """#2936. Said when nothing differs too, so a column check that found
        nothing cannot be mistaken for one that never ran."""
        import re
        said = re.search(r"The (\d+) row\(s\) both files carry agree on "
                         r"d4d_subject_range, subject_multivalued, "
                         r"type_compatible", self.stdout)
        self.assertIsNotNone(said, self.stdout)
        self.assertGreater(int(said.group(1)), 100,
                           "the check compared almost nothing")

    def test_the_summary_is_currently_the_fresh_one(self):
        """Pinned so that fixing #294 cannot silently leave them swapped."""
        self.assertIn("describes the generator's output", self.stdout)


class TestTheCheckActsOnColumnDrift(unittest.TestCase):
    """#2999. What `--check` does with `check_column_drift`'s answer.

    Every other `--check` test reads the committed file, where no value
    differs, so neither half of that use was exercised: printing the
    differences rather than "agree", and failing on them. The second was
    hidden besides by the ten KNOWN_UNDERIVABLE rows, which fail the check on
    their own; once #234 is fixed, a verdict that ignored column drift would
    pass a table that contradicts the schema.

    So the check is pointed (`--output-dir`) at the generator's own output,
    which regenerates exactly, and at a copy of it with one value put back to
    the placeholder #2936 removed — a copy that differs from regeneration in
    that value and in nothing else.
    """

    @classmethod
    def setUpClass(cls):
        import io
        import shutil
        import tempfile
        from contextlib import redirect_stdout
        sys.path.insert(0, str(REPO / "src" / "semantic_exchange"))
        from generate_structural_mapping import main  # noqa: E402

        def run(*argv):
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(list(argv))
            return code, out.getvalue()

        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        exact, drifted = base / "exact", base / "drifted"
        cls.written = run("--output-dir", str(exact))
        shutil.copytree(exact, drifted)

        cls.mapping = drifted / COMMITTED.name
        lines = cls.mapping.read_text(encoding="utf-8").splitlines(keepends=True)
        header = lines[0].rstrip("\n").split("\t")
        at = {c: header.index(c) for c in
              ("subject_id", "predicate_id", "object_id", "composition_path",
               "type_compatible")}
        for i, line in enumerate(lines[1:], start=1):
            fields = line.rstrip("\n").split("\t")
            if fields[at["composition_path"]]:
                assert fields[at["type_compatible"]] == "False", line
                fields[at["type_compatible"]] = "True"
                lines[i] = "\t".join(fields) + "\n"
                cls.triple = tuple(fields[at[c]] for c in
                                   ("subject_id", "predicate_id", "object_id"))
                break
        else:
            raise AssertionError("the generator wrote no composition row")
        cls.mapping.write_text("".join(lines), encoding="utf-8")
        cls.rows = len(lines) - 1
        cls.drifted_bytes = cls.mapping.read_bytes()

        cls.exact_result = run("--check", "--output-dir", str(exact))
        cls.drifted_result = run("--check", "--output-dir", str(drifted))
        cls.absent = base / "absent"
        cls.absent_result = run("--check", "--output-dir", str(cls.absent))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_the_generators_own_output_passes(self):
        """The control: without it, a drifted copy that fails says nothing
        about the one value changed."""
        self.assertEqual(self.written[0], 0, self.written[1])
        code, out = self.exact_result
        self.assertEqual(code, 0, out)
        self.assertIn("regenerate exactly", out)

    def test_one_differing_value_fails_the_check(self):
        """No triple is lost or gained and the summary is fresh, so this
        exit status is the column comparison's alone."""
        code, out = self.drifted_result
        self.assertEqual(code, 1, out)
        self.assertNotIn("regeneration does not produce", out)
        self.assertNotIn("committed file lacks", out)
        self.assertNotIn("summary does not regenerate", out)

    def test_the_differing_value_is_printed_and_agreement_is_not(self):
        s, p, o = self.triple
        _, out = self.drifted_result
        self.assertIn(f"1 value(s) differ on the {self.rows} row(s) both "
                      "files carry:", out)
        self.assertIn(f"{s}  --{p}->  {o}  type_compatible: committed 'True', "
                      "regenerated 'False'", out)
        self.assertNotIn("agree on", out)

    def test_the_summary_is_named_as_the_fresh_artifact(self):
        self.assertIn("The summary regenerates exactly, so it describes the "
                      "generator's output", self.drifted_result[1])

    def test_the_check_writes_nothing_where_it_reads(self):
        self.assertEqual(self.mapping.read_bytes(), self.drifted_bytes)
        code, out = self.absent_result
        self.assertEqual(code, 1, out)
        self.assertIn("No committed mapping", out)
        self.assertFalse(self.absent.exists(),
                         "--check created the directory it was checking")


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

    def test_a_missing_structural_column_names_the_file_and_the_column(self):
        import tempfile
        from generate_structural_mapping import check_column_drift
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "no_range.tsv"
            p.write_text("subject_id\tpredicate_id\tobject_id\t"
                         "subject_multivalued\ttype_compatible\n"
                         "a\tb\tc\tFalse\tTrue\n")
            with self.assertRaises(ValueError) as ctx:
                check_column_drift(COMMITTED, p)
            self.assertIn("d4d_subject_range", str(ctx.exception))
            self.assertIn("no_range.tsv", str(ctx.exception))


def _rows(text):
    import csv
    return list(csv.DictReader(
        [l for l in text.splitlines() if not l.startswith("#")],
        delimiter="\t"))


class TestColumnDrift(unittest.TestCase):
    """#2936: `check_column_drift` on files small enough to read."""

    HEADER = ("subject_id\tpredicate_id\tobject_id\td4d_subject_range\t"
              "subject_multivalued\ttype_compatible\tconfidence\n")

    def setUp(self):
        sys.path.insert(0, str(REPO / "src" / "semantic_exchange"))
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _file(self, name, *lines):
        p = Path(self._tmp.name) / name
        p.write_text(self.HEADER + "".join(l + "\n" for l in lines))
        return p

    def test_a_placeholder_on_a_shared_row_is_reported(self):
        from generate_structural_mapping import check_column_drift
        committed = self._file(
            "committed.tsv",
            "d4d:Dataset/anomalies\tskos:closeMatch\td4d:x\tstring\tFalse\tTrue\t0.7")
        regenerated = self._file(
            "regenerated.tsv",
            "d4d:Dataset/anomalies\tskos:closeMatch\td4d:x\tDataAnomaly\tTrue\tFalse\t0.7")
        compared, differ = check_column_drift(committed, regenerated)
        triple = ("d4d:Dataset/anomalies", "skos:closeMatch", "d4d:x")
        self.assertEqual(compared, 1)
        self.assertEqual(differ, [
            (triple, "d4d_subject_range", "string", "DataAnomaly"),
            (triple, "subject_multivalued", "False", "True"),
            (triple, "type_compatible", "True", "False"),
        ])

    def test_confidence_is_not_a_column_difference(self):
        """The triple check's reason for ignoring confidence still holds."""
        from generate_structural_mapping import check_column_drift
        committed = self._file("committed.tsv", "s\tp\to\tstring\tFalse\tTrue\t0.7")
        regenerated = self._file("regenerated.tsv", "s\tp\to\tstring\tFalse\tTrue\t0.9")
        self.assertEqual(check_column_drift(committed, regenerated), (1, []))

    def test_a_row_only_one_file_carries_is_the_triple_checks_business(self):
        from generate_structural_mapping import check_column_drift
        committed = self._file("committed.tsv",
                               "s\tp\to\tstring\tFalse\tTrue\t0.7",
                               "hand\tp\to\tFileCollectionTypeEnum\tTrue\tTrue\t1.0")
        regenerated = self._file("regenerated.tsv", "s\tp\to\tstring\tFalse\tTrue\t0.7")
        self.assertEqual(check_column_drift(committed, regenerated), (1, []))


def _schema_values(sv, subject_id):
    """(range, multivalued) the schema gives the subject `d4d:Class/a.b`: the
    last segment's induced range, and whether *any* segment is multivalued.
    """
    owner, path = subject_id[len("d4d:"):].split("/", 1)
    rng, multivalued = None, False
    for name in path.split("."):
        slot = sv.induced_slot(name, owner)
        rng, multivalued = slot.range, multivalued or bool(slot.multivalued)
        owner = rng
    return rng, multivalued


@unittest.skipUnless(COMMITTED.exists(), "structural mapping not present")
class TestRowsStateTheSchema(unittest.TestCase):
    """#2936. `_map_composition_paths` wrote every row with range None (then
    emitted as "string"), multivalued False and type_compatible True, whatever
    the path reached. `anomalies` is a list of `DataAnomaly`, so all sixteen
    rows contradicted the schema on cardinality, six also on range, and none
    had been checked.

    The expected values come from linkml's `SchemaView.induced_slot`, not from
    the generator's own parser, so the generator is not graded against its own
    answer.
    """

    CARDINALITY = "Cardinality mismatch: multivalued slot mapping to single value"

    @classmethod
    def setUpClass(cls):
        import io
        from contextlib import redirect_stdout
        from linkml_runtime.utils.schemaview import SchemaView
        sys.path.insert(0, str(REPO / "src" / "semantic_exchange"))
        from generate_structural_mapping import (  # noqa: E402
            D4DSchemaParser, ROCrateSchemaParser, StructuralMappingGenerator,
        )
        schema = REPO / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
        cls.sv = SchemaView(str(schema))
        cls.d4d = D4DSchemaParser(schema)
        gen = StructuralMappingGenerator(
            cls.d4d,
            ROCrateSchemaParser(
                REPO / "data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json"))
        with redirect_stdout(io.StringIO()):
            gen.generate_mappings()
        cls.regenerated = [m.to_sssom_row() for m in gen.mappings]
        cls.committed = _rows(COMMITTED.read_text(encoding="utf-8"))

    def _assert_rows_state_the_schema(self, rows):
        slot_rows = [r for r in rows if "/" in r["subject_id"]]
        self.assertTrue(any(r["composition_path"] for r in slot_rows),
                        "no composition rows to check")
        for r in slot_rows:
            rng, multivalued = _schema_values(self.sv, r["subject_id"])
            with self.subTest(subject=r["subject_id"]):
                self.assertEqual(r["d4d_subject_range"], rng)
                self.assertEqual(r["subject_multivalued"], str(multivalued))

    def test_every_committed_slot_row_states_the_schema(self):
        """Hand rows included: `FileCollection/collection_type` said
        multivalued after #382 made the slot single-valued. The four
        class-level rows name a class, not a slot, and are not checked."""
        self._assert_rows_state_the_schema(self.committed)

    def test_every_regenerated_slot_row_states_the_schema(self):
        self._assert_rows_state_the_schema(self.regenerated)

    def test_composition_rows_are_checked_not_asserted(self):
        """Each is a path through the multivalued `anomalies` mapped to one
        string, which is the cardinality rule `addressing_gaps` and
        `informed_consent` already fail on."""
        for label, rows in (("committed", self.committed),
                            ("regenerated", self.regenerated)):
            comp = [r for r in rows if r["composition_path"]]
            self.assertEqual(len(comp), 16, label)
            for r in comp:
                with self.subTest(file=label, subject=r["subject_id"]):
                    self.assertEqual(r["rocrate_value_type"], "str")
                    self.assertEqual(r["type_compatible"], "False")
                    self.assertEqual(r["warnings"], self.CARDINALITY)

    def test_twenty_of_the_committed_rows_are_flagged(self):
        """The count this fix states: the 4 flagged before it
        (`addressing_gaps` and `informed_consent` on `Dataset` and
        `DataSubset`) plus the 16 composition rows. It moves only with a
        deliberate change to the table."""
        flagged = [r for r in self.committed if r["type_compatible"] == "False"]
        self.assertEqual((len(flagged), len(self.committed)), (20, 165))

    def test_the_module_docstring_states_the_current_counts(self):
        """#3000. The docstring said 150 rows against 160, and 21 `d4d:` rows
        committed against 18 regenerated, while the file had 165 rows (#407
        and #503 added rows after it was written) and the assertion above said
        so. Nothing compared the prose with the files; this does."""
        import re
        doc = sys.modules[__name__].__doc__
        rows = re.search(r"emits (\d+) rows against the committed (\d+)", doc)
        d4d = re.search(r"(\d+) `d4d:` rows committed, (\d+) regenerated", doc)
        self.assertIsNotNone(rows, "the docstring no longer states row counts")
        self.assertIsNotNone(d4d, "the docstring no longer states d4d: counts")

        def d4d_targets(rows_):
            return sum(r["object_id"].startswith("d4d:") for r in rows_)
        self.assertEqual(
            (int(rows.group(1)), int(rows.group(2))),
            (len(self.regenerated), len(self.committed)))
        self.assertEqual(
            (int(d4d.group(1)), int(d4d.group(2))),
            (d4d_targets(self.committed), d4d_targets(self.regenerated)))

    def test_a_path_the_schema_does_not_have_is_named(self):
        with self.assertRaises(ValueError) as ctx:
            self.d4d.resolve_path("Dataset", "anomalies.no_such_slot")
        self.assertIn("'no_such_slot' is not an attribute of 'DataAnomaly'",
                      str(ctx.exception))

    def test_an_unknown_range_is_not_written_as_string(self):
        from generate_structural_mapping import (
            MappingJustification, MappingPredicate, StructuralMapping,
        )
        row = StructuralMapping(
            d4d_class="C", d4d_slot="s", d4d_slot_uri=None, d4d_range=None,
            d4d_multivalued=False, rocrate_property="p", rocrate_path="p",
            rocrate_type="str", predicate=MappingPredicate.CLOSE_MATCH,
            justification=MappingJustification.STRUCTURAL, confidence=0.7,
        ).to_sssom_row()
        self.assertEqual(row["d4d_subject_range"], "")

if __name__ == "__main__":
    unittest.main()
