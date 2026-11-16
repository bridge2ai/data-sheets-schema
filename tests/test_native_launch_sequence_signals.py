"""Issue 6208: synthetic parent-only signals and slow command cleanup.

The real-process witnesses execute only a copied package and fabricated
native_generation. No native binary, provider, capture or generation runs.
"""
from pathlib import Path
from types import SimpleNamespace
import json
import os
import signal
import subprocess
import sys
import time

import pytest

from data_sheets_schema import native_launch_sequence as seq
from data_sheets_schema import native_host_power as host_power
from tests import test_native_launch_sequence as fixture
from tests.test_native_launch_sequence import deny_real_commands  # noqa: F401


@pytest.mark.parametrize('signum', [signal.SIGINT, signal.SIGTERM])
def test_signal_before_claim_preserves_journal_and_starts_no_child(tmp_path, monkeypatch, signum):
    paths = fixture.paths(tmp_path)
    journal = tmp_path / 'word-state'
    before = {path.relative_to(journal): path.read_bytes() for path in journal.rglob('*') if path.is_file()}
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    original = host_power.sequence_start
    def interrupted(path, stamp):
        original(path, stamp)
        os.kill(os.getpid(), signum)
    monkeypatch.setattr(host_power, 'sequence_start', interrupted)
    calls = fixture.fake_commands(monkeypatch, paths)
    assert fixture.run_sequence(fixture.argv(paths)) == 1
    saved = fixture.record(paths)
    assert calls == [] and saved['steps'] == []
    assert saved['stop_reason'] == 'signal ' + str(signum)
    assert saved['signals_received'] == [signum]
    assert saved['signal_forwarding_errors'] == []
    assert before == {path.relative_to(journal): path.read_bytes() for path in journal.rglob('*') if path.is_file()}
    assert all(signal.getsignal(sig) is handler for sig, handler in previous.items())


@pytest.mark.parametrize('when', ['spawn', 'wait'])
def test_signal_during_command_ownership_is_forwarded_once_then_synced(tmp_path, monkeypatch, when):
    paths = fixture.paths(tmp_path)
    calls = fixture.fake_commands(monkeypatch, paths)
    original_spawn = seq.subprocess.Popen
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    forwarded, waited, synced = [], [], []
    original_sync = os.fsync
    def sync(fd):
        synced.append(fd)
        return original_sync(fd)
    monkeypatch.setattr(os, 'fsync', sync)
    def spawn(*args, **kwargs):
        child = original_spawn(*args, **kwargs)
        if args[0][6] == 'launch':
            return child
        child.send_signal = forwarded.append
        child.returncode = None
        before_sync = len(synced)
        polls = []
        def wait(timeout):
            assert timeout == seq.COMMAND_WAIT_POLL_SECONDS
            assert len(synced) == before_sync, 'streams must sync only after child reap'
            polls.append(True)
            if len(polls) == 1:
                if when == 'wait':
                    os.kill(os.getpid(), signal.SIGINT)
                os.kill(os.getpid(), signal.SIGTERM)
                raise subprocess.TimeoutExpired(args[0], timeout)
            kwargs['stderr'].write(b'cleanup completed\n')
            waited.append(True)
            child.returncode = 23
            return child.returncode
        child.wait = wait
        if when == 'spawn':
            os.kill(os.getpid(), signal.SIGINT)
        return child
    monkeypatch.setattr(seq.subprocess, 'Popen', spawn)
    assert fixture.run_sequence(fixture.argv(paths)) == 1
    saved = fixture.record(paths)
    assert len(calls) == 2 and waited == [True]
    assert forwarded == [signal.SIGINT]
    assert saved['signals_received'] == [signal.SIGINT, signal.SIGTERM]
    assert saved['stop_reason'] == 'signal ' + str(signal.SIGINT)
    assert saved['steps'][1]['return_code'] == 23
    assert Path(saved['steps'][1]['stderr_path']).read_bytes().endswith(b'cleanup completed\n')
    assert not (paths['packet-directory'] / seq.OUTPUTS[1]).exists()
    assert all(signal.getsignal(sig) is handler for sig, handler in previous.items())


@pytest.mark.parametrize('failure', [ProcessLookupError, PermissionError])
def test_signal_delivery_failure_never_aborts_reap(tmp_path, failure):
    received, waited = [], []
    def deliver(signum):
        received.append(signum)
        raise failure('private diagnostic')
    child = SimpleNamespace(send_signal=deliver, wait=lambda timeout: waited.append(True) or 7)
    state = seq._SequenceSignals()
    state.receive(signal.SIGTERM, None)
    with state:
        assert state.wait(child) == 7
    assert received == [signal.SIGTERM] and waited == [True]
    assert state.forwarding_errors == ([] if failure is ProcessLookupError else ['PermissionError'])
    with pytest.raises(KeyboardInterrupt, match='signal'):
        state.check()


@pytest.mark.parametrize('failure', [KeyboardInterrupt, InterruptedError])
def test_wait_retries_interrupt_without_killing_child(failure):
    forwarded, waits = [], []
    def wait(timeout):
        assert timeout == seq.COMMAND_WAIT_POLL_SECONDS
        waits.append(True)
        if len(waits) == 1:
            raise failure()
        return 5
    child = SimpleNamespace(send_signal=forwarded.append, wait=wait)
    state = seq._SequenceSignals()
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    with state:
        assert state.wait(child) == 5
    assert len(waits) == 2
    assert forwarded == ([signal.SIGINT] if failure is KeyboardInterrupt else [])
    assert all(signal.getsignal(sig) is handler for sig, handler in previous.items())


def test_spawn_failure_restores_both_previous_handlers(tmp_path, monkeypatch):
    paths = fixture.paths(tmp_path)
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    fixture.fake_commands(monkeypatch, paths, fail_exception=seq.COMMANDS[0])
    assert fixture.run_sequence(fixture.argv(paths)) == 1
    assert fixture.record(paths)['stop_reason'] == 'OSError'
    assert all(signal.getsignal(sig) is handler for sig, handler in previous.items())


FAKE_COMMAND = r'''import hashlib, json, os, signal, sys, time
from pathlib import Path

def main():
    name = sys.argv[1]
    flags = dict(zip(sys.argv[2::2], sys.argv[3::2]))
    auxiliary = Path(flags['--registration']).parent / 'signal-fixture'
    config = json.loads((auxiliary / 'config.json').read_text())
    with (auxiliary / 'commands.jsonl').open('a') as stream:
        stream.write(json.dumps(name) + '\n'); stream.flush(); os.fsync(stream.fileno())
    if name == 'launch':
        from data_sheets_schema import native_prepared_worker as worker
        raw = Path(flags['--registration']).read_bytes()
        attempt = json.loads(raw)['registration']['attempt_directory']
        prepared = worker.publish_prepared(flags['--prepared-directory'], registration_raw=raw,
            attempt=attempt, source_sha256='a' * 64, environment_sha256='b' * 64, max_age_seconds=1200)
        worker.wait_proceed(flags['--prepared-directory'], prepared_raw=prepared,
            registration_raw=raw, attempt=attempt, max_age_seconds=1200)
    if name == config['interrupt_step']:
        received = []
        def receive(signum, frame):
            received.append(signum)
        signal.signal(signal.SIGINT, receive)
        signal.signal(signal.SIGTERM, receive)
        (auxiliary / 'ready').write_text(str(os.getpid()))
        deadline = time.monotonic() + 12
        while not received and time.monotonic() < deadline:
            time.sleep(0.01)
        if not received:
            raise SystemExit(91)
        began = time.monotonic()
        (auxiliary / 'cleanup-started').write_text('ready for repeated signal')
        time.sleep(0.7)
        (auxiliary / 'final.json').write_text(json.dumps({
            'signals_received': received, 'cleanup_seconds': time.monotonic() - began,
            'pid': os.getpid()}))
        sys.stderr.write('slow cleanup complete\n'); sys.stderr.flush()
    if name == 'capture-subscription-event':
        word = Path(flags['--launch-word']).read_bytes()
        path = Path(flags['--output-directory']) / 'captures' / hashlib.sha256(word).hexdigest() / 'capture-1/capture.json'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'{}')
        body = {'capture_manifest': str(path), 'sha256': hashlib.sha256(b'{}').hexdigest()}
    elif name == 'prepare-subscription-guard-v2':
        path = Path(flags['--output']); path.write_bytes(b'{}')
        body = {'path': str(path), 'guard_sha256': hashlib.sha256(b'{}').hexdigest()}
    elif name == 'launch':
        body = {'state': 'completed_pending_independent_review', 'runtime_gates_passed': True}
    else:
        raise AssertionError('unexpected command')
    print(json.dumps({'command': name, 'result': body}), flush=True)
    return 0
'''


def copied_signal_package(tmp_path):
    root = tmp_path / 'isolated'
    package = root / 'src/data_sheets_schema'
    package.mkdir(parents=True)
    (package / '__init__.py').write_bytes(b'')
    for name in ('native_launch_sequence', 'native_subscription_guard', 'native_sequence_start',
                 'native_launch_entry', 'native_capture_words', 'native_subscription_guard_v2',
                 'native_u4b_policy', 'native_run_limits', 'native_shared_runtime_values',
                 'native_runtime_profiles', 'native_host_power', 'native_path_identity',
                 'native_prepared_worker'):
        (package / (name + '.py')).write_bytes((seq.SOURCE_ROOT / 'src/data_sheets_schema' / (name + '.py')).read_bytes())
    (package / 'native_generation.py').write_text(FAKE_COMMAND)
    return root


def await_file(path, process, stderr):
    deadline = time.monotonic() + 20
    while not path.is_file():
        assert process.poll() is None, stderr.read_text()
        assert time.monotonic() < deadline, 'synthetic signal witness did not reach ' + path.name
        time.sleep(0.01)


@pytest.mark.parametrize('signum', [signal.SIGINT, signal.SIGTERM])
@pytest.mark.parametrize('step', [seq.COMMANDS[0], seq.COMMANDS[2]])
def test_parent_signal_waits_for_slow_fake_cleanup_and_retains_record(tmp_path, signum, step):
    paths = fixture.paths(tmp_path)
    root = copied_signal_package(tmp_path)
    auxiliary = tmp_path / 'signal-fixture'; auxiliary.mkdir()
    (auxiliary / 'config.json').write_text(json.dumps({'interrupt_step': step}))
    bootstrap = '''import sys, signal
from pathlib import Path
sys.path.insert(0, sys.argv.pop(1))
auxiliary = Path(sys.argv.pop(1))
from data_sheets_schema import native_host_power, native_launch_entry
native_host_power.probe = lambda: {'source':'ac','battery_percent':90,'lid':'closed'}
previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
status = native_launch_entry.main(sys.argv[1:])
assert all(signal.getsignal(sig) is handler for sig, handler in previous.items())
(auxiliary / 'handlers-restored').write_text('yes')
raise SystemExit(status)
'''
    stderr_path = auxiliary / 'parent.stderr.txt'
    with (auxiliary / 'parent.stdout.txt').open('wb') as stdout, stderr_path.open('wb') as stderr:
        process = fixture.REAL_POPEN([sys.executable, '-I', '-B', '-c', bootstrap,
            str(root / 'src'), str(auxiliary), *fixture.argv(paths)], cwd=root,
            env={'PATH': '/usr/bin:/bin:/usr/sbin:/sbin'}, stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            await_file(auxiliary / 'ready', process, stderr_path)
            os.kill(process.pid, signum)
            await_file(auxiliary / 'cleanup-started', process, stderr_path)
            repeated = signal.SIGTERM if signum == signal.SIGINT else signal.SIGINT
            os.kill(process.pid, repeated)
            assert process.wait(timeout=20) == 1, stderr_path.read_text()
        finally:
            # Test-only cleanup of the exact copied supervisor. Its fake child
            # also has a finite readiness watchdog; no real controller runs.
            fixture.finish_copied_process(process)
    completed = json.loads((auxiliary / 'final.json').read_text())
    assert completed['cleanup_seconds'] > 0.25
    assert completed['signals_received'] == [signum]
    assert completed['pid'] == int((auxiliary / 'ready').read_text())
    assert (auxiliary / 'handlers-restored').read_text() == 'yes'
    saved = fixture.record(paths)
    assert saved['status'] == 'stopped' and saved['stop_reason'] == 'signal ' + str(signum)
    assert saved['signals_received'] == [signum, repeated]
    assert saved['signal_forwarding_errors'] == []
    expected = [seq.COMMANDS[2], *seq.COMMANDS[:min(seq.COMMANDS.index(step) + 1, 2)]]
    assert [json.loads(line) for line in (auxiliary / 'commands.jsonl').read_text().splitlines()] == expected
    assert [item['step'] for item in saved['steps']] == expected
    interrupted = next(item for item in saved['steps'] if item['step'] == step)
    assert interrupted['return_code'] == 0
    assert Path(interrupted['stderr_path']).read_bytes() == b'slow cleanup complete\n'
    assert json.loads(Path(interrupted['output_path']).read_bytes())['command'] == step
    for name in (seq.OUTPUTS[2], seq.OUTPUTS[0], seq.OUTPUTS[1])[len(expected):]:
        assert not (paths['packet-directory'] / name).exists()


def test_signal_after_reap_before_returncode_never_forwards_recycled_pid():
    state = seq._SequenceSignals()
    forwarded = []
    child = SimpleNamespace(returncode=None, send_signal=forwarded.append)
    def wait(timeout):
        assert timeout == seq.COMMAND_WAIT_POLL_SECONDS
        # Simulate waitpid having already released this PID before Popen
        # assigns returncode. Only a latch is safe in the signal handler.
        os.kill(os.getpid(), signal.SIGTERM)
        assert child.returncode is None and forwarded == []
        child.returncode = 0
        return 0
    child.wait = wait
    with state:
        assert state.wait(child) == 0
    assert state.received == [signal.SIGTERM] and forwarded == []
    with pytest.raises(KeyboardInterrupt, match='signal'):
        state.check()


@pytest.mark.parametrize('boundary', ['completion_clock', 'serialization'])
def test_final_signal_cutoff_keeps_status_reason_and_list_consistent(tmp_path, monkeypatch, boundary):
    paths = fixture.paths(tmp_path)
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    clock_calls_after_result = []
    armed = []
    def produced(name, document):
        if name == seq.COMMANDS[1]:
            armed.append(True)
    fixture.fake_commands(monkeypatch, paths, mutate=produced)
    clock = seq._utc_now
    def sampled():
        stamp = clock()
        if armed:
            clock_calls_after_result.append(True)
            # Guard completion, launch completion, then the final clock.
            if boundary == 'completion_clock' and len(clock_calls_after_result) == 3:
                os.kill(os.getpid(), signal.SIGINT)
                os.kill(os.getpid(), signal.SIGTERM)
        return stamp
    monkeypatch.setattr(seq, '_utc_now', sampled)
    canonical = fixture.guard.canonical
    serialized = []
    def encode(value):
        if type(value) is dict and value.get('kind') == seq.SEQUENCE_KIND:
            serialized.append(True)
            if boundary == 'serialization':
                os.kill(os.getpid(), signal.SIGINT)
                os.kill(os.getpid(), signal.SIGTERM)
        return canonical(value)
    monkeypatch.setattr(fixture.guard, 'canonical', encode)
    result = fixture.run_sequence(fixture.argv(paths))
    saved = fixture.record(paths)
    assert serialized == [True] and len(saved['steps']) == 3
    assert saved['signal_recording_cutoff'] == 'after completion clock sample, before immutable record serialization'
    if boundary == 'completion_clock':
        assert result == 1 and saved['status'] == 'stopped'
        assert saved['stop_reason'] == 'signal ' + str(signal.SIGINT)
        assert saved['signals_received'] == [signal.SIGINT, signal.SIGTERM]
    else:
        assert result == 0 and saved['status'] == 'completed'
        assert saved['stop_reason'] is None and saved['signals_received'] == []
    assert all(signal.getsignal(sig) is handler for sig, handler in previous.items())


@pytest.mark.parametrize('initial', ['timeout', 'interrupt'])
@pytest.mark.parametrize('cleanup_timeout', [False, True])
def test_copied_witness_failure_always_reaps_its_owned_process(tmp_path, monkeypatch, initial, cleanup_timeout):
    first_error = (subprocess.TimeoutExpired(['copied-fake-only'], 20)
                   if initial == 'timeout' else KeyboardInterrupt('synthetic witness interrupt'))
    calls = []
    child = SimpleNamespace(returncode=None)
    def communicate(timeout=None):
        calls.append(('communicate', timeout))
        count = sum(name == 'communicate' for name, _ in calls)
        if count == 1:
            raise first_error
        if count == 2 and cleanup_timeout:
            raise subprocess.TimeoutExpired(['copied-fake-only'], timeout)
        child.returncode = -signal.SIGKILL if cleanup_timeout else -signal.SIGTERM
        return b'', b''
    child.communicate = communicate
    child.poll = lambda: child.returncode
    child.send_signal = lambda signum: calls.append(('signal', signum))
    child.kill = lambda: calls.append(('kill', None))
    monkeypatch.setattr(fixture, 'REAL_POPEN', lambda *args, **kwargs: child)
    # Exercise the real witness's try/finally, not an isolated imitation.
    with pytest.raises(type(first_error)) as caught:
        fixture.test_isolated_real_subprocess_uses_only_copied_fake_command(tmp_path, 'native_launch_entry')
    assert caught.value is first_error
    assert child.returncode is not None
    assert calls[:3] == [('communicate', 20), ('signal', signal.SIGTERM), ('communicate', 20)]
    assert calls[3:] == ([('kill', None), ('communicate', None)] if cleanup_timeout else [])
