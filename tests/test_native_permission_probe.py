"""Probe software tests use invented records/mocks; no native binary or API."""
from contextlib import contextmanager
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_permission_probe as probe
from data_sheets_schema import native_probe_provider as provider
from data_sheets_schema import native_subscription_guard as guard
from tests.test_native_shared_permissions import fabricated_manifest
from tests.test_native_generation_frontdoor import saved_case

_REAL_POPEN = probe.subprocess.Popen


def test_permission_stop_unwinds_and_restores_handlers():
    before = {number: probe.signal.getsignal(number)
              for number in (probe.signal.SIGINT, probe.signal.SIGTERM)}
    cleaned = []
    with pytest.raises(InterruptedError, match="permission probe stopped"):
        with probe._probe_signals():
            try:
                probe.signal.raise_signal(probe.signal.SIGTERM)
            finally:
                probe.signal.raise_signal(probe.signal.SIGTERM)
                probe.signal.raise_signal(probe.signal.SIGINT)
                cleaned.append(True)
    assert cleaned == [True]
    assert {number: probe.signal.getsignal(number) for number in before} == before


def retained_binary(tmp_path):
    """Invented Mach-O-format bytes; tests never execute this file."""
    target = tmp_path / "claude-retained"
    target.write_bytes(b"\xcf\xfa\xed\xfe" + b"\0" * 60)
    target.chmod(0o700)
    return target, {"path": str(target), "sha256": guard.sha(target.read_bytes()),
                    "version": "2.1.269 (Claude Code)"}


def test_retained_binary_static_default_never_launches(tmp_path, monkeypatch):
    target, pins = retained_binary(tmp_path)
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **k: pytest.fail("no execution"))
    result = probe.verify_retained_binary(pins)
    assert result["sha256"] == guard.sha(target.read_bytes())
    assert result["resolved_path"] == str(target)
    assert result["macho_magic"]
    assert result["observed_version"] is None
    assert not result["version_verified"] and not result["codesign_verified"]


@pytest.mark.parametrize("fault", ["missing", "directory", "not_executable", "digest",
                                 "script", "short_macho", "version", "relative"])
def test_retained_binary_refuses_bad_pins_or_file_before_any_execution(tmp_path, fault):
    target, pins = retained_binary(tmp_path)
    if fault == "missing":
        target.unlink()
    elif fault == "directory":
        target.unlink()
        target.mkdir()
    elif fault == "not_executable":
        target.chmod(0o600)
    elif fault == "digest":
        pins["sha256"] = "a" * 64
    elif fault in ("script", "short_macho"):
        target.write_bytes(b"#!/bin/sh\nexit 0\n" if fault == "script" else b"\xcf\xfa\xed\xfe")
        pins["sha256"] = guard.sha(target.read_bytes())
    elif fault == "version":
        pins["version"] = "v1\nv2"
    else:
        pins["path"] = "claude"
    with pytest.raises((ValueError, FileNotFoundError)):
        probe.verify_retained_binary(
            pins, check_version=True, runner=lambda *a, **k: pytest.fail("invalid dispatched"))


def test_retained_binary_symlink_requires_explicit_resolution_and_rechecks_pin(tmp_path):
    target, pins = retained_binary(tmp_path)
    link = tmp_path / "latest"
    link.symlink_to(target)
    pins["path"] = str(link)
    with pytest.raises(ValueError, match="symlink"):
        probe.verify_retained_binary(pins)
    assert probe.verify_retained_binary(pins, allow_resolved_symlink=True)["resolved_path"] == str(target)
    target.write_bytes(b"updated")
    with pytest.raises(ValueError, match="SHA256"):
        probe.verify_retained_binary(pins, allow_resolved_symlink=True)


def test_retained_binary_other_platform_requires_explicit_format_opt_out(tmp_path):
    target, pins = retained_binary(tmp_path)
    target.write_bytes(b"\x7fELF" + b"\0" * 60)
    pins["sha256"] = guard.sha(target.read_bytes())
    with pytest.raises(ValueError, match="Mach-O"):
        probe.verify_retained_binary(pins)
    result = probe.verify_retained_binary(pins, require_macho=False)
    assert not result["macho_magic"] and not result["version_verified"]


def test_retained_binary_optional_checks_use_exact_pins_and_isolated_environment(tmp_path, monkeypatch):
    target, pins = retained_binary(tmp_path)
    calls = []
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "must-not-pass-to-runner")

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stderr=b"",
            stdout=(pins["version"] + "\n").encode() if "--version" in argv else b"")

    result = probe.verify_retained_binary(pins, check_version=True, check_codesign=True, runner=run)
    assert result["observed_version"] == pins["version"]
    assert result["version_verified"] and result["codesign_verified"]
    assert [row[0] for row in calls] == [
        [str(target), "--version"],
        ["/usr/bin/codesign", "--verify", "--strict", str(target)]]
    for _, kwargs in calls:
        assert kwargs["timeout"] == 10 and kwargs["stdin"] == probe.subprocess.DEVNULL
        assert kwargs["env"]["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:1"
        assert "ANTHROPIC_AUTH_TOKEN" not in kwargs["env"]
        assert not Path(kwargs["cwd"]).exists()


@pytest.mark.parametrize("fault", ["wrong_version", "stderr", "exit", "overflow",
                                 "timeout", "changed_bytes", "changed_symlink"])
def test_retained_binary_optional_checks_fail_closed(tmp_path, fault):
    target, pins = retained_binary(tmp_path)
    link = tmp_path / "latest"
    link.symlink_to(target)
    pins["path"] = str(link)

    def run(*args, **kwargs):
        if fault == "timeout":
            raise probe.subprocess.TimeoutExpired(args[0], kwargs["timeout"])
        if fault == "changed_bytes":
            target.write_bytes(b"mutated")
        if fault == "changed_symlink":
            other = tmp_path / "other"
            other.write_bytes(target.read_bytes())
            other.chmod(0o700)
            link.unlink()
            link.symlink_to(other)
        return SimpleNamespace(
            returncode=1 if fault == "exit" else 0,
            stderr=b"warning" if fault == "stderr" else b"",
            stdout=(b"wrong\n" if fault == "wrong_version" else
                    b"x" * 4097 if fault == "overflow" else (pins["version"] + "\n").encode()))

    with pytest.raises((ValueError, probe.subprocess.TimeoutExpired)):
        probe.verify_retained_binary(pins, allow_resolved_symlink=True, check_version=True, runner=run)


@pytest.mark.parametrize("options", [
    {"timeout_seconds": float("nan")}, {"timeout_seconds": 61},
    {"timeout_seconds": True}, {"check_version": 1},
])
def test_retained_binary_execution_is_explicit_and_bounded(tmp_path, options):
    _, pins = retained_binary(tmp_path)
    with pytest.raises(ValueError):
        probe.verify_retained_binary(pins, **options)


def test_retained_binary_explicit_version_flag_uses_bounded_default(tmp_path, monkeypatch):
    _, pins = retained_binary(tmp_path)
    calls = []

    def bounded(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout=(pins["version"] + "\n").encode(), stderr=b"")

    monkeypatch.setattr(probe, "_bounded_binary_check", bounded)
    assert probe.verify_retained_binary(pins, check_version=True)["version_verified"]
    assert calls == [[pins["path"], "--version"]]


@pytest.mark.parametrize("case", ["success", "stdout_overflow", "stderr_overflow", "timeout"])
def test_binary_runner_bounded_software_peer_cleanup(tmp_path, monkeypatch, case):
    """Ordinary Python peers exercise pipe cleanup; no retained native binary."""
    processes = []
    actual = probe.subprocess.Popen

    def spawn(*args, **kwargs):
        child = actual(*args, **kwargs)
        processes.append(child)
        return child

    monkeypatch.setattr(probe.subprocess, "Popen", spawn)
    snippets = {
        "success": "import sys; print('version'); print('diagnostic', file=sys.stderr)",
        # Keep the leader alive until cleanup. An immediately exiting peer
        # races sandbox group lookup and can produce an ambiguous EPERM
        # during group cleanup; that uncertainty correctly refuses.
        # The separate inherited-pipe test retains the exited-leader case.
        "stdout_overflow": "import sys,time; sys.stdout.write('x'*8192); sys.stdout.flush(); time.sleep(30)",
        "stderr_overflow": "import sys,time; sys.stderr.write('x'*8192); sys.stderr.flush(); time.sleep(30)",
        "timeout": "import time; time.sleep(30)",
    }
    started = time.monotonic()
    kwargs = dict(stdin=probe.subprocess.DEVNULL, capture_output=True, check=False,
                  timeout=0.5, env={"PATH": "/usr/bin:/bin"}, cwd=tmp_path)
    if case == "success":
        result = probe._bounded_binary_check([sys.executable, "-c", snippets[case]], **kwargs)
        assert (result.returncode, result.stdout, result.stderr) == (0, b"version\n", b"diagnostic\n")
    else:
        exception = ValueError if case.endswith("overflow") else probe.subprocess.TimeoutExpired
        with pytest.raises(exception):
            probe._bounded_binary_check([sys.executable, "-c", snippets[case]], **kwargs)
    assert time.monotonic() - started < 5
    assert len(processes) == 1 and processes[0].poll() is not None
    assert processes[0].stdout.closed and processes[0].stderr.closed


@pytest.mark.parametrize("denied", [False, True])
def test_binary_runner_exited_leader_with_open_pipes_still_attempts_group_cleanup(
        tmp_path, monkeypatch, denied):
    """Mock an inherited pipe holder: host policy may deny orphan-group signals."""
    signals, writers = [], []

    class ExitedLeader:
        pid, returncode = 999999999, 0

        def __init__(self):
            for name in ("stdout", "stderr"):
                read_fd, write_fd = os.pipe()
                setattr(self, name, os.fdopen(read_fd, "rb"))
                writers.append(write_fd)

        def poll(self):
            return 0

        def wait(self, timeout):
            return 0

    process = ExitedLeader()

    def killpg(pid, sig):
        signals.append((pid, sig))
        if denied:
            raise PermissionError("host denied cleanup; cannot attest success")

    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(probe.os, "killpg", killpg)
    try:
        with pytest.raises(PermissionError if denied else probe.subprocess.TimeoutExpired):
            probe._bounded_binary_check(
                ["invented-native", "--version"], stdin=probe.subprocess.DEVNULL,
                capture_output=True, timeout=0.05, check=False, env={}, cwd=tmp_path)
        assert signals == [(process.pid, probe.signal.SIGTERM)] + (
            [] if denied else [(process.pid, probe.signal.SIGKILL)])
        assert process.stdout.closed and process.stderr.closed
    finally:
        for descriptor in writers:
            os.close(descriptor)


@pytest.mark.parametrize(('already_exited', 'wait_times_out'), [
    (True, False), (False, False), (False, True),
])
def test_denied_group_signal_still_attempts_reap_and_preserves_refusal(
        monkeypatch, already_exited, wait_times_out):
    """A reaped leader alone cannot attest cleanup of its process group."""
    refusal = PermissionError('group cleanup denied')
    calls = []

    class Process:
        pid = 999999999
        reaped = False
        returncode = 0 if already_exited else None

        def wait(self, timeout):
            calls.append(('wait', timeout))
            if wait_times_out:
                raise probe.subprocess.TimeoutExpired('invented child', timeout)
            self.reaped = True
            self.returncode = 0
            return 0

        def poll(self):
            return self.returncode

    process = Process()

    def denied(pid, sig):
        calls.append(('signal', pid, sig))
        raise refusal

    monkeypatch.setattr(probe.os, 'killpg', denied)
    with pytest.raises(PermissionError) as caught:
        probe._terminate(process)
    assert caught.value is refusal
    assert calls == [('signal', process.pid, probe.signal.SIGTERM), ('wait', 1)]
    assert process.reaped is (not wait_times_out)


def test_retained_binary_codesign_failure_is_not_verified(tmp_path):
    _, pins = retained_binary(tmp_path)
    with pytest.raises(ValueError, match="codesign check failed"):
        probe.verify_retained_binary(pins, check_codesign=True, runner=lambda *a, **k:
            SimpleNamespace(returncode=1, stdout=b"", stderr=b"invalid signature"))


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


@pytest.mark.parametrize('kind', [None, 'legacy', 'd4d_native_permission_expected', 1])
def test_unknown_or_legacy_producer_never_falls_back(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(probe, '_loaded_probe_inputs',
                        lambda *a: pytest.fail('unknown protocol reached authority loading'))
    monkeypatch.setattr(probe.subprocess, 'Popen',
                        lambda *a, **k: pytest.fail('unknown protocol dispatched'))
    monkeypatch.setattr(probe, 'local_provider',
                        lambda *a, **k: pytest.fail('unknown protocol opened listener'))
    out = tmp_path / 'unused'
    with pytest.raises(ValueError):
        probe.produce_saved_probe({'kind': kind}, out, deadline_seconds=30)
    assert not out.exists()


@pytest.mark.parametrize('fail_later', [False, True])
def test_shared_producer_actual_capture_paths_with_mocked_native_events(saved_case, tmp_path, monkeypatch, fail_later):
    from data_sheets_schema import native_shared_permissions as p
    from data_sheets_schema import native_shared_permission_orchestration as verify
    expected = deepcopy(saved_case["expected"])
    # These are test-only invented authority records, not permission approval.
    directory = tmp_path / "shared"
    source_raw = saved_case['manifest']['members']['source.before']['text'].encode()
    manifest = fabricated_manifest(expected, saved_case["selection"], directory, source_raw)
    monkeypatch.setattr(probe, "_identity", lambda expected: {})
    monkeypatch.setattr(probe, "_version", lambda expected, deadline, directory:
                        (expected["runtime"]["executable"]["version"] + "\n").encode())
    monkeypatch.setattr(probe, "local_provider", mock_provider)
    transport_source = Path(provider.__file__).read_bytes()
    actual_read_bytes = Path.read_bytes
    def refuse_late_transport_read(path):
        if path == Path(provider.__file__) and (directory / 'transport-provider.py').exists():
            pytest.fail('transport source was reopened after its checked capture')
        return actual_read_bytes(path)
    monkeypatch.setattr(Path, 'read_bytes', refuse_late_transport_read)
    def git_only(argv, *args, **kwargs):
        if (not isinstance(argv, (list, tuple)) or Path(argv[0]).name != 'git'
                or kwargs.get('shell')):
            pytest.fail('no actual binary allowed')
        return _REAL_POPEN(argv, *args, **kwargs)
    monkeypatch.setattr(probe.subprocess, "Popen", git_only)
    def synthetic_run(expected, launch, policy, observer, classifier, transport, server, deadline):
        prefix = "traces/" + observer.trace + "/"
        members = manifest["members"]
        events = [json.loads(row) for row in members[prefix + "transcript.jsonl"]["text"].splitlines()]
        for event in events:
            try:
                observer(event)
                if fail_later and observer.trace != 'settled' and observer.session:
                    raise TimeoutError('later trace failed')
            except transport.budget_stop:
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
    if fail_later:
        with pytest.raises(TimeoutError, match='later trace failed'):
            probe.produce_saved_probe(expected, directory, deadline_seconds=60)
        assert (directory / 'captured/source.before').read_bytes() == source_raw
        assert (directory / 'captured/traces/settled/outcome.json').is_file()
        assert (directory / p.TRACES[1] / 'evidence_root/neutral.before.json').is_file()
        assert (directory / p.TRACES[1] / 'launch.before.json').is_file()
        assert guard.strict_json((directory / 'failure.json').read_bytes())['error_type'] == 'TimeoutError'
        assert not (directory / 'permission-probe.json').exists()
        return
    output = probe.produce_saved_probe(expected, directory, deadline_seconds=60)
    reading = verify.verify_saved_probe(output.read_bytes(), expected=expected)
    assert reading["passed"]
    assert len(reading["cases"]) == len(json.loads(manifest['members']['cases.json']['text']))
    assert len(reading["traces"]) == len(p.TRACES)
    assert (directory / "transport-provider.py").read_bytes() == transport_source
    assert all((directory / trace / "evidence_root" / "parent-stop.json").is_file()
               for trace in p.TRACES if trace != "settled")
    sidecar = guard.strict_json((directory / 'producer-evidence.json').read_bytes())
    assert sidecar['manifest_sha256'] == guard.sha(output.read_bytes())
    assert sidecar['transport_source_sha256'] == guard.sha(transport_source)
    monkeypatch.setattr(probe, '_version', lambda *a: pytest.fail('spent path started another probe'))
    with pytest.raises(FileExistsError):
        probe.produce_saved_probe(expected, directory, deadline_seconds=60)


class FakePipe(io.BytesIO):
    def fileno(self):
        return 123


@pytest.mark.parametrize('limit', [3, 100])
def test_shutdown_tail_retains_bytes_and_explicitly_marks_truncation(limit):
    read_fd, write_fd = os.pipe()
    os.write(write_fd, b'last diagnostic')
    os.close(write_fd)
    with os.fdopen(read_fd, 'rb') as stream:
        raw, status = probe._pipe_tail(stream, limit, time.monotonic() + 1)
    assert raw == b'last diagnostic'[:limit]
    assert status == ('byte_limit' if limit == 3 else 'eof')


def test_shutdown_tail_times_out_on_inherited_open_pipe():
    read_fd, write_fd = os.pipe()
    try:
        with os.fdopen(read_fd, 'rb') as stream:
            assert probe._pipe_tail(stream, 100, time.monotonic() + .01) == (b'', 'time_limit')
    finally:
        os.close(write_fd)


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
    transport = SimpleNamespace(control=Control, budget_stop=BudgetStop, check=lambda: None)
    call = lambda: probe._run_native({}, launch, {}, lambda e: None, None, transport,
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


def test_deadline_refused_before_loading_or_process(monkeypatch, tmp_path):
    monkeypatch.setattr(probe, "_identity", lambda expected: {})
    monkeypatch.setattr(probe, "_version", lambda *a: pytest.fail("version process before admission"))
    expected = {}
    for seconds in (True, 0, 601):
        with pytest.raises(ValueError, match="deadline"):
            probe.produce_saved_probe(expected, tmp_path / "unused", deadline_seconds=seconds)


@pytest.mark.parametrize('fault', ['effort', 'max', 'key', 'provider', 'login', 'auth_method'])
def test_owner_runtime_choice_refuses_conflicting_declarations(saved_case, monkeypatch, tmp_path, fault):
    expected = deepcopy(saved_case['expected'])
    runtime = expected['runtime']
    if fault == 'effort':
        runtime['effort'] = 'medium'
    elif fault == 'max':
        runtime['auth']['subscriptionType'] = 'pro'
    elif fault == 'key':
        runtime['environment']['ANTHROPIC_API_KEY'] = 'synthetic-forbidden-key'
    elif fault == 'provider':
        runtime['auth']['apiProvider'] = 'thirdParty'
    elif fault == 'login':
        runtime['auth']['loggedIn'] = False
    else:
        runtime['auth']['authMethod'] = 'api_key'
    monkeypatch.setattr(probe, '_loaded_probe_inputs',
                        lambda *a: pytest.fail('wrong owner selection reached source loading'))
    monkeypatch.setattr(probe, 'local_provider',
                        lambda *a, **k: pytest.fail('wrong owner selection opened listener'))
    out = tmp_path / 'refused'
    with pytest.raises(ValueError):
        probe.produce_saved_probe(expected, out, deadline_seconds=30)
    assert not out.exists()


def test_capture_requires_main_thread_before_loading(saved_case, monkeypatch):
    from data_sheets_schema import native_execution_authority_v2 as authority
    monkeypatch.setattr(authority, 'dependency_identity',
                        lambda: pytest.fail('worker entered authority loader'))
    errors = []
    def worker():
        try:
            with probe._loaded_probe_inputs(saved_case['expected']):
                pytest.fail('worker obtained permission capabilities')
        except ValueError as exc:
            errors.append(str(exc))
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert errors == ['permission probe capture requires the main thread']


@pytest.mark.parametrize('mode', ['trickle', 'complete', 'truncated', 'already_expired'])
def test_provider_body_uses_absolute_deadline_without_socket(monkeypatch, mode):
    ticks = [0.0]
    monkeypatch.setattr(provider.time, 'monotonic', lambda: ticks[0])
    calls, timeouts = [], []
    class Stream:
        def read1(self, size):
            calls.append(size)
            ticks[0] += 0.4
            return b'' if mode == 'truncated' else b'x'
        def read(self, size):
            pytest.fail('unbounded buffered read was used')
    handler = SimpleNamespace(server=SimpleNamespace(deadline=0 if mode == 'already_expired' else 1),
        connection=SimpleNamespace(settimeout=timeouts.append), rfile=Stream())
    if mode == 'complete':
        assert provider._read_request(handler, 2) == b'xx'
    elif mode == 'truncated':
        with pytest.raises(ValueError, match='truncated'):
            provider._read_request(handler, 10)
    else:
        with pytest.raises(TimeoutError, match='deadline'):
            provider._read_request(handler, 10)
    assert len(calls) <= 3
    assert all(0 < value <= 1 for value in timeouts)
    if mode == 'already_expired':
        assert not calls and not timeouts


@pytest.mark.parametrize('mode', ['start_failure', 'normal', 'body_failure', 'hung_worker'])
def test_provider_listener_cleanup_is_bounded_even_on_start_failure(monkeypatch, mode):
    """Entire server/thread boundary is fake; no socket is created or listened."""
    events = []
    class Server:
        server_port = 12345
        def __init__(self, address, handler):
            events.append(('created', address))
        def close_active_request(self):
            events.append('active_closed')
        def server_close(self):
            events.append('listener_closed')
        def shutdown(self):
            pytest.fail('unbounded HTTPServer.shutdown is forbidden')
    class Thread:
        ident = None
        def __init__(self, **kwargs):
            assert kwargs['daemon'] is True
        def start(self):
            if mode == 'start_failure':
                raise RuntimeError('injected start failure')
            self.ident = 1
        def join(self, timeout):
            assert timeout == 2
            events.append('joined')
        def is_alive(self):
            return mode == 'hung_worker'
    monkeypatch.setattr(provider, '_Server', Server)
    monkeypatch.setattr(provider.threading, 'Thread', Thread)
    def run():
        with provider.local_provider(cases=lambda: [], model='synthetic',
                                     deadline=time.monotonic() + 10) as (_, url):
            assert url == 'http://127.0.0.1:12345'
            if mode == 'body_failure':
                raise ValueError('injected body failure')
    if mode == 'normal':
        run()
    else:
        with pytest.raises(ValueError if mode == 'body_failure' else RuntimeError):
            run()
    assert events.count('active_closed') == events.count('listener_closed') == 1
    assert ('joined' in events) is (mode != 'start_failure')


def test_provider_stopping_closes_active_connection_without_socket():
    calls = []
    connection = SimpleNamespace(shutdown=lambda how: calls.append(('shutdown', how)),
                                 close=lambda: calls.append('closed'))
    server = object.__new__(provider._Server)
    server.connection_lock = threading.Lock()
    server.active_connection = connection
    server.close_active_request()
    assert calls == [('shutdown', provider.socket.SHUT_RDWR), 'closed']
    assert server.active_connection is None
    server.close_active_request()
    assert len(calls) == 2


@pytest.mark.parametrize('fail_later', [False, True])
def test_captured_inputs_survive_later_failure_without_authority_fixture(tmp_path, monkeypatch, fail_later):
    """Mock process/consumer boundaries; exercise real incremental disk writes."""
    source = tmp_path / 'source'
    source.write_bytes(b'original source')
    directory = tmp_path / 'evidence'
    sources = []
    for name in ('native_permission_probe', 'native_probe_provider', 'native_subscription_guard'):
        path = Path(probe.__file__).with_name(name + '.py')
        raw = path.read_bytes()
        sources.append({'module': 'data_sheets_schema.' + name, 'path': str(path.resolve()),
                        'bytes': len(raw), 'sha256': guard.sha(raw)})
    expected = {'production_sources': sources, 'source': {'path': str(source), 'sha256': guard.sha(source.read_bytes())},
        'runtime': {'executable': {'path': str(tmp_path / 'binary')}},
        'selection': {'path': str(tmp_path / 'selection')}, 'permission_environment': {},
        'policy': {'readonly_lookups': {'repository': str(tmp_path / 'repository'),
                                     'inputs': [], 'output_directories': []}}}
    selected = {'stage_root': str(tmp_path / 'stage')}
    consumer = SimpleNamespace(MAX_MEMBER=probe.MAX_STREAM, TRACES=('settled', 'later'),
        KIND='invented', VERSION=1, ORIGIN='invented', recipe_sources=lambda: {'recipe/provider.py': '# fixed'},
        verify_saved_probe=lambda *a, **k: {'checked': True, 'passed': True})
    transport_raw = Path(provider.__file__).read_bytes()
    real_read = Path.read_bytes
    def read(path):
        if path == Path(provider.__file__):
            pytest.fail('checked transport source reopened with Path.read_bytes')
        return real_read(path)
    monkeypatch.setattr(Path, 'read_bytes', read)
    monkeypatch.setattr(probe, '_identity', lambda *a: None)
    def version(*args):
        assert (directory / 'captured/source.before').read_bytes() == b'original source'
        assert (directory / 'captured/selection.json').read_bytes() == b'{}'
        assert (directory / 'transport-provider.py').read_bytes() == transport_raw
        return b'version\n'
    monkeypatch.setattr(probe, '_version', version)
    def trace(*args):
        if args[-1] == 'later':
            assert (directory / 'captured/traces/settled/outcome.json').read_bytes() == b'{}'
            if fail_later:
                raise TimeoutError('injected later failure')
        return {'cases.json': b'[]', 'outcome.json': b'{}'}
    monkeypatch.setattr(probe, '_trace', trace)
    call = lambda: probe._produce_captured(expected, directory, time.monotonic() + 60,
        consumer, {}, {}, object(), selected, b'{}')
    if fail_later:
        with pytest.raises(TimeoutError, match='injected later failure'):
            call()
        assert not (directory / 'permission-probe.json').exists()
        assert guard.strict_json((directory / 'failure.json').read_bytes())['error_type'] == 'TimeoutError'
    else:
        assert call().is_file()
        assert guard.strict_json((directory / 'producer-evidence.json').read_bytes())['transport_source_sha256'] == guard.sha(transport_raw)
