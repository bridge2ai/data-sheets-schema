"""U0/#4354 coordination and offline-wrapper contracts; 2026-11-06."""
from __future__ import annotations

import argparse
import errno
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys

import pytest


SCRIPT = Path(__file__).parents[1] / 'scripts/adhoc/native_u0_run_20261106.py'
spec = importlib.util.spec_from_file_location('native_u0_wrapper', SCRIPT)
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)


def test_exclusive_lock_records_owner_and_does_not_replace(tmp_path):
    path = tmp_path / 'quiet.lock'
    first = wrapper.QuietLock(path, 180, 'one')
    first.acquire()
    raw = path.read_bytes()
    doc = json.loads(raw)
    assert doc['pid'] == os.getpid()
    assert doc['owner_nonce']
    assert doc['expected_end_utc'] > doc['start_utc']
    with pytest.raises(FileExistsError):
        wrapper.QuietLock(path, 180, 'two').acquire()
    assert path.read_bytes() == raw
    first.release()
    assert not path.exists()


@pytest.mark.parametrize('change', ['replace', 'mutate', 'symlink'])
def test_release_never_removes_replaced_or_changed_lock(tmp_path, change):
    path = tmp_path / 'quiet.lock'
    lock = wrapper.QuietLock(path, 180, 'one')
    lock.acquire()
    if change == 'mutate':
        path.write_bytes(b'new owner')
    else:
        path.unlink()
        if change == 'replace':
            path.write_bytes(lock.raw)  # Same content is not the same inode.
        else:
            other = tmp_path / 'other'
            other.write_bytes(lock.raw)
            path.symlink_to(other)
    with pytest.raises(RuntimeError, match='changed'):
        lock.release()
    assert path.exists()


def test_allowlisted_environment_removes_unknown_provider_secrets(tmp_path, monkeypatch):
    for name in ('ANTHROPIC_API_KEY', 'CBORG_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN',
                 'UNFORESEEN_VENDOR_SECRET', 'PYTHONPATH', 'PYTHONHOME', 'PYTEST_PLUGINS'):
        monkeypatch.setenv(name, 'should-not-be-inherited')
    env = wrapper.clean_environment(tmp_path / 'home', tmp_path / 'tmp')
    assert 'should-not-be-inherited' not in env.values()
    assert env['HOME'] == str(tmp_path / 'home')
    assert env['PATH'] == '/usr/bin:/bin:/usr/sbin:/sbin'
    assert env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] == '1'
    assert env['GIT_CONFIG_GLOBAL'] == os.devnull


def test_command_preserves_isolation_gate_and_limits(tmp_path):
    args = argparse.Namespace(tree=tmp_path / 'tree', python=Path('/python'),
        driver=tmp_path / 'driver.py', output=tmp_path / 'evidence', trial='canary',
        target='current', driver_seconds=1800, mode='idle', idle_only=False)
    command = wrapper.driver_command(args, tmp_path / 'sandbox.sb')
    assert command[:4] == ['/usr/bin/sandbox-exec', '-D', 'FROZEN_TREE=' + str(args.tree), '-f']
    assert command[6:9] == ['-S', '-P', '-B']
    assert command[command.index('--idle-seconds') + 1] == '60'
    assert command[command.index('--plugin-autoload') + 1] == 'disabled'
    assert '--worker' not in command
    assert '--helper-timeout' not in command
    assert '--deadline-seconds' not in command


def test_network_selfcheck_requires_eperm(tmp_path, monkeypatch):
    class Denied:
        def __init__(self, *args):
            raise OSError(errno.EPERM, 'denied')
    monkeypatch.setattr(wrapper.socket, 'socket', Denied)
    target = tmp_path / 'network.json'
    assert wrapper.network_self_check(target) == 0
    assert json.loads(target.read_bytes())['network_bind_denied'] is True


def test_unrelated_network_error_does_not_prove_sandbox(tmp_path, monkeypatch):
    class Broken:
        def __init__(self, *args):
            raise OSError(errno.EMFILE, 'unrelated failure')
    monkeypatch.setattr(wrapper.socket, 'socket', Broken)
    assert wrapper.network_self_check(tmp_path / 'network.json') == 1


def test_profile_denies_network_and_frozen_source_writes():
    text = wrapper.PROFILE.read_text()
    assert '(deny network*)' in text
    assert '(deny file-write* (subpath (param "FROZEN_TREE")))' in text


def run_args(tmp_path, monkeypatch):
    tree, output = tmp_path / 'frozen', tmp_path / 'evidence'
    tree.mkdir()
    output.mkdir()
    monkeypatch.setattr(wrapper, 'EXEC_ROOT', tmp_path)
    monkeypatch.setattr(wrapper, 'LOCK_PATH', tmp_path / 'quiet.lock')
    monkeypatch.setattr(wrapper.time, 'sleep', lambda seconds: None)
    return argparse.Namespace(tree=tree, output=output, driver=SCRIPT,
        python=Path(sys.executable), trial='canary', target='current',
        driver_seconds=1800, mode='idle', idle_only=False,
        sandbox_profile=wrapper.PROFILE)


def mock_network_check(monkeypatch, passed=True):
    def checked(command, **kwargs):
        wrapper.write_new(Path(command[-1]), {'network_bind_denied': passed})
        return argparse.Namespace(returncode=0 if passed else 1)
    monkeypatch.setattr(wrapper.subprocess, 'run', checked)


def write_driver_proof(args, **changes):
    target = args.output / args.trial / 'outcome.json'
    target.parent.mkdir(exist_ok=True)
    wrapper.write_new(target, {'cleanup_verified': True, 'source_unchanged': True,
                              'returncode': 0, **changes})


def test_failed_network_preflight_releases_lock_without_driver(tmp_path, monkeypatch):
    args = run_args(tmp_path, monkeypatch)
    mock_network_check(monkeypatch, False)
    monkeypatch.setattr(wrapper.subprocess, 'Popen', lambda *a, **k: pytest.fail('driver launched'))
    assert wrapper.run(args) == 1
    assert not wrapper.LOCK_PATH.exists()
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert outcome['lock_released'] is True
    assert outcome['status'] == 'wrapper_failed'


def test_successful_driver_cannot_hide_foreign_lock_replacement(tmp_path, monkeypatch):
    args = run_args(tmp_path, monkeypatch)
    mock_network_check(monkeypatch)
    class Child:
        pid, returncode = 123456, 0
        def wait(self, timeout):
            write_driver_proof(args)
            wrapper.LOCK_PATH.unlink()
            wrapper.LOCK_PATH.write_bytes(b'foreign owner')
            return 0
        def poll(self):
            return 0
    monkeypatch.setattr(wrapper.subprocess, 'Popen', lambda *a, **k: Child())
    assert wrapper.run(args) == 1
    assert wrapper.LOCK_PATH.read_bytes() == b'foreign owner'
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert outcome['returncode'] == 0
    assert outcome['lock_released'] is False
    assert 'changed' in outcome['lock_error']


def test_interruption_allows_driver_cleanup_before_releasing_lock(tmp_path, monkeypatch):
    args = run_args(tmp_path, monkeypatch)
    mock_network_check(monkeypatch)
    actions = []
    class Child:
        pid, returncode = 123456, None
        def wait(self, timeout):
            if timeout != 120:
                raise wrapper.Interrupted(signal.SIGTERM)
            assert wrapper.LOCK_PATH.exists()
            actions.append('reaped')
            write_driver_proof(args)
            self.returncode = 0
            return 0
        def poll(self):
            return self.returncode
    monkeypatch.setattr(wrapper.subprocess, 'Popen', lambda *a, **k: Child())
    monkeypatch.setattr(wrapper.os, 'killpg', lambda pid, sig: actions.append((pid, sig)))
    assert wrapper.run(args) == 128 + signal.SIGTERM
    assert actions == [(123456, signal.SIGINT), 'reaped']
    assert not wrapper.LOCK_PATH.exists()


@pytest.mark.parametrize('kind', [
    'missing', 'malformed', 'no-cleanup', 'negative-worker', 'source-changed',
    'truthy-cleanup', 'truthy-source', 'not-object',
])
def test_positive_driver_exit_without_strict_cleanup_proof_retains_lock(tmp_path, monkeypatch, kind):
    args = run_args(tmp_path, monkeypatch)
    mock_network_check(monkeypatch)
    class Child:
        pid, returncode = 123456, 1
        def wait(self, timeout):
            target = args.output / args.trial / 'outcome.json'
            target.parent.mkdir()
            if kind == 'missing':
                pass
            elif kind == 'malformed':
                target.write_bytes(b'{')
            elif kind == 'not-object':
                target.write_bytes(b'[]')
            else:
                value = {'cleanup_verified': True, 'source_unchanged': True}
                if kind == 'no-cleanup':
                    value.pop('cleanup_verified')
                elif kind == 'negative-worker':
                    value.update(cleanup_verified=False, returncode=-9)
                elif kind == 'source-changed':
                    value['source_unchanged'] = False
                elif kind == 'truthy-cleanup':
                    value['cleanup_verified'] = 1
                elif kind == 'truthy-source':
                    value['source_unchanged'] = 1
                wrapper.write_new(target, value)
            return self.returncode
        def poll(self):
            return self.returncode
    monkeypatch.setattr(wrapper.subprocess, 'Popen', lambda *a, **k: Child())
    assert wrapper.run(args) == 1
    assert wrapper.LOCK_PATH.exists()
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert outcome['driver_process_stopped'] is True
    assert outcome['driver_cleanup_completed'] is False
    assert outcome['lock_released'] is False
    assert outcome['cleanup_proof_error']
    assert outcome['lock_retained_reason'] == outcome['cleanup_proof_error']


def test_completed_gate_unlocks_only_with_verified_cleanup_and_source(tmp_path, monkeypatch):
    args = run_args(tmp_path, monkeypatch)
    args.idle_only = True
    mock_network_check(monkeypatch)
    events = []
    def sleep(seconds):
        assert wrapper.LOCK_PATH.exists()
        events.append(('settling', seconds))
    monkeypatch.setattr(wrapper.time, 'sleep', sleep)
    class Child:
        pid, returncode = 123456, 0
        def wait(self, timeout):
            assert events == [('settling', 60)]
            write_driver_proof(args, status='host_idle', returncode=None)
            return 0
        def poll(self):
            return 0
    monkeypatch.setattr(wrapper.subprocess, 'Popen', lambda *a, **k: Child())
    assert wrapper.run(args) == 0
    assert not wrapper.LOCK_PATH.exists()
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert outcome['driver_cleanup_completed'] is True
    assert outcome['driver_cleanup_proof']['cleanup_verified'] is True
    assert outcome['driver_cleanup_proof']['source_unchanged'] is True
    assert outcome['quiet_settling_started_at'] <= outcome['quiet_settling_finished_at']
    assert outcome['quiet_settling_seconds'] == 60


def test_forced_driver_stop_retains_lock_even_with_saved_proof(tmp_path, monkeypatch):
    args = run_args(tmp_path, monkeypatch)
    mock_network_check(monkeypatch)
    class Child:
        pid, returncode = 123456, -9
        def wait(self, timeout):
            write_driver_proof(args)
            return -9
        def poll(self):
            return -9
    monkeypatch.setattr(wrapper.subprocess, 'Popen', lambda *a, **k: Child())
    assert wrapper.run(args) == 1
    assert wrapper.LOCK_PATH.exists()
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert outcome['driver_cleanup_proof']['cleanup_verified'] is True
    assert outcome['driver_cleanup_completed'] is False
    assert 'forced termination' in outcome['lock_retained_reason']
