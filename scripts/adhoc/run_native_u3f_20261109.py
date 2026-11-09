"""U3-F sequential offline cohorts, 2026-11-09.

Inputs: committed source and explicit nodes. Outputs: assigned scratch only.
Uses inherited credential, network, native-exec, origin and cleanup controls.
The enclosing validation bound is 3300 seconds; selected test/production
deadlines are unchanged. No public completion deadline cases are selected.
"""
import importlib.util
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('u3f_runner', ROOT / 'scripts/adhoc/run_native_u1u3_20261108.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
r.w.__file__ = r.w.runner.__file__ = __file__
r.w.runner.DEADLINE = 3300
clean = r.w.runner.clean_environment

def environment(out, interpreter_directory):
    result = clean(out, interpreter_directory)
    if os.environ.get('U3F_PARITY') == '1':
        result.update(U3F_PARITY='1', U1_PARITY_OUTPUT=str(out / 'parity'),
                      PYTEST_PLUGINS='scripts.adhoc.u3e_parity_plugin_20261108')
    return result

r.w.runner.clean_environment = environment
if __name__ == '__main__':
    r.w.runner.time = r.w.DeadlineClock()
    raise SystemExit(r.w.runner.main())
