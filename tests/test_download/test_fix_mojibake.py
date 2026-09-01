"""Double-encoded UTF-8 is repaired at preprocess time, conservatively (#872)."""
import unittest

from src.download.preprocess_sources import fix_mojibake

EMDASH = "\u2014"
BROKEN = EMDASH.encode("utf-8").decode("latin-1")      # U+00E2 U+0080 U+0094


class FixMojibake(unittest.TestCase):
    def test_double_encoded_em_dash_and_accents_are_restored(self):
        self.assertEqual(fix_mojibake(f"Share\n{BROKEN} copy"), f"Share\n{EMDASH} copy")
        accent = "Beno\u00eet".encode("utf-8").decode("latin-1")
        self.assertEqual(fix_mojibake(f"{accent} {BROKEN} x"), f"Beno\u00eet {EMDASH} x")

    def test_clean_text_passes_through_untouched(self):
        for s in ("plain ascii", f"real em{EMDASH}dash", "caf\u00e9 valid"):
            self.assertEqual(fix_mojibake(s), s)

    def test_mixed_content_repairs_only_the_broken_lines(self):
        mixed = f"good {EMDASH} line\nbad {BROKEN} line"
        self.assertEqual(fix_mojibake(mixed), f"good {EMDASH} line\nbad {EMDASH} line")

    def test_unrepairable_text_is_returned_unchanged(self):
        s = f"{BROKEN} then \u2603 snowman breaks latin-1 on the same line"
        self.assertEqual(fix_mojibake(s), s)


if __name__ == "__main__":
    unittest.main()
