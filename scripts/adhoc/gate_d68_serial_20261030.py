#!/usr/bin/env python3
"""D68-D70/#5212 serial integration gates, 2026-10-30.

Input: installed Python and stage; run from the packet/scratch merge worktree.
Output: per-process JSON reports under .d68-validation and a stage ledger.
Canary exercises the exact sandbox/launcher/subprocess path before shard fanout.
No remotes, provider calls or concurrency. CI test selection, native interpreter.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("python")
parser.add_argument("stage", choices=("canary", "collect", "shards"))
parser.add_argument("--tag", default="merge-final")
args = parser.parse_args()
storage = ROOT / ".d68-validation"
storage.mkdir(exist_ok=True)
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

if args.stage == "shards":
    subprocess.run(["git", "merge-base", "--is-ancestor", "50bc50af6", head], cwd=ROOT, check=True)
    canary = json.loads((storage / f"{args.tag}-canary.json").read_text())
    assert canary["head"] == head and canary["runs"][0]["exit_code"] == 0

if args.stage == "canary":
    cases = [("canary", ["tests/test_d68_legacy_readonly.py::test_completed_legacy_verifier_is_readonly[i1]"])]
elif args.stage == "collect":
    cases = [("collect-whole", ["--collect-only"]), ("collect-ci", ["tests", "--collect-only"])]
else:
    cases = [(f"shard-{i}-of-6", ["tests", "-p", "utils.pytest_shard", f"--ci-shard={i}/6",
               "--ci-shard-timings=utils/ci_test_durations.json", "--ci-lane=ordinary"])
             for i in range(1, 7)]
    cases += [(lane, ["tests", "-p", "utils.pytest_shard", f"--ci-lane={lane}"])
              for lane in ("routing-dispatch", "routing-portable", "routing-regate", "routing-default-layout")]

ledger = {"head": head, "stage": args.stage, "runs": []}
destination = storage / f"{args.tag}-{args.stage}.json"
for name, selected in cases:
    base = storage / f"{args.tag}-{name}"
    assert not base.exists(), f"preserve prior gate: {base}"
    command = ["/usr/bin/sandbox-exec", "-D", f"TREE={ROOT}", "-f",
               str(ROOT / "scripts/adhoc/d68_offline_20261030.sb"), args.python,
               "-S", "-P", "-B", str(ROOT / "scripts/adhoc/run_d68_offline_20261030.py"),
               *selected, "-q", "--tb=short", "--basetemp", str(base)]
    print(f"START {name} {head}", flush=True)
    code = subprocess.run(command, cwd=ROOT).returncode
    report = base / "d68-result.json"
    result = json.loads(report.read_text())
    assert report.stat().st_size and result["environment"]["head"] == head
    row = {"name": name, "exit_code": code, "selected": len(result["selected"]),
           "collection_errors": len(result["collection_errors"]), "report": str(report.relative_to(ROOT))}
    ledger["runs"].append(row)
    destination.write_text(json.dumps(ledger, indent=2) + "\n")
    print(f"FINISH {json.dumps(row)}", flush=True)
    if args.stage == "canary":
        assert code == 0 and row["selected"] == 1
    if args.stage == "shards":
        assert not result["collection_errors"]
        assert len([r for r in result["reports"] if r["when"] == "teardown"]) == row["selected"]
print(f"COMPLETE {destination}", flush=True)
