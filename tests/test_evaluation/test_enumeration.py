"""Enumeration depth, and refusing to report grounding that was not measured (#332).

The module exists because rubric20 cannot see enumeration at all — the judge
receives only the D4D record, never the sources, so any enumeration question it
asked could score a count, and a count rewards invention.

The load-bearing behaviour here is the refusal. Most enumerated content is prose
with nothing verbatim to check: two thirds of items across the 25 current records
carry no identifying label, and on AI_READI 74 of 77 `variables` items and 9 of 9
`known_limitations` items carry no checkable anchor either. A grounding rate
computed over the remainder would read ~100% while examining 4% of the content.

So `grounding` raises where nothing was checkable, and `coverage` is the number
that has to be read first. `0.0` would read as "invented" and `1.0` as "fully
grounded"; the measurement is absent, not zero.
"""

import glob
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.enumeration import (NothingCheckable, SlotEnumeration,
                                            anchors_in, measure, measure_slot,
                                            total_depth)

REPO = Path(__file__).resolve().parents[2]


class TestAnchors(unittest.TestCase):
    """What counts as checkable, and — more importantly — what does not."""

    def test_identifiers_are_anchors(self):
        for text, expected in (
                ("see 10.13026/249v-w155 for details", "10.13026/249v-w155"),
                ("Aaron Y. Lee, MD (ORCID 0000-0002-7452-1648)", "0000-0002-7452-1648"),
                ("cell line RRID:CVCL_0419", "RRID:CVCL_0419"),
                ("hosted at https://physionet.org/content/b2ai-voice/",
                 "https://physionet.org/content/b2ai-voice/"),
                ("grant OT2OD032742 from NIH", "OT2OD032742")):
            with self.subTest(text=text):
                self.assertIn(expected, anchors_in(text))

    def test_prose_yields_no_anchors(self):
        """The whole reason coverage is reported.

        A sentence of ordinary English is unverifiable by substring matching:
        every word appears somewhere in a 200 KB bundle, so matching them would
        drive every rate to 100% and make the arms indistinguishable.
        """
        self.assertEqual(
            anchors_in("Cross-sectional design with a single study visit per "
                       "participant, limiting longitudinal analysis."), set())

    def test_short_tokens_are_not_anchors(self):
        """`v2` or `p53` appear by chance; they are not evidence."""
        self.assertEqual(anchors_in("uses v2 and p53"), set())

    def test_the_length_floor_lives_in_one_place(self):
        """A five-character token qualifies and a four-character one does not.

        Pinned because an earlier version carried a second `MIN_ANCHOR_CHARS`
        check that no input could reach — `\\b` keeps trailing punctuation out
        of the match, so the strip never shortens one. Two floors, one of them
        dead, is how a relaxed quantifier later goes unnoticed.
        """
        self.assertEqual(anchors_in("id ab123 end"), {"ab123"})
        self.assertEqual(anchors_in("id ab12 end"), set())

    def test_trailing_sentence_punctuation_is_stripped(self):
        """`10.13026/xyz.` and `10.13026/xyz` are the same anchor."""
        self.assertEqual(anchors_in("published at 10.13026/xyz."),
                         {"10.13026/xyz"})

    def test_a_bare_word_is_not_an_anchor(self):
        """An anchor must mix letters and digits, or match an identifier
        pattern. Otherwise `participants` would be an anchor."""
        self.assertEqual(anchors_in("participants demographics recruitment"), set())


class TestCoverageAndGrounding(unittest.TestCase):

    def test_grounding_raises_when_nothing_was_checkable(self):
        """`0.0` reads as invented and `1.0` as verified. Neither is supported
        by an item nobody could check."""
        measured = measure_slot("known_limitations",
                                [{"description": "Cross-sectional design only."}],
                                source="whatever the bundle says")
        self.assertEqual(measured.items, 1)
        self.assertEqual(measured.coverage, 0.0)
        with self.assertRaises(NothingCheckable):
            measured.grounding

    def test_the_refusal_names_the_slot_and_says_it_is_unmeasured(self):
        measured = measure_slot("purposes", [{"description": "To share data."}], "")
        with self.assertRaises(NothingCheckable) as caught:
            measured.grounding
        message = str(caught.exception)
        self.assertIn("purposes", message)
        self.assertIn("unmeasured rather than zero", message)

    def test_coverage_separates_checkable_items_from_the_rest(self):
        measured = measure_slot("creators", [
            {"description": "Aaron Y. Lee, MD (ORCID 0000-0002-7452-1648)"},
            {"description": "A researcher with no identifier given"},
            {"description": "Another with none either"},
        ], source="aaron y. lee, md (orcid 0000-0002-7452-1648)")
        self.assertEqual(measured.items, 3)
        self.assertEqual(measured.checkable_items, 1)
        self.assertAlmostEqual(measured.coverage, 1 / 3)
        self.assertEqual(measured.grounding, 1.0)

    def test_an_absent_anchor_lowers_grounding(self):
        """The measure has to be able to say no, or it says nothing."""
        measured = measure_slot("external_resources", [
            {"description": "see 10.13026/real-one"},
            {"description": "see 10.99999/not-in-the-source"},
        ], source="the bundle mentions 10.13026/real-one and nothing else")
        self.assertEqual(measured.anchors, 2)
        self.assertEqual(measured.grounding, 0.5)

    def test_zero_items_is_not_an_error(self):
        measured = measure_slot("resources", None, "")
        self.assertEqual(measured.items, 0)
        self.assertEqual(measured.coverage, 0.0)


class TestNestedText(unittest.TestCase):
    """The identity sits inside prose, not in a `name` field."""

    def test_an_anchor_nested_below_the_item_is_found(self):
        """`file_collections` puts identifiers a level down. A top-level-only
        scan would report those items as unmeasurable."""
        measured = measure_slot("file_collections", [
            {"title": "imaging", "conforms_to": {"url": "https://example.org/spec-v1"}},
        ], source="conforms to https://example.org/spec-v1")
        self.assertEqual(measured.checkable_items, 1)
        self.assertEqual(measured.grounding, 1.0)

    def test_a_scalar_item_is_measured(self):
        measured = measure_slot("keywords", ["OT2OD032742", "voice"],
                                source="grant ot2od032742")
        self.assertEqual(measured.items, 2)
        self.assertEqual(measured.checkable_items, 1)


class TestMintedIdentifiers(unittest.TestCase):
    """A record's own `id` cannot be in the source (#335).

    Counting it as an anchor that was not found measures identifier style rather
    than fidelity, and penalises whichever arm gives things stable identifiers.
    """

    def test_an_id_is_not_an_anchor(self):
        measured = measure_slot("creators", [
            {"id": "CM4AI_creator_release_authors",
             "description": "A researcher with no identifier given"},
        ], source="nothing here matches")
        self.assertEqual(measured.anchors, 0)
        self.assertEqual(measured.checkable_items, 0)

    def test_excluding_the_id_does_not_hide_a_real_anchor_beside_it(self):
        """Only the `id` key is dropped, not the item."""
        measured = measure_slot("creators", [
            {"id": "aireadi:creator_lee", "description": "ORCID 0000-0002-7452-1648"},
        ], source="orcid 0000-0002-7452-1648")
        self.assertEqual(measured.anchors, 1)
        self.assertEqual(measured.grounding, 1.0)

    def test_a_minted_id_nested_deeper_is_also_excluded(self):
        measured = measure_slot("file_collections", [
            {"title": "imaging", "conforms_to": {"id": "local:spec-9000"}},
        ], source="")
        self.assertEqual(measured.anchors, 0)


class TestUrlAnchorsAreSeparable(unittest.TestCase):
    """The arms differ on URL enrichment, not on fidelity (#336).

    A record supplying `https://www.emory.edu/` for a source that says "Emory
    University" is contributing world knowledge; substring matching scores that
    identically to an invented link. Splitting the counts makes the confound
    visible rather than burying it in one rate.
    """

    def test_urls_are_counted_separately_and_also_in_the_total(self):
        measured = measure_slot("creators", [
            {"description": "Emory, https://www.emory.edu/, ORCID 0000-0002-7452-1648"},
        ], source="orcid 0000-0002-7452-1648")
        self.assertEqual(measured.anchors, 2)
        self.assertEqual(measured.url_anchors, 1)
        self.assertEqual(measured.url_anchors_found, 0)
        self.assertEqual(measured.identifier_anchors, 1)
        self.assertEqual(measured.identifier_anchors_found, 1)

    def test_a_found_url_counts_as_found_in_both_places(self):
        measured = measure_slot("external_resources", [
            {"description": "see https://physionet.org/content/b2ai-voice/"},
        ], source="hosted at https://physionet.org/content/b2ai-voice/")
        self.assertEqual(measured.url_anchors, 1)
        self.assertEqual(measured.url_anchors_found, 1)
        self.assertEqual(measured.anchors_found, 1)

    def test_the_split_is_exhaustive(self):
        """Identifier and URL counts must partition the totals, or a reader
        subtracting one from the other gets a number that means nothing."""
        measured = measure_slot("creators", [
            {"description": "https://a.example/x and 10.1234/y and OT2OD032742"},
        ], source="10.1234/y")
        self.assertEqual(measured.identifier_anchors + measured.url_anchors,
                         measured.anchors)
        self.assertEqual(
            measured.identifier_anchors_found + measured.url_anchors_found,
            measured.anchors_found)


class TestMeasure(unittest.TestCase):

    def test_it_finds_the_list_valued_slots(self):
        record = {"title": "a string", "keywords": ["OT2OD032742"],
                  "creators": [{"description": "x"}], "instances": []}
        measured = measure(record, source="ot2od032742")
        self.assertEqual(sorted(measured), ["creators", "keywords"])
        self.assertEqual(total_depth(measured), 2)

    def test_a_named_subset_is_honoured(self):
        record = {"keywords": ["a"], "creators": [{"description": "b"}]}
        self.assertEqual(sorted(measure(record, "", slots=["creators"])), ["creators"])

    def test_matching_is_case_insensitive_on_both_sides(self):
        measured = measure_slot("keywords", ["OT2OD032742"], source="ot2od032742")
        self.assertEqual(measured.grounding, 1.0)


class TestTheLiveCorpus(unittest.TestCase):
    """Properties that must hold on real records, not just fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.records = []
        for path in sorted(glob.glob(str(
                REPO / "data" / "d4d_concatenated" / "claudecode_agent"
                / "2026-07-31*" / "*_d4d.yaml")))[:8]:
            project = Path(path).name.replace("_d4d.yaml", "")
            bundle = (REPO / "data" / "preprocessed" / "concatenated"
                      / f"{project}_preprocessed.txt")
            if bundle.exists():
                cls.records.append((yaml.safe_load(Path(path).read_text()),
                                    bundle.read_text(errors="ignore")))

    def test_there_are_records_to_measure(self):
        self.assertTrue(self.records, "no current records with bundles found")

    def test_every_rate_is_a_proportion_or_refuses(self):
        for record, bundle in self.records:
            for slot, measured in measure(record, bundle).items():
                with self.subTest(slot=slot):
                    self.assertGreaterEqual(measured.coverage, 0.0)
                    self.assertLessEqual(measured.coverage, 1.0)
                    try:
                        self.assertGreaterEqual(measured.grounding, 0.0)
                        self.assertLessEqual(measured.grounding, 1.0)
                    except NothingCheckable:
                        self.assertEqual(measured.checkable_items, 0)

    def test_coverage_is_genuinely_partial(self):
        """The premise of the whole module.

        If every item were checkable, `coverage` would be noise and `grounding`
        could be reported bare. It is not: on the real corpus a substantial
        share of enumerated items carry nothing verifiable.
        """
        items = checkable = 0
        for record, bundle in self.records:
            for measured in measure(record, bundle).values():
                items += measured.items
                checkable += measured.checkable_items
        self.assertGreater(items, 100)
        self.assertLess(checkable / items, 0.75,
                        "coverage is near-total, so this module's caution is "
                        "unnecessary and its docstring is wrong")

    def test_checkable_items_never_exceeds_items(self):
        for record, bundle in self.records:
            for slot, m in measure(record, bundle).items():
                with self.subTest(slot=slot):
                    self.assertLessEqual(m.checkable_items, m.items)
                    self.assertLessEqual(m.anchors_found, m.anchors)


if __name__ == "__main__":
    unittest.main()
