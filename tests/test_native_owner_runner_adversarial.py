"""Independent private runner controls; invented local peers, never native/auth.

The closed E/S fixtures in this module are local consistency declarations,
not public registrations or launch authorization. The coordinator alone runs
these tests after all source writers and readers have released the checkout.
"""
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time

import pytest

from data_sheets_schema import native_owner_control_v1 as owner
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_runner_v1 as runner_module
from data_sheets_schema import native_shared_contract as c
from tests.test_native_owner_control import Host, control_graph, shared_lock
from tests.test_native_owner_runner import fixed_clock, make_case, runner_case, selected_controls


@pytest.fixture
def tail_host(tmp_path, control_graph, request):
    """Real inherited initialization, independent pipes and unbuffered files."""
    host = Host(tmp_path / 'tail-case', control_graph, **getattr(request, 'param', {}))
    host.expected_cleanup_error = None
    yield host
    for release in host.releases:
        release.set()
    for thread, errors in host.writers:
        thread.join(2)
        assert not thread.is_alive() and not errors
    host.close_input()
    worker = host.channel._work_thread
    if worker is not None:
        worker.join(2)
        assert not worker.is_alive(), 'test-owned worker must not leak'
    # A deliberately incomplete append keeps its terminal refusal on close.
    # Tests assert that refusal and its evidence before this resource cleanup.
    try:
        try:
            host.channel.close()
        except BaseException as error:
            if not isinstance(error, host.BudgetStop) and error is not host.expected_cleanup_error:
                raise
    finally:
        for stream in (host.transcript, host.evidence, host.process.stdin, host.process.stdout):
            if not stream.closed:
                stream.close()
        os.close(host.host_read)


def _stopped_pending(host):
    """Cancellation crosses actual intake while a real SH blocks persistence."""
    before = host.transcript_path.read_bytes()
    raw = host.emit({'type': 'system', 'message': 'unadmitted invented tail'},
                    {'type': 'control_cancel_request', 'request_id': 'stop-before-append'})
    with shared_lock(host.transcript_path):
        with pytest.raises(host.BudgetStop, match='cancelled or timed out'):
            host.step()
    assert host.transcript_path.read_bytes() == before
    assert bytes(host.channel._pending_raw) == raw
    snapshot = host.channel.failure_snapshot()
    assert snapshot['first_stop'] == 'native control callback was cancelled or timed out'
    assert snapshot['transcript']['written_bytes'] == len(before)
    assert snapshot['transcript']['admitted_bytes'] == len(before)
    return before, raw, snapshot


def _assert_append_identity(host, before, final, snapshot):
    report = host.channel.close_report()
    assert report['format'] == 'native_owner_close_v2'
    assert report['cleanup_mode'] == 'append'
    assert report['close_deadline_ns'] - report['close_start_ns'] == 250_000_000
    assert report['written_bytes_at_stop'] == len(before)
    assert report['admitted_bytes_at_stop'] == len(before)
    assert report['admitted_bytes'] == len(before)
    assert report['final_written_bytes'] == report['suffix_start'] == len(final)
    assert report['operation_failed'] is True and report['admitted'] is False
    assert host.channel.failure_snapshot() == snapshot
    assert host.transcript_path.read_bytes() == final
    return report


def _assert_suffix(host, expected):
    report = host.channel.close_report()
    assert report['suffix'] == {'bytes': len(expected), 'sha256': hashlib.sha256(expected).hexdigest()}
    assert host.channel.failed_members().get('transcript_suffix', b'') == expected


def test_real_append_preserves_failure_cut_and_writes_only_under_ex(tail_host, monkeypatch):
    host = tail_host
    before, pending, snapshot = _stopped_pending(host)
    extra = b'raw shutdown bytes, not an admitted event\n'
    assert os.write(host.host_write, extra) == len(extra)
    host.close_input()
    transcript_fd = host.transcript.fileno()
    original_write = owner._write
    writes = []

    def checked_write(fd, raw):
        assert fd == transcript_fd, 'close must not write a control record or outgoing grant'
        independent = os.open(host.transcript_path, os.O_RDONLY)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(independent, fcntl.LOCK_SH | fcntl.LOCK_NB)
        finally:
            os.close(independent)
        assert len(raw) <= owner.CHUNK_BYTES
        count = original_write(fd, raw)
        writes.append(bytes(raw[:count]))
        return count

    monkeypatch.setattr(owner, '_write', checked_write)
    host.channel.close_after_process_termination()
    report = _assert_append_identity(host, before, before + pending + extra, snapshot)
    assert b''.join(writes) == pending + extra
    assert report['tail_capture_complete'] is True
    assert report['capture_complete'] is False
    _assert_suffix(host, b'')
    assert host.transcript.fileno() == transcript_fd and not host.transcript.closed


def test_sh_release_within_close_budget_allows_exact_once_append(tail_host):
    host = tail_host
    before, pending, snapshot = _stopped_pending(host)
    host.close_input()
    fd = os.open(host.transcript_path, os.O_RDONLY)
    fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    released = threading.Event()

    def release():
        time.sleep(.04)
        fcntl.flock(fd, fcntl.LOCK_UN)
        released.set()

    thread = threading.Thread(target=release)
    thread.start()
    try:
        host.channel.close_after_process_termination()
    finally:
        thread.join(2)
        os.close(fd)
    assert released.is_set() and not thread.is_alive()
    report = _assert_append_identity(host, before, before + pending, snapshot)
    assert report['tail_capture_complete'] is True
    _assert_suffix(host, b'')


def test_persistent_sh_retains_suffix_and_alternate_close_never_retries(tail_host, monkeypatch):
    host = tail_host
    before, pending, snapshot = _stopped_pending(host)
    host.close_input()
    with shared_lock(host.transcript_path):
        with pytest.raises(host.BudgetStop):
            host.channel.close_after_process_termination()
    first = _assert_append_identity(host, before, before, snapshot)
    assert first['capture_complete'] is False
    _assert_suffix(host, pending)

    def forbidden(*args, **kwargs):
        pytest.fail('terminal close must not reopen an I/O or waiting window')

    with monkeypatch.context() as patch:
        patch.setattr(owner, '_write', forbidden)
        patch.setattr(owner.coordination, 'try_lease', forbidden)
        for close in (host.channel.close_after_process_termination, host.channel.close):
            with pytest.raises(host.BudgetStop):
                close()
            assert host.channel.close_report() == first
            assert host.transcript_path.read_bytes() == before


def test_short_append_then_error_keeps_only_unwritten_suffix(tail_host, monkeypatch):
    host = tail_host
    before, pending, snapshot = _stopped_pending(host)
    host.close_input()
    actual_write = owner._write
    calls = []

    def short_then_fail(fd, raw):
        assert fd == host.transcript.fileno()
        calls.append(bytes(raw))
        if len(calls) == 1:
            return actual_write(fd, raw[:7])
        raise OSError('invented append failure after seven physical bytes')

    monkeypatch.setattr(owner, '_write', short_then_fail)
    with pytest.raises(host.BudgetStop):
        host.channel.close_after_process_termination()
    report = _assert_append_identity(host, before, before + pending[:7], snapshot)
    assert len(calls) == 2 and calls[1] == pending[7:]
    assert report['capture_complete'] is False
    assert report['retention_error'] is not None
    _assert_suffix(host, pending[7:])
    with pytest.raises(host.BudgetStop):
        host.channel.close_after_process_termination()
    assert len(calls) == 2


def test_full_append_then_confirmation_failure_does_not_invent_remainder(tail_host, monkeypatch):
    host = tail_host
    before, pending, snapshot = _stopped_pending(host)
    host.close_input()
    confirm = host.channel._confirm_stream

    def late_failure(role):
        confirm(role)
        if role == 'transcript' and host.channel._written_bytes > len(before):
            raise host.BudgetStop('invented post-write identity refusal')

    monkeypatch.setattr(host.channel, '_confirm_stream', late_failure)
    with pytest.raises(host.BudgetStop):
        host.channel.close_after_process_termination()
    report = _assert_append_identity(host, before, before + pending, snapshot)
    assert report['capture_complete'] is False and report['retention_error'] is not None
    _assert_suffix(host, b'')


@pytest.mark.parametrize('arguments', ['positional', 'keyword'])
def test_close_deadline_cannot_be_supplied_by_caller(tail_host, arguments):
    host = tail_host
    before, pending, snapshot = _stopped_pending(host)
    future = time.monotonic_ns() + 10**15
    with pytest.raises(TypeError):
        if arguments == 'positional':
            host.channel.close_after_process_termination(future)
        else:
            host.channel.close_after_process_termination(close_deadline_ns=future)
    assert host.channel.close_report() is None
    assert host.channel.failure_snapshot() == snapshot
    assert host.transcript_path.read_bytes() == before
    host.close_input()
    host.channel.close_after_process_termination()
    _assert_append_identity(host, before, before + pending, snapshot)


def test_tail_contention_and_actual_worker_share_one_close_allowance(tail_host, monkeypatch):
    host = tail_host
    entered, release_worker = threading.Event(), threading.Event()
    host.releases.append(release_worker)

    def blocked_observer(event):
        entered.set()
        assert release_worker.wait(5), 'fixture must release its actual observer'

    host.channel.event_observer = blocked_observer
    host.emit({'type': 'system', 'message': 'hold an actual observer'})
    host.pump(entered.is_set)
    worker = host.channel._work_thread
    assert worker is not None and worker.is_alive()
    before, pending, snapshot = _stopped_pending(host)
    assert snapshot['active_kind'] == 'observer'
    assert snapshot['completed_result_captured'] is False
    host.close_input()
    observed_joins = []
    actual_join = worker.join

    def counted_join(timeout=None):
        observed_joins.append(timeout)
        return actual_join(timeout)

    fd = os.open(host.transcript_path, os.O_RDONLY)
    fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    released = threading.Event()
    waiting = threading.Event()
    lease = owner.coordination.try_lease

    def observe_contention(fd, mode):
        result = lease(fd, mode)
        if fd == host.transcript.fileno() and result is None:
            waiting.set()
        return result

    def release_lock():
        assert waiting.wait(2), 'release follows actual close-time contention'
        time.sleep(.10)
        fcntl.flock(fd, fcntl.LOCK_UN)
        released.set()

    releaser = threading.Thread(target=release_lock)
    releaser.start()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(worker, 'join', counted_join)
            patch.setattr(owner.coordination, 'try_lease', observe_contention)
            with pytest.raises(host.BudgetStop, match='worker'):
                host.channel.close_after_process_termination()
        report = _assert_append_identity(host, before, before + pending, snapshot)
        assert released.is_set()
        assert report['worker_shutdown_complete'] is False
        assert report['unfinished_workers'] == 1
        assert len(observed_joins) == 1
        assert 0 <= observed_joins[0] < .20, 'join must not obtain a fresh .25-second window'
    finally:
        release_worker.set()
        releaser.join(2)
        os.close(fd)
        actual_join(2)
    assert not worker.is_alive() and not releaser.is_alive()
    assert host.channel.failure_snapshot() == snapshot, 'a reply after the stop cut is not retroactive evidence'


def test_artifact_only_close_cannot_be_upgraded_to_a_second_append_window(tail_host, monkeypatch):
    host = tail_host
    before, pending, snapshot = _stopped_pending(host)
    host.close_input()
    host.channel.close()
    first = host.channel.close_report()
    assert first['format'] == 'native_owner_close_v1'
    _assert_suffix(host, pending)

    def forbidden(*args, **kwargs):
        pytest.fail('alternate cleanup cannot append after terminal artifact-only retention')

    with monkeypatch.context() as patch:
        patch.setattr(owner, '_write', forbidden)
        patch.setattr(owner.coordination, 'try_lease', forbidden)
        host.channel.close_after_process_termination()
    assert host.channel.close_report() == first
    assert host.channel.failure_snapshot() == snapshot
    assert host.transcript_path.read_bytes() == before


def test_concurrent_close_cannot_create_another_lock_waiter(tail_host, monkeypatch):
    host = tail_host
    before, pending, snapshot = _stopped_pending(host)
    host.close_input()
    entered = threading.Event()
    original_lease = owner.coordination.try_lease
    errors = []

    def observed_lease(fd, mode):
        if fd == host.transcript.fileno():
            entered.set()
        return original_lease(fd, mode)

    def close_in_thread():
        try:
            host.channel.close_after_process_termination()
        except BaseException as error:
            errors.append(error)

    with shared_lock(host.transcript_path), monkeypatch.context() as patch:
        patch.setattr(owner.coordination, 'try_lease', observed_lease)
        closer = threading.Thread(target=close_in_thread)
        closer.start()
        try:
            assert entered.wait(2)
            with pytest.raises(host.BudgetStop, match='in progress'):
                host.channel.close()
        finally:
            closer.join(2)
    assert not closer.is_alive()
    assert len(errors) == 1 and isinstance(errors[0], host.BudgetStop)
    _assert_append_identity(host, before, before, snapshot)
    _assert_suffix(host, pending)


@pytest.mark.parametrize('tail_host', [{'stream_byte_limit': 256 * 1024}], indirect=True)
def test_exact_stream_capacity_can_append_existing_multichunk_suffix_without_another_read(tail_host, monkeypatch):
    host = tail_host
    before = host.transcript_path.read_bytes()
    cancel = (json.dumps({'type': 'control_cancel_request', 'request_id': 'at-capacity'}) + '\n').encode()
    template = {'type': 'system', 'padding': ''}
    overhead = len((json.dumps(template) + '\n').encode()) + len(cancel)
    template['padding'] = 'x' * (256 * 1024 - len(before) - overhead)
    pending = (json.dumps(template) + '\n').encode() + cancel
    assert len(pending) > owner.CHUNK_BYTES * 2
    assert len(before) + len(pending) == 256 * 1024
    with shared_lock(host.transcript_path):
        delivered = host.feed(pending)
        with pytest.raises(host.BudgetStop, match='cancelled or timed out'):
            host.pump(lambda: host.channel._stopped.is_set())
    assert delivered.wait(2)
    assert bytes(host.channel._pending_raw) == pending
    snapshot = host.channel.failure_snapshot()
    host.close_input()

    def forbidden_read(*args, **kwargs):
        pytest.fail('appending old bytes must not grant a fresh pipe-read allowance')

    with monkeypatch.context() as patch:
        patch.setattr(owner.os, 'read', forbidden_read)
        with pytest.raises(host.BudgetStop):
            host.channel.close_after_process_termination()
    report = _assert_append_identity(host, before, before + pending, snapshot)
    assert report['tail_capture_complete'] is False
    assert report['tail_reason'] == 'stream byte capacity exhausted'
    _assert_suffix(host, b'')


def _encode_associations(case):
    """Rebind only S to the supplied E; preserve deliberate C/E contradictions."""
    raw = c.canonical(case['execution'])
    case['started']['registration_sha256'] = c.sha(raw)
    case['kwargs']['execution_raw'] = raw
    case['kwargs']['started_raw'] = c.canonical(case['started'])


def _encode_composition(case):
    raw = c.canonical(case['composition'])
    case['execution']['composition_raw_json'] = raw.decode()
    case['execution']['composition_sha256'] = c.sha(raw)
    case['started']['composition_sha256'] = c.sha(raw)
    _encode_associations(case)


def _no_child(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('a conflicting private association must never dispatch')
    monkeypatch.setattr(runner_module, '_spawn', forbidden)


@pytest.mark.parametrize('mutation', [
    'instruction_path', 'instruction_bytes', 'instruction_digests', 'instruction_utf8',
    'composition_bytes', 'policy_hash', 'policy_nested', 'policy_false_vs_zero',
    'argv', 'environment', 'started_hash', 'started_attempt', 'boolean_duration',
])
def test_conflicting_consumed_inputs_refuse_before_dispatch_and_spend_binding(runner_case, monkeypatch, mutation):
    case = runner_case
    original = dict(case['kwargs'])
    original.update(argv=list(original['argv']), env=dict(original['env']),
                    command_policy=deepcopy(original['command_policy']))
    if mutation == 'instruction_path':
        alternate = case['root'] / 'same-bytes-other-identity.txt'
        alternate.write_bytes(case['instruction'].read_bytes())
        case['kwargs']['instruction'] = alternate
    elif mutation == 'instruction_bytes':
        case['instruction'].write_bytes(b'different consumed instruction\n')
    elif mutation == 'instruction_digests':
        case['execution']['instruction_sha256'] = '0' * 64
        _encode_associations(case)
    elif mutation == 'instruction_utf8':
        raw = b'\xff\xfe\n'
        case['instruction'].write_bytes(raw)
        case['composition']['instruction_sha256'] = case['execution']['instruction_sha256'] = c.sha(raw)
        _encode_composition(case)
    elif mutation == 'composition_bytes':
        case['execution']['composition_raw_json'] += '\n'
        _encode_associations(case)
    elif mutation == 'policy_hash':
        case['composition']['policy_sha256'] = '0' * 64
        _encode_composition(case)
    elif mutation == 'policy_nested':
        case['kwargs']['command_policy']['readonly_lookups']['inputs'].append('/invented-unregistered-input')
    elif mutation == 'policy_false_vs_zero':
        case['composition']['policy']['fixture_optional'] = False
        case['composition']['policy_sha256'] = c.sha(c.canonical(case['composition']['policy']))
        case['kwargs']['command_policy']['fixture_optional'] = 0
        _encode_composition(case)
    elif mutation == 'argv':
        case['kwargs']['argv'].append('--unregistered-argument')
    elif mutation == 'environment':
        case['kwargs']['env']['INVENTED_UNREGISTERED'] = 'different'
    elif mutation == 'started_hash':
        case['started']['registration_sha256'] = '0' * 64
        case['kwargs']['started_raw'] = c.canonical(case['started'])
    elif mutation == 'started_attempt':
        case['started']['attempt_id'] = 'a-different-attempt'
        case['kwargs']['started_raw'] = c.canonical(case['started'])
    elif mutation == 'boolean_duration':
        case['kwargs']['deadline_seconds'] = True
    _no_child(monkeypatch)
    with pytest.raises(ValueError):
        case['runner'].execute_child(**case['kwargs'])
    first = case['runner'].report()
    assert first['state'] == 'failed' and first['dispatches'] == 0
    assert first['owner_published'] is False
    assert first['execution_authorized'] is False
    assert list(case['attempt'].iterdir()) == []
    with pytest.raises(ValueError, match='one-use'):
        case['runner'].execute_child(**original)
    assert case['runner'].report() == first
    assert list(case['attempt'].iterdir()) == []


@pytest.mark.parametrize('mutation', ['argv', 'environment', 'policy', 'instruction'])
def test_verify_launch_cannot_swap_consumed_inputs_after_initial_binding(runner_case, monkeypatch, mutation):
    case = runner_case

    def change_after_binding():
        if mutation == 'argv':
            case['kwargs']['argv'].append('--late-unregistered-argument')
        elif mutation == 'environment':
            case['kwargs']['env']['LANG'] = 'C'
        elif mutation == 'policy':
            case['kwargs']['command_policy']['readonly_lookups']['inputs'].append('/late-unregistered-input')
        else:
            case['instruction'].write_bytes(b'late replacement must not reach the peer\n')

    case['kwargs']['verify_launch'] = change_after_binding
    _no_child(monkeypatch)
    with pytest.raises(ValueError, match='changed during verification'):
        case['runner'].execute_child(**case['kwargs'])
    report = case['runner'].report()
    assert report['dispatches'] == 0 and report['state'] == 'failed'
    assert report['owner_published'] is True and report['stop_marker_published'] is True
    assert not (case['root'] / 'received-instruction.txt').exists()
    owner_raw = case['runner'].owner_raw()
    assert owner_raw == (case['attempt'] / 'stream-owner.json').read_bytes()
    assert json.loads(owner_raw)['execution_sha256'] == c.sha(case['kwargs']['execution_raw'])


@pytest.mark.parametrize('kind', ['symlink', 'hardlink'])
def test_instruction_alias_refuses_without_touching_source_or_peer(runner_case, monkeypatch, kind):
    case = runner_case
    original = case['instruction'].read_bytes()
    other = case['root'] / 'other-instruction.txt'
    if kind == 'symlink':
        other.write_bytes(original)
        case['instruction'].unlink()
        case['instruction'].symlink_to(other)
    else:
        os.link(case['instruction'], other)
    _no_child(monkeypatch)
    with pytest.raises(ValueError):
        case['runner'].execute_child(**case['kwargs'])
    assert case['instruction'].read_bytes() == other.read_bytes() == original
    assert list(case['attempt'].iterdir()) == []
    assert case['runner'].report()['dispatches'] == 0


def test_bound_runner_after_loader_exit_cannot_be_revived_by_reentry(tmp_path, monkeypatch):
    selected = authority.dependency_identity(stream_snapshot_profile=1)
    with authority.loaded_dependencies(selected) as controls:
        case = make_case(tmp_path / 'expired-context-case', controls)
    _no_child(monkeypatch)
    with pytest.raises(ValueError, match='loader lifetime'):
        case['runner'].execute_child(**case['kwargs'])
    first = case['runner'].report()
    assert first['dispatches'] == 0
    with authority.loaded_dependencies(selected):
        with pytest.raises(ValueError, match='one-use'):
            case['runner'].execute_child(**case['kwargs'])
    assert case['runner'].report() == first
    assert list(case['attempt'].iterdir()) == []


def test_nested_loader_does_not_admit_outer_runner_and_restoration_cannot_retry(runner_case, monkeypatch):
    case = runner_case
    _no_child(monkeypatch)
    with authority.loaded_dependencies(case['identity']):
        with pytest.raises(ValueError, match='loader lifetime'):
            case['runner'].execute_child(**case['kwargs'])
    with pytest.raises(ValueError, match='one-use'):
        case['runner'].execute_child(**case['kwargs'])
    assert case['runner'].report()['dispatches'] == 0


@pytest.mark.parametrize('role', ['native_control', 'run_native_canary', 'budgeted_cborg'])
def test_stale_bare_graph_is_terminal_even_after_module_restoration(runner_case, monkeypatch, role):
    case = runner_case
    _no_child(monkeypatch)
    with monkeypatch.context() as patch:
        patch.setitem(sys.modules, role, object())
        with pytest.raises(ValueError, match='stale or foreign'):
            case['runner'].execute_child(**case['kwargs'])
    with pytest.raises(ValueError, match='one-use'):
        case['runner'].execute_child(**case['kwargs'])
    assert case['runner'].report()['dispatches'] == 0
    assert list(case['attempt'].iterdir()) == []


def test_actual_peer_consumes_the_validated_instruction_not_a_late_replacement(runner_case, monkeypatch):
    case = runner_case
    expected = case['instruction'].read_bytes()
    spawn = runner_module._spawn
    dispatched = []

    def replace_after_final_check(argv, **kwargs):
        case['instruction'].write_bytes(b'late path contents must never replace captured bytes\n')
        process = spawn(argv, **kwargs)
        dispatched.append(process)
        return process

    monkeypatch.setattr(runner_module, '_spawn', replace_after_final_check)
    assert case['runner'].execute_child(**case['kwargs']) == 0
    assert len(dispatched) == 1 and dispatched[0].poll() == 0
    assert (case['root'] / 'received-instruction.txt').read_bytes() == expected
    assert case['instruction'].read_bytes() != expected
    assert case['runner'].report()['execution_authorized'] is False
    assert case['runner'].report()['native_acceptance'] == 'not_assessed'


@pytest.mark.parametrize('secondary_failure', ['stop_marker', 'report'])
def test_actual_observer_budgetstop_survives_cleanup_failures(runner_case, monkeypatch, secondary_failure):
    case = runner_case
    BudgetStop = case['controls']['budgeted_cborg'].BudgetStop
    primary = BudgetStop('invented observer first stop, preserve exact exception')
    spawned = []
    spawn = runner_module._spawn
    terminate = case['controls']['run_native_canary'].terminate_group
    termination_calls = []

    def actual_spawn(argv, **kwargs):
        process = spawn(argv, **kwargs)
        spawned.append((process, kwargs['stderr']))
        return process

    def actual_terminate(process):
        assert process is spawned[0][0]
        assert not process.stdout.closed and not spawned[0][1].closed
        termination_calls.append(process)
        return terminate(process)

    def observer(event):
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            raise primary

    case['kwargs']['event_observer'] = observer
    monkeypatch.setattr(runner_module, '_spawn', actual_spawn)
    monkeypatch.setattr(case['controls']['run_native_canary'], 'terminate_group', actual_terminate)
    if secondary_failure == 'stop_marker':
        durable_new = runner_module.durable.durable_new

        def refused_marker(path, raw):
            if Path(path).name == 'stream-owner-stop.json':
                raise OSError('invented stop-marker write failure')
            return durable_new(path, raw)

        monkeypatch.setattr(runner_module.durable, 'durable_new', refused_marker)
    else:
        encode = owner._json

        def refused_report(value, *args, **kwargs):
            if value.get('format') == 'native_owner_runner_report_v1':
                raise ValueError('invented bounded-report serialization failure')
            return encode(value, *args, **kwargs)

        monkeypatch.setattr(owner, '_json', refused_report)
    with pytest.raises(BudgetStop) as caught:
        case['runner'].execute_child(**case['kwargs'])
    assert caught.value is primary
    assert len(spawned) == len(termination_calls) == 1
    process, stderr = spawned[0]
    assert process.poll() is not None
    assert process.stdin.closed and process.stdout.closed and stderr.closed
    assert (case['root'] / 'received-instruction.txt').is_file()
    report = case['runner'].report()
    assert report['state'] == 'failed' and report['dispatches'] == 1
    assert report['execution_authorized'] is False
    snapshot = json.loads(case['runner'].failed_members()['failure_summary'])
    assert snapshot['first_stop'] == str(primary)
    if secondary_failure == 'stop_marker':
        assert report['primary_error']['message'] == str(primary)
        assert any(row['stage'] == 'stop_marker' for row in report['cleanup_errors'])
        assert report['stop_marker_published'] is False
    else:
        assert report['format'] == 'native_owner_runner_report_refused_v1'
    assert case['stops'][0] == str(primary)


def test_successful_peer_does_not_hide_first_cleanup_refusal(runner_case, monkeypatch):
    case = runner_case
    secondary = OSError('invented stop-marker failure after successful peer')
    durable_new = runner_module.durable.durable_new

    def refused_marker(path, raw):
        if Path(path).name == 'stream-owner-stop.json':
            raise secondary
        return durable_new(path, raw)

    monkeypatch.setattr(runner_module.durable, 'durable_new', refused_marker)
    with pytest.raises(OSError) as caught:
        case['runner'].execute_child(**case['kwargs'])
    assert caught.value is secondary
    report = case['runner'].report()
    assert report['state'] == 'failed' and report['dispatches'] == 1
    assert report['returncode'] == 0 and report['primary_error'] is None
    assert report['cleanup_errors'][0]['stage'] == 'stop_marker'
    assert report['control_close']['capture_complete'] is True
    assert (case['root'] / 'received-instruction.txt').read_bytes() == case['instruction'].read_bytes()


@pytest.mark.parametrize('over_limit', [False, True])
def test_actual_runner_instruction_capture_respects_exact_local_boundary(runner_case, monkeypatch, over_limit):
    case = runner_case
    limit = len(case['kwargs']['execution_raw']) + 1024
    raw = b'x' * (limit + int(over_limit))
    case['instruction'].write_bytes(raw)
    case['composition']['instruction_sha256'] = case['execution']['instruction_sha256'] = c.sha(raw)
    _encode_composition(case)
    assert len(case['kwargs']['execution_raw']) < limit
    assert len(case['kwargs']['started_raw']) < limit
    assert len(case['execution']['composition_raw_json'].encode()) < limit
    monkeypatch.setattr(runner_module, 'REQUEST_LIMIT', limit)
    if over_limit:
        _no_child(monkeypatch)
        with pytest.raises(ValueError, match='bound|exceed|large|size'):
            case['runner'].execute_child(**case['kwargs'])
        assert case['runner'].report()['dispatches'] == 0
        assert list(case['attempt'].iterdir()) == []
    else:
        assert case['runner'].execute_child(**case['kwargs']) == 0
        assert (case['root'] / 'received-instruction.txt').read_bytes() == raw
        assert case['runner'].report()['dispatches'] == 1


@pytest.mark.parametrize('replacement', ['symlink', 'missing', 'regular_file'])
def test_separate_cwd_changed_by_verifier_refuses_before_dispatch_and_cannot_retry(runner_case, monkeypatch, replacement):
    case = runner_case
    cwd = case['root'] / 'registered-cwd'
    cwd.mkdir()
    saved = case['root'] / 'original-cwd'
    unrelated = case['root'] / 'unregistered-cwd'
    unrelated.mkdir()
    sentinel = unrelated / 'sentinel.txt'
    sentinel.write_bytes(b'must not be consumed or changed')
    case['kwargs']['cwd'] = case['execution']['working_directory'] = case['composition']['working_directory'] = str(cwd)
    case['kwargs']['command_policy']['readonly_lookups']['repository'] = str(cwd)
    case['composition']['policy'] = deepcopy(case['kwargs']['command_policy'])
    case['composition']['policy_sha256'] = c.sha(c.canonical(case['composition']['policy']))
    _encode_composition(case)
    execution_raw, started_raw = case['kwargs']['execution_raw'], case['kwargs']['started_raw']

    def replace_cwd():
        cwd.rename(saved)
        if replacement == 'symlink':
            cwd.symlink_to(unrelated, target_is_directory=True)
        elif replacement == 'regular_file':
            cwd.write_bytes(b'not a working directory')

    case['kwargs']['verify_launch'] = replace_cwd
    _no_child(monkeypatch)
    with pytest.raises((ValueError, OSError)):
        case['runner'].execute_child(**case['kwargs'])
    assert case['runner'].report()['dispatches'] == 0
    assert case['runner'].report()['owner_published'] is True
    assert case['kwargs']['execution_raw'] == execution_raw
    assert case['kwargs']['started_raw'] == started_raw
    assert not (case['root'] / 'received-instruction.txt').exists()
    assert sentinel.read_bytes() == b'must not be consumed or changed'
    if cwd.is_symlink() or cwd.exists():
        cwd.unlink()
    saved.rename(cwd)
    case['kwargs']['verify_launch'] = lambda: None
    with pytest.raises(ValueError, match='one-use'):
        case['runner'].execute_child(**case['kwargs'])


def test_actual_resource_close_error_updates_evidence_and_is_terminal(tail_host, monkeypatch):
    host = tail_host
    host.close_input()
    close_selector = host.channel.selector.close
    error = OSError('invented error after actual selector close')
    host.expected_cleanup_error = error
    closes = []

    def close_then_fail():
        close_selector()
        closes.append(True)
        raise error

    monkeypatch.setattr(host.channel.selector, 'close', close_then_fail)
    with pytest.raises(OSError) as first:
        host.channel.close_after_process_termination()
    assert first.value is error
    report = host.channel.close_report()
    assert report['capture_complete'] is False
    assert report['cleanup_error'] == 'OSError'
    assert report['tail_capture_complete'] is True
    assert report['worker_shutdown_complete'] is True
    for close in (host.channel.close, host.channel.close_after_process_termination):
        with pytest.raises(OSError) as repeated:
            close()
        assert repeated.value is error
        assert host.channel.close_report() == report
    assert closes == [True]
