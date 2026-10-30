#!/usr/bin/env python3
"""D68-D70/#5212 evidence summary and d9 comparison, 2026-10-30.

Inputs: retained d9 archive, local phase JSON reports and specificity JSON.
Output: compact validation summary with artifact hashes and base failure IDs.
No raw evidence mutation, Git remotes or provider calls.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
raw = ROOT / ".d68-validation"
archive = ROOT / "notes/reviews/d41_legacy_recovery_evidence_20261029/authentic_controls.tar.gz"
with tarfile.open(archive) as tar:
    old = json.load(tar.extractfile("ci/result.json"))
base_failures = [row for row in old["reports"] if row["outcome"] == "failed"]
base_nodes = {row["nodeid"] for row in base_failures}
summary = {"base": {"head": old["head"], "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    "failures": base_failures}, "runs": {}}
for path in sorted(raw.glob("*/d68-result.json")):
    data = json.loads(path.read_text())
    failures = [row for row in data["reports"] if row["outcome"] == "failed"]
    for row in failures:
        row["also_failed_on_d9"] = row["nodeid"] in base_nodes
    summary["runs"][path.parent.name] = {
        "source": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "exit_code": data["exit_code"], "head": data["environment"].get("head"),
        "selected": len(data["selected"]),
        "phases": dict(Counter(f'{r["when"]}:{r["outcome"]}' for r in data["reports"])),
        "collection_errors": data["collection_errors"], "failures": failures}
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
dest.write_text(json.dumps(summary, indent=2) + "\n")
for name, row in summary["runs"].items():
    print(name, row["exit_code"], row["selected"], row["phases"], "collection errors", len(row["collection_errors"]))
    for failure in row["failures"]:
        print("  FAIL", failure["nodeid"], failure["when"], "also d9:", failure["also_failed_on_d9"])
print("specificity", summary.get("specificity"))
