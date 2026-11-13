"""Supplemental capture-to-reservation timing. Never read for admission.

Buffer throughout each capture, preparation or launch operation. Persist only
when its outer scope exits, after its outcome and freshness decisions and after
registration locks have unwound. Never write into the closed capture tree or
consume an attempt. Missing records mean unknown durations.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import time

from .native_elapsed import elapsed_ns

_active = ContextVar('native_pre_dispatch_timing', default=None)
MAX_BYTES = 8 * 1024 * 1024
MAX_BUFFER = 256


class Trace:
    def __init__(self, registration_raw):
        self.identity = hashlib.sha256(registration_raw).hexdigest()
        self.path = None
        self.pending = []
        self.disabled = False
        self.sealed = False
        self.sequence = 0
        self.trace_id = f'{os.getpid()}-{time.monotonic_ns()}'

    def record(self, boundary, **fields):
        if self.disabled or self.sealed:
            return
        try:
            raw = json.dumps({'boundary': boundary, 'elapsed_ns': elapsed_ns(),
                'wall_ns': time.time_ns(), 'registration_sha256': self.identity,
                'pid': os.getpid(), 'trace_id': self.trace_id, **fields},
                sort_keys=True, separators=(',', ':')).encode() + b'\n'
            if len(raw) > 4096 or len(self.pending) >= MAX_BUFFER:
                raise ValueError('pre-dispatch timing buffer bound')
            self.pending.append(raw)
        except InterruptedError:
            self.disabled = True
            self.pending.clear()
            raise
        except Exception:
            self.disabled = True
            self.pending.clear()

    def bind(self, value):
        if self.disabled or self.path is not None:
            return
        try:
            # Caller supplies a freshly verified registration, never parsed input.
            parent = Path(value['attempt_directory']).parent
            if not parent.is_absolute():
                raise ValueError('nonabsolute diagnostic parent')
            self.path = parent / ('host-pre-dispatch-' + self.identity + '.jsonl')
        except InterruptedError:
            self.disabled = True
            self.pending.clear()
            raise
        except Exception:
            self.disabled = True
            self.pending.clear()

    def flush(self):
        """After the operation's outcome only; failures drop diagnostic rows."""
        if self.disabled or self.path is None or not self.pending:
            return
        try:
            parent = self.path.parent
            if parent.resolve(strict=True) != parent:
                raise ValueError('noncanonical diagnostic parent')
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND |
                         os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                    raise ValueError('unsafe diagnostic file')
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                body = b''.join(self.pending)
                if os.fstat(fd).st_size + len(body) > MAX_BYTES:
                    raise ValueError('pre-dispatch timing file bound')
                if os.write(fd, body) != len(body):
                    raise OSError('incomplete pre-dispatch timing write')
            finally:
                os.close(fd)
        except InterruptedError:
            self.disabled = True
            raise
        except Exception:
            self.disabled = True
        finally:
            self.pending.clear()


@contextmanager
def scope(registration_raw):
    previous = _active.get()
    if previous is not None:
        yield previous
        return
    # Only explicit capture, guard preparation and launch create a scope.
    # Ordinary registration/readback calls have no timing side effects.
    try:
        trace = Trace(registration_raw)
    except InterruptedError:
        raise
    except Exception:
        yield None
        return
    token = _active.set(trace)
    try:
        yield trace
    finally:
        _active.reset(token)
        trace.flush()


def bind(value):
    trace = _active.get()
    if trace is not None:
        trace.bind(value)


def record(boundary, **fields):
    trace = _active.get()
    if trace is not None:
        trace.record(boundary, **fields)


def finish():
    """End this launch's diagnostic window after the reservation span closes."""
    trace = _active.get()
    if trace is not None:
        trace.sealed = True


@contextmanager
def step(name):
    trace = _active.get()
    if trace is None:
        yield
        return
    trace.sequence += 1
    identity = trace.sequence
    trace.record(name, phase='start', step_id=identity)
    error = None
    try:
        yield
    except BaseException as exc:
        error = type(exc).__name__
        raise
    finally:
        trace.record(name, phase='end', step_id=identity, error_type=error)
