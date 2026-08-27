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


def _event(ts, usage=None, tools=()):
    content = [{"type": "tool_use", "name": n, "input": i} for n, i in tools]
    msg = {"role": "assistant", "content": content}
    if usage is not None:
        msg["usage"] = usage
    return json.dumps({"timestamp": ts, "message": msg})


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

    def test_no_bundle_means_no_coverage_keys(self):
        t = self._transcript("a.jsonl", [_event("2026-08-27T00:00:00Z", usage={"output_tokens": 1})])
        obs = ao.observe([t], None)
        self.assertNotIn("bundle_lines_read", obs)
        self.assertEqual(obs["total_tokens"], 1)


if __name__ == "__main__":
    unittest.main()
