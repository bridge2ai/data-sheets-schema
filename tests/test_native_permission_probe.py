"""Probe software tests use invented records/mocks; no native binary or API."""
from contextlib import contextmanager
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_permission_probe as probe
from data_sheets_schema import native_probe_provider as provider
from data_sheets_schema import native_subscription_guard as guard
from tests.test_native_execution_permissions import fixture as legacy_fixture
from tests.test_native_shared_permissions import fixture as shared_fixture
from tests.test_native_shared_permissions import fabricated_manifest


def test_scripted_provider_is_exact_sequence_and_has_no_model_answer():
    cases = [{"id": "a", "tool": "Read", "input": {"file_path": "/invented"}},
             {"id": "b", "tool": "Write", "input": {"file_path": "/invented", "content": "test"}}]
    body = {"model": "synthetic", "messages": []}
    payload = provider.response_payload(body, cases, "synthetic")
    assert payload["content"][0]["id"] == "a"
    body["messages"] = [{"content": [{"type": "tool_result", "tool_use_id": "a"}]}]
    assert provider.response_payload(body, cases, "synthetic")["content"][0]["id"] == "b"
    body["messages"][0]["content"].append({"type": "tool_result", "tool_use_id": "b"})
    final = provider.response_payload(body, cases, "synthetic")
    assert final["content"] == [{"type": "text", "text": "OFFLINE_COMPLETE"}]
    assert final["usage"] == {"input_tokens": 0, "output_tokens": 0}  # local stub, never calibration
    kind, raw = provider.encode_response(payload, True)
    assert kind == "text/event-stream" and b"message_stop" in raw and b"input_json_delta" in raw
    assert json.loads(provider.encode_response(payload, False)[1]) == payload
    body["messages"][0]["content"].reverse()
    with pytest.raises(ValueError, match="order"):
        provider.response_payload(body, cases, "synthetic")
    with pytest.raises(ValueError, match="model"):
        provider.response_payload(body, cases, "different")


def test_shared_fixed_selector_is_executed():
    from data_sheets_schema import native_shared_permissions as p
    namespace = {}
    exec(p.recipe_sources()["recipe/provider.py"], namespace)
    calls = []
    def reply(cases, number):
        calls.append(number)
        return namespace["reply"](cases, number)
    cases = [{"id": "x", "tool": "Read", "input": {}}]
    result = provider.response_payload({"model": "test", "messages": []}, cases, "test", reply=reply)
    assert calls == [0] and result["content"][0]["id"] == "x"


def test_bounded_writes_never_append_over_limit():
    output = io.BytesIO()
    sink = probe._Bounded(output, 2)
    sink.write(b"12")
    with pytest.raises(ValueError, match="bound"):
        sink.write(b"3")
    assert output.getvalue() == b"12"


def test_missing_or_changed_binary_never_falls_back(tmp_path, monkeypatch):
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **k: pytest.fail("unexpected subprocess"))
    expected = {"runtime": {"executable": {"path": str(tmp_path / "missing"), "sha256": "a" * 64}}}
    with pytest.raises(FileNotFoundError):
        probe._identity(expected)
    path = tmp_path / "not-native"
    path.write_bytes(b"not executable instructions")
    path.chmod(0o700)
    expected["runtime"]["executable"]["path"] = str(path)
    with pytest.raises(ValueError, match="SHA256"):
        probe._identity(expected)


def test_version_refuses_expired_deadline_before_popen(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "_identity", lambda expected: {})
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **k: pytest.fail("expired probe dispatched"))
    with pytest.raises(TimeoutError):
        probe._version({}, 0, tmp_path)


@contextmanager
def mock_provider(**kwargs):
    yield SimpleNamespace(failure=None), "http://127.0.0.1:18455"


def test_legacy_producer_roundtrip_only_mocked_process_boundary(legacy_fixture, tmp_path, monkeypatch):
    from data_sheets_schema import native_execution_permissions as p
    fixture = legacy_fixture
    expected = fixture["expected"]
    monkeypatch.setattr(probe, "_identity", lambda expected: {})
    monkeypatch.setattr(probe, "_version", lambda expected, deadline, directory:
                        (expected["runtime"]["executable"]["version"] + "\n").encode())
    monkeypatch.setattr(probe, "local_provider", mock_provider)
    def synthetic_run(*args):
        manifest = fixture["manifest"]["members"]
        return {"transcript.jsonl": manifest["transcript.jsonl"]["text"].encode(),
                "control.jsonl": manifest["control.jsonl"]["text"].encode(), "stderr.txt": b"",
                "exit_code": 0, "shutdown": {"control_initialized": True,
                    "control_shutdown_complete": True, "unfinished_control_workers": 0, "child_reaped": True}}
    monkeypatch.setattr(probe, "_run_native", synthetic_run)
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **k: pytest.fail("no actual binary allowed"))
    output = probe.produce_saved_probe(expected, tmp_path / "legacy", deadline_seconds=30)
    reading = p.verify_saved_probe(output.read_bytes(), expected=expected)
    assert reading["passed"] and len(reading["cases"]) == 7
    sidecar = guard.strict_json((output.parent / "producer-evidence.json").read_bytes())
    assert sidecar["manifest_sha256"] == guard.sha(output.read_bytes())
    with pytest.raises(FileExistsError):
        probe.produce_saved_probe(expected, output.parent, deadline_seconds=30)


def test_shared_producer_actual_capture_paths_with_mocked_native_events(shared_fixture, tmp_path, monkeypatch):
    from data_sheets_schema import native_shared_permissions as p
    expected = deepcopy(shared_fixture["expected"])
    # These are test-only invented authority records, not permission approval.
    for name in ("native_permission_probe", "native_probe_provider", "native_subscription_guard"):
        path = Path(probe.__file__).with_name(name + ".py")
        raw = path.read_bytes()
        expected["production_sources"].append({"module": "data_sheets_schema." + name,
            "path": str(path.resolve()), "sha256": guard.sha(raw), "bytes": len(raw)})
    selection_path = Path(expected["selection"]["path"])
    selection_path.write_bytes(guard.canonical(shared_fixture["selection"]))
    directory = tmp_path / "shared"
    manifest = fabricated_manifest(expected, shared_fixture["selection"], directory, shared_fixture["source_raw"])
    monkeypatch.setattr(probe, "_identity", lambda expected: {})
    monkeypatch.setattr(probe, "_version", lambda expected, deadline, directory:
                        (expected["runtime"]["executable"]["version"] + "\n").encode())
    monkeypatch.setattr(probe, "local_provider", mock_provider)
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **k: pytest.fail("no actual binary allowed"))
    def synthetic_run(expected, launch, policy, observer, classifier, controls, server, deadline):
        prefix = "traces/" + observer.trace + "/"
        members = manifest["members"]
        events = [json.loads(row) for row in members[prefix + "transcript.jsonl"]["text"].splitlines()]
        for event in events:
            try:
                observer(event)
            except controls["run_native_canary"].BudgetStop:
                assert observer.expected_stop
                break
            if event.get("type") == "control_request":
                data = event["request"]["input"]
                if data["tool_name"] == "Bash":
                    assert classifier(data["tool_input"]["command"], None, None, policy)
            if event.get("type") == "user":
                # Test-only simulation of the observed native Write effect.
                for block in event["message"]["content"]:
                    case = next(case for case in observer.cases if case["id"] == block["tool_use_id"])
                    if case["tool"] == "Write" and case["mode"] == "allowed":
                        Path(case["input"]["file_path"]).write_text(case["input"]["content"])
        return {"transcript.jsonl": members[prefix + "transcript.jsonl"]["text"].encode(),
            "control.jsonl": members[prefix + "control.jsonl"]["text"].encode(), "stderr.txt": b"",
            "exit_code": 0 if observer.trace == "settled" else -15,
            "shutdown": {"control_initialized": True, "control_shutdown_complete": True,
                         "unfinished_control_workers": 0, "child_reaped": True}}
    monkeypatch.setattr(probe, "_run_native", synthetic_run)
    output = probe.produce_saved_probe(expected, directory, deadline_seconds=60)
    reading = p.verify_saved_probe(output.read_bytes(), expected=expected)
    assert reading["passed"] and len(reading["cases"]) == 25 and len(reading["traces"]) == 7
    assert (directory / "transport-provider.py").read_bytes() == Path(provider.__file__).read_bytes()
    assert all((directory / trace / "evidence_root" / "parent-stop.json").is_file()
               for trace in p.TRACES if trace != "settled")


class FakePipe(io.BytesIO):
    def fileno(self):
        return 123


@pytest.mark.parametrize("mode", ["complete", "timeout", "control_start_error", "overflow"])
def test_native_boundary_reaps_closes_and_retains_failed_evidence(tmp_path, monkeypatch, mode):
    class BudgetStop(Exception):
        pass
    class Process:
        pid, returncode = 999999999, None
        stdin, stdout, stderr = FakePipe(), FakePipe(), FakePipe()
        def poll(self):
            return self.returncode
        def wait(self, timeout):
            if self.returncode is None:
                self.returncode = -15
            return self.returncode
    process = Process()
    class Control:
        initialized = True
        stdout_closed = False
        control_shutdown_complete = False
        unfinished_control_workers = 0
        def __init__(self, *args, **kwargs):
            pass
        def start(self, child, transcript, journal, instruction):
            transcript.write(b'{"type":"synthetic-start"}\n')
            journal.write('{"kind":"synthetic-start"}\n')
            if mode == "control_start_error":
                raise ValueError("injected start failure")
        def service(self):
            if mode == "timeout":
                raise TimeoutError("injected deadline")
            self.stdout_closed, process.returncode = True, 0
        def finish(self):
            pass
        def close(self):
            self.control_shutdown_complete = True
    signals = []
    monkeypatch.setattr(probe, "_identity", lambda expected: {})
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(probe.os, "set_blocking", lambda *a: None)
    monkeypatch.setattr(probe.os, "read", lambda *a: b"x" * (probe.MAX_STREAM + 1) if mode == "overflow" else b"")
    monkeypatch.setattr(probe.os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    root = tmp_path / "trace"
    root.mkdir()
    launch = {"config_root": str(root / "config"), "argv": ["never-run"], "cwd": str(root), "environment": {}}
    controls = {"native_control": SimpleNamespace(NativeControl=Control),
                "run_native_canary": SimpleNamespace(BudgetStop=BudgetStop)}
    call = lambda: probe._run_native({}, launch, {}, lambda e: None, None, controls,
                                     SimpleNamespace(failure=None), float("inf"))
    if mode == "complete":
        result = call()
        assert result["shutdown"]["child_reaped"]
    else:
        with pytest.raises((ValueError, TimeoutError)):
            call()
    assert process.poll() is not None and len(signals) == 2
    assert all(stream.closed for stream in (process.stdin, process.stdout, process.stderr))
    assert b"synthetic-start" in (root / "transcript.jsonl").read_bytes()
    assert (root / "control.jsonl").is_file() and (root / "stderr.txt").is_file()


def test_deadline_and_protected_paths_refused_before_process(legacy_fixture, monkeypatch, tmp_path):
    monkeypatch.setattr(probe, "_identity", lambda expected: {})
    monkeypatch.setattr(probe, "_version", lambda *a: pytest.fail("version process before admission"))
    expected = legacy_fixture["expected"]
    for seconds in (True, 0, 601):
        with pytest.raises(ValueError, match="deadline"):
            probe.produce_saved_probe(expected, tmp_path / "unused", deadline_seconds=seconds)
    repo = Path(expected["policy"]["readonly_lookups"]["repository"])
    with pytest.raises(ValueError, match="protected"):
        probe.produce_saved_probe(expected, repo / "forbidden-probe", deadline_seconds=30)
    assert not (repo / "forbidden-probe").exists()
