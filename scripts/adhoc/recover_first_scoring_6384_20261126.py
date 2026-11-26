#!/usr/bin/env python3
"""One offline first-scoring recovery, issues 6384/6395, 2026-11-26.

Inputs: one terminal identity refusal, unchanged response/session/input bytes,
the measured validator and the separately pinned revised identity reader.
Outputs: an exclusive sibling claim, private validation evidence, and only with
explicit authorization an atomic publication plus linked recovery manifest.
No model command, authentication access, prompt rebuild or response repair.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
RUNNER = "scripts/adhoc/score_semantic_rubric_codex_20261125.py"
MEASURED_HEAD = "9452a5c49a0533d86c5e08c1093021036ef98830"
MEASURED_SHA = "b2a5c0995d891d4c5179509834b460390b1d921d78b0191965fc4ea3f91c21b9"
REVISED_HEAD = "60dc199726b63fb64d4eafd4cef3760ac7e2a76c"
REVISED_SHA = "45324f05ef4360f95620c5e9a37d7896661321177242f700f25bd22fe72cf51b"
EXPORTER_SHA = "21dd7efdd954daea36e0ab30cdbe36fabafa30c0de7152703eaf68902dfa43b9"
GUARD_SHA = "539871779c2965002ef7c3b9cdf9836c46dfb942ff589c10451011034c223aa5"
FALSE_REASONS = (
    "ScorerError: session has no thread-owned model-bearing turn context",
    "ScorerError: inherited context lacks retained ancestor-owned turn evidence",
)
LIMIT = 32 * 1024 * 1024


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def physical(value):
    path = Path(os.path.abspath(value))
    require(not any(part.is_symlink() for part in (path, *path.parents)), "symlink route refused")
    return path


def read(path):
    path = physical(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= LIMIT,
            "input is not a bounded nonempty regular file")
    return path.read_bytes()


def document(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    value = json.loads(read(path), object_pairs_hook=pairs,
                       parse_constant=lambda value: require(False, "nonfinite JSON value"))
    require(isinstance(value, dict), "metadata must be an object")
    return value


def write(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with physical(path).open("xb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    require(read(path) == raw, "saved evidence bytes differ")
    return sha(raw)


def load(path, digest, name):
    path = physical(path)
    require(sha(read(path)) == digest, "pinned program bytes differ: " + path.name)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "cannot load pinned program")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def programs():
    exporter = load(ROOT / "scripts/adhoc/repeat_root_scope_scoring_20261126.py",
                    EXPORTER_SHA, "recovery_atomic_exporter")
    guard = load(ROOT / "scripts/adhoc/replay_scorer_session_identity_6384_20261126.py",
                 GUARD_SHA, "recovery_physical_guard")
    revised = load(ROOT / RUNNER, REVISED_SHA, "recovery_revised_reader")
    return exporter, guard, revised


def helper_identity():
    return {"sha256": sha(read(__file__)), "path": "scripts/adhoc/" + Path(__file__).name,
            "exporter_sha256": EXPORTER_SHA, "path_guard_sha256": GUARD_SHA}


def stamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timestamp must have a timezone")
    return parsed


def checkout(root):
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True, timeout=30)
    require(result.stdout.strip() == MEASURED_HEAD, "measured checkout head differs")
    for flags in ([], ["--cached"]):
        subprocess.run(["git", "-C", str(root), "diff", *flags, "--quiet"],
                       check=True, timeout=30)


def input_pins(plan, measured):
    """Keep validator/input pins; never open the obsolete model binary or auth."""
    require(plan["runner_sha256"] == MEASURED_SHA, "measured runner pin differs")
    require(sha(read(plan["runner"])) == MEASURED_SHA, "measured runner bytes differ")
    for name in plan["inputs"]:
        measured.input_bytes(plan, name)
    for path, digest in plan["validation_sha256"].items():
        require(sha(read(path)) == digest, "measured validator dependency changed")
    command = plan["validation_command"]
    require(isinstance(command, list) and command[1:4] == ["run", "python", "scripts/validate_evaluation_schema.py"],
            "measured validator command differs")
    executable = command[0]
    require(measured.executable_digest(executable) == plan["executable_sha256"].get(executable),
            "validator executable changed")
    require(physical(plan["validation_cwd"]) == physical(plan["repo_root"]), "validator checkout differs")
    venv = physical(plan["validation_venv"])
    require((venv / "pyvenv.cfg").is_file() and (venv / "bin/python").is_file(),
            "existing validation environment required")


def eligibility(original_run):
    run = physical(original_run)
    require(run.name.endswith("-01"), "first scoring must name its original attempt 01")
    plan, receipt = document(run / "plan.json"), document(run / "receipt.json")
    require(receipt.get("status") == "REFUSED" and receipt.get("failure") in FALSE_REASONS,
            "only a diagnosed identity-reader refusal is recoverable")
    require(receipt.get("plan_sha256") == sha(json.dumps(plan, sort_keys=True).encode()),
            "original receipt does not bind its plan")
    require(type(receipt.get("codex_exit")) is int and receipt["codex_exit"] == 0
            and receipt.get("auth_copy_absent") is True, "original invocation or cleanup is unproven")
    require("validator_exit" not in receipt and "evaluation_model" not in receipt,
            "original run progressed beyond the identity-reader refusal")
    require(stamp(receipt["started_utc"]) <= stamp(receipt["codex_started_utc"])
            <= stamp(receipt["codex_finished_utc"]) <= stamp(receipt["finished_utc"]),
            "original refusal is not terminal or timestamps differ")
    require(physical(plan["run_directory"]) == run, "original run location differs")
    for name, expected in (("working_directory", run / "working"), ("codex_home", run / "codex-home")):
        require(physical(plan[name]) == expected, "original runtime path differs")
    require(not os.path.lexists(run / "codex-home/auth.json"), "original authentication copy remains")
    for name in ("candidate_evaluation.json", "validator.stdout.txt", "validator.stderr.txt"):
        require(not os.path.lexists(run / name), "original run already has validation artifacts")
    root = physical(plan["repo_root"])
    require(physical(plan["runner"]) == root / RUNNER, "measured runner location differs")
    identity = plan["identity"]
    require(identity["version"] == "6.0" and identity["rubric"] in ("rubric10-semantic", "rubric20-semantic"),
            "only the measured root-scope semantic instrument is supported")
    for name in ("project", "label", "method", "instrument_id"):
        require(isinstance(identity[name], str) and identity[name] and "/" not in identity[name]
                and "\\" not in identity[name] and identity[name] not in (".", ".."), "unsafe cell identity")
    destination = root / "data/evaluation_llm" / identity["rubric"].replace("-", "_") / "label_aware" / identity["instrument_id"] / (identity["project"] + "_" + identity["label"] + "_evaluation.json")
    require(plan["instrument"] == identity["instrument_id"] and physical(plan["output"]) == destination,
            "normal first-scoring publication path differs")
    require(not os.path.lexists(destination), "cell already has a publication")
    return run, root, plan, receipt, destination


def retained_snapshot(run, plan):
    paths = [run / name for name in ("plan.json", "receipt.json", "raw-response.json", "codex.stdout.jsonl")]
    sessions = physical(run / "codex-home/sessions")
    require(sessions.is_dir(), "retained session directory missing")
    paths.extend(sorted(sessions.rglob("*.jsonl")))
    require(len(paths) > 4, "retained session logs missing")
    working = physical(plan["working_directory"])
    require(sorted(item.name for item in working.iterdir()) == sorted(plan["inputs"]),
            "isolated input inventory changed")
    for name in plan["inputs"]:
        paths.append(working / name)
    result = {str(path.relative_to(run)): read(path) for path in paths}
    for name, item in plan["inputs"].items():
        require(sha(result["working/" + name]) == item["sha256"], "isolated input bytes changed")
    return result


def retained_pins(run, plan):
    return {name: sha(raw) for name, raw in retained_snapshot(run, plan).items()}


def read_identity(module, plan, started, finished, snapshots):
    run, original = physical(plan["run_directory"]), module.read_file
    permitted = {name for name in snapshots if name == "codex.stdout.jsonl"
                 or name.startswith("codex-home/sessions/")}
    def captured(path, maximum=LIMIT):
        name = str(physical(path).relative_to(run))
        require(name in permitted, "identity reader attempted a non-identity file read")
        raw = snapshots[name]
        require(0 < len(raw) <= maximum, "identity input exceeds reader bound")
        return raw
    module.read_file = captured
    try:
        observed = module.session_identity(plan, started, finished)
    finally:
        module.read_file = original
    expected = {name: sha(snapshots[name]) for name in permitted if name != "codex.stdout.jsonl"}
    require({item["path"]: item["sha256"] for item in observed["session_logs"]} == expected,
            "observed identity does not bind the captured session logs")
    return observed


def require_retained(run, plan, pins):
    require(retained_pins(run, plan) == pins, "retained original evidence changed")


def construct_candidate(measured, plan, observed, response_snapshot):
    """Execute the exact construction statements extracted from the pinned blob."""
    source = read(plan["runner"])
    require(sha(source) == MEASURED_SHA, "candidate constructor source differs")
    tree = ast.parse(source)
    execute = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "execute")
    body = next(node for node in execute.body if isinstance(node, ast.Try)).body
    def assignment(node, name):
        return isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    first = next(index for index, node in enumerate(body) if assignment(node, "candidate"))
    last = next(index for index, node in enumerate(body) if assignment(node, "staged"))
    require(first < last, "pinned candidate constructor boundaries differ")
    namespace = dict(measured.__dict__)
    namespace.update(plan=plan, observed=observed, run=Path(plan["run_directory"]))
    original_read = measured.read_file
    def captured(path, maximum=LIMIT):
        if physical(path) == physical(plan["run_directory"]) / "raw-response.json":
            require(0 < len(response_snapshot) <= maximum, "captured response exceeds reader bound")
            return response_snapshot
        return original_read(path, maximum)
    namespace["read_file"] = captured
    module = ast.Module(body=deepcopy(body[first:last]), type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), "pinned_measured_candidate_constructor", "exec"), namespace)
    return namespace["candidate"]


def recovery_paths(run, root, recovery_root, guard):
    directory = guard.require_output_outside(physical(recovery_root) / run.name, [run, root])
    claims = physical(run.parent / "first-scoring-remediations" / run.name)
    claim = claims / "claim.json"
    guard.require_output_outside(claim, [run, root])
    require(not os.path.lexists(run.with_name(run.name[:-3] + "-02")),
            "replacement attempt 02 already exists")
    # The claim always lives beside the original run, independently of the
    # chosen recovery-root. A second output root cannot create a second try.
    return directory, claims, claim


def reference(value, prior):
    require(isinstance(value, str) and value.strip() and value == value.strip(),
            "a distinct explicit owner authorization reference is required")
    require(value not in prior, "authorization reference must be separate from earlier acts")
    return value


def perform(args):
    exporter, guard, revised = programs()
    run, root, plan, original, destination = eligibility(args.original_run)
    directory, claims, claim = recovery_paths(run, root, args.recovery_root, guard)
    if args.publish_validated:
        return publish_validated(args, exporter, guard, run, root, plan, original,
                                 destination, directory, claim)
    authorization = reference(args.authorization_reference, [original.get("authorization_reference", "")])
    require(not os.path.lexists(claims) and not os.path.lexists(directory),
            "recovery was already claimed; no second validation attempt")
    checkout(root)
    measured = load(root / RUNNER, MEASURED_SHA, "recovery_measured_runner")
    exporter.in_checkout(root, input_pins, plan, measured)
    # Eligibility and authorization precede the first retained-response read.
    snapshots = retained_snapshot(run, plan)
    pins = {name: sha(raw) for name, raw in snapshots.items()}
    require(json.loads(snapshots["plan.json"]) == plan and json.loads(snapshots["receipt.json"]) == original,
            "original metadata changed before capture")
    identity = helper_identity()
    value = {"kind": "FIRST_SCORING_RECOVERY_CLAIM", "action": "recovery", "identity": plan["identity"],
             "original_run": str(run), "recovery_directory": str(directory),
             "original_plan_sha256": pins["plan.json"], "original_receipt_sha256": pins["receipt.json"],
             "authorization_reference": authorization, "program": identity,
             "revised_reader_commit": REVISED_HEAD, "revised_reader_sha256": REVISED_SHA,
             "created_utc": utc()}
    receipt = {"status": "RECOVERY_STARTED", "identity": plan["identity"],
               "authorization_reference": authorization, "started_utc": utc(),
               "claim_sha256": None, "program": identity,
               "measured_runner_commit": MEASURED_HEAD, "measured_runner_sha256": MEASURED_SHA,
               "revised_reader_commit": REVISED_HEAD, "revised_reader_sha256": REVISED_SHA,
               "original_run": str(run), "original_pins": pins,
               "original_codex_started_utc": original["codex_started_utc"],
               "original_codex_finished_utc": original["codex_finished_utc"],
               "historical_executable_sha256": plan["executable_sha256"],
               "destination": str(destination), "model_calls": 0}
    # Issue 6407: defer termination before the first claim mutation, not only
    # during identity/validation. Ownership flags keep a losing claim race from
    # writing into another controller's state; every owned setup exit is caught.
    control = exporter._ExportSignals()
    claimed, created, refusal_ready = False, False, False
    try:
        control.check()
        claims.parent.mkdir(mode=0o700, exist_ok=True)
        claims.mkdir(mode=0o700, exist_ok=False)
        claimed = True
        claim_sha = write(claim, value)
        receipt["claim_sha256"] = claim_sha
        directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory.mkdir(mode=0o700, exist_ok=False)
        created = True
        write(directory / "failure.json", {"status": "RECOVERY_REFUSED", "failure": "recovery has not completed"})
        os.link(directory / "failure.json", directory / "refusal-reserve.json")
        refusal_ready = True
        control.check()
        started, finished = stamp(original["codex_started_utc"]), stamp(original["codex_finished_utc"])
        try:
            read_identity(measured, plan, started, finished, snapshots)
        except measured.ScorerError as exc:
            require(type(exc).__name__ + ": " + str(exc) == original["failure"],
                    "measured identity refusal does not reproduce exactly")
        else:
            require(False, "measured reader accepts; not an identity-only recovery")
        receipt["acceptance_started_utc"] = utc()
        observed = read_identity(revised, plan, started, finished, snapshots)
        receipt["evaluation_model"] = observed
        receipt["acceptance_finished_utc"] = utc()
        control.check()
        candidate = exporter.in_checkout(root, construct_candidate, measured, plan, observed,
                                          snapshots["raw-response.json"])
        linkage = {"kind": "identity_reader_recovery", "claim_sha256": claim_sha,
                   "measured_runner_sha256": MEASURED_SHA, "revised_reader_commit": REVISED_HEAD,
                   "original_plan_sha256": pins["plan.json"], "original_receipt_sha256": pins["receipt.json"],
                   "response_sha256": pins["raw-response.json"], "recovery_program_sha256": identity["sha256"]}
        candidate["scorer_instrument"].update(runner_sha256=REVISED_SHA, recovery=linkage)
        staged = directory / "validated-evaluation.json"
        measured.write_json(staged, candidate)
        raw = read(staged)
        receipt["validator_input_sha256"] = sha(raw)
        command = list(plan["validation_command"])
        require(command.count("--file") == 1, "validator file argument differs")
        command[command.index("--file") + 1] = str(staged)
        home = directory / "home"
        home.mkdir(mode=0o700)
        venv = physical(plan["validation_venv"])
        environment = {"PATH": str(venv / "bin") + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       "HOME": str(home), "VIRTUAL_ENV": str(venv), "POETRY_VIRTUALENVS_CREATE": "false",
                       "PIP_NO_INDEX": "1", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        receipt["validation_started_utc"] = utc()
        receipt["validator_exit"] = exporter._validate_staged(command, root, environment, directory, control)
        receipt["validation_finished_utc"] = utc()
        require(receipt["validator_exit"] == 0, "exact-file validation refused; no second recovery attempt")
        require(read(staged) == raw, "candidate changed during validation")
        require_retained(run, plan, pins)
        exporter.in_checkout(root, input_pins, plan, measured)
        require(helper_identity() == identity, "recovery program changed during validation")
        staged.chmod(0o400)
        receipt.update(status="VALIDATED_RECOVERY_NOT_PUBLISHED", validated_sha256=sha(raw), finished_utc=utc())
        receipt_sha = write(directory / "recovery-receipt.json", receipt)
        write(claims / "validation.json", {"action": "recovery", "status": receipt["status"],
              "claim_sha256": claim_sha, "recovery_receipt_sha256": receipt_sha,
              "validated_sha256": sha(raw), "recovery_directory": str(directory)})
        control.commit(directory / "failure.json")
    except BaseException as exc:
        receipt.update(status="RECOVERY_REFUSED", failure=type(exc).__name__ + ": " + str(exc), finished_utc=utc())
        if claimed:
            write(claims / "failure.json", {"action": "recovery", **receipt})
        if created and not (directory / "recovery-receipt.json").exists():
            write(directory / "recovery-receipt.json", receipt)
        if refusal_ready:
            exporter._export_refusal(directory, destination, None, {"status": "RECOVERY_REFUSED", "failure": receipt["failure"]})
        raise
    finally:
        control.restore()
    if args.publish:
        return publish_validated(args, exporter, guard, run, root, plan, original,
                                 destination, directory, claim, direct=True)
    return {"status": "PASS", "reason": "identity and exact-file validation passed; publication not requested"}


def publish_validated(args, exporter, guard, run, root, plan, original, destination,
                      directory, claim, direct=False):
    require(directory.is_dir(), "successful saved recovery required")
    recorded_claim = document(claim)
    require(recorded_claim.get("action") == "recovery", "cell was claimed by another remediation path")
    receipt_path = directory / "recovery-receipt.json"
    receipt = document(receipt_path)
    terminal = document(claim.parent / "validation.json")
    require(receipt.get("status") == "VALIDATED_RECOVERY_NOT_PUBLISHED"
            and receipt.get("validator_exit") == 0, "recovery did not validate; never retry")
    require(recorded_claim.get("original_run") == str(run)
            and recorded_claim.get("recovery_directory") == str(directory)
            and receipt.get("original_run") == str(run), "saved recovery location differs")
    require(recorded_claim.get("identity") == receipt.get("identity") == plan["identity"], "saved recovery identity differs")
    require(receipt.get("claim_sha256") == sha(read(claim))
            and recorded_claim.get("program") == receipt.get("program") == helper_identity(),
            "saved recovery claim/program binding differs")
    require(terminal.get("action") == "recovery" and terminal.get("status") == receipt["status"]
            and terminal.get("claim_sha256") == sha(read(claim))
            and terminal.get("recovery_receipt_sha256") == sha(read(receipt_path))
            and terminal.get("recovery_directory") == str(directory)
            and terminal.get("validated_sha256") == receipt.get("validated_sha256"),
            "fixed-cell validation receipt binding differs")
    require(receipt.get("revised_reader_commit") == recorded_claim.get("revised_reader_commit") == REVISED_HEAD
            and receipt.get("revised_reader_sha256") == recorded_claim.get("revised_reader_sha256") == REVISED_SHA,
            "saved revised reader binding differs")
    require(receipt.get("authorization_reference") == recorded_claim.get("authorization_reference"),
            "saved recovery authorization differs")
    prior = [original.get("authorization_reference", "")]
    if not direct:
        prior.append(receipt["authorization_reference"])
    authorization = reference(args.authorization_reference, prior)
    if direct:
        require(authorization == receipt["authorization_reference"], "direct publication authorization differs")
    require(not (directory / "failure.json").exists(), "recovery retains failure evidence")
    require(not os.path.lexists(directory / "publication-claim.json"), "publication already claimed; never retry")
    require_retained(run, plan, receipt["original_pins"])
    require(receipt["original_pins"]["plan.json"] == recorded_claim["original_plan_sha256"]
            and receipt["original_pins"]["receipt.json"] == recorded_claim["original_receipt_sha256"],
            "original recovery claim pins differ")
    checkout(root)
    measured = load(root / RUNNER, MEASURED_SHA, "recovery_measured_publication_check")
    exporter.in_checkout(root, input_pins, plan, measured)
    staged = physical(directory / "validated-evaluation.json")
    raw = read(staged)
    require(sha(raw) == receipt["validated_sha256"] == receipt["validator_input_sha256"],
            "saved validated bytes changed")
    require(receipt.get("destination") == str(destination) and not os.path.lexists(destination),
            "saved destination differs or already exists")
    publication = {"status": "RECOVERY_PUBLICATION_STARTED", "authorization_reference": authorization,
                   "recovery_receipt_sha256": sha(read(receipt_path)), "claim_sha256": sha(read(claim)),
                   "started_utc": utc(), "destination": str(destination), "validated_sha256": sha(raw)}
    # The successful dry-run is immutable. The separate publication claim is
    # protected from its first write through terminal receipt and rollback.
    control = exporter._ExportSignals()
    owned = None
    claimed = False
    try:
        control.check()
        # Issue 6410: claim ownership with one exclusive filesystem operation
        # before a multi-step JSON write can fail. The existing durable reserve
        # is also the refusal marker if creation, flush or readback fails. A
        # losing concurrent linker owns nothing and must not alter winner state.
        os.link(directory / "refusal-reserve.json", directory / "failure.json")
        claimed = True
        write(directory / "publication-claim.json", publication)
        control.check()
        destination.parent.mkdir(parents=True, exist_ok=True)
        info = staged.stat()
        require(destination.parent.stat().st_dev == info.st_dev, "atomic publication requires the same filesystem")
        owned = info.st_dev, info.st_ino
        control.check()
        os.link(staged, physical(destination), follow_symlinks=False)
        control.check()
        require(read(destination) == raw and read(staged) == raw, "publication differs from validated bytes")
        require_retained(run, plan, receipt["original_pins"])
        exporter.in_checkout(root, input_pins, plan, measured)
        require(helper_identity() == receipt["program"], "recovery program changed during publication")
        publication.update(status="RECOVERED_AND_PUBLISHED", finished_utc=utc(), published_sha256=sha(raw))
        publication_sha = write(directory / "publication-receipt.json", publication)
        manifest = {"kind": "FIRST_SCORING_RECOVERY", "status": "RECOVERED_AND_PUBLISHED",
                    "scoring_replicate": 1, "identity": plan["identity"], "attempt": 1,
                    "original_run": str(run), "original_pins": receipt["original_pins"],
                    "measured_runner_sha256": MEASURED_SHA, "revised_reader_commit": REVISED_HEAD,
                    "revised_reader_sha256": REVISED_SHA, "program": helper_identity(),
                    "recovery_claim": str(claim), "recovery_claim_sha256": sha(read(claim)),
                    "recovery_receipt": str(receipt_path), "recovery_receipt_sha256": sha(read(receipt_path)),
                    "publication_receipt": str(directory / "publication-receipt.json"),
                    "publication_receipt_sha256": publication_sha,
                    "authorization_reference": authorization,
                    "recovery_authorization_reference": receipt["authorization_reference"],
                    "acceptance_started_utc": receipt["acceptance_started_utc"],
                    "acceptance_finished_utc": receipt["acceptance_finished_utc"],
                    "validation_started_utc": receipt["validation_started_utc"],
                    "validation_finished_utc": receipt["validation_finished_utc"],
                    "destination": str(destination), "destination_sha256": sha(raw), "model_calls": 0}
        write(directory / "manifest.json", manifest)
        write(claim.parent / "manifest.json", {"action": "recovery", "status": "RECOVERED_AND_PUBLISHED",
              "manifest_path": str(directory / "manifest.json"),
              "manifest_sha256": sha(read(directory / "manifest.json")),
              "claim_sha256": sha(read(claim)), "destination_sha256": sha(raw)})
        control.check()
        control.commit(directory / "failure.json")
        return {"status": "PASS", "reason": "recovered exact validated bytes published without a model call"}
    except BaseException as exc:
        publication.update(status="RECOVERY_PUBLICATION_REFUSED", failure=type(exc).__name__ + ": " + str(exc), finished_utc=utc())
        if claimed:
            # Roll back publication and retain the reserved failure marker even
            # if the subsequent detailed terminal-receipt write also fails.
            exporter._export_refusal(directory, destination, owned, publication)
            if not (directory / "publication-receipt.json").exists():
                write(directory / "publication-receipt.json", publication)
            shared_manifest = claim.parent / "manifest.json"
            if shared_manifest.exists():
                shared_manifest.rename(claim.parent / "unaccepted-manifest.json")
            write(claim.parent / "publication-failure.json", publication)
        raise
    finally:
        control.restore()


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--original-run", required=True, type=Path)
    result.add_argument("--recovery-root", required=True, type=Path)
    result.add_argument("--authorization-reference", required=True,
                        help="Separate owner decision reference, not proof; publish-validated needs a new reference.")
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                      help="Consume the one validation attempt; never publish. Failure is terminal.")
    mode.add_argument("--publish", action="store_true", help="One identity/validation attempt and atomic publication.")
    mode.add_argument("--publish-validated", action="store_true",
                      help="Publish the same successful dry-run bytes; never repeat identity or validation.")
    return result


def main(argv=None):
    try:
        result = perform(parser().parse_args(argv))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
        # No response, candidate, scoring fields or validator output is printed.
        print(json.dumps({"status": "REFUSED", "reason": type(exc).__name__ + ": " + str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
