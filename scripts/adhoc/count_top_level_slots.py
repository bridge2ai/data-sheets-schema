"""Count populated top-level slots in one or more D4D YAML records.

Purpose: informational slot counts for a native D4D run's reconciliation report.
Inputs: paths to D4D records (YAML).
Outputs: one line per record: path, populated top-level slot count, line count (read-only).
Run: AI_READI 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1 (generic-v9 native run).
Date: 2026-11-21
"""
from __future__ import annotations

import sys

import yaml


def populated(v) -> bool:
    return v not in (None, "", [], {})


for p in sys.argv[1:]:
    text = open(p).read()
    rec = yaml.safe_load(text)
    n = sum(1 for v in rec.values() if populated(v))
    print(f"{p}\t{n}\t{len(text.splitlines())}")
