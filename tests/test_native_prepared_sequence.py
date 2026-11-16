"""D156 process ownership tests using an ordinary sleeping Python child only."""
import os
import signal
import sys
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_launch_sequence as sequence


def test_prepared_failure_kills_group_and_reaps_leader(tmp_path):
    state = sequence._SequenceSignals()
    steps = []
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', steps, state)
    owned.step['argv'] = [sys.executable, '-I', '-c', 'import time; time.sleep(60)']
    try:
        owned.start()
        assert os.getpgid(owned.child.pid) == owned.child.pid
        assert owned.child.poll() is None
        raise ValueError('synthetic capture refusal')
    except ValueError:
        owned.close()
    assert owned.child.returncode == -signal.SIGKILL
    assert steps[0]['return_code'] == -signal.SIGKILL
    assert steps[0]['completed_at'] is not None
    with pytest.raises(ProcessLookupError):
        os.killpg(owned.child.pid, 0)
    assert owned.stdout.closed and owned.stderr.closed


def test_synthetic_capture_is_absent_until_preparation_callback(tmp_path, monkeypatch):
    from tests.test_native_subscription_capture import component
    from tests.utils.native_synthetic_evidence import authority_for
    args, value = component(tmp_path, monkeypatch)
    ci = tmp_path / 'ci.json'
    ci.write_bytes(b'{"synthetic":true}')
    issued = authority_for(args['registration_raw'], ci, tmp_path, defer_capture=True)
    assert not list(tmp_path.rglob('capture.json'))
    assert not list(tmp_path.rglob('invented-subscription.json'))
    assert not os.path.exists(value['attempt_directory'])
    pin = issued['prepare_capture'](None)
    assert len(list(tmp_path.rglob('capture.json'))) == 1
    saved = sequence.guard.read_regular(pin['guard_path'])
    assert sequence.guard.sha(saved) == pin['guard_sha256']
    assert not os.path.exists(value['attempt_directory'])


def test_controller_preparation_has_no_reservation_writes_and_closes_on_refusal(monkeypatch):
    from data_sheets_schema import native_shared_controller_orchestration as controller
    adapter = object.__new__(controller.CallbackAdapter)
    adapter._activated = False
    adapter.value = {'dependencies': {}}
    adapter.execution = {'synthetic': True}
    adapter.registration_raw = b'synthetic'
    adapter.spec = adapter.selection = object()
    events = []
    def controls(_):
        yield object()
    def preload(*args):
        events.append('prepared')
        try:
            yield SimpleNamespace(classifier=object(), state=object(), phase=object(), catalogs=object(),
                admission=SimpleNamespace(check_active=lambda: events.append('checked')),
                capture=SimpleNamespace(activate_admitted=lambda *args: events.append('reserved')))
        finally:
            events.append('closed')
    monkeypatch.setattr(controller.control_loading, 'loaded_controls', contextmanager(controls))
    monkeypatch.setattr(controller.registration, 'verified',
        lambda *args, **kwargs: adapter.execution)
    monkeypatch.setattr(controller.callback_loading, 'preloaded_callbacks', contextmanager(preload))
    monkeypatch.setattr(controller.render, 'commands', lambda spec: ())
    adapter.prepare_before_capture()
    assert events == ['prepared'] and not adapter._activated
    adapter.close_prepared()
    assert events == ['prepared', 'closed'] and not adapter._activated
    assert not hasattr(adapter, '_classifier_scope')


def test_spawn_failure_closes_reserved_streams(tmp_path, monkeypatch):
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', [], sequence._SequenceSignals())
    def refused(*args, **kwargs):
        raise OSError('synthetic spawn failure')
    monkeypatch.setattr(sequence.subprocess, 'Popen', refused)
    try:
        with pytest.raises(OSError, match='synthetic spawn failure'):
            owned.start()
    finally:
        owned.close()
    assert owned.child is None
    assert owned.stdout.closed and owned.stderr.closed


def test_exited_worker_is_not_reaped_before_failure_group_cleanup(tmp_path):
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', [], sequence._SequenceSignals())
    owned.step['argv'] = [sys.executable, '-I', '-c', 'raise SystemExit(7)']
    try:
        owned.start()
        deadline = time.monotonic() + 10
        while owned._exit_status() is None:
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert owned._exit_status() == 7
        assert owned.child.returncode is None
        # A second WNOWAIT observation succeeds: the PID is still owned.
        assert owned._exit_status() == 7
    finally:
        owned.close()
    assert owned.child.returncode == 7


def test_cleanup_attempts_reap_even_if_group_signal_fails(tmp_path, monkeypatch):
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', [], sequence._SequenceSignals())
    reaped = []
    owned.child = SimpleNamespace(pid=123, wait=lambda: reaped.append(True) or 9)
    owned._exit_status = lambda: None
    def refuse(*args):
        raise PermissionError('synthetic signal refusal')
    monkeypatch.setattr(sequence.os, 'killpg', refuse)
    with pytest.raises(PermissionError, match='synthetic signal refusal'):
        owned.close()
    assert reaped == [True] and owned.step['return_code'] == 9


def test_cleanup_never_signals_an_unverifiable_group_after_reaping(tmp_path, monkeypatch):
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', [], sequence._SequenceSignals())
    reaped, calls = [], []
    owned.child = SimpleNamespace(pid=123, wait=lambda: reaped.append(True) or 7)
    owned._exit_status = lambda: 7
    def signal_group(pid, signum):
        calls.append(signum)
        if signum:
            raise PermissionError('synthetic group refusal')
        assert reaped
    monkeypatch.setattr(sequence.os, 'killpg', signal_group)
    with pytest.raises(PermissionError, match='synthetic group refusal'):
        owned.close()
    assert calls == [signal.SIGKILL, 0]
    assert owned.step['return_code'] == 7


def prepared_scope_case(tmp_path, monkeypatch, *, production, through_selection=False):
    """Exercise launch ordering across a real replacement of the worker class."""
    import importlib.util
    from contextlib import ExitStack, nullcontext
    from data_sheets_schema import native_execution_orchestration as engine
    from data_sheets_schema import native_prepared_worker as ambient
    from data_sheets_schema import native_sequence_inputs
    from data_sheets_schema import native_runtime_profiles
    from data_sheets_schema import native_u4b_policy
    from data_sheets_schema import native_u4b_runtime
    from data_sheets_schema import native_subscription_admission as old_admission
    from data_sheets_schema import native_subscription_guard_v2 as old_guard
    import data_sheets_schema

    raw = b'exact prepared registration'
    value = {'runtime': {}, 'composition_raw_json': '{}'}
    authorization = {'raw': {name: b'authority' for name in ('review', 'ci', 'launch_word')},
        'inputs': {name: str(tmp_path / name) for name in ('review', 'ci', 'launch_word')}}
    spec = importlib.util.spec_from_file_location(ambient.__name__, ambient.__file__)
    scoped = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scoped)
    assert scoped.PreparedIdentity is not ambient.PreparedIdentity
    checks = []

    def initialize(self, submitted, checked, authorized):
        assert submitted == raw and checked == value and authorized == authorization
        self.registration_raw = submitted

    # Isolate heavy source verification; retain the real exact-class/byte gate.
    for module in (ambient, scoped):
        monkeypatch.setattr(module.PreparedIdentity, '__init__', initialize)
        monkeypatch.setattr(module.PreparedIdentity, 'recheck', lambda self: value)

    class ReachedPreparedConsumer(Exception):
        pass

    def unchanged(self, submitted_value, submitted_raw, submitted_authority):
        assert submitted_value == value and submitted_raw == raw
        assert submitted_authority == authorization
        checks.append('fresh-unchanged')
        raise ReachedPreparedConsumer()

    if through_selection:
        for module in (ambient, scoped):
            monkeypatch.setattr(module.PreparedIdentity, 'require_unchanged', unchanged)
        for name, path in authorization['inputs'].items():
            (tmp_path / name).write_bytes(authorization['raw'][name])
        (tmp_path / 'guard').write_bytes(b'guard')

    def consume(identity):
        assert identity.registration_raw == raw
        assert scoped.checked_value(identity, raw) == value
        with pytest.raises(ValueError, match='differs from capture authority'):
            scoped.checked_value(identity, b'foreign registration')
        checks.append('production' if production else 'synthetic')
        if through_selection:
            return {'guard_path': str(tmp_path / 'guard'), 'guard_sha256': 'a' * 64}
        raise ReachedPreparedConsumer()

    def exchange(directory, *, identity, **kwargs):
        return consume(identity)

    monkeypatch.setattr(scoped, 'exchange', exchange)
    monkeypatch.setattr(ambient, 'exchange', exchange)

    def prepare():
        monkeypatch.setitem(sys.modules, ambient.__name__, scoped)
        monkeypatch.setattr(data_sheets_schema, 'native_prepared_worker', scoped)
        if through_selection:
            clones = []
            for old in (old_guard, old_admission):
                spec = importlib.util.spec_from_file_location(old.__name__, old.__file__)
                clone = importlib.util.module_from_spec(spec)
                monkeypatch.setitem(sys.modules, old.__name__, clone)
                monkeypatch.setattr(data_sheets_schema, old.__name__.split('.')[-1], clone)
                spec.loader.exec_module(clone)
                clones.append(clone)
            guard_module, admission_module = clones
            for module in (old_admission, admission_module):
                def load(*args, selected=module.v2, **kwargs):
                    guard = object.__new__(selected.SubscriptionGuard)
                    guard._raw, guard._clock = b'guard', selected._now
                    return guard
                monkeypatch.setattr(module, 'load_current', load)
                monkeypatch.setattr(module, 'preflight_current_selection', lambda *args, **kwargs: None)
            monkeypatch.setattr(admission_module, 'context', lambda *args, **kwargs: (guard_module, {}))
            monkeypatch.setattr(guard_module.SubscriptionGuard, '__init__',
                lambda self, *args, **kwargs: checks.append('joined'))
            monkeypatch.setattr(native_u4b_runtime, 'validate_prepared_runtime', lambda runtime: None)

    adapter = SimpleNamespace(prepare_before_capture=prepare, close_prepared=lambda: checks.append('closed'))
    registration = SimpleNamespace(verified=lambda submitted: value,
        execution_paths_v2=lambda *args, **kwargs: (tmp_path / 'attempt', tmp_path / 'evidence'))
    contract = SimpleNamespace(registration=registration,
        composition=SimpleNamespace(verified_composition=lambda raw: {}), authority=None,
        gates=None, replay=None, shared=None, kind='d4d_native_shared_attempt',
        make_controller=lambda *args: adapter, prewarm_controller=lambda adapter: None,
        transport_phase_spec=lambda adapter: None)
    effects = SimpleNamespace(**{name: None for name in ('file', 'durable_new', 'sync_directory',
        'mkdir_durable', 'signals', 'now', 'probe_runtime', 'sys', 'launch_guard')},
        expected_runtime_observation=lambda value: {}, authorizations=lambda *args, **kwargs: authorization,
        unchanged=lambda *args: None)
    controls = SimpleNamespace(require_complete=lambda: None, loaded_classifier=lambda: nullcontext(None))
    monkeypatch.setattr(engine, '_require_launch_profile', lambda *args: None)
    monkeypatch.setattr(native_sequence_inputs, 'check_authority', lambda *args: None)
    monkeypatch.setattr(native_runtime_profiles, 'require_synthetic', lambda *args: None)
    monkeypatch.setattr(native_u4b_policy, 'registered_policy', lambda runtime: {'max_age_seconds': 1200})
    monkeypatch.setattr(engine.admission, 'admit', lambda *args, **kwargs:
        SimpleNamespace(registration_raw=raw, evidence=tuple(SimpleNamespace(
            pin=SimpleNamespace(path=authorization['inputs'][name]), raw=authorization['raw'][name])
            for name in ('review', 'ci', 'launch_word'))))
    with pytest.raises(ReachedPreparedConsumer), ExitStack() as cleanup:
        engine._launch_prepared(raw, review_path=authorization['inputs']['review'],
            ci_path=authorization['inputs']['ci'], launch_word_path=authorization['inputs']['launch_word'],
            contract=contract, effects=effects, controls=controls, expected_profile='synthetic',
            expected_authority_sha256=None, prepared_directory=tmp_path if production else None,
            prepare_capture=None if production else consume, preparation_cleanup=cleanup)
    assert checks == ['production' if production else 'synthetic',
        *(['joined', 'fresh-unchanged'] if through_selection else []), 'closed']


def test_synthetic_identity_belongs_to_prepared_callback_scope(tmp_path, monkeypatch):
    prepared_scope_case(tmp_path, monkeypatch, production=False)


def test_production_exchange_belongs_to_prepared_callback_scope(tmp_path, monkeypatch):
    prepared_scope_case(tmp_path, monkeypatch, production=True)


def test_synthetic_guard_and_unchanged_check_use_prepared_scope(tmp_path, monkeypatch):
    prepared_scope_case(tmp_path, monkeypatch, production=False, through_selection=True)


def test_production_guard_and_unchanged_check_use_prepared_scope(tmp_path, monkeypatch):
    prepared_scope_case(tmp_path, monkeypatch, production=True, through_selection=True)
