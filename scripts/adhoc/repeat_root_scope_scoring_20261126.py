#!/usr/bin/env python3
"""Repeat-scoring orchestration, PR 6366, 2026-11-26.

Inputs: two pinned scorer checkouts and accepted run-1 plans/receipts. Outputs:
read-only repeat plans, or unchanged scorer runs plus byte-identical exports and
private manifests. Execution requires separate authorization; never resume a run.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
SCORER_HEAD = "9452a5c49a0533d86c5e08c1093021036ef98830"
RUNNER_SHA = "b2a5c0995d891d4c5179509834b460390b1d921d78b0191965fc4ea3f91c21b9"
RUNNER = "scripts/adhoc/score_semantic_rubric_codex_20261125.py"
INSTRUMENT = "2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6"
LABEL_PREFIX = "2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep"
METHOD = "claudecode_release"
PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC")
RUBRICS = ("rubric10", "rubric20")
LIMIT = 32 * 1024 * 1024
EXPORT_VALIDATOR_TIMEOUT = 120
EXPORT_STOP_GRACE = 2.0
EXPORT_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def physical(value):
    path = Path(os.path.abspath(value))
    require(all(not parent.is_symlink() for parent in (path, *path.parents)),
            f"symlink route refused: {path}")
    return path


def read_bytes(path):
    path = physical(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= LIMIT,
            f"expected bounded regular file: {path}")
    return path.read_bytes()


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    return json.loads(read_bytes(path), object_pairs_hook=pairs)


def write_json(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with physical(path).open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    require(read_bytes(path) == raw, "JSON receipt write differs")


def plan_digest(plan):
    return sha(json.dumps(plan, sort_keys=True).encode())


def _orchestration():
    return {"path": str(Path(__file__).resolve()), "sha256": sha(read_bytes(__file__))}


def _checkout(root):
    root = physical(root)
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True, timeout=60).stdout.strip()
    require(head == SCORER_HEAD, "scoring checkout is not the exact run-1 head")
    for flags in ([], ["--cached"]):
        subprocess.run(["git", "-C", str(root), "diff", *flags, "--quiet"], check=True, timeout=60)
    require(sha(read_bytes(root / RUNNER)) == RUNNER_SHA, "pinned scorer runner differs")


def _load_scorer(root):
    path = physical(root) / RUNNER
    require(sha(read_bytes(path)) == RUNNER_SHA, "pinned scorer runner differs")
    spec = importlib.util.spec_from_file_location("repeat_pinned_scorer", path)
    require(spec is not None and spec.loader is not None, "cannot load pinned scorer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def in_checkout(root, function, *args):
    previous_cwd, previous_path = Path.cwd(), list(sys.path)
    try:
        os.chdir(physical(root))
        sys.path.insert(0, str(physical(root) / "src"))
        return function(*args)
    finally:
        os.chdir(previous_cwd)
        sys.path[:] = previous_path


def _dependencies(plan):
    root = Path(plan["repo_root"])
    result = {}
    for path, digest in plan["validation_sha256"].items():
        relative = Path(path).relative_to(root).as_posix()
        require(relative not in result, "duplicate validator dependency")
        result[relative] = digest
    return result


def _command_shape(plan, name):
    replacements = ((str(Path(plan["run_directory"])), "RUN"),
                    (str(Path(plan["repo_root"])), "ROOT"))
    shaped = []
    for argument in plan[name]:
        for prefix, replacement in replacements:
            if argument == prefix or argument.startswith(prefix + "/"):
                argument = replacement + argument[len(prefix):]
                break
        shaped.append(argument)
    return shaped


def verify_plan_identity(plan, baseline_plan):
    require(plan["runner_sha256"] == baseline_plan["runner_sha256"] == RUNNER_SHA,
            "runner differs from run 1")
    for name in ("instrument", "identity", "deterministic_fields", "definition_provenance",
                 "prompt", "prompt_sha256", "requested", "executable_sha256", "validation_venv", "auth_file"):
        require(plan[name] == baseline_plan[name], f"run-1 binding differs: {name}")
    require(sha(plan["prompt"].encode()) == plan["prompt_sha256"], "prompt hash differs")
    require({name: item["sha256"] for name, item in plan["inputs"].items()} ==
            {name: item["sha256"] for name, item in baseline_plan["inputs"].items()},
            "measured input hashes differ from run 1")
    require(_dependencies(plan) == _dependencies(baseline_plan), "validator dependencies differ from run 1")
    require(_command_shape(plan, "validation_command") == _command_shape(baseline_plan, "validation_command"),
            "validator argv differs from run 1")
    require(_command_shape(plan, "command") == _command_shape(baseline_plan, "command"),
            "scorer argv differs from run 1")


def _accepted(plan, plan_path, receipt_path):
    require(read_json(plan_path) == plan, "saved scorer plan differs")
    receipt = read_json(receipt_path)
    require(receipt.get("status") == "VALIDATED_AND_PUBLISHED", "scorer receipt is not accepted")
    require(receipt.get("plan_sha256") == plan_digest(plan), "scorer receipt names another plan")
    require(receipt.get("codex_exit") == 0 and receipt.get("validator_exit") == 0,
            "scorer or validator did not succeed")
    require(receipt.get("auth_copy_absent") is True, "authentication cleanup is unproven")
    require(not (physical(plan["run_directory"]) / "codex-home/auth.json").exists(),
            "copied authentication remains")
    require(receipt.get("output") == plan["output"], "scorer receipt names another publication")
    raw = read_bytes(plan["output"])
    require(raw == read_bytes(Path(plan["run_directory"]) / "candidate_evaluation.json"),
            "published and validated bytes differ")
    require(sha(raw) == receipt.get("output_sha256") == receipt.get("validator_input_sha256"),
            "accepted output hashes differ")
    logs = receipt.get("evaluation_model", {}).get("session_logs")
    require(isinstance(logs, list) and logs, "accepted session evidence missing")
    seen = set()
    run = physical(plan["run_directory"])
    for entry in logs:
        path = physical(run / entry["path"])
        require(run in path.parents and path not in seen, "session evidence path differs")
        require(sha(read_bytes(path)) == entry["sha256"], "accepted session evidence changed")
        seen.add(path)
    return receipt, raw


def _baseline_runs(directory):
    directory = physical(directory)
    result = {}
    for run in sorted(directory.iterdir()):
        physical(run)
        if not run.is_dir():
            continue
        plan_path, receipt_path = run / "plan.json", run / "receipt.json"
        plan = read_json(plan_path)
        require(physical(plan["run_directory"]) == run, "baseline plan names another run directory")
        _accepted(plan, plan_path, receipt_path)
        identity = plan["identity"]
        label = identity["label"]
        require(label in {LABEL_PREFIX + str(rep) for rep in (1, 2, 3)}, "unexpected baseline label")
        generation_rep = int(label[-1])
        family = identity["rubric"].removesuffix("-semantic")
        key = generation_rep, identity["project"], family
        require(key not in result, "duplicate baseline identity")
        require(identity.get("version") == "6.0" and identity.get("method") == METHOD
                and identity.get("instrument_id") == INSTRUMENT and plan.get("instrument") == INSTRUMENT,
                "baseline is not the registered root-scope instrument")
        require(plan["runner_sha256"] == RUNNER_SHA, "baseline runner differs")
        result[key] = {"plan": plan, "plan_path": str(plan_path), "receipt_path": str(receipt_path),
                       "plan_sha256": sha(read_bytes(plan_path)), "receipt_sha256": sha(read_bytes(receipt_path))}
    expected = {(rep, project, rubric) for rep in (1, 2, 3) for project in PROJECTS for rubric in RUBRICS}
    require(set(result) == expected and len(result) == 30, "expected exactly thirty accepted run-1 identities")
    return result


def _destination(root, scoring_rep, identity):
    root = physical(root)
    require(root.is_dir() and "evaluation_llm" not in root.parts, "publication root is not a safe repository root")
    family = identity["rubric"].removesuffix("-semantic")
    return physical(root / "data/evaluation_repeats" / INSTRUMENT / f"scoring_rep{scoring_rep}" /
                    (family + "_semantic") / f"{identity['project']}_{identity['label']}_evaluation.json")


def _canary(job):
    return (job["scoring_replicate"], job["generation_replicate"],
            job["plan"]["identity"]["project"], job["plan"]["identity"]["rubric"]) == (
                2, 1, "CM4AI", "rubric10-semantic")


def _verify_baseline(job):
    for kind in ("plan", "receipt"):
        require(sha(read_bytes(job[f"baseline_{kind}_path"])) == job[f"baseline_{kind}_sha256"],
                "baseline evidence changed")
    baseline = read_json(job["baseline_plan_path"])
    _accepted(baseline, job["baseline_plan_path"], job["baseline_receipt_path"])
    verify_plan_identity(job["plan"], baseline)


def _manifest_value(job, receipt, raw):
    plan = job["plan"]
    return {"status": "EXPORTED_VALIDATED_REPEAT", "source_head": SCORER_HEAD,
            "orchestration": _orchestration(),
            "scoring_replicate": job["scoring_replicate"], "generation_replicate": job["generation_replicate"],
            "identity": plan["identity"], "baseline_plan": job["baseline_plan_path"],
            "baseline_plan_sha256": job["baseline_plan_sha256"],
            "baseline_receipt": job["baseline_receipt_path"],
            "baseline_receipt_sha256": job["baseline_receipt_sha256"],
            "actual_plan": str(Path(plan["run_directory"]) / "plan.json"),
            "actual_plan_sha256": sha(read_bytes(Path(plan["run_directory"]) / "plan.json")),
            "actual_receipt": str(Path(plan["run_directory"]) / "receipt.json"),
            "actual_receipt_sha256": sha(read_bytes(Path(plan["run_directory"]) / "receipt.json")),
            "source_output": plan["output"], "source_output_sha256": sha(raw),
            "destination": job["destination"], "destination_sha256": sha(raw),
            "prompt_sha256": plan["prompt_sha256"], "prompt_equals_run1": True,
            "log_root": plan["run_directory"], "session_logs": receipt["evaluation_model"]["session_logs"],
            "copy_validator_exit": 0}


def _verified_skip(job, manifest_path):
    require(_canary(job), "only the accepted repeat canary may be skipped")
    require(physical(manifest_path) == physical(job["manifest_path"]), "canary manifest path differs")
    require(not (physical(manifest_path).parent / "failure.json").exists(), "canary export has refusal evidence")
    _verify_baseline(job)
    plan = job["plan"]
    _checkout(plan["repo_root"])
    scorer = _load_scorer(plan["repo_root"])
    in_checkout(plan["repo_root"], scorer.check_inputs, plan)
    receipt, raw = _accepted(plan, Path(plan["run_directory"]) / "plan.json",
                             Path(plan["run_directory"]) / "receipt.json")
    require(read_bytes(job["destination"]) == raw, "canary export bytes differ")
    require(read_json(manifest_path) == _manifest_value(job, receipt, raw), "canary export manifest differs")


def build_batch(args):
    roots = {rep: physical(getattr(args, f"scoring_root_{rep}")) for rep in (2, 3)}
    require(roots[2] != roots[3], "scoring replicates require distinct checkouts")
    for root in roots.values():
        _checkout(root)
    runs = physical(args.runs_root)
    publication = physical(args.publication_root)
    require(all(runs != root and root not in runs.parents for root in (*roots.values(), publication)),
            "runs root must be outside the checkouts and publication repository")
    baselines = _baseline_runs(args.baseline_runs)
    jobs = []
    accepted_canary_job = None
    orchestration = _orchestration()
    for scoring_rep in (2, 3):
        root = roots[scoring_rep]
        scorer = _load_scorer(root)
        for (generation_rep, project, family), baseline in sorted(baselines.items()):
            selected = not ((args.scoring_replicate is not None and args.scoring_replicate != scoring_rep)
                            or (args.generation_replicate is not None and args.generation_replicate != generation_rep)
                            or (args.project is not None and args.project != project)
                            or (args.rubric is not None and args.rubric != family))
            skip = bool(args.accepted_canary and (scoring_rep, generation_rep, project, family) ==
                        (2, 1, "CM4AI", "rubric10"))
            if not selected and not skip:
                continue
            label = LABEL_PREFIX + str(generation_rep)
            job_id = f"scoring_rep{scoring_rep}__{label}__{project}__{family}"
            run = physical(runs / job_id)
            export = physical(runs / "export-manifests" / job_id)
            argv = ["--repo-root", str(root), "--method-directory", METHOD, "--label", label,
                    "--record", str(root / "data/d4d_concatenated" / METHOD / label / f"{project}_d4d.yaml"),
                    "--rubric", family + "-semantic", "--semantic-version", "6.0", "--scope-context",
                    str(root / "data/evaluation_scope/2026-11-25c" / label / f"{project}.scope.json"),
                    "--run-directory", str(run), "--codex-binary", str(args.codex_binary),
                    "--poetry-binary", str(args.poetry_binary), "--validation-venv", str(args.validation_venv),
                    "--auth-file", str(args.auth_file), "--timeout", str(args.timeout)]
            if skip:
                plan = read_json(run / "plan.json")
                require(physical(plan["repo_root"]) == root and physical(plan["run_directory"]) == run,
                        "captured canary plan names another checkout or run")
                expected_output = (root / "data/evaluation_llm" / (family + "_semantic") /
                                   "label_aware" / INSTRUMENT / f"{project}_{label}_evaluation.json")
                require(physical(plan["output"]) == expected_output
                        and physical(plan["runner"]) == root / RUNNER
                        and physical(plan["working_directory"]) == run / "working"
                        and physical(plan["codex_home"]) == run / "codex-home",
                        "captured canary publication or runtime paths differ")
            else:
                plan = in_checkout(root, scorer.build_plan, scorer.parser().parse_args([*argv, "--plan"]))
            verify_plan_identity(plan, baseline["plan"])
            job = {"id": job_id, "scoring_replicate": scoring_rep, "generation_replicate": generation_rep,
                   "plan": plan, "scorer_argv": argv, "baseline_plan_path": baseline["plan_path"],
                   "baseline_receipt_path": baseline["receipt_path"],
                   "baseline_plan_sha256": baseline["plan_sha256"],
                   "baseline_receipt_sha256": baseline["receipt_sha256"],
                   "destination": str(_destination(publication, scoring_rep, plan["identity"])),
                   "export_directory": str(export), "manifest_path": str(export / "manifest.json"), "skip": skip,
                   "orchestration": orchestration}
            if skip:
                _verified_skip(job, args.accepted_canary)
                accepted_canary_job = job
            else:
                require(not physical(job["destination"]).exists(), "repeat destination already exists")
                require(not export.exists(), "repeat export attempt already exists")
            if selected:
                jobs.append(job)
    require(jobs, "no selected jobs")
    require(not args.accepted_canary or accepted_canary_job is not None, "accepted canary proof missing")
    require(len({job["id"] for job in jobs}) == len(jobs), "duplicate repeat job")
    return {"mode": "REPEAT_PLAN", "scorer_head": SCORER_HEAD, "job_count": len(jobs), "jobs": jobs,
            "orchestration": orchestration, "accepted_canary_job": accepted_canary_job}


class _ExportSignals:
    """Defer interruption until child/publication ownership is recorded."""

    def __init__(self):
        self.pending = None
        self.previous = {}
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, EXPORT_SIGNALS)
        try:
            for number in EXPORT_SIGNALS:
                self.previous[number] = signal.signal(number, self.record)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)

    def record(self, number, frame):
        if self.pending is None:
            self.pending = number

    def check(self):
        pending = set(signal.sigpending()).intersection(EXPORT_SIGNALS)
        number = self.pending or (min(pending) if pending else None)
        if number is not None:
            raise InterruptedError(f"repeat export interrupted by signal {number}")

    def _restore_handlers(self):
        for number, previous in self.previous.items():
            signal.signal(number, previous)
        self.previous.clear()

    def restore(self):
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, EXPORT_SIGNALS)
        try:
            self._restore_handlers()
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)

    def commit(self, failure):
        # Pending interruptions abort before completion. Signals arriving after
        # this commit point are delivered to the caller's original handlers.
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, EXPORT_SIGNALS)
        try:
            self.check()
            failure.unlink()
            self.check()
            self._restore_handlers()
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)


def _group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def _stop_validator(child):
    # Stop the entire session even if its leader exited before a descendant.
    for number in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(child.pid, number)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + EXPORT_STOP_GRACE
        while time.monotonic() < deadline:
            child.poll()
            if not _group_exists(child.pid):
                child.wait(timeout=EXPORT_STOP_GRACE)
                return
            time.sleep(0.05)
    child.wait(timeout=EXPORT_STOP_GRACE)
    require(not _group_exists(child.pid), "validator process group cleanup is unproven")


def _validate_staged(command, root, environment, export, control):
    child = None
    with (export / "validator.stdout.txt").open("xb") as stdout, (export / "validator.stderr.txt").open("xb") as stderr:
        try:
            control.check()
            child = subprocess.Popen(command, cwd=root, env=environment, stdout=stdout, stderr=stderr,
                                     start_new_session=True)
            deadline = time.monotonic() + EXPORT_VALIDATOR_TIMEOUT
            while True:
                control.check()
                status = child.poll()
                if status is not None:
                    return status
                if time.monotonic() >= deadline:
                    raise subprocess.TimeoutExpired(command, EXPORT_VALIDATOR_TIMEOUT)
                time.sleep(0.05)
        finally:
            if child is not None:
                _stop_validator(child)


def _export_refusal(export, destination, staged_identity, failure):
    # A racing existing destination belongs to its creator, never this export.
    cleanup_errors = []
    try:
        if staged_identity is not None and os.path.lexists(destination):
            current = destination.lstat()
            if (current.st_dev, current.st_ino) == staged_identity:
                destination.unlink()
    except OSError as exc:
        cleanup_errors.append(f"publication cleanup: {type(exc).__name__}: {exc}")
    manifest = export / "manifest.json"
    if manifest.exists():
        try:
            manifest.rename(export / "unaccepted-manifest.json")
        except OSError as exc:
            cleanup_errors.append(f"manifest retention: {type(exc).__name__}: {exc}")
    refused = export / "failure.json"
    if not refused.exists():
        os.link(export / "refusal-reserve.json", refused)
    failure.update(destination_exists=os.path.lexists(destination), cleanup_errors=cleanup_errors)
    # The already persisted refusal survives a full volume or a second signal.
    try:
        detail = export / "refusal-detail.json"
        write_json(detail, failure)
        os.replace(detail, refused)
    except OSError:
        pass


def export_job(job, args):
    control = _ExportSignals()
    export = None
    staged_identity = None
    try:
        plan = job["plan"]
        root, run = physical(plan["repo_root"]), physical(plan["run_directory"])
        destination = _destination(args.publication_root, job["scoring_replicate"], plan["identity"])
        require(destination == physical(job["destination"]), "repeat destination differs")
        require(not destination.exists(), "repeat destination already exists")
        candidate_export = physical(job["export_directory"])
        require(candidate_export == physical(args.runs_root) / "export-manifests" / job["id"], "export evidence path differs")
        require(physical(job["manifest_path"]) == candidate_export / "manifest.json", "export manifest path differs")
        require(physical(args.publication_root) not in candidate_export.parents,
                "export staging must be outside the publication repository")
        candidate_export.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        candidate_export.mkdir(mode=0o700, exist_ok=False)
        failure = {"status": "EXPORT_REFUSED", "failure": "export has not completed",
                   "source_head": SCORER_HEAD, "destination": str(destination), "run_directory": str(run)}
        write_json(candidate_export / "failure.json", failure)
        os.link(candidate_export / "failure.json", candidate_export / "refusal-reserve.json")
        export = candidate_export
        control.check()
        require(job.get("orchestration", _orchestration()) == _orchestration(), "orchestration helper changed")
        _checkout(root)
        _verify_baseline(job)
        scorer = _load_scorer(root)
        in_checkout(root, scorer.check_inputs, plan)
        receipt, raw = _accepted(plan, run / "plan.json", run / "receipt.json")
        control.check()
        staged = export / "staged-evaluation.json"
        with staged.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        require(read_bytes(staged) == raw, "staged repeat bytes differ")
        control.check()
        command = list(plan["validation_command"])
        require(command.count("--file") == 1, "unexpected validator file arguments")
        command[command.index("--file") + 1] = str(staged)
        venv = physical(plan["validation_venv"])
        environment = {"PATH": str(venv / "bin") + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       "HOME": str(run / "home"), "VIRTUAL_ENV": str(venv),
                       "POETRY_VIRTUALENVS_CREATE": "false", "PIP_NO_INDEX": "1",
                       "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        status = _validate_staged(command, root, environment, export, control)
        require(status == 0, "relocated exact-file validation failed; do not rerun scorer")
        require(read_bytes(staged) == raw, "staged export changed during validation")
        control.check()
        _verify_baseline(job)
        in_checkout(root, scorer.check_inputs, plan)
        final_receipt, final_raw = _accepted(plan, run / "plan.json", run / "receipt.json")
        require(final_receipt == receipt and final_raw == raw, "source publication changed during export")
        destination.parent.mkdir(parents=True, exist_ok=True)
        staged.chmod(0o400)
        info = staged.stat()
        staged_identity = info.st_dev, info.st_ino
        require(destination.parent.stat().st_dev == info.st_dev, "atomic export requires the same filesystem")
        control.check()
        # link is atomic and exclusive; no overwrite or cross-device fallback.
        # Handlers only record signals, so ownership cannot be lost mid-syscall.
        os.link(staged, physical(destination), follow_symlinks=False)
        control.check()
        require(sha(read_bytes(destination)) == sha(raw), "published repeat differs from validated bytes")
        manifest = _manifest_value(job, receipt, raw)
        write_json(job["manifest_path"], manifest)
        control.check()
        control.commit(export / "failure.json")
        return manifest
    except BaseException as exc:
        if export is not None:
            failure.update(failure=f"{type(exc).__name__}: {exc}", signal=control.pending)
            _export_refusal(export, destination, staged_identity, failure)
        raise
    finally:
        control.restore()


def execute_batch(batch, args):
    require(args.authorization_reference and args.authorization_reference.strip(), "execution needs separate authorization")
    jobs = batch["jobs"]
    require(len(jobs) == 1 or (len(jobs) == 20 and args.generation_replicate in (1, 2, 3)),
            "execute exactly one selected job or one twenty-job generation stream")
    require(batch["orchestration"] == _orchestration(), "orchestration helper changed since plan")
    canary = batch.get("accepted_canary_job")
    # Issue 6374: every stream, including streams without the canary row,
    # needs proof of the same end-to-end canary before any paid launch.
    require((len(jobs) == 1 and _canary(jobs[0])) or canary is not None,
            "non-canary execution requires the accepted repeat canary")
    if canary is not None:
        _verified_skip(canary, args.accepted_canary)
    physical(args.runs_root).mkdir(mode=0o700, parents=True, exist_ok=True)
    exported = []
    for job in jobs:
        require(batch["orchestration"] == _orchestration(), "orchestration helper changed during stream")
        root = physical(job["plan"]["repo_root"])
        _checkout(root)
        _verify_baseline(job)
        if job["skip"]:
            _verified_skip(job, args.accepted_canary)
            exported.append({"id": job["id"], "status": "VERIFIED_CANARY_ALREADY_EXPORTED"})
            continue
        require(not physical(job["destination"]).exists(), "repeat destination appeared before launch")
        require(not physical(job["export_directory"]).exists(), "repeat export attempt already exists")
        scorer = _load_scorer(root)
        current = in_checkout(root, scorer.build_plan,
                              scorer.parser().parse_args([*job["scorer_argv"], "--plan"]))
        require(current == job["plan"], "preflight plan changed before launch")
        # main, rather than execute, owns the unchanged bounded signal cleanup.
        rc = in_checkout(root, scorer.main, [*job["scorer_argv"], "--execute", "--authorization-reference",
                                             args.authorization_reference])
        require(rc == 0, "scorer failed; stream stopped without retry")
        exported.append(export_job(job, args))
    return {"status": "SELECTED_REPEAT_JOBS_COMPLETE", "source_head": SCORER_HEAD,
            "job_count": len(jobs), "results": exported}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("scoring-root-2", "scoring-root-3", "baseline-runs", "publication-root", "runs-root",
                 "validation-venv", "auth-file"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--codex-binary", required=True)
    p.add_argument("--poetry-binary", required=True)
    p.add_argument("--generation-replicate", type=int, choices=(1, 2, 3))
    p.add_argument("--scoring-replicate", type=int, choices=(2, 3))
    p.add_argument("--project", choices=PROJECTS)
    p.add_argument("--rubric", choices=RUBRICS)
    p.add_argument("--accepted-canary", type=Path)
    p.add_argument("--authorization-reference")
    p.add_argument("--timeout", type=int, default=3600)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--execute", action="store_true")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        require(0 < args.timeout <= 7200, "timeout must be 1 through 7200 seconds")
        batch = build_batch(args)
        result = batch if args.plan else execute_batch(batch, args)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
