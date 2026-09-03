"""The British-spelling instrument's boundary claims, as tests (#653, #670).

The #670 review found every boundary claim existed only as comments — no unit
test exercised `british_spellings` at all, in either instrument version. The
battery below is the review's own adversarial set: the exclusions the
instrument turns on (American "analyses", "programmed", "central"), the
families both instruments had missed (organise ×76 in the v4 arm), and the
exemptions (quotes, case).
"""

import unittest

from data_sheets_schema.grounding import BRITISH_PATTERNS, british_spellings


class Battery(unittest.TestCase):

    CASES = (
        # The exclusion the v2 instrument exists for.
        ("designing analyses that depend on image volume", 0),
        ("three analyses of the analysis", 0),
        # Unambiguously British inflections still count.
        ("we analysed the colour fundus images", 2),
        ("analysing the data", 1),
        # American derivations of shared stems must not match.
        ("programmed the programmer to run programmes", 1),
        ("central control at the epicenter", 0),
        ("licensed and enrolled participants", 0),
        # The organise family — 76 occurrences in the v4 arm escaped both
        # instruments (#670 review).
        ("we organise and organised the organiser", 3),
        ("organisational and organisationally", 2),
        # Bare enrol, the licenced misspelling, the composed suffixes.
        ("please enrol; he enrols", 2),
        ("licenced under a licencing scheme", 2),
        ("honourable and unfavourable favourites", 3),
        ("behaviourally, the colourings were colourful", 3),
        # Exemptions: quoted spans and case.
        ('"the programme is great" said the licence', 1),
        ("THE PROGRAMME AND COLOUR", 2),
        # Hyphenated compounds are genuine British usage and count.
        ("a multi-centre colour-coded trial", 2),
        # Identifiers with underscores are not prose.
        ("see data_centre_config", 0),
        # v3 (#836, #859): the families the review pass found at 0.
        ("tumour and oedema measured in metres while travelling", 4),
        ("two centimetres of colour artefacts, minimised and personalised", 5),
        ("generalisability was prioritised, totalling three", 3),
        ("paediatric haemoglobin, anaemia and ageing", 4),
        ("randomised trials, a visualisation, hypothesised and authorised", 4),
        ("macula-centred fibre counsellors practised", 4),
        # American controls and homographs: the noun `practice`, the
        # American `specialist`/`emphasis`, `cancellation`, `program`.
        ("tumor edema meters traveling artifact minimize personalized totaling", 0),
        ("in practice the specialist put emphasis on the cancellation of the program", 0),
        ("the synthesis and hypothesis of the analysis", 0),
    )

    def test_the_battery(self):
        for text, expected in self.CASES:
            with self.subTest(text=text[:40]):
                self.assertEqual(british_spellings(text), expected)

    def test_no_pattern_matches_the_empty_string(self):
        """A degenerate pattern would count every record's length."""
        for pattern in BRITISH_PATTERNS:
            self.assertIsNone(pattern.match(""))

    def test_the_american_control_text_scores_zero(self):
        """A wholly American paragraph is the instrument's specificity floor."""
        text = ("The program was licensed and organized by the center. "
                "Enrollment favored standardized labeling; the catalog "
                "summarized colorful behavioral analyses.")
        self.assertEqual(british_spellings(text), 0)


if __name__ == "__main__":
    unittest.main()


class PrefixClassification(unittest.TestCase):
    """Registered scheme vs minted namespace (#671, refined by its review).

    The first v2 draft blanket-excluded `urn:` and thereby erased 758 corpus
    occurrences of minted namespaces wearing the scheme (`urn:cm4ai:…`). The
    NID-aware rule keeps the ark fix without that hole, and the grounding net
    catches what classification exempts: a minted ark counts `absent`.
    """

    SLOTS = {"id", "same_as", "publisher"}

    def _count(self, value):
        from data_sheets_schema.grounding import undeclared_prefixes
        return undeclared_prefixes({"id": value}, self.SLOTS)

    def test_ark_is_a_scheme_not_a_minted_prefix(self):
        self.assertEqual(self._count("ark:59853/rocrate-x"), {})
        self.assertEqual(self._count("ARK:59853/x"), {},
                         "the exclusion must be case-insensitive")

    def test_a_urn_under_a_registered_nid_is_excused(self):
        self.assertEqual(self._count("urn:uuid:1234-abcd"), {})

    def test_a_urn_under_an_invented_nid_is_counted_as_that_namespace(self):
        self.assertEqual(self._count("urn:cm4ai:creator:x"), {"urn:cm4ai": 1})
        self.assertEqual(self._count("urn:b2ai-voice:thing"),
                         {"urn:b2ai-voice": 1})

    def test_a_bare_invented_prefix_still_counts(self):
        self.assertEqual(self._count("chorus:admission-42"), {"chorus": 1})

    def test_a_minted_ark_is_caught_by_grounding_not_classification(self):
        """The safety net the review demanded: exempt from the prefix count,
        an unattested ark must still fail grounding as `absent`."""
        from data_sheets_schema.grounding import ground
        self.assertEqual(ground("ark:99999/fake-thing", "no arks here"),
                         ("ark", "ark:99999/fake-thing", "absent"))

    def test_an_attested_ark_grounds(self):
        from data_sheets_schema.grounding import ground
        bundle = "the release ark:59853/rocrate-b2ai-x sits in fairhub"
        self.assertEqual(ground("ark:59853/rocrate-b2ai-x", bundle)[2],
                         "grounded")
