#!/usr/bin/env python3
# Purpose: retain source identity and observed import provenance for Wave 7 CI-layout runs.
# Inputs: frozen local checkout; outputs: JSON-ready source/import records, no mutations.
# Refs integration of PRs #5094–#5213; 2026-10-29. Adapted from Wave 3 attestation.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def git(root, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *args], env=env)


def source(root):
    entries, exact = {}, True
    for row in git(root, 'ls-tree', '-rz', 'HEAD').decode().split('\0'):
        if not row:
            continue
        meta, name = row.split('\t', 1)
        mode, kind, oid = meta.split()
        path = root / name
        if kind == 'commit':
            entries[name] = {'gitlink': oid, 'contents_attested': False}
            continue
        if not path.exists() and not path.is_symlink():
            entries[name] = {'missing': True}
            exact = False
            continue
        raw = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
        actual_mode = '120000' if path.is_symlink() else ('100755' if path.stat().st_mode & 0o111 else '100644')
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        exact = exact and blob == oid and actual_mode == mode
        entries[name] = {'git_blob': blob, 'sha256': sha(raw), 'bytes': len(raw), 'mode': actual_mode}
    return {'head': git(root, 'rev-parse', 'HEAD').decode().strip(),
            'tree': git(root, 'rev-parse', 'HEAD^{tree}').decode().strip(),
            'tracked_exact': exact, 'entries': entries}


def origins(root, baseline):
    found = {}
    for name, module in tuple(sys.modules.items()):
        if name == 'data_sheets_schema' or name.startswith('data_sheets_schema.'):
            expected = root / 'src'
        elif name == 'tests' or name.startswith('tests.'):
            expected = root / 'tests'
        elif name == 'utils' or name.startswith('utils.'):
            expected = root / 'utils'
        else:
            continue
        paths = list(getattr(module, '__path__', ()))
        if getattr(module, '__file__', None):
            paths.append(module.__file__)
        if not paths or any(not Path(p).resolve(strict=True).is_relative_to(expected) for p in paths):
            raise ValueError('foreign or missing module origin: ' + name)
        if getattr(module, '__file__', None):
            path = Path(module.__file__).resolve(strict=True)
            item = baseline['entries'].get(str(path.relative_to(root)), {})
            if sha(path.read_bytes()) != item.get('sha256'):
                raise ValueError('module origin differs from frozen source: ' + name)
        found[name] = paths
    return found


def fairscape(root, baseline):
    path = root / 'fairscape_models'
    expected = baseline['entries'].get('fairscape_models', {}).get('gitlink')
    if not expected or not (path / '.git').exists():
        raise ValueError('CI requires the locally initialized fairscape_models gitlink; no automatic fetch')
    actual = git(path, 'rev-parse', 'HEAD').decode().strip()
    top = Path(git(path, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    dirty = git(path, 'status', '--porcelain=v1', '--untracked-files=all').decode()
    if actual != expected or top != path.resolve() or dirty:
        raise ValueError('fairscape_models must be clean at its exact recorded gitlink')
    return {'expected_gitlink': expected, 'head': actual, 'clean': True,
            'contents_attested': False, 'scope': 'local Git identity/status only; no network initialization'}
