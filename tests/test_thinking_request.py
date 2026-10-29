"""The request states its thinking regime, and the record repeats it (#1047).

Two CM4AI 04g runs came back with no thinking block on `full`,
`reconcile_full` and `report` while `audit` and `repair` in the same runs
had it. The runner sent no `thinking` parameter. On `claude-opus-5` omitting
the parameter *runs adaptive thinking* — so these were not runs that were
not asked, and the record could not say so because it recorded nothing
about the request. Stating the request fixes that and nothing more: under
adaptive a phase with no thinking block is a legal outcome (11 of 152 logs
have one on `full`, 8 of them CM4AI's), so the record gains "we asked", not
the power to call a recurrence a deviation (review of #1105).

Held here: the request states `{"type": "adaptive"}` on models that accept
it and nothing on models that predate it; it never sends `budget_tokens`,
which the issue proposed and which is a 400 on this family; every kwarg
the runner passes binds to the pinned SDK's real `stream()` signature —
`output_config` is not one of them and travels as `extra_body`.
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

    def test_generic_v10_condition_requests_summarized_display(self):
        """Condition 'generic_v10' requests adaptive thinking with summarized display."""
        settings = _model_settings("generic_v10")
        self.assertEqual(settings["thinking"], {"type": "adaptive", "display": "summarized"})

        class _Spec:
            condition = "generic_v10"

        settings_obj = _model_settings(_Spec())
        self.assertEqual(settings_obj["thinking"], {"type": "adaptive", "display": "summarized"})

        # Every v10 condition, the routed ones included, declares it (owner,
        # D06, 2026-10-19; #5061 F4).
        from data_sheets_schema.api_runner import CONDITION_AXES, CONDITION_PROMPTS
        v10 = [c for c in CONDITION_PROMPTS if (CONDITION_AXES.get(c) or {}).get("base") == "v10"]
        self.assertIn("generic_v10_source_heading_routing_v1", v10)
        self.assertIn("generic_v10_source_heading_span_v1", v10)
        for routed in v10:
            with self.subTest(condition=routed):
                self.assertEqual(_model_settings(routed)["thinking"],
                                 {"type": "adaptive", "display": "summarized"})

        # Every earlier condition, not a sample of them (#5043 review): a
        # display on any would move that condition's declaration. Variants of
        # the name are not conditions and never opt in.
        earlier = [c for c in CONDITION_PROMPTS if c not in v10]
        for other in earlier + [None, "GENERIC_V10", " generic_v10", "generic_v10x"]:
            with self.subTest(condition=other):
                other_settings = _model_settings(other)
                self.assertEqual(other_settings["thinking"], {"type": "adaptive"})

    def test_the_basis_names_a_display_the_condition_sets(self):
        from data_sheets_schema.api_runner import _thinking_basis
        with_display = _thinking_basis(_model_settings("generic_v10"))
        self.assertIn("The request also sets display: summarized", with_display)
        self.assertIn("not the omitted-parameter default", with_display)
        self.assertNotIn("display", _thinking_basis(_model_settings("generic_v9")))

    def test_summarized_display_binds_to_the_real_sdk(self):
        import inspect
        import anthropic
        client, calls = _capturing_client()
        _call_with_retry(client, model="claude-opus-5", max_tokens=100,
                         temperature=None, system="s", messages=[],
                         thinking={"type": "adaptive", "display": "summarized"})
        kw = calls[0]
        self.assertEqual(kw["thinking"], {"type": "adaptive", "display": "summarized"})
        sig = inspect.signature(anthropic.resources.messages.Messages.stream)
        sig.bind(None, **kw)

    def test_summarized_display_reaches_the_wire(self):
        """Binding shows the kwarg name exists, which predates the display;
        the serialized body shows the nested key is sent (#5043 review)."""
        import json
        import anthropic
        import httpx
        bodies = []

        def handler(request):
            bodies.append(json.loads(request.content))
            return httpx.Response(400, json={"type": "error", "error": {
                "type": "invalid_request_error", "message": "offline probe"}})

        client = anthropic.Anthropic(api_key="offline", base_url="http://probe.invalid", max_retries=0,
                                     http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        thinking = _model_settings("generic_v10")["thinking"]
        with self.assertRaises(anthropic.BadRequestError):
            with client.messages.stream(model="claude-opus-5", max_tokens=10, thinking=thinking,
                                        messages=[{"role": "user", "content": "x"}]) as stream:
                stream.get_final_message()
        with self.assertRaises(anthropic.BadRequestError):
            client.messages.count_tokens(model="claude-opus-5", thinking=thinking,
                                         messages=[{"role": "user", "content": "x"}])
        self.assertEqual([b["thinking"] for b in bodies],
                         [{"type": "adaptive", "display": "summarized"}] * 2)


    def test_the_runner_request_path_puts_the_display_on_the_wire(self):
        """The runner's own path, not the SDK called directly (#5068):
        `_call_with_usage` -> `_call_with_retry` -> the real SDK client on a
        mock transport, with the settings generic_v10 declares. The ledger
        hooks are stubbed; the request is built by the runner. This is the
        runner's generic path (`shared_generation_version=0`), not the
        registered v10 path, whose shared-2 admission swaps in a bounded
        client (`source_heading_admission.prepare`); the next test covers
        that client (#5073 F6)."""
        import json
        from types import SimpleNamespace
        from unittest.mock import patch
        import anthropic
        import httpx
        from data_sheets_schema import api_runner
        bodies = []

        def sse(*events):
            return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events)

        def handler(request):
            bodies.append(json.loads(request.content))
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=sse(
                {"type": "message_start", "message": {
                    "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5",
                    "content": [], "stop_reason": None, "stop_sequence": None,
                    "usage": {"input_tokens": 3, "output_tokens": 0}}},
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "ok"}},
                {"type": "content_block_stop", "index": 0},
                {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                 "usage": {"output_tokens": 1}},
                {"type": "message_stop"}))

        client = anthropic.Anthropic(api_key="offline", base_url="http://probe.invalid", max_retries=0,
                                     http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        settings = _model_settings("generic_v10")
        spec = SimpleNamespace(shared_generation_version=0)
        with patch.object(api_runner, "_require_surviving_accounting"), \
             patch.object(api_runner, "_begin_usage_call", return_value="u1"), \
             patch.object(api_runner, "_cancel_usage_call"):
            resp, identifier = api_runner._call_with_usage(
                spec, "full", 1, "2026-10-18T00:00:00Z", client, model=settings["name"], max_tokens=100,
                temperature=None, system="s", messages=[{"role": "user", "content": "x"}],
                thinking=settings["thinking"])
        self.assertEqual(identifier, "u1")
        self.assertEqual(resp.stop_reason, "end_turn")
        self.assertEqual([b["thinking"] for b in bodies], [{"type": "adaptive", "display": "summarized"}])

    def test_the_shared_2_admission_path_puts_the_display_on_the_wire(self):
        """The registered v10 path (#5073 F6): `_call_with_usage` with
        shared_generation_version 2 goes through `source_heading_admission.prepare`,
        which swaps in the bounded single-attempt client and counts the request
        with `messages.count_tokens` before sending it. Both the count and the
        stream leave through that real client on a mock transport and carry the
        display; the ledger and registration checks around them are stubbed."""
        import json
        from contextlib import ExitStack
        from types import SimpleNamespace
        from unittest.mock import patch
        import anthropic
        import httpx
        from data_sheets_schema import api_runner, receipt_completion, shared_generation
        from data_sheets_schema import source_heading_admission as admission
        from data_sheets_schema import typed_audit_runtime, usage_ledger
        bodies = []

        def sse(*events):
            return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events)

        def handler(request):
            bodies.append((request.url.path, json.loads(request.content)))
            if request.url.path.endswith("/count_tokens"):
                return httpx.Response(200, json={"input_tokens": 3})
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=sse(
                {"type": "message_start", "message": {
                    "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5",
                    "content": [], "stop_reason": None, "stop_sequence": None,
                    "usage": {"input_tokens": 3, "output_tokens": 0}}},
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "ok"}},
                {"type": "content_block_stop", "index": 0},
                {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                 "usage": {"output_tokens": 1}},
                {"type": "message_stop"}))

        client = anthropic.Anthropic(api_key="offline", base_url="http://probe.invalid", max_retries=2,
                                     http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        used = []
        real_bound = receipt_completion._single_attempt_client

        def bounded(c):
            used.append(real_bound(c))
            return used[-1]
        streamed_with = []
        real_retry = api_runner._call_with_retry

        def retry(c, **kw):
            streamed_with.append(c)
            return real_retry(c, **kw)
        settings = _model_settings("generic_v10")
        spec = SimpleNamespace(shared_generation_version=2)
        limits = {"max_calls": 5, "aggregate_input_tokens": 10**9, "aggregate_output_tokens": 10**9,
                  "context_limit_tokens": 1_000_000, "context_limit_basis": "offline test"}
        with ExitStack() as stack:
            for target, name, kw in [
                    (api_runner, "_require_surviving_accounting", {}),
                    (api_runner, "_begin_usage_call", {"return_value": "u1"}),
                    (api_runner, "_cancel_usage_call", {}), (api_runner, "_persist_usage", {}),
                    (typed_audit_runtime, "require_request", {}),
                    (usage_ledger, "require_resolved", {}),
                    (usage_ledger, "_read", {"return_value": {"generation_id": "g"}}),
                    (usage_ledger, "_write", {}),
                    (admission, "_recheck", {"return_value": (None, [])}),
                    (admission, "_limits", {"return_value": limits}),
                    (admission, "_check_wire", {}), (admission, "_check_payload", {}),
                    (admission, "_base", {"return_value": {"generation_id": "g", "registration_sha256": "r"}}),
                    (admission, "require_wire", {}), (admission, "remember_response", {}),
                    (shared_generation, "require_client", {}),
                    (receipt_completion, "_save", {"return_value": {"path": "p", "sha256": "s"}}),
                    (receipt_completion, "_single_attempt_client", {"side_effect": bounded}),
                    (api_runner, "_call_with_retry", {"side_effect": retry})]:
                stack.enter_context(patch.object(target, name, **kw))
            resp, identifier = api_runner._call_with_usage(
                spec, "full", 1, "2026-10-18T00:00:00Z", client, model=settings["name"], max_tokens=100,
                temperature=None, system="s", messages=[{"role": "user", "content": "x"}],
                thinking=settings["thinking"])
        self.assertEqual((identifier, resp.stop_reason), ("u1", "end_turn"))
        self.assertEqual(len(used), 1)
        self.assertEqual(used[0].max_retries, 0)
        self.assertEqual(streamed_with, used)                 # the stream left through it too
        self.assertEqual([path.rsplit("/", 1)[-1] for path, _ in bodies], ["count_tokens", "messages"])
        self.assertEqual([b["thinking"] for _, b in bodies],
                         [{"type": "adaptive", "display": "summarized"}] * 2)

    def test_effort_travels_as_extra_body_and_every_kwarg_binds_to_the_real_sdk(self):
        """The first version passed `output_config=` as a named kwarg, and a
        fake client that accepted anything let the test pass; the pinned SDK
        (0.72.0) has no such keyword and no **kwargs, so the run would have
        died with a TypeError on the first phase (review finding 1). The
        kwargs are bound to the real signature here."""
        import inspect
        import anthropic
        client, calls = _capturing_client()
        _call_with_retry(client, model="claude-opus-5", max_tokens=100,
                         temperature=None, system="s", messages=[],
                         thinking={"type": "adaptive"}, effort="high")
        kw = calls[0]
        self.assertEqual(kw["extra_body"], {"output_config": {"effort": "high"}})
        self.assertNotIn("output_config", kw)
        sig = inspect.signature(anthropic.resources.messages.Messages.stream)
        sig.bind(None, **kw)                                  # raises TypeError on an unknown kwarg
        self.assertFalse(any(p.kind is inspect.Parameter.VAR_KEYWORD
                             for p in sig.parameters.values()),
                         "the SDK grew **kwargs; the binding check no longer proves anything")

    def test_a_model_that_predates_adaptive_thinking_gets_no_parameter(self):
        from unittest import mock
        from data_sheets_schema import api_runner
        self.assertTrue(api_runner.accepts_adaptive_thinking("claude-opus-5"))
        self.assertTrue(api_runner.accepts_adaptive_thinking("google/claude-opus-5-high"))
        self.assertFalse(api_runner.accepts_adaptive_thinking("claude-haiku-4-5-20251001"))
        self.assertFalse(api_runner.accepts_adaptive_thinking("claude-sonnet-4-5-20250929"))
        settings = dict(_model_settings())
        # the settings builder consults the gate: simulate the older model
        with mock.patch.object(api_runner, "accepts_adaptive_thinking", lambda name: False):
            older = _model_settings()
        self.assertNotIn("thinking", older)
        self.assertIn("not on the list of families known to accept adaptive thinking", older["thinking_note"])
        self.assertNotIn("predates", older["thinking_note"])   # a cause the gate cannot know (round 2)
        self.assertEqual(settings["thinking"], {"type": "adaptive"})

    def test_every_call_site_in_the_runner_passes_the_thinking_settings(self):
        """Only `_generate_phase` runs on the offline fixture (review finding
        6). Derived, not enumerated (round 2, note 4): every
        `_call_with_usage(` or direct `_call_with_retry(` occurrence in the
        module must carry both kwargs. Definitions and the transparent
        accounting wrapper (which forwards **kwargs) are excluded."""
        import inspect
        import re
        from data_sheets_schema import api_runner
        src = inspect.getsource(api_runner)
        src = src.replace(inspect.getsource(api_runner._call_with_usage), "", 1)
        calls = [m for m in re.finditer(r"_call_with_(?:retry|usage)\(", src)
                 if not src[max(0, m.start() - 4):m.start()].endswith("def ")]
        self.assertGreaterEqual(len(calls), 4)
        for m in calls:
            window = src[m.start():m.start() + 400]
            self.assertIn('thinking=settings.get("thinking")', window, src[m.start() - 80:m.start() + 80])
            self.assertIn('effort=settings.get("effort")', window)

    def test_no_effort_means_no_output_config(self):
        """The config says effort is the provider default. Recording a
        default as a setting is what CLAUDE.md forbids for reasoning effort;
        the request must not invent one either."""
        client, calls = _capturing_client()
        _call_with_retry(client, model="claude-opus-5", max_tokens=100,
                         temperature=None, system="s", messages=[],
                         thinking={"type": "adaptive"})
        self.assertNotIn("output_config", calls[0])
        self.assertNotIn("extra_body", calls[0])
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
        self.assertIn("legal adaptive outcome", d["model"]["thinking_basis"])
        self.assertIn("judging paths", d["model"]["thinking_basis"])   # scoped, not universal
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

    def test_the_full_phase_without_a_block_is_named_and_phases_are_deduplicated(self):
        s = reasoning.summarise(self.LOG + [dict(self.LOG[0])])   # a retried full phase
        self.assertTrue(s["full_phase_without_reasoning"])
        self.assertEqual(s["phases_without_reasoning"], ["full", "reconcile_full", "report"])
        self.assertNotIn("phases_disagree_on_presence", s)      # the per-run alarm is gone

    def test_an_estimate_over_an_observed_zero_is_named_with_the_error_median(self):
        """11,590 estimated on a phase the endpoint counted at 0 is not
        reasoning; it is text-length error. Named, not summed — and the
        median error where a count exists is beside it, because the error
        is not smaller there (review finding 4)."""
        s = reasoning.summarise([dict(e, estimate_error=(e["reasoning_tokens_estimate"]
                                                          - e["reasoning_tokens_observed"]))
                                 for e in self.LOG])
        self.assertEqual(s["estimate_over_observed_zero"], ["full", "reconcile_full", "report"])
        self.assertEqual(s["estimate_error_median"], 1055)      # median of |27|, |1055| over observed > 0
        self.assertNotIn("estimate_unsound_entries", s)

    def test_a_uniform_run_is_not_flagged(self):
        uniform = [dict(e, reasoning_present=True, reasoning_tokens_observed=10)
                   for e in self.LOG]
        s = reasoning.summarise(uniform)
        self.assertFalse(s["full_phase_without_reasoning"])
        self.assertEqual(s["estimate_over_observed_zero"], [])

    def test_short_phases_without_thinking_do_not_raise_the_full_phase_flag(self):
        """Audit, report and core skip thinking routinely under adaptive —
        146 of 152 logs have some phase without a block. That is not the
        signal; the full phase without one is."""
        short = [dict(e, reasoning_present=(e["phase"] == "full"),
                      reasoning_tokens_observed=(10 if e["phase"] == "full" else 0))
                 for e in self.LOG]
        s = reasoning.summarise(short)
        self.assertFalse(s["full_phase_without_reasoning"])
        self.assertEqual(s["phases_without_reasoning"], ["audit", "full_readdress", "reconcile_full", "report"])


if __name__ == "__main__":
    unittest.main()



# D57: retain externally observed journal heads across fixture resumes.
import pytest
pytestmark = pytest.mark.usefixtures("journal_launch_monitor")
