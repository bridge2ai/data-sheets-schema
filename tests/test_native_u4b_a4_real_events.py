"""A4 P1-1: exact historical quota bytes, synthetic guard authority and clock.

The extraction helper pins every event to its committed transcript and physical
line. All 209 events reach the genuine admission and delivery bodies. No account,
native executable, provider or successful full registration is exercised.
"""
from copy import deepcopy
import json

import pytest

from data_sheets_schema import native_subscription_guard_v2 as guard
from scripts.adhoc.native_u4b_a4_real_events_20261108 import BASE, event_case, fixture, make_guard
from tests.test_native_subscription_guard_v2 import case


CORPUS = fixture()
EVENTS = CORPUS['events']


def _prepare(context, raw):
    return guard.prepare_guard(registration_raw=context['registration'], runtime=context['runtime'],
        launch_word_raw=context['word'], owner_statement=context['owner'], event_raw=raw,
        captured_at=context['document']['captured_at'],
        maximum_starting_utilization=context['owner']['max_starting_weekly_utilization'],
        max_age_seconds=context['owner']['max_age_seconds'], clock=lambda: context['now'])


def _completed(context, value, transcript):
    return guard.validate_saved_observations(value.raw, value.snapshot(),
        registration_raw=context['registration'], runtime=context['runtime'],
        launch_word_raw=context['word'], owner_statement=context['owner'],
        transcript_raw=transcript, complete=True)


def _representative(status):
    return next(row for row in EVENTS if guard.strict_json(row['raw_json'])['rate_limit_info']['status'] == status)


def test_complete_pinned_event_corpus_preserves_physical_lines_and_source_inventory():
    assert CORPUS['source_commit'] == BASE
    assert len(CORPUS['sources']) == 64 and len(EVENTS) == 209
    assert sum(row['events'] for row in CORPUS['sources']) == 209
    assert {guard.strict_json(row['raw_json'])['rate_limit_info']['status'] for row in EVENTS} == {
        'allowed', 'allowed_warning'}
    for row in EVENTS:
        raw = row['raw_json'].encode()
        assert guard.sha(raw) == row['sha256'] and len(raw) == row['bytes']
        assert raw.endswith(b'\n') and raw.count(b'\n') == 1


def test_retain_before_after_real_event_route_counts(tmp_path):
    from scripts.adhoc.native_u4b_a4_real_events_20261108 import compare
    authority = tmp_path / 'authority'
    authority.mkdir()
    report = compare(authority)
    (tmp_path / 'corpus-comparison.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    assert report['events'] == 209 and report['transcripts'] == 64
    for route in ('admission_shape', 'observe_shape'):
        assert report['totals']['before'][route] == {'admitted': 182, 'refused': 27}
        assert report['totals']['after'][route] == {'admitted': 209}
    assert report['totals']['after']['observe'] == {'admitted': 209}
    for row in report['rows']:
        refusal = row['after']['admission']
        if refusal['status'] == 'refused':
            assert refusal['reason'] in {'insufficient weekly subscription headroom',
                                         'insufficient five-hour subscription headroom'}


@pytest.mark.parametrize('row', EVENTS, ids=[f'event-{index:03}' for index in range(1, 210)])
def test_every_real_event_reaches_admission_and_observe_with_exact_bytes(case, row):
    raw = row['raw_json'].encode()
    context = event_case(case, raw)
    event = guard.strict_json(raw)
    readings = guard.window_readings(event)
    nested = event['rate_limit_info']['unifiedWindows']
    for name in ('five_hour', 'seven_day'):
        assert readings[name]['utilization'] == nested[name]['utilization']
        assert readings[name]['resets_at'] == nested[name]['resetsAt']
    # Real high-use events remain refused by the current admission maxima.
    reason = ('insufficient weekly subscription headroom' if nested['seven_day']['utilization'] > 0.5
              else 'insufficient five-hour subscription headroom' if nested['five_hour']['utilization'] > 0.25
              else None)
    if reason:
        with pytest.raises(ValueError, match=reason):
            _prepare(context, raw)
    else:
        prepared = _prepare(context, raw)
        document = guard.strict_json(prepared)
        assert document['event_json'].encode() == raw
        assert document['event_sha256'] == row['sha256']
        assert make_guard(guard, context).snapshot()['initial_windows'] == readings
    # Starting maxima do not prohibit a non-exhausted live observation.
    value = make_guard(guard, context, seed=True)
    value.before_dispatch()
    value.observe(event)
    assert value.observed_events == 1 and value.stop_reason is None
    for name in ('five_hour', 'seven_day'):
        assert value.snapshot()['observed_windows'][name]['last']['utilization'] == nested[name]['utilization']
    assert raw == row['raw_json'].encode()


@pytest.mark.parametrize('status', ['allowed', 'allowed_warning'])
def test_real_allowed_shapes_complete_exact_saved_replay(case, status):
    row = _representative(status)
    raw = row['raw_json'].encode()
    context = event_case(case, raw)
    value = make_guard(guard, context, seed=True)
    value.before_dispatch()
    value.observe(guard.strict_json(raw))
    result = _completed(context, value, raw)
    assert result['checked'] is result['complete'] is result['passed'] is True
    assert result['observed_rate_limit_events'] == 1
    assert result['transcript'] == {'bytes': len(raw), 'sha256': row['sha256']}
    assert value.snapshot()['after_readings_verified'] is False


@pytest.mark.parametrize('mutation', [
    'overage_allowed', 'overage_unknown', 'overage_null', 'reason_unknown', 'reason_without_status',
    'using_overage', 'missing_overage_flag', 'alias_missing_nested', 'alias_missing_reset',
    'alias_conflicting_reset', 'alias_boolean_reset', 'alias_status_conflict', 'nested_overage',
    'nested_missing_utilization', 'nested_boolean_utilization', 'nested_exhausted',
    'nested_negative', 'nested_unknown_field', 'unknown_top_field'])
def test_real_alias_shape_remains_fail_closed_at_admission_delivery_and_replay(case, mutation):
    source = _representative('allowed')
    raw = source['raw_json'].encode()
    context = event_case(case, raw)
    event = deepcopy(guard.strict_json(raw))
    info = event['rate_limit_info']
    name = info['rateLimitType']
    nested = info['unifiedWindows'][name]
    if mutation == 'overage_allowed': info['overageStatus'] = 'allowed'
    elif mutation == 'overage_unknown': info['overageStatus'] = 'unknown'
    elif mutation == 'overage_null': info['overageStatus'] = None
    elif mutation == 'reason_unknown': info['overageDisabledReason'] = 'unrecognized'
    elif mutation == 'reason_without_status': del info['overageStatus']
    elif mutation == 'using_overage': info['isUsingOverage'] = True
    elif mutation == 'missing_overage_flag': del info['isUsingOverage']
    elif mutation == 'alias_missing_nested': del info['unifiedWindows'][name]
    elif mutation == 'alias_missing_reset': del info['resetsAt']
    elif mutation == 'alias_conflicting_reset': info['resetsAt'] += 1
    elif mutation == 'alias_boolean_reset': info['resetsAt'] = True
    elif mutation == 'alias_status_conflict': nested['status'] = 'allowed_warning'
    elif mutation == 'nested_overage': nested['isUsingOverage'] = True
    elif mutation == 'nested_missing_utilization': del nested['utilization']
    elif mutation == 'nested_boolean_utilization': nested['utilization'] = False
    elif mutation == 'nested_exhausted': nested['utilization'] = 1
    elif mutation == 'nested_negative': nested['utilization'] = -0.1
    elif mutation == 'nested_unknown_field': nested['unexpected'] = False
    else: info['unexpected'] = False
    changed = guard.canonical(event)
    with pytest.raises(ValueError):
        _prepare(context, changed)
    value = make_guard(guard, context, seed=True)
    value.before_dispatch()
    with pytest.raises(ValueError):
        value.observe(event)
    assert value.stop_reason and value.observed_events == 1
    with pytest.raises(ValueError):
        _completed(context, value, changed + b'\n')
    assert source['raw_json'].encode() == raw


def test_alias_pointer_preserves_zero_and_still_requires_both_admission_windows(case):
    raw = _representative('allowed')['raw_json'].encode()
    context = event_case(case, raw)
    event = guard.strict_json(raw)
    info = event['rate_limit_info']
    assert 'utilization' not in info
    info['unifiedWindows'][info['rateLimitType']]['utilization'] = 0
    assert guard.window_readings(event)['five_hour']['utilization'] == 0
    _prepare(context, guard.canonical(event))
    del info['unifiedWindows']['seven_day']
    with pytest.raises(ValueError, match='no seven_day window'):
        _prepare(context, guard.canonical(event))
