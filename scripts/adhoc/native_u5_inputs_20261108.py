#!/usr/bin/env python3
"""Export immutable U5 comparison inputs from local Git, 2026-11-08 (#4354).

Inputs: U4 baseline, the named committed schema-3.2.0 input, and the committed
candidate HEAD for scanner comparison. Outputs: new scratch directories plus
per-file byte/Git-blob/SHA-256 manifests. The original API baseline remains a
separate input. No fetching, checkout, overlays, imports of production code or
writes to either worktree.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u5-prep'
BASE = 'd258611c5381bd7cf973817ebd2b6a04f65818b3'
SCHEMA = '5e382f0c423fa8b0a331340adcdfac5a328bd6b3'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'}
BASE_PATHS = ('src', 'tests', 'utils', 'configs', '.claude', '.github',
              'pyproject.toml', 'Makefile', 'project',
              'notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv')
# Discovery walks all three Python roots, follows their sibling documents,
# lists session assets/memory, and reads the explicit shared source manifest.
# Do not substitute the narrower API export or any live ignored files.
BASE_SCAN_PATHS = ('src', 'tests', 'utils', 'configs', '.claude', '.github',
                   'pyproject.toml', 'Makefile', 'project', 'notes', 'scripts',
                   'CLAUDE.md', 'CLAUDE.local.md',
                   'data/preprocessed/source_manifest.yaml')
MAX_EXPORT_BYTES = 500_000_000
MAX_EXPORT_FILES = 15000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', *args],
                                   cwd=ROOT, env=ENV, timeout=120)


def committed_inventory(commit, paths):
    """Preflight immutable Git metadata before allocating an archive or output."""
    if re.fullmatch(r'[0-9a-f]{40}', commit) is None:
        raise ValueError('export commit must be a full immutable SHA')
    if not paths or len(set(paths)) != len(paths):
        raise ValueError('export path mask must be nonempty and distinct')
    listed = git('ls-tree', '-r', '-l', '-z', commit, '--', *paths)
    expected = {}
    total = 0
    for row in listed.split(b'\0'):
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        mode, kind, oid, size = metadata.decode().split()
        if kind != 'blob' or mode not in ('100644', '100755'):
            raise ValueError('only ordinary committed file inputs are admitted')
        relative = PurePosixPath(name.decode())
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('unsafe committed input path')
        if str(relative) in expected:
            raise ValueError('duplicate committed input path')
        size = int(size)
        if size < 0:
            raise ValueError('invalid committed input size')
        expected[str(relative)] = (mode, oid, size)
        total += size
        if len(expected) > MAX_EXPORT_FILES or total > MAX_EXPORT_BYTES:
            raise ValueError('committed export exceeds file or byte bound')
    if not expected:
        raise ValueError('unexpected export inventory')
    return expected, total


def materialize(label, commit, paths):
    if re.fullmatch(r'[a-z0-9][a-z0-9-]*', label) is None:
        raise ValueError('export label must be a literal safe component')
    destination = SCRATCH / label
    if destination.resolve() != destination or os.path.lexists(destination):
        raise ValueError('export requires a fresh literal assigned scratch directory')
    expected, total = committed_inventory(commit, paths)
    commit_tree = git('rev-parse', commit + '^{tree}').decode().strip()
    # Omit non-existing optional prefixes; archive rejects an unmatched pathspec.
    present = [p for p in paths if any(n == p or n.startswith(p + '/') for n in expected)]
    raw = git('archive', '--format=tar', commit, '--', *present)
    if len(raw) > MAX_EXPORT_BYTES:
        raise ValueError('comparison archive exceeds 500 MB')
    destination.mkdir()
    (destination / 'source.tar').write_bytes(raw)
    tree = destination / 'tree'
    tree.mkdir()
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        for member in archive:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('unsafe archive member')
            if member.isdir():
                continue
            if not member.isfile() or member.name not in expected or member.name in files:
                raise ValueError('unexpected archive member')
            mode, oid, size = expected[member.name]
            if member.size != size:
                raise ValueError('archived size differs from committed Git blob')
            data = archive.extractfile(member).read()
            identity = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if identity != oid:
                raise ValueError('archived bytes differ from committed Git blob')
            target = tree / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
            target.chmod(0o755 if mode == '100755' else 0o644)
            files[member.name] = {'mode': mode, 'git_blob': oid, 'sha256': sha(data), 'bytes': len(data)}
    if set(files) != set(expected):
        raise ValueError('incomplete committed export')
    manifest = {'kind': 'u5_named_external_git_input', 'commit': commit,
                'commit_tree': commit_tree, 'path_mask': list(paths),
                'entry_count': len(expected), 'total_blob_bytes': total,
                'archive_sha256': sha(raw), 'archive_bytes': len(raw),
                'tree': str(tree), 'files': files,
                'scope': 'Committed files under the declared mask only; no live ignored inputs, '
                         'schema installation, full filesystem or native acceptance.'}
    encoded = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    (destination / 'manifest.json').write_bytes(encoded)
    print(json.dumps({'input': label, 'commit': commit, 'files': len(files),
                      'total_blob_bytes': total, 'archive_bytes': len(raw),
                      'manifest_sha256': sha(encoded), 'archive_sha256': sha(raw)}))


def checked_scanner_input(label, expected_commit):
    """Check exact committed inventory and physical export, not just its claims."""
    if label not in ('scanner-baseline-' + BASE[:9], 'scanner-candidate'):
        raise ValueError('unknown scanner export label')
    directory = SCRATCH / label
    if directory.resolve() != directory:
        raise ValueError('scanner export directory must not be an alias')
    manifest_path = directory / 'manifest.json'
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError('scanner manifest must be a regular file')
    manifest = json.loads(manifest_path.read_bytes())
    if manifest.get('commit') != expected_commit:
        raise ValueError('scanner input commit differs from selected head')
    if manifest.get('path_mask') != list(BASE_SCAN_PATHS):
        raise ValueError('scanner input mask is incomplete or different')
    expected, total = committed_inventory(expected_commit, BASE_SCAN_PATHS)
    tree = directory / 'tree'
    if tree.resolve() != tree or manifest.get('tree') != str(tree):
        raise ValueError('scanner export tree differs from the selected physical tree')
    if manifest.get('commit_tree') != git('rev-parse', expected_commit + '^{tree}').decode().strip():
        raise ValueError('scanner commit tree differs from Git')
    files = manifest.get('files')
    if (not isinstance(files, dict) or set(files) != set(expected)
            or type(manifest.get('entry_count')) is not int or manifest['entry_count'] != len(expected)
            or type(manifest.get('total_blob_bytes')) is not int or manifest['total_blob_bytes'] != total):
        raise ValueError('scanner inventory is incomplete or inconsistent with Git')
    actual = set()
    for parent, dirs, names in os.walk(tree, followlinks=False):
        for name in dirs:
            if (Path(parent) / name).is_symlink():
                raise ValueError('scanner export contains a directory alias')
        for name in names:
            path = Path(parent) / name
            relative = path.relative_to(tree).as_posix()
            if relative not in expected or path.is_symlink():
                raise ValueError('scanner export contains an extra or aliased input')
            mode, oid, size = expected[relative]
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size != size:
                raise ValueError('scanner export input type or size changed')
            if stat.S_IMODE(info.st_mode) != (0o755 if mode == '100755' else 0o644):
                raise ValueError('scanner export input mode changed')
            raw = path.read_bytes()
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            if blob != oid or files[relative] != {
                    'mode': mode, 'git_blob': oid, 'sha256': sha(raw), 'bytes': size}:
                raise ValueError('scanner export bytes or manifest pin differ from Git')
            actual.add(relative)
    if actual != set(expected):
        raise ValueError('scanner export is missing committed inputs')
    return tree, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', choices=('baseline', 'schema', 'scanner-baseline', 'scanner-candidate'))
    args = parser.parse_args()
    if args.input == 'baseline':
        materialize('baseline-' + BASE[:9], BASE, BASE_PATHS)
    elif args.input == 'schema':
        materialize('schema-' + SCHEMA[:9], SCHEMA, ('src/data_sheets_schema/schema',))
    elif args.input == 'scanner-baseline':
        materialize('scanner-baseline-' + BASE[:9], BASE, BASE_SCAN_PATHS)
    else:
        candidate = git('rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
        materialize('scanner-candidate', candidate, BASE_SCAN_PATHS)


if __name__ == '__main__':
    main()
