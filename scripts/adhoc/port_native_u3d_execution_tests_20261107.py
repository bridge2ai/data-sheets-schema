#!/usr/bin/env python3
"""Recover exact U3-D execution test inputs; D95, 2026-11-07.

Inputs: the fixed local donor and explicit allowlisted paths. Outputs: exclusive
new fixture/test files and SHA-256 inventory. No test, peer or network executes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DONOR = '142d090bb1cf686ef87b9105b96e0f982356b90f'
ROSTER = frozenset((
    'tests/test_native_execution_engine.py',
    'tests/test_native_shared_publication.py',
    'tests/test_native_shared_execution.py',
    'tests/test_native_shared_execution_failure.py',
    'tests/test_native_shared_execution_variant.py',
    'tests/native_shared_fixture.py',
    'tests/native_shared_omission_fixture.py',
    'tests/fixtures/native_shared_execution/fake_cli.py',
))
ENV = {'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', *args],
        cwd=ROOT, env=ENV, timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+')
    args = parser.parse_args()
    if git('branch', '--show-current').decode().strip() != 'codex/native-u3d-integration-20261107':
        parser.error('only the assigned U3-D branch may receive fixtures')
    if len(set(args.paths)) != len(args.paths) or any(path not in ROSTER for path in args.paths):
        parser.error('paths must be distinct and allowlisted')
    pending = []
    for relative in args.paths:
        target = ROOT / relative
        if target.exists() or target.is_symlink():
            raise SystemExit('refusing overwrite: ' + relative)
        pending.append((relative, target, git('show', DONOR + ':' + relative)))
    for relative, target, raw in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
        if target.read_bytes() != raw:
            raise RuntimeError('extraction differs: ' + relative)
        print(json.dumps({'donor': DONOR, 'path': relative, 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}, sort_keys=True))


if __name__ == '__main__':
    main()
