#!/usr/bin/env python3
"""Resolve the U3-B/C receipt add/add, owner D95, 2026-11-07.

Inputs: exact local B and C Git objects, an in-progress merge of B into C.
Output: B's unchanged owner file followed by C's marked delivery section.
No network, package imports, other file writes or Git mutations are performed.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
B = 'a3aac3bed7402e5afad953eb050a39ec3ec5e553'
C = '9bf29183a4a8fa97290ed6b7691848fe22313241'
TARGET = 'src/data_sheets_schema/native_shared_receipts.py'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': ''}


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=ROOT, env=ENV, timeout=30)


def main():
    if git('branch', '--show-current').strip() != b'codex/native-u3c-controller-20261107':
        raise SystemExit('requires assigned U3-C branch')
    if git('rev-parse', 'HEAD').decode().strip() != C or git('rev-parse', 'MERGE_HEAD').decode().strip() != B:
        raise SystemExit('requires the exact B-into-C in-progress merge')
    if git('diff', '--name-only', '--diff-filter=U').decode().splitlines() != [TARGET]:
        raise SystemExit('unexpected conflict roster')
    owner = git('show', B + ':' + TARGET)
    delivery = git('show', C + ':' + TARGET)
    marker = b'# BEGIN U3-C RECEIPT DELIVERY\n'
    end = b'# END U3-C RECEIPT DELIVERY\n'
    if delivery.count(marker) != 1 or delivery.count(end) != 1 or not delivery.endswith(end):
        raise SystemExit('delivery marker contract differs')
    section = delivery[delivery.index(marker):]
    result = owner + b'\n\n' + section
    ast.parse(result)
    target = ROOT / TARGET
    if target.is_symlink() or not target.is_file():
        raise SystemExit('receipt target must be an existing regular file')
    target.write_bytes(result)
    if target.read_bytes() != result or not result.startswith(owner):
        raise SystemExit('receipt write did not preserve exact owner bytes')
    print(json.dumps({'owner_commit': B, 'delivery_commit': C,
        'owner_bytes': len(owner), 'owner_sha256': hashlib.sha256(owner).hexdigest(),
        'delivery_sha256': hashlib.sha256(section).hexdigest(),
        'merged_sha256': hashlib.sha256(result).hexdigest()}, sort_keys=True))


if __name__ == '__main__':
    main()
