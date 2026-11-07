"""U3-A round 2 verified-byte imports; synthetic modules, never native calls."""
from copy import deepcopy
import hashlib
import importlib.util
import importlib._bootstrap_external
from pathlib import Path
import sys
import threading
from types import ModuleType, SimpleNamespace

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority


def pin(raw):
    return hashlib.sha256(raw).hexdigest()


def _source_stat_sequence(monkeypatch, path, *, change=None):
    """Inject observation metadata only; read and hash the actual source file."""
    original = Path.lstat
    observed = original(path)
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns',
              'st_atime', 'st_atime_ns')
    before = {key: getattr(observed, key) for key in fields}
    after = {**before, 'st_atime': before['st_atime'] + 1,
             'st_atime_ns': before['st_atime_ns'] + 1_000_000_000}
    if change is not None:
        after[change] += 1
    observations = []
    def read_stat(value, *args, **kwargs):
        if value != path:
            return original(value, *args, **kwargs)
        observations.append(value)
        if len(observations) > 2:
            pytest.fail('unexpected source metadata observation')
        return SimpleNamespace(**(before if len(observations) == 1 else after))
    monkeypatch.setattr(Path, 'lstat', read_stat)
    return observations


def test_verified_source_read_allows_only_access_time_to_change(tmp_path, monkeypatch):
    raw = b'VALUE = "unchanged pinned source"\n'
    path = tmp_path / 'source.py'; path.write_bytes(raw)
    visits = _source_stat_sequence(monkeypatch, path)
    assert authority._verified_source_bytes(path, pin(raw)) == raw
    assert visits == [path, path]


@pytest.mark.parametrize('field', ['st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns'])
def test_verified_source_read_still_refuses_identity_or_mutation_metadata(tmp_path, monkeypatch, field):
    raw = b'VALUE = "same bytes do not excuse changed file identity"\n'
    path = tmp_path / 'source.py'; path.write_bytes(raw)
    visits = _source_stat_sequence(monkeypatch, path, change=field)
    with pytest.raises(ValueError, match='source bytes differ from their pin'):
        authority._verified_source_bytes(path, pin(raw))
    assert visits == [path, path]


def test_access_time_only_change_does_not_excuse_wrong_source_digest(tmp_path, monkeypatch):
    raw = b'VALUE = "source still requires its exact digest"\n'
    path = tmp_path / 'source.py'; path.write_bytes(raw)
    visits = _source_stat_sequence(monkeypatch, path)
    with pytest.raises(ValueError, match='source bytes differ from their pin'):
        authority._verified_source_bytes(path, '0' * 64)
    assert visits == [path, path]


def forged_cache(path):
    """The cache is timestamp-valid for the original source but different code."""
    info = path.stat()
    raw = path.read_bytes() + b'\nFORGED_CACHE_EXECUTED = True\n'
    code = compile(raw, str(path), 'exec', dont_inherit=True)
    cached = Path(importlib.util.cache_from_source(str(path)))
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(importlib._bootstrap_external._code_to_timestamp_pyc(
        code, int(info.st_mtime), info.st_size))
    return cached


def test_verified_source_module_ignores_timestamp_valid_bytecode(tmp_path):
    raw = b'def checked():\n    return "verified bytes"\n'
    path = tmp_path / 'consumer.py'; path.write_bytes(raw)
    cache = forged_cache(path)
    cache_before = cache.read_bytes()
    old_policy = sys.dont_write_bytecode
    old_finders = list(sys.meta_path)
    with authority.verified_source_module('_u3a_verified_fixture', path=path, raw=raw, sha256=pin(raw)) as module:
        assert module.checked() == 'verified bytes'
        assert not hasattr(module, 'FORGED_CACHE_EXECUTED')
        assert module.__cached__ is None and sys.dont_write_bytecode is True
        assert authority.module_source_identity(module) == {
            'name': '_u3a_verified_fixture', 'path': str(path), 'sha256': pin(raw)}
    assert '_u3a_verified_fixture' not in sys.modules
    assert sys.dont_write_bytecode is old_policy
    assert sys.meta_path == old_finders
    assert cache.read_bytes() == cache_before


def test_source_context_uses_captured_bytes_not_later_file_or_preloaded_module(tmp_path):
    raw = b'def checked():\n    return "captured"\n'
    path = tmp_path / 'consumer.py'; path.write_bytes(b'raise AssertionError("disk fallback")\n')
    name = '_u3a_replaced_fixture'
    prior = ModuleType(name); prior.__file__ = str(path)
    sys.modules[name] = prior
    try:
        with authority.verified_source_module(name, path=path, raw=raw, sha256=pin(raw)) as module:
            assert module is not prior and module.checked() == 'captured'
        assert sys.modules[name] is prior
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize('change', ['function', 'code', 'origin', 'loader'])
def test_source_identity_rejects_post_load_substitution(tmp_path, change):
    raw = b'def checked():\n    return 1\n'
    path = tmp_path / 'consumer.py'; path.write_bytes(raw)
    with pytest.raises(ValueError, match='identity or callable code changed'):
        with authority.verified_source_module('_u3a_changed_fixture', path=path, raw=raw, sha256=pin(raw)) as module:
            if change == 'function':
                module.checked = lambda: 2
            elif change == 'code':
                module.checked.__code__ = (lambda: 2).__code__
            elif change == 'origin':
                module.__file__ = str(path) + '.foreign'
            else:
                module.__loader__ = object()
            authority.module_source_identity(module)
    assert '_u3a_changed_fixture' not in sys.modules


def test_failed_source_context_restores_parent_binding_and_policy(tmp_path, monkeypatch):
    name = '_u3a_package.child'
    parent = ModuleType('_u3a_package'); parent.__path__ = []
    previous = object(); parent.child = previous
    monkeypatch.setitem(sys.modules, '_u3a_package', parent)
    raw = b'raise RuntimeError("source import refused")\n'
    path = tmp_path / 'child.py'; path.write_bytes(raw)
    old_policy, old_path = sys.dont_write_bytecode, list(sys.path)
    with pytest.raises(RuntimeError, match='source import refused'):
        with authority.verified_source_module(name, path=path, raw=raw, sha256=pin(raw)):
            pytest.fail('failing source yielded a module')
    assert name not in sys.modules and parent.child is previous
    assert sys.dont_write_bytecode is old_policy and sys.path == old_path


def test_source_pin_and_nonmain_thread_refuse_before_module_installation(tmp_path):
    raw = b'raise AssertionError("must not execute")\n'
    path = tmp_path / 'consumer.py'; path.write_bytes(raw)
    with pytest.raises(ValueError, match='source identity'):
        with authority.verified_source_module('_u3a_refused_fixture', path=path, raw=raw, sha256='0' * 64):
            pytest.fail('wrong bytes accepted')
    errors = []
    def child():
        try:
            with authority.verified_source_module('_u3a_refused_fixture', path=path, raw=raw, sha256=pin(raw)):
                errors.append('unexpected admission')
        except ValueError as error:
            errors.append(str(error))
    thread = threading.Thread(target=child); thread.start(); thread.join(timeout=5)
    assert not thread.is_alive() and errors == ['native source loading requires the main thread']
    assert '_u3a_refused_fixture' not in sys.modules


@pytest.fixture
def closure(tmp_path, monkeypatch):
    """Exact synthetic inherited roster; no U2 loader or source modification."""
    rows = {
        'prepare_registration': ('notes/preparation.py', b'def require_envelope(value):\n    return value\n'),
        'helper_dependency': ('notes/dependency.py', b'VALUE = "source"\n'),
        'run_direct_canary_awake': ('notes/awake.py', b'import helper_dependency\nVALUE = helper_dependency.VALUE\n'),
    }
    modules = {}
    for name, (relative, raw) in rows.items():
        path = tmp_path / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        modules[name] = {'path': relative, 'sha256': pin(raw)}
    modules['prepare_registration_v2'] = dict(modules['prepare_registration'])
    additional = {'run_direct_canary_awake': modules.pop('run_direct_canary_awake')}
    identity = {'version': 2, 'base': {'authority_version': 2, 'modules': modules, 'package_sources': {}},
                'additional_modules': additional}
    monkeypatch.setattr(authority, 'ROOT', tmp_path)
    monkeypatch.setattr(authority, 'ADDITIONAL', additional)
    monkeypatch.setattr(authority, 'dependency_identity', lambda: deepcopy(identity))
    def forbidden(*args, **kwargs):
        pytest.fail('U3-A delegated to an inherited path/bytecode loader')
    monkeypatch.setattr(authority.neutral, 'loaded_dependencies', forbidden)
    monkeypatch.setattr(authority.neutral.composition, 'load_controls', forbidden)
    names = set(modules) | set(additional)
    absent = object(); before = {name: sys.modules.pop(name, absent) for name in names}
    try:
        yield tmp_path, identity
    finally:
        for name, module in before.items():
            if module is absent:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def test_closed_loader_compiles_transitive_helpers_and_exposes_only_frozen_controls(closure):
    root, identity = closure
    caches = [forged_cache(root / relative) for relative in ('notes/preparation.py', 'notes/dependency.py', 'notes/awake.py')]
    before = {path: path.read_bytes() for path in caches}
    old_path, old_meta, old_policy = list(sys.path), list(sys.meta_path), sys.dont_write_bytecode
    with authority.loaded_dependencies(identity) as controls:
        assert set(controls) == {'prepare_registration_v2', 'run_direct_canary_awake'}
        assert controls['run_direct_canary_awake'].VALUE == 'source'
        assert controls['prepare_registration_v2'] is sys.modules['prepare_registration']
        for name in (*identity['base']['modules'], *identity['additional_modules']):
            assert not hasattr(sys.modules[name], 'FORGED_CACHE_EXECUTED')
            assert authority.module_source_identity(sys.modules[name])['sha256']
    assert sys.path == old_path and sys.meta_path == old_meta and sys.dont_write_bytecode is old_policy
    assert not (set(identity['base']['modules']) | set(identity['additional_modules'])).intersection(sys.modules)
    assert {path: path.read_bytes() for path in caches} == before


def graph_fixture(tmp_path, monkeypatch, sources):
    pins = {}
    for module, raw in sources.items():
        relative = 'src/' + module.replace('.', '/') + '.py'
        path = tmp_path / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        pins[relative] = pin(raw)
    monkeypatch.setattr(authority, 'ROOT', tmp_path)
    return pins


@pytest.mark.parametrize('source', [
    b'import data_sheets_schema.native_execution_authority as old\n',
    b'from . import native_execution_registration as old\n',
    b'from data_sheets_schema.native_supervisor_authority import dependency_identity as old\n',
    b'from .native_attempt_supervisor import run as old\n',
])
def test_consumer_graph_refuses_direct_and_relative_legacy_aliases(tmp_path, monkeypatch, source):
    name = 'data_sheets_schema.synthetic_consumer'
    pins = graph_fixture(tmp_path, monkeypatch, {name: source})
    with pytest.raises(ValueError, match='forbidden v1 execution authority'):
        authority.refuse_legacy_consumer_imports(source, name=name, package_sources=pins)


def test_consumer_graph_refuses_transitive_legacy_import_and_changed_dependency(tmp_path, monkeypatch):
    name = 'data_sheets_schema.synthetic_consumer'
    source = b'from . import synthetic_dependency\n'
    dependency = b'from .native_execution import launch as old\n'
    pins = graph_fixture(tmp_path, monkeypatch, {name: source, 'data_sheets_schema.synthetic_dependency': dependency})
    with pytest.raises(ValueError, match='forbidden v1 execution authority'):
        authority.refuse_legacy_consumer_imports(source, name=name, package_sources=pins)
    pins['src/data_sheets_schema/synthetic_dependency.py'] = '0' * 64
    with pytest.raises(ValueError, match='source bytes differ'):
        authority.refuse_legacy_consumer_imports(source, name=name, package_sources=pins)


@pytest.mark.parametrize('source', [
    b'import importlib as loader\nloader.import_module("foreign")\n',
    b'from importlib import import_module as load\nload("foreign")\n',
    b'__import__("foreign")\n', b'exec("import foreign")\n',
    b'getattr(__builtins__, "__import__")("foreign")\n',
])
def test_consumer_graph_refuses_dynamic_loading(tmp_path, monkeypatch, source):
    name = 'data_sheets_schema.synthetic_consumer'
    pins = graph_fixture(tmp_path, monkeypatch, {name: source})
    with pytest.raises(ValueError, match='dynamic loading or evaluation'):
        authority.refuse_legacy_consumer_imports(source, name=name, package_sources=pins)


def test_consumer_graph_accepts_explicit_pinned_helpers_and_stops_at_reviewed_v2_boundary(tmp_path, monkeypatch):
    name = 'data_sheets_schema.synthetic_consumer'
    source = b'import json\nfrom . import synthetic_dependency\nfrom .native_execution_registration_v2 import verified\n'
    dependency = b'def value():\n    return 1\n'
    pins = graph_fixture(tmp_path, monkeypatch, {name: source, 'data_sheets_schema.synthetic_dependency': dependency})
    result = authority.refuse_legacy_consumer_imports(source, name=name, package_sources=pins)
    assert result == {name: pin(source), 'data_sheets_schema.synthetic_dependency': pin(dependency)}


def test_consumer_graph_allows_ordinary_fixed_field_introspection(tmp_path, monkeypatch):
    name = 'data_sheets_schema.synthetic_consumer'
    source = b'from . import synthetic_dependency\n'
    dependency = (b'from dataclasses import dataclass\n'
        b'@dataclass\nclass Row:\n    value: int = 1\n'
        b'def read(row):\n    return getattr(row, "value"), vars(row)["value"]\n')
    pins = graph_fixture(tmp_path, monkeypatch, {name: source, 'data_sheets_schema.synthetic_dependency': dependency})
    assert authority.refuse_legacy_consumer_imports(source, name=name, package_sources=pins) == {
        name: pin(source), 'data_sheets_schema.synthetic_dependency': pin(dependency)}


def test_consumer_context_recompiles_cached_transitive_graph_and_restores_bindings(tmp_path, monkeypatch):
    import data_sheets_schema as package
    name, child = 'data_sheets_schema.synthetic_consumer', 'data_sheets_schema.synthetic_dependency'
    source = b'from . import synthetic_dependency\ndef read():\n    return synthetic_dependency.value()\n'
    dependency = b'def value():\n    return "pinned transitive source"\n'
    pins = graph_fixture(tmp_path, monkeypatch, {name: source, child: dependency})
    path = tmp_path / 'src/data_sheets_schema/synthetic_consumer.py'
    dep_path = path.with_name('synthetic_dependency.py')
    caches = [forged_cache(path), forged_cache(dep_path)]
    before = {cache: cache.read_bytes() for cache in caches}
    prior = ModuleType(child); prior.__file__ = str(dep_path); prior.value = lambda: 'cached foreign code'
    monkeypatch.setitem(sys.modules, child, prior)
    monkeypatch.setattr(package, 'synthetic_dependency', prior, raising=False)
    old_meta = list(sys.meta_path)
    with authority.verified_source_module(name, path=path, raw=source,
            sha256=pin(source), package_sources=pins) as module:
        assert module.read() == 'pinned transitive source'
        assert sys.modules[child] is not prior
        assert package.synthetic_dependency is sys.modules[child]
        assert not hasattr(module, 'FORGED_CACHE_EXECUTED')
        assert not hasattr(sys.modules[child], 'FORGED_CACHE_EXECUTED')
        assert authority.module_source_identity(sys.modules[child])['sha256'] == pin(dependency)
    assert name not in sys.modules and not hasattr(package, 'synthetic_consumer')
    assert sys.modules[child] is prior and package.synthetic_dependency is prior
    assert sys.meta_path == old_meta
    assert {cache: cache.read_bytes() for cache in caches} == before


def _nested_consumer_fixture(tmp_path, monkeypatch, request, initializer):
    """The parent is implicit: neither child nor consumer explicitly imports it."""
    import data_sheets_schema as package
    name = 'data_sheets_schema.synthetic_parent_consumer'
    parent_name = 'data_sheets_schema.synthetic_parent_package'
    child_name = parent_name + '.child'
    absent = object()
    previous = {key: sys.modules.get(key, absent) for key in (name, parent_name, child_name)}
    attributes = {key: vars(package).get(key, absent)
                  for key in ('synthetic_parent_consumer', 'synthetic_parent_package')}
    def restore_after_failed_regression():
        # The unfixed implementation can leak an implicit parent even when a
        # test fails. Keep the red demonstration isolated from later tests.
        for key, value in previous.items():
            if value is absent:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value
        for key, value in attributes.items():
            if value is absent:
                vars(package).pop(key, None)
            else:
                setattr(package, key, value)
    request.addfinalizer(restore_after_failed_regression)
    source = (b'from .synthetic_parent_package.child import value\n'
              b'def read():\n    return value()\n')
    child = b'def value():\n    return "pinned child"\n'
    pins = graph_fixture(tmp_path, monkeypatch, {name: source, child_name: child})
    root = tmp_path/'src/data_sheets_schema'
    init_path = root/'synthetic_parent_package/__init__.py'
    init_path.write_bytes(initializer)
    init_relative = str(init_path.relative_to(tmp_path))
    pins[init_relative] = pin(initializer)
    # Make ordinary import's fallback point at this synthetic fixture too.
    # Otherwise missing parent closure could merely produce ModuleNotFoundError
    # instead of exposing the exact cached-bytecode hole being exercised.
    monkeypatch.setattr(package, '__path__', [str(root)])
    for module_name in (name, parent_name, child_name):
        monkeypatch.delitem(sys.modules, module_name, raising=False)
    for attribute in ('synthetic_parent_consumer', 'synthetic_parent_package'):
        monkeypatch.delattr(package, attribute, raising=False)
    return {'name': name, 'parent': parent_name, 'child': child_name,
            'source': source, 'initializer': initializer, 'pins': pins,
            'path': root/'synthetic_parent_consumer.py', 'init_path': init_path,
            'init_relative': init_relative, 'package': package}


def test_implicit_parent_initializer_cannot_import_legacy_authority(tmp_path, monkeypatch, request):
    fixture = _nested_consumer_fixture(tmp_path, monkeypatch, request,
        b'from data_sheets_schema.native_execution_authority import dependency_identity\n')
    with pytest.raises(ValueError, match='forbidden v1 execution authority'):
        authority.refuse_legacy_consumer_imports(fixture['source'], name=fixture['name'],
                                                package_sources=fixture['pins'])
    assert not {fixture['name'], fixture['parent'], fixture['child']}.intersection(sys.modules)


@pytest.mark.parametrize('cached_parent', [False, True], ids=['forged-pyc', 'cached-parent-and-forged-pyc'])
def test_implicit_parent_is_source_compiled_and_all_bindings_restore(tmp_path, monkeypatch, request, cached_parent):
    fixture = _nested_consumer_fixture(tmp_path, monkeypatch, request, b'MARKER = "verified parent"\n')
    cache = forged_cache(fixture['init_path'])
    cache_before = cache.read_bytes()
    previous_parent = previous_child = None
    if cached_parent:
        previous_parent = ModuleType(fixture['parent'])
        previous_parent.__file__ = str(fixture['init_path'])
        previous_parent.__path__ = [str(fixture['init_path'].parent)]
        previous_parent.MARKER = 'cached foreign parent'
        previous_child = ModuleType(fixture['child'])
        previous_child.__file__ = str(fixture['init_path'].with_name('child.py'))
        previous_child.value = lambda: 'cached foreign child'
        previous_parent.child = previous_child
        monkeypatch.setitem(sys.modules, fixture['parent'], previous_parent)
        monkeypatch.setitem(sys.modules, fixture['child'], previous_child)
        monkeypatch.setattr(fixture['package'], 'synthetic_parent_package', previous_parent, raising=False)
    with authority.verified_source_module(fixture['name'], path=fixture['path'], raw=fixture['source'],
            sha256=pin(fixture['source']), package_sources=fixture['pins']) as module:
        assert module.read() == 'pinned child'
        parent = sys.modules[fixture['parent']]
        assert parent.MARKER == 'verified parent'
        assert parent is not previous_parent
        assert not hasattr(parent, 'FORGED_CACHE_EXECUTED')
        assert parent.__cached__ is None
        assert authority.module_source_identity(parent) == {
            'name': fixture['parent'], 'path': str(fixture['init_path']),
            'sha256': pin(fixture['initializer'])}
        assert fixture['package'].synthetic_parent_package is parent
        assert parent.child is sys.modules[fixture['child']]
    assert fixture['name'] not in sys.modules
    assert not hasattr(fixture['package'], 'synthetic_parent_consumer')
    if cached_parent:
        assert sys.modules[fixture['parent']] is previous_parent
        assert sys.modules[fixture['child']] is previous_child
        assert fixture['package'].synthetic_parent_package is previous_parent
        assert previous_parent.child is previous_child
    else:
        assert fixture['parent'] not in sys.modules and fixture['child'] not in sys.modules
        assert not hasattr(fixture['package'], 'synthetic_parent_package')
    assert cache.read_bytes() == cache_before


def test_implicit_parent_without_initializer_pin_refuses_before_import(tmp_path, monkeypatch, request):
    fixture = _nested_consumer_fixture(tmp_path, monkeypatch, request,
        b'raise AssertionError("an unpinned parent must never execute")\n')
    fixture['pins'].pop(fixture['init_relative'])
    with pytest.raises(ValueError, match='parent package initializer is not pinned'):
        with authority.verified_source_module(fixture['name'], path=fixture['path'], raw=fixture['source'],
                sha256=pin(fixture['source']), package_sources=fixture['pins']):
            pytest.fail('consumer with unpinned implicit parent was admitted')
    assert not {fixture['name'], fixture['parent'], fixture['child']}.intersection(sys.modules)


def test_implicit_parent_with_pinned_empty_initializer_is_verified(tmp_path, monkeypatch, request):
    fixture = _nested_consumer_fixture(tmp_path, monkeypatch, request, b'')
    graph = authority.refuse_legacy_consumer_imports(fixture['source'], name=fixture['name'],
                                                   package_sources=fixture['pins'])
    assert graph[fixture['parent']] == pin(b'')
    with authority.verified_source_module(fixture['name'], path=fixture['path'], raw=fixture['source'],
            sha256=pin(fixture['source']), package_sources=fixture['pins']) as module:
        assert module.read() == 'pinned child'
        parent = sys.modules[fixture['parent']]
        assert parent.__cached__ is None
        assert authority.module_source_identity(parent)['sha256'] == pin(b'')
    assert not {fixture['name'], fixture['parent'], fixture['child']}.intersection(sys.modules)
