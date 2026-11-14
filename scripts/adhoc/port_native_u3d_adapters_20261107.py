#!/usr/bin/env python3
"""Apply reviewed narrow donor hunks onto current adapters (D95), 2026-11-07.

Inputs: fixed donor delta, explicit current files. Outputs: adapted files and
diff hashes; never replaces complete shared modules. Refuses drift/conflicts.
Manual current-schema/v2 fixes follow in the same branch. No network.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DONOR = '0d5bddbc03b02cfa3efdea312c10aca002f6d85c'
ROSTER = ('cli/derive.py', 'cli/receipts.py', 'receipts.py', 'receipt_completion_policy.py')
ENV = {'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}


def git(*args, data=None):
    return subprocess.run(['/usr/bin/git', '--no-replace-objects', *args], cwd=ROOT,
        env=ENV, input=data, capture_output=True, check=True, timeout=30).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('names', nargs='+', choices=ROSTER)
    args = parser.parse_args()
    if git('branch', '--show-current').decode().strip() != 'codex/native-u3d-integration-20261107':
        raise SystemExit('wrong branch')
    for name in args.names:
        relative = 'src/data_sheets_schema/' + name
        patch = git('diff', DONOR + '^', DONOR, '--', relative)
        if not patch or git('diff', '--name-only', 'HEAD', '--', relative).strip():
            raise SystemExit('empty donor or locally edited target: ' + relative)
        git('apply', '--check', '-', data=patch)
        git('apply', '-', data=patch)
        if not git('diff', '--name-only', 'HEAD', '--', relative).strip():
            raise RuntimeError('no adaptation persisted: ' + relative)
        print(relative, 'patch_sha256=' + hashlib.sha256(patch).hexdigest(),
              'file_sha256=' + hashlib.sha256((ROOT / relative).read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
