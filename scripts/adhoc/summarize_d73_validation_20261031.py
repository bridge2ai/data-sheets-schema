#!/usr/bin/env python3
"""#5212/D73, 2026-10-31: summarize retained offline pytest evidence.

Inputs: named external basetemp JSON reports and sibling logs.
Output: compact JSON counts, source identities, failed phases and worker proof.
Raw reports stay in scratch-5212fix; no unfinished run is counted as complete.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-5212fix"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("phases", nargs="+")
parser.add_argument("--output", type=Path)
args = parser.parse_args()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

summaries = []
for phase in args.phases:
    path = SCRATCH / phase / "d73-result.json"
    if not path.is_file():
        summaries.append({"phase": phase, "complete": False})
        continue
    raw = path.read_bytes()
    report = json.loads(raw)
    phases = report["reports"]
    calls = [item for item in phases if item["when"] == "call"]
    workers = report.get("worker_collections", {})
    assert all(ids == report["selected"] for ids in workers.values())
    log = SCRATCH / (phase + ".log")
    summaries.append({"phase": phase, "complete": True, "raw_report": str(path),
        "raw_sha256": sha(raw), "log_sha256": sha(log.read_bytes()) if log.is_file() else None,
        "exit_code": report["exit_code"], "environment": report["environment"],
        "command": report["command"], "canary_node": report.get("canary_node"),
        "selected": len(report["selected"]), "selected_sha256": sha(json.dumps(report["selected"]).encode()),
        "call_outcomes": dict(Counter(item["outcome"] for item in calls)),
        "skipped_phases": [item for item in phases if item["outcome"] == "skipped"],
        "failed_phases": [item for item in phases if item["outcome"] == "failed"],
        "passed_by_file": dict(Counter(item["nodeid"].split("::", 1)[0] for item in calls if item["outcome"] == "passed")),
        "collection_errors": report["collection_errors"],
        "worker_collections": {key: len(value) for key, value in workers.items()},
        "passing_nodes": [item["nodeid"] for item in calls if item["outcome"] == "passed" and
            any(key in item["nodeid"] for key in ("checkpoint_refuses", "the_repair_round_is_told",
                "fresh_restart_", "predecessor_binding_survives", "changed_inputs_in_portable",
                "legacy_progress_without_input", "changed_input_restart_recovers",
                "explicit_restart_preserves", "automatic_date_is_restored", "readable_repair_gets",
                "fresh_generation_archives", "portable_record_refuses_changed_instruction",
                "puts_the_display_on_the_wire"))]})
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summaries, indent=2) + "\n")
    assert args.output.stat().st_size
for row in summaries:
    print(json.dumps({key: row[key] for key in ("phase", "complete", "exit_code", "selected",
        "call_outcomes", "worker_collections") if key in row}))
    for failure in row.get("failed_phases", []):
        print(json.dumps(failure))
