"""U0/#4354 coordination and offline-wrapper contracts; 2026-11-06."""
from __future__ import annotations

import argparse
import errno
import hashlib
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


@pytest.mark.parametrize('mode', ['idle', 'load-diagnostic', 'cpu-profile'])
def test_command_preserves_isolation_gate_and_limits(tmp_path, mode):
    args = argparse.Namespace(tree=tmp_path / 'tree', python=Path('/python'),
        driver=tmp_path / 'driver.py', output=tmp_path / 'evidence', trial='canary',
        target='current', driver_seconds=1800, mode=mode, idle_only=False)
    command = wrapper.driver_command(args, tmp_path / 'sandbox.sb', 98765)
    assert command[:7] == ['/usr/bin/sandbox-exec', '-D', 'FROZEN_TREE=' + str(args.tree),
        '-D', 'HOST_SAMPLES=' + str(tmp_path / 'host-samples.jsonl'), '-f', str(tmp_path / 'sandbox.sb')]
    assert command[8:11] == ['-S', '-P', '-B']
    assert command[command.index('--host-samples') + 1] == str(tmp_path / 'host-samples.jsonl')
    assert command[command.index('--host-observer-pid') + 1] == '98765'
    assert command[command.index('--idle-seconds') + 1] == '60'
    assert command[command.index('--mode') + 1] == mode
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
    assert '(deny file-write* (literal (param "HOST_SAMPLES")))' in text


def run_args(tmp_path, monkeypatch):
    tree, output = tmp_path / 'frozen', tmp_path / 'evidence'
    tree.mkdir()
    output.mkdir()
    monkeypatch.setattr(wrapper, 'EXEC_ROOT', tmp_path)
    monkeypatch.setattr(wrapper, 'LOCK_PATH', tmp_path / 'quiet.lock')
    monkeypatch.setattr(wrapper.time, 'sleep', lambda seconds: None)
    observer = tmp_path / 'observer.py'
    observer.write_text('# Non-executed mock observer fixture.\n')
    monkeypatch.setattr(wrapper, 'OBSERVER', observer)
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


class MockObserver:
    pid, returncode = 123455, None
    signals = None

    def poll(self):
        return self.returncode

    def wait(self, timeout):
        assert wrapper.LOCK_PATH.exists()
        assert timeout == wrapper.OBSERVER_STOP_SECONDS
        with self.samples.open('a') as stream:
            stream.write(json.dumps({'kind': 'observer_end', 'observer_pid': self.pid,
                'samples': 0, 'ps_unchanged': True, 'reason': 'signal'}) + '\n')
        self.returncode = 0
        return 0

    def send_signal(self, signum):
        if self.signals is not None:
            self.signals.append((self.pid, signum))


def mock_children(monkeypatch, driver, observer=None, signals=None):
    """Exercise real wrapper lifecycle with two independently owned fake sessions."""
    observer = observer or MockObserver()
    observer.signals = signals
    launched = []
    def launch(command, **kwargs):
        assert kwargs['start_new_session'] is True
        assert kwargs['env']['PATH'] == '/usr/bin:/bin:/usr/sbin:/sbin'
        assert 'ANTHROPIC_API_KEY' not in kwargs['env']
        if not launched:
            assert command[1:5] == ['-S', '-P', '-B', str(wrapper.OBSERVER)]
            assert kwargs['stdout'] == wrapper.subprocess.DEVNULL
            assert command[command.index('--samples') + 1] == str(kwargs['cwd'] / 'host-samples.jsonl')
            assert int(command[command.index('--max-seconds') + 1]) > 0
            samples = Path(command[command.index('--samples') + 1])
            observer.samples = samples
            samples.write_text(json.dumps({'kind': 'observer_start', 'observer_pid': observer.pid,
                'ps_sha256': hashlib.sha256(wrapper.HOST_PS.read_bytes()).hexdigest()}) + '\n')
            launched.append('observer')
            return observer
        assert launched == ['observer']
        assert command[0] == str(wrapper.SANDBOX)
        assert command[command.index('--host-observer-pid') + 1] == str(observer.pid)
        launched.append('driver')
        return driver
    monkeypatch.setattr(wrapper.subprocess, 'Popen', launch)
    monkeypatch.setattr(wrapper.os, 'killpg',
        lambda pid, sig: signals.append((pid, sig)) if signals is not None else None)
    return launched


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
    mock_children(monkeypatch, Child())
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
    mock_children(monkeypatch, Child(), signals=actions)
    assert wrapper.run(args) == 128 + signal.SIGTERM
    assert actions == [(123456, signal.SIGINT), 'reaped', (123455, signal.SIGTERM)]
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
    mock_children(monkeypatch, Child())
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
    launched = mock_children(monkeypatch, Child())
    assert wrapper.run(args) == 0
    assert not wrapper.LOCK_PATH.exists()
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert outcome['driver_cleanup_completed'] is True
    assert outcome['driver_cleanup_proof']['cleanup_verified'] is True
    assert outcome['driver_cleanup_proof']['source_unchanged'] is True
    assert outcome['quiet_settling_started_at'] <= outcome['quiet_settling_finished_at']
    assert outcome['quiet_settling_seconds'] == 60
    assert launched == ['observer', 'driver']
    assert outcome['observer_cleanup']['process_stopped'] is True
    assert outcome['observer_cleanup']['forced'] is False
    assert outcome['observer_cleanup_completed'] is True
    assert outcome['observer_cleanup_proof']['samples'] == 0
    assert outcome['network_bind_denied'] is True
    plan = json.loads((args.output / 'canary.wrapper/plan.json').read_bytes())
    assert plan['driver_pid'] == 123456
    assert plan['observer_pid'] == outcome['observer_pid'] == 123455
    assert plan['observer_command'] == outcome['observer_command']
    for key in ('observer_helper_sha256', 'host_ps_sha256', 'sandbox_profile_sha256'):
        assert len(plan[key]) == 64
        assert outcome[key] == plan[key]
    assert 'Lead ruling 2026-11-06 after U0-R2' in plan['protocol_amendment']
    assert plan['host_samples'] == str(args.output / 'canary.wrapper/host-samples.jsonl')
    assert plan['observer_cleanup_reserve_seconds'] == 30
    assert plan['quiet_gate_required'] is True
    assert plan['protocol_amendment_2'] is None


@pytest.mark.parametrize('cleanup_verified', [True, False])
@pytest.mark.parametrize('mode,target', [('cpu-profile', 'cpu-profile'),
    ('cpu-pair', 'pair-control'), ('cpu-pair', 'pair-treatment')])
def test_cpu_profile_skips_settling_but_keeps_lock_and_cleanup_proof(
        tmp_path, monkeypatch, cleanup_verified, mode, target):
    args = run_args(tmp_path, monkeypatch)
    args.mode = mode
    args.target = target
    mock_network_check(monkeypatch)
    monkeypatch.setattr(wrapper.time, 'sleep', lambda _: pytest.fail('CPU profile waited for quiet'))
    class Child:
        pid, returncode = 123456, 0
        def wait(self, timeout):
            assert wrapper.LOCK_PATH.exists()
            write_driver_proof(args, cleanup_verified=cleanup_verified)
            return 0
        def poll(self):
            return 0
    launched = mock_children(monkeypatch, Child())
    assert wrapper.run(args) == (0 if cleanup_verified else 1)
    assert wrapper.LOCK_PATH.exists() is (not cleanup_verified)
    assert launched == ['observer', 'driver']
    plan = json.loads((args.output / 'canary.wrapper/plan.json').read_bytes())
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert plan['command'][plan['command'].index('--mode') + 1] == mode
    assert plan['cooperative_settling_seconds'] == outcome['quiet_settling_seconds'] == 0
    assert outcome['quiet_settling_skipped'] is True
    assert outcome['network_bind_denied'] is True
    assert outcome['helper_limit_seconds'] == 180
    assert outcome['attempt_limit_seconds'] == 900
    assert plan['quiet_gate_required'] is outcome['quiet_gate_required'] is False
    assert plan['protocol_amendment_2'] == outcome['protocol_amendment_2']
    assert 'Lead ruling 2, 2026-11-06' in outcome['protocol_amendment_2']
    assert 'Wall time is contended' in outcome['protocol_amendment_2']
    if mode == 'cpu-pair':
        assert plan['causal_pair_authority'] == outcome['causal_pair_authority']
        assert 'one control/treatment' in outcome['causal_pair_authority']


def test_cpu_profile_refuses_idle_only_combination(tmp_path, monkeypatch):
    args = run_args(tmp_path, monkeypatch)
    args.mode, args.idle_only = 'cpu-profile', True
    with pytest.raises(ValueError, match='not an idle-only gate'):
        wrapper.resolve_arguments(args)


@pytest.mark.parametrize('mode,target', [('cpu-profile', 'current'), ('idle', 'cpu-profile'),
                                        ('load-diagnostic', 'cpu-profile')])
def test_cpu_mode_requires_its_diagnostic_target(tmp_path, monkeypatch, mode, target):
    args = run_args(tmp_path, monkeypatch)
    args.mode, args.target = mode, target
    with pytest.raises(ValueError, match='exact diagnostic target'):
        wrapper.resolve_arguments(args)


@pytest.mark.parametrize('mode_option, expected', [([], 'idle'), (['--mode', 'cpu-profile'], 'cpu-profile')])
def test_cli_cpu_profile_is_explicit_and_idle_stays_default(monkeypatch, mode_option, expected):
    parsed = []
    monkeypatch.setattr(wrapper, 'run', lambda args: parsed.append(args) or 0)
    assert wrapper.main(['--python', '/python', '--driver', '/driver.py', '--tree', '/tree',
        '--output', '/output', '--trial', 'neutral', *mode_option]) == 0
    assert parsed[0].mode == expected


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
    mock_children(monkeypatch, Child())
    assert wrapper.run(args) == 1
    assert wrapper.LOCK_PATH.exists()
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert outcome['driver_cleanup_proof']['cleanup_verified'] is True
    assert outcome['driver_cleanup_completed'] is False
    assert 'forced termination' in outcome['lock_retained_reason']


def test_observer_that_cannot_be_reaped_keeps_lock_despite_driver_proof(tmp_path, monkeypatch):
    args = run_args(tmp_path, monkeypatch)
    mock_network_check(monkeypatch)
    actions = []
    class Child:
        pid, returncode = 123456, 0
        def wait(self, timeout):
            write_driver_proof(args)
            return 0
        def poll(self):
            return 0
    class StuckObserver(MockObserver):
        def wait(self, timeout):
            assert wrapper.LOCK_PATH.exists()
            raise wrapper.subprocess.TimeoutExpired('observer', timeout)
    mock_children(monkeypatch, Child(), StuckObserver(), signals=actions)
    assert wrapper.run(args) == 1
    assert wrapper.LOCK_PATH.exists()
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert outcome['driver_cleanup_completed'] is True
    assert outcome['observer_cleanup']['process_stopped'] is False
    assert 'TimeoutExpired' in outcome['lock_retained_reason']
    assert actions == [(123455, signal.SIGTERM), (123455, signal.SIGKILL)]


def test_early_observer_exit_is_nonzero_even_when_driver_attests_cleanup(tmp_path, monkeypatch):
    args = run_args(tmp_path, monkeypatch)
    mock_network_check(monkeypatch)
    class Child:
        pid, returncode = 123456, 0
        def wait(self, timeout):
            write_driver_proof(args)
            observer.returncode = 0
            return 0
        def poll(self):
            return 0
    observer = MockObserver()
    mock_children(monkeypatch, Child(), observer)
    assert wrapper.run(args) == 1
    assert wrapper.LOCK_PATH.exists()
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert outcome['observer_cleanup']['exited_before_stop'] is True
    assert outcome['observer_cleanup_completed'] is False


def test_forced_observer_cleanup_records_kill_and_requires_terminal_state(tmp_path, monkeypatch):
    args = run_args(tmp_path, monkeypatch)
    mock_network_check(monkeypatch)
    class Child:
        pid, returncode = 123456, 0
        def wait(self, timeout):
            write_driver_proof(args)
            return 0
        def poll(self):
            return 0
    class StubbornObserver(MockObserver):
        attempts = 0
        def wait(self, timeout):
            assert wrapper.LOCK_PATH.exists()
            self.attempts += 1
            if self.attempts == 1:
                raise wrapper.subprocess.TimeoutExpired('observer', timeout)
            self.returncode = -9
            return -9
    mock_children(monkeypatch, Child(), StubbornObserver())
    assert wrapper.run(args) == 1
    assert wrapper.LOCK_PATH.exists()
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert outcome['observer_cleanup']['forced'] is True
    assert outcome['observer_cleanup']['process_stopped'] is True
    assert outcome['observer_cleanup']['returncode'] == -9
    assert outcome['observer_cleanup_completed'] is False


@pytest.mark.parametrize('failure', ['missing-end', 'wrong-count', 'changed-ps', 'killed'])
def test_observer_terminal_proof_required_before_unlock(tmp_path, monkeypatch, failure):
    args = run_args(tmp_path, monkeypatch)
    mock_network_check(monkeypatch)
    class Child:
        pid, returncode = 123456, 0
        def wait(self, timeout):
            write_driver_proof(args)
            if failure == 'killed':
                observer.returncode = -9
            return 0
        def poll(self):
            return 0
    class UnprovenObserver(MockObserver):
        def wait(self, timeout):
            self.returncode = 0
            if failure != 'missing-end':
                with self.samples.open('a') as stream:
                    stream.write(json.dumps({'kind': 'observer_end', 'observer_pid': self.pid,
                        'samples': 1 if failure == 'wrong-count' else 0,
                        'ps_unchanged': failure != 'changed-ps', 'reason': 'signal'}) + '\n')
            return 0
    observer = UnprovenObserver()
    mock_children(monkeypatch, Child(), observer)
    assert wrapper.run(args) == 1
    assert wrapper.LOCK_PATH.exists()
    outcome = json.loads((args.output / 'canary.wrapper/outcome.json').read_bytes())
    assert outcome['driver_cleanup_completed'] is True
    assert outcome['observer_cleanup_completed'] is False
    assert outcome['lock_retained_reason'] == outcome['observer_cleanup_error']


@pytest.mark.parametrize('failure', ['wrong-pid', 'wrong-ps', 'symlink', 'exited'])
def test_observer_readiness_requires_exact_matching_metadata(tmp_path, failure):
    observer = MockObserver()
    samples = tmp_path / 'samples.jsonl'
    document = {'kind': 'observer_start', 'observer_pid': observer.pid, 'ps_sha256': 'a' * 64}
    if failure == 'wrong-pid':
        document['observer_pid'] += 1
    elif failure == 'wrong-ps':
        document['ps_sha256'] = 'b' * 64
    elif failure == 'exited':
        observer.returncode = 1
    raw = json.dumps(document) + '\n'
    if failure == 'symlink':
        other = tmp_path / 'other.jsonl'
        other.write_text(raw)
        samples.symlink_to(other)
    else:
        samples.write_text(raw)
    with pytest.raises((ValueError, RuntimeError)):
        wrapper.wait_observer_ready(observer, samples, 'a' * 64)


def test_observer_readiness_timeout_is_bounded(tmp_path, monkeypatch):
    moments = iter([0, wrapper.OBSERVER_READY_SECONDS])
    monkeypatch.setattr(wrapper.time, 'monotonic', lambda: next(moments))
    monkeypatch.setattr(wrapper.time, 'sleep', lambda _: pytest.fail('wait exceeded bound'))
    with pytest.raises(TimeoutError, match='within 15 seconds'):
        wrapper.wait_observer_ready(MockObserver(), tmp_path / 'missing.jsonl', 'a' * 64)
