#!/usr/bin/env python3
"""#5126 review-fix evidence producer, 2026-11-05.

Inputs: local Git commit or working evaluation tree, explicit pytest targets.
Outputs: temporary frozen archives, deadline-bound offline test/mutation logs.
Uses the existing validation driver; no network or provider execution.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import bc1_g2_validate_20261103 as driver
import validate_historical_evaluation_20261105 as validation

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("archive", "test", "mutate"))
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mutation", choices=("M2", "M3"))
    args, targets = parser.parse_known_args()
    os.environ.update(validation.ENV)
    for key in list(os.environ):
        if any(term in key.upper() for term in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")):
            os.environ.pop(key, None)
    if args.action == "archive":
        assert args.tree.is_absolute() and args.tree.is_relative_to(Path("/private/tmp"))
        driver.archive(args.ref, args.tree)
        common = validation.git("rev-parse", "--git-common-dir").decode().strip()
        objects = (ROOT / common / "objects").resolve()
        subprocess.run(["git", "init", "--quiet", str(args.tree)], check=True)
        (args.tree / ".git/objects/info/alternates").write_text(str(objects) + "\n")
        commit = json.loads((args.tree / ".g2-archive.json").read_bytes())["commit"]
        validation.git("update-ref", "--no-deref", "HEAD", commit, root=args.tree)
        validation.git("read-tree", commit, root=args.tree)
        validation.git("update-index", "--refresh", root=args.tree)
        validation.archive_identity(args.tree)
        return
    assert args.output and targets
    saved = None
    if args.action == "mutate":
        validation.archive_identity(args.tree)
        if args.mutation == "M2":
            path = args.tree / "src/data_sheets_schema/evaluation/historical_eval_binding.py"
            old, new = ' or len(value) != pin["bytes"]', ''
        else:
            path = args.tree / "src/data_sheets_schema/evaluation/registered_eval_runner.py"
            old = '    is_historical = authority_kind == "historical_provenance_v1"'
            new = ('    if authority_kind == "shared_generation_v1" and '
                   '_json(_read(Path(registration))).get("format") == "historical_artifact_binding_v1":\n'
                   '        authority_kind = "historical_provenance_v1"\n' + old)
        saved = path.read_bytes()
        assert saved.decode().count(old) == 1
        path.write_text(saved.decode().replace(old, new))
    try:
        command = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
                   sys.executable, "-B", str(ROOT / "scripts/adhoc/bc1_g2_validate_20261103.py"),
                   "test", str(args.tree), "--output", str(args.output), *targets,
                   "-q", "-n", "2", "--dist=load", "--maxschedchunk=1"]
        validation.save(args.output.with_suffix(".launcher.json"), {
            "command": command, "deadline_seconds": 3600, "mutation": args.mutation,
            "producer": validation.pin(Path(__file__)),
            "driver": validation.pin(ROOT / "scripts/adhoc/bc1_g2_validate_20261103.py")})
        result = subprocess.run(command, cwd=args.tree, timeout=3650)
        if saved is not None:
            report = json.loads((args.output / "result.json").read_bytes())
            assert result.returncode == 1 and sum(int(s["failures"]) for s in report["suites"]) > 0
        else:
            assert result.returncode == 0
    finally:
        if saved is not None:
            path.write_bytes(saved)
            validation.archive_identity(args.tree)


if __name__ == "__main__":
    main()
