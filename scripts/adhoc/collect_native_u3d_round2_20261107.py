#!/usr/bin/env python3
"""U3D-R5/R9, 2026-11-07: collect local round-2 outcomes and scoped source hashes.
Inputs: current D checkout and scratch-native-u3d/round2-* evidence.
Output: scratch-native-u3d/round2-evidence.json; no network or mutations to sources.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3d'
assert not os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

allowed = {'src/data_sheets_schema/cli/receipts.py', 'src/data_sheets_schema/receipts.py',
           'src/data_sheets_schema/native_shared_render.py', 'tests/test_native_shared_render.py',
           'tests/test_native_initial_structure_mode.py',
           'scripts/adhoc/prepare_native_u3d_round2_scratch_20261107.py',
           'scripts/adhoc/collect_native_u3d_round2_20261107.py'}
changed = set(git('diff', '--name-only', '96adabfb3').splitlines())
untracked = set(git('ls-files', '--others', '--exclude-standard').splitlines())
assert changed | untracked <= allowed, (changed | untracked) - allowed
runs = {}
for directory in sorted(SCRATCH.glob('round2-*')):
    if not directory.is_dir():
        continue
    row = {}
    for name in ('outcome.json', 'plan.json', 'network.json', 'pytest-command.json'):
        path = directory / name
        if path.exists():
            row[name] = {'sha256': sha(path), 'value': json.loads(path.read_text())}
    xml = directory / 'pytest.xml'
    if xml.exists():
        row['junit'] = {'sha256': sha(xml), 'suites': [dict(s.attrib) for s in ET.parse(xml).getroot().iter('testsuite')]}
    if row:
        runs[directory.name] = row
witness = SCRATCH / 'round2-render/cases/test_initial_and_final_receipt0/render-digests.json'
result = {'base': '96adabfb3ea6e558be02bbfa5dfcbcac16c03b0b', 'head': git('rev-parse', 'HEAD'),
          'branch': git('branch', '--show-current'), 'allowed_source_hashes': {p: sha(ROOT / p) for p in sorted(allowed)},
          'tracked_changes': sorted(changed), 'untracked': sorted(untracked),
          'protected_files': 'unchanged; tracked diff restricted to explicit allowlist',
          'render_witness': json.loads(witness.read_text()), 'runs': runs,
          'scratch_current_overlay_hashes': {p: sha(SCRATCH / 'round2-composed/tree' / p)
              for p in sorted(allowed) if (SCRATCH / 'round2-composed/tree' / p).is_file()},
          'scratch_note': 'composition.json records initial copy; render test subsequently gained R9 regression; current hashes above'}
out = SCRATCH / 'round2-evidence.json'
out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
assert out.stat().st_size > 0
print(out)
