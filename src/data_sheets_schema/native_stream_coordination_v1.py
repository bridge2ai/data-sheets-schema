"""Private local-file coordination primitives; no selected production route.

These objects do not derive a deadline or authenticate a writer. A future
profile must supply already verified owner identity and remaining lifetime.
"""
from contextvars import ContextVar
from dataclasses import dataclass
import errno
import fcntl
import json
import os
from pathlib import Path
import sys
import threading
import time

from . import native_shared_evidence as evidence
from . import native_clock_domain_v1 as clock
from . import native_shared_contract as contract

PROFILE = 'native_stream_sample_lock_v1'
POLL_SECONDS = .05
_BUDGET = ContextVar('native_owner_reader_budget', default=None)
_SCOPE = ContextVar('native_owner_reader_scope', default=None)
_OWNER_READER = ContextVar('native_owner_live_reader_context', default=None)
_OWNER_BYTES = 16_384


@dataclass(frozen=True, init=False)
class ReaderBudget:
    deadline_ns: int
    stop_events: tuple
    _clock_raw: bytes | None

    def __init__(self, deadline_ns, stop_events, *, clock_domain=None):
        if (type(deadline_ns) is not int or deadline_ns <= 0
                or type(stop_events) is not tuple or not stop_events
                or any(type(event) is not threading.Event for event in stop_events)):
            raise ValueError('reader budget requires an absolute deadline and actual stop events')
        raw = None if clock_domain is None else clock._encoded(clock_domain)
        object.__setattr__(self, 'deadline_ns', deadline_ns)
        object.__setattr__(self, 'stop_events', stop_events)
        object.__setattr__(self, '_clock_raw', raw)

    def clock_domain(self):
        """Detached saved claims; no acquisition or live-scope assertion."""
        return None if self._clock_raw is None else json.loads(self._clock_raw)

    def require_domain(self):
        """Check exact live scope/domain only, without a deadline/stop sample."""
        if self._clock_raw is not None:
            scope = _SCOPE.get()
            if scope is None or scope.budget is not self:
                raise ValueError('clock-bound reader budget has no matching live scope')
            scope.require_current()

    def cleanup_guard(self):
        """Capture this exact scope, without renewing its deadline or lease."""
        self.require_domain()
        return _CleanupGuard(None if self._clock_raw is None else _SCOPE.get())

    def remaining(self):
        self.require_domain()
        if any(event.is_set() for event in self.stop_events):
            raise ValueError('native owner coordination stopped')
        remaining = (self.deadline_ns - time.monotonic_ns()) / 1_000_000_000
        if remaining <= 0:
            raise ValueError('native owner coordination deadline elapsed')
        return remaining

    def wait(self):
        self.stop_events[0].wait(min(POLL_SECONDS, self.remaining()))
        self.remaining()


@dataclass(frozen=True)
class _CleanupGuard:
    scope: object

    def require_current(self):
        # A stopped attempt still needs bounded local cleanup. This checks only
        # its captured domain scope, never attempt admission or remaining time.
        if self.scope is not None:
            self.scope.require_current()


class _ReaderScope:
    """One context entry; a borrowed parent lease never transfers ownership."""
    def __init__(self, budget, lease):
        if type(budget) is not ReaderBudget:
            raise ValueError('not a private reader budget')
        if lease is not None and (budget._clock_raw is None or type(lease) is not clock._DomainLease):
            raise ValueError('borrowed clock lease requires a clock-bound reader budget')
        self.budget = budget
        self._lease = lease
        self._owns_lease = budget._clock_raw is not None and lease is None
        self._entered = self._finished = self.live = False
        self._creator = None
        self._tokens = None
        self.close_error = None

    def require_current(self):
        if (not self.live or self._finished or _SCOPE.get() is not self
                or _BUDGET.get() is not self.budget
                or threading.current_thread() is not self._creator):
            raise ValueError('reader budget scope is inactive or belongs to another context')
        if self.budget._clock_raw is not None:
            if type(self._lease) is not clock._DomainLease:
                raise ValueError('reader budget scope lacks its fixed clock lease')
            self._lease.require_current(self.budget.clock_domain())

    def __enter__(self):
        if self._entered:
            raise ValueError('reader budget scope cannot be reentered')
        self._entered = True
        self._creator = threading.current_thread()
        try:
            if self._owns_lease:
                acquired = clock.capture_domain()
                if type(acquired) is not clock._DomainLease:
                    raise ValueError('reader acquisition did not return the fixed clock lease')
                self._lease = acquired
            self._tokens = (_BUDGET.set(self.budget), _SCOPE.set(self))
            self.live = True
            if self.budget._clock_raw is not None:
                self.require_current()
            return self
        except BaseException as error:
            self._finish(error)
            raise

    def _finish(self, primary):
        # Invalidate before restoring a surrounding context and before closing;
        # a copied Context cannot make this entry live again.
        self.live = False
        self._finished = True
        try:
            if self._tokens is not None:
                budget_token, scope_token = self._tokens
                self._tokens = None
                try:
                    _SCOPE.reset(scope_token)
                finally:
                    _BUDGET.reset(budget_token)
        finally:
            if self._owns_lease and self._lease is not None:
                lease, self._lease = self._lease, None
                try:
                    lease.close()
                except BaseException as error:
                    self.close_error = error
                    if primary is None:
                        raise

    def __exit__(self, kind, error, traceback):
        if (not self.live or self._finished or _SCOPE.get() is not self
                or _BUDGET.get() is not self.budget
                or threading.current_thread() is not self._creator):
            raise ValueError('reader budget scope exit requires its active consuming context')
        if error is None and self.budget._clock_raw is not None:
            try:
                self.require_current()
            except BaseException as checked_error:
                self._finish(checked_error)
                raise
        else:
            self._finish(error)
            return False
        self._finish(None)
        return False


@dataclass(frozen=True)
class _ReaderAssociation:
    selection: object
    execution_raw: bytes
    started_raw: bytes
    owner_raw: bytes
    owner_path: str
    stop_path: str
    streams: tuple
    max_bytes: int


def _selected_reader_scope(scope):
    # Fixed module origins and actual bare objects, not an injectable guard.
    from . import native_owner_profile_v1 as profile
    if type(scope) is not profile._Scope:
        raise ValueError('private reader requires the fixed selected scope')
    scope.require()
    if any(sys.modules.get(name) is not module for name, module in scope.members):
        raise ValueError('private reader selected module graph changed')
    # Worker require() has just checked these same four qualified origins in
    # _require_parent_graph(). Parent scopes only check their bare loader graph,
    # so they retain the separate qualified sweep here. No check is retained
    # beyond this one invocation.
    if scope._parent is None:
        for role, name in profile._MODULES.items():
            profile._origin(role, sys.modules.get(name))


def _reader_association(scope, selection, execution_raw, started_raw, owner_raw, budget):
    """Validate captured joins, then prove selected source; no public E bypass."""
    from . import native_execution_authority as authority
    from . import native_owner_runner_v1 as runner
    from . import native_shared_selection as selections

    if type(budget) is not ReaderBudget or budget._clock_raw is None:
        raise ValueError('private reader requires a clock-bound reader budget')
    _selected_reader_scope(scope)
    guard = budget.cleanup_guard()
    if current_reader_budget() is not budget:
        raise ValueError('private reader requires its exact current reader budget')
    owner = runner.validate_owner_record_v2(contract.strict_json(
        owner_raw, 'private reader owner', _OWNER_BYTES))
    if clock._encoded(owner['clock_domain']) != budget._clock_raw:
        raise ValueError('private reader clock domain differs from its owner')
    guard.require_current()
    budget.remaining()
    if budget.deadline_ns > owner['deadline_ns']:
        raise ValueError('private reader budget exceeds the original owner deadline')
    if type(selection) is not contract.NativeSelectionCapture:
        raise ValueError('private reader requires the immutable selected capture')
    # Reuse only exact-byte schema derivation metadata; each live association
    # still reconstructs all carriers and checks its scope, source and budget.
    rebuilt = selections._rebuild(selection.registration, selection.authority,
                                  selection.schemas, selection.receipt_policy,
                                  use_schema_cache=True)
    if rebuilt != selection:
        raise ValueError('private reader selection differs from captured reconstruction')
    # Only the rebuilt carrier supplies bounds; the per-read limit is not a
    # replacement for the later capture layer's aggregate evidence accounting.
    maximum = min(rebuilt.bounds()['max_evidence_bytes'], contract.HARD_LIMITS['stream_bytes'])
    request_limit = contract.HARD_LIMITS['request_bytes']
    execution = contract.strict_json(execution_raw, 'private reader execution', request_limit)
    started = contract.strict_json(started_raw, 'private reader started', request_limit)
    if (type(execution) is not dict or execution.get('kind') != contract.KINDS['execution']
            or type(execution.get('version')) is not int or execution['version'] != 1
            or type(started) is not dict or started.get('kind') != 'd4d_native_shared_attempt'
            or type(started.get('version')) is not int or started['version'] != 1
            or started.get('state') != 'started' or type(started.get('dispatch_limit')) is not int
            or started['dispatch_limit'] != 1):
        raise ValueError('private reader requires exact execution and started kinds/versions')
    if type(execution.get('composition_raw_json')) is not str:
        raise ValueError('private reader requires captured composition bytes')
    composition_raw = execution['composition_raw_json'].encode('utf-8')
    composition = contract.strict_json(composition_raw, 'private reader composition', request_limit)
    if (type(composition) is not dict
            or composition.get('kind') != 'd4d_native_shared_callback_composition'
            or type(composition.get('version')) is not int or composition['version'] != 1
            or execution.get('composition_sha256') != contract.sha(composition_raw)
            or started.get('composition_sha256') != contract.sha(composition_raw)):
        raise ValueError('private reader composition binding differs')
    selection_sha = contract.sha(rebuilt.registration.raw)
    if (type(composition.get('selection_raw_json')) is not str
            or composition['selection_raw_json'].encode('utf-8') != rebuilt.registration.raw
            or composition.get('selection_sha256') != selection_sha
            or execution.get('selection_sha256') != selection_sha
            or rebuilt.registration.pin.sha256 != selection_sha):
        raise ValueError('private reader selection raw bytes or hashes differ')
    attempt = Path(contract.canonical_path(execution.get('attempt_directory'), 'reader attempt'))
    cwd = contract.canonical_path(execution.get('working_directory'), 'reader working directory')
    if (type(execution.get('attempt_id')) is not str or not execution['attempt_id']
            or execution['attempt_id'] != attempt.name
            or started.get('attempt_id') != execution['attempt_id']
            or composition.get('working_directory') != cwd
            or started.get('registration_sha256') != contract.sha(execution_raw)
            or owner['execution_sha256'] != contract.sha(execution_raw)
            or owner['started_sha256'] != contract.sha(started_raw)):
        raise ValueError('private reader execution/started/owner binding differs')
    runtime = execution.get('runtime')
    if (type(runtime) is not dict or type(runtime.get('deadline_seconds')) is not int
            or runtime['deadline_seconds'] <= 0
            or owner['duration_ns'] != runtime['deadline_seconds'] * 1_000_000_000):
        raise ValueError('private reader original owner duration differs')
    rows = []
    for role in ('transcript', 'control'):
        item = owner[role]
        if item['path'] != str(attempt / (role + '.jsonl')):
            raise ValueError('private reader owner stream path differs')
        rows.append((role, item['path'], item['device'], item['inode']))
    selected = execution.get('dependencies')
    scope_profile = contract.canonical(json.loads(scope.profile))
    if (authority._selector(selected) != 1
            or contract.canonical(owner['coordination_profile']) != scope_profile
            or contract.canonical(selected['stream_snapshot_profile']) != scope_profile):
        raise ValueError('private reader selected source identity differs')
    # The unchanged proof first compares this exact declaration against a
    # freshly computed complete dependency identity, then proves its Git
    # roster and blobs. Do not scan once here and again inside that proof.
    # No result or authority is reused by another reader association.
    authority.require_committed(selected)
    # Setup does not renew the deadline. Require the same scope after pure
    # reconstruction and local source/Git proof, before any owner/stream I/O.
    _selected_reader_scope(scope)
    guard.require_current()
    budget.remaining()
    return (_ReaderAssociation(rebuilt, execution_raw, started_raw, owner_raw,
        str(attempt / 'stream-owner.json'), str(attempt / 'stream-owner-stop.json'),
        tuple(rows), maximum), guard)


class _OwnerReaderContext:
    """One private consuming-thread entry over an already bound budget scope.

    This borrows authority and a lease; it does not authorize public execution,
    acquire another clock lease, or propagate a loader into worker threads.
    """
    __slots__ = ('_selected_scope', '_budget', '_association', '_guard',
                 '_creator', '_entered', '_live', '_token', '_owner_metadata')

    def __init__(self, scope, *, selection, execution_raw, started_raw, owner_raw, budget):
        self._selected_scope, self._budget = scope, budget
        self._creator = threading.current_thread()
        self._entered = self._live = False
        self._token = self._owner_metadata = None
        self._association, self._guard = _reader_association(scope, selection,
            execution_raw, started_raw, owner_raw, budget)

    @property
    def budget(self):
        return self._budget

    def _require_lifetime(self):
        if (not self._live or _OWNER_READER.get() is not self
                or threading.current_thread() is not self._creator):
            raise ValueError('private reader context is inactive or belongs to another context')
        _selected_reader_scope(self._selected_scope)
        self._guard.require_current()
        self._budget.remaining()

    def _role_for_path(self, path):
        for role, expected, _, _ in self._association.streams:
            if type(path) is str and path == expected:
                return role
        raise ValueError('private reader path differs from its fixed owner stream')

    def _stop(self):
        try:
            os.lstat(self._association.stop_path)
        except FileNotFoundError as error:
            if error.errno == errno.ENOENT:
                return
            raise
        raise ValueError('native owner stop marker forbids live reads')

    def require_current(self, role=None, path=None, *, max_bytes=None):
        self._require_lifetime()
        if role is not None or path is not None:
            if type(role) is not str or self._role_for_path(path) != role:
                raise ValueError('private reader role/path differs from its fixed owner stream')
        if max_bytes is not None:
            contract.positive_int(max_bytes, 'private reader selected stream byte limit',
                                  self._association.max_bytes)
        self._stop()
        member = evidence.read_regular(self._association.owner_path, 'stream_owner',
                                       max_bytes=_OWNER_BYTES)
        if member.captured.raw != self._association.owner_raw:
            raise ValueError('private reader owner bytes changed')
        if self._owner_metadata is None:
            self._owner_metadata = member.metadata_json
        elif self._owner_metadata != member.metadata_json:
            raise ValueError('private reader owner identity or metadata changed')
        self._stop()
        self._require_lifetime()

    def identity(self, role, path):
        self.require_current(role, path)
        return next({'device': device, 'inode': inode}
                    for named, _, device, inode in self._association.streams if named == role)

    def __enter__(self):
        if self._entered:
            raise ValueError('private reader context cannot be reentered')
        self._entered = True
        try:
            if threading.current_thread() is not self._creator:
                raise ValueError('private reader context belongs to another consuming thread')
            self._token = _OWNER_READER.set(self)
            self._live = True
            self.require_current()
            return self
        except BaseException:
            self._finish()
            raise

    def _finish(self):
        self._live = False
        if self._token is not None:
            token, self._token = self._token, None
            _OWNER_READER.reset(token)

    def __exit__(self, kind, error, traceback):
        if (not self._live or _OWNER_READER.get() is not self
                or threading.current_thread() is not self._creator):
            raise ValueError('private reader context exit requires its active consuming context')
        scope = self._guard.scope
        if (type(scope) is not _ReaderScope
                or _SCOPE.get() is not scope or _BUDGET.get() is not self._budget
                or scope.budget is not self._budget
                or scope._creator is not threading.current_thread()):
            raise ValueError('private reader context exit requires its exact borrowed budget scope')
        # Structural checks only: error exit must not read origins, clocks,
        # owner bytes or the stop marker and thereby mask the body failure.
        from . import native_owner_profile_v1 as profile
        if profile._ACTIVE.get() is not self._selected_scope:
            raise ValueError('private reader context exit requires its exact selected loader scope')
        try:
            # A stop/domain/owner failure after an already failed read is
            # secondary; never replace the original read exception at exit.
            if error is None:
                self.require_current()
        finally:
            self._finish()
        return False


class _Lease:
    def __init__(self, fd):
        self.fd, self.active = fd, True

    def __enter__(self):
        if not self.active:
            raise ValueError('stream lease is already released')
        return self

    def __exit__(self, *unused):
        if self.active:
            self.active = False
            fcntl.flock(self.fd, fcntl.LOCK_UN)


def try_lease(fd, mode):
    """One nonblocking attempt. Only genuine contention returns None."""
    if (type(fd) is not int or fd < 0 or type(mode) is not int
            or mode not in (fcntl.LOCK_SH, fcntl.LOCK_EX)):
        raise ValueError('stream lease requires an actual fd and exact SH or EX mode')
    try:
        fcntl.flock(fd, mode | fcntl.LOCK_NB)
    except OSError as exc:
        if exc.errno not in (errno.EACCES, errno.EAGAIN):
            raise
        return None
    return _Lease(fd)


def sample_metadata(fd, path, budget, *, include_path=False, reader_context=None):
    """Read metadata under SH, without holding the lease for any byte read."""
    if type(budget) is not ReaderBudget or type(include_path) is not bool:
        raise ValueError('metadata sample requires the private absolute reader budget')
    if reader_context is not None:
        if type(reader_context) is not _OwnerReaderContext or reader_context.budget is not budget:
            raise ValueError('metadata sample requires its exact private reader context and budget')
        role = reader_context._role_for_path(path)
    target = Path(path)
    while True:
        if reader_context is not None:
            # Its final lifetime check already samples this exact budget.
            # Keep every owner check at the same lease boundary.
            reader_context.require_current(role, path)
        else:
            budget.remaining()
        lease = try_lease(fd, fcntl.LOCK_SH)
        if lease is None:
            budget.wait()
            continue
        if reader_context is None:
            with lease:
                budget.remaining()
                before = evidence._stat(target.lstat()) if include_path else None
                opened = evidence._stat(os.fstat(fd))
        else:
            failed = False
            try:
                lease.__enter__()
                reader_context.require_current(role, path)
                before = evidence._stat(target.lstat()) if include_path else None
                opened = evidence._stat(os.fstat(fd))
                if include_path and str(target.resolve(strict=True)) != path:
                    raise ValueError('live stream path is not its exact physical path')
            except BaseException:
                failed = True
                raise
            finally:
                try:
                    lease.__exit__(None, None, None)
                except BaseException:
                    if not failed:
                        raise
        if reader_context is not None:
            reader_context.require_current(role, path)
        return (before, opened) if include_path else opened


def reader_budget(budget, *, clock_lease=None):
    """One thread-owned entry; acquisition starts on enter, not construction.

    Context exit checks only domain lifetime, not attempt admission: the parent
    deliberately retains a borrowed scope through cleanup after admission stops.
    A worker must explicitly check remaining() before/after its operation.
    Retain this context object to inspect close_error even when entry fails.
    """
    return _ReaderScope(budget, clock_lease)


def current_reader_budget():
    return _BUDGET.get()
