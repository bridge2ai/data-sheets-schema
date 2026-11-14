"""U1 #4354, 2026-11-06: adapt donor additions and generate a bounded M7 patch.
Inputs: local Git donors and M7. Outputs: U1 files and scratch donor patch.
Run tests mode first; production mode applies only unprotected named files.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1'
REF = '5d87ea67660e00affcbc6dbae0d35172d85209d7'

def show(path):
    return subprocess.check_output(['git', 'show', f'{REF}:{path}'], cwd=ROOT)

mode = sys.argv[1]
if mode == 'tests':
    names = ['tests/test_native_shared_' + n + '.py' for n in ('contract', 'evidence', 'selection', 'render')]
    names += ['tests/test_native_schema_metadata_reuse.py']
else:
    assert mode == 'production'
    names = ['src/data_sheets_schema/native_shared_' + n + '.py' for n in ('contract', 'evidence', 'selection', 'render')]
    names += ['src/download/prompts/native_shared_' + n + '_v1.md' for n in ('generation', 'receipt_policy')]
for name in names:
    path = ROOT / name
    assert not path.exists(), path
    path.write_bytes(show(name))
if mode == 'production':
    patch = subprocess.check_output(['git', 'diff', REF + '^1', REF, '--',
        'src/data_sheets_schema/api_runner.py', 'src/data_sheets_schema/schema_snapshot.py'], cwd=ROOT)
    (SCRATCH / 'donor-adaptation.patch').write_bytes(patch)
    subprocess.run(['git', 'apply', '--reject', str(SCRATCH / 'donor-adaptation.patch')], cwd=ROOT, check=False)
