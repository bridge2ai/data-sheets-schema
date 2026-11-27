#!/usr/bin/env python3
"""Blinded offline session-identity replay for issue 6384, 2026-11-26.

Inputs: explicit original run roots, saved plans/receipts/stdout/session logs,
and the separately reviewed scorer source. Outputs: a new structural JSON report.
Never calls a model, validator, publication path or candidate/raw-response reader.
Inventory-only mode reads plans and receipts; replay waits for the source freeze.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode = True
LIMIT = 32 * 1024 * 1024
SERIES = ("2026-11-25c", "2026-11-22b")
FALSE_REASONS = (
    "session has no thread-owned model-bearing turn context",
    "inherited context lacks retained ancestor-owned turn evidence",
)
EXPECTED = {"2026-11-25c/published": 90, "2026-11-25c/false_refusal": 2,
            "2026-11-25c/true_refusal": 1, "2026-11-22b/published": 26,
            "2026-11-22b/false_refusal": 3, "2026-11-22b/true_refusal": 1}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def physical(path):
    result = Path(os.path.abspath(path))
    require(not any(part.is_symlink() for part in (result, *result.parents)), "symlink input refused")
    return result


def require_output_outside(output, protected_directories):
    """Refuse lexical and filesystem aliases of protected ancestry (6403)."""
    output = physical(output)
    identities = set()
    for directory in protected_directories:
        directory = physical(directory)
        require(output != directory and directory not in output.parents,
                "output is within a protected directory")
        info = directory.stat()
        require(stat.S_ISDIR(info.st_mode), "protected input is not a directory")
        identities.add((info.st_dev, info.st_ino))
    # Case folding and Unicode normalization may leave different path strings
    # naming the same directory. Compare existing ancestors by device and inode;
    # nonexistent suffixes do not conceal an existing protected ancestor.
    for ancestor in (output, *output.parents):
        try:
            info = ancestor.stat()
        except FileNotFoundError:
            continue
        require((info.st_dev, info.st_ino) not in identities,
                "output aliases a protected directory")
    return output


def read(path):
    path = physical(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= LIMIT, "input is not a bounded regular file")
    return path.read_bytes()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def document(path):
    raw = read(path)
    value = json.loads(raw)
    require(isinstance(value, dict), "metadata must be an object")
    return value, {"path": str(physical(path)), "bytes": len(raw), "sha256": sha(raw)}


def classify(plan, receipt, run):
    identity = plan.get("identity", {})
    require(isinstance(identity, dict), "plan identity must be an object")
    label = identity.get("label", "")
    series = next((value for value in SERIES if isinstance(label, str) and label.startswith(value + "_")), None)
    if series is None:
        return None
    # The requested 22b population is its original 30-run pass. Later owner
    # replacement attempts are a separate population and are never replayed here.
    if series == "2026-11-22b" and not run.name.endswith("-01"):
        return None
    require(receipt.get("finished_utc"), "cohort run is not finished")
    status = receipt.get("status")
    if status == "VALIDATED_AND_PUBLISHED":
        category = "published"
    elif status == "REFUSED":
        failure = receipt.get("failure", "")
        if isinstance(failure, str) and any(failure.endswith(reason) for reason in FALSE_REASONS):
            category = "false_refusal"
        else:
            require(type(receipt.get("validator_exit")) is int and receipt["validator_exit"] != 0,
                    "refusal is outside the diagnosed identity or validation categories")
            category = "true_refusal"
    else:
        raise ValueError("cohort receipt is neither published nor refused")
    require(Path(plan.get("run_directory", "")) == run, "plan run directory differs from retained location")
    require(receipt.get("plan_sha256") == sha(json.dumps(plan, sort_keys=True).encode()),
            "receipt does not bind its saved plan")
    return {"series": series, "category": category, "original_status": status,
            "run_directory": str(run), "identity": {key: identity.get(key) for key in
                ("project", "method", "label", "rubric", "version", "instrument_id")},
            "measured_runner_sha256": plan.get("runner_sha256"),
            "prompt_sha256": plan.get("prompt_sha256"),
            "input_sha256s": {name: item.get("sha256") for name, item in plan.get("inputs", {}).items()
                              if isinstance(item, dict)},
            "original_validator_exit": receipt.get("validator_exit")}


def inventory(roots, run_directories=()):
    directories = {physical(path) for path in run_directories}
    checked_roots = [physical(path) for path in roots]
    for root in checked_roots:
        require(root.is_dir(), "run root is not a directory")
        if (root / "plan.json").is_file() and (root / "receipt.json").is_file():
            directories.add(root)
        for child in sorted(root.iterdir()):
            if child.is_dir() and not child.is_symlink() and (child / "plan.json").is_file() and (child / "receipt.json").is_file():
                directories.add(physical(child))
    rows, retained = [], {}
    for run in sorted(directories):
        plan, plan_pin = document(run / "plan.json")
        receipt, receipt_pin = document(run / "receipt.json")
        row = classify(plan, receipt, run)
        if row is None:
            continue
        row["metadata_pins"] = [plan_pin, receipt_pin]
        rows.append(row)
        retained[str(run)] = (plan, receipt)
    return {"roots": [str(root) for root in checked_roots],
            "run_directories": [str(physical(path)) for path in run_directories],
            "counts": dict(sorted(Counter(row["series"] + "/" + row["category"] for row in rows).items())),
            "runs": rows}, retained


def load_reader(path):
    path = physical(path)
    raw = read(path)
    spec = importlib.util.spec_from_file_location("identity_replay_reader", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, raw


def metadata_shapes(report, retained):
    """Read only each log's first metadata row; export types and comparisons."""
    shapes, pins = Counter(), []
    for row in report["runs"]:
        run = physical(row["run_directory"])
        plan, _receipt = retained[str(run)]
        for path in session_paths(plan, run)[1:]:
            with path.open("rb") as stream:
                raw = stream.readline(LIMIT + 1)
            require(0 < len(raw) <= LIMIT, "first metadata row exceeds bound")
            value = json.loads(raw)
            require(value.get("type") == "session_meta" and isinstance(value.get("payload"), dict),
                    "session log lacks first-row metadata")
            meta = value["payload"]
            parent = meta.get("parent_thread_id")
            if parent is not None:
                fork = meta.get("forked_from_id")
                ordinal = meta.get("subagent_history_start_ordinal")
                key = ("fork=" + type(fork).__name__ + ";present=" + str("forked_from_id" in meta)
                       + ";equals_parent=" + str(fork == parent)
                       + ";ordinal=" + type(ordinal).__name__ + ";present="
                       + str("subagent_history_start_ordinal" in meta))
                shapes[key] += 1
            pins.append({"run_directory": str(run), "path": str(path.relative_to(run)),
                         "first_metadata_bytes": len(raw), "first_metadata_sha256": sha(raw),
                         "is_child": parent is not None})
    return {"child_shape_counts": dict(sorted(shapes.items())), "first_metadata_pins": pins}


def safe_reason(error, source):
    # Reader messages may interpolate model/tool names from the transcript.
    # Only literal source-authored wording is released; dynamic values are hidden.
    text = str(error)
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "require" or len(node.args) < 2:
            continue
        value = node.args[1]
        if isinstance(value, ast.Constant) and isinstance(value.value, str) and text == value.value:
            return value.value
        if isinstance(value, ast.JoinedStr) and value.values and isinstance(value.values[0], ast.Constant):
            prefix = value.values[0].value
            if isinstance(prefix, str) and prefix and text.startswith(prefix):
                return prefix + "[dynamic value withheld]"
    return type(error).__name__ + ": identity reader refused; detail withheld"


def session_paths(plan, run):
    require(physical(plan["codex_home"]) == run / "codex-home", "plan session root is outside retained run")
    require(physical(plan["working_directory"]) == run / "working", "plan working directory is outside retained run")
    root = run / "codex-home/sessions"
    paths = [run / "codex.stdout.jsonl", *sorted(root.rglob("*.jsonl"))]
    return [physical(path) for path in paths]


def replay_one(module, source, row, plan, receipt):
    run = physical(row["run_directory"])
    paths = [run / "plan.json", run / "receipt.json", *session_paths(plan, run)]
    snapshots = {str(path): read(path) for path in paths}
    for pin in row["metadata_pins"]:
        require(sha(snapshots[pin["path"]]) == pin["sha256"], "metadata changed after inventory")
    permitted = {str(path) for path in paths[2:]}
    original_read = module.read_file

    def guarded_read(path, maximum=LIMIT):
        name = str(physical(path))
        require(name in permitted, "identity replay attempted a forbidden file read")
        raw = snapshots[name]
        require(0 < len(raw) <= maximum, "identity replay input exceeds reader bound")
        return raw

    observed, failure = None, None
    module.read_file = guarded_read
    try:
        started = datetime.fromisoformat(receipt["codex_started_utc"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(receipt["codex_finished_utc"].replace("Z", "+00:00"))
        require(started.tzinfo is not None and finished.tzinfo is not None and started <= finished,
                "invalid retained invocation window")
        observed = module.session_identity(plan, started, finished)
    except Exception as error:
        failure = {"reason": safe_reason(error, source), "exception_type": type(error).__name__,
                   "withheld_detail_sha256": sha(str(error).encode())}
    finally:
        module.read_file = original_read
    require(session_paths(plan, run) == paths[2:], "retained session inventory changed during replay")
    require(all(read(path) == snapshots[str(path)] for path in paths), "retained bytes changed during replay")
    result = {**row, "identity_result": "REFUSE" if failure else "ACCEPT",
              "reason": failure["reason"] if failure else "retained session identity accepted",
              "input_bytes_unchanged": True, "evaluation_validation_performed": False,
              "publication_performed": False,
              "read_pins": [{"path": str(path.relative_to(run)), "bytes": len(snapshots[str(path)]),
                             "sha256": sha(snapshots[str(path)])} for path in paths]}
    if failure:
        result.update(failure)
    else:
        logs = observed.get("session_logs", [])
        result["structure"] = {"session_count": len(logs),
                               "child_session_count": sum(item.get("parent_thread_id") is not None for item in logs),
                               "owned_turn_count": sum(len(item.get("owned_turn_ids", [])) for item in logs)}
    return result


def save(path, value):
    path = physical(path)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False).replace(chr(64), "\\u0040") + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--run-directory", type=Path, action="append", default=[])
    parser.add_argument("--runner", type=Path)
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--session-metadata", action="store_true")
    parser.add_argument("--require-census", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    require(args.root or args.run_directory, "explicit retained roots or runs are required")
    require(os.getpriority(os.PRIO_PROCESS, 0) >= 10, "run the replay at nice 10 or lower priority")
    report, retained = inventory(args.root, args.run_directory)
    require(report["runs"], "no matching retained runs")
    if args.require_census:
        require(report["counts"] == EXPECTED, "retained census differs from required 123-run population")
    output = physical(args.output)
    require(not output.exists(), "output already exists")
    for run in retained:
        require(not output.is_relative_to(Path(run)), "output must be outside retained runs")
    for run in report["run_directories"]:
        require(not output.is_relative_to(Path(run)), "output must be outside explicitly supplied runs")
    for root in report["roots"]:
        require(not output.is_relative_to(Path(root)), "output must be outside retained roots")
    require_output_outside(output, [*retained, *report["run_directories"], *report["roots"]])
    report.update(mode="inventory_only" if args.inventory_only else "identity_replay",
                  validation_performed=False, publication_performed=False)
    if args.session_metadata:
        report["metadata_structure"] = metadata_shapes(report, retained)
    if not args.inventory_only:
        require(args.runner is not None, "replay requires the separately reviewed runner")
        module, source = load_reader(args.runner)
        report["reader"] = {"path": str(physical(args.runner)), "sha256": sha(source)}
        report["runs"] = [replay_one(module, source, row, *retained[row["run_directory"]]) for row in report["runs"]]
        require(read(args.runner) == source, "reader source changed during replay")
        report["identity_counts"] = dict(sorted(Counter(row["identity_result"] for row in report["runs"]).items()))
    save(output, report)
    print(json.dumps({"mode": report["mode"], "counts": report["counts"],
                      "identity_counts": report.get("identity_counts"),
                      "report_sha256": sha(read(output))}, sort_keys=True))
    return 0 if args.inventory_only or all(row["identity_result"] == "ACCEPT" for row in report["runs"]) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"status": "REPLAY_SETUP_REFUSED", "exception_type": type(error).__name__,
                          "detail_sha256": sha(str(error).encode())}, sort_keys=True))
        raise SystemExit(2)
