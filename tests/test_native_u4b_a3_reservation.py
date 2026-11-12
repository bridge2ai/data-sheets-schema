"""A3 execution reservation ordering, 2026-11-08; never native dispatch.

The public engine.launch and its first real mkdir/fsync execute. Unavailable
registration/composition/source capability, controller prewarm and CI/admit prerequisites are
explicit component isolations, not successful full-chain registration. The
actual saved runtime, scripted capture, review/word, guard/context, current-word
journal and the shared reservation lock bodies execute. Direct guards also use
the public capture_admission_lease. The fused route uses its actual input tail
and full _current_authority entry, with registration reconstruction isolated.
A sentinel stops immediately
after the first generation-directory reservation. No native executable, network
provider, keep-awake acquisition or runtime probe is reached.
"""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_capture_words as words
from data_sheets_schema import native_execution_capabilities as capabilities
from data_sheets_schema import native_execution_orchestration as engine
from data_sheets_schema import native_execution_registration_v2 as admission
from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_shared_execution_orchestration as native
from data_sheets_schema import native_shared_registration_orchestration as registration
from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema import native_subscription_admission as subscription
from data_sheets_schema import native_subscription_guard_v2 as guard
from tests.test_native_subscription_capture import component, read_arguments
from tests.test_native_subscription_guard_v2 import timestamp


class FirstReservationObserved(RuntimeError):
    """Expected stop after actual mkdir/fsync; no native dispatch permitted."""


def reservation_case(tmp_path, monkeypatch, *, remaining, change_at_admit=None,
                     source_check_seconds=0, deferred_selection=False,
                     mutate_values=None, tail_failure=None):
    arguments, value = component(tmp_path, monkeypatch,
        mode='second_mismatch' if change_at_admit == 'poison' else 'success')
    # The observation and production policy already bind this Darwin fixture.
    # Keep both intact. Non-Darwin components isolate only the host prerequisite;
    # they do not establish native portability. Darwin keeps the actual function.
    declared_platform = value['runtime']['keep_awake']['host_platform']
    if native._platform() != declared_platform:
        monkeypatch.setattr(native, '_platform', lambda: declared_platform)
    raw = arguments['registration_raw']
    ci_raw = b'{"scope":"isolated CI prerequisite, not launch acceptance"}'
    word = guard.strict_json(arguments['launch_word_raw'])
    word['ci_sha256'] = guard.sha(ci_raw)
    arguments['launch_word_raw'] = guard.canonical(word)
    manifest = capture.capture_subscription(**arguments)
    recorded = capture.read_capture(manifest, **read_arguments(arguments))
    assert recorded['lifecycle'] == {'spawn_count': 1, 'returncode': 0,
        'cleanup': {'child_started': True, 'leader_reaped': True, 'group_absent': True}}
    selected = recorded['selected_event']
    owner = review.validate_bundle(**read_arguments(arguments))
    clock = [guard._timestamp(selected['captured_at'], 'captured_at')
             + owner['max_age_seconds'] - remaining]
    monkeypatch.setattr(guard, '_now', lambda: clock[0])
    guard_raw = guard.prepare_guard(registration_raw=raw, runtime=value['runtime'],
        launch_word_raw=arguments['launch_word_raw'], owner_statement=owner,
        event_raw=selected['event_json'].encode(), captured_at=selected['captured_at'],
        maximum_starting_utilization=owner['max_starting_weekly_utilization'],
        max_age_seconds=owner['max_age_seconds'])
    watched = guard.SubscriptionGuard(guard_raw, expected_sha256=guard.sha(guard_raw),
        registration_raw=raw, runtime=value['runtime'],
        launch_word_raw=arguments['launch_word_raw'], owner_statement=owner)
    contract, effects = native._engine_bindings(launch_guard=watched)
    contract.require_fixed()  # The fixed package-module contract is not bypassed.
    attempt, evidence = Path(value['attempt_directory']), Path(value['evidence_directory'])
    bodies = {'review': arguments['review_bundle_raw'], 'ci': ci_raw,
              'launch_word': arguments['launch_word_raw']}
    inputs = {}
    for name, body in bodies.items():
        path = tmp_path / ('authority-' + name + '.json')
        path.write_bytes(body)
        inputs[name] = str(path)
    authorization = {'inputs': inputs, 'raw': bodies}
    trace, classifier = [], object()
    active = [False]
    entering_lease = [False]
    reservation_ready = [False]
    engine_value = [None]
    admitted_guard = [watched]
    if deferred_selection:
        guard_path = tmp_path / 'authority-guard.json'
        guard_path.write_bytes(guard_raw)
        effects = replace(effects, launch_guard=subscription.select_current(
            guard_path, guard.sha(guard_raw), registration_raw=raw,
            runtime=value['runtime'], launch_word_path=inputs['launch_word'],
            review_path=inputs['review']))

    def forbidden(*args, **kwargs):
        pytest.fail('reservation test reached a post-reservation effect or executable')

    class IsolatedSourceControls:
        """Unavailable source capability prerequisite; no execution interface."""
        def require_complete(self):
            trace.append('isolated-source-check')
            if active[0]:
                trace.append('in-lease-source-check')
                clock[0] += source_check_seconds

        @contextmanager
        def loaded_classifier(self):
            assert not active[0]
            yield classifier

        def __getitem__(self, key):
            forbidden(key)

    @contextmanager
    def isolated_capabilities(dependencies):
        assert dependencies == value['dependencies']
        trace.append('isolated-source-enter')
        yield IsolatedSourceControls()

    class IsolatedController:
        """Unavailable controller prerequisite only; no activation or effects."""
        def prewarm_before_acceptance(self):
            assert not active[0] and not entering_lease[0]
            assert not attempt.exists() and not evidence.exists()
            trace.append('controller-prewarm-closed')

    def isolated_controller(self, checked, submitted):
        assert checked == value and submitted == raw
        assert not active[0] and not attempt.exists() and not evidence.exists()
        trace.append('controller-construct')
        return IsolatedController()

    def isolated_composition(submitted):
        assert submitted == value['composition_raw_json'].encode()
        trace.append('isolated-composition')
        return {'instruction_path': str(tmp_path / 'never-read-instruction.txt')}

    def isolated_paths(submitted, *, fresh, extra_protected):
        assert submitted == value and fresh is True
        assert extra_protected == list(inputs.values())
        assert not attempt.exists() and not evidence.exists()
        return attempt, evidence

    def isolated_authorizations(submitted, checked, **paths):
        assert submitted == raw and checked == value
        assert paths == {name + '_path': path for name, path in inputs.items()}
        assert review.validate_bundle(raw, bodies['review'], bodies['launch_word']) == owner
        assert guard.strict_json(bodies['launch_word'])['ci_sha256'] == guard.sha(bodies['ci'])
        return authorization

    def isolated_unchanged(checked, submitted, selected_authorization):
        assert checked == value and submitted == raw and selected_authorization == authorization
        assert registration.verified(raw) == value
        assert all(Path(path).read_bytes() == bodies[name] for name, path in inputs.items())
        trace.append('isolated-source-recapture')

    def isolated_committed_source(dependencies):
        assert dependencies == value['dependencies']
        assert not active[0] and not attempt.exists()
        trace.append('isolated-committed-source')

    actual_tail = native._unchanged_inputs
    actual_file = native._file

    def traced_input_tail(checked, selected_authorization):
        assert reservation_ready[0] and not active[0]
        assert selected_authorization == authorization
        trace.append('input-tail-enter')
        actual_tail(checked, selected_authorization)
        trace.append('input-tail-passed')

    def observed_file(path, name):
        result = actual_file(path, name)
        if reservation_ready[0] and str(path) == inputs['ci'] and mutate_values == 'during-read':
            engine_value[0]['permission_probe_sha256'] = '3' * 64
            trace.append('engine-mutated-during-read')
        return result

    def isolated_admit(submitted, *, review_path, ci_path, launch_word_path, classifier_projection):
        assert submitted == raw and classifier_projection is classifier and not active[0]
        assert (review_path, ci_path, launch_word_path) == tuple(inputs.values())
        trace.append('isolated-admit')
        # Mutation follows static inspection but precedes late current capture
        # acceptance. The genuine current join must now refuse before the lease.
        if change_at_admit == 'superseded':
            newer = guard.strict_json(arguments['launch_word_raw'])
            newer['authorized_at'] = timestamp(guard._timestamp(newer['authorized_at'], 'word') + 1)
            capture.activate_capture_word(registration_raw=raw,
                review_bundle_raw=bodies['review'], launch_word_raw=guard.canonical(newer))
            trace.append('newer-word-recorded')
        elif change_at_admit == 'poison':
            with pytest.raises(ValueError, match='registration permanently refused'):
                capture.capture_subscription(**arguments)
            trace.append('limits-refusal-recorded')
        return SimpleNamespace(registration_raw=raw, evidence=tuple(
            SimpleNamespace(pin=SimpleNamespace(path=inputs[name]), raw=bodies[name])
            for name in ('review', 'ci', 'launch_word')))

    actual_load_current = subscription.load_current
    actual_join = engine._join_subscription_authority
    actual_require = words.Journal.require
    actual_locked = words.locked
    actual_current_authority = capture._current_authority

    def traced_load_current(*args, **kwargs):
        assert deferred_selection and not active[0] and not entering_lease[0]
        assert trace[-1] == 'controller-prewarm-closed'
        trace.append('load-current-enter')
        result = actual_load_current(*args, **kwargs)
        assert type(result) is guard.SubscriptionGuard
        assert result.raw == watched.raw == guard_raw
        assert result.value['captured_at'] == selected['captured_at']
        assert result._clock is guard._now and not result.dispatched
        admitted_guard[0] = result
        trace.append('load-current-accepted')
        return result

    def traced_join(*args, **kwargs):
        current = kwargs.get('current_launch', False)
        if current:
            assert not active[0] and not entering_lease[0]
            assert args[0] is admitted_guard[0]
            trace.append('current-join-enter')
        result = actual_join(*args, **kwargs)
        if current:
            trace.append('current-join-passed')
            reservation_ready[0] = True
            engine_value[0] = args[2]
            if mutate_values in ('current', 'both'):
                engine_value[0]['permission_probe_sha256'] = '3' * 64
                trace.append('engine-value-mutated')
            if tail_failure == 'changed-bytes':
                Path(inputs['ci']).write_bytes(b'changed authority bytes\n')
            elif tail_failure == 'read-failure':
                Path(inputs['ci']).unlink()
            elif tail_failure == 'platform':
                monkeypatch.setattr(native, '_platform', lambda: 'changed-platform')
        return result

    def traced_current_authority(*args, **kwargs):
        tracing = reservation_ready[0]
        if tracing:
            assert not active[0] and not attempt.exists()
            trace.append('lease-authority-enter')
        result = actual_current_authority(*args, **kwargs)
        if tracing:
            trace.append('lease-authority-passed')
            if mutate_values in ('fresh', 'both'):
                result[0]['permission_probe_sha256'] = '3' * 64
                trace.append('fresh-value-mutated')
        return result

    def traced_require(self, *args, **kwargs):
        if entering_lease[0]:
            assert active[0] and kwargs.get('current', True) is True
            trace.append('lease-current-enter')
        result = actual_require(self, *args, **kwargs)
        if entering_lease[0]:
            trace.append('lease-current-passed')
        return result

    @contextmanager
    def traced_locked(*args, **kwargs):
        if not reservation_ready[0]:
            with actual_locked(*args, **kwargs) as journal:
                yield journal
            return
        assert not active[0], 'reservation attempted a nested capture journal lease'
        assert kwargs.get('create', False) is False
        trace.append('lease-enter')
        entering_lease[0] = True
        try:
            with actual_locked(*args, **kwargs) as journal:
                active[0] = True
                trace.append('lease-held')
                try:
                    yield journal
                finally:
                    active[0] = False
        finally:
            entering_lease[0] = False
            reservation_ready[0] = False
            trace.append('lease-exit')

    actual_margin = guard.SubscriptionGuard.before_reservation

    def traced_margin(self):
        assert self is admitted_guard[0] and active[0]
        trace.append('margin-enter')
        result = actual_margin(self)
        trace.append('margin-passed')
        return result

    actual_sync = effects.sync_directory

    def stop_after_reservation(parent):
        assert parent == attempt.parent and active[0]
        assert attempt.is_dir() and list(attempt.iterdir()) == []
        assert not evidence.exists() and not watched.dispatched
        assert not admitted_guard[0].dispatched
        actual_sync(parent)
        trace.append('first-mkdir-fsynced')
        raise FirstReservationObserved('first generation reservation observed; intentional test stop')

    monkeypatch.setattr(engine.ExecutionContract, 'make_controller', isolated_controller)
    monkeypatch.setattr(subscription, 'load_current', traced_load_current)
    monkeypatch.setattr(engine, '_join_subscription_authority', traced_join)
    monkeypatch.setattr(words.Journal, 'require', traced_require)
    monkeypatch.setattr(words, 'locked', traced_locked)
    monkeypatch.setattr(capture, '_current_authority', traced_current_authority)
    monkeypatch.setattr(native.authority, 'require_committed', isolated_committed_source)
    monkeypatch.setattr(native, '_unchanged_inputs', traced_input_tail)
    monkeypatch.setattr(native, '_file', observed_file)
    monkeypatch.setattr(capabilities, 'loaded_capabilities', isolated_capabilities)
    monkeypatch.setattr(contract.composition, 'verified_composition', isolated_composition)
    monkeypatch.setattr(registration, 'execution_paths_v2', isolated_paths)
    monkeypatch.setattr(admission, 'admit', isolated_admit)
    monkeypatch.setattr(guard.SubscriptionGuard, 'before_reservation', traced_margin)
    monkeypatch.setattr(engine, '_execute_child', forbidden)
    effects = replace(effects, authorizations=isolated_authorizations, unchanged=isolated_unchanged,
        expected_runtime_observation=lambda checked: {'isolated': checked == value},
        sync_directory=stop_after_reservation, durable_new=forbidden, mkdir_durable=forbidden,
        probe_runtime=forbidden, signals=forbidden)

    def invoke():
        return engine.launch(raw, review_path=inputs['review'], ci_path=inputs['ci'],
            launch_word_path=inputs['launch_word'], contract=contract, effects=effects)

    return invoke, arguments, value, watched, trace, active


def test_registered_90_second_margin_permits_first_real_reservation_only(tmp_path, monkeypatch):
    invoke, arguments, value, watched, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=90)
    with pytest.raises(FirstReservationObserved):
        invoke()
    assert Path(value['attempt_directory']).is_dir()
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]
    ordered = ['isolated-admit', 'lease-enter', 'lease-held', 'in-lease-source-check', 'margin-enter',
               'margin-passed', 'first-mkdir-fsynced', 'lease-exit']
    assert [item for item in trace if item in ordered] == ordered
    # The genuine flock is released even when the deliberate stop propagates.
    with words.locked(value, arguments['registration_raw']) as journal:
        assert journal.require(arguments['launch_word_raw'])['word_sha256'] == guard.sha(
            arguments['launch_word_raw'])


def test_registered_89_second_margin_refuses_before_any_attempt_directory(tmp_path, monkeypatch):
    invoke, _, value, watched, trace, active = reservation_case(tmp_path, monkeypatch, remaining=89)
    with pytest.raises(ValueError, match='pre-reservation freshness margin'):
        invoke()
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]
    assert 'lease-held' in trace and 'margin-enter' in trace and trace[-1] == 'lease-exit'
    assert 'margin-passed' not in trace and 'first-mkdir-fsynced' not in trace


@pytest.mark.parametrize('remaining,permits_reservation', [(90, False), (91, True)],
                         ids=['90-refuse', '91-reserve'])
def test_source_recapture_time_is_charged_before_measuring_reservation_margin(
        tmp_path, monkeypatch, remaining, permits_reservation):
    """One synthetic second models source recapture; no sleeping or native call."""
    invoke, _, value, watched, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=remaining, source_check_seconds=1)
    if permits_reservation:
        with pytest.raises(FirstReservationObserved):
            invoke()
        assert Path(value['attempt_directory']).is_dir()
        assert 'margin-passed' in trace and 'first-mkdir-fsynced' in trace
    else:
        with pytest.raises(ValueError, match='pre-reservation freshness margin'):
            invoke()
        assert not Path(value['attempt_directory']).exists()
        assert 'margin-passed' not in trace and 'first-mkdir-fsynced' not in trace
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]
    assert trace.count('in-lease-source-check') == 1
    assert trace.index('in-lease-source-check') < trace.index('margin-enter')
    assert trace[-1] == 'lease-exit'


@pytest.mark.parametrize('change,reason', [('superseded', 'superseded'),
                                        ('poison', 'registration permanently refused')],
                         ids=['superseded', 'poison'])
def test_admission_changes_after_initial_join_refuse_before_attempt_reservation(
        tmp_path, monkeypatch, change, reason):
    invoke, _, value, watched, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=90, change_at_admit=change)
    with pytest.raises(ValueError, match=reason):
        invoke()
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]
    assert 'isolated-admit' in trace and trace[-1] == 'current-join-enter'
    assert 'current-join-passed' not in trace and 'lease-enter' not in trace
    assert 'lease-held' not in trace and 'margin-enter' not in trace
    assert 'first-mkdir-fsynced' not in trace


def test_deferred_capture_acceptance_exact_order_to_real_reservation(tmp_path, monkeypatch):
    """Only controller/source/CI prerequisites are isolated; all quota gates run."""
    invoke, arguments, value, watched, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=90, deferred_selection=True)
    with pytest.raises(FirstReservationObserved):
        invoke()
    expected = [
        'controller-construct', 'controller-prewarm-closed',
        'load-current-enter', 'load-current-accepted',
        'current-join-enter', 'current-join-passed',
        'input-tail-enter', 'isolated-committed-source', 'input-tail-passed',
        'lease-authority-enter', 'lease-authority-passed', 'lease-enter', 'lease-held',
        'lease-current-enter', 'lease-current-passed',
        'isolated-source-check', 'in-lease-source-check',
        'margin-enter', 'margin-passed', 'first-mkdir-fsynced', 'lease-exit',
    ]
    assert trace[trace.index('controller-construct'):] == expected
    assert trace.count('load-current-enter') == trace.count('load-current-accepted') == 1
    assert trace.count('isolated-source-recapture') == 1  # Pre-admission call survives.
    assert Path(value['attempt_directory']).is_dir()
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]
    with words.locked(value, arguments['registration_raw']) as journal:
        assert journal.require(arguments['launch_word_raw'])['word_sha256'] == guard.sha(
            arguments['launch_word_raw'])


@pytest.mark.parametrize('change,reason', [('superseded', 'superseded'),
                                        ('poison', 'registration permanently refused')],
                         ids=['superseded', 'poison'])
def test_deferred_capture_late_load_refuses_admission_mutation(tmp_path, monkeypatch, change, reason):
    invoke, _, value, watched, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=90, deferred_selection=True, change_at_admit=change)
    with pytest.raises(ValueError, match=reason):
        invoke()
    assert trace[-1] == 'load-current-enter'
    assert 'load-current-accepted' not in trace and 'lease-enter' not in trace
    assert 'margin-enter' not in trace and 'first-mkdir-fsynced' not in trace
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]


@pytest.mark.parametrize('mutation', ['current', 'fresh', 'both'])
def test_fused_lease_compares_original_current_and_fresh_execution(tmp_path, monkeypatch, mutation):
    """The producer is isolated; both equal changed values must still refuse."""
    invoke, _, value, watched, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=90, deferred_selection=True, mutate_values=mutation)
    with pytest.raises(ValueError, match='selection changed before reservation'):
        invoke()
    assert value['permission_probe_sha256'] == '2' * 64
    assert 'lease-authority-passed' in trace and 'input-tail-passed' in trace
    assert ('engine-value-mutated' in trace) == (mutation in ('current', 'both'))
    assert ('fresh-value-mutated' in trace) == (mutation in ('fresh', 'both'))
    assert 'lease-enter' not in trace and 'first-mkdir-fsynced' not in trace
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]


def test_fused_lease_refuses_engine_mutation_during_authorization_read(tmp_path, monkeypatch):
    invoke, _, value, watched, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=90, deferred_selection=True, mutate_values='during-read')
    with pytest.raises(ValueError, match='selection changed before reservation'):
        invoke()
    assert trace.index('input-tail-enter') < trace.index('engine-mutated-during-read')
    assert trace.index('engine-mutated-during-read') < trace.index('input-tail-passed')
    assert 'lease-authority-passed' in trace and 'lease-enter' not in trace
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]


@pytest.mark.parametrize('failure,error,reason', [
    ('changed-bytes', ValueError, 'external native shared launch authority changed'),
    ('read-failure', FileNotFoundError, 'authority-ci.json'),
    ('platform', ValueError, 'registered execution host differs'),
], ids=['changed-bytes', 'read-failure', 'platform'])
def test_fused_lease_uses_actual_shared_input_checks(tmp_path, monkeypatch, failure, error, reason):
    invoke, _, value, watched, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=90, deferred_selection=True, tail_failure=failure)
    with pytest.raises(error, match=reason):
        invoke()
    assert trace[-2:] == ['input-tail-enter', 'isolated-committed-source']
    assert 'input-tail-passed' not in trace and 'lease-authority-enter' not in trace
    assert 'lease-enter' not in trace and 'first-mkdir-fsynced' not in trace
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]


@pytest.mark.parametrize('remaining,permits_reservation', [(90, False), (91, True)],
                         ids=['90-refuse', '91-reserve'])
def test_fused_lease_charges_controls_before_margin(tmp_path, monkeypatch, remaining, permits_reservation):
    """Synthetic clock cost checks order, not measured elapsed freshness."""
    invoke, _, value, watched, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=remaining, source_check_seconds=1, deferred_selection=True)
    if permits_reservation:
        with pytest.raises(FirstReservationObserved):
            invoke()
        assert Path(value['attempt_directory']).is_dir()
        assert 'margin-passed' in trace and 'first-mkdir-fsynced' in trace
    else:
        with pytest.raises(ValueError, match='pre-reservation freshness margin'):
            invoke()
        assert not Path(value['attempt_directory']).exists()
        assert 'margin-passed' not in trace and 'first-mkdir-fsynced' not in trace
    assert trace.count('in-lease-source-check') == 1
    assert trace.index('in-lease-source-check') < trace.index('margin-enter')
    assert trace[-1] == 'lease-exit'
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]
