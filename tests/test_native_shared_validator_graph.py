"""PR6302: source-pinned callback validator closure, 2026-11-22.

Exercise the actual graph reader and verified wire module without constructing
an execution fixture or launching a native process. Mutations are temporary
software controls; no saved native evidence is changed.
"""
from contextlib import contextmanager
import json
from types import ModuleType

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_callback_orchestration as callbacks
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401


CAPTURE = 'data_sheets_schema.native_shared_capture'
WIRE = 'data_sheets_schema.native_wire_2_1_325'
CONTRACT = 'data_sheets_schema.native_shared_contract'
WIRE_PATH = 'src/data_sheets_schema/native_wire_2_1_325.py'


def current_sources():
    return authority.dependency_identity()['base']['package_sources']


def source(name, pins):
    relative = 'src/' + name.replace('.', '/') + '.py'
    return authority._verified_source_bytes(authority.ROOT / relative, pins[relative])


def test_actual_capture_validator_graph_is_closed_and_source_pinned(isolated_modules, record_property):
    pins = current_sources()
    reached = authority.refuse_legacy_consumer_imports(
        source(CAPTURE, pins), name=CAPTURE, package_sources=pins)
    assert WIRE in reached
    assert set(reached) <= callbacks.VALIDATOR_MODULES
    assert reached[WIRE] == pins[WIRE_PATH]
    wire_graph = authority.refuse_legacy_consumer_imports(
        source(WIRE, pins), name=WIRE, package_sources=pins)
    assert set(wire_graph) == {WIRE, CONTRACT}
    record_property('callback_validator_graph', json.dumps(reached, sort_keys=True))


def test_capture_graph_refuses_missing_or_changed_wire_source_pin(isolated_modules):
    pins = current_sources()
    raw = source(CAPTURE, pins)
    missing = dict(pins)
    missing.pop(WIRE_PATH)
    with pytest.raises(ValueError, match='missing or ambiguous source'):
        authority.refuse_legacy_consumer_imports(raw, name=CAPTURE, package_sources=missing)
    changed = {**pins, WIRE_PATH: '0' * 64}
    with pytest.raises(ValueError, match='source bytes differ from their pin'):
        authority.refuse_legacy_consumer_imports(raw, name=CAPTURE, package_sources=changed)


def verified_wire(pins):
    with authority.loaded_verified_package_module(WIRE, package_sources=pins) as module:
        identities = tuple((item, tuple(sorted(authority.module_source_identity(item).items())))
                           for item in (module, module.c))
        source_pins = tuple((str(authority.ROOT / relative), pins[relative]) for relative in (
            WIRE_PATH, 'src/data_sheets_schema/native_shared_contract.py'))
        check = callbacks._SourceCheck(source_pins, identities)
        check()
        yield module, check
        check()


verified_wire = contextmanager(verified_wire)


def test_verified_wire_semantic_mutations_disable_prefix_reuse_stickily(isolated_modules, monkeypatch):
    with verified_wire(current_sources()) as (module, check):
        constants = ('VERSION', 'INIT_VERSION', 'EXECUTABLE_SHA256', 'STATUS_BASIS',
                     'FAILURE_STATUS_BASIS', 'WRITE_SUCCESS_SUFFIX', '_DERIVATION_RULE')
        for name in constants:
            guard = callbacks._ValidatorGuard((module,), check, b'fixed software admission')
            assert guard.reusable()
            with monkeypatch.context() as patch:
                patch.setattr(module, name, getattr(module, name) + ' changed')
                assert not guard.reusable(), name
            assert not guard.reusable(), name
        for change in ('alias', 'function', 'code', 'defaults'):
            guard = callbacks._ValidatorGuard((module,), check, b'fixed software admission')
            assert guard.reusable()
            with monkeypatch.context() as patch:
                if change == 'alias':
                    patch.setattr(module, 'c', ModuleType(CONTRACT))
                elif change == 'function':
                    patch.setattr(module, 'profile', lambda runtime: True)
                elif change == 'code':
                    patch.setattr(module.profile, '__code__', (lambda runtime: True).__code__)
                else:
                    patch.setattr(module.denied_tool_result, '__kwdefaults__',
                                  {'basis': 'foreign', 'permission_denied': None})
                assert not guard.reusable(), change
            assert not guard.reusable(), change


def test_verified_wire_cannot_expand_the_closed_binding_graph(isolated_modules, monkeypatch):
    with verified_wire(current_sources()) as (module, check):
        for name in ('data_sheets_schema.unreviewed_validator',
                     'data_sheets_schema.native_shared_permissions',
                     'src.data_sheets_schema.native_wire_2_1_325'):
            with monkeypatch.context() as patch:
                patch.setattr(module, 'foreign_dependency', ModuleType(name), raising=False)
                with pytest.raises(ValueError, match='outside its closed graph'):
                    callbacks._ValidatorGuard((module,), check, b'fixed software admission')
