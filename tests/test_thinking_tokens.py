"""The endpoint's own thinking-token count (#999) and the agentic transcript's
reasoning measure (#1000).

Probed 2026-09-04: CBORG returns `usage.output_tokens_details.thinking_tokens`
(non-streaming body, and the stream's `message_delta` usage) while still
withholding the text; the SDK's `get_final_message()` drops it. Subagent
transcripts carry usage per turn, signed empty thinking blocks and, from
recent runtimes, the same `output_tokens_details`.
"""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from data_sheets_schema import reasoning
from data_sheets_schema.api_runner import _call_with_retry


class Usage:
    def __init__(self, output_tokens=31, details=None, extra=None):
        self.input_tokens = 27
        self.output_tokens = output_tokens
        self.cache_read_input_tokens = 0
        self.cache_creation_input_tokens = 0
        if details is not None:
            self.output_tokens_details = details
        if extra is not None:
            self.model_extra = extra


class Resp:
    def __init__(self, usage, text="713", thinking=""):
        self.usage = usage
        self.stop_reason = "end_turn"
        self.content = [SimpleNamespace(type="thinking", thinking=thinking, signature="sig"),
                        SimpleNamespace(type="text", text=text)]


class TestCapture(unittest.TestCase):
    def test_the_count_is_read_from_an_attribute_an_extra_or_a_dict(self):
        self.assertEqual(reasoning.thinking_tokens(Resp(Usage(details={"thinking_tokens": 28}))), 28)
        self.assertEqual(reasoning.thinking_tokens(Resp(Usage(details=SimpleNamespace(thinking_tokens=10)))), 10)
        self.assertEqual(reasoning.thinking_tokens(Resp(Usage(extra={"output_tokens_details": {"thinking_tokens": 5}}))), 5)
        self.assertIsNone(reasoning.thinking_tokens(Resp(Usage())))
        self.assertIsNone(reasoning.thinking_tokens(Resp(Usage(details={"thinking_tokens": None}))))
        self.assertIsNone(reasoning.thinking_tokens(SimpleNamespace(content=[])))

    def test_the_entry_carries_observed_beside_the_estimate_and_their_difference(self):
        d = reasoning.capture(Resp(Usage(output_tokens=31, details={"thinking_tokens": 28}), text="x" * 8)).to_dict()
        self.assertEqual((d["reasoning_tokens_estimate"], d["reasoning_tokens_observed"], d["estimate_error"]),
                         (29, 28, 1))
        self.assertTrue(d["reasoning_present"] and not d["reasoning_available"])
        d = reasoning.capture(Resp(Usage(output_tokens=31))).to_dict()
        self.assertIsNone(d["reasoning_tokens_observed"])
        self.assertNotIn("estimate_error", d)

    def test_the_summary_keeps_observed_apart_from_estimated(self):
        entries = [reasoning.capture(Resp(Usage(31, details={"thinking_tokens": 28}), text="x" * 8)).to_dict(),
                   reasoning.capture(Resp(Usage(13, details={"thinking_tokens": 10}), text="x" * 4)).to_dict(),
                   reasoning.capture(Resp(Usage(40), text="x" * 40)).to_dict()]
        s = reasoning.summarise(entries)
        self.assertEqual((s["entries"], s["with_observed_count"], s["reasoning_tokens_observed_total"]), (3, 2, 38))
        self.assertEqual(s["estimate_error_total"], (29 - 28) + (12 - 10))
        self.assertEqual(s["reasoning_tokens_estimate_total"], 29 + 12 + 30)
        s = reasoning.summarise([entries[2]])
        self.assertEqual((s["with_observed_count"], s["reasoning_tokens_observed_total"], s["estimate_error_total"]),
                         (0, None, None))


class _Delta:
    type = "message_delta"

    def __init__(self, usage):
        self.usage = usage


class _Stream:
    """A stream whose final message's usage lacks the breakdown the delta
    carried — the SDK's shape."""

    def __init__(self, events, final):
        self._events, self._final = events, final

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter(self._events)

    def get_final_message(self):
        return self._final


class _Client:
    def __init__(self, stream):
        self.messages = SimpleNamespace(stream=lambda **kw: stream)


class TestTheRunnerReadsTheDelta(unittest.TestCase):
    def _call(self, stream):
        return _call_with_retry(_Client(stream), model="m", max_tokens=100, temperature=None,
                                system="s", messages=[{"role": "user", "content": "q"}])

    def test_the_delta_usage_extra_lands_on_the_final_message(self):
        final = Resp(Usage(output_tokens=31))
        delta = _Delta(Usage(output_tokens=31, extra={"output_tokens_details": {"thinking_tokens": 28}}))
        msg = self._call(_Stream([SimpleNamespace(type="message_start"), delta], final))
        self.assertIs(msg, final)
        self.assertEqual(reasoning.thinking_tokens(msg), 28)

    def test_a_stream_without_the_breakdown_leaves_the_message_alone(self):
        final = Resp(Usage(output_tokens=31))
        msg = self._call(_Stream([_Delta(Usage(output_tokens=31))], final))
        self.assertIsNone(reasoning.thinking_tokens(msg))

    def test_a_stream_that_cannot_be_iterated_still_returns_the_message(self):
        final = Resp(Usage(output_tokens=31))

        class _Plain:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def get_final_message(self):
                return final
        self.assertIs(self._call(_Plain()), final)


class TestLogStatus(unittest.TestCase):
    def test_an_agentic_run_with_a_transcript_measure_is_recovered(self):
        obs = {"total_tokens": 10, "output_tokens": 5, "assistant_turns": 2}
        self.assertEqual(reasoning.log_status("Claude Code", "2026-08-28_x", False, obs), reasoning.RECOVERED)
        self.assertEqual(reasoning.log_status("Claude Code", "2026-08-28_x", False, {"total_tokens": 10}),
                         reasoning.NO_LOG_RUNTIME)
        self.assertEqual(reasoning.log_status("Claude Code", "2026-08-28_x", False, None), reasoning.NO_LOG_RUNTIME)
        self.assertEqual(reasoning.log_status("Claude API (direct)", "2026-08-28_x", False, obs), reasoning.NO_LOG_MISSING)


def _line(ts, mid, output_tokens, content, details=None):
    usage = {"input_tokens": 1, "output_tokens": output_tokens}
    if details is not None:
        usage["output_tokens_details"] = details
    return json.dumps({"timestamp": ts, "uuid": ts, "type": "assistant",
                       "message": {"id": mid, "role": "assistant", "usage": usage, "content": content}})


class TestTheTranscriptMeasure(unittest.TestCase):
    def test_turns_blocks_and_counts_are_summed_once_per_message(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("agentic_observed", Path("scripts/agentic_observed.py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp) / "agent-x.jsonl"
            think = {"type": "thinking", "thinking": "", "signature": "s"}
            t.write_text("\n".join([
                _line("2026-09-04T01:00:00Z", "m1", 100, [think, {"type": "text", "text": "x" * 40}],
                      {"thinking_tokens": 80}),
                _line("2026-09-04T01:00:01Z", "m1", 100, [think, {"type": "text", "text": "x" * 40}],
                      {"thinking_tokens": 80}),                              # the same message, streamed twice
                _line("2026-09-04T01:00:02Z", "m2", 50, [{"type": "text", "text": "y" * 8}]),
            ]) + "\n")
            out = mod.observe([t], None, None, None, None)
        self.assertEqual({k: out[k] for k in ("assistant_turns", "output_tokens", "thinking_blocks",
                                              "thinking_text_chars", "visible_text_chars",
                                              "reasoning_tokens_estimate", "thinking_tokens",
                                              "turns_with_thinking_tokens")},
                         {"assistant_turns": 2, "output_tokens": 150, "thinking_blocks": 1,
                          "thinking_text_chars": 0, "visible_text_chars": 48,
                          "reasoning_tokens_estimate": 150 - 12, "thinking_tokens": 80,
                          "turns_with_thinking_tokens": 1})

    def test_no_turn_with_a_count_omits_the_key_rather_than_writing_zero(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("agentic_observed", Path("scripts/agentic_observed.py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp) / "agent-x.jsonl"
            t.write_text(_line("2026-09-04T01:00:00Z", "m1", 10, [{"type": "text", "text": "abcd"}]) + "\n")
            out = mod.observe([t], None, None, None, None)
        self.assertNotIn("thinking_tokens", out)
        self.assertEqual(out["reasoning_tokens_estimate"], 9)

    def test_annotate_observed_accepts_the_measure(self):
        from data_sheets_schema.cli.provenance import _OBSERVED_FIELDS
        self.assertTrue(set(reasoning.OBSERVED_REASONING_KEYS) <= _OBSERVED_FIELDS)


if __name__ == "__main__":
    unittest.main()
