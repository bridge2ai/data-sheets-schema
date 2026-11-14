"""Supplemental capture-to-reservation timing. Never read for admission.

Buffer throughout each capture, preparation or launch operation. Persist only
when its outer scope exits, after its outcome and freshness decisions and after
registration locks have unwound, through a bounded nonblocking handoff to a
daemon writer. Never write into the closed capture tree or consume an attempt.
Queue contention, capacity, I/O failure or process exit may drop diagnostics;
missing records mean unknown durations. Callers never join the writer.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import fcntl
import hashlib
import json
import os
from pathlib import Path
from collections import deque
import stat
import threading
import time

from .native_elapsed import elapsed_ns

_active = ContextVar('native_pre_dispatch_timing', default=None)
MAX_BYTES = 8 * 1024 * 1024
MAX_BUFFER = 256
MAX_QUEUED_TRACES = 8
_pending = deque()
_writer_lock = threading.Lock()
_writer = None


def _drop(trace):
    trace.disabled = True
    trace.pending.clear()
    trace._persisted.set()


def _drain():
    global _writer
    try:
        while True:
            with _writer_lock:
                if not _pending:
                    _writer = None
                    return
                trace = _pending.popleft()
            trace.flush()
    except BaseException:
        # InterruptedError remains an exception, including in a direct flush.
        # A failed diagnostic worker has no authority over the completed run.
        with _writer_lock:
            for trace in _pending:
                _drop(trace)
            _pending.clear()
            _writer = None
        raise


def _handoff(trace):
    """No file I/O or wait for persistence on the operation's return path."""
    global _writer
    trace.sealed = True
    if trace.disabled or trace.path is None or not trace.pending:
        _drop(trace)
        return
    acquired = False
    try:
        acquired = _writer_lock.acquire(blocking=False)
        if not acquired or len(_pending) >= MAX_QUEUED_TRACES:
            _drop(trace)
            return
        _pending.append(trace)
        if _writer is None:
            writer = threading.Thread(target=_drain, name='native-timing-writer', daemon=True)
            _writer = writer
            try:
                writer.start()
            except BaseException:
                if not writer.is_alive():
                    _writer = None
                    _pending.remove(trace)
                raise
    except InterruptedError:
        _drop(trace)
        raise
    except Exception:
        _drop(trace)
    finally:
        if acquired:
            _writer_lock.release()


class Trace:
    def __init__(self, registration_raw):
        self.identity = hashlib.sha256(registration_raw).hexdigest()
        self.path = None
        self.pending = []
        self.disabled = False
        self.sealed = False
        self.sequence = 0
        self.trace_id = f'{os.getpid()}-{time.monotonic_ns()}'
        self._persisted = threading.Event()  # Tests may wait after the outcome; production never does.

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
            self._persisted.set()
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
            self._persisted.set()


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
        _handoff(trace)


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
