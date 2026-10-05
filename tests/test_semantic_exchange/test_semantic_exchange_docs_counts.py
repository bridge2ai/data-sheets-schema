"""docs/semantic_exchange.md's "Coverage at a glance" states what the files
hold (#4032).

Before #4032 the list said 108 rows in the "semantic SSSOM", the
property-level table #3884 retired; 156 structural rows; 112 SKOS triples;
six predicates, the sixth being "class-level alignments", which is not a
predicate; and five target namespaces. Nothing compared any of them with the
files. Here each line is read and derived from the file it counts, as
test_skos_alignment_header.py holds the TTL's own statistics block to the
TTL, and a line no pattern below reads fails, so the list cannot gain a
count that nothing checks.

Nothing here walks the corpus: the inputs are the docs page, the SKOS TTL
and the three SSSOM tables.
"""

import csv
import io
import re
import unittest
from pathlib import Path

from tests.test_semantic_exchange.test_skos_alignment_header import (
    parsed_triples,
)

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs" / "semantic_exchange.md"
EXCHANGE = REPO / "src" / "data_sheets_schema" / "semantic_exchange"
COMPREHENSIVE = (EXCHANGE / "d4d_rocrate_sssom_comprehensive.tsv",
                 EXCHANGE / "d4d_rocrate_sssom_uri_comprehensive.tsv")
STRUCTURAL = (REPO / "data" / "semantic_exchange"
              / "d4d_rocrate_structural_mapping.sssom.tsv")

#: The prefix each namespace the list names stands for.
NAMESPACE_NAMES = {"schema.org": "schema", "RAI": "rai", "EVI": "evi",
                   "DCAT": "dcat", "d4d-internal": "d4d", "rdf": "rdf"}

#: The lines of the list, each by the pattern that reads it.
LINES = {
    "comprehensive": re.compile(
        r"\*\*(\d+)\*\* rows in each comprehensive SSSOM table, "
        r"one per schema slot name"),
    "structural": re.compile(r"\*\*(\d+)\*\* rows in the structural SSSOM"),
    "triples": re.compile(
        r"\*\*(\d+)\*\* SKOS mapping triples in the alignment TTL\b.*"),
    "predicates": re.compile(r"\*\*(\d+)\*\* SKOS predicates in use: (.+)"),
    "namespaces": re.compile(r"\*\*(\d+)\*\* target namespaces: (.+)"),
}


def coverage_lines(text):
    """The bullets of the "Coverage at a glance" section, without "- "."""
    section = text.split("\n## Coverage at a glance\n", 1)[1]
    section = section.split("\n## ", 1)[0]
    return [line[2:] for line in section.splitlines() if line.startswith("- ")]


def data_rows(path):
    """A TSV table's rows: its ``#`` comment lines and header aside."""
    body = "".join(line for line in
                   path.read_text(encoding="utf-8").splitlines(keepends=True)
                   if not line.startswith("#"))
    return list(csv.DictReader(io.StringIO(body), delimiter="\t"))


class TestCoverageAtAGlanceStatesTheFiles(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.lines = coverage_lines(DOCS.read_text(encoding="utf-8"))
        cls.said = {}
        for key, pattern in LINES.items():
            found = [m for m in map(pattern.fullmatch, cls.lines) if m]
            if len(found) == 1:
                cls.said[key] = found[0]
        cls.triples = parsed_triples()

    def test_every_line_is_read_once(self):
        """A line no pattern reads is a count nothing checks; that is how
        the retired table's 108 stayed on the page."""
        self.assertTrue(self.lines)
        for line in self.lines:
            with self.subTest(line=line):
                self.assertEqual(
                    sum(bool(p.fullmatch(line)) for p in LINES.values()), 1)
        self.assertEqual(set(self.said), set(LINES))

    def test_the_comprehensive_tables(self):
        """The pair that replaced the retired "semantic SSSOM" (#3884): both
        tables have the stated number of rows. That the rows are the schema's
        slot names, one each, is TestEverySlotHasOneRow's
        (test_comprehensive_sssom.py)."""
        stated = int(self.said["comprehensive"].group(1))
        self.assertEqual({path.name: len(data_rows(path))
                          for path in COMPREHENSIVE},
                         {path.name: stated for path in COMPREHENSIVE})

    def test_the_structural_table(self):
        """The committed table, KNOWN_UNDERIVABLE rows included."""
        self.assertEqual(int(self.said["structural"].group(1)),
                         len(data_rows(STRUCTURAL)))

    def test_the_triples(self):
        """Counted by an rdflib parse, as the TTL's own statistics are."""
        self.assertEqual(int(self.said["triples"].group(1)),
                         len(self.triples))

    def test_the_predicates(self):
        """The names are the predicates the triples use, and nothing else
        is listed: "class-level alignments" was once counted as a sixth."""
        said = self.said["predicates"]
        names = re.findall(r"`(\w+)`", said.group(2))
        used = {predicate for _, predicate, _ in self.triples}
        self.assertEqual(said.group(2), ", ".join(f"`{n}`" for n in names))
        self.assertEqual(sorted(names), sorted(used))
        self.assertEqual(int(said.group(1)), len(used))

    def test_the_namespaces(self):
        """The names stand for the prefixes of the triples' targets: the
        list named five, without rdf (d4d:id's rdf:ID)."""
        said = self.said["namespaces"]
        names = [name.strip() for name in said.group(2).split(",")]
        used = {obj.split(":", 1)[0] for _, _, obj in self.triples}
        self.assertLessEqual(set(names), set(NAMESPACE_NAMES))
        self.assertEqual(sorted(NAMESPACE_NAMES[n] for n in names
                                if n in NAMESPACE_NAMES),
                         sorted(used))
        self.assertEqual(int(said.group(1)), len(used))


if __name__ == "__main__":
    unittest.main()
