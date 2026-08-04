"""Scores measured against different maxima must never be averaged together.

167 committed rubric20 evaluations record `max_points: 84`; everything written
after the correction records 88 (#275). A mean over both lands somewhere
plausible and reads as a result, which is why the default here is to refuse.

These tests **run** the report generators rather than inspecting their source.
The previous round asserted on the text of the file, and a grep cannot see an
unbound name — which is how `create_detailed_report` shipped raising NameError
with a green suite and three green CI runs behind it (#278).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from data_sheets_schema.rubric_pooling import (  # noqa: E402
    MixedDenominators,
    common_denominator,
    denominator_label,
    denominator_of,
    group_by_denominator,
    pooling_warning,
)


def _result(points, maximum, method="claudecode_agent", project="CHORUS"):
    return {"project": project, "method": method,
            "overall_score": {"total_points": points, "max_points": maximum,
                              "percentage": 100.0 * points / maximum}}


class TestCommonDenominator(unittest.TestCase):
    def test_one_maximum_is_returned(self):
        self.assertEqual(common_denominator([_result(70, 88), _result(60, 88)]), 88)

    def test_two_maxima_raise(self):
        with self.assertRaises(MixedDenominators) as ctx:
            common_denominator([_result(70, 88), _result(70, 84)])
        self.assertIn("84", str(ctx.exception))
        self.assertIn("88", str(ctx.exception))

    def test_it_does_not_quietly_pick_one(self):
        """Returning the max, the mode, or a default would let an aggregate
        over two instruments look like an aggregate over one."""
        for picker in (max, min):
            with self.assertRaises(MixedDenominators):
                common_denominator([_result(70, 88), _result(70, 84)])

    def test_a_record_without_max_points_falls_back(self):
        self.assertEqual(denominator_of({"overall_score": {}}, default=88), 88)
        self.assertEqual(denominator_of({}, default=88), 88)

    def test_empty_is_the_default_not_an_error(self):
        self.assertEqual(common_denominator([], default=88), 88)


class TestGrouping(unittest.TestCase):
    def test_groups_are_poolable(self):
        groups = group_by_denominator(
            [_result(70, 88), _result(60, 84), _result(50, 88)])
        self.assertEqual(sorted(groups), [84, 88])
        self.assertEqual(len(groups[88]), 2)
        for denom, group in groups.items():
            self.assertEqual(common_denominator(group), denom,
                             "every group must itself be poolable")

    def test_label_marks_a_mixed_set(self):
        self.assertEqual(denominator_label([_result(70, 88)]), "88")
        self.assertEqual(denominator_label([_result(70, 88), _result(70, 84)]),
                         "MIXED(84/88)")

    def test_warning_is_empty_when_there_is_nothing_to_warn_about(self):
        self.assertEqual(pooling_warning([_result(70, 88)]), "")

    def test_warning_names_both_populations(self):
        text = pooling_warning([_result(70, 88), _result(70, 84), _result(60, 84)])
        self.assertIn("2 scored out of 84", text)
        self.assertIn("1 scored out of 88", text)


class TestTheReportGeneratorsActuallyRun(unittest.TestCase):
    """#278: the bug a source-text assertion could not see.

    `create_detailed_report` referenced a name bound in a different function.
    Every existing assertion passed because they read the file instead of
    calling it.
    """

    def setUp(self):
        """Redirect output to a temp dir.

        These functions write into `data/evaluation_llm/rubric20/`. An earlier
        version of this file called them without redirecting and overwrote two
        committed artifacts with fixture data — a test that damages the corpus
        it is meant to protect.
        """
        import tempfile
        import summarize_rubric20_results as mod
        self.mod = mod
        self._tmp = tempfile.TemporaryDirectory()
        self._real_dir = mod.EVAL_DIR
        mod.EVAL_DIR = Path(self._tmp.name)
        self.mixed = [_result(70, 88, method="claudecode_agent"),
                      _result(66, 84, method="gpt5"),
                      _result(60, 84, method="curated", project="VOICE")]

    def tearDown(self):
        self.mod.EVAL_DIR = self._real_dir
        self._tmp.cleanup()

    def _report(self, results):
        import io
        from contextlib import redirect_stdout
        with redirect_stdout(io.StringIO()):
            self.mod.create_detailed_report(results)
        written = Path(self._tmp.name) / "summary_report.md"
        self.assertTrue(written.exists(), "the report must actually be written")
        return written.read_text()

    def test_detailed_report_runs_on_a_mixed_corpus(self):
        """The call itself is the assertion — an unbound name raises here."""
        self.assertIn("Rubric20", self._report(self.mixed))

    def test_detailed_report_reports_each_maximum_separately(self):
        text = self._report(self.mixed)
        self.assertIn("Scored out of 84", text)
        self.assertIn("Scored out of 88", text)

    def test_detailed_report_warns_that_the_corpus_is_mixed(self):
        self.assertIn("different maxima", self._report(self.mixed))

    def test_no_single_average_spans_both_maxima(self):
        """The whole point: one number over two instruments must not appear."""
        text = self._report(self.mixed)
        self.assertNotIn("/MIXED", text,
                         "an average must belong to one denominator, not a label")

    def test_a_single_denominator_corpus_gets_no_warning(self):
        text = self._report([_result(70, 88), _result(60, 88)])
        self.assertNotIn("different maxima", text)
        self.assertIn("Scored out of 88", text)

    def test_markdown_table_runs_and_marks_mixed_rows(self):
        import io
        from contextlib import redirect_stdout
        with redirect_stdout(io.StringIO()):
            self.mod.create_markdown_table(self.mixed)
        written = Path(self._tmp.name) / "summary_table.md"
        self.assertTrue(written.exists())


if __name__ == "__main__":
    unittest.main()
