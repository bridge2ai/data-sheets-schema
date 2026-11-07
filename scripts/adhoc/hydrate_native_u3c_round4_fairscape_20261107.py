#!/usr/bin/env python3
"""Materialize the exact local FAIRSCAPE gitlink in C4 scratch, 2026-11-07.

Inputs: current C4 gitlink and the already-local primary FAIRSCAPE Git object.
Outputs: a new scratch dependency tree, original tar and SHA manifest. No
network, installer, submodule initialization, Git mutation or worktree write.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
PIN = '8c80311d7d8b0fadac07dca9567d632103691f48'
SCRATCH = ROOT.parent / 'scratch-native-u3c-r4'
SOURCE = ROOT.parent.parent / 'data-sheets-schema/fairscape_models'
DESTINATION = SCRATCH / 'dependencies' / ('fairscape-' + PIN)
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': '', 'GIT_OPTIONAL_LOCKS': '0'}
MAX_BYTES = 64 * 1024 * 1024


def git(cwd, *args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd, env=ENV, timeout=30)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned_files():
    expected = f'160000 commit {PIN}\tfairscape_models\n'.encode()
    if git(ROOT, 'ls-tree', 'HEAD', 'fairscape_models') != expected:
        raise RuntimeError('C4 FAIRSCAPE gitlink changed')
    rows = {}
    for entry in git(SOURCE, 'ls-tree', '-rz', PIN).split(b'\0'):
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.decode('ascii').split()
        name = raw_name.decode('utf-8')
        path = Path(name)
        if (mode not in ('100644', '100755') or kind != 'blob' or name in rows
                or path.is_absolute() or '..' in path.parts or '.git' in path.parts):
            raise RuntimeError('unsupported FAIRSCAPE git tree entry')
        rows[name] = {'mode': mode, 'git_blob': oid}
    if not rows or len(rows) > 4096:
        raise RuntimeError('empty or oversized FAIRSCAPE git tree')
    return rows


def tree_evidence(tree, expected):
    actual = {}
    total = 0
    for path in sorted(tree.rglob('*')):
        if path.is_symlink():
            raise RuntimeError('symlink in materialized FAIRSCAPE tree')
        if path.is_dir():
            continue
        name = path.relative_to(tree).as_posix()
        if not path.is_file() or name not in expected or path.stat().st_size > MAX_BYTES:
            raise RuntimeError('unexpected FAIRSCAPE dependency file: ' + name)
        raw = path.read_bytes()
        total += len(raw)
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if blob != expected[name]['git_blob'] or total > MAX_BYTES:
            raise RuntimeError('FAIRSCAPE bytes differ from the local pinned Git object: ' + name)
        actual[name] = {**expected[name], 'sha256': sha(raw), 'bytes': len(raw)}
    if set(actual) != set(expected):
        raise RuntimeError('incomplete FAIRSCAPE dependency tree')
    return actual


def dependency_evidence():
    if not os.path.lexists(DESTINATION):
        return {'available': False, 'gitlink': PIN, 'destination': str(DESTINATION)}
    if DESTINATION != DESTINATION.resolve(strict=True) or not DESTINATION.is_dir():
        raise RuntimeError('FAIRSCAPE destination must be a literal directory')
    manifest_path = DESTINATION / 'manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    tree = DESTINATION / 'tree'
    if tree != tree.resolve(strict=True):
        raise RuntimeError('FAIRSCAPE tree must not be a symlink')
    files = tree_evidence(tree, pinned_files())
    archive = DESTINATION / 'source.tar'
    if (manifest.get('gitlink') != PIN or manifest.get('files') != files
            or manifest.get('archive_sha256') != sha(archive.read_bytes())):
        raise RuntimeError('FAIRSCAPE materialization manifest mismatch')
    return {'available': True, 'gitlink': PIN, 'package_root': str(tree),
            'manifest_sha256': sha(manifest_path.read_bytes()),
            'archive_sha256': manifest['archive_sha256'], 'file_count': len(files),
            'validation': 'every file independently compared with exact local Git blob identity'}


def main():
    if os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'):
        raise SystemExit('quiet window active; dependency materialization not started')
    if not SCRATCH.is_dir() or SCRATCH != SCRATCH.resolve(strict=True):
        raise RuntimeError('canonical C4 scratch directory must already exist')
    expected = pinned_files()
    raw = git(SOURCE, 'archive', '--format=tar', PIN)
    if len(raw) > MAX_BYTES:
        raise RuntimeError('FAIRSCAPE archive exceeds 64 MiB')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        members = archive.getmembers()
        seen = set()
        total = 0
        for member in members:
            name = Path(member.name)
            if (name.is_absolute() or '..' in name.parts or '.git' in name.parts
                    or member.name in seen or not (member.isfile() or member.isdir())):
                raise RuntimeError('unsafe or duplicate archive member')
            seen.add(member.name)
            total += member.size
        if len(members) > 8192 or total > MAX_BYTES:
            raise RuntimeError('oversized FAIRSCAPE archive contents')
        parent = DESTINATION.parent
        parent.mkdir(exist_ok=True)
        if parent != parent.resolve(strict=True):
            raise RuntimeError('dependency parent must not be a symlink')
        DESTINATION.mkdir(exist_ok=False)
        tree = DESTINATION / 'tree'
        tree.mkdir()
        archive.extractall(tree, members=members, filter='data')
    (DESTINATION / 'source.tar').write_bytes(raw)
    manifest = {'gitlink': PIN, 'local_object_source': str(SOURCE),
                'archive_sha256': sha(raw), 'files': tree_evidence(tree, expected)}
    with (DESTINATION / 'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    evidence = dependency_evidence()
    print(json.dumps(evidence, sort_keys=True))


if __name__ == '__main__':
    main()
