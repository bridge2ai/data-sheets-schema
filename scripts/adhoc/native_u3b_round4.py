"""Prepare/run the single-node base/head timing comparison, 2026-11-07.

Inputs: local exact Git revisions and existing protected launcher.
Outputs: scratch archive, identity, logs/events/XML; serves Round 4 lead ruling.
No checkout, network, production edits or extra pytest invocations.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u3b/round4-20261107-timing'
BASE = 'f101652f53f23d9be83a213b6d5850bd6e9341fc'
HEAD = 'ea2c9728c88f1ac5ae9b17b719f068c79eaf5d62'
NODE = 'tests/test_source_heading_runtime_api.py::test_actual_completed_capture_is_portable_and_refuses_changed_bytes'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['prepare', 'base', 'head'])
parser.add_argument('--plan', action='store_true')
args = parser.parse_args()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD
if (ROOT.parent / 'plans/native_quiet_window.lock').exists():
    raise SystemExit('Quiet lock present; wait at least 60 seconds before checking again')
if args.action == 'prepare':
    OUT.mkdir(exist_ok=False)
    archive = OUT / 'base.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git', 'archive', BASE], cwd=ROOT, stdout=stream,
                       env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'}, check=True)
    tree = OUT / 'base'
    tree.mkdir()
    with tarfile.open(archive) as source:
        source.extractall(tree, filter='data')
    test = NODE.split('::')[0]
    assert (tree / test).read_bytes() == (ROOT / test).read_bytes()
    assert not (tree / '.git').exists()
    identity = {'base': BASE, 'head': HEAD, 'node': NODE,
                'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'test_sha256': hashlib.sha256((tree / test).read_bytes()).hexdigest()}
    (OUT / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    print(json.dumps(identity, indent=2))
else:
    name = 'round4-' + args.action
    tree = OUT / 'base' if args.action == 'base' else ROOT
    command = [str(PYTHON), str(ROOT / 'scripts/adhoc/validate_native_u3b.py'),
               name, '--workers', '0', '--output-dir', str(OUT), '--tree', str(tree),
               NODE, '-q', '--tb=short', '--durations=1',
               '--junitxml=' + str(OUT / (name + '.xml'))]
    print(json.dumps(command), flush=True)
    if not args.plan:
        raise SystemExit(subprocess.call(command, cwd=ROOT))
