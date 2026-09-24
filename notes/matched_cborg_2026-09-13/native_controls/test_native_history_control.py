"""Selected responsive history verification and legacy replay (#2420)."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from budgeted_cborg import BudgetStop
import native_control as control


def test_legacy_initialize_frame_exact():
    assert control.initialize_frame() == {
        'type': 'control_request', 'request_id': 'd4d_initialize_v1', 'request': {
            'subtype': 'initialize', 'hooks': {'PreToolUse': [{
                'matcher': 'Bash|Read|Write', 'hookCallbackIds': ['d4d_tool_policy_v2'], 'timeout': 3}]}}}


def test_selected_initialize_is_exact_and_detached():
    selected = control.control_contract({'pretool_control': deepcopy(control.HISTORY_CONTRACT)})
    assert control.initialize_frame(selected)['request']['hooks']['PreToolUse'] == [{
        'matcher': 'Bash|Read|Write', 'hookCallbackIds': ['d4d_tool_policy_v3'], 'timeout': 125}]
    selected['observer_timeout_seconds'] = 1
    assert control.HISTORY_CONTRACT['observer_timeout_seconds'] == 120


@pytest.mark.parametrize('change', [
    lambda c: c.update(version=True), lambda c: c.update(version=3.0),
    lambda c: c.update(observer_timeout_seconds=True), lambda c: c.update(observer_timeout_seconds=0),
    lambda c: c.update(observer_timeout_seconds=121), lambda c: c.update(callback_timeout_seconds=3),
    lambda c: c.update(runtime_callback_timeout_seconds=126), lambda c: c.update(extra=1),
    lambda c: c.pop('observer_timeout_seconds'), lambda c: c.update(callback_id='d4d_tool_policy_v2'),
])
def test_unknown_or_malformed_selected_contract_refuses(change):
    value = deepcopy(control.HISTORY_CONTRACT); change(value)
    with pytest.raises(BudgetStop, match='contract'):
        control.control_contract({'pretool_control': value})


@pytest.mark.parametrize('value', [None, [], '', {'version': 3}])
def test_missing_contract_refuses(value):
    with pytest.raises(BudgetStop, match='contract'):
        control.control_contract({'pretool_control': value})


# Real nonblocking OS pipes exercise the selected pump. All frames, commands,
# source files and observations are invented; no native/provider is contacted.
import io
import os
import threading
import time
from types import SimpleNamespace


class Host:
    def __init__(self, root, observer=None, classify=None):
        parent_read, self.host_write = os.pipe()
        self.host_read, parent_write = os.pipe()
        os.set_blocking(self.host_read, False)
        self.policy = {'pretool_control': deepcopy(control.HISTORY_CONTRACT), 'python': 'synthetic-python',
                       'readonly_lookups': {'repository': str(root), 'inputs': [], 'output_directories': []}}
        self.classify = classify or (lambda *args: ('prescribed', 'synthetic registered operation'))
        self.channel = control.NativeControl(self.policy, self.classify, event_observer=observer)
        self.evidence, self.transcript = io.StringIO(), io.BytesIO()
        self.responses, self.received = [], b''
        self.channel.start(SimpleNamespace(stdin=os.fdopen(parent_write, 'wb', buffering=0),
                                            stdout=os.fdopen(parent_read, 'rb', buffering=0)),
                           self.transcript, self.evidence, 'invented input')
        self.releases = []
        self.pump(lambda: len(self.responses) == 1)
        self.emit({'type': 'control_response', 'response': {'subtype': 'success',
                    'request_id': control.INIT_ID, 'response': {}}})
        self.pump(lambda: len(self.responses) == 2 and self.channel._active_work is None)

    def drain(self):
        while True:
            try:
                raw = os.read(self.host_read, 65536)
            except BlockingIOError:
                break
            if not raw:
                break
            self.received += raw
        while b'\n' in self.received:
            line, self.received = self.received.split(b'\n', 1)
            self.responses.append(json.loads(line))

    def emit(self, *events):
        raw = b''.join((json.dumps(event) + '\n').encode() for event in events)
        assert os.write(self.host_write, raw) == len(raw)

    def step(self):
        self.channel.service()
        self.drain()

    def pump(self, predicate, timeout=4):
        deadline = time.monotonic() + timeout
        while not predicate():
            assert time.monotonic() < deadline, 'synthetic pump did not finish'
            self.step()

    def frames(self, identity='tool1', request='request1'):
        payload = {'command': 'synthetic approved command'}
        call = {'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': identity, 'name': 'Bash', 'input': payload}]}}
        callback = {'type': 'control_request', 'request_id': request, 'request': {
            'subtype': 'hook_callback', 'callback_id': self.channel.contract['callback_id'], 'input': {
                'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_use_id': identity,
                'tool_input': payload, 'cwd': self.policy['readonly_lookups']['repository']}}}
        return call, callback

    def decisions(self):
        return [json.loads(row) for row in self.evidence.getvalue().splitlines()
                if json.loads(row)['kind'] == 'decision']

    def cleanup(self):
        for release in self.releases:
            release.set()
        thread = self.channel._work_thread
        if thread is not None:
            thread.join(2)
            assert not thread.is_alive(), 'test must not leak a non-daemon worker'
        try:
            self.channel.close()
        except BudgetStop:
            assert self.channel._shutdown_snapshot == (1, False)
        os.close(self.host_read)
        if self.host_write is not None:
            os.close(self.host_write)


@pytest.fixture
def host_factory(tmp_path):
    hosts = []
    def make(**kwargs):
        host = Host(tmp_path, **kwargs)
        hosts.append(host)
        return host
    yield make
    for host in hosts:
        host.cleanup()


def blocking_observer(host_factory, *, outcome=None):
    entered, release = threading.Event(), threading.Event()
    observed = []
    def observe(event):
        observed.append(event['type'])
        if event['type'] == 'assistant':
            entered.set()
            assert release.wait(3)
            if outcome is not None:
                raise outcome
    calls = []
    host = host_factory(observer=observe, classify=lambda *args: (calls.append(True) or ('prescribed', 'approved')))
    host.releases.append(release)
    host.emit(*host.frames())
    host.pump(entered.is_set)
    return host, entered, release, observed, calls


def test_slow_prior_history_is_responsive_and_precedes_every_authorization(host_factory, monkeypatch):
    host, entered, release, observed, calls = blocking_observer(host_factory)
    clock = [0.]
    # Advance history by more than the legacy host's 3 seconds; classifier
    # starts afterwards and retains a separate 2-second completion budget.
    monkeypatch.setattr(control, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    host.channel._active_work = ('observer', 0., host.channel._active_work[2])
    host.channel._callback_intake = {key: 0. for key in host.channel._callback_intake}
    clock[0] = 3.25
    started = time.monotonic(); host.step()
    assert time.monotonic() - started < .3
    assert calls == [] and host.decisions() == [] and len(host.responses) == 2
    assert observed[-1] == 'assistant'
    release.set()
    host.pump(lambda: len(host.responses) == 3)
    assert calls == [True] and len(host.decisions()) == 1
    assert observed[-1] == 'control_request'
    assert host.responses[-1]['response']['response'] == {}


def test_rejected_history_never_classifies_or_grants(host_factory):
    host, _, release, observed, calls = blocking_observer(host_factory, outcome=BudgetStop('synthetic history rejected'))
    release.set()
    with pytest.raises(BudgetStop, match='synthetic history rejected'):
        host.pump(lambda: len(host.responses) == 3)
    assert host.channel._stopped.is_set()
    assert calls == [] and host.decisions() == [] and len(host.responses) == 2
    assert observed[-1] == 'assistant'


def test_cancel_intake_stops_during_history_and_discards_late_outcome(host_factory):
    host, _, release, observed, calls = blocking_observer(host_factory)
    host.emit({'type': 'control_cancel_request', 'request_id': 'request1'}, {'type': 'result'})
    before = host.evidence.getvalue()
    started = time.monotonic()
    with pytest.raises(BudgetStop, match='cancelled or timed out'):
        host.step()
    assert time.monotonic() - started < .3
    assert not host.channel.terminal and not host.channel._events
    release.set(); host.channel._work_thread.join(1)
    assert host.channel._work_replies.empty() and calls == []
    assert host.evidence.getvalue() == before and len(host.responses) == 2
    with pytest.raises(BudgetStop, match='stopped'):
        host.step()


def test_observer_timeout_stops_without_waiting_for_its_history_lock(host_factory, monkeypatch):
    host, _, release, observed, calls = blocking_observer(host_factory)
    kind, started, event = host.channel._active_work
    monkeypatch.setattr(control, 'time', SimpleNamespace(monotonic=lambda: started + 121))
    with pytest.raises(BudgetStop, match='observer verification timed out'):
        host.step()
    assert host.channel._stopped.is_set() and not calls and not host.decisions()
    release.set()


def test_close_incomplete_worker_is_immutable_and_never_publishes_late(host_factory, monkeypatch):
    host, _, release, observed, calls = blocking_observer(host_factory)
    worker = host.channel._work_thread
    assert worker.daemon is False
    monkeypatch.setattr(control, 'CONTROL_WORKER_JOIN_SECONDS', .01)
    before = host.evidence.getvalue()
    with pytest.raises(BudgetStop, match='closure incomplete'):
        host.channel.close()
    assert host.channel.unfinished_control_workers == 1
    assert host.channel.control_shutdown_complete is False
    release.set(); worker.join(1)
    assert not worker.is_alive()
    assert host.channel.unfinished_control_workers == 1
    assert host.channel.control_shutdown_complete is False
    assert host.channel._work_replies.empty() and host.evidence.getvalue() == before
    assert not calls and not host.decisions()


def test_complete_worker_close_reports_no_unfinished_worker(host_factory):
    host = host_factory()
    host.channel.close()
    assert host.channel.unfinished_control_workers == 0
    assert host.channel.control_shutdown_complete is True


def test_completed_classifier_uses_completion_time_not_delayed_drain(host_factory, monkeypatch):
    clock = [0.]
    host = host_factory()
    monkeypatch.setattr(control, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    host.emit(*host.frames())
    host.pump(lambda: host.channel._active_work is not None and host.channel._active_work[0] == 'classifier')
    host.channel._work_thread.join(1)
    clock[0] = 2.5  # completed at zero, still inside the distinct host 125s bound
    host.pump(lambda: len(host.responses) == 3)
    assert len(host.decisions()) == 1


def test_late_classifier_result_cannot_authorize(host_factory, monkeypatch):
    clock = [0.]
    def classify(*args):
        clock[0] = 2.5
        return 'prescribed', 'late result'
    host = host_factory(classify=classify)
    monkeypatch.setattr(control, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    host.emit(*host.frames())
    with pytest.raises(BudgetStop, match='classifier verification timed out'):
        host.pump(lambda: len(host.responses) == 3)
    assert not host.decisions() and len(host.responses) == 2


def test_response_deadline_is_distinct_from_completed_classifier_budget(host_factory, monkeypatch):
    clock = [0.]
    host = host_factory()
    monkeypatch.setattr(control, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    host.emit(*host.frames())
    host.pump(lambda: host.channel._active_work is not None and host.channel._active_work[0] == 'classifier')
    host.channel._work_thread.join(1)
    clock[0] = 126.
    with pytest.raises(BudgetStop, match='response window elapsed'):
        host.step()
    assert not host.decisions() and len(host.responses) == 2


def test_cancellation_beats_completed_classifier_reply(host_factory):
    host = host_factory()
    host.emit(*host.frames())
    host.pump(lambda: host.channel._active_work is not None and host.channel._active_work[0] == 'classifier')
    host.channel._work_thread.join(1)
    host.emit({'type': 'control_cancel_request', 'request_id': 'request1'})
    with pytest.raises(BudgetStop, match='cancelled or timed out'):
        host.step()
    assert not host.decisions() and len(host.responses) == 2


@pytest.mark.parametrize('bound', ['frames', 'bytes'])
def test_input_queue_has_finite_backpressure(host_factory, monkeypatch, bound):
    host, _, release, observed, calls = blocking_observer(host_factory)
    if bound == 'frames':
        monkeypatch.setattr(control, 'MAX_HISTORY_QUEUE_FRAMES', 2)
    else:
        monkeypatch.setattr(control, 'MAX_HISTORY_QUEUE_BYTES', host.channel._event_bytes + 5)
    host.emit({'type': 'system', 'marker': 'one'}, {'type': 'system', 'marker': 'two'},
              {'type': 'system', 'marker': 'three'})
    with pytest.raises(BudgetStop, match='input queue exceeds'):
        host.step()
    assert calls == [] and not host.decisions()
    release.set()


def test_eof_does_not_close_while_history_is_pending(host_factory):
    host, _, release, observed, calls = blocking_observer(host_factory)
    os.close(host.host_write); host.host_write = None
    host.step()
    assert host.channel._stdout_eof and not host.channel.stdout_closed
    release.set()
    host.pump(lambda: host.channel.stdout_closed)
    assert len(host.responses) == 3
    with pytest.raises(BudgetStop, match='complete evidence'):
        host.channel.finish()


def test_selected_complete_history_replays_and_legacy_contract_cannot_relabel_it(host_factory, tmp_path):
    host = host_factory()
    host.emit(*host.frames())
    host.pump(lambda: len(host.responses) == 3)
    host.emit({'type': 'user', 'message': {'content': [
        {'type': 'tool_result', 'tool_use_id': 'tool1', 'content': 'invented result', 'is_error': False}]}},
        {'type': 'result', 'permission_denials': []})
    host.pump(lambda: host.channel.terminal and host.channel._active_work is None)
    host.channel.finish()
    events = [json.loads(line) for line in host.transcript.getvalue().splitlines()]
    evidence = tmp_path / 'invented-control.jsonl'; evidence.write_text(host.evidence.getvalue())
    checked = control.check_control_history(events, evidence, host.policy, host.classify)
    assert checked['checked'] and checked['problems'] == [] and checked['decisions'] == 1
    legacy = deepcopy(host.policy); legacy['pretool_control'] = deepcopy(control.CONTRACT)
    assert control.check_control_history(events, evidence, legacy, host.classify)['problems']


def test_all_journals_and_child_writes_stay_on_main_thread(host_factory, monkeypatch):
    owner = threading.get_ident()
    host = host_factory()
    recorded, sent = [], []
    original_record, original_write = host.channel.record, os.write
    def record(value):
        recorded.append(threading.get_ident())
        return original_record(value)
    def write(fd, raw):
        if fd == host.channel.process.stdin.fileno():
            sent.append(threading.get_ident())
        return original_write(fd, raw)
    monkeypatch.setattr(host.channel, 'record', record)
    monkeypatch.setattr(control.os, 'write', write)
    host.emit(*host.frames())
    host.pump(lambda: len(host.responses) == 3)
    assert recorded == [owner] and sent == [owner]


@pytest.mark.parametrize('failure', [ValueError('synthetic classifier failure'), ('prescribed', None), ['prescribed', 'wrong type']])
def test_selected_classifier_error_or_malformed_reply_never_grants(host_factory, failure):
    def classify(*args):
        if isinstance(failure, BaseException):
            raise failure
        return failure
    host = host_factory(classify=classify)
    host.emit(*host.frames())
    with pytest.raises(BudgetStop, match='verification failed|malformed decision'):
        host.pump(lambda: len(host.responses) == 3)
    assert host.channel._stopped.is_set() and not host.decisions()
    assert len(host.responses) == 2


def test_every_callback_waits_for_prior_result_observation(host_factory):
    entered, release = threading.Event(), threading.Event()
    seen, classified = [], []
    def observe(event):
        seen.append(event['type'])
        if event['type'] == 'user':
            entered.set()
            assert release.wait(3)
    host = host_factory(observer=observe, classify=lambda *args: (classified.append(True) or ('prescribed', 'approved')))
    host.releases.append(release)
    host.emit(*host.frames())
    host.pump(lambda: len(host.responses) == 3)
    host.emit({'type': 'user', 'message': {'content': [
        {'type': 'tool_result', 'tool_use_id': 'tool1', 'content': 'invented result', 'is_error': False}]}},
        *host.frames('tool2', 'request2'))
    host.pump(entered.is_set)
    host.step()
    assert classified == [True] and len(host.decisions()) == 1 and len(host.responses) == 3
    assert 'tool2' not in host.channel.calls
    release.set()
    host.pump(lambda: len(host.responses) == 4)
    assert classified == [True, True]
    assert [row['request']['request_id'] for row in host.decisions()] == ['request1', 'request2']


def test_file_observation_is_off_main_and_late_metadata_cannot_publish(host_factory, monkeypatch):
    host = host_factory()
    entered, release = threading.Event(), threading.Event()
    host.releases.append(release)
    observed_threads = []
    def file_observe(*args):
        observed_threads.append(threading.get_ident())
        entered.set(); assert release.wait(3)
        return {'kind': 'persisted_output', 'invented': True}
    monkeypatch.setattr(host.channel.files, 'observe', file_observe)
    host.emit({'type': 'system', 'subtype': 'invented-observation'})
    host.pump(entered.is_set)
    assert observed_threads != [threading.get_ident()]
    before = host.evidence.getvalue()
    host.emit({'type': 'control_cancel_request'})
    with pytest.raises(BudgetStop, match='cancelled'):
        host.step()
    release.set(); host.channel._work_thread.join(1)
    assert host.evidence.getvalue() == before
    assert host.channel._work_replies.empty()


def test_history_rejection_does_not_publish_prior_file_observation(host_factory, monkeypatch):
    def observe(event):
        if event['type'] == 'system':
            raise BudgetStop('synthetic later phase rejection')
    host = host_factory(observer=observe)
    monkeypatch.setattr(host.channel.files, 'observe', lambda *args: {'kind': 'persisted_output', 'invented': True})
    before = host.evidence.getvalue()
    host.emit({'type': 'system', 'subtype': 'invented-observation'})
    with pytest.raises(BudgetStop, match='later phase rejection'):
        host.pump(lambda: host.channel.stdout_closed)
    assert host.evidence.getvalue() == before


def test_blocked_reply_remains_subject_to_cancellation_and_no_eof_completion(host_factory, monkeypatch):
    host = host_factory()
    fd = host.channel.process.stdin.fileno()
    original_write = os.write
    def blocked_write(target, raw):
        if target == fd:
            raise BlockingIOError()
        return original_write(target, raw)
    monkeypatch.setattr(control.os, 'write', blocked_write)
    host.emit(*host.frames())
    host.pump(lambda: bool(host.channel.outgoing))
    assert len(host.decisions()) == 1 and len(host.responses) == 2
    # A journaled decision is deliberately distinct from delivery.
    host.emit({'type': 'control_cancel_request', 'request_id': 'request1'})
    with pytest.raises(BudgetStop, match='cancelled'):
        host.step()
    assert host.channel.outgoing == b'' and len(host.responses) == 2
    with pytest.raises(BudgetStop, match='verified delivery'):
        host.channel.finish()


def test_selected_denial_is_replayed_as_denial(host_factory, tmp_path):
    host = host_factory(classify=lambda *args: ('not_prescribed', 'invented disallowed operation'))
    host.emit(*host.frames())
    host.pump(lambda: len(host.responses) == 3)
    assert host.responses[-1]['response']['response']['hookSpecificOutput']['permissionDecision'] == 'deny'
    host.emit({'type': 'user', 'message': {'content': [
        {'type': 'tool_result', 'tool_use_id': 'tool1', 'content': 'denied', 'is_error': True}]}},
        {'type': 'result'})
    host.pump(lambda: host.channel.terminal and host.channel._active_work is None)
    host.channel.finish()
    evidence = tmp_path / 'invented-denied-control.jsonl'; evidence.write_text(host.evidence.getvalue())
    events = [json.loads(line) for line in host.transcript.getvalue().splitlines()]
    checked = control.check_control_history(events, evidence, host.policy, host.classify)
    assert checked['checked'] and checked['problems'] == [] and checked['decisions'] == 1


@pytest.mark.parametrize('cancel', [False, True])
def test_queued_grant_waits_for_complete_input_and_observes_cancel_after_large_frame(host_factory, monkeypatch, cancel):
    host = host_factory()
    original = os.write
    parent_fd = host.channel.process.stdin.fileno()
    def blocked(fd, raw):
        if fd == parent_fd:
            raise BlockingIOError()
        return original(fd, raw)
    monkeypatch.setattr(control.os, 'write', blocked)
    host.emit(*host.frames())
    host.pump(lambda: bool(host.channel.outgoing))
    assert len(host.decisions()) == 1 and len(host.responses) == 2
    # First supply only part of a legal >64KiB frame. The already classified
    # grant must stay private while later raw input may contain cancellation.
    raw = (json.dumps({'type': 'system', 'subtype': 'synthetic_progress', 'padding': 'x' * 131072}) + '\n').encode()
    original(host.host_write, raw[:1024])
    monkeypatch.setattr(control.os, 'write', original)
    host.step()
    assert host.channel.buffer and len(host.responses) == 2
    suffix = raw[1024:]
    if cancel:
        suffix += (json.dumps({'type': 'control_cancel_request', 'request_id': 'request1'}) + '\n').encode()
    done = threading.Event()
    def write_rest():
        try:
            offset = 0
            while offset < len(suffix):
                offset += original(host.host_write, suffix[offset:])
        except OSError:
            pass  # The failure case closes the test's receiving pipe.
        finally:
            done.set()
    writer = threading.Thread(target=write_rest, daemon=False)
    writer.start()
    try:
        if cancel:
            with pytest.raises(BudgetStop, match='cancelled'):
                host.pump(lambda: len(host.responses) == 3)
            assert len(host.responses) == 2 and host.channel.outgoing == b''
        else:
            host.pump(lambda: len(host.responses) == 3)
            assert host.responses[-1]['response']['request_id'] == 'request1'
    finally:
        # Cleanup is bounded and does not leave the synthetic pipe writer.
        if not done.wait(.2):
            host.channel.process.stdout.close()
        writer.join(1)
        assert not writer.is_alive()


def test_unfinished_input_cannot_extend_queued_reply_response_deadline(host_factory, monkeypatch):
    clock = [0.]
    host = host_factory()
    monkeypatch.setattr(control, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    original = os.write
    parent_fd = host.channel.process.stdin.fileno()
    def blocked(fd, raw):
        if fd == parent_fd: raise BlockingIOError()
        return original(fd, raw)
    monkeypatch.setattr(control.os, 'write', blocked)
    host.emit(*host.frames())
    host.pump(lambda: bool(host.channel.outgoing))
    original(host.host_write, b'{"type":"system","padding":"unfinished')
    monkeypatch.setattr(control.os, 'write', original)
    host.step()
    assert len(host.responses) == 2
    clock[0] = 126.
    with pytest.raises(BudgetStop, match='response window elapsed'):
        host.step()
    assert len(host.responses) == 2 and host.channel.outgoing == b''
