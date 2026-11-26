#!/usr/bin/env python3
"""One separately authorized replacement of a refused first scoring.

2026-11-26, issues 6395, 6406 and 6411. Inputs: a measured checkout and original
plan/receipt metadata. Outputs: a read-only plan or one immutable attempt claim,
the unchanged measured executor's attempt 2, and a terminal declaration. Never
reads an original refused response, candidate, transcript or authentication copy.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shlex
import signal
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
SUPPORT = Path(__file__).with_name("repeat_root_scope_scoring_20261126.py")
SPEC = importlib.util.spec_from_file_location("first_replacement_support", SUPPORT)
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
require, physical = support.require, support.physical
read_bytes, read_json, write_json = support.read_bytes, support.read_json, support.write_json
sha, plan_digest = support.sha, support.plan_digest
SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
KIND = "ROOT_SCOPE_FIRST_SCORING_REPLACEMENT_V1"


def utc():
    return datetime.now(timezone.utc).isoformat()


def helper_identity():
    return {"path": str(physical(__file__)), "sha256": sha(read_bytes(__file__)),
            "support_path": str(physical(SUPPORT)), "support_sha256": sha(read_bytes(SUPPORT))}


def absent(path, reason):
    path = physical(path)
    require(not os.path.lexists(path), reason)


def retained_metadata_hash(path):
    """Retain even an empty partial metadata file without interpreting its contents."""
    path = physical(path)
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    require(stat.S_ISREG(info.st_mode) and 0 <= info.st_size <= support.LIMIT,
            "replacement metadata is not a bounded regular file")
    return sha(path.read_bytes())


def outside(path, directory):
    path, directory = physical(path), physical(directory)
    identity = directory.stat()
    for parent in (path, *path.parents):
        try:
            found = parent.stat()
        except FileNotFoundError:
            continue
        require((found.st_dev, found.st_ino) != (identity.st_dev, identity.st_ino),
                "replacement runtime or declaration is inside a protected directory")


def paths(first):
    first = physical(first)
    require(first.is_dir() and first.name.endswith("-01") and len(first.name) > 3,
            "first scoring must be an existing physical run ending -01")
    second = physical(first.with_name(first.name[:-3] + "-02"))
    state = physical(first.parent / "first-scoring-remediations" / first.name)
    return first, second, state


def refusal(first, root):
    """Read only the two original metadata files; existence checks read no payload."""
    plan_path, receipt_path = first / "plan.json", first / "receipt.json"
    plan, receipt = read_json(plan_path), read_json(receipt_path)
    require(isinstance(plan, dict) and isinstance(receipt, dict), "original metadata must be mappings")
    require(receipt.get("status") == "REFUSED", "attempt 1 must be REFUSED")
    require(receipt.get("plan_sha256") == plan_digest(plan), "refused receipt binds another plan")
    require(receipt.get("auth_copy_absent") is True, "original authentication cleanup is unproven")
    absent(first / "codex-home/auth.json", "original authentication copy remains")
    require(not receipt.get("output") and not receipt.get("output_sha256"),
            "original refusal claims a published output")
    times = []
    for key in ("started_utc", "finished_utc"):
        require(isinstance(receipt.get(key), str), "original refusal must have terminal timestamps")
        instant = datetime.fromisoformat(receipt[key])
        require(instant.tzinfo is not None, "original refusal timestamp lacks timezone")
        times.append(instant)
    require(times[1] >= times[0], "original refusal timestamps are reversed")
    word = receipt.get("authorization_reference")
    require(isinstance(word, str) and word.strip(), "original authorization reference is missing")
    require(physical(plan["repo_root"]) == root and physical(plan["runner"]) == root / support.RUNNER,
            "original plan names a different measured checkout or runner")
    require(physical(plan["run_directory"]) == first
            and physical(plan["working_directory"]) == first / "working"
            and physical(plan["codex_home"]) == first / "codex-home", "original runtime paths differ")
    identity = plan.get("identity", {})
    require(identity.get("version") == "6.0" and identity.get("rubric") in (
        "rubric10-semantic", "rubric20-semantic") and identity.get("instrument_id") == support.INSTRUMENT
        and plan.get("instrument") == support.INSTRUMENT and plan.get("runner_sha256") == support.RUNNER_SHA,
        "original plan is not the pinned measured first-scoring instrument")
    absent(plan["output"], "first scoring already has a publication")
    return plan, receipt, {"run_directory": str(first), "plan_path": str(plan_path),
                          "plan_sha256": sha(read_bytes(plan_path)), "receipt_path": str(receipt_path),
                          "receipt_sha256": sha(read_bytes(receipt_path))}


def replace_argument(command, option, old, new):
    require(isinstance(command, list) and command.count(option) == 1, "runtime option is absent or duplicated")
    index = command.index(option) + 1
    require(index < len(command) and command[index] == str(old), "runtime option names a different path")
    command[index] = str(new)


def relocated_plan(original, second):
    """Only named runtime leaves may move; text elsewhere is never substituted."""
    first = physical(original["run_directory"])
    expected = deepcopy(original)
    require(original["commands_shell"] == [shlex.join(original[name]) for name in ("command", "validation_command")],
            "original shell rendering differs from argv")
    expected.update(run_directory=str(second), working_directory=str(second / "working"),
                    codex_home=str(second / "codex-home"))
    for name, value in original["artifacts"].items():
        require(value == str(first / name), "original artifact path differs")
        expected["artifacts"][name] = str(second / name)
    for name, value in original["isolated_inputs"].items():
        require(value == str(first / "working" / name), "original isolated input path differs")
        expected["isolated_inputs"][name] = str(second / "working" / name)
    require(set(original["isolated_inputs"]) == set(original["inputs"]), "original isolated input census differs")
    replace_argument(expected["command"], "--cd", first / "working", second / "working")
    replace_argument(expected["command"], "--output-last-message", first / "raw-response.json", second / "raw-response.json")
    replace_argument(expected["validation_command"], "--file", first / "candidate_evaluation.json", second / "candidate_evaluation.json")
    replace_argument(expected["validation_command"], "--agent-definition", first / "working/agent-definition.md",
                     second / "working/agent-definition.md")
    expected["commands_shell"] = [shlex.join(expected[name]) for name in ("command", "validation_command")]
    return expected


def scorer_arguments(original, second, timeout):
    identity = original["identity"]
    argv = ["--repo-root", original["repo_root"], "--method-directory", identity["method"],
            "--label", identity["label"], "--record", original["inputs"]["record.yaml"]["source"],
            "--rubric", identity["rubric"], "--semantic-version", "6.0", "--scope-context",
            original["inputs"]["scope-context.json"]["source"], "--run-directory", str(second),
            "--codex-binary", original["command"][0], "--poetry-binary", original["validation_command"][0],
            "--validation-venv", original["validation_venv"], "--auth-file", original["auth_file"],
            "--timeout", str(timeout), "--plan"]
    if "caller-context.yaml" in original["inputs"]:
        argv.extend(["--context", original["inputs"]["caller-context.yaml"]["source"]])
    return argv


def verify_job(job, *, consumed=False):
    require(job["kind"] == KIND and job["scoring_replicate"] == 1 and job["attempt"] == 2,
            "only first-scoring attempt 2 is supported")
    require(job["source_head"] == support.SCORER_HEAD
            and job["mode"] == "FIRST_SCORING_REPLACEMENT_PLAN", "replacement source or mode differs")
    require(job["orchestration"] == helper_identity(), "replacement helper changed")
    root = physical(job["plan"]["repo_root"])
    first, second, state = paths(job["refused_attempt"]["run_directory"])
    outside(first, root)
    outside(second, root)
    outside(state, root)
    outside(state, first)
    original, receipt, binding = refusal(first, root)
    require(binding == job["refused_attempt"], "original refusal metadata changed")
    require(plan_digest(job["plan"]) == plan_digest(relocated_plan(original, second)),
            "replacement plan differs beyond named runtime paths")
    require(plan_digest(job["plan"]) == job["plan_sha256"], "compared replacement plan digest differs")
    timeout = job["timeout_seconds"]
    require(type(timeout) is int and 0 < timeout <= 7200, "replacement timeout is invalid")
    require(job["scorer_arguments"] == scorer_arguments(original, second, timeout),
            "replacement arguments differ from the compared plan")
    require(job["state_directory"] == str(state) and job["claim_path"] == str(state / "claim.json")
            and job["manifest_path"] == str(state / "manifest.json"), "replacement declaration paths differ")
    if not consumed:
        absent(second, "attempt 2 already exists; a third attempt is forbidden")
        absent(state, "first scoring remediation already claimed; another attempt is forbidden")
    return receipt


def build_job(args):
    require(0 < args.timeout <= 7200, "timeout must be 1 through 7200 seconds")
    root = physical(args.scoring_root)
    support._checkout(root)
    first, second, state = paths(args.refused_run)
    absent(second, "attempt 2 already exists; a third attempt is forbidden")
    absent(state, "first scoring remediation already claimed; another attempt is forbidden")
    original, _receipt, binding = refusal(first, root)
    scorer = support._load_scorer(root)
    argv = scorer_arguments(original, second, args.timeout)
    plan = support.in_checkout(root, scorer.build_plan, scorer.parser().parse_args(argv))
    job = {"kind": KIND, "mode": "FIRST_SCORING_REPLACEMENT_PLAN", "scoring_replicate": 1,
           "attempt": 2, "source_head": support.SCORER_HEAD, "orchestration": helper_identity(),
           "timeout_seconds": args.timeout,
           "plan": plan, "plan_sha256": plan_digest(plan), "refused_attempt": binding,
           "scorer_arguments": argv, "state_directory": str(state),
           "claim_path": str(state / "claim.json"), "manifest_path": str(state / "manifest.json")}
    verify_job(job)
    return job


def execute_job(job, args):
    reference = args.replacement_authorization_reference
    require(isinstance(reference, str) and reference.strip(), "replacement requires a separate owner authorization reference")
    prior = verify_job(job)
    require(reference.strip() != prior["authorization_reference"].strip(), "replacement authorization must differ from attempt 1")
    require(physical(args.scoring_root) == physical(job["plan"]["repo_root"])
            and physical(args.refused_run) == physical(job["refused_attempt"]["run_directory"]),
            "replacement invocation names a different cell")
    root, state = physical(args.scoring_root), physical(job["state_directory"])
    support._checkout(root)
    scorer = support._load_scorer(root)
    runner_args = scorer.parser().parse_args(job["scorer_arguments"])
    require(runner_args.timeout == args.timeout, "replacement timeout changed since plan")
    runner_args.authorization_reference = reference
    runner_args.plan, runner_args.execute = False, True
    support.in_checkout(root, scorer.check_inputs, job["plan"])
    claim = {"kind": KIND, "action": "replacement", "status": "ATTEMPT2_CLAIMED", "scoring_replicate": 1, "attempt": 2,
             "identity": job["plan"]["identity"], "authorization_reference": reference,
             "claimed_utc": utc(), "source_head": support.SCORER_HEAD, "orchestration": job["orchestration"],
             "refused_attempt": job["refused_attempt"], "replacement_plan_sha256": job["plan_sha256"],
             "run_directory": job["plan"]["run_directory"], "destination": job["plan"]["output"]}
    previous, claimed, failure = {}, False, None
    expected_bindings = {
        "claim_sha256": sha((json.dumps(claim, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()),
        "observed_original_plan_sha256": job["refused_attempt"]["plan_sha256"],
        "observed_original_receipt_sha256": job["refused_attempt"]["receipt_sha256"],
    }
    publication = None
    terminal = {"kind": KIND, "action": "replacement", "status": "FIRST_SCORING_REPLACEMENT_REFUSED", "attempt": 2,
                "scoring_replicate": 1, "identity": job["plan"]["identity"],
                "authorization_reference": reference, "source_head": support.SCORER_HEAD,
                "orchestration": job["orchestration"], "refused_attempt": job["refused_attempt"],
                "replacement_plan_sha256": job["plan_sha256"], "destination": job["plan"]["output"],
                "accepted_output_sha256": None}

    interruptions = []

    def interrupted(number, frame):
        first = not interruptions
        if number not in interruptions:
            interruptions.append(number)
        # Issue 6411: cancellation may raise only inside the protected attempt
        # call. Its frame is absent at finalizer entry, even before the first
        # finalizer statement runs. Later signals cannot interrupt cleanup.
        while first and frame is not None:
            if frame.f_code is run_attempt.__code__:
                raise InterruptedError(f"replacement interrupted by signal {number}")
            frame = frame.f_back

    def observe_interruptions():
        nonlocal failure
        # Called with these signals masked. Consume pending signals while our
        # dispositions are still installed, rather than delivering them to the
        # caller before a terminal refusal can be persisted.
        pending = set(signal.sigpending()).intersection(SIGNALS)
        while pending:
            number = signal.sigwait(pending)
            if number not in interruptions:
                interruptions.append(number)
            pending = set(signal.sigpending()).intersection(SIGNALS)
        if interruptions:
            terminal["interruption_signals"] = list(interruptions)
            if failure is None:
                failure = InterruptedError(f"replacement interrupted by signal {interruptions[0]}")
            terminal.update(status="FIRST_SCORING_REPLACEMENT_REFUSED", accepted_output_sha256=None,
                            failure=type(failure).__name__ + ": " + str(failure))
            for field in ("output_sha256", "validator_input_sha256", "destination_sha256"):
                terminal.pop(field, None)

    def run_attempt():
        nonlocal claimed, publication
        if interruptions:
            raise InterruptedError(f"replacement interrupted by signal {interruptions[0]}")
        state.parent.mkdir(mode=0o700, parents=False, exist_ok=True)
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
        try:
            state.mkdir(mode=0o700, exist_ok=False)
            claimed = True
            write_json(job["claim_path"], claim)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        verify_job(job, consumed=True)
        require(read_json(job["claim_path"]) == claim, "exclusive replacement claim changed")
        require(sha(read_bytes(job["claim_path"])) == expected_bindings["claim_sha256"],
                "exclusive replacement claim bytes changed")
        # Never call scorer.main: it would rebuild a plan after this comparison.
        result = support.in_checkout(root, scorer.execute, job["plan"], runner_args)
        run = Path(job["plan"]["run_directory"])
        snapshots = {kind: read_bytes(run / (kind + ".json")) for kind in ("plan", "receipt")}
        require(plan_digest(read_json(run / "plan.json")) == job["plan_sha256"],
                "executed plan differs from the compared plan")
        accepted, raw = support._accepted(job["plan"], run / "plan.json", run / "receipt.json")
        require(plan_digest(result) == plan_digest(accepted) and accepted["authorization_reference"] == reference,
                "measured executor returned a different receipt or authorization")
        require(plan_digest(json.loads(snapshots["plan"])) == job["plan_sha256"]
                and plan_digest(json.loads(snapshots["receipt"])) == plan_digest(accepted),
                "verified metadata differs from the accepted snapshots")
        for kind in ("plan", "receipt"):
            require(read_bytes(run / (kind + ".json")) == snapshots[kind],
                    "accepted metadata changed during verification")
            expected_bindings["actual_" + kind + "_sha256"] = sha(snapshots[kind])
        expected_bindings["observed_destination_sha256"] = sha(raw)
        publication = {"accepted_output_sha256": sha(raw), "output_sha256": sha(raw),
                       "validator_input_sha256": accepted["validator_input_sha256"],
                       "destination_sha256": sha(raw)}

    try:
        for number in SIGNALS:
            previous[number] = signal.signal(number, interrupted)
        run_attempt()
    except BaseException as error:
        failure = error
        terminal["failure"] = type(error).__name__ + ": " + str(error)
    finally:
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
        try:
            if claimed:
                run = Path(job["plan"]["run_directory"])
                claim_path = Path(job["claim_path"])
                terminal.update(finished_utc=utc(), claim_path=str(claim_path),
                                verified_bindings=expected_bindings)
                bound_paths = (("claim", claim_path), ("actual_plan", run / "plan.json"),
                               ("actual_receipt", run / "receipt.json"),
                               ("observed_original_plan", Path(job["refused_attempt"]["plan_path"])),
                               ("observed_original_receipt", Path(job["refused_attempt"]["receipt_path"])),
                               ("observed_destination", Path(job["plan"]["output"])))
                for kind, path in bound_paths:
                    if kind in ("actual_plan", "actual_receipt"):
                        terminal[kind] = str(path)
                    try:
                        terminal[kind + "_sha256"] = retained_metadata_hash(path)
                    except (OSError, ValueError) as error:
                        terminal[kind + "_sha256"] = None
                        terminal[kind + "_binding_failure"] = type(error).__name__ + ": " + str(error)
                        if failure is None:
                            failure = error
                differences = [key for key, value in expected_bindings.items() if terminal[key] != value]
                if differences:
                    terminal["binding_failures"] = differences
                    if failure is None:
                        failure = ValueError("accepted or original binding changed before terminal declaration: "
                                             + ", ".join(differences))
                if failure is None and publication is not None:
                    terminal.update(status="FIRST_SCORING_REPLACEMENT_PUBLISHED", **publication)
                elif failure is not None:
                    terminal["failure"] = type(failure).__name__ + ": " + str(failure)
                terminal["destination_exists"] = os.path.lexists(job["plan"]["output"])
                observe_interruptions()
                manifest = physical(job["manifest_path"])
                for revision in range(len(SIGNALS) + 1):
                    persisted = deepcopy(terminal)
                    write_json(manifest, persisted)
                    info = manifest.stat()
                    observe_interruptions()
                    if terminal == persisted:
                        break
                    # A signal during persistence invalidates that provisional
                    # terminal. Preserve its exact bytes as unaccepted history,
                    # then write the refusal before restoring dispositions.
                    raw = (json.dumps(persisted, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
                    current = manifest.stat()
                    require((info.st_dev, info.st_ino) == (current.st_dev, current.st_ino)
                            and read_bytes(manifest) == raw, "provisional terminal changed before refusal")
                    archive = state / ("unaccepted-manifest-" + str(revision + 1) + ".json")
                    os.link(manifest, archive, follow_symlinks=False)
                    manifest.unlink()
                else:
                    raise RuntimeError("signal census did not stabilize before terminal persistence")
            else:
                observe_interruptions()
        finally:
            # The last pending-signal check after persistence is the commit
            # point. Signals arriving afterwards belong to the caller again.
            for number, disposition in previous.items():
                signal.signal(number, disposition)
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
    if failure is not None:
        raise failure
    return terminal


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--scoring-root", type=Path, required=True)
    result.add_argument("--refused-run", type=Path, required=True)
    result.add_argument("--replacement-authorization-reference")
    result.add_argument("--timeout", type=int, default=3600)
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--execute", action="store_true")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        job = build_job(args)
        result = job if args.plan else execute_job(job, args)
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("REFUSED: " + type(error).__name__ + ": " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
