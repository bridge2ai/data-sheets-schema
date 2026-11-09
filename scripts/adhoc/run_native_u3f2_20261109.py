"""U3-F2 sequential offline cohorts, 2026-11-09.

Inputs: committed source and explicit test nodes. Outputs: fresh assigned
scratch-native-u1u3/u3f2 evidence. Inherit U3-F's credential removal, OS network
and native-execution denial, origin checks and observed-descendant cleanup;
use a 3200-second test bound below this brief's 3300-second invocation ceiling.
No production or selected test deadline is changed.
"""
import importlib.util
import os
from pathlib import Path
import signal
import threading
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('u3f2_parent',
    ROOT / 'scripts/adhoc/run_native_u3f_20261109.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
f.r.w.__file__ = f.r.w.runner.__file__ = __file__
f.r.w.runner.DEADLINE = 3200


def bounded_popen(command, *args, **kwargs):
    child = f.r.original_popen(command, *args, **kwargs)
    if command and command[0] == '/usr/bin/sandbox-exec':
        def cutoff():
            if child.poll() is None:
                f.r.watchdog_events.append(dict(utc=datetime.now(timezone.utc).isoformat(),
                    pid=child.pid, cutoff_seconds=3250))
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    return
                try:
                    child.wait(timeout=5)
                except f.r.w.runner.subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
        timer = threading.Timer(3250, cutoff)
        timer.daemon = True
        timer.start()
        f.r.watchdogs.append(timer)
    return child


def bounded_parent(args):
    try:
        return f.r.supervised(args)
    finally:
        if args.out.is_dir():
            f.r.w.runner.save(args.out / 'early-cutoff.json',
                dict(cutoff_seconds=3250, events=f.r.watchdog_events))


f.r.guarded_popen = bounded_popen
f.r.w.runner.parent = bounded_parent

if __name__ == '__main__':
    f.r.w.runner.time = f.r.w.DeadlineClock()
    raise SystemExit(f.r.w.runner.main())
