#!/usr/bin/env python3
"""Inspect the current integrated C/D import graphs; U3-F2, 2026-11-09.

Inputs: this checkout's unchanged package bytes and genuine A dependency pins.
Outputs: fresh manifest, graph census and source-stability JSON below pytest's
tmp_path. No source overlay, consumer execution or launcher metadata is used.
The historical filename is retained for provenance; the D8-overlay test and
entry point are retired. Static graph acceptance is not execution admission.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
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
HISTORICAL_D8_HEAD = '3ab9fbc189f647d0abf00a50ab4c35634fe5228e'
OLD_BOOTSTRAP = ('consumer cannot import verifier bootstrap boundary: '
                 'data_sheets_schema.native_execution_registration_v2')
OLD_REFUSALS = {name: OLD_BOOTSTRAP for name in (
    'native_gate_engine', 'native_shared_execution', 'native_shared_gates',
    'native_shared_publication', 'native_shared_registration', 'native_shared_results')}
OLD_REFUSALS['native_shared_permissions'] = (
    'consumer package import has missing or ambiguous source: '
    'data_sheets_schema.native_shared_permission_protocol')
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_PACKAGE_BYTES = 256 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def package_files(root):
    """Retain the full package source set; never construct a filtered pin map."""
    result = {}
    total = 0
    package = root / 'src/data_sheets_schema'
    for path in sorted(package.rglob('*')):
        if path.is_symlink():
            raise RuntimeError('census package contains a symbolic link: ' + str(path))
        if path.suffix not in ('.py', '.yaml', '.json'):
            continue
        if not path.is_file() or path != path.resolve(strict=True):
            raise RuntimeError('package inventory requires regular physical source files: ' + str(path))
        with path.open('rb') as stream:
            raw = stream.read(MAX_SOURCE_BYTES + 1)
        if len(raw) > MAX_SOURCE_BYTES:
            raise RuntimeError('individual census source exceeds 64 MiB')
        total += len(raw)
        if total > MAX_PACKAGE_BYTES:
            raise RuntimeError('census package exceeds 256 MiB')
        result[path.relative_to(root).as_posix()] = raw
    if not result:
        raise RuntimeError('empty census package')
    return result


def _project_origins():
    """Record loaded project modules without importing any census consumers."""
    origins = {}
    package = ROOT / 'src/data_sheets_schema'
    for name, module in tuple(sys.modules.items()):
        if name != 'data_sheets_schema' and not name.startswith('data_sheets_schema.'):
            continue
        source = getattr(module, '__file__', None)
        if source is not None:
            resolved = Path(source).resolve()
            if not resolved.is_relative_to(package):
                raise RuntimeError('foreign project module: ' + name)
            origins[name] = str(resolved)
        for item in getattr(module, '__path__', ()):
            if not Path(item).resolve().is_relative_to(package):
                raise RuntimeError('foreign project package namespace: ' + name)
    return origins


def inspect_current(out):
    """Run A's actual graph guard against the current complete package closure.

    A's dependency capture performs local Git reads. This helper creates no
    subprocess, socket, package copy, loader substitution or source overlay.
    Already-imported consumers are recorded; the census may not import more.
    """
    from data_sheets_schema import native_execution_authority_v2 as authority

    if authority.ROOT.resolve() != ROOT:
        raise RuntimeError('A guard resolved a different source root')
    out = Path(out).absolute()
    if out != out.resolve() or out.is_relative_to(ROOT):
        raise ValueError('census output must be a fresh physical path outside the worktree')
    out.mkdir(parents=False, exist_ok=False)
    original = package_files(ROOT)
    helper_raw = Path(__file__).read_bytes()
    origins_before = _project_origins()
    identity = authority.dependency_identity()
    pins = identity['base']['package_sources']
    if pins != {name: sha(raw) for name, raw in original.items()}:
        raise RuntimeError('A dependency pins do not cover the exact current source inventory')
    names = (*C_CONSUMERS, *D_CONSUMERS, *D_SUPPORT)
    owned = {'data_sheets_schema.' + name for name in names}
    if len(names) != 28 or len(owned) != 28 or owned != authority.CONSUMER_OWNED_MODULES:
        raise RuntimeError('current C/D census roster differs from the closed A roster')
    imported_before = {name: sys.modules[name] for name in owned if name in sys.modules}
    save(out / 'manifest.json', {
        'kind': 'current_integrated_consumer_graph_census', 'version': 1,
        'root': str(ROOT), 'source_commit': identity['base']['source_commit'],
        'source_commit_basis': 'observed local HEAD; graph census is not a committed-source admission proof',
        'helper_sha256': sha(helper_raw), 'dependency_identity': identity,
        'files': {name: {'sha256': sha(raw), 'bytes': len(raw)}
                  for name, raw in original.items()},
        'source_overlay': False,
        'historical_overlay_retired': {
            'D8_head': HISTORICAL_D8_HEAD,
            'test_node': 'test_actual_c_and_overlay_d_graphs_are_accepted',
            'reason': 'D8 bytes predate the current integrated consumers and neutral dependencies',
        },
    })
    outcomes = {}
    for short in names:
        name = 'data_sheets_schema.' + short
        stem = 'src/' + name.replace('.', '/')
        candidates = [path for path in (stem + '.py', stem + '/__init__.py') if path in original]
        if len(candidates) != 1:
            raise RuntimeError('census target has missing or ambiguous source: ' + name)
        try:
            graph = authority.refuse_legacy_consumer_imports(
                original[candidates[0]], name=name, package_sources=pins)
        except ValueError as exc:
            outcomes[short] = {'status': 'refused', 'reason': str(exc)}
        else:
            outcomes[short] = {'status': 'accepted', 'graph': graph}
    origins_after = _project_origins()
    imported_after = {name: sys.modules[name] for name in owned if name in sys.modules}
    source_unchanged = package_files(ROOT) == original
    helper_unchanged = Path(__file__).read_bytes() == helper_raw
    consumers_unchanged = (imported_before.keys() == imported_after.keys()
        and all(imported_after[name] is module for name, module in imported_before.items()))
    stability = {'package_sources_unchanged': source_unchanged,
                 'helper_source_unchanged': helper_unchanged,
                 'consumer_modules_unchanged': consumers_unchanged}
    save(out / 'source-stability.json', stability)
    result = {
        'kind': 'current_integrated_consumer_graph_census', 'version': 1,
        'A_guard_path': str(Path(authority.__file__).resolve()),
        'A_guard_sha256': sha(original['src/data_sheets_schema/native_execution_authority_v2.py']),
        'rosters': {'C': list(C_CONSUMERS), 'D': list(D_CONSUMERS), 'D_support': list(D_SUPPORT)},
        'A_closed_owned_roster': sorted(authority.CONSUMER_OWNED_MODULES),
        'origins_before': origins_before, 'origins_after': origins_after,
        'previously_loaded_consumers': sorted(imported_before),
        'outcomes': outcomes, 'historical_D8_refusals': OLD_REFUSALS,
        'remaining_refusals': {name: row for name, row in outcomes.items() if row['status'] == 'refused'},
        'source_stability': stability, 'source_overlay': False,
        'limits': [
            'Static graph acceptance only; no admission or runtime reconstruction executed.',
            'No projection lifetime or classifier handoff acceptance follows from import acceptance.',
            'No child or native executable was launched by this helper; A captures local Git identity.',
            'Historical D8 refusal metadata is provenance only; no D8 source is loaded or overlaid.',
        ],
    }
    save(out / 'census.json', result)
    if not all(stability.values()):
        raise RuntimeError('census changed source or loaded consumers; retained witness identifies the failure')
    return result
