#!/usr/bin/env python3
"""U3D-R5 round 2, 2026-11-07: copy prior verified composition, overlay scoped edits.
Inputs: clean prior four-packet scratch composition and current D checkout.
Output: new scratch tree and hash manifest; no commits, network or executables.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent / 'scratch-native-u3d'
OLD = BASE / 'composed-96adabfb3-01/tree'
OUT = BASE / 'round2-composed'
FILES = ['src/data_sheets_schema/cli/receipts.py', 'src/data_sheets_schema/receipts.py',
         'src/data_sheets_schema/native_shared_render.py', 'tests/test_native_shared_render.py',
         'tests/test_native_initial_structure_mode.py',
         'scripts/adhoc/prepare_native_u3d_round2_scratch_20261107.py']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert not os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'), 'quiet window active'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=OLD).decode().strip() == 'd2feae57f49b65ba34ef38842b5b8d0b25095c79'
assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=OLD)
assert not OUT.exists()
OUT.mkdir()
# One actual copy and byte verification before copying the tree.
shutil.copy2(OLD / FILES[0], OUT / 'canary.py')
assert sha(OUT / 'canary.py') == sha(OLD / FILES[0])
shutil.copytree(OLD, OUT / 'tree', symlinks=True)
for name in FILES:
    shutil.copy2(ROOT / name, OUT / 'tree' / name)
    assert sha(ROOT / name) == sha(OUT / 'tree' / name)
prior = json.loads((OLD.parent / 'composition.json').read_text())
for packet in prior['packets']:
    assert sha(OUT / 'tree' / packet['target']) == packet['postimage_sha256']
(OUT / 'composition.json').write_text(json.dumps({'prior_composition': str(OLD.parent),
    'prior_manifest_sha256': sha(OLD.parent / 'composition.json'),
    'overlays': {name: sha(ROOT / name) for name in FILES},
    'policy': 'copied existing composition, no new commit; only scoped sources/tests and this helper overlaid'}, indent=2) + '\n')
print(OUT / 'tree')
