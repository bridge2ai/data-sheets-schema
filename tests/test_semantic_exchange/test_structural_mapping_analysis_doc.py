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
        table ("| **Total mappings** | 142 | 100% |") is the shape caught."""
        self.assertNotRegex(self.doc, r"\d+(\.\d+)?\s*%",
                            "the doc states a percentage")
        self.assertNotRegex(self.doc, r"(?i)total mappings",
                            "the doc states a total")
        self.assertNotRegex(self.doc, r"\|\s*\*{0,2}~?\d+\*{0,2}\s*\|",
                            "the doc has a table cell that is a number")
        self.assertNotRegex(self.doc, r"(?i)\b\d+\s+(mappings|rows)\b",
                            "the doc states a number of mappings or rows")

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


if __name__ == "__main__":
    unittest.main()
