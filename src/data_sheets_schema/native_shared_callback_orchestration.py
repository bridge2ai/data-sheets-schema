"""Main-thread admission of immutable callback references.

The loader scopes belong to the caller's main-thread lifetime. Workers may
use captured references, but may not open or close a source-loader scope.
This is a source contract, not a sandbox against arbitrary Python reflection.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass
from threading import current_thread, main_thread

from . import native_execution_authority_v2 as authority
from . import native_shared_controls_orchestration as loading


def require_main_thread():
    if current_thread() is not main_thread():
        raise ValueError('native callback cannot load captures; preload on the main thread at admission')


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
        yield selected
        require_main_thread()
        selected._require(controls)
