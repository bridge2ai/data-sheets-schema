#!/usr/bin/env python3
"""List one-record scorer plans for explicit labels; issue 6315, 2026-11-25.

Reads only selected records and instrument files. Never starts a scoring process.
"""
import argparse
import json
from pathlib import Path
import shlex
import sys

sys.dont_write_bytecode = True

from score_semantic_rubric_codex_20261125 import RUBRICS, ScorerError, build_plan, component, parser


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument("--method-directory", required=True)
    p.add_argument("--label", action="append", required=True)
    p.add_argument("--runs-root", type=Path, required=True)
    p.add_argument("--codex-binary", default="codex")
    p.add_argument("--poetry-binary", default="poetry")
    p.add_argument("--validation-venv", type=Path, default=Path(sys.prefix))
    p.add_argument("--auth-file", type=Path, default=Path.home() / ".codex/auth.json")
    p.add_argument("--plan", action="store_true", required=True)
    args = p.parse_args(argv)
    try:
        component(args.method_directory, "method")
        if len(set(args.label)) != len(args.label):
            raise ScorerError("duplicate label")
        plans = []
        invocations = []
        records = []
        for label in args.label:
            component(label, "label")
            source = args.repo_root / "data/d4d_concatenated" / args.method_directory / label
            selected = sorted(source.glob("*_d4d.yaml"))
            if not selected:
                raise ScorerError(f"no direct D4D records under the named label: {source}")
            for record in selected:
                records.append(str(record))
                for rubric in RUBRICS:
                    command = [sys.executable, str(Path(__file__).with_name("score_semantic_rubric_codex_20261125.py")),
                               "--repo-root", str(args.repo_root), "--method-directory", args.method_directory,
                               "--label", label, "--record", str(record), "--rubric", rubric,
                               "--run-directory", str(args.runs_root / (label + "__" + record.stem + "__" + rubric)),
                               "--codex-binary", args.codex_binary, "--poetry-binary", args.poetry_binary,
                               "--validation-venv", str(args.validation_venv), "--auth-file", str(args.auth_file), "--plan"]
                    plans.append(build_plan(parser().parse_args(command[2:])))
                    invocations.append(shlex.join(command))
        print(json.dumps({"mode": "PLAN_ONLY", "record_count": len(records),
                          "evaluation_count": len(plans), "records": records,
                          "invocations": invocations, "plans": plans}, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
