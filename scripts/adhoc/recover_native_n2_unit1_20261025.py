#!/usr/bin/env python3
"""Recover N2 unit1 immutable protocol/selection, 2026-10-25, Refs #4354.

Inputs: pinned local Git trial db0573d96 and v10 merge-base74d; owned checkout.
Outputs: exact archived native files and narrow API/schema integration patch.
No remote/provider operations; preserve current API additions and protected files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = "db0573d96bb16ee32d3537ea0a9ad0ca607e355a"
COMMON = "74d1351a98ffa78794687681c853267df9e50b69"
NEW_FILES = (
    "src/data_sheets_schema/native_shared_contract.py",
    "src/data_sheets_schema/native_shared_evidence.py",
    "src/data_sheets_schema/native_shared_selection.py",
    "src/data_sheets_schema/native_shared_render.py",
    "src/download/prompts/native_shared_generation_v1.md",
    "src/download/prompts/native_shared_receipt_policy_v1.md",
    "tests/test_native_shared_contract.py",
    "tests/test_native_shared_evidence.py",
    "tests/test_native_shared_selection.py",
    "tests/test_native_shared_render.py",
    "tests/test_native_schema_metadata_reuse.py",
)
PATCH_FILES = ("src/data_sheets_schema/schema_snapshot.py", "src/data_sheets_schema/api_runner.py")


def git(root, *args, input=None):
    return subprocess.run(["git", "-C", str(root), *args], input=input, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if git(root, "branch", "--show-current").decode().strip() != "codex/n2-1-protocol-selection":
        raise ValueError("recovery is restricted to the owned unit1 branch")
    for name in NEW_FILES:
        if (root / name).exists() or (root / name).is_symlink():
            raise ValueError("refuse replacing existing content: " + name)
    if git(root, "diff", "--", *PATCH_FILES).strip():
        raise ValueError("refuse patching dirty integration files")
    patch = git(root, "diff", "--binary", COMMON, SOURCE, "--", *PATCH_FILES)
    git(root, "apply", "--check", input=patch)
    pins = []
    for name in NEW_FILES:
        raw = git(root, "show", SOURCE + ":" + name)
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        pins.append({"path": name, "source": SOURCE, "sha256": hashlib.sha256(raw).hexdigest()})
    git(root, "apply", input=patch)
    # Native selection has already passed validate_native_shared above this
    # point. The API-only selector remains unchanged and rejects native inputs.
    api_path = root / "src/data_sheets_schema/api_runner.py"
    text = api_path.read_text()
    old = "        from .shared_generation import select as select_shared\n        select_shared(self)\n"
    new = "        if not self.native_shared_generation_version:\n            from .shared_generation import select as select_shared\n            select_shared(self)\n"
    if text.count(old) != 1:
        raise ValueError("native/API selector boundary differs")
    api_path.write_text(text.replace(old, new))
    note = root / "notes/native_n2_unit1_recovery_2026-10-25.json"
    note.write_text(json.dumps({"source": SOURCE, "common": COMMON, "copied": pins,
        "patch_files": list(PATCH_FILES), "patch_sha256": hashlib.sha256(patch).hexdigest(),
        "caller_cut": "RunSpec skips API-only select after exact native validation; shared_generation.py unchanged"}, indent=2) + "\n")


if __name__ == "__main__":
    main()
