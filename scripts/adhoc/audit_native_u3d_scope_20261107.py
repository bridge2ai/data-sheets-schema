#!/usr/bin/env python3
"""Audit the pre-B U3-D source scope and save identities, D95, 2026-11-07.

Inputs: this isolated tree and U3-C checkpoint. Output: exclusive JSON witness.
Reads every source file, including ignored files; never imports or edits it.
This pre-merge audit intentionally refuses any additional B/C source changes.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = '9bf29183a4a8fa97290ed6b7691848fe22313241'
NEW = {'native_execution_engine.py', 'native_gate_engine.py', 'native_subscription_guard.py',
       *(f'native_shared_{name}.py' for name in ('execution', 'gates', 'permissions',
          'publication', 'registration', 'results', 'schema_gates'))}
ADAPTERS = {'derive_core.py', 'receipt_completion_policy.py', 'receipts.py',
    'backfill_checks.py', 'cli/derive.py', 'cli/prompt.py', 'cli/provenance.py',
    'cli/receipts.py', 'native_receipt_origin.py', 'receipt_origin_record.py',
    'schema/d4d_generation_record.yaml'}
ENV = {'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', *args],
                                   cwd=ROOT, env=ENV, timeout=30)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if git('branch', '--show-current').decode().strip() != 'codex/native-u3d-integration-20261107':
        raise SystemExit('only the assigned U3-D branch')
    prefix = 'src/data_sheets_schema/'
    tracked = set(git('ls-tree', '-r', '--name-only', BASE, '--', prefix).decode().splitlines())
    # rglob deliberately includes gitignored files. Bytecode is not source.
    actual = {str(p.relative_to(ROOT)) for p in (ROOT / prefix).rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    allowed = {prefix + p for p in NEW | ADAPTERS}
    changed = {}
    for name in sorted(tracked | actual):
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError('missing or aliased source: ' + name)
        raw = path.read_bytes()
        before = git('show', BASE + ':' + name) if name in tracked else None
        if before != raw:
            if name not in allowed:
                raise RuntimeError('out-of-scope source change: ' + name)
            changed[name] = {'sha256': sha(raw), 'bytes': len(raw),
                'base_sha256': None if before is None else sha(before)}
            if path.suffix == '.py':
                ast.parse(raw, filename=name)
    if not {prefix + p for p in NEW} <= set(changed):
        raise RuntimeError('required new modules absent')
    result = {'base': BASE, 'head': git('rev-parse', 'HEAD').decode().strip(),
        'phase': 'pre-B source scope; not integrated acceptance', 'changed': changed,
        'unchanged_source_files': len(actual) - len(changed),
        'provenance_py_unchanged': prefix + 'provenance.py' not in changed,
        'ignored_source_files_included': True,
        'notes': 'Allowed source roster only. Frozen v1/U2 and protected source bytes unchanged.'}
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps({'path': str(args.out), 'sha256': sha(args.out.read_bytes()),
                      'changed_source_files': len(changed)}))


if __name__ == '__main__':
    main()
