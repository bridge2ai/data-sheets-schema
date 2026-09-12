"""Offline tests of the paid-batch launch and retention boundaries."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reference_rescore_cborg_batch as batch


def fake_command(tmp_path, *, failing=False):
    worker = tmp_path / "fake_worker.py"
    worker.write_text(
        "import sys,time\n"
        "job=sys.argv[1]\n"
        "time.sleep(0.08)\n"
        "print(f'Starting {job} (offline)',flush=True)\n"
        + ("time.sleep(0.3 if job=='a' else 0.6)\n" if failing else "time.sleep(0.4)\n")
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
