"""Offline accounting regressions for interrupted evaluator sessions."""
import importlib.util
import json
import shutil
from pathlib import Path
import sys

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("audit_reference_rescore", SCRIPTS / "audit_reference_rescore.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def original_attempt(source):
    source.mkdir(parents=True)
    (source / "prompt.txt").write_text("original registered prompt")
    (source / "transcript.jsonl").write_text('{"type":"result"}\n')
    (source / "candidate.json").write_text('{"score":1}\n')
    (source / "receipt.json").write_text(json.dumps({
        "job_id": source.parent.name, "status": "passed", "exit_code": 0,
        "started_at": "2026-09-12T00:00:00+00:00", "completed_at": "2026-09-12T00:01:00+00:00"}))


def recovery_attempt(root, original, recovered):
    recovered.mkdir()
    record = {"job_id": original.parent.name, "status": "passed", "model_calls_during_recovery": 0,
              "recovered_from": str(original.relative_to(root))}
    for name, key in (("receipt.json", "original_receipt_sha256"),
                      ("transcript.jsonl", "transcript_sha256"),
                      ("prompt.txt", "user_prompt_sha256"),
                      ("candidate.json", "evaluation_sha256")):
        record[key] = audit.r.digest(original / name)
    (recovered / "receipt.json").write_text(json.dumps(record))


@pytest.mark.parametrize("stage", ["directory", "prompt", "transcript"])
def test_interruption_remains_visible_after_successful_retry_and_blocks_completion(tmp_path, monkeypatch, stage):
    plan = tmp_path / "plan"
    original = plan / "attempts/job/interrupted"
    original.mkdir(parents=True)
    if stage in ("prompt", "transcript"):
        (original / "prompt.txt").write_text("original registered prompt")
    if stage == "transcript":
        (original / "transcript.jsonl").write_text('{"type":"assistant"}\n')
    # This is deliberately gitignored: filesystem inventory must still see it.
    (tmp_path / ".gitignore").write_text("plan/attempts/job/interrupted/\n")
    retry = plan / "attempts/job/retry"
    original_attempt(retry)
    (plan / "manifest.json").write_text(json.dumps({"jobs": [{"id": "job"}]}))
    sources, unresolved = audit.inventory_attempts(tmp_path, plan, {"job"})
    assert sources == {"job": [retry]}
    assert len(unresolved) == 1
    assert unresolved[0]["source"] == "plan/attempts/job/interrupted"
    assert "cost unknown" in unresolved[0]["reason"]
    monkeypatch.setattr(audit.r, "ROOT", tmp_path)
    monkeypatch.setattr(audit.r, "PLAN", plan)
    with pytest.raises(ValueError, match="unresolved attempt evidence.*interrupted"):
        audit.audit_results(complete=True)
    assert not (plan / "completion_audit.json").exists()


def test_offline_recovery_receipt_does_not_count_as_another_evaluator_session(tmp_path):
    plan = tmp_path / "plan"
    original = plan / "attempts/job/original"
    original_attempt(original)
    recovered = original.with_name("recovered")
    recovery_attempt(tmp_path, original, recovered)
    sources, unresolved = audit.inventory_attempts(tmp_path, plan, {"job"})
    assert sources == {"job": [original]}
    assert unresolved == []


@pytest.mark.parametrize("damage", ["lost", "receipt", "transcript", "cross_job"])
def test_recovery_with_missing_or_mismatched_original_is_unresolved_after_retry(tmp_path, monkeypatch, damage):
    plan = tmp_path / "plan"
    original = plan / "attempts/job/original"
    original_attempt(original)
    recovered = original.with_name("recovered")
    recovery_attempt(tmp_path, original, recovered)
    retry = original.with_name("retry")
    original_attempt(retry)
    if damage == "lost":
        shutil.rmtree(original)
    elif damage in ("receipt", "transcript"):
        name = "receipt.json" if damage == "receipt" else "transcript.jsonl"
        path = original / name
        path.write_text(path.read_text() + "\n")  # Still parses; recorded hash must catch it.
    else:
        path = recovered / "receipt.json"
        record = json.loads(path.read_text())
        record["recovered_from"] = "plan/attempts/another_job/original"
        path.write_text(json.dumps(record))
    sources, unresolved = audit.inventory_attempts(tmp_path, plan, {"job"})
    assert retry in sources["job"]
    assert any(row["source"].endswith("/recovered") for row in unresolved)
    (plan / "manifest.json").write_text(json.dumps({"jobs": [{"id": "job"}]}))
    monkeypatch.setattr(audit.r, "ROOT", tmp_path)
    monkeypatch.setattr(audit.r, "PLAN", plan)
    with pytest.raises(ValueError, match="unresolved attempt evidence.*recovered"):
        audit.audit_results(complete=True)


@pytest.mark.parametrize("artifact,contents", [
    ("receipt.json", '{"job_id":'),
    ("transcript.jsonl", '{"type":"assistant"}\n{"type":'),
    ("transcript.jsonl", "Weekly quota exhausted\n"),
])
def test_malformed_failure_artifacts_do_not_hide_a_successful_retry(tmp_path, monkeypatch, artifact, contents):
    plan = tmp_path / "plan"
    original = plan / "attempts/job/interrupted"
    original_attempt(original)
    (original / artifact).write_text(contents)
    retry = original.with_name("retry")
    original_attempt(retry)
    sources, unresolved = audit.inventory_attempts(tmp_path, plan, {"job"})
    assert sources == {"job": [retry]}
    assert len(unresolved) == 1
    assert unresolved[0]["source"].endswith("/interrupted")
    assert "outcome and cost unresolved" in unresolved[0]["reason"]
    (plan / "manifest.json").write_text(json.dumps({"jobs": [{"id": "job"}]}))
    monkeypatch.setattr(audit.r, "ROOT", tmp_path)
    monkeypatch.setattr(audit.r, "PLAN", plan)
    with pytest.raises(ValueError, match="unresolved attempt evidence.*interrupted"):
        audit.audit_results(complete=True)
