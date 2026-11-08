"""U3-D R8-5: real source-loader capabilities and reservation ordering.

These tests use pinned local source only.  They never dispatch a child/native
executable, call a provider, or grant admission to a registration.
"""
from contextlib import contextmanager
import queue
import sys
import threading
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
    original = capabilities.authority.loaded_dependencies

    @contextmanager
    def missing_capability(expected):
        with original(expected) as classifier:
            module = sys.modules[name]
            value = vars(module).pop(member)
            try:
                yield classifier
            finally:
                setattr(module, member, value)

    monkeypatch.setattr(capabilities.authority, 'loaded_dependencies', missing_capability)
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


def test_classifier_scope_restores_transport_identity(dependencies):
    with capabilities.loaded_capabilities(dependencies) as controls:
        transport = sys.modules['run_native_canary']
        budget_stop = controls['run_native_canary'].BudgetStop
        with controls.loaded_classifier() as projection:
            # C's exact loader-minted projection is alive only for pure calls.
            assert projection['budgeted_cborg'].BudgetStop is not budget_stop
        assert sys.modules['run_native_canary'] is transport
        assert controls['run_native_canary'].BudgetStop is budget_stop
        controls.require_complete()


def test_pure_gate_members_preserve_pinned_results(dependencies, tmp_path):
    control_log = tmp_path / 'control.jsonl'
    control_log.write_bytes(b'{"kind":"decision","request":{"request":{"input":{"effort":"high"}}}}\n')
    terminal = {'modelUsage': {'synthetic': {'inputTokens': 4, 'outputTokens': 3,
        'cacheReadInputTokens': 0, 'cacheCreationInputTokens': 0}}}
    registration = {'model': {'model': 'synthetic', 'auxiliary_models_permitted': []}}
    observation = {'malformed_message_events': 2, 'usage_from_terminal_result': True}
    with capabilities.loaded_capabilities(dependencies) as controls:
        pure = controls.gate_members
        direct, native = sys.modules['run_direct_canary'], sys.modules['run_native_canary']
        assert pure['model_accounting'](terminal, registration) == direct.model_accounting(terminal, registration)
        assert pure['observed_efforts'](control_log) == direct.observed_efforts(control_log) == ['high']
        assert pure['observation_problems'](observation) == native.observation_problems(observation)


def test_c_source_loader_worker_thread_blocker_is_reproduced(dependencies):
    """Diagnostic retained finding, not an admission/acceptance success.

    NativeControl._start_work runs the real C classifier body on its actual
    worker.  The minimal state bypasses construction only to isolate the thread
    boundary: no execution registration, permission or launch is fabricated.
    C currently enters A's main-thread-only loader there and must be repaired
    by its owner before the native runtime can satisfy the live gate.
    """
    from data_sheets_schema.native_shared_controller_orchestration import CallbackAdapter
    adapter = object.__new__(CallbackAdapter)
    adapter.failure = None
    adapter.policy = {'python': sys.executable}
    adapter.value = {'dependencies': dependencies}
    with authority.loaded_dependencies(dependencies):
        historical = sys.modules['native_control']
        worker = object.__new__(historical.NativeControl)
        worker._stopped = threading.Event()
        worker._publication_lock = threading.Lock()
        worker._active_work = None
        worker._work_replies = queue.Queue(maxsize=1)
        worker._start_work('classifier', None,
            lambda: adapter.classify('pwd', sys.executable, set(), adapter.policy))
        worker._work_thread.join(timeout=5)
        assert not worker._work_thread.is_alive()
        _, result = worker._work_replies.get_nowait()
        assert isinstance(result, ValueError)
        assert str(result) == 'native source loading requires the main thread'


def test_c_refusal_is_translated_without_losing_transport_budget_identity():
    class CStop(Exception):
        pass
    class TransportStop(Exception):
        pass
    class Adapter:
        _budget_stop = CStop
        def classify(self, *args):
            raise CStop('unchanged selected refusal')
    with pytest.raises(TransportStop, match='unchanged selected refusal') as caught:
        engine._guarded_classifier(Adapter(), TransportStop)('command')
    assert isinstance(caught.value.__cause__, CStop)
