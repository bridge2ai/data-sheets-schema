#!/usr/bin/env python3
"""Purpose: locked, OS-offline U0 recorder trials; D92/#4354, 2026-11-06.

Inputs: reviewed historical measurement driver, frozen Git worktree, Python.
Outputs: new sibling wrapper/trial evidence and a temporary coordination lock.
This wrapper never chooses a native executable or changes the 180/900s limits.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import stat
import subprocess
import sys
import time


EXEC_ROOT = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
LOCK_PATH = EXEC_ROOT / 'plans/native_quiet_window.lock'
PROFILE = Path(__file__).with_name('native_u0_offline_20261106.sb')
OBSERVER = Path(__file__).with_name('native_u0_host_observer_20261106.py')
HOST_PS = Path('/bin/ps')
SANDBOX = Path('/usr/bin/sandbox-exec')
SETTLING_SECONDS = 60
IDLE_GATE_SECONDS = 60
CLEANUP_SECONDS = 120
OBSERVER_STOP_SECONDS = 15
OBSERVER_READY_SECONDS = 15
PROTOCOL_AMENDMENT = (
    'Lead ruling 2026-11-06 after U0-R2 in '
    'notes/coordination/2026-11-06-codex-native-u0.md: the unchanged /bin/ps '
    'host observer runs separately without a sandbox; the driver and every '
    'descendant retain deny network*. Gate thresholds and 180/900s limits are unchanged.')
PROTOCOL_AMENDMENT_2 = (
    'Lead ruling 2, 2026-11-06 in notes/coordination/2026-11-06-codex-native-u0.md: '
    'one unchanged neutral recorder run on the diagnostic-only copy may bypass '
    'quiet-host qualification for CPU-time attribution. The quiet-window lock, '
    'network denial, credential removal and 180/900s limits remain mandatory. '
    'Wall time is contended and establishes no helper timing pass or fail; the '
    'strict quiet-host gate is deferred, not waived for timing claims.')


def utc_now():
    return datetime.now(timezone.utc)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def write_new(path, value):
    with Path(path).open('xb') as stream:
        stream.write(json_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())


class QuietLock:
    """Cooperative lock: never replace an existing or changed lock."""

    def __init__(self, path, seconds, trial):
        self.path = Path(path)
        self.fd = None
        started = utc_now()
        self.document = {
            'format': 'native_u0_quiet_window_v1', 'pid': os.getpid(),
            'start_utc': started.isoformat(),
            'expected_end_utc': (started + timedelta(seconds=seconds)).isoformat(),
            'owner_nonce': secrets.token_hex(24), 'trial': trial,
        }
        self.raw = json_bytes(self.document)

    def acquire(self):
        if self.fd is not None:
            raise RuntimeError('lock already acquired')
        self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                          | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        self.identity = os.fstat(self.fd)
        try:
            offset = 0
            while offset < len(self.raw):
                written = os.write(self.fd, self.raw[offset:])
                if written <= 0:
                    raise OSError('incomplete lock write')
                offset += written
            os.fsync(self.fd)
        except BaseException:
            os.close(self.fd)
            self.fd = None
            raise  # Keep partial evidence; never guess ownership on retry.

    def release(self):
        if self.fd is None:
            raise RuntimeError('no owned lock to release')
        try:
            current = self.path.lstat()
            if (not stat.S_ISREG(current.st_mode)
                    or (current.st_dev, current.st_ino)
                    != (self.identity.st_dev, self.identity.st_ino)
                    or self.path.read_bytes() != self.raw):
                raise RuntimeError('quiet lock changed; retained for coordination review')
            self.path.unlink()
        finally:
            os.close(self.fd)
            self.fd = None

    def retain(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def clean_environment(home, temporary):
    """Construct from literals, not an inherited provider-variable blacklist."""
    return {
        'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
        'HOME': str(home), 'TMPDIR': str(temporary) + '/',
        'LANG': 'C', 'LC_ALL': 'C', 'TZ': 'UTC', 'PYTHONUTF8': '1',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_ADDOPTS': '',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
        'UV_OFFLINE': '1', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
        'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
    }


def sandbox_prefix(profile, tree, python):
    return [str(SANDBOX), '-D', 'FROZEN_TREE=' + str(tree),
            '-D', 'HOST_SAMPLES=' + str(profile.parent / 'host-samples.jsonl'), '-f', str(profile),
            str(python), '-S', '-P', '-B']


def driver_command(args, profile, observer_pid):
    command = sandbox_prefix(profile, args.tree, args.python) + [str(args.driver),
        '--tree', str(args.tree), '--target', args.target,
        '--output', str(args.output), '--trial', args.trial,
        '--python', str(args.python), '--idle-seconds', '60', '--mode', args.mode,
        '--plugin-autoload', 'disabled', '--driver-seconds', str(args.driver_seconds),
        '--host-samples', str(profile.parent / 'host-samples.jsonl'),
        '--host-observer-pid', str(observer_pid)]
    if args.idle_only:
        command.append('--idle-only')
    return command


def observer_command(python, samples, max_seconds):
    return [str(python), '-S', '-P', '-B', str(OBSERVER),
            '--samples', str(samples), '--max-seconds', str(max_seconds)]


def wait_observer_ready(observer, samples, ps_sha256):
    """Wait boundedly for exact, complete metadata from the separate observer."""
    deadline = time.monotonic() + OBSERVER_READY_SECONDS
    while True:
        if observer.poll() is not None:
            raise RuntimeError('host observer exited before metadata was ready')
        try:
            identity = samples.lstat()
        except FileNotFoundError:
            identity = None
        if identity is not None:
            if not stat.S_ISREG(identity.st_mode) or samples.resolve(strict=True) != samples:
                raise ValueError('host samples must be an exact regular file')
            with samples.open('rb') as stream:
                line = stream.readline(65537)
            after = samples.lstat()
            if (identity.st_dev, identity.st_ino) != (after.st_dev, after.st_ino):
                raise ValueError('host samples changed identity during readiness check')
            if len(line) > 65536:
                raise ValueError('host observer metadata exceeds bound')
            if line.endswith(b'\n'):
                metadata = json.loads(line)
                if (not isinstance(metadata, dict)
                        or metadata.get('kind') != 'observer_start'
                        or metadata.get('observer_pid') != observer.pid
                        or metadata.get('ps_sha256') != ps_sha256):
                    raise ValueError('host observer metadata does not match launched observer')
                return {'device': identity.st_dev, 'inode': identity.st_ino,
                        'metadata_sha256': hashlib.sha256(line).hexdigest()}
        if time.monotonic() >= deadline:
            raise TimeoutError('host observer metadata not ready within 15 seconds')
        time.sleep(0.1)


def network_self_check(output):
    """Verify OS refusal of local bind; never send a packet or contact a host."""
    result = {'format': 'native_u0_network_denial_v1', 'pid': os.getpid(),
              'checked_at': utc_now().isoformat(), 'network_bind_denied': False}
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
    except OSError as exc:
        result.update(errno=exc.errno, exception=type(exc).__name__)
        result['network_bind_denied'] = exc.errno == errno.EPERM
    finally:
        if sock is not None:
            sock.close()
    write_new(output, result)
    return 0 if result['network_bind_denied'] else 1


class Interrupted(BaseException):
    def __init__(self, signum):
        self.signum = signum


def stop_child(child):
    """Stop the driver process; its exit code does not prove descendant cleanup."""
    if child is None:
        return True
    if child.poll() is not None:
        return child.returncode >= 0  # A killed driver cannot attest descendant cleanup.
    try:
        os.killpg(child.pid, signal.SIGINT)
    except ProcessLookupError:
        return True
    try:
        child.wait(timeout=CLEANUP_SECONDS)
        return True
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait(timeout=15)
        return False  # Driver's descendants could survive; retain quiet lock.


def stop_observer(observer):
    """Stop only our observer session and attest its terminal process state."""
    state = {'process_stopped': observer is None, 'forced': False, 'returncode': None,
             'exited_before_stop': False}
    if observer is None:
        return state
    if observer.poll() is not None:
        state.update(process_stopped=True, returncode=observer.returncode,
                     exited_before_stop=True)
        return state
    try:
        # Let an in-flight read-only ps/sysctl finish, so the observer can emit end.
        observer.send_signal(signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        observer.wait(timeout=OBSERVER_STOP_SECONDS)
    except subprocess.TimeoutExpired:
        state['forced'] = True
        try:
            os.killpg(observer.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            observer.wait(timeout=OBSERVER_STOP_SECONDS)
        except subprocess.TimeoutExpired as exc:
            state['error'] = type(exc).__name__ + ': observer not reaped after forced stop'
    state.update(process_stopped=observer.poll() is not None,
                 returncode=observer.returncode)
    return state


def observer_cleanup_proof(path, observer_pid, readiness):
    """Require an unchanged sample file and a normal, counted terminal marker."""
    path = Path(path)
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or path.resolve(strict=True) != path
            or not 0 < before.st_size <= 2_000_000_000):
        raise ValueError('observer samples must be an exact bounded regular file')
    if (readiness is None or (before.st_dev, before.st_ino)
            != (readiness['device'], readiness['inode'])):
        raise ValueError('observer samples lack verified original file identity')
    digest = hashlib.sha256()
    count = 0
    end = None
    with path.open('rb') as stream:
        first = stream.readline(65537)
        if hashlib.sha256(first).hexdigest() != readiness['metadata_sha256']:
            raise ValueError('observer metadata changed after readiness check')
        digest.update(first)
        while line := stream.readline(16_000_001):
            if len(line) > 16_000_000 or not line.endswith(b'\n'):
                raise ValueError('observer sample line is incomplete or exceeds bound')
            digest.update(line)
            row = json.loads(line)
            if not isinstance(row, dict) or row.get('observer_pid') != observer_pid or end is not None:
                raise ValueError('observer evidence has foreign PID or follows terminal marker')
            if row.get('kind') == 'sample':
                count += 1
                if type(row.get('sequence')) is not int or row['sequence'] != count:
                    raise ValueError('observer sample sequence is not contiguous')
            elif row.get('kind') == 'observer_end':
                if (row.get('ps_unchanged') is not True or row.get('reason') != 'signal'
                        or type(row.get('samples')) is not int or row['samples'] != count):
                    raise ValueError('observer terminal proof has wrong count, reason or ps identity')
                end = row
            else:
                raise ValueError('observer evidence contains error or unexpected record')
    after = path.lstat()
    identity = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(before, key) != getattr(after, key) for key in identity):
        raise ValueError('observer evidence changed during terminal verification')
    if end is None:
        raise ValueError('observer evidence lacks terminal observer_end proof')
    return {'path': str(path), 'sha256': digest.hexdigest(), 'samples': count,
            'observer_pid': observer_pid, 'ps_unchanged': True, 'reason': end['reason']}


def driver_cleanup_proof(path):
    """Read the driver's exact saved cleanup/source proof, not its exit code."""
    path = Path(path)
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or path.resolve(strict=True) != path
            or not 0 < before.st_size <= 64_000_000):
        raise ValueError('driver outcome must be an exact bounded regular file')
    raw = path.read_bytes()
    after = path.lstat()
    identity = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(before, key) != getattr(after, key) for key in identity):
        raise ValueError('driver outcome changed during verification')
    document = json.loads(raw)
    if not isinstance(document, dict):
        raise ValueError('driver outcome must be a JSON object')
    if document.get('cleanup_verified') is not True:
        raise ValueError('driver outcome lacks explicit cleanup_verified true')
    if document.get('source_unchanged') is not True:
        raise ValueError('driver outcome lacks explicit source_unchanged true')
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(),
            'cleanup_verified': True, 'source_unchanged': True,
            'worker_returncode': document.get('returncode')}


def resolve_arguments(args):
    if args.mode == 'cpu-profile' and args.idle_only:
        raise ValueError('cpu-profile is a diagnostic recorder run, not an idle-only gate')
    if (args.mode == 'cpu-profile') != (args.target == 'cpu-profile'):
        raise ValueError('CPU profiling requires its exact diagnostic target; baseline modes exclude it')
    args.tree = args.tree.resolve(strict=True)
    args.output = args.output.resolve(strict=True)
    args.driver = args.driver.resolve(strict=True)
    args.python = args.python.absolute()  # Keep the selected venv spelling.
    if not args.python.is_file() or not os.access(args.python, os.X_OK):
        raise ValueError('selected Python is not an executable file')
    if not args.python.resolve(strict=True).name.startswith('python'):
        raise ValueError('U0 accepts a Python interpreter, never a native executable')
    root = Path(__file__).resolve().parents[2]
    if (not args.tree.is_relative_to(EXEC_ROOT) or args.tree == EXEC_ROOT
            or not args.output.is_relative_to(EXEC_ROOT) or args.output == EXEC_ROOT
            or args.output.is_relative_to(args.tree) or args.output.is_relative_to(root)):
        raise ValueError('frozen source and external evidence must be isolated under d4d-executions')
    if not args.tree.is_dir() or not args.output.is_dir():
        raise ValueError('source and evidence parent must already be directories')
    if (not args.trial or len(args.trial) > 80
            or not args.trial[0].isalnum()
            or any(not (c.isascii() and (c.isalnum() or c in '._-')) for c in args.trial)):
        raise ValueError('invalid exclusive trial name')
    if (args.output / args.trial).exists():
        raise ValueError('trial evidence already exists')
    if not 900 <= args.driver_seconds <= 7200:
        raise ValueError('outer driver watchdog must be 900–7200 seconds')


def run(args):
    resolve_arguments(args)
    wrapper = args.output / (args.trial + '.wrapper')
    wrapper.mkdir(mode=0o700, exist_ok=False)
    home, temporary = wrapper / 'home', wrapper / 'tmp'
    home.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    profile_raw = args.sandbox_profile.read_bytes()
    if (b'(deny network*)' not in profile_raw or
            b'(deny file-write* (literal (param "HOST_SAMPLES")))' not in profile_raw):
        raise ValueError('reviewed sandbox profile must deny network* and host-sample writes')
    profile = wrapper / 'sandbox.sb'
    with profile.open('xb') as stream:
        stream.write(profile_raw)
    env = clean_environment(home, temporary)
    selfcheck = sandbox_prefix(profile, args.tree, args.python) + [
        str(Path(__file__).resolve()), '--network-self-check', str(wrapper / 'network-self-check.json')]
    settling_seconds = 0 if args.mode == 'cpu-profile' else SETTLING_SECONDS
    # Grace + configured gate allowance + watchdog + cleanup + preflight/source.
    # The gate allowance remains conservative when CPU profiling bypasses the gate.
    budget = (settling_seconds + IDLE_GATE_SECONDS + CLEANUP_SECONDS
              + 2 * OBSERVER_STOP_SECONDS + 60
              + (0 if args.idle_only else args.driver_seconds))
    started_monotonic = time.monotonic()
    lock = QuietLock(LOCK_PATH, budget, args.trial)
    result = {'format': 'native_u0_wrapper_result_v1', 'status': 'not_started',
              'started_at': utc_now().isoformat(), 'lock_released': False,
              'helper_limit_seconds': 180, 'attempt_limit_seconds': 900}
    child = observer = None
    acquired = False
    old_handlers = {}
    exit_code = 1

    def interrupted(signum, _frame):
        raise Interrupted(signum)

    plan = {
        'command': None, 'driver_pid': None, 'observer_pid': None,
        'observer_command': None, 'host_samples': str(wrapper / 'host-samples.jsonl'),
        'protocol_amendment': PROTOCOL_AMENDMENT,
        'protocol_amendment_2': PROTOCOL_AMENDMENT_2 if args.mode == 'cpu-profile' else None,
        'mode': args.mode, 'quiet_gate_required': args.mode != 'cpu-profile',
        'observer_helper_sha256': hashlib.sha256(OBSERVER.read_bytes()).hexdigest(),
        'host_ps_path': str(HOST_PS), 'host_ps_sha256': hashlib.sha256(HOST_PS.read_bytes()).hexdigest(),
        'network_self_check_command': selfcheck,
        'sandbox_profile_sha256': hashlib.sha256(profile_raw).hexdigest(),
        'driver_sha256': hashlib.sha256(args.driver.read_bytes()).hexdigest(),
        'wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'retained_environment_names': sorted(env),
        'home': str(home), 'temporary': str(temporary), 'lock': lock.document,
        'lock_budget_seconds': budget, 'cooperative_settling_seconds': settling_seconds,
        'idle_gate_seconds': IDLE_GATE_SECONDS, 'cleanup_reserve_seconds': CLEANUP_SECONDS,
        'observer_cleanup_reserve_seconds': 2 * OBSERVER_STOP_SECONDS,
        'scope': 'synthetic peer only; exact native-binary exclusion audited separately',
    }
    write_new(wrapper / 'plan-intent.json', plan)
    try:
        lock.acquire()
        acquired = True
        write_new(wrapper / 'lock-created.json', lock.document)
        for signum in (signal.SIGINT, signal.SIGTERM):
            old_handlers[signum] = signal.signal(signum, interrupted)
        with (wrapper / 'network-self-check.log').open('xb') as log:
            checked = subprocess.run(selfcheck, env=env, cwd=args.tree,
                                     stdout=log, stderr=subprocess.STDOUT, timeout=30)
        result['network_self_check_returncode'] = checked.returncode
        check = json.loads((wrapper / 'network-self-check.json').read_bytes())
        result['network_bind_denied'] = check.get('network_bind_denied') is True
        if checked.returncode or check.get('network_bind_denied') is not True:
            raise RuntimeError('OS network denial not established; no gate or trial launched')
        if profile.read_bytes() != profile_raw:
            raise RuntimeError('sandbox profile changed before driver launch')
        result['quiet_settling_started_at'] = utc_now().isoformat()
        result['quiet_settling_seconds'] = settling_seconds
        result['quiet_settling_skipped'] = args.mode == 'cpu-profile'
        if settling_seconds:
            time.sleep(settling_seconds)
        result['quiet_settling_finished_at'] = utc_now().isoformat()
        driver_wait = (budget - (time.monotonic() - started_monotonic)
                       - CLEANUP_SECONDS - 2 * OBSERVER_STOP_SECONDS)
        if driver_wait <= 0:
            raise TimeoutError('lock budget exhausted before driver launch')
        observer_max = max(1, int(budget - (time.monotonic() - started_monotonic)))
        plan['observer_command'] = observer_command(
            args.python, wrapper / 'host-samples.jsonl', observer_max)
        with (wrapper / 'observer.log').open('xb') as observer_log:
            observer = subprocess.Popen(plan['observer_command'], env=env, cwd=wrapper,
                stdout=subprocess.DEVNULL, stderr=observer_log, start_new_session=True)
        plan['observer_pid'] = observer.pid
        plan['observer_max_seconds'] = observer_max
        write_new(wrapper / 'observer-started.json', {
            'pid': observer.pid, 'command': plan['observer_command'],
            'started_at': utc_now().isoformat(), 'max_seconds': observer_max})
        plan['observer_readiness'] = wait_observer_ready(
            observer, wrapper / 'host-samples.jsonl', plan['host_ps_sha256'])
        driver_wait = (budget - (time.monotonic() - started_monotonic)
                       - CLEANUP_SECONDS - 2 * OBSERVER_STOP_SECONDS)
        if driver_wait <= 0:
            raise TimeoutError('lock budget exhausted during observer startup')
        command = driver_command(args, profile, observer.pid)
        plan['command'] = command
        with (wrapper / 'driver.log').open('xb') as log:
            child = subprocess.Popen(command, env=env, cwd=args.tree, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            result.update(status='running', driver_pid=child.pid)
            plan['driver_pid'] = child.pid
            result['returncode'] = child.wait(timeout=driver_wait)
        result['status'] = 'driver_completed'
        exit_code = result['returncode']
    except Interrupted as exc:
        result.update(status='interrupted', signal=exc.signum)
        exit_code = 128 + exc.signum
    except BaseException as exc:
        result.update(status='wrapper_failed', error=type(exc).__name__ + ': ' + str(exc))
        exit_code = 1
    finally:
        for signum in old_handlers:
            signal.signal(signum, signal.SIG_IGN)
        process_stopped = False
        try:
            process_stopped = stop_child(child)
        except BaseException as exc:
            result['cleanup_error'] = type(exc).__name__ + ': ' + str(exc)
        result['driver_process_stopped'] = process_stopped
        cleanup_known = process_stopped
        if child is not None:
            try:
                result['driver_cleanup_proof'] = driver_cleanup_proof(
                    args.output / args.trial / 'outcome.json')
            except BaseException as exc:
                cleanup_known = False
                result['cleanup_proof_error'] = type(exc).__name__ + ': ' + str(exc)
        result['driver_cleanup_completed'] = cleanup_known
        observer_state = {'process_stopped': False}
        try:
            observer_state = stop_observer(observer)
        except BaseException as exc:
            result['observer_cleanup_error'] = type(exc).__name__ + ': ' + str(exc)
        result['observer_cleanup'] = observer_state
        if observer_state.get('error'):
            result['observer_cleanup_error'] = observer_state['error']
        observer_clean = observer is None
        if observer is not None:
            try:
                if (not observer_state['process_stopped'] or observer_state.get('forced')
                        or observer_state.get('exited_before_stop')
                        or observer_state.get('returncode') != 0):
                    raise ValueError('observer did not complete normal requested termination')
                result['observer_cleanup_proof'] = observer_cleanup_proof(
                    wrapper / 'host-samples.jsonl', observer.pid, plan.get('observer_readiness'))
                observer_clean = True
            except BaseException as exc:
                result.setdefault('observer_cleanup_error', type(exc).__name__ + ': ' + str(exc))
                exit_code = 1
        result['observer_cleanup_completed'] = observer_clean
        cleanup_known = cleanup_known and observer_clean
        if acquired:
            try:
                if cleanup_known:
                    lock.release()
                    result['lock_released'] = True
                else:
                    lock.retain()
                    result['lock_retained_reason'] = (
                        result.get('cleanup_proof_error') or result.get('cleanup_error')
                        or result.get('observer_cleanup_error')
                        or 'driver cleanup uncertain after forced termination; do not delete automatically')
            except BaseException as exc:
                result['lock_error'] = type(exc).__name__ + ': ' + str(exc)
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)
        result['finished_at'] = utc_now().isoformat()
        for key in ('observer_pid', 'observer_command', 'observer_helper_sha256',
                    'host_ps_path', 'host_ps_sha256', 'sandbox_profile_sha256',
                    'protocol_amendment', 'protocol_amendment_2', 'mode',
                    'quiet_gate_required', 'host_samples'):
            result[key] = plan[key]
        write_new(wrapper / 'plan.json', plan)
        write_new(wrapper / 'outcome.json', result)
        print(json.dumps({'wrapper': str(wrapper), **result}, sort_keys=True), flush=True)
    if acquired and not result['lock_released']:
        return 1
    return exit_code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network-self-check', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--driver', type=Path)
    parser.add_argument('--tree', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--trial')
    parser.add_argument('--target', choices=('current', 'original', 'delivery', 'cpu-profile'), default='current')
    parser.add_argument('--driver-seconds', type=int, default=1800)
    parser.add_argument('--mode', choices=('idle', 'load-diagnostic', 'cpu-profile'), default='idle')
    parser.add_argument('--idle-only', action='store_true')
    parser.add_argument('--sandbox-profile', type=Path, default=PROFILE)
    args = parser.parse_args(argv)
    if args.network_self_check is not None:
        return network_self_check(args.network_self_check)
    if any(getattr(args, name) is None for name in ('python', 'driver', 'tree', 'output', 'trial')):
        parser.error('--python, --driver, --tree, --output and --trial are required')
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
