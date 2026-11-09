"""U3-H offline sequential validation, 2026-11-09, D126 and review P1/P2.

Inputs: committed source, explicit nodes. Outputs: fresh u3h scratch evidence.
Reuse U3-G's 3200s bound/3250s watchdog, credentials, OS denial and origin checks.
No production deadline or permission changes; no provider/native execution.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('u3h_parent',
    ROOT / 'scripts/adhoc/run_native_u3g_20261109.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
g.f.r.w.__file__ = g.f.r.w.runner.__file__ = __file__
clean = g.f.r.w.runner.clean_environment


def environment(out, interpreter_directory):
    result = clean(out, interpreter_directory)
    result['D4D_U5_INPUT_ROOT'] = str(g.f.r.SCRATCH / 'u3h')
    return result


g.f.r.w.runner.clean_environment = environment
if __name__ == '__main__':
    g.f.r.w.runner.time = g.f.r.w.DeadlineClock()
    raise SystemExit(g.f.r.w.runner.main())
