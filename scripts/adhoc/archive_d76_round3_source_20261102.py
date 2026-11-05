#!/usr/bin/env python3
"""Create a pinned, locally archived D76 validation source copy (2026-11-02).

Inputs: local repository and full commit, local FAIRSCAPE object source, fresh
destination/evidence directory. Outputs: retained tar files and source manifest.
No fetch, checkout, install, existing-directory mutation, or remote operations.
New Git metadata reads existing local objects solely for history-dependent tests.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def git(root, *args, **kwargs):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
               GIT_OPTIONAL_LOCKS='0', GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='protocol.allow',
               GIT_CONFIG_VALUE_0='never')
    return subprocess.run(['git', '--no-replace-objects', '-C', str(root), *args],
                          env=env, check=True, **kwargs)


def value(root, *args):
    return git(root, *args, stdout=subprocess.PIPE).stdout.decode().strip()


def physical_parent(path):
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('absolute non-traversing destination required')
    current = Path(path.anchor)
    for part in path.parts[1:-1]:
        current /= part
        if current.is_symlink() or not current.is_dir():
            raise ValueError('destination parent must be existing physical directories')


def safe_members(archive):
    members = archive.getmembers()
    names, symlinks = set(), set()
    for item in members:
        path = PurePosixPath(item.name)
        if path.is_absolute() or '..' in path.parts or '.git' in path.parts or item.name in names:
            raise ValueError('unsafe or duplicate archive path: ' + item.name)
        names.add(item.name)
        if item.issym():
            target = PurePosixPath(item.linkname)
            if target.is_absolute():
                raise ValueError('absolute archive symlink refused')
            resolved = list(path.parent.parts)
            for part in target.parts:
                if part == '..':
                    if not resolved:
                        raise ValueError('escaping archive symlink refused')
                    resolved.pop()
                elif part != '.':
                    resolved.append(part)
            symlinks.add(path)
        elif not (item.isfile() or item.isdir()):
            raise ValueError('nonregular archive member refused')
    if any(parent in symlinks for item in members for parent in PurePosixPath(item.name).parents):
        raise ValueError('archive member traverses a symlink')
    return members


def archive_one(repository, head, destination, tarpath):
    if not re.fullmatch(r'[0-9a-f]{40}', head) or value(repository, 'rev-parse', head + '^{commit}') != head:
        raise ValueError('exact full local commit required')
    with tarpath.open('xb') as output:
        git(repository, 'archive', '--format=tar', head, stdout=output)
    destination.mkdir(exist_ok=False)
    with tarfile.open(tarpath, 'r:') as archive:
        archive.extractall(destination, members=safe_members(archive), filter='data')
    # The files above came only from git archive. A fresh index/HEAD grants local
    # history access without replacing or checking out any archive file.
    git(destination, 'init', '--quiet', '--template=')
    objects = Path(value(repository, 'rev-parse', '--git-path', 'objects'))
    if not objects.is_absolute():
        objects = repository / objects
    objects = objects.resolve(strict=True)
    (destination / '.git/objects/info/alternates').write_text(str(objects) + '\n')
    (destination / '.git/HEAD').write_text(head + '\n')
    git(destination, 'read-tree', head)
    return {'head': head, 'git_tree': value(repository, 'rev-parse', head + '^{tree}'),
            'archive': str(tarpath), 'archive_sha256': sha(tarpath), 'archive_bytes': tarpath.stat().st_size,
            'source_method': 'git archive; metadata initialized afterwards without checkout',
            'local_object_alternate': str(objects)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True, type=Path)
    parser.add_argument('--head', required=True)
    parser.add_argument('--fairscape-source', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args()
    for path in (args.destination, args.evidence):
        physical_parent(path)
        if path.exists() or path.is_symlink():
            raise ValueError('fresh archive destination/evidence required')
    args.evidence.mkdir(exist_ok=False)
    report = archive_one(args.repository.resolve(strict=True), args.head, args.destination,
                         args.evidence / 'source.tar')
    link = value(args.repository, 'ls-tree', args.head, 'fairscape_models').split()
    if len(link) != 4 or link[:2] != ['160000', 'commit'] or link[3] != 'fairscape_models':
        raise ValueError('expected FAIRSCAPE gitlink missing')
    subdirectory = args.destination / 'fairscape_models'
    # Git archive emits an empty directory for a gitlink. Retain it; extract
    # the submodule into a fresh staging sibling, then move into the empty slot.
    staging = args.destination / '.d76-fairscape-archive-staging'
    sub = archive_one(args.fairscape_source.resolve(strict=True), link[2], staging,
                      args.evidence / 'fairscape.tar')
    if subdirectory.exists() and (subdirectory.is_symlink() or any(subdirectory.iterdir())):
        raise ValueError('gitlink archive directory unexpectedly nonempty')
    if subdirectory.exists():
        subdirectory.rmdir()  # Newly created empty archive placeholder only.
    staging.rename(subdirectory)
    report['fairscape'] = sub
    report['destination'] = str(args.destination)
    report['status'] = value(args.destination, 'status', '--porcelain=v1', '--untracked-files=all')
    if report['status']:
        raise ValueError('archived source not clean: ' + report['status'])
    with (args.evidence / 'archive-source.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
