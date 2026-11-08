#!/usr/bin/env python3
"""U5 offline validation launcher, 2026-11-08 (#4354).

Inputs: committed preparation checkout, explicit pytest nodes and physical
dependency venv Python with -S -P -B. Outputs: new assigned U5 scratch runs.
Reuses U4's reviewed credential removal, network/native-executable denial,
source witnesses, quiet-window cooperation and 3600-second dual-clock bound.
"""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / 'scripts/adhoc/run_native_u4_prep_tests_20261108.py'
spec = importlib.util.spec_from_file_location('u5_reviewed_runner', source)
u4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u4)
wrapper = u4.wrapper
SCRATCH = wrapper.runner.EXECUTIONS / 'scratch-native-u5-prep'
wrapper.SCRATCH = SCRATCH
wrapper.__file__ = __file__
wrapper.runner.SCRATCH = SCRATCH
wrapper.runner.__file__ = __file__
wrapper.runner.PROFILE = wrapper.sandbox_profile()
wrapper.dependency.SCRATCH = SCRATCH
wrapper.dependency.DESTINATION = SCRATCH / 'dependencies' / ('fairscape-' + wrapper.dependency.PIN)

if __name__ == '__main__':
    if sys.argv[1:] == ['--hydrate-local-dependency']:
        wrapper.dependency.main()
        raise SystemExit(0)
    wrapper.runner.time = wrapper.DeadlineClock()
    raise SystemExit(wrapper.runner.main())
