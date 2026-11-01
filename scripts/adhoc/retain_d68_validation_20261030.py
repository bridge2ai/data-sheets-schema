#!/usr/bin/env python3
"""D68-D70/#5212 review items 3 and 7: retain final evidence, 2026-10-30.

Inputs: completed serial gate, census JSON, phase summary and baseline controls.
Outputs: compact committed phase ledger, per-record census, failure ledger and
artifact hashes. Raw reports stay in local scratch; no remote/provider actions.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--tag", required=True)
parser.add_argument("--notes-tag", required=True)
parser.add_argument("--extra-run", action="append", default=[], help="Also retain a focused or D41 report by run name")
parser.add_argument("--resolved-file", type=Path, help="Reviewed dispositions for repaired introduced failures")
parser.add_argument("--focused-run", required=True)
parser.add_argument("--census-tag", default="final")
args = parser.parse_args()
raw = ROOT / ".d68-validation"
merge = raw / "merge"
summary = json.loads((raw / "validation-summary.json").read_text())
coverage = summary["final_coverage"]
assert coverage["tag"] == args.tag and coverage["complete"], coverage
stage = json.loads((merge / ".d68-validation" / f"{args.notes_tag}-notes.json").read_text())
assert len(stage["runs"]) == 4
subprocess.run(["git", "diff", "--exit-code", stage["head"], coverage["head"],
                "--", "src", "notes", ".github", "tests/fixtures"], cwd=ROOT, check=True)
notes_reports = [json.loads((merge / row["report"]).read_text()) for row in stage["runs"]]
notes_selected_files = sorted({node.split("::")[0] for report in notes_reports for node in report["selected"]})
subprocess.run(["git", "diff", "--exit-code", stage["head"], coverage["head"],
                "--", *notes_selected_files], cwd=ROOT, check=True)
selected = {Path(row["report"]).parent.name for row in coverage["job_reports"]}
selected.update(f"{args.tag}-{name}" for name in ("collect-ci", "collect-whole", "canary"))
selected.update(f"{args.notes_tag}-{row['name']}" for row in stage["runs"])
selected.add(args.focused_run)
selected.update(args.extra_run)
assert selected.issubset(summary["runs"]), selected - summary["runs"].keys()
failures = []
for name in sorted(selected):
    assert all(row["same_error_lines_on_d9"] for row in summary["runs"][name]["collection_base_evidence"]), name
    for row in summary["runs"][name]["failures"]:
        failures.append({"run": name, **row})
assert all(row["also_failed_on_d9"] for row in failures), [
    row["nodeid"] for row in failures if not row["also_failed_on_d9"]]
baseline_sources = {source for row in failures for source in row["same_restrictions_d9_evidence"]}
for name, row in summary["runs"].items():
    if row["source"] in baseline_sources:
        selected.add(name)

destination = ROOT / "notes/reviews/d41_legacy_impl_d68_d70_evidence_20261030"
assert not destination.exists(), "preserve previous retained evidence"
destination.mkdir()
ledger = {}
for name in sorted(selected):
    brief = summary["runs"][name]
    path = ROOT / brief["source"]
    data = json.loads(path.read_text())
    phases = {}
    for row in data["reports"]:
        phases.setdefault(row["nodeid"], {})[row["when"]] = row["outcome"]
    ledger[name] = {"source": brief["source"], "sha256": brief["sha256"],
        "environment": data["environment"], "command": data["command"],
        "exit_code": data["exit_code"], "collection_errors": data["collection_errors"],
        "collection_base_evidence": brief["collection_base_evidence"],
        "counts": brief["phases"], "failures": [{key: value for key, value in row.items() if key != "message"}
                                                for row in brief["failures"]],
        "cases": [[node, phases.get(node, {})] for node in data["selected"]]}

def write(name, value):
    path = destination / name
    path.write_text(json.dumps(value, indent=2) + "\n")
    assert path.stat().st_size

write("phase-ledger.json", ledger)
write("failure-ledger.json", failures)
write("coverage.json", {**coverage, "notes_head": stage["head"], "notes_runs": stage["runs"]})
write("baseline-archive.json", summary["base"])
write("specificity.json", summary.get("specificity"))
if args.resolved_file:
    dispositions = json.loads(args.resolved_file.read_text())
    assert dispositions and all(row["resolution_verified"] for row in dispositions)
    write("resolved-findings.json", dispositions)
lines = ["# Remaining failures and d9 evidence", "",
         "Every row names the exact phase and retained baseline evidence. These",
         "are failures under the declared offline/nested-checkout environment.", ""]
for row in failures:
    lines.extend([f"- `{row['run']}`: `{row['nodeid']}` ({row['when']}).",
                  "  Baseline: " + ("; ".join(f"`{value}`" for value in row["same_restrictions_d9_evidence"])
                  or "original d9 archive, exact node and phase") + "."])
(destination / "failures.md").write_text("\n".join(lines) + "\n")
for name in (f"corpus-{scope}-{args.census_tag}" for scope in ("base", "packet", "merge")):
    source = raw / f"{name}.json"
    census = json.loads(source.read_text())
    assert not census["parse_errors"] and census["counts"]["v8_changes"] == 0
    shutil.copyfile(source, destination / source.name)
for source in sorted(raw.glob("failure-comparison-*.json")):
    comparison = json.loads(source.read_text())
    assert comparison["paired"] == len(comparison["failures"])
    shutil.copyfile(source, destination / source.name)
manifest = {path.name: {"bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in sorted(destination.iterdir())}
write("manifest.json", manifest)
print(json.dumps({"destination": str(destination), "runs": len(ledger),
                  "failure_phases": len(failures), "counts": dict(Counter(row["run"] for row in failures)),
                  "bytes": sum(row["bytes"] for row in manifest.values())}, indent=2))
