"""Private owner-pump experiment; no launcher/profile/registration integration.

Each factory call binds the current verified frozen object graph. No frozen
class or BudgetStop is retained in this module's globals. Adding these package
files changes whole-source pins even though historical controller bytes stay
unchanged (#4693).
"""
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
from types import ModuleType

from . import native_attribution_controller as inherited
from . import native_shared_contract as contract
from . import native_shared_evidence as evidence
from . import native_stream_coordination_v1 as coordination
from .native_origin_resolution import resolve_fixed_origin

SUMMARY_LIMIT = 16 * 1024
RECORD_LIMIT = 16 * 1024 * 1024
CHUNK_BYTES = 65536


def _write(fd, raw):
    """Single injectable syscall seam; positive counts are physical progress."""
    return os.write(fd, raw)


def _json(value, limit=SUMMARY_LIMIT):
    pieces, count = [], 0
    for part in json.JSONEncoder(sort_keys=True, separators=(',', ':'), allow_nan=False).iterencode(value):
        raw = part.encode('utf-8')
        count += len(raw)
        if count > limit:
            raise ValueError('failed owner evidence exceeds its retention bound')
        pieces.append(raw)
    return b''.join(pieces)


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _failure_fallback(snapshot):
    """Keep small facts when an independent identity/result exceeds the cap."""
    fallback = {key: snapshot[key] for key in ('format', 'active_kind', 'worker_started',
        'worker_finished', 'intended_record_exists', 'control_commit', 'transcript')}
    fallback.update(capture_state='capture_refused', capture_error='summary_bound',
        result=None, completed_result_captured=False, unretained_fields=['result'])
    for key in ('first_stop', 'request_id'):
        value = snapshot[key]
        if value is None:
            fallback[key] = None
            continue
        if type(value) is not str:
            # Generic observer frames are not callback schemas: request_id
            # may be structured data. Never coerce or call its methods here.
            fallback[key] = None
            fallback[key + '_retention_error'] = 'not_text'
            fallback['unretained_fields'].append(key)
            continue
        try:
            raw = value.encode('utf-8')
        except UnicodeError:
            fallback[key] = None
            fallback['unretained_fields'].append(key)
            continue
        if len(raw) <= 512:
            fallback[key] = value
        else:
            fallback[key] = None
            fallback[key + '_identity'] = _pin(raw)
            fallback['unretained_fields'].append(key)
    return fallback


def make_control(controls):
    """Bind only the exact 12-role frozen subset INSIDE its verified loader."""
    manifest = inherited.controller_sources()
    if type(controls) is not dict or set(controls) != set(manifest['modules']):
        raise ValueError('owner factory requires the exact frozen controller roster')
    bound = dict(controls)

    def current_graph():
        for name, pin in manifest['modules'].items():
            module = bound[name]
            expected = str(inherited.ROOT / pin['path'])
            if (type(module) is not ModuleType or sys.modules.get(name) is not module
                    or resolve_fixed_origin(getattr(module, '__file__', ''), expected) !=
                       resolve_fixed_origin(expected, expected)):
                raise ValueError('owner factory has a stale or foreign controller object graph')
        native = bound['native_control']
        if native.NativeControl._collect_work.__globals__.get('BudgetStop') is not bound['budgeted_cborg'].BudgetStop:
            raise ValueError('owner factory BudgetStop differs from its active controller graph')

    current_graph()
    native, BudgetStop = bound['native_control'], bound['budgeted_cborg'].BudgetStop

    class OwnerControl(native.NativeControl):
        """Private testable pump. Handles and evidence sink belong to its caller."""
        budget_stop_type = BudgetStop

        def __init__(self, policy, classify, config_root=None, event_observer=None, *,
                     attempt_deadline_ns, stop_event, stream_byte_limit=contract.HARD_LIMITS['stream_bytes'],
                     owner_clock_domain=None):
            current_graph()
            if (type(stream_byte_limit) is not int or not 0 < stream_byte_limit <= contract.HARD_LIMITS['stream_bytes']):
                raise ValueError('owner stream limit exceeds the existing complete stream bound')
            # Validate before the inherited constructor allocates a selector.
            coordination.ReaderBudget(attempt_deadline_ns, (stop_event,), clock_domain=owner_clock_domain)
            super().__init__(policy, classify, config_root, event_observer)
            if not self.history_control:
                raise ValueError('private owner pump requires the exact history contract')
            self._owner_budget = coordination.ReaderBudget(attempt_deadline_ns, (self._stopped, stop_event),
                clock_domain=owner_clock_domain)
            self._external_stop = stop_event
            self._stream_limit = stream_byte_limit
            self._pending_raw = bytearray()
            self._received_bytes = self._written_bytes = self._admitted_bytes = self._parsed_bytes = 0
            self._control_written = 0
            self._control_lease = None
            self._control_commit = None
            self._anchors = {}
            self._first_failure = None
            self._failure_json = self._close_json = None
            self._failed_members = {}
            self._stop_snapshot_taken = False
            self._contention = False
            self._write_quota = CHUNK_BYTES
            self._initialization_pending = False
            self._close_lock = threading.Lock()
            self._close_started = False
            self._close_error = None
            self._close_deadline_ns = None
            self._close_domain_guard = None
            self._worker_clock_close = None

        def _check_budget(self):
            try:
                self._owner_budget.remaining()
            except ValueError as error:
                raise BudgetStop(str(error)) from error

        def _live_monotonic(self):
            self._owner_budget.require_domain()
            return native.time.monotonic()

        def start(self, process, transcript, evidence_stream, instruction):
            current_graph()
            self._check_budget()
            # Buffered close-time writes would escape a failed EX lease.
            for role, stream in (('transcript', transcript), ('control', evidence_stream)):
                if type(stream) is not io.FileIO or not stream.writable() or stream.closed:
                    raise ValueError('owner fixture streams must be writable unbuffered FileIO')
                meta = evidence._stat(os.fstat(stream.fileno()))
                evidence._metadata(meta, meta['size'])
                if meta['size'] != 0:
                    raise ValueError('owner fixture streams must be fresh and empty')
                self._anchors[role] = meta
            if any(self._anchors['transcript'][k] != self._anchors['control'][k] for k in ('device', 'inode')) is False:
                raise ValueError('owner streams alias one inode')
            # Retain the original start clock and setup. A contended fresh
            # journal defers only its record/send transition, never intake.
            self.process, self.transcript, self.evidence = process, transcript, evidence_stream
            self.instruction = instruction
            self.started = self._live_monotonic()
            os.set_blocking(process.stdout.fileno(), False)
            os.set_blocking(process.stdin.fileno(), False)
            self.selector.register(process.stdout, native.selectors.EVENT_READ, 'stdout')
            self._initialization_pending = True
            try:
                self._commit_initialization()
            except BaseException as error:
                self._latch_failure(error)
                self._stop_history()
                raise

        def _commit_initialization(self):
            if not self._initialization_pending:
                return
            self._owner_budget.require_domain()
            lease = coordination.try_lease(self.evidence.fileno(), fcntl.LOCK_EX)
            if lease is None:
                self._contention = True
                return
            with lease:
                self._control_lease = lease
                try:
                    self.record({'kind': 'initialize_sent', 'policy_sha256': native.digest(self.policy),
                        'frame': native.initialize_frame(self.contract)})
                    self.send(native.initialize_frame(self.contract))
                    self._control_commit = None
                    self._initialization_pending = False
                finally:
                    self._control_lease = None

        def _confirm_stream(self, role):
            stream = self.transcript if role == 'transcript' else self.evidence
            expected = self._written_bytes if role == 'transcript' else self._control_written
            meta = evidence._stat(os.fstat(stream.fileno()))
            evidence._metadata(meta, meta['size'])
            if (any(meta[k] != self._anchors[role][k] for k in ('device', 'inode'))
                    or meta['size'] != expected or expected > self._stream_limit):
                raise BudgetStop('owner stream physical write extent changed')

        def record(self, value):
            if self._stopped.is_set():
                raise BudgetStop('native history control is stopped')
            if self._control_lease is None or not self._control_lease.active:
                raise BudgetStop('owner journal write lacks the pump commit lease')
            raw = (json.dumps({'at': datetime.now(timezone.utc).isoformat(), **value}) + '\n').encode('utf-8')
            self._control_commit = {'raw': raw, 'start': self._control_written, 'written': 0, 'complete': False}
            if self._control_written + len(raw) > self._stream_limit:
                raise BudgetStop('owner control stream exceeds its byte bound')
            self._confirm_stream('control')
            offset = 0
            while offset < len(raw):
                self._check_budget()
                count = _write(self.evidence.fileno(), raw[offset:])
                if type(count) is not int or not 0 < count <= len(raw) - offset:
                    raise OSError('owner journal write made invalid progress')
                offset += count
                self._control_written += count
                self._control_commit['written'] += count
            self._confirm_stream('control')
            self._control_commit['complete'] = True

        def _flush_pending(self):
            if not self._pending_raw or self._write_quota <= 0:
                return
            self._owner_budget.require_domain()
            lease = coordination.try_lease(self.transcript.fileno(), fcntl.LOCK_EX)
            if lease is None:
                self._contention = True
                return
            with lease:
                self._confirm_stream('transcript')
                raw = bytes(self._pending_raw[:self._write_quota])
                offset = 0
                while offset < len(raw):
                    self._check_budget()
                    count = _write(self.transcript.fileno(), raw[offset:])
                    if type(count) is not int or not 0 < count <= len(raw) - offset:
                        raise OSError('owner transcript write made invalid progress')
                    offset += count
                    self._written_bytes += count
                    self._write_quota -= count
                    del self._pending_raw[:count]
                self._confirm_stream('transcript')
                self._admitted_bytes = self._written_bytes

        def _intake_history(self):
            capacity = native.MAX_HISTORY_QUEUE_BYTES - len(self._pending_raw)
            if capacity <= 0:
                raise BudgetStop('owner pending raw capacity exhausted')
            capacity = min(capacity, self._stream_limit - self._received_bytes)
            if capacity <= 0:
                raise BudgetStop('owner transcript stream byte capacity exhausted')
            try:
                raw = os.read(self.process.stdout.fileno(), min(CHUNK_BYTES, capacity))
            except BlockingIOError:
                return
            if not raw:
                self.selector.unregister(self.process.stdout)
                self._stdout_eof = True
                if self.buffer.strip():
                    raise BudgetStop('native transcript ends inside a JSON frame')
                return
            self._pending_raw.extend(raw)
            self._received_bytes += len(raw)
            self.buffer += raw
            self._flush_pending()
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                self._parsed_bytes += len(line) + 1
                self.transcript_line += 1
                if len(line) > native.MAX_FRAME_BYTES:
                    raise BudgetStop('native control frame exceeds its size limit')
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except (ValueError, UnicodeError) as error:
                    raise BudgetStop('native control received malformed JSON') from error
                if not isinstance(event, dict):
                    raise BudgetStop('native control received a non-object event')
                if event.get('type') == 'control_cancel_request':
                    raise BudgetStop('native control callback was cancelled or timed out')
                if (len(self._events) >= native.MAX_HISTORY_QUEUE_FRAMES
                        or self._event_bytes + len(line) > native.MAX_HISTORY_QUEUE_BYTES):
                    raise BudgetStop('native history input queue exceeds its bound')
                received = self._live_monotonic()
                if event.get('type') == 'control_request' and isinstance(event.get('request_id'), str):
                    self._callback_intake.setdefault(event['request_id'], received)
                self._events.append((self.transcript_line, event, len(line), self._parsed_bytes))
                self._event_bytes += len(line)
            if len(self.buffer) > native.MAX_FRAME_BYTES:
                raise BudgetStop('native control frame exceeds its size limit')

        def _start_work(self, kind, event, operation):
            self._owner_budget.require_domain()
            start_ns = time.monotonic_ns()
            limit = self.contract['observer_timeout_seconds' if kind == 'observer' else 'callback_timeout_seconds']
            budget = coordination.ReaderBudget(min(self._owner_budget.deadline_ns,
                start_ns + int(limit * 1_000_000_000)), self._owner_budget.stop_events,
                clock_domain=self._owner_budget.clock_domain())
            def bounded():
                clock_scope = coordination.reader_budget(budget)
                try:
                    with clock_scope:
                        budget.remaining()
                        result = operation()
                        budget.remaining()
                        return result
                finally:
                    if clock_scope.close_error is not None:
                        error = clock_scope.close_error
                        # Error evidence belongs to the same publication cut
                        # as the worker result; a later close cannot backfill it.
                        try:
                            raw = str(error).encode('utf-8', errors='backslashreplace')
                            detail = {'type': type(error).__name__[:128], 'message':
                                raw.decode('utf-8') if len(raw) <= 512 else None,
                                'message_identity': _pin(raw)}
                            captured = _json(detail)
                        except BaseException:
                            captured = b'{"capture_refused":true,"reason":"worker clock close diagnostic unavailable"}'
                        with self._publication_lock:
                            if not self._stop_snapshot_taken:
                                self._worker_clock_close = captured
            return super()._start_work(kind, event, bounded)

        def _collect_work(self):
            if self._active_work is None:
                return
            self._owner_budget.require_domain()
            kind, started, event = self._active_work
            limit = self.contract['observer_timeout_seconds' if kind == 'observer' else 'callback_timeout_seconds']
            if self._work_result is None:
                try:
                    self._work_result = self._work_replies.get_nowait()
                except queue.Empty:
                    if self._live_monotonic() - started >= limit:
                        raise BudgetStop('native ' + kind + ' verification timed out before execution')
                    return
            finished, value = self._work_result
            if self._owner_budget.clock_domain() is not None and isinstance(value, BaseException):
                # A failed worker scope does not attest the inherited trailing
                # timestamp's domain. Preserve its error before comparing that
                # timestamp with the parent's start; unbound order is unchanged.
                if self._work_thread.is_alive():
                    return
                self._work_thread.join(0)
                if isinstance(value, BudgetStop):
                    raise value
                raise BudgetStop('native ' + kind + ' verification failed before execution') from value
            if finished - started >= limit:
                raise BudgetStop('native ' + kind + ' verification timed out before execution')
            if self._work_thread.is_alive():
                return
            self._work_thread.join(0)
            if isinstance(value, BudgetStop):
                raise value
            if isinstance(value, BaseException):
                raise BudgetStop('native ' + kind + ' verification failed before execution') from value
            if kind != 'observer' and (not isinstance(value, tuple) or len(value) != 2
                    or value[0] not in ('prescribed', 'not_prescribed') or not isinstance(value[1], str)):
                raise BudgetStop('native command classification returned a malformed decision')
            self._owner_budget.require_domain()
            lease = coordination.try_lease(self.evidence.fileno(), fcntl.LOCK_EX)
            if lease is None:
                self._contention = True
                return
            with lease:
                self._control_lease = lease
                try:
                    if kind == 'observer':
                        if value is not None:
                            self.record(value)
                        self._active_work = self._work_thread = self._work_result = None
                        if event.get('type') == 'control_request':
                            self._start_work('classifier', event, lambda: self._classify_frame(event))
                    else:
                        self._check_response_bounds()
                        request_id = event['request_id']
                        _, request = self.pending[request_id]
                        classification, basis = value
                        response = {'type': 'control_response', 'response': {'subtype': 'success',
                            'request_id': request_id, 'response': native.hook_output(classification, basis)}}
                        self.record({'kind': 'decision', 'request': request, 'response': response,
                                     'classification': classification, 'basis': basis})
                        self.pending.pop(request_id)
                        self.decided.add(request_id)
                        self.decided_tools.add(request['request']['input']['tool_use_id'])
                        self.classifications[request['request']['input']['tool_use_id']] = classification
                        self._pending_response_id = request_id
                        self.send(response)
                        self._active_work = self._work_thread = self._work_result = None
                    self._control_commit = None
                finally:
                    self._control_lease = None

        def _service_history(self):
            self._check_budget()
            if not self.initialized and self._live_monotonic() - self.started >= self.contract['initialize_timeout_seconds']:
                raise BudgetStop('native control initialization timed out before the prompt')
            self._contention = False
            self._write_quota = CHUNK_BYTES
            self._flush_pending()
            for key, _ in self.selector.select(.05):
                if key.data == 'stdout':
                    self._intake_history()
            self._check_budget()
            self._check_response_bounds()
            self._commit_initialization()
            self._collect_work()
            if (not self._initialization_pending and self._active_work is None and not self.outgoing and self._events
                    and self._events[0][3] <= self._admitted_bytes):
                self._owner_budget.require_domain()
                lease = coordination.try_lease(self.evidence.fileno(), fcntl.LOCK_EX)
                if lease is None:
                    self._contention = True
                else:
                    with lease:
                        self._control_lease = lease
                        try:
                            number, event, size, _ = self._events.popleft()
                            self._event_bytes -= size
                            self.handle(event, line_number=number)
                            self._control_commit = None
                        finally:
                            self._control_lease = None
            self._check_response_bounds()
            input_waiting = bool(self.buffer or self._pending_raw) or any(
                key.data == 'stdout' for key, _ in self.selector.select(0))
            if self.outgoing and self._active_work is None and not input_waiting:
                try:
                    count = os.write(self.process.stdin.fileno(), self.outgoing)
                except BlockingIOError:
                    count = 0
                self.outgoing = self.outgoing[count:]
                if not self.outgoing and self._pending_response_id is not None:
                    self._callback_intake.pop(self._pending_response_id, None)
                    self._pending_response_id = None
            self.stdout_closed = (self._stdout_eof and not self._events and self._active_work is None
                                  and not self.outgoing and not self._pending_raw)
            if (self.terminal and self._active_work is None and not self.outgoing
                    and not self._pending_raw and not self.process.stdin.closed):
                self.process.stdin.close()
            if self._contention:
                try:
                    self._owner_budget.wait()
                except ValueError as error:
                    raise BudgetStop(str(error)) from error

        def _latch_failure(self, error):
            if self._first_failure is None:
                self._first_failure = str(error) if isinstance(error, BudgetStop) else type(error).__name__ + ': ' + str(error)

        def service(self):
            try:
                current_graph()
                return self._service_history()
            except BaseException as error:
                self._latch_failure(error)
                self._stop_history()
                raise

        def _stop_history(self):
            if self._stop_snapshot_taken:
                return
            with self._publication_lock:
                self._stopped.set()
                completed = self._work_result
                if completed is None:
                    try:
                        completed = self._work_replies.get_nowait()
                    except queue.Empty:
                        pass
                active, commit = self._active_work, self._control_commit
                if self._worker_clock_close is not None:
                    self._failed_members['worker_clock_close'] = self._worker_clock_close
                self._stop_snapshot_taken = True
                self.outgoing = b''
                self._events.clear()
                self._event_bytes = 0
                while True:
                    try:
                        self._work_replies.get_nowait()
                    except queue.Empty:
                        break
                self._work_result = None
            if self._first_failure is None and active is None and not self._pending_raw and not commit:
                return
            snapshot = {'format': 'native_owner_failure_v1', 'first_stop': self._first_failure,
                'capture_state': 'captured', 'active_kind': active[0] if active else None,
                'worker_started': active[1] if active else None,
                'worker_finished': completed[0] if completed else None,
                'completed_result_captured': completed is not None,
                'request_id': active[2].get('request_id') if active else None,
                'result': completed[1] if completed else None,
                'intended_record_exists': commit is not None,
                'control_commit': None, 'transcript': {'received_bytes': self._received_bytes,
                    'written_bytes': self._written_bytes, 'admitted_bytes': self._admitted_bytes,
                    'pending': _pin(bytes(self._pending_raw))}}
            try:
                if completed and isinstance(completed[1], BaseException):
                    raise ValueError('completed error is not a retained decision')
                if commit is not None:
                    raw = commit['raw']
                    snapshot['control_commit'] = {'record': _pin(raw), 'start': commit['start'],
                        'written': commit['written'], 'complete': commit['complete']}
                    if len(raw) > RECORD_LIMIT:
                        raise ValueError('intended control record exceeds failed-evidence bound')
                    self._failed_members['control_record'] = raw
                self._failure_json = _json(snapshot)
            except Exception as error:
                snapshot.update(capture_state='capture_refused', result=None,
                    completed_result_captured=False, capture_error=type(error).__name__)
                try:
                    self._failure_json = _json(snapshot)
                except Exception:
                    self._failure_json = _json(_failure_fallback(snapshot))

        def failure_snapshot(self):
            return json.loads(self._failure_json) if self._failure_json is not None else None

        def failed_members(self):
            return dict(self._failed_members)

        def close_report(self):
            return json.loads(self._close_json) if self._close_json is not None else None

        def finish(self):
            try:
                current_graph()
                if self._pending_raw or self._written_bytes != self._admitted_bytes:
                    raise BudgetStop('owner session ended with uncommitted transcript bytes')
                return super().finish()
            except BaseException as error:
                self._latch_failure(error)
                self._stop_history()
                raise

        def retain_pipe_tail(self, path):
            raise ValueError('private owner pump has no runner tail-publication route')

        def close(self):
            return self._close_once(append=False)

        def close_after_process_termination(self):
            """One fixed cleanup allowance; the caller cannot supply a clock."""
            return self._close_once(append=True)

        def _append_close_chunk(self, suffix, deadline):
            if self._close_now() >= deadline:
                return False
            lease = coordination.try_lease(self.transcript.fileno(), fcntl.LOCK_EX)
            if lease is None:
                return False
            with lease:
                self._close_domain_guard.require_current()
                self._confirm_stream('transcript')
                path = Path(self.transcript.name)
                observed = evidence._stat(path.lstat())
                evidence._metadata(observed, self._written_bytes)
                if (str(path.resolve(strict=True)) != str(path)
                        or any(observed[k] != self._anchors['transcript'][k] for k in ('device', 'inode'))):
                    raise BudgetStop('owner close transcript path identity changed')
                if self._close_now() >= deadline:
                    return False
                raw = bytes(suffix[:CHUNK_BYTES])
                count = _write(self.transcript.fileno(), raw)
                if type(count) is not int or not 0 < count <= len(raw):
                    raise OSError('owner close write made invalid progress')
                self._written_bytes += count
                del suffix[:count]
                self._confirm_stream('transcript')
                after = evidence._stat(path.lstat())
                evidence._metadata(after, self._written_bytes)
                if any(after[k] != self._anchors['transcript'][k] for k in ('device', 'inode')):
                    raise BudgetStop('owner close transcript path identity changed')
            return True

        def _close_now(self):
            # Cleanup has its own one-entry allowance. It checks the borrowed
            # live domain, never the already-stopped attempt remaining budget.
            self._close_domain_guard.require_current()
            return time.monotonic_ns()

        def _close_once(self, *, append):
            if not self._close_lock.acquire(blocking=False):
                raise BudgetStop('native owner cleanup is already in progress')
            process = getattr(self, 'process', None)
            try:
                if self._close_started:
                    if self._close_error is not None:
                        raise self._close_error
                    return
                self._close_started = True
                # Sample once at entry, before copying, failure capture or
                # potentially slow domain checks. Validate before interpreting.
                start = time.monotonic_ns()
                self._close_deadline_ns = start + 250_000_000
                deadline = self._close_deadline_ns
                suffix = bytearray(self._pending_raw)
                written_at_stop, admitted_at_stop = self._written_bytes, self._admitted_bytes
                reason, retention_error, eof = None, None, False
                try:
                    self._stop_history()
                    self._close_domain_guard = self._owner_budget.cleanup_guard()
                    # Capacity is for received bytes, not space recycled by
                    # successful append. Pending bytes already consume it.
                    remaining = self._stream_limit - written_at_stop - len(suffix)
                    if remaining < 0:
                        reason = 'stream byte capacity exhausted'
                    elif process is None:
                        eof = append  # No process was started; no pipe is invented.
                    else:
                        if process.stdout.closed:
                            reason = 'pipe unavailable'
                        while True:
                            if self._close_now() >= deadline:
                                reason = reason or 'close deadline elapsed'
                                break
                            progress = False
                            if append and suffix and retention_error is None:
                                try:
                                    progress = self._append_close_chunk(suffix, deadline)
                                except BaseException as error:
                                    retention_error = type(error).__name__
                            if not eof and reason is None:
                                if remaining <= 0:
                                    reason = 'stream byte capacity exhausted'
                                elif self._close_now() >= deadline:
                                    reason = 'close deadline elapsed'
                                else:
                                    try:
                                        raw = os.read(process.stdout.fileno(), min(CHUNK_BYTES, remaining))
                                    except BlockingIOError:
                                        if not append:
                                            reason = 'pipe not at EOF'
                                        raw = None
                                    except OSError as error:
                                        reason = 'pipe tail read failed: ' + type(error).__name__
                                        raw = None
                                    if raw == b'':
                                        eof = True
                                    elif raw is not None:
                                        suffix.extend(raw)
                                        remaining -= len(raw)
                                        progress = True
                            if (eof or reason is not None) and (not append or not suffix or retention_error is not None):
                                break
                            if not progress:
                                wait = min(.01, max(0, (deadline - self._close_now()) / 1e9))
                                time.sleep(wait)
                    worker = self._work_thread
                    if worker is not None:
                        wait = max(0, (deadline - self._close_now()) / 1e9)
                        worker.join(wait)
                    unfinished = int(worker is not None and worker.is_alive())
                    self._shutdown_snapshot = (unfinished, not unfinished)
                    operation_failed = self._first_failure is not None or self._failure_json is not None
                    if operation_failed or suffix or not eof or reason or retention_error or unfinished:
                        self._failed_members['transcript_suffix'] = bytes(suffix)
                    result = {'format': 'native_owner_close_v2' if append else 'native_owner_close_v1',
                        'worker_shutdown_complete': not unfinished, 'unfinished_workers': unfinished,
                        'capture_complete': eof and reason is None and not suffix and not operation_failed and retention_error is None,
                        'tail_capture_complete': eof and reason is None, 'tail_reason': reason,
                        'suffix_start': self._written_bytes, 'admitted_bytes': self._admitted_bytes,
                        'suffix': _pin(bytes(suffix)), 'role': 'transcript',
                        'operation_failed': operation_failed, 'admitted': False}
                    if append:
                        result.update(cleanup_mode='append', close_start_ns=start, close_deadline_ns=deadline,
                            written_bytes_at_stop=written_at_stop, admitted_bytes_at_stop=admitted_at_stop,
                            final_written_bytes=self._written_bytes, retention_error=retention_error)
                    self._close_json = _json(result)
                    if unfinished:
                        self._close_error = BudgetStop('native control worker remains active; closure incomplete')
                    elif append and (not eof or reason or retention_error or suffix):
                        self._close_error = BudgetStop('native owner tail retention incomplete: ' +
                            (retention_error or reason or 'unwritten suffix'))
                except BaseException as error:
                    self._close_error = error
                    worker = self._work_thread
                    unfinished = int(worker is not None and worker.is_alive())
                    self._shutdown_snapshot = (unfinished, not unfinished)
                    self._failed_members['transcript_suffix'] = bytes(suffix)
                    # Fixed primitive fallback survives a failed report
                    # serializer; the first entry is nevertheless terminal.
                    self._close_json = json.dumps({'format': 'native_owner_close_refused_v1',
                        'capture_complete': False, 'tail_capture_complete': False,
                        'worker_shutdown_complete': not unfinished, 'unfinished_workers': unfinished,
                        'operation_failed': self._first_failure is not None,
                        'cleanup_error': type(error).__name__, 'admitted': False,
                        'suffix_start': self._written_bytes, 'suffix': _pin(bytes(suffix))},
                        sort_keys=True, separators=(',', ':')).encode()
                finally:
                    for action in [self.selector.close] + ([stream.close for stream in
                            (process.stdin, process.stdout) if stream is not None and not stream.closed]
                            if process is not None else []):
                        try:
                            action()
                        except BaseException as error:
                            if self._close_error is None:
                                self._close_error = error
                            result = json.loads(self._close_json)
                            result.update(capture_complete=False, cleanup_error=type(error).__name__)
                            self._close_json = json.dumps(result, sort_keys=True,
                                separators=(',', ':')).encode()
                if self._close_error is not None:
                    raise self._close_error
            except BaseException as error:
                if self._close_started and self._close_error is None:
                    self._close_error = error
                if self._close_started and self._close_json is None:
                    self._close_json = json.dumps({'format': 'native_owner_close_refused_v1',
                        'capture_complete': False, 'tail_capture_complete': False,
                        'cleanup_error': type(error).__name__, 'admitted': False},
                        sort_keys=True, separators=(',', ':')).encode()
                raise
            finally:
                self._close_lock.release()

    return OwnerControl
