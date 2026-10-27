#!/usr/bin/env python3
"""Recover N2 default controller/receipt integration, 2026-10-25 (#4354).

Inputs: cached 7c1002cae target, pre-owner a33d80d84 and their merge base.
Outputs: explicit scoped worktree files plus a recovery manifest. Existing
files use a three-way merge, preserving newer target-side API fixes. No owner
profile, provider, GitHub, push, protected shared-generation file or asset edit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

BASE = "286b88688c9775c3b351fe7ec0d5b49b2ef01fff"
SOURCE = "a33d80d84"
TARGET = "7c1002cae"
SHARED = (
    "attribution", "capture", "controller", "current", "effects", "execution",
    "gates", "observations", "permissions", "phase", "policy", "publication",
    "receipts", "registration", "results", "schema_gates", "stage", "streams",
)
NEW_MODULES = [f"src/data_sheets_schema/native_shared_{name}.py" for name in SHARED] + [
    f"src/data_sheets_schema/{name}.py" for name in (
        "native_catalog_reuse", "native_execution_engine", "native_gate_engine",
        "native_subscription_guard")]
COMMON = [f"src/data_sheets_schema/{name}.py" for name in (
    "native_execution", "native_execution_registration", "native_execution_gates",
    "native_attempt_supervisor", "receipt_completion_policy", "receipts",
    "receipt_origin_record", "backfill_checks", "derive_core", "audit_omissions",
    "cache_dependencies", "typed_audit", "cli/derive", "cli/receipts", "cli/provenance", "cli/prompt")]
COMMON += ["src/data_sheets_schema/schema/d4d_generation_record.yaml"]
EXCLUDED_TESTS = {
    "tests/test_native_shared_contract.py", "tests/test_native_shared_evidence.py",
    "tests/test_native_shared_selection.py", "tests/test_native_shared_render.py",
    "tests/test_native_permission_probe.py", "tests/test_native_subscription_guard.py",
    "tests/test_native_ci_evidence.py", "tests/test_native_ci_evidence_adversarial.py",
    "tests/test_native_shared_acceptance_runner.py",
    "tests/test_native_typed_catalog_scanner.py",
}


def git(root, *args, check=True):
    return subprocess.run(["git", "-C", str(root), *args], check=check,
                          capture_output=True).stdout


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def recover(root, path, *, added):
    target = root / path
    incoming = git(root, "show", f"{SOURCE}:{path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if added:
        if target.exists():
            if target.read_bytes() != incoming:
                raise ValueError(f"refusing overwrite of changed recovered path {path}")
            return {"path": path, "operation": "new_preowner_file", "sha256": digest(incoming)}
        target.write_bytes(incoming)
        return {"path": path, "operation": "new_preowner_file", "sha256": digest(incoming)}
    previous = target.read_bytes()
    expected = git(root, "show", f"{TARGET}:{path}")
    if previous != expected:
        raise ValueError(f"target path changed before recovery: {path}")
    ancestor = git(root, "show", f"{BASE}:{path}")
    with tempfile.TemporaryDirectory(prefix="n2-unit2-merge-") as directory:
        temporary = Path(directory)
        for name, raw in (("target", previous), ("base", ancestor), ("incoming", incoming)):
            (temporary / name).write_bytes(raw)
        result = subprocess.run(["git", "merge-file", "-p", "-L", "cached-target-7c1002cae",
            "-L", BASE, "-L", "preowner-a33d80d84", str(temporary / "target"),
            str(temporary / "base"), str(temporary / "incoming")], capture_output=True)
    if not 0 <= result.returncode <= 127:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    target.write_bytes(result.stdout)
    return {"path": path, "operation": "three_way_merge", "conflict": bool(result.returncode),
            "target_sha256": digest(previous), "source_sha256": digest(incoming),
            "base_sha256": digest(ancestor), "merged_sha256": digest(result.stdout)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    added_tests = git(root, "diff", "--name-only", "--diff-filter=A", BASE, SOURCE, "--", "tests").decode().splitlines()
    tracked = set(git(root, "ls-tree", "-r", "--name-only", TARGET, "--", "tests").decode().splitlines())
    tests = [path for path in added_tests if path not in EXCLUDED_TESTS and path not in tracked]
    rows = [recover(root, path, added=True) for path in [*NEW_MODULES, *tests]]
    rows.extend(recover(root, path, added=False) for path in COMMON)
    conflicts = [row["path"] for row in rows if row.get("conflict")]
    result = {"source": git(root, "rev-parse", SOURCE).decode().strip(),
              "target": git(root, "rev-parse", TARGET).decode().strip(), "merge_base": BASE,
              "rows": rows, "conflicts_for_manual_review": conflicts,
              "existing_test_files_retained": sorted(set(added_tests) & tracked),
              "omitted": "Unit1 protocol/selection/render files; owner profile; probe producer/CLI and acceptance utilities."}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"recovered_files": len(rows), "conflicts": conflicts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
