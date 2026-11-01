#!/usr/bin/env python3
"""D68-D70/#5212 review item 7: compare failure causes, 2026-10-30.

Inputs: merge and unchanged-d9 phase reports. Output: exact-node/phase paired
traces and error-line groups for human review; matching names alone proves no
cause equivalence. No tests, writes to evidence inputs, or network operations.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("current", type=Path)
parser.add_argument("baseline", type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
current = json.loads(args.current.read_text())
baseline = json.loads(args.baseline.read_text())
assert baseline["environment"]["head"] == "d9b69d84d9a6936809681ae240bb8e767649ca11"
base_failures = {(row["nodeid"], row["when"]): row for row in baseline["reports"] if row["outcome"] == "failed"}

def cause(message):
    lines = [line.strip() for line in message.splitlines() if re.match(r"^E\s", line)]
    return lines or message.splitlines()[-1:]

rows = []
for row in current["reports"]:
    if row["outcome"] != "failed":
        continue
    old = base_failures.get((row["nodeid"], row["when"]))
    rows.append({"nodeid": row["nodeid"], "when": row["when"],
                 "current_cause": cause(row["message"]),
                 "baseline_cause": cause(old["message"]) if old else None,
                 "current_trace": row["message"], "baseline_trace": old["message"] if old else None})
data = {"current": str(args.current), "baseline": str(args.baseline),
        "current_head": current["environment"]["head"], "baseline_head": baseline["environment"]["head"],
        "paired": sum(row["baseline_trace"] is not None for row in rows), "failures": rows}
args.output.write_text(json.dumps(data, indent=2) + "\n")
print("failed phases", len(rows), "paired", data["paired"])
groups = Counter((tuple(row["current_cause"]), tuple(row["baseline_cause"] or [])) for row in rows)
for (new, old), count in groups.items():
    print(json.dumps({"count": count, "current": new, "baseline": old}))
assert data["paired"] == len(rows)
