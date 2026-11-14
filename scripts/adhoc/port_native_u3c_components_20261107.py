#!/usr/bin/env python3
"""Seed U3-C functional modules from the reviewed donor, 2026-11-07 (D95).

Inputs: exact local donor Git object and an explicit subset of the fixed roster.
Outputs: new files in this assigned worktree, plus path/byte/SHA provenance.
This is extraction provenance, not the final adaptation or a launch helper.
Run one file and verify it before the remaining extraction. Refuse overwrites.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DONOR = '0d5bddbc03b02cfa3efdea312c10aca002f6d85c'
TEST_DONOR = '142d090bb1cf686ef87b9105b96e0f982356b90f'
BRANCH = 'codex/native-u3c-controller-20261107'
ROSTER = ('controller', 'capture', 'current', 'effects', 'observations',
          'phase', 'policy', 'stage', 'streams', 'attribution')
TESTS = ('phase', 'effects', 'initial_receipts')
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_NO_LAZY_FETCH': '1'}


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args],
        cwd=ROOT, env=ENV, timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('components', nargs='*', choices=ROSTER)
    parser.add_argument('--tests', nargs='+', choices=TESTS, default=[])
    args = parser.parse_args()
    if not args.components and not args.tests:
        parser.error('an explicit component or test is required')
    if len(set(args.components)) != len(args.components) or len(set(args.tests)) != len(args.tests):
        parser.error('duplicate component')
    if git('branch', '--show-current').decode().strip() != BRANCH:
        raise SystemExit('only the assigned U3-C branch may receive these files')
    pending = []
    selected = [(DONOR, f'src/data_sheets_schema/native_shared_{name}.py')
                for name in args.components]
    selected += [(TEST_DONOR, f'tests/test_native_shared_{name}.py') for name in args.tests]
    for donor, relative in selected:
        target = ROOT / relative
        if target.exists() or target.is_symlink():
            raise SystemExit('refusing existing path: ' + relative)
        pending.append((donor, relative, target, git('show', donor + ':' + relative)))
    for donor, relative, target, raw in pending:
        with target.open('xb') as stream:
            stream.write(raw)
        if target.read_bytes() != raw:
            raise RuntimeError('written extraction differs: ' + relative)
        print(json.dumps({'donor': donor, 'path': relative, 'bytes': len(raw),
                          'sha256': hashlib.sha256(raw).hexdigest()}, sort_keys=True))


if __name__ == '__main__':
    main()
