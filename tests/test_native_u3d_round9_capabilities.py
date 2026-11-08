"""U3-D R8-5: real source-loader capabilities and reservation ordering.

These tests use pinned local source only.  They never dispatch a child/native
executable, call a provider, or grant admission to a registration.
"""
from contextlib import contextmanager
import sys
from types import ModuleType

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_execution_capabilities as capabilities
from data_sheets_schema import native_execution_orchestration as engine
from data_sheets_schema import native_shared_execution_orchestration as execute
from data_sheets_schema import native_gate_engine as gates


@pytest.fixture
def dependencies():
    return authority.dependency_identity()


def test_actual_capabilities_are_closed_and_a_map_is_unchanged(dependencies):
    with authority.loaded_dependencies(dependencies) as public:
        assert set(public) == {'prepare_registration_v2', 'run_direct_canary_awake'}
    with capabilities.loaded_capabilities(dependencies) as controls:
        assert set(controls) == set(capabilities._MEMBERS)
        for name, members in capabilities._MEMBERS.items():
            projection = controls[name]
            assert not isinstance(projection, ModuleType)
            assert set(projection._values) == members
            for forbidden in {'main', 'auth_evidence', 'cborg_client'} - members:
                with pytest.raises(AttributeError):
                    getattr(projection, forbidden)
        pure = controls.gate_members
        assert set(pure) == {'model_accounting', 'LIMIT_KEYS', 'observed_efforts', 'observation_problems'}
        assert not any(isinstance(value, ModuleType) for value in pure.values())
        assert 'execute_child' not in pure
        assert pure['LIMIT_KEYS'] == tuple(sys.modules['run_direct_canary'].LIMIT_KEYS)
        assert controls['run_native_canary'].BudgetStop is controls['budgeted_cborg'].BudgetStop
        saved = controls
    with pytest.raises(ValueError, match='expired'):
        saved.require_complete()


@pytest.mark.parametrize('name, member', [
    ('run_direct_canary', 'NoProxy'), ('run_native_canary', 'execute_child'),
    ('native_readonly', '_paths'), ('native_command_policy', '_simple_command'),
    ('native_control', 'control_contract'),
])
def test_missing_real_capability_refuses_before_reservation_or_any_effect(
        dependencies, monkeypatch, tmp_path, name, member):
    original = capabilities.classifier_loading.loaded_controls

    @contextmanager
    def missing_capability(expected):
        with original(expected) as classifier:
            module = sys.modules[name]
            value = vars(module).pop(member)
            try:
                yield classifier
            finally:
                setattr(module, member, value)

    monkeypatch.setattr(capabilities.classifier_loading, 'loaded_controls', missing_capability)
    monkeypatch.setattr(execute.registration, 'verified', lambda raw: {'dependencies': dependencies})
    entered = []

    def effect_path(*args, **kwargs):
        entered.append('reservation-or-effect-path')
        (tmp_path / 'spent-attempt').mkdir()
        pytest.fail('a missing capability reached the reservation path')

    monkeypatch.setattr(engine, '_launch', effect_path)
    contract, effects = execute._engine_bindings()
    with pytest.raises(ValueError, match='capability|callable code changed'):
        engine.launch(b'no execution admission', review_path='unused', ci_path='unused',
            launch_word_path='unused', contract=contract, effects=effects)
    assert entered == []
    assert not (tmp_path / 'spent-attempt').exists()


def test_member_mutation_and_expired_functions_refuse(dependencies, monkeypatch):
    with capabilities.loaded_capabilities(dependencies) as controls:
        direct = sys.modules['run_direct_canary']
        pure = controls.gate_members
        original = direct.model_accounting
        monkeypatch.setattr(direct, 'model_accounting', lambda *a, **k: {})
        try:
            with pytest.raises(ValueError, match='callable code changed'):
                pure['model_accounting']({}, {})
        finally:
            monkeypatch.setattr(direct, 'model_accounting', original)
    with pytest.raises(ValueError, match='scope is closed'):
        pure['model_accounting']({}, {})


@pytest.mark.parametrize('carrier', [
    {'run_native_canary': object(), 'run_direct_canary': object()},
    {'model_accounting': lambda: None, 'LIMIT_KEYS': (), 'observed_efforts': lambda: None,
     'observation_problems': lambda: None, 'execute_child': lambda: None},
])
def test_gate_consumer_refuses_launcher_carriers_before_reading_prepared(carrier):
    with pytest.raises(ValueError, match='four pure helper members'):
        gates.check({}, {}, {}, carrier, kind='native_shared', exit_code=0, shutdown={},
            live={}, first_stop=None, runtime_authority={}, keep_awake={})


def test_gate_consumer_refuses_indirect_capability_carrier():
    pure = {'model_accounting': lambda: None, 'LIMIT_KEYS': ('max_tokens',),
            'observed_efforts': lambda: None, 'observation_problems': lambda: None}
    with pytest.raises(ValueError, match='orchestration capability carriers'):
        gates.check({'controls': object()}, {}, {}, pure, kind='native_shared', exit_code=0,
            shutdown={}, live={}, first_stop=None, runtime_authority={}, keep_awake={})
