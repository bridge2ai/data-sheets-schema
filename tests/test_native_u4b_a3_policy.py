"""A3 registered policy and margin checks using actual pure guard/review bodies.

All evidence is invented. These component tests exercise no account, binary,
network, registration reconstruction or actual attempt reservation. The caller's
reservation ordering is covered separately by execution integration tests.
"""
from copy import deepcopy

import pytest

from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_guard_v2 as guard
from data_sheets_schema.native_u4b_policy import TERM_VALUES
from tests.test_native_subscription_guard_v2 import (
    build, case, event_document, saved, timestamp,
)


TERMS = {
    'max_starting_weekly_utilization': 0.5,
    'max_starting_five_hour_utilization': 0.25,
    'max_age_seconds': 1200,
    'pre_reservation_margin_seconds': 90,
}


def test_registered_terms_pin_provisional_age_and_unchanged_margin():
    # Independent pin: deriving every assertion from production would hide drift.
    assert TERM_VALUES == TERMS
    assert guard.MAX_AGE_SECONDS == TERMS['max_age_seconds']


@pytest.mark.parametrize('window,utilization,passes', [
    ('five_hour', 0, True), ('five_hour', 0.25, True), ('five_hour', 0.250001, False),
    ('seven_day', 0, True), ('seven_day', 0.50, True), ('seven_day', 0.500001, False),
])
def test_starting_window_inclusive_registered_boundary(case, window, utilization, passes):
    event = deepcopy(case['event'])
    event['rate_limit_info']['unifiedWindows'][window]['utilization'] = utilization
    if passes:
        value = build(case, document=event_document(case, event))
        value.before_reservation()
        assert not value.dispatched
        assert value.value['max_starting_weekly_utilization'] == 0.5
        assert value.value['max_starting_five_hour_utilization'] == 0.25
    else:
        with pytest.raises(ValueError, match='headroom'):
            build(case, document=event_document(case, event))


@pytest.mark.parametrize('remaining,passes', [(TERMS['max_age_seconds'], True), (91, True), (90, True),
                                            (89, False), (1, False), (0, False)])
def test_pre_reservation_margin_90_seconds_is_inclusive_without_dispatch(case, remaining, passes):
    value = build(case, now=case['now'] + case['owner']['max_age_seconds'] - remaining)
    before = value.snapshot()
    if passes:
        assert value.before_reservation() is None
    else:
        with pytest.raises(ValueError, match='pre-reservation freshness margin'):
            value.before_reservation()
    assert value.snapshot() == before
    assert not value.dispatched and value.observed_events == 0


def test_margin_check_does_not_consume_dispatch_or_apply_again_after_preparation(case):
    clock = [case['now'] + case['owner']['max_age_seconds']
             - case['owner']['pre_reservation_margin_seconds']]
    value = guard.SubscriptionGuard(case['raw'], expected_sha256=guard.sha(case['raw']),
        registration_raw=case['registration'], runtime=case['runtime'], launch_word_raw=case['word'],
        owner_statement=case['owner'], clock=lambda: clock[0])
    value.before_reservation()
    assert not value.dispatched
    clock[0] = case['now'] + case['owner']['max_age_seconds'] - 1
    value.before_dispatch()
    assert value.dispatched and value.snapshot()['dispatched_at'] == timestamp(clock[0])
    with pytest.raises(ValueError, match='already consumed'):
        value.before_reservation()


def test_missing_margin_stops_caller_before_its_reservation_marker(case):
    # This marker demonstrates pure caller ordering only, not a live reservation.
    reserved = []
    value = build(case, now=case['now'] + case['owner']['max_age_seconds']
                  - case['owner']['pre_reservation_margin_seconds'] + 1)
    with pytest.raises(ValueError, match='pre-reservation freshness margin'):
        value.before_reservation()
        reserved.append('would reserve after guard')
    assert reserved == [] and not value.dispatched


@pytest.mark.parametrize('key', list(TERMS))
@pytest.mark.parametrize('mutation', ['different', 'bool', 'missing'])
def test_rehashed_owner_terms_cannot_choose_registered_admission_policy(case, key, mutation):
    statement = deepcopy(case['owner'])
    if mutation == 'missing':
        del statement[key]
    else:
        statement[key] = True if mutation == 'bool' else TERMS[key] - 0.01
    with pytest.raises(ValueError):
        review.validate_terms(statement, case['runtime'], word_owner=statement['owner'])
    document = {**case['document'], 'owner_statement_sha256': guard.sha(guard.canonical(statement))}
    with pytest.raises(ValueError):
        build(case, document=document, owner=statement)


@pytest.mark.parametrize('key', list(TERMS))
@pytest.mark.parametrize('mutation', ['different', 'bool', 'missing'])
def test_rehashed_guard_terms_cannot_choose_registered_admission_policy(case, key, mutation):
    document = deepcopy(case['document'])
    if mutation == 'missing':
        del document[key]
    else:
        document[key] = True if mutation == 'bool' else TERMS[key] - 1
    with pytest.raises(ValueError):
        build(case, document=document)


@pytest.mark.parametrize('key', list(TERMS))
def test_even_owner_agreement_cannot_replace_registered_policy(case, key):
    runtime, statement = deepcopy(case['runtime']), deepcopy(case['owner'])
    basis = guard.strict_json(runtime['limits_basis'])
    changed = TERMS[key] - (0.01 if key.endswith('_utilization') else 1)
    basis['admission'][key] = changed
    runtime['limits_basis'] = guard.canonical(basis).decode()
    statement[key] = changed
    with pytest.raises(ValueError, match='registered admission term'):
        review.validate_terms(statement, runtime, word_owner=statement['owner'])


def test_guard_runtime_is_exactly_the_runtime_in_registration_bytes(case):
    runtime, statement = deepcopy(case['runtime']), deepcopy(case['owner'])
    runtime['keep_awake']['basis'] = statement['keep_awake']['basis'] = 'A different explicit basis.'
    # These supplied values agree with each other but not with the registration.
    review.validate_terms(statement, runtime, word_owner=statement['owner'])
    document = {**case['document'], 'runtime_sha256': guard.sha(guard.canonical(runtime)),
        'owner_statement_sha256': guard.sha(guard.canonical(statement))}
    with pytest.raises(ValueError, match='registered runtime bytes'):
        build(case, document=document, runtime=runtime, owner=statement)


@pytest.mark.parametrize('key', ['maximum_starting_five_hour_utilization',
                                'pre_reservation_margin_seconds'])
def test_saved_snapshot_recomputes_new_registered_fields(case, key):
    value = build(case)
    value.before_reservation()
    value.before_dispatch()
    snapshot = value.snapshot()
    snapshot[key] += 1
    with pytest.raises(ValueError):
        saved(case, value, b'', snapshot=snapshot, complete=False)


def test_starting_maxima_are_not_midrun_limits(case):
    value = build(case)
    value.before_reservation()
    value.before_dispatch()
    event = deepcopy(case['event'])
    for row in event['rate_limit_info']['unifiedWindows'].values():
        row['utilization'] = 0.9
    value.observe(event)
    result = saved(case, value, guard.canonical(event) + b'\n')
    assert result['checked'] is result['passed'] is True
    assert result['observed_windows']['five_hour']['highest']['utilization'] == 0.9


@pytest.mark.parametrize('field,value', [('maximum_starting_five_hour_utilization', 0.3),
                                       ('pre_reservation_margin_seconds', 89)])
def test_prepare_guard_explicit_terms_must_equal_registered_values(case, field, value):
    kwargs = {'registration_raw': case['registration'], 'runtime': case['runtime'],
        'launch_word_raw': case['word'], 'event_raw': guard.canonical(case['event']),
        'captured_at': timestamp(case['now']), 'owner_statement': case['owner'],
        'maximum_starting_utilization': 0.5, 'max_age_seconds': case['owner']['max_age_seconds'],
        'clock': lambda: case['now'], field: value}
    with pytest.raises(ValueError):
        guard.prepare_guard(**kwargs)


def test_new_capture_state_directory_is_registered_not_owner_selected(case):
    statement = deepcopy(case['owner'])
    statement['quota_capture']['directory'] += '-other'
    with pytest.raises(ValueError, match='registered capture state directory'):
        review.validate_terms(statement, case['runtime'], word_owner=statement['owner'])


def test_prior_capture_request_version_is_preserved_for_readback(case):
    statement = deepcopy(case['owner'])
    statement['quota_capture'].update(kind=review.PREVIOUS_CAPTURE_KIND, version=2)
    result = review.validate_terms(statement, case['runtime'], word_owner=statement['owner'])
    assert result['quota_capture']['version'] == 2
    assert result['quota_capture']['kind'] == review.PREVIOUS_CAPTURE_KIND
    assert result['quota_capture']['count'] == 3
