"""Tests for the replicate-agreement measures.

Nothing here touches the network. The judge and embedder are injected, and the
one test that exercises the real cache reads the committed one in offline mode,
where a miss raises instead of billing.
"""

import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from data_sheets_schema.agreement import (
    EQUIVALENCE_SYSTEM,
    JUDGE_VALUE_CHARS,
    LEGACY_JUDGE_VALUE_CHARS,
    Embedder,
    EquivalenceJudge,
    OfflineCacheMiss,
    SlotAgreement,
    _digest,
    _judge_key,
    _legacy_judge_key,
    _parse_verdict,
    _sent,
    build_matrix,
    compare_records,
    render,
)

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "evaluation_llm" / "agreement_cache"


class TestRender(unittest.TestCase):
    def test_strings_are_stripped_not_quoted(self):
        self.assertEqual(render("  CHoRUS  "), "CHoRUS")

    def test_key_order_alone_is_not_a_difference(self):
        """`sort_keys=True` is what stops dict ordering reading as disagreement.

        Without it two records asserting identical facts would differ purely
        because the generator emitted the keys in a different order.
        """
        self.assertEqual(render({"a": 1, "b": 2}), render({"b": 2, "a": 1}))

    def test_differing_values_still_differ(self):
        self.assertNotEqual(render({"n": 1}), render({"n": 2}))

    def test_non_ascii_survives(self):
        self.assertIn("é", render({"name": "Café"}))


class TestParseVerdict(unittest.TestCase):
    def test_bare_json(self):
        self.assertEqual(_parse_verdict('{"equivalent": true, "reason": "same"}'),
                         (True, "same"))

    def test_fenced_json(self):
        ok, reason = _parse_verdict('```json\n{"equivalent": false, "reason": "no"}\n```')
        self.assertFalse(ok)
        self.assertEqual(reason, "no")

    def test_prose_around_json(self):
        ok, _ = _parse_verdict('Here you go:\n{"equivalent": true, "reason": "x"}\nDone.')
        self.assertTrue(ok)

    def test_truncated_json_is_salvaged(self):
        """A thinking block can eat the budget and clip the closing brace.

        The verdict was still reached and the call was still paid for, so it is
        recovered — flagged as truncated so nobody mistakes the clipped reason
        for the whole of one.
        """
        ok, reason = _parse_verdict('{"equivalent": true, "reason": "they both say')
        self.assertTrue(ok)
        self.assertIn("[truncated]", reason)

    def test_truncated_with_no_reason_at_all(self):
        ok, reason = _parse_verdict('{"equivalent": false')
        self.assertFalse(ok)
        self.assertEqual(reason, "[truncated]")

    def test_unparseable_raises_rather_than_assuming_agreement(self):
        """The load-bearing default.

        Treating an unreadable response as agreement would inflate the very
        number this module exists to measure honestly, and it would do so
        silently. Failing loudly is the only safe direction.
        """
        with self.assertRaises(ValueError):
            _parse_verdict("I think they broadly agree, yes.")

    def test_reason_is_capped(self):
        _, reason = _parse_verdict(json.dumps({"equivalent": True, "reason": "x" * 900}))
        self.assertEqual(len(reason), 300)


class TestJudgeKey(unittest.TestCase):
    def test_slot_and_values_cannot_run_together(self):
        """The scheme-1 bug (#242): no separator meant these collided."""
        self.assertEqual(_legacy_judge_key("titl", ["ex"]),
                         _legacy_judge_key("title", ["x"]))
        self.assertNotEqual(_judge_key("titl", ["ex"]),
                            _judge_key("title", ["x"]))

    def test_value_boundaries_cannot_run_together(self):
        self.assertEqual(_legacy_judge_key("title", ["ab", "c"]),
                         _legacy_judge_key("title", ["a", "bc"]))
        self.assertNotEqual(_judge_key("title", ["ab", "c"]),
                            _judge_key("title", ["a", "bc"]))

    def test_order_of_values_does_not_matter(self):
        self.assertEqual(_judge_key("s", ["a", "b"]), _judge_key("s", ["b", "a"]))

    def test_key_tracks_the_cap_so_widening_it_invalidates_the_right_rows(self):
        """The #244 trap.

        Keyed on the full values, raising the cap would leave the key alone and
        every verdict reached on truncated evidence would be served again as
        though it had been reached on the whole of it — the cache would undo
        the fix silently. Keyed on what was sent, only the affected slots move.
        """
        short = ["a", "b"]
        long_pair = ["x" * 50, "x" * 40 + "y" * 10]
        with unittest.mock.patch("data_sheets_schema.agreement.JUDGE_VALUE_CHARS", 30):
            key_short_narrow = _judge_key("s", _sent(short))
            key_long_narrow = _judge_key("s", _sent(long_pair))
        with unittest.mock.patch("data_sheets_schema.agreement.JUDGE_VALUE_CHARS", 100):
            key_short_wide = _judge_key("s", _sent(short))
            key_long_wide = _judge_key("s", _sent(long_pair))
        self.assertEqual(key_short_narrow, key_short_wide,
                         "a slot the cap never touched must stay cached")
        self.assertNotEqual(key_long_narrow, key_long_wide,
                            "a slot the cap bit must re-judge")

    def test_values_beyond_the_cap_are_the_only_difference_hidden(self):
        """Under a narrow cap two values differing only past it look identical."""
        with unittest.mock.patch("data_sheets_schema.agreement.JUDGE_VALUE_CHARS", 10):
            self.assertEqual(_sent(["same_text_AAA", "same_text_BBB"]),
                             ["same_text_", "same_text_"])


class FakeJudge:
    """Equivalent iff every value shares a first word."""

    def __init__(self):
        self.seen = []

    def __call__(self, slot, values):
        self.seen.append(slot)
        heads = {render(v).split()[0] for v in values}
        return len(heads) == 1, "fake"


class FakeEmbedder:
    def __init__(self):
        self.calls = 0
        self.offline_misses = 0

    def similarity(self, texts):
        self.calls += 1
        return 0.5


class TestCompareRecords(unittest.TestCase):
    def test_slots_held_by_one_replicate_are_skipped(self):
        """A slot only one replicate emitted says nothing about agreement.

        Counting it either way would conflate coverage with consistency.
        """
        rows = compare_records({"r1": {"a": 1, "only": 9}, "r2": {"a": 1}})
        self.assertEqual([r.slot for r in rows], ["a"])

    def test_exact_is_computed_on_rendered_values(self):
        rows = compare_records({"r1": {"a": {"x": 1, "y": 2}},
                                "r2": {"a": {"y": 2, "x": 1}}})
        self.assertTrue(rows[0].exact)

    def test_shape_distinguishes_scalar_from_object(self):
        rows = compare_records({"r1": {"s": "text", "o": {"k": 1}},
                                "r2": {"s": "other", "o": {"k": 2}}})
        shapes = {r.slot: r.shape for r in rows}
        self.assertEqual(shapes, {"s": "scalar", "o": "object"})

    def test_truncation_is_flagged(self):
        long_a = "x" * (JUDGE_VALUE_CHARS + 1)
        rows = compare_records({"r1": {"a": long_a, "b": "short"},
                                "r2": {"a": long_a + "!", "b": "brief"}})
        flags = {r.slot: r.truncated for r in rows}
        self.assertEqual(flags, {"a": True, "b": False})

    def test_the_legacy_cap_is_reported_separately(self):
        """What the 4000-char cap would have hidden, at the current cap.

        Both numbers are needed to say what changed between the published run
        and this one without re-deriving the corpus.
        """
        mid = "x" * (LEGACY_JUDGE_VALUE_CHARS + 1)
        rows = compare_records({"r1": {"a": mid}, "r2": {"a": mid + "!"}})
        self.assertFalse(rows[0].truncated)
        self.assertTrue(rows[0].truncated_at_legacy_cap)
        self.assertEqual(rows[0].max_chars, LEGACY_JUDGE_VALUE_CHARS + 2)

    def test_judge_and_embedder_are_both_consulted(self):
        judge, emb = FakeJudge(), FakeEmbedder()
        rows = compare_records({"r1": {"a": "same thing"}, "r2": {"a": "same other"}},
                               embedder=emb, judge=judge)
        self.assertTrue(rows[0].equivalent)
        self.assertEqual(rows[0].similarity, 0.5)
        self.assertEqual(judge.seen, ["a"])

    def test_rows_are_sorted_by_slot(self):
        rows = compare_records({"r1": {"z": 1, "a": 1}, "r2": {"z": 2, "a": 2}})
        self.assertEqual([r.slot for r in rows], ["a", "z"])


class TestEmbedderSimilarity(unittest.TestCase):
    def setUp(self):
        self.emb = Embedder(cache_path=None)

    def test_single_distinct_text_short_circuits(self):
        """No call is made, and the answer is 1.0 rather than undefined."""
        self.assertEqual(self.emb.similarity(["a", "a", "a"]), 1.0)
        self.assertEqual(self.emb.calls, 0)

    def test_cosine_on_known_vectors(self):
        self.emb._vecs = {_digest("a"): [1.0, 0.0], _digest("b"): [0.0, 1.0],
                          _digest("c"): [1.0, 0.0]}
        self.assertAlmostEqual(self.emb.similarity(["a", "b"]), 0.0)
        self.assertAlmostEqual(self.emb.similarity(["a", "c"]), 1.0)

    def test_offline_miss_raises_rather_than_billing(self):
        with self.assertRaises(OfflineCacheMiss):
            Embedder(cache_path=None, offline=True).similarity(["a", "b"])


class TestJudgeCache(unittest.TestCase):
    def test_identical_values_never_reach_the_judge(self):
        judge = EquivalenceJudge(model="m", cache_path=None, offline=True)
        self.assertEqual(judge("a", ["same", "same"]), (True, "identical"))
        self.assertEqual(judge.calls, 0)

    def test_round_trip_through_the_cache_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.jsonl"
            j1 = EquivalenceJudge(model="m", cache_path=path)
            j1._save(_judge_key("slot", _sent(["a", "b"])), "slot", True, "because")
            j2 = EquivalenceJudge(model="m", cache_path=path, offline=True)
            self.assertEqual(j2("slot", ["a", "b"]), (True, "because"))
            self.assertEqual(j2.memo_hits, 1)

    def test_a_different_judge_model_does_not_reuse_the_verdict(self):
        """Two models are two instruments (#243).

        Silently serving one's verdict under the other's name would make a
        model comparison compare nothing.
        """
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.jsonl"
            EquivalenceJudge(model="m1", cache_path=path)._save(
                _judge_key("slot", _sent(["a", "b"])), "slot", True, "because")
            other = EquivalenceJudge(model="m2", cache_path=path, offline=True)
            with self.assertRaises(OfflineCacheMiss):
                other("slot", ["a", "b"])

    def test_the_cache_records_the_cap_it_was_judged_under(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.jsonl"
            EquivalenceJudge(model="m", cache_path=path)._save(
                _judge_key("s", _sent(["a", "b"])), "s", True, "r")
            written = json.loads(path.read_text().splitlines()[0])
            self.assertEqual(written["judge_chars"], JUDGE_VALUE_CHARS)

    def test_a_different_rubric_does_not_reuse_the_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.jsonl"
            path.write_text(json.dumps({"rubric": "not-the-current-one",
                                        "model": "m", "key": _judge_key("s", ["a", "b"]),
                                        "slot": "s", "equivalent": True,
                                        "reason": "stale"}) + "\n")
            judge = EquivalenceJudge(model="m", cache_path=path, offline=True)
            with self.assertRaises(OfflineCacheMiss):
                judge("s", ["a", "b"])

    def test_legacy_records_without_a_model_are_still_readable(self):
        """The 434 published verdicts predate model scoping.

        They are frozen, so reading them is safe; re-running them would restate
        the same answers at full price.
        """
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.jsonl"
            path.write_text(json.dumps({"rubric": _digest(EQUIVALENCE_SYSTEM),
                                        "key": _legacy_judge_key("s", ["a", "b"]),
                                        "slot": "s", "equivalent": False,
                                        "reason": "old"}) + "\n")
            judge = EquivalenceJudge(model="m", cache_path=path, offline=True)
            self.assertEqual(judge("s", ["a", "b"]), (False, "old"))
            self.assertEqual(judge.legacy_hits, 1)

    def test_a_legacy_verdict_reached_on_truncated_evidence_is_not_reused(self):
        """The heart of the #244 fix.

        Legacy records are keyed on the *full* values but were judged on the
        first 4000 characters. Where a value ran past that, the cached answer
        rests on evidence we no longer accept, and reusing it would leave the
        published number exactly where it was while appearing to have fixed it.
        Such a slot must miss the cache and be re-judged.
        """
        long_pair = ["x" * 5000, "x" * 5000 + " but actually different"]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.jsonl"
            path.write_text(json.dumps(
                {"rubric": _digest(EQUIVALENCE_SYSTEM),
                 "key": _legacy_judge_key("s", long_pair),
                 "slot": "s", "equivalent": True,
                 "reason": "identical for the first 4000 chars"}) + "\n")
            judge = EquivalenceJudge(model="m", cache_path=path, offline=True)
            with self.assertRaises(OfflineCacheMiss):
                judge("s", long_pair)
            self.assertEqual(judge.legacy_hits, 0)

    def test_a_legacy_verdict_under_the_old_cap_is_still_reused(self):
        """The other half: don't re-buy 510 verdicts that were never truncated."""
        short_pair = ["a" * 100, "b" * 100]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.jsonl"
            path.write_text(json.dumps(
                {"rubric": _digest(EQUIVALENCE_SYSTEM),
                 "key": _legacy_judge_key("s", short_pair),
                 "slot": "s", "equivalent": False, "reason": "old"}) + "\n")
            judge = EquivalenceJudge(model="m", cache_path=path, offline=True)
            self.assertEqual(judge("s", short_pair), (False, "old"))
            self.assertEqual(judge.legacy_hits, 1)


@unittest.skipUnless((CACHE / "matrix.json").exists(), "agreement cache not present")
class TestPublishedMatrixReproduces(unittest.TestCase):
    """The note's tables must come back out of the committed cache.

    This is the check that `notes/replicate_agreement_2026-08-02.md` is a record
    of something re-runnable rather than a transcript of a session that is gone.
    Offline throughout, so it costs nothing and cannot quietly re-measure.
    """

    def test_matrix_rebuilds_offline_and_matches(self):
        published = json.loads((CACHE / "matrix.json").read_text())
        matrix, _ = build_matrix(root=REPO / "data" / "d4d_concatenated",
                                 cache_dir=CACHE, offline=True)
        self.assertEqual(len(matrix), 8)
        for key, cell in published.items():
            self.assertIn(key, matrix)
            self.assertEqual(matrix[key]["shared"], cell["shared"], key)
            self.assertEqual(matrix[key]["equivalent"], cell["equivalent"], key)
            self.assertAlmostEqual(matrix[key]["rate"], cell["rate"], places=9,
                                   msg=key)

    def test_the_headline_delta_is_smaller_than_the_spread(self):
        """#169's conclusion, as an assertion rather than a paragraph."""
        published = json.loads((CACHE / "matrix.json").read_text())
        v1 = {k.split("|")[1]: v["rate"] for k, v in published.items()
              if k.startswith("v1")}
        v2 = {k.split("|")[1]: v["rate"] for k, v in published.items()
              if k.startswith("v2")}
        deltas = [(v2[p] - v1[p]) * 100 for p in v1]
        mean = sum(deltas) / len(deltas)
        sd = (sum((d - mean) ** 2 for d in deltas) / (len(deltas) - 1)) ** 0.5
        self.assertLess(abs(mean), sd, "effect should be smaller than its spread")
        self.assertTrue(any(d > 0 for d in deltas) and any(d < 0 for d in deltas),
                        "deltas should not agree in sign")

    def test_nothing_in_the_published_matrix_is_truncated(self):
        """#244: the cap must not be biting any cell the note reports.

        If a future record grows past 100k this goes red, which is the point —
        the alternative is a rate quietly measured on partial evidence again.
        """
        published = json.loads((CACHE / "matrix.json").read_text())
        offenders = {k: c["truncated"] for k, c in published.items()
                     if c.get("truncated")}
        self.assertEqual(offenders, {})

    def test_every_cell_records_the_cap_and_model_it_was_judged_under(self):
        published = json.loads((CACHE / "matrix.json").read_text())
        for key, cell in published.items():
            self.assertEqual(cell["judge_chars"], JUDGE_VALUE_CHARS, key)
            self.assertTrue(cell["judge_model"], key)


if __name__ == "__main__":
    unittest.main()
