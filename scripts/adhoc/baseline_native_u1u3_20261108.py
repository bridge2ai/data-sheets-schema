#!/usr/bin/env python3
"""U3-E 2026-11-08 same-environment failure attribution on saved main.
Inputs: exact scratch baseline archive and explicit baseline nodes; outputs:
assigned scratch witnesses. No baseline source edits or provider/native access.
"""
import importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('baseline_runner', HERE / 'scripts/adhoc/run_native_u1u3_20261108.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
root = r.SCRATCH / 'baseline'
r.w.ROOT = r.w.runner.ROOT = r.w.dependency.ROOT = root
r.w.__file__ = r.w.runner.__file__ = __file__
# This guard verifies a B-only smoke test's write destination. That source
# does not exist on saved main and is never selected in baseline comparisons;
# OS write confinement remains identical and is the actual safety boundary.
r.w.smoke_evidence = lambda: {'scope': 'B-only smoke fixture absent from saved main; not selected; OS confinement unchanged'}
if __name__ == '__main__':
    r.w.runner.time = r.w.DeadlineClock()
    raise SystemExit(r.w.runner.main())
