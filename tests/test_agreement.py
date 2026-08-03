"""Tests for the replicate-agreement measures.

Nothing here touches the network. The judge and embedder are injected, and the
one test that exercises the real cache reads the committed one in offline mode,
where a miss raises instead of billing.
"""

import json
import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from data_sheets_schema.agreement import (
    EMBED_MAX_TOKENS,
    EQUIVALENCE_SYSTEM,
    JUDGE_VALUE_CHARS,
    LEGACY_JUDGE_VALUE_CHARS,
    Embedder,
    EquivalenceJudge,
    OfflineCacheMiss,
    PrefixOnlyEmbedding,
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

    def test_vectors_are_keyed_on_the_text_actually_sent(self):
        """#251, mirroring #244: the cap must be part of the cache identity."""
        long_a = "x" * 200
        long_b = "x" * 190 + "y" * 10
        with unittest.mock.patch("data_sheets_schema.agreement.EMBED_VALUE_CHARS", 100):
            k_a, k_b = _digest(long_a[:100]), _digest(long_b[:100])
        self.assertEqual(k_a, k_b, "identical prefixes collapse under a narrow cap")
        with unittest.mock.patch("data_sheets_schema.agreement.EMBED_VALUE_CHARS", 500):
            self.assertNotEqual(_digest(long_a[:500]), _digest(long_b[:500]))


class TestPrefixOnlyEmbedding(unittest.TestCase):
    """The endpoint truncates at 2048 tokens and answers 200 (#251).

    Measured against the live endpoint: a 30,000-character input returns
    `prompt_tokens: 2048`, and two values differing only past that point come
    back byte-identical at cosine 1.000000, where the same contradiction scores
    0.843 when it fits. These tests pin the client's response to that, without
    calling it.
    """

    def _embedder_returning(self, tokens):
        emb = Embedder(cache_path=None)
        payload = {"data": [{"embedding": [1.0, 0.0]}],
                   "usage": {"prompt_tokens": tokens}}

        class FakeResp:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def read(self_inner):
                return json.dumps(payload).encode()

        return emb, FakeResp

    def test_a_truncated_vector_refuses_to_be_used(self):
        emb, resp = self._embedder_returning(EMBED_MAX_TOKENS)
        with unittest.mock.patch.dict(os.environ, {"CBORG_API_KEY": "x"}), \
             unittest.mock.patch("urllib.request.urlopen", return_value=resp()), \
             unittest.mock.patch("json.load",
                                 lambda f: json.loads(f.read().decode())):
            with self.assertRaises(PrefixOnlyEmbedding):
                emb.vector("a very long value")

    def test_a_vector_inside_the_ceiling_is_returned(self):
        emb, resp = self._embedder_returning(EMBED_MAX_TOKENS - 1)
        with unittest.mock.patch.dict(os.environ, {"CBORG_API_KEY": "x"}), \
             unittest.mock.patch("urllib.request.urlopen", return_value=resp()), \
             unittest.mock.patch("json.load",
                                 lambda f: json.loads(f.read().decode())):
            self.assertEqual(emb.vector("short value"), [1.0, 0.0])

    def test_a_cached_prefix_only_vector_still_refuses(self):
        """The refusal must survive a round trip through the cache file."""
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "e.jsonl"
            emb = Embedder(cache_path=path)
            emb._save(_digest("sent"), [1.0, 0.0], EMBED_MAX_TOKENS, True)
            reloaded = Embedder(cache_path=path, offline=True)
            with self.assertRaises(PrefixOnlyEmbedding):
                reloaded.vector("sent")

    def test_compare_records_records_null_rather_than_a_prefix_cosine(self):
        """A cosine over prefixes must not be filed as a cosine over values."""
        class PrefixEmbedder:
            offline_misses = 0
            prefix_only_skips = 0

            def similarity(self, texts):
                raise PrefixOnlyEmbedding("kept only the head")

        emb = PrefixEmbedder()
        rows = compare_records({"r1": {"a": "x"}, "r2": {"a": "y"}}, embedder=emb)
        self.assertIsNone(rows[0].similarity)
        self.assertEqual(emb.prefix_only_skips, 1)

    def test_a_bare_embedder_needs_no_bookkeeping_attributes(self):
        """#254: the failure path must not demand more than the happy path.

        `embedder` is an injection point. Requiring it to pre-declare counters
        meant the only code that touched them — the error handlers — raised
        AttributeError on any object that had not anticipated them.
        """
        class Bare:
            def similarity(self, texts):
                raise PrefixOnlyEmbedding("kept only the head")

        emb = Bare()
        rows = compare_records({"r1": {"a": "x"}, "r2": {"a": "y"}}, embedder=emb)
        self.assertIsNone(rows[0].similarity)
        self.assertEqual(emb.prefix_only_skips, 1)

    def test_a_bare_embedder_survives_an_offline_miss_too(self):
        class Bare:
            def similarity(self, texts):
                raise OfflineCacheMiss("not cached")

        emb = Bare()
        rows = compare_records({"r1": {"a": "x"}, "r2": {"a": "y"}}, embedder=emb)
        self.assertIsNone(rows[0].similarity)
        self.assertEqual(emb.offline_misses, 1)


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

    def test_a_cap_that_collapses_two_values_into_one_refuses_to_judge(self):
        """#249 — truncation taken to its limit.

        Shown two identical blocks the judge would answer "equivalent",
        correctly on the evidence and wrongly about the dataset. There is no
        honest verdict available at that cap, so there is no verdict.
        """
        judge = EquivalenceJudge(model="m", cache_path=None, offline=True)
        with unittest.mock.patch("data_sheets_schema.agreement.JUDGE_VALUE_CHARS", 5):
            with self.assertRaises(ValueError) as ctx:
                judge("slot", ["AAAAA_tail_X", "AAAAA_tail_Y"])
        self.assertIn("collapses", str(ctx.exception))
        self.assertEqual(judge.calls, 0)

    def test_values_still_distinct_after_the_cap_are_judged_normally(self):
        judge = EquivalenceJudge(model="m", cache_path=None, offline=True)
        with unittest.mock.patch("data_sheets_schema.agreement.JUDGE_VALUE_CHARS", 5):
            with self.assertRaises(OfflineCacheMiss):
                judge("slot", ["AAAAA_x", "BBBBB_y"])

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

    def test_every_published_slot_actually_carries_a_verdict(self):
        """#250 — a rate is only a rate if everything in it was judged."""
        published = json.loads((CACHE / "matrix.json").read_text())
        for key, cell in published.items():
            self.assertEqual(cell["unjudged"], 0, key)
            self.assertIsNotNone(cell["rate"], key)

    def test_the_embedding_proxy_still_fails_to_discriminate(self):
        """The negative result, asserted rather than merely reproducible (#247).

        This is the finding that closes off the cheap route: cosine similarity
        cannot separate slots the judge called equivalent from slots it called
        different, because every value is schema-shaped prose about the same
        dataset and the embedding measures topic. Recomputed here from the
        committed per-slot rows — no vectors needed, which is the point.

        It is pinned because it is the kind of result someone will want to
        re-litigate when the judge's cost comes up, and a number in a note is
        easier to wave away than a red test.
        """
        rows = json.loads((CACHE / "CHORUS_v2_rows.json").read_text())
        # `is True` / `is False`, not truthiness: `equivalent` is tri-state and
        # an unjudged row is None. Splitting on truthiness would file it under
        # "judged, and they differed" — the #250 bug, which this very test
        # would otherwise reintroduce while pinning the finding it protects.
        self.assertTrue(all(r["equivalent"] is not None for r in rows),
                        "every row must carry a verdict for the means to mean anything")
        self.assertTrue(all(r["similarity"] is not None for r in rows),
                        "and a similarity, or the sample is not what it claims")
        eq = [r["similarity"] for r in rows if r["equivalent"] is True]
        df = [r["similarity"] for r in rows if r["equivalent"] is False]
        self.assertEqual(len(eq) + len(df), len(rows), "no row may be dropped")
        self.assertEqual((len(eq), len(df)), (18, 30))
        mean_eq, mean_df = sum(eq) / len(eq), sum(df) / len(df)
        self.assertAlmostEqual(mean_eq, 0.92272, places=4)
        self.assertAlmostEqual(mean_df, 0.91442, places=4)
        self.assertLess(mean_eq - mean_df, 0.01,
                        "if the gap ever exceeds a point, the proxy is worth "
                        "revisiting and this test should be the thing that says so")

    def test_the_tracked_vector_cache_stays_small(self):
        """#247: growth here is permanent, so it should be a decision.

        Nothing in git can be un-committed — this blob is already in history at
        587 KB packed, so deleting it from HEAD would reclaim exactly nothing.
        What *is* still available is refusing to add ten times more of it. The
        cache holds 136 vectors, one per distinct CHORUS v2 value; embedding
        the whole corpus would be 1439 vectors, about 14 MB, tracked forever.

        If you meant to do that, raise this bound in the same commit and say
        why. The number existing is the point; its exact value is not.
        """
        path = CACHE / "embeddings.jsonl"
        vectors = sum(1 for line in path.read_text().splitlines() if line.strip())
        self.assertLessEqual(vectors, 200,
                             f"{vectors} vectors tracked; a full-corpus sweep "
                             "is ~1439 and adds ~14 MB to history permanently")

    def test_missing_similarity_is_counted_rather_than_left_to_be_inferred(self):
        """#253 — only CHORUS v2 was ever embedded; the rest must say so."""
        published = json.loads((CACHE / "matrix.json").read_text())
        for key, cell in published.items():
            self.assertIn("similarity_absent", cell)
        chorus_v2 = next(c for k, c in published.items()
                         if k.startswith("v2") and k.endswith("CHORUS"))
        self.assertEqual(chorus_v2["similarity_absent"], 0,
                         "CHORUS v2 is the one cell with a full similarity column")
        others = [c["similarity_absent"] for k, c in published.items()
                  if not (k.startswith("v2") and k.endswith("CHORUS"))]
        self.assertTrue(all(n > 0 for n in others),
                        "every other cell is missing similarity and must record it")


class TestUnjudgedSlotsAreNotCountedAsDisagreement(unittest.TestCase):
    """#250: `bool(None)` is False, which reads as "judged, and they differed"."""

    def test_an_unjudged_slot_is_none_not_false(self):
        rows = compare_records({"r1": {"a": "x"}, "r2": {"a": "y"}})
        self.assertIsNone(rows[0].equivalent)

    def test_the_three_states_are_distinguishable(self):
        """Judged-equivalent, judged-different and unjudged must not merge."""
        judged_yes = SlotAgreement("a", 2, False, equivalent=True)
        judged_no = SlotAgreement("b", 2, False, equivalent=False)
        unjudged = SlotAgreement("c", 2, False, equivalent=None)
        rows = [judged_yes, judged_no, unjudged]
        self.assertEqual(sum(r.equivalent is True for r in rows), 1)
        self.assertEqual(sum(r.equivalent is False for r in rows), 1)
        self.assertEqual(sum(r.equivalent is None for r in rows), 1)
        # The bug: bool() folds the unjudged row into the disagreements.
        self.assertEqual(sum(bool(r.equivalent) for r in rows), 1)
        self.assertEqual(len(rows) - sum(bool(r.equivalent) for r in rows), 2)


if __name__ == "__main__":
    unittest.main()
