#!/usr/bin/env python3
"""Inspect the local U3-C pre-B packet, 2026-11-07 (D95).

Inputs: this checkout and its fixed U3-A base. Outputs: JSON to stdout containing
source scope, syntax checks and artifact hashes for the U3-C report. Offline;
does not import project code or change files. Run with Python -S -P -B.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = '3690a570a078d30ed8abd113200ce7f6384c5536'
ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}
MODULES = ('controller', 'capture', 'current', 'effects', 'observations', 'phase',
           'policy', 'stage', 'streams', 'attribution', 'receipts')


def git(*args):
    return subprocess.run(['/usr/bin/git', '-C', str(ROOT), *args], env=ENV,
                          check=True, capture_output=True, timeout=60).stdout


def main():
    changed_existing = git('diff', '--name-only', BASE, '--', 'src/').decode().splitlines()
    existing = set(git('ls-tree', '-r', '--name-only', BASE, '--', 'src/').decode().splitlines())
    modified_existing = sorted(existing.intersection(changed_existing))
    if modified_existing:
        raise RuntimeError('pre-B packet changed existing source: ' + repr(modified_existing))
    paths = {ROOT / f'src/data_sheets_schema/native_shared_{name}.py' for name in MODULES}
    paths.update(ROOT.glob('scripts/adhoc/*native_u3c*.py'))
    paths.update(ROOT.glob('tests/test_native_shared_*.py'))
    paths.add(ROOT / 'tests/native_shared_captured_fixture.py')
    paths.add(ROOT / 'notes/native_authority_v2.md')
    files = {}
    for path in sorted(paths):
        raw = path.read_bytes()
        if not raw:
            raise RuntimeError('empty artifact: ' + str(path))
        if path.suffix == '.py':
            ast.parse(raw, filename=str(path))
        files[str(path.relative_to(ROOT))] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    print(json.dumps({'base': BASE, 'head': git('rev-parse', 'HEAD').decode().strip(),
        'status': git('status', '--porcelain=v1').decode().splitlines(),
        'changed': git('diff', '--name-status', BASE, 'HEAD').decode().splitlines(),
        'modified_existing_source': modified_existing,
        'source_modules': len(MODULES), 'files': files}, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
