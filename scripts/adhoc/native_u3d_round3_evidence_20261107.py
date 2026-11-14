#!/usr/bin/env python3
"""U3D-R9, 2026-11-07: prepare four-packet scratch or collect Round 3 evidence.

Inputs: verified prior composition, current scoped checkout, offline runner outputs.
Outputs: fresh round3-composed tree or round3-evidence.json. No scratch commits.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent / 'scratch-native-u3d'
OLD = BASE / 'composed-96adabfb3-01/tree'
OUT = BASE / 'round3-composed'
SCOPED = ['src/data_sheets_schema/native_shared_policy.py',
          'src/data_sheets_schema/native_shared_phase.py',
          'src/data_sheets_schema/native_shared_capture.py',
          'tests/test_native_shared_phase.py',
          'tests/test_native_shared_controller.py',
          'scripts/adhoc/native_u3d_round3_evidence_20261107.py']
ROUND2 = ['src/data_sheets_schema/cli/receipts.py', 'src/data_sheets_schema/receipts.py',
          'src/data_sheets_schema/native_shared_render.py', 'tests/test_native_shared_render.py',
          'tests/test_native_initial_structure_mode.py',
          'scripts/adhoc/prepare_native_u3d_round2_scratch_20261107.py',
          'scripts/adhoc/collect_native_u3d_round2_20261107.py']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args, root=ROOT):
    return subprocess.check_output(['git', *args], cwd=root).decode().strip()


assert not os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'), 'quiet window active'
assert git('branch', '--show-current') == 'codex/native-u3d-integration-20261107'
changed = set(git('diff', '--name-only', '04c2ba98a').splitlines())
untracked = set(git('ls-files', '--others', '--exclude-standard').splitlines())
assert changed | untracked <= set(SCOPED), (changed | untracked) - set(SCOPED)
prior = json.loads((OLD.parent / 'composition.json').read_text())
if sys.argv[1:] == ['compose']:
    assert git('rev-parse', 'HEAD', root=OLD) == 'd2feae57f49b65ba34ef38842b5b8d0b25095c79'
    assert not git('status', '--porcelain', '--untracked-files=no', root=OLD)
    assert not OUT.exists()
    OUT.mkdir()
    shutil.copy2(OLD / SCOPED[0], OUT / 'canary.py')
    assert sha(OUT / 'canary.py') == sha(OLD / SCOPED[0])
    shutil.copytree(OLD, OUT / 'tree', symlinks=True)
    for name in ROUND2 + SCOPED:
        shutil.copy2(ROOT / name, OUT / 'tree' / name)
        assert sha(ROOT / name) == sha(OUT / 'tree' / name)
    for packet in prior['packets']:
        assert sha(OUT / 'tree' / packet['target']) == packet['postimage_sha256']
    (OUT / 'composition.json').write_text(json.dumps({
        'prior': str(OLD.parent), 'prior_manifest_sha256': sha(OLD.parent / 'composition.json'),
        'overlays': {name: sha(ROOT / name) for name in ROUND2 + SCOPED},
        'packets': prior['packets'], 'policy': 'verified prior composition copied; no new commit'}, indent=2) + '\n')
    print(OUT / 'tree')
elif sys.argv[1:] == ['sync']:
    for name in ROUND2 + SCOPED:
        shutil.copy2(ROOT / name, OUT / 'tree' / name)
        assert sha(ROOT / name) == sha(OUT / 'tree' / name)
    for packet in prior['packets']:
        assert sha(OUT / 'tree' / packet['target']) == packet['postimage_sha256']
    manifest = json.loads((OUT / 'composition.json').read_text())
    manifest['overlays'] = {name: sha(ROOT / name) for name in ROUND2 + SCOPED}
    (OUT / 'composition.json').write_text(json.dumps(manifest, indent=2) + '\n')
elif sys.argv[1:] == ['collect']:
    runs = {}
    for directory in sorted(BASE.glob('round3-*')):
        if not directory.is_dir():
            continue
        row = {}
        for name in ('outcome.json', 'plan.json', 'network.json', 'pytest-command.json'):
            path = directory / name
            if path.is_file():
                row[name] = {'sha256': sha(path), 'value': json.loads(path.read_text())}
        xml = directory / 'pytest.xml'
        if xml.is_file():
            row['junit'] = {'sha256': sha(xml), 'suites': [dict(s.attrib) for s in ET.parse(xml).getroot().iter('testsuite')]}
        if row:
            runs[directory.name] = row
    for packet in prior['packets']:
        assert sha(OUT / 'tree' / packet['target']) == packet['postimage_sha256']
    for name in ROUND2 + SCOPED:
        assert sha(ROOT / name) == sha(OUT / 'tree' / name)
    output = BASE / 'round3-evidence.json'
    output.write_text(json.dumps({'base': '04c2ba98a', 'head': git('rev-parse', 'HEAD'),
        'changes': sorted(changed | untracked), 'source_hashes': {p: sha(ROOT / p) for p in SCOPED},
        'composition_sha256': sha(OUT / 'composition.json'), 'runs': runs,
        'protected_sources': 'tracked diff restricted to explicit allowlist; scratch packet postimages verified'},
        indent=2, sort_keys=True) + '\n')
    assert output.stat().st_size > 0
    print(output)
else:
    raise SystemExit('choose compose, sync or collect')
