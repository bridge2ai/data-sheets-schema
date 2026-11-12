"""Apply H3 test-only alias isolation, 2026-11-12.

Input: lead CI failure ledger. Output: eight affected test modules.
Serves helper3 CI origin assignment; leaves production source checks intact.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT.parent / 'codex-development-efficiency-20261111'
ledger = json.loads((REPORT / 'notes/development_efficiency_20261111/handoffs/lead-ci-run-42976790438-failures-20261112.json').read_text())
files = sorted({r['file'] for r in ledger['failures'] if r['class'].startswith('import origin:')})
for name in files:
    path = ROOT / name
    source = path.read_text()
    assert 'pytestmark' not in source and 'isolated_modules' not in source, name
    source += '''

# The pinned v1 and v2 closures intentionally share bare module names. Isolate
# each case from collection imports and earlier v1 cases without relaxing the
# production origin check (including deliberate foreign imports in test bodies).
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: E402,F401
import pytest as _origin_pytest  # noqa: E402

pytestmark = _origin_pytest.mark.usefixtures("isolated_modules")
'''
    path.write_text(source)
print(json.dumps({'changed': files}, indent=2))
