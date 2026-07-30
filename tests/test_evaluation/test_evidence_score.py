"""Evidence-grounded scoring: partitioning, propagation, and its limits.

The module scores a record against its input bundle because there is no gold
standard to score against. The partition that makes it affordable also
introduces the one approximation worth watching, so most of these tests are
about keeping that approximation visible and measurable.
"""

import unittest
from pathlib import Path

from data_sheets_schema.evidence_score import (
    _parse_judgement,
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

    def test_ranks_on_summed_support_not_the_mean(self):
        """The mean cannot separate records that share most of their slots.

        Measured on CM4AI: rep3 carried 12 of 16 divergent slots against rep1's
        3, yet their evidence means differed by 0.0022 — below the 0.016
        propagation bias — because 57 shared stable slots dominated the average.
        """
        from data_sheets_schema.evidence_score import SlotScore
        # Both average 1.0; one carries three times the grounded content.
        scores = ([SlotScore("s%d" % i, "wide", 1.0) for i in range(6)] +
                  [SlotScore("s%d" % i, "narrow", 1.0) for i in range(2)])
        ranked = combine(scores, presence={})
        self.assertEqual(ranked[0].label, "wide")
        self.assertEqual(ranked[0].evidence, ranked[1].evidence,
                         "means are equal — only the sum separates them")
        self.assertEqual(ranked[0].supported_slots, 6.0)
        self.assertEqual(ranked[1].supported_slots, 2.0)

    def test_unsupported_slots_earn_no_credit(self):
        """The one property presence lacks: padding must not pay.

        A record with more slots loses to a sparser one when the extra content
        is not grounded. Untested against real data — this corpus contains no
        fabrication — so it is pinned here instead.
        """
        from data_sheets_schema.evidence_score import SlotScore
        padded = ([SlotScore("a", "padded", 1.0)] +
                  [SlotScore("f%d" % i, "padded", 0.0) for i in range(5)])
        honest = [SlotScore("a", "honest", 1.0), SlotScore("b", "honest", 1.0)]
        ranked = combine(padded + honest, presence={})
        self.assertEqual(ranked[0].label, "honest")
        self.assertEqual(ranked[0].slots_scored, 2)
        self.assertEqual(ranked[1].slots_scored, 6,
                         "the padded record has more slots and still loses")

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
        self.assertEqual(r["record_level_spread"], 0.0)
        self.assertIn("affordable", r["verdict"])

    def test_systematic_bias_is_caught(self):
        """One replicate consistently favoured is the case that breaks ranking."""
        def uneven(*, project, slot, value, bundle):
            return SlotJudgement(supported=1.0 if value == 1 else 0.0)

        recs = {"a": {"x": 1, "y": 1}, "b": {"x": 2, "y": 2}}
        r = measure_propagation_error("P", recs, "bundle", uneven, sample=5)
        self.assertEqual(r["record_level_spread"], 1.0)
        self.assertIn("biases record scores", r["verdict"])

    def test_scattered_noise_does_not_condemn_propagation(self):
        """Per-slot disagreement that cancels at record level is affordable.

        The distinction the first version of this measure missed: it counted
        any nonzero spread as a disagreement, which is ~always true of a
        continuous scorer, and condemned propagation on incidence alone.
        """
        # 'a' wins slot x by 0.4, 'b' wins slot y by 0.4 — every slot disagrees,
        # yet neither record is favoured overall.
        scores = {("x", "a"): 0.9, ("x", "b"): 0.5,
                  ("y", "a"): 0.5, ("y", "b"): 0.9}

        def scattered(*, project, slot, value, bundle):
            return SlotJudgement(supported=scores[(slot, value)])

        recs = {"a": {"x": "a", "y": "a"}, "b": {"x": "b", "y": "b"}}
        r = measure_propagation_error("P", recs, "bundle", scattered, sample=5)
        self.assertEqual(r["disagreement_rate"], 1.0, "every slot differs")
        self.assertEqual(r["record_level_spread"], 0.0, "yet nothing is biased")
        self.assertIn("affordable", r["verdict"])

    def test_material_disagreement_ignores_small_wobbles(self):
        """A 0.05 difference is scorer noise, not a change of judgement."""
        def wobble(*, project, slot, value, bundle):
            return SlotJudgement(supported=0.9 if value == "a" else 0.85)

        recs = {"a": {"x": "a", "y": "a"}, "b": {"x": "b", "y": "b"}}
        r = measure_propagation_error("P", recs, "bundle", wobble, sample=5)
        self.assertEqual(r["disagreement_rate"], 1.0)
        self.assertEqual(r["material_disagreements"], 0)

    def test_detail_is_returned_for_audit(self):
        recs = {"a": {"x": 1}, "b": {"x": 2}}
        r = measure_propagation_error("P", recs, "bundle", fake_scorer(), sample=5)
        self.assertEqual(len(r["detail"]), 1)
        self.assertEqual(set(r["detail"][0]["scores"]), {"a", "b"})

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


class TestJudgementParsing(unittest.TestCase):
    """Parsing a reply that the model did not finish writing.

    `google/claude-opus-5-high` spends output budget on a thinking block before
    emitting anything, so a ceiling sized for the answer gets consumed by the
    reasoning and the JSON is cut mid-string. `supported` is emitted first, so
    the score is fully present in the fragment even when the reason is not, and
    discarding a complete number because its trailing prose is missing would
    throw away a judgement that was actually made.
    """

    def test_complete_reply(self):
        j = _parse_judgement('{"supported": 0.5, "reason": "partly"}')
        self.assertEqual(j.supported, 0.5)
        self.assertEqual(j.reason, "partly")

    def test_reply_truncated_inside_reason_keeps_the_score(self):
        j = _parse_judgement('{"supported": 0.95, "reason": "The Dataverse pag')
        self.assertEqual(j.supported, 0.95)
        self.assertIn("truncated", j.reason)

    def test_truncated_integer_score(self):
        self.assertEqual(
            _parse_judgement('{"supported": 1, "reason": "yes beca').supported,
            1.0)

    def test_prose_around_the_json_is_tolerated(self):
        j = _parse_judgement('Here you go:\n{"supported": 0.0, "reason": "no"}\n')
        self.assertEqual(j.supported, 0.0)

    def test_empty_reply_raises_rather_than_scoring_zero(self):
        """The failure mode this guards: an all-thinking response.

        Defaulting an unreadable reply to 0.0 would let the scorer's own
        exhaustion look like an unsupported claim, dragging the record's
        evidence average down for a reason that has nothing to do with it.
        """
        with self.assertRaises(ValueError):
            _parse_judgement("")

    def test_json_without_supported_raises(self):
        with self.assertRaises(ValueError):
            _parse_judgement('{"reason": "forgot the score"}')


if __name__ == "__main__":
    unittest.main()


class TestJudgementContext(unittest.TestCase):
    """Every input that changes an answer must change the key (#180 and after).

    The original key was assembled by hand at the call site and omitted the
    bundle. Patching that in place left the rubric and the schema unkeyed, both
    of which were already live hazards — the rubric had been edited mid-session,
    and the schema changes routinely in a schema project. A declared context
    makes the next omission impossible rather than merely unlikely.
    """

    def _ctx(self, **kw):
        from data_sheets_schema.evidence_score import JudgementContext
        base = dict(axis="fitness", model="m", rubric="r", corpus="", schema="s")
        base.update(kw)
        return JudgementContext(**base)

    def test_every_field_participates_in_the_fingerprint(self):
        base = self._ctx()
        for fieldname, other in (("axis", "grounding"), ("model", "m2"),
                                 ("rubric", "r2"), ("corpus", "c2"),
                                 ("schema", "s2")):
            with self.subTest(field=fieldname):
                self.assertNotEqual(base.fingerprint(),
                                    self._ctx(**{fieldname: other}).fingerprint(),
                                    f"{fieldname} must change the key")

    def test_identical_contexts_agree(self):
        self.assertEqual(self._ctx().fingerprint(), self._ctx().fingerprint())

    def test_mismatch_names_the_dimension_that_moved(self):
        from data_sheets_schema.evidence_score import JudgementContext
        cur = self._ctx(rubric="new")
        self.assertEqual(
            JudgementContext.mismatch(self._ctx(rubric="old").as_entry(), cur),
            "rubric")

    def test_matching_entry_reports_no_mismatch(self):
        from data_sheets_schema.evidence_score import JudgementContext
        self.assertIsNone(
            JudgementContext.mismatch(self._ctx().as_entry(), self._ctx()))

    def test_entries_without_context_are_rejected(self):
        """Pre-context entries cannot be placed and must not be assumed current."""
        from data_sheets_schema.evidence_score import JudgementContext
        self.assertIsNotNone(
            JudgementContext.mismatch({"model": "m", "slot": "s"}, self._ctx()))

    def test_grounding_and_fitness_entries_never_collide(self):
        self.assertNotEqual(self._ctx(axis="fitness", corpus="", schema="s"),
                            self._ctx(axis="grounding", corpus="c", schema=""))


class TestBundleKeyedCache(unittest.TestCase):
    """Grounding judgements must not cross corpora (#180).

    Grounding asks "is this supported by *these documents*", so the same value
    against a different bundle is a different question. Keyed on (slot, value)
    alone, a scorer reused across projects returned one project's verdict for
    another on every slot whose value collides.
    """

    def _scorer(self, calls):
        from data_sheets_schema.evidence_score import LLMSlotScorer
        import data_sheets_schema.api_runner as ar

        class Resp:
            def __init__(self, t):
                self.content = [type("B", (), {"type": "text", "text": t})()]
                self.stop_reason = "end_turn"
                self.usage = None

        def fake(client, *, model, max_tokens, temperature, system, messages):
            calls.append(messages[0]["content"][0]["text"])
            return Resp('{"supported": 1.0, "reason": "ok"}')

        self._real = ar._call_with_retry
        ar._call_with_retry = fake
        self.addCleanup(lambda: setattr(ar, "_call_with_retry", self._real))
        return LLMSlotScorer(client=object(), model="m")

    def test_same_value_in_two_corpora_is_judged_twice(self):
        calls = []
        sc = self._scorer(calls)
        sc(project="A", slot="is_tabular", value=True, bundle="CORPUS-A")
        sc(project="B", slot="is_tabular", value=True, bundle="CORPUS-B")
        self.assertEqual(len(calls), 2, "each corpus must be judged on its own")
        self.assertIn("CORPUS-A", calls[0])
        self.assertIn("CORPUS-B", calls[1])

    def test_same_value_same_corpus_still_memoises(self):
        calls = []
        sc = self._scorer(calls)
        for _ in range(3):
            sc(project="A", slot="is_tabular", value=True, bundle="CORPUS-A")
        self.assertEqual(len(calls), 1)
        self.assertEqual(sc.memo_hits, 2)

    def test_a_rubric_edit_invalidates_cached_judgements(self):
        """The hazard that was live and unnoticed: SCORER_SYSTEM was edited
        mid-session and every judgement cached before it kept answering the old
        rubric."""
        from data_sheets_schema.evidence_score import (
            JudgementContext, LLMSlotScorer)
        import json as _json
        from tempfile import TemporaryDirectory
        old = JudgementContext(axis="grounding", model="m", rubric="OLD",
                               corpus="c")
        with TemporaryDirectory() as td:
            p = Path(td) / "cache.jsonl"
            p.write_text(_json.dumps({**old.as_entry(), "slot": "s",
                                      "value": "1", "supported": 1.0}) + "\n")
            sc = LLMSlotScorer(client=object(), model="m", cache_path=p)
            sc._load_cache(JudgementContext(axis="grounding", model="m",
                                            rubric="NEW", corpus="c"))
            self.assertEqual(sc.cache_loaded, 0)
            self.assertEqual(sc.cache_skipped, {"rubric": 1})

    def test_bundle_fingerprint_is_stable_and_short(self):
        from data_sheets_schema.evidence_score import bundle_fingerprint
        a, b = bundle_fingerprint("x" * 90_000), bundle_fingerprint("x" * 90_000)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 12)
        self.assertNotEqual(a, bundle_fingerprint("y" * 90_000))
