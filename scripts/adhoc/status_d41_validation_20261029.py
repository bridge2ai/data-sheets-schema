#!/usr/bin/env python3
"""#5212, 2026-10-29: summarize retained serial pytest progress, read-only.

Input: evidence root with per-mode collected.json/reports.jsonl/result.json.
Output: JSON status on stdout. In-flight incomplete final lines are ignored.
"""
import json
from collections import Counter
from pathlib import Path
import sys

root = Path(sys.argv[1])
for name in ("ci-canary", "ci-observer-canary", "collect", "suites", "ci", "collect-tests"):
    folder = root / name
    if not folder.is_dir():
        continue
    rows = []
    for line in (folder / "reports.jsonl").read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    try:
        collected = len(json.loads((folder / "collected.json").read_bytes()))
    except (OSError, ValueError):
        collected = None
    result = json.loads((folder / "result.json").read_bytes()) if (folder / "result.json").exists() else None
    counts = Counter(r["outcome"] for r in rows if r["when"] == "call")
    print(json.dumps({"stage": name, "collected": collected,
                      "completed": sum(r["when"] == "teardown" for r in rows),
                      "calls": dict(counts), "last": rows[-1]["nodeid"] if rows else None,
                      "setup_errors": sum(r["when"] == "setup" and r["outcome"] == "failed" for r in rows),
                      "teardown_errors": sum(r["when"] == "teardown" and r["outcome"] == "failed" for r in rows),
                      "setup_skips": sum(r["when"] == "setup" and r["outcome"] == "skipped" for r in rows),
                      "exit_code": result["exit_code"] if result else None,
                      "collection_errors": len(result["collection_errors"]) if result else None}))
