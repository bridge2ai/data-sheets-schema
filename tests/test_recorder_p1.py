"""The four recorder items landed before the v8 fill: the batch writes the
verdict it acts on (#1020), output sizes are re-read at record write
(#1021), a dirty tree names its paths and the regate rows carry their cap
(#1023), and a dropped stream leaves evidence (#1017)."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from data_sheets_schema import api_runner, provenance
from data_sheets_schema.api_runner import (INCOMPLETE_TAIL_CHARS, IncompleteStreamError, RunSpec,
                                           _call_with_retry, _record_incomplete_stream)
from data_sheets_schema.canary import verdict_block


class TestOutputSizes(unittest.TestCase):
    def test_sizes_are_re_read_from_the_files_at_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "full.yaml"; f.write_text("id: x\n")
            data = {"outputs": {"full": {"path": str(f), "bytes": 3}, "core": {"path": str(Path(tmp) / "gone"), "bytes": 9},
                                "report": None}}
            provenance.refresh_output_sizes(data)
        self.assertEqual(data["outputs"]["full"]["bytes"], 6)
        self.assertEqual(data["outputs"]["core"]["bytes"], 9)                # a missing file keeps what was recorded
        self.assertNotIn("outputs_sized_at", data)                        # the record schema is closed


class TestRepoFacts(unittest.TestCase):
    def test_dirty_paths_are_named_and_bounded(self):
        porcelain = "\n".join([" M src/a.py", "?? data/.run_locks/x.json"] + [f"?? f{i}" for i in range(60)])
        with mock.patch.object(provenance, "_run", lambda args: porcelain if "status" in args else "abc"):
            facts = provenance.repo_facts()
        self.assertTrue(facts["dirty"])
        self.assertEqual(facts["dirty_file_count"], 62)
        self.assertEqual(facts["dirty_paths"][:2], ["src/a.py", "data/.run_locks/x.json"])
        self.assertEqual(len(facts["dirty_paths"]), provenance.DIRTY_PATHS_MAX)
        self.assertEqual(facts["dirty_paths_truncated"], 12)
        with mock.patch.object(provenance, "_run", lambda args: "" if "status" in args else "abc"):
            clean = provenance.repo_facts()
        self.assertEqual((clean["dirty"], clean["dirty_paths"]), (False, []))
        self.assertNotIn("dirty_paths_truncated", clean)


class TestVerdictBlock(unittest.TestCase):
    def test_the_block_carries_basis_recorder_and_the_prior(self):
        v = {"status": "ok", "rows": [], "regressions": [], "blind": [], "unbaselined": []}
        b = verdict_block(v, label_prefix="v7", report_basis_counts={"measured": 1, "vacuous": 2, "unchecked": 0},
                          recorded_by="d4d api batch", prior={"status": "regressed", "rows": [1]})
        self.assertEqual((b["status"], b["recorded_by"], b["prior_verdict"]), ("ok", "d4d api batch", {"status": "regressed", "rows": [1]}))
        self.assertIn("'v7'", b["basis"]); self.assertIn("measured", b["basis"])
        self.assertNotIn("prior_verdict", verdict_block(v, label_prefix="v7", report_basis_counts={}, recorded_by="x"))


class _Usage:
    input_tokens = 6349; output_tokens = 5; cache_read_input_tokens = 0; cache_creation_input_tokens = 0

    def model_dump(self):
        return {"input_tokens": 6349, "output_tokens": 5}


class _CutStream:
    """A stream that delivered 68k characters and then closed cleanly."""

    def __init__(self):
        self.current_message_snapshot = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="x" * 68183)], usage=_Usage(), stop_reason=None)

    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __iter__(self): return iter([SimpleNamespace(type="message_start"), SimpleNamespace(type="content_block_start")])
    def get_final_message(self): return self.current_message_snapshot


class _Complete:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __iter__(self): return iter([SimpleNamespace(type="message_start"), SimpleNamespace(type="message_delta", usage=None),
                                     SimpleNamespace(type="message_stop")])
    def get_final_message(self):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="done")], usage=_Usage(), stop_reason="end_turn")


class TestIncompleteEvidence(unittest.TestCase):
    def test_the_caller_receives_what_the_stream_delivered(self):
        streams = [_CutStream(), _Complete()]
        client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: streams.pop(0)))
        seen = []
        msg = _call_with_retry(client, model="m", max_tokens=100, temperature=None, system="s",
                               messages=[{"role": "user", "content": "q"}], sleep=lambda _: None,
                               on_incomplete=seen.append)
        self.assertEqual(msg.stop_reason, "end_turn")
        (info,) = seen
        self.assertEqual((info["attempt"], info["incomplete"], info["events"], info["content_chars"]), (1, 1, 2, 68183))
        self.assertEqual(len(info["tail"]), INCOMPLETE_TAIL_CHARS)
        self.assertEqual(len(info["content_sha256"]), 64)
        self.assertEqual(info["usage"]["output_tokens"], 5)

    def test_a_zero_event_close_whose_snapshot_asserts_stays_transient(self):
        """#1037 review: the SDK's `current_message_snapshot` asserts before message_start."""
        class _Zero:
            @property
            def current_message_snapshot(self):
                raise AssertionError("no message yet")

            def __enter__(self): return self
            def __exit__(self, *a): return False
            def __iter__(self): return iter([])
            def get_final_message(self): raise AssertionError("no message yet")
        streams = [_Zero(), _Complete()]
        client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: streams.pop(0)))
        seen = []
        msg = _call_with_retry(client, model="m", max_tokens=100, temperature=None, system="s",
                               messages=[{"role": "user", "content": "q"}], sleep=lambda _: None,
                               on_incomplete=seen.append)
        self.assertEqual((msg.stop_reason, seen[0]["events"], seen[0]["content_chars"]), ("end_turn", 0, 0))

    def test_the_usage_row_carries_the_keys_the_consumers_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = RunSpec(project="P", arm="", method="m", bundle=Path(tmp) / "b.txt", label="L", out_dir=Path(tmp))
            usage = []
            _record_incomplete_stream(spec, "full", 1, "t", {"incomplete": 2, "usage": {"input_tokens": 6349, "output_tokens": 5}}, usage)
        (row,) = usage
        self.assertEqual((row["input_tokens"], row["output_tokens"], row["cache_read"], row["cache_write"]), (6349, 5, None, None))
        self.assertEqual(sum(u.get("input_tokens") or 0 for u in usage), 6349)

    def test_a_recorder_that_raises_does_not_make_the_drop_fatal(self):
        streams = [_CutStream(), _Complete()]
        client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: streams.pop(0)))

        def boom(info):
            raise RuntimeError("disk full")
        msg = _call_with_retry(client, model="m", max_tokens=100, temperature=None, system="s",
                               messages=[{"role": "user", "content": "q"}], sleep=lambda _: None, on_incomplete=boom)
        self.assertEqual(msg.stop_reason, "end_turn")

    def test_the_phase_leaves_a_snapshot_and_a_usage_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = RunSpec(project="P", arm="", method="m", bundle=Path(tmp) / "b.txt", label="L", out_dir=Path(tmp))
            usage = []
            info = {"attempt": 2, "incomplete": 1, "events": 41, "seconds": 1065.9, "content_chars": 68183,
                    "content_sha256": "ab" * 32, "tail": "…the end of what arrived", "usage": {"output_tokens": 5}}
            _record_incomplete_stream(spec, "full", 2, "2026-09-05T02:19:49+00:00", info, usage)
            (row,) = usage
            snap = Path(row["snapshot"])
            self.assertTrue(snap.exists() and snap.name.startswith("P_full_incomplete_attempt2_1"))
            text = snap.read_text()
        self.assertIn("content_sha256: " + "ab" * 32, text)
        self.assertTrue(text.endswith("…the end of what arrived"))
        self.assertEqual((row["phase"], row["attempt"], row["transport_attempt"], row["outcome"][:33], row["output_tokens"]),
                         ("full", 2, 1, "stream ended without message_stop", 5))


class TestOfflineExecuteRecordsTheRun(unittest.TestCase):
    """Through the runner's own offline path: every usage row carries its cap and
    the recorded sizes are the files' sizes at write (#1021, #1023)."""

    def test_sizes_and_caps_on_the_record(self):
        import yaml

        from tests.test_download.test_api_runner import FakeClient, spec
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(api_runner, "_client", lambda: FakeClient()):
            out = Path(tmp) / "out"
            api_runner.execute(spec(out_dir=out))
            r = yaml.safe_load((out / "CHORUS_provenance.yaml").read_text())
            for name, entry in (r.get("outputs") or {}).items():
                if isinstance(entry, dict) and entry.get("path"):
                    self.assertEqual(entry["bytes"], Path(entry["path"]).stat().st_size, name)
            rows = [u for u in r["api_usage"] if "outcome" not in u]
            self.assertTrue(rows)
            self.assertEqual([u["phase"] for u in rows if u.get("max_tokens") is None], [])
            self.assertIn("dirty_paths", r["repo"])

    def test_sizes_describe_the_bytes_the_hashes_do_even_when_the_regate_rewrites_the_report(self):
        import yaml

        from tests.test_download.test_api_runner import FakeClient, spec
        real_gate = api_runner._gate_report

        def gate_that_rewrites(spec_, *a, **k):
            out = real_gate(spec_, *a, **k)
            spec_.report_path.write_text(spec_.report_path.read_text() + "\n\nappended after the gate\n")
            return out
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(api_runner, "_client", lambda: FakeClient()), \
             mock.patch.object(api_runner, "_gate_report", gate_that_rewrites):
            out = Path(tmp) / "out"
            api_runner.execute(spec(out_dir=out))
            r = yaml.safe_load((out / "CHORUS_provenance.yaml").read_text())
            rep = r["outputs"]["report"]
            self.assertEqual(rep["bytes"], Path(rep["path"]).stat().st_size)


if __name__ == "__main__":
    unittest.main()
