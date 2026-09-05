"""A stream that ended before `message_stop` is retried, not accepted (#1013).

The VOICE 2026-09-04e full phase: 68,183 characters streamed, then the
connection closed cleanly; the SDK returned the snapshot with usage from
`message_start` (5 output tokens) and no stop reason; the runner accepted
the body because it parsed and carried the receipt marker; the receipt
stopped at 7 of 22 chunks and the canary read 15 unreviewed.
"""

import unittest
from types import SimpleNamespace

from data_sheets_schema.api_runner import (INCOMPLETE_STREAM_ATTEMPTS, MAX_ATTEMPTS, IncompleteStreamError,
                                           _call_with_retry)


class _Usage:
    input_tokens = 6349
    output_tokens = 5
    cache_read_input_tokens = 0
    cache_creation_input_tokens = 0


def _message(stop_reason):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text="x" * 100)], usage=_Usage(),
                           stop_reason=stop_reason)


COMPLETE = [SimpleNamespace(type="message_start"), SimpleNamespace(type="message_delta", usage=None),
            SimpleNamespace(type="message_stop")]
CUT = [SimpleNamespace(type="message_start"), SimpleNamespace(type="content_block_start")]


class _Stream:
    """`events` is what the SSE stream yielded before EOF; `final` is the SDK's
    snapshot at that point."""

    def __init__(self, final, events=None):
        self._final = final
        self._events = COMPLETE if events is None else events
        self.asked_for_final = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter(self._events)

    def get_final_message(self):
        self.asked_for_final = True
        if not self._events:
            raise AssertionError("the SDK asserts a message on a zero-event stream")
        return self._final


class _Client:
    def __init__(self, streams):
        self.calls = 0
        streams = list(streams)

        def stream(**kw):
            self.calls += 1
            return streams.pop(0)
        self.messages = SimpleNamespace(stream=stream)


def _call(client):
    return _call_with_retry(client, model="m", max_tokens=100, temperature=None, system="s",
                            messages=[{"role": "user", "content": "q"}], sleep=lambda _: None)


class TestTheGuard(unittest.TestCase):
    def test_a_stream_cut_before_message_stop_is_retried_and_the_complete_one_returned(self):
        cut = _Stream(_message(None), CUT)
        client = _Client([cut, _Stream(_message("end_turn"))])
        msg = _call(client)
        self.assertEqual((client.calls, msg.stop_reason, cut.asked_for_final), (2, "end_turn", False))

    def test_a_delta_without_message_stop_is_still_incomplete(self):
        """#1016: `[message_start, message_delta, EOF]` is cut too — the contract ends with message_stop."""
        cut = _Stream(_message(None), [SimpleNamespace(type="message_start"),
                                       SimpleNamespace(type="message_delta", usage=None)])
        client = _Client([cut, _Stream(_message("end_turn"))])
        self.assertEqual((_call(client).stop_reason, client.calls), ("end_turn", 2))

    def test_a_framed_close_whose_message_never_stopped_is_incomplete(self):
        """A proxy that sends a synthetic delta and message_stop after losing upstream: the
        SDK's message still carries no stop_reason, and that is the message's own word."""
        framed = _Stream(_message(None), COMPLETE)
        client = _Client([framed, _Stream(_message("end_turn"))])
        self.assertEqual((_call(client).stop_reason, client.calls, framed.asked_for_final), ("end_turn", 2, True))

    def test_a_zero_event_close_is_incomplete_before_the_sdk_asserts(self):
        client = _Client([_Stream(_message(None), []), _Stream(_message("end_turn"))])
        self.assertEqual((_call(client).stop_reason, client.calls), ("end_turn", 2))

    def test_incomplete_streams_are_bounded_below_the_attempt_ladder(self):
        client = _Client([_Stream(_message(None), CUT)] * MAX_ATTEMPTS)
        with self.assertRaises(IncompleteStreamError) as cm:
            _call(client)
        self.assertEqual(client.calls, INCOMPLETE_STREAM_ATTEMPTS + 1)
        self.assertIn("#1013", str(cm.exception))

    def test_a_complete_stream_is_untouched(self):
        client = _Client([_Stream(_message("max_tokens"))])
        self.assertEqual((_call(client).stop_reason, client.calls), ("max_tokens", 1))

    def test_a_stream_that_cannot_be_iterated_is_taken_at_the_sdk_word(self):
        """The suite's fake streams expose no events; the guard judges on events, not on their absence."""
        final = _message(None)

        class _Plain:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def get_final_message(self):
                return final
        client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: _Plain()))
        self.assertIs(_call(client), final)


if __name__ == "__main__":
    unittest.main()
