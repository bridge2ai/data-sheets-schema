#!/usr/bin/env python3
"""Inspect C4 plus pinned D8 import graphs, without importing D, 2026-11-07.

Inputs: actual C4 package bytes; git-show D8's ten consumers and two neutral
dependencies. Outputs: a fresh scratch-only overlay, per-file origin manifest,
and unchanged A guard outcomes. Run through the C4 diagnostic pytest node.
This uncommitted composite proves no loader lifetime or execution admission.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3c-r4'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
D_HEAD = '3ab9fbc189f647d0abf00a50ab4c35634fe5228e'
D_CONSUMERS = (
    'native_execution_engine', 'native_gate_engine', 'native_subscription_guard',
    'native_shared_execution', 'native_shared_gates', 'native_shared_permissions',
    'native_shared_publication', 'native_shared_registration',
    'native_shared_results', 'native_shared_schema_gates',
)
D_SUPPORT = ('native_shared_gate_primitives', 'native_shared_runtime_values')
C_CONSUMERS = (
    'native_shared_attribution', 'native_shared_capture', 'native_shared_controller',
    'native_shared_current', 'native_shared_effects', 'native_shared_observations',
    'native_shared_phase', 'native_shared_policy', 'native_shared_receipts',
    'native_shared_stage', 'native_shared_streams',
    'native_shared_controls', 'native_shared_authority_wire',
    'native_shared_permission_protocol', 'native_shared_runtime_constants',
    'native_shared_evidence',
)
OLD_BOOTSTRAP = ('consumer cannot import verifier bootstrap boundary: '
                 'data_sheets_schema.native_execution_registration_v2')
OLD_REFUSALS = {name: OLD_BOOTSTRAP for name in (
    'native_gate_engine', 'native_shared_execution', 'native_shared_gates',
    'native_shared_publication', 'native_shared_registration', 'native_shared_results')}
OLD_REFUSALS['native_shared_permissions'] = (
    'consumer package import has missing or ambiguous source: '
    'data_sheets_schema.native_shared_permission_protocol')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def require_network_denial():
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', 0))
        except OSError as exc:
            if exc.errno == errno.EPERM:
                return {'network_bind_denied': True, 'errno': exc.errno}
            raise
    raise RuntimeError('census must run inside the C4 network-denied test runner')


def package_files(root):
    result = {}
    for path in sorted((root / 'src/data_sheets_schema').rglob('*')):
        if path.suffix not in ('.py', '.yaml', '.json'):
            continue
        if path.is_symlink() or not path.is_file():
            raise RuntimeError('package inventory requires regular source files: ' + str(path))
        if path.stat().st_size > 64 * 1024 * 1024:
            raise RuntimeError('individual census source exceeds 64 MiB')
        result[path.relative_to(root).as_posix()] = path.read_bytes()
    if not result or sum(map(len, result.values())) > 256 * 1024 * 1024:
        raise RuntimeError('empty or oversized census package')
    return result


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT,
                                   env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'}, timeout=30)


def build_and_inspect(out, dependency_site):
    require_network_denial()
    if os.path.lexists(LOCK):
        raise RuntimeError('quiet window is active; census not started')
    out = Path(out).absolute()
    if out != out.resolve() or out == SCRATCH or not out.is_relative_to(SCRATCH):
        raise ValueError('census output must be a fresh literal C4 scratch path')
    dependency_site = Path(dependency_site)
    if (dependency_site != dependency_site.resolve(strict=True)
            or dependency_site.name != 'site-packages' or not dependency_site.is_dir()):
        raise ValueError('expected physical dependency site; no site hooks are loaded')
    out.mkdir(parents=False, exist_ok=False)
    overlay = out / 'overlay'
    original = package_files(ROOT)
    sources = dict(original)
    origins = {name: {'kind': 'current_C4', 'sha256': sha(raw), 'bytes': len(raw)}
               for name, raw in sources.items()}
    for name in (*D_CONSUMERS, *D_SUPPORT):
        relative = 'src/data_sheets_schema/' + name + '.py'
        raw = git('show', D_HEAD + ':' + relative)
        if name in D_SUPPORT and relative in sources and sources[relative] != raw:
            raise RuntimeError('C/D neutral dependency conflict requires review: ' + relative)
        prior = sha(sources[relative]) if relative in sources else None
        sources[relative] = raw
        origins[relative] = {'kind': 'git_show_D8', 'commit': D_HEAD,
                             'sha256': sha(raw), 'bytes': len(raw), 'prior_C4_sha256': prior}
    for name, raw in sources.items():
        path = overlay / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    manifest = {'C4_head': git('rev-parse', 'HEAD').decode().strip(),
                'C4_status': git('status', '--porcelain', '--untracked-files=normal').decode(),
                'D8_head': D_HEAD, 'files': origins,
                'overlay': str(overlay), 'helper_sha256': sha(Path(__file__).read_bytes()),
                'scope': 'uncommitted source overlay; static graph census only; D consumers never imported'}
    if manifest['C4_status']:
        raise RuntimeError('C4 census requires a committed clean candidate')
    save(out / 'manifest.json', manifest)
    env = {key: value for key, value in os.environ.items() if key in (
        'PATH', 'HOME', 'TMPDIR', 'LANG', 'PYTHONNOUSERSITE', 'PYTHONSAFEPATH',
        'PYTHONDONTWRITEBYTECODE', 'GIT_NO_LAZY_FETCH', 'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_SYSTEM')}
    env['PYTHONPATH'] = str(overlay / 'src') + os.pathsep + str(overlay)
    command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()),
               '--inspect-overlay', str(overlay), '--dependency-site', str(dependency_site),
               '--out', str(out / 'census.json')]
    save(out / 'command.json', {'argv': command, 'environment': env,
                               'deadline': 'enclosing C4 runner, at most 3600 s'})
    # The enclosing runner owns the deadline and descendant cleanup. An inner
    # timeout must not orphan the census child when a quiet lock pauses it.
    completed = subprocess.run(command, cwd=overlay, env=env, capture_output=True)
    (out / 'stdout.log').write_bytes(completed.stdout)
    (out / 'stderr.log').write_bytes(completed.stderr)
    unchanged = package_files(ROOT) == original
    save(out / 'source-stability.json', {'unchanged': unchanged})
    if completed.returncode or not unchanged:
        raise RuntimeError('census failed or source changed; retained logs identify the failure')
    result = json.loads((out / 'census.json').read_bytes())
    return result


def inspect_overlay(overlay, dependency_site, output):
    network = require_network_denial()
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise RuntimeError('census child requires -S -P -B')
    sys.path.append(str(dependency_site))  # Path only; no .pth processing.
    from data_sheets_schema import native_execution_authority_v2 as authority
    if authority.ROOT != overlay:
        raise RuntimeError('A guard did not resolve its own scratch source root')
    inventory = package_files(overlay)
    pins = {name: sha(raw) for name, raw in inventory.items()}
    outcomes = {}
    for short in (*C_CONSUMERS, *D_CONSUMERS, *D_SUPPORT):
        name = 'data_sheets_schema.' + short
        stem = 'src/' + name.replace('.', '/')
        candidates = [p for p in (stem + '.py', stem + '/__init__.py') if p in inventory]
        if len(candidates) != 1:
            raise RuntimeError('census target has missing or ambiguous source: ' + name)
        raw = inventory[candidates[0]]
        try:
            graph = authority.refuse_legacy_consumer_imports(raw, name=name, package_sources=pins)
        except ValueError as exc:
            outcomes[short] = {'status': 'refused', 'reason': str(exc)}
        else:
            outcomes[short] = {'status': 'accepted', 'graph': graph}
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == 'data_sheets_schema' or name.startswith('data_sheets_schema.'):
            path = getattr(module, '__file__', None)
            if path is not None:
                resolved = Path(path).resolve()
                if not resolved.is_relative_to(overlay / 'src/data_sheets_schema'):
                    raise RuntimeError('foreign project module: ' + name)
                origins[name] = str(resolved)
            for item in getattr(module, '__path__', ()):
                if not Path(item).resolve().is_relative_to(overlay / 'src/data_sheets_schema'):
                    raise RuntimeError('foreign project package namespace: ' + name)
    if any('data_sheets_schema.' + name in sys.modules for name in D_CONSUMERS):
        raise RuntimeError('census unexpectedly executed a D consumer')
    result = {'network': network, 'A_guard_path': str(Path(authority.__file__).resolve()),
              'A_guard_sha256': sha(Path(authority.__file__).read_bytes()),
              'rosters': {'C': list(C_CONSUMERS), 'D': list(D_CONSUMERS), 'D_support': list(D_SUPPORT)},
              'A_closed_owned_roster': sorted(authority.CONSUMER_OWNED_MODULES),
              'origins': origins, 'outcomes': outcomes, 'old_D8_refusals': OLD_REFUSALS,
              'old_refusal_comparison': {name: {'old_reason': old,
                  'current': outcomes[name], 'old_reason_still_present': outcomes[name].get('reason') == old}
                  for name, old in OLD_REFUSALS.items()},
              'remaining_refusals': {name: row for name, row in outcomes.items() if row['status'] == 'refused'},
              'limits': ['No admission or runtime reconstruction executed.',
                         'No projection lifetime or D classifier handoff acceptance follows from import acceptance.',
                         'This composite is not a merged commit or a complete D integration validation.']}
    save(output, result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect-overlay', type=Path, required=True)
    parser.add_argument('--dependency-site', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    inspect_overlay(args.inspect_overlay, args.dependency_site, args.out)
