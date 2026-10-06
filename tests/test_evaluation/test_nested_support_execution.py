"""Invented loopback replies exercise the actual HTTP boundary, not accuracy."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import socket
from urllib.parse import urlsplit
import threading
import time

from click.testing import CliRunner
import pytest

from data_sheets_schema import nested_support_execution as ex, nested_support_results as saved
from data_sheets_schema.cli.evaluate import evaluate
from data_sheets_schema.support_plan import canonical
from tests.test_evaluation.test_nested_support_results import plan, native  # noqa: F401
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401


_CONNECT = socket.socket.connect


def reply(**changes):
    return native(usage={"input_tokens": 12, "output_tokens": 23,
                         "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}, **changes)


@pytest.fixture
def peer():
    state = {"requests": [], "body": canonical(reply()), "status": 200, "delay": 0,
             "headers": {}, "declared_length": None}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["content-length"]))
            state["requests"].append({"path": self.path, "headers": dict(self.headers), "raw": body})
            time.sleep(state["delay"])
            try:
                self.send_response(state["status"])
                self.send_header("content-length", str(state["declared_length"] or len(state["body"])))
                self.send_header("request-id", "invented-request")
                for k, v in state["headers"].items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(state["body"])
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    state["url"] = f"http://127.0.0.1:{server.server_port}/v1/messages"
    yield state
    server.shutdown()
    server.server_close()
    thread.join()


def declaration(peer, output):
    return {"format": ex.FORMAT, "registration_id": "synthetic-registration", "purpose": "local_fixture",
            "run_output": str(output.resolve()),
            "transport": {"adapter": ex.ADAPTER, "url": peer["url"], "model": "judge", "auth": "none",
                "anthropic_version": "2023-06-01", "timeout_ms": 2000, "thinking": None,
                "effort": None, "retries": 0, "redirects": False, "environment_proxies": False},
            "limits": {"max_calls": 2, "request_bytes": 100_000, "response_bytes": 50_000,
                "total_response_bytes": 100_002, "input_reservation_per_call": 100,
                "input_scheduling_threshold": 200, "output_scheduling_threshold": 834},
            "decisions": {k: None for k in ("instrument_review", "context_review", "controls_review",
                "private_control_handling", "paid_authorization", "calibration_acceptance", "canary_acceptance")},
            "prices": None}


@pytest.fixture
def make(plan, tmp_path, peer, monkeypatch):
    # The inherited offline planner fixture forbids all connects. Permit only
    # this real fixture socket after its plan is built; external calls still fail.
    endpoint = urlsplit(peer["url"])
    def connect(sock, address):
        assert address == ("127.0.0.1", endpoint.port), "non-fixture network access"
        return _CONNECT(sock, address)
    monkeypatch.setattr(socket.socket, "connect", connect)
    def build(*, count=1, change=None, name="one"):
        root = tmp_path / name
        root.mkdir()
        descriptor, registered, output = root / "descriptor", root / "registered", root / "run"
        saved.prepare(plan[1], descriptor, selections=plan[-1][:count], protocol=saved.FORMAT)
        declared = declaration(peer, output)
        if change:
            change(declared)
        path = root / "declaration.json"
        path.write_bytes(canonical(declared))
        reg = ex.prepare(descriptor, path, registered)
        return registered, output, reg, descriptor
    return build


def test_actual_cli_http_request_raw_binding_usage_and_offline_report(make, peer, monkeypatch):
    registered, output, reg, descriptor = make(count=2, change=lambda d: d.update(prices={
        "currency": "TEST", "per_tokens": 1000, "source": "fictional fixture", "as_of": "synthetic",
        "rates": {k: "1" for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}}))
    original = {str(p.relative_to(descriptor)): p.read_bytes() for p in descriptor.rglob("*") if p.is_file()}
    runner = CliRunner()
    result = runner.invoke(evaluate, ["support-execution", "run", "--registration", str(registered)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["admitted_calls"] == 2 and report["all_selected_accepted"]
    assert report["scientific_eligibility"] is False
    assert report["original_readiness"] == reg["original_readiness"]
    assert report["original_readiness"]["ready_for_paid_run"] is False
    assert report["observed_usage_totals"]["input_tokens"] == 24
    assert report["observed_cost"] == "0.070"
    for request, observed, row in zip(reg["requests"], peer["requests"], report["rows"]):
        assert observed["raw"] == (registered / "artifacts" / request["effective_request"]["sha256"]).read_bytes()
        body = json.loads(observed["raw"])
        assert body["max_tokens"] == 417 and body["stream"] is False
        assert "temperature" not in body and "thinking" not in body
        assert "authorization" not in {k.lower(): v for k, v in observed["headers"].items()}
        result = row["saved_result"]
        assert result["assessment"]["reasoning"][0]["thinking"] == "Invented test reasoning"
        assert (output / "artifacts" / result["response"]["sha256"]).read_bytes() == peer["body"]
    assert original == {str(p.relative_to(descriptor)): p.read_bytes() for p in descriptor.rglob("*") if p.is_file()}
    monkeypatch.setattr(ex, "_dispatch", lambda *a, **k: pytest.fail("recheck dispatched"))
    assert ex.recheck(output) == report
    assert runner.invoke(evaluate, ["support-execution", "recheck", "--run", str(output)]).exit_code == 0
    copied = registered.parent / "copy"
    shutil.copytree(registered, copied)
    with pytest.raises(ValueError, match="exist"):
        ex.run(copied)
    assert len(peer["requests"]) == 2


@pytest.mark.parametrize("case", ["wrong_model", "malformed", "unknown_cache", "over_input", "over_output",
                                  "status", "redirect", "encoding", "oversize", "timeout", "partial"])
def test_one_failed_call_preserves_raw_and_stops_without_retry(make, peer, case):
    change = None
    if case == "wrong_model": peer["body"] = canonical(reply(model="different"))
    elif case == "malformed": peer["body"] = b"{"
    elif case == "unknown_cache": peer["body"] = canonical(native())
    elif case in ("over_input", "over_output"):
        value = reply()
        value["usage"]["input_tokens" if case == "over_input" else "output_tokens"] = 101 if case == "over_input" else 418
        peer["body"] = canonical(value)
    elif case == "status": peer["status"] = 429
    elif case == "redirect":
        peer["status"] = 302
        peer["headers"]["location"] = peer["url"]
    elif case == "encoding": peer["headers"]["content-encoding"] = "gzip"
    elif case == "oversize": peer["body"] = b"x" * 51_000
    elif case == "timeout":
        peer["delay"] = .08
        change = lambda d: d["transport"].update(timeout_ms=20)
    elif case == "partial": peer["declared_length"] = len(peer["body"]) + 30
    registered, output, _, _ = make(count=2, change=change)
    report = ex.run(registered)
    assert len(peer["requests"]) == 1
    assert report["rows"][0]["status"] == "failed" and not report["all_selected_accepted"]
    assert sum(c["not_started"] for c in report["selected_counts"].values()) == 1
    outcome = json.loads((output / "attempts/000000/response.json").read_bytes())
    captured = (output / "artifacts" / outcome["body"]["sha256"]).read_bytes()
    if case not in ("timeout", "partial"):
        assert captured == peer["body"][:50_001]
    if case == "unknown_cache":
        assert report["rows"][0]["saved_result"]["assessment"]["status"] == "accepted"
        assert report["observed_usage_totals"]["cache_read_input_tokens"] is None
    if case == "over_input":
        assert report["observed_usage_totals"]["input_tokens"] == 101
    if case == "status":
        assert outcome["status_code"] == 429
        assert report["observed_usage_totals"]["input_tokens"] == 12
        assert report["observed_usage_totals"]["output_tokens"] == 23
        assert report["rows"][0]["saved_result"]["assessment"]["status"] == "accepted"
        assert "transport_not_successful" in report["rows"][0]["problems"]
    assert ex.recheck(output) == report
    with pytest.raises(ValueError):
        ex.run(registered)
    assert len(peer["requests"]) == 1


@pytest.mark.parametrize("case", ["bool_calls", "hard_spend", "header", "query", "credentials", "external_fixture",
                                  "approval", "model", "request_limit", "price_nan", "proxy", "retry"])
def test_invalid_declarations_refuse_before_admission(make, peer, case):
    def change(d):
        if case == "bool_calls": d["limits"]["max_calls"] = True
        elif case == "hard_spend": d["limits"]["hard_dollar_cap"] = 1
        elif case == "header": d["transport"]["anthropic_version"] = "version\r\nInjected: value"
        elif case == "query": d["transport"]["url"] += "?key=secret"
        elif case == "credentials": d["transport"]["url"] = d["transport"]["url"].replace("http://", "http://user:pass@")
        elif case == "external_fixture": d["transport"]["url"] = "https://example.invalid/v1/messages"
        elif case == "approval": d["decisions"]["paid_authorization"] = {"reference": "fictional", "sha256": "0" * 64}
        elif case == "model": d["transport"]["model"] = "other"
        elif case == "request_limit": d["limits"]["request_bytes"] = 1
        elif case == "price_nan": d["prices"] = {"currency": "TEST", "per_tokens": 1000, "source": "fictional", "as_of": "synthetic", "rates": {"input_tokens": "NaN"}}
        elif case == "proxy": d["transport"]["environment_proxies"] = True
        elif case == "retry": d["transport"]["retries"] = 1
    with pytest.raises(ValueError):
        make(change=change)
    assert peer["requests"] == []


@pytest.mark.parametrize("point", ["admitted", "raw"])
def test_crash_is_spent_and_raw_settlement_recovers_without_http(make, peer, monkeypatch, point):
    registered, output, _, _ = make(count=2)
    real = ex._exclusive
    def crash(path, raw):
        real(path, raw)
        if path.name == ("admitted.json" if point == "admitted" else "response.json"):
            raise OSError("injected interruption after durable boundary")
    monkeypatch.setattr(ex, "_exclusive", crash)
    with pytest.raises(OSError, match="injected"):
        ex.run(registered)
    monkeypatch.setattr(ex, "_exclusive", real)
    expected_calls = 0 if point == "admitted" else 1
    assert len(peer["requests"]) == expected_calls
    monkeypatch.setattr(ex, "_dispatch", lambda *a, **k: pytest.fail("offline recovery called HTTP"))
    first = ex.recheck(output)
    assert ex.recheck(output) == first
    assert first["rows"][0]["status"] == ("spent_unknown" if point == "admitted" else "accepted")
    with pytest.raises(ValueError):
        ex.run(registered)
    assert len(peer["requests"]) == expected_calls


def test_captured_ledger_relocates_and_rechecks_without_originals_or_network(make, peer, tmp_path, monkeypatch):
    registered, output, _, descriptor = make()
    expected = ex.run(registered)
    capture, ledger = ex.capture_run(output)
    portable = tmp_path / "portable"
    portable.mkdir()
    (portable / "artifacts").mkdir()
    for sha, raw in capture.blobs.items():
        (portable / "artifacts" / sha).write_bytes(raw)
    registered.rename(registered.with_name("registration-retained"))
    descriptor.rename(descriptor.with_name("descriptor-retained"))
    output.rename(output.with_name("run-retained"))
    import httpx
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: pytest.fail("captured replay constructed client"))
    monkeypatch.setattr(ex, "_identity", lambda: pytest.fail("captured replay read ambient implementation"))
    assert ex.recheck_captured(saved.Capture(portable), ledger) == expected
    changed = copy.deepcopy(ledger)
    changed["attempts"][0]["admitted"] = changed["attempts"][0]["response"]
    with pytest.raises((ValueError, KeyError)):
        ex.recheck_captured(saved.Capture(portable), changed)


def test_scheduling_ceiling_stops_at_actual_usage_not_assumed_cost(make, peer):
    registered, output, _, _ = make(count=2, change=lambda d: d["limits"].update(input_scheduling_threshold=100))
    result = ex.run(registered)
    assert len(peer["requests"]) == 1 and not result["all_selected_accepted"]
    assert result["observed_cost"] is None
    assert sum(c["not_started"] for c in result["selected_counts"].values()) == 1


def test_tampered_summary_or_alias_refuses(make, peer):
    registered, output, _, _ = make()
    ex.run(registered)
    report = output / "report.json"
    value = json.loads(report.read_bytes())
    value["scientific_eligibility"] = True
    report.write_bytes(canonical(value))
    with pytest.raises(ValueError, match="report differs"):
        ex.recheck(output)
    alias = output.with_name("alias")
    alias.symlink_to(output, target_is_directory=True)
    with pytest.raises(ValueError, match="real directory"):
        ex.recheck(alias)


def test_later_admission_requires_settlement_but_terminal_recovery_remains(make, peer):
    registered, output, _, _ = make(count=2)
    expected = ex.run(registered)
    mutant = output.with_name("missing-prior-settlement")
    terminal = output.with_name("missing-terminal-settlement")
    shutil.copytree(output, mutant)
    shutil.copytree(output, terminal)
    (mutant / "attempts/000000/settled.json").unlink()
    (terminal / "attempts/000001/settled.json").unlink()
    with pytest.raises(ValueError, match="preceding durable settlement"):
        ex.recheck(mutant)
    assert ex.recheck(terminal) == expected
    assert ex.recheck(output) == expected
    assert len(peer["requests"]) == 2


@pytest.mark.parametrize("rate", ["1e9999999", "1e-9999999", "1." + "1" * 33])
def test_extreme_decimal_rates_refuse_before_any_admission(make, peer, rate):
    def change(d):
        d["prices"] = {"currency": "TEST", "per_tokens": 1000, "source": "fictional", "as_of": "synthetic",
                       "rates": {"input_tokens": rate}}
    with pytest.raises(ValueError, match="precision/exponent"):
        make(change=change)
    assert peer["requests"] == []


def test_cost_arithmetic_is_explicit_and_failed_usage_is_preserved(make, peer):
    from decimal import localcontext, Inexact
    peer["status"] = 429
    rates = {k: "0.123456789012345678" for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}
    registered, output, _, _ = make(change=lambda d: d.update(prices={
        "currency": "TEST", "per_tokens": 3, "source": "fictional", "as_of": "synthetic", "rates": rates}))
    expected = ex.run(registered)
    assert expected["rows"][0]["status"] == "failed"
    assert expected["observed_cost"] is not None
    with localcontext() as context:
        context.prec = 2
        context.traps[Inexact] = True
        assert ex.recheck(output) == expected
    assert len(peer["requests"]) == 1


def test_raw_and_derived_storage_reservation_is_checked_before_http(make, peer, monkeypatch):
    registered, output, reg, _ = make(count=2)
    capture = saved.Capture(registered)
    ex._load(capture, capture.entry("registration.json"))
    # The allowance covers raw responses, envelopes, duplicated result fields
    # and descriptor/attempt metadata in a portable captured ledger.
    needed = (capture.total + 8 * reg["declaration"]["limits"]["total_response_bytes"]
              + 2 * reg["descriptor"]["bytes"] + 16_384 * len(reg["requests"]))
    monkeypatch.setattr(saved, "MAX_CAPTURE_BYTES", needed - 1)
    with pytest.raises(ValueError, match="remaining captured storage"):
        ex.run(registered)
    assert not output.exists() and peer["requests"] == []
    monkeypatch.setattr(saved, "MAX_CAPTURE_BYTES", needed)
    assert ex.run(registered)["all_selected_accepted"]
    assert len(peer["requests"]) == 2


def test_actual_positive_rejects_rehashed_impossible_transport_states(make, peer):
    registered, output, _, _ = make(count=2)
    expected = ex.run(registered)
    capture, ledger = ex.capture_run(output)
    original = json.loads(capture.get(ledger["attempts"][0]["response"]))
    assert original["stage"] == "complete" and original["body_complete"] is True
    assert ex.recheck_captured(capture, ledger) == expected
    for change in ({"stage": "connect_or_send"}, {"body_complete": False},
                   {"failure": "response_byte_limit_exceeded"},
                   {"stage": "response_body", "body_complete": False,
                    "failure": "unsupported_content_encoding"}):
        mutated = copy.deepcopy(ledger)
        mutated["attempts"][0]["response"] = capture.add(canonical({**original, **change}))
        with pytest.raises(ValueError, match="conflict|requires"):
            ex.recheck_captured(capture, mutated)
    assert ex.recheck(output) == expected
    assert len(peer["requests"]) == 2
