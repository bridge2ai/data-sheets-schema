#!/usr/bin/env python3
"""Pin one approved scratch-only #5213 ordering mutation, 2026-11-02.

Input: SHA-bound mutation.json from mutate_d76_integration_order_20261102.py.
Output: new external commit evidence and a detached local scratch commit whose
single parent is the final integration HEAD. Never updates an authoring branch,
remotes or source files. Archive that commit with the unchanged archive helper
before invoking the unchanged strict test runner. No tests launched here.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('d76_mutation_commit_common', HERE / 'd76_suite_common_20261031.py')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
ALLOWED = {'src/data_sheets_schema/api_runner.py', 'src/data_sheets_schema/cli/api.py'}


def physical(path):
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('absolute nontraversing path required')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError('symlinked path refused')
    return path.resolve(strict=True)


def git(root, *args, env=None, data=None, check=True):
    clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    clean.update(GIT_NO_LAZY_FETCH='1', GIT_CONFIG_GLOBAL='/dev/null',
                 GIT_CONFIG_NOSYSTEM='1', GIT_OPTIONAL_LOCKS='0')
    if env:
        clean.update(env)
    return subprocess.run(['git', '--no-replace-objects', '-C', str(root), *args],
        env=clean, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mutation', type=Path, required=True)
    parser.add_argument('--mutation-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.mutation.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.mutation_sha256:
        raise ValueError('mutation proof changed')
    proof = json.loads(raw)
    scratch, source = physical(Path(proof['scratch'])), physical(Path(proof['source']))
    if (scratch == source or not scratch.name.startswith('codex-5213-order-mutant-')
            or scratch == HERE.parents[1]):
        raise ValueError('dedicated physical scratch archive required')
    if not args.output.is_absolute() or '..' in args.output.parts or args.output.exists() or args.output.is_symlink():
        raise ValueError('fresh absolute nontraversing commit evidence directory required')
    parent = physical(args.output.parent)
    if parent.is_relative_to(scratch) or parent.is_relative_to(source):
        raise ValueError('fresh external commit evidence directory required')
    if git(scratch, 'symbolic-ref', '-q', 'HEAD', check=False).returncode != 1:
        raise ValueError('scratch must be detached, never an authoring branch')
    old_head = git(scratch, 'rev-parse', 'HEAD').stdout.decode().strip()
    expected_after = json.loads((args.mutation.parent / 'scratch-after.json').read_text())
    expected_source = json.loads((args.mutation.parent / 'source-before.json').read_text())
    if (old_head != proof['head'] or expected_source['head'] != proof['head']
            or common.source(scratch) != expected_after or common.source(source) != expected_source):
        raise ValueError('source or mutation differs from frozen mutation evidence')
    changed = set(proof['changed_files'])
    if not changed or not changed <= ALLOWED or proof['source_unchanged'] is not True:
        raise ValueError('unapproved mutation scope')
    observed = set(git(scratch, 'diff', '--name-only').stdout.decode().splitlines())
    if observed != changed or git(scratch, 'diff', '--cached', '--name-only').stdout:
        raise ValueError('scratch index or changes differ from declared mutation')
    if git(scratch, 'ls-files', '--others').stdout:
        raise ValueError('unexpected scratch files, including ignored files')
    if common.sha((args.mutation.parent / 'mutation.diff').read_bytes()) != proof['diff_sha256']:
        raise ValueError('recorded mutation patch changed')
    for name in changed:
        if expected_source['entries'][name]['sha256'] != proof['files'][name]['before_sha256']:
            raise ValueError('mutation original bytes differ from final source: ' + name)
        if common.sha((scratch / name).read_bytes()) != proof['files'][name]['after_sha256']:
            raise ValueError('mutation file differs: ' + name)
    args.output.mkdir(exist_ok=False)
    index_env = {'GIT_INDEX_FILE': str(args.output / 'scratch-index')}
    git(scratch, 'read-tree', old_head, env=index_env)
    for name in sorted(changed):
        blob = git(scratch, 'hash-object', '-w', '--stdin', data=(scratch / name).read_bytes()).stdout.decode().strip()
        mode = expected_after['entries'][name]['mode']
        git(scratch, 'update-index', '--add', '--cacheinfo', f'{mode},{blob},{name}', env=index_env)
    tree = git(scratch, 'write-tree', env=index_env).stdout.decode().strip()
    message = ('Scratch-only D76 ordering mutation: ' + proof['route'] + '\n\n'
               'Never publish. Parent is the final integration candidate.\n').encode()
    identity = {'GIT_AUTHOR_NAME': 'Offline mutation validation', 'GIT_AUTHOR_EMAIL': 'mutation@localhost',
                'GIT_COMMITTER_NAME': 'Offline mutation validation', 'GIT_COMMITTER_EMAIL': 'mutation@localhost'}
    head = git(scratch, 'commit-tree', tree, '-p', old_head, env=identity, data=message).stdout.decode().strip()
    git(scratch, 'update-ref', '--no-deref', 'HEAD', head, old_head)
    git(scratch, 'read-tree', head)  # index only; do not checkout or alter a source byte
    after = common.source(scratch)
    if (not after['tracked_exact'] or after['head'] != head or after['tree'] != tree
            or after['entries'] != expected_after['entries']
            or common.source(source) != expected_source
            or git(scratch, 'status', '--porcelain=v1', '--untracked-files=all').stdout):
        raise ValueError('scratch commit verification failed; preserve artifacts')
    common.save(args.output / 'committed-source.json', after)
    common.save(args.output / 'mutation-commit.json', {'head': head, 'parent': old_head, 'tree': tree,
        'scratch': str(scratch), 'route': proof['route'], 'changed_files': sorted(changed),
        'mutation_proof': str(args.mutation), 'mutation_sha256': args.mutation_sha256,
        'source_unchanged': True, 'tracked_exact': True, 'published': False,
        'helper_sha256': common.sha(Path(__file__).read_bytes()),
        'tests_executed': False, 'next': 'archive this exact mutation HEAD; use unchanged strict runner'})
    print(head)


if __name__ == '__main__':
    main()
