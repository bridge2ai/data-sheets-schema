#!/usr/bin/env python3
"""U4b offline validation, 2026-11-08 (#4354).

Inputs: committed checkout and explicit nodes. Outputs: fresh assigned scratch
runs. Reuse U4's credential stripping, sandbox, source witnesses, quiet lock,
two-worker ceiling and 3600-second bound. Only local fake peers may execute.
"""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('u4b_reviewed_runner',
    ROOT / 'scripts/adhoc/run_native_u4_prep_tests_20261108.py')
u4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u4)
wrapper = u4.wrapper
SCRATCH = wrapper.runner.EXECUTIONS / 'scratch-native-u4b'
wrapper.SCRATCH = SCRATCH
wrapper.__file__ = __file__
wrapper.runner.SCRATCH = SCRATCH
wrapper.runner.__file__ = __file__
wrapper.runner.PROFILE = wrapper.sandbox_profile()
wrapper.dependency.SCRATCH = SCRATCH
wrapper.dependency.DESTINATION = SCRATCH / 'dependencies' / ('fairscape-' + wrapper.dependency.PIN)
_environment = wrapper.runner.clean_environment


def clean_environment(out, interpreter_directory):
    env = _environment(out, interpreter_directory)
    # Retest U5's exact cohorts with new immutable exports in this task's
    # scratch, never replacing the retained U5 inputs/evidence.
    env['D4D_U5_INPUT_ROOT'] = str(SCRATCH)
    return env


wrapper.runner.clean_environment = clean_environment

if __name__ == '__main__':
    if sys.argv[1:] == ['--hydrate-local-dependency']:
        wrapper.dependency.main()
        raise SystemExit(0)
    wrapper.runner.time = wrapper.DeadlineClock()
    raise SystemExit(wrapper.runner.main())
