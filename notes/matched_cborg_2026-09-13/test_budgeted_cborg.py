"""Offline admission tests: no credentials, network or scientific ratings."""
from contextlib import contextmanager
from decimal import Decimal
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

from budgeted_cborg import (BudgetStop, CappedClient, Ledger, cborg_client,
                           provider_context_evidence, provider_context_headers)


PRICES = {"input": 0.000005, "output": 0.000025,
          "cache_read": 0.0000005, "cache_write": 0.00000625}


class Fake:
    def __init__(self, *, fail=False):
        self.messages = self
        self.calls = 0
        self.counts = 0
        self.fail = fail

    def count_tokens(self, **request):
        self.counts += 1
        return SimpleNamespace(input_tokens=100)

    def create(self, **request):
        self.calls += 1
        if self.fail:
            raise TimeoutError("response was lost")
        value = {"model": "claude-opus-5", "stop_reason": "end_turn", "content": [{"type": "text", "text": "fixture"}],
                 "usage": {"input_tokens": 100, "output_tokens": 50,
                           "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 500}}
        return SimpleNamespace(model_dump=lambda **kw: value)

    @contextmanager
    def stream(self, **request):
        class Stream:
            def __iter__(self):
                yield SimpleNamespace(type="message_stop")
            def get_final_message(inner):
                return self.create(**request)
        yield Stream()


def client(tmp_path, *, fail=False, cap=5, verify=lambda: None):
    provider = Fake(fail=fail)
    ledger = Ledger(tmp_path / "ledger.json", manifest_sha256="test", total_cap=200, attempt_cap=cap)
    capped = CappedClient(provider, ledger=ledger, attempt="canary-1", evidence=tmp_path / "requests",
                          model="claude-opus-5", prices=PRICES, verify=verify)
    return provider, capped, ledger


REQUEST = {"model": "claude-opus-5", "max_tokens": 1000,
           "messages": [{"role": "user", "content": "Synthetic fixture"}]}


@pytest.mark.parametrize("policy", [None, False, True, {}, [], "", "default", "headroom-compressed"])
def test_unknown_context_policy_stops_before_client_creation(policy):
    with pytest.raises(BudgetStop, match="context policy"):
        cborg_client({"provider_base_url": "https://unused.invalid",
                      "provider_context_policy": policy}, "offline", max_retries=0)


@pytest.mark.parametrize("bypass", [False, True])
def test_registered_context_policy_reaches_sdk_count_and_generation_unchanged(tmp_path, bypass):
    import httpx
    manifest = {"provider_base_url": "https://api.cborg.lbl.gov"}
    if bypass:
        manifest["provider_context_policy"] = "headroom_bypass_v1"
    calls = []
    def respond(request):
        calls.append(request)
        if request.url.path.endswith("/count_tokens"):
            return httpx.Response(200, json={"input_tokens": 100})
        events = [
            {"type": "message_start", "message": {"id": "offline", "type": "message", "role": "assistant",
             "model": REQUEST["model"], "content": [], "stop_reason": None,
             "usage": {"input_tokens": 100, "output_tokens": 0}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "fixture"}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 10}},
            {"type": "message_stop"},
        ]
        raw = "".join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events)
        return httpx.Response(200, content=raw, headers={"content-type": "text/event-stream"})
    sdk = cborg_client(manifest, "offline-never-sent", max_retries=0,
                       http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    ledger = Ledger(tmp_path / "ledger.json", manifest_sha256="offline")
    capped = CappedClient(sdk, ledger=ledger, attempt="offline", evidence=tmp_path / "requests",
                          model=REQUEST["model"], prices=PRICES, verify=lambda: None)
    with sdk:
        with capped.messages.stream(**REQUEST) as stream:
            list(stream)
            assert stream.get_final_message().content[0].text == "fixture"
    assert [call.url.path for call in calls] == ["/v1/messages/count_tokens", "/v1/messages"]
    assert all(call.headers.get("x-headroom-bypass") == ("true" if bypass else None) for call in calls)
    assert json.loads(calls[0].content) == {k: v for k, v in REQUEST.items() if k != "max_tokens"}
    assert json.loads(calls[1].content) == {**REQUEST, "stream": True}
    evidence = provider_context_evidence(manifest)
    assert evidence["requested_headers"] == provider_context_headers(manifest)
    assert evidence["provider_behavior_independently_observed"] is False
    assert json.loads(ledger.path.read_bytes())["requests"][0]["status"] == "settled"


def test_reserve_before_generation_and_capture_every_charge(tmp_path):
    provider, capped, ledger = client(tmp_path)
    capped.messages.create(**REQUEST)
    state = json.loads(ledger.path.read_bytes())
    assert provider.calls == provider.counts == 1
    assert Decimal(state["requests"][0]["cost_usd"]) == Decimal("0.005375")
    assert state["requests"][0]["status"] == "settled"
    assert len(list((tmp_path / "requests").rglob("request.json"))) == 1
    assert len(list((tmp_path / "requests").rglob("response.json"))) == 1


def test_unaffordable_call_never_reaches_generation(tmp_path):
    provider, capped, _ = client(tmp_path, cap=0.01)
    with pytest.raises(BudgetStop, match="remaining budget"):
        capped.messages.create(**REQUEST)
    assert provider.calls == 0


def test_refusal_survives_swallowed_exception_and_new_transport(tmp_path):
    provider, capped, ledger = client(tmp_path, cap=0.01)
    with pytest.raises(BudgetStop, match="remaining budget"):
        capped.messages.create(**REQUEST)
    # This cheaper call would fit, including after a process/controller restart.
    provider2, restarted, _ = client(tmp_path, cap=0.01)
    for instance in (capped, restarted):
        with pytest.raises(BudgetStop, match="previously stopped"):
            instance.messages.create(**{**REQUEST, "max_tokens": 1})
    assert provider.calls == provider2.calls == provider2.counts == 0
    assert provider.counts == 1
    denied = json.loads(ledger.path.read_bytes())["stopped_attempts"]["canary-1"]
    assert denied["paid_request"] is False and denied["denied_request_sha256"]
    assert len(list((tmp_path / "denied_requests").rglob("request.json"))) == 1


def test_real_repair_catch_cannot_allow_a_cheaper_report(tmp_path, monkeypatch):
    from data_sheets_schema import api_runner as api
    from tests.test_download.test_api_runner import spec
    bundle = tmp_path / "bundle.txt"
    bundle.write_text("Synthetic input\n")
    run = spec(project="EXTERNAL", bundle=bundle, manifest=None, profile="neutral", out_dir=tmp_path)
    body = "id: x\nname: n\ntitle: T\ndescription: d\n"
    run.full_path.write_text(body)
    provider, capped, ledger = client(tmp_path, cap=0.1)
    monkeypatch.setattr(api, "MAX_ATTEMPTS", 1)
    monkeypatch.setattr(api, "_validator_lines", lambda *args: (["bad shape"], None))
    monkeypatch.setattr(api, "phase_max_tokens", lambda spec, phase, *args, **kw: 1000 if phase == "report" else 100000)
    settings = {"name": "claude-opus-5", "temperature": None, "temperature_applies": False, "max_tokens": 1000}
    log = api._repair_invalid(run, capped, settings, [])
    assert "remaining budget" in log[0]["outcome"]  # The real runner caught it.
    carry = {key: body for key in api.PHASE_NEEDS["report"]}
    assert api._regenerate_report(run, capped, settings, [], carry, phase="report_regate") is False
    assert provider.calls == 0 and provider.counts == 1
    with pytest.raises(BudgetStop, match="remaining budget"):
        capped.messages.require_active()  # Controller cannot call this completed.
    assert json.loads(ledger.path.read_bytes())["requests"] == []


@pytest.mark.parametrize("failure,status", [("lost", "pending"), ("model", "protocol_failure"), ("charge", "over_reservation")])
def test_last_report_failure_stops_without_a_subsequent_request(tmp_path, monkeypatch, failure, status):
    from data_sheets_schema import api_runner as api
    from tests.test_download.test_api_runner import spec
    bundle = tmp_path / "bundle.txt"
    bundle.write_text("Synthetic input\n")
    run = spec(project="EXTERNAL", bundle=bundle, manifest=None, profile="neutral", out_dir=tmp_path)
    provider, capped, ledger = client(tmp_path, fail=failure == "lost")
    original = provider.create
    def failed_response(**request):
        value = original(**request).model_dump()
        if failure == "model":
            value["model"] = "unexpected-model"
        if failure == "charge":
            value["usage"]["output_tokens"] = 1000000
        return SimpleNamespace(model_dump=lambda **kw: value)
    provider.create = failed_response
    monkeypatch.setattr(api, "MAX_ATTEMPTS", 1)
    monkeypatch.setattr(api, "phase_max_tokens", lambda *args, **kw: 1000)
    settings = {"name": "claude-opus-5", "temperature": None, "temperature_applies": False, "max_tokens": 1000}
    carry = {key: "id: x\nname: n\ntitle: T\ndescription: d\n" for key in api.PHASE_NEEDS["report"]}
    assert api._regenerate_report(run, capped, settings, [], carry, phase="report_regate") is False
    assert provider.calls == provider.counts == 1
    state = json.loads(ledger.path.read_bytes())
    assert state["requests"][0]["status"] == status
    with pytest.raises(BudgetStop):
        capped.messages.require_active()
    _, restarted, _ = client(tmp_path)
    with pytest.raises(BudgetStop):
        restarted.messages.require_active()
    assert "canary-1" in state["stopped_attempts"]


@pytest.mark.parametrize("status", ["pending", "protocol_failure", "over_reservation"])
def test_final_check_rejects_unsettled_rows_even_without_a_stop_event(tmp_path, status):
    _, capped, ledger = client(tmp_path)
    ticket = ledger.reserve("interrupted-earlier-attempt", 0.1, "request")
    if status != "pending":
        with pytest.raises(BudgetStop):
            ledger.settle(ticket, 0.2 if status == "over_reservation" else 0.01,
                          response_sha256="response", usage={},
                          protocol_failure="unexpected model" if status == "protocol_failure" else None)
    with pytest.raises(BudgetStop, match="pending or unknown"):
        capped.messages.require_active()


def test_unknown_charge_blocks_a_new_attempt(tmp_path):
    provider, capped, ledger = client(tmp_path, fail=True)
    with pytest.raises(TimeoutError):
        capped.messages.create(**REQUEST)
    assert json.loads(ledger.path.read_bytes())["requests"][0]["status"] == "pending"
    with pytest.raises(BudgetStop, match="pending or unknown"):
        ledger.reserve("a-new-attempt", 0.05, "request")
    assert provider.calls == 1


def test_manifest_change_stops_before_count_or_generation(tmp_path):
    def changed():
        raise BudgetStop("pin changed")
    provider, capped, _ = client(tmp_path, verify=changed)
    with pytest.raises(BudgetStop, match="pin changed"):
        capped.messages.create(**REQUEST)
    assert provider.calls == provider.counts == 0


def test_stream_settles_only_once(tmp_path):
    provider, capped, ledger = client(tmp_path)
    with capped.messages.stream(**REQUEST) as stream:
        assert stream.get_final_message() is stream.get_final_message()
    assert provider.calls == 1
    assert len(json.loads(ledger.path.read_bytes())["requests"]) == 1


def test_total_and_attempt_caps_are_independent(tmp_path):
    ledger = Ledger(tmp_path / "ledger.json", manifest_sha256="test", total_cap=6, attempt_cap=5)
    ticket = ledger.reserve("a", 4, "one")
    ledger.settle(ticket, 4, response_sha256="response", usage={})
    with pytest.raises(BudgetStop):
        ledger.reserve("a", 1.01, "two")
    ticket = ledger.reserve("b", 2, "two")
    ledger.settle(ticket, 2, response_sha256="response", usage={})
    with pytest.raises(BudgetStop):
        ledger.reserve("c", 0.01, "three")


def test_over_reservation_stops_further_spend(tmp_path):
    ledger = Ledger(tmp_path / "ledger.json", manifest_sha256="test")
    ticket = ledger.reserve("a", 0.1, "one")
    with pytest.raises(BudgetStop, match="exceeded"):
        ledger.settle(ticket, 0.11, response_sha256="response", usage={})
    with pytest.raises(BudgetStop, match="pending or unknown"):
        ledger.reserve("b", 0.1, "two")


@pytest.mark.parametrize("charge", [-1, "NaN", "Infinity"])
def test_invalid_charge_cannot_release_reservation(tmp_path, charge):
    ledger = Ledger(tmp_path / "ledger.json", manifest_sha256="test")
    ticket = ledger.reserve("a", 0.1, "one")
    with pytest.raises(BudgetStop, match="invalid response charge"):
        ledger.settle(ticket, charge, response_sha256="response", usage={})
    with pytest.raises(BudgetStop, match="pending or unknown"):
        ledger.reserve("b", 0.1, "two")


def test_unexpected_model_prevents_later_spending(tmp_path):
    provider, capped, ledger = client(tmp_path)
    original = provider.create
    def substituted(**request):
        value = original(**request).model_dump()
        value["model"] = "unregistered-model"
        return SimpleNamespace(model_dump=lambda **kw: value)
    provider.create = substituted
    with pytest.raises(BudgetStop, match="returned model differs"):
        capped.messages.create(**REQUEST)
    row = json.loads(ledger.path.read_bytes())["requests"][0]
    assert row["status"] == "protocol_failure" and "cost_usd" in row
    with pytest.raises(BudgetStop, match="pending or unknown"):
        ledger.reserve("later", 0.1, "two")


def test_negative_cache_usage_keeps_unknown_charge_reserved(tmp_path):
    provider, capped, ledger = client(tmp_path)
    original = provider.create
    def invalid(**request):
        value = original(**request).model_dump()
        value["usage"]["cache_read_input_tokens"] = -10000
        return SimpleNamespace(model_dump=lambda **kw: value)
    provider.create = invalid
    with pytest.raises(BudgetStop, match="invalid response token counts"):
        capped.messages.create(**REQUEST)
    assert json.loads(ledger.path.read_bytes())["requests"][0]["status"] == "pending"


@pytest.mark.parametrize("project", ["CHORUS", "KIDS_FIRST"])
@pytest.mark.parametrize("stop_reason", ["end_turn", None])
def test_registered_first_request_passes_real_runner_and_sdk_offline(tmp_path, monkeypatch, project, stop_reason):
    """Exercise actual request assembly, SDK token count and SSE handling.

    Every HTTP request terminates in MockTransport; no provider is contacted.
    """
    import anthropic
    import httpx
    from data_sheets_schema import api_runner
    monkeypatch.setattr(api_runner, "MAX_ATTEMPTS", 1)
    here = Path(__file__).resolve().parent
    request = json.loads((here / "initial_requests" / f"{project}_api_rep1.json").read_bytes())
    observed = json.loads((here / "api_initial_admission.json").read_bytes())["requests"]
    count = next(row["input_tokens"] for row in observed if row["job"] == f"{project}_api_rep1")
    paths = []
    def respond(http_request):
        paths.append(http_request.url.path)
        if http_request.url.path.endswith("/count_tokens"):
            return httpx.Response(200, json={"input_tokens": count})
        body = json.loads(http_request.content)
        assert body.pop("stream") is True
        assert body == request
        events = [
            {"type": "message_start", "message": {"id": "offline", "type": "message", "role": "assistant",
             "model": request["model"], "content": [], "stop_reason": None, "stop_sequence": None,
             "usage": {"input_tokens": count, "output_tokens": 0}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "offline fixture"}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": stop_reason, "stop_sequence": None}, "usage": {"output_tokens": 1}},
            {"type": "message_stop"},
        ]
        wire = "".join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events)
        return httpx.Response(200, content=wire, headers={"Content-Type": "text/event-stream"})
    sdk = anthropic.Anthropic(api_key="offline-fixture-key", base_url="https://offline.example.invalid",
        max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    ledger = Ledger(tmp_path / "ledger.json", manifest_sha256="offline")
    capped = CappedClient(sdk, ledger=ledger, attempt="offline", evidence=tmp_path / "requests",
        model=request["model"], prices=PRICES, verify=lambda: None, initial_request=request)
    if stop_reason is None:
        with pytest.raises(BudgetStop, match="completion is unverified"):
            api_runner._call_with_retry(capped, **request, temperature=0, wall_clock=5)
        assert json.loads(ledger.path.read_bytes())["requests"][0]["status"] == "pending"
        assert len(list((tmp_path / "requests").rglob("response.json"))) == 1
        with pytest.raises(BudgetStop, match="pending or unknown"):
            ledger.reserve("another-attempt", 0.001, "next-request")
    else:
        result = api_runner._call_with_retry(capped, **request, temperature=0, wall_clock=5)
        assert result.stop_reason == "end_turn" and result.content[0].text == "offline fixture"
        assert json.loads(ledger.path.read_bytes())["requests"][0]["status"] == "settled"
    assert paths == ["/v1/messages/count_tokens", "/v1/messages"]
    sdk.close()
