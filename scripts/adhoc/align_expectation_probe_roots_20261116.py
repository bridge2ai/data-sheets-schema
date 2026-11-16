"""Align regression probe import census with saved CLI, PR 5968, 2026-11-16.
Inputs: regression generator and generated helper. Outputs: exact CLI import roots.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
old = "    # Run the original invalid handoff against the genuine verified consumer.\n"
new = old + """    # Fixture imports needed the test root; production verification needs the
    # same import census as the standalone prefix and saved-step CLI.
    sys.path[:] = [str(ROOT / 'src'), str(ROOT / 'scripts'),
        *(p for p in sys.path if p not in (str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')))]
"""
for name in ('stage_expectation_regression_20261116.py', 'expectation_scope_regression_20261116.py'):
    path = root / 'scripts/adhoc' / name
    text = path.read_text()
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
