"""Read-only installed-payload evidence for H3 refinements, 2026-11-13.

Inputs: current interpreter import roots and installed distribution bytes.
Outputs: canary or checked-prefix inventory JSON in an explicit offline cohort.
Relocated out of normal CI collection after its recorded diagnostic runs.

The first test checks one real distribution. The second records either a full
primary dependency-root manifest or explicit partial counts and a hold. It does
not repair the primary environment or execute any installed package payload.
"""
import hashlib
import json
from pathlib import Path
import sys

import pytest

from data_sheets_schema import native_environment_manifest as manifest


def pin(path):
    raw = Path(path).read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, value, *, canonical=False):
    raw = manifest.c.canonical(value) if canonical else (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw
    return pin(path)


def totals(rows):
    return {'distributions': len(rows),
        'files_verified': sum(row['verified_files']['count'] for row in rows),
        'bytes_verified': sum(row['verified_files']['bytes'] for row in rows),
        'files_unverified_by_kind': {
            kind: sum(group['count'] for row in rows for group in row['unverified_files'] if group['kind'] == kind)
            for kind in sorted(manifest.UNVERIFIED_KINDS)}}


def test_one_real_installed_distribution_canary(tmp_path):
    chosen = [distribution for distribution in manifest.metadata.distributions(path=manifest._import_paths())
              if manifest._name(distribution.metadata['Name']) == 'attrs']
    assert len(chosen) == 1, 'single real-distribution canary requires one attrs installation'
    captured = manifest._capture_distribution(chosen[0])
    manifest._require_stable_payloads([captured])
    assert captured['row']['name'] == 'attrs' and captured['row']['verified_files']['count'] > 0
    assert captured['own_project'] is False
    save(tmp_path / 'installed-distribution-canary.json', {
        'status': 'one_distribution_payloads_verified', 'distribution': captured['row'],
        'totals': totals([captured['row']]), 'record': pin(captured['record_path']),
        'manifest_source': pin(manifest.__file__), 'interpreter': manifest._interpreter_identity(),
        'scope': 'One real installed distribution read as data in the isolated offline test process; no whole-environment or primary-startup claim.'})


def test_primary_dependency_root_payload_inventory(tmp_path, monkeypatch):
    # Keep source/stdlib/borrowed primary dependency roots, but remove the
    # harness-only site containing its SYNTHETIC bootstrap metadata, and the
    # helper directory pytest inserts when explicitly collecting this adhoc
    # diagnostic. Neither is a primary dependency root. No files or primary
    # configuration are changed; this is a read-only census.
    prefix = Path(sys.prefix).resolve(strict=True)
    helper = Path(__file__).resolve().parent
    actual_paths = manifest._import_paths()
    selected = [path for path in actual_paths if not Path(path).is_relative_to(prefix) and Path(path) != helper]
    assert selected and selected != actual_paths
    monkeypatch.setattr(manifest.sys, 'path', selected)
    captured = {}
    capture = manifest._capture_distribution
    def observe(distribution, **kwargs):
        result = capture(distribution, **kwargs)
        if not result['own_project']:
            captured[result['record_path']] = result['row']
        return result
    monkeypatch.setattr(manifest, '_capture_distribution', observe)
    value = error = None
    try:
        value = manifest.generate()
    except ValueError as exc:
        error = {'type': type(exc).__name__, 'reason': str(exc)}
    rows = sorted(captured.values(), key=lambda row: row['name']) if value is None else value['distributions']
    report = {'status': 'held_partial_inventory' if value is None else 'complete_manifest_verified',
        'complete': value is not None, 'hold': error, 'totals': totals(rows),
        'distributions_checked_before_hold' if value is None else 'distributions': rows,
        'import_roots': selected, 'omitted_test_bootstrap_roots': sorted(set(actual_paths) - set(selected)),
        'omitted_root_reasons': {path: 'pytest diagnostic helper import root' if Path(path) == helper
                                else 'isolated SYNTHETIC bootstrap prefix'
                                for path in sorted(set(actual_paths) - set(selected))},
        'interpreter': manifest._interpreter_identity(), 'executing_python': sys.executable,
        'executing_prefix': sys.prefix, 'manifest_source': pin(manifest.__file__),
        'scope': 'Primary dependency-root bytes read from an isolated offline process, with SYNTHETIC harness metadata excluded. No primary startup, environment modification, registration, probe or native execution.'}
    if value is not None:
        report['manifest'] = save(tmp_path / 'primary-dependency-environment-manifest.json', value, canonical=True)
        report['unowned_files'] = value['unowned_files']
        report['excluded_roots'] = value['excluded_roots']
        report['unowned_totals'] = {'count': len(value['unowned_files']),
                                   'bytes': sum(row['bytes'] for row in value['unowned_files'])}
    saved = save(tmp_path / 'primary-dependency-payload-inventory.json', report)
    if error is not None:
        pytest.fail('primary dependency census held; saved partial evidence: ' + saved['path'] + '; ' + error['reason'])
