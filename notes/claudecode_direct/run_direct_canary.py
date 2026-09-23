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
import re
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
#: A job id is one path component of the preparer's shape (#2252): it names
#: the attempt directory and nothing else may.
JOB_ID = preparation.JOB_ID
LIMIT_KEYS = ("contextWindow", "maxOutputTokens")
DECIMAL = re.compile(r"[0-9]+(\.[0-9]+)?")


def is_hex(text, length):
    return isinstance(text, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", text) is not None


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
        provider=preparation.PROVIDER, reasoning_effort=preparation.EFFORT, prompt_text_env=True)


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
    limits = model.get("limits_expected")
    if (not isinstance(limits, dict) or set(limits) != set(LIMIT_KEYS)
            or not all(type(value) is int and value > 0 for value in limits.values())):
        raise BudgetStop("registration does not state the expected runtime limits")
    runtime = registration["native_runtime"]
    if runtime["environment"] != preparation.CHILD_ENVIRONMENT:
        raise BudgetStop("the registered child environment differs from the preparer's")
    if runtime.get("forbidden_environment") != list(preparation.FORBIDDEN_ENVIRONMENT):
        raise BudgetStop("the registered forbidden environment differs from the preparer's")
    if runtime["cli_flags"] != preparation.CLI_FLAGS + ["--effort", preparation.EFFORT]:
        raise BudgetStop("the registered CLI flags differ from the preparer's")
    if runtime["expected_api_key_source"] != "none":
        raise BudgetStop("the direct arm expects a login, not a key")
    if Path(str(runtime.get("system_prompt"))).resolve() != (HERE / "system.md").resolve():
        raise BudgetStop("the registered system prompt is not the direct arm's system.md")   # #2264
    if runtime.get("executable") not in registration["pinned_files"]:
        raise BudgetStop("the registered executable is not pinned")                          # #2263
    generation = registration["generation"]
    deadline = generation.get("attempt_deadline_seconds")
    if type(deadline) is not int or deadline <= 0:
        raise BudgetStop("the registered attempt deadline is not a positive integer")        # #2273
    guard = generation.get("runaway_budget_guard_usd")
    if not isinstance(guard, str) or not DECIMAL.fullmatch(guard) or float(guard) <= 0:
        raise BudgetStop("the registered runaway guard is not a positive decimal string")    # #2273
    for job in registration["generation"]["jobs"]:
        if not isinstance(job.get("id"), str) or not JOB_ID.fullmatch(job["id"]):
            raise BudgetStop("a registered job id is not a single path component")
        # The job, not only the arm block, must be the direct arm's (#2205):
        # the job's fields drive the instruction and every write.
        if (job["method"], job["runtime"], job["execution_arm"]) != (
                preparation.METHOD, preparation.RUNTIME, preparation.EXECUTION_ARM):
            raise BudgetStop("a registered job belongs to another arm")
        if not job["output_directories"]:
            raise BudgetStop("a registered job names no output directory")
        targets = list(job["output_directories"]) + list(job["outputs"].values())
        if not all(under_direct_roots(p) for p in targets):
            raise BudgetStop("a registered job would write outside the direct arm's directories")
        if job["render_spec"].get("reasoning_effort") != preparation.EFFORT:
            raise BudgetStop("a registered job does not assert the registered effort")
        if job["render_spec"].get("prompt_text_env") is not True:
            # A recorder line with a shell expansion cannot run under dontAsk (#2282).
            raise BudgetStop("a registered job's recorder line does not read the launch instruction by --prompt-text-env")
    for file, expected in registration["pinned_files"].items():
        if not Path(file).is_file() or sha(file) != expected:
            raise BudgetStop(f"a registered pin changed: {Path(file).name}")


def verify_environment():
    present = [name for name in preparation.FORBIDDEN_ENVIRONMENT if os.environ.get(name)]
    if present:
        raise BudgetStop("the direct arm refuses provider keys or redirection in its environment: " + ", ".join(present))


def observed_efforts(control_log):
    """Every effort level the runtime reported on a tool callback (#2208).
    A line that is not a decision record, or not a mapping at any level, is
    skipped like an undecodable one (#2250)."""
    levels = set()
    with Path(control_log).open("rb") as handle:
        for raw in handle:
            try:
                record = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            if not isinstance(record, dict) or record.get("kind") != "decision":
                continue
            request = record.get("request")
            inner = request.get("request") if isinstance(request, dict) else None
            inputs = inner.get("input") if isinstance(inner, dict) else None
            effort = inputs.get("effort") if isinstance(inputs, dict) else None
            if isinstance(effort, dict) and isinstance(effort.get("level"), str):
                levels.add(effort["level"])
            elif isinstance(effort, str):
                levels.add(effort)
    return sorted(levels)


def _events(path):
    """Decoded JSON objects of a JSON-lines file, one per line; a line that
    does not decode to an object, or nests too deep to decode, is skipped
    (#2340)."""
    with Path(path).open("rb") as handle:
        for number, raw in enumerate(handle, 1):
            try:
                event = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError, RecursionError):
                continue
            if isinstance(event, dict):
                yield number, event


def rate_limits(transcript):
    """What the runtime reported about the subscription's rate-limit windows
    (#2283): per window the first, last and highest utilization, each with the
    reset it was reported against, so a window that resets mid-run is not
    paired across the reset (#2335). Never raises: a diagnostic must not
    displace the stop it sits beside."""
    out = {"events": 0, "windows": {}, "statuses": [], "overage_used": False}
    try:
        for _, event in _events(transcript):
            if event.get("type") != "rate_limit_event":
                continue
            info = event.get("rate_limit_info")
            if not isinstance(info, dict):
                continue
            out["events"] += 1
            if isinstance(info.get("status"), str) and info["status"] not in out["statuses"]:
                out["statuses"].append(info["status"])
            out["overage_used"] = out["overage_used"] or info.get("isUsingOverage") is True
            windows = dict(info["unifiedWindows"]) if isinstance(info.get("unifiedWindows"), dict) else {}
            if isinstance(info.get("rateLimitType"), str) and info["rateLimitType"] not in windows:
                windows[info["rateLimitType"]] = info
            for name, window in windows.items():
                if not isinstance(name, str) or not isinstance(window, dict):
                    continue
                utilization = window.get("utilization")
                if type(utilization) not in (int, float):
                    continue
                reading = {"utilization": utilization,
                           "resets_at": window["resetsAt"] if type(window.get("resetsAt")) is int else None}
                entry = out["windows"].setdefault(name, {"first": reading, "last": reading, "max": reading})
                entry["last"] = reading
                if utilization > entry["max"]["utilization"]:
                    entry["max"] = reading
    except FileNotFoundError:
        return {**out, "note": "no transcript"}
    except Exception as error:
        return {**out, "note": f"transcript unreadable: {type(error).__name__}"}
    return out


def child_outcome(transcript, control_log, exit_code=None):
    """Whether the child itself completed, by the launcher's own completion
    predicate (#2337), and which tool calls no control decision covers, named
    by id and transcript line (#2338). Never raises; a scan that cannot finish
    reports `uncovered_tool_calls: None` with `child_outcome_note` (#2340)."""
    out = {"child_completed": False, "result_subtype": None, "terminal_reason": None, "stop_reason": None,
           "uncovered_tool_calls": []}
    try:
        events = list(_events(transcript))
        results = [event for _, event in events if event.get("type") == "result"]
        if len(results) == 1:
            final = results[0]
            out.update(result_subtype=final.get("subtype"), terminal_reason=final.get("terminal_reason"),
                       stop_reason=final.get("stop_reason"))
            out["child_completed"] = (final.get("is_error") is False and final.get("terminal_reason") == "completed"
                                      and final.get("stop_reason") == "end_turn" and exit_code in (None, 0))
        decided, rejected = set(), set()
        try:
            for _, record in _events(control_log):
                if record.get("kind") == "decision":
                    request = record.get("request")
                    inner = request.get("request") if isinstance(request, dict) else None
                    data = inner.get("input") if isinstance(inner, dict) else None
                    if isinstance(data, dict) and isinstance(data.get("tool_use_id"), str):
                        decided.add(data["tool_use_id"])
                elif record.get("kind") == "input_rejected_before_callback" and isinstance(record.get("tool_use_id"), str):
                    rejected.add(record["tool_use_id"])
        except FileNotFoundError:
            out["control_log_missing"] = True

        def blocks(event):
            message = event.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            return [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []
        answers = {}
        for _, event in events:
            for block in blocks(event):
                if block.get("type") == "tool_result" and isinstance(block.get("tool_use_id"), str):
                    content = block.get("content")
                    answers[block["tool_use_id"]] = content if isinstance(content, str) else json.dumps(content)
        for line, event in events:
            for block in blocks(event):
                identity = block.get("id")
                if (block.get("type") == "tool_use" and isinstance(identity, str)
                        and identity not in decided and identity not in rejected):
                    out["uncovered_tool_calls"].append({"tool_use_id": identity, "tool": block.get("name"),
                                                        "transcript_line": line,
                                                        "result_head": (answers.get(identity) or "")[:160]})
    except Exception as error:
        out["uncovered_tool_calls"] = None
        out["child_outcome_note"] = f"outcome unreadable: {type(error).__name__}"
    return out


def counted(entry, key):
    """A non-negative integer token count from a model-usage entry, else None."""
    value = entry.get(key) if isinstance(entry, dict) else None
    return value if type(value) is int and value >= 0 else None


def model_accounting(terminal, registration):
    """The registered model's usage, the auxiliary models' usage, and any
    model the registration does not permit (#2207). Presence is not enough
    (#2247): the registered model must carry the work, and no auxiliary
    model may carry more generation than it, which is what a main-loop
    fallback would look like."""
    usage = terminal.get("modelUsage")
    if not isinstance(usage, dict):
        raise BudgetStop("native terminal model accounting is missing")
    registered = registration["model"]["model"]
    permitted = set(registration["model"].get("auxiliary_models_permitted", []))
    if registered not in usage:
        raise BudgetStop("native terminal accounting does not name the registered model")
    own = usage[registered]
    if not isinstance(own, dict):
        raise BudgetStop("native terminal accounting for the registered model is not a mapping")
    read = [counted(own, key) for key in ("inputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")]
    generated = counted(own, "outputTokens")
    if generated is None or any(value is None for value in read):
        raise BudgetStop("native terminal accounting for the registered model is incomplete")
    if generated == 0 or sum(read) == 0:
        raise BudgetStop("native terminal accounting shows no work on the registered model")
    auxiliary = {name: value for name, value in usage.items() if name != registered}
    foreign = sorted(name for name in auxiliary if name not in permitted)
    if foreign:
        raise BudgetStop("native terminal accounting names a model the registration does not permit: " + ", ".join(foreign))
    for name, entry in sorted(auxiliary.items()):
        if not isinstance(entry, dict) or counted(entry, "outputTokens") is None:
            raise BudgetStop(f"native terminal accounting for an auxiliary model is incomplete: {name}")
        if counted(entry, "outputTokens") >= generated:
            raise BudgetStop(f"an auxiliary model carried at least as much generation as the registered model: {name}")
    if sum(counted(entry, "outputTokens") for entry in auxiliary.values()) >= generated:
        # Together, not one at a time (#2271).
        raise BudgetStop("the auxiliary models together carried at least as much generation as the registered model")
    return own, auxiliary


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
    # The binder's whole record, not four keys of it (#2245): the CI run it
    # names must be on the registered commit, and it must name a run and the
    # independent review it bound.
    if not is_hex(registration.get("code_commit"), 40) or review.get("ci_head") != registration["code_commit"]:
        raise BudgetStop("the review's CI evidence is not on the registered code commit")
    if (type(review.get("ci_run_id")) is not int or review["ci_run_id"] <= 0
            or not is_hex(review.get("independent_review_sha256"), 64)):
        raise BudgetStop("the review does not bind a CI run and an independent review")
    if word.get("registration_sha256") != registration_sha or not str(word.get("exact_response", "")).strip():
        raise BudgetStop("the maintainer's launch word for this exact registration is required")
    verify_environment()
    verify_registration(registration, registration_path)
    job = next((j for j in registration["generation"]["jobs"] if j["id"] == args.job), None)
    if job is None or not job["canary"]:
        raise BudgetStop("this launcher only runs registered direct-arm canaries")
    if any(Path(p).exists() for p in job["output_directories"]):
        raise BudgetStop("direct canary output already exists; never overwrite or resume")
    try:
        spec = spec_for(job)
        rendering, identity = spec.render_spec(), spec.input_identity()
    except (KeyError, ValueError, TypeError) as error:
        raise BudgetStop(f"the registered specification cannot be built: {error}") from error   # #2272
    if rendering != job["render_spec"] or identity != job["input_identity"]:
        raise BudgetStop("direct generation instruction or input identity changed")
    per_job = registration["per_job_environment"].get(job["id"])
    if not isinstance(per_job, dict):
        raise BudgetStop("the registered job environment is not a mapping")
    if per_job.get("D4D_LAUNCH_INSTRUCTION") != job["instruction"]:
        raise BudgetStop("provenance must read the exact registered launch instruction")
    # All three names are bound to the job, not only the instruction (#2265):
    # the profile and the manifest are what the recorder attests.
    if per_job != {"D4D_MANIFEST": job["manifest"], "D4D_PROFILE": job["profile"],
                   "D4D_LAUNCH_INSTRUCTION": job["instruction"]}:
        raise BudgetStop("the registered job environment must bind exactly the job's manifest, profile and launch instruction")
    try:
        command_policy = build_command_policy(job, registration["python"], registration["repository"])
    except (KeyError, OSError, ValueError, TypeError, SyntaxError) as error:
        # The same named stop the native launcher gives (#2251).
        raise BudgetStop(f"the registered command policy cannot be built: {error}") from error
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
               "executable_sha256": registration["pinned_files"][runtime["executable"]],
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
            # Named, because a 1M-context build reports itself as another
            # model (`claude-opus-5[1m]`, #2266) and the reader must see that.
            raise BudgetStop("native runtime initialization differs from registration: "
                             f"model {init.get('model')!r}, key source {init.get('apiKeySource')!r}, "
                             f"version {init.get('claude_code_version')!r}, tools {sorted(init.get('tools', []))} "
                             f"against {registration['model']['model']!r}, {runtime['expected_api_key_source']!r}, "
                             f"{runtime['version'].split()[0]!r}, ['Bash', 'Read', 'Write']")
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
        usage = terminal.get("usage")
        if not isinstance(usage, dict) or not all(
                type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")):
            raise BudgetStop("native terminal usage is incomplete")
        receipt["runtime_limits_observed"] = {key: registered_usage.get(key) for key in LIMIT_KEYS}
        # Whether the terminal's total and the per-model figures are meant to
        # agree in the runtime's accounting is not established: recorded,
        # not gated (#2271).
        per_model = sum(counted(entry, "outputTokens") for entry in [registered_usage, *auxiliary_usage.values()])
        receipt["accounting_reconciliation"] = {"terminal_output_tokens": usage["output_tokens"],
                                                "model_usage_output_tokens": per_model,
                                                "difference": usage["output_tokens"] - per_model}
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
                evidence_problem = (None if evidence["checked"] and not evidence["findings"]
                                    else "explicit evidence assertions failed" if evidence["checked"]
                                    else "explicit evidence assertions were not checked")
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
        # An unreported effort and a downgraded one are different findings (#2249).
        if not receipt["effort_observed"]:
            problems = list(problems) + [
                f"the runtime reported no effort on any tool callback; the registration asserts {registration['model']['effort']!r}"]
        elif receipt["effort_observed"] != [registration["model"]["effort"]]:
            problems = list(problems) + [
                f"the runtime reported effort {receipt['effort_observed']} where the registration asserts {registration['model']['effort']!r}"]
        if receipt["runtime_limits_observed"] != registration["model"]["limits_expected"]:
            # A different context window is a different instrument (#2246).
            problems = list(problems) + [
                f"the runtime reported limits {receipt['runtime_limits_observed']} where the registration expects "
                f"{registration['model']['limits_expected']}"]
        if not pair or not pair.get("ran"):
            problems = list(problems) + ["the full and core records were not checked for consistency"]
        elif not pair.get("consistent"):
            problems = list(problems) + ["the full and core records are not consistent"]
        receipt.update(validation_problems=problems, pair_consistency=pair, native_observed=observed,
                       runtime_reported_cost_usd=terminal.get("total_cost_usd"), runtime_usage=usage,
                       runtime_model_usage=registered_usage, auxiliary_model_usage=auxiliary_usage,
                       num_turns=terminal.get("num_turns"),
                       status="validation_failed" if problems else "completed_pending_independent_review")
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
            except (OSError, ValueError, TypeError):
                receipt["effort_observed"] = []
        if "permission_denials" in receipt:
            receipt["disqualifying_denials"] = native.denial_problems(receipt["permission_denials"])
        else:
            receipt.update(native.stopped_denials(attempt / "transcript.jsonl", classify))
        # Say whether the child itself completed and which calls no decision
        # covers (#2285). A disqualifying denial leads the receipt only where
        # the child completed and the controller stopped for missing evidence,
        # the case of the first canary; any other controller stop (a deadline,
        # a pin change, another model) is the run's cause and keeps the
        # headline, with the denials beside it (#2334).
        receipt.update(child_outcome(attempt / "transcript.jsonl", attempt / "control.jsonl", receipt.get("exit_code")))
        if (receipt.get("disqualifying_denials") and receipt.get("child_completed")
                and receipt.get("reason") == "native control session ended without complete evidence"):
            receipt["controller_reason"] = receipt.get("reason")
            receipt["controller_reason_source"] = receipt.get("reason_source")
            receipt["reason"] = "disqualified: " + receipt["disqualifying_denials"][0]
            receipt["reason_source"] = "denial"
        native.retain_traceback(attempt, exc)
    finally:
        receipt["rate_limits"] = rate_limits(attempt / "transcript.jsonl")
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
