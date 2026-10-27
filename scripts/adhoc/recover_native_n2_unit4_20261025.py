#!/usr/bin/env python3
# Purpose: preserve reviewed native scanner/cache and offline acceptance-runner recovery.
# Inputs: retained db0573d96 and pre-owner a33d80d84 Git objects; owned N2 unit4 tree.
# Outputs: scanner/test delta, five acceptance utility/test files, exact source inventory.
# Issue: #4354 / N2; date: 2026-10-25. Offline only; no process launches or providers.
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

TRIAL = "db0573d96bb16ee32d3537ea0a9ad0ca607e355a"
DEFAULT = "a33d80d84c70cc9ee557f15d6e34fa73fc14f153"
BASE = "7c1002caeb776ccb0caebb474e22e5558b7b9602"
SCANNER = (".claude/skills/d4d-generation-specificity-audit/scan.py",
           "tests/test_generation_specificity_skill.py")
ADDITIONS = ("utils/native_ci_evidence.py", "utils/native_shared_acceptance.py",
             "tests/test_native_ci_evidence.py", "tests/test_native_ci_evidence_adversarial.py",
             "tests/test_native_shared_acceptance_runner.py",
             "tests/test_native_typed_catalog_scanner.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--output", default="notes/native_n2_unit4_recovery_2026-10-25.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0")

    def git(*args):
        return subprocess.run(["git", "--no-replace-objects", "-C", str(root), *args],
                              env=env, check=True, capture_output=True, timeout=30).stdout

    if git("branch", "--show-current").strip() != b"codex/n2-4-alignment-acceptance":
        raise ValueError("recovery is restricted to the owned unit4 branch")
    if not args.verify_only:
        for name in SCANNER:
            if (root / name).read_bytes() != git("show", f"{BASE}:{name}"):
                raise ValueError(f"scanner target differs from reviewed base: {name}")
        if any((root / name).exists() or (root / name).is_symlink() for name in ADDITIONS):
            raise ValueError("refusing to overwrite existing acceptance files")
    rows = [(TRIAL, name) for name in SCANNER] + [(DEFAULT, name) for name in ADDITIONS]
    content = [(ref, name, git("show", f"{ref}:{name}")) for ref, name in rows]
    for _, name, raw in content:
        if args.verify_only:
            if (root / name).read_bytes() != raw:
                raise ValueError(f"recovered content differs: {name}")
        else:
            (root / name).write_bytes(raw)
    report = {"kind": "native_n2_unit4_recovery", "files": [
        {"source": ref, "path": name, "bytes": len(raw),
         "sha256": hashlib.sha256(raw).hexdigest()} for ref, name, raw in content],
        "scope": "source reconstruction; no acceptance or runtime success implied"}
    output = root / args.output
    if output.parent.resolve() != root / "notes" or output.is_symlink():
        raise ValueError("inventory must be a new file in this checkout's notes directory")
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(output)


if __name__ == "__main__":
    main()
