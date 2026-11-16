"""D156 process ownership tests using an ordinary sleeping Python child only."""
import os
import signal
import sys
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_launch_sequence as sequence


def test_prepared_failure_kills_group_and_reaps_leader(tmp_path):
    state = sequence._SequenceSignals()
    steps = []
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', steps, state)
    owned.step['argv'] = [sys.executable, '-I', '-c', 'import time; time.sleep(60)']
    try:
        owned.start()
        assert os.getpgid(owned.child.pid) == owned.child.pid
        assert owned.child.poll() is None
        raise ValueError('synthetic capture refusal')
    except ValueError:
        owned.close()
    assert owned.child.returncode == -signal.SIGKILL
    assert steps[0]['return_code'] == -signal.SIGKILL
    assert steps[0]['completed_at'] is not None
    with pytest.raises(ProcessLookupError):
        os.killpg(owned.child.pid, 0)
    assert owned.stdout.closed and owned.stderr.closed


def test_synthetic_capture_is_absent_until_preparation_callback(tmp_path, monkeypatch):
    from tests.test_native_subscription_capture import component
    from tests.utils.native_synthetic_evidence import authority_for
    args, value = component(tmp_path, monkeypatch)
    ci = tmp_path / 'ci.json'
    ci.write_bytes(b'{"synthetic":true}')
    issued = authority_for(args['registration_raw'], ci, tmp_path, defer_capture=True)
    assert not list(tmp_path.rglob('capture.json'))
    assert not list(tmp_path.rglob('invented-subscription.json'))
    assert not os.path.exists(value['attempt_directory'])
    pin = issued['prepare_capture'](None)
    assert len(list(tmp_path.rglob('capture.json'))) == 1
    saved = sequence.guard.read_regular(pin['guard_path'])
    assert sequence.guard.sha(saved) == pin['guard_sha256']
    assert not os.path.exists(value['attempt_directory'])


def test_controller_preparation_has_no_reservation_writes_and_closes_on_refusal(monkeypatch):
    from data_sheets_schema import native_shared_controller_orchestration as controller
    adapter = object.__new__(controller.CallbackAdapter)
    adapter._activated = False
    adapter.value = {'dependencies': {}}
    adapter.execution = {'synthetic': True}
    adapter.registration_raw = b'synthetic'
    adapter.spec = adapter.selection = object()
    events = []
    def controls(_):
        yield object()
    def preload(*args):
        events.append('prepared')
        try:
            yield SimpleNamespace(classifier=object(), state=object(), phase=object(), catalogs=object(),
                admission=SimpleNamespace(check_active=lambda: events.append('checked')),
                capture=SimpleNamespace(activate_admitted=lambda *args: events.append('reserved')))
        finally:
            events.append('closed')
    monkeypatch.setattr(controller.control_loading, 'loaded_controls', contextmanager(controls))
    monkeypatch.setattr(controller.registration, 'verified',
        lambda *args, **kwargs: adapter.execution)
    monkeypatch.setattr(controller.callback_loading, 'preloaded_callbacks', contextmanager(preload))
    monkeypatch.setattr(controller.render, 'commands', lambda spec: ())
    adapter.prepare_before_capture()
    assert events == ['prepared'] and not adapter._activated
    adapter.close_prepared()
    assert events == ['prepared', 'closed'] and not adapter._activated
    assert not hasattr(adapter, '_classifier_scope')


def test_spawn_failure_closes_reserved_streams(tmp_path, monkeypatch):
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', [], sequence._SequenceSignals())
    def refused(*args, **kwargs):
        raise OSError('synthetic spawn failure')
    monkeypatch.setattr(sequence.subprocess, 'Popen', refused)
    try:
        with pytest.raises(OSError, match='synthetic spawn failure'):
            owned.start()
    finally:
        owned.close()
    assert owned.child is None
    assert owned.stdout.closed and owned.stderr.closed


def test_exited_worker_is_not_reaped_before_failure_group_cleanup(tmp_path):
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', [], sequence._SequenceSignals())
    owned.step['argv'] = [sys.executable, '-I', '-c', 'raise SystemExit(7)']
    try:
        owned.start()
        deadline = time.monotonic() + 10
        while owned._exit_status() is None:
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert owned._exit_status() == 7
        assert owned.child.returncode is None
        # A second WNOWAIT observation succeeds: the PID is still owned.
        assert owned._exit_status() == 7
    finally:
        owned.close()
    assert owned.child.returncode == 7


def test_cleanup_attempts_reap_even_if_group_signal_fails(tmp_path, monkeypatch):
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', [], sequence._SequenceSignals())
    reaped = []
    owned.child = SimpleNamespace(pid=123, wait=lambda: reaped.append(True) or 9)
    owned._exit_status = lambda: None
    def refuse(*args):
        raise PermissionError('synthetic signal refusal')
    monkeypatch.setattr(sequence.os, 'killpg', refuse)
    with pytest.raises(PermissionError, match='synthetic signal refusal'):
        owned.close()
    assert reaped == [True] and owned.step['return_code'] == 9


def test_cleanup_never_signals_an_unverifiable_group_after_reaping(tmp_path, monkeypatch):
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', [], sequence._SequenceSignals())
    reaped, calls = [], []
    owned.child = SimpleNamespace(pid=123, wait=lambda: reaped.append(True) or 7)
    owned._exit_status = lambda: 7
    def signal_group(pid, signum):
        calls.append(signum)
        if signum:
            raise PermissionError('synthetic group refusal')
        assert reaped
    monkeypatch.setattr(sequence.os, 'killpg', signal_group)
    with pytest.raises(PermissionError, match='synthetic group refusal'):
        owned.close()
    assert calls == [signal.SIGKILL, 0]
    assert owned.step['return_code'] == 7
