#!/usr/bin/env python3
"""Attribute scanner refusal without changing its contracts, 2026-11-13.
Input: closed admitted export and completed queued guard cohort. Output:
isolated baseline scanner outcome, serialized behind existing validation.
"""
from pathlib import Path
import subprocess
import sys
import time

R = Path(__file__).resolve().parents[2]
B = Path.home() / 'agent-work/data-sheets-schema/helper2-pins-admission-20261113'
while not (B / 'tests/generation-guards/outcome.json').exists():
    time.sleep(5)
time.sleep(2)
command = [sys.executable, '-S', '-P', '-B', str(R / 'scripts/adhoc/run_h2_pins_admission_20261113.py'),
    '--tree', str(B / 'fixed'), '--out', str(B / 'tests/admitted-scanner-baseline'),
    '--workers', '0', '--timeout-seconds', '1800', '--scanner']
raise SystemExit(subprocess.run(command, cwd=R).returncode)
