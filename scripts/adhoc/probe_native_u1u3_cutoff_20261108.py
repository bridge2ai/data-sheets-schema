#!/usr/bin/env python3
"""U3-E 2026-11-08: exercise the actual early-cutoff branch on a sleeping
ordinary Python peer. Input: assembly wrapper. Output: assigned scratch JSON.
The test compresses the watchdog interval only; no production/test deadline changes.
"""
import importlib.util
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u1u3'
if sys.argv[1:] == ['--peer']:
    time.sleep(60)
    raise SystemExit(0)
spec = importlib.util.spec_from_file_location('cutoff_probe', ROOT / 'scripts/adhoc/run_native_u1u3_20261108.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
original_timer = r.threading.Timer
r.threading.Timer = lambda seconds, callback: original_timer(1, callback)
started = time.monotonic()
child = r.guarded_popen(['/usr/bin/sandbox-exec', '-f', str(OUT / 'cutoff-canary/network-denied.sb'),
                         sys.executable, '-S', '-P', '-B', __file__, '--peer'], start_new_session=True)
code = child.wait(timeout=10)
elapsed = time.monotonic() - started
assert code == -15 and elapsed < 10 and len(r.watchdog_events) == 1
for timer in r.watchdogs:
    timer.join(timeout=2)
with (OUT / 'cutoff-probe.json').open('x') as f:
    json.dump({'returncode': code, 'seconds': elapsed, 'events': r.watchdog_events,
               'probe_interval_seconds': 1, 'normal_cutoff_seconds': 3300,
               'verified': 'actual guarded Popen path terminated its own ordinary Python process group'}, f, indent=2)
print('cutoff branch verified', elapsed, flush=True)
