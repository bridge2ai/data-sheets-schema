#!/usr/bin/env python3
"""Stop only this optional canary after ten minutes, retaining evidence, 2026-11-13.
Inputs own cohort PID witness; outputs cancellation request. No CPU monitoring.
Signals only the verified runner parent; its existing owned-process cleanup runs.
"""
from pathlib import Path
import json
import os
import signal
import sys
import time

R = Path(__file__).resolve().parents[2]
out = Path.home() / 'agent-work/data-sheets-schema/helper2-review-fixes-20261113/tests/unaffected-canary'
site = Path(sys.executable).absolute().parent.parent / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
sys.path.append(str(site))
import psutil
if (out / 'outcome.json').exists():
    print('already finished')
    raise SystemExit(0)
pid = json.loads((out / 'network.json').read_bytes())['pid']
worker = psutil.Process(pid)
parent = worker.parent()
command = parent.cmdline()
runner = str(R / 'scripts/adhoc/run_h2_review_fixes_20261113.py')
assert runner in command and '--worker' not in command
assert command[command.index('--out') + 1] == str(out)
elapsed = time.time() - parent.create_time()
if elapsed < 600:
    print(json.dumps({'status': 'still within optional 600-second bound', 'elapsed_seconds': elapsed}))
    raise SystemExit(0)
record = {'reason': 'optional pre-clock canary exceeded ten-minute diagnostic bound; current whole-file attempt already retained',
          'parent_pid': parent.pid, 'parent_created': parent.create_time(), 'worker_pid': pid,
          'elapsed_seconds': elapsed, 'signal': 'SIGINT', 'native_execution_authorized': False}
with (out / 'cancellation-request.json').open('x') as stream:
    json.dump(record, stream, indent=2); stream.write('\n')
os.kill(parent.pid, signal.SIGINT)
print(json.dumps(record))
