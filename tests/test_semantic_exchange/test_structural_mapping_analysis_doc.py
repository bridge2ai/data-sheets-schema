"""STRUCTURAL_MAPPING_ANALYSIS.md must not drift from the file it describes.

It said "142 mappings, 100% type-compatible" while the committed structural
SSSOM had 165 rows, 20 of them flagged incompatible, and cited example rows
the file never carried (#2976). Nothing compared the prose with the file. It
now states no counts and points at `make check-sssom-structural`; these tests
keep it that way, and hold the few facts about the file it still states.
"""

import csv
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "data" / "semantic_exchange" / "STRUCTURAL_MAPPING_ANALYSIS.md"
MAPPING = DOC.with_name("d4d_rocrate_structural_mapping.sssom.tsv")


def _committed_rows():
    return list(csv.DictReader(
        [l for l in MAPPING.read_text(encoding="utf-8").splitlines()
         if not l.startswith("#")],
        delimiter="\t"))


@unittest.skipUnless(DOC.exists() and MAPPING.exists(),
                     "structural mapping or its analysis not present")
class TestTheAnalysisDocDoesNotDrift(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.doc = DOC.read_text(encoding="utf-8")
        cls.rows = _committed_rows()

    def test_it_states_no_counts(self):
        """A count in prose is a count nothing regenerates. The old metrics
        table ("| **Total mappings** | 142 | 100% |") is the shape that was
        there. This is a heuristic, not a proof: it fails on a percentage,
        the phrase "total mappings", a table cell that is only a number, a
        number directly before "mappings" or "rows", and any integer of two
        or more digits that is not an issue reference (`#2936`) or part of a
        decimal (`0.85`), so "20 of 165" and "10 hand-written rows" fail. It
        does not catch a single-digit count ("5 are flagged") or a number
        spelled out ("sixteen rows"); the doc legitimately carries section
        numbers and similarity thresholds, so those cannot be banned (#3395).
        """
        self.assertNotRegex(self.doc, r"\d+(\.\d+)?\s*%",
                            "the doc states a percentage")
        self.assertNotRegex(self.doc, r"(?i)total mappings",
                            "the doc states a total")
        self.assertNotRegex(self.doc, r"\|\s*\*{0,2}~?\d+\*{0,2}\s*\|",
                            "the doc has a table cell that is a number")
        self.assertNotRegex(self.doc, r"(?i)\b\d+\s+(mappings|rows)\b",
                            "the doc states a number of mappings or rows")
        self.assertNotRegex(self.doc, r"(?<![#\w.])\d{2,}(?!\d|\.\d)",
                            "the doc states a multi-digit number that is not "
                            "an issue reference or a decimal")

    def test_it_points_at_the_check_that_exists(self):
        self.assertIn("make check-sssom-structural", self.doc)
        makefile = (REPO / "Makefile").read_text(encoding="utf-8")
        self.assertRegex(makefile, r"(?m)^check-sssom-structural:")

    def test_every_row_it_cites_is_in_the_committed_file(self):
        """The old examples included `d4d:Dataset/license → license` and
        `d4d:Purpose/response → d4d:purpose`, neither ever in the file."""
        cited = set(re.findall(r"`(d4d:[A-Za-z]+/[A-Za-z_.]+)`", self.doc))
        self.assertTrue(cited, "the doc cites no row; this test checks nothing")
        subjects = {r["subject_id"] for r in self.rows}
        self.assertEqual(cited - subjects, set(),
                         "the doc cites subjects the committed file lacks")

    def test_what_it_says_about_the_committed_file_holds(self):
        """Two statements about the file's current content. If either stops
        being true, the doc is what needs changing; if the doc drops one, drop
        its check here."""
        prose = " ".join(self.doc.split())
        self.assertIn("No row in the committed file comes from it.", prose)
        self.assertEqual(
            [r["subject_id"] for r in self.rows
             if r["structural_notes"].startswith("Module mapping")], [],
            "the doc says the module strategy emits nothing")
        self.assertIn("the only composition rows go through `anomalies`", prose)
        composition = [r for r in self.rows if r["composition_path"]]
        self.assertTrue(composition)
        self.assertEqual(
            {r["composition_path"].split(".", 1)[0] for r in composition},
            {"anomalies"})
        self.assertEqual({r["type_compatible"] for r in composition},
                         {"False"},
                         "the doc says every composition row is flagged")

    def test_the_composition_depth_it_states_holds(self):
        """The doc once said the strategy follows "every dotted path"; the
        generator goes one level below the slot and stops (#3381)."""
        prose = " ".join(self.doc.split())
        self.assertIn("a path never has more than one dot", prose)
        composition = [r["composition_path"] for r in self.rows
                       if r["composition_path"]]
        self.assertTrue(composition)
        self.assertEqual([p for p in composition if p.count(".") > 1], [],
                         "the doc says no composition path has two dots")

    def test_the_cardinality_rule_it_states_holds(self):
        """The doc once said a composition row's range *and cardinality* are
        the end of the path's. The generator takes the range from the last
        segment but marks the row multivalued when any segment is
        (`D4DSchemaParser.resolve_path`), which is why every committed
        `anomalies.*` row is multivalued and flagged (#3393)."""
        import io
        import sys
        from contextlib import redirect_stdout
        prose = " ".join(self.doc.split())
        self.assertNotIn("range and cardinality are those the schema gives "
                         "the end of the path", prose)
        self.assertIn("the row is multivalued when *any* segment of the path "
                      "is", prose)
        row = {r["subject_id"]: r for r in self.rows}.get(
            "d4d:Dataset/anomalies.name")
        self.assertIsNotNone(row, "the doc's example row is gone")
        self.assertEqual((row["d4d_subject_range"], row["subject_multivalued"]),
                         ("string", "True"))
        self.assertEqual(
            {r["subject_multivalued"] for r in self.rows
             if r["composition_path"]}, {"True"},
            "the doc says every composition row is multivalued via anomalies")
        schema = (REPO / "src" / "data_sheets_schema" / "schema"
                  / "data_sheets_schema_all.yaml")
        sys.path.insert(0, str(REPO / "src" / "semantic_exchange"))
        from generate_structural_mapping import D4DSchemaParser  # noqa: E402
        with redirect_stdout(io.StringIO()):
            parser = D4DSchemaParser(schema)
        self.assertFalse(parser.classes["DataAnomaly"].attributes["name"]
                         .multivalued,
                         "the doc says a name is one string per anomaly")
        self.assertTrue(parser.classes["Dataset"].attributes["anomalies"]
                        .multivalued, "the doc says `anomalies` is a list")
        self.assertTrue(parser.resolve_path("Dataset", "anomalies.name")
                        .multivalued)

    def test_it_does_not_claim_the_class_level_rows_are_checked(self):
        """TestRowsStateTheSchema checks only rows whose subject names a slot;
        the doc once said every hand-written row's range and cardinality were
        checked, class-level rows included (#3380)."""
        prose = " ".join(self.doc.split())
        self.assertIn("The class-level rows are not checked", prose)
        self.assertNotIn("Their range and cardinality columns are still "
                         "checked", prose)
        self.assertTrue([r for r in self.rows if "/" not in r["subject_id"]],
                        "the doc describes class-level rows the file lacks")


if __name__ == "__main__":
    unittest.main()
