"""Main-thread admission of immutable callback references.

The loader scopes belong to the caller's main-thread lifetime. Workers may
use captured references, but may not open or close a source-loader scope.
This is a source contract, not a sandbox against arbitrary Python reflection.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import asdict, dataclass
from inspect import isfunction
import sys
from threading import current_thread, main_thread

from . import native_execution_authority_v2 as authority
from . import native_shared_controls_orchestration as loading
from . import native_execution_registration_v2 as registration
from . import native_shared_contract as c
from .native_shared_callback_capture import FrozenSpec


def require_main_thread():
    if current_thread() is not main_thread():
        raise ValueError('native callback cannot load captures; preload on the main thread at admission')


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

    def classify(self, command, python, programs, policy):
        self._require(self._controls)
        return self._classify(command, python, programs, policy,
                              classifier_projection=self._controls)

    def readonly(self, command, lookups):
        self._require(self._controls)
        return self._lookup(command, lookups, self._simple_command)


def _function(module, name):
    return _Function(getattr(module, name), module,
                     tuple(sorted(authority.module_source_identity(module).items())))


@contextmanager
def preloaded_classifier(dependencies):
    """Keep A's verified carrier alive until all callback workers have joined."""
    require_main_thread()
    with ExitStack() as stack:
        controls = stack.enter_context(loading.loaded_controls(dependencies))
        pins = dependencies['base']['package_sources']
        pure = stack.enter_context(authority.loaded_verified_package_module(
            'data_sheets_schema.native_shared_controls', package_sources=pins))
        policy = stack.enter_context(authority.loaded_verified_package_module(
            'data_sheets_schema.native_shared_policy', package_sources=pins))
        selected = Classifier(_function(policy, 'classify_bash'),
            _function(pure, 'require_controls'), controls,
            controls['native_readonly'].lookup_command,
            controls['native_command_policy']._simple_command)
        with _worker_load_guard(dependencies):
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
def preloaded_callbacks(composition, spec, selected, execution, registration_raw, command_argv):
    """Main-thread source loading, then a closed worker interface.

    The caller has just verified outer E with A. All source/input pins remain
    checked, and the captured fixed D consumer rebuilds E on each capture.
    No mutable RunSpec, caller-selected verifier, or source loader is handed
    to callback code. Missing D modules refuse here, before activation writes.
    """
    require_main_thread()
    frozen = FrozenSpec.capture(spec)
    dependencies = composition['dependencies']
    pins = dependencies['base']['package_sources']
    preparation_raw = composition['preparation_raw_json'].encode('utf-8')
    prepared = c.strict_json(preparation_raw, max_bytes=c.HARD_LIMITS['request_bytes'])['registration']
    arguments = registration._rebuild_inputs(execution, preparation_raw)
    arguments.pop('preparation_raw')
    with ExitStack() as stack:
        classifier = stack.enter_context(preloaded_classifier(dependencies))
        modules = {}
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
            graph.update(authority.refuse_legacy_consumer_imports(raw,
                name=identity['name'], package_sources=pins))
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
        with _worker_load_guard(dependencies):
            yield callbacks
        require_main_thread()
        source_check()
