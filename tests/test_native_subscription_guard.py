"""Offline subscription observations are bound evidence, never quota/auth probes."""
from copy import deepcopy
from datetime import datetime, timezone

import pytest

from data_sheets_schema import native_subscription_guard as guard


@pytest.fixture
def case():
    now = 1_800_000_000
    runtime = {'auth': {'loggedIn': True, 'authMethod': 'claude.ai',
        'apiProvider': 'firstParty', 'expected_api_key_source': 'none'}}
    event = {'type': 'rate_limit_event', 'rate_limit_info': {
        'status': 'allowed', 'isUsingOverage': False, 'rateLimitType': 'seven_day',
        'utilization': 0.2, 'resetsAt': now + 3600}}
    event_raw = guard.canonical(event)
    registration_raw, launch_raw = b'exact v2 outer registration', b'exact owner launch evidence'
    document = {'kind': guard.KIND, 'version': guard.VERSION,
        'registration_sha256': guard.sha(registration_raw),
        'runtime_sha256': guard.sha(guard.canonical(runtime)),
        'launch_word_sha256': guard.sha(launch_raw),
        'max_starting_weekly_utilization': 0.5, 'max_age_seconds': 60,
        'captured_at': datetime.fromtimestamp(now, timezone.utc).isoformat().replace('+00:00', 'Z'),
        'event_json': event_raw.decode(), 'event_sha256': guard.sha(event_raw)}
    return document, runtime, registration_raw, launch_raw, now


def build(case, *, document=None, now=None):
    doc, runtime, registration, launch, clock = case
    raw = guard.canonical(doc if document is None else document)
    return guard.SubscriptionGuard(raw, expected_sha256=guard.sha(raw),
        registration_raw=registration, runtime=runtime, launch_word_raw=launch,
        clock=lambda: clock if now is None else now)


def test_exact_bound_observation_dispatch_once_and_saved_readback(case):
    value = build(case)
    assert value.dispatched is False
    value.before_dispatch()
    assert value.snapshot()['dispatched'] is True
    with pytest.raises(ValueError, match='already consumed'):
        value.before_dispatch()
    _, runtime, registration, launch, _ = case
    replay = guard.validate_saved_snapshot(value.raw, value.snapshot(),
        registration_raw=registration, runtime=runtime, launch_word_raw=launch)
    assert replay.snapshot() == value.snapshot()
    assert 'not authenticated' in replay.snapshot()['basis']


@pytest.mark.parametrize('key,value', [('version', True), ('max_age_seconds', True),
    ('max_age_seconds', 301), ('max_starting_weekly_utilization', True),
    ('max_starting_weekly_utilization', float('inf')), ('extra', 'not permitted'),
    ('registration_sha256', '0' * 64), ('runtime_sha256', '0' * 64),
    ('launch_word_sha256', '0' * 64), ('event_sha256', '0' * 64)])
def test_rehashed_wrong_or_ambiguous_evidence_refuses(case, key, value):
    doc = deepcopy(case[0]); doc[key] = value
    with pytest.raises(ValueError):
        build(case, document=doc)


@pytest.mark.parametrize('offset', [-1, 61, 4000])
def test_future_stale_and_reset_observations_refuse(case, offset):
    with pytest.raises(ValueError):
        build(case, now=case[-1] + offset)


@pytest.mark.parametrize('change', ['overage', 'unknown', 'exhausted', 'missing_flag',
    'missing_weekly', 'contradictory_alias', 'bool_utilization', 'bool_reset'])
def test_rehashed_unsafe_native_reading_refuses(case, change):
    doc = deepcopy(case[0]); event = guard.strict_json(doc['event_json'])
    info = event['rate_limit_info']
    if change == 'overage': info['isUsingOverage'] = True
    elif change == 'unknown': info['status'] = 'unknown'
    elif change == 'exhausted': info['utilization'] = 1
    elif change == 'missing_flag': del info['isUsingOverage']
    elif change == 'missing_weekly': info['rateLimitType'] = 'five_hour'
    elif change == 'contradictory_alias':
        info['unifiedWindows'] = {'seven_day': {'utilization': 0.3, 'resetsAt': info['resetsAt']}}
    elif change == 'bool_utilization': info['utilization'] = False
    else: info['resetsAt'] = True
    raw = guard.canonical(event)
    doc.update(event_json=raw.decode(), event_sha256=guard.sha(raw))
    with pytest.raises(ValueError):
        build(case, document=doc)


def test_live_events_stop_unsafe_state_without_reaging_normal_utilization(case):
    value = build(case); value.before_dispatch()
    event = guard.strict_json(case[0]['event_json'])
    event['rate_limit_info']['utilization'] = 0.8
    value.observe(event)
    assert value.stop_reason is None and value.observed_events == 1
    event['rate_limit_info']['isUsingOverage'] = True
    with pytest.raises(ValueError, match='overage'):
        value.observe(event)
    assert value.stop_reason and value.observed_events == 2


def test_dispatch_rereads_exact_file_and_refuses_replacement(case, tmp_path):
    value = build(case)
    path = tmp_path.resolve() / 'guard.json'; path.write_bytes(value.raw)
    value.path = path
    value.before_dispatch(check_only=True)
    path.write_bytes(value.raw + b'\n')
    with pytest.raises(ValueError, match='changed'):
        value.before_dispatch()
    assert not value.dispatched


@pytest.mark.parametrize('change', ['dispatch_bool', 'count_bool', 'changed_count', 'extra'])
def test_saved_snapshot_cannot_add_unbound_claims(case, change):
    value = build(case); snapshot = value.snapshot()
    if change == 'dispatch_bool': snapshot['dispatched'] = 1
    elif change == 'count_bool': snapshot['observed_rate_limit_events'] = False
    elif change == 'changed_count': snapshot['maximum_starting_utilization'] = 1
    else: snapshot['accepted'] = True
    _, runtime, registration, launch, _ = case
    with pytest.raises(ValueError):
        guard.validate_saved_snapshot(value.raw, snapshot, registration_raw=registration,
            runtime=runtime, launch_word_raw=launch)


def _saved_observations(case, value, transcript, *, snapshot=None, complete=True):
    _, runtime, registration, launch, _ = case
    return guard.validate_saved_observations(value.raw, value.snapshot() if snapshot is None else snapshot,
        registration_raw=registration, runtime=runtime, launch_word_raw=launch,
        transcript_raw=transcript, complete=complete)


def test_completed_subscription_state_replays_exact_ordered_events_without_reaging(case):
    value = build(case)
    value.before_dispatch()
    event = guard.strict_json(case[0]['event_json'])
    value.observe(event)
    transcript = guard.canonical({'type': 'system', 'subtype': 'init'}) + b'\n' + guard.canonical(event) + b'\n'
    result = _saved_observations(case, value, transcript)
    assert result['checked'] is result['complete'] is result['passed'] is True
    assert result['observed_rate_limit_events'] == 1
    assert result['transcript'] == {'bytes': len(transcript), 'sha256': guard.sha(transcript)}


@pytest.mark.parametrize('mutation', ['count', 'stop', 'unsafe_before_safe', 'incomplete_line', 'not_dispatched'])
def test_completed_snapshot_cannot_replace_actual_subscription_events(case, mutation):
    value = build(case)
    value.before_dispatch()
    event = guard.strict_json(case[0]['event_json'])
    value.observe(event)
    snapshot = value.snapshot()
    transcript = guard.canonical(event) + b'\n'
    if mutation == 'count':
        snapshot['observed_rate_limit_events'] += 1
    elif mutation == 'stop':
        snapshot['stop_reason'] = 'fabricated cleared lifecycle stop'
    elif mutation == 'unsafe_before_safe':
        unsafe = deepcopy(event)
        unsafe['rate_limit_info']['isUsingOverage'] = True
        transcript = guard.canonical(unsafe) + b'\n' + transcript
        snapshot['observed_rate_limit_events'] = 2
    elif mutation == 'incomplete_line':
        transcript = transcript[:-1]
    else:
        snapshot['dispatched'] = False
    with pytest.raises(ValueError):
        _saved_observations(case, value, transcript, snapshot=snapshot)


def test_failed_buffered_suffix_is_explicitly_not_an_observed_prefix(case):
    value = build(case)
    value.before_dispatch()
    event = guard.strict_json(case[0]['event_json'])
    event['rate_limit_info']['isUsingOverage'] = True
    # No call to observe: these bytes model a suffix written by the transport
    # but never delivered to the guard after an unrelated controller failure.
    result = _saved_observations(case, value, guard.canonical(event) + b'\n', complete=False)
    assert result['checked'] is result['complete'] is result['passed'] is False
    assert 'not independently verified' in result['basis']
    assert 'observed_rate_limit_events' not in result
