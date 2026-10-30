#!/usr/bin/env python3
"""D68-D70/#5212 evidence summary and d9 comparison, 2026-10-30.

Inputs: retained d9 archive, local phase JSON reports and specificity JSON.
Output: compact validation summary with artifact hashes and base failure IDs.
No raw evidence mutation, Git remotes or provider calls.
"""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
raw = ROOT / ".d68-validation"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--tag", default="merge-strict")
args = parser.parse_args()
archive = ROOT / "notes/reviews/d41_legacy_recovery_evidence_20261029/authentic_controls.tar.gz"
with tarfile.open(archive) as tar:
    old = json.load(tar.extractfile("ci/result.json"))
    old_collection = json.load(tar.extractfile("collect/result.json"))
base_failures = [row for row in old["reports"] if row["outcome"] == "failed"]
base_nodes = {(row["nodeid"], row["when"]) for row in base_failures}
summary = {"base": {"head": old["head"], "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    "failures": base_failures, "collection_errors": old_collection["collection_errors"]}, "runs": {}}
baseline_paths = list(raw.glob("base/.d68-validation/*/d68-result.json"))
same_restrictions = {}
for path in baseline_paths:
    data = json.loads(path.read_text())
    assert data["environment"]["head"] == old["head"]
    for row in data["reports"]:
        if row["outcome"] == "failed":
            same_restrictions.setdefault((row["nodeid"], row["when"]), []).append(str(path.relative_to(ROOT)))
paths = [*raw.glob("*/d68-result.json"), *raw.glob("merge/.d68-validation/*/d68-result.json"), *baseline_paths]
for path in sorted(paths):
    data = json.loads(path.read_text())
    failures = [row for row in data["reports"] if row["outcome"] == "failed"]
    for row in failures:
        key = (row["nodeid"], row["when"])
        row["original_d9_archive_failed"] = key in base_nodes
        row["same_restrictions_d9_evidence"] = same_restrictions.get(key, [])
        row["also_failed_on_d9"] = key in base_nodes or key in same_restrictions
    summary["runs"][path.parent.name] = {
        "source": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "exit_code": data["exit_code"], "head": data["environment"].get("head"),
        "selected": len(data["selected"]),
        "phases": dict(Counter(f'{r["when"]}:{r["outcome"]}' for r in data["reports"])),
        "collection_errors": data["collection_errors"], "failures": failures}
    if "shard" in path.parent.name or "routing-" in path.parent.name:
        required = {"test_latch_journal.py", "test_api_latch_guard.py", "test_pr5212_d55_fixes.py",
                    "test_d42_claude_d55.py", "test_pr5212_r3_fixes.py", "test_pr5212_r4_fixes.py",
                    "test_d41_request_parity.py"}
        selected = [node for node in data["selected"] if Path(node.split("::")[0]).name in required]
        summary["runs"][path.parent.name]["d41_selected"] = len(selected)
        summary["runs"][path.parent.name]["d41_call_outcomes"] = dict(Counter(
            row["outcome"] for row in data["reports"] if row["when"] == "call" and row["nodeid"] in selected))
specificity = raw / "specificity.json"
if specificity.exists():
    audit = json.loads(specificity.read_text())
    changed = []
    inherited_design = []
    for name in sorted({item["path"] for item in audit["violations"]}):
        old_file = subprocess.run(["git", "show", f"d9b69d84d:{name}"], cwd=ROOT, capture_output=True)
        if old_file.returncode or old_file.stdout != (ROOT / name).read_bytes():
            changed.append(name)
            design = subprocess.run(["git", "show", f"f5e78ff02:{name}"], cwd=ROOT, capture_output=True)
            if design.returncode == 0 and design.stdout == (ROOT / name).read_bytes():
                inherited_design.append(name)
    summary["specificity"] = {"violations": len(audit["violations"]),
                              "violation_files_changed_from_d9": changed,
                              "inherited_unchanged_from_design": inherited_design,
                              "introduced_since_d9": sum(item["path"] in changed for item in audit["violations"])}
dest = raw / "validation-summary.json"
merged = raw / "merge/.d68-validation"
gate = merged / f"{args.tag}-shards.json"
if gate.exists():
    stage = json.loads(gate.read_text())
    reports = [json.loads((merged.parent / row["report"]).read_text()) for row in stage["runs"]]
    collection_path = merged / f"{args.tag}-collect-ci/d68-result.json"
    collection = json.loads(collection_path.read_text()) if collection_path.exists() else None
    selected = Counter(node for data in reports for node in data["selected"])
    expected = Counter(collection["selected"]) if collection else Counter()
    completed = Counter(row["nodeid"] for data in reports for row in data["reports"] if row["when"] == "teardown")
    summary["final_coverage"] = {"tag": args.tag, "head": stage["head"], "runs": len(reports),
        "selected": sum(selected.values()), "expected": sum(expected.values()),
        "missing": list((expected - selected).elements()), "extra": list((selected - expected).elements()),
        "incomplete": list((selected - completed).elements()),
        "complete": len(reports) == 10 and bool(collection) and selected == expected == completed}
dest.write_text(json.dumps(summary, indent=2) + "\n")
for name, row in summary["runs"].items():
    print(name, row["exit_code"], row["selected"], row["phases"], "collection errors", len(row["collection_errors"]))
    for failure in row["failures"]:
        print("  FAIL", failure["nodeid"], failure["when"], "also d9:", failure["also_failed_on_d9"])
print("specificity", summary.get("specificity"))
coverage = summary.get("final_coverage")
print("coverage", ({key: len(value) if isinstance(value, list) else value
                    for key, value in coverage.items()} if coverage else None))
print("base failures", [(row["nodeid"], row["when"]) for row in base_failures])
