"""Checkpoint-scoped resolution regressions for issue 6241; synthetic only."""
import hashlib
from pathlib import Path
import sys
from types import ModuleType

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority


def test_exit_rejects_physical_source_swap(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    package = root / 'src/data_sheets_schema'
    package.mkdir(parents=True)
    source = b'VALUE = 1\n'
    target = package / 'checkpoint_fixture.py'
    target.write_bytes(source)
    outside = root / 'outside.py'
    outside.write_bytes(source)
    pins = {'src/data_sheets_schema/checkpoint_fixture.py': hashlib.sha256(source).hexdigest()}
    monkeypatch.setattr(authority, 'ROOT', root)
    with pytest.raises(ValueError, match='captured source identity'):
        with authority.loaded_verified_package_module(
                'data_sheets_schema.checkpoint_fixture', package_sources=pins) as module:
            assert module.VALUE == 1
            assert authority._package_name(module.__file__) == module.__name__
            target.rename(package / 'original.py')
            target.symlink_to(outside)


def test_scan_reuses_root_only_within_one_segment(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    package = root / 'src/data_sheets_schema'
    package.mkdir(parents=True)
    monkeypatch.setattr(authority, 'ROOT', root)
    modules = {}
    for name in ('first', 'second'):
        module = ModuleType(name)
        module.__file__ = str(package / (name + '.py'))
        modules[name] = module
    original = Path.resolve
    calls = []

    def resolve(path, *args, **kwargs):
        calls.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'resolve', resolve)
    monkeypatch.setattr(sys, 'modules', modules)
    assert set(authority._ambient_package_bindings()) == set(modules)
    assert calls == [package, package / 'first.py', package / 'second.py']
    calls.clear()
    assert set(authority._ambient_package_bindings()) == set(modules)
    assert calls == [package, package / 'first.py', package / 'second.py']


def test_source_changed_between_loader_passes_refuses(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    package = root / 'src/data_sheets_schema'
    package.mkdir(parents=True)
    target = package / 'checkpoint_fixture.py'
    source = b'VALUE = 1\n'
    target.write_bytes(source)
    pins = {'src/data_sheets_schema/checkpoint_fixture.py': hashlib.sha256(source).hexdigest()}
    monkeypatch.setattr(authority, 'ROOT', root)
    with authority.loaded_verified_package_module(
            'data_sheets_schema.checkpoint_fixture', package_sources=pins) as module:
        assert module.VALUE == 1
    target.write_bytes(b'VALUE = 2\n')
    with pytest.raises(ValueError, match='source bytes differ from their pin'):
        with authority.loaded_verified_package_module(
                'data_sheets_schema.checkpoint_fixture', package_sources=pins):
            pytest.fail('changed source executed')
