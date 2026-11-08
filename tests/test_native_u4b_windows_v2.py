"""A2 items 4-6: numerical windows, UTC chronology and unverified stopped data.

2026-11-08. Invented quota events exercise actual guard construction, delivery,
snapshot validation and transcript replay. No account, process or provider is
used, and these fixtures do not certify real subscription entitlement.
"""
from copy import deepcopy

import pytest

from data_sheets_schema import native_subscription_guard_v2 as guard
from tests.test_native_subscription_guard_v2 import case, build, event_document, saved, timestamp


def extended(case, *, numeric=True):
    event = deepcopy(case['event'])
    event['rate_limit_info']['unifiedWindows']['fortnight'] = (
        {'utilization': 0.25, 'resetsAt': case['now'] + 7200} if numeric
        else {'description': 'Uninterpreted future window', 'status': 'opaque'})
    return event


def test_real_guard_replays_numeric_and_record_only_unknown_windows(case):
    event = extended(case)
    event['rate_limit_info']['unifiedWindows']['future_metadata'] = {'status': 'opaque', 'note': 'retained'}
    value = build(case, document=event_document(case, event))
    before = value.snapshot()
    assert before['initial_windows']['fortnight']['utilization'] == 0.25
    assert before['initial_record_only_windows']['future_metadata'] == [{'status': 'opaque', 'note': 'retained'}]
    value.before_dispatch()
    value.observe(event)
    out = saved(case, value, guard.canonical(event) + b'\n')
    assert out['checked'] is out['complete'] is out['passed'] is True
    assert out['observed_windows']['fortnight']['count'] == 1
    opaque = out['observed_record_only_windows']['future_metadata']
    assert opaque['count'] == 1 and opaque['first'] == opaque['last']
    assert opaque['last']['rows'] == [{'status': 'opaque', 'note': 'retained'}]
    assert 'no safety verdict' in value.snapshot()['unknown_window_policy']


@pytest.mark.parametrize('utilization', [0, 0.0, 0.999999])
def test_unknown_numeric_fraction_boundaries_preserve_zero_and_headroom(case, utilization):
    event = extended(case)
    event['rate_limit_info']['unifiedWindows']['fortnight']['utilization'] = utilization
    value = build(case, document=event_document(case, event))
    value.before_dispatch()
    value.observe(event)
    out = saved(case, value, guard.canonical(event) + b'\n')
    assert out['passed'] is True
    assert out['observed_windows']['fortnight']['last']['utilization'] == utilization


@pytest.mark.parametrize('window', ['five_hour', 'seven_day', 'fortnight'])
@pytest.mark.parametrize('bad', [-0.1, False, True, 1, 1.1, '0.2', None])
def test_same_fraction_domain_at_admission_delivery_and_completed_replay(case, window, bad):
    event = extended(case)
    event['rate_limit_info']['unifiedWindows'][window]['utilization'] = bad
    with pytest.raises(ValueError):
        build(case, document=event_document(case, event))
    value = build(case)
    value.before_dispatch()
    original = value.snapshot()
    with pytest.raises(ValueError):
        value.observe(event)
    assert value.stop_reason and value.observed_events == 1
    # An unchanged success-looking snapshot cannot suppress the bad event.
    with pytest.raises(ValueError):
        saved(case, value, guard.canonical(event) + b'\n', snapshot=original)


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -float('inf')])
def test_unknown_nonfinite_live_reading_is_never_record_only(case, bad):
    value = build(case)
    value.before_dispatch()
    event = extended(case)
    event['rate_limit_info']['unifiedWindows']['fortnight']['utilization'] = bad
    with pytest.raises(ValueError, match='finite bounded JSON'):
        value.observe(event)
    assert value.stop_reason and value.observed_events == 1
    assert 'fortnight' not in value.snapshot()['observed_record_only_windows']


@pytest.mark.parametrize('window', ['five_hour', 'seven_day', 'fortnight'])
@pytest.mark.parametrize('reset_offset', [0, 30])
def test_reset_must_follow_both_capture_and_dispatch_in_every_route(case, window, reset_offset):
    event = extended(case)
    event['rate_limit_info']['unifiedWindows'][window]['resetsAt'] = case['now'] + reset_offset
    # Dispatch is later than capture; +30 is after capture but not dispatch.
    with pytest.raises(ValueError, match='reset'):
        build(case, document=event_document(case, event), now=case['now'] + 30)
    value = build(case, now=case['now'] + 30)
    value.before_dispatch()
    before = value.snapshot()
    assert before['dispatched_at'] == timestamp(case['now'] + 30)
    with pytest.raises(ValueError, match='reset'):
        value.observe(event)
    with pytest.raises(ValueError, match='reset'):
        saved(case, value, guard.canonical(event) + b'\n', snapshot=before)


@pytest.mark.parametrize('status', ['rejected', 'unknown'])
def test_numeric_unknown_window_cannot_hide_explicit_unsafe_status(case, status):
    event = extended(case)
    event['rate_limit_info']['unifiedWindows']['fortnight']['status'] = status
    with pytest.raises(ValueError, match='fortnight.*rejected or unknown'):
        build(case, document=event_document(case, event))


def test_unknown_without_utilization_is_raw_record_only_even_with_opaque_status(case):
    event = extended(case, numeric=False)
    event['rate_limit_info']['unifiedWindows']['fortnight'].update(status='rejected', resetsAt=False)
    value = build(case, document=event_document(case, event))
    value.before_dispatch()
    value.observe(event)
    out = saved(case, value, guard.canonical(event) + b'\n')
    assert out['passed'] is True
    assert 'fortnight' not in out['observed_windows']
    assert out['observed_record_only_windows']['fortnight']['last']['rows'][0]['resetsAt'] is False
    event['rate_limit_info']['status'] = 'rejected'
    with pytest.raises(ValueError, match='top-level'):
        value.observe(event)


def test_record_only_event_after_dispatch_does_not_invent_numerical_reading(case):
    event = {'type': 'rate_limit_event', 'rate_limit_info': {'status': 'allowed',
        'isUsingOverage': False, 'rateLimitType': 'future_metadata', 'note': 'not allowed at info level'}}
    # Unknown top-level fields remain refused; record-only is not a parser bypass.
    with pytest.raises(ValueError, match='unknown fields'):
        guard.window_readings(event, require_both=False)
    del event['rate_limit_info']['note']
    value = build(case)
    value.before_dispatch()
    value.observe(event)
    out = saved(case, value, guard.canonical(event) + b'\n')
    assert out['passed'] is True
    assert all(row['count'] == 0 for row in out['observed_windows'].values())
    assert out['observed_record_only_windows']['future_metadata']['count'] == 1


@pytest.mark.parametrize('mutation', ['missing_dispatch', 'earlier_dispatch', 'late_dispatch',
    'boolean_dispatch', 'offset_dispatch', 'invented_verified', 'opaque_payload', 'opaque_count'])
def test_saved_snapshot_cannot_rewrite_dispatch_or_record_only_evidence(case, mutation):
    event = extended(case, numeric=False)
    value = build(case)
    value.before_dispatch()
    value.observe(event)
    snapshot = value.snapshot()
    if mutation == 'missing_dispatch': del snapshot['dispatched_at']
    elif mutation == 'earlier_dispatch': snapshot['dispatched_at'] = timestamp(case['now'] - 1)
    elif mutation == 'late_dispatch': snapshot['dispatched_at'] = timestamp(case['now'] + 121)
    elif mutation == 'boolean_dispatch': snapshot['dispatched_at'] = False
    elif mutation == 'offset_dispatch': snapshot['dispatched_at'] = timestamp(case['now']).replace('Z', '+00:00')
    elif mutation == 'invented_verified': snapshot['after_readings_verified'] = True
    elif mutation == 'opaque_payload': snapshot['observed_record_only_windows']['fortnight']['last']['rows'][0]['description'] = 'changed'
    else: snapshot['observed_record_only_windows']['fortnight']['count'] = False
    with pytest.raises(ValueError):
        saved(case, value, guard.canonical(event) + b'\n', snapshot=snapshot)


@pytest.mark.parametrize('stamp', [
    '2026-11-08T00:00:00', '2026-11-08 00:00:00Z', '2026-11-08T00:00:00z',
    '2026-11-08T00:00:00+00:00', '2026-11-08T01:00:00+01:00',
    '2026-11-08T00:00:00.1234567Z', '2026-11-08T00:00:00.Z',
    '2026-02-30T00:00:00Z', '2026-11-08T24:00:00Z', '2026-11-08T00:00:60Z',
    ' 2026-11-08T00:00:00Z', '2026-11-08T00:00:00Z\n', 0, False, None,
])
def test_authorized_at_strict_utc_format_before_any_dispatch(case, stamp):
    word = guard.strict_json(case['word'])
    word['authorized_at'] = stamp
    raw = guard.canonical(word)
    with pytest.raises(ValueError, match='authorized_at'):
        build(case, word=raw, document={**case['document'], 'launch_word_sha256': guard.sha(raw)})


@pytest.mark.parametrize('fraction', ['', '.1', '.123456'])
def test_explicit_utc_timestamp_accepts_only_documented_precision(fraction):
    stamp = '2026-11-08T00:00:00' + fraction + 'Z'
    assert type(guard._timestamp(stamp, 'authorized_at')) is float


@pytest.mark.parametrize('stopped', [False, True])
def test_incomplete_after_readings_are_labeled_unverified_in_snapshot_and_result(case, stopped):
    value = build(case)
    value.before_dispatch()
    event = extended(case)
    if stopped:
        event['rate_limit_info']['unifiedWindows']['five_hour']['utilization'] = 1
        with pytest.raises(ValueError):
            value.observe(event)
    else:
        value.observe(event)
    snapshot = value.snapshot()
    assert snapshot['after_readings_verified'] is False
    assert 'stopped-attempt readings remain unverified' in snapshot['after_readings_basis']
    out = saved(case, value, guard.canonical(event) + b'\n', complete=False)
    assert out['checked'] is out['complete'] is out['passed'] is False
    assert 'not independently verified' in out['basis']


def test_unknown_window_inventories_are_bounded_across_events(case):
    value = build(case)
    value.before_dispatch()
    # Two mandatory names already occupy the fixed total bound.
    for index in range(guard.MAX_WINDOWS - len(guard.WINDOWS)):
        event = {'type': 'rate_limit_event', 'rate_limit_info': {'status': 'allowed',
            'isUsingOverage': False, 'unifiedWindows': {f'opaque_{index}': {}}}}
        value.observe(event)
    event['rate_limit_info']['unifiedWindows'] = {'one_too_many': {}}
    with pytest.raises(ValueError, match='inventory exceeds its bound'):
        value.observe(event)
    assert len(value.snapshot()['observed_record_only_windows']) == guard.MAX_WINDOWS - len(guard.WINDOWS)
