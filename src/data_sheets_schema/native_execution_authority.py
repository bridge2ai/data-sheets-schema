"""Additive source authority for explicit direct native execution (#4334).

The released controller manifest and neutral supervisor authority stay intact.
Only the keep-awake primitives are added; no historical launcher is invoked.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib
from pathlib import Path
import re
import subprocess
import sys

from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_supervisor_authority as neutral
from data_sheets_schema.resources import git_env

ROOT = neutral.ROOT
ADDITIONAL = {
    'run_direct_canary_awake': {
        'path': 'notes/claudecode_direct/run_direct_canary_awake.py',
        'sha256': 'd0ad068e83a1ddf40c4c2c401ea5a264403e02c569391cf5433c47d14c5b69a5',
    },
}
PACKAGE = 'src/data_sheets_schema'
SOURCE_SUFFIXES = frozenset(('.py', '.yaml', '.json'))


def dependency_identity():
    base = neutral.dependency_identity()
    for name, pin in ADDITIONAL.items():
        target = ROOT / pin['path']
        if draft._sha(target.read_bytes()) != pin['sha256']:
            raise ValueError(f'additional native execution dependency changed: {name}')
        loaded = sys.modules.get(name)
        if loaded is not None and Path(getattr(loaded, '__file__', '')).resolve() != target.resolve():
            raise ValueError(f'native execution dependency imported from another origin: {name}')
    return {'version': 1, 'base': base, 'additional_modules': ADDITIONAL}


def _package_roster(raw):
    """Read literal NUL-delimited tree paths; never follow links or an index."""
    if not raw or not raw.endswith(b'\0'):
        raise ValueError('incomplete committed package tree')
    seen, trees, sources = set(), set(), set()
    for record in raw[:-1].split(b'\0'):
        header, separator, path_raw = record.partition(b'\t')
        parts = header.split(b' ')
        if (not separator or len(parts) != 3
                or not re.fullmatch(rb'[0-9a-f]{40}|[0-9a-f]{64}', parts[2])):
            raise ValueError('malformed committed package tree entry')
        try:
            path = path_raw.decode('utf-8')
        except UnicodeDecodeError as error:
            raise ValueError('committed package path is not UTF-8') from error
        if (not path or any(part in ('', '.', '..') for part in path.split('/'))
                or path in seen
                or not (path in ('src', PACKAGE) or path.startswith(PACKAGE + '/'))):
            raise ValueError('duplicate or invalid committed package path')
        seen.add(path)
        mode, kind = parts[:2]
        if mode == b'040000' and kind == b'tree':
            trees.add(path)
            continue
        if path in ('src', PACKAGE) or mode == b'160000' or kind == b'commit':
            raise ValueError('committed package contains a non-tree boundary or Gitlink')
        if kind != b'blob' or mode not in (b'100644', b'100755', b'120000'):
            raise ValueError('invalid committed package object kind or mode')
        if Path(path).suffix in SOURCE_SUFFIXES:
            if mode not in (b'100644', b'100755'):
                raise ValueError('committed package source is not a regular blob: ' + path)
            # The unchanged batch object proof uses LF-delimited queries.
            # Refuse unsupported literal names, never split/quote/drop them.
            if '\n' in path or '\r' in path:
                raise ValueError('committed package source has an unsupported line-break path')
            sources.add(path)
    if not {'src', PACKAGE} <= trees:
        raise ValueError('committed package tree is missing')
    return sources


def _require_package_roster(source_commit, package_sources):
    if (type(source_commit) is not str
            or re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', source_commit) is None
            or type(package_sources) is not dict
            or any(type(path) is not str for path in package_sources)):
        raise ValueError('invalid committed package source declaration')
    tree = subprocess.run(
        ['git', '--no-replace-objects', 'ls-tree', '-r', '-t', '-z', '--full-tree',
         source_commit, '--', PACKAGE + '/'],
        cwd=ROOT, env=git_env(), capture_output=True, timeout=30, check=True)
    expected = _package_roster(tree.stdout)
    current = set(package_sources)
    if expected != current:
        raise ValueError('committed package source roster differs: missing=' +
                         repr(sorted(expected - current)) + '; extra=' + repr(sorted(current - expected)))


def require_committed(identity):
    """Review/CI authority cannot describe different uncommitted package bytes.

    Require the complete package roster, then compare actual dependency SHA256
    values with blobs in the named local Git commit. This queries the local
    object database only, with Git overrides removed. Tests/docs outside the
    consumed closure do not affect admission.
    """
    if draft._encoded(dependency_identity()) != draft._encoded(identity):
        raise ValueError('native execution dependency identity changed')
    base = identity['base']
    _require_package_roster(base['source_commit'], base['package_sources'])
    paths = dict(base['package_sources'])
    paths.update({pin['path']: pin['sha256'] for pin in base['modules'].values()})
    paths.update({pin['path']: pin['sha256'] for pin in identity['additional_modules'].values()})
    # One persistent reader avoids a process for every package source.
    query = ''.join(f"{base['source_commit']}:{path}\n" for path in sorted(paths)).encode()
    proc = subprocess.run(['git', '--no-replace-objects', 'cat-file', '--batch'], cwd=ROOT, env=git_env(),
                          input=query, capture_output=True, timeout=30, check=True)
    offset = 0
    for path in sorted(paths):
        end = proc.stdout.find(b'\n', offset)
        if end < 0:
            raise ValueError('incomplete source-object proof')
        header = proc.stdout[offset:end].split()
        if len(header) != 3 or header[1] != b'blob':
            raise ValueError(f'consumed source is not committed at the reviewed head: {path}')
        size = int(header[2])
        raw = proc.stdout[end + 1:end + 1 + size]
        offset = end + size + 2
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != paths[path]:
            raise ValueError(f'consumed source differs from the reviewed commit: {path}')
    if offset != len(proc.stdout):
        raise ValueError('unexpected source-object proof tail')


@contextmanager
def loaded_dependencies(expected):
    """Load exact module origins, then restore imported bare-module/path state."""
    if draft._encoded(dependency_identity()) != draft._encoded(expected):
        raise ValueError('native execution dependency identity changed')
    previous = {name: sys.modules.get(name) for name in ADDITIONAL}
    old_path = list(sys.path)
    try:
        with neutral.loaded_dependencies(expected['base']) as controls:
            sys.path.insert(0, str(ROOT / 'notes/claudecode_direct'))
            extra = {name: importlib.import_module(name) for name in ADDITIONAL}
            if draft._encoded(dependency_identity()) != draft._encoded(expected):
                raise ValueError('loaded native execution dependency identity changed')
            yield {**controls, **extra}
    finally:
        sys.path[:] = old_path
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
