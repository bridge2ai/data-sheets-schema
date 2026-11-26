#!/usr/bin/env python3
"""Summarize offline plans/scans and optionally check real Poetry; issue 6315, 2026-11-25.

Reads saved evidence; writes summary and validator receipts. Never calls Codex.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-directory", type=Path, required=True)
    parser.add_argument("--plan-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--real-poetry-plan", type=Path)
    parser.add_argument("--poetry-binary", default="/Users/marcin/.pyenv/shims/poetry")
    parser.add_argument("--branch-scan", default="scanner-branch.json")
    args = parser.parse_args()
    bundle = json.loads(args.plan_file.read_bytes())
    result = {"plan_file": str(args.plan_file), "plan_sha256": digest(args.plan_file),
              "records": bundle["record_count"], "evaluations": bundle["evaluation_count"],
              "record_paths_unique": len(set(bundle["records"])),
              "outputs_unique": len({row["output"] for row in bundle["plans"]}),
              "run_directories_created": [row["run_directory"] for row in bundle["plans"]
                                          if Path(row["run_directory"]).exists()],
              "rubric_inputs": {row["identity"]["rubric"]: row["inputs"]
                                for row in bundle["plans"]}}
    scans = [args.evidence_directory / name for name in ("scanner-base.json", args.branch_scan)]
    if all(path.exists() for path in scans):
        documents = [json.loads(path.read_bytes()) for path in scans]
        result["scanner_sha256"] = {path.name: digest(path) for path in scans}
        result["scanner_comparison"] = {}
        for key in ("hits", "violations", "test_dependencies"):
            before, after = (document[key] for document in documents)
            counts = [Counter(json.dumps(item, sort_keys=True) for item in rows) for rows in (before, after)]
            result["scanner_comparison"][key] = {
                "before_count": len(before), "after_count": len(after), "ordered_equal": before == after,
                "added": [json.loads(item) for item in (counts[1] - counts[0]).elements()],
                "removed": [json.loads(item) for item in (counts[0] - counts[1]).elements()],
            }
    if args.real_poetry_plan:
        plan = json.loads(args.real_poetry_plan.read_bytes())
        command = [args.poetry_binary, *plan["validation_command"][1:]]
        run = Path(plan["run_directory"])
        venv = Path(plan["validation_venv"])
        env = {"PATH": str(venv / "bin") + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
               "HOME": str(run / "home"), "VIRTUAL_ENV": str(venv),
               "POETRY_VIRTUALENVS_CREATE": "false", "PIP_NO_INDEX": "1",
               "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        completed = subprocess.run(command, cwd=plan["validation_cwd"], env=env,
                                   capture_output=True, timeout=120)
        stdout = args.output.with_suffix(".poetry-stdout.txt")
        stderr = args.output.with_suffix(".poetry-stderr.txt")
        with stdout.open("xb") as handle:
            handle.write(completed.stdout)
        with stderr.open("xb") as handle:
            handle.write(completed.stderr)
        result["real_poetry"] = {"command": command, "cwd": plan["validation_cwd"],
                                 "returncode": completed.returncode,
                                 "stdout": str(stdout), "stderr": str(stderr)}
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"summary": str(args.output), "sha256": digest(args.output),
                      "records": result["records"], "evaluations": result["evaluations"],
                      "scanner": {key: {name: item[name] for name in ("before_count", "after_count", "ordered_equal")}
                                  for key, item in result.get("scanner_comparison", {}).items()},
                      "real_poetry_exit": result.get("real_poetry", {}).get("returncode")}, indent=2))
    return int(result.get("real_poetry", {}).get("returncode", 0) != 0)


if __name__ == "__main__":
    sys.exit(main())
