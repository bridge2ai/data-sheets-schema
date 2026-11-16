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


def test_moved_head_between_passes_refuses(monkeypatch):
    neutral = authority.neutral
    heads = iter(('1' * 40, '2' * 40))
    commands = []

    def git_head(command, **kwargs):
        commands.append(command)
        assert command == ['git', 'rev-parse', 'HEAD']
        return next(heads)

    monkeypatch.setattr(neutral.composition, 'controller_sources', lambda: {'modules': {}})
    monkeypatch.setattr(neutral, 'ADDITIONAL', {})
    monkeypatch.setattr(authority, 'ADDITIONAL', {})
    monkeypatch.setattr(neutral.draft, '_code_pins', lambda: {})
    monkeypatch.setattr(neutral.subprocess, 'check_output', git_head)
    # Keep source-origin enumeration independent of the test runner's imports.
    monkeypatch.setattr(sys, 'modules', {})
    identity = authority.dependency_identity()
    with pytest.raises(ValueError, match='dependency identity changed'):
        authority.require_committed(identity)
    assert len(commands) == 2


def test_one_loader_pass_keeps_read_and_exit_observations(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    package = root / 'src/data_sheets_schema'
    package.mkdir(parents=True)
    target = package / 'checkpoint_fixture.py'
    source = b'VALUE = 1\n'
    target.write_bytes(source)
    pins = {'src/data_sheets_schema/checkpoint_fixture.py': hashlib.sha256(source).hexdigest()}
    monkeypatch.setattr(authority, 'ROOT', root)
    original_resolve, original_lstat = Path.resolve, Path.lstat
    resolved, observed = [], []

    def resolve(path, *args, **kwargs):
        resolved.append(path)
        return original_resolve(path, *args, **kwargs)

    def lstat(path, *args, **kwargs):
        observed.append(path)
        return original_lstat(path, *args, **kwargs)

    def unexpected_git(*args, **kwargs):
        pytest.fail('a source-loader pass should not introduce Git calls')

    monkeypatch.setattr(Path, 'resolve', resolve)
    monkeypatch.setattr(Path, 'lstat', lstat)
    monkeypatch.setattr(authority.subprocess, 'Popen', unexpected_git)
    with authority.loaded_verified_package_module(
            'data_sheets_schema.checkpoint_fixture', package_sources=pins) as module:
        assert module.VALUE == 1
    assert observed.count(target) == 2
    assert resolved.count(target) == 2
    assert resolved.count(package) == 2
