"""Independent private-pump boundaries; no native child or provider is launched."""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import os
import sys
import threading
import time
from types import ModuleType, SimpleNamespace

import pytest

from data_sheets_schema import native_attribution_controller as inherited
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_supervisor_authority as supervisor
from data_sheets_schema import native_owner_control_v1 as owner
from data_sheets_schema import native_stream_coordination_v1 as coordination
from .test_native_owner_control import control_graph, host_factory


@contextmanager
def _shared(path):
    # A distinct open-file description is required: dup(owner_fd) would not
    # model another reader's lock ownership.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _text_event():
    return {'type': 'assistant', 'message': {'content': [
        {'type': 'text', 'text': 'invented source frame'}]}}


@pytest.mark.parametrize('deadline', [None, True, False, 0, -1, 1.0,
                                      float('nan'), float('inf'), '123'])
def test_deadline_shape_is_not_coerced_in_budget_or_controller(control_graph, tmp_path, deadline):
    stop = threading.Event()
    with pytest.raises(ValueError):
        coordination.ReaderBudget(deadline, (stop,))
    cls = owner.make_control(control_graph)
    policy = {'pretool_control': deepcopy(control_graph['native_control'].HISTORY_CONTRACT),
              'python': 'synthetic-python',
              'readonly_lookups': {'repository': str(tmp_path), 'inputs': [],
                                   'output_directories': []}}
    with pytest.raises(ValueError):
        cls(policy, lambda *unused: ('prescribed', 'invented'),
            attempt_deadline_ns=deadline, stop_event=stop)


@pytest.mark.parametrize('condition', ['expired', 'stopped'])
def test_unavailable_reader_budget_refuses_before_lock_or_metadata(condition, tmp_path, monkeypatch):
    path = tmp_path / 'stream'
    path.write_bytes(b'unchanged\n')
    stop = threading.Event()
    deadline = 1 if condition == 'expired' else time.monotonic_ns() + 10_000_000_000
    if condition == 'stopped':
        stop.set()
    budget = coordination.ReaderBudget(deadline, (stop,))

    def forbidden(*args, **kwargs):
        raise AssertionError('an unavailable budget attempted a stream lease')

    monkeypatch.setattr(coordination, 'try_lease', forbidden)
    with path.open('rb', buffering=0) as stream:
        with pytest.raises(ValueError, match='deadline elapsed|coordination stopped'):
            coordination.sample_metadata(stream.fileno(), path, budget, include_path=True)
    assert path.read_bytes() == b'unchanged\n'


@pytest.mark.parametrize('when', ['entry', 'backoff'])
@pytest.mark.parametrize('condition', ['expired', 'stopped'])
def test_real_contention_budget_stop_keeps_the_active_exception_and_first_cause(
        host_factory, monkeypatch, when, condition):
    host = host_factory()
    before_control = host.control_path.read_bytes()
    before_transcript = host.transcript_path.read_bytes()
    before_responses = list(host.responses)
    deadline = host.channel._owner_budget.deadline_ns
    clock = [deadline - 1_000_000_000]
    waits = []
    monkeypatch.setattr(coordination, 'time', SimpleNamespace(monotonic_ns=lambda: clock[0]))

    def restrict():
        if condition == 'expired':
            clock[0] = deadline
        else:
            host.external_stop.set()

    def wait(quantum):
        assert 0 < quantum <= .05
        waits.append(quantum)
        restrict()
        return False

    # Exercise the real failed flock attempt; only the passage of time/the
    # arrival of a stop during Event.wait is deterministic.
    monkeypatch.setattr(host.channel._stopped, 'wait', wait)
    expected = ('native owner coordination deadline elapsed' if condition == 'expired'
                else 'native owner coordination stopped')
    with _shared(host.transcript_path):
        host.emit(_text_event())
        if when == 'entry':
            restrict()
        with pytest.raises(host.BudgetStop) as caught:
            host.step()
    assert type(caught.value) is host.BudgetStop
    assert str(caught.value) == expected
    assert len(waits) == (1 if when == 'backoff' else 0)
    assert host.channel._owner_budget.deadline_ns == deadline
    assert host.control_path.read_bytes() == before_control
    assert host.transcript_path.read_bytes() == before_transcript
    assert host.responses == before_responses
    snapshot = host.channel.failure_snapshot()
    assert snapshot['first_stop'] == expected
    host.close_input()
    host.channel.close()
    host.channel.close()
    assert host.channel.failure_snapshot() == snapshot


def test_partial_transcript_write_retains_only_unwritten_suffix_then_pipe_tail(
        host_factory, monkeypatch):
    observed = []
    host = host_factory(observer=lambda event: observed.append(event))
    observed.clear()
    before = host.transcript_path.read_bytes()
    controls = host.control_path.read_bytes()
    responses = list(host.responses)
    event = _text_event()
    raw = (json.dumps(event) + '\n').encode()
    original = owner._write
    calls = []

    def broken(fd, data):
        if fd != host.transcript.fileno():
            return original(fd, data)
        calls.append(bytes(data))
        if len(calls) == 1:
            return original(fd, data[:5])
        raise OSError('invented partial transcript write')

    monkeypatch.setattr(owner, '_write', broken)
    host.emit(event)
    with pytest.raises(OSError, match='invented partial transcript write'):
        host.step()
    assert host.transcript_path.read_bytes() == before + raw[:5]
    assert observed == [] and host.responses == responses
    assert host.control_path.read_bytes() == controls
    snapshot = host.channel.failure_snapshot()
    assert snapshot['first_stop'] == 'OSError: invented partial transcript write'
    assert snapshot['transcript'] == {
        'received_bytes': len(before) + len(raw), 'written_bytes': len(before) + 5,
        'admitted_bytes': len(before), 'pending': _pin(raw[5:])}
    tail = b'invented unparsed pipe tail\n'
    assert os.write(host.host_write, tail) == len(tail)
    host.close_input()
    host.channel.close()
    report = host.channel.close_report()
    assert report['suffix_start'] == len(before) + 5
    assert report['admitted_bytes'] == len(before)
    assert report['suffix'] == _pin(raw[5:] + tail)
    assert report['tail_capture_complete'] is True
    assert report['capture_complete'] is False and report['admitted'] is False
    assert host.channel.failed_members()['transcript_suffix'] == raw[5:] + tail
    assert host.transcript_path.read_bytes() == before + raw[:5]
    assert len(calls) == 2
    # Returned evidence cannot mutate the frozen first failure.
    altered = host.channel.failure_snapshot()
    altered['transcript']['written_bytes'] = -1
    host.channel.failed_members().clear()
    host.channel.close()
    assert host.channel.failure_snapshot() == snapshot
    assert host.channel.close_report() == report
    assert host.channel.failed_members()['transcript_suffix'] == raw[5:] + tail
    assert len(calls) == 2


def test_full_physical_write_followed_by_late_error_is_not_success_with_empty_suffix(
        host_factory, monkeypatch):
    observed = []
    host = host_factory(observer=lambda event: observed.append(event))
    observed.clear()
    before = host.transcript_path.read_bytes()
    event = _text_event()
    raw = (json.dumps(event) + '\n').encode()
    original = type(host.channel)._confirm_stream

    def late(self, role):
        original(self, role)
        if role == 'transcript' and host.transcript_path.stat().st_size > len(before):
            raise OSError('invented post-write check failure')

    monkeypatch.setattr(type(host.channel), '_confirm_stream', late)
    host.emit(event)
    with pytest.raises(OSError, match='invented post-write check failure'):
        host.step()
    assert host.transcript_path.read_bytes() == before + raw
    assert observed == []
    snapshot = host.channel.failure_snapshot()
    assert snapshot['transcript']['written_bytes'] == len(before) + len(raw)
    assert snapshot['transcript']['admitted_bytes'] == len(before)
    assert snapshot['transcript']['pending'] == _pin(b'')
    host.close_input()
    host.channel.close()
    report = host.channel.close_report()
    assert report['suffix'] == _pin(b'') and report['capture_complete'] is False
    assert host.channel.failed_members()['transcript_suffix'] == b''
    host.channel.close()
    assert host.channel.failure_snapshot() == snapshot


def test_partial_decision_journal_keeps_exact_record_and_never_emits_response(
        host_factory, monkeypatch):
    host = host_factory(classify=lambda *unused: ('prescribed', 'invented classification basis'))
    before = host.control_path.read_bytes()
    responses = list(host.responses)
    original = owner._write
    calls = []

    def broken(fd, data):
        if fd != host.evidence.fileno():
            return original(fd, data)
        calls.append(bytes(data))
        if len(calls) == 1:
            return original(fd, data[:7])
        raise OSError('invented partial decision journal')

    monkeypatch.setattr(owner, '_write', broken)
    host.emit(*host.frames())
    with pytest.raises(OSError, match='invented partial decision journal'):
        host.pump(lambda: len(host.responses) > len(responses))
    snapshot = host.channel.failure_snapshot()
    assert snapshot['active_kind'] == 'classifier'
    assert snapshot['completed_result_captured'] is True
    assert snapshot['result'] == ['prescribed', 'invented classification basis']
    record = host.channel.failed_members()['control_record']
    assert json.loads(record)['kind'] == 'decision'
    assert snapshot['control_commit'] == {
        'record': _pin(record), 'start': len(before), 'written': 7, 'complete': False}
    assert host.control_path.read_bytes() == before + record[:7]
    assert host.responses == responses
    host.close_input()
    host.channel.close()
    host.channel.close()
    assert len(calls) == 2
    assert host.channel.failure_snapshot() == snapshot
    assert host.channel.failed_members()['control_record'] == record


@pytest.mark.parametrize('polled', [False, True])
def test_completed_decision_available_at_stop_cut_survives_cleanup(host_factory, polled):
    entered, release = threading.Event(), threading.Event()

    def classify(*unused):
        entered.set()
        assert release.wait(3)
        return 'prescribed', 'completed before the stop cut'

    host = host_factory(classify=classify)
    host.releases.append(release)
    host.emit(*host.frames())
    host.pump(entered.is_set)
    started = host.channel._active_work[1]
    before = host.control_path.read_bytes()
    with _shared(host.control_path):
        earliest_finish = time.monotonic()
        release.set()
        host.channel._work_thread.join(1)
        latest_finish = time.monotonic()
        assert not host.channel._work_thread.is_alive()
        if polled:
            host.step()
        host.external_stop.set()
        with pytest.raises(host.BudgetStop, match='coordination stopped'):
            host.step()
    assert host.control_path.read_bytes() == before
    assert len(host.responses) == 2 and host.decisions() == []
    snapshot = host.channel.failure_snapshot()
    assert snapshot['capture_state'] == 'captured'
    assert snapshot['active_kind'] == 'classifier'
    assert snapshot['worker_started'] == started
    assert earliest_finish <= snapshot['worker_finished'] <= latest_finish
    assert snapshot['completed_result_captured'] is True
    assert snapshot['result'] == ['prescribed', 'completed before the stop cut']
    assert snapshot['request_id'] == 'request1'
    assert snapshot['intended_record_exists'] is False
    assert snapshot['control_commit'] is None
    assert 'control_record' not in host.channel.failed_members()
    host.close_input()
    host.channel.close()
    host.channel.close()
    assert host.channel.failure_snapshot() == snapshot
    assert host.channel.close_report()['operation_failed'] is True


def test_worker_finishing_after_stop_cut_does_not_backfill_a_captured_result(host_factory):
    entered, release = threading.Event(), threading.Event()

    def classify(*unused):
        entered.set()
        assert release.wait(3)
        return 'prescribed', 'completed too late for the stop cut'

    host = host_factory(classify=classify)
    host.releases.append(release)
    host.emit(*host.frames())
    host.pump(entered.is_set)
    worker = host.channel._work_thread
    host.external_stop.set()
    with pytest.raises(host.BudgetStop, match='coordination stopped'):
        host.step()
    snapshot = host.channel.failure_snapshot()
    assert snapshot['completed_result_captured'] is False
    assert snapshot['worker_finished'] is None and snapshot['result'] is None
    assert snapshot['intended_record_exists'] is False
    release.set()
    worker.join(1)
    assert not worker.is_alive()
    host.close_input()
    host.channel.close()
    assert host.channel.failure_snapshot() == snapshot
    assert len(host.responses) == 2 and host.decisions() == []


def test_known_loader_budget_stop_crosses_actual_worker_without_generic_relabeling(
        host_factory, control_graph):
    stopped = control_graph['budgeted_cborg'].BudgetStop

    def classify(*unused):
        raise stopped('invented exact known controller stop')

    host = host_factory(classify=classify)
    assert host.channel.budget_stop_type is stopped is host.BudgetStop
    host.emit(*host.frames())
    with pytest.raises(stopped) as caught:
        host.pump(lambda: len(host.responses) > 2)
    assert type(caught.value) is stopped
    assert str(caught.value) == 'invented exact known controller stop'
    snapshot = host.channel.failure_snapshot()
    assert snapshot['first_stop'] == 'invented exact known controller stop'
    assert snapshot['capture_state'] == 'capture_refused'
    assert len(host.responses) == 2 and host.decisions() == []
    host.close_input()
    host.channel.close()
    assert host.channel.failure_snapshot() == snapshot


def test_successful_finish_close_is_distinct_from_failed_evidence(host_factory):
    host = host_factory()
    host.emit({'type': 'result'})
    host.pump(lambda: host.channel.terminal and host.channel._active_work is None)
    host.close_input()
    host.pump(lambda: host.channel.stdout_closed)
    host.channel.finish()
    transcript, control = host.transcript_path.read_bytes(), host.control_path.read_bytes()
    host.channel.close()
    report = host.channel.close_report()
    assert report['capture_complete'] is True
    assert report['tail_capture_complete'] is True and report['tail_reason'] is None
    assert report['worker_shutdown_complete'] is True and report['unfinished_workers'] == 0
    assert report['operation_failed'] is False
    assert report['suffix'] == _pin(b'')
    assert host.channel.failure_snapshot() is None
    assert host.channel.failed_members() == {}
    host.channel.close()
    assert host.channel.close_report() == report
    assert host.channel.failure_snapshot() is None
    assert host.channel.failed_members() == {}
    assert (host.transcript_path.read_bytes(), host.control_path.read_bytes()) == (transcript, control)


def test_final_evidence_refusal_is_still_failed_after_close(host_factory):
    host = host_factory()
    host.close_input()
    host.pump(lambda: host.channel.stdout_closed)
    before = (host.transcript_path.read_bytes(), host.control_path.read_bytes())
    expected = 'native control session ended without complete evidence'
    with pytest.raises(host.BudgetStop) as caught:
        host.channel.finish()
    assert type(caught.value) is host.BudgetStop and str(caught.value) == expected
    snapshot = host.channel.failure_snapshot()
    assert snapshot['first_stop'] == expected
    host.channel.close()
    report = host.channel.close_report()
    assert report['operation_failed'] is True and report['capture_complete'] is False
    assert report['tail_capture_complete'] is True
    assert report['suffix'] == _pin(b'')
    host.channel.close()
    assert host.channel.failure_snapshot() == snapshot
    assert host.channel.close_report() == report
    assert (host.transcript_path.read_bytes(), host.control_path.read_bytes()) == before


def test_oversized_request_identity_keeps_bounded_first_stop_and_write_accounting(host_factory):
    entered, release = threading.Event(), threading.Event()

    def classify(*unused):
        entered.set()
        assert release.wait(5)
        return 'prescribed', 'small completed result'

    host = host_factory(classify=classify)
    host.releases.append(release)
    request = 'request-' + 'x' * (owner.SUMMARY_LIMIT + 1)
    raw = b''.join((json.dumps(frame) + '\n').encode() for frame in host.frames(request=request))
    done = host.feed(raw)
    host.pump(lambda: done.is_set() and entered.is_set())
    before = (host.transcript_path.read_bytes(), host.control_path.read_bytes())
    with _shared(host.control_path):
        release.set()
        host.channel._work_thread.join(1)
        assert not host.channel._work_thread.is_alive()
        host.external_stop.set()
        with pytest.raises(host.BudgetStop, match='^native owner coordination stopped$'):
            host.step()
    snapshot = host.channel.failure_snapshot()
    assert snapshot['capture_state'] == 'capture_refused'
    assert snapshot['first_stop'] == 'native owner coordination stopped'
    assert snapshot['request_id'] is None
    assert snapshot['request_id_identity'] == _pin(request.encode('utf-8'))
    assert 'request_id' in snapshot['unretained_fields']
    assert snapshot['transcript'] == {
        'received_bytes': len(before[0]), 'written_bytes': len(before[0]),
        'admitted_bytes': len(before[0]), 'pending': _pin(b'')}
    assert len(host.channel._failure_json) <= owner.SUMMARY_LIMIT
    assert len(host.responses) == 2 and host.decisions() == []
    host.close_input()
    host.channel.close()
    host.channel.close()
    assert host.channel.failure_snapshot() == snapshot
    assert (host.transcript_path.read_bytes(), host.control_path.read_bytes()) == before


def test_oversized_original_stop_is_identified_without_truncation_or_offset_loss(host_factory):
    host = host_factory()
    reason = 'invented exact stop: ' + '\N{LATIN SMALL LETTER E WITH ACUTE}' * owner.SUMMARY_LIMIT

    def classify(*unused):
        raise host.BudgetStop(reason)

    host.channel.classify = classify
    host.emit(*host.frames())
    with pytest.raises(host.BudgetStop) as caught:
        host.pump(lambda: len(host.responses) > 2)
    assert type(caught.value) is host.BudgetStop and str(caught.value) == reason
    snapshot = host.channel.failure_snapshot()
    assert snapshot['capture_state'] == 'capture_refused'
    assert snapshot['first_stop'] is None
    assert snapshot['first_stop_identity'] == _pin(reason.encode('utf-8'))
    assert 'first_stop' in snapshot['unretained_fields']
    written = len(host.transcript_path.read_bytes())
    assert snapshot['transcript'] == {
        'received_bytes': written, 'written_bytes': written,
        'admitted_bytes': written, 'pending': _pin(b'')}
    assert len(host.channel._failure_json) <= owner.SUMMARY_LIMIT
    assert len(host.responses) == 2 and host.decisions() == []
    host.close_input()
    host.channel.close()
    assert host.channel.failure_snapshot() == snapshot
    assert host.channel.close_report()['operation_failed'] is True


@pytest.mark.parametrize('shape', ['list', 'mapping'])
def test_large_nontext_identity_on_generic_observer_does_not_mask_original_stop(
        host_factory, shape):
    entered, release = threading.Event(), threading.Event()

    def observe(event):
        if event['type'] == 'system':
            entered.set()
            assert release.wait(5)

    host = host_factory(observer=observe)
    host.releases.append(release)
    padding = 'x' * (owner.SUMMARY_LIMIT + 1)
    request = [padding] if shape == 'list' else {'padding': padding}
    # Generic source events do not use the callback's textual ID contract.
    event = {'type': 'system', 'request_id': request}
    raw = (json.dumps(event) + '\n').encode()
    done = host.feed(raw)
    host.pump(lambda: done.is_set() and entered.is_set())
    worker = host.channel._work_thread
    written = len(host.transcript_path.read_bytes())
    host.external_stop.set()
    with pytest.raises(host.BudgetStop) as caught:
        host.step()
    assert type(caught.value) is host.BudgetStop
    assert str(caught.value) == 'native owner coordination stopped'
    snapshot = host.channel.failure_snapshot()
    assert snapshot['capture_state'] == 'capture_refused'
    assert snapshot['first_stop'] == 'native owner coordination stopped'
    assert snapshot['request_id'] is None
    assert 'request_id' in snapshot['unretained_fields']
    assert snapshot['transcript'] == {
        'received_bytes': written, 'written_bytes': written,
        'admitted_bytes': written, 'pending': _pin(b'')}
    assert len(host.channel._failure_json) <= owner.SUMMARY_LIMIT
    release.set()
    worker.join(1)
    assert not worker.is_alive()
    host.close_input()
    host.channel.close()
    assert host.channel.failure_snapshot() == snapshot
    assert len(host.responses) == 2 and host.decisions() == []


@pytest.mark.parametrize('completed_before_change', [False, True])
def test_restoring_stale_service_graph_cannot_revive_a_pending_grant(
        host_factory, monkeypatch, completed_before_change):
    entered, release = threading.Event(), threading.Event()

    def classify(*unused):
        entered.set()
        assert release.wait(5)
        return 'prescribed', 'must remain stopped after graph restoration'

    host = host_factory(classify=classify)
    host.releases.append(release)
    host.emit(*host.frames())
    host.pump(entered.is_set)
    worker = host.channel._work_thread
    before = host.control_path.read_bytes()
    with _shared(host.control_path):
        if completed_before_change:
            release.set()
            worker.join(1)
            assert not worker.is_alive()
        replacement = ModuleType('budgeted_cborg')
        replacement.__file__ = sys.modules['budgeted_cborg'].__file__
        with monkeypatch.context() as changed:
            changed.setitem(sys.modules, 'budgeted_cborg', replacement)
            with pytest.raises(ValueError, match='stale or foreign controller object graph'):
                host.step()
        snapshot = host.channel.failure_snapshot()
        assert snapshot['first_stop'] == (
            'ValueError: owner factory has a stale or foreign controller object graph')
        assert snapshot['completed_result_captured'] is completed_before_change
        release.set()
        worker.join(1)
        assert not worker.is_alive()
        with pytest.raises(host.BudgetStop, match='coordination stopped'):
            host.step()
    assert host.channel.failure_snapshot() == snapshot
    assert len(host.responses) == 2 and host.decisions() == []
    assert host.control_path.read_bytes() == before
    host.close_input()
    host.channel.close()
    assert host.channel.failure_snapshot() == snapshot


def test_close_uses_one_worker_join_allowance_and_freezes_incomplete_shutdown(
        host_factory, monkeypatch):
    entered, release = threading.Event(), threading.Event()

    def classify(*unused):
        entered.set()
        assert release.wait(5)
        return 'prescribed', 'completion after close is not captured'

    host = host_factory(classify=classify)
    host.releases.append(release)
    host.emit(*host.frames())
    host.pump(entered.is_set)
    worker = host.channel._work_thread
    joins = []
    original = worker.join

    def joined(timeout=None):
        joins.append(timeout)
        return original(timeout)

    monkeypatch.setattr(worker, 'join', joined)
    host.close_input()
    with pytest.raises(host.BudgetStop, match='worker remains active; closure incomplete'):
        host.channel.close()
    assert len(joins) == 1 and 0 <= joins[0] <= host.control.CONTROL_WORKER_JOIN_SECONDS
    snapshot = host.channel.failure_snapshot()
    report = host.channel.close_report()
    assert snapshot['completed_result_captured'] is False
    assert report['unfinished_workers'] == 1 and report['worker_shutdown_complete'] is False
    assert report['operation_failed'] is True and report['capture_complete'] is False
    release.set()
    original(1)
    assert not worker.is_alive()
    with pytest.raises(host.BudgetStop, match='worker remains active; closure incomplete'):
        host.channel.close()
    assert len(joins) == 1
    assert host.channel.close_report() == report
    assert host.channel.failure_snapshot() == snapshot
    assert len(host.responses) == 2 and host.decisions() == []


def _bounded_line(size):
    empty = {'type': 'system', 'padding': ''}
    overhead = len(json.dumps(empty).encode())
    assert size >= overhead
    event = {**empty, 'padding': 'x' * (size - overhead)}
    raw = (json.dumps(event) + '\n').encode()
    assert len(raw) == size + 1
    return event, raw


def test_one_maximum_content_frame_plus_lf_is_not_double_counted(host_factory, monkeypatch):
    seen = []
    host = host_factory(observer=lambda event: seen.append(event['type']))
    seen.clear()
    before = host.transcript_path.read_bytes()
    # Reduced ceilings isolate exact arithmetic under actual SH contention.
    # A separate control below also exercises the unchanged released ceiling.
    monkeypatch.setattr(host.control, 'MAX_FRAME_BYTES', 64)
    monkeypatch.setattr(host.control, 'MAX_HISTORY_QUEUE_BYTES', 128)
    event, raw = _bounded_line(64)
    with _shared(host.transcript_path):
        assert host.emit(event) == raw
        host.step()
        assert seen == []
        assert host.transcript_path.read_bytes() == before
    host.pump(lambda: seen == ['system'] and host.channel._active_work is None)
    assert host.transcript_path.read_bytes() == before + raw
    assert host.channel.failure_snapshot() is None


def test_released_maximum_frame_plus_lf_crosses_real_pipe_without_changing_caps(host_factory):
    seen = []
    host = host_factory(observer=lambda event: seen.append(event['type']),
                        deadline_ns=time.monotonic_ns() + 120_000_000_000)
    seen.clear()
    before = host.transcript_path.read_bytes()
    assert host.control.MAX_FRAME_BYTES == 16 * 1024 * 1024
    assert host.control.MAX_HISTORY_QUEUE_BYTES == 32 * 1024 * 1024
    _, raw = _bounded_line(host.control.MAX_FRAME_BYTES)
    done = host.feed(raw, timeout=120)
    host.pump(lambda: done.is_set() and seen == ['system']
              and host.channel._active_work is None, timeout=120)
    assert host.transcript_path.read_bytes() == before + raw
    assert host.channel.failure_snapshot() is None
    assert len(host.responses) == 2 and host.decisions() == []


@pytest.mark.parametrize('content', ['two_frames', 'blank_lines'])
def test_raw_capacity_includes_lf_and_retains_unread_tail_without_dispatch(
        host_factory, monkeypatch, content):
    seen = []
    host = host_factory(observer=lambda event: seen.append(event['type']))
    seen.clear()
    before = host.transcript_path.read_bytes()
    monkeypatch.setattr(host.control, 'MAX_FRAME_BYTES', 64)
    monkeypatch.setattr(host.control, 'MAX_HISTORY_QUEUE_BYTES', 128)
    raw = _bounded_line(64)[1] * 2 if content == 'two_frames' else b'\n' * 130
    with _shared(host.transcript_path):
        assert os.write(host.host_write, raw) == len(raw)
        host.step()
        with pytest.raises(host.BudgetStop, match='pending raw capacity exhausted'):
            host.step()
    assert seen == [] and len(host.responses) == 2
    assert host.transcript_path.read_bytes() == before
    snapshot = host.channel.failure_snapshot()
    assert snapshot['transcript'] == {
        'received_bytes': len(before) + 128, 'written_bytes': len(before),
        'admitted_bytes': len(before), 'pending': _pin(raw[:128])}
    host.close_input()
    host.channel.close()
    assert host.channel.failed_members()['transcript_suffix'] == raw
    assert host.channel.close_report()['tail_capture_complete'] is True
    assert host.channel.close_report()['capture_complete'] is False


def test_complete_stream_capacity_does_not_give_close_a_second_allowance(host_factory):
    limit = 2048
    host = host_factory(stream_byte_limit=limit)
    before = host.transcript_path.read_bytes()
    remaining = limit - len(before)
    assert remaining > 0
    raw = b'\n' * remaining + b'unretained excess'
    with _shared(host.transcript_path):
        assert os.write(host.host_write, raw) == len(raw)
        host.step()
        with pytest.raises(host.BudgetStop, match='transcript stream byte capacity exhausted'):
            host.step()
    host.close_input()
    host.channel.close()
    report = host.channel.close_report()
    assert report['suffix_start'] == len(before)
    assert report['suffix'] == _pin(b'\n' * remaining)
    assert report['tail_capture_complete'] is False
    assert report['tail_reason'] == 'stream byte capacity exhausted'
    assert report['capture_complete'] is False
    assert host.channel.failed_members()['transcript_suffix'] == b'\n' * remaining
    host.channel.close()
    assert host.channel.close_report() == report


@contextmanager
def _loader_state(*, prefilled):
    """Give actual source loaders a controlled cache, restoring the caller's state."""
    roles = tuple(inherited.controller_sources()['modules'])
    names = set(roles) | set(supervisor.ADDITIONAL) | set(authority.ADDITIONAL)
    saved = {name: sys.modules[name] for name in names if name in sys.modules}
    old_path = sys.path[:]
    for name in names:
        sys.modules.pop(name, None)
    try:
        if prefilled:
            inherited.load_controls()
        yield roles, names
    finally:
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update(saved)
        sys.path[:] = old_path


class _EndLoader(Exception):
    pass


@pytest.mark.parametrize('prefilled', [False, True])
@pytest.mark.parametrize('exceptional_exit', [False, True])
def test_real_loader_v1_successor_order_keeps_fresh_bound_classes_and_restores_cache(
        prefilled, exceptional_exit):
    with _loader_state(prefilled=prefilled) as (roles, names):
        before = {name: sys.modules.get(name) for name in names}
        before_path = sys.path[:]
        bindings = []
        # Actual v1/successor/v1/successor loader entries. No subclass is
        # cached between calls, even when the frozen base was already cached.
        for selected in (False, True, False, True):
            def visit():
                with authority.loaded_dependencies(authority.dependency_identity()) as controls:
                    frozen = {name: controls[name] for name in roles}
                    original = frozen['native_control'].NativeControl
                    assert all(sys.modules[name] is module for name, module in frozen.items())
                    if selected:
                        bound = owner.make_control(frozen)
                        assert issubclass(bound, original)
                        assert bound is not original
                        bindings.append(bound)
                    assert frozen['native_control'].NativeControl is original
                    if exceptional_exit:
                        raise _EndLoader('invented loader exit')

            if exceptional_exit:
                with pytest.raises(_EndLoader, match='invented loader exit'):
                    visit()
            else:
                visit()
            assert {name: sys.modules.get(name) for name in names} == before
            assert sys.path == before_path
        assert len(bindings) == 2 and bindings[0] is not bindings[1]


@pytest.mark.parametrize('exceptional_exit', [False, True])
def test_same_source_stale_loader_objects_cannot_bind_a_new_successor(exceptional_exit):
    with _loader_state(prefilled=False) as (roles, names):
        captured = []

        def first_entry():
            with authority.loaded_dependencies(authority.dependency_identity()) as controls:
                frozen = {name: controls[name] for name in roles}
                captured.append(frozen)
                owner.make_control(frozen)
                if exceptional_exit:
                    raise _EndLoader('invented loader exit')

        if exceptional_exit:
            with pytest.raises(_EndLoader):
                first_entry()
        else:
            first_entry()
        assert not any(name in sys.modules for name in names)
        stale = captured[0]
        with authority.loaded_dependencies(authority.dependency_identity()) as controls:
            current = {name: controls[name] for name in roles}
            assert current['native_control'] is not stale['native_control']
            assert current['native_control'].__file__ == stale['native_control'].__file__
            assert (current['budgeted_cborg'].BudgetStop
                    is not stale['budgeted_cborg'].BudgetStop)
            with pytest.raises(ValueError):
                owner.make_control(stale)
            bound = owner.make_control(current)
            assert issubclass(bound, current['native_control'].NativeControl)
            assert not issubclass(bound, stale['native_control'].NativeControl)
