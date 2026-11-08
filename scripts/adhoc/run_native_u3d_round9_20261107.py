#!/usr/bin/env python3
"""U3-D9 offline validation, 2026-11-07.

Inputs: committed D checkout and explicit pytest nodes. Outputs: exclusive
scratch-native-u3d run directories, source witnesses, JUnit and sandbox logs.
Retains the C4 credential/network/native-exec/write restrictions and deadline.
"""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / 'scripts/adhoc/run_native_u3c_round4_20261107.py'
spec = importlib.util.spec_from_file_location('d9_reviewed_runner', source)
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)
SCRATCH = wrapper.runner.EXECUTIONS / 'scratch-native-u3d'
wrapper.SCRATCH = SCRATCH
wrapper.__file__ = __file__
wrapper.runner.SCRATCH = SCRATCH
wrapper.runner.__file__ = __file__
wrapper.runner.PROFILE = wrapper.sandbox_profile()
wrapper.dependency.SCRATCH = SCRATCH
wrapper.dependency.SOURCE = wrapper.runner.EXECUTIONS.parent / 'data-sheets-schema/fairscape_models'
wrapper.dependency.DESTINATION = SCRATCH / 'dependencies' / ('fairscape-' + wrapper.dependency.PIN)

if __name__ == '__main__':
    if sys.argv[1:] == ['--hydrate-local-dependency']:
        wrapper.dependency.main()
        raise SystemExit(0)
    wrapper.runner.time = wrapper.DeadlineClock()
    raise SystemExit(wrapper.runner.main())
