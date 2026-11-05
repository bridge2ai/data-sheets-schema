#!/usr/bin/env python3
"""Launch one review-only SG2 portability witness for PR #5213, 2026-11-03.

Inputs: full pinned source/head/archive proof, variant/layout, fresh evidence.
Outputs: exact invocation record and unchanged strict-runner evidence below run/.
The ordinary nested SG2 child is deliberately unattested; its clean outer source
and explicit dirty/non-Git fixture construction remain independently attested.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

WITNESS = "scripts/adhoc/test_d76_round4_sg2_portability_20261103.py"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--archive-proof", type=Path, required=True)
    parser.add_argument("--variant", choices=("dirty-tracked", "non-git"), required=True)
    parser.add_argument("--layout", choices=("none", "explicit", "conventional"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode
    tree = args.tree.resolve(strict=True)
    if len(args.head) != 40 or any(c not in "0123456789abcdef" for c in args.head):
        raise ValueError("exact full commit required")
    if not args.output.is_absolute() or ".." in args.output.parts or args.output.exists() or args.output.is_symlink():
        raise ValueError("fresh absolute output required")
    if args.output.parent.resolve(strict=True) != args.output.parent or args.output.is_relative_to(tree):
        raise ValueError("physical output parent outside source required")
    if Path(__file__).resolve() != tree / "scripts/adhoc/run_d76_round4_portability_20261103.py":
        raise ValueError("use the launcher committed in the selected source archive")
    proof = args.archive_proof.resolve(strict=True)
    metadata = json.loads(proof.read_text())
    if metadata["head"] != args.head or metadata["destination"] != str(tree):
        raise ValueError("archive identity differs")
    target = WITNESS + "::test_real_sg2_works_without_clean_git_precondition[" + args.layout + "-" + args.variant + "]"
    command = [sys.executable, "-S", "-P", "-B",
        str(tree / "scripts/adhoc/run_d76_round3_validation_20261102.py"),
        "--tree", str(tree), "--expect-head", args.head, "--archive-proof", str(proof),
        "--output", str(args.output / "run"), "--target", target,
        "--workers", "0", "--deadline-seconds", "1800"]
    args.output.mkdir()
    record = {"head": args.head, "archive_proof": str(proof),
        "archive_proof_sha256": hashlib.sha256(proof.read_bytes()).hexdigest(),
        "command": command, "cwd": str(tree), "variant": args.variant, "layout": args.layout,
        "target": target, "workers": 0, "deadline_seconds": 1800,
        "witness_sha256": hashlib.sha256((tree / WITNESS).read_bytes()).hexdigest(),
        "review_only_trial": True, "nested_child_mode": "ordinary pytest without source attestation",
        "environment_additions": {"D4D_SG2_PORTABILITY_ARCHIVE_PROOF": str(proof),
                                  "D4D_SG2_PORTABILITY_HEAD": args.head}}
    with (args.output / "invocation.json").open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    env = dict(os.environ)
    env.update(record["environment_additions"])
    result = subprocess.run(command, cwd=tree, env=env)
    with (args.output / "launcher-result.json").open("x") as stream:
        json.dump({"returncode": result.returncode,
                   "scope": "literal strict-runner return code; expected-before failure is not a pass"},
                  stream, indent=2, sort_keys=True)
        stream.write("\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

