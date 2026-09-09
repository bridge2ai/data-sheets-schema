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

    def test_on_a_receipt_condition_the_whole_response_is_kept(self):
        """The review's finding (#1048): `split_receipt` rebinds the loop's
        `text` to the pre-marker half, and the first version snapshotted that.
        On exactly the failure the file exists for — "the text after the
        receipt marker is not a receipt" — it dropped the text after the
        marker, reported a length that was never delivered, and hashed a
        string that never existed. The function is given the response as
        delivered; this holds it to that."""
        import hashlib
        from data_sheets_schema.api_runner import RECEIPT_MARK
        record = "```yaml\nid: x\n```\n"
        after = "This is prose where a receipt document should be, so it is unusable."
        whole = f"{record}{RECEIPT_MARK}\n{after}\n"
        self._write(whole, problem="the text after the receipt marker is not a receipt")
        body = self.written["CHORUS_full_unusable_attempt1.txt"]
        self.assertIn(after, body, "the text after the marker is the evidence")
        self.assertIn(f"response_chars: {len(whole)}", body)
        self.assertIn(hashlib.sha256(whole.encode()).hexdigest(), body)

    def test_a_long_receipt_response_keeps_the_tail_where_the_receipt_is(self):
        """#1104 review: the receipt is the response's last document, so a
        receipt-parse failure lives in the tail and a head-only snapshot
        showed a reader none of the text that failed — the header was true
        and the body still omitted the evidence."""
        from data_sheets_schema.api_runner import (RECEIPT_MARK,
                                                   UNUSABLE_TAIL_CHARS)
        record = "```yaml\nid: x\n" + ("k: v\n" * 3000) + "```\n"
        after = "PROSE-WHERE-A-RECEIPT-SHOULD-BE and it is not a mapping"
        whole = f"{record}{RECEIPT_MARK}\n{after}\n"
        self.assertGreater(len(whole), UNUSABLE_HEAD_CHARS + UNUSABLE_TAIL_CHARS)
        self._write(whole, problem="the text after the receipt marker is not a receipt")
        body = self.written["CHORUS_full_unusable_attempt1.txt"]
        self.assertIn(after, body)
        self.assertIn("characters elided", body)
        self.assertIn("the window starts at the marker", body)

    def test_a_marker_echoed_inline_in_prose_is_not_a_receipt(self):
        """Round-3 finding 1: `split_receipt` is line-anchored (#740), so a
        record whose prose quotes the marker has no receipt document; the
        snapshot must not elide the record's middle and point at a tail."""
        from data_sheets_schema.api_runner import RECEIPT_MARK
        whole = ("```yaml\nid: x\ndescription: the response must end with "
                 + RECEIPT_MARK + " then the receipt\n" + ("k: v\n" * 5000) + "```\n")
        self._write(whole, problem="response contained no parseable yaml object")
        body = self.written["CHORUS_full_unusable_attempt1.txt"]
        self.assertNotIn("characters elided", body)
        self.assertIn("(truncated here)", body)

    def test_the_window_starts_at_the_marker_so_the_receipts_opening_is_shown(self):
        """Round-3 finding 2: every real receipt is longer than the tail
        bound, and a receipt-parse failure shows at the opening (prose, a
        fence, no `chunks:`), not in the last chunk entries."""
        from data_sheets_schema.api_runner import RECEIPT_MARK
        record = "```yaml\nid: x\n" + ("k: v\n" * 3000) + "```\n"
        opening = "OPENING-OF-THE-RECEIPT: prose where a mapping should be\n"
        whole = f"{record}{RECEIPT_MARK}\n{opening}" + ("- id: c999\n  status: extracted\n" * 2000) + "LAST-LINE\n"
        self._write(whole, problem="the text after the receipt marker is not a receipt")
        body = self.written["CHORUS_full_unusable_attempt1.txt"]
        self.assertIn(RECEIPT_MARK + "\n" + opening, body)          # marker and opening, contiguous
        self.assertNotIn("LAST-LINE", body)                          # the end is what is elided
        self.assertIn("elided after the window", body)
        self.assertIn("from the receipt marker on", body)

    def test_a_long_record_only_response_still_keeps_only_the_head(self):
        """No marker, no tail: a record failure's question is its shape."""
        whole = "```yaml\n" + ("k: v\n" * 5000) + "```\nEND-MARKER\n"
        self._write(whole)
        body = self.written["CHORUS_full_unusable_attempt1.txt"]
        self.assertNotIn("END-MARKER", body)
        self.assertNotIn("characters elided", body)

    def test_a_short_receipt_response_is_kept_whole_without_an_elision(self):
        from data_sheets_schema.api_runner import RECEIPT_MARK
        whole = f"```yaml\nid: x\n```\n{RECEIPT_MARK}\nshort prose\n"
        self._write(whole)
        body = self.written["CHORUS_full_unusable_attempt1.txt"]
        self.assertIn("short prose", body)
        self.assertNotIn("characters elided", body)

    def test_a_readdress_row_of_the_same_attempt_number_is_not_stamped(self):
        """Round-3 finding 3: `_readdress_receipt` appends a `full_readdress`
        row with attempt 1; the guard must check the phase, not only the
        attempt number, or that row is overwritten."""
        from data_sheets_schema.api_runner import _record_unusable_response
        own = {"phase": "full", "attempt": 1, "output_tokens": 7}
        foreign = {"phase": "full_readdress", "attempt": 1, "output_tokens": 9}
        # the call-site guard, reproduced: the row is passed only when phase and attempt match
        for row, expect in ((own, "output_tokens: 7"), (foreign, "output_tokens: None")):
            self.written.clear()
            usage_row = row if row.get("attempt") == 1 and row.get("phase") == "full" else None
            _record_unusable_response(self.spec, "full", 1, "p", "some text", usage_row)
            self.assertIn(expect, self.written["CHORUS_full_unusable_attempt1.txt"])

    def test_an_empty_response_writes_nothing(self):
        """There is no evidence in an empty body, and a file full of header
        would imply there was."""
        self.assertIsNone(self._write(""))
        self.assertEqual(self.written, {})


class ThroughThePhaseLoop(unittest.TestCase):
    """Unmocked `_generate_phase` on a client whose every response is
    unusable, on a receipt condition: the snapshot is written to the run
    directory with the whole response, and the usage row carries the distinct
    key rather than #1017's `outcome`."""

    def test_the_snapshot_lands_whole_and_the_row_is_marked_not_abandoned(self):
        import glob
        import hashlib
        import tempfile
        from pathlib import Path
        from data_sheets_schema import api_runner
        from data_sheets_schema.api_runner import (MAX_ATTEMPTS, RECEIPT_MARK,
                                                   _generate_phase, _model_settings)
        from tests.test_download.test_api_runner import spec

        after = "prose where a receipt should be, so this is unusable"
        body = f"```yaml\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n```\n{RECEIPT_MARK}\n{after}\n"

        class _Block:
            type = "text"
            text = body

        class _Usage:
            input_tokens = 10; output_tokens = 20
            cache_read_input_tokens = cache_creation_input_tokens = 0

        class _Resp:
            content = [_Block()]; usage = _Usage(); stop_reason = "end_turn"

        class _Stream:
            def __init__(self, **kw): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def get_final_message(self): return _Resp()

        class _Messages:
            stream = staticmethod(lambda **kw: _Stream(**kw))

        class _Client:
            messages = _Messages()

        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        s = spec(out_dir=Path(tmp.name) / "out", condition="generic_v8")
        usage = []
        from unittest import mock
        # 0 ** attempt == 0 for every attempt >= 1: zero sleep with no reach
        # into the stdlib module (round-3 finding 8).
        with mock.patch.object(api_runner, "BACKOFF_BASE_SECONDS", 0), self.assertRaises(RuntimeError):
            _generate_phase(s, "full", {}, _Client(), _model_settings(), usage)

        files = sorted(glob.glob(str(Path(tmp.name) / "**" / "*_full_unusable_attempt*.txt"),
                                 recursive=True))
        self.assertEqual(len(files), MAX_ATTEMPTS, files)
        snap = Path(files[0]).read_text()
        self.assertIn(after, snap)
        self.assertIn(f"response_chars: {len(body)}", snap)
        self.assertIn(hashlib.sha256(body.encode()).hexdigest(), snap)

        self.assertEqual(len(usage), MAX_ATTEMPTS)
        for row in usage:
            self.assertIn("unusable_reason", row)
            self.assertIn("unusable_snapshot", row)
            self.assertNotIn("outcome", row, "a billed attempt is not an abandoned one")


if __name__ == "__main__":
    unittest.main()
