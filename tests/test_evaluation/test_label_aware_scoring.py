"""Per-replicate scoring: discovery, label keying, and what actually discriminates.

Before this, `d4d evaluate presence --method claudecode_agent` evaluated zero
files — discovery used a hardcoded flat path table that the move to run-labelled
directories invalidated — and every output was keyed (project, method), so three
replicates of one method overwrote each other.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, "src")

from evaluation.evaluate_d4d import D4DEvaluator          # noqa: E402
from data_sheets_schema.constants import (                # noqa: E402
    RUBRIC10_PATH,
    RUBRIC20_PATH,
)

DATA = Path("data")
GENERIC = [f"2026-07-28_claude-opus-5-generic_rep{n}" for n in (1, 2, 3)]


def evaluator():
    return D4DEvaluator(str(RUBRIC10_PATH), str(RUBRIC20_PATH))


class TestDiscovery(unittest.TestCase):
    def test_finds_run_labelled_records(self):
        found = D4DEvaluator.discover_records(DATA, "CHORUS", "claudecode_agent")
        self.assertGreater(len(found), 1,
                           "run-labelled layout not discovered")
        self.assertTrue(all(lbl for lbl, _ in found),
                        "run-labelled records must carry a label")

    def test_finds_flat_records_with_no_label(self):
        found = D4DEvaluator.discover_records(DATA, "CHORUS", "gpt5")
        if not found:
            self.skipTest("gpt5 records not present")
        self.assertTrue(any(lbl is None for lbl, _ in found),
                        "flat layout must yield label=None")

    def test_curated_uses_its_own_filename(self):
        found = D4DEvaluator.discover_records(DATA, "AI_READI", "curated")
        if not found:
            self.skipTest("curated records not present")
        self.assertTrue(all(p.name.endswith("_curated.yaml") for _, p in found))

    def test_core_methods_use_the_core_filename(self):
        found = D4DEvaluator.discover_records(DATA, "CHORUS",
                                              "claudecode_agent_core")
        if not found:
            self.skipTest("core records not present")
        self.assertTrue(all(p.name.endswith("_d4d_core.yaml") for _, p in found))

    def test_arms_added_later_need_no_code_change(self):
        """Discovery globs; it does not enumerate methods."""
        found = D4DEvaluator.discover_records(DATA, "CHORUS",
                                              "claudecode_agent_crate")
        self.assertTrue(found, "crate arm not discovered")

    def test_unknown_method_returns_empty_not_an_error(self):
        self.assertEqual(
            D4DEvaluator.discover_records(DATA, "CHORUS", "no_such_method"), [])

    def test_every_discovered_path_exists(self):
        for method in ("claudecode_agent", "claudecode_agent_crate"):
            for _, p in D4DEvaluator.discover_records(DATA, "VOICE", method):
                self.assertTrue(p.is_file(), p)


class TestLabelKeying(unittest.TestCase):
    def test_evaluation_carries_the_label(self):
        ev = evaluator()
        p = DATA / "d4d_concatenated/claudecode_agent" / GENERIC[0] / "CHORUS_d4d.yaml"
        if not p.exists():
            self.skipTest("generic runs not present")
        r = ev.evaluate_d4d_file(p, "CHORUS", "claudecode_agent", label=GENERIC[0])
        self.assertEqual(r.label, GENERIC[0])

    def test_label_defaults_to_none_for_flat_records(self):
        ev = evaluator()
        p = DATA / "d4d_concatenated/gpt5/CHORUS_d4d.yaml"
        if not p.exists():
            self.skipTest("gpt5 record not present")
        self.assertIsNone(
            ev.evaluate_d4d_file(p, "CHORUS", "gpt5").label)

    def test_replicates_produce_distinct_report_filenames(self):
        """The collision that silently kept only the last replicate."""
        names = set()
        for lbl in GENERIC:
            parts = ["CHORUS", "claudecode_agent", lbl.replace("/", "_")]
            names.add(f"{'_'.join(parts)}_evaluation.md")
        self.assertEqual(len(names), 3)


class TestWhatActuallyDiscriminates(unittest.TestCase):
    """Selection needs a score that separates replicates. Only one rubric does.

    Recorded as tests because it bounds what a selection score can be built
    from: rubric20 as implemented is constant across every record in the
    corpus, so it can contribute nothing to ranking.
    """

    def _scores(self, project):
        ev = evaluator()
        out = []
        for lbl in GENERIC:
            p = (DATA / "d4d_concatenated/claudecode_agent" / lbl /
                 f"{project}_d4d.yaml")
            if p.exists():
                out.append(ev.evaluate_d4d_file(p, project, "claudecode_agent",
                                                label=lbl))
        return out

    def test_rubric20_now_discriminates(self):
        """These two tests previously asserted the opposite.

        They pinned the stub — every numeric question scoring 4, every record
        totalling 71/88 — as a documented finding rather than a passing feature.
        Now that the questions are measured, the assertions invert: across the
        corpus rubric20 returns five distinct totals with an 8-point spread.
        """
        results = self._scores("AI_READI")
        if len(results) < 3:
            self.skipTest("generic runs not present")
        self.assertGreater(
            len({r.rubric20_total for r in results}), 1,
            "rubric20 has stopped discriminating — check evaluate_d4d.py")

    def test_rubric20_numeric_scores_land_on_declared_bands(self):
        results = self._scores("CHORUS")
        if not results:
            self.skipTest("generic runs not present")
        scores = {q.score for q in results[0].rubric20_scores
                  if q.score_type == "numeric"}
        self.assertNotEqual(scores, {4}, "the 0-or-4 stub is back")
        self.assertTrue(scores <= {0, 3, 5},
                        f"scores must be rubric bands, got {sorted(scores)}")

    def test_rubric10_does_discriminate(self):
        results = self._scores("CM4AI")
        if len(results) < 3:
            self.skipTest("generic runs not present")
        self.assertGreater(len({r.rubric10_total for r in results}), 1,
                           "rubric10 must separate replicates to be usable "
                           "for selection")
