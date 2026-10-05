"""Fixed engine boundary and old facade fault-seam preservation; no child calls."""
from dataclasses import replace
from types import ModuleType, SimpleNamespace
import sys

import pytest

from data_sheets_schema import native_execution as old
from data_sheets_schema import native_execution_engine as engine
from data_sheets_schema import native_execution_authority as authority


def test_old_facade_keeps_current_effect_functions(monkeypatch):
    sentinel = OSError('same original exception through public seam')
    seen = []
    def verify(raw):
        seen.append(raw)
        raise sentinel
    monkeypatch.setattr(old.registration, 'verified', verify)
    with pytest.raises(OSError) as caught:
        old.launch(b'exact registration', review_path='r', ci_path='c', launch_word_path='w')
    assert caught.value is sentinel
    assert seen == [b'exact registration']
    for name, effect in (('_file', 'file'), ('durable_new', 'durable_new'),
            ('_sync_directory', 'sync_directory'), ('_mkdir_durable', 'mkdir_durable'),
            ('_signals', 'signals'), ('_now', 'now'), ('_probe_runtime', 'probe_runtime'),
            ('expected_runtime_observation', 'expected_runtime_observation'),
            ('authorizations', 'authorizations'), ('_unchanged', 'unchanged')):
        unique = lambda *a, **k: None
        monkeypatch.setattr(old, name, unique)
        assert getattr(old._engine_bindings()[1], effect) is unique


def test_fixed_contract_cannot_select_foreign_semantic_module():
    contract, _ = old._engine_bindings()
    contract.require_fixed()
    for field in ('registration', 'composition', 'authority', 'gates', 'replay', 'shared'):
        with pytest.raises(ValueError, match='fixed package'):
            replace(contract, **{field: ModuleType('foreign_plugin')}).require_fixed()
    with pytest.raises(ValueError, match='fixed package'):
        replace(contract, kind='caller_chosen_kind').require_fixed()


def test_legacy_transport_receives_original_spec_without_new_phase_check():
    contract, _ = old._engine_bindings()
    exact = object()
    assert contract.transport_phase_spec(SimpleNamespace(spec=exact)) is exact


def test_new_transport_requires_truthful_axis_and_mandatory_policy_observer():
    contract, _ = old._engine_bindings()
    contract = replace(contract, kind='d4d_native_shared_attempt')
    checked=[]
    adapter=SimpleNamespace(spec=SimpleNamespace(render_version=26, native_shared_generation_version=1),
        policy={'registered': True}, classify=lambda:None, observe=lambda:None,
        require_phase_authority=lambda:checked.append(True))
    assert contract.transport_phase_spec(adapter) is None
    assert checked == [True]
    for name, value in (('render_version', 25), ('render_version', 26.0),
                        ('native_shared_generation_version', True), ('native_shared_generation_version', 0)):
        before=getattr(adapter.spec,name)
        setattr(adapter.spec,name,value)
        with pytest.raises(ValueError,match='selected policy and phase'):
            contract.transport_phase_spec(adapter)
        setattr(adapter.spec,name,before)
    adapter.policy={}
    with pytest.raises(ValueError,match='selected policy and phase'):
        contract.transport_phase_spec(adapter)


def test_engine_in_actual_source_closure_and_foreign_loaded_origin_refused(monkeypatch):
    identity=authority.dependency_identity()
    assert 'src/data_sheets_schema/native_execution_engine.py' in identity['base']['package_sources']
    foreign=ModuleType('data_sheets_schema.native_execution_engine')
    foreign.__file__='/outside-selected-package/native_execution_engine.py'
    monkeypatch.setitem(sys.modules, foreign.__name__, foreign)
    with pytest.raises(ValueError,match='another origin'):
        authority.dependency_identity()
