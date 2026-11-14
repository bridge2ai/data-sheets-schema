"""Proof under the proposed manifest identity; the live scanner pin stays held."""
import hashlib

import pytest

from tests.test_native_u1_scanner_contracts import ROOT, RUNNER, _native_route_root, scan


@pytest.fixture
def proposed_manifest_pin(monkeypatch):
    relative = 'src/data_sheets_schema/native_environment_manifest.py'
    digest = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    assert scan._NATIVE_V3_RENDER_SOURCES[relative] != digest
    monkeypatch.setitem(scan._NATIVE_V3_RENDER_SOURCES, relative, digest)


def test_unrotated_scanner_pin_still_refuses_new_manifest_implementation():
    with pytest.raises(scan.ConfigError):
        scan.derive_native_shared_route(ROOT, scan._tree(ROOT / RUNNER))


def test_proposed_identity_proves_explicit_mode_route(proposed_manifest_pin):
    assert scan.derive_native_shared_route(ROOT, scan._tree(ROOT / RUNNER))


@pytest.mark.parametrize('replacement', ["mode='light'", "mode='full'", 'other_mode=None', ''])
def test_proposed_identity_refuses_changed_mode_forwarding(tmp_path, proposed_manifest_pin, replacement):
    root = _native_route_root(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    path = root / 'src/data_sheets_schema/native_execution_registration_v2.py'
    text = path.read_text()
    original = 'mode=native_environment_manifest.preparation_mode()'
    assert original in text
    path.write_text(text.replace(', ' + original, ', ' + replacement if replacement else '', 1))
    with pytest.raises(scan.ConfigError):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
