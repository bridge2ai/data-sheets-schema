"""The request states its thinking regime, and the record repeats it (#1047).

Two CM4AI 04g runs came back with no thinking block on `full`,
`reconcile_full` and `report` while `audit` and `repair` in the same runs
had it, and every other fill run had it on `full`. The runner sent no
`thinking` parameter. But on `claude-opus-5` omitting the parameter *runs
adaptive thinking* — so these were not runs that were not asked. They were a
provider deviation on a request identical to ten that got thinking, and the
record could not say so, because it recorded nothing about the request.

Two things are held here. The request states `{"type": "adaptive"}` — which
changes nothing the model does and everything the record can say — and it
never sends `budget_tokens`, which the issue proposed and which is a 400 on
this model family.
"""
import unittest

from data_sheets_schema import reasoning
from data_sheets_schema.api_runner import _call_with_retry, _model_settings


class _Usage:
    input_tokens = output_tokens = 1
    cache_read_input_tokens = cache_creation_input_tokens = 0


class _Resp:
    stop_reason = "end_turn"
    content = []
    usage = _Usage()


def _capturing_client():
    """The thinnest client that satisfies `_call_with_retry`.

    Deliberately no `__iter__`: the runner only walks stream events when the
    stream is iterable, and a fake that yields nothing trips the
    incomplete-stream guard (#1013) — after the kwargs were captured, which
    hid the real failure behind a misleading one. `FakeClient` in
    `test_api_runner` has the same shape for the same reason.
    """
    calls = []

    class _Stream:
        def __init__(self, **kw):
            calls.append(kw)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_final_message(self):
            return _Resp()

    class _Messages:
        stream = staticmethod(lambda **kw: _Stream(**kw))

    class _C:
        messages = _Messages()

    return _C(), calls


class TestTheRequestStatesThinking(unittest.TestCase):
    def test_adaptive_thinking_is_sent_when_given(self):
        client, calls = _capturing_client()
        _call_with_retry(client, model="claude-opus-5", max_tokens=100,
                         temperature=None, system="s", messages=[],
                         thinking={"type": "adaptive"})
        self.assertEqual(calls[0]["thinking"], {"type": "adaptive"})

    def test_budget_tokens_is_never_sent(self):
        """The issue proposed `{type: enabled, budget_tokens: N}`. That shape
        is rejected with a 400 on claude-opus-5; sending it would fail every
        phase of every run. The settings never produce it."""
        settings = _model_settings()
        self.assertNotIn("budget_tokens", settings["thinking"])
        self.assertEqual(settings["thinking"], {"type": "adaptive"})

    def test_effort_travels_as_output_config(self):
        client, calls = _capturing_client()
        _call_with_retry(client, model="claude-opus-5", max_tokens=100,
                         temperature=None, system="s", messages=[],
                         thinking={"type": "adaptive"}, effort="high")
        self.assertEqual(calls[0]["output_config"], {"effort": "high"})

    def test_no_effort_means_no_output_config(self):
        """The config says effort is the provider default. Recording a
        default as a setting is what CLAUDE.md forbids for reasoning effort;
        the request must not invent one either."""
        client, calls = _capturing_client()
        _call_with_retry(client, model="claude-opus-5", max_tokens=100,
                         temperature=None, system="s", messages=[],
                         thinking={"type": "adaptive"})
        self.assertNotIn("output_config", calls[0])
        self.assertNotIn("effort", _model_settings())


class TestEveryPhaseAndTheRecordStateIt(unittest.TestCase):
    """Through `execute()` on the offline fixture: every phase request carries
    the thinking parameter, none carries `budget_tokens`, and the record says
    what was requested."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        from data_sheets_schema import api_runner
        from tests.test_download.test_api_runner import FakeClient, spec
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.spec = spec(out_dir=Path(self.tmp.name) / "out")
        self.client = FakeClient()
        self.api = api_runner
        self._client = api_runner._client
        api_runner._client = lambda: self.client
        self.addCleanup(lambda: setattr(api_runner, "_client", self._client))

    def test_every_request_states_adaptive_thinking_and_never_a_budget(self):
        self.api.execute(self.spec)
        self.assertTrue(self.client.messages.calls)
        for kw in self.client.messages.calls:
            self.assertEqual(kw.get("thinking"), {"type": "adaptive"})
            self.assertNotIn("budget_tokens", kw.get("thinking", {}))

    def test_the_record_carries_the_request_and_its_basis(self):
        import yaml
        # The record's path, read the way the fixture's own tests read it —
        # `record_path` is not exported by `provenance`, and importing it from
        # there is the exact bug that module's docstring records (#1047's
        # test reproduced it once before this line was written).
        self.api.execute(self.spec)
        out = self.spec.out_dir
        d = yaml.safe_load((out / f"{self.spec.project}_provenance.yaml").read_text())
        self.assertEqual(d["model"]["thinking_requested"], {"type": "adaptive"})
        self.assertIn("default when the parameter is omitted",
                      d["model"]["thinking_basis"])
        # No configured effort: nothing invented (CLAUDE.md, "never write
        # default or a guess").
        self.assertNotIn("reasoning_effort", d["model"])


class TestSummariseNamesTheRegime(unittest.TestCase):
    """The real shape of CM4AI 04g rep2's log."""

    LOG = [
        {"phase": "full", "reasoning_present": False, "reasoning_tokens_observed": 0,
         "reasoning_tokens_estimate": 11590},
        {"phase": "full_readdress", "reasoning_present": True,
         "reasoning_tokens_observed": 661, "reasoning_tokens_estimate": 688},
        {"phase": "audit", "reasoning_present": True,
         "reasoning_tokens_observed": 12597, "reasoning_tokens_estimate": 13652},
        {"phase": "reconcile_full", "reasoning_present": False,
         "reasoning_tokens_observed": 0, "reasoning_tokens_estimate": 6634},
        {"phase": "report", "reasoning_present": False,
         "reasoning_tokens_observed": 0, "reasoning_tokens_estimate": 1809},
    ]

    def test_phases_that_disagree_are_flagged_and_named(self):
        s = reasoning.summarise(self.LOG)
        self.assertTrue(s["phases_disagree_on_presence"])
        self.assertEqual(s["phases_without_reasoning"],
                         ["full", "reconcile_full", "report"])

    def test_an_estimate_over_an_observed_zero_is_named_unsound(self):
        """11,590 estimated on a phase the endpoint counted at 0 is not
        reasoning; it is text-length error. Named, not summed."""
        s = reasoning.summarise(self.LOG)
        self.assertEqual(s["estimate_unsound_entries"],
                         ["full", "reconcile_full", "report"])

    def test_a_uniform_run_is_not_flagged(self):
        uniform = [dict(e, reasoning_present=True, reasoning_tokens_observed=10)
                   for e in self.LOG]
        s = reasoning.summarise(uniform)
        self.assertFalse(s["phases_disagree_on_presence"])
        self.assertEqual(s["estimate_unsound_entries"], [])

    def test_a_run_with_no_thinking_anywhere_is_uniform_not_disagreeing(self):
        """Uniformly absent is a regime too, but not a *split* one."""
        none = [dict(e, reasoning_present=False, reasoning_tokens_observed=0)
                for e in self.LOG]
        self.assertFalse(reasoning.summarise(none)["phases_disagree_on_presence"])


if __name__ == "__main__":
    unittest.main()
