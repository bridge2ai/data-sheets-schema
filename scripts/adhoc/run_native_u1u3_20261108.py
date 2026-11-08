#!/usr/bin/env python3
"""U3-E assembly validation, 2026-11-08: committed source + explicit nodes
to scratch-native-u1u3 logs/XML/origins/host-load evidence. Offline PR handoff.
Reuse D10's supervised, credential-stripped, OS-denied validation path.
"""
import importlib.util
import os
from pathlib import Path
import sys
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

def supervised(args):
    before = {'utc': datetime.now(timezone.utc).isoformat(), 'load': os.getloadavg(), 'logical_cpus': os.cpu_count()}
    code = parent(args)
    w.runner.save(args.out / 'host-load.json', {'before': before, 'after': {'utc': datetime.now(timezone.utc).isoformat(), 'load': os.getloadavg()}})
    return code

w.runner.parent = supervised
if __name__ == '__main__':
    if sys.argv[1:] == ['--hydrate-local-dependency']:
        w.dependency.main()
    else:
        w.runner.time = w.DeadlineClock()
        raise SystemExit(w.runner.main())
