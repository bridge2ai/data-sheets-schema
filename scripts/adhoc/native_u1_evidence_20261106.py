"""U1 #4354, 2026-11-06: retain identities for the blocked handoff.
Inputs: completed/partial scratch evidence and unchanged protected files.
Output: small committed evidence manifest; no tests or source changes.
"""
from pathlib import Path
from importlib.metadata import version
import hashlib
import json
import platform
import subprocess
ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1'
BASE = '8bc90e93d736d464f98e9eedffee45f0ad8e5d3f'

def identity(path):
    raw = path.read_bytes()
    assert raw
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

protected = []
for name in ('src/data_sheets_schema/shared_generation.py', 'src/download/prompts/canonical_hashes.yaml'):
    path = ROOT / name
    assert path.read_bytes() == subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)
    protected.append(identity(path))
files = ('failing-first.log', 'refusals-before.log', 'refusals-before-corrected.log',
         'scanner-before.log', 'scanner-before.json', 'scanner-before.md', 'scanner-after.log',
         'parity-before.log', 'parity-before-fixed.log', 'native-canary.log', 'native-focused.log',
         'api-regressions.log', 'regression-roster.txt')
result = {'status': 'BLOCKED_PROTECTED_ADMISSION_PACKET_REQUIRED', 'base': BASE,
          'python': platform.python_version(), 'packages': {name: version(name) for name in
            ('pytest', 'pytest-xdist', 'linkml', 'linkml-runtime', 'PyYAML', 'jsonschema', 'referencing')},
          'protected_unchanged': protected,
          'evidence': [identity(SCRATCH / name) for name in files],
          'baseline_render_artifacts': [identity(p) for p in sorted((SCRATCH / 'parity-before').glob('*.txt'))],
          'dependency_lock': identity(ROOT / 'poetry.lock'),
          'tests': {'native_focused': '168 passed; 20.13s; -n 2', 'native_canary': '1 passed; 0.76s',
              'api_regressions': 'interrupted at protected-boundary stop; progress 27%, no final summary',
              'api_parity': '13 before renders retained; tuned fixture failed; no after comparison',
              'collection': 'not run: protected-boundary stop',
              'specificity_before': '9 violations, exit 1',
              'specificity_after': 'exit 2: shared selector call guards/order changed; no completed scan'}}
out = ROOT / 'scripts/adhoc/native_u1_packets/evidence.json'
out.write_text(json.dumps(result, indent=2) + '\n')
print(out)
