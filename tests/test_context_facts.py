"""What a run can honestly say about the context it used (#568).

The v4 arm named its model `claude-opus-5` and sent a 285,113-token request
that succeeded. Nothing in the record said what the ceiling was, so "will the
next change fit" could not be answered from the corpus — only by running it.

Two claims, deliberately kept apart: what the run *sent*, which is arithmetic
over evidence the run already wrote, and what it was *allowed* to send, which is
usually unknowable and is left as a named gap rather than guessed.
"""

import unittest
from pathlib import Path

import yaml

from data_sheets_schema.api_runner import context_facts

USAGE = [
    {"phase": "full", "input_tokens": 3042, "cache_read": 0, "cache_write": 29402},
    {"phase": "reconcile_core", "input_tokens": 51074, "cache_read": 197941,
     "cache_write": 0},
]


class ContextFactsTest(unittest.TestCase):

    def test_cached_tokens_count_toward_the_peak(self):
        """They occupy the window exactly as fresh tokens do.

        Counting only `input_tokens` would have reported AI-READI's largest
        request as 51k rather than 249k, which is the difference between
        "plenty of headroom" and "unknown".
        """
        self.assertEqual(context_facts("m", USAGE)["peak_request_tokens"],
                         51074 + 197941)

    def test_the_peak_names_its_phase(self):
        self.assertEqual(context_facts("m", USAGE)["peak_phase"],
                         "reconcile_core")

    def test_an_unstated_limit_is_null_and_says_why(self):
        """A guess would make headroom computable and wrong."""
        facts = context_facts("claude-opus-5", USAGE)
        self.assertIsNone(facts["limit_tokens"])
        self.assertIn("not stated by the route", facts["limit_basis"])

    def test_a_route_that_states_its_window_is_believed(self):
        for name in ("claude-opus-5[1m]", "claude-opus-5-1m", "vendor/model:1m"):
            with self.subTest(name=name):
                facts = context_facts(name, USAGE)
                self.assertEqual(facts["limit_tokens"], 1_000_000)
                self.assertIn(name, facts["limit_basis"])

    def test_no_usage_gives_no_peak_rather_than_zero(self):
        """An agentic run sent no measured request; zero would be a claim."""
        self.assertIsNone(context_facts("m", [])["peak_request_tokens"])


class CorpusTest(unittest.TestCase):
    """What the backfill put on disk, and the fact that changed the plan."""

    BASE = Path("data/d4d_concatenated")

    def _peaks(self):
        out = []
        for p in self.BASE.glob("*_core/*/*_provenance.yaml"):
            rec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            ctx = (rec.get("model") or {}).get("context") or {}
            if ctx.get("peak_request_tokens"):
                out.append((ctx["peak_request_tokens"], ctx["peak_phase"]))
        if not out:
            self.skipTest("no API records in this checkout")
        return out

    def test_the_corpus_has_already_run_far_above_the_v4_peak(self):
        """The measurement that corrected my own #568 reasoning.

        I raised the context risk of #566 against AI-READI's 249k
        `reconcile_full`. The corpus had already sent 363,261 tokens
        successfully — so a v5 request near 279k is well inside demonstrated
        behaviour, and the risk I flagged was smaller than I stated.
        """
        self.assertGreaterEqual(max(t for t, _ in self._peaks()), 363_000)

    def test_the_peak_phase_is_reconcile_core_not_reconcile_full(self):
        """Also corrects #568: I reasoned about the wrong phase.

        `reconcile_core` receives the reconciled full record, the core record
        and the audit findings, so it is the largest request in 56 of 67 runs.
        `reconcile_full` — the phase #566 enlarges — peaks in 3.
        """
        from collections import Counter
        phases = Counter(ph for _, ph in self._peaks())
        self.assertEqual(phases.most_common(1)[0][0], "reconcile_core")


if __name__ == "__main__":
    unittest.main()
