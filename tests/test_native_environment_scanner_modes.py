"""Authorized manifest identity and distinct v2/v3 scanner source closures."""
import hashlib
import subprocess

import pytest

from tests.test_native_u1_scanner_contracts import ROOT, RUNNER, _native_route_root, scan


MANIFEST = 'src/data_sheets_schema/native_environment_manifest.py'
AUTHORITY = 'src/data_sheets_schema/native_execution_authority_v2.py'
V2_CANDIDATE = 'f5c7c312f41e555c8023b880eeb3da327aa815cb'
HISTORICAL_MANIFEST = '13d4d45e0bd375608d3b8c4808af6ea51cb6489d1053e0415fa799e443f46e7c'


def test_historical_scanner_pin_refuses_current_manifest_implementation(monkeypatch):
    monkeypatch.setitem(scan._NATIVE_V3_RENDER_SOURCES, MANIFEST, HISTORICAL_MANIFEST)
    with pytest.raises(scan.ConfigError, match='authority source changed: ' + MANIFEST):
        scan.derive_native_shared_route(ROOT, scan._tree(ROOT / RUNNER))


def test_committed_identity_proves_explicit_mode_route():
    assert scan._NATIVE_V3_RENDER_SOURCES[MANIFEST] == hashlib.sha256((ROOT / MANIFEST).read_bytes()).hexdigest()
    assert scan.derive_native_shared_route(ROOT, scan._tree(ROOT / RUNNER))


@pytest.mark.parametrize('replacement', ["mode='light'", "mode='full'", 'other_mode=None', ''])
def test_committed_identity_refuses_changed_mode_forwarding(tmp_path, replacement):
    root = _native_route_root(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    path = root / 'src/data_sheets_schema/native_execution_registration_v2.py'
    text = path.read_text()
    original = 'mode=native_environment_manifest.preparation_mode()'
    assert original in text
    path.write_text(text.replace(', ' + original, ', ' + replacement if replacement else '', 1))
    with pytest.raises(scan.ConfigError):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def historical_v2_root(tmp_path):
    """Copy committed producer bytes as data; never import historical code."""
    root = _native_route_root(tmp_path)
    for relative in ('src/data_sheets_schema/cli/prompt.py',
                     'src/data_sheets_schema/native_execution_registration_v2.py', AUTHORITY):
        raw = subprocess.run(['git', '--no-replace-objects', '-C', str(ROOT),
                              'show', V2_CANDIDATE + ':' + relative],
                             capture_output=True, check=True, timeout=30).stdout
        (root / relative).write_bytes(raw)
    return root


def test_same_scanner_derives_historical_v2_and_current_v3(tmp_path):
    assert scan._NATIVE_V2_INTEGRATED_RENDER_SOURCES[AUTHORITY] != scan._NATIVE_V3_RENDER_SOURCES[AUTHORITY]
    root = historical_v2_root(tmp_path)
    assert hashlib.sha256((root / AUTHORITY).read_bytes()).hexdigest() == scan._NATIVE_V2_INTEGRATED_RENDER_SOURCES[AUTHORITY]
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['renderer'] == 26
    assert scan.derive_native_shared_route(ROOT, scan._tree(ROOT / RUNNER))['renderer'] == 26


@pytest.mark.parametrize('version', ('v2', 'v3'))
def test_authority_pin_cannot_cross_between_versioned_routes(tmp_path, monkeypatch, version):
    root = historical_v2_root(tmp_path) if version == 'v2' else _native_route_root(tmp_path)
    source = scan._NATIVE_V2_INTEGRATED_RENDER_SOURCES if version == 'v2' else scan._NATIVE_V3_RENDER_SOURCES
    other = scan._NATIVE_V3_RENDER_SOURCES if version == 'v2' else scan._NATIVE_V2_INTEGRATED_RENDER_SOURCES
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['renderer'] == 26
    monkeypatch.setitem(source, AUTHORITY, other[AUTHORITY])
    with pytest.raises(scan.ConfigError, match='authority source changed: ' + AUTHORITY):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
