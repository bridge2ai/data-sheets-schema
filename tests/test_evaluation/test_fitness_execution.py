"""Real loopback dispatch of invented fitness messages, never calibration."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import socket
import threading

from click.testing import CliRunner
import pytest

from data_sheets_schema import nested_support_execution as ex, nested_support_results as saved
from data_sheets_schema import top_level_fitness_results as fit
from data_sheets_schema.cli.evaluate import evaluate
from data_sheets_schema.support_plan import canonical
from tests.test_evaluation.test_nested_support_execution import declaration, _CONNECT
from tests.test_evaluation.test_nested_support_plan import build
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401
from tests.test_evaluation.test_top_level_fitness_results import native


def reply(**changes):
    return native(usage={"input_tokens": 12, "output_tokens": 23,
                         "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}, **changes)


@pytest.fixture
def fitness_peer():
    state = {"requests": [], "responses": [(200, canonical(reply()))]}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            raw = self.rfile.read(int(self.headers["content-length"]))
            index = len(state["requests"])
            state["requests"].append({"raw": raw, "headers": dict(self.headers), "path": self.path})
            status, body = state["responses"][min(index, len(state["responses"]) - 1)]
            self.send_response(status)
            self.send_header("content-length", str(len(body)))
            self.send_header("request-id", f"invented-fitness-{index}")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    state["url"] = f"http://127.0.0.1:{server.server_port}/v1/messages"
    state["port"] = server.server_port
    yield state
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture
def make_fitness(fixture, fitness_peer, tmp_path, monkeypatch):
    manifest = build(fixture, max_tokens=417)
    selections = [{"target_id": t["id"], "attempt_id": f"fitness-{i}"}
                  for i, t in enumerate(manifest["targets"]) if t["axis"] == "fitness"]
    def connect(sock, address):
        assert address == ("127.0.0.1", fitness_peer["port"]), "non-fixture network access"
        return _CONNECT(sock, address)
    monkeypatch.setattr(socket.socket, "connect", connect)
    def prepare(*, count=1, name="case", change=None):
        root = tmp_path / name
        root.mkdir()
        descriptor, registration, output = root / "descriptor", root / "registration", root / "run"
        fit.prepare(fixture[1], descriptor, selections=selections[:count], protocol=fit.FORMAT)
        declared = declaration(fitness_peer, output)
        declared["format"] = ex.FITNESS_FORMAT
        if change:
            change(declared)
        declaration_path = root / "declaration.json"
        declaration_path.write_bytes(canonical(declared))
        value = ex.prepare(descriptor, declaration_path, registration)
        return registration, output, value, descriptor
    return prepare


def test_actual_fitness_cli_binding_and_relocated_captured_recheck(make_fitness, fitness_peer, tmp_path, monkeypatch):
    registration, output, reg, descriptor = make_fitness(count=2, change=lambda d: d["transport"].update(
        thinking={"type": "adaptive"}, effort="high"))
    descriptor_before = {str(p.relative_to(descriptor)): p.read_bytes() for p in descriptor.rglob("*") if p.is_file()}
    result = CliRunner().invoke(evaluate, ["support-execution", "run", "--registration", str(registration)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["format"] == ex.FITNESS_FORMAT and report["axis"] == "fitness"
    assert report["selected_counts"] == {"fitness_top_level": {"selected": 2, "accepted": 2, "failed": 0,
                                                               "spent_unknown": 0, "not_started": 0}}
    assert report["original_readiness"] == reg["original_readiness"]
    assert report["original_readiness"]["ready_for_paid_run"] is False
    assert report["scientific_eligibility"] is False
    assert report["observed_usage_totals"] == {"input_tokens": 24, "output_tokens": 46,
                                              "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    assert set(reg["implementation"]["sources"]) == set(ex._SOURCE_NAMES) | {
        "top_level_fitness_results.py", "schema_digest.py", "evidence_score.py"}
    for request, observed, row in zip(reg["requests"], fitness_peer["requests"], report["rows"]):
        original_raw = (registration / "artifacts" / request["planned_request"]["sha256"]).read_bytes()
        original = json.loads(original_raw)
        effective = {k: v for k, v in original.items() if k != "temperature"}
        effective.update(stream=False, thinking={"type": "adaptive"}, output_config={"effort": "high"})
        assert observed["raw"] == canonical(effective)
        assert observed["raw"] == (registration / "artifacts" / request["effective_request"]["sha256"]).read_bytes()
        assert row["saved_result"]["format"] == fit.FORMAT
        assert row["saved_result"]["binding"]["request"] == request["planned_request"]
        assert row["saved_result"]["assessment"]["fitness"] == .75
        assert row["saved_result"]["assessment"]["failure"] == "form"
        assert "verdict" not in row["saved_result"]["assessment"]
        assert row["saved_result"]["scientific_scoring_eligible"] is False
    assert descriptor_before == {str(p.relative_to(descriptor)): p.read_bytes() for p in descriptor.rglob("*") if p.is_file()}
    with pytest.raises(ValueError):
        ex.run(registration)
    assert len(fitness_peer["requests"]) == 2
    moved = tmp_path / "relocated"
    shutil.copytree(output, moved)
    for path in (registration, descriptor, output):
        path.rename(path.with_name(path.name + "-unavailable"))
    old = Path.read_bytes
    def captured_only(path):
        assert path.is_relative_to(moved), path
        return old(path)
    monkeypatch.setattr(Path, "read_bytes", captured_only)
    monkeypatch.setattr(ex, "_identity", lambda *a: pytest.fail("ambient source identity"))
    monkeypatch.setattr(socket.socket, "connect", lambda *a: pytest.fail("network during recheck"))
    assert ex.recheck(moved) == report


@pytest.mark.parametrize("change", [
    {"content": [{"type": "text", "text": '{"verdict":"supported","reason":"wrong instrument"}'}]},
    {"content": [{"type": "text", "text": '{"fitness":true,"failure":"none","reason":"wrong type"}'}]},
    {"model": "different-model"}, {"stop_reason": "max_tokens"},
])
def test_actual_fitness_strict_rejection_stops_selected_suffix(make_fitness, fitness_peer, change):
    fitness_peer["responses"] = [(200, canonical(reply(**change)))]
    registration, output, _, _ = make_fitness(count=2)
    report = ex.run(registration)
    assert len(fitness_peer["requests"]) == 1
    row = report["rows"][0]
    assert row["status"] == "failed" and row["saved_result"]["assessment"]["status"] == "rejected"
    assert report["selected_counts"]["fitness_top_level"]["not_started"] == 1
    assert report["scientific_eligibility"] is False
    assert ex.recheck(output) == report


def test_mixed_success_and_failed_http_retain_assessment_and_usage(make_fitness, fitness_peer):
    fitness_peer["responses"] = [(200, canonical(reply())), (429, canonical(reply()))]
    registration, output, _, _ = make_fitness(count=2, change=lambda d: d.update(prices={
        "currency": "TEST", "per_tokens": 1000, "source": "invented", "as_of": "fictional",
        "rates": {k: "1" for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}}))
    report = ex.run(registration)
    assert [r["status"] for r in report["rows"]] == ["accepted", "failed"]
    assert all(r["saved_result"]["assessment"]["status"] == "accepted" for r in report["rows"])
    assert report["accepted_accounted_input_tokens"] == 12
    assert report["accepted_accounted_output_tokens"] == 23
    assert report["observed_usage_totals"]["input_tokens"] == 24
    assert report["observed_usage_totals"]["output_tokens"] == 46
    assert report["observed_cost"] == "0.070"
    assert not report["all_selected_accepted"] and not report["scientific_eligibility"]
    assert ex.recheck(output) == report


def test_unknown_cache_usage_cannot_become_accounted_success(make_fitness, fitness_peer):
    fitness_peer["responses"] = [(200, canonical(native()))]
    registration, output, _, _ = make_fitness(count=2)
    report = ex.run(registration)
    row = report["rows"][0]
    assert row["saved_result"]["assessment"]["status"] == "accepted"
    assert row["status"] == "failed" and "usage_unknown_or_incomplete" in row["problems"]
    assert report["observed_usage_totals"]["cache_read_input_tokens"] is None
    assert report["selected_counts"]["fitness_top_level"]["not_started"] == 1
    assert ex.recheck(output) == report


def test_instrument_swap_and_missing_fitness_identity_refuse(make_fitness, fitness_peer, monkeypatch):
    with pytest.raises(ValueError):
        make_fitness(name="wrong-family", change=lambda d: d.update(format=ex.FORMAT))
    registration, output, reg, _ = make_fitness()
    wrong = copy.deepcopy(reg["implementation"])
    wrong["sources"]["schema_digest.py"]["sha256"] = "0" * 64
    monkeypatch.setattr(ex, "_identity", lambda *a: wrong)
    with pytest.raises(ex.ExecutionError, match="implementation/runtime differs"):
        ex.run(registration)
    assert not output.exists() and not fitness_peer["requests"]


def test_captured_ledger_and_admission_cannot_switch_instruments(make_fitness):
    registration, output, _, _ = make_fitness()
    ex.run(registration)
    capture, ledger = ex.capture_run(output)
    changed = copy.deepcopy(ledger)
    changed["format"] = ex.FORMAT
    with pytest.raises(ex.ExecutionError, match="registered instrument"):
        ex.recheck_captured(capture, changed)
    admission = json.loads(capture.get(ledger["attempts"][0]["admitted"]))
    admission["format"] = ex.FORMAT
    changed = copy.deepcopy(ledger)
    changed["attempts"][0]["admitted"] = capture.add(canonical(admission))
    with pytest.raises(ex.ExecutionError, match="admission differs"):
        ex.recheck_captured(capture, changed)
