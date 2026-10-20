"""Private owner-pump controls with ordinary pipes/files, never a native child.

The fixture is intentionally shared with the independent adversarial module.
It imports the real verified frozen graph but does not launch its helpers.
"""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import select
import threading
import time
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_attribution_controller as inherited
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_control_v1 as owner
from data_sheets_schema import native_stream_coordination_v1 as coordination


@pytest.fixture(scope='module')
def control_graph():
    roles = tuple(inherited.controller_sources()['modules'])
    with authority.loaded_dependencies(authority.dependency_identity()) as modules:
        yield {name: modules[name] for name in roles}


class Host:
    def __init__(self, root, graph, *, observer=None, classify=None,
                 deadline_ns=None, external_stop=None, stream_byte_limit=None, initialize=True,
                 owner_clock_domain=None):
        self.root = Path(root)
        self.root.mkdir()
        self.control = graph['native_control']
        self.BudgetStop = graph['budgeted_cborg'].BudgetStop
        self.external_stop = external_stop or threading.Event()
        self.releases, self.writers = [], []
        self.responses, self.received = [], b''
        self.policy = {'pretool_control': deepcopy(self.control.HISTORY_CONTRACT),
            'python': 'synthetic-python',
            'readonly_lookups': {'repository': str(root), 'inputs': [], 'output_directories': []}}
        selected = owner.make_control(graph)
        options = {} if stream_byte_limit is None else {'stream_byte_limit': stream_byte_limit}
        options['owner_clock_domain'] = owner_clock_domain
        self.channel = selected(self.policy,
            classify or (lambda *args: ('prescribed', 'synthetic registered operation')),
            event_observer=observer, attempt_deadline_ns=(time.monotonic_ns() + 30_000_000_000
                if deadline_ns is None else deadline_ns), stop_event=self.external_stop, **options)
        parent_read, self.host_write = os.pipe()
        self.host_read, parent_write = os.pipe()
        os.set_blocking(self.host_read, False)
        os.set_blocking(self.host_write, False)
        self.process = SimpleNamespace(stdin=os.fdopen(parent_write, 'wb', buffering=0),
            stdout=os.fdopen(parent_read, 'rb', buffering=0))
        self.transcript_path, self.control_path = self.root / 'transcript.jsonl', self.root / 'control.jsonl'
        self.transcript = self.transcript_path.open('xb', buffering=0)
        self.evidence = self.control_path.open('xb', buffering=0)
        if initialize:
            self.initialize()

    def initialize(self):
        self.channel.start(self.process, self.transcript, self.evidence, 'invented input')
        self.handshake()

    def handshake(self):
        self.pump(lambda: len(self.responses) == 1)
        self.emit({'type': 'control_response', 'response': {'subtype': 'success',
            'request_id': self.control.INIT_ID, 'response': {}}})
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
        assert os.write(self.host_write, raw) == len(raw), 'use feed() for a large invented frame'
        return raw

    def feed(self, raw, timeout=10):
        """Finite ordinary writer, needed only when invented bytes exceed pipe capacity."""
        done, stop = threading.Event(), threading.Event()
        errors = []
        self.releases.append(stop)
        def deliver():
            offset, deadline = 0, time.monotonic() + timeout
            try:
                while offset < len(raw) and not stop.is_set():
                    if time.monotonic() >= deadline:
                        raise AssertionError('bounded synthetic writer did not finish')
                    if select.select([], [self.host_write], [], .05)[1]:
                        try:
                            offset += os.write(self.host_write, raw[offset:offset + 65536])
                        except BlockingIOError:
                            pass
            except BaseException as error:
                errors.append(error)
            finally:
                done.set()
        thread = threading.Thread(target=deliver, daemon=False)
        self.writers.append((thread, errors))
        thread.start()
        return done

    def step(self):
        self.channel.service()
        self.drain()

    def pump(self, predicate, timeout=5):
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
        return [row for raw in self.control_path.read_bytes().splitlines()
                if (row := json.loads(raw))['kind'] == 'decision']

    def close_input(self):
        if self.host_write is not None:
            os.close(self.host_write)
            self.host_write = None

    def cleanup(self):
        for release in self.releases:
            release.set()
        for thread, errors in self.writers:
            thread.join(2)
            assert not thread.is_alive(), 'fixture writer must not leak'
            assert not errors, errors
        self.close_input()
        thread = self.channel._work_thread
        if thread is not None:
            thread.join(2)
            assert not thread.is_alive(), 'fixture worker must not leak'
        try:
            self.channel.close()
        except self.BudgetStop:
            assert self.channel._shutdown_snapshot == (1, False)
        self.transcript.close()
        self.evidence.close()
        for stream in (self.process.stdin, self.process.stdout):
            if not stream.closed:
                stream.close()
        os.close(self.host_read)


@pytest.fixture
def host_factory(tmp_path, control_graph):
    hosts = []
    def make(**kwargs):
        host = Host(tmp_path / ('case-' + str(len(hosts))), control_graph, **kwargs)
        hosts.append(host)
        return host
    yield make
    for host in reversed(hosts):
        host.cleanup()


@contextmanager
def shared_lock(path):
    """Independent file description, never dup() of the owner description."""
    fd = os.open(path, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        yield fd
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def test_normal_decision_is_journaled_once_before_response(host_factory, monkeypatch):
    host = host_factory()
    original = owner._write
    writes = []
    def record_write(fd, raw):
        if fd == host.evidence.fileno() and b'"kind": "decision"' in raw:
            assert len(host.responses) == 2
            writes.append(bytes(raw))
        return original(fd, raw)
    monkeypatch.setattr(owner, '_write', record_write)
    host.emit(*host.frames())
    host.pump(lambda: len(host.responses) == 3)
    assert len(writes) == len(host.decisions()) == 1
    assert host.channel._control_commit is None
    assert host.channel.failure_snapshot() is None
    assert host.responses[-1]['response']['response'] == {}


def test_startup_control_contention_defers_one_init_record_without_resetting_clock(host_factory):
    host = host_factory(initialize=False)
    with shared_lock(host.control_path):
        host.channel.start(host.process, host.transcript, host.evidence, 'invented input')
        started = host.channel.started
        host.step()
        assert host.control_path.read_bytes() == b''
        assert host.responses == [] and host.channel.outgoing == b''
        assert host.channel.started == started
        assert host.channel.failure_snapshot() is None
    host.handshake()
    assert host.channel.started == started
    rows = [json.loads(row) for row in host.control_path.read_bytes().splitlines()]
    assert [row['kind'] for row in rows] == ['initialize_sent', 'initialize_ack']
    assert len(host.responses) == 2


def test_startup_contention_keeps_original_initialize_window(host_factory, monkeypatch):
    host = host_factory(initialize=False)
    with shared_lock(host.control_path):
        host.channel.start(host.process, host.transcript, host.evidence, 'invented input')
        deadline = host.channel.started + host.channel.contract['initialize_timeout_seconds']
        monkeypatch.setattr(host.control, 'time', SimpleNamespace(monotonic=lambda: deadline))
        with pytest.raises(host.BudgetStop, match='initialization timed out before the prompt'):
            host.step()
        assert host.control_path.read_bytes() == b'' and host.responses == []
    assert host.channel._stopped.is_set()


def test_cancel_is_read_while_initial_control_record_waits_for_lock(host_factory):
    host = host_factory(initialize=False)
    with shared_lock(host.control_path):
        host.channel.start(host.process, host.transcript, host.evidence, 'invented input')
        host.emit({'type': 'control_cancel_request', 'request_id': 'unstarted'})
        with pytest.raises(host.BudgetStop, match='cancelled or timed out'):
            host.step()
        assert host.control_path.read_bytes() == b'' and host.responses == []
    assert host.channel.failure_snapshot()['first_stop'] == 'native control callback was cancelled or timed out'


def test_transcript_contention_buffers_without_dispatch_then_commits_in_chunks(host_factory):
    seen = []
    host = host_factory(observer=lambda event: seen.append(event['type']))
    seen.clear()
    frame = {'type': 'system', 'padding': 'x' * (owner.CHUNK_BYTES * 3)}
    raw = (json.dumps(frame) + '\n').encode()
    before = host.transcript_path.read_bytes()
    with shared_lock(host.transcript_path):
        done = host.feed(raw)
        host.pump(lambda: done.is_set() and len(host.channel._pending_raw) == len(raw))
        assert host.transcript_path.read_bytes() == before
        assert seen == []
        assert len(host.channel._events) == 1
    previous = len(before)
    while host.channel._pending_raw:
        host.step()
        now = len(host.transcript_path.read_bytes())
        assert 0 < now - previous <= owner.CHUNK_BYTES
        previous = now
    host.pump(lambda: host.channel._active_work is None and seen == ['system'])
    assert host.transcript_path.read_bytes() == before + raw
    assert host.channel._written_bytes == host.channel._admitted_bytes == len(before + raw)


def test_cancel_intake_remains_responsive_during_transcript_lock(host_factory):
    observed = []
    host = host_factory(observer=lambda event: observed.append(event['type']))
    observed.clear()
    large = {'type': 'system', 'padding': 'x' * (owner.CHUNK_BYTES * 3)}
    cancel = {'type': 'control_cancel_request', 'request_id': 'unstarted'}
    raw = b''.join((json.dumps(row) + '\n').encode() for row in (large, cancel, {'type': 'result'}))
    before = host.transcript_path.read_bytes()
    with shared_lock(host.transcript_path):
        host.feed(raw)
        with pytest.raises(host.BudgetStop, match='cancelled or timed out'):
            host.pump(lambda: host.channel.terminal)
    assert observed == [] and not host.channel.terminal
    assert host.transcript_path.read_bytes() == before
    assert len(host.responses) == 2 and host.decisions() == []
    assert host.channel.failure_snapshot()['first_stop'] == 'native control callback was cancelled or timed out'


def test_completed_classifier_waits_for_control_lease_without_duplicate_commit(host_factory):
    entered, release = threading.Event(), threading.Event()
    def classify(*args):
        entered.set()
        assert release.wait(3)
        return 'prescribed', 'synthetic bounded classification'
    host = host_factory(classify=classify)
    host.releases.append(release)
    host.emit(*host.frames())
    host.pump(entered.is_set)
    before = host.control_path.read_bytes()
    with shared_lock(host.control_path):
        release.set()
        host.channel._work_thread.join(1)
        assert not host.channel._work_thread.is_alive()
        host.step()
        assert host.channel._work_result is not None
        assert 'request1' in host.channel.pending
        assert host.control_path.read_bytes() == before
        assert len(host.responses) == 2 and host.decisions() == []
    host.pump(lambda: len(host.responses) == 3)
    assert len(host.decisions()) == 1
    host.step()
    assert len(host.decisions()) == 1 and len(host.responses) == 3


@pytest.mark.parametrize('kind', ['observer', 'classifier'])
def test_worker_deadline_keeps_active_budget_stop_identity(host_factory, monkeypatch, kind):
    entered, release = threading.Event(), threading.Event()
    def pause(event=None, *args):
        if kind == 'observer' and event['type'] != 'assistant':
            return None
        entered.set()
        assert release.wait(3)
        return ('prescribed', 'too late') if kind == 'classifier' else None
    host = host_factory(**({'observer': pause} if kind == 'observer' else {'classify': pause}))
    host.releases.append(release)
    host.emit(*host.frames())
    host.pump(entered.is_set)
    active_kind, started, _ = host.channel._active_work
    assert active_kind == kind
    limit = host.channel.contract['observer_timeout_seconds' if kind == 'observer' else 'callback_timeout_seconds']
    monkeypatch.setattr(host.control, 'time', SimpleNamespace(monotonic=lambda: started + limit))
    with pytest.raises(host.BudgetStop, match=kind + ' verification timed out'):
        host.step()
    assert host.channel.budget_stop_type is host.BudgetStop
    assert len(host.responses) == 2 and host.decisions() == []


def test_worker_reads_share_absolute_budget_and_parent_context_is_restored(host_factory):
    captured = []
    def observe(event):
        captured.append(coordination.current_reader_budget())
    host = host_factory(observer=observe)
    assert captured and all(type(value) is coordination.ReaderBudget for value in captured)
    assert all(value.deadline_ns <= host.channel._owner_budget.deadline_ns for value in captured)
    assert all(value.stop_events == host.channel._owner_budget.stop_events for value in captured)
    assert coordination.current_reader_budget() is None


def test_metadata_sample_releases_shared_lease_before_return(tmp_path):
    path = tmp_path / 'stream'
    path.write_bytes(b'old\n')
    reader, writer = os.open(path, os.O_RDONLY), os.open(path, os.O_RDWR)
    try:
        budget = coordination.ReaderBudget(time.monotonic_ns() + 1_000_000_000, (threading.Event(),))
        before, opened = coordination.sample_metadata(reader, path, budget, include_path=True)
        assert before == opened and opened['size'] == 4
        lease = coordination.try_lease(writer, fcntl.LOCK_EX)
        assert lease is not None
        with lease:
            os.lseek(writer, 0, os.SEEK_END)
            assert os.write(writer, b'new\n') == 4
        assert coordination.sample_metadata(reader, path, budget)['size'] == 8
    finally:
        os.close(reader)
        os.close(writer)


def test_reader_lock_wait_uses_one_deadline_and_cancellation(tmp_path):
    path = tmp_path / 'stream'
    path.write_bytes(b'bounded\n')
    reader, writer = os.open(path, os.O_RDONLY), os.open(path, os.O_RDWR)
    stop, entered = threading.Event(), threading.Event()
    errors = []
    try:
        lease = coordination.try_lease(writer, fcntl.LOCK_EX)
        assert lease is not None
        budget = coordination.ReaderBudget(time.monotonic_ns() + 1_000_000_000, (stop,))
        def sample():
            entered.set()
            try:
                coordination.sample_metadata(reader, path, budget)
            except BaseException as error:
                errors.append(error)
        with lease:
            thread = threading.Thread(target=sample, daemon=False)
            thread.start()
            assert entered.wait(1)
            stop.set()
            thread.join(1)
            assert not thread.is_alive()
        assert len(errors) == 1 and str(errors[0]) == 'native owner coordination stopped'
    finally:
        stop.set()
        os.close(reader)
        os.close(writer)


def test_known_worker_refusal_keeps_exact_class_and_text(host_factory):
    host = host_factory()
    def classify(*args):
        raise host.BudgetStop('invented registered refusal')
    host.channel.classify = classify
    host.emit(*host.frames())
    with pytest.raises(host.BudgetStop, match='^invented registered refusal$'):
        host.pump(lambda: len(host.responses) == 3)
    assert host.channel.failure_snapshot()['first_stop'] == 'invented registered refusal'
    assert host.channel.failure_snapshot()['capture_state'] == 'capture_refused'
    assert len(host.responses) == 2 and not host.decisions()
