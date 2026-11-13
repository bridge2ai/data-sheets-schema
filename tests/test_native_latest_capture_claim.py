"""N1 v8 last-claimed capture regressions, 2026-11-12.

Only the existing local scripted Python capture peer may execute. Registration
reconstruction and engine prerequisites retain the explicit component isolation
of their source fixtures. The actual word/claim locks, capture reconstruction,
guard serialization, current admission and first reservation boundary execute.
These tests establish neither native/account evidence nor launch acceptance.
"""
from pathlib import Path

import pytest

from data_sheets_schema import native_capture_words as words
from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_admission as admission
from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema import native_subscription_guard_v2 as guard
from tests import test_native_subscription_capture as fixtures
from tests.test_native_u4b_a3_reservation import FirstReservationObserved, reservation_case
from tests.test_native_u4b_admission import prepared


def retained(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob('*') if path.is_file()}


def current_context(raw, arguments, value, *, current=True):
    return admission.context(raw, registration_raw=arguments['registration_raw'],
        runtime=value['runtime'], review_bundle_raw=arguments['review_bundle_raw'],
        launch_word_raw=arguments['launch_word_raw'], current=current)


def test_latest_capture_canary_records_checked_pair_and_holds_reservation_lock(tmp_path, monkeypatch):
    arguments, value, paths, raw = prepared(tmp_path, monkeypatch)
    document = guard.strict_json(raw)
    assert set(document) == guard.KEYS
    assert document['capture_index'] == document['capture_claim_count'] == 1
    instance = admission.load_current(paths['guard'], guard.sha(raw),
        registration_raw=arguments['registration_raw'], runtime=value['runtime'],
        launch_word_path=paths['word'], review_path=paths['review'])
    snapshot = instance.snapshot()
    assert snapshot['capture_index'] == snapshot['capture_claim_count'] == 1
    terms = review.validate_bundle(**fixtures.read_arguments(arguments))
    guard.validate_saved_snapshot(raw, snapshot, registration_raw=arguments['registration_raw'],
        runtime=value['runtime'], launch_word_raw=arguments['launch_word_raw'], owner_statement=terms)
    before = retained(arguments['directory'])
    with capture.capture_admission_lease(**fixtures.read_arguments(arguments), guard_raw=raw):
        with pytest.raises(ValueError, match='already in use'):
            capture.capture_subscription(**arguments)
        instance.before_reservation()
    assert retained(arguments['directory']) == before
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
    assert paths['guard'].read_bytes() == raw


@pytest.mark.parametrize('later', ['success', 'quota_refused', 'failed', 'interrupted'])
def test_last_claim_supersedes_earlier_guard_even_when_it_cannot_be_admitted(
        tmp_path, monkeypatch, later):
    original_peer = fixtures.peer

    def peer(mode):
        raw = original_peer(mode)
        if later == 'quota_refused':
            raw = raw.replace(b"'utilization':0.2,", b"'utilization':(0.9 if "
                b"os.path.basename(os.path.dirname(os.getcwd())) == 'capture-2' else 0.2),")
        elif later == 'failed':
            raw = raw.replace(b"if MODE == 'nonzero':", b"if MODE == 'nonzero' or "
                b"os.path.basename(os.path.dirname(os.getcwd())) == 'capture-2':")
        return raw

    monkeypatch.setattr(fixtures, 'peer', peer)
    arguments, value, paths, raw = prepared(tmp_path, monkeypatch)
    root = fixtures.word_directory(arguments)
    first = root / 'capture-1' / 'capture.json'
    original_first = retained(first.parent)
    if later == 'interrupted':
        original_new = capture._new

        def interrupted(path, body):
            original_new(path, body)
            if path.name == 'claim-2.json':
                raise InterruptedError('synthetic interruption after second durable claim')

        with monkeypatch.context() as patch:
            patch.setattr(capture, '_new', interrupted)
            with pytest.raises(InterruptedError, match='second durable claim'):
                capture.capture_subscription(**arguments)
        assert not (root / 'capture-2').exists()
    elif later == 'failed':
        with pytest.raises(ValueError, match='process failed'):
            capture.capture_subscription(**arguments)
        failed = capture.strict_json((root / 'capture-2' / 'capture.json').read_bytes())
        assert failed['status'] == 'failed' and failed['lifecycle']['spawn_count'] == 1
    else:
        second = capture.capture_subscription(**arguments)
        assert capture.read_capture(second, **fixtures.read_arguments(arguments))['capture_index'] == 2
        if later == 'quota_refused':
            with pytest.raises(ValueError, match='weekly subscription headroom'):
                with capture.current_guard_preparation(second, **fixtures.read_arguments(arguments)):
                    pytest.fail('quota-refused capture produced a guard')
    assert (root / 'claim-2.json').is_file()
    before = retained(arguments['directory'])
    with pytest.raises(ValueError, match='last claimed capture'):
        with capture.current_guard_preparation(first, **fixtures.read_arguments(arguments)):
            pytest.fail('superseded capture produced a guard')
    with pytest.raises(ValueError, match='last claimed capture'):
        current_context(raw, arguments, value)
    with pytest.raises(ValueError, match='last claimed capture'):
        with capture.capture_admission_lease(**fixtures.read_arguments(arguments), guard_raw=raw):
            pytest.fail('superseded guard reached reservation')
    # Historical reconstruction is still exact and independent of later claims.
    module, _ = current_context(raw, arguments, value, current=False)
    assert module is guard
    assert retained(first.parent) == original_first
    assert retained(arguments['directory']) == before
    assert paths['guard'].read_bytes() == raw
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()


def test_guard_preparation_holds_word_lock_through_guard_file_write(tmp_path, monkeypatch):
    arguments, value = fixtures.component(tmp_path, monkeypatch)
    manifest = capture.capture_subscription(**arguments)
    before = retained(arguments['directory'])
    destination = tmp_path / 'prepared-current-guard.json'
    with capture.current_guard_preparation(manifest, **fixtures.read_arguments(arguments)) as raw:
        with pytest.raises(ValueError, match='already in use'):
            capture.capture_subscription(**arguments)
        with pytest.raises(ValueError, match='already in use'):
            capture.activate_capture_word(**fixtures.read_arguments(arguments))
        destination.write_bytes(raw)
        assert destination.read_bytes() == raw
    assert retained(arguments['directory']) == before
    current_context(raw, arguments, value)


def test_historical_v2_shape_cannot_gain_current_admission(tmp_path, monkeypatch):
    arguments, value, paths, current = prepared(tmp_path, monkeypatch)
    document = guard.strict_json(current)
    for key in guard.CAPTURE_SELECTION_KEYS:
        del document[key]
    historical = guard.canonical(document)
    assert set(document) == guard.HISTORICAL_KEYS
    module, extra = current_context(historical, arguments, value, current=False)
    instance = module.SubscriptionGuard(historical, expected_sha256=guard.sha(historical),
        registration_raw=arguments['registration_raw'], runtime=value['runtime'],
        launch_word_raw=arguments['launch_word_raw'], **extra)
    assert not guard.CAPTURE_SELECTION_KEYS & set(instance.snapshot())
    module.validate_saved_snapshot(historical, instance.snapshot(),
        registration_raw=arguments['registration_raw'], runtime=value['runtime'],
        launch_word_raw=arguments['launch_word_raw'], **extra)
    with pytest.raises(ValueError, match='capture selection'):
        current_context(historical, arguments, value)
    paths['guard'].write_bytes(historical)
    with pytest.raises(ValueError, match='capture selection'):
        admission.load_current(paths['guard'], guard.sha(historical),
            registration_raw=arguments['registration_raw'], runtime=value['runtime'],
            launch_word_path=paths['word'], review_path=paths['review'])
    with pytest.raises(ValueError, match='capture selection'):
        with capture.capture_admission_lease(**fixtures.read_arguments(arguments), guard_raw=historical):
            pytest.fail('legacy quota component gained current reservation admission')
    assert not Path(value['attempt_directory']).exists()


@pytest.mark.parametrize('change', [
    {'capture_index': True}, {'capture_claim_count': 1.0}, {'capture_index': 0},
    {'capture_index': 4, 'capture_claim_count': 4}, {'capture_claim_count': 2},
    {'extra_selection': 1}, {'capture_index': None},
])
def test_rehashed_selection_requires_closed_strict_integer_pair(tmp_path, monkeypatch, change):
    arguments, value, _, raw = prepared(tmp_path, monkeypatch)
    document = guard.strict_json(raw)
    document.update(change)
    if document['capture_index'] is None:
        del document['capture_index']
    changed = guard.canonical(document)
    with pytest.raises(ValueError):
        current_context(changed, arguments, value)
    with pytest.raises(ValueError):
        with capture.capture_admission_lease(**fixtures.read_arguments(arguments), guard_raw=changed):
            pytest.fail('malformed selection reached reservation')


@pytest.mark.parametrize('event_index', [1, 2])
def test_rehashed_valid_numbers_cannot_select_another_capture(tmp_path, monkeypatch, event_index):
    arguments, value, _, raw = prepared(tmp_path, monkeypatch)
    second = capture.capture_subscription(**arguments)
    if event_index == 2:
        with capture.current_guard_preparation(second, **fixtures.read_arguments(arguments)) as raw:
            pass
    document = guard.strict_json(raw)
    document.update(capture_index=3 - event_index, capture_claim_count=3 - event_index)
    with pytest.raises(ValueError, match='last claimed capture|capture index differs'):
        current_context(guard.canonical(document), arguments, value)


def test_saved_snapshot_cannot_change_the_checked_claim_count(tmp_path, monkeypatch):
    arguments, value, _, raw = prepared(tmp_path, monkeypatch)
    terms = review.validate_bundle(**fixtures.read_arguments(arguments))
    instance = guard.SubscriptionGuard(raw, expected_sha256=guard.sha(raw),
        registration_raw=arguments['registration_raw'], runtime=value['runtime'],
        launch_word_raw=arguments['launch_word_raw'], owner_statement=terms)
    snapshot = instance.snapshot()
    snapshot['capture_claim_count'] = 2
    with pytest.raises(ValueError, match='metadata differs'):
        guard.validate_saved_snapshot(raw, snapshot, registration_raw=arguments['registration_raw'],
            runtime=value['runtime'], launch_word_raw=arguments['launch_word_raw'], owner_statement=terms)


@pytest.mark.parametrize('deferred', [False, True])
def test_claim_added_after_current_join_refuses_both_actual_reservation_routes(
        tmp_path, monkeypatch, deferred):
    actual_locked = words.locked
    invoke, arguments, value, _, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=300, deferred_selection=deferred)
    original = capture._current_authority
    claimed = []

    def add_claim_before_lock(*args, **kwargs):
        authority = original(*args, **kwargs)
        if 'current-join-passed' in trace and not claimed:
            # The inherited trace wrapper describes the engine lease only.
            # The interleaved capture uses the same genuine flock body.
            with monkeypatch.context() as patch:
                patch.setattr(words, 'locked', actual_locked)
                claimed.append(capture.capture_subscription(**arguments))
        return authority

    monkeypatch.setattr(capture, '_current_authority', add_claim_before_lock)
    with pytest.raises(ValueError, match='last claimed capture'):
        invoke()
    assert len(claimed) == 1 and claimed[0].parent.name == 'capture-2'
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
    assert 'margin-enter' not in trace and 'first-mkdir-fsynced' not in trace
    assert not active[0]


@pytest.mark.parametrize('deferred', [False, True])
def test_latest_check_lock_remains_held_through_actual_first_reservation(
        tmp_path, monkeypatch, deferred):
    actual_locked = words.locked
    invoke, arguments, value, _, trace, active = reservation_case(
        tmp_path, monkeypatch, remaining=300, deferred_selection=deferred)
    original = guard.SubscriptionGuard.before_reservation
    checked = []

    def contested(instance):
        assert active[0]
        with monkeypatch.context() as patch:
            patch.setattr(words, 'locked', actual_locked)
            with pytest.raises(ValueError, match='already in use'):
                capture.capture_subscription(**arguments)
        checked.append(guard.capture_selection(instance.value, required=True))
        return original(instance)

    monkeypatch.setattr(guard.SubscriptionGuard, 'before_reservation', contested)
    with pytest.raises(FirstReservationObserved):
        invoke()
    assert checked == [{'capture_index': 1, 'capture_claim_count': 1}]
    assert Path(value['attempt_directory']).is_dir()
    assert not (fixtures.word_directory(arguments) / 'claim-2.json').exists()
    assert trace.index('margin-passed') < trace.index('first-mkdir-fsynced')
    assert not active[0]
    with words.locked(value, arguments['registration_raw']) as journal:
        journal.require(arguments['launch_word_raw'])
