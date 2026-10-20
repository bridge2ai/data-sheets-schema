"""Private fixed source profile, without a runner or public execution selector.

Dynamic pins describe files at exact fixed origins, not authenticated loaded
bytecode. Selected lifetime is explicit even when bare-module caches survive.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
from pathlib import Path
import sys
import threading
from types import MappingProxyType, ModuleType

from . import native_attribution_controller as inherited
from . import native_attribution_registration as draft

ROOT = inherited.ROOT
FORMAT = 'native_stream_snapshot_profile_v1'
RESOLVER_PATH = 'src/data_sheets_schema/native_owner_profile_v1.py'
IMPLEMENTATIONS = MappingProxyType({
    'coordination': 'src/data_sheets_schema/native_stream_coordination_v1.py',
    'control': 'src/data_sheets_schema/native_owner_control_v1.py',
    'runner': 'src/data_sheets_schema/native_owner_runner_v1.py',
    'clock': 'src/data_sheets_schema/native_clock_domain_v1.py',
})
_MODULES = MappingProxyType({
    'coordination': 'data_sheets_schema.native_stream_coordination_v1',
    'control': 'data_sheets_schema.native_owner_control_v1',
    'runner': 'data_sheets_schema.native_owner_runner_v1',
    'clock': 'data_sheets_schema.native_clock_domain_v1',
})
_ACTIVE = ContextVar('native_owner_profile_scope', default=None)
_CURRENT_PROFILE = object()


def _source_sha(relative):
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError('private owner profile requires its fixed regular source file: ' + relative)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _origin(role, module):
    expected = ROOT / IMPLEMENTATIONS[role]
    if (type(module) is not ModuleType or module.__name__ != _MODULES[role]
            or sys.modules.get(_MODULES[role]) is not module
            or not getattr(module, '__file__', None)
            or Path(module.__file__).resolve() != expected.resolve()):
        raise ValueError('private owner implementation has a foreign qualified origin')


def source_profile(selector):
    """Return detached fixed-path pins for exact one; zero adds no authority."""
    if type(selector) is not int or selector not in (0, 1):
        raise ValueError('stream_snapshot_profile must be exact integer 0 or 1')
    if selector == 0:
        return None
    inherited.controller_sources()
    # An already-imported resolver must not disappear from recursive package
    # discovery and thereby remove its own definition from selected authority.
    _source_sha(RESOLVER_PATH)
    pins = {}
    for role, relative in IMPLEMENTATIONS.items():
        loaded = sys.modules.get(_MODULES[role])
        if loaded is not None:
            _origin(role, loaded)
        pins[role] = {'path': relative, 'sha256': _source_sha(relative)}
    return {'format': FORMAT, 'profile': 1,
        'base_controller_sources_sha256': inherited.SOURCES_SHA256,
        'implementations': pins}


def verify_profile(profile, package_sources):
    """Recompute the closed profile and require agreement with whole-source pins."""
    if (type(profile) is not dict
            or set(profile) != {'format', 'profile', 'base_controller_sources_sha256', 'implementations'}
            or type(profile['profile']) is not int or profile['profile'] != 1
            or type(package_sources) is not dict
            or draft._encoded(profile) != draft._encoded(source_profile(1))):
        raise ValueError('private owner source profile differs from its fixed implementation')
    if any(package_sources.get(pin['path']) != pin['sha256']
           for pin in profile['implementations'].values()):
        raise ValueError('private owner profile differs from the package source authority')
    if package_sources.get(RESOLVER_PATH) != _source_sha(RESOLVER_PATH):
        raise ValueError('private owner resolver differs from the package source authority')


def _bare_origins(controls):
    """Snapshot fixed loader declarations, never an observed module's path."""
    from . import native_execution_authority as authority
    declarations = {**inherited.controller_sources()['modules'],
        **authority.neutral.ADDITIONAL, **authority.ADDITIONAL}
    if set(controls) != set(declarations):
        raise ValueError('private selected loader module roster differs')
    return tuple((name, str((ROOT / declarations[name]['path']).resolve()))
                 for name in sorted(declarations))


class _Scope:
    def __init__(self, profile, controls, *, parent=None, owner_budget=None):
        self.profile = draft._encoded(profile) if parent is None else parent.profile
        self.controls = controls
        self.members = tuple(controls.items()) if parent is None else parent.members
        self._origins = _bare_origins(controls) if parent is None else parent._origins
        self._creator = threading.current_thread()
        self._parent, self._owner_budget = parent, owner_budget
        self._budget = self._guard = self._token = None
        self._entered = False
        self.live = parent is None

    def _require_members(self):
        if (not self.live
                or set(self.controls) != {name for name, _ in self.members}
                or any(self.controls[name] is not module for name, module in self.members)):
            raise ValueError('private owner binding is outside its selected loader lifetime')

    def _require_bare_origins(self):
        for name, expected in self._origins:
            module = self.controls[name]
            source = getattr(module, '__file__', None)
            if (type(module) is not ModuleType or module.__name__ != name
                    or sys.modules.get(name) is not module
                    or type(source) is not str or not source
                    or str(Path(source).resolve()) != expected):
                raise ValueError('private selected bare module has a stale or foreign origin: ' + name)

    def _require_parent_graph(self):
        # A worker inspects its retained parent without pretending the parent's
        # ContextVar or creator thread is current in this worker.
        parent = self._parent
        if (type(parent) is not _Scope or parent._parent is not None
                or parent.profile != self.profile or parent.controls is not self.controls
                or parent.members != self.members or parent._origins != self._origins):
            raise ValueError('private worker binding differs from its original loader parent')
        parent._require_members()
        self._require_bare_origins()
        for role, name in _MODULES.items():
            _origin(role, sys.modules.get(name))

    def require(self):
        if (not self.live or _ACTIVE.get() is not self
                or threading.current_thread() is not self._creator):
            raise ValueError('private owner binding is outside its selected loader lifetime')
        self._require_members()
        if self._parent is None:
            self._require_bare_origins()
        else:
            self._guard.require_current()
            self._budget.remaining()
            self._require_parent_graph()
            self._budget.remaining()

    def __enter__(self):
        if self._parent is None or self._entered:
            raise ValueError('private worker scope requires one fresh worker entry')
        self._entered = True
        try:
            from . import native_stream_coordination_v1 as coordination
            if (threading.current_thread() is not self._creator
                    or self._creator is self._parent._creator):
                raise ValueError('private worker scope requires its distinct consuming thread')
            budget = coordination.current_reader_budget()
            owner = self._owner_budget
            if (type(budget) is not coordination.ReaderBudget or budget is owner
                    or budget.clock_domain() is None):
                raise ValueError('private worker scope requires a distinct clock-bound worker budget')
            self._budget, self._guard = budget, budget.cleanup_guard()
            self._guard.require_current()
            if (budget.clock_domain() != owner.clock_domain()
                    or budget.deadline_ns > owner.deadline_ns
                    or len(budget.stop_events) != len(owner.stop_events)
                    or any(actual is not expected for actual, expected in
                           zip(budget.stop_events, owner.stop_events))):
                raise ValueError('private worker budget differs from its original owner binding')
            budget.remaining()
            self._token = _ACTIVE.set(self)
            self.live = True
            self.require()
            return self
        except BaseException:
            self._finish_worker()
            raise

    def _finish_worker(self):
        self.live = False
        if self._token is not None:
            token, self._token = self._token, None
            _ACTIVE.reset(token)

    def __exit__(self, kind, error, traceback):
        from . import native_stream_coordination_v1 as coordination
        if (self._parent is None or not self.live or _ACTIVE.get() is not self
                or threading.current_thread() is not self._creator):
            raise ValueError('private worker scope exit requires its active consuming context')
        scope = self._guard.scope
        if (type(scope) is not coordination._ReaderScope
                or coordination._SCOPE.get() is not scope
                or coordination.current_reader_budget() is not self._budget
                or scope.budget is not self._budget or scope._creator is not self._creator):
            raise ValueError('private worker scope exit requires its exact borrowed budget scope')
        try:
            # Parent expiry/graph refusal must not replace an existing operation
            # failure or prevent invalidation of this correctly owned entry.
            if error is None:
                self.require()
        finally:
            self._finish_worker()
        return False


def _worker_scope(parent, owner_budget):
    """One reader-only worker entry; acquire no lease and alter no global loader."""
    from . import native_stream_coordination_v1 as coordination
    if type(parent) is not _Scope or parent._parent is not None:
        raise ValueError('private worker scope requires its original loader parent')
    if (type(owner_budget) is not coordination.ReaderBudget
            or owner_budget.clock_domain() is None):
        raise ValueError('private worker scope requires the original clock-bound owner budget')
    return _Scope(None, parent.controls, parent=parent, owner_budget=owner_budget)


@contextmanager
def _reconstruction_controls(profile=_CURRENT_PROFILE):
    """Use the current selected graph for complete offline C/E reconstruction.

    Original loader entries may prepare proposals without a runtime budget.
    Existing parent/worker budgets remain exact and cannot be renewed here.
    This borrows no new scope/lease and grants no control or runner factory.
    """
    from . import native_stream_coordination_v1 as coordination
    scope = _ACTIVE.get()
    if (type(scope) is not _Scope or not scope.live
            or threading.current_thread() is not scope._creator):
        raise ValueError('selected reconstruction requires its exact current loader scope')
    if profile is _CURRENT_PROFILE:
        profile = json.loads(scope.profile)
    if (type(profile) is not dict
            or draft._encoded(profile) != scope.profile):
        raise ValueError('selected reconstruction requires its exact current loader scope')
    profile_raw = draft._encoded(profile)
    budget = coordination.current_reader_budget()
    reader_scope = coordination._SCOPE.get()
    guard = None
    if budget is not None:
        if type(budget) is not coordination.ReaderBudget or budget.clock_domain() is None:
            raise ValueError('selected reconstruction requires its exact clock-bound budget')
        guard = budget.cleanup_guard()
    elif scope._parent is not None or reader_scope is not None:
        raise ValueError('selected worker reconstruction requires its current budget')

    def require():
        if (_ACTIVE.get() is not scope or coordination.current_reader_budget() is not budget
                or coordination._SCOPE.get() is not reader_scope
                or scope.profile != profile_raw
                or draft._encoded(profile) != profile_raw):
            raise ValueError('selected reconstruction context changed')
        if guard is not None:
            guard.require_current()
            budget.remaining()
        scope.require()
        # A worker's require() just checked these same qualified origins
        # through _require_parent_graph(). Parent scopes check only bare
        # origins there, so retain their explicit qualified sweep.
        if scope._parent is None:
            for role, name in _MODULES.items():
                _origin(role, sys.modules.get(name))
        if draft._encoded(source_profile(1)) != scope.profile:
            raise ValueError('selected reconstruction source profile changed')
        if guard is not None:
            guard.require_current()
            budget.remaining()

    require()
    yield scope.controls
    # A body exception skips this success-only check, preserving its cause.
    require()


@contextmanager
def _binding_scope(profile, package_sources, controls):
    """Fixed authority-loader seam only; no caller-selected import or callback."""
    verify_profile(profile, package_sources)
    # These fixed imports may reuse same-origin cached modules; no claim is
    # made that origin/hash checks authenticate their in-memory code objects.
    from . import native_stream_coordination_v1 as coordination
    from . import native_owner_control_v1 as owner
    from . import native_owner_runner_v1 as runner
    from . import native_clock_domain_v1 as clock
    _origin('coordination', coordination)
    _origin('control', owner)
    _origin('runner', runner)
    _origin('clock', clock)
    scope = _Scope(profile, controls)
    token = _ACTIVE.set(scope)
    try:
        yield
    finally:
        scope.live = False  # Also invalidates a copied ContextVar context.
        _ACTIVE.reset(token)


def bind_control(profile, controls):
    """Bind a fresh private class only inside its exact selected loader entry."""
    scope = _ACTIVE.get()
    if (type(scope) is not _Scope or scope._parent is not None or controls is not scope.controls
            or draft._encoded(profile) != scope.profile):
        raise ValueError('private owner control requires its exact selected loader scope')
    scope.require()
    from . import native_owner_control_v1 as owner
    _origin('control', owner)
    roles = inherited.controller_sources()['modules']
    bound = owner.make_control({name: controls[name] for name in roles})

    class SelectedOwnerControl(bound):
        def __init__(self, *args, **kwargs):
            scope.require()
            super().__init__(*args, **kwargs)

        def _check_budget(self):
            # Base service catches this before cleanup, retaining first stop.
            scope.require()
            return super()._check_budget()

        def _start_work(self, kind, event, operation):
            scope.require()
            owner_budget = self._owner_budget
            if owner_budget.clock_domain() is None:
                return super()._start_work(kind, event, operation)

            def selected_operation():
                # The private base enters the actual worker's clock/budget
                # before invoking this fixed wrapper, not another loader.
                with _worker_scope(scope, owner_budget):
                    return operation()

            return super()._start_work(kind, event, selected_operation)

        def start(self, *args, **kwargs):
            try:
                scope.require()
                return super().start(*args, **kwargs)
            except BaseException as error:
                self._latch_failure(error)
                self._stop_history()
                raise

        def finish(self):
            try:
                scope.require()
            except BaseException as error:
                self._latch_failure(error)
                self._stop_history()
                raise
            return super().finish()

    return SelectedOwnerControl


def bind_runner(profile, controls):
    """One private owner lifetime in the exact selected scope; no public route."""
    control_class = bind_control(profile, controls)
    scope = _ACTIVE.get()
    from . import native_owner_runner_v1 as runner
    _origin('runner', runner)
    return runner._make_runner(scope, profile, controls, control_class)


def bind_reader_context(profile, controls, *, selection, execution_raw,
                        started_raw, owner_raw, budget):
    """Bind a reader in this original or borrowed consuming-thread scope.

    Neither mode supplies a public execution permission.
    """
    scope = _ACTIVE.get()
    if (type(scope) is not _Scope or controls is not scope.controls
            or draft._encoded(profile) != scope.profile):
        raise ValueError('private reader requires its exact selected loader scope')
    scope.require()
    from . import native_stream_coordination_v1 as coordination
    _origin('coordination', coordination)
    return coordination._OwnerReaderContext(scope, selection=selection,
        execution_raw=execution_raw, started_raw=started_raw,
        owner_raw=owner_raw, budget=budget)
