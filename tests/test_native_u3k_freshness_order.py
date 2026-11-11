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


def prepared_frontdoor(root, monkeypatch, entry):
    root.mkdir(parents=True, exist_ok=True)
    if entry == 'launch':
        args, value, paths, raw = prepared(root, monkeypatch)
        return args, value, paths, raw, native.launch, 'launch'
    from copy import deepcopy
    from data_sheets_schema import native_shared_registration_orchestration as registration
    from tests.test_native_subscription_capture import component
    from tests.utils import native_synthetic_evidence as synthetic_fixture
    _, base_value = component(root, monkeypatch)
    runtime_path = root / 'base-runtime.json'
    runtime_path.write_bytes(guard.canonical(base_value['runtime']))
    value = deepcopy(base_value)
    value['runtime'] = synthetic_fixture.runtime_for(
        {'runtime_path': runtime_path}, root / 'synthetic-root')
    registration_raw = guard.canonical({
        'authority_version': 2, 'controller_sources_sha256': 'f' * 64,
        'registration': value})
    monkeypatch.setattr(registration, 'verified',
        lambda submitted: deepcopy(value) if submitted == registration_raw
        else (_ for _ in ()).throw(AssertionError('unexpected registration bytes')))
    monkeypatch.setattr(capture.subprocess, 'Popen',
        lambda *a, **k: pytest.fail('synthetic front-door fixture spawned a process'))
    ci = root / 'seed-ci.json'
    ci.write_bytes(b'{"synthetic_component_only":true}')
    issued = synthetic_fixture.authority_for(registration_raw, ci, root)
    paths = {'guard': issued['subscription_guard_path'],
             'word': issued['launch_word_path'],
             'review': issued['review_path']}
    raw = paths['guard'].read_bytes()
    basis = guard.strict_json(value['runtime']['limits_basis'].encode())
    args = {'registration_raw': registration_raw,
            'review_bundle_raw': paths['review'].read_bytes(),
            'launch_word_raw': paths['word'].read_bytes(),
            'directory': Path(basis['admission']['capture_state_directory'])}
    return args, value, paths, raw, native.synthetic_launch, 'synthetic_launch'


def _trap_frontdoor_reconstruction(monkeypatch, args, value, forbidden):
    from copy import deepcopy
    from data_sheets_schema import native_shared_registration_orchestration as registration
    verified_calls = []
    def single_frontdoor_verified(submitted):
        assert submitted == args['registration_raw']
        if verified_calls:
            pytest.fail('front-door preflight repeated registration.verified')
        verified_calls.append(submitted)
        return deepcopy(value)
    monkeypatch.setattr(registration, 'verified', single_frontdoor_verified)
    monkeypatch.setattr(subscription, 'load_current', forbidden)
    monkeypatch.setattr(subscription, 'context', forbidden)
    monkeypatch.setattr(capture, 'read_capture_for_event', forbidden)
    monkeypatch.setattr(capture, 'read_capture', forbidden)
    return verified_calls


def test_frontdoor_defers_capture_without_loading_a_guard(tmp_path, monkeypatch):
    for entry in ('launch', 'synthetic_launch'):
        case_dir = tmp_path / entry
        with monkeypatch.context() as patch:
            args, value, paths, raw, invoke, engine_name = prepared_frontdoor(
                case_dir, patch, entry)
            calls = []
            def forbidden(*args, **kwargs):
                pytest.fail('front door accepted or reconstructed a capture before engine preflight')
            def isolated_engine(registration_raw, **kwargs):
                # Boundary forwarding only; this stub grants no engine admission.
                selected = kwargs['effects'].launch_guard
                assert type(selected) is subscription.CurrentSelection
                assert selected.registration_raw == registration_raw == args['registration_raw']
                assert selected.expected_sha256 == guard.sha(raw)
                calls.append(selected)
                return 'unaccepted-selection-observed'
            verified_calls = _trap_frontdoor_reconstruction(patch, args, value, forbidden)
            patch.setattr(engine, engine_name, isolated_engine)
            result = invoke(args['registration_raw'], review_path=paths['review'],
                launch_word_path=paths['word'], ci_path=case_dir / 'unread-ci.json',
                subscription_guard_path=paths['guard'], subscription_guard_sha256=guard.sha(raw))
            assert result == 'unaccepted-selection-observed'
            assert len(calls) == 1 and len(verified_calls) == 1
            assert not Path(value['attempt_directory']).exists()


@pytest.mark.parametrize('entry', ['launch', 'synthetic_launch'])
@pytest.mark.parametrize('defect,match', [
    ('expired', 'stale or future-dated'),
    ('superseded', 'superseded'),
    ('guard_sha', 'subscription guard bytes differ from selected SHA256'),
])
def test_frontdoor_refuses_expired_or_spent_capture_before_engine_without_loading_guard(
        tmp_path, monkeypatch, entry, defect, match):
    args, value, paths, raw, invoke, _ = prepared_frontdoor(tmp_path, monkeypatch, entry)
    if defect == 'expired':
        captured = guard._timestamp(guard.strict_json(raw)['captured_at'], 'captured_at')
        monkeypatch.setattr(guard, '_now', lambda: captured + 301)
    elif defect == 'superseded':
        renewed = newer(args)
        capture.activate_capture_word(**read_arguments(renewed))
    else:
        paths['guard'].write_bytes(raw + b' ')
    def forbidden(*args, **kwargs):
        pytest.fail('invalid front-door capture reached reconstruction, load_current or engine')
    verified_calls = _trap_frontdoor_reconstruction(monkeypatch, args, value, forbidden)
    if defect == 'guard_sha':
        monkeypatch.setattr(subscription.review, 'validate_bundle', forbidden)
    monkeypatch.setattr(engine, 'launch', forbidden)
    monkeypatch.setattr(engine, 'synthetic_launch', forbidden)
    with pytest.raises(ValueError, match=match):
        invoke(args['registration_raw'], review_path=paths['review'],
            launch_word_path=paths['word'], ci_path=tmp_path / 'unread-ci.json',
            subscription_guard_path=paths['guard'], subscription_guard_sha256=guard.sha(raw))
    assert len(verified_calls) == 1
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
