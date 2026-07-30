"""Tests for reasoning capture.

The case that matters most is the one this project actually hits: a thinking
block that arrives signed but empty. Capture must record that as "a reasoning
block existed and its text was withheld", never as "there was no reasoning" —
those are different facts and only one of them is true of CBORG runs.
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sheets_schema import reasoning


class Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Usage:
    def __init__(self, output_tokens):
        self.output_tokens = output_tokens


class Resp:
    def __init__(self, content, output_tokens=None, stop_reason="end_turn"):
        self.content = content
        self.usage = Usage(output_tokens)
        self.stop_reason = stop_reason


class TestCapture(unittest.TestCase):

    def test_signed_but_empty_block_is_present_not_available(self):
        """CBORG's shape: signature present, plaintext stripped."""
        resp = Resp([Block(type="thinking", thinking="", signature="abc123"),
                     Block(type="text", text='{"supported": 1.0}')],
                    output_tokens=714)
        cap = reasoning.capture(resp)
        self.assertTrue(cap.present, "a thinking block was returned")
        self.assertFalse(cap.available, "its text was not")
        self.assertTrue(cap.blocks[0]["signed"])
        self.assertNotIn("thinking", cap.blocks[0],
                         "no empty thinking key implying captured text")
        self.assertIn("withheld_note", cap.to_dict())

    def test_real_thinking_text_is_kept(self):
        resp = Resp([Block(type="thinking", thinking="Checking the roster.",
                           signature="sig"),
                     Block(type="text", text="ok")], output_tokens=50)
        cap = reasoning.capture(resp)
        self.assertTrue(cap.available)
        self.assertEqual(cap.blocks[0]["thinking"], "Checking the roster.")
        self.assertNotIn("withheld_note", cap.to_dict())

    def test_no_thinking_block_at_all(self):
        cap = reasoning.capture(Resp([Block(type="text", text="hi")],
                                     output_tokens=5))
        self.assertFalse(cap.present)
        self.assertFalse(cap.available)
        self.assertEqual(cap.blocks, [])

    def test_reasoning_token_estimate_subtracts_visible_text(self):
        # 400 chars of visible text ~ 100 tokens, so ~600 went to thinking.
        resp = Resp([Block(type="thinking", thinking="", signature="s"),
                     Block(type="text", text="x" * 400)], output_tokens=700)
        self.assertEqual(reasoning.capture(resp).reasoning_tokens_estimate, 600)

    def test_estimate_is_none_without_usage(self):
        resp = Resp([Block(type="text", text="hi")], output_tokens=None)
        self.assertIsNone(reasoning.capture(resp).reasoning_tokens_estimate)

    def test_estimate_never_negative(self):
        """A short thinking block and long text must not yield a negative."""
        resp = Resp([Block(type="text", text="x" * 4000)], output_tokens=10)
        self.assertEqual(reasoning.capture(resp).reasoning_tokens_estimate, 0)

    def test_redacted_thinking_counts_as_a_block(self):
        resp = Resp([Block(type="redacted_thinking", data="opaque")],
                    output_tokens=20)
        cap = reasoning.capture(resp)
        self.assertTrue(cap.present)
        self.assertEqual(cap.blocks[0]["type"], "redacted_thinking")

    def test_signature_value_is_never_stored(self):
        resp = Resp([Block(type="thinking", thinking="", signature="SECRETSIG")],
                    output_tokens=10)
        self.assertNotIn("SECRETSIG", json.dumps(reasoning.capture(resp).to_dict()))


class TestLog(unittest.TestCase):

    def test_append_and_read_roundtrip(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "nested" / "r.jsonl"
            reasoning.append(p, {"phase": "full", "reasoning_present": True})
            reasoning.append(p, {"phase": "core", "reasoning_present": True})
            entries = reasoning.read(p)
            self.assertEqual([e["phase"] for e in entries], ["full", "core"])

    def test_read_missing_file_is_empty_not_an_error(self):
        with TemporaryDirectory() as td:
            self.assertEqual(reasoning.read(Path(td) / "absent.jsonl"), [])

    def test_summarise_separates_present_from_available(self):
        entries = [
            {"reasoning_present": True, "reasoning_available": False,
             "reasoning_tokens_estimate": 600, "stop_reason": "end_turn"},
            {"reasoning_present": True, "reasoning_available": True,
             "reasoning_tokens_estimate": 100, "stop_reason": "max_tokens"},
        ]
        s = reasoning.summarise(entries)
        self.assertEqual(s["entries"], 2)
        self.assertEqual(s["with_reasoning_block"], 2)
        self.assertEqual(s["with_reasoning_text"], 1)
        self.assertEqual(s["reasoning_tokens_estimate_total"], 700)
        self.assertEqual(s["reasoning_tokens_estimate_max"], 600)
        self.assertEqual(s["truncated"], 1)

    def test_summarise_empty(self):
        self.assertEqual(reasoning.summarise([]), {"entries": 0})


if __name__ == "__main__":
    unittest.main()
