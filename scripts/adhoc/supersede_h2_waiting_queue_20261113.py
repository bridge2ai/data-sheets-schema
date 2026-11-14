#!/usr/bin/env python3
"""Supersede only helper 2's idle fixed2 validation queue, 2026-11-13.
Inputs: exact recorded PID and command; output: retained termination receipt.
Issue 6195's final source change needs a fresh export. Never stop active tests.
"""
import json
import argparse
from pathlib import Path
import os
import signal
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = Path.home() / 'agent-work/data-sheets-schema/helper2-integration-fixes-20261113'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pid', type=int, required=True)
parser.add_argument('--export', choices=('fixed2', 'fixed3'), required=True)
args = parser.parse_args()
PID = args.pid
expected = ('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python '
    '-S -P -B scripts/adhoc/validate_h2_integration_20261113.py ' + args.export + ' unit-canary '
    '--stop-on-failure --after preload-pending')
command = subprocess.check_output(['/bin/ps', '-p', str(PID), '-o', 'command='], text=True).strip()
assert command == expected, command
table = subprocess.check_output(['/bin/ps', '-ax', '-o', 'pid=,ppid='], text=True)
assert not any(int(row.split()[1]) == PID for row in table.splitlines()), 'queue has children'
cwd = subprocess.check_output(['/usr/sbin/lsof', '-a', '-p', str(PID), '-d', 'cwd', '-Fn'], text=True)
assert '\nn' + str(ROOT) + '\n' in cwd, cwd
assert not (BASE / 'tests' / (args.export + '-unit-canary')).exists(), 'queue already started'
out = BASE / ('superseded-' + args.export + '-queue.json')
with out.open('x') as stream:
    os.kill(PID, signal.SIGTERM)
    json.dump({'pid': PID, 'command': command, 'no_children': True,
        'cwd': str(ROOT), 'action': 'SIGTERM idle queue; retain export; no active tests stopped'}, stream, indent=2)
    stream.write('\n')
print(out)
