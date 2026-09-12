"""Offline tests of the paid-batch launch and retention boundaries."""
import json
import hashlib
import os
from pathlib import Path
import signal
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
