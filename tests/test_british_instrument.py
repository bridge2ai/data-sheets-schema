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
