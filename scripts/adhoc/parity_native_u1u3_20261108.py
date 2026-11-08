"""U3-E 2026-11-08 explicit before/after raw instruction artifacts.
Inputs: committed candidate or isolated saved-main parity harness; output:
assigned scratch sandboxed pytest and instruction bytes. No production overlays.
"""
import importlib.util
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
basis = os.environ.get('U3E_PARITY_BASIS')
if basis not in ('baseline', 'candidate'):
    raise RuntimeError('explicit parity basis required')
name = 'baseline_native_u1u3_20261108.py' if basis == 'baseline' else 'run_native_u1u3_20261108.py'
spec = importlib.util.spec_from_file_location('parity_basis', ROOT / 'scripts/adhoc' / name)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
r = module.r if basis == 'baseline' else module
if basis == 'baseline':
    module.root = r.SCRATCH / 'baseline-parity'
    r.w.ROOT = r.w.runner.ROOT = r.w.dependency.ROOT = module.root
r.w.__file__ = r.w.runner.__file__ = __file__
clean = r.w.runner.clean_environment
def environment(out, interpreter_directory):
    return {**clean(out, interpreter_directory),
        'U3E_PARITY_BASIS': basis,
        'U1_PARITY_OUTPUT': str(out / 'parity'),
        'PYTEST_PLUGINS': 'scripts.adhoc.u3e_parity_plugin_20261108'}
r.w.runner.clean_environment = environment
if __name__ == '__main__':
    r.w.runner.time = r.w.DeadlineClock()
    raise SystemExit(r.w.runner.main())

