"""Real SDK/HTTP stream failures stay failures and retain bounded evidence.

All HTTP requests terminate in MockTransport; no provider or token-count call.
"""
import json
import threading
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from data_sheets_schema import api_runner as runner
from data_sheets_schema.stream_evidence import RECENT_EVENTS


def start():
    return {"type": "message_start", "message": {
        "id": "offline-message", "type": "message", "role": "assistant",
        "model": "offline-model", "content": [], "stop_reason": None,
        "stop_sequence": None, "usage": {"input_tokens": 20, "output_tokens": 7},
    }}


DELTA = {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
         "usage": {"output_tokens": 10}}
STOP = {"type": "message_stop"}


class Wire(httpx.SyncByteStream):
    def __init__(self, events, *, cut=False):
        self.events = events
        self.cut = cut

    def __iter__(self):
        for event in self.events:
            yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode()
        if self.cut:
            raise httpx.RemoteProtocolError("incomplete chunked body")


def sdk(events, *, cut=False, headers=None):
    def respond(request):
        assert request.url.path == "/v1/messages"
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(200, stream=Wire(events, cut=cut), headers={
            "content-type": "text/event-stream", "request-id": "offline-request-id",
            "x-litellm-call-id": "offline-proxy-id", "authorization": "never-record-this",
            **(headers or {}),
        })
    return anthropic.Anthropic(api_key="offline-fixture", base_url="https://offline.invalid",
                              max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(respond)))


def call(client, seen, **kwargs):
    return runner._call_with_retry(client, model="offline-model", max_tokens=100,
                                   temperature=None, system="s", messages=[{"role": "user", "content": "q"}],
                                   on_incomplete=seen.append, sleep=lambda _: None, **kwargs)


@pytest.fixture(autouse=True)
def single_attempt(monkeypatch):
    monkeypatch.setattr(runner, "MAX_ATTEMPTS", 1)


@pytest.mark.parametrize("cut", [False, True])
@pytest.mark.parametrize("events", [[], [start()], [start(), DELTA]])
def test_empty_success_http_status_never_hides_missing_terminal_event(events, cut):
    seen = []
    with sdk(events, cut=cut) as client:
        with pytest.raises(httpx.RemoteProtocolError if cut else runner.IncompleteStreamError):
            call(client, seen)
    (info,) = seen
    trace = info["stream_trace"]
    assert info["events"] == trace["events"] == len(events)
    assert trace["http_status"] == 200
    assert trace["message_start_seen"] is bool(events)
    assert trace["message_delta_seen"] is (len(events) == 2)
    assert trace["message_stop_seen"] is False
    assert trace["correlation_headers"] == {"request-id": "offline-request-id", "x-litellm-call-id": "offline-proxy-id"}
    assert trace["exception_type"] == ("RemoteProtocolError" if cut else "IncompleteStreamError")
    assert trace["headers_seconds"] >= 0
    assert "never-record-this" not in json.dumps(info)
    if events:
        assert trace["headers_seconds"] <= trace["first_event_seconds"] <= trace["last_event_seconds"]
        assert info["usage"]["output_tokens"] == (10 if len(events) == 2 else 7)


def test_complete_stream_is_accepted_and_transport_failure_after_stop_is_not():
    seen = []
    with sdk([start(), DELTA, STOP]) as client:
        assert call(client, seen).stop_reason == "end_turn"
    assert seen == []
    with sdk([start(), DELTA, STOP], cut=True) as client:
        with pytest.raises(httpx.RemoteProtocolError):
            call(client, seen)
    trace = seen[0]["stream_trace"]
    assert trace["message_stop_seen"] is True
    assert trace["stop_reason"] == "end_turn"
    assert trace["exception_type"] == "RemoteProtocolError"


def test_framed_close_without_stop_reason_is_described_accurately():
    seen = []
    delta = {**DELTA, "delta": {"stop_reason": None, "stop_sequence": None}}
    with sdk([start(), delta, STOP]) as client:
        with pytest.raises(runner.IncompleteStreamError): call(client, seen)
    assert seen[0]["stream_trace"]["message_stop_seen"] is True
    assert seen[0]["stream_trace"]["stop_reason"] is None
    assert seen[0]["outcome"] == "stream closed with no stop_reason (#1013)"


def test_thinking_payload_and_filtered_wire_pings_are_not_claimed_as_trace_data():
    events = [start(), {"type": "ping"},
              {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
              {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "private-reasoning-payload"}}]
    seen = []
    with sdk(events, cut=True) as client:
        with pytest.raises(httpx.RemoteProtocolError):
            call(client, seen)
    trace = seen[0]["stream_trace"]
    assert trace["observation"] == "sdk_events_not_wire_sse"
    assert trace["content_block_counts"] == {"thinking": 1}
    assert trace["event_counts"]["thinking"] == 1  # SDK-generated event, not a wire frame.
    assert "ping" not in trace["event_counts"]  # Pinned SDK filters it.
    assert "private-reasoning-payload" not in json.dumps(seen)
    assert seen[0]["content_chars"] == 0


@pytest.mark.parametrize("error_type", ["overloaded_error", "invalid_request_error"])
def test_sse_errors_keep_declared_error_and_http_status_even_when_not_retryable(error_type):
    seen = []
    events = [start(), {"type": "error", "error": {"type": error_type, "message": "fixture failure"}}]
    with sdk(events) as client:
        with pytest.raises(anthropic.APIStatusError):
            call(client, seen)
    (info,) = seen
    trace = info["stream_trace"]
    assert trace["http_status"] == 200
    assert trace["events"] == 1
    assert trace["provider_error_type"] == error_type
    assert trace["exception_type"] == "APIStatusError"
    assert "error" not in trace["event_counts"]  # SDK raises before yielding.


def test_http_error_before_iteration_keeps_unknown_event_count():
    def respond(request):
        return httpx.Response(429, json={"error": {"type": "rate_limit_error", "message": "fixture"}},
                              headers={"request-id": "offline-limit"})
    seen = []
    with anthropic.Anthropic(api_key="offline", max_retries=0,
                             http_client=httpx.Client(transport=httpx.MockTransport(respond))) as client:
        with pytest.raises(anthropic.RateLimitError):
            call(client, seen)
    trace = seen[0]["stream_trace"]
    assert trace["events"] is None and trace["iterable"] is None
    assert trace["message_start_seen"] is None
    assert trace["http_status"] == 429
    assert trace["correlation_headers"] == {"request-id": "offline-limit"}


def test_correlation_header_values_are_bounded_and_allowlisted():
    seen = []
    with sdk([start()], headers={"request-id": "x" * 161, "x-request-id": "unsafe value", "cf-ray": "fixture-ray-1"}) as client:
        with pytest.raises(runner.IncompleteStreamError):
            call(client, seen)
    assert seen[0]["stream_trace"]["correlation_headers"] == {
        "x-litellm-call-id": "offline-proxy-id", "cf-ray": "fixture-ray-1"}


def test_unknown_event_flood_cannot_grow_metadata_without_bound():
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def __iter__(self):
            for n in range(1000):
                yield SimpleNamespace(type=f"untrusted-event-{n}", text="untrusted-payload")
    seen = []
    client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kwargs: Stream()))
    with pytest.raises(runner.IncompleteStreamError):
        call(client, seen)
    trace = seen[0]["stream_trace"]
    assert trace["events"] == 1000
    assert trace["event_counts"] == {"unknown": 1000}
    assert len(trace["recent_events"]) == RECENT_EVENTS
    assert trace["earlier_events"] == 1000 - RECENT_EVENTS
    assert len(json.dumps(trace)) < 2500
    assert "untrusted" not in json.dumps(trace)


def test_watchdog_snapshot_is_not_rewritten_by_late_worker_and_next_attempt(monkeypatch):
    release = threading.Event()
    late_done = threading.Event()
    calls = []
    class Stream:
        def __init__(self, first): self.first = first
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def close(self): pass
        def __iter__(self):
            yield SimpleNamespace(type="message_start")
            if self.first:
                release.wait(5)
                for _ in range(20): yield SimpleNamespace(type="content_block_delta")
                yield SimpleNamespace(type="message_stop")
                late_done.set()
            else:
                release.set()
                assert late_done.wait(2)
                raise httpx.RemoteProtocolError("second request interrupted")
        def get_final_message(self): return SimpleNamespace(stop_reason="end_turn")
    def stream(**kwargs):
        calls.append(1)
        return Stream(first=len(calls) == 1)
    monkeypatch.setattr(runner, "MAX_ATTEMPTS", 2)
    seen = []
    try:
        with pytest.raises(httpx.RemoteProtocolError):
            call(SimpleNamespace(messages=SimpleNamespace(stream=stream)), seen, wall_clock=0.3)
        assert len(calls) == len(seen) == 2
        first, second = [info["stream_trace"] for info in seen]
        assert first["events"] == second["events"] == 1
        assert first["message_stop_seen"] is second["message_stop_seen"] is False
        assert first["exception_type"] == "RuntimeError"
        assert second["exception_type"] == "RemoteProtocolError"
    finally:
        release.set()


def test_trace_survives_snapshot_journal_and_record_merge(tmp_path):
    spec = runner.RunSpec(project="P", arm="", method="m", bundle=tmp_path / "b.txt", label="L", out_dir=tmp_path)
    seen = []
    with sdk([start()], cut=True) as client:
        with pytest.raises(httpx.RemoteProtocolError): call(client, seen)
    usage = []
    runner._record_incomplete_stream(spec, "full", 1, "fixture-time", seen[0], usage, max_tokens=100)
    (persisted,) = runner._abandoned_rows(spec)
    trace = seen[0]["stream_trace"]
    assert persisted["stream_trace"] == trace
    snapshot = Path(persisted["snapshot"]).read_text()
    line = next(line for line in snapshot.splitlines() if line.startswith("# stream trace: "))
    assert json.loads(line.removeprefix("# stream trace: ")) == trace
    assert runner.merge_abandoned_rows(spec, [])[0]["stream_trace"] == trace
    assert persisted["output_tokens"] == 7  # A partial snapshot, never promoted to final usage.


def test_delayed_watchdog_close_targets_its_original_stream(monkeypatch):
    """Delay close-thread scheduling until two abandoned attempts have unwound."""
    real_thread = threading.Thread
    callbacks = []
    closed = []
    opened = []
    release = threading.Event()

    def thread_factory(*args, **kwargs):
        if kwargs.get("name", "").startswith("phase-call-"):
            return real_thread(*args, **kwargs)
        return SimpleNamespace(start=lambda: callbacks.append(kwargs["target"]))

    class Stream:
        def __init__(self, number): self.number = number
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def __iter__(self):
            yield SimpleNamespace(type="message_start")
            release.wait(5)
            yield SimpleNamespace(type="message_stop")
        def close(self): closed.append(self.number)
        def get_final_message(self): return SimpleNamespace(stop_reason="end_turn")

    def stream(**kwargs):
        opened.append(1)
        return Stream(len(opened))

    monkeypatch.setattr(threading, "Thread", thread_factory)
    monkeypatch.setattr(runner, "MAX_ATTEMPTS", 2)
    try:
        with pytest.raises(RuntimeError, match="watchdog"):
            call(SimpleNamespace(messages=SimpleNamespace(stream=stream)), [], wall_clock=0.3)
        assert len(callbacks) == len(opened) == 2
        for close in callbacks:
            close()
        assert closed == [1, 2]
    finally:
        release.set()
