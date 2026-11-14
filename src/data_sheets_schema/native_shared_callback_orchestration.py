"""Main-thread admission of immutable callback references.

The loader scopes belong to the caller's main-thread lifetime. Workers may
use captured references, but may not open or close a source-loader scope.
This is a source contract, not a sandbox against arbitrary Python reflection.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import asdict, dataclass, fields, is_dataclass
from inspect import isbuiltin, isfunction, ismethod
from types import MappingProxyType, ModuleType
from pathlib import PurePath
import sys
from threading import current_thread, main_thread, RLock

from . import native_execution_authority_v2 as authority
from . import native_shared_controls_orchestration as loading
from . import native_execution_registration_v2 as registration
from . import native_shared_contract as c
from .native_shared_callback_capture import FrozenSpec


# Closed verified observation/stage graph, including deferred pure utilities.
VALIDATOR_MODULES = frozenset('data_sheets_schema.' + name for name in (
    'agentic_runtime', 'audit_batch_format', 'audit_batches', 'audit_grammar',
    'audit_omissions', 'audit_protocol', 'cache_dependencies', 'canary',
    'chunking', 'corpus', 'duplicate_keys', 'evidence_assertions', 'grounding',
    'native_catalog_initialization', 'native_catalog_reuse', 'native_model_aliases',
    'native_schema_event_reuse', 'native_shared_authority_wire',
    'native_shared_capture', 'native_shared_contract', 'native_shared_controller',
    'native_shared_controls', 'native_shared_current', 'native_shared_effects',
    'native_shared_evidence', 'native_shared_observations', 'native_shared_phase',
    'native_shared_policy', 'native_shared_receipts', 'native_shared_render',
    'native_shared_selection', 'native_shared_stage', 'native_shared_streams',
    'profiles', 'receipt_completion_policy', 'receipts', 'registry', 'resources',
    'schema_snapshot', 'schema_view', 'support_targets', 'typed_audit',
    'source_metadata', 'source_review', 'bc1_context'))


def _binding_identity(value):
    if isinstance(value, (ModuleType, type)) or isfunction(value) or ismethod(value) or isbuiltin(value):
        return id(value), type(value)
    return None


def _environment_identity(value):
    if value is None or type(value) in (str, bytes, int, float, bool):
        return type(value), value
    return _binding_identity(value)


def _effective_bindings(modules, retained=None):
    """Attest imported aliases and callable environments, without retaining runs."""
    result = []
    for module in modules:
        functions = []
        for name, value in sorted(vars(module).items()):
            identity = _binding_identity(value)
            if identity is None:
                continue
            if retained is not None:
                retained.append(value)
            result.append((module.__name__, name, identity))
            origin = value.__name__ if isinstance(value, ModuleType) else getattr(value, '__module__', '')
            if origin and origin.startswith('data_sheets_schema.') and origin not in VALIDATOR_MODULES:
                raise ValueError('validator binding reaches a module outside its closed graph')
            if isfunction(value) or ismethod(value):
                functions.append((name, value.__func__ if ismethod(value) else value))
            elif isinstance(value, type) and value.__module__ == module.__name__:
                for member, function in sorted(vars(value).items()):
                    if isinstance(function, property):
                        for index, accessor in enumerate((function.fget, function.fset, function.fdel)):
                            if isfunction(accessor):
                                functions.append((name + '.' + member + ':' + str(index), accessor))
                    if isinstance(function, (staticmethod, classmethod)):
                        function = function.__func__
                    if isfunction(function):
                        functions.append((name + '.' + member, function))
        for name, function in functions:
            environments = (function.__defaults__ or (),
                tuple(sorted((function.__kwdefaults__ or {}).items())),
                tuple(cell.cell_contents for cell in (function.__closure__ or ())))
            if retained is not None:
                retained.extend((function, function.__code__, function.__defaults__, function.__kwdefaults__))
                retained.extend(environments[0])
                retained.extend(value for _, value in environments[1])
                retained.extend(environments[2])
            result.append((module.__name__, name, id(function), id(function.__code__),
                id(function.__defaults__), id(function.__kwdefaults__),
                tuple(_environment_identity(value) for value in environments[0]),
                tuple((key, _environment_identity(value)) for key, value in environments[1]),
                tuple(_environment_identity(value) for value in environments[2])))
    return tuple(result)


class _ValidatorGuard:
    def __init__(self, modules, source_check, admission_bytes):
        self.modules = tuple(modules)
        self.source_check = source_check
        self.admission_bytes = admission_bytes
        self.disabled = False
        self.references = []
        self.source_identities = (getattr(source_check, 'pins', ()),
            tuple(identity for _, identity in getattr(source_check, 'modules', ())))
        self.baseline = self.snapshot(retain=True)

    def snapshot(self, *, retain=False):
        constants = []
        for module in self.modules:
            for name, value in sorted(vars(module).items()):
                private_contract = name in ('_DYNAMIC', '_LIMITS', '_OBSERVATION_KEYS',
                    '_OBSERVATION_PAYLOADS', '_METADATA', '_COMPOSITION_KEYS',
                    '_REQUIRED', '_OPTIONAL', '_TERMINAL_HELPERS', '_JSON_HELPERS', '_ADVANCE_KEYS')
                private_limit = name.startswith('_') and any(token in name for token in (
                    'LIMIT', 'MAX_', 'CEILING', '_BYTES', '_ENTRIES', '_SECONDS'))
                grammar = hasattr(value, 'pattern') and hasattr(value, 'flags')
                if (name.isupper() and (not name.startswith('_') or private_contract or private_limit or grammar)
                        and _binding_identity(value) is None and name != '_BYTES'):
                    constants.append((module.__name__, name,
                        _constant_value(value, self.references if retain else None)))
        return (_effective_bindings(self.modules, self.references if retain else None), tuple(constants),
            self.source_identities,
            self.admission_bytes, sys.executable, sys.version, sys.implementation.cache_tag)

    def reusable(self):
        if self.disabled:
            return False
        try:
            same = self.snapshot() == self.baseline
        except (ValueError, TypeError, AttributeError, RuntimeError):
            same = False
        if not same:
            self.disabled = True
        return same


def _constant_value(value, retained=None):
    identity = _binding_identity(value)
    if identity is not None or type(value) is object:
        if retained is not None:
            retained.append(value)
        if isfunction(value):
            if retained is not None:
                retained.extend((value.__code__, value.__defaults__, value.__kwdefaults__))
                retained.extend(cell.cell_contents for cell in value.__closure__ or ())
            return (identity, id(value.__code__), id(value.__defaults__), id(value.__kwdefaults__),
                _constant_value(value.__defaults__, retained),
                _constant_value(value.__kwdefaults__, retained),
                tuple(_environment_identity(cell.cell_contents) for cell in value.__closure__ or ()))
        return ('identity', id(value), type(value))
    if value is None or type(value) in (str, bytes, int, float, bool):
        return type(value), value
    if isinstance(value, PurePath):
        return (type(value), str(value))
    if type(value) in (dict, MappingProxyType):
        return (type(value), tuple((_constant_value(key, retained), _constant_value(item, retained))
            for key, item in sorted(value.items(), key=lambda pair: repr(pair[0]))))
    if type(value) in (tuple, list):
        return (type(value).__name__, tuple(_constant_value(item, retained) for item in value))
    if type(value) in (set, frozenset):
        return (type(value), frozenset(_constant_value(item, retained) for item in value))
    if is_dataclass(value):
        return (type(value), tuple((field.name, _constant_value(getattr(value, field.name), retained))
                                  for field in fields(value)))
    # Compiled grammar patterns are immutable, but identity alone omits flags.
    if hasattr(value, 'pattern') and hasattr(value, 'flags'):
        return (type(value), value.pattern, value.flags)
    raise ValueError('validator constant cannot be represented')


def require_main_thread():
    if current_thread() is not main_thread():
        raise ValueError('native callback cannot load captures; preload on the main thread at admission')


@contextmanager
def _locked_stack(lock):
    """Never revoke a carrier or unwind a loader while a callback uses it."""
    stack = ExitStack()
    try:
        yield stack
    except BaseException:
        require_main_thread()
        with lock:
            if not stack.__exit__(*sys.exc_info()):
                raise
    else:
        require_main_thread()
        with lock:
            stack.close()


@dataclass(frozen=True, slots=True)
class _WorkerLoadRefusal:
    historical_names: frozenset

    def find_spec(self, fullname, path=None, target=None):
        if current_thread() is not main_thread() and (
                fullname.startswith(('data_sheets_schema.', 'src.data_sheets_schema.'))
                or fullname in self.historical_names):
            raise ValueError('native callback cannot load module ' + fullname
                             + '; preload on the main thread at admission')
        return None


@contextmanager
def _worker_load_guard(dependencies):
    require_main_thread()
    guard = _WorkerLoadRefusal(frozenset(dependencies['base']['modules'])
                              | frozenset(dependencies['additional_modules']))
    sys.meta_path.insert(0, guard)
    try:
        yield
    finally:
        require_main_thread()
        sys.meta_path.remove(guard)


@dataclass(frozen=True, slots=True)
class _Function:
    """A fixed function and its loader attestation, never a late module lookup."""
    function: object
    module: object
    identity: tuple

    def __call__(self, *args, **kwargs):
        self.check()
        try:
            return self.function(*args, **kwargs)
        finally:
            self.check()

    def check(self):
        if tuple(sorted(authority.module_source_identity(self.module).items())) != self.identity:
            raise ValueError('preloaded callback source identity changed')


@dataclass(frozen=True, slots=True)
class Classifier:
    """No caller-controlled mapping or deferred source loading reaches a worker."""
    _classify: _Function
    _require: _Function
    _controls: object
    _lookup: object
    _simple_command: object
    _lock: object

    def classify(self, command, python, programs, policy):
        with self._lock:
            self._require(self._controls)
            return self._classify(command, python, programs, policy,
                                  classifier_projection=self._controls)

    def readonly(self, command, lookups):
        with self._lock:
            self._require(self._controls)
            return self._lookup(command, lookups, self._simple_command)


def _function(module, name):
    return _Function(getattr(module, name), module,
                     tuple(sorted(authority.module_source_identity(module).items())))


@contextmanager
def preloaded_classifier(dependencies, *, _lock=None):
    """Keep A's verified carrier alive until all callback workers have joined."""
    require_main_thread()
    lock = RLock() if _lock is None else _lock
    with _locked_stack(lock) as stack:
        controls = stack.enter_context(loading.loaded_controls(dependencies))
        pins = dependencies['base']['package_sources']
        pure = stack.enter_context(authority.loaded_verified_package_module(
            'data_sheets_schema.native_shared_controls', package_sources=pins))
        policy = stack.enter_context(authority.loaded_verified_package_module(
            'data_sheets_schema.native_shared_policy', package_sources=pins))
        selected = Classifier(_function(policy, 'classify_bash'),
            _function(pure, 'require_controls'), controls,
            controls['native_readonly'].lookup_command,
            controls['native_command_policy']._simple_command, lock)
        stack.enter_context(_worker_load_guard(dependencies))
        yield selected
        require_main_thread()
        selected._require(controls)


@dataclass(frozen=True, slots=True)
class _Module:
    module: object
    identity: tuple
    members: tuple

    def __getattr__(self, name):
        if tuple(sorted(authority.module_source_identity(self.module).items())) != self.identity:
            raise ValueError('preloaded callback module identity changed')
        for key, value in self.members:
            if key == name:
                return value
        raise AttributeError(name)


def _module(module, names):
    return _Module(module, tuple(sorted(authority.module_source_identity(module).items())),
        tuple((name, _function(module, name) if isfunction(getattr(module, name))
               else getattr(module, name)) for name in names))


@dataclass(frozen=True, slots=True)
class _SourceCheck:
    pins: tuple
    modules: tuple

    def __call__(self):
        for path, digest in self.pins:
            authority._verified_source_bytes(path, digest)
        for module, identity in self.modules:
            if tuple(sorted(authority.module_source_identity(module).items())) != identity:
                raise ValueError('preloaded callback dependency identity changed')


@dataclass(frozen=True, slots=True)
class Callbacks:
    classifier: Classifier
    admission: object
    capture: _Module
    captured: _Module
    streams: _Module
    effects: _Module
    evidence: _Module
    gates: _Module
    policy: _Module
    mapping: _Function
    state: object
    phase: object
    catalogs: object


@contextmanager
def preloaded_callback_utilities(dependencies):
    """Warm reviewed deferred utility imports, without widening A's graph rule.

    Typed source authority, source-review/preflight and omission schema checks
    call these pure utilities from deferred bodies that A deliberately does
    not traverse for utility modules. Keep their verified objects alive across
    worker use, exactly like the directly reached callback dependencies.
    """
    require_main_thread()
    pins = dependencies['base']['package_sources']
    with ExitStack() as stack:
        modules = {name: stack.enter_context(authority.loaded_verified_package_module(
            'data_sheets_schema.' + name, package_sources=pins)) for name in (
                'source_metadata', 'source_review', 'duplicate_keys', 'bc1_context', 'grounding',
                # Stage publication calls host_power from an orchestration body
                # outside A's consumer import graph. Keep all newly introduced
                # timing utilities source-verified for the same worker lifetime.
                'native_host_power', 'native_elapsed', 'native_attempt_timing',
                'native_admission_timer', 'native_pre_dispatch_timing')}
        yield modules


@contextmanager
def preloaded_callbacks(composition, spec, selected, execution, registration_raw, command_argv):
    """Main-thread source loading, then a closed worker interface.

    The caller has just verified outer E with A. All source/input pins remain
    checked, and the captured fixed D consumer rebuilds E on each capture.
    No mutable RunSpec, caller-selected verifier, or source loader is handed
    to callback code. Missing D modules refuse here, before activation writes.

    RunSpec boundary: validated-caller

    RunSpec precondition: Main-thread caller has just verified outer execution through A and supplies its unchanged prepared spec and composition; frozen capture is not independent admission.
    """
    require_main_thread()
    frozen = FrozenSpec.capture(spec)
    dependencies = composition['dependencies']
    pins = dependencies['base']['package_sources']
    preparation_raw = composition['preparation_raw_json'].encode('utf-8')
    prepared = c.strict_json(preparation_raw, max_bytes=c.HARD_LIMITS['request_bytes'])['registration']
    arguments = registration._rebuild_inputs(execution, preparation_raw)
    arguments.pop('preparation_raw')
    lock = RLock()
    with _locked_stack(lock) as stack:
        classifier = stack.enter_context(preloaded_classifier(dependencies, _lock=lock))
        modules = stack.enter_context(preloaded_callback_utilities(dependencies))
        for short in ('native_shared_callback_capture', 'native_shared_callback_io', 'native_shared_capture',
                      'native_shared_selection', 'native_shared_streams', 'native_shared_effects',
                      'native_shared_evidence', 'native_shared_phase', 'native_shared_receipts',
                      'native_shared_render', 'native_shared_policy', 'native_shared_attribution', 'native_shared_gates',
                      'audit_omissions'):
            modules[short] = stack.enter_context(authority.loaded_verified_package_module(
                'data_sheets_schema.' + short, package_sources=pins))
        rebuild = stack.enter_context(registration._consumer(dependencies))
        # A's graph includes deferred imports in its consumer-owned modules.
        # Warm those dependencies on the main thread rather than letting the
        # installed source finder compile one in a callback worker.
        graph = {}
        for module in (*modules.values(), rebuild):
            identity = authority.module_source_identity(module)
            raw = authority._verified_source_bytes(identity['path'], identity['sha256'])
            reached = authority.refuse_legacy_consumer_imports(raw,
                name=identity['name'], package_sources=pins)
            if identity['name'] == 'data_sheets_schema.native_shared_capture' and not set(reached) <= VALIDATOR_MODULES:
                raise ValueError('validator import graph exceeds its closed binding guard')
            graph.update(reached)
        graph_modules = []
        for name in sorted(graph):
            if name.startswith('data_sheets_schema.'):
                graph_modules.append(stack.enter_context(authority.loaded_verified_package_module(
                    name, package_sources=pins)))
        # Orchestrators may import A in their main-thread-only entry points.
        # Their callback entries use the explicit Admission and no loader.
        for short in ('native_shared_capture_orchestration', 'native_shared_attribution_orchestration'):
            name = 'data_sheets_schema.' + short
            relative = 'src/' + name.replace('.', '/') + '.py'
            path, digest = authority.ROOT / relative, pins[relative]
            raw = authority._verified_source_bytes(path, digest)
            modules[short] = stack.enter_context(authority.verified_source_module(
                name, path=path, raw=raw, sha256=digest))
        capture_inputs = modules['native_shared_callback_capture']
        frozen = capture_inputs.FrozenSpec(frozen.fields_json, frozen.rendered_json)
        current = modules['native_shared_selection'].capture(selected.registration.pin.path)
        if asdict(current) != asdict(selected):
            raise ValueError('callback selection changed across source-verified handoff')
        rendered_commands = modules['native_shared_render'].commands(frozen)
        if rendered_commands != command_argv or frozen.render_spec() != composition['render_spec']:
            raise ValueError('immutable callback spec differs from admitted rendering')
        source_pins = {str(authority.ROOT / path): digest for path, digest in pins.items()}
        for pin in (*dependencies['base']['modules'].values(), *dependencies['additional_modules'].values()):
            source_pins[str(authority.ROOT / pin['path'])] = pin['sha256']
        source_pins.update(prepared['pinned_files'])
        source_check = _SourceCheck(tuple(sorted(source_pins.items())), tuple(
            (module, tuple(sorted(authority.module_source_identity(module).items())))
            for module in (*modules.values(), *graph_modules, rebuild)))
        source_check()
        composition_raw = execution['composition_raw_json'].encode('utf-8')
        admitted = capture_inputs.Admission(registration_raw, c.canonical(execution),
            composition_raw, preparation_raw, c.canonical(arguments), current, frozen,
            _function(rebuild, 'rebuild_v2_body'), classifier._controls, source_check)
        capture_inputs._ADMISSIONS[admitted] = tuple(
            (name, getattr(admitted, name)) for name in capture_inputs._ADMISSION_MEMBERS)
        stack.callback(capture_inputs._ADMISSIONS.pop, admitted, None)
        # Reconstruct once before the first possible publication, too.
        admitted.reconstruct()
        validator_modules = {module.__name__: module for module in (*modules.values(), *graph_modules)
                             if module.__name__ in VALIDATOR_MODULES}
        if set(validator_modules) != VALIDATOR_MODULES:
            raise ValueError('verified loader did not load the closed validator graph')
        guard = _ValidatorGuard(validator_modules.values(), source_check,
            (composition_raw, preparation_raw, c.canonical(arguments)))
        prefix = capture_inputs._PrefixOwner(guard, admitted)
        capture_inputs._PREFIX_OWNERS[admitted] = prefix
        stack.callback(capture_inputs._PREFIX_OWNERS.pop, admitted, None)
        stack.callback(prefix.close)
        paths = frozen._agentic_artifact_paths
        phase = modules['native_shared_phase'].PhaseState(rendered_commands,
            full_path=paths['full'], core_path=paths['core'], report_path=paths['report'],
            receipt_path=paths['receipt'], working_directory=composition['working_directory'])
        state = modules['native_shared_attribution_orchestration']._LiveAttribution(
            current, execution_raw=registration_raw, spec=frozen, composition_raw=composition_raw,
            _admission=admitted)
        callbacks = Callbacks(classifier, admitted,
            _module(modules['native_shared_capture_orchestration'], (
                '_load', '_load_live', 'initialize', 'activate_admitted', 'durable_new',
                'observe_advance_settled', 'observe_response_intent', 'observe_request_read',
                'observe_response_written', 'seal_originals')),
            _module(modules['native_shared_capture'], (
                'current_effect_view', '_effect_view_from_decision', '_provenance_block', 'phase_replay')),
            _module(modules['native_shared_streams'], (
                'ROLES', '_LiveStreamRefusal', 'diagnostic_document', 'read_live_stream', 'prefix', 'stream_files')),
            _module(modules['native_shared_effects'], ('classify_effect',)),
            _module(modules['native_shared_evidence'], ('event', 'read_regular')),
            _module(modules['native_shared_gates'], ('current_evidence',)),
            _module(modules['native_shared_policy'], ('stage_overlay_governs',)),
            _function(modules['audit_omissions'], '_mapping'), state, phase,
            modules['native_shared_receipts']._ReceiptCatalogContext())
        stack.enter_context(_worker_load_guard(dependencies))
        yield callbacks
        require_main_thread()
        source_check()
