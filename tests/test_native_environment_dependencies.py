"""Pinned helper loading must not enlarge the importable environment."""
import importlib
import sys

import pytest

from data_sheets_schema import native_environment_manifest as manifest
from data_sheets_schema import native_execution_authority_v2 as authority
from tests.test_native_execution_registration_v2 import isolated_modules


def test_loaded_dependency_scope_preserves_manifest_and_pinned_imports(tmp_path, monkeypatch, isolated_modules):
    monkeypatch.chdir(authority.ROOT)
    before_path = list(sys.path)
    before_manifest = manifest.generate()
    dependencies = authority.dependency_identity()
    with authority.loaded_dependencies(dependencies):
        assert sys.path == before_path
        assert manifest.generate() == before_manifest
        # Force a fresh import after path restoration. The retained source-only
        # finder must resolve the declared helper without a notes directory on
        # sys.path, and attest the exact committed helper bytes.
        name = 'native_command_policy'
        sys.modules.pop(name)
        loaded = importlib.import_module(name)
        expected = dependencies['base']['modules'][name]
        assert authority.module_source_identity(loaded) == {
            'name': name, 'path': str(authority.ROOT / expected['path']),
            'sha256': expected['sha256']}
        assert manifest.generate() == before_manifest
        foreign = tmp_path / 'SYNTHETIC-unowned-import-root'
        foreign.mkdir()
        (foreign / 'SYNTHETIC_unowned.py').write_text('SYNTHETIC = True\n')
        sys.path.insert(0, str(foreign))
        with pytest.raises(ValueError, match='missing distribution RECORD ownership'):
            manifest.generate()
    assert sys.path == before_path
