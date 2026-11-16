"""Offline D156 final-clock regressions; no executable or account is used."""
from copy import deepcopy

import pytest

from data_sheets_schema import native_subscription_guard_v2 as guard
from tests.test_native_subscription_guard_v2 import case, event_document, timestamp


def ticking(case, document=None):
    clock = [case['now']]
    raw = guard.canonical(case['document'] if document is None else document)
    value = guard.SubscriptionGuard(raw, expected_sha256=guard.sha(raw),
        registration_raw=case['registration'], runtime=case['runtime'],
        launch_word_raw=case['word'], owner_statement=case['owner'],
        clock=lambda: clock[0])
    return value, clock


def test_stale_between_consumption_and_process_dispatch_cannot_retry(case):
    value, clock = ticking(case)
    value.before_dispatch()
    clock[0] += 1201
    with pytest.raises(ValueError, match='stale'):
        value.before_process_dispatch()
    clock[0] = case['now']
    with pytest.raises(ValueError, match='stale'):
        value.before_process_dispatch()
    assert value.snapshot()['dispatched_at'] == timestamp(case['now'])


def test_window_reset_between_consumption_and_process_dispatch(case):
    event = deepcopy(case['event'])
    event['rate_limit_info']['unifiedWindows']['five_hour']['resetsAt'] = case['now'] + 60
    value, clock = ticking(case, event_document(case, event))
    value.before_dispatch()
    clock[0] += 60
    with pytest.raises(ValueError, match='window reset'):
        value.before_process_dispatch()


def test_saved_observation_uses_final_boundary_timestamp(case):
    value, clock = ticking(case)
    value.before_dispatch()
    clock[0] += 50
    value.before_process_dispatch()
    snapshot = value.snapshot()
    assert snapshot['dispatched_at'] == timestamp(clock[0])
    guard.validate_saved_snapshot(value.raw, snapshot,
        registration_raw=case['registration'], runtime=case['runtime'],
        launch_word_raw=case['word'], owner_statement=case['owner'])
    with pytest.raises(ValueError, match='already attempted'):
        value.before_process_dispatch()


def test_final_boundary_rejects_mutated_memory(case):
    value, clock = ticking(case)
    value.before_dispatch()
    value._windows['five_hour']['count'] = 1
    with pytest.raises(ValueError, match='authority changed'):
        value.before_process_dispatch()


def test_final_boundary_rejects_backward_clock(case):
    value, clock = ticking(case)
    value.before_dispatch()
    clock[0] -= 1
    with pytest.raises(ValueError, match='backward'):
        value.before_process_dispatch()
