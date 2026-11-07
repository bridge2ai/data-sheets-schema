"""U3-A v2 execution closure and loader refusals; no native/provider launch."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_attribution_controller_v2 as composition
from data_sheets_schema import native_execution_authority as v1
from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema.resources import git_env


@pytest.fixture
def isolated_modules():
    """Keep authority-version imports independent of earlier test modules."""
    manifest = json.loads((authority.ROOT / composition.SOURCES_PATH).read_bytes())
    names = set(manifest['modules']) | set(authority.neutral.ADDITIONAL) | set(authority.ADDITIONAL)
    absent = object()
    previous = {name: sys.modules.pop(name, absent) for name in names}
    old_path = list(sys.path)
    try:
        yield names
    finally:
        sys.path[:] = old_path
        for name, module in previous.items():
            if module is absent:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def test_committed_v2_closure_loads_exact_origins_and_preserves_v1(isolated_modules):
    old_globals = {name: getattr(v1, name) for name in ('draft', 'neutral', 'ADDITIONAL', 'ROOT')}
    old_pins = deepcopy(v1.ADDITIONAL)
    identity = authority.dependency_identity()
    assert identity['version'] == identity['base']['authority_version'] == 2
    assert set(identity) == {'version', 'base', 'additional_modules'}
    assert identity['base']['package_sources'] == authority.draft._code_pins()
    assert identity['base']['modules']['prepare_registration']['path'].endswith('prepare_registration_v2.py')
    assert identity['base']['modules']['prepare_direct']['path'].endswith('prepare_direct_v2.py')
    authority.require_committed(identity)
    old_path = list(sys.path)
    with authority.loaded_dependencies(identity) as modules:
        assert set(modules) == authority.EXPOSED_CONTROLS
        assert sys.modules['prepare_registration'] is modules['prepare_registration_v2']
        pins = {**identity['base']['modules'], **identity['additional_modules']}
        for name, pin in pins.items():
            loaded = sys.modules[name]
            assert Path(loaded.__file__).resolve() == (authority.ROOT / pin['path']).resolve()
            assert authority.module_source_identity(loaded)['sha256'] == pin['sha256']
        assert callable(modules['prepare_registration_v2'].require_envelope)
        assert callable(modules['run_direct_canary_awake'].KeepAwake)
    assert sys.path == old_path
    assert not isolated_modules.intersection(sys.modules)
    for name, value in old_globals.items():
        assert getattr(v1, name) is value
    assert v1.ADDITIONAL == old_pins


@pytest.mark.parametrize('field,value', [('version', 1), ('version', True), ('version', '2'),
                                         ('base', 1), ('base', True)])
def test_cross_version_authority_refuses_before_import(isolated_modules, monkeypatch, field, value):
    identity = authority.dependency_identity()
    if field == 'base':
        identity['base']['authority_version'] = value
    else:
        identity['version'] = value
    monkeypatch.setattr(authority.importlib, 'import_module',
                        lambda *args: pytest.fail('invalid authority must refuse before imports'))
    with pytest.raises(ValueError, match='version-2'):
        authority.require_committed(identity)
    with pytest.raises(ValueError, match='version-2'):
        with authority.loaded_dependencies(identity):
            pytest.fail('cross-version authority admitted')


def test_identity_does_not_expose_mutable_additional_pin_state(isolated_modules):
    identity = authority.dependency_identity()
    identity['additional_modules']['run_direct_canary_awake']['sha256'] = '0' * 64
    assert authority.ADDITIONAL == v1.ADDITIONAL
    assert authority.dependency_identity()['additional_modules'] == v1.ADDITIONAL


def test_additional_helper_tampering_refuses(isolated_modules, monkeypatch):
    helper = (authority.ROOT / authority.ADDITIONAL['run_direct_canary_awake']['path']).read_bytes()
    original = authority.draft._sha
    monkeypatch.setattr(authority.draft, '_sha', lambda raw: '0' * 64 if raw == helper else original(raw))
    with pytest.raises(ValueError, match='additional native execution dependency changed'):
        authority.dependency_identity()


@pytest.mark.parametrize('name', ['prepare_registration', 'prepare_registration_v2', 'prepare_direct',
                                'run_direct_canary_awake'])
def test_foreign_or_v1_module_origin_refuses_without_replacement(isolated_modules, monkeypatch, name):
    identity = authority.dependency_identity()
    foreign = SimpleNamespace(__file__=str(authority.ROOT / 'notes/foreign' / (name + '.py')))
    monkeypatch.setitem(sys.modules, name, foreign)
    old_path = list(sys.path)
    with pytest.raises(ValueError, match='another origin'):
        with authority.loaded_dependencies(identity):
            pytest.fail('foreign source admitted')
    assert sys.modules[name] is foreign
    assert sys.path == old_path


@pytest.mark.parametrize('failure_name', ['native_control', 'run_direct_canary_awake'])
def test_failed_import_restores_all_aliases_and_path(isolated_modules, monkeypatch, failure_name):
    identity = authority.dependency_identity()
    old_path = list(sys.path)
    original = authority.importlib.import_module

    def fail_selected(name, *args, **kwargs):
        if name == failure_name:
            # Simulate an importer that leaves its partially initialized module
            # behind, after the v2 preparer aliases have already been populated.
            sys.modules[name] = SimpleNamespace(__file__='/incomplete-import')
            sys.path.insert(0, '/incomplete-import')
            raise ImportError('synthetic import failure')
        return original(name, *args, **kwargs)

    monkeypatch.setattr(authority.importlib, 'import_module', fail_selected)
    with pytest.raises(ImportError, match='synthetic import failure'):
        with authority.loaded_dependencies(identity):
            pytest.fail('failed import yielded controls')
    assert sys.path == old_path
    assert not isolated_modules.intersection(sys.modules)


def test_existing_module_and_none_state_restored_on_body_failure(isolated_modules):
    identity = authority.dependency_identity()
    with authority.loaded_dependencies(identity) as outer:
        previous = {name: sys.modules[name] for name in isolated_modules}
        old_path = list(sys.path)
        with pytest.raises(RuntimeError, match='synthetic body failure'):
            with authority.loaded_dependencies(identity):
                sys.modules['run_direct_canary_awake'] = None
                sys.path.insert(0, '/synthetic-body')
                raise RuntimeError('synthetic body failure')
        assert sys.path == old_path
        assert all(sys.modules[name] is module for name, module in previous.items())
        assert sys.modules['run_direct_canary_awake'] is outer['run_direct_canary_awake']
    # An explicit import blocker is distinct from an absent module. Preserve it
    # even when the inherited loader fails before this layer imports its helper.
    sys.modules['run_direct_canary_awake'] = None
    old_path = list(sys.path)
    with pytest.raises(ModuleNotFoundError):
        with authority.loaded_dependencies(identity):
            pytest.fail('None import blocker was bypassed')
    assert 'run_direct_canary_awake' in sys.modules
    assert sys.modules['run_direct_canary_awake'] is None
    assert sys.path == old_path
    assert not (isolated_modules - {'run_direct_canary_awake'}).intersection(sys.modules)


def _git(root, *args):
    env = git_env()
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=root,
                          env=env, capture_output=True, check=True, timeout=30)


@pytest.fixture
def committed_fixture(tmp_path, monkeypatch):
    """Exercise actual local Git objects without modifying the implementation."""
    root = tmp_path / 'source-object-proof'
    root.mkdir()
    files = {
        'src/data_sheets_schema/module.py': b'# source\n',
        'src/data_sheets_schema/.retained.yaml': b'value: retained\n',
        'src/data_sheets_schema/a space.json': b'{}\n',
        'notes/preparer.py': b'# preparer\n',
        'notes/awake.py': b'# awake\n',
    }
    for relative, raw in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    _git(root, 'init', '-q')
    _git(root, 'add', '--', '.')
    _git(root, '-c', 'user.name=Software fixture', '-c', 'user.email=fixture@example.invalid',
         '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic source proof')
    pins = {path: hashlib.sha256(raw).hexdigest() for path, raw in files.items()}
    identity = {
        'version': 2,
        'base': {'authority_version': 2,
                 'source_commit': _git(root, 'rev-parse', 'HEAD').stdout.decode().strip(),
                 'package_sources': {path: sha for path, sha in pins.items() if path.startswith('src/')},
                 'modules': {'prepare': {'path': 'notes/preparer.py', 'sha256': pins['notes/preparer.py']}}},
        'additional_modules': {'awake': {'path': 'notes/awake.py', 'sha256': pins['notes/awake.py']}},
    }
    monkeypatch.setattr(authority, 'ROOT', root)
    monkeypatch.setattr(authority, 'dependency_identity', lambda: deepcopy(identity))
    authority.require_committed(identity)
    return root, identity


@pytest.mark.parametrize('change', ['omit', 'extra', 'changed_package', 'changed_preparer', 'changed_awake'])
def test_complete_committed_roster_and_blob_proof(committed_fixture, change):
    root, identity = committed_fixture
    if change == 'omit':
        identity['base']['package_sources'].pop('src/data_sheets_schema/.retained.yaml')
    elif change == 'extra':
        path = 'src/data_sheets_schema/unreviewed.py'
        (root / path).write_bytes(b'# not committed\n')
        identity['base']['package_sources'][path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    elif change == 'changed_package':
        identity['base']['package_sources']['src/data_sheets_schema/module.py'] = '0' * 64
    elif change == 'changed_preparer':
        identity['base']['modules']['prepare']['sha256'] = '0' * 64
    else:
        identity['additional_modules']['awake']['sha256'] = '0' * 64
    message = 'source roster differs' if change in ('omit', 'extra') else 'differs from the reviewed commit'
    with pytest.raises(ValueError, match=message):
        authority.require_committed(identity)


@pytest.mark.parametrize('change', ['separator', 'negative_size', 'tail', 'missing', 'truncated'])
def test_malformed_blob_proof_refuses(committed_fixture, monkeypatch, change):
    _, identity = committed_fixture
    original = authority.subprocess.run

    def malformed(command, **kwargs):
        result = original(command, **kwargs)
        if command[-2:] == ['cat-file', '--batch']:
            raw = result.stdout
            end = raw.index(b'\n')
            size = int(raw[:end].rsplit(b' ', 1)[1])
            if change == 'separator':
                raw = raw[:end + size + 1] + b'X' + raw[end + size + 2:]
            elif change == 'negative_size':
                raw = raw[:end].rsplit(b' ', 1)[0] + b' -1' + raw[end:]
            elif change == 'tail':
                raw += b'extra'
            elif change == 'missing':
                raw = b'not-a-source missing\n'
            else:
                raw = raw[:end + size]
            result.stdout = raw
        return result

    monkeypatch.setattr(authority.subprocess, 'run', malformed)
    with pytest.raises(ValueError):
        authority.require_committed(identity)


@pytest.mark.parametrize('mode,kind,path', [
    ('120000', 'blob', 'src/data_sheets_schema/link.py'),
    ('160000', 'commit', 'src/data_sheets_schema/submodule'),
    ('100644', 'blob', 'src/data_sheets_schema/../escape.py'),
    ('100644', 'blob', 'src/data_sheets_schema/a\nb.py'),
])
def test_package_roster_refuses_nonregular_or_ambiguous_sources(mode, kind, path):
    def entry(entry_mode, entry_kind, entry_path):
        return f'{entry_mode} {entry_kind} {"a" * 40}\t{entry_path}\0'.encode()
    raw = (entry('040000', 'tree', 'src') + entry('040000', 'tree', authority.PACKAGE)
           + entry(mode, kind, path))
    with pytest.raises(ValueError):
        authority._package_roster(raw)
