#!/usr/bin/env python3
"""Read-only E1/#5755 sparse-index diagnosis, 2026-11-11.

Input: preserved first failed preparation. Output: one new JSON diagnosis next
to its manifest. No imports of project code, checkout, setup, tests or retries.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2].parent
FAILED = ROOT / 'scratch-native-u1u3/u3m/composition-01bdcb22dad6'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_OPTIONAL_LOCKS': '0',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_CONFIG_GLOBAL': '/dev/null'}


def git(cwd, *args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd, env=ENV, timeout=10)


def main():
    manifest = FAILED / 'composition.json'
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != '985e31929f02cd7ac0e77b57e7f81cc5209747f9896bb810545c75739b2d8d3c':
        raise ValueError('failed preparation manifest changed')
    value = json.loads(raw)
    source = Path(value['source_worktree'])
    expected, gitlinks = set(), {}
    for row in git(source, 'ls-tree', '-r', '-l', '-z', value['source_commit']).split(b'\0'):
        if not row:
            continue
        meta, path = row.split(b'\t', 1)
        mode, kind, oid, size = meta.split()
        path = path.decode()
        if kind == b'commit':
            gitlinks[path] = oid.decode()
        elif ('/' not in path or path in value['sparse_controller_files']
              or any(path.startswith(prefix + '/') for prefix in value['sparse_directories'])):
            expected.add(path)
    rows = git(FAILED / 'tree', 'ls-files', '-t', '-z').split(b'\0')
    actual = {row[2:].decode() for row in rows if row.startswith(b'H ')}
    old_regular = actual - {'fairscape_models'}
    result = dict(manifest_sha256=hashlib.sha256(raw).hexdigest(),
        source_commit=value['source_commit'], source_manifest_unchanged=manifest.read_bytes() == raw,
        expected_regular_files=len(expected), actual_non_skip_entries=len(actual),
        old_rule_extra=sorted(old_regular - expected), old_rule_missing=sorted(expected - old_regular),
        selected_gitlinks={path: oid for path, oid in gitlinks.items() if path in actual},
        regular_roster_equal_after_gitlink_classification=(actual - gitlinks.keys()) == expected,
        index_delta=git(FAILED / 'tree', 'diff', '--cached', '--name-only',
                        value['source_commit']).decode().splitlines(),
        private_head=git(FAILED / 'tree', 'rev-parse', 'HEAD').decode().strip(),
        linked_worktree_exists=os.path.lexists(value['worktree']),
        contract_exists=os.path.lexists(FAILED.parent / 'wp1-contract-01bdcb22dad6.json'),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Static Git/index/artifact diagnosis only; no new materialization or validation run.')
    out = FAILED / 'sparse-index-diagnosis.json'
    with out.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result, indent=2, sort_keys=True))
    print('diagnosis_sha256=' + hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
