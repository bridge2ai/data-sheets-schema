#!/usr/bin/env python3
"""Recover only the idle helper-2 queue after daemon restart, 2026-11-13.
Input: explicitly inspected queue PID; output: termination identity receipt.
Refuses any child, nonmatching command/cwd, or completed admitted cohort.
Never signals the active test runner, workers, native binaries or other helpers.
"""
import argparse
import json
from pathlib import Path

import psutil

R = Path(__file__).resolve().parents[2]
B = Path.home() / 'agent-work/data-sheets-schema/helper2-pins-admission-20261113'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pid', type=int, required=True)
args = parser.parse_args()
assert not (B / 'tests/admitted-touched-files/outcome.json').exists()
process = psutil.Process(args.pid)
cmd = process.cmdline()
assert cmd[1:] == ['-S', '-P', '-B', 'scripts/adhoc/check_h2_admission_changes_20261113.py'], cmd
assert Path(process.cwd()) == R and process.ppid() == 1
assert not process.children(recursive=True)
record = dict(pid=process.pid, created=process.create_time(), command=cmd,
    cwd=process.cwd(), children=[], reason='daemon restart disconnected inherited stdout; queue was still waiting')
process.terminate()
process.wait(timeout=10)
record['terminated'] = True
path = B / 'queue-recovery.json'
with path.open('x') as stream: json.dump(record, stream, indent=2); stream.write('\n')
print(path)
