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


if __name__ == "__main__":
    unittest.main()
