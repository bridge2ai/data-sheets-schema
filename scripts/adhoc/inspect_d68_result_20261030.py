#!/usr/bin/env python3
"""D68-D70/#5212 review item 7: inspect retained pytest evidence, 2026-10-30.

Input: one d68-result.json. Output: phase counts, collection errors and failures
to stdout. Never changes a report or reruns a case.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("report", type=Path)
args = parser.parse_args()
data = json.loads(args.report.read_text())
print("head", data["environment"]["head"], "exit", data["exit_code"], "selected", len(data["selected"]))
print(dict(Counter(f'{row["when"]}:{row["outcome"]}' for row in data["reports"])))
for row in data["collection_errors"]:
    print("COLLECTION", row)
for row in data["reports"]:
    if row["outcome"] == "failed":
        print("FAIL", row["nodeid"], row["when"])
        print(row["message"])
