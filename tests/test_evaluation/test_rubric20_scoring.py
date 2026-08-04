"""Rubric20 must be able to rank; for a long time it could not.

`_score_rubric20_question` returned 0 when a field was absent and a flat 4 when
present — never 1, 2, 3 or 5. Across the whole corpus that produced 71/88 for
*every* record, so the rubric meant to discriminate on quality was inert while
appearing to work.
"""

import unittest
from pathlib import Path

from data_sheets_schema.constants.evaluation import RUBRIC10_PATH, RUBRIC20_PATH
from src.evaluation.evaluate_d4d import D4DEvaluator

GENERIC = ("data/d4d_concatenated/claudecode_agent/"
           "2026-07-28_claude-opus-5-generic_rep{n}/{p}_d4d.yaml")


class TestRubric20Discriminates(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ev = D4DEvaluator(str(RUBRIC10_PATH), str(RUBRIC20_PATH))

    def _totals(self):
        out = []
        for project in ("AI_READI", "CHORUS", "CM4AI", "VOICE"):
            for n in (1, 2, 3):
                f = Path(GENERIC.format(n=n, p=project))
                if f.exists():
                    out.append(self.ev.evaluate_d4d_file(
                        str(f), project, "claudecode_agent").rubric20_total)
        return out

    def test_records_do_not_all_score_the_same(self):
        totals = self._totals()
        if len(totals) < 6:
            self.skipTest("generic corpus not present")
        self.assertGreater(len(set(totals)), 1,
                           "a rubric that returns one number cannot rank")

    def test_the_stub_score_of_4_is_no_longer_universal(self):
        """4 was the old constant for any populated field."""
        f = Path(GENERIC.format(n=1, p="CM4AI"))
        if not f.exists():
            self.skipTest("corpus not present")
        r = self.ev.evaluate_d4d_file(str(f), "CM4AI", "claudecode_agent")
        numeric = [q for q in r.rubric20_scores if q.max_score == 5]
        self.assertTrue(numeric)
        self.assertNotEqual({q.score for q in numeric}, {4},
                            "every numeric question still scoring 4")
        self.assertTrue({q.score for q in numeric} <= {0, 3, 5},
                        "scores must land on the rubric's declared bands")


class TestMeasuredBands(unittest.TestCase):
    """The four questions with explicit numeric thresholds are measured."""

    @classmethod
    def setUpClass(cls):
        cls.ev = D4DEvaluator(str(RUBRIC10_PATH), str(RUBRIC20_PATH))

    def _q(self, qid):
        return next(q for q in self.ev.rubric20["d4d_evaluation_rubric"]["rubric"]
                    if q["id"] == qid)

    def test_keyword_count_bands(self):
        q = self._q(3)
        for keywords, expected in (([], 0), (["a", "b"], 0), (["a"] * 5, 3),
                                   (["a"] * 9, 5)):
            with self.subTest(n=len(keywords)):
                data = {"keywords": keywords} if keywords else {}
                s = self.ev._score_rubric20_question(data, q)
                self.assertEqual(s.score, expected)

    def test_entry_length_bands(self):
        q = self._q(2)
        for text, expected in (("x" * 10, 0), ("x" * 100, 3), ("x" * 300, 5)):
            with self.subTest(n=len(text)):
                fields = q["field"] if isinstance(q["field"], list) else [q["field"]]
                s = self.ev._score_rubric20_question({fields[0]: text}, q)
                self.assertEqual(s.score, expected)

    def test_absent_field_scores_zero_not_a_middling_default(self):
        q = self._q(3)
        self.assertEqual(self.ev._score_rubric20_question({}, q).score, 0)

    def test_labels_report_the_measurement(self):
        """A score of 3 should say what was measured, not just assert a band."""
        q = self._q(3)
        s = self.ev._score_rubric20_question({"keywords": ["a", "b", "c"]}, q)
        self.assertIn("measured", s.score_label)


class TestDeclaredMaximumMatchesTheQuestions(unittest.TestCase):

    def test_description_total_matches_computed_total(self):
        """The prose said 84 while the questions defined 88.

        The questions are what get scored, so the prose was stale — and the LLM
        evaluation paths follow the prose, which is why the two denominators
        disagreed.
        """
        import re
        ev = D4DEvaluator(str(RUBRIC10_PATH), str(RUBRIC20_PATH))
        r = ev.rubric20["d4d_evaluation_rubric"]
        qs = r["rubric"]
        computed = (sum(5 for q in qs if q.get("score_type") != "pass_fail")
                    + sum(1 for q in qs if q.get("score_type") == "pass_fail"))
        m = re.search(r"Total maximum score:\s*(\d+)\s*points", r["description"])
        self.assertIsNotNone(m, "the rubric should declare its total")
        self.assertEqual(int(m.group(1)), computed)

    def test_the_constant_matches_the_questions_too(self):
        """The third place the total lived, and the one nothing checked.

        `RUBRIC20_MAX_SCORE` said 84 while the questions defined 88. It was
        exported and imported by nothing, so no test and no caller ever
        contradicted it — dead and wrong, which is the combination the next
        person needing a denominator picks up.
        """
        from data_sheets_schema.constants import RUBRIC20_MAX_SCORE
        ev = D4DEvaluator(str(RUBRIC10_PATH), str(RUBRIC20_PATH))
        qs = ev.rubric20["d4d_evaluation_rubric"]["rubric"]
        computed = (sum(5 for q in qs if q.get("score_type") != "pass_fail")
                    + sum(1 for q in qs if q.get("score_type") == "pass_fail"))
        self.assertEqual(RUBRIC20_MAX_SCORE, computed)

    def test_the_question_count_matches_too(self):
        from data_sheets_schema.constants import RUBRIC20_MAX_QUESTIONS
        ev = D4DEvaluator(str(RUBRIC10_PATH), str(RUBRIC20_PATH))
        qs = ev.rubric20["d4d_evaluation_rubric"]["rubric"]
        self.assertEqual(RUBRIC20_MAX_QUESTIONS, len(qs))

    def test_no_rubric20_path_hardcodes_a_denominator(self):
        """A literal denominator is one nothing can keep in sync.

        The total lived in seven places. Fixing the two obvious ones left the
        LLM path — including the judge's own prompt, which handed the model a
        `"max_points": 84` template to copy — still reporting out of 84 while
        the presence path used 88, so the two were never comparable.

        Unrelated 84s exist (an 84-question healthsheet, a percentage), so this
        matches the shapes a denominator takes rather than the digits.
        """
        from pathlib import Path
        patterns = ("/84", "* 84", ", 84)", "or 84", "= 84", '"max_points": 84')
        offenders = []
        for path in (list(Path("scripts").glob("*rubric20*.py"))
                     + list(Path("scripts").glob("*evaluation*.py"))
                     + [Path("src/download/prompts/rubric20_system_prompt.md")]):
            for n, line in enumerate(path.read_text().splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                if any(p in line for p in patterns):
                    offenders.append(f"{path}:{n}: {line.strip()[:70]}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()


class TestQ1BandInterpolation(unittest.TestCase):
    """Q1 is the only measured question whose bands leave a gap (#188).

    0 is "<=40%", 3 is "~70%", 5 is ">=90%", and nothing states what 41-69%
    scores. One rule — split a gap at the midpoint — must govern both
    boundaries. An earlier version interpolated the lower boundary and took the
    upper one literally, so a record at 45% scored 0 while one at 85% scored 3.
    """

    @classmethod
    def setUpClass(cls):
        cls.ev = D4DEvaluator(str(RUBRIC10_PATH), str(RUBRIC20_PATH))

    def test_both_boundaries_come_from_the_same_rule(self):
        thresholds = dict((s, f) for s, f in self.ev.Q1_BAND_THRESHOLDS)
        self.assertAlmostEqual(thresholds[3], (0.40 + 0.70) / 2)
        self.assertAlmostEqual(thresholds[5], (0.70 + 0.90) / 2)

    def test_bands_are_monotonic_in_the_measurement(self):
        prev = -1
        for frac in (0.0, 0.3, 0.45, 0.55, 0.6, 0.79, 0.8, 0.95, 1.0):
            band = self.ev._band_for(frac, self.ev.Q1_BAND_THRESHOLDS)
            self.assertGreaterEqual(band, prev, f"band fell at {frac}")
            prev = band

    def test_a_fully_populated_record_reaches_the_top_band(self):
        self.assertEqual(self.ev._band_for(1.0, self.ev.Q1_BAND_THRESHOLDS), 5)

    def test_an_empty_record_reaches_the_bottom_band(self):
        self.assertEqual(self.ev._band_for(0.0, self.ev.Q1_BAND_THRESHOLDS), 0)
