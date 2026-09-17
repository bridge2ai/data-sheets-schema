"""scripts/agentic_observed.py — totals and bundle coverage from transcripts (#700, #688)."""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("agentic_observed", ROOT / "scripts" / "agentic_observed.py")
ao = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ao)


_IDS = iter(range(1, 10_000))


def _event(ts, usage=None, tools=(), msg_id=None, results=(), ids=None):
    """One transcript line. Tool-use ids are unique per call, as in real
    transcripts; pass `ids` to fix them when a later event must reference one."""
    ids = list(ids) if ids else [f"tu-{next(_IDS)}" for _ in tools]
    content = [{"type": "tool_use", "name": n, "input": i, "id": tid}
               for tid, (n, i) in zip(ids, tools)]
    content += [{"type": "tool_result", "tool_use_id": tid, "is_error": err, "content": "x"}
                for tid, err in results]
    msg = {"role": "assistant", "content": content}
    if usage is not None:
        msg["usage"] = usage
    if msg_id:
        msg["id"] = msg_id
    return json.dumps({"timestamp": ts, "message": msg, "uuid": ts})


class Observe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / "P_preprocessed.txt"
        self.bundle.write_text("\n".join(f"line {i}" for i in range(3000)) + "\n")

    def _transcript(self, name, lines):
        p = self.root / name
        p.write_text("\n".join(lines) + "\n")
        return p

    def test_totals_and_coverage_from_one_transcript(self):
        t = self._transcript("a.jsonl", [
            _event("2026-08-27T00:00:00Z",
                   usage={"input_tokens": 10, "cache_read_input_tokens": 100,
                          "cache_creation_input_tokens": 5, "output_tokens": 7},
                   tools=[("Read", {"file_path": str(self.bundle)})]),
            _event("2026-08-27T00:01:00Z",
                   usage={"input_tokens": 1, "output_tokens": 1},
                   tools=[("Read", {"file_path": str(self.bundle), "offset": 2001, "limit": 500}),
                          ("Grep", {"pattern": "x", "path": str(self.bundle)})]),
        ])
        obs = ao.observe([t], self.bundle)
        self.assertEqual(obs["total_tokens"], 124)
        self.assertEqual(obs["tool_uses"], 3)
        self.assertEqual(obs["duration_ms"], 60000)
        # default window 0..2000 plus 2000..2500 → 2500 of 3000; the grep is
        # a touch, not a read
        self.assertEqual(obs["bundle_lines_read"], 2500)
        self.assertEqual(obs["bundle_lines_total"], 3000)
        self.assertEqual(obs["_bundle_search_touches"], 1)

    def test_two_invocations_are_summed_and_windows_unioned(self):
        a = self._transcript("a.jsonl", [_event("2026-08-27T00:00:00Z",
            usage={"output_tokens": 5}, tools=[("Read", {"file_path": str(self.bundle), "limit": 1000})])])
        b = self._transcript("b.jsonl", [_event("2026-08-27T02:00:00Z",
            usage={"output_tokens": 6}, tools=[("Read", {"file_path": str(self.bundle), "offset": 501, "limit": 1000})]),
            _event("2026-08-27T02:00:30Z", usage={"output_tokens": 1})])
        obs = ao.observe([a, b], self.bundle)
        self.assertEqual(obs["total_tokens"], 12)
        self.assertEqual(obs["duration_ms"], 30000)   # each transcript's own span
        self.assertEqual(obs["bundle_lines_read"], 1500)   # 0..1000 ∪ 500..1500

    def test_one_api_message_over_several_lines_is_counted_once(self):
        """#701 review F1: a response spans several JSONL lines sharing a
        message id, each repeating the input counts — summing per line
        roughly doubled every run_observed total in the corpus."""
        u1 = {"input_tokens": 100, "cache_read_input_tokens": 1000, "output_tokens": 1}
        u2 = {"input_tokens": 100, "cache_read_input_tokens": 1000, "output_tokens": 227}
        t = self._transcript("a.jsonl", [
            _event("2026-08-27T00:00:00Z", usage=u1, msg_id="msg_1"),
            _event("2026-08-27T00:00:01Z", usage=u2, msg_id="msg_1"),
            _event("2026-08-27T00:00:02Z", usage={"output_tokens": 3}, msg_id="msg_2"),
        ])
        obs = ao.observe([t], None)
        self.assertEqual(obs["total_tokens"], 100 + 1000 + 227 + 3)

    def test_an_errored_read_does_not_count_as_read(self):
        """#701 review F2: the tool caps a read at ~25k tokens and returns an
        error; 17 such reads in the v5 arm were counted as coverage."""
        t = self._transcript("a.jsonl", [
            _event("2026-08-27T00:00:00Z", usage={"output_tokens": 1}, ids=["big"],
                   tools=[("Read", {"file_path": str(self.bundle), "limit": 2000})]),
            _event("2026-08-27T00:00:01Z", results=[("big", True)]),
            _event("2026-08-27T00:00:02Z", usage={"output_tokens": 1}, ids=["small"],
                   tools=[("Read", {"file_path": str(self.bundle), "limit": 500})]),
            _event("2026-08-27T00:00:03Z", results=[("small", False)]),
        ])
        obs = ao.observe([t], self.bundle)
        self.assertEqual(obs["bundle_lines_read"], 500)
        self.assertEqual(obs["_bundle_reads_failed"], 1)

    def test_until_cuts_post_run_activity(self):
        """An agent that keeps acting after its run is not the run."""
        from datetime import datetime, timezone
        t = self._transcript("a.jsonl", [
            _event("2026-08-27T00:00:00Z", usage={"output_tokens": 1}, msg_id="m1"),
            _event("2026-08-27T00:10:00Z", usage={"output_tokens": 2}, msg_id="m2"),
            _event("2026-08-27T01:00:00Z", usage={"output_tokens": 40}, msg_id="m3",
                   tools=[("Bash", {"command": "env"})]),
        ])
        cut = datetime(2026, 8, 27, 0, 30, tzinfo=timezone.utc)
        obs = ao.observe([t], None, until=cut)
        self.assertEqual(obs["total_tokens"], 3)
        self.assertEqual(obs["tool_uses"], 0)
        self.assertEqual(obs["duration_ms"], 600000)

    def test_receipt_chunks_the_transcript_never_opened_are_counted(self):
        """#709: the receipt is the claim, the read windows the observation."""
        import yaml
        manifest = self.root / "P_chunks.yaml"
        manifest.write_text(yaml.safe_dump({"chunks": [
            {"id": "c001", "lines": [1, 1000]}, {"id": "c002", "lines": [1001, 2000]},
            {"id": "c003", "lines": [2001, 3000]}]}))
        receipt = self.root / "P_coverage_receipt.yaml"
        receipt.write_text(yaml.safe_dump({"chunks": [
            {"id": "c001", "status": "extracted"}, {"id": "c002", "status": "nothing_relevant"},
            {"id": "c003", "status": "nothing_relevant"}, {"id": "c999", "status": "nothing_relevant"}]}))
        t = self._transcript("a.jsonl", [
            _event("2026-08-27T00:00:00Z", usage={"output_tokens": 1},
                   tools=[("Read", {"file_path": str(self.bundle), "offset": 1, "limit": 2000})]),
            # c003 read through a shell: honest, invisible, counted as unopened
            _event("2026-08-27T00:01:00Z", usage={"output_tokens": 1},
                   tools=[("Bash", {"command": f"sed -n 2001,3000p {self.bundle}"})]),
        ])
        obs = ao.observe([t], self.bundle, receipt=receipt, manifest=manifest)
        self.assertEqual(obs["receipt_chunks_total"], 3)          # the manifest's count (#732)
        self.assertEqual(obs["receipt_chunks_unopened"], 1)
        self.assertEqual(obs["_receipt_unopened_ids"], ["c003"])
        self.assertEqual(obs["_receipt_strangers"], ["c999"])
        # a receipt of bogus ids is not 0/0
        receipt.write_text(yaml.safe_dump({"chunks": [{"id": "zzz"}, {"id": "c001"}, {"id": "c001"}]}))
        obs = ao.observe([t], self.bundle, receipt=receipt, manifest=manifest)
        self.assertEqual(obs["receipt_chunks_total"], 3)
        self.assertEqual(obs["_receipt_duplicates"], ["c001"]); self.assertEqual(obs["_receipt_unclaimed"], ["c002", "c003"])
        receipt.write_text(yaml.safe_dump({"chunks": [
            {"id": "c001", "status": "extracted"}, {"id": "c002", "status": "nothing_relevant"},
            {"id": "c003", "status": "nothing_relevant"}]}))
        # a chunk read in two smaller windows that cover it is opened (#736)
        t3 = self._transcript("c.jsonl", [
            _event("2026-08-27T00:00:00Z", usage={"output_tokens": 1},
                   tools=[("Read", {"file_path": str(self.bundle), "offset": 1, "limit": 1500}),
                          ("Read", {"file_path": str(self.bundle), "offset": 1501, "limit": 1500})])])
        self.assertEqual(ao.observe([t3], self.bundle, receipt=receipt, manifest=manifest)["receipt_chunks_unopened"], 0)
        # a partly-opened chunk is unopened: the receipt claims the whole chunk
        t2 = self._transcript("b.jsonl", [
            _event("2026-08-27T00:00:00Z", usage={"output_tokens": 1},
                   tools=[("Read", {"file_path": str(self.bundle), "offset": 1, "limit": 1500})])])
        self.assertEqual(ao.observe([t2], self.bundle, receipt=receipt, manifest=manifest)["receipt_chunks_unopened"], 2)

    def test_no_bundle_means_no_coverage_keys(self):
        t = self._transcript("a.jsonl", [_event("2026-08-27T00:00:00Z", usage={"output_tokens": 1})])
        obs = ao.observe([t], None)
        self.assertNotIn("bundle_lines_read", obs)
        self.assertEqual(obs["total_tokens"], 1)


if __name__ == "__main__":
    unittest.main()


class StringMessageLines(unittest.TestCase):
    """Claude Code 2.1.272 stream-json writes some lines whose `message` is a
    string; the observer crashed on them (#1915) and a native run under that
    runtime could not be observed at all."""

    def test_a_string_message_line_is_skipped_not_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bundle = root / "P_preprocessed.txt"
            bundle.write_text("\n".join(f"line {i}" for i in range(100)) + "\n")
            lines = [
                json.dumps({"timestamp": "2026-09-16T21:52:20Z", "type": "system", "message": "API Error: 402 stopped", "uuid": "a"}),
                _event("2026-09-16T21:52:21Z", usage={"output_tokens": 5},
                       tools=[("Read", {"file_path": str(bundle), "offset": 1, "limit": 100})], msg_id="m1"),
                json.dumps({"timestamp": "2026-09-16T21:52:22Z", "type": "result", "message": "done", "uuid": "b"}),
            ]
            t = root / "t.jsonl"; t.write_text("\n".join(lines) + "\n")
            obs = ao.observe([t], bundle, None, None, None)
        self.assertEqual(obs["output_tokens"], 5)
        self.assertEqual(obs["bundle_lines_read"], 100)
        self.assertNotIn("malformed_message_events", obs)

    def test_a_malformed_assistant_or_user_message_is_counted_not_hidden(self):
        """#1926: a measurement-bearing event whose message is not a mapping
        must be surfaced, or a broken transcript reads as a clean one."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bundle = root / "P_preprocessed.txt"
            bundle.write_text("\n".join(f"line {i}" for i in range(100)) + "\n")
            lines = [
                _event("2026-09-16T21:52:21Z", usage={"output_tokens": 5},
                       tools=[("Read", {"file_path": str(bundle), "offset": 1, "limit": 100})], msg_id="m1"),
                json.dumps({"timestamp": "2026-09-16T21:52:22Z", "type": "user", "message": ["error"], "uuid": "b"}),
            ]
            t = root / "t.jsonl"; t.write_text("\n".join(lines) + "\n")
            obs = ao.observe([t], bundle, None, None, None)
        self.assertEqual(obs["malformed_message_events"], 1)


class TerminalResultUsage(unittest.TestCase):
    """Claude Code 2.1.272 stream-json: assistant events carry initial usage
    snapshots only; the terminal `result` event carries the session's
    finalized usage (#1931). Without it the retained v10q transcript read
    344 output tokens against the runtime's 118,696."""

    def test_finalized_usage_from_the_terminal_result_wins(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bundle = root / "P_preprocessed.txt"
            bundle.write_text("\n".join(f"line {i}" for i in range(100)) + "\n")
            lines = [
                _event("2026-09-16T21:52:21Z", usage={"output_tokens": 3},
                       tools=[("Read", {"file_path": str(bundle), "offset": 1, "limit": 100})], msg_id="m1"),
                _event("2026-09-16T21:52:25Z", usage={"output_tokens": 17}, msg_id="m2"),
                json.dumps({"timestamp": "2026-09-16T22:21:00Z", "type": "result", "message": "done", "uuid": "r",
                            "usage": {"input_tokens": 7367, "cache_creation_input_tokens": 212559,
                                      "cache_read_input_tokens": 4326307, "output_tokens": 118696,
                                      "output_tokens_details": {"thinking_tokens": 74283}}}),
            ]
            t = root / "t.jsonl"; t.write_text("\n".join(lines) + "\n")
            obs = ao.observe([t], bundle, None, None, None)
        self.assertEqual(obs["output_tokens"], 118696)
        self.assertEqual(obs["thinking_tokens"], 74283)
        self.assertEqual(obs["total_tokens"], 7367 + 212559 + 4326307 + 118696)
        self.assertEqual(obs["usage_from_terminal_result"], 1)
        self.assertGreater(obs["reasoning_tokens_estimate"], 100000)
        self.assertEqual(obs["bundle_lines_read"], 100)

    def test_without_a_terminal_result_the_snapshot_maximum_stands(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bundle = root / "P_preprocessed.txt"; bundle.write_text("x\n")
            lines = [_event("2026-09-16T21:52:21Z", usage={"output_tokens": 3}, msg_id="m1"),
                     _event("2026-09-16T21:52:22Z", usage={"output_tokens": 9}, msg_id="m1")]
            t = root / "t.jsonl"; t.write_text("\n".join(lines) + "\n")
            obs = ao.observe([t], bundle, None, None, None)
        self.assertEqual(obs["output_tokens"], 9)
        self.assertNotIn("usage_from_terminal_result", obs)

    def test_an_empty_message_on_a_measurement_event_is_malformed_too(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bundle = root / "P_preprocessed.txt"; bundle.write_text("x\n")
            lines = [json.dumps({"timestamp": "2026-09-16T21:52:21Z", "type": "assistant", "message": "", "uuid": "a"}),
                     json.dumps({"timestamp": "2026-09-16T21:52:22Z", "type": "user", "message": [], "uuid": "b"}),
                     json.dumps({"timestamp": "2026-09-16T21:52:23Z", "type": "system", "message": "", "uuid": "c"})]
            t = root / "t.jsonl"; t.write_text("\n".join(lines) + "\n")
            obs = ao.observe([t], bundle, None, None, None)
        self.assertEqual(obs["malformed_message_events"], 2)


class TerminalResultPerInvocation(unittest.TestCase):
    """Codex round 3 on #1920 (#1935–#1937): a terminal result describes one
    invocation, not every transcript of a resumed run; an untimestamped one
    must not defeat `--until`; and the estimate method changes only where
    the session totals are all there is."""

    @staticmethod
    def _terminal(output, ts=None):
        d = {"type": "result", "message": "done", "uuid": f"r{output}",
             "usage": {"input_tokens": 10, "cache_creation_input_tokens": 0,
                       "cache_read_input_tokens": 0, "output_tokens": output}}
        if ts:
            d["timestamp"] = ts
        return json.dumps(d)

    def _files(self, root):
        bundle = root / "P_preprocessed.txt"; bundle.write_text("x\n")
        a = root / "a.jsonl"
        a.write_text("\n".join([_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="a1"),
                                self._terminal(100)]) + "\n")
        b = root / "b.jsonl"
        b.write_text("\n".join([_event("2026-09-16T22:00:00Z", usage={"output_tokens": 4}, msg_id="b1"),
                                self._terminal(200)]) + "\n")
        c = root / "c.jsonl"   # resumed without a terminal result: snapshot accounting
        c.write_text("\n".join([_event("2026-09-16T23:00:00Z", usage={"output_tokens": 2}, msg_id="c1"),
                                _event("2026-09-16T23:00:01Z", usage={"output_tokens": 9}, msg_id="c1")]) + "\n")
        return bundle, a, b, c

    def test_each_finalized_invocation_counts_once_in_either_order(self):
        with tempfile.TemporaryDirectory() as d:
            bundle, a, b, c = self._files(Path(d))
            ab = ao.observe([a, b], bundle, None, None, None)
            ba = ao.observe([b, a], bundle, None, None, None)
        self.assertEqual(ab["output_tokens"], 300); self.assertEqual(ab["total_tokens"], 320)
        self.assertEqual(ab["usage_from_terminal_result"], 2)
        self.assertEqual({k: v for k, v in ab.items() if k != "duration_ms"},
                         {k: v for k, v in ba.items() if k != "duration_ms"})

    def test_a_transcript_without_a_terminal_result_keeps_its_snapshot_maximum(self):
        with tempfile.TemporaryDirectory() as d:
            bundle, a, b, c = self._files(Path(d))
            ac = ao.observe([a, c], bundle, None, None, None)
            ca = ao.observe([c, a], bundle, None, None, None)
        self.assertEqual(ac["output_tokens"], 109); self.assertEqual(ac["usage_from_terminal_result"], 1)
        self.assertEqual(ac["assistant_turns"], 2)
        self.assertEqual(ca["output_tokens"], 109)

    def test_an_untimestamped_terminal_result_does_not_defeat_until(self):
        until = datetime.fromisoformat("2026-09-16T20:00:00+00:00")     # before the run
        with tempfile.TemporaryDirectory() as d:
            bundle, a, b, c = self._files(Path(d))
            obs = ao.observe([a, b], bundle, until, None, None)
            # a cut after the run's only message still uses the finalized totals
            later = ao.observe([a], bundle, datetime.fromisoformat("2026-09-16T21:30:00+00:00"), None, None)
            # a timestamped terminal result after the cut is cut like any event
            t = Path(d) / "t.jsonl"
            t.write_text("\n".join([_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="t1"),
                                    self._terminal(100, "2026-09-16T21:40:00Z")]) + "\n")
            timed = ao.observe([t], bundle, datetime.fromisoformat("2026-09-16T21:30:00+00:00"), None, None)
        self.assertEqual(obs.get("output_tokens", 0), 0); self.assertEqual(obs["total_tokens"], 0)
        self.assertEqual(obs["tool_uses"], 0); self.assertNotIn("usage_from_terminal_result", obs)
        self.assertEqual(later["output_tokens"], 100); self.assertEqual(later["usage_from_terminal_result"], 1)
        self.assertEqual(timed["output_tokens"], 3); self.assertNotIn("usage_from_terminal_result", timed)

    def test_the_estimate_is_per_message_unless_only_session_totals_exist(self):
        def text_event(ts, out, chars, mid):
            msg = {"role": "assistant", "id": mid, "usage": {"output_tokens": out},
                   "content": [{"type": "text", "text": "v" * chars}]}
            return json.dumps({"timestamp": ts, "message": msg, "uuid": ts})
        lines = [text_event("2026-09-16T21:00:00Z", 1, 12, "m1"), text_event("2026-09-16T21:00:01Z", 5, 0, "m2")]
        with tempfile.TemporaryDirectory() as d:
            bundle = Path(d) / "P_preprocessed.txt"; bundle.write_text("x\n")
            snap = Path(d) / "s.jsonl"; snap.write_text("\n".join(lines) + "\n")
            fin = Path(d) / "f.jsonl"; fin.write_text("\n".join(lines + [self._terminal(6)]) + "\n")
            per_message = ao.observe([snap], bundle, None, None, None)
            pooled = ao.observe([fin], bundle, None, None, None)
            both = ao.observe([snap, fin], bundle, None, None, None)
        self.assertEqual(per_message["reasoning_tokens_estimate"], 5)   # max(0, 1-3) + max(0, 5-0)
        self.assertEqual(pooled["reasoning_tokens_estimate"], 3)        # 6 - 12 // 4, over the session
        self.assertEqual(both["overlapping_evidence"], 2)               # two files carrying one message each: refused, not reconciled (#1972)


class AmbiguousEvidence(unittest.TestCase):
    """Codex rounds 4–8 on #1920 (#1944, #1950, #1960, #1965–#1968, #1972–#1976):
    evidence that does not fit one invocation per file is refused, not
    reconciled, and the refusal reaches every consumer like a malformed event."""

    @staticmethod
    def _terminal(output, ts=None, uuid=None):
        d = {"type": "result", "message": "done", "uuid": uuid or f"r{output}",
             "usage": {"input_tokens": 10, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": output}}
        if ts:
            d["timestamp"] = ts
        return json.dumps(d)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / "P_preprocessed.txt"; self.bundle.write_text("x\n")

    def _file(self, name, lines):
        p = self.root / name; p.write_text("\n".join(lines) + "\n"); return p

    def test_a_copy_cut_short_beside_the_complete_file_is_refused(self):
        lines = [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"),
                 _event("2026-09-16T21:05:00Z", usage={"output_tokens": 5}, msg_id="m2"), self._terminal(100)]
        full = self._file("full.jsonl", lines); prefix = self._file("prefix.jsonl", lines[:2])
        alone = ao.observe([full], self.bundle, None, None, None)
        self.assertEqual(alone["output_tokens"], 100); self.assertNotIn("overlapping_evidence", alone)
        for order in ([prefix, full], [full, prefix]):
            self.assertEqual(ao.observe(order, self.bundle, None, None, None)["overlapping_evidence"], 2)

    def test_a_message_after_a_result_a_second_result_and_a_repeated_result_are_refused(self):
        after = self._file("after.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"), self._terminal(100),
                                           _event("2026-09-16T21:10:00Z", usage={"output_tokens": 9}, msg_id="m2")])
        self.assertEqual(ao.observe([after], self.bundle, None, None, None)["overlapping_evidence"], 1)
        twice = self._file("twice.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"),
                                           self._terminal(100), self._terminal(100, uuid="r-again")])
        self.assertEqual(ao.observe([twice], self.bundle, None, None, None)["overlapping_evidence"], 1)
        a = self._file("a.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"), self._terminal(100)])
        copy = self._file("copy.jsonl", [self._terminal(100)])          # the same result under the same identity
        self.assertEqual(ao.observe([a, copy], self.bundle, None, None, None)["overlapping_evidence"], 1)

    def test_distinct_invocations_still_sum(self):
        a = self._file("a.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"),
                                   _event("2026-09-16T21:01:00Z", usage={"output_tokens": 3}, msg_id="m1"), self._terminal(100)])
        b = self._file("b.jsonl", [_event("2026-09-16T22:00:00Z", usage={"output_tokens": 4}, msg_id="m2"),
                                   _event("2026-09-16T22:01:00Z", usage={"output_tokens": 4}, msg_id="m2")])
        obs = ao.observe([a, b], self.bundle, None, None, None)
        self.assertEqual(obs["output_tokens"], 104); self.assertEqual(obs["duration_ms"], 120_000)
        self.assertEqual(obs["usage_from_terminal_result"], 1); self.assertNotIn("overlapping_evidence", obs)
        self.assertEqual(obs, ao.observe([b, a], self.bundle, None, None, None))

    def test_thinking_from_a_terminal_result_claims_no_turn_coverage(self):
        t = self._file("t.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"),
                                   json.dumps({"type": "result", "message": "done", "uuid": "r",
                                               "usage": {"input_tokens": 1, "output_tokens": 50,
                                                         "output_tokens_details": {"thinking_tokens": 20}}})])
        obs = ao.observe([t], self.bundle, None, None, None)
        self.assertEqual(obs["thinking_tokens"], 20); self.assertNotIn("turns_with_thinking_tokens", obs)

    def test_trailing_events_after_a_result_and_a_set_aside_result(self):
        t = self._file("t.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"),
                                   self._terminal(100, ts="2026-09-16T21:01:00Z"),
                                   json.dumps({"timestamp": "2026-09-16T21:02:00Z", "type": "user", "uuid": "u",
                                               "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": "late"}]}})])
        kept = ao.observe([t], self.bundle, datetime.fromisoformat("2026-09-16T21:01:00+00:00"), None, None)
        self.assertEqual(kept["output_tokens"], 100); self.assertNotIn("terminal_results_excluded_by_cut", kept)
        s = self._file("s.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"),
                                   _event("2026-09-16T21:09:00Z", usage={"output_tokens": 0}, msg_id="m3"), self._terminal(1000)])
        cut = ao.observe([s], self.bundle, datetime.fromisoformat("2026-09-16T21:05:00+00:00"), None, None)
        self.assertEqual(cut["output_tokens"], 3); self.assertEqual(cut["terminal_results_excluded_by_cut"], 1)
        late = self._file("late.jsonl", [_event("2026-09-16T23:00:00Z", usage={"output_tokens": 5}, msg_id="m9"),
                                         self._terminal(50, ts="2026-09-16T23:01:00Z")])
        both = ao.observe([t, late], self.bundle, datetime.fromisoformat("2026-09-16T22:00:00+00:00"), None, None)
        self.assertEqual(both, ao.observe([t], self.bundle, datetime.fromisoformat("2026-09-16T22:00:00+00:00"), None, None))



class Round9(unittest.TestCase):
    """#1979–#1983: repeated paths, shared tool ids, excluded second results,
    mixed thinking sources and id-less copies."""

    @staticmethod
    def _terminal(output, ts=None, uuid=None, thinking=None):
        u = {"input_tokens": 10, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": output}
        if thinking is not None:
            u["output_tokens_details"] = {"thinking_tokens": thinking}
        d = {"type": "result", "message": "done", "uuid": uuid or f"r{output}", "usage": u}
        if ts:
            d["timestamp"] = ts
        return json.dumps(d)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / "P_preprocessed.txt"; self.bundle.write_text("\n".join(f"l{i}" for i in range(10)) + "\n")

    def _file(self, name, lines):
        p = self.root / name; p.write_text("\n".join(lines) + "\n"); return p

    def test_the_same_path_twice_is_refused(self):
        t = self._file("t.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1")])
        once = ao.observe([t], self.bundle, None, None, None); twice = ao.observe([t, t], self.bundle, None, None, None)
        self.assertEqual(twice["output_tokens"], once["output_tokens"]); self.assertEqual(twice["overlapping_evidence"], 1)

    def test_a_tool_id_shared_by_two_files_is_refused(self):
        a = self._file("a.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1",
                                          tools=[("Read", {"file_path": str(self.bundle), "offset": 1, "limit": 1})], ids=["shared"])])
        b = self._file("b.jsonl", [_event("2026-09-16T22:00:00Z", usage={"output_tokens": 4}, msg_id="m2",
                                          tools=[("Read", {"file_path": str(self.bundle), "offset": 1, "limit": 2})], ids=["shared"])])
        for order in ([a, b], [b, a]):
            self.assertEqual(ao.observe(order, self.bundle, None, None, None)["overlapping_evidence"], 1)

    def test_a_cut_excluded_second_result_is_refused(self):
        t = self._file("t.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"), self._terminal(100),
                                   self._terminal(200, ts="2026-09-16T22:00:00Z", uuid="r-late")])
        obs = ao.observe([t], self.bundle, datetime.fromisoformat("2026-09-16T21:30:00+00:00"), None, None)
        self.assertEqual(obs["overlapping_evidence"], 1)

    def test_mixed_thinking_sources_claim_no_turn_coverage(self):
        a = self._file("a.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"), self._terminal(100, thinking=80)])
        b = self._file("b.jsonl", [_event("2026-09-16T22:00:00Z", usage={"output_tokens": 4, "output_tokens_details": {"thinking_tokens": 7}}, msg_id="m2")])
        obs = ao.observe([a, b], self.bundle, None, None, None)
        self.assertEqual(obs["thinking_tokens"], 87); self.assertNotIn("turns_with_thinking_tokens", obs)
        self.assertEqual(ao.observe([b], self.bundle, None, None, None)["turns_with_thinking_tokens"], 1)

    def test_an_id_less_byte_identical_copy_is_refused(self):
        line = json.dumps({"timestamp": "2026-09-16T21:00:00Z", "uuid": "u1", "message": {"role": "assistant", "usage": {"output_tokens": 30}, "content": []}})
        a = self._file("a.jsonl", [line]); b = self._file("b.jsonl", [line])
        self.assertEqual(ao.observe([a], self.bundle, None, None, None)["output_tokens"], 30)
        self.assertEqual(ao.observe([a, b], self.bundle, None, None, None)["overlapping_evidence"], 1)


class Round10(unittest.TestCase):
    """#1986–#1989: byte-identical and hard-linked copies, terminal results
    without thinking detail, tool calls after a result, and a result event
    carrying a mapping message."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / "P_preprocessed.txt"; self.bundle.write_text("\n".join(f"l{i}" for i in range(10)) + "\n")

    def _file(self, name, lines):
        p = self.root / name; p.write_text("\n".join(lines) + "\n"); return p

    def test_a_copy_with_no_ids_at_all_and_a_hard_link_are_refused(self):
        lines = [json.dumps({"timestamp": "2026-09-16T21:00:00Z", "message": {"role": "assistant", "usage": {"output_tokens": 30}, "content": []}}),
                 json.dumps({"timestamp": "2026-09-16T21:01:00Z", "message": {"role": "assistant", "usage": {"output_tokens": 40}, "content": []}})]
        a = self._file("a.jsonl", lines); b = self._file("b.jsonl", lines)
        self.assertEqual(ao.observe([a], self.bundle, None, None, None)["output_tokens"], 70)
        self.assertEqual(ao.observe([a, b], self.bundle, None, None, None)["overlapping_evidence"], 1)
        link = self.root / "link.jsonl"; import os; os.link(a, link)
        self.assertEqual(ao.observe([a, link], self.bundle, None, None, None)["overlapping_evidence"], 1)

    def test_a_terminal_result_without_thinking_detail_keeps_per_turn_coverage(self):
        t = self._file("t.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3, "output_tokens_details": {"thinking_tokens": 7}}, msg_id="m1"),
                                   json.dumps({"type": "result", "message": "done", "uuid": "r", "usage": {"input_tokens": 1, "output_tokens": 100}})])
        obs = ao.observe([t], self.bundle, None, None, None)
        self.assertEqual(obs["thinking_tokens"], 7); self.assertEqual(obs["turns_with_thinking_tokens"], 1)
        self.assertEqual(obs["usage_from_terminal_result"], 1)

    def test_a_tool_call_after_the_result_is_refused(self):
        t = self._file("t.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"),
                                   json.dumps({"type": "result", "message": "done", "uuid": "r", "usage": {"input_tokens": 1, "output_tokens": 100}}),
                                   json.dumps({"timestamp": "2026-09-16T21:02:00Z", "type": "assistant", "uuid": "late",
                                               "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Read", "id": "tu-late",
                                                                                              "input": {"file_path": str(self.bundle), "offset": 1, "limit": 3}}]}})])
        obs = ao.observe([t], self.bundle, None, None, None)
        self.assertEqual(obs["overlapping_evidence"], 1); self.assertEqual(obs["tool_uses"], 0); self.assertEqual(obs["bundle_lines_read"], 0)

    def test_an_excluded_result_with_a_mapping_message_is_still_a_result(self):
        t = self._file("t.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"),
                                   json.dumps({"timestamp": "2026-09-16T22:00:00Z", "type": "result", "message": {}, "uuid": "r1", "usage": {"input_tokens": 1, "output_tokens": 100}}),
                                   json.dumps({"timestamp": "2026-09-16T22:01:00Z", "type": "result", "message": {}, "uuid": "r2", "usage": {"input_tokens": 1, "output_tokens": 100}})])
        obs = ao.observe([t], self.bundle, datetime.fromisoformat("2026-09-16T21:30:00+00:00"), None, None)
        self.assertEqual(obs["output_tokens"], 3); self.assertEqual(obs["terminal_results_excluded_by_cut"], 1)
        self.assertEqual(obs["overlapping_evidence"], 1)


class Round11(unittest.TestCase):
    """#1991–#1994: an excluded result still bounds the invocation; a shared
    message id without usage is refused; a retained result with nested
    usage is one result; thinking provenance is recorded."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / "P_preprocessed.txt"; self.bundle.write_text("\n".join(f"l{i}" for i in range(10)) + "\n")

    def _file(self, name, lines):
        p = self.root / name; p.write_text("\n".join(lines) + "\n"); return p

    def test_an_excluded_result_still_bounds_the_invocation(self):
        t = self._file("t.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"),
                                   json.dumps({"timestamp": "2026-09-16T22:00:00Z", "type": "result", "message": "done", "uuid": "r", "usage": {"input_tokens": 1, "output_tokens": 100}}),
                                   json.dumps({"type": "assistant", "uuid": "late", "message": {"role": "assistant", "id": "m9", "usage": {"output_tokens": 70},
                                               "content": [{"type": "tool_use", "name": "Read", "id": "tu-late", "input": {"file_path": str(self.bundle), "offset": 1, "limit": 3}}]}})])
        obs = ao.observe([t], self.bundle, datetime.fromisoformat("2026-09-16T21:30:00+00:00"), None, None)
        self.assertEqual(obs["output_tokens"], 3); self.assertEqual(obs["tool_uses"], 0); self.assertEqual(obs["bundle_lines_read"], 0)
        self.assertGreaterEqual(obs["overlapping_evidence"], 1)

    def test_a_shared_message_id_without_usage_is_refused(self):
        shared = json.dumps({"timestamp": "2026-09-16T21:00:00Z", "type": "assistant", "uuid": "u-shared",
                             "message": {"role": "assistant", "id": "m-shared", "content": [{"type": "text", "text": "hi"}]}})
        a = self._file("a.jsonl", [shared, json.dumps({"type": "result", "message": "done", "uuid": "ra", "usage": {"input_tokens": 1, "output_tokens": 100}})])
        b = self._file("b.jsonl", [shared, json.dumps({"type": "result", "message": "done", "uuid": "rb", "usage": {"input_tokens": 1, "output_tokens": 200}})])
        self.assertEqual(ao.observe([a, b], self.bundle, None, None, None)["overlapping_evidence"], 1)

    def test_a_retained_result_with_nested_usage_is_one_result(self):
        t = self._file("t.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"),
                                   json.dumps({"type": "result", "uuid": "r", "usage": {"input_tokens": 1, "output_tokens": 100},
                                               "message": {"role": "assistant", "id": "m1", "usage": {"output_tokens": 100}}})])
        obs = ao.observe([t], self.bundle, None, None, None)
        self.assertEqual(obs["output_tokens"], 100); self.assertNotIn("overlapping_evidence", obs); self.assertEqual(obs["assistant_turns"], 1)

    def test_thinking_provenance_is_recorded(self):
        a = self._file("a.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1"),
                                   json.dumps({"type": "result", "message": "done", "uuid": "ra", "usage": {"input_tokens": 1, "output_tokens": 100, "output_tokens_details": {"thinking_tokens": 80}}})])
        b = self._file("b.jsonl", [_event("2026-09-16T22:00:00Z", usage={"output_tokens": 4, "output_tokens_details": {"thinking_tokens": 7}}, msg_id="m2"),
                                   json.dumps({"type": "result", "message": "done", "uuid": "rb", "usage": {"input_tokens": 1, "output_tokens": 50}})])
        obs = ao.observe([a, b], self.bundle, None, None, None)
        self.assertEqual(obs["thinking_tokens"], 87); self.assertEqual(obs["thinking_from_terminal_results"], 1)
        self.assertEqual(obs["usage_from_terminal_result"], 2); self.assertNotIn("turns_with_thinking_tokens", obs)
        only_b = ao.observe([b], self.bundle, None, None, None)
        self.assertNotIn("thinking_from_terminal_results", only_b); self.assertEqual(only_b["turns_with_thinking_tokens"], 1)


class Round12(unittest.TestCase):
    """#1996: a tool result belongs to the file that made the call."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / "P_preprocessed.txt"; self.bundle.write_text("\n".join(f"l{i}" for i in range(10)) + "\n")

    def _file(self, name, lines):
        p = self.root / name; p.write_text("\n".join(lines) + "\n"); return p

    def test_a_foreign_error_result_is_refused_and_does_not_fail_the_window(self):
        a = self._file("a.jsonl", [_event("2026-09-16T21:00:00Z", usage={"output_tokens": 3}, msg_id="m1",
                                          tools=[("Read", {"file_path": str(self.bundle), "offset": 1, "limit": 3})], ids=["read-a"]),
                                   json.dumps({"timestamp": "2026-09-16T21:00:01Z", "type": "user", "uuid": "ua",
                                               "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "read-a", "content": "ok"}]}}),
                                   json.dumps({"type": "result", "message": "done", "uuid": "ra", "usage": {"input_tokens": 1, "output_tokens": 100}})])
        b = self._file("b.jsonl", [_event("2026-09-16T22:00:00Z", usage={"output_tokens": 4}, msg_id="m2"),
                                   json.dumps({"timestamp": "2026-09-16T22:00:01Z", "type": "user", "uuid": "ub",
                                               "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "read-a", "is_error": True, "content": "x"}]}}),
                                   json.dumps({"type": "result", "message": "done", "uuid": "rb", "usage": {"input_tokens": 1, "output_tokens": 50}})])
        alone = ao.observe([a], self.bundle, None, None, None); self.assertEqual(alone["bundle_lines_read"], 3)
        for order in ([a, b], [b, a]):
            obs = ao.observe(order, self.bundle, None, None, None)
            self.assertEqual(obs["overlapping_evidence"], 1); self.assertEqual(obs["bundle_lines_read"], 3)
        own_error = self._file("c.jsonl", [_event("2026-09-16T23:00:00Z", usage={"output_tokens": 3}, msg_id="m3",
                                                  tools=[("Read", {"file_path": str(self.bundle), "offset": 1, "limit": 3})], ids=["read-c"]),
                                           json.dumps({"timestamp": "2026-09-16T23:00:01Z", "type": "user", "uuid": "uc",
                                                       "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "read-c", "is_error": True, "content": "x"}]}})])
        self.assertEqual(ao.observe([own_error], self.bundle, None, None, None)["bundle_lines_read"], 0)
