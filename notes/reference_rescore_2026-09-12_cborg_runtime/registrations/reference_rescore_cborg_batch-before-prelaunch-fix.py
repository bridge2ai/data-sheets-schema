#!/usr/bin/env python3
"""Launch the registered CBORG ratings with a separately reviewed four-worker canary.

This scheduler does not alter the frozen evaluator, prompts or manifest. Its
pilot is an already planned repeat rating. Each worker runs the original
isolated evaluator and retains its original attempt evidence.
"""
from __future__ import annotations

import argparse
from collections import deque
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

import reference_rescore_cborg as c

ROOT = c.ROOT
PLAN = ROOT / f"notes/reference_rescore_{c.DATE}"
REGISTRATION = PLAN / "batch_registration.json"


def load_registered():
    r = c.load_runner()
    manifest = json.loads((PLAN / "manifest.json").read_bytes())
    registration = json.loads(REGISTRATION.read_bytes())
    if (registration["manifest_sha256"] != r.digest(PLAN / "manifest.json")
            or registration["scheduler_sha256"] != r.digest(Path(__file__))
            or registration["workers"] != 4
            or manifest["transport"] != c.TRANSPORT):
        raise ValueError("batch registration does not match the frozen execution files")
    r.verify_frozen(manifest)
    return r, manifest, registration


def verified_output(r, manifest, job):
    """Bind the accepted bytes to the last successful original evaluator Write."""
    receipt = r.successful_receipt(manifest, job)
    target = ROOT / job["output"]
    original = [p for p in (PLAN / "attempts" / job["id"]).iterdir()
                if (p / "prompt.txt").is_file() and (p / "candidate.json").is_file()
                and (p / "candidate.json").read_bytes() == target.read_bytes()]
    if len(original) != 1:
        raise ValueError("missing or ambiguous original candidate")
    source = original[0]
    events = [json.loads(line) for line in (source / "transcript.jsonl").read_text().splitlines() if line.strip()]
    evidence = r.validate_candidate(target, job, manifest, events)
    initializers = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    expected = Path(initializers[0]["cwd"]) / "output_evaluation.json"
    writes, completed = {}, []
    for event in events:
        message = event.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), list):
            continue
        for block in message["content"]:
            if not isinstance(block, dict):
                continue
            if event["type"] == "assistant" and block.get("type") == "tool_use" and block.get("name") == "Write":
                args = block.get("input") or {}
                path = Path(args.get("file_path", ""))
                if path.is_absolute() and path.resolve() == expected.resolve() and isinstance(args.get("content"), str):
                    writes[block["id"]] = args["content"].encode()
            if event["type"] == "user" and block.get("type") == "tool_result" and not block.get("is_error"):
                if block.get("tool_use_id") in writes:
                    completed.append(writes.pop(block["tool_use_id"]))
    if not completed or completed[-1] != target.read_bytes():
        raise ValueError("published output does not match the last successful original Write")
    if receipt["evaluation_sha256"] != evidence["evaluation_sha256"]:
        raise ValueError("receipt differs from original output")
    if job["rubric"] == "rubric10-semantic":
        doc = json.loads(target.read_bytes())
        canary = next(j for j in manifest["jobs"] if j["id"] == manifest["canary_id"])
        reference = json.loads((ROOT / canary["output"]).read_bytes())
        names = lambda d: [(e["id"], e["name"], [s["name"] for s in e["sub_elements"]]) for e in d["elements"]]
        if names(doc) != names(reference):
            raise ValueError("rubric10 item identities differ from the reviewed canary")
    return {"job_id": job["id"], "evaluation_sha256": evidence["evaluation_sha256"],
            "original_attempt": str(source.relative_to(ROOT)), "runtime_model": evidence["runtime_model"]}


def require_review(r, filename, hash_key, expected):
    review = json.loads((PLAN / filename).read_bytes())
    if review.get("verdict") != "approved" or review.get(hash_key) != expected:
        raise ValueError(f"missing matching approved review: {filename}")


def require_pilot(r, manifest, registration):
    acceptance = json.loads((PLAN / "batch_canary_acceptance.json").read_bytes())
    job = next(j for j in manifest["jobs"] if j["id"] == registration["pilot_job_id"])
    output = verified_output(r, manifest, job)
    if (acceptance.get("registration_sha256") != r.digest(REGISTRATION)
            or acceptance.get("evaluation_sha256") != output["evaluation_sha256"]):
        raise ValueError("batch canary acceptance differs from this registration or rating")


def pending_jobs(r, manifest, registration, phase):
    """Never retry an attempted job automatically, including an unfinished attempt."""
    selected = [j for j in manifest["jobs"] if phase != "pilot" or j["id"] == registration["pilot_job_id"]]
    pending = []
    for job in selected:
        if (ROOT / job["output"]).exists():
            verified_output(r, manifest, job)
            continue
        attempts = PLAN / "attempts" / job["id"]
        if job["id"] in registration.get("reviewed_retries", {}) or (attempts.exists() and any(attempts.iterdir())):
            verify_reviewed_retry(r, job, registration, attempts)
        pending.append(job)
    return pending


def verify_reviewed_retry(r, job, registration, attempts):
    """Allow only the exact failed history inspected before a single fresh retry."""
    import audit_reference_rescore as audit

    retry = registration.get("reviewed_retries", {}).get(job["id"])
    if not retry:
        raise ValueError(f"{job['id']} already has an attempt; inspect and register any retry separately")
    expected = retry["attempts"]
    if not expected or not attempts.is_dir():
        raise ValueError("reviewed retry history is missing or its registered inventory is empty")
    actual = {str(path.relative_to(ROOT)): path for path in attempts.iterdir()}
    if set(actual) != set(expected):
        raise ValueError("retry history changed; another attempt requires separate review")
    for rel, path in actual.items():
        files = {str(p.relative_to(ROOT)): r.digest(p) for p in path.rglob("*") if p.is_file()}
        if files != expected[rel]:
            raise ValueError("reviewed failed-attempt bytes changed")
        receipt = json.loads((path / "receipt.json").read_bytes())
        if (receipt.get("job_id") != job["id"] or receipt.get("status") != "incomplete"
                or not receipt.get("completed_at") or not (path / "prompt.txt").is_file()):
            raise ValueError("retry requires a completed, excluded original attempt")
        audit.terminal_cost(audit.read_trace(path))


@contextmanager
def batch_lock():
    # Retain the inode, as for the frozen runner's canary lock.
    with (PLAN / ".batch.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def schedule(job_ids, command, run_dir, workers=4):
    """Start one worker at a time until its frozen runner releases the startup gate.

    A failure stops new launches; already running evaluator sessions finish and
    retain their receipts. The controller never retries or abandons a worker.
    """
    pending = deque(job_ids)
    selector = selectors.DefaultSelector()
    active = {}
    waiting_for_start = None
    failed = False
    completed = []
    stop_signal = None

    def request_stop(signum, frame):
        nonlocal stop_signal
        stop_signal = signum

    run_dir.mkdir(parents=True, exist_ok=False)
    with (run_dir / "events.jsonl").open("x") as events:
        def record(kind, **fields):
            event = {"event": kind, "at": time.time(), **fields}
            events.write(json.dumps(event) + "\n")
            events.flush()
            print(json.dumps(event), flush=True)

        previous_handlers = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)}
        interruption_recorded = False
        try:
            while pending or active:
                if stop_signal is not None:
                    failed = True
                    if not interruption_recorded:
                        record("interrupted", signal=stop_signal, action="stop new launches; drain active workers")
                        interruption_recorded = True
                # Observe all exits before considering another launch.
                for process, info in list(active.items()):
                    code = process.poll()
                    if code is not None and code != 0:
                        failed = True
                    if code is not None and info["eof"]:
                        if not info["started"]:
                            failed = True
                        record("finished", job=info["job"], exit_code=code)
                        completed.append({"job_id": info["job"], "exit_code": code})
                        info["log"].close()
                        process.stdout.close()
                        del active[process]
                        if waiting_for_start is process:
                            waiting_for_start = None
                if waiting_for_start is not None:
                    info = active[waiting_for_start]
                    if time.monotonic() - info["launched"] > 60 and not info["startup_timeout"]:
                        failed = True
                        info["startup_timeout"] = True
                        record("startup_timeout", job=info["job"], action="stop new launches; drain active workers")
                if failed and not active:
                    break
                if pending and not failed and stop_signal is None and waiting_for_start is None and len(active) < workers:
                    job_id = pending[0]
                    argv = command(job_id)
                    child_env = dict(os.environ)
                    # Observe a stop during argument preparation before consuming
                    # the job. Defer signal handling only across the short atomic
                    # launch decision; workers unblock these inherited signals.
                    stop_signals = {signal.SIGINT, signal.SIGTERM}
                    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, stop_signals)
                    try:
                        if stop_signal is None and not stop_signals.intersection(signal.sigpending()):
                            process = subprocess.Popen(argv, cwd=ROOT, env=child_env,
                                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                       start_new_session=True)
                            pending.popleft()
                            os.set_blocking(process.stdout.fileno(), False)
                            info = {"job": job_id, "buffer": b"", "started": False, "eof": False,
                                    "launched": time.monotonic(), "startup_timeout": False,
                                    "log": (run_dir / f"{job_id}.txt").open("xb")}
                            active[process] = info
                            selector.register(process.stdout, selectors.EVENT_READ, process)
                            waiting_for_start = process
                            record("launched", job=job_id, pid=process.pid)
                    finally:
                        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
                for key, _ in selector.select(timeout=0.2):
                    process = key.data
                    info = active[process]
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        info["eof"] = True
                        continue
                    info["log"].write(chunk)
                    info["log"].flush()
                    info["buffer"] += chunk
                    while b"\n" in info["buffer"]:
                        line, info["buffer"] = info["buffer"].split(b"\n", 1)
                        if line.startswith(f"Starting {info['job']} (".encode()):
                            info["started"] = True
                            if waiting_for_start is process:
                                waiting_for_start = None
                            record("started", job=info["job"], active_workers=len(active))
        except BaseException as exc:
            failed = True
            record("controller_error", error=f"{type(exc).__name__}: {exc}",
                   action="stop new launches; drain active workers")
        finally:
            # Even an operator interruption or controller exception must not
            # strand a paid evaluator whose original runner owns its timeout.
            for process, info in active.items():
                os.set_blocking(process.stdout.fileno(), True)
                info["log"].write(process.stdout.read())
                code = process.wait()
                record("finished", job=info["job"], exit_code=code, drained_after_controller_error=True)
                completed.append({"job_id": info["job"], "exit_code": code})
                info["log"].close()
                process.stdout.close()
            selector.close()
            for sig, handler in previous_handlers.items():
                signal.signal(sig, handler)
        result = {"status": "stopped" if failed or stop_signal is not None else "passed", "completed": completed,
                  "not_launched": list(pending), "workers": workers, "stop_signal": stop_signal}
        (run_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "pilot", "accept-pilot", "remaining", "worker"))
    parser.add_argument("--job")
    parser.add_argument("--phase", choices=("pilot", "remaining"))
    args = parser.parse_args(argv)
    if args.action == "worker":
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT, signal.SIGTERM})
    r, manifest, registration = load_registered()
    pilot = next(j for j in manifest["jobs"] if j["id"] == registration["pilot_job_id"])
    r.require_canary(manifest, pilot)
    if args.action == "plan":
        print(json.dumps({"workers": registration["workers"], "pilot": pilot["id"],
                          "remaining": [j["id"] for j in pending_jobs(r, manifest, registration, "remaining")]}))
        return 0
    require_review(r, registration.get("pre_spend_review", "batch_pre_spend_review.json"),
                   "registration_sha256", r.digest(REGISTRATION))
    pilot_launch = PLAN / registration.get("pilot_launch_record", "batch_canary_launch.json")
    if args.action == "accept-pilot":
        with batch_lock():
            output = verified_output(r, manifest, pilot)
            require_review(r, "batch_canary_review.json", "evaluation_sha256", output["evaluation_sha256"])
            launch = json.loads(pilot_launch.read_bytes())
            result = json.loads((ROOT / launch["run_dir"] / "result.json").read_bytes())
            if (launch["registration_sha256"] != r.digest(REGISTRATION) or result["status"] != "passed"
                    or result["completed"] != [{"job_id": pilot["id"], "exit_code": 0}]
                    or result["workers"] != registration["workers"] or result["not_launched"]):
                raise ValueError("batch canary did not complete through this scheduler")
            r.write_json(PLAN / "batch_canary_acceptance.json", {
                "accepted_at": r.now(), "registration_sha256": r.digest(REGISTRATION), **output})
        return 0
    phase = args.phase if args.action == "worker" else args.action
    if phase not in ("pilot", "remaining"):
        raise ValueError("worker phase is required")
    if phase == "remaining":
        require_pilot(r, manifest, registration)
    c.cborg_environment(dict(os.environ))
    if args.action == "worker":
        job = next(j for j in manifest["jobs"] if j["id"] == args.job)
        if phase == "pilot" and job != pilot:
            raise ValueError("pilot phase accepts only its registered rating")
        if job not in pending_jobs(r, {**manifest, "jobs": [job]}, registration, phase):
            raise ValueError("worker job is already completed")
        receipt = r.run_job(manifest, job, str(ROOT / "scripts/reference_rescore_cborg.py"))
        if receipt["status"] != "passed":
            return 1
        verified_output(r, manifest, job)
        return 0
    with batch_lock():
        jobs = pending_jobs(r, manifest, registration, phase)
        if phase == "pilot" and len(jobs) != 1:
            raise ValueError("pilot already completed; inspect it before acceptance")
        run_dir = PLAN / "batch_runs" / (r.now().replace(":", "-") + "_" + phase)
        if phase == "pilot":
            with pilot_launch.open("x") as handle:
                json.dump({"registered_at": r.now(), "registration_sha256": r.digest(REGISTRATION),
                           "run_dir": str(run_dir.relative_to(ROOT))}, handle, indent=2)
                handle.write("\n")
        command = lambda job: [sys.executable, str(Path(__file__).resolve()), "worker", "--phase", phase, "--job", job]
        result = schedule([j["id"] for j in jobs], command, run_dir, registration["workers"])
        return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
