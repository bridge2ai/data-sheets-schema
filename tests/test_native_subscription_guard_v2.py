"""U4b quota observations and raw-bundle joins, all invented offline evidence.

No native executable, account, provider, socket, process or actual launch is
used. The real owner-term/bundle parser and guard bodies perform every check.
"""
from copy import deepcopy
from datetime import datetime, timezone

import pytest

from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_guard_v2 as guard
from tests.utils.native_u4b_fixtures import bundle_for


def timestamp(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace('+00:00', 'Z')


@pytest.fixture
def case(tmp_path):
    now = 1_800_000_000
    runtime = {'auth': {'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
                       'expected_api_key_source': 'none'},
               'model': 'claude-opus-5[1m]', 'environment': {'CLAUDE_CODE_DISABLE_1M_CONTEXT': '0'},
               'budget_guard_usd': '90', 'deadline_seconds': 900,
               'keep_awake': {'policy': 'not_applicable', 'host_platform': 'linux',
                             'basis': 'Invented guard component fixture; no host assertion.'}}
    value = {'attempt_id': 'invented-guard-component', 'runtime': runtime,
        'dependencies': {'base': {'source_commit': 'a' * 40}}, 'permission_probe_sha256': 'b' * 64}
    registration = guard.canonical({'authority_version': 2, 'controller_sources_sha256': 'f' * 64,
                                    'registration': value})
    bundle, word = bundle_for(registration, tmp_path.resolve() / 'unused-capture', timestamp(now - 10))
    owner = review.validate_bundle(registration, bundle, word)
    event = {'type': 'rate_limit_event', 'rate_limit_info': {
        'status': 'allowed', 'isUsingOverage': False, 'unifiedWindows': {
            'five_hour': {'utilization': 0.2, 'resetsAt': now + 3600},
            'seven_day': {'utilization': 0.3, 'resetsAt': now + 86400}}}}
    raw = guard.prepare_guard(registration_raw=registration, runtime=runtime, launch_word_raw=word,
        owner_statement=owner, event_raw=guard.canonical(event), captured_at=timestamp(now),
        maximum_starting_utilization=owner['max_starting_weekly_utilization'],
        max_age_seconds=owner['max_age_seconds'], clock=lambda: now)
    return {'now': now, 'runtime': runtime, 'registration': registration, 'bundle': bundle,
            'word': word, 'owner': owner, 'event': event, 'raw': raw, 'document': guard.strict_json(raw)}


def build(case, *, document=None, runtime=None, word=None, owner=None, now=None, fresh=True):
    raw = guard.canonical(case['document'] if document is None else document)
    return guard.SubscriptionGuard(raw, expected_sha256=guard.sha(raw), registration_raw=case['registration'],
        runtime=case['runtime'] if runtime is None else runtime, launch_word_raw=case['word'] if word is None else word,
        owner_statement=case['owner'] if owner is None else owner,
        clock=lambda: case['now'] if now is None else now, check_freshness=fresh)


def event_document(case, event):
    raw = guard.canonical(event)
    return {**case['document'], 'event_json': raw.decode(), 'event_sha256': guard.sha(raw)}


def saved(case, value, transcript, *, snapshot=None, complete=True):
    return guard.validate_saved_observations(value.raw, value.snapshot() if snapshot is None else snapshot,
        registration_raw=case['registration'], runtime=case['runtime'], launch_word_raw=case['word'],
        owner_statement=case['owner'], transcript_raw=transcript, complete=complete)


def test_both_windows_exact_binding_and_single_dispatch(case):
    value = build(case)
    snapshot = value.snapshot()
    assert snapshot['version'] == 2 and snapshot['weekly']['utilization'] == 0.3
    assert snapshot['five_hour']['utilization'] == 0.2
    assert snapshot['authorized_at'] == timestamp(case['now'] - 10)
    assert snapshot['owner_statement_sha256'] == guard.sha(guard.canonical(case['owner']))
    assert snapshot['observed_windows'] == {
        name: {'count': 0, 'first': None, 'last': None, 'highest': None} for name in guard.WINDOWS}
    value.before_dispatch()
    assert value.dispatched
    with pytest.raises(ValueError, match='already consumed'):
        value.before_dispatch()
    assert 'not authenticated' in value.snapshot()['basis']


@pytest.mark.parametrize('window', ['five_hour', 'seven_day'])
@pytest.mark.parametrize('change', ['missing', 'rejected', 'unknown_status', 'exhausted', 'overage',
                                  'null', 'bool_utilization', 'bool_reset', 'negative_reset', 'unknown_property'])
def test_every_admission_window_refuses_unsafe_nested_row_under_allowed_top(case, window, change):
    event = deepcopy(case['event'])
    windows = event['rate_limit_info']['unifiedWindows']
    if change == 'missing':
        del windows[window]
    elif change == 'null':
        windows[window] = None
    else:
        key, value = {'rejected': ('status', 'rejected'), 'unknown_status': ('status', 'unexpected'),
            'exhausted': ('utilization', 1), 'overage': ('isUsingOverage', True),
            'bool_utilization': ('utilization', False), 'bool_reset': ('resetsAt', True),
            'negative_reset': ('resetsAt', -1), 'unknown_property': ('other_window', {})}[change]
        windows[window][key] = value
    assert event['rate_limit_info']['status'] == 'allowed'
    with pytest.raises(ValueError):
        build(case, document=event_document(case, event))


@pytest.mark.parametrize('change', ['top_rejected', 'top_unknown', 'top_overage', 'missing_overage',
                                  'unknown_window', 'unknown_top_window', 'malformed_windows', 'orphan_reading'])
def test_unknown_or_top_level_unsafe_observation_never_becomes_safe(case, change):
    event = deepcopy(case['event']); info = event['rate_limit_info']
    if change == 'top_rejected': info['status'] = 'rejected'
    elif change == 'top_unknown': info['status'] = 'pending'
    elif change == 'top_overage': info['isUsingOverage'] = True
    elif change == 'missing_overage': del info['isUsingOverage']
    elif change == 'unknown_window':
        info['unifiedWindows']['fortnight'] = {**info['unifiedWindows']['seven_day'], 'utilization': False}
    elif change == 'unknown_top_window':
        info.update(rateLimitType='fortnight', utilization=-0.1, resetsAt=case['now'] + 3000)
    elif change == 'malformed_windows': info['unifiedWindows'] = []
    else: info['utilization'] = 0.1
    with pytest.raises(ValueError):
        build(case, document=event_document(case, event))


@pytest.mark.parametrize('window', ['five_hour', 'seven_day'])
@pytest.mark.parametrize('mutation', ['none', 'utilization', 'resetsAt', 'status', 'isUsingOverage'])
def test_top_and_nested_window_aliases_must_agree(case, window, mutation):
    event = deepcopy(case['event']); info = event['rate_limit_info']
    info.update(rateLimitType=window, **info['unifiedWindows'][window])
    if mutation == 'none':
        assert build(case, document=event_document(case, event)).snapshot()['five_hour']['utilization'] == 0.2
        return
    info['unifiedWindows'][window][mutation] = {
        'utilization': 0.4, 'resetsAt': case['now'] + 5000,
        'status': 'allowed_warning', 'isUsingOverage': True}[mutation]
    with pytest.raises(ValueError, match='aliases conflict'):
        build(case, document=event_document(case, event))


@pytest.mark.parametrize('captured_delta,dispatch_delta,passes', [(-11, 0, False), (-10, 0, True),
                                                              (0, 120, True), (0, 121, False), (1, 0, False)])
def test_word_capture_and_actual_dispatch_chronology(case, captured_delta, dispatch_delta, passes):
    document = {**case['document'], 'captured_at': timestamp(case['now'] + captured_delta)}
    if passes:
        build(case, document=document, now=case['now'] + dispatch_delta).before_dispatch()
    else:
        with pytest.raises(ValueError):
            build(case, document=document, now=case['now'] + dispatch_delta)


@pytest.mark.parametrize('value', ['yesterday', '2026-11-08', '2026-11-08T00:00:00+00:00', None, True,
                                 '2026-13-08T00:00:00Z'])
def test_guard_independently_parses_word_timestamp_even_when_hash_rebound(case, value):
    word = guard.strict_json(case['word']); word['authorized_at'] = value
    raw = guard.canonical(word)
    with pytest.raises(ValueError, match='authorized_at'):
        build(case, word=raw, document={**case['document'], 'launch_word_sha256': guard.sha(raw)})


@pytest.mark.parametrize('window', ['five_hour', 'seven_day'])
@pytest.mark.parametrize('reset_delta,dispatch_delta', [(0, 0), (1, 1)])
def test_each_window_reset_must_follow_capture_and_actual_dispatch(case, window, reset_delta, dispatch_delta):
    event = deepcopy(case['event'])
    event['rate_limit_info']['unifiedWindows'][window]['resetsAt'] = case['now'] + reset_delta
    with pytest.raises(ValueError, match='reset'):
        build(case, document=event_document(case, event), now=case['now'] + dispatch_delta)


def test_duplicate_word_timestamp_cannot_choose_an_earlier_authorization(case):
    raw = case['word'][:-1] + b',"authorized_at":"2020-01-01T00:00:00Z"}'
    with pytest.raises(ValueError, match='duplicate'):
        build(case, word=raw, document={**case['document'], 'launch_word_sha256': guard.sha(raw)})


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -0.1, 1.1])
def test_nonfinite_and_out_of_range_live_readings_fail_closed(case, bad):
    value = build(case); value.before_dispatch()
    event = deepcopy(case['event'])
    event['rate_limit_info']['unifiedWindows']['five_hour']['utilization'] = bad
    with pytest.raises(ValueError):
        value.observe(event)
    assert value.stop_reason is not None and value.observed_events == 1


def test_allowed_warning_and_single_known_live_window_are_explicitly_supported(case):
    value = build(case); value.before_dispatch()
    event = {'type': 'rate_limit_event', 'rate_limit_info': {'status': 'allowed_warning',
        'isUsingOverage': False, 'rateLimitType': 'five_hour',
        'utilization': 0.8, 'resetsAt': case['now'] + 3000}}
    value.observe(event)
    snapshot = value.snapshot()
    assert snapshot['observed_windows']['five_hour']['count'] == 1
    assert snapshot['observed_windows']['seven_day']['first'] is None
    assert saved(case, value, guard.canonical(event) + b'\n')['passed'] is True


@pytest.mark.parametrize('key,value', [('version', True), ('word', 'AUTHORIZED'), ('extra', 'not allowed'),
                                     ('registration_sha256', '0' * 64), ('owner', 'different owner')])
def test_rehashed_word_cannot_relax_closed_protocol_or_owner_binding(case, key, value):
    word = guard.strict_json(case['word']); word[key] = value
    raw = guard.canonical(word)
    with pytest.raises(ValueError):
        build(case, word=raw, document={**case['document'], 'launch_word_sha256': guard.sha(raw)})


@pytest.mark.parametrize('key,value', [('version', 1), ('version', True), ('max_age_seconds', True),
    ('max_age_seconds', 121), ('max_age_seconds', 301), ('max_starting_weekly_utilization', 0.8),
    ('max_starting_weekly_utilization', True), ('owner_statement_sha256', '0' * 64), ('extra', 1)])
def test_rehashed_guard_cannot_choose_weaker_terms_or_other_version(case, key, value):
    with pytest.raises(ValueError):
        build(case, document={**case['document'], key: value})


@pytest.mark.parametrize('change', ['budget_string', 'budget_number', 'deadline', 'awake', 'context', 'model', 'auth'])
def test_rehashed_runtime_must_still_equal_the_owner_terms(case, change):
    runtime = deepcopy(case['runtime'])
    if change == 'budget_string': runtime['budget_guard_usd'] = '91'
    elif change == 'budget_number': runtime['budget_guard_usd'] = 90
    elif change == 'deadline': runtime['deadline_seconds'] += 1
    elif change == 'awake': runtime['keep_awake']['basis'] = 'changed'
    elif change == 'context': runtime['environment']['CLAUDE_CODE_DISABLE_1M_CONTEXT'] = '1'
    elif change == 'model': runtime['model'] = 'claude-opus-5'
    else: runtime['auth']['expected_api_key_source'] = 'provider-key'
    document = {**case['document'], 'runtime_sha256': guard.sha(guard.canonical(runtime))}
    with pytest.raises(ValueError):
        build(case, runtime=runtime, document=document)


def test_public_values_do_not_mutate_admission_or_lifecycle(case):
    value = build(case)
    value.value['max_age_seconds'] = 300
    value.reading['utilization'] = 0
    value.owner_statement['budget_guard_usd'] = '900'
    value.snapshot()['observed_windows']['seven_day']['count'] = 99
    assert value.max_age == 120 and value.reading['utilization'] == 0.3
    assert value.owner_statement['budget_guard_usd'] == '90' and value.observed_events == 0
    for attribute, replacement in [('raw', b'new'), ('maximum', 1), ('dispatched', True), ('stop_reason', None)]:
        with pytest.raises(AttributeError):
            setattr(value, attribute, replacement)


def test_guard_file_rechecked_at_dispatch_and_saved_binding(case, tmp_path):
    path = tmp_path.resolve() / 'guard.json'; path.write_bytes(case['raw'])
    word = tmp_path.resolve() / 'word.json'; word.write_bytes(case['word'])
    value = guard.load_guard(path, guard.sha(case['raw']), registration_raw=case['registration'],
        runtime=case['runtime'], launch_word_path=word, owner_statement=case['owner'], clock=lambda: case['now'])
    path.write_bytes(case['raw'] + b'\n')
    with pytest.raises(ValueError, match='changed before dispatch'):
        value.before_dispatch()
    assert not value.dispatched


def test_live_nested_stop_keeps_first_reason_and_observed_extrema(case):
    value = build(case); value.before_dispatch()
    unsafe = deepcopy(case['event']); unsafe['rate_limit_info']['unifiedWindows']['five_hour']['utilization'] = 1
    with pytest.raises(ValueError, match='five_hour.*exhausted'):
        value.observe(unsafe)
    first_stop = value.stop_reason
    later = deepcopy(case['event']); later['rate_limit_info']['isUsingOverage'] = True
    with pytest.raises(ValueError) as error:
        value.observe(later)
    assert str(error.value) == value.stop_reason == first_stop
    with pytest.raises(ValueError, match='five_hour.*exhausted'):
        value.observe(case['event'])
    snapshot = value.snapshot()
    assert snapshot['observed_rate_limit_events'] == 3
    assert snapshot['observed_windows']['five_hour']['highest']['utilization'] == 1
    assert snapshot['observed_windows']['five_hour']['highest']['event_index'] == 1
    assert snapshot['observed_windows']['five_hour']['last']['event_index'] == 3


@pytest.mark.parametrize('window', ['five_hour', 'seven_day'])
def test_live_exhaustion_and_unsafe_unknown_windows_stop_even_with_allowed_top(case, window):
    value = build(case); value.before_dispatch()
    event = deepcopy(case['event'])
    event['rate_limit_info']['unifiedWindows'][window]['status'] = 'rejected'
    with pytest.raises(ValueError, match=window):
        value.observe(event)
    assert value.stop_reason and value.observed_events == 1
    unknown = deepcopy(case['event'])
    unknown['rate_limit_info']['unifiedWindows']['unrecognized'] = {
        'utilization': 1, 'resetsAt': case['now'] + 3600}
    fresh = build(case); fresh.before_dispatch()
    with pytest.raises(ValueError, match='unrecognized.*exhausted'):
        fresh.observe(unknown)


def test_early_observation_cannot_enable_dispatch(case):
    value = build(case)
    with pytest.raises(ValueError, match='before dispatch'):
        value.observe(case['event'])
    with pytest.raises(ValueError, match='before dispatch'):
        value.before_dispatch()
    assert not value.dispatched and value.observed_events == 1


def observed_pair(case):
    value = build(case); value.before_dispatch()
    first = deepcopy(case['event'])
    first['rate_limit_info']['unifiedWindows']['five_hour']['utilization'] = 0.9
    first['rate_limit_info']['unifiedWindows']['seven_day']['utilization'] = 0.8
    last = deepcopy(case['event'])
    for row in last['rate_limit_info']['unifiedWindows'].values():
        row['resetsAt'] += 86400
        row['utilization'] = 0.1
    # A legitimate rise above the starting maximum is not a mid-run refusal.
    value.observe(first); value.observe(last)
    transcript = (guard.canonical({'type': 'system', 'subtype': 'init'}) + b'\n'
                  + guard.canonical(first) + b'\n' + guard.canonical(last) + b'\n')
    return value, transcript


def test_complete_ordered_readback_preserves_reset_pairing_and_extrema(case):
    value, transcript = observed_pair(case)
    result = saved(case, value, transcript)
    assert result['checked'] is result['complete'] is result['passed'] is True
    assert result['observed_rate_limit_events'] == 2
    for name, row in result['observed_windows'].items():
        assert row['count'] == 2 and row['first'] == row['highest']
        assert row['last']['utilization'] == 0.1 and row['last']['event_index'] == 2
        assert row['last']['resets_at'] == row['highest']['resets_at'] + 86400
    assert result['transcript'] == {'bytes': len(transcript), 'sha256': guard.sha(transcript)}


@pytest.mark.parametrize('mutation', ['count', 'highest', 'last', 'first', 'window_count', 'stop',
    'dispatched', 'static_boolean', 'unknown_field', 'transcript_order', 'unsafe_prefix', 'truncated', 'duplicate_key'])
def test_saved_readback_refuses_rehashed_snapshot_or_transcript_mutations(case, mutation):
    value, transcript = observed_pair(case)
    snapshot = value.snapshot()
    row = snapshot['observed_windows']['five_hour']
    if mutation == 'count': snapshot['observed_rate_limit_events'] += 1
    elif mutation == 'highest': row['highest']['utilization'] = 0.95
    elif mutation == 'last': row['last']['resets_at'] += 1
    elif mutation == 'first': row['first']['status'] = 'allowed_warning'
    elif mutation == 'window_count': row['count'] = 1
    elif mutation == 'stop': snapshot['stop_reason'] = 'invented refusal'
    elif mutation == 'dispatched': snapshot['dispatched'] = False
    elif mutation == 'static_boolean': snapshot['version'] = True
    elif mutation == 'unknown_field': snapshot['accepted'] = True
    elif mutation == 'transcript_order':
        lines = transcript.splitlines(keepends=True)
        transcript = lines[0] + lines[2] + lines[1]
    elif mutation == 'unsafe_prefix':
        unsafe = deepcopy(case['event']); unsafe['rate_limit_info']['unifiedWindows']['five_hour']['status'] = 'rejected'
        transcript = guard.canonical(unsafe) + b'\n' + transcript
    elif mutation == 'duplicate_key':
        transcript = b'{"type":"system","type":"rate_limit_event"}\n' + transcript
    else: transcript = transcript[:-1]
    with pytest.raises(ValueError):
        saved(case, value, transcript, snapshot=snapshot)


def test_incomplete_delivery_never_authenticates_buffered_after_readings(case):
    value = build(case); value.before_dispatch()
    unsafe = deepcopy(case['event']); unsafe['rate_limit_info']['unifiedWindows']['five_hour']['utilization'] = 1
    transcript = guard.canonical(unsafe) + b'\n' + guard.canonical(case['event']) + b'\n'
    result = saved(case, value, transcript, complete=False)
    assert result['checked'] is result['complete'] is result['passed'] is False
    assert value.observed_events == 0
    diagnostic = result['transcript_diagnostic']
    assert diagnostic['observed_rate_limit_events'] == 2
    assert diagnostic['observed_windows']['five_hour']['highest']['utilization'] == 1
    assert 'not proof of delivered' in diagnostic['basis']
    assert diagnostic['first_stop'] == 'five_hour subscription window is exhausted'
    assert 'observed_rate_limit_events' not in result
    assert saved(case, value, None, complete=False)['transcript_diagnostic'] is None
    broken = saved(case, value, b'broken', complete=False)
    assert broken['passed'] is False and broken['transcript_diagnostic']['complete'] is False


def test_no_after_observations_are_unavailable_readings_not_zero_utilization(case):
    value = build(case); value.before_dispatch()
    result = saved(case, value, b'{"type":"system","subtype":"init"}\n')
    assert result['observed_rate_limit_events'] == 0
    assert all(row['first'] is row['last'] is row['highest'] is None for row in result['observed_windows'].values())


def test_huge_json_integer_retains_named_stop(case):
    value = build(case); value.before_dispatch()
    event = deepcopy(case['event'])
    event['rate_limit_info']['unifiedWindows']['five_hour']['utilization'] = 10 ** 400
    with pytest.raises(ValueError, match='finite fraction'):
        value.observe(event)
    assert 'finite fraction' in value.stop_reason
    assert value.observed_events == 1


def test_file_descriptor_closed_if_initial_fstat_fails(tmp_path, monkeypatch):
    path = tmp_path.resolve() / 'evidence.json'; path.write_bytes(b'{}')
    closed = []
    original_close = guard.os.close
    def close(fd):
        closed.append(fd); original_close(fd)
    def fail(fd):
        raise OSError('injected fstat failure')
    with monkeypatch.context() as patch:
        patch.setattr(guard.os, 'close', close)
        patch.setattr(guard.os, 'fstat', fail)
        with pytest.raises(OSError, match='injected fstat'):
            guard.read_regular(path)
    assert len(closed) == 1
