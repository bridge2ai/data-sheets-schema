"""One explicit native capture, guard and launch sequence; never retries.

Proposed amendment N1, not authorization to run. Inputs are explicit paths;
children use this source checkout and a fixed environment. Raw command outputs
are retained before interpretation. Completion still needs independent review.
Rewriting the trusted entry itself or the Python interpreter is out of scope.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time

from . import native_subscription_guard as guard
from . import native_host_power as host_power

SEQUENCE_KIND = 'd4d_native_launch_sequence'
SEQUENCE_VERSION = 1
MAX_COMMAND_OUTPUT_BYTES = 32 * 1024 * 1024
COMMAND_WAIT_POLL_SECONDS = 0.2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
COMMANDS = ('capture-subscription-event', 'prepare-subscription-guard-v2', 'launch')
OUTPUTS = ('capture-command.json', 'guard-command.json', 'launch-command.json')
START_FILENAME = 'sequence-start.json'
SCRIPT_FILENAME = 'sequence-script.py'
# -I excludes ambient PYTHONPATH/cwd; explicitly select this file's checkout.
BOOTSTRAP = ('import sys; sys.path.insert(0, sys.argv.pop(1)); '
             'from data_sheets_schema.native_generation import main; '
             'raise SystemExit(main())')
CHILD_ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': '/nonexistent',
             'LANG': 'C.UTF-8', 'GIT_CONFIG_GLOBAL': '/dev/null',
             'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_TERMINAL_PROMPT': '0',
             'GIT_NO_LAZY_FETCH': '1', 'GIT_NO_REPLACE_OBJECTS': '1'}


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _strict_utc(value):
    if type(value) is not str or re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z', value) is None:
        raise ValueError('delegated start times must be strict UTC timestamps')
    return datetime.fromisoformat(value[:-1] + '+00:00')


def _delegation(direction, confirmation, now):
    if (direction is None) != (confirmation is None):
        raise ValueError('delegated start needs both recorded times')
    if direction is None:
        return
    current = _strict_utc(now)
    for value in (direction, confirmation):
        seconds = (current - _strict_utc(value)).total_seconds()
        if not 0 <= seconds <= 1800:
            raise ValueError('delegated start must be within thirty minutes after both recorded times')


def _path(value):
    path = Path(value)
    if (not path.is_absolute() or str(path) != str(value)
            or path.parent.resolve(strict=True) != path.parent or path.is_symlink()):
        raise ValueError('sequence paths must be canonical, absolute and non-symlinked')
    return path


def _require_output_separation(packet, guard_path, capture_root, registration_raw):
    """Read captured entry bytes before any packet creation or journal write."""
    from .native_path_identity import overlaps
    from .native_u4b_policy import registered_policy
    value = guard.strict_json(registration_raw)['registration']
    reservations = [_path(value[name]) for name in ('attempt_directory', 'evidence_directory')]
    capture_state = Path(registered_policy(value['runtime'])['capture_state_directory'])
    if any(overlaps(packet, reserved) for reserved in (*reservations, capture_state)):
        raise ValueError('sequence packet overlaps registered reservation or capture state')
    if any(overlaps(guard_path, reserved) for reserved in (*reservations, capture_state)):
        raise ValueError('sequence guard overlaps registered reservation or capture state')
    # Capture intentionally writes inside its registered journal. Only this
    # exact equality is allowed; a sibling, ancestor or descendant is not it.
    if capture_root != capture_state:
        raise ValueError('sequence capture output differs from registered capture state')
    if any(overlaps(capture_root, reserved) for reserved in reservations):
        raise ValueError('sequence capture output overlaps a registered reservation')


def _new(path):
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb')


def _write_new(path, raw):
    with _new(path) as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _digest(raw, label):
    if type(raw) is not str or re.fullmatch('[0-9a-f]{64}', raw) is None:
        raise ValueError(label + ' must be a lowercase SHA-256')
    return raw


def _unchanged(inputs):
    for path, raw in inputs.items():
        if guard.read_regular(path, limit=MAX_COMMAND_OUTPUT_BYTES) != raw:
            raise ValueError('sequence input changed between commands')


class _SequenceSignals:
    """Defer interruption until the owned command has reaped and synced.

    The first signal is forwarded once to the exact command PID. Its fresh
    session prevents a terminal signal from reaching both parent and child.
    Child startup before its own cleanup handler is installed is not covered
    by this parent-side guarantee. The outcome uses one received-signal tuple
    captured after the completion clock sample and before record serialization.
    Later signals are deferred and cannot alter the already decided outcome.
    """

    def __init__(self):
        self.received = []
        self.forwarding_errors = []
        self._child = None
        self._forwarded = False
        self._previous = {}

    def _forward(self):
        if self._child is None or not self.received or self._forwarded:
            return
        # Ordinary control only: the handler never polls or signals a PID.
        # Latch before the call; another signal may arrive while it executes.
        self._forwarded = True
        try:
            self._child.send_signal(self.received[0])
        except ProcessLookupError:
            pass  # The command exited before delivery; it is still reaped.
        except BaseException as exc:
            # Keep cleanup running with bounded diagnostics, never arbitrary
            # exception text. A failed delivery does not permit a second send.
            self.forwarding_errors.append(type(exc).__name__)

    def receive(self, signum, _frame):
        # No process API here: waitpid may have reaped the child while Popen's
        # returncode is not set yet. Sending from this handler could hit a
        # recycled PID. Ordinary control forwards only between wait polls.
        self.received.append(signum)

    def check(self):
        if self.received:
            raise KeyboardInterrupt('native sequence received signal ' + str(self.received[0]))

    def wait(self, child):
        self._child = child
        try:
            while True:
                self._forward()  # Includes a signal latched during Popen.
                try:
                    return child.wait(timeout=COMMAND_WAIT_POLL_SECONDS)
                except (subprocess.TimeoutExpired, InterruptedError):
                    # Polling bounds signal-forwarding latency; it is not an
                    # overall cleanup deadline and never authorizes a kill.
                    continue
                except KeyboardInterrupt:
                    # Defensive support for an independently raised interrupt;
                    # our installed handlers themselves never raise.
                    self.receive(signal.SIGINT, None)
        finally:
            self._child = None

    def __enter__(self):
        if threading.current_thread() is not threading.main_thread():
            raise ValueError('native sequence requires main-thread signal ownership')
        self._previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
        try:
            for sig in self._previous:
                signal.signal(sig, self.receive)
        except BaseException:
            for sig, handler in self._previous.items():
                signal.signal(sig, handler)
            raise
        return self

    def __exit__(self, *_error):
        for sig, handler in self._previous.items():
            signal.signal(sig, handler)


def _run_step(command, flags, output, steps, interrupts):
    interrupts.check()
    argv = [sys.executable, '-I', '-B', '-c', BOOTSTRAP, str(SOURCE_ROOT / 'src'), command, *flags]
    stderr_path = output.with_suffix('.stderr.txt')
    step = {'step': command, 'argv': argv, 'started_at': _utc_now(),
            'completed_at': None, 'return_code': None, 'output_path': str(output),
            'stderr_path': str(stderr_path)}
    # Reserve both outputs before the command, including on spawn failure.
    with _new(output) as stdout, _new(stderr_path) as stderr:
        steps.append(step)
        try:
            interrupts.check()
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     cwd=SOURCE_ROOT, env=dict(CHILD_ENV), start_new_session=True)
            # No overall cleanup timeout, Popen context, kill or terminate:
            # the command owns its cleanup and registered execution deadline.
            step['return_code'] = interrupts.wait(child)
        finally:
            stdout.flush(); stderr.flush()
            os.fsync(stdout.fileno()); os.fsync(stderr.fileno())
            step['completed_at'] = _utc_now()
    interrupts.check()
    if step['return_code'] != 0:
        raise ValueError(command + ' exited nonzero; see retained command output')
    return _step_result(command, output, step)


def _step_result(command, output, step):
    raw = guard.read_regular(output, limit=MAX_COMMAND_OUTPUT_BYTES)
    step['output_sha256'] = guard.sha(raw)
    try:
        doc = guard.strict_json(raw)
    except ValueError as exc:
        raise ValueError(command + ' output is not strict JSON') from exc
    if type(doc) is not dict or doc.get('command') != command:
        raise ValueError(command + ' output lacks its exact command identity')
    body = doc.get('result')
    if type(body) is not dict or not body:
        raise ValueError(command + ' output lacks its result object')
    return body


class _PreparedStep:
    """Own the prepared launch process and its output until reaped."""

    def __init__(self, flags, output, steps, interrupts):
        self.output, self.interrupts = output, interrupts
        self.child = self.stdout = self.stderr = None
        self.complete = False
        self.proceed_possible = False
        argv = [sys.executable, '-I', '-B', '-c', BOOTSTRAP,
                str(SOURCE_ROOT / 'src'), 'launch', *flags]
        self.step = {'step': 'launch', 'argv': argv, 'started_at': _utc_now(),
            'completed_at': None, 'return_code': None, 'output_path': str(output),
            'stderr_path': str(output.with_suffix('.stderr.txt'))}
        steps.append(self.step)

    def start(self):
        self.interrupts.check()
        self.stdout = _new(self.output)
        self.stderr = _new(self.output.with_suffix('.stderr.txt'))
        self.child = subprocess.Popen(self.step['argv'], stdin=subprocess.DEVNULL,
            stdout=self.stdout, stderr=self.stderr, cwd=SOURCE_ROOT,
            env=dict(CHILD_ENV), start_new_session=True)

    def ready(self, directory, *, registration_raw, attempt, max_age_seconds):
        from .native_prepared_worker import require_prepared
        while True:
            self.interrupts.check()
            if self._exit_status() is not None:
                raise ValueError('prepared launch exited before proceed')
            if os.path.lexists(directory / 'prepared.json'):
                return require_prepared(directory, registration_raw=registration_raw,
                    attempt=attempt, max_age_seconds=max_age_seconds, pid=self.child.pid)
            time.sleep(COMMAND_WAIT_POLL_SECONDS)

    def _exit_status(self):
        # Keep the leader unreaped until group cleanup. Its retained PID pins
        # the group identity even after exit; never signal a recycled PID.
        status = os.waitid(os.P_PID, self.child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if status is None or status.si_pid == 0:
            return None
        return status.si_status if status.si_code == os.CLD_EXITED else -status.si_status

    def require_ready(self, directory, *, prepared_raw, registration_raw, attempt, max_age_seconds):
        from .native_prepared_worker import require_prepared
        self.interrupts.check()
        if self._exit_status() is not None:
            raise ValueError('prepared launch exited before proceed')
        if require_prepared(directory, registration_raw=registration_raw,
                attempt=attempt, max_age_seconds=max_age_seconds,
                pid=self.child.pid) != prepared_raw:
            raise ValueError('prepared record changed before proceed')

    def proceed(self, directory, **kwargs):
        from .native_prepared_worker import publish_proceed
        # Publication can fail after the link becomes visible to the worker.
        self.proceed_possible = True
        return publish_proceed(directory, **kwargs)

    def send_signal(self, signum):
        # Popen.send_signal polls (and can reap) first. This owner deliberately
        # retains the leader until close, so signal its exact retained PID.
        os.kill(self.child.pid, signum)

    def finish(self):
        self.interrupts._child = self
        try:
            while True:
                self.interrupts._forward()
                code = self._exit_status()
                if code is not None:
                    self.step['return_code'] = code
                    break
                time.sleep(COMMAND_WAIT_POLL_SECONDS)
        finally:
            self.interrupts._child = None
        self.interrupts.check()
        if self.step['return_code'] != 0:
            raise ValueError('prepared launch exited nonzero; see retained output')
        for stream in (self.stdout, self.stderr):
            stream.flush()
            os.fsync(stream.fileno())
        result = _step_result('launch', self.output, self.step)
        return result

    def _kill_group(self):
        try:
            os.killpg(self.child.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
        except PermissionError as error:
            refusal = error
        # Darwin can refuse a group containing only its zombie leader. Match
        # the existing transport rule: verify exit before reaping, then only
        # probe. A remaining or recycled group is a refusal, never a target.
        if self._exit_status() is None:
            raise refusal
        self.child.wait()
        deadline = time.monotonic() + 4
        while True:
            try:
                os.killpg(self.child.pid, 0)
            except ProcessLookupError:
                return
            except PermissionError:
                if time.monotonic() < deadline:
                    time.sleep(0.04)
                    continue
            raise refusal

    def close(self):
        try:
            if self.child is not None:
                try:
                    if not self.complete:
                        if self.proceed_possible:
                            # The native child owns a separate session. Let the
                            # worker's signal handler unwind transport cleanup;
                            # never kill its owner or impose a cleanup timeout.
                            try:
                                self.send_signal(signal.SIGTERM)
                            except ProcessLookupError:
                                pass
                        else:
                            self._kill_group()
                finally:
                    self.step['return_code'] = self.child.wait()
        finally:
            failure = None
            for stream in (self.stdout, self.stderr):
                if stream is not None:
                    try:
                        try:
                            stream.flush()
                            os.fsync(stream.fileno())
                        finally:
                            stream.close()
                    except BaseException as exc:
                        if failure is None:
                            failure = exc
            self.step['completed_at'] = _utc_now()
            if failure is not None:
                raise failure


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('registration', 'review', 'launch-word', 'account-choice', 'ci', 'output-directory'):
        result.add_argument('--' + name, required=True)
    result.add_argument('--subscription-guard', '--output', dest='subscription_guard', required=True)
    result.add_argument('--packet-directory', '--packet', dest='packet_directory', required=True)
    result.add_argument('--direction-recorded-at', help='Recorded UTC time of the owner direction')
    result.add_argument('--host-confirmed-at', help='Recorded UTC time of the owner host-state confirmation')
    return result


def _run_verified(argv, *, verified_script, entry_inputs):
    from data_sheets_schema.native_launch_entry import _require_invocation
    _require_invocation(globals(), argv, verified_script, entry_inputs)
    args = parser().parse_args(argv)
    started = _utc_now()
    record = {'kind': SEQUENCE_KIND, 'version': SEQUENCE_VERSION, 'started_at': started,
              'completed_at': None, 'status': 'stopped', 'stop_reason': None,
              'capture_manifest': None, 'guard_sha256': None, 'steps': [],
              'direction_recorded_at': args.direction_recorded_at,
              'host_confirmed_at': args.host_confirmed_at, 'delegation_checked_at': None,
              'script_path': None}
    sequence = None
    worker = None
    with _SequenceSignals() as interrupts:
        try:
            inputs = {_path(getattr(args, name)): None for name in
                      ('registration', 'review', 'launch_word', 'account_choice', 'ci')}
            capture_root = _path(args.output_directory)
            guard_path = _path(args.subscription_guard)
            packet = _path(args.packet_directory)
            _require_output_separation(packet, guard_path, capture_root,
                                       entry_inputs[Path(args.registration)])
            if packet.exists():
                if not packet.is_dir() or packet.resolve(strict=True) != packet:
                    raise ValueError('packet must be a resolved directory')
            else:
                packet.mkdir(mode=0o700)
            outputs = [packet / name for name in OUTPUTS]
            sequence_candidate = packet / 'sequence.json'
            targets = [*outputs, *(p.with_suffix('.stderr.txt') for p in outputs),
                       sequence_candidate, packet / START_FILENAME, packet / SCRIPT_FILENAME, guard_path]
            if len(set(targets)) != len(targets) or any(p in inputs for p in targets):
                raise ValueError('sequence output paths collide')
            for path in targets:
                if os.path.lexists(path):
                    raise FileExistsError('sequence refuses an existing output')
            # Exclusive claim prevents concurrent starts sharing one packet.
            host_power.sequence_start(packet / START_FILENAME, started)
            sequence = sequence_candidate
            interrupts.check()
            script_path = packet / SCRIPT_FILENAME
            _write_new(script_path, verified_script)
            record['script_path'] = str(script_path)
            _delegation(args.direction_recorded_at, args.host_confirmed_at, started)
            for path in inputs:
                inputs[path] = guard.read_regular(path, limit=MAX_COMMAND_OUTPUT_BYTES)
            if any(inputs.get(path) != raw for path, raw in entry_inputs.items()):
                raise ValueError('sequence entry inputs changed before use')
            if capture_root.exists() and (not capture_root.is_dir() or capture_root.resolve() != capture_root):
                raise ValueError('capture root must be a resolved directory')
            word_raw = inputs[Path(args.launch_word)]
            slots = [capture_root / 'captures' / guard.sha(word_raw) / ('capture-' + str(i)) / 'capture.json'
                     for i in range(1, 4)]
            existed = {path for path in slots if os.path.lexists(path)}
            common = ['--registration', args.registration, '--review', args.review,
                      '--launch-word', args.launch_word, '--account-choice', args.account_choice]
            pins = {name: {'path': str(_path(getattr(args, name))),
                          'sha256': guard.sha(inputs[_path(getattr(args, name))])}
                    for name in ('registration', 'review', 'launch_word', 'account_choice', 'ci')}
            def bound(extra=None):
                return [*common, '--sequence-inputs', guard.canonical({**pins, **(extra or {})}).decode()]
            _unchanged(inputs)
            record['delegation_checked_at'] = _utc_now()
            _delegation(args.direction_recorded_at, args.host_confirmed_at, record['delegation_checked_at'])
            interrupts.check()
            from .native_sequence_start import claim
            record['start_claim'] = claim(inputs[Path(args.registration)], launch_word_raw=word_raw,
                direction=args.direction_recorded_at, confirmation=args.host_confirmed_at,
                packet=packet, started_at=record['delegation_checked_at'])
            # Durable claiming is preflight too; it must not carry a start across
            # either delegated deadline before the first child dispatch.
            record['delegation_checked_at'] = _utc_now()
            _delegation(args.direction_recorded_at, args.host_confirmed_at, record['delegation_checked_at'])
            start_pin = {'path': record['start_claim'],
                         'sha256': guard.sha(guard.read_regular(record['start_claim'], limit=MAX_COMMAND_OUTPUT_BYTES))}
            from .native_u4b_policy import registered_policy
            registration_raw = inputs[Path(args.registration)]
            registered = guard.strict_json(registration_raw)['registration']
            ipc = packet / 'prepared-worker'
            ipc.mkdir(mode=0o700)
            worker = _PreparedStep([*bound(), '--ci', args.ci,
                '--prepared-directory', str(ipc)], outputs[2], record['steps'], interrupts)
            worker.start()
            prepared_raw = worker.ready(ipc, registration_raw=registration_raw,
                attempt=Path(registered['attempt_directory']),
                max_age_seconds=registered_policy(registered['runtime'])['max_age_seconds'])
            _unchanged(inputs)
            record['prepared_at'] = _utc_now()
            _delegation(args.direction_recorded_at, args.host_confirmed_at, record['prepared_at'])
            readiness = dict(prepared_raw=prepared_raw, registration_raw=registration_raw,
                attempt=Path(registered['attempt_directory']),
                max_age_seconds=registered_policy(registered['runtime'])['max_age_seconds'])
            worker.require_ready(ipc, **readiness)
            captured = _run_step(COMMANDS[0], [*bound({'sequence_start': start_pin}), '--output-directory', str(capture_root)],
                                 outputs[0], record['steps'], interrupts)
            manifest_value = captured.get('capture_manifest')
            if type(manifest_value) is not str:
                raise ValueError('capture output lacks its manifest path')
            manifest = _path(manifest_value)
            if manifest not in slots or manifest in existed:
                raise ValueError('capture output must name a new capture under this word')
            manifest_raw = guard.read_regular(manifest, limit=MAX_COMMAND_OUTPUT_BYTES)
            if guard.sha(manifest_raw) != _digest(captured.get('sha256'), 'capture digest'):
                raise ValueError('capture output digest differs from saved manifest')
            record['capture_manifest'] = str(manifest)
            _unchanged(inputs)
            prepared = _run_step(COMMANDS[1], [*bound({'capture': {'path': str(manifest), 'sha256': guard.sha(manifest_raw)}}), '--capture', str(manifest), '--output', str(guard_path)],
                                 outputs[1], record['steps'], interrupts)
            if prepared.get('path') != str(guard_path):
                raise ValueError('guard output lacks the requested path')
            digest = _digest(prepared.get('guard_sha256'), 'guard digest')
            if guard.sha(guard.read_regular(guard_path, limit=MAX_COMMAND_OUTPUT_BYTES)) != digest:
                raise ValueError('guard output digest differs from saved guard')
            record['guard_sha256'] = digest
            _unchanged(inputs)
            if guard.read_regular(manifest, limit=MAX_COMMAND_OUTPUT_BYTES) != manifest_raw:
                raise ValueError('capture manifest changed before launch')
            worker.require_ready(ipc, **readiness)
            worker.proceed(ipc, prepared_raw=prepared_raw, guard_path=guard_path,
                            guard_sha256=digest)
            final = worker.finish()
            if (final.get('state') != 'completed_pending_independent_review'
                    or final.get('runtime_gates_passed') is not True):
                raise ValueError('launch did not report complete runtime gates')
            interrupts.check()
            record['status'] = 'completed'
            worker.complete = True
        except BaseException as exc:
            # Do not print child stderr, JSON values or arbitrary exception text.
            record['stop_reason'] = type(exc).__name__
            print('native launch sequence stopped; inspect the retained packet', file=sys.stderr)
        finally:
            if worker is not None:
                try:
                    worker.close()
                except BaseException as cleanup_error:
                    record['status'] = 'stopped'
                    record['stop_reason'] = 'worker cleanup ' + type(cleanup_error).__name__
            record['completed_at'] = _utc_now()
            # This single immutable tuple is the outcome's signal cutoff.
            # A signal during later serialization/persistence cannot create
            # contradictory status, reason and received-signal fields.
            received = tuple(interrupts.received)
            if received:
                record['status'] = 'stopped'
                record['stop_reason'] = 'signal ' + str(received[0])
            record['signals_received'] = list(received)
            record['signal_forwarding_errors'] = list(interrupts.forwarding_errors)
            record['signal_recording_cutoff'] = 'after completion clock sample, before immutable record serialization'
            if sequence is not None:
                try:
                    _write_new(sequence, guard.canonical(record))
                except OSError:
                    record['status'] = 'stopped'
                    print('native launch sequence could not save its record', file=sys.stderr)
    return 0 if record['status'] == 'completed' else 1


def main(argv=None):
    # Compatibility route; the documented trusted entry avoids importing this
    # implementation until after its byte check.
    from .native_launch_entry import main as entry
    return entry(argv)


if __name__ == '__main__':
    raise SystemExit(main())
