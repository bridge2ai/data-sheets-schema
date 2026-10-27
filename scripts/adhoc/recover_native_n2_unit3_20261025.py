#!/usr/bin/env python3
# Purpose: recover the reviewed, default-only native probe/guard front door for N2/#4354.
# Inputs: local a33d80d84 Git objects; optional e81da8b98 bounded-pin patch.
# Outputs: five recovered source/test files and a SHA256 inventory; no live operations.
# Date: 2026-10-25. Run only in the owned unit3 branch; never fetch or publish.
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

SOURCE = "a33d80d84c70cc9ee557f15d6e34fa73fc14f153"
PIN_FIX = "e81da8b9852ce49a3af4e377b7b1cef91b4d1ee0"
FILES = (
    "src/data_sheets_schema/native_permission_probe.py",
    "src/data_sheets_schema/native_probe_provider.py",
    "src/data_sheets_schema/native_generation.py",
    "tests/test_native_permission_probe.py",
    "tests/test_native_subscription_guard.py",
)
PIN_FILES = (FILES[0], FILES[3])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("recover", "bounded-pin-fix"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0")

    def git(*argv):
        return subprocess.run(["git", "--no-replace-objects", "-C", str(root), *argv],
                              env=env, check=True, capture_output=True, timeout=30).stdout

    if git("branch", "--show-current").strip() != b"codex/n2-3-permission-guards":
        raise ValueError("recovery is restricted to the owned unit3 branch")
    if args.stage == "recover":
        rows = [(name, git("show", f"{SOURCE}:{name}")) for name in FILES]
        if any((root / name).exists() or (root / name).is_symlink() for name, _ in rows):
            raise ValueError("refusing to replace an existing source or test")
        for name, raw in rows:
            (root / name).write_bytes(raw)
    else:
        for name in PIN_FILES:
            if (root / name).read_bytes() != git("show", f"{SOURCE}:{name}"):
                raise ValueError(f"bounded pin fix requires exact archived source: {name}")
        for name in PIN_FILES:
            (root / name).write_bytes(git("show", f"{PIN_FIX}:{name}"))
    report = {
        "kind": "offline_native_n2_unit3_recovery",
        "stage": args.stage,
        "archived_source": SOURCE,
        "bounded_pin_fix": PIN_FIX if args.stage == "bounded-pin-fix" else None,
        "files": [{"path": name, "bytes": len((root / name).read_bytes()),
                   "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()}
                  for name in FILES],
        "scope": "source recovery only; no executable, account, provider or launch validation",
    }
    target = root / "notes" / f"native_n2_unit3_{args.stage}_2026-10-25.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(target)


if __name__ == "__main__":
    main()
