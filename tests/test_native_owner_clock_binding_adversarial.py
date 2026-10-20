"""Independent clock-bound lifetime controls with invented kernel declarations.

Actual lease/thread guards, ordinary pipes, file locks and a Python peer remain
real. The fixed OS acquisition boundary is synthetic; these tests grant neither
platform-support nor native/helper execution acceptance.
"""
from contextlib import contextmanager
from contextvars import copy_context
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_clock_domain_v1 as clocks
from data_sheets_schema import native_owner_control_v1 as control_module
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_owner_runner_v1 as runner_module
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_owner_control import Host, control_graph, shared_lock
from tests.test_native_owner_runner import fixed_clock, make_case, selected_controls


def invented_domain():
    return {'format': 'native_clock_domain_v1', 'platform': 'darwin',
        'clock': 'monotonic_ns', 'implementation': 'mach_absolute_time()',
        'boot_uuid': '12345678-1234-4234-8234-123456789abc',
        'timebase': {'numerator': 125, 'denominator': 3}}


@pytest.fixture
def clock_probe(monkeypatch, fixed_clock):
    """Preserve the real thread-affine lease while observing owning lifetimes."""
    probe = SimpleNamespace(parent=threading.current_thread(), leases=[], closes=[],
        worker_acquire_error=None, worker_close_error=None, worker_recheck_error=None,
        parent_recheck_error=None, parent_close_error=None, rechecking=threading.local())
    original_capture = clocks.capture_domain
    original_current = clocks._DomainLease.require_current
    original_close = clocks._DomainLease.close

    def capture_backend():
        if (threading.current_thread() is not probe.parent
                and not getattr(probe.rechecking, 'active', False)
                and probe.worker_acquire_error is not None):
            raise probe.worker_acquire_error
        return invented_domain(), None

    def capture():
        lease = original_capture()
        lease._fixture_temporary = getattr(probe.rechecking, 'active', False)
        lease._fixture_thread = threading.current_thread()
        if not lease._fixture_temporary:
            probe.leases.append(lease)
        return lease

    def current(self, *args, **kwargs):
        if not getattr(self, '_fixture_temporary', False):
            error = (probe.parent_recheck_error if threading.current_thread() is probe.parent
                     else probe.worker_recheck_error)
            if error is not None:
                raise error
        previous = getattr(probe.rechecking, 'active', False)
        probe.rechecking.active = True
        try:
            return original_current(self, *args, **kwargs)
        finally:
            probe.rechecking.active = previous

    def close(self):
        was_closed = self._closed
        result = original_close(self)
        if not getattr(self, '_fixture_temporary', False) and not was_closed:
            probe.closes.append((self, threading.current_thread()))
            error = (probe.parent_close_error if threading.current_thread() is probe.parent
                     else probe.worker_close_error)
            if error is not None:
                raise error
        return result

    monkeypatch.setattr(clocks, '_capture', capture_backend)
    monkeypatch.setattr(clocks, 'capture_domain', capture)
    monkeypatch.setattr(clocks._DomainLease, 'require_current', current)
    monkeypatch.setattr(clocks._DomainLease, 'close', close)
    return probe


def bound_budget(domain=None):
    return coordination.ReaderBudget(time.monotonic_ns() + 30_000_000_000,
        (threading.Event(),), clock_domain=invented_domain() if domain is None else domain)


def forbidden(*args, **kwargs):
    raise AssertionError('this refusal must precede live clock/OS effects')


@pytest.mark.parametrize('state', ['never_entered', 'exited', 'copied_expired', 'copied_reentered', 'nested_other'])
def test_bound_budget_never_silently_reverts_to_unbound_time(monkeypatch, clock_probe, state):
    budget = bound_budget()
    if state == 'never_entered':
        action = budget.remaining
        context = None
    elif state == 'nested_other':
        context = coordination.reader_budget(budget)
        context.__enter__()
        inner = coordination.reader_budget(bound_budget())
        inner.__enter__()
        action = budget.remaining
    else:
        with coordination.reader_budget(budget):
            saved = copy_context()
            assert budget.remaining() > 0
        context = coordination.reader_budget(budget) if state == 'copied_reentered' else None
        if context is not None:
            context.__enter__()
        action = budget.remaining if state == 'exited' else lambda: saved.run(budget.remaining)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(coordination, 'time', SimpleNamespace(monotonic_ns=forbidden))
            patch.setattr(clocks, 'capture_domain', forbidden)
            with pytest.raises(ValueError):
                action()
    finally:
        if state == 'nested_other':
            inner.__exit__(None, None, None)
            assert budget.remaining() > 0, 'the original live outer entry is restored'
        if context is not None:
            context.__exit__(None, None, None)


def test_binding_is_immutable_and_borrowed_lease_is_never_closed_by_budget(clock_probe):
    declaration = invented_domain()
    budget = bound_budget(declaration)
    declaration['timebase']['denominator'] = 999
    exposed = budget.clock_domain()
    exposed['boot_uuid'] = 'ffffffff-ffff-4fff-8fff-ffffffffffff'
    assert budget.clock_domain() == invented_domain()
    with clocks.capture_domain() as parent:
        with coordination.reader_budget(budget, clock_lease=parent):
            assert budget.remaining() > 0
        assert not parent._closed
        parent.require_current()
    assert [(lease, thread) for lease, thread in clock_probe.closes if lease is parent] == [
        (parent, threading.current_thread())]


@pytest.mark.parametrize('reuse', ['outside', 'reentered', 'wrong_nested'])
def test_cleanup_guard_belongs_to_one_live_entry_and_never_checks_attempt_time(monkeypatch, clock_probe, reuse):
    budget = bound_budget()
    outer = coordination.reader_budget(budget)
    outer.__enter__()
    guard = budget.cleanup_guard()
    budget.stop_events[0].set()
    with monkeypatch.context() as patch:
        patch.setattr(coordination, 'time', SimpleNamespace(monotonic_ns=forbidden))
        guard.require_current()  # Stopped admission does not preclude bounded cleanup.
    if reuse == 'wrong_nested':
        replacement = coordination.reader_budget(bound_budget())
        replacement.__enter__()
    else:
        outer.__exit__(None, None, None)
        replacement = coordination.reader_budget(budget) if reuse == 'reentered' else None
        if replacement is not None:
            replacement.__enter__()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(coordination, 'time', SimpleNamespace(monotonic_ns=forbidden))
            patch.setattr(clocks, 'capture_domain', forbidden)
            with pytest.raises(ValueError):
                guard.require_current()
    finally:
        if replacement is not None:
            replacement.__exit__(None, None, None)
        if reuse == 'wrong_nested':
            guard.require_current()
            outer.__exit__(None, None, None)


def test_worker_cannot_borrow_parent_thread_lease(clock_probe):
    outcomes = []
    with clocks.capture_domain() as parent:
        def worker():
            try:
                with coordination.reader_budget(bound_budget(), clock_lease=parent):
                    outcomes.append('incorrectly entered')
            except BaseException as error:
                outcomes.append(error)
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(2)
        assert not thread.is_alive()
        assert len(outcomes) == 1 and isinstance(outcomes[0], clocks.ClockDomainError)
        assert 'another thread' in str(outcomes[0])
        assert not parent._closed
        parent.require_current()


@pytest.mark.parametrize('primary_present', [False, True])
def test_owned_scope_close_failure_is_retained_without_replacing_operation(clock_probe, primary_present):
    close_error = OSError('invented worker lease close failure')
    primary = RuntimeError('invented original operation refusal')
    result = []
    clock_probe.worker_close_error = close_error
    def worker():
        scope = None
        try:
            with coordination.reader_budget(bound_budget()) as scope:
                if primary_present:
                    raise primary
        except BaseException as error:
            result.append((error, scope.close_error))
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(2)
    assert not thread.is_alive()
    assert result == [(primary if primary_present else close_error, close_error)]
    owned = [lease for lease in clock_probe.leases if lease._fixture_thread is thread]
    assert len(owned) == 1 and owned[0]._closed
    assert clock_probe.closes.count((owned[0], thread)) == 1


def owner_document():
    return {'format': 'native_stream_owner_v2', 'coordination_profile': profile.source_profile(1),
        'execution_sha256': 'a' * 64, 'started_sha256': 'b' * 64, 'owner_pid': 1,
        'clock': 'monotonic_ns', 'start_ns': 1_000, 'duration_ns': 10_000,
        'deadline_ns': 11_000, 'clock_domain': invented_domain(),
        'transcript': {'path': '/unavailable-synthetic/attempt/transcript.jsonl', 'device': 1, 'inode': 2},
        'control': {'path': '/unavailable-synthetic/attempt/control.jsonl', 'device': 1, 'inode': 3}}


def test_saved_owner_validation_is_detached_without_live_authority(monkeypatch):
    value = owner_document()
    # Saved source hashes are declarations, not proof that the current files match.
    value['coordination_profile']['implementations']['clock']['sha256'] = 'c' * 64
    expected = deepcopy(value)
    with monkeypatch.context() as patch:
        patch.setattr(clocks, 'capture_domain', forbidden)
        patch.setattr(profile, 'source_profile', forbidden)
        patch.setattr(profile, '_source_sha', forbidden)
        patch.setattr(runner_module, 'time', SimpleNamespace(monotonic_ns=forbidden))
        patch.setattr(os, 'getpid', forbidden)
        patch.setattr(os, 'open', forbidden)
        patch.setattr(os, 'stat', forbidden)
        patch.setattr(os, 'lstat', forbidden)
        patch.setattr(os, 'fstat', forbidden)
        patch.setattr(fcntl, 'flock', forbidden)
        actual = runner_module.validate_owner_record_v2(value)
    assert actual == expected
    value['clock_domain']['timebase']['denominator'] = 7
    actual['transcript']['inode'] = 10
    actual['coordination_profile']['implementations']['clock']['sha256'] = 'd' * 64
    assert expected['clock_domain'] == invented_domain()
    assert runner_module.validate_owner_record_v2(expected) == expected


@pytest.mark.parametrize('current_change', ['expanded', 'missing_clock'])
def test_archived_owner_v2_uses_its_frozen_four_role_contract(monkeypatch, current_change):
    value = owner_document()
    current = dict(profile.IMPLEMENTATIONS)
    if current_change == 'expanded':
        current['future_component'] = 'src/data_sheets_schema/future_component.py'
    else:
        current.pop('clock')
    monkeypatch.setattr(profile, 'IMPLEMENTATIONS', current)
    assert runner_module.validate_owner_record_v2(value) == value
    malformed = deepcopy(value)
    malformed['coordination_profile']['implementations'].pop('clock')
    with pytest.raises(ValueError):
        runner_module.validate_owner_record_v2(malformed)


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(format='native_stream_owner_v1'),
    lambda d: d.pop('clock_domain'),
    lambda d: d.update(clock_domain=None),
    lambda d: d.update(start_ns=True),
    lambda d: d.update(deadline_ns=False),
    lambda d: d.update(duration_ns=0),
    lambda d: d.update(deadline_ns=d['deadline_ns'] + 1),
    lambda d: d.update(owner_pid=True),
    lambda d: d['control'].update(device=1, inode=2),
    lambda d: d['transcript'].update(inode=False),
    lambda d: d['control'].update(path=d['transcript']['path']),
    lambda d: d['clock_domain'].update(platform='linux'),
    lambda d: d['clock_domain']['timebase'].update(denominator=True),
    lambda d: d['coordination_profile']['implementations'].pop('clock'),
    lambda d: d['coordination_profile']['implementations']['clock'].update(path='src/foreign.py'),
    lambda d: d['coordination_profile']['implementations']['clock'].update(sha256='not-a-sha'),
])
def test_saved_owner_closed_binding_refuses_ambiguous_records(mutation):
    value = owner_document()
    mutation(value)
    with pytest.raises(ValueError):
        runner_module.validate_owner_record_v2(value)


@pytest.fixture
def bound_host(tmp_path, control_graph, clock_probe):
    """A real owner channel with a parent-owned scope, including teardown."""
    hosts = []

    @contextmanager
    def make(**options):
        host = Host(tmp_path / ('clock-case-' + str(len(hosts))), control_graph,
                    initialize=False, owner_clock_domain=invented_domain(), **options)
        hosts.append(host)
        host.expected_close_error = None
        with clocks.capture_domain() as parent:
            with coordination.reader_budget(host.channel._owner_budget, clock_lease=parent):
                try:
                    host.initialize()
                    yield host
                finally:
                    clock_probe.worker_acquire_error = None
                    clock_probe.worker_close_error = None
                    clock_probe.worker_recheck_error = None
                    clock_probe.parent_recheck_error = None
                    for release in host.releases:
                        release.set()
                    host.close_input()
                    thread = host.channel._work_thread
                    if thread is not None:
                        thread.join(2)
                        assert not thread.is_alive(), 'fixture must release its ordinary worker'
                    try:
                        host.channel.close()
                    except BaseException as error:
                        assert host.expected_close_error is not None
                        assert error is host.expected_close_error
                    finally:
                        for stream in (host.transcript, host.evidence, host.process.stdin, host.process.stdout):
                            if not stream.closed:
                                stream.close()
                        os.close(host.host_read)
    yield make


@pytest.mark.parametrize('failure', ['acquire', 'recheck', 'close'])
def test_actual_worker_clock_failure_cannot_publish_a_successful_decision(bound_host, clock_probe, failure):
    observed = []
    refusal = clocks.ClockDomainError('invented worker clock ' + failure)
    def observer(event):
        observed.append(event)
        if failure == 'recheck' and event.get('subtype') == 'clock-target':
            clock_probe.worker_recheck_error = refusal
    with bound_host(observer=observer) as host:
        observed.clear()
        if failure == 'acquire':
            clock_probe.worker_acquire_error = refusal
        elif failure == 'close':
            clock_probe.worker_close_error = refusal
        host.emit({'type': 'system', 'subtype': 'clock-target'})
        with pytest.raises(host.BudgetStop):
            host.pump(lambda: host.channel._active_work is None and bool(observed))
        assert host.channel._stopped.is_set()
        assert host.decisions() == []
        if failure == 'acquire':
            assert observed == []
        else:
            assert len(observed) == 1
        assert host.channel.failure_snapshot() is not None


@pytest.mark.parametrize('failure', ['acquire', 'recheck'])
def test_failed_worker_domain_is_not_reinterpreted_as_a_foreign_clock_timeout(
        bound_host, clock_probe, monkeypatch, failure):
    refusal = clocks.ClockDomainError('preserve the original worker domain refusal')
    def observer(event):
        if event.get('subtype') == 'foreign-completion-clock':
            clock_probe.worker_recheck_error = refusal

    with bound_host(observer=observer) as host:
        if failure == 'acquire':
            clock_probe.worker_acquire_error = refusal
        real_clock = time.monotonic
        # The frozen wrapper stamps completion after our bound scope exits.
        # Failed domain checking cannot make this worker timestamp comparable.
        monkeypatch.setattr(host.control, 'time', SimpleNamespace(monotonic=lambda:
            real_clock() + (1_000_000 if threading.current_thread() is not clock_probe.parent else 0)))
        host.emit({'type': 'system', 'subtype': 'foreign-completion-clock'})
        with pytest.raises(host.BudgetStop) as caught:
            host.pump(lambda: False)
        assert caught.value.__cause__ is refusal
        assert 'timed out' not in str(caught.value)
        assert host.channel.failure_snapshot()['first_stop'] == str(caught.value)
        assert host.decisions() == []


def test_actual_worker_original_stop_survives_secondary_lease_close(bound_host, clock_probe):
    original = []
    secondary = OSError('invented worker close after original stop')
    def observer(event):
        if event.get('subtype') == 'first-stop':
            raise original[0]
    with bound_host(observer=observer) as host:
        original.append(host.BudgetStop('preserve this exact original worker stop'))
        clock_probe.worker_close_error = secondary
        host.emit({'type': 'system', 'subtype': 'first-stop'})
        with pytest.raises(host.BudgetStop) as caught:
            host.pump(lambda: False)
        assert caught.value is original[0]
        assert host.channel.failure_snapshot()['first_stop'] == str(original[0])
        detail = json.loads(host.channel.failed_members()['worker_clock_close'])
        assert detail['type'] == 'OSError' and detail['message'] == str(secondary)
        assert host.decisions() == []


def test_late_worker_close_error_cannot_backfill_a_frozen_stop_cut(bound_host, clock_probe, monkeypatch):
    closing, release = threading.Event(), threading.Event()
    with bound_host() as host:
        host.releases.append(release)
        original_close = clocks._DomainLease.close
        secondary = OSError('worker close occurs after the parent publication cut')
        clock_probe.worker_close_error = secondary

        def delayed_close(lease):
            if (not getattr(lease, '_fixture_temporary', False)
                    and threading.current_thread() is not clock_probe.parent):
                closing.set()
                assert release.wait(2), 'the test must release its ordinary worker'
            return original_close(lease)

        monkeypatch.setattr(clocks._DomainLease, 'close', delayed_close)
        host.emit({'type': 'system', 'subtype': 'finished-operation-closing-lease'})
        host.pump(closing.is_set)
        worker = host.channel._work_thread
        assert worker is not None and worker.is_alive()
        host.external_stop.set()
        with pytest.raises(host.BudgetStop):
            host.step()
        before = host.channel.failed_members()
        cut = host.channel.failure_snapshot()
        assert cut['completed_result_captured'] is False
        assert 'worker_clock_close' not in before
        release.set()
        worker.join(2)
        assert not worker.is_alive()
        assert host.channel.failed_members() == before
        assert host.channel.failure_snapshot() == cut
        assert host.decisions() == []


def test_actual_worker_cannot_return_success_after_its_own_budget_expires(bound_host, monkeypatch):
    expired = {}
    def observer(event):
        if event.get('subtype') == 'late-result':
            current = coordination.current_reader_budget()
            assert current.clock_domain() == invented_domain()
            expired[threading.current_thread()] = current.deadline_ns
    with bound_host(observer=observer) as host:
        actual_clock = time.monotonic_ns
        monkeypatch.setattr(coordination, 'time', SimpleNamespace(
            monotonic_ns=lambda: expired.get(threading.current_thread(), actual_clock())))
        host.emit({'type': 'system', 'subtype': 'late-result'})
        with pytest.raises(host.BudgetStop):
            host.pump(lambda: False)
        assert expired and threading.current_thread() not in expired
        assert host.decisions() == []
        assert host.channel.failure_snapshot() is not None


def test_real_parent_ex_contention_uses_exact_scope_before_stream_write(bound_host, clock_probe):
    with bound_host() as host:
        before = host.transcript_path.read_bytes()
        raw = host.emit({'type': 'system', 'subtype': 'blocked-ex'})
        with shared_lock(host.transcript_path):
            host.step()
            assert host.transcript_path.read_bytes() == before
            other = bound_budget()
            with coordination.reader_budget(other):
                with pytest.raises(host.BudgetStop):
                    host.step()
            assert host.transcript_path.read_bytes() == before
        assert host.channel._stopped.is_set()
        assert raw not in host.transcript_path.read_bytes()
        assert host.channel.failure_snapshot() is not None


def test_cleanup_domain_refusal_retains_suffix_and_never_attempts_stream_effects(bound_host, clock_probe, monkeypatch):
    with bound_host() as host:
        before = host.transcript_path.read_bytes()
        raw = host.emit({'type': 'system', 'subtype': 'retain-this-tail'})
        with shared_lock(host.transcript_path):
            host.step()
            assert host.transcript_path.read_bytes() == before
        host.close_input()
        host.channel._stop_history()
        clock_probe.parent_recheck_error = clocks.ClockDomainError('invented terminal clock mismatch')
        with monkeypatch.context() as patch:
            patch.setattr(coordination, 'try_lease', forbidden)
            patch.setattr(control_module, '_write', forbidden)
            with pytest.raises((ValueError, host.BudgetStop)) as caught:
                host.channel.close_after_process_termination()
        assert isinstance(caught.value, (ValueError, host.BudgetStop))
        host.expected_close_error = caught.value
        assert host.transcript_path.read_bytes() == before
        assert host.channel.failed_members()['transcript_suffix'].endswith(raw)
        report = host.channel.close_report()
        assert report['capture_complete'] is False
        assert report['format'] == 'native_owner_close_refused_v1'
        assert report['suffix_start'] == len(before)
        clock_probe.parent_recheck_error = None
        with pytest.raises(type(caught.value)) as repeated:
            host.channel.close_after_process_termination()
        assert repeated.value is caught.value
        assert host.channel.close_report() == report


@pytest.mark.parametrize('delay_at', ['stop_history', 'domain_guard'])
def test_cleanup_setup_consumes_the_original_quarter_second(bound_host, monkeypatch, delay_at):
    with bound_host() as host:
        before = host.transcript_path.read_bytes()
        raw = host.emit({'type': 'system', 'subtype': 'no-renewed-cleanup-window'})
        with shared_lock(host.transcript_path):
            host.step()
            assert host.transcript_path.read_bytes() == before
        host.close_input()
        clock = [10_000_000_000]
        initial = clock[0]
        if delay_at == 'stop_history':
            original = host.channel._stop_history
            def delayed():
                clock[0] += 300_000_000
                return original()
            monkeypatch.setattr(host.channel, '_stop_history', delayed)
        else:
            original = coordination.ReaderBudget.cleanup_guard
            def delayed(self):
                clock[0] += 300_000_000
                return original(self)
            monkeypatch.setattr(coordination.ReaderBudget, 'cleanup_guard', delayed)
        with monkeypatch.context() as patch:
            patch.setattr(control_module, 'time', SimpleNamespace(
                monotonic_ns=lambda: clock[0],
                sleep=lambda seconds: clock.__setitem__(0, clock[0] + int(seconds * 1_000_000_000))))
            patch.setattr(control_module, '_write', forbidden)
            with pytest.raises(host.BudgetStop) as caught:
                host.channel.close_after_process_termination()
        host.expected_close_error = caught.value
        result = host.channel.close_report()
        assert result['close_start_ns'] == initial
        assert result['close_deadline_ns'] == initial + 250_000_000
        assert result['tail_reason'] == 'close deadline elapsed'
        assert result['capture_complete'] is False
        assert host.transcript_path.read_bytes() == before
        assert host.channel.failed_members()['transcript_suffix'].endswith(raw)


def test_last_domain_check_cannot_authorize_a_write_using_an_earlier_time(bound_host, monkeypatch):
    with bound_host() as host:
        before = host.transcript_path.read_bytes()
        raw = host.emit({'type': 'system', 'subtype': 'write-within-original-close-budget'})
        with shared_lock(host.transcript_path):
            host.step()
            assert host.transcript_path.read_bytes() == before
        host.close_input()
        now, writes = [10_000_000_000], []
        start = now[0]
        check = coordination._CleanupGuard.require_current
        write = control_module._write

        def delayed_check(guard):
            now[0] += 50_000_000
            return check(guard)

        def observed_write(fd, chunk):
            writes.append(now[0])
            return write(fd, chunk)

        with monkeypatch.context() as patch:
            patch.setattr(coordination._CleanupGuard, 'require_current', delayed_check)
            patch.setattr(control_module, 'time', SimpleNamespace(
                monotonic_ns=lambda: now[0], sleep=lambda seconds: None))
            patch.setattr(control_module, '_write', observed_write)
            with pytest.raises(host.BudgetStop) as caught:
                host.channel.close_after_process_termination()
        host.expected_close_error = caught.value
        assert writes, 'the real append must exercise its final domain/time check'
        assert all(value < start + 250_000_000 for value in writes)
        assert host.transcript_path.read_bytes() == before + raw
        assert host.channel.close_report()['capture_complete'] is False


def test_final_domain_check_is_accounted_before_waiting_for_actual_worker(bound_host, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def observer(event):
        if event.get('subtype') == 'worker-held-during-close':
            entered.set()
            assert release.wait(2), 'the fixture must release its ordinary worker'

    with bound_host(observer=observer) as host:
        host.releases.append(release)
        host.emit({'type': 'system', 'subtype': 'worker-held-during-close'})
        host.pump(entered.is_set)
        worker = host.channel._work_thread
        assert worker is not None and worker.is_alive()
        host.close_input()
        now, eof, waits = [10_000_000_000], [False], []
        start = now[0]
        read = os.read
        check = coordination._CleanupGuard.require_current
        join = worker.join
        pipe = host.process.stdout.fileno()

        def observed_read(fd, count):
            raw = read(fd, count)
            if fd == pipe and raw == b'':
                eof[0] = True
            return raw

        def delayed_check(guard):
            if eof[0]:
                now[0] += 200_000_000
            return check(guard)

        def observed_join(timeout=None):
            waits.append((now[0], timeout))
            return join(timeout)

        with monkeypatch.context() as patch:
            patch.setattr(os, 'read', observed_read)
            patch.setattr(coordination._CleanupGuard, 'require_current', delayed_check)
            patch.setattr(control_module, 'time', SimpleNamespace(
                monotonic_ns=lambda: now[0], sleep=lambda seconds: None))
            patch.setattr(worker, 'join', observed_join)
            with pytest.raises(host.BudgetStop) as caught:
                host.channel.close_after_process_termination()
        host.expected_close_error = caught.value
        assert eof[0] and len(waits) == 1
        for sampled, timeout in waits:
            assert timeout is not None and 0 <= timeout <= max(0, (start + 250_000_000 - sampled) / 1e9)
        assert host.channel.close_report()['worker_shutdown_complete'] is False
        release.set()
        worker.join(2)
        assert not worker.is_alive()


@pytest.mark.parametrize('primary_present', [False, True])
def test_actual_runner_parent_lease_close_cannot_hide_first_failure(tmp_path, selected_controls,
        clock_probe, primary_present):
    case = make_case(tmp_path / 'parent-close', selected_controls)
    original = case['controls']['budgeted_cborg'].BudgetStop('invented original observer stop')
    secondary = OSError('invented terminal parent lease close')
    clock_probe.parent_close_error = secondary
    if primary_present:
        def observer(event):
            if event.get('type') == 'system':
                raise original
        case['kwargs']['event_observer'] = observer
    with pytest.raises(type(original if primary_present else secondary)) as caught:
        case['runner'].execute_child(**case['kwargs'])
    assert caught.value is (original if primary_present else secondary)
    report = case['runner'].report()
    assert report['state'] == 'failed' and report['dispatches'] == 1
    assert report['stop_marker_published'] is True
    assert any(row['error']['type'] == 'OSError' for row in report['cleanup_errors'])
    parent_leases = [lease for lease in clock_probe.leases if lease._fixture_thread is clock_probe.parent]
    assert len(parent_leases) == 1
    assert clock_probe.closes.count((parent_leases[0], clock_probe.parent)) == 1
    assert case['proxy'].control_shutdown['control_shutdown_complete']
