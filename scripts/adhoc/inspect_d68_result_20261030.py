#!/usr/bin/env python3
"""D68-D70/#5212 review item 7: inspect retained pytest evidence, 2026-10-30.

Input: one d68-result.json. Output: phase counts, collection errors and failures
to stdout. Never changes a report or reruns a case.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("report", type=Path)
parser.add_argument("--limit", type=int)
parser.add_argument("--progress-log", type=Path, help="Estimate current case from quiet progress and a CI collection report")
parser.add_argument("--shard", help="Ordinary CI shard INDEX/TOTAL for --progress-log")
args = parser.parse_args()
data = json.loads(args.report.read_text())
if args.progress_log:
    assert args.shard
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from utils.pytest_shard import API_CASE_LANES, balanced_files, read_weights, _estimates
    index, total = map(int, args.shard.split("/"))
    nodes = [node for node in data["selected"] if node not in API_CASE_LANES.values()]
    weights = read_weights(root / "utils/ci_test_durations.json")
    owners = balanced_files((node.split("::")[0] for node in nodes), total, weights)
    selected = [node for node in nodes if owners[node.split("::")[0]] == index]
    counts = Counter(node.split("::")[0] for node in selected)
    estimates = _estimates(counts, weights)
    selected.sort(key=lambda node: -estimates[node.split("::")[0]] / counts[node.split("::")[0]])
    completed = sum(len(match[1]) for line in args.progress_log.read_text().splitlines()
                    if (match := re.fullmatch(r"([.FEsxX]+)(?:\s+\[\s*\d+%\])?", line)))
    print(json.dumps({"estimated_completed": completed, "selected": len(selected),
        "near_current": selected[max(0, completed - 2):completed + 3],
        "limitation": "Quiet progress is approximate if a test has multiple failed phases"}, indent=2))
    raise SystemExit(0)
print("head", data["environment"]["head"], "exit", data["exit_code"], "selected", len(data["selected"]))
print(dict(Counter(f'{row["when"]}:{row["outcome"]}' for row in data["reports"])))
for row in data["collection_errors"]:
    print("COLLECTION", row)
shown = 0
for row in data["reports"]:
    if row["outcome"] == "failed":
        if args.limit is not None and shown >= args.limit:
            break
        print("FAIL", row["nodeid"], row["when"])
        print(row["message"])
        shown += 1
