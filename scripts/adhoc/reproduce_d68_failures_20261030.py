#!/usr/bin/env python3
"""D68-D70/#5212 review item 7: same-restriction d9 controls, 2026-10-30.

Inputs: retained phase reports and a successful baseline launcher canary.
Outputs: immutable reproduction plan and one report/log per serial baseline
process. --plan performs free checks only. No tracked baseline edits or remotes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from d68_process_logging_20261030 import run_logged

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--tag", required=True)
parser.add_argument("--canary", required=True, type=Path)
parser.add_argument("--full-selection", action="store_true")
parser.add_argument("--plan", action="store_true")
parser.add_argument("--exclude-file", action="append", default=[],
                    help="Explicitly record (not reproduce) failures in a test file absent from committed d9")
parser.add_argument("reports", nargs="+", type=Path)
args = parser.parse_args()
base_root = ROOT / ".d68-validation/base"
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=base_root, text=True).strip()
assert head == "d9b69d84d9a6936809681ae240bb8e767649ca11"
subprocess.run(["git", "diff", "--exit-code", "HEAD"], cwd=base_root, check=True)
tracked = set(subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "-z", head],
                                     cwd=base_root).decode().split("\0"))
assert not (args.full_selection and args.exclude_file), "full selection cannot exclude failures"
assert all(name not in tracked for name in args.exclude_file), "exclusions must be absent from committed d9"
archive = ROOT / "notes/reviews/d41_legacy_recovery_evidence_20261029/authentic_controls.tar.gz"
with tarfile.open(archive) as tar:
    original_collection = json.load(tar.extractfile("collect/result.json"))
assert original_collection["head"] == head
original_nodes = set(original_collection["collected"])
canary = json.loads(args.canary.read_text()) if args.canary.exists() else None
assert canary is not None or args.plan, "run the baseline launcher canary first"
if canary is not None:
    assert canary["environment"]["head"] == head and canary["exit_code"] == 0
    assert len(canary["selected"]) == 1 and len(canary["reports"]) == 3
    assert all(row["outcome"] == "passed" for row in canary["reports"])
cases = []
excluded = []
for source in args.reports:
    data = json.loads(source.read_text())
    failed = list(dict.fromkeys(row["nodeid"] for row in data["reports"] if row["outcome"] == "failed"))
    excluded.extend({"source": str(source), "nodeid": node,
                     "reason": "test file absent from committed d9; requires separate introduced-failure disposition"}
                    for node in failed if node.split("::")[0] in args.exclude_file)
    failed = [node for node in failed if node.split("::")[0] not in args.exclude_file]
    assert all(node.split("::")[0] in tracked for node in failed), [
        node for node in failed if node.split("::")[0] not in tracked]
    assert all(node in original_nodes for node in failed), [
        node for node in failed if node not in original_nodes]
    if not failed:
        continue
    if canary is not None:
        assert data["environment"]["notes_controls"] == canary["environment"]["notes_controls"]
    scratch = base_root / ".d68-validation" / f"{args.tag}-{source.parent.name}"
    assert not scratch.exists(), scratch
    if args.full_selection:
        selected = list(data["command"])
        assert not any(word.startswith("--ci-shard") for word in selected)
        selected[selected.index("--basetemp") + 1] = str(scratch)
    else:
        selected = [*failed, "-q", "--tb=short", "--basetemp", str(scratch)]
    cases.append({"source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "failed_nodes": failed, "scratch": str(scratch), "args": selected})
plan = {"baseline_head": head, "canary": str(args.canary), "canary_verified": canary is not None,
        "original_collection_archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "full_selection": args.full_selection, "cases": cases, "excluded_not_in_d9": excluded}
destination = ROOT / ".d68-validation" / f"reproduction-{args.tag}.json"
print(json.dumps(plan, indent=2), flush=True)
if args.plan:
    raise SystemExit(0)
assert not destination.exists(), destination
destination.write_text(json.dumps(plan, indent=2) + "\n")
outcomes = []
for case in cases:
    scratch = Path(case["scratch"])
    command = ["/usr/bin/sandbox-exec", "-D", f"TREE={base_root}", "-f",
               str(base_root / "scripts/adhoc/d68_offline_20261030.sb"), sys.executable,
               "-S", "-P", "-B", str(base_root / "scripts/adhoc/run_d68_offline_20261030.py"), *case["args"]]
    print("START", scratch.name, flush=True)
    code = run_logged(command, scratch, cwd=base_root)
    report = scratch / "d68-result.json"
    data = json.loads(report.read_text())
    assert data["environment"]["head"] == head and not data["collection_errors"]
    assert len(data["selected"]) == len([row for row in data["reports"] if row["when"] == "teardown"])
    outcome = {"source": case["source"], "report": str(report), "exit_code": code,
               "selected": len(data["selected"]), "failed_nodes": list(dict.fromkeys(
                   row["nodeid"] for row in data["reports"] if row["outcome"] == "failed"))}
    outcomes.append(outcome)
    destination.with_suffix(".results.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print("FINISH", json.dumps(outcome), flush=True)
    subprocess.run(["git", "diff", "--exit-code", "HEAD"], cwd=base_root, check=True)
