"""Offline tests of the paid-batch launch and retention boundaries."""
import json
import hashlib
import os
from pathlib import Path
import signal
import shutil
import subprocess
from types import SimpleNamespace
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reference_rescore_cborg_batch as batch


def fake_command(tmp_path, *, failing=False):
    worker = tmp_path / "fake_worker.py"
    worker.write_text(
        "import pathlib,sys,time\n"
        "job=sys.argv[1]\n"
        "time.sleep(0.08)\n"
        "print(f'Starting {job} (offline)',flush=True)\n"
        "pathlib.Path('ready_'+job).touch()\n"
        "while len(list(pathlib.Path('.').glob('ready_*')))<4:time.sleep(0.02)\n"
        + ("if job!='a':\n while '\"exit_code\": 1' not in pathlib.Path('run/events.jsonl').read_text():time.sleep(0.02)\n" if failing else "")
        + ("sys.exit(1 if job=='a' else 0)\n" if failing else "")
    )
    return lambda job: [sys.executable, str(worker), job]


def test_scheduler_waits_for_startup_and_limits_concurrency(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    result = batch.schedule(list("abcdef"), fake_command(tmp_path), tmp_path / "run", workers=4)
    assert result["status"] == "passed"
    assert len(result["completed"]) == 6
    events = [json.loads(line) for line in (tmp_path / "run/events.jsonl").read_text().splitlines()]
    launches = [e for e in events if e["event"] == "launched"]
    starts = {e["job"]: e for e in events if e["event"] == "started"}
    for previous, current in zip(launches, launches[1:]):
        assert current["at"] >= starts[previous["job"]]["at"]
    active = peak = 0
    for event in events:
        active += (event["event"] == "launched") - (event["event"] == "finished")
        peak = max(peak, active)
    assert active == 0 and peak == 4


def test_failure_stops_new_launches_and_drains_inflight(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    result = batch.schedule(list("abcdef"), fake_command(tmp_path, failing=True), tmp_path / "run", workers=4)
    assert result["status"] == "stopped"
    assert result["not_launched"] == ["e", "f"]
    assert sorted(result["completed"], key=lambda j: j["job_id"]) == [
        {"job_id": "a", "exit_code": 1}, *[{"job_id": j, "exit_code": 0} for j in "bcd"]]


def test_exit_without_startup_does_not_open_the_queue(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    result = batch.schedule(["a", "b"], lambda job: [sys.executable, "-c", "pass"], tmp_path / "run")
    assert result["status"] == "stopped" and result["not_launched"] == ["b"]


def test_existing_ignored_attempt_is_not_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    monkeypatch.setattr(batch, "PLAN", tmp_path)
    attempt = tmp_path / "attempts/a/.unfinished"
    attempt.mkdir(parents=True)
    (tmp_path / ".gitignore").write_text("attempts/\n")
    with pytest.raises(ValueError, match="already has an attempt"):
        batch.pending_jobs(None, {"jobs": [{"id": "a", "output": "missing.json"}]}, {}, "remaining")


def test_review_must_approve_the_exact_registration(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "PLAN", tmp_path)
    (tmp_path / "review.json").write_text(json.dumps({"verdict": "approved", "registration_sha256": "old"}))
    with pytest.raises(ValueError, match="matching approved review"):
        batch.require_review(None, "review.json", "registration_sha256", "current")


def test_pilot_acceptance_binds_the_output_and_registration(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "PLAN", tmp_path)
    monkeypatch.setattr(batch, "verified_output", lambda *a: {"evaluation_sha256": "current-output"})
    (tmp_path / "batch_canary_acceptance.json").write_text(json.dumps({
        "registration_sha256": "current-registration", "evaluation_sha256": "edited-output"}))
    r = SimpleNamespace(digest=lambda p: "current-registration")
    with pytest.raises(ValueError, match="acceptance differs"):
        batch.require_pilot(r, {"jobs": [{"id": "pilot"}]}, {"pilot_job_id": "pilot"})


@pytest.mark.parametrize("stop_signal", [signal.SIGINT, signal.SIGTERM])
def test_foreground_stop_drains_workers_and_retains_evidence(tmp_path, stop_signal):
    worker = tmp_path / "worker.py"
    worker.write_text(
        "from pathlib import Path\nimport sys,time\n"
        "job=sys.argv[1];p=Path(job);p.mkdir()\n"
        "print(f'Starting {job} (offline)',flush=True)\n"
        "(p/'started').touch()\n"
        "while not Path('release').exists():time.sleep(0.02)\n"
        "(p/'candidate.json').write_text('original candidate')\n"
        "(p/'receipt.json').write_text('completed receipt')\n"
    )
    controller = tmp_path / "controller.py"
    controller.write_text(
        f"import sys\nsys.path.insert(0,{str(Path(batch.__file__).parent)!r})\n"
        "from pathlib import Path\nimport reference_rescore_cborg_batch as b\n"
        "b.ROOT=Path.cwd()\n"
        "r=b.schedule(list('abcde'),lambda j:[sys.executable,'worker.py',j],Path('run'))\n"
        "raise SystemExit(0 if r['status']=='passed' else 1)\n"
    )
    process = subprocess.Popen([sys.executable, str(controller)], cwd=tmp_path,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        deadline = time.monotonic() + 15
        while len(list(tmp_path.glob("*/started"))) < 4:
            assert process.poll() is None
            assert time.monotonic() < deadline
            time.sleep(0.02)
        os.killpg(process.pid, stop_signal)
        (tmp_path / "release").touch()
        output, _ = process.communicate(timeout=15)
        assert process.returncode == 1, output.decode()
        result = json.loads((tmp_path / "run/result.json").read_text())
        assert result["status"] == "stopped" and result["stop_signal"] == stop_signal
        assert result["not_launched"] == ["e"]
        assert len(result["completed"]) == 4
        assert all(row["exit_code"] == 0 for row in result["completed"])
        for job in "abcd":
            assert (tmp_path / job / "candidate.json").read_text() == "original candidate"
            assert (tmp_path / job / "receipt.json").read_text() == "completed receipt"
        assert not (tmp_path / "e").exists()
    finally:
        (tmp_path / "release").touch(exist_ok=True)
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=15)


@pytest.mark.parametrize("stop_signal", [signal.SIGINT, signal.SIGTERM])
def test_stop_during_launch_preparation_leaves_job_queued(tmp_path, monkeypatch, stop_signal):
    monkeypatch.setattr(batch, "ROOT", tmp_path)

    def prepare(job):
        os.kill(os.getpid(), stop_signal)
        return [sys.executable, "-c", "raise AssertionError('must not launch')"]

    def forbidden_spawn(*args, **kwargs):
        raise AssertionError("a worker started after the controller observed a stop")

    monkeypatch.setattr(batch.subprocess, "Popen", forbidden_spawn)
    result = batch.schedule(["a", "b"], prepare, tmp_path / "run")
    assert result["status"] == "stopped" and result["stop_signal"] == stop_signal
    assert result["not_launched"] == ["a", "b"] and result["completed"] == []
    assert not any(json.loads(line)["event"] == "controller_error"
                   for line in (tmp_path / "run/events.jsonl").read_text().splitlines())


def test_worker_unblocks_inherited_launch_signals_before_preflight(monkeypatch):
    def inspect_mask():
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        assert not {signal.SIGINT, signal.SIGTERM}.intersection(mask)
        raise ValueError("offline preflight reached")

    monkeypatch.setattr(batch, "load_registered", inspect_mask)
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
    try:
        with pytest.raises(ValueError, match="offline preflight reached"):
            batch.main(["worker", "--phase", "pilot", "--job", "a"])
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def reviewed_failure(tmp_path, monkeypatch, *, status="incomplete", terminal=True):
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    monkeypatch.setattr(batch, "PLAN", tmp_path)
    prior = tmp_path / "attempts/a/old"
    prior.mkdir(parents=True)
    (prior / "receipt.json").write_text(json.dumps({"job_id": "a", "status": status, "completed_at": "2026-09-12T19:19:00+00:00"}))
    (prior / "prompt.txt").write_text("frozen prompt")
    (prior / "transcript.jsonl").write_text(json.dumps({"type": "result", "total_cost_usd": 1.0}) + "\n" if terminal else "")
    r = SimpleNamespace(digest=lambda p: hashlib.sha256(p.read_bytes()).hexdigest())
    registration = {"reviewed_retries": {"a": {"attempts": {
        str(prior.relative_to(tmp_path)): {str(p.relative_to(tmp_path)): r.digest(p) for p in prior.iterdir()}}}}}
    return r, registration, prior, {"jobs": [{"id": "a", "output": "missing.json"}]}


def test_reviewed_retry_is_invalidated_by_any_new_attempt(tmp_path, monkeypatch):
    r, registration, prior, manifest = reviewed_failure(tmp_path, monkeypatch)
    assert batch.pending_jobs(r, manifest, registration, "remaining") == manifest["jobs"]
    (prior.parent / ".new-unfinished-attempt").mkdir()
    with pytest.raises(ValueError, match="history changed"):
        batch.pending_jobs(r, manifest, registration, "remaining")


def test_reviewed_retry_refuses_changed_failed_evidence(tmp_path, monkeypatch):
    r, registration, prior, manifest = reviewed_failure(tmp_path, monkeypatch)
    (prior / "prompt.txt").write_text("edited prompt")
    with pytest.raises(ValueError, match="bytes changed"):
        batch.pending_jobs(r, manifest, registration, "remaining")


@pytest.mark.parametrize("status,terminal,message", [
    ("passed", True, "completed, excluded"), ("incomplete", False, "terminal result")])
def test_reviewed_retry_requires_exclusion_and_complete_cost_evidence(tmp_path, monkeypatch, status, terminal, message):
    r, registration, prior, manifest = reviewed_failure(tmp_path, monkeypatch, status=status, terminal=terminal)
    with pytest.raises(ValueError, match=message):
        batch.pending_jobs(r, manifest, registration, "remaining")


@pytest.mark.parametrize("keep_empty_parent", [False, True])
def test_registered_retry_rejects_missing_or_empty_history(tmp_path, monkeypatch, keep_empty_parent):
    r, registration, prior, manifest = reviewed_failure(tmp_path, monkeypatch)
    shutil.rmtree(prior if keep_empty_parent else prior.parent)
    with pytest.raises(ValueError, match="history"):
        batch.pending_jobs(r, manifest, registration, "remaining")


@pytest.fixture
def prelaunch_case(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, 'ROOT', tmp_path)
    monkeypatch.setattr(batch, 'PLAN', tmp_path / 'plan')
    plan = tmp_path / 'plan'
    source = plan / 'attempts' / 'a' / 'first'
    source.mkdir(parents=True)
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'scripts/reference_rescore_cborg.py').write_text('reviewed adapter')
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    r = SimpleNamespace(digest=digest, job_prompt=lambda m, j: 'pinned prompt')
    (plan / 'manifest.json').write_text(json.dumps({'jobs': [{'id': 'a'}]}))
    (source / 'prompt.txt').write_text('pinned prompt')
    (source / 'transcript.jsonl').write_bytes(b'')
    (source / 'stderr.txt').write_text('Traceback: reviewed guard\nValueError: Claude Code version differs from the registered transport\n')
    receipt = {'job_id': 'a', 'status': 'incomplete', 'exit_code': 1,
               'manifest_sha256': digest(plan / 'manifest.json'),
               'user_prompt_sha256': digest(source / 'prompt.txt'),
               'started_at': '2026-09-12T20:03:10+00:00',
               'completed_at': '2026-09-12T20:03:11+00:00'}
    (source / 'receipt.json').write_text(json.dumps(receipt))
    rel = str(source.relative_to(tmp_path))
    files = {str(p.relative_to(tmp_path)): digest(p) for p in source.iterdir()}
    registration = {'prelaunch_failures': {rel: {'reason': 'registered_cli_version_guard_before_execve',
                    'adapter_sha256': digest(tmp_path / 'scripts/reference_rescore_cborg.py'), 'files': files}},
                    'reviewed_retries': {'a': {'attempts': {rel: files}}}}
    return r, source, registration


def test_exact_reviewed_prelaunch_failure_allows_one_retry(prelaunch_case):
    r, source, registration = prelaunch_case
    batch.verify_reviewed_retry(r, {'id': 'a'}, registration, source.parent)
    result = batch.verify_prelaunch_failure(r, source, registration)
    assert result['evaluator_launched'] is False and result['model_calls'] == 0
    (source.parent / 'another').mkdir()
    with pytest.raises(ValueError, match='retry history changed'):
        batch.verify_reviewed_retry(r, {'id': 'a'}, registration, source.parent)


@pytest.mark.parametrize('change', ['missing', 'changed', 'extra', 'nonempty_trace', 'passed', 'wrong_error', 'adapter'])
def test_ambiguous_or_changed_prelaunch_evidence_blocks(prelaunch_case, change):
    r, source, registration = prelaunch_case
    if change == 'missing':
        (source / 'stderr.txt').unlink()
    elif change == 'changed':
        (source / 'prompt.txt').write_text('changed')
    elif change == 'extra':
        (source / 'candidate.json').write_text('{}')
    elif change == 'adapter':
        (batch.ROOT / 'scripts/reference_rescore_cborg.py').write_text('unreviewed control flow')
    else:
        if change == 'nonempty_trace':
            path = source / 'transcript.jsonl'
            path.write_text('{"type":"system","subtype":"init"}\n')
        elif change == 'passed':
            path = source / 'receipt.json'
            record = json.loads(path.read_bytes()); record['status'] = 'passed'
            path.write_text(json.dumps(record))
        else:
            path = source / 'stderr.txt'
            path.write_text('Some other failure\n')
        # Even a newly pinned hash cannot turn a model session or another error
        # into this narrow pre-launch classification.
        registration['prelaunch_failures'][str(source.relative_to(batch.ROOT))]['files'][str(path.relative_to(batch.ROOT))] = r.digest(path)
    with pytest.raises(ValueError):
        batch.verify_prelaunch_failure(r, source, registration)


def test_prelaunch_inventory_preserves_other_unresolved_attempts(prelaunch_case):
    r, source, registration = prelaunch_case
    rel = str(source.relative_to(batch.ROOT))
    other = {'source': 'plan/attempts/a/uncertain', 'reason': 'missing terminal cost'}
    original = lambda *args: ({}, [{'source': rel, 'reason': 'no terminal cost'}, other])
    sources, unresolved = batch.inventory_with_prelaunch(r, registration, original, batch.ROOT, batch.PLAN, {'a'})
    assert sources == {} and unresolved == [other]
    with pytest.raises(ValueError, match='original failed inventory'):
        batch.inventory_with_prelaunch(r, registration, lambda *a: ({'a': [source]}, []), batch.ROOT, batch.PLAN, {'a'})


def test_cli_binary_mismatch_stops_before_attempt(tmp_path, monkeypatch):
    binary = tmp_path / 'claude'; binary.write_bytes(b'registered binary')
    r = SimpleNamespace(digest=lambda p: hashlib.sha256(p.read_bytes()).hexdigest())
    registration = {'cli_executable_sha256': r.digest(binary)}
    monkeypatch.setattr(batch.shutil, 'which', lambda _, **kwargs: str(binary))
    batch.verify_cli_executable(r, registration)
    binary.write_bytes(b'auto-updated binary')
    with pytest.raises(ValueError, match='registered CLI executable'):
        batch.verify_cli_executable(r, registration)


def test_interpreter_directory_cannot_shadow_the_pinned_cli(tmp_path, monkeypatch):
    selected = tmp_path / 'pinned'; selected.mkdir()
    interpreter = tmp_path / 'python-bin'; interpreter.mkdir()
    cli = selected / 'claude'; cli.write_bytes(b'registered binary'); cli.chmod(0o755)
    shadow = interpreter / 'claude'; shadow.write_bytes(b'different binary'); shadow.chmod(0o755)
    r = SimpleNamespace(digest=lambda p: hashlib.sha256(p.read_bytes()).hexdigest())
    registration = {'cli_executable_sha256': r.digest(cli)}
    monkeypatch.setenv('PATH', str(selected))
    monkeypatch.setattr(batch.sys, 'executable', str(interpreter / 'python'))
    assert shutil.which('claude') == str(cli)
    with pytest.raises(ValueError, match='registered CLI executable'):
        batch.verify_cli_executable(r, registration)
    shadow.unlink()
    batch.verify_cli_executable(r, registration)
