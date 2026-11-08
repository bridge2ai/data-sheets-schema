#!/usr/bin/env python3
"""Export immutable U5 comparison inputs from local Git, 2026-11-08 (#4354).

Inputs: U4 baseline and the named committed schema-3.2.0 input. Outputs: new
scratch directories plus per-file byte/Git-blob/SHA-256 manifests. No fetching,
checkout, overlays, imports of production code or writes to either worktree.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
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


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', *args],
                                   cwd=ROOT, env=ENV, timeout=120)


def materialize(label, commit, paths):
    destination = SCRATCH / label
    if destination.resolve() != destination or os.path.lexists(destination):
        raise ValueError('export requires a fresh literal assigned scratch directory')
    listed = git('ls-tree', '-r', '-z', commit, '--', *paths)
    expected = {}
    for row in listed.split(b'\0'):
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        if kind != 'blob' or mode not in ('100644', '100755'):
            raise ValueError('only ordinary committed file inputs are admitted')
        expected[name.decode()] = (mode, oid)
    if not expected or len(expected) > 15000:
        raise ValueError('unexpected export inventory')
    # Omit non-existing optional prefixes; archive rejects an unmatched pathspec.
    present = [p for p in paths if any(n == p or n.startswith(p + '/') for n in expected)]
    raw = git('archive', '--format=tar', commit, '--', *present)
    if len(raw) > 500_000_000:
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
            data = archive.extractfile(member).read()
            mode, oid = expected[member.name]
            identity = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if identity != oid:
                raise ValueError('archived bytes differ from committed Git blob')
            target = tree / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
            target.chmod(0o755 if mode == '100755' else 0o644)
            files[member.name] = {'git_blob': oid, 'sha256': sha(data), 'bytes': len(data)}
    if set(files) != set(expected):
        raise ValueError('incomplete committed export')
    manifest = {'kind': 'u5_named_external_git_input', 'commit': commit,
                'archive_sha256': sha(raw), 'tree': str(tree), 'files': files,
                'scope': 'measurement input only; no schema installation or acceptance'}
    encoded = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    (destination / 'manifest.json').write_bytes(encoded)
    print(json.dumps({'input': label, 'commit': commit, 'files': len(files),
                      'manifest_sha256': sha(encoded), 'archive_sha256': sha(raw)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', choices=('baseline', 'schema'))
    args = parser.parse_args()
    if args.input == 'baseline':
        materialize('baseline-' + BASE[:9], BASE, BASE_PATHS)
    else:
        materialize('schema-' + SCHEMA[:9], SCHEMA, ('src/data_sheets_schema/schema',))


if __name__ == '__main__':
    main()
