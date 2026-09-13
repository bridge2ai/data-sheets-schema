"""Registered execution deadline and explicit accounting for reviewed timeouts.

The frozen scoring runner is unchanged. No terminal result or cost is invented:
only exact, reviewed interrupted traces may have an unknown cost in the dated
audit. Unregistered incomplete attempts still block progress.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

PATH = "scripts/reference_rescore_cborg_deadline.py"
SECONDS = 1800


class DeadlineSubprocess:
    """Change only the frozen evaluator call; retain its candidate on timeout."""

    def __init__(self, r, original, executable, extension):
        self.r, self.original = r, original
        self.executable, self.extension = executable, extension

    def __getattr__(self, name):
        return getattr(self.original, name)

    def run(self, command, *args, **kwargs):
        if not isinstance(command, (list, tuple)) or command[:2] != [self.executable, "--print"]:
            return self.original.run(command, *args, **kwargs)
        if kwargs.get("timeout") != 900:
            raise ValueError("frozen evaluator deadline changed")
        attempt = Path(kwargs["stdout"].name).parent
        if attempt.parent.parent != self.r.PLAN / "attempts":
            raise ValueError("deadline evidence requires an original attempt directory")
        record = {"started_at": self.r.now(), "extension": self.extension,
                  "original_timeout_seconds": 900, "timeout_seconds": SECONDS,
                  "timed_out": False, "returncode": None}
        kwargs = {**kwargs, "timeout": SECONDS}
        try:
            completed = self.original.run(command, *args, **kwargs)
            record["returncode"] = completed.returncode
            return completed
        except subprocess.TimeoutExpired:
            record["timed_out"] = True
            candidate = Path(kwargs["cwd"]) / "output_evaluation.json"
            if candidate.is_file():
                # Preserve before the frozen runner removes its temporary tree.
                # A timed-out candidate remains excluded from accepted outputs.
                shutil.copyfile(candidate, attempt / "candidate.json")
                record["retained_candidate_sha256"] = self.r.digest(attempt / "candidate.json")
            raise
        finally:
            record["completed_at"] = self.r.now()
            with (attempt / "execution_deadline.json").open("x") as out:
                json.dump(record, out, indent=2)
                out.write("\n")


def enable(r, registration):
    extension = registration["deadline_extension"]
    if (extension.get("path") != PATH or extension.get("sha256") != r.digest(r.ROOT / PATH)
            or extension.get("timeout_seconds") != SECONDS):
        raise ValueError("deadline extension differs from its registration")
    executable = registration.get("validator_status_extension", {}).get(
        "path", "scripts/reference_rescore_cborg.py")
    r.subprocess = DeadlineSubprocess(r, r.subprocess, str(r.ROOT / executable), extension)


def verify_timeout_failure(r, source, registration):
    """Recognize the two reviewed 900-second failures, never generic silence."""
    import audit_reference_rescore as audit
    import reference_rescore_cborg as c

    rel = str(source.relative_to(r.ROOT))
    entry = registration.get("timeout_failures", {}).get(rel)
    if not entry or entry.get("reason") != "reviewed_900_second_timeout_before_write":
        raise ValueError("missing reviewed timeout classification")
    files = {str(p.relative_to(r.ROOT)): r.digest(p) for p in source.rglob("*") if p.is_file()}
    required = {str(source.relative_to(r.ROOT) / name) for name in
                ("receipt.json", "stderr.txt", "transcript.jsonl", "prompt.txt")}
    if set(files) != required or files != entry.get("files"):
        raise ValueError("reviewed timeout evidence changed or is incomplete")
    manifest = json.loads((r.PLAN / "manifest.json").read_bytes())
    job = next(j for j in manifest["jobs"] if j["id"] == source.parent.name)
    receipt = json.loads((source / "receipt.json").read_bytes())
    if (receipt.get("job_id") != job["id"] or receipt.get("status") != "incomplete"
            or "exit_code" in receipt or receipt.get("manifest_sha256") != r.digest(r.PLAN / "manifest.json")
            or receipt.get("user_prompt_sha256") != r.digest(source / "prompt.txt")
            or receipt.get("system_prompt_sha256") != manifest["instruments"][job["rubric"]]["definition_sha256"]
            or (source / "prompt.txt").read_bytes() != r.job_prompt(manifest, job).encode()
            or not str(receipt.get("error", "")).startswith("TimeoutExpired: ")
            or not receipt["error"].endswith("timed out after 900 seconds")):
        raise ValueError("receipt does not establish the reviewed timeout")
    start, end = (datetime.fromisoformat(receipt[key]) for key in ("started_at", "completed_at"))
    if not start.tzinfo or not end.tzinfo or (end - start).total_seconds() < 900:
        raise ValueError("timeout timestamps do not establish a completed 900-second wait")
    events = audit.read_trace(source)
    c.verify_runtime_transport(events)
    _, models = r.transcript_evidence(events)
    if models != {manifest["transport"]["runtime_model_identifier"]}:
        raise ValueError("timeout lacks the registered model-response evidence")
    if any(e.get("type") == "result" for e in events):
        raise ValueError("a terminal result must use ordinary cost accounting")
    for event in events:
        message = event.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), list):
            if any(isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Write"
                   for b in message["content"]):
                raise ValueError("reviewed pre-Write timeout contains a Write")
    controller = r.ROOT / entry["controller_result"]
    if r.digest(controller) != entry["controller_result_sha256"]:
        raise ValueError("timeout controller evidence changed")
    result = json.loads(controller.read_bytes())
    if (result.get("status") != "stopped"
            or [row for row in result["completed"] if row["job_id"] == job["id"]]
            != [{"job_id": job["id"], "exit_code": 1}]):
        raise ValueError("controller did not finish the failed worker")
    return {"source": rel, "job_id": job["id"], "classification": entry["reason"],
            "evaluator_launched": True, "accepted": False, "cli_reported_cost_usd": None,
            "cost_basis": "No terminal CLI result. Partial stream usage does not establish complete cost; this real session is unpriced, not free."}


def fingerprint(events):
    return hashlib.sha256(json.dumps(events, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def accounted_audit(r, registration):
    """Use all frozen acceptance gates; classify only byte-pinned interruptions."""
    import audit_reference_rescore as audit
    import reference_rescore_cborg_batch as batch

    timeouts = [verify_timeout_failure(r, r.ROOT / rel, registration)
                for rel in registration.get("timeout_failures", {})]
    reviewed = {fingerprint(audit.read_trace(r.ROOT / row["source"])) for row in timeouts}
    if len(reviewed) != len(timeouts):
        raise ValueError("ambiguous timeout trace inventory")
    original_inventory, original_cost, original_runner = audit.inventory_attempts, audit.terminal_cost, audit.r
    audit.r = r
    audit.terminal_cost = lambda events: None if fingerprint(events) in reviewed else original_cost(events)
    audit.inventory_attempts = lambda root, plan, jobs: batch.inventory_with_prelaunch(
        r, registration, original_inventory, root, plan, jobs)
    try:
        result = audit.audit_results(complete=False)
    finally:
        audit.inventory_attempts, audit.terminal_cost, audit.r = original_inventory, original_cost, original_runner
    if result["status"] != "verified":
        return result
    unpriced = {row["source"] for row in result["original_calls"] if row["cli_reported_cost_usd"] is None}
    if unpriced != {row["source"] for row in timeouts}:
        raise ValueError("unpriced session inventory differs from reviewed timeouts")
    for call in result["original_calls"]:
        if call["source"] in unpriced:
            if call["accepted_source"] or call["status"] != "incomplete":
                raise ValueError("an interrupted session cannot become an accepted source")
            call["original_error"] = "TimeoutExpired: evaluator exceeded 900 seconds before a Write or terminal result"
    result["known_terminal_cli_cost_usd"] = result["cli_reported_total_cost_usd"]
    if timeouts:
        result["cli_reported_total_cost_usd"] = None
    result["unpriced_excluded_sessions"] = timeouts
    result["cost_qualification"] = (
        f"{len(timeouts)} retained interrupted evaluator sessions have unknown cost. "
        "The known terminal CLI subtotal excludes their unreported usage; total expenditure is unknown. "
        "CLI estimates are not reconciled CBORG charges. Measurement/session completion does not imply complete cost accounting."
    )
    return result
