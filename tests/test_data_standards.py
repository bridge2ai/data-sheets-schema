"""Data standards are terms, not prose (#403).

Every record of `2026-08-07_…-generic-v3_rep1` put a data standard into free
text `conforms_to`, in four different shapes for one concept:

    Brain Imaging Data Structure (BIDS) v1.9.0
    Digital Imaging and Communications in Medicine (DICOM)
    Open mHealth
    https://www.researchobject.org/ro-crate/

None resolvable to a term, so the corpus cannot be queried for "what standards
does this follow?" — and a free string had no way into the exchange layer.

Added rather than replaced. `conforms_to` still records what the sources *say*;
`conforms_to_standard` records which standard that is.
"""

import unittest
from pathlib import Path

from linkml_runtime import SchemaView

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
CORE = ROOT / "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"

#: The standards actually seen in the corpus, which the vocabulary must cover
#: or the slot is unusable on the records that motivated it.
OBSERVED = ("DICOM", "BIDS", "OMOP_CDM", "WFDB", "OPEN_MHEALTH", "ESDS",
            "CDS", "RO_CRATE")


class TestTheVocabularyExists(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.view = SchemaView(str(FULL))
        cls.enum = cls.view.get_enum("DataStandardEnum")

    def test_the_enum_exists(self):
        self.assertIsNotNone(self.enum)

    def test_it_covers_every_standard_the_corpus_names(self):
        values = set(self.enum.permissible_values)
        for standard in OBSERVED:
            with self.subTest(standard=standard):
                self.assertIn(standard, values)

    def test_it_has_an_escape_hatch(self):
        """Without `OTHER` a run meeting an uncovered standard either drops the
        fact or picks a near-neighbour, and the second is an invention."""
        self.assertIn("OTHER", self.enum.permissible_values)

    def test_other_says_to_keep_the_name(self):
        text = self.enum.permissible_values["OTHER"].description
        self.assertIn("conforms_to", text)

    def test_it_warns_against_the_near_neighbour(self):
        text = self.enum.permissible_values["OTHER"].description
        self.assertIn("invention", text)


class TestItIsNotMergedIntoFormatEnum(unittest.TestCase):
    """A serialization and a data standard are different concepts. Widening
    `FormatEnum` to absorb DICOM would make `format` unanswerable."""

    @classmethod
    def setUpClass(cls):
        cls.view = SchemaView(str(FULL))

    def test_format_enum_does_not_carry_data_standards(self):
        values = set(self.view.get_enum("FormatEnum").permissible_values)
        for standard in ("DICOM", "BIDS", "OMOP_CDM", "WFDB"):
            with self.subTest(standard=standard):
                self.assertNotIn(standard, values)

    def test_the_two_enums_do_not_overlap(self):
        fmt = set(self.view.get_enum("FormatEnum").permissible_values)
        std = set(self.view.get_enum("DataStandardEnum").permissible_values)
        self.assertEqual(fmt & std, set())


class TestItReachesTheExchangeLayer(unittest.TestCase):
    """The projection failure #403 reported: a free string had no home in core,
    so the most interoperability-relevant fact about a distribution was lost."""

    @classmethod
    def setUpClass(cls):
        cls.core = SchemaView(str(CORE))

    def test_core_distribution_carries_it(self):
        slots = {s.name for s in
                 self.core.class_induced_slots("CoreDistribution")}
        self.assertIn("conforms_to_standard", slots)

    def test_core_dataset_carries_it(self):
        slots = {s.name for s in self.core.class_induced_slots("CoreDataset")}
        self.assertIn("conforms_to_standard", slots)

    def test_the_enum_resolves_from_the_core_schema(self):
        """A slot whose range is unreachable would generate but not validate."""
        self.assertIsNotNone(self.core.get_enum("DataStandardEnum"))


class TestFreeTextSurvives(unittest.TestCase):
    """Added, not replaced. The sources say things the vocabulary cannot, and
    a term-only slot would drop `ASCII File Format Guidelines for Earth Science
    Data` rather than record it."""

    @classmethod
    def setUpClass(cls):
        cls.view = SchemaView(str(FULL))
        cls.slots = {s.name: s for s in cls.view.class_induced_slots("Dataset")}

    def test_conforms_to_is_still_free_text(self):
        self.assertEqual(self.slots["conforms_to"].range, "string")

    def test_the_new_slot_is_multivalued(self):
        """A dataset commonly follows several standards — AI_READI names five."""
        self.assertTrue(self.slots["conforms_to_standard"].multivalued)

    def test_neither_is_required(self):
        for slot in ("conforms_to", "conforms_to_standard"):
            with self.subTest(slot=slot):
                self.assertFalse(self.slots[slot].required)

    def test_the_description_says_to_populate_both(self):
        text = self.slots["conforms_to_standard"].description
        self.assertIn("Populate both", text)


class TestTheGroundingGapIsNamed(unittest.TestCase):
    """No `meaning:` is asserted. Several of these standards have no stable
    ontology term this repository can verify, and inventing a CURIE that
    resolves to nothing is the failure `d4d runs identifiers` exists to find.
    """

    @classmethod
    def setUpClass(cls):
        cls.enum = SchemaView(str(FULL)).get_enum("DataStandardEnum")

    def test_no_value_asserts_an_unverified_meaning(self):
        for name, value in self.enum.permissible_values.items():
            with self.subTest(value=name):
                self.assertIsNone(value.meaning)

    def test_the_absence_is_documented_rather_than_silent(self):
        self.assertIn("No `meaning:` is asserted", self.enum.description)


BUNDLES = ROOT / "data/preprocessed/concatenated"

#: How each value is actually written in the source documents. A vocabulary
#: value is a claim that some dataset follows this standard, so it has to be
#: traceable to evidence like any other claim.
IN_SOURCES = {
    "DICOM": "DICOM",
    "BIDS": "Brain Imaging Data Structure",
    "OMOP_CDM": "OMOP",
    "WFDB": "WFDB",
    "OPEN_MHEALTH": "Open mHealth",
    "ESDS": "Earth Science Data",
    "CDS": "Clinical Dataset Structure",
    "RO_CRATE": "RO-Crate",
    "FHIR": "FHIR",
}


@unittest.skipUnless(BUNDLES.exists(), "bundles absent")
class TestEveryValueIsAttested(unittest.TestCase):
    """No value comes from model memory.

    `CDS` — "Clinical Dataset Structure v0.1.1" — was the one to check: it
    appears in a generated record, and a standard named only by a record and
    by no source would be a hallucination about to be enshrined in the schema,
    where it would look authoritative for ever. It appears on 19 lines of the
    bundles, so it is real.

    This guard matters more than it looks. Adding a plausible standard is easy
    and unfalsifiable once merged: the schema is not evidence, and nothing else
    would ever check it against a source.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = "\n".join(
            p.read_text(encoding="utf-8", errors="replace").lower()
            for p in sorted(BUNDLES.glob("*_preprocessed.txt")))

    def test_each_value_appears_in_some_bundle(self):
        for value, phrase in IN_SOURCES.items():
            with self.subTest(value=value):
                self.assertIn(phrase.lower(), self.text,
                              f"{value} is named by no source document")

    def test_every_enum_value_is_covered_by_this_check(self):
        """So a value added later cannot skip the check by not being listed."""
        enum = SchemaView(str(FULL)).get_enum("DataStandardEnum")
        unchecked = set(enum.permissible_values) - set(IN_SOURCES) - {"OTHER"}
        self.assertEqual(unchecked, set(),
                         "a vocabulary value with no attestation entry")
