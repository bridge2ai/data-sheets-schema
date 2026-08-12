"""British spellings in generated prose, but never in quoted source (#502).

From Camille Nebeker's review: standardize on American English. The trap is
that the bundles themselves contain British spellings — `licence` 13 times,
`programme` 6 — so a find-and-replace over the records would silently rewrite
what a source said, which is the one thing the provenance guard exists to
prevent.

The checker is therefore conservative in the direction of silence: a false
"quoted" merely fails to report, while a false "generated" would invite
someone to edit evidence.
"""

import unittest

from data_sheets_schema.spelling import (
    BRITISH,
    in_identifiers,
    occurrences,
)


class TestDetection(unittest.TestCase):
    def test_a_british_spelling_is_found_with_its_american_form(self):
        [occ] = occurrences({"description": "the programme ran"}, None)
        self.assertEqual((occ.word, occ.suggestion), ("programme", "program"))

    def test_the_slot_is_reported(self):
        [occ] = occurrences({"license_and_use_terms": "labelled MIT"}, None)
        self.assertEqual(occ.slot, "license_and_use_terms")

    def test_nested_values_are_reached(self):
        rec = {"creators": [{"affiliations": [{"name": "Centre for Ageing"}]}]}
        words = {o.word.lower() for o in occurrences(rec, None)}
        self.assertIn("centre", words)

    def test_american_text_is_clean(self):
        self.assertEqual(
            occurrences({"description": "the program analyzed behavior"}, None),
            [])

    def test_matching_is_whole_word(self):
        """`centres` must match; `epicentre-like` substrings must not produce
        a suggestion for a word that is not there."""
        words = {o.word.lower() for o in
                 occurrences({"a": "two centres", "b": "programmed"}, None)}
        self.assertIn("centres", words)
        self.assertNotIn("programme", words)

    def test_case_is_preserved_in_the_report(self):
        [occ] = occurrences({"description": "The Programme"}, None)
        self.assertEqual(occ.word, "Programme")
        self.assertEqual(occ.suggestion, "program")


class TestQuotedDetection(unittest.TestCase):
    SENTENCE = ("Data are released under a bespoke licence agreed with the "
                "participating sites and reviewed annually by the committee.")

    def test_text_copied_from_the_bundle_is_marked_quoted(self):
        bundle = f"Some preamble. {self.SENTENCE} Some trailing text."
        [occ] = occurrences({"description": self.SENTENCE}, bundle)
        self.assertTrue(occ.quoted)

    def test_the_same_text_is_generated_when_the_bundle_lacks_it(self):
        """The discriminating case: identical text, different verdict."""
        [occ] = occurrences({"description": self.SENTENCE},
                            "an unrelated bundle about something else")
        self.assertFalse(occ.quoted)

    def test_no_bundle_marks_nothing_quoted(self):
        """Honest for a record whose bundle cannot be identified — the caller
        learns the split was not established, rather than being told
        everything is generated."""
        [occ] = occurrences({"description": self.SENTENCE}, None)
        self.assertFalse(occ.quoted)

    def test_reflowed_text_still_matches_its_source(self):
        """A record wraps prose at a different width than its source, so a
        literal comparison would call almost everything generated."""
        wrapped = self.SENTENCE.replace(" the ", "\n     the ")
        bundle = f"preamble {self.SENTENCE} trailing"
        [occ] = occurrences({"description": wrapped}, bundle)
        self.assertTrue(occ.quoted)

    def test_case_differences_do_not_defeat_the_match(self):
        bundle = f"preamble {self.SENTENCE.upper()} trailing"
        [occ] = occurrences({"description": self.SENTENCE}, bundle)
        self.assertTrue(occ.quoted)


class TestIdentifiers(unittest.TestCase):
    def test_a_british_spelling_in_an_id_is_reported(self):
        """Structural rather than stylistic: an id is a token other records may
        key on, so it cannot be fixed by a later copy-edit. The 2026-08-11 arm
        carries `aireadi:external-training-programme`."""
        rec = {"purposes": [{"id": "aireadi:external-training-programme"}]}
        [occ] = in_identifiers(rec)
        self.assertEqual(occ.word, "programme")
        self.assertEqual(occ.context, "aireadi:external-training-programme")

    def test_prose_is_not_reported_as_an_identifier(self):
        self.assertEqual(in_identifiers({"description": "the programme"}), [])

    def test_an_identifier_finding_is_never_excused_as_quoted(self):
        """Even if a source spells it that way, the record chose to mint it."""
        rec = {"id": "x:training-programme"}
        self.assertFalse(in_identifiers(rec)[0].quoted)


class TestVocabulary(unittest.TestCase):
    def test_no_entry_maps_a_word_to_itself(self):
        same = [b for b, a in BRITISH.items() if b == a]
        self.assertEqual(same, [])

    def test_words_with_american_homographs_are_excluded(self):
        """`practice` is a valid American noun and `license` the American
        spelling of both noun and verb, so a blanket rule on either produces
        false positives on correct text. `licence` is British-only and is
        included; `practise` is left out as ambiguous in context."""
        self.assertNotIn("practice", BRITISH)
        self.assertNotIn("license", BRITISH)
        self.assertIn("licence", BRITISH)
