#!/usr/bin/env python3
# Purpose: exercise CI's native receipt-checker tests for #5364, 2026-10-29.
# Inputs: selected offline test modules and pytest options from the CI helper.
# Outputs: caller-selected log/XML; no edits to pinned notes or run directories.
"""Use through the existing -S -B offline launcher, after the tests/ suite."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CONTROLS = ROOT / "notes/matched_cborg_2026-09-13"
sys.path[:0] = [str(CONTROLS), str(CONTROLS / "native_controls")]
os.environ["PYTHONPATH"] = os.pathsep.join([*sys.path[:2], os.environ["PYTHONPATH"]])

import pytest

before = set((ROOT / "notes").rglob("*"))
result = pytest.main(["-q", "-p", "no:cacheprovider", *sys.argv[1:]])
assert set((ROOT / "notes").rglob("*")) == before, "offline tests added paths under notes/"
raise SystemExit(result)
