"""Offline accounting regressions for interrupted evaluator sessions."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("audit_reference_rescore", SCRIPTS / "audit_reference_rescore.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


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
    retry.mkdir()
    (retry / "prompt.txt").write_text("original registered prompt")
    (retry / "transcript.jsonl").write_text('{"type":"result"}\n')
    (retry / "receipt.json").write_text(json.dumps({"job_id": "job", "status": "passed"}))
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
    original.mkdir(parents=True)
    (original / "prompt.txt").write_text("original registered prompt")
    (original / "transcript.jsonl").write_text('{"type":"result"}\n')
    (original / "receipt.json").write_text(json.dumps({"job_id": "job", "status": "passed"}))
    recovered = original.with_name("recovered")
    recovered.mkdir()
    (recovered / "receipt.json").write_text(json.dumps({
        "job_id": "job", "status": "passed", "model_calls_during_recovery": 0,
        "recovered_from": "plan/attempts/job/original"}))
    sources, unresolved = audit.inventory_attempts(tmp_path, plan, {"job"})
    assert sources == {"job": [original]}
    assert unresolved == []
