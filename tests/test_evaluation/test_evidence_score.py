"""Evidence-grounded scoring: partitioning, propagation, and its limits.

The module scores a record against its input bundle because there is no gold
standard to score against. The partition that makes it affordable also
introduces the one approximation worth watching, so most of these tests are
about keeping that approximation visible and measurable.
"""

import unittest
from pathlib import Path

from data_sheets_schema.evidence_score import (
    Partition,
    RecordScore,
    SlotJudgement,
    build_plan,
    combine,
    load_record,
    measure_propagation_error,
    partition_slots,
    run_plan,
    savings,
)

DATA = Path("data")
GENERIC = "2026-07-28_claude-opus-5-generic_rep{}"


def fake_scorer(score_map=None, default=1.0):
    """Deterministic scorer. score_map keys are (slot, label) or slot."""
    score_map = score_map or {}

    def _score(*, project, slot, value, bundle):
        for key in ((slot, value if isinstance(value, str) else None), slot):
            if key in score_map:
                return SlotJudgement(supported=score_map[key], reason="mapped")
        return SlotJudgement(supported=default, reason="default")
    return _score


class TestPartition(unittest.TestCase):
    def test_stable_is_the_intersection(self):
        recs = {"a": {"x": 1, "y": 2}, "b": {"x": 9, "z": 3}}
        p = partition_slots(recs)
        self.assertEqual(p.stable, {"x"})
        self.assertEqual(p.divergent, {"y", "z"})

    def test_stable_is_about_presence_not_value(self):
        """Values differ between replicates almost always; presence is the axis."""
        recs = {"a": {"x": "one"}, "b": {"x": "completely different"}}
        self.assertEqual(partition_slots(recs).stable, {"x"})

    def test_empty_input(self):
        self.assertEqual(partition_slots({}).total, 0)

    def test_single_replicate_has_no_divergence(self):
        p = partition_slots({"a": {"x": 1, "y": 2}})
        self.assertEqual(p.divergent, set())
        self.assertEqual(p.stable, {"x", "y"})

    def test_counts_use_actual_occupancy_not_multiplication(self):
        """A divergent slot is absent from at least one replicate by definition.

        Counting it as `divergent * n_replicates` overcounts — the bug this
        test exists to prevent.
        """
        recs = {"a": {"x": 1, "y": 1}, "b": {"x": 1}, "c": {"x": 1}}
        p = partition_slots(recs)
        self.assertEqual(p.stable, {"x"})
        self.assertEqual(p.divergent, {"y"})
        self.assertEqual(p.scoring_count(recs), 2)     # x once + y once
        self.assertNotEqual(p.scoring_count(recs), 1 + 1 * 3)
        self.assertEqual(p.naive_count(recs), 4)       # 2 + 1 + 1


class TestPlan(unittest.TestCase):
    def test_plan_length_matches_savings(self):
        recs = {"a": {"x": 1, "y": 1}, "b": {"x": 2}, "c": {"x": 3, "z": 1}}
        self.assertEqual(len(build_plan("P", recs).to_score),
                         savings(recs)["planned_scorings"])

    def test_stable_slots_are_planned_once(self):
        recs = {"a": {"x": 1}, "b": {"x": 2}, "c": {"x": 3}}
        plan = build_plan("P", recs)
        self.assertEqual([s for s, _ in plan.to_score], ["x"])

    def test_divergent_slots_planned_only_where_present(self):
        recs = {"a": {"x": 1, "y": 1}, "b": {"x": 1}, "c": {"x": 1, "y": 1}}
        plan = build_plan("P", recs)
        ys = [(s, l) for s, l in plan.to_score if s == "y"]
        self.assertEqual({l for _, l in ys}, {"a", "c"})

    def test_representative_is_recorded(self):
        recs = {"a": {"x": 1}, "b": {"x": 2}}
        plan = build_plan("P", recs, representative_label="b")
        self.assertEqual(plan.representative["x"], "b")


class TestRunPlanAndPropagation(unittest.TestCase):
    def test_stable_score_reaches_every_replicate(self):
        recs = {"a": {"x": 1}, "b": {"x": 2}, "c": {"x": 3}}
        scores = run_plan(build_plan("P", recs), recs, "bundle", fake_scorer())
        self.assertEqual({s.label for s in scores}, {"a", "b", "c"})

    def test_propagated_scores_are_flagged(self):
        """A ranking built from propagated scores must be identifiable as such."""
        recs = {"a": {"x": 1}, "b": {"x": 2}, "c": {"x": 3}}
        plan = build_plan("P", recs, representative_label="a")
        scores = run_plan(plan, recs, "bundle", fake_scorer())
        by_label = {s.label: s for s in scores}
        self.assertFalse(by_label["a"].propagated)
        self.assertTrue(by_label["b"].propagated)
        self.assertTrue(by_label["c"].propagated)

    def test_divergent_scores_are_not_flagged_as_propagated(self):
        recs = {"a": {"x": 1, "y": 1}, "b": {"x": 1}}
        scores = run_plan(build_plan("P", recs), recs, "bundle", fake_scorer())
        y = [s for s in scores if s.slot == "y"]
        self.assertEqual(len(y), 1)
        self.assertFalse(y[0].propagated)

    def test_scorer_called_once_per_planned_pair(self):
        calls = []

        def counting(*, project, slot, value, bundle):
            calls.append((slot, value))
            return SlotJudgement(supported=1.0)

        recs = {"a": {"x": 1, "y": 1}, "b": {"x": 2}, "c": {"x": 3}}
        plan = build_plan("P", recs)
        run_plan(plan, recs, "bundle", counting)
        self.assertEqual(len(calls), len(plan.to_score))


class TestCombine(unittest.TestCase):
    def test_evidence_outweighs_presence_by_default(self):
        """Presence rewards density; it must not dominate."""
        from data_sheets_schema.evidence_score import SlotScore
        scores = [SlotScore("x", "dense", 0.0), SlotScore("x", "sparse", 1.0)]
        ranked = combine(scores, presence={"dense": 1.0, "sparse": 0.0})
        self.assertEqual(ranked[0].label, "sparse",
                         "a well-supported sparse record must beat an "
                         "unsupported dense one")

    def test_ranked_best_first(self):
        from data_sheets_schema.evidence_score import SlotScore
        scores = [SlotScore("x", "lo", 0.2), SlotScore("x", "hi", 0.9)]
        ranked = combine(scores, presence={})
        self.assertEqual([r.label for r in ranked], ["hi", "lo"])

    def test_propagated_fraction_is_reported(self):
        from data_sheets_schema.evidence_score import SlotScore
        scores = [SlotScore("x", "a", 1.0, propagated=False),
                  SlotScore("y", "a", 1.0, propagated=True)]
        ranked = combine(scores, presence={})
        self.assertAlmostEqual(ranked[0].propagated_fraction, 0.5)


class TestPropagationErrorMeasurement(unittest.TestCase):
    """The approximation must be testable, not assumed."""

    def test_identical_scores_report_no_disagreement(self):
        recs = {"a": {"x": 1, "y": 1}, "b": {"x": 2, "y": 2}}
        r = measure_propagation_error("P", recs, "bundle", fake_scorer(), sample=5)
        self.assertEqual(r["disagreements"], 0)
        self.assertIn("safe", r["verdict"])

    def test_divergent_judgements_are_caught(self):
        """If a stable slot scores differently per replicate, say so."""
        def uneven(*, project, slot, value, bundle):
            return SlotJudgement(supported=1.0 if value == 1 else 0.0)

        recs = {"a": {"x": 1, "y": 1}, "b": {"x": 2, "y": 2}}
        r = measure_propagation_error("P", recs, "bundle", uneven, sample=5)
        self.assertGreater(r["disagreement_rate"], 0.1)
        self.assertIn("flattens", r["verdict"])

    def test_no_stable_slots_is_reported_not_crashed(self):
        recs = {"a": {"x": 1}, "b": {"y": 1}}
        self.assertEqual(
            measure_propagation_error("P", recs, "b", fake_scorer())["sampled"], 0)


class TestAgainstTheRealCorpus(unittest.TestCase):
    def records(self, project):
        recs = {}
        for n in (1, 2, 3):
            f = (DATA / "d4d_concatenated/claudecode_agent" /
                 GENERIC.format(n) / f"{project}_d4d.yaml")
            if f.exists():
                recs[f"rep{n}"] = load_record(f)
        return recs

    def test_partition_saves_more_than_half(self):
        recs = self.records("VOICE")
        if len(recs) < 3:
            self.skipTest("generic runs not present")
        self.assertGreater(savings(recs)["reduction"], 0.5)

    def test_plan_matches_savings_on_every_project(self):
        for p in ("AI_READI", "CHORUS", "CM4AI", "VOICE"):
            recs = self.records(p)
            if len(recs) < 3:
                continue
            self.assertEqual(len(build_plan(p, recs).to_score),
                             savings(recs)["planned_scorings"], p)

    def test_curated_records_unwrap_for_comparison(self):
        f = DATA / "d4d_concatenated/curated/AI_READI_curated.yaml"
        if not f.exists():
            self.skipTest("curated not present")
        rec = load_record(f)
        self.assertNotIn("DatasetCollection", rec)
        self.assertGreater(len(rec), 10)


if __name__ == "__main__":
    unittest.main()
