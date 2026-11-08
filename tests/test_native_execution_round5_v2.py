"""U3-A Round 5 review regressions; synthetic carrier, offline, 2026-11-07."""
import importlib
from pathlib import Path
import sys

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from tests.test_native_execution_verified_loader_v2 import graph_fixture, pin, forged_cache

NAME = 'data_sheets_schema.native_shared_registration'
CARRIER = 'data_sheets_schema.synthetic_projection'
PROJECTION = (b'class Carrier: pass\n'
              b'def mint(): return Carrier()\n'
              b'def check(value):\n'
              b'    if type(value) is not Carrier: raise ValueError("foreign carrier")\n'
              b'    return True\n')
CONSUMER = (b'from . import synthetic_projection as projection\n'
            b'def check(value): return projection.check(value)\n')


def test_verified_carrier_identity_and_ordinary_copy_refusal(tmp_path, monkeypatch):
    import data_sheets_schema as package
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: CONSUMER, CARRIER: PROJECTION})
    monkeypatch.setattr(package, '__path__', [str(tmp_path / 'src/data_sheets_schema')])
    ordinary = importlib.import_module(CARRIER)
    try:
        ordinary_carrier = ordinary.mint()
        with authority.loaded_verified_package_module(CARRIER, package_sources=pins) as projection:
            assert projection is not ordinary
            carrier = projection.mint()
            with authority.loaded_verified_package_module(NAME, package_sources=pins) as consumer:
                assert consumer.projection is projection
                assert consumer.check(carrier)
                with pytest.raises(ValueError, match='foreign carrier'):
                    consumer.check(ordinary_carrier)
            assert sys.modules[CARRIER] is projection
        assert sys.modules[CARRIER] is ordinary
        assert not authority._VERIFIED_PACKAGE_MODULES
    finally:
        sys.modules.pop(CARRIER, None)
        vars(package).pop('synthetic_projection', None)


def test_verified_source_change_refuses_reuse(tmp_path, monkeypatch):
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: CONSUMER, CARRIER: PROJECTION})
    with authority.loaded_verified_package_module(CARRIER, package_sources=pins):
        (tmp_path / 'src/data_sheets_schema/synthetic_projection.py').write_bytes(PROJECTION + b'# changed\n')
        with pytest.raises(ValueError, match='source bytes differ'):
            with authority.loaded_verified_package_module(NAME, package_sources=pins):
                pytest.fail('changed source reused')


@pytest.mark.parametrize('target', ['native_execution_registration', 'native_attribution_registration',
                                  'native_execution', 'native_execution_registration_v2'])
@pytest.mark.parametrize('deferred', [False, True])
def test_review_src_alias_refused(target, deferred):
    pins = dict(authority.dependency_identity()['base']['package_sources'])
    statement = f'import src.data_sheets_schema.{target} as legacy\n'
    raw = ('def later():\n    ' + statement if deferred else statement).encode()
    relative = 'src/data_sheets_schema/native_shared_registration.py'
    pins[relative] = pin(raw)
    with pytest.raises(ValueError, match='forbidden v1|bootstrap boundary'):
        with authority.verified_source_module(NAME, path=authority.ROOT / relative,
                raw=raw, sha256=pin(raw), package_sources=pins):
            pytest.fail('alias bypass')


def test_runtime_alias_refusal_and_source_only_loading():
    pins = dict(authority.dependency_identity()['base']['package_sources'])
    raw = b'value = 1\n'
    relative = 'src/data_sheets_schema/native_shared_registration.py'
    pins[relative] = pin(raw)
    before = set(sys.modules)
    try:
        with authority.verified_source_module(NAME, path=authority.ROOT / relative,
                raw=raw, sha256=pin(raw), package_sources=pins):
            with pytest.raises(ValueError, match='forbidden v1'):
                importlib.import_module('src.data_sheets_schema.native_attribution_registration')
            loaded = importlib.import_module('src.data_sheets_schema.native_shared_contract')
            assert loaded.__cached__ is None
            assert authority.module_source_identity(loaded)['sha256'] == pins[
                'src/data_sheets_schema/native_shared_contract.py']
    finally:
        for key in set(sys.modules) - before:
            if key == 'src' or key.startswith('src.'):
                sys.modules.pop(key, None)


def test_forged_projection_cache_never_executes(tmp_path, monkeypatch):
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: CONSUMER, CARRIER: PROJECTION})
    path = tmp_path / 'src/data_sheets_schema/synthetic_projection.py'
    cache = forged_cache(path)
    before = cache.read_bytes()
    with authority.loaded_verified_package_module(CARRIER, package_sources=pins) as projection:
        with authority.loaded_verified_package_module(NAME, package_sources=pins) as consumer:
            assert consumer.check(projection.mint())
            assert not hasattr(projection, 'FORGED_CACHE_EXECUTED')
    assert cache.read_bytes() == before


@pytest.mark.parametrize('preloaded', [False, True])
def test_resolved_bare_alias_ignores_forged_cache(tmp_path, monkeypatch, preloaded):
    raw = b'import synthetic_projection as projection\n'
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: raw, CARRIER: PROJECTION})
    root = tmp_path / 'src/data_sheets_schema'
    monkeypatch.syspath_prepend(str(root))
    prior = importlib.import_module('synthetic_projection') if preloaded else None
    cache = forged_cache(root / 'synthetic_projection.py')
    before = cache.read_bytes()
    try:
        with authority.loaded_verified_package_module(NAME, package_sources=pins) as consumer:
            assert consumer.projection is not prior
            assert consumer.projection.__cached__ is None
            assert not hasattr(consumer.projection, 'FORGED_CACHE_EXECUTED')
            assert consumer.projection.check(consumer.projection.mint())
        assert sys.modules.get('synthetic_projection') is prior
        assert cache.read_bytes() == before
    finally:
        sys.modules.pop('synthetic_projection', None)


def test_runtime_dependency_enters_verified_set(tmp_path, monkeypatch):
    helper = 'data_sheets_schema.synthetic_deferred'
    raw = b'def later():\n    from . import synthetic_projection\n    return synthetic_projection\n'
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: CONSUMER, CARRIER: PROJECTION, helper: raw})
    with authority.loaded_verified_package_module(helper, package_sources=pins) as orchestration:
        projection = orchestration.later()
        with authority.loaded_verified_package_module(NAME, package_sources=pins) as consumer:
            assert consumer.projection is projection
            assert consumer.check(projection.mint())


def test_alias_reuses_verified_carrier_object(tmp_path, monkeypatch):
    raw = b'import synthetic_projection as projection\n'
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: raw, CARRIER: PROJECTION})
    monkeypatch.syspath_prepend(str(tmp_path / 'src/data_sheets_schema'))
    with authority.loaded_verified_package_module(CARRIER, package_sources=pins) as projection:
        original_spec = projection.__spec__
        with authority.loaded_verified_package_module(NAME, package_sources=pins) as consumer:
            assert consumer.projection is projection
            assert consumer.projection.check(projection.mint())
            assert projection.__spec__ is original_spec
        assert 'synthetic_projection' not in sys.modules


@pytest.mark.parametrize('target', ['native_execution', 'native_execution_registration_v2',
                                  'native_shared_contract'])
def test_from_src_namespace_gets_canonical_treatment(target):
    pins = dict(authority.dependency_identity()['base']['package_sources'])
    relative = 'src/data_sheets_schema/native_shared_registration.py'
    raw = f'from src.data_sheets_schema import {target} as imported\n'.encode()
    pins[relative] = pin(raw)
    context = authority.verified_source_module(NAME, path=authority.ROOT / relative,
                raw=raw, sha256=pin(raw), package_sources=pins)
    if target != 'native_shared_contract':
        with pytest.raises(ValueError, match='forbidden v1|bootstrap boundary'), context:
            pytest.fail('namespace alias bypass')
    else:
        with context as consumer:
            assert consumer.imported is sys.modules['data_sheets_schema.' + target]
            assert consumer.imported.__cached__ is None


@pytest.mark.parametrize('statement', [
    'import sys; value = sys.meta_path', 'import sys; value = sys.path_hooks',
    'import sys; value = sys.path_importer_cache', 'import os; value = os.sys.modules',
    'from sys import meta_path as paths; value = paths',
    'import pkgutil; pkgutil.resolve_name("foreign")',
    'import inspect; inspect.stack()', 'value = exc.__traceback__.tb_frame',
    'value = generator.gi_frame', 'value = frame.f_back',
])
def test_cheap_lint_gaps_refuse(tmp_path, monkeypatch, statement):
    raw = ('def later():\n    ' + statement + '\n').encode()
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: raw})
    with pytest.raises(ValueError, match='lint forbids|dynamic loading'):
        authority.refuse_legacy_consumer_imports(raw, name=NAME, package_sources=pins)


def test_actual_pinned_helper_ignores_scratch_forged_cache(tmp_path, monkeypatch, record_property):
    """The real pinned helper is only imported; no native command is invoked."""
    import importlib._bootstrap_external as bytecode
    declaration = authority.ADDITIONAL['run_direct_canary_awake']
    source = authority.ROOT / declaration['path']
    original = source.read_bytes()
    assert pin(original) == declaration['sha256']
    monkeypatch.setattr(sys, 'pycache_prefix', str(tmp_path / 'forged-cache'))
    cache = Path(importlib.util.cache_from_source(str(source)))
    assert cache.is_relative_to(tmp_path)
    cache.parent.mkdir(parents=True)
    forged = compile(original + b'\nFORGED_R5_CACHE_EXECUTED = True\n', str(source), 'exec')
    info = source.stat()
    raw = bytecode._code_to_timestamp_pyc(forged, int(info.st_mtime), info.st_size)
    cache.write_bytes(raw)
    identity = authority.dependency_identity()
    absent = object()
    names = set(identity['base']['modules']) | set(identity['additional_modules'])
    previous = {name: sys.modules.get(name, absent) for name in names}
    old_path, old_meta, old_policy = list(sys.path), list(sys.meta_path), sys.dont_write_bytecode
    with authority.loaded_dependencies(identity) as controls:
        assert set(controls) == {'prepare_registration_v2', 'run_direct_canary_awake'}
        loaded = controls['run_direct_canary_awake']
        assert not hasattr(loaded, 'FORGED_R5_CACHE_EXECUTED')
        assert loaded.__cached__ is None
        assert authority.module_source_identity(loaded)['sha256'] == declaration['sha256']
    assert all(sys.modules.get(name, absent) is prior for name, prior in previous.items())
    assert (sys.path, sys.meta_path, sys.dont_write_bytecode) == (old_path, old_meta, old_policy)
    assert source.read_bytes() == original and cache.read_bytes() == raw
    record_property('actual_helper_sha256', pin(original))
    record_property('forged_cache_sha256', pin(raw))
    record_property('executed_forged_bytecode', False)
