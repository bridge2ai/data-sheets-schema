#!/usr/bin/env python3
"""Round 4 accepted review findings, 2026-11-07.

Inputs: scoped worktree, retained Round 3 composition and run plans.
Outputs: new Round 4 scratch composition and evidence manifest, or bounded
runs through the existing offline supervisor. No network or scratch commits.
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
OUT = BASE / 'round4-composed'
SCOPED = ['src/data_sheets_schema/cli/receipts.py', 'src/data_sheets_schema/receipts.py',
    'src/data_sheets_schema/native_shared_phase.py', 'src/data_sheets_schema/native_shared_render.py',
    'tests/test_native_shared_phase.py', 'tests/test_native_shared_render.py',
    'tests/test_native_shared_controller.py', 'tests/test_native_initial_structure_mode.py',
    'tests/test_native_u3d_receipt_policy.py', 'scripts/adhoc/run_native_u3d_tests_20261107.py',
    'scripts/adhoc/native_u3d_round4_evidence_20261107.py']
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


assert not os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'), 'quiet window active'
assert git('branch', '--show-current') == 'codex/native-u3d-integration-20261107'
changed = set(git('diff', '--name-only', '98eb2c4f2').splitlines())
untracked = set(git('ls-files', '--others', '--exclude-standard').splitlines())
assert changed | untracked <= set(SCOPED), (changed | untracked) - set(SCOPED)
mode = sys.argv[1]
if mode == 'compose':
    prior = BASE / 'round3-composed'
    manifest = json.loads((prior / 'composition.json').read_text())
    OUT.mkdir()
    shutil.copy2(prior / 'tree' / SCOPED[0], OUT / 'canary.py')
    assert sha(OUT / 'canary.py') == sha(prior / 'tree' / SCOPED[0])
    shutil.copytree(prior / 'tree', OUT / 'tree', symlinks=True)
    for name in SCOPED:
        shutil.copy2(ROOT / name, OUT / 'tree' / name)
        assert sha(ROOT / name) == sha(OUT / 'tree' / name)
    for packet in manifest['packets']:
        assert sha(OUT / 'tree' / packet['target']) == packet['postimage_sha256']
    manifest.update(prior=str(prior), prior_manifest_sha256=sha(prior / 'composition.json'),
        overlays={name: sha(ROOT / name) for name in SCOPED}, policy='verified copy; no scratch commit')
    (OUT / 'composition.json').write_text(json.dumps(manifest, indent=2) + '\n')
elif mode == 'run':
    cohort = sys.argv[2]
    source = OUT / 'tree' if cohort.startswith('composed') else ROOT
    if cohort == 'regressions':
        args = json.loads((BASE / 'round3-regressions/pytest-command.json').read_text())['args']
        nodes = [arg for arg in args if arg.startswith('tests/')]
    elif cohort == 'composed-canary':
        nodes = ['tests/test_native_shared_render.py::test_split_receipt_commands_match_native_consumers']
    elif cohort == 'composed-consumers':
        nodes = ['tests/test_native_shared_phase.py', 'tests/test_native_shared_render.py',
                 'tests/test_native_phase_scope_rendering.py', 'tests/test_native_shared_controller.py']
    elif cohort == 'permissions':
        nodes = ['tests/test_native_shared_permissions.py']
    elif cohort == 'focused':
        nodes = ['tests/test_native_shared_phase.py', 'tests/test_native_initial_structure_mode.py',
                 'tests/test_native_u3d_receipt_policy.py', 'tests/test_native_shared_render.py']
    else:
        raise ValueError(cohort)
    raise SystemExit(subprocess.call([str(PYTHON), '-S', '-P', '-B',
        str(source / 'scripts/adhoc/run_native_u3d_tests_20261107.py'), '--out',
        str(BASE / ('round4-' + cohort)), *nodes], cwd=source))
elif mode == 'collect':
    runs = {}
    for path in sorted(BASE.glob('round4-*/plan.json')):
        directory = path.parent
        row = {}
        for name in ('plan.json', 'outcome.json', 'pytest-command.json'):
            file = directory / name
            row[name] = {'sha256': sha(file), 'value': json.loads(file.read_text())}
        assert sha(directory / 'tested.diff') == row['plan.json']['value']['tested_diff_sha256']
        row['junit'] = [dict(s.attrib) for s in ET.parse(directory / 'pytest.xml').getroot().iter('testsuite')]
        runs[directory.name] = row
    manifest = json.loads((OUT / 'composition.json').read_text())
    for packet in manifest['packets']:
        assert sha(OUT / 'tree' / packet['target']) == packet['postimage_sha256']
    for name in SCOPED:
        assert sha(ROOT / name) == sha(OUT / 'tree' / name)
    (BASE / 'round4-evidence.json').write_text(json.dumps({'base': '98eb2c4f2',
        'source_hashes': {name: sha(ROOT / name) for name in SCOPED}, 'runs': runs,
        'composition_sha256': sha(OUT / 'composition.json')}, indent=2) + '\n')
else:
    raise ValueError(mode)
