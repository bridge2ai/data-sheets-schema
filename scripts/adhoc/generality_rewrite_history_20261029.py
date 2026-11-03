#!/usr/bin/env python3
# Purpose: remove G1 evidence from every unpublished commit, preserving all blobs.
# Inputs: clean G1 branch on 55c7b94b8, original backup branch, external evidence dir.
# Outputs: rewritten merge-free branch, verified evidence archive and commit map.
# G1 N9, 2026-10-29. No push, prune, shared-default rewrite or provider operation.
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE = '55c7b94b838eb500888055da5a47acf2ee9e2e15'
BRANCH = 'codex/wave7-generality-g1-20261029'
ORIGINAL = 'codex/wave7-generality-g1-orig-20261029'
PREFIX = 'notes/reviews/generality_g1_evidence_2026-10-29/'

def git(*args, **kwargs):
    return subprocess.check_output(['git', *args], **kwargs)

parser = argparse.ArgumentParser()
parser.add_argument('evidence', type=Path)
args = parser.parse_args()
root = Path(git('rev-parse', '--show-toplevel').decode().strip())
out = args.evidence.resolve()
assert not out.is_relative_to(root)
assert git('branch', '--show-current').decode().strip() == BRANCH
assert not git('status', '--porcelain'), 'commit the reproduction helper first'
assert git('rev-parse', ORIGINAL).decode().strip() == '0ba88ba120aa29b86a885aaaa579b8bf59148d3a'
head = git('rev-parse', 'HEAD').decode().strip()
assert not git('rev-list', '--merges', f'{BASE}..{head}')
commits = git('rev-list', '--reverse', f'{BASE}..{head}').decode().splitlines()
out.mkdir(parents=True, exist_ok=True)
archive = out / 'original-g1'
archive.mkdir(exist_ok=True)
blobs = out / 'history-blobs'
blobs.mkdir(exist_ok=True)
env = dict(os.environ, GIT_INDEX_FILE=str(out / 'rewrite.index'))
mapping, manifest = {}, []
parent = BASE
for position, old in enumerate(commits):
    git('read-tree', old, env=env)
    paths = git('ls-tree', '-rz', old, '--', PREFIX).split(b'\0')
    removed = []
    for entry in filter(None, paths):
        metadata, path_raw = entry.split(b'\t', 1)
        _mode, kind, oid = metadata.split()
        assert kind == b'blob'
        path = path_raw.decode()
        assert path.startswith(PREFIX)
        raw = git('cat-file', 'blob', oid.decode())
        saved = blobs / oid.decode()
        if not saved.exists():
            saved.write_bytes(raw)
        assert saved.read_bytes() == raw
        manifest.append({'commit': old, 'path': path, 'blob': oid.decode(),
                         'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
        if old == head:
            target = archive / path.removeprefix(PREFIX)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            assert target.read_bytes() == raw
        removed.append(path)
    if removed:
        git('update-index', '--force-remove', '--', *removed, env=env)
    tree = git('write-tree', env=env).decode().strip()
    metadata = git('show', '-s', '--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI', old).decode().rstrip('\n').split('\0')
    commit_env = dict(os.environ, **dict(zip(
        ['GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_AUTHOR_DATE',
         'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL', 'GIT_COMMITTER_DATE'], metadata)))
    message = git('show', '-s', '--format=%B', old)
    new = git('commit-tree', tree, '-p', parent, input=message, env=commit_env).decode().strip()
    assert git('rev-parse', new + '^{tree}').decode().strip() == tree
    assert not git('ls-tree', '-r', '--name-only', new, '--', PREFIX)
    changed = git('diff', '--name-only', old, new).decode().splitlines()
    assert all(p.startswith(PREFIX) for p in changed)
    mapping[old] = new
    parent = new
    if position == 0:
        print('Canary: first commit rebuilt, tree verified, evidence paths absent.', flush=True)
assert not git('rev-list', '--merges', f'{BASE}..{parent}')
assert all(p.startswith(PREFIX) for p in git('diff', '--name-only', head, parent).decode().splitlines())
for commit in mapping.values():
    added = git('diff-tree', '--no-commit-id', '--diff-filter=A', '--name-only', '-r', commit).decode().splitlines()
    assert not any(p.endswith('.gz') for p in added), (commit, added)
(out / 'history-evidence-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
(out / 'commit-map.json').write_text(json.dumps({'base': BASE, 'old_head': head,
    'new_head': parent, 'commits': mapping}, indent=2) + '\n')
git('update-ref', 'refs/heads/codex/wave7-generality-g1-pre-rewrite-20261029', head)
git('update-ref', 'refs/heads/' + BRANCH, parent, head)
# The verified only tree difference is the already archived evidence directory.
git('read-tree', '--reset', '-u', parent)
assert not git('status', '--porcelain')
print(json.dumps({'old_head': head, 'new_head': parent, 'commits': len(mapping),
                  'archived_evidence_versions': len(manifest)}, indent=2), flush=True)
