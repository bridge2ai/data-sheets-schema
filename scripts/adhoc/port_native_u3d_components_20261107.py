#!/usr/bin/env python3
"""Recover U3-D components from local donors (D95), 2026-11-07.

Inputs: fixed donor commits and explicit source/test names. Outputs: exclusive
new files in the assigned worktree and their byte counts/SHA-256s. One-file
canary precedes batch recovery. This records extraction, not final adaptation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DONOR = '0d5bddbc03b02cfa3efdea312c10aca002f6d85c'
TEST_DONOR = '142d090bb1cf686ef87b9105b96e0f982356b90f'
ROSTER = ('native_execution_engine', 'native_gate_engine', 'native_subscription_guard',
          'native_shared_execution', 'native_shared_gates', 'native_shared_permissions',
          'native_shared_publication', 'native_shared_registration',
          'native_shared_results', 'native_shared_schema_gates')
ENV = {'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', *args],
        cwd=ROOT, env=ENV, timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('components', nargs='*')
    parser.add_argument('--tests', nargs='+', default=[])
    args = parser.parse_args()
    if git('branch', '--show-current').decode().strip() != 'codex/native-u3d-integration-20261107':
        parser.error('only the assigned U3-D branch may receive these files')
    if not args.components and not args.tests:
        parser.error('explicit sources/tests required')
    if any(name not in ROSTER for name in args.components):
        parser.error('unknown source component')
    if any(not re.fullmatch(r'test_native_[a-z0-9_]+\.py', name)
           and name != 'test_derive_core_selected_schemas.py' for name in args.tests):
        parser.error('test names must be bounded native test basenames')
    selected = [(DONOR, 'src/data_sheets_schema/' + name + '.py') for name in args.components]
    selected += [(TEST_DONOR, 'tests/' + name) for name in args.tests]
    if len(set(selected)) != len(selected):
        parser.error('duplicate path')
    pending = []
    for donor, relative in selected:
        target = ROOT / relative
        if target.exists() or target.is_symlink():
            raise SystemExit('refusing overwrite: ' + relative)
        pending.append((donor, relative, target, git('show', donor + ':' + relative)))
    for donor, relative, target, raw in pending:
        with target.open('xb') as stream:
            stream.write(raw)
        if target.read_bytes() != raw:
            raise RuntimeError('extraction differs: ' + relative)
        print(json.dumps({'donor': donor, 'path': relative, 'bytes': len(raw),
                          'sha256': hashlib.sha256(raw).hexdigest()}, sort_keys=True))


if __name__ == '__main__':
    main()
