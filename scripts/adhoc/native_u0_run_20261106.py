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
SANDBOX = Path('/usr/bin/sandbox-exec')
SETTLING_SECONDS = 60
IDLE_GATE_SECONDS = 60
CLEANUP_SECONDS = 120


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
    return [str(SANDBOX), '-D', 'FROZEN_TREE=' + str(tree), '-f', str(profile),
            str(python), '-S', '-P', '-B']


def driver_command(args, profile):
    command = sandbox_prefix(profile, args.tree, args.python) + [str(args.driver),
        '--tree', str(args.tree), '--target', args.target,
        '--output', str(args.output), '--trial', args.trial,
        '--python', str(args.python), '--idle-seconds', '60', '--mode', args.mode,
        '--plugin-autoload', 'disabled', '--driver-seconds', str(args.driver_seconds)]
    if args.idle_only:
        command.append('--idle-only')
    return command


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
    if b'(deny network*)' not in profile_raw:
        raise ValueError('reviewed sandbox profile must explicitly deny network*')
    profile = wrapper / 'sandbox.sb'
    with profile.open('xb') as stream:
        stream.write(profile_raw)
    env = clean_environment(home, temporary)
    command = driver_command(args, profile)
    selfcheck = sandbox_prefix(profile, args.tree, args.python) + [
        str(Path(__file__).resolve()), '--network-self-check', str(wrapper / 'network-self-check.json')]
    # 60s grace + 60s sampled gate + watchdog + 120s cleanup + 60s preflight/source.
    budget = (SETTLING_SECONDS + IDLE_GATE_SECONDS + CLEANUP_SECONDS + 60
              + (0 if args.idle_only else args.driver_seconds))
    started_monotonic = time.monotonic()
    lock = QuietLock(LOCK_PATH, budget, args.trial)
    result = {'format': 'native_u0_wrapper_result_v1', 'status': 'not_started',
              'started_at': utc_now().isoformat(), 'lock_released': False,
              'helper_limit_seconds': 180, 'attempt_limit_seconds': 900}
    child = None
    acquired = False
    old_handlers = {}
    exit_code = 1

    def interrupted(signum, _frame):
        raise Interrupted(signum)

    write_new(wrapper / 'plan.json', {
        'command': command, 'network_self_check_command': selfcheck,
        'sandbox_profile_sha256': hashlib.sha256(profile_raw).hexdigest(),
        'driver_sha256': hashlib.sha256(args.driver.read_bytes()).hexdigest(),
        'wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'retained_environment_names': sorted(env),
        'home': str(home), 'temporary': str(temporary), 'lock': lock.document,
        'lock_budget_seconds': budget, 'cooperative_settling_seconds': SETTLING_SECONDS,
        'idle_gate_seconds': IDLE_GATE_SECONDS, 'cleanup_reserve_seconds': CLEANUP_SECONDS,
        'scope': 'synthetic peer only; exact native-binary exclusion audited separately',
    })
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
        if checked.returncode or check.get('network_bind_denied') is not True:
            raise RuntimeError('OS network denial not established; no gate or trial launched')
        if profile.read_bytes() != profile_raw:
            raise RuntimeError('sandbox profile changed before driver launch')
        result['quiet_settling_started_at'] = utc_now().isoformat()
        result['quiet_settling_seconds'] = SETTLING_SECONDS
        time.sleep(SETTLING_SECONDS)
        result['quiet_settling_finished_at'] = utc_now().isoformat()
        driver_wait = budget - (time.monotonic() - started_monotonic) - CLEANUP_SECONDS
        if driver_wait <= 0:
            raise TimeoutError('lock budget exhausted before driver launch')
        with (wrapper / 'driver.log').open('xb') as log:
            child = subprocess.Popen(command, env=env, cwd=args.tree, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            result.update(status='running', driver_pid=child.pid)
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
        if acquired:
            try:
                if cleanup_known:
                    lock.release()
                    result['lock_released'] = True
                else:
                    lock.retain()
                    result['lock_retained_reason'] = (
                        result.get('cleanup_proof_error') or result.get('cleanup_error')
                        or 'driver cleanup uncertain after forced termination; do not delete automatically')
            except BaseException as exc:
                result['lock_error'] = type(exc).__name__ + ': ' + str(exc)
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)
        result['finished_at'] = utc_now().isoformat()
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
    parser.add_argument('--target', choices=('current', 'original', 'delivery'), default='current')
    parser.add_argument('--driver-seconds', type=int, default=1800)
    parser.add_argument('--mode', choices=('idle', 'load-diagnostic'), default='idle')
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
