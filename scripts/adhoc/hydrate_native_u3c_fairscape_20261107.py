#!/usr/bin/env python3
"""Populate C's empty pinned FAIRSCAPE dependency offline, U3-C r2, 2026-11-07.

Input: exact existing local submodule Git object; output: only the empty
fairscape_models directory in the assigned C checkout, plus printed identities.
No checkout source, Git index, remote, dependency installer or credential is used.
"""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = '8c80311d7d8b0fadac07dca9567d632103691f48'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': ''}


def git(cwd, *args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd, env=ENV, timeout=30)


def main():
    if git(ROOT, 'branch', '--show-current').strip() != b'codex/native-u3c-controller-20261107':
        raise SystemExit('only the assigned U3-C checkout may be populated')
    target = ROOT / 'fairscape_models'
    if target.is_symlink() or not target.is_dir() or any(target.iterdir()):
        raise SystemExit('requires the existing empty dependency directory')
    expected = f'160000 commit {PIN}\tfairscape_models\n'.encode()
    if git(ROOT, 'ls-tree', 'HEAD', 'fairscape_models') != expected:
        raise SystemExit('dependency pin changed')
    source = ROOT.parent.parent / 'data-sheets-schema/fairscape_models'
    raw = git(source, 'archive', '--format=tar', PIN)
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        members = archive.getmembers()
        for member in members:
            path = Path(member.name)
            if (path.is_absolute() or '..' in path.parts or '.git' in path.parts
                    or not (member.isfile() or member.isdir())):
                raise SystemExit('unexpected dependency archive entry')
        archive.extractall(target, members=members, filter='data')
    package = target / 'fairscape_models/rocrate.py'
    if not package.is_file() or not package.stat().st_size:
        raise SystemExit('dependency artifact was not populated')
    print(json.dumps({'gitlink': PIN, 'archive_sha256': hashlib.sha256(raw).hexdigest(),
        'rocrate_sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
        'target': str(target)}, sort_keys=True))


if __name__ == '__main__':
    main()
