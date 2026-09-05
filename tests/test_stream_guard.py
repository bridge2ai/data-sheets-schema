"""A stream that ended before `message_stop` is retried, not accepted (#1013).

The VOICE 2026-09-04e full phase: 68,183 characters streamed, then the
connection closed cleanly; the SDK returned the snapshot with usage from
`message_start` (5 output tokens) and no stop reason; the runner accepted
the body because it parsed and carried the receipt marker; the receipt
stopped at 7 of 22 chunks and the canary read 15 unreviewed.
"""

import unittest
from types import SimpleNamespace

from data_sheets_schema.api_runner import MAX_ATTEMPTS, IncompleteStreamError, _call_with_retry


class _Usage:
    input_tokens = 6349
    output_tokens = 5
    cache_read_input_tokens = 0
    cache_creation_input_tokens = 0


def _message(stop_reason):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text="x" * 100)], usage=_Usage(),
                           stop_reason=stop_reason)


class _Stream:
    def __init__(self, final):
        self._final = final

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter([SimpleNamespace(type="message_start")])

    def get_final_message(self):
        return self._final


class _Client:
    def __init__(self, finals):
        self.calls = 0
        finals = list(finals)

        def stream(**kw):
            self.calls += 1
            return _Stream(finals.pop(0))
        self.messages = SimpleNamespace(stream=stream)


def _call(client):
    return _call_with_retry(client, model="m", max_tokens=100, temperature=None, system="s",
                            messages=[{"role": "user", "content": "q"}], sleep=lambda _: None)


class TestTheGuard(unittest.TestCase):
    def test_a_snapshot_without_a_stop_reason_is_retried_and_the_complete_one_returned(self):
        client = _Client([_message(None), _message("end_turn")])
        msg = _call(client)
        self.assertEqual((client.calls, msg.stop_reason), (2, "end_turn"))

    def test_every_attempt_incomplete_raises_the_incomplete_stream_error(self):
        client = _Client([_message(None)] * MAX_ATTEMPTS)
        with self.assertRaises(IncompleteStreamError) as cm:
            _call(client)
        self.assertEqual(client.calls, MAX_ATTEMPTS)
        self.assertIn("#1013", str(cm.exception))

    def test_a_complete_stream_is_untouched(self):
        client = _Client([_message("max_tokens")])
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

    def test_a_delta_seen_but_no_stop_reason_is_not_the_guard_case(self):
        class _WithDelta(_Stream):
            def __iter__(self):
                return iter([SimpleNamespace(type="message_start"), SimpleNamespace(type="message_delta", usage=None)])
        final = _message(None)
        client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: _WithDelta(final)))
        self.assertIs(_call(client), final)


if __name__ == "__main__":
    unittest.main()
