"""Launch one registered direct-arm generation canary (#2202).

Claude Code on the maintainer's Claude subscription, direct to Anthropic. The
controls that hook the runtime are reused unchanged from the native controls:
the pre-execution command and file policies, the phase history, the denial
classifier, the transcript diagnostics, the observer and every record and
receipt gate. Nothing meters the provider: there is no proxy and no ledger,
and the receipt carries the runtime's own terminal accounting instead.

Every check runs before the attempt directory exists, so a refusal never
consumes the job identity (#2206). The child's environment is built from the
preparer's constants and screened wherever its values come from (#2204); the
job's method, runtime and output directories must be the direct arm's, so no
registration can write into another arm (#2205); the runtime's auxiliary
model is recorded rather than failing the run (#2207); and the effort the
runtime reports on every tool callback is compared with the registered
effort (#2208).
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTROLS = ROOT / "notes" / "matched_cborg_2026-09-13"
sys.path[:0] = [str(ROOT / "src"), str(CONTROLS), str(CONTROLS / "native_controls")]

from budgeted_cborg import BudgetStop, write_new                       # noqa: E402
from native_command_policy import build_command_policy, command_guidance, permission_arguments  # noqa: E402
from native_control import check_control_history, load_native_events, digest as control_digest  # noqa: E402
from native_phase_history import phase_history                        # noqa: E402
import run_native_canary as native                                    # noqa: E402
from run_api_canary import sha, check_canary_receipts                 # noqa: E402
import prepare_direct as preparation                                  # noqa: E402

DIRECT_ROOTS = ("data/d4d_concatenated/claudecode_direct/", "data/d4d_concatenated/claudecode_direct_core/")


def now():
    return datetime.now(timezone.utc).isoformat()


class NoProxy:
    """What `execute_child` needs from a transport, for a run that has none.

    The runtime talks to Anthropic itself. This object only carries the
    controller's own stop state, so a deadline or an unexpected error is
    recorded on the receipt the same way as in the proxied arms."""
    def __init__(self):
        self.state = threading.Condition(threading.RLock())
        self.failed = threading.Event()
        self.failure = None
        self.closed = False
        self.unfinished_handlers = 0

    def close_admission(self):
        with self.state:
            self.closed = True


def spec_for(job):
    from data_sheets_schema import api_runner
    return api_runner.RunSpec(
        project=job["project"], arm="baseline", method=job["method"], bundle=Path(job["bundle"]),
        label=job["label"], condition=job["render_spec"]["condition"], manifest=Path(job["manifest"]),
        chunk_manifest=Path(job["chunks"]), profile=job["profile"], profile_basis="stated by the registered caller",
        render_version=job["render_version"], run_date=job["run_date"], runtime=job["runtime"],
        provider=preparation.PROVIDER, reasoning_effort=preparation.EFFORT)


def under_direct_roots(path):
    text = str(path)
    return not Path(text).is_absolute() and ".." not in Path(text).parts and text.startswith(DIRECT_ROOTS)


def verify_registration(registration, path):
    """Everything about the registration that must hold, before and after the run."""
    if registration.get("kind") != "d4d_direct_arm_registration" or registration.get("schema_version") != 1:
        raise BudgetStop("not a direct-arm registration")
    if Path(registration["repository"]).resolve() != ROOT or Path.cwd().resolve() != ROOT:
        raise BudgetStop("the direct arm runs from the checkout its registration names")
    if preparation.git_head(ROOT) != registration["code_commit"]:
        raise BudgetStop("the checkout is not at the registered code commit")
    if sys.executable != registration["python"]:
        raise BudgetStop("the registered Python differs from the launcher's")
    arm = registration["arm"]
    if (arm["method"], arm["runtime"], arm["provider"], arm["execution_arm"]) != (
            preparation.METHOD, preparation.RUNTIME, preparation.PROVIDER, preparation.EXECUTION_ARM):
        raise BudgetStop("registration names another arm")
    model = registration["model"]
    if model["model"] != preparation.MODEL or model["effort"] != preparation.EFFORT:
        raise BudgetStop("registration names another model or effort")
    if set(model.get("auxiliary_models_permitted", [])) != set(preparation.AUXILIARY_MODELS):
        raise BudgetStop("registration names other auxiliary models")
    runtime = registration["native_runtime"]
    if runtime["environment"] != preparation.CHILD_ENVIRONMENT:
        raise BudgetStop("the registered child environment differs from the preparer's")
    if runtime["cli_flags"] != preparation.CLI_FLAGS + ["--effort", preparation.EFFORT]:
        raise BudgetStop("the registered CLI flags differ from the preparer's")
    if runtime["expected_api_key_source"] != "none":
        raise BudgetStop("the direct arm expects a login, not a key")
    for job in registration["generation"]["jobs"]:
        # The job, not only the arm block, must be the direct arm's (#2205):
        # the job's fields drive the instruction and every write.
        if (job["method"], job["runtime"], job["execution_arm"]) != (
                preparation.METHOD, preparation.RUNTIME, preparation.EXECUTION_ARM):
            raise BudgetStop("a registered job belongs to another arm")
        targets = list(job["output_directories"]) + list(job["outputs"].values())
        if not job["output_directories"] or not all(under_direct_roots(p) for p in targets):
            raise BudgetStop("a registered job would write outside the direct arm's directories")
        if job["render_spec"].get("reasoning_effort") != preparation.EFFORT:
            raise BudgetStop("a registered job does not assert the registered effort")
    for file, expected in registration["pinned_files"].items():
        if not Path(file).is_file() or sha(file) != expected:
            raise BudgetStop(f"a registered pin changed: {Path(file).name}")


def verify_environment():
    present = [name for name in preparation.FORBIDDEN_ENVIRONMENT if os.environ.get(name)]
    if present:
        raise BudgetStop("the direct arm refuses provider keys or redirection in its environment: " + ", ".join(present))


def observed_efforts(control_log):
    """Every effort level the runtime reported on a tool callback (#2208)."""
    levels = set()
    with Path(control_log).open("rb") as handle:
        for raw in handle:
            try:
                record = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            if record.get("kind") != "decision":
                continue
            effort = (((record.get("request") or {}).get("request") or {}).get("input") or {}).get("effort")
            if isinstance(effort, dict) and isinstance(effort.get("level"), str):
                levels.add(effort["level"])
            elif isinstance(effort, str):
                levels.add(effort)
    return sorted(levels)


def model_accounting(terminal, registration):
    """The registered model's usage, the auxiliary models' usage, and any
    model the registration does not permit (#2207)."""
    usage = terminal.get("modelUsage") or {}
    registered = registration["model"]["model"]
    permitted = set(registration["model"].get("auxiliary_models_permitted", []))
    if registered not in usage:
        raise BudgetStop("native terminal accounting does not name the registered model")
    auxiliary = {name: value for name, value in usage.items() if name != registered}
    foreign = sorted(name for name in auxiliary if name not in permitted)
    if foreign:
        raise BudgetStop("native terminal accounting names a model the registration does not permit: " + ", ".join(foreign))
    return usage[registered], auxiliary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True, help="the independent review and CI binding")
    parser.add_argument("--job", required=True)
    parser.add_argument("--launch-word", type=Path, required=True,
                        help="the maintainer's recorded launch instruction for exactly this registration")
    args = parser.parse_args(argv)
    registration_path = args.registration.resolve()
    registration = json.loads(registration_path.read_bytes())
    registration_sha = sha(registration_path)
    review = json.loads(args.review.read_bytes())
    word = json.loads(args.launch_word.read_bytes())
    if (review.get("verdict") != "approve" or review.get("ci_conclusion") != "success"
            or review.get("registration_sha256") != registration_sha or args.job not in review.get("allowed_jobs", [])):
        raise BudgetStop("this registration and job need independent approval and CI")
    if word.get("registration_sha256") != registration_sha or not str(word.get("exact_response", "")).strip():
        raise BudgetStop("the maintainer's launch word for this exact registration is required")
    verify_environment()
    verify_registration(registration, registration_path)
    job = next((j for j in registration["generation"]["jobs"] if j["id"] == args.job), None)
    if job is None or not job["canary"]:
        raise BudgetStop("this launcher only runs registered direct-arm canaries")
    if any(Path(p).exists() for p in job["output_directories"]):
        raise BudgetStop("direct canary output already exists; never overwrite or resume")
    spec = spec_for(job)
    if spec.render_spec() != job["render_spec"] or spec.input_identity() != job["input_identity"]:
        raise BudgetStop("direct generation instruction or input identity changed")
    per_job = registration["per_job_environment"][job["id"]]
    if per_job.get("D4D_LAUNCH_INSTRUCTION") != job["instruction"]:
        raise BudgetStop("provenance must read the exact registered launch instruction")
    command_policy = build_command_policy(job, registration["python"], registration["repository"])
    if registration["per_job_command_policy"].get(job["id"]) != command_policy:
        raise BudgetStop("the command policy differs from the registered job")
    runtime = registration["native_runtime"]
    executable = Path(runtime["executable"])
    if not executable.is_absolute() or executable.resolve(strict=True) != executable:
        raise BudgetStop("native executable must be an absolute resolved path")
    if subprocess.check_output([str(executable), "--version"], text=True).strip() != runtime["version"]:
        raise BudgetStop("native runtime version changed")
    here = registration_path.parent
    attempt = here / "attempts" / args.job
    if attempt.exists():
        raise BudgetStop("this attempt identity is consumed; register afresh")
    # The login is checked in the child's exact environment, in a throwaway
    # configuration directory, before anything of the attempt exists (#2206).
    probe_config = Path(tempfile.mkdtemp(prefix="direct-auth-probe-", dir=here))
    try:
        auth = preparation.auth_evidence(str(executable), preparation.child_environment(
            probe_config, runtime["environment"], per_job))
    finally:
        shutil.rmtree(probe_config, ignore_errors=True)
    attempt.mkdir(parents=True, exist_ok=False)
    config = attempt / "cli_config"
    config.mkdir(mode=0o700)
    env = preparation.child_environment(config, runtime["environment"], per_job)
    env.update(PYTHONPATH=str(ROOT / "src"), VIRTUAL_ENV=sys.prefix)
    system_prompt = Path(runtime["system_prompt"]).read_text(encoding="utf-8") + command_guidance(command_policy)
    argv_child = [str(executable), *runtime["cli_flags"], "--model", registration["model"]["model"], "--name", job["id"],
                  "--max-budget-usd", registration["generation"]["runaway_budget_guard_usd"],
                  *permission_arguments(command_policy), "--system-prompt", system_prompt]
    receipt = {"job": job["id"], "registration_sha256": registration_sha, "review_sha256": sha(args.review),
               "launch_word_sha256": sha(args.launch_word), "started_at": now(), "status": "incomplete",
               "launch_commit": registration["code_commit"], "arm": registration["arm"],
               "model": registration["model"], "auth": auth,
               "instruction_sha256": sha(job["instruction"]), "system_sha256": sha(runtime["system_prompt"]),
               "control_policy_sha256": control_digest(command_policy),
               "effective_system_sha256": hashlib.sha256(system_prompt.encode("utf-8")).hexdigest(),
               "child_environment_names": sorted(env)}
    write_new(attempt / "started.json", receipt)
    runtime_reads = []
    proxy = NoProxy()

    def classify(denials):
        return native.classify_denials(denials, instruction_text=Path(job["instruction"]).read_text(encoding="utf-8"),
                                       python=registration["python"], repository=registration["repository"],
                                       output_directories=job["output_directories"],
                                       readable_inputs=native.registered_reads(job) + runtime_reads,
                                       command_policy=command_policy)
    try:
        receipt["exit_code"] = native.execute_child(
            argv_child, proxy=proxy, instruction=job["instruction"], attempt=attempt, cwd=registration["repository"],
            env=env, deadline_seconds=registration["generation"]["attempt_deadline_seconds"],
            command_policy=command_policy, phase_spec=spec,
            verify_launch=lambda: verify_registration(registration, registration_path),
            record_stop=lambda reason: receipt.update(controller_stop=reason))
        events = load_native_events(attempt / "transcript.jsonl")
        initializers = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
        finals = [e for e in events if e.get("type") == "result"]
        if len(initializers) != 1 or len(finals) != 1:
            raise BudgetStop("native runtime initialization or terminal result is missing or ambiguous")
        init, terminal = initializers[0], finals[0]
        if (init.get("model") != registration["model"]["model"]
                or init.get("apiKeySource") != runtime["expected_api_key_source"]
                or init.get("claude_code_version") != runtime["version"].split()[0]
                or set(init.get("tools", [])) != {"Read", "Write", "Bash"}):
            raise BudgetStop("native runtime initialization differs from registration")
        receipt["pretool_control"] = check_control_history(events, attempt / "control.jsonl", command_policy,
                                                           native._classify_command, config)
        runtime_reads[:] = receipt["pretool_control"].get("persisted_output_paths", [])
        receipt["permission_denials"] = classify(terminal.get("permission_denials"))
        receipt["command_history"] = native.command_history(events, command_policy, receipt["permission_denials"])
        if spec.render_version >= 13:
            receipt["phase_history"] = phase_history(events, spec, complete=True, repository=registration["repository"],
                                                     command_policy=command_policy)
        receipt["effort_observed"] = observed_efforts(attempt / "control.jsonl")
        if (receipt["exit_code"] or terminal.get("is_error") or terminal.get("terminal_reason") != "completed"
                or terminal.get("stop_reason") != "end_turn"):
            raise BudgetStop("native attempt failed or stopped before completion")
        registered_usage, auxiliary_usage = model_accounting(terminal, registration)
        # The runtime's own accounting stands in for the ledger. It must be
        # complete; its cost figure is the runtime's estimate and is kept
        # as such.
        usage = terminal.get("usage") or {}
        if not all(type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")):
            raise BudgetStop("native terminal usage is incomplete")
        if not all(Path(p).is_file() for p in job["outputs"].values()):
            raise BudgetStop("native generation did not produce every registered artifact")
        from data_sheets_schema import api_runner, agentic_observed
        problems = api_runner.validate_outputs(spec)
        pair = api_runner.pair_consistency(spec)
        receipt_check = check_canary_receipts(spec, job["input_identity"])
        receipt["receipt_acceptance"] = receipt_check
        if not receipt_check["passed"]:
            problems = list(problems) + ["coverage receipt acceptance failed"]
        if spec.render_version >= 9:
            try:
                evidence = native.native_evidence_check(spec)
                evidence_problem = None if evidence["checked"] and not evidence["findings"] else "explicit evidence assertions failed"
            except Exception as error:
                evidence = {"checked": False, "error_type": type(error).__name__}
                evidence_problem = f"explicit evidence assertions could not be checked ({type(error).__name__})"
            receipt["evidence_assertions"] = evidence
            if evidence_problem:
                problems = list(problems) + [evidence_problem]
        observed = agentic_observed.observe([attempt / "transcript.jsonl"], Path(job["bundle"]))
        problems = (list(problems) + native.observation_problems(observed) + native.denial_problems(receipt["permission_denials"])
                    + receipt["command_history"]["problems"] + receipt["pretool_control"]["problems"]
                    + receipt.get("phase_history", {}).get("problems", []))
        if receipt["effort_observed"] != [registration["model"]["effort"]]:
            problems = list(problems) + [
                f"the runtime reported effort {receipt['effort_observed']} where the registration asserts {registration['model']['effort']!r}"]
        receipt.update(validation_problems=problems, pair_consistency=pair, native_observed=observed,
                       runtime_reported_cost_usd=terminal.get("total_cost_usd"), runtime_usage=usage,
                       runtime_model_usage=registered_usage, auxiliary_model_usage=auxiliary_usage,
                       num_turns=terminal.get("num_turns"),
                       status="validation_failed" if problems or not pair or not pair.get("ran") or not pair.get("consistent")
                       else "completed_pending_independent_review")
        verify_registration(registration, registration_path)
    except BaseException as exc:
        receipt.update(status="stopped", error_type=type(exc).__name__)
        # No ledger to consult: the controller's own stop is the only source.
        receipt.update(native.stop_explanation(exc, here / "no-ledger.json", args.job, proxy.failure))
        receipt.update(native.transcript_terminal_state(attempt / "transcript.jsonl"))
        if "pretool_control" not in receipt:
            try:
                stopped_events = load_native_events(attempt / "transcript.jsonl")
                receipt["pretool_control"] = check_control_history(stopped_events, attempt / "control.jsonl",
                                                                   command_policy, native._classify_command, config)
                runtime_reads[:] = receipt["pretool_control"].get("persisted_output_paths", [])
            except (OSError, ValueError, TypeError):
                receipt["pretool_control"] = {"checked": False, "problems": ["stopped native transcript is unreadable"]}
        if spec.render_version >= 13 and "phase_history" not in receipt:
            try:
                receipt["phase_history"] = phase_history(load_native_events(attempt / "transcript.jsonl"), spec, complete=False,
                                                         repository=registration["repository"], command_policy=command_policy)
            except (OSError, ValueError, TypeError):
                receipt["phase_history"] = {"checked": False, "problems": ["stopped native phase history is unreadable"]}
        if "effort_observed" not in receipt:
            try:
                receipt["effort_observed"] = observed_efforts(attempt / "control.jsonl")
            except OSError:
                receipt["effort_observed"] = []
        if "permission_denials" in receipt:
            receipt["disqualifying_denials"] = native.denial_problems(receipt["permission_denials"])
        else:
            receipt.update(native.stopped_denials(attempt / "transcript.jsonl", classify))
        native.retain_traceback(attempt, exc)
    finally:
        receipt.update(finished_at=now(),
                       artifacts={str(p): sha(p) for folder in job["output_directories"]
                                  for p in sorted(Path(folder).rglob("*")) if p.is_file()})
        write_new(attempt / "result.json", receipt)
        print(json.dumps({k: v for k, v in receipt.items()
                          if k not in {"artifacts", "validation_problems", "pair_consistency", "native_observed",
                                       "runtime_model_usage", "auxiliary_model_usage", "child_environment_names"}}, indent=2))
    return 0 if receipt["status"] == "completed_pending_independent_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
