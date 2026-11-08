#!/usr/bin/env python3
"""U3-E assembly validation, 2026-11-08: committed source + explicit nodes
to scratch-native-u1u3 logs/XML/origins/host-load evidence. Offline PR handoff.
Reuse D10's supervised, credential-stripped, OS-denied validation path.
"""
import importlib.util
import os
from pathlib import Path
import sys
import signal
import threading
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('u3e_d10', ROOT / 'scripts/adhoc/run_native_u3d_round9_20261107.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
w = d.wrapper
SCRATCH = w.runner.EXECUTIONS / 'scratch-native-u1u3'
w.SCRATCH = w.runner.SCRATCH = w.dependency.SCRATCH = SCRATCH
w.dependency.DESTINATION = SCRATCH / 'dependencies' / ('fairscape-' + w.dependency.PIN)
w.__file__ = w.runner.__file__ = __file__
w.runner.PROFILE = w.sandbox_profile()
parent = w.runner.parent
original_popen = w.runner.subprocess.Popen
watchdogs = []
watchdog_events = []

def guarded_popen(command, *args, **kwargs):
    child = original_popen(command, *args, **kwargs)
    if command and command[0] == '/usr/bin/sandbox-exec':
        # Independent of OwnedProcesses.observe(), whose repeated process-tree
        # traversal delayed the inherited deadline in the first broad run.
        # Leave 300 seconds for cleanup; never increase a selected attempt limit.
        def cutoff():
            if child.poll() is None:
                watchdog_events.append({'utc': datetime.now(timezone.utc).isoformat(),
                                        'pid': child.pid, 'cutoff_seconds': 3300})
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    return
                try:
                    child.wait(timeout=5)
                except w.runner.subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
        timer = threading.Timer(3300, cutoff)
        timer.daemon = True
        timer.start()
        watchdogs.append(timer)
    return child

def supervised(args):
    before = {'utc': datetime.now(timezone.utc).isoformat(), 'load': os.getloadavg(), 'logical_cpus': os.cpu_count()}
    w.runner.subprocess.Popen = guarded_popen
    try:
        code = parent(args)
    finally:
        for timer in watchdogs:
            timer.cancel()
        w.runner.subprocess.Popen = original_popen
        if args.out.is_dir():
            w.runner.save(args.out / 'early-cutoff.json', {'cutoff_seconds': 3300, 'events': watchdog_events})
    w.runner.save(args.out / 'host-load.json', {'before': before, 'after': {'utc': datetime.now(timezone.utc).isoformat(), 'load': os.getloadavg()}})
    return 125 if watchdog_events else code

w.runner.parent = supervised
if __name__ == '__main__':
    if sys.argv[1:] == ['--hydrate-local-dependency']:
        w.dependency.main()
    else:
        w.runner.time = w.DeadlineClock()
        raise SystemExit(w.runner.main())
