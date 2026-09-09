"""A billed response the parser refused is kept as evidence (#1048).

On the v8 fill, CHORUS `2026-09-04f rep2` printed "phase full attempt 1
unusable … retrying" twice and attempt 3 was accepted. The three attempts are
on the record as `api_usage` rows — 40,093 / 54,886 / 43,814 output tokens,
all `end_turn` — and in the reasoning log. **The text of the first two is
gone.** `intermediate/` holds only the accepted `CHORUS_full.yaml`.

A dropped stream has left `…_incomplete_attempt{N}_{n}.txt` since #1017. A
*complete* response the parser rejected left nothing, though it costs the same
money and answers the more interesting question: what shape did the model
produce instead of the expected one?

Recorder-only. The accepted attempt is still what the record describes.
"""
import json
import unittest
from pathlib import Path
from unittest import mock

from data_sheets_schema.api_runner import (UNUSABLE_HEAD_CHARS,
                                           _record_unusable_response)


class _Spec:
    """The two attributes `_snapshot` reads."""

    def __init__(self, tmp):
        self.project = "CHORUS"
        self.core_dir = Path(tmp)


class UnusableSnapshotTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.spec = _Spec(self.tmp.name)
        self.written = {}

        def fake_snapshot(spec, name, body):
            path = Path(self.tmp.name) / "intermediate" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            self.written[name] = body
            return path

        patcher = mock.patch("data_sheets_schema.api_runner._snapshot",
                             side_effect=fake_snapshot)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(self, text, problem="no parseable yaml object", attempt=1,
               usage_row=None):
        return _record_unusable_response(self.spec, "full", attempt, problem,
                                         text, usage_row)

    def test_it_writes_a_snapshot_named_for_the_attempt(self):
        path = self._write("some text the parser refused", attempt=2)
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "CHORUS_full_unusable_attempt2.txt")

    def test_the_header_carries_the_reason_and_the_cost(self):
        """Without the reason the file is a mystery; without the tokens there
        is no way to see what the attempt cost."""
        self._write("body", problem="response carries no `--- COVERAGE RECEIPT ---` document",
                    usage_row={"output_tokens": 40093, "stop_reason": "end_turn"})
        body = self.written["CHORUS_full_unusable_attempt1.txt"]
        self.assertIn("#1048", body)
        self.assertIn("COVERAGE RECEIPT", body)
        self.assertIn("40093", body)
        self.assertIn("end_turn", body)

    def test_it_keeps_the_head_not_the_tail(self):
        """The dropped-stream snapshot keeps a tail because the head was
        already delivered. An unusable body is whole, and its *shape* is the
        question, so the head is what a reader needs."""
        text = "HEAD-MARKER" + "x" * (UNUSABLE_HEAD_CHARS * 2) + "TAIL-MARKER"
        self._write(text)
        body = self.written["CHORUS_full_unusable_attempt1.txt"]
        self.assertIn("HEAD-MARKER", body)
        self.assertNotIn("TAIL-MARKER", body)

    def test_a_long_body_says_it_was_cut(self):
        self._write("y" * (UNUSABLE_HEAD_CHARS + 1))
        self.assertIn("truncated here",
                      self.written["CHORUS_full_unusable_attempt1.txt"])

    def test_a_short_body_is_kept_whole_and_does_not_claim_truncation(self):
        self._write("short")
        body = self.written["CHORUS_full_unusable_attempt1.txt"]
        self.assertIn("short", body)
        self.assertNotIn("truncated here", body)

    def test_the_full_response_is_hashed_even_when_the_body_is_cut(self):
        """The snapshot is bounded, so the hash is what proves which response
        it came from."""
        import hashlib
        text = "z" * (UNUSABLE_HEAD_CHARS + 500)
        self._write(text)
        self.assertIn(hashlib.sha256(text.encode()).hexdigest(),
                      self.written["CHORUS_full_unusable_attempt1.txt"])
        self.assertIn(f"response_chars: {len(text)}",
                      self.written["CHORUS_full_unusable_attempt1.txt"])

    def test_an_empty_response_writes_nothing(self):
        """There is no evidence in an empty body, and a file full of header
        would imply there was."""
        self.assertIsNone(self._write(""))
        self.assertEqual(self.written, {})


if __name__ == "__main__":
    unittest.main()
