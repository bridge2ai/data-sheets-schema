"""scripts/agentic_observed.py — totals and bundle coverage from transcripts (#700, #688)."""
import importlib.util
import json
import tempfile
import unittest
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
