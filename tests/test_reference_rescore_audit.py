"""Offline accounting regressions for interrupted evaluator sessions."""
import importlib.util
import json
import shutil
from datetime import datetime, timedelta, timezone
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
    (source / "transcript.jsonl").write_text('{"type":"result","total_cost_usd":1.0}\n')
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


def test_interim_audit_returns_unresolved_accounting_before_receipt_selection(tmp_path, monkeypatch, capsys):
    plan = tmp_path / "plan"
    original = plan / "attempts/job/interrupted"
    original_attempt(original)
    (original / "receipt.json").write_text('{"job_id":')
    retry = original.with_name("retry")
    original_attempt(retry)
    output = tmp_path / "evaluation.json"
    output.write_bytes((retry / "candidate.json").read_bytes())
    manifest = {"jobs": [{"id": "job", "output": "evaluation.json"}, {"id": "pending"}],
                "canary_id": "job", "pinned_files": {}, "prior_evaluations": {}, "instruments": {}}
    (plan / "manifest.json").write_text(json.dumps(manifest))
    acceptance = {"manifest_sha256": audit.r.digest(plan / "manifest.json"),
                  "evaluation_sha256": audit.r.digest(output), "runtime_model": "claude-opus-5"}
    receipt = json.loads((retry / "receipt.json").read_text())
    receipt.update(acceptance)
    (retry / "receipt.json").write_text(json.dumps(receipt))
    (plan / "canary_acceptance.json").write_text(json.dumps(acceptance))
    monkeypatch.setattr(audit.r, "ROOT", tmp_path)
    monkeypatch.setattr(audit.r, "PLAN", plan)
    # Exercise the real downstream selector: this is the failure the interim
    # accounting must avoid, rather than weakening the uniqueness gate.
    with pytest.raises(json.JSONDecodeError):
        audit.r.require_canary(manifest, manifest["jobs"][1])
    result = audit.audit_results(complete=False)
    assert result["status"] == "unresolved"
    assert result["inventoried_original_attempts"] == ["plan/attempts/job/retry"]
    assert result["accepted"] is None
    assert result["actual_model_calls"] is None
    assert result["cli_reported_total_cost_usd"] is None
    assert not result["session_accounting_complete"]
    assert len(result["unresolved_attempts"]) == 1
    monkeypatch.setattr(sys, "argv", ["audit_reference_rescore.py"])
    with pytest.raises(SystemExit) as error:
        audit.main()
    assert error.value.code == 1
    assert json.loads(capsys.readouterr().out)["status"] == "unresolved"
    with pytest.raises(ValueError, match="unresolved attempt evidence"):
        audit.audit_results(complete=True)


@pytest.mark.parametrize("terminal", [None, {"type": "result"},
                                     {"type": "result", "total_cost_usd": float("nan")},
                                     {"type": "result", "total_cost_usd": True}])
def test_complete_cohort_with_unresolved_terminal_usage_never_certifies(tmp_path, monkeypatch, capsys, terminal):
    """Exercise full accounting; scoring gates have their own real-validator tests."""
    plan = tmp_path / "plan"
    monkeypatch.setattr(audit.r, "ROOT", tmp_path)
    monkeypatch.setattr(audit.r, "PLAN", plan)
    monkeypatch.setattr(audit.r, "verify_frozen", lambda manifest: None)
    monkeypatch.setattr(audit.r, "require_canary", lambda manifest, job: None)
    monkeypatch.setattr(audit.r, "job_prompt", lambda manifest, job: "original registered prompt")
    monkeypatch.setattr(audit.r, "successful_receipt", lambda manifest, job: {
        "evaluation_sha256": audit.r.digest(tmp_path / job["output"])})
    monkeypatch.setattr(audit.r, "validate_candidate", lambda path, *args: {
        "evaluation_sha256": audit.r.digest(path), "definition_sha256": "definition"})
    doc = {"elements": [{"id": i, "name": f"element{i}", "sub_elements": [
        {"name": f"item{i}.{j}"} for j in range(5)]} for i in range(10)], "overall_score": {}}
    (tmp_path / "rubric.txt").write_text(" ".join(s["name"] for e in doc["elements"] for s in e["sub_elements"]))
    manifest = {"jobs": [], "canary_id": "job00", "prior_evaluations": {}, "instruments": {
        "rubric10-semantic": {"definition_sha256": "definition", "rubric": "rubric.txt"}}}
    for i in range(56):
        job = {"id": f"job{i:02}", "output": f"evaluation{i}.json", "rubric": "rubric10-semantic"}
        manifest["jobs"].append(job)
        source = plan / "attempts" / job["id"] / "original"
        original_attempt(source)
        (source / "candidate.json").write_text(json.dumps(doc))
        (tmp_path / job["output"]).write_bytes((source / "candidate.json").read_bytes())
        receipt = json.loads((source / "receipt.json").read_text())
        start = datetime(2026, 9, 12, tzinfo=timezone.utc) + timedelta(minutes=2 * i)
        receipt.update(started_at=start.isoformat(), completed_at=(start + timedelta(minutes=1)).isoformat(),
                       user_prompt_sha256=audit.r.digest(source / "prompt.txt"), system_prompt_sha256="definition")
        (source / "receipt.json").write_text(json.dumps(receipt))
    (plan / "manifest.json").write_text(json.dumps(manifest))
    for name in ("model_provenance_registration", "model_provenance_fill_preservation",
                 "canonical_validator_registration", "canonical_validator_fill_preservation",
                 "reporting_audit_registration", "reporting_audit_fill_preservation"):
        (plan / f"{name}.json").write_text(json.dumps({"retained_attempt_files": {},
            "existing_outputs": {"evaluation0.json": audit.r.digest(tmp_path / "evaluation0.json")}}))
    baseline = audit.audit_results(complete=True)
    assert baseline["accepted"] == baseline["actual_model_calls"] == 56
    completion_before = (plan / "completion_audit.json").read_bytes()
    failed = plan / "attempts/job00/timeout"
    original_attempt(failed)
    receipt = json.loads((failed / "receipt.json").read_text())
    receipt.update(status="incomplete", error="TimeoutExpired", user_prompt_sha256=audit.r.digest(failed / "prompt.txt"),
                   system_prompt_sha256="definition")
    receipt.pop("exit_code")
    (failed / "receipt.json").write_text(json.dumps(receipt))
    events = [{"type": "assistant", "message": {"content": []}}]
    if terminal is not None:
        events.append(terminal)
    (failed / "transcript.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    result = audit.audit_results(complete=False)
    assert result["status"] == "unresolved"
    assert result["cli_reported_total_cost_usd"] is None
    assert len(result["inventoried_original_attempts"]) == 56
    assert "terminal" in result["unresolved_attempts"][0]["reason"]
    with pytest.raises(ValueError, match="unresolved attempt evidence.*terminal"):
        audit.audit_results(complete=True)
    assert (plan / "completion_audit.json").read_bytes() == completion_before
    monkeypatch.setattr(sys, "argv", ["audit_reference_rescore.py"])
    with pytest.raises(SystemExit) as error:
        audit.main()
    assert error.value.code == 1
    assert json.loads(capsys.readouterr().out)["status"] == "unresolved"
