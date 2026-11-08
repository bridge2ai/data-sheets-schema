"""A3 execution reservation ordering, 2026-11-08; never native dispatch.

The public engine.launch and its first real mkdir/fsync execute. Unavailable
registration/composition/source capability and CI/admit prerequisites are
explicit component isolations, not successful full-chain registration. The
actual saved runtime, scripted capture, review/word, guard/context, current-word
journal and capture_admission_lease bodies execute. A sentinel stops immediately
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
from data_sheets_schema import native_subscription_guard_v2 as guard
from tests.test_native_subscription_capture import component, read_arguments
from tests.test_native_subscription_guard_v2 import timestamp


class FirstReservationObserved(RuntimeError):
    """Expected stop after actual mkdir/fsync; no native dispatch permitted."""


def reservation_case(tmp_path, monkeypatch, *, remaining, change_at_admit=None,
                     source_check_seconds=0):
    arguments, value = component(tmp_path, monkeypatch,
        mode='second_mismatch' if change_at_admit == 'poison' else 'success')
    raw = arguments['registration_raw']
    ci_raw = b'{"scope":"isolated CI prerequisite, not launch acceptance"}'
    word = guard.strict_json(arguments['launch_word_raw'])
    word['ci_sha256'] = guard.sha(ci_raw)
    arguments['launch_word_raw'] = guard.canonical(word)
    manifest = capture.capture_subscription(**arguments)
    recorded = capture.read_capture(manifest, **read_arguments(arguments))
    selected = recorded['selected_event']
    owner = review.validate_bundle(**read_arguments(arguments))
    clock = [guard._timestamp(selected['captured_at'], 'captured_at') + 300 - remaining]
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

    def isolated_admit(submitted, *, review_path, ci_path, launch_word_path, classifier_projection):
        assert submitted == raw and classifier_projection is classifier and not active[0]
        assert (review_path, ci_path, launch_word_path) == tuple(inputs.values())
        trace.append('isolated-admit')
        # Mutations occur after the engine's initial genuine context join. Its
        # later genuine lease must therefore be the check that prevents mkdir.
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

    actual_lease = capture.capture_admission_lease

    @contextmanager
    def traced_lease(**kwargs):
        assert not active[0], 'reservation attempted a nested capture journal lease'
        trace.append('lease-enter')
        try:
            with actual_lease(**kwargs) as selected_word:
                active[0] = True
                trace.append('lease-held')
                try:
                    yield selected_word
                finally:
                    active[0] = False
        finally:
            trace.append('lease-exit')

    actual_margin = guard.SubscriptionGuard.before_reservation

    def traced_margin(self):
        assert self is watched and active[0]
        trace.append('margin-enter')
        result = actual_margin(self)
        trace.append('margin-passed')
        return result

    actual_sync = effects.sync_directory

    def stop_after_reservation(parent):
        assert parent == attempt.parent and active[0]
        assert attempt.is_dir() and list(attempt.iterdir()) == []
        assert not evidence.exists() and not watched.dispatched
        actual_sync(parent)
        trace.append('first-mkdir-fsynced')
        raise FirstReservationObserved('first generation reservation observed; intentional test stop')

    monkeypatch.setattr(capabilities, 'loaded_capabilities', isolated_capabilities)
    monkeypatch.setattr(contract.composition, 'verified_composition', isolated_composition)
    monkeypatch.setattr(registration, 'execution_paths_v2', isolated_paths)
    monkeypatch.setattr(admission, 'admit', isolated_admit)
    monkeypatch.setattr(capture, 'capture_admission_lease', traced_lease)
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


@pytest.mark.parametrize('remaining,permits_reservation', [(90, False), (91, True)])
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
                                        ('poison', 'registration permanently refused')])
def test_admission_changes_after_initial_join_refuse_before_attempt_reservation(
        tmp_path, monkeypatch, change, reason):
    invoke, _, value, watched, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=90, change_at_admit=change)
    with pytest.raises(ValueError, match=reason):
        invoke()
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
    assert not watched.dispatched and not active[0]
    assert 'isolated-admit' in trace and 'lease-enter' in trace and trace[-1] == 'lease-exit'
    assert 'lease-held' not in trace and 'margin-enter' not in trace
    assert 'first-mkdir-fsynced' not in trace
