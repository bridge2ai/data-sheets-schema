"""U3-K ordering/refusal regressions; no native launch acceptance.

The saved-capture components use their existing ordinary-Python fixture. Engine
ordering tests explicitly isolate source/CI/controller prerequisites and stop at
the existing first-reservation sentinel. No provider or native executable runs.
"""
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_subscription_admission as subscription
from data_sheets_schema import native_subscription_guard_v2 as guard
from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema import native_execution_orchestration as engine
from data_sheets_schema import native_shared_execution_orchestration as native
from data_sheets_schema import native_shared_controller_orchestration as controller
from tests.test_native_u4b_admission import prepared
from tests.test_native_u4b_a3_captures import newer
from tests.test_native_u4b_a3_reservation import reservation_case, FirstReservationObserved
from tests.test_native_subscription_capture import read_arguments, word_directory


def selection_case(tmp_path, monkeypatch):
    args, value, paths, raw = prepared(tmp_path, monkeypatch)
    selection = subscription.select_current(paths['guard'], guard.sha(raw),
        registration_raw=args['registration_raw'], runtime=value['runtime'],
        launch_word_path=paths['word'], review_path=paths['review'])
    authorization = {'inputs': {'review': str(paths['review']), 'launch_word': str(paths['word'])},
        'raw': {'review': args['review_bundle_raw'], 'launch_word': args['launch_word_raw']}}
    kwargs = {'registration_raw': args['registration_raw'], 'runtime': value['runtime'],
              'authorization': authorization}
    return args, value, paths, raw, selection, kwargs


def test_selection_is_data_only_and_late_acceptance_keeps_original_timestamp(tmp_path, monkeypatch):
    args, value, paths, raw, selection, kwargs = selection_case(tmp_path, monkeypatch)
    assert type(selection) is subscription.CurrentSelection
    with pytest.raises(FrozenInstanceError):
        selection.expected_sha256 = '0' * 64
    assert subscription.inspect_current_selection(selection, **kwargs) is None
    accepted = subscription.accept_current_selection(selection, **kwargs)
    assert type(accepted) is guard.SubscriptionGuard
    assert accepted._clock is guard._now
    assert accepted.raw == raw
    assert accepted.value['captured_at'] == guard.strict_json(raw)['captured_at']
    assert not accepted.dispatched
    assert not Path(value['attempt_directory']).exists()


def test_static_inspection_does_not_make_expired_capture_fresh(tmp_path, monkeypatch):
    args, value, paths, raw, selection, kwargs = selection_case(tmp_path, monkeypatch)
    subscription.inspect_current_selection(selection, **kwargs)
    captured = guard._timestamp(guard.strict_json(raw)['captured_at'], 'captured_at')
    monkeypatch.setattr(guard, '_now', lambda: captured + 301)
    with pytest.raises(ValueError, match='stale or future-dated'):
        subscription.accept_current_selection(selection, **kwargs)
    assert not Path(value['attempt_directory']).exists()


@pytest.mark.parametrize('changed', ['guard', 'word', 'review', 'capture'])
def test_late_acceptance_rechecks_changed_saved_bytes(tmp_path, monkeypatch, changed):
    args, value, paths, raw, selection, kwargs = selection_case(tmp_path, monkeypatch)
    subscription.inspect_current_selection(selection, **kwargs)
    if changed == 'capture':
        path = word_directory(args) / 'capture-1' / 'capture.json'
        document = guard.strict_json(path.read_bytes())
        document['lifecycle']['spawn_count'] = 0
        path.write_bytes(guard.canonical(document))
    else:
        path = paths[changed]
        path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError):
        subscription.accept_current_selection(selection, **kwargs)
    assert not Path(value['attempt_directory']).exists()


def test_late_acceptance_rechecks_newer_current_word(tmp_path, monkeypatch):
    args, value, paths, raw, selection, kwargs = selection_case(tmp_path, monkeypatch)
    subscription.inspect_current_selection(selection, **kwargs)
    renewed = newer(args)
    capture.activate_capture_word(**read_arguments(renewed))
    with pytest.raises(ValueError, match='superseded'):
        subscription.accept_current_selection(selection, **kwargs)
    assert not Path(value['attempt_directory']).exists()


def test_frontdoor_defers_capture_without_loading_a_guard(tmp_path, monkeypatch):
    args, value, paths, raw = prepared(tmp_path, monkeypatch)
    calls = []
    def forbidden(*args, **kwargs):
        pytest.fail('front door accepted a capture before engine preflight')
    def isolated_engine(registration_raw, **kwargs):
        # Boundary forwarding only; this stub grants no engine admission.
        selected = kwargs['effects'].launch_guard
        assert type(selected) is subscription.CurrentSelection
        assert selected.registration_raw == registration_raw == args['registration_raw']
        assert selected.expected_sha256 == guard.sha(raw)
        calls.append(selected)
        return 'unaccepted-selection-observed'
    monkeypatch.setattr(subscription, 'load_current', forbidden)
    monkeypatch.setattr(engine, 'launch', isolated_engine)
    result = native.launch(args['registration_raw'], review_path=paths['review'],
        launch_word_path=paths['word'], ci_path=tmp_path/'unread-ci.json',
        subscription_guard_path=paths['guard'], subscription_guard_sha256=guard.sha(raw))
    assert result == 'unaccepted-selection-observed' and len(calls) == 1
    assert not Path(value['attempt_directory']).exists()


@pytest.mark.parametrize('refuse', [False, True])
def test_callback_prewarm_closes_scope_without_activation(monkeypatch, refuse):
    adapter = object.__new__(controller.CallbackAdapter)
    adapter._activated = False
    adapter.value = {'dependencies': {}}
    adapter.execution = {'scope': 'isolated prewarm lifecycle only'}
    adapter.registration_raw = b'isolated'
    adapter.spec, adapter.selection = object(), object()
    events = []
    @contextmanager
    def controls(_):
        yield object()
    @contextmanager
    def preload(*args):
        events.append('enter')
        def check():
            events.append('check')
            if refuse:
                raise ValueError('isolated warmup refusal')
        try:
            yield SimpleNamespace(admission=SimpleNamespace(check_active=check))
        finally:
            events.append('exit')
    monkeypatch.setattr(controller.control_loading, 'loaded_controls', controls)
    monkeypatch.setattr(controller.registration, 'verified',
        lambda raw, *, classifier_projection: adapter.execution)
    monkeypatch.setattr(controller.render, 'commands', lambda spec: ('isolated',))
    monkeypatch.setattr(controller.callback_loading, 'preloaded_callbacks', preload)
    if refuse:
        with pytest.raises(ValueError, match='isolated warmup refusal'):
            adapter.prewarm_before_acceptance()
    else:
        assert adapter.prewarm_before_acceptance() is None
    assert events == ['enter', 'check', 'exit']
    assert adapter._activated is False
    assert '_callbacks' not in adapter.__dict__
    assert '_classifier_scope' not in adapter.__dict__


@pytest.mark.parametrize('remaining,allows_mkdir', [(89, False), (90, True)])
def test_cold_controller_work_precedes_original_margin_and_real_reservation(
        tmp_path, monkeypatch, remaining, allows_mkdir):
    invoke, args, value, watched, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=remaining)
    class IsolatedController:
        def prewarm_before_acceptance(self):
            assert not active[0]
            assert not Path(value['attempt_directory']).exists()
            trace.append('controller-prewarm-closed')
    def construct(self, checked, raw):
        assert checked == value and raw == args['registration_raw']
        trace.append('controller-construct')
        return IsolatedController()
    monkeypatch.setattr(engine.ExecutionContract, 'make_controller', construct)
    expected = FirstReservationObserved if allows_mkdir else ValueError
    with pytest.raises(expected):
        invoke()
    assert trace.index('controller-construct') < trace.index('controller-prewarm-closed')
    assert trace.index('controller-prewarm-closed') < trace.index('lease-enter')
    assert trace.index('lease-held') < trace.index('in-lease-source-check') < trace.index('margin-enter')
    assert Path(value['attempt_directory']).exists() is allows_mkdir
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]
