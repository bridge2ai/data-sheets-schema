"""The committed structural mapping does not regenerate, and that is pinned.

`make gen-sssom-structural` emits 155 rows against the committed 165 (#234). A
mapping nobody can rebuild is a mapping nobody can safely change, so the ten
missing rows are enumerated, with what is actually wrong with each, as
`KNOWN_UNDERIVABLE` in `generate_structural_mapping.py`; this test and the
generator's `--check` (`make check-sssom-structural`) both read that one set
(#3968). Both counts, and the `d4d:` counts in the table below, are compared
with the files by `test_the_module_docstring_states_the_current_counts`
(#3000).

The point is not to bless the gap. It is that **new** drift should fail while the
known gap does not, because a check that has been red since the day it was
written is a check nobody reads. `--check` was that check until #3968.

Nor may the gap be lost. A rewrite by the generator drops all ten rows, so
`make gen-sssom-all` no longer runs the structural target and `make
clean-sssom` no longer deletes the table (#3967); `--check` names every
curated row a rewrite dropped.

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

import functools
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "src" / "semantic_exchange" / "generate_structural_mapping.py"
COMMITTED = (REPO / "data" / "semantic_exchange"
             / "d4d_rocrate_structural_mapping.sssom.tsv")
SUMMARY = COMMITTED.with_name("d4d_rocrate_structural_mapping_summary.md")


def _snapshot(*paths):
    """Each file's content hash and modification time, keyed by name.

    The content alone cannot see `--check` writing back what regeneration
    makes where the file already holds exactly that (#3056); the time can.
    """
    import hashlib
    return {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(),
                     p.stat().st_mtime_ns)
            for p in paths}


if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))

# The rows the committed file asserts that regeneration does not produce are
# `gsm.KNOWN_UNDERIVABLE`, each with its reason where it is defined. This
# file reads the generator's set rather than a copy of it, so the test and
# `--check` cannot disagree about what the gap is (#3968).
import generate_structural_mapping as gsm  # noqa: E402


@functools.lru_cache(maxsize=None)
def _generator():
    """One generator run on the real inputs, shared by the classes that
    check copies of the committed table with `run_check`: parsing the merged
    schema is most of their time, and the run is only read afterwards."""
    import io
    from contextlib import redirect_stdout
    with redirect_stdout(io.StringIO()):
        generator = gsm.StructuralMappingGenerator(
            gsm.D4DSchemaParser(
                REPO / "src/data_sheets_schema/schema/"
                "data_sheets_schema_all.yaml"),
            gsm.ROCrateSchemaParser(
                REPO / "data/ro-crate/profiles/fairscape/"
                "full-ro-crate-metadata.json"))
        generator.generate_mappings()
    return generator


def _run_check(directory, known=None):
    """`run_check` on the mapping and summary in `directory`, with `known`
    or else KNOWN_UNDERIVABLE as `main` passes it when the check runs:
    (exit status, what it printed)."""
    import io
    from contextlib import redirect_stdout
    out = io.StringIO()
    with redirect_stdout(out):
        code = gsm.run_check(
            _generator(), directory / COMMITTED.name, directory / SUMMARY.name,
            gsm.KNOWN_UNDERIVABLE if known is None else known)
    return code, out.getvalue()


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
            set(self.lost), gsm.KNOWN_UNDERIVABLE,
            "the set of rows that will not regenerate has changed — if rows "
            "were fixed, shrink KNOWN_UNDERIVABLE in "
            "generate_structural_mapping.py; if new ones appeared, they are "
            "drift and need a reason")

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
        """A check that regenerates in place becomes the thing it detects.

        Both committed artifacts, by content and by modification time: the
        committed summary regenerates byte for byte, so a `--check` that wrote
        it back would leave its content as it was (#3056).
        `TestTheCheckActsOnColumnDrift` makes the same check on a summary
        that differs from regeneration, where the content would move too.

        Since #3968 this run takes the pass branch, the one that accepts the
        KNOWN_UNDERIVABLE rows; until then it failed on them and never
        reached a pass. `TestTheCheckActsOnColumnDrift` covers the pass with
        no known gap, on the generator's own output (#3142)."""
        present = [p for p in (COMMITTED, SUMMARY) if p.exists()]
        before = _snapshot(*present)
        subprocess.run([sys.executable, str(SCRIPT), "--check"],
                       cwd=REPO, capture_output=True)
        self.assertEqual(_snapshot(*present), before)

    def test_check_mode_passes_on_exactly_the_known_gap(self):
        """#3968. `make check-sssom-structural` runs this, and it exited 1 on
        main by design: the committed file carries the KNOWN_UNDERIVABLE
        rows, which only the test above allowed. It accepts exactly them
        now, and still names each one, so a pass shows the gap rather than
        hiding it. Run as `make` runs it, so it also holds `main` to passing
        the module's set; `TestTheCheckAcceptsExactlyTheKnownGap` and
        `TestTheCheckDoesWhatItsStatementSays` hold the check to
        CHECK_STATEMENT, the one statement of what it compares (#4076)."""
        result = subprocess.run([sys.executable, str(SCRIPT), "--check"],
                                cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            f"✓ The committed mapping regenerates apart from the "
            f"{len(gsm.KNOWN_UNDERIVABLE)} row(s) KNOWN_UNDERIVABLE lists, "
            "and the summary regenerates exactly.", result.stdout)
        for s, p, o in gsm.KNOWN_UNDERIVABLE:
            self.assertIn(f"      {s}  --{p}->  {o}\n", result.stdout)



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
        nothing cannot be mistaken for one that never ran. This run passes
        on the KNOWN_UNDERIVABLE rows (#3968); the same line on a pass with
        no known gap is
        `TestTheCheckActsOnColumnDrift.test_a_pass_says_which_columns_it_compared`
        (#3057)."""
        import re
        said = re.search(r"The (\d+) row\(s\) both files carry agree on "
                         r"d4d_subject_range, subject_multivalued, "
                         r"type_compatible", self.stdout)
        self.assertIsNotNone(said, self.stdout)
        self.assertGreater(int(said.group(1)), 100,
                           "the check compared almost nothing")

    def test_the_summary_is_currently_the_fresh_one(self):
        """Pinned so that fixing #294 cannot silently leave them swapped.
        Said on the pass as well since #3968: the summary describes the
        generator's output, which lacks the KNOWN_UNDERIVABLE rows."""
        self.assertIn("describes the generator's output", self.stdout)


class TestTheCheckActsOnColumnDrift(unittest.TestCase):
    """#2999. What `--check` does with `check_column_drift`'s answer.

    The `--check` tests that read the committed file read one where no
    value differs, so neither half of that use was exercised there: printing
    the differences rather than "agree", and failing on them. The second was
    hidden besides by the ten KNOWN_UNDERIVABLE rows, which failed the check
    on their own until #3968 had it accept exactly them; a verdict that
    ignored column drift would now pass a table that contradicts the schema.

    So the check is pointed (`--output-dir`) at the generator's own output,
    which regenerates exactly, and at a copy of it with one value put back to
    the placeholder #2936 removed — a copy that differs from regeneration in
    that value and in nothing else.

    The generator's own output carries none of the KNOWN_UNDERIVABLE rows,
    and the check now fails a table that lacks them (#3968), so these runs
    patch the set empty: the check as it will run once #294 has made every
    row derivable. `TestTheCheckAcceptsExactlyTheKnownGap` runs it with the
    set as it stands.

    A third copy differs in its summary alone, by one appended line (#3056).
    It is what lets "writes nothing where it reads" fail for the summary: in
    the other two the summary is already what regeneration makes, so writing
    it back would leave its bytes unchanged.

    All three are snapshotted, the check is run on exactly the directories
    snapshotted, and the generator's own output is among them (#3142). It is
    the only run here that takes the pass branch; the committed data takes
    the other pass, the one that accepts the KNOWN_UNDERIVABLE rows. A pass
    means both
    artifacts already equal what regeneration makes, so a write there leaves
    their content as it was and only the modification time can see it. Every
    file is therefore set to a fixed past time before the snapshot, so that
    the time moves on any write however coarse the file system's clock,
    rather than resting on the check running in a later tick than the
    generator that wrote the file.
    """

    #: What each file read is set to before the snapshot: 2000-01-01 UTC.
    PAST_NS = 946_684_800 * 10**9

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

        stale = base / "stale_summary"
        shutil.copytree(exact, stale)
        with (stale / SUMMARY.name).open("a", encoding="utf-8") as fh:
            fh.write("A line regeneration does not write.\n")

        drifted_no_summary = base / "drifted_no_summary"
        shutil.copytree(drifted, drifted_no_summary)
        (drifted_no_summary / SUMMARY.name).unlink()

        no_summary = base / "no_summary"
        shutil.copytree(exact, no_summary)
        (no_summary / SUMMARY.name).unlink()

        # The check runs on these and on nothing else that exists, so no
        # directory it reads can be left out of the snapshot (#3142).
        read_from = {"exact": exact, "drifted": drifted,
                     "stale summary": stale, "no summary": no_summary,
                     "drifted, no summary": drifted_no_summary}
        for path in read_from.values():
            for file in path.iterdir():
                os.utime(file, ns=(cls.PAST_NS, cls.PAST_NS))

        def directory(name):
            return _snapshot(*sorted(read_from[name].iterdir()))
        cls.before = {name: directory(name) for name in read_from}

        # No known gap: these copies are the generator's own output, which
        # carries none of the KNOWN_UNDERIVABLE rows (#3968).
        with mock.patch.object(gsm, "KNOWN_UNDERIVABLE", frozenset()):
            cls.results = {name: run("--check", "--output-dir", str(path))
                           for name, path in read_from.items()}
            cls.absent = base / "absent"
            cls.absent_result = run("--check", "--output-dir",
                                    str(cls.absent))
        cls.exact_result = cls.results["exact"]
        cls.drifted_result = cls.results["drifted"]
        cls.stale_result = cls.results["stale summary"]
        cls.no_summary_result = cls.results["no summary"]
        cls.drifted_no_summary_result = cls.results["drifted, no summary"]
        cls.after = {name: directory(name) for name in read_from}

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

    def test_a_pass_says_which_columns_it_compared(self):
        """#3057. Before #2936 a pass printed only "regenerate exactly", from
        a check that compared triples alone. Without this line a pass from the
        column check reads exactly like one from that check, so the columns
        compared, and how many rows, are said on a pass too."""
        _, out = self.exact_result
        self.assertIn(f"The {self.rows} row(s) both files carry agree on "
                      "d4d_subject_range, subject_multivalued, "
                      "type_compatible.", out)

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

    def test_a_summary_that_differs_fails_the_check_and_is_named(self):
        """The control for the stale-summary copy: the check read that
        summary and found it differs. Its mapping regenerates exactly, so the
        exit status is the summary's alone."""
        code, out = self.stale_result
        self.assertEqual(code, 1, out)
        self.assertIn("The summary does not regenerate", out)
        self.assertNotIn("regeneration does not produce", out)
        self.assertNotIn("committed file lacks", out)
        self.assertNotIn("value(s) differ", out)
        self.assertIn(f"The {self.rows} row(s) both files carry agree on", out)

    def test_a_stale_summary_alone_is_what_the_headline_names(self):
        """#3125. The headline blamed the mapping whatever drifted, said the
        summary failed "either" when nothing else had, and closed on the
        mapping's #234 line. Here the mapping regenerates exactly."""
        _, out = self.stale_result
        self.assertIn("✗ The committed summary does not regenerate from the "
                      "mapping's inputs.", out)
        self.assertNotIn("committed mapping does not regenerate", out)
        self.assertNotIn("either", out)
        self.assertNotIn("(#234)", out)

    def test_a_missing_summary_is_named_missing_not_stale(self):
        """A summary that does not exist is not stale: the check says it is
        missing, and fails."""
        code, out = self.no_summary_result
        self.assertEqual(code, 1, out)
        self.assertIn("✗ No committed summary at", out)
        self.assertIn("the summary beside it is missing", out)
        self.assertNotIn("stale", out)
        self.assertNotIn("committed mapping does not regenerate", out)

    def test_a_missing_summary_beside_a_drifted_mapping_is_named_missing(self):
        """Codex review of #3372: with the mapping drifted too, the closing
        line still names the missing summary, not a stale one."""
        code, out = self.drifted_no_summary_result
        self.assertEqual(code, 1, out)
        self.assertIn("✗ The committed mapping does not regenerate", out)
        self.assertIn("There is no committed summary either, at", out)
        self.assertNotIn("does not regenerate either", out)

    def test_a_drifted_mapping_is_what_the_headline_names(self):
        """The other side of #3125: with the summary fresh, the mapping."""
        _, out = self.drifted_result
        self.assertIn("✗ The committed mapping does not regenerate from its "
                      "inputs.", out)
        self.assertNotIn("committed summary does not regenerate", out)
        self.assertIn("(#234)", out)

    def test_the_check_writes_nothing_where_it_reads(self):
        """Every file in each directory the check read, by content and by
        modification time, and no file added. The stale-summary copy is the
        one where writing the summary back would change its content (#3056),
        so for the failure branch the catch does not rest on the file
        system's clock alone. The generator's own output is the one that
        takes the pass branch (#3142); there both files already equal what
        regeneration makes, so the catch is the modification time, which was
        set to a fixed past time before the snapshot."""
        self.assertIn(0, [code for code, _ in self.results.values()],
                      "no directory the check read took the pass branch, so "
                      "a write on a pass would go unseen")
        for name, before in self.before.items():
            with self.subTest(directory=name):
                self.assertEqual({mtime for _, mtime in before.values()},
                                 {self.PAST_NS},
                                 "the files were not set to the past time, "
                                 "so an unchanged time may be the clock's "
                                 "granularity rather than no write")
                self.assertEqual(sorted(self.after[name]), sorted(before))
                for file, (content, mtime) in before.items():
                    self.assertEqual(self.after[name][file][0], content,
                                     f"--check rewrote {file}")
                    self.assertEqual(self.after[name][file][1], mtime,
                                     f"--check wrote to {file}")
        code, out = self.absent_result
        self.assertEqual(code, 1, out)
        self.assertIn("No committed mapping", out)
        self.assertFalse(self.absent.exists(),
                         "--check created the directory it was checking")


@unittest.skipUnless(COMMITTED.exists() and SUMMARY.exists(),
                     "structural mapping not present")
class TestTheCheckAcceptsExactlyTheKnownGap(unittest.TestCase):
    """#3968. `--check` accepts the rows KNOWN_UNDERIVABLE lists and no
    other row, so it is green on the committed table and red when the rows
    regeneration does not produce stop being exactly those. What it compares
    is CHECK_STATEMENT's to say (#4076); these cases hold it to what that
    says of the triples, the four ways one fails and the accepted rows
    named, and `TestTheCheckDoesWhatItsStatementSays` to the rest.

    Each case is a copy of the committed mapping and summary changed in one
    way, checked by `run_check` with the set as it stands against one
    generator run (`main` would parse the merged schema once per case).
    These fail: a row added; a regenerable row's object changed; a
    structural value changed on a row both files carry; one
    KNOWN_UNDERIVABLE row removed; the generator's own output, which is the
    table `make gen-sssom-structural` writes and lacks every one of them
    (#3967); and the unchanged copy checked against the set with one
    regenerable row added to it, which is what the set says once #294 makes
    one of its rows derivable and nobody takes it out.
    """

    #: The KNOWN_UNDERIVABLE row taken out of one copy.
    REMOVED = ("d4d:FileCollection/total_bytes", "skos:exactMatch",
               "dcat:byteSize")

    @classmethod
    def setUpClass(cls):
        import io
        import shutil
        import tempfile
        from contextlib import redirect_stdout

        cls.generator = _generator()
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)

        header, *lines = COMMITTED.read_text(encoding="utf-8").splitlines(
            keepends=True)
        names = header.rstrip("\n").split("\t")

        def fields(line):
            return line.rstrip("\n").split("\t")

        def triple(row):
            return tuple(row[names.index(c)] for c in gsm.TRIPLE)

        def joined(row):
            return "\t".join(row) + "\n"

        def changed(row, column, value):
            row = list(row)
            row[names.index(column)] = value
            return row

        # The first committed row regeneration produces. Every case but the
        # removal and the rewrite adds, changes or lists this one.
        at = next(i for i, line in enumerate(lines)
                  if triple(fields(line)) not in gsm.KNOWN_UNDERIVABLE)
        row = fields(lines[at])
        cls.regenerable = triple(row)
        added = changed(row, "object_id", "schema:addedByThisTest")
        moved = changed(row, "object_id", "schema:changedByThisTest")
        cls.added, cls.moved = triple(added), triple(moved)
        column = "subject_multivalued"
        was = row[names.index(column)]
        cls.revalued = (column, str(was != "True"), was)
        revalued = changed(row, column, cls.revalued[1])

        def copy(name, data):
            directory = base / name
            directory.mkdir()
            (directory / COMMITTED.name).write_text(header + "".join(data),
                                                    encoding="utf-8")
            shutil.copy(SUMMARY, directory / SUMMARY.name)
            return directory

        def replace(line):
            return lines[:at] + [line] + lines[at + 1:]

        cases = {
            "committed": copy("committed", lines),
            "added row": copy("added", lines + [joined(added)]),
            "changed row": copy("changed", replace(joined(moved))),
            "changed value": copy("revalued", replace(joined(revalued))),
            "known row removed": copy(
                "removed",
                [line for line in lines if triple(fields(line)) != cls.REMOVED]),
        }
        rewritten = cases["rewritten"] = base / "rewritten"
        rewritten.mkdir()
        with redirect_stdout(io.StringIO()):
            cls.generator.export_sssom(rewritten / COMMITTED.name)
            cls.generator.export_summary(rewritten / SUMMARY.name)

        cls.results = {name: _run_check(directory)
                       for name, directory in cases.items()}
        cls.results["listed but produced"] = _run_check(
            cases["committed"], gsm.KNOWN_UNDERIVABLE | {cls.regenerable})
        cls.shared = len(lines) - len(gsm.KNOWN_UNDERIVABLE)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    @staticmethod
    def _listed(rows):
        """`rows` as the check prints a list of them, in its order."""
        return "".join(f"      {s}  --{p}->  {o}\n" for s, p, o in sorted(rows))

    def test_the_committed_table_passes_and_names_the_gap(self):
        """The state of main, and the control for the cases below: each
        fails for the one change made to its copy."""
        code, out = self.results["committed"]
        self.assertEqual(code, 0, out)
        self.assertIn(
            f"✓ The committed mapping regenerates apart from the "
            f"{len(gsm.KNOWN_UNDERIVABLE)} row(s) KNOWN_UNDERIVABLE lists, "
            "and the summary regenerates exactly.", out)
        self.assertIn(self._listed(gsm.KNOWN_UNDERIVABLE), out)
        self.assertIn(f"The {self.shared} row(s) both files carry agree on",
                      out)

    def test_an_added_row_fails_and_is_named(self):
        code, out = self.results["added row"]
        self.assertEqual(code, 1, out)
        self.assertIn("✗ The committed mapping does not regenerate from its "
                      "inputs.", out)
        self.assertIn("1 row(s) in the committed file that regeneration does "
                      "not produce and KNOWN_UNDERIVABLE does not list:\n"
                      + self._listed([self.added]), out)

    def test_a_changed_row_fails_and_both_halves_are_named(self):
        """The row as changed is one regeneration does not produce, and the
        row as it was is one regeneration produces that the copy lacks."""
        code, out = self.results["changed row"]
        self.assertEqual(code, 1, out)
        self.assertIn("1 row(s) in the committed file that regeneration does "
                      "not produce and KNOWN_UNDERIVABLE does not list:\n"
                      + self._listed([self.moved]), out)
        self.assertIn("1 row(s) regeneration produces that the committed "
                      "file lacks:\n" + self._listed([self.regenerable]), out)

    def test_a_changed_value_fails_beside_the_accepted_gap(self):
        """Accepting the gap must hide nothing else: this copy carries every
        KNOWN_UNDERIVABLE row and differs in one value."""
        code, out = self.results["changed value"]
        self.assertEqual(code, 1, out)
        column, now, was = self.revalued
        s, p, o = self.regenerable
        self.assertIn(f"1 value(s) differ on the {self.shared} row(s) both "
                      f"files carry:\n      {s}  --{p}->  {o}  {column}: "
                      f"committed {now!r}, regenerated {was!r}\n", out)
        self.assertIn(self._listed(gsm.KNOWN_UNDERIVABLE), out)
        self.assertNotIn("does not carry", out)

    def test_a_removed_known_row_is_reported(self):
        """A curated row deleted from the table fails the check by name,
        and the rest of the gap is still accepted and listed. Nothing else
        differs, so the headline is the gap's, not the mapping's."""
        code, out = self.results["known row removed"]
        self.assertEqual(code, 1, out)
        self.assertIn("✗ The rows regeneration does not produce are not "
                      "exactly the ones KNOWN_UNDERIVABLE lists.", out)
        self.assertIn("1 row(s) KNOWN_UNDERIVABLE lists that the committed "
                      "file does not carry:\n" + self._listed([self.REMOVED]),
                      out)
        self.assertIn("Restore their lines from git", out)
        rest = gsm.KNOWN_UNDERIVABLE - {self.REMOVED}
        self.assertIn(f"{len(rest)} row(s) in the committed file that "
                      "regeneration does not produce, listed with their "
                      "reasons in KNOWN_UNDERIVABLE", out)
        self.assertIn(self._listed(rest), out)
        self.assertNotIn("committed mapping does not regenerate", out)
        self.assertNotIn("(#234)", out)

    def test_a_table_the_generator_rewrote_fails_on_every_known_row(self):
        """#3967. What `make gen-sssom-all` wrote after a schema edit until
        it stopped running the structural target, and what `make
        gen-sssom-structural` still writes. It regenerates exactly, so the
        check fails on the curated rows it dropped alone, and names each."""
        code, out = self.results["rewritten"]
        self.assertEqual(code, 1, out)
        self.assertIn(f"{len(gsm.KNOWN_UNDERIVABLE)} row(s) KNOWN_UNDERIVABLE "
                      "lists that the committed file does not carry:\n"
                      + self._listed(gsm.KNOWN_UNDERIVABLE), out)
        self.assertIn("a table the generator rewrote lacks them (#3967)", out)
        self.assertIn(f"The {self.shared} row(s) both files carry agree on",
                      out)
        self.assertNotIn("committed mapping does not regenerate", out)
        self.assertIn("\n  The summary regenerates exactly.\n", out)
        self.assertNotIn("rather than the mapping beside it", out)

    def test_a_listed_row_regeneration_produces_fails(self):
        """A row the set lists that regeneration produces is no longer a
        gap, and the drift test above fails on it too: the set must shrink
        as #294 makes rows derivable."""
        code, out = self.results["listed but produced"]
        self.assertEqual(code, 1, out)
        self.assertIn("✗ The rows regeneration does not produce are not "
                      "exactly the ones KNOWN_UNDERIVABLE lists.", out)
        self.assertIn("1 row(s) KNOWN_UNDERIVABLE lists that regeneration now "
                      "produces:\n" + self._listed([self.regenerable]), out)
        self.assertIn("take them out of KNOWN_UNDERIVABLE (#294)", out)


@unittest.skipUnless(COMMITTED.exists() and SUMMARY.exists(),
                     "structural mapping not present")
class TestTheCheckDoesWhatItsStatementSays(unittest.TestCase):
    """#4076. CHECK_STATEMENT is the one statement of what `--check`
    compares: `run_check`'s docstring ends with it and `--help` prints it
    (`TestTheCheckIsStatedOnce`). These cases hold the check to it.

    Descriptions written apart from the check were found wrong twice, first
    saying it compared more than it does (#4050) and then less (#4076), and
    the test that guarded them asked only that they name certain words.
    Here each case is a copy of the committed mapping and summary, which the
    check passes and in which no triple is repeated, changed in one way and
    checked by `run_check` with KNOWN_UNDERIVABLE as it stands:

    - the value in each column, alone, of four rows, two that regeneration
      produces and two KNOWN_UNDERIVABLE rows (one class-level, one naming
      a slot), against the verdict EDIT_VERDICTS gives that column on that
      kind of row, which is the table the statement prints. The table is
      for a change that leaves every other value the csv module reads as
      it was, so each copy is read back as the check reads it and must
      differ from the committed mapping in that one value; and each changed
      triple must be named, the new one as a row KNOWN_UNDERIVABLE does not
      list and the old one as missing;
    - a triple repeated: by a row with other structural values before the
      row it repeats and after it, and by an exact copy;
    - lines that are not rows (a # line before the header and after it,
      and an empty line), and a value in double quotes;
    - the summary's line endings (CRLF, and CR), and its text: its first
      character, its last character that is not whitespace, and a space
      before a line ending;
    - no mapping, no summary, a mapping without each column the statement
      names, and a mapping or a summary in UTF-16.

    What the statement says of the four ways a triple fails, and of the
    accepted rows being named, is `TestTheCheckAcceptsExactlyTheKnownGap`'s.
    Its sentences are not parsed: a case stands behind each, so a change to
    what the check does fails here, but a sentence reworded to say something
    else is caught only by review.
    """

    #: What a value changed by this test has appended to it.
    CHANGE = " (changed by this test)"

    @staticmethod
    def _outcome(directory):
        """`_run_check` on `directory`, or `(None, the error)` when it raises
        ValueError, so that a copy the check cannot read fails the case it
        belongs to rather than every case in the class."""
        try:
            return _run_check(directory)
        except ValueError as error:
            return None, f"{type(error).__name__}: {error}"

    @classmethod
    def setUpClass(cls):
        import tempfile

        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        header, *lines = COMMITTED.read_text(encoding="utf-8").splitlines(
            keepends=True)
        names = cls.names = header.rstrip("\n").split("\t")
        summary = SUMMARY.read_bytes()

        def fields(line):
            return line.rstrip("\n").split("\t")

        def joined(row):
            return "\t".join(row) + "\n"

        def triple(line):
            row = fields(line)
            return tuple(row[names.index(c)] for c in gsm.TRIPLE)

        def changed(line, columns):
            row = fields(line)
            for c in columns:
                row[names.index(c)] += cls.CHANGE
            return joined(row)

        def mapping(at, *replacement):
            """The committed mapping with `lines[at]` replaced by the lines
            `replacement`."""
            return header + "".join(lines[:at] + list(replacement)
                                    + lines[at + 1:])

        def copy(name, text=None, summary_bytes=None):
            """A directory with `text` as its mapping (bytes as they are, a
            string in UTF-8) and `summary_bytes` as its summary, each the
            committed one's when None and absent when False."""
            directory = base / name
            directory.mkdir()
            if text is not False:
                text = header + "".join(lines) if text is None else text
                (directory / COMMITTED.name).write_bytes(
                    text if isinstance(text, bytes) else text.encode("utf-8"))
            if summary_bytes is not False:
                (directory / SUMMARY.name).write_bytes(
                    summary if summary_bytes is None else summary_bytes)
            return directory

        # The statement's table is for a mapping in which no triple is
        # repeated; the committed one is that mapping.
        cls.repeated = len(lines) - len({triple(line) for line in lines})
        # Each row as the check reads it: the values the table's changes
        # are to (#4076).
        read = gsm._read_sssom(COMMITTED, gsm.TRIPLE)

        def values_changed(path):
            """The (row, column) of every value the check reads from `path`
            that differs from the committed mapping's, and whether it reads
            the same number of rows."""
            rows_read = gsm._read_sssom(path, gsm.TRIPLE)
            return len(rows_read) == len(read), sorted(
                (i, c) for i, (was, now) in enumerate(zip(read, rows_read))
                for c in was.keys() | now.keys() if was.get(c) != now.get(c))

        produced = [i for i, line in enumerate(lines)
                    if triple(line) not in gsm.KNOWN_UNDERIVABLE]
        listed = [i for i, line in enumerate(lines)
                  if triple(line) in gsm.KNOWN_UNDERIVABLE]
        rows = {"produced": (produced[0], produced[-1]),
                "known": (next(i for i in listed
                               if "/" not in triple(lines[i])[0]),
                          next(i for i in listed
                               if "/" in triple(lines[i])[0]))}
        cls.edits, cls.read_back = {}, {}
        for kind, at_rows in rows.items():
            for at in at_rows:
                for n, column in enumerate(names):
                    directory = copy(f"{kind}-{at}-{n}",
                                     mapping(at, changed(lines[at], [column])))
                    key = kind, triple(lines[at]), column
                    cls.edits[key] = cls._outcome(directory)
                    cls.read_back[key] = (
                        values_changed(directory / COMMITTED.name),
                        (True, [(at, column)]))

        at = produced[0]
        other = changed(lines[at], gsm.STRUCTURAL_COLUMNS)
        quoted = fields(lines[at])
        first = names.index(gsm.STRUCTURAL_COLUMNS[0])
        quoted[first] = f'"{quoted[first]}"'
        last = len(summary.rstrip()) - 1
        assert summary[:1] != b"x" and summary[last:last + 1] != b"x"
        added = "# a line this test adds\n"
        cases = {
            "unchanged": copy("unchanged"),
            "repeated, other values before": copy(
                "repeated-before", mapping(at, other, lines[at])),
            "repeated, other values after": copy(
                "repeated-after", mapping(at, lines[at], other)),
            "repeated exactly": copy(
                "repeated-exactly", mapping(at, lines[at], lines[at])),
            "a # line before the header": copy(
                "hash-before", added + header + "".join(lines)),
            "a # line after the header": copy(
                "hash-after", header + added + "".join(lines)),
            "an empty line": copy("empty-line", mapping(at, lines[at], "\n")),
            "a value in double quotes": copy(
                "quoted", mapping(at, joined(quoted))),
            "summary with CRLF line endings": copy(
                "crlf", summary_bytes=summary.replace(b"\n", b"\r\n")),
            "summary with CR line endings": copy(
                "cr", summary_bytes=summary.replace(b"\n", b"\r")),
            "summary's first character changed": copy(
                "first", summary_bytes=b"x" + summary[1:]),
            "summary's last character changed": copy(
                "last",
                summary_bytes=summary[:last] + b"x" + summary[last + 1:]),
            "summary with a space before a line ending": copy(
                "space", summary_bytes=summary.replace(b"\n", b" \n", 1)),
            "no mapping": copy("no-mapping", text=False),
            "no summary": copy("no-summary", summary_bytes=False),
            "a mapping that is not UTF-8": copy(
                "utf16-mapping", (header + "".join(lines)).encode("utf-16")),
            "a summary that is not UTF-8": copy(
                "utf16-summary",
                summary_bytes=summary.decode("utf-8").encode("utf-16")),
        }
        cls.results = {name: cls._outcome(directory)
                       for name, directory in cases.items()}

        # A mapping without each column the statement names.
        cls.errors = {}
        for column in gsm.TRIPLE + gsm.STRUCTURAL_COLUMNS:
            gone = names.index(column)
            text = "".join(
                joined([f for i, f in enumerate(fields(line)) if i != gone])
                for line in [header, *lines])
            cls.errors[column] = cls._outcome(copy(f"without-{gone}", text))
        cls.shared = len(lines) - len(gsm.KNOWN_UNDERIVABLE)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    @staticmethod
    def _verdict(column, kind):
        """The verdict the table the statement prints, EDIT_VERDICTS, gives a
        change to `column` on a row of `kind`."""
        named = {c: entry for entry in gsm.EDIT_VERDICTS if entry[0]
                 for c in entry[0]}
        _, produced, known = named.get(column) or next(
            entry for entry in gsm.EDIT_VERDICTS if entry[0] is None)
        return produced if kind == "produced" else known

    def _assert_passes(self, case):
        code, out = self.results[case]
        self.assertEqual(code, 0, out)
        self.assertIn("✓ The committed mapping regenerates apart from the "
                      f"{len(gsm.KNOWN_UNDERIVABLE)} row(s)", out)
        self.assertIn(f"The {self.shared} row(s) both files carry agree on",
                      out)

    def test_the_unchanged_copy_passes(self):
        """The control: every other case is this copy changed in one way."""
        self._assert_passes("unchanged")

    def test_each_column_has_one_verdict(self):
        """The table names each column of the mapping at most once and only
        columns it has, and leaves some to `any other column`, so it gives
        every column one verdict on each kind of row."""
        named = [c for columns, _, _ in gsm.EDIT_VERDICTS if columns
                 for c in columns]
        self.assertEqual(len(named), len(set(named)), "a column named twice")
        self.assertLessEqual(set(named), set(self.names),
                             "the table names a column the mapping lacks")
        self.assertEqual([columns for columns, _, _ in gsm.EDIT_VERDICTS]
                         .count(None), 1)
        self.assertTrue(set(self.names) - set(named),
                        "`any other column` stands for no column")
        for _, produced, known in gsm.EDIT_VERDICTS:
            self.assertLessEqual({produced, known}, {"fails", "passes"})

    def test_each_changed_value_has_the_verdict_the_statement_prints(self):
        """Every column, on each of the four rows, against the verdict
        EDIT_VERDICTS gives it there. A check that compared more or less
        than the table says fails here, and so does a table changed without
        the check."""
        self.assertEqual(len(self.edits), 4 * len(self.names))
        for (kind, row, column), (code, out) in self.edits.items():
            verdict = self._verdict(column, kind)
            with self.subTest(row=row, column=column, verdict=verdict):
                self.assertEqual(code, {"fails": 1, "passes": 0}[verdict],
                                 out)

    def test_each_change_is_the_kind_the_table_is_for(self):
        """The table is for a mapping with no triple repeated, changed in
        one value and in no other value the csv module reads. A copy whose
        change moved what else is read would test something the table does
        not claim, so each is read back with the check's own reader."""
        self.assertEqual(self.repeated, 0, "a triple is repeated")
        self.assertEqual(len(self.read_back), len(self.edits))
        for (kind, row, column), (found, wanted) in self.read_back.items():
            with self.subTest(row=row, column=column):
                self.assertEqual(found, wanted)

    def test_a_changed_triple_is_named_new_and_old(self):
        """What the statement says a changed triple fails as: the new triple
        as one the mapping carries that regeneration does not produce and
        KNOWN_UNDERIVABLE does not list, and the old one as missing, which on
        a KNOWN_UNDERIVABLE row is a listed triple the mapping lacks (#4076)
        and on a row regeneration produces is one it produces that the
        mapping lacks."""
        listed = TestTheCheckAcceptsExactlyTheKnownGap._listed
        missing = {
            "known": "1 row(s) KNOWN_UNDERIVABLE lists that the committed "
                     "file does not carry:\n",
            "produced": "1 row(s) regeneration produces that the committed "
                        "file lacks:\n",
        }
        cases = [(kind, row, column) for kind, row, column in self.edits
                 if column in gsm.TRIPLE]
        self.assertEqual(len(cases), 4 * len(gsm.TRIPLE))
        for kind, row, column in cases:
            code, out = self.edits[kind, row, column]
            new = tuple(value + self.CHANGE if name == column else value
                        for name, value in zip(gsm.TRIPLE, row))
            with self.subTest(row=row, column=column):
                self.assertEqual(code, 1, out)
                self.assertIn(
                    "1 row(s) in the committed file that regeneration does "
                    "not produce and KNOWN_UNDERIVABLE does not list:\n"
                    + listed([new]), out)
                self.assertIn(missing[kind] + listed([row]), out)

    def test_a_repeated_triple_is_not_seen(self):
        """The rows are a set, and the structural columns are read from the
        last row that carries a triple: other values before the row they
        repeat pass, and the same row after it fails on each of them."""
        for case in ("repeated exactly", "repeated, other values before"):
            with self.subTest(case=case):
                self._assert_passes(case)
        code, out = self.results["repeated, other values after"]
        self.assertEqual(code, 1, out)
        self.assertIn(f"{len(gsm.STRUCTURAL_COLUMNS)} value(s) differ on the "
                      f"{self.shared} row(s) both files carry", out)

    def test_lines_that_are_not_rows_and_quotes_are_not_compared(self):
        for case in ("a # line before the header", "a # line after the header",
                     "an empty line", "a value in double quotes"):
            with self.subTest(case=case):
                self._assert_passes(case)

    def test_the_summary_is_compared_whole_except_its_line_endings(self):
        for case in ("summary with CRLF line endings",
                     "summary with CR line endings"):
            with self.subTest(case=case):
                self._assert_passes(case)
        for case in ("summary's first character changed",
                     "summary's last character changed",
                     "summary with a space before a line ending"):
            code, out = self.results[case]
            with self.subTest(case=case):
                self.assertEqual(code, 1, out)
                self.assertIn("✗ The committed summary does not regenerate",
                              out)

    def test_a_missing_mapping_or_summary_fails(self):
        code, out = self.results["no mapping"]
        self.assertEqual(code, 1, out)
        self.assertIn("✗ No committed mapping at", out)
        code, out = self.results["no summary"]
        self.assertEqual(code, 1, out)
        self.assertIn("✗ No committed summary at", out)

    def test_a_mapping_without_a_column_it_names_is_an_error_naming_it(self):
        """An error, not an exit status: `_outcome` gives None for one."""
        for column, (code, out) in self.errors.items():
            with self.subTest(column=column):
                self.assertIsNone(code, out)
                self.assertIn(f"no {column} column", out)

    def test_a_file_that_is_not_utf8_is_an_error(self):
        for case in ("a mapping that is not UTF-8",
                     "a summary that is not UTF-8"):
            code, out = self.results[case]
            with self.subTest(case=case):
                self.assertIsNone(code, out)
                self.assertIn("UnicodeDecodeError: 'utf-8' codec", out)


class TestTheAggregateTargetsLeaveTheStructuralTable(unittest.TestCase):
    """#3967. `make gen-sssom-all` ran `gen-sssom-structural`, whose rule
    rewrites the table whenever the merged schema, the RO-Crate example or
    the generator is newer than it, so the documented aggregate run after a
    schema edit dropped the KNOWN_UNDERIVABLE rows; `make clean-sssom`
    deleted the table outright.

    Read from `make -n`, which runs no recipe, with every input of the
    structural rule marked new (`-W`), so a dependency on that rule by any
    route prints its recipe. `RUN=false` keeps any expansion of `$(RUN)`
    from reaching an environment, as the onboarding test's dry runs do.
    """

    #: The structural rule's prerequisites, as the Makefile names them.
    INPUTS = ("src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
              "data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json",
              "src/semantic_exchange/generate_structural_mapping.py")

    def _dry_run(self, target):
        import shutil
        if shutil.which("make") is None:
            self.skipTest("make is not installed")
        what_if = [arg for path in self.INPUTS for arg in ("-W", path)]
        result = subprocess.run(
            ["make", "-n", "--no-print-directory", *what_if, target,
             "RUN=false"],
            cwd=REPO, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_gen_sssom_all_does_not_rewrite_the_structural_table(self):
        out = self._dry_run("gen-sssom-all")
        self.assertIn("generate_comprehensive_sssom.py", out,
                      "the dry run did not reach the comprehensive rules")
        self.assertIn("generate_comprehensive_sssom_uri.py", out)
        self.assertNotIn(SCRIPT.name, out)
        self.assertNotIn(COMMITTED.name, out)

    def test_gen_sssom_structural_still_rewrites_it(self):
        """Kept as an explicit target, and the control for the test above:
        with the same inputs marked new, it runs the generator."""
        out = self._dry_run("gen-sssom-structural")
        self.assertIn(f"python {SCRIPT.relative_to(REPO)}\n", out)

    def test_clean_sssom_leaves_the_structural_table(self):
        out = self._dry_run("clean-sssom")
        self.assertIn("rm -f", out)
        self.assertIn("d4d_rocrate_sssom_comprehensive.tsv", out)
        self.assertIn("d4d_rocrate_sssom_uri_comprehensive.tsv", out)
        self.assertNotIn(COMMITTED.name, out)


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


class TestKnownGap(unittest.TestCase):
    """#3968: `check_known_gap` on files small enough to read."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _file(self, name, *triples):
        p = Path(self._tmp.name) / name
        p.write_text("\t".join(gsm.TRIPLE) + "\n"
                     + "".join("\t".join(t) + "\n" for t in triples))
        return p

    def test_each_kind_of_row_lands_in_its_own_answer(self):
        """A listed row regeneration produces is `derivable` whether or not
        the committed file carries it, and is never `missing`, which would
        call it a row regeneration cannot produce. A row both files carry
        that the set does not list, which every other committed row is,
        lands in none."""
        gap, unlisted, missing = (("gap", "p", "o"), ("unlisted", "p", "o"),
                                  ("missing", "p", "o"))
        produced = ("produced", "p", "o")
        produced_only = ("produced_only", "p", "o")
        shared = ("shared", "p", "o")
        committed = self._file("committed.tsv", gap, unlisted, produced, shared)
        regenerated = self._file("regenerated.tsv", produced, produced_only,
                                 shared)
        self.assertEqual(
            gsm.check_known_gap(committed, regenerated,
                                frozenset({gap, missing, produced,
                                           produced_only})),
            ([gap], [unlisted], [missing], [produced, produced_only]))

    def test_exactly_the_listed_gap_leaves_nothing_else(self):
        known = frozenset({("a", "p", "o"), ("b", "p", "o")})
        committed = self._file("committed.tsv", *sorted(known), ("c", "p", "o"))
        regenerated = self._file("regenerated.tsv", ("c", "p", "o"))
        self.assertEqual(gsm.check_known_gap(committed, regenerated, known),
                         (sorted(known), [], [], []))


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

    A class-level row (`d4d:DataSubset`) names a class, not a slot. Its range
    is the class itself and it is not multivalued (#3388), and the class must
    be one the full or the core merged schema declares: the `Core*` classes
    live only in the core schema.
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
        cls.core_sv = SchemaView(str(
            REPO / "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"))
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
        multivalued after #382 made the slot single-valued. The class-level
        rows are checked by the test below."""
        self._assert_rows_state_the_schema(self.committed)

    def _class_row_problems(self, rows):
        """What each class-level row says that its class does not."""
        problems = []
        for r in rows:
            if "/" in r["subject_id"]:
                continue
            name = r["subject_id"][len("d4d:"):]
            if not (self.sv.get_class(name) or self.core_sv.get_class(name)):
                problems.append(f"{name}: a class in neither the full nor the "
                                "core merged schema")
            if r["d4d_subject_range"] != name:
                problems.append(f"{name}: range {r['d4d_subject_range']!r}")
            if r["subject_multivalued"] != "False":
                problems.append(
                    f"{name}: multivalued {r['subject_multivalued']!r}")
        return problems

    def test_every_committed_class_row_states_its_class(self):
        """#3388. `d4d:DataSubset` gave its parent `Dataset` as its range,
        and nothing read the column on a row without a slot."""
        self.assertTrue([r for r in self.committed if "/" not in r["subject_id"]],
                        "no class-level rows to check")
        self.assertEqual(self._class_row_problems(self.committed), [])

    def test_a_class_row_that_misstates_its_class_is_found(self):
        """The check's own controls: the `DataSubset` row as it was before
        #3388, a multivalued class row, and a class no schema declares."""
        def row(subject, rng, multivalued="False"):
            return {"subject_id": subject, "d4d_subject_range": rng,
                    "subject_multivalued": multivalued}
        self.assertEqual(
            self._class_row_problems([row("d4d:DataSubset", "Dataset")]),
            ["DataSubset: range 'Dataset'"])
        self.assertEqual(
            self._class_row_problems(
                [row("d4d:CoreDataset", "CoreDataset", "True")]),
            ["CoreDataset: multivalued 'True'"])
        self.assertEqual(
            self._class_row_problems([row("d4d:NoSuchClass", "NoSuchClass")]),
            ["NoSuchClass: a class in neither the full nor the core merged "
             "schema"])

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



class TestTheSummaryIsDescribedAsTruncated(unittest.TestCase):
    """The summary shows each justification group's first rows, not all of
    them, and the two descriptions of it say so with the counts it shows
    (#3664). A description that calls it a listing of the rows invites a
    comparison with the TSV that would miss most of them."""

    README = REPO / "data" / "semantic_exchange" / "README.md"
    DOCS = REPO / "docs" / "semantic_exchange.md"

    @classmethod
    def setUpClass(cls):
        import re
        text = SUMMARY.read_text()
        groups = [int(n) for n in re.findall(r"^## \w+ Mappings \((\d+)\)$",
                                             text, re.M)]
        cls.total = sum(groups)
        cls.shown = len(re.findall(r"^- \*\*", text, re.M))
        cls.groups = groups
        cls.more = [int(n) for n in re.findall(r"^\.\.\. and (\d+) more$",
                                               text, re.M)]

    def test_the_summary_shows_at_most_ten_rows_per_group(self):
        self.assertTrue(self.groups)
        self.assertEqual(self.shown, sum(min(n, 10) for n in self.groups))
        self.assertEqual(self.more, [n - 10 for n in self.groups if n > 10])
        self.assertLess(self.shown, self.total)

    def _row(self, path):
        for line in path.read_text().splitlines():
            if line.startswith("| `d4d_rocrate_structural_mapping_summary.md`"):
                return line
        self.fail(f"{path.name} has no row for the summary")

    def test_each_description_states_the_truncation_and_its_counts(self):
        for path in (self.README, self.DOCS):
            with self.subTest(path=path.name):
                row = self._row(path)
                self.assertNotIn("listing of the rows", row)
                self.assertIn("first 10 rows", row)
                self.assertIn(f"{self.shown} of", row)
                self.assertIn(f"{self.total}", row)


class TestTheCheckIsStatedOnce(unittest.TestCase):
    """#4050, #4076. What `--check` compares was described in five places,
    each written apart from the check, and review found them wrong twice:
    they said it failed on any difference but the accepted rows (#4050),
    then that it compared no column of those rows, whose triples it does
    compare (#4076). The test that guarded them asked only that each name
    certain words, so it passed descriptions the check contradicted.

    So it is stated once, in CHECK_STATEMENT, which is written from the
    columns the check compares (TRIPLE, STRUCTURAL_COLUMNS) and from the
    table of verdicts (EDIT_VERDICTS), and held to what the check does by
    `TestTheCheckDoesWhatItsStatementSays`. `run_check`'s docstring ends
    with it, and `--help` prints it when run as the docs say to run it. The
    README, the docs page, the analysis doc and the Makefile's help for the
    target name no column where they mention the check, and send the reader
    to `--help` instead.
    """

    README = REPO / "data" / "semantic_exchange" / "README.md"
    DOCS = REPO / "docs" / "semantic_exchange.md"
    ANALYSIS = README.with_name("STRUCTURAL_MAPPING_ANALYSIS.md")
    MAKEFILE = REPO / "Makefile"
    #: How the docs say to read the statement.
    HELP = "python src/semantic_exchange/generate_structural_mapping.py --help"
    #: What marks a paragraph as one about `make check-sssom-structural`.
    MENTION = re.compile(r"check-sssom-structural|--check\b|\b[Tt]he check\b")

    @classmethod
    def setUpClass(cls):
        columns = COMMITTED.read_text(encoding="utf-8").splitlines()[0]
        cls.columns = columns.split("\t")
        cls.named = re.compile(
            r"\b(?:" + "|".join(map(re.escape, cls.columns)) + r")\b")

    def test_help_prints_the_statement(self):
        script = REPO / self.HELP.split()[1]
        self.assertEqual(script, SCRIPT)
        result = subprocess.run([sys.executable, str(script), "--help"],
                                cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(gsm.CHECK_STATEMENT, result.stdout)

    def test_run_checks_docstring_ends_with_the_statement(self):
        self.assertTrue(gsm.run_check.__doc__.endswith(
            "\n\n" + gsm.CHECK_STATEMENT))

    def test_the_docs_name_no_column_beside_the_check_and_point_to_help(self):
        """Each paragraph of the three docs that mentions the check names no
        column of the mapping, so none can say what it compares, and each
        doc gives the command that prints the statement. The analysis doc
        said "the check requires" the class-level rows' range and
        cardinality, which only `TestRowsStateTheSchema` does (#4076)."""
        for path in (self.README, self.DOCS, self.ANALYSIS):
            paragraphs = [" ".join(block.split()) for block in
                          path.read_text(encoding="utf-8").split("\n\n")]
            about = [p for p in paragraphs if self.MENTION.search(p)]
            with self.subTest(doc=path.name):
                self.assertTrue(about, "no paragraph mentions the check")
                for paragraph in about:
                    self.assertIsNone(self.named.search(paragraph), paragraph)
                self.assertTrue(any(self.HELP in p for p in about),
                                "no paragraph about the check points to "
                                f"`{self.HELP}`")
        target = next(line for line in
                      self.MAKEFILE.read_text(encoding="utf-8").splitlines()
                      if line.startswith("check-sssom-structural:"))
        described = target.split("##", 1)[1]
        self.assertIsNone(self.named.search(described), described)
        self.assertIn("generate_structural_mapping.py --help", described)


if __name__ == "__main__":
    unittest.main()
