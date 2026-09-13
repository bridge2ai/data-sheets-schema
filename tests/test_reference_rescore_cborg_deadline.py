"""Offline evidence-retention and unknown-cost gates for the dated CBORG run."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_reference_rescore as audit
import reference_rescore_cborg_deadline as deadline
import reference_rescore_cborg as cborg

from tests.test_reference_rescore import environment, runner


def test_timeout_keeps_original_candidate_before_frozen_runner_cleanup(environment, monkeypatch):
    root, manifest, job, _ = environment
    called = []
    candidate = b'{"original": "incomplete evaluator write"}\n'

    def timeout(command, **kwargs):
        called.append((command, kwargs["timeout"]))
        assert command[command.index("--max-budget-usd") + 1] == "5"
        (Path(kwargs["cwd"]) / "output_evaluation.json").write_bytes(candidate)
        kwargs["stdout"].write('{"type":"assistant"}\n')
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    extension = {"path": deadline.PATH, "sha256": "test", "timeout_seconds": 1800}
    proxy = deadline.DeadlineSubprocess(runner, SimpleNamespace(run=timeout), "test-cli", extension)
    monkeypatch.setattr(runner, "subprocess", proxy)
    receipt = runner.run_job(manifest, job, "test-cli")
    assert receipt["status"] == "incomplete" and receipt["error"].startswith("TimeoutExpired:")
    assert not (root / job["output"]).exists()
    attempt, = (runner.PLAN / "attempts" / job["id"]).iterdir()
    assert (attempt / "candidate.json").read_bytes() == candidate
    proof = json.loads((attempt / "execution_deadline.json").read_bytes())
    assert proof["timed_out"] is True and proof["returncode"] is None
    assert proof["retained_candidate_sha256"] == runner.digest(attempt / "candidate.json")
    assert called[0][1] == 1800
    assert list((root / "temporary").iterdir()) == []


def test_other_subprocess_calls_are_unchanged(tmp_path):
    calls = []
    original = SimpleNamespace(run=lambda *args, **kwargs: calls.append((args, kwargs)))
    proxy = deadline.DeadlineSubprocess(None, original, "registered-cli", {})
    proxy.run(["python", "validator.py"], timeout=900, capture_output=True)
    assert calls == [((["python", "validator.py"],), {"timeout": 900, "capture_output": True})]


def test_real_local_timeout_retains_candidate_and_waits_for_process(environment, monkeypatch):
    root, manifest, job, _ = environment
    executable = root / "synthetic_cli"
    executable.write_text(f"#!{sys.executable}\n"
                          "from pathlib import Path\nimport time\n"
                          "Path('output_evaluation.json').write_text('original partial candidate')\n"
                          "print('{\"type\":\"assistant\"}',flush=True)\ntime.sleep(60)\n")
    executable.chmod(0o700)
    monkeypatch.setattr(deadline, "SECONDS", 0.5)
    proxy = deadline.DeadlineSubprocess(runner, subprocess, str(executable), {"synthetic_probe": True})
    monkeypatch.setattr(runner, "subprocess", proxy)
    receipt = runner.run_job(manifest, job, str(executable))
    assert receipt["status"] == "incomplete" and receipt["error"].startswith("TimeoutExpired:")
    attempt, = (runner.PLAN / "attempts" / job["id"]).iterdir()
    assert (attempt / "candidate.json").read_text() == "original partial candidate"
    assert json.loads((attempt / "execution_deadline.json").read_bytes())["timed_out"] is True
    assert not (root / job["output"]).exists()
    assert list((root / "temporary").iterdir()) == []


def test_changed_frozen_timeout_rejects_before_launch():
    def forbidden(*args, **kwargs):
        raise AssertionError("must not launch")
    proxy = deadline.DeadlineSubprocess(None, SimpleNamespace(run=forbidden), "registered-cli", {})
    with pytest.raises(ValueError, match="frozen evaluator deadline"):
        proxy.run(["registered-cli", "--print"], timeout=901)


@pytest.fixture
def reviewed_timeout(tmp_path):
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    plan = tmp_path / "plan"
    source = plan / "attempts/job/original"
    source.mkdir(parents=True)
    job = {"id": "job", "rubric": "r10", "output": "out.json"}
    manifest = {"jobs": [job], "instruments": {"r10": {"definition_sha256": "definition"}},
                "transport": cborg.TRANSPORT}
    (plan / "manifest.json").write_text(json.dumps(manifest))
    (source / "prompt.txt").write_text("original prompt")
    (source / "stderr.txt").write_text("")
    events = [
        {"type": "system", "subtype": "init", "tools": ["Read", "Write", "Bash"],
         "apiKeySource": "ANTHROPIC_API_KEY", "claude_code_version": "2.1.269"},
        {"type": "assistant", "message": {"id": "msg-original", "model": "claude-opus-5",
                                          "content": [{"type": "text", "text": "began"}]}}]
    (source / "transcript.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    receipt = {"job_id": "job", "status": "incomplete", "started_at": "2026-09-12T22:00:00+00:00",
               "completed_at": "2026-09-12T22:15:01+00:00", "manifest_sha256": digest(plan / "manifest.json"),
               "user_prompt_sha256": digest(source / "prompt.txt"), "system_prompt_sha256": "definition",
               "error": "TimeoutExpired: original command timed out after 900 seconds"}
    (source / "receipt.json").write_text(json.dumps(receipt))
    controller = plan / "result.json"
    controller.write_text(json.dumps({"status": "stopped", "completed": [{"job_id": "job", "exit_code": 1}]}))
    r = SimpleNamespace(ROOT=tmp_path, PLAN=plan, digest=digest, job_prompt=lambda m, j: "original prompt",
                        transcript_evidence=runner.transcript_evidence)
    entry = {"reason": "reviewed_900_second_timeout_before_write",
             "files": {str(p.relative_to(tmp_path)): digest(p) for p in source.iterdir()},
             "controller_result": "plan/result.json", "controller_result_sha256": digest(controller)}
    registration = {"timeout_failures": {str(source.relative_to(tmp_path)): entry}}
    return r, source, registration, events, receipt


def test_exact_interrupted_session_is_counted_and_unpriced(reviewed_timeout):
    r, source, registration, _, _ = reviewed_timeout
    row = deadline.verify_timeout_failure(r, source, registration)
    assert row["evaluator_launched"] is True and row["accepted"] is False
    assert row["cli_reported_cost_usd"] is None


@pytest.mark.parametrize("mutation", ["unregistered", "extra_ignored_file", "changed_bytes", "missing_prompt"])
def test_timeout_inventory_requires_every_original_byte(reviewed_timeout, mutation):
    r, source, registration, _, _ = reviewed_timeout
    if mutation == "unregistered":
        registration["timeout_failures"] = {}
    elif mutation == "extra_ignored_file":
        (source / ".ignored").write_text("extra")
    elif mutation == "changed_bytes":
        (source / "stderr.txt").write_text("different")
    else:
        (source / "prompt.txt").unlink()
    with pytest.raises(ValueError):
        deadline.verify_timeout_failure(r, source, registration)


@pytest.mark.parametrize("mutation", ["passed", "exit_code", "short_wait", "wrong_prompt", "terminal",
                                     "write", "wrong_model", "empty_trace", "worker_not_drained"])
def test_even_rehashed_inadequate_evidence_is_not_a_known_timeout(reviewed_timeout, mutation):
    r, source, registration, events, receipt = reviewed_timeout
    entry = registration["timeout_failures"][str(source.relative_to(r.ROOT))]
    if mutation == "passed": receipt["status"] = "passed"
    elif mutation == "exit_code": receipt["exit_code"] = 0
    elif mutation == "short_wait": receipt["completed_at"] = receipt["started_at"]
    elif mutation == "wrong_prompt": (source / "prompt.txt").write_text("edited")
    elif mutation == "terminal": events.append({"type": "result", "total_cost_usd": 1})
    elif mutation == "write": events[1]["message"]["content"].append({"type": "tool_use", "name": "Write"})
    elif mutation == "wrong_model": events[1]["message"]["model"] = "another-model"
    elif mutation == "empty_trace": events = []
    elif mutation == "worker_not_drained":
        (r.PLAN / "result.json").write_text('{"status":"running","completed":[]}')
        entry["controller_result_sha256"] = r.digest(r.PLAN / "result.json")
    (source / "transcript.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    (source / "receipt.json").write_text(json.dumps(receipt))
    entry["files"] = {str(p.relative_to(r.ROOT)): r.digest(p) for p in source.iterdir()}
    with pytest.raises(ValueError):
        deadline.verify_timeout_failure(r, source, registration)


def test_cost_overlay_is_exact_and_restores_frozen_audit(reviewed_timeout, monkeypatch):
    r, source, registration, events, _ = reviewed_timeout
    original_cost, original_inventory, original_runner = audit.terminal_cost, audit.inventory_attempts, audit.r

    def inspect_overlay(*, complete):
        assert complete is False
        assert audit.terminal_cost(events) is None
        assert audit.terminal_cost([{"type": "result", "total_cost_usd": 2.5}]) == 2.5
        changed = copy.deepcopy(events)
        changed[1]["message"]["id"] = "another-session"
        with pytest.raises(ValueError, match="terminal result"):
            audit.terminal_cost(changed)
        return {"status": "verified", "cli_reported_total_cost_usd": 2.5, "cost_accounting_complete": False,
                "original_calls": [{"source": str(source.relative_to(r.ROOT)), "cli_reported_cost_usd": None,
                                    "accepted_source": False, "status": "incomplete"}]}

    monkeypatch.setattr(audit, "audit_results", inspect_overlay)
    result = deadline.accounted_audit(r, registration)
    assert result["known_terminal_cli_cost_usd"] == 2.5
    assert result["cli_reported_total_cost_usd"] is None
    assert result["cost_accounting_complete"] is False
    assert len(result["unpriced_excluded_sessions"]) == 1
    assert audit.terminal_cost is original_cost and audit.inventory_attempts is original_inventory and audit.r is original_runner


def test_cost_overlay_restores_frozen_functions_on_failure(reviewed_timeout, monkeypatch):
    r, _, registration, _, _ = reviewed_timeout
    saved = audit.terminal_cost, audit.inventory_attempts, audit.r
    def fail(**kwargs):
        raise RuntimeError("audit failed")
    monkeypatch.setattr(audit, "audit_results", fail)
    with pytest.raises(RuntimeError, match="audit failed"):
        deadline.accounted_audit(r, registration)
    assert (audit.terminal_cost, audit.inventory_attempts, audit.r) == saved
