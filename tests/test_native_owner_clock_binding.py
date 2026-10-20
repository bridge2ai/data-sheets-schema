"""Private clock binding with an invented backend; no kernel/provider campaign."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import threading
import time
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_clock_domain_v1 as clocks
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_owner_runner_v1 as runner
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_owner_control import Host, control_graph
from tests.test_native_owner_runner import (
    SYNTHETIC_CLOCK, fixed_clock, runner_case, selected_controls,
)


def saved_owner():
    """Actual current role pins, deliberately nonexistent captured stream paths."""
    return {'format': 'native_stream_owner_v2', 'coordination_profile': profile.source_profile(1),
        'execution_sha256': '1' * 64, 'started_sha256': '2' * 64,
        'owner_pid': 123, 'clock': 'monotonic_ns', 'start_ns': 100,
        'deadline_ns': 200, 'duration_ns': 100,
        'transcript': {'path': '/retained/software-fixture/transcript.jsonl', 'device': 1, 'inode': 2},
        'control': {'path': '/retained/software-fixture/control.jsonl', 'device': 1, 'inode': 3},
        'clock_domain': deepcopy(SYNTHETIC_CLOCK)}


def test_saved_v2_returns_detached_complete_claims():
    value = saved_owner()
    expected = deepcopy(value)
    parsed = runner.validate_owner_record_v2(value)
    assert parsed == expected and parsed is not value
    value['clock_domain']['timebase']['numerator'] = 7
    value['coordination_profile']['implementations'].clear()
    assert parsed == expected
    parsed['transcript']['path'] = '/invented/change'
    assert runner.validate_owner_record_v2(expected) == expected


def test_bound_budget_keeps_immutable_detached_domain(fixed_clock):
    original = deepcopy(fixed_clock)
    budget = coordination.ReaderBudget(time.monotonic_ns() + 30_000_000_000,
        (threading.Event(),), clock_domain=original)
    original['timebase']['numerator'] = 9
    returned = budget.clock_domain()
    returned['timebase']['numerator'] = 11
    assert budget.clock_domain() == fixed_clock
    with pytest.raises(FrozenInstanceError):
        budget.deadline_ns += 1
    with coordination.reader_budget(budget):
        assert budget.remaining() > 0
        assert coordination.current_reader_budget() is budget
    assert coordination.current_reader_budget() is None


def test_unbound_component_budget_performs_no_clock_acquisition(monkeypatch):
    def forbidden():
        pytest.fail('component-only unbound budget must not claim a clock lease')
    monkeypatch.setattr(clocks, 'capture_domain', forbidden)
    budget = coordination.ReaderBudget(time.monotonic_ns() + 30_000_000_000, (threading.Event(),))
    assert budget.clock_domain() is None and budget.remaining() > 0
    with coordination.reader_budget(budget):
        assert budget.remaining() > 0
    budget.cleanup_guard().require_current()


def test_borrowed_parent_scope_never_closes_its_lease(fixed_clock):
    budget = coordination.ReaderBudget(time.monotonic_ns() + 30_000_000_000,
        (threading.Event(),), clock_domain=fixed_clock)
    parent = clocks.capture_domain()
    try:
        with coordination.reader_budget(budget, clock_lease=parent) as scope:
            assert budget.remaining() > 0
            assert scope.close_error is None
        assert not parent._closed
        parent.require_current(fixed_clock)
    finally:
        parent.close()
    assert parent._closed


def test_cleanup_guard_checks_domain_after_admission_stop_without_renewing_budget(fixed_clock):
    stop = threading.Event()
    budget = coordination.ReaderBudget(time.monotonic_ns() + 30_000_000_000,
        (stop,), clock_domain=fixed_clock)
    deadline = budget.deadline_ns
    with coordination.reader_budget(budget):
        guard = budget.cleanup_guard()
        stop.set()
        with pytest.raises(ValueError, match='stopped'):
            budget.remaining()
        guard.require_current()
        assert budget.deadline_ns == deadline
    with pytest.raises(ValueError, match='inactive'):
        guard.require_current()


def test_actual_runner_parent_and_worker_leases_are_thread_owned_and_closed(runner_case, monkeypatch):
    case = runner_case
    capture = clocks.capture_domain
    leases, observed = [], []
    lock = threading.Lock()
    parent_thread = threading.current_thread()

    def tracked_capture():
        lease = capture()
        with lock:
            leases.append((threading.current_thread(), lease))
        return lease

    def observer(event):
        budget = coordination.current_reader_budget()
        assert budget is not None and budget.clock_domain() == SYNTHETIC_CLOCK
        assert budget.remaining() > 0
        observed.append((threading.current_thread(), event['type']))

    monkeypatch.setattr(clocks, 'capture_domain', tracked_capture)
    case['kwargs']['event_observer'] = observer
    assert case['runner'].execute_child(**case['kwargs']) == 0
    owner = json.loads(case['runner'].owner_raw())
    assert runner.validate_owner_record_v2(owner) == owner
    assert owner['clock_domain'] == SYNTHETIC_CLOCK
    assert observed and all(thread is not parent_thread for thread, _ in observed)
    assert any(thread is parent_thread for thread, _ in leases)
    assert any(thread is not parent_thread for thread, _ in leases)
    assert all(lease._creator_thread is thread and lease._closed for thread, lease in leases)
    assert case['runner'].report()['state'] == 'completed'
    assert case['runner'].report()['control_close']['capture_complete'] is True
    assert coordination.current_reader_budget() is None


def test_slow_parent_acquisition_consumes_original_attempt_allowance(runner_case, monkeypatch):
    case = runner_case
    clock = [1_000_000_000]
    capture = clocks.capture_domain
    leases = []
    monkeypatch.setattr(runner, 'time', SimpleNamespace(monotonic_ns=lambda: clock[0]))

    def delayed_capture():
        lease = capture()
        if not leases:
            clock[0] += case['kwargs']['deadline_seconds'] * 1_000_000_000
        leases.append(lease)
        return lease

    def forbidden(*args, **kwargs):
        pytest.fail('clock acquisition cannot renew an expired attempt')

    monkeypatch.setattr(clocks, 'capture_domain', delayed_capture)
    monkeypatch.setattr(runner, '_spawn', forbidden)
    with pytest.raises(case['controls']['budgeted_cborg'].BudgetStop, match='deadline elapsed'):
        case['runner'].execute_child(**case['kwargs'])
    assert leases and all(lease._closed for lease in leases)
    assert case['runner'].owner_raw() is None
    assert case['runner'].report()['dispatches'] == 0
    assert list(case['attempt'].iterdir()) == []


def test_real_bound_pump_classifies_with_worker_context_and_cleans_inside_parent_scope(
        tmp_path, control_graph, fixed_clock):
    seen = []

    def classify(*args):
        budget = coordination.current_reader_budget()
        assert budget.clock_domain() == fixed_clock and budget.remaining() > 0
        seen.append(threading.current_thread())
        return 'prescribed', 'invented local clock-bound classification'

    host = Host(tmp_path / 'bound', control_graph, classify=classify, initialize=False,
        owner_clock_domain=fixed_clock)
    with clocks.capture_domain() as parent:
        with coordination.reader_budget(host.channel._owner_budget, clock_lease=parent):
            try:
                host.initialize()
                host.emit(*host.frames())
                host.pump(lambda: len(host.decisions()) == 1 and not host.channel.outgoing)
                assert seen and all(thread is not threading.current_thread() for thread in seen)
                assert host.decisions()[0]['classification'] == 'prescribed'
            finally:
                host.cleanup()
            assert host.channel.close_report()['worker_shutdown_complete'] is True
        assert not parent._closed


def test_historical_three_role_profile_does_not_select_clock_bound_runner(selected_controls):
    selected = profile.source_profile(1)
    selected['implementations'].pop('clock')
    with pytest.raises(ValueError, match='selected loader scope'):
        profile.bind_runner(selected, selected_controls)
