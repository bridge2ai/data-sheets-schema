"""A5 overage reasons, 2026-11-09 (#4354): real event shapes, no account calls."""
import pytest

from data_sheets_schema import native_subscription_guard_v2 as guard
from tests.test_native_subscription_guard_v2 import case
from tests.test_native_u4b_a4_real_events import _representative, _prepare, _completed
from scripts.adhoc.native_u4b_a4_real_events_20261108 import event_case, make_guard


@pytest.mark.parametrize('reason', ['owner_disabled_extra_usage', 'x' * 256, 'é' * 128])
def test_unknown_bounded_reason_admits_observes_and_replays(case, reason):
    event = guard.strict_json(_representative('allowed')['raw_json'])
    event['rate_limit_info']['overageDisabledReason'] = reason
    raw = guard.canonical(event)
    context = event_case(case, raw)
    prepared = guard.strict_json(_prepare(context, raw))
    assert guard.strict_json(prepared['event_json'])['rate_limit_info']['overageDisabledReason'] == reason
    value = make_guard(guard, context, seed=True)
    value.before_dispatch()
    value.observe(event)
    assert value.stop_reason is None
    assert _completed(context, value, raw + b'\n')['passed'] is True


@pytest.mark.parametrize('reason', [None, False, 42, [], {}, '', ' ', 'x' * 257,
                                    'é' * 129, 'line\nbreak', 'line\rbreak', '\x00', '\ud800'])
def test_malformed_or_oversized_reason_refuses_both_routes(case, reason):
    event = guard.strict_json(_representative('allowed')['raw_json'])
    context = event_case(case, guard.canonical(event))
    event['rate_limit_info']['overageDisabledReason'] = reason
    with pytest.raises(ValueError, match='overage disabled reason'):
        _prepare(context, guard.canonical(event))
    value = make_guard(guard, context, seed=True)
    value.before_dispatch()
    with pytest.raises(ValueError, match='overage disabled reason'):
        value.observe(event)


@pytest.mark.parametrize('field', ['overageDisabledReason', 'overageStatus', 'isUsingOverage'])
def test_unknown_reason_still_requires_complete_rejected_overage_evidence(field):
    event = guard.strict_json(_representative('allowed')['raw_json'])
    event['rate_limit_info']['overageDisabledReason'] = 'owner_disabled'
    del event['rate_limit_info'][field]
    for require_both in (True, False):
        assert guard._inspect(event, require_both=require_both)[2] is not None
