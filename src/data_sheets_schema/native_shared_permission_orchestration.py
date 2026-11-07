"""Fresh source loading for D's saved-permission consumer.

This layer may call A; the consumer may not. It obtains the genuine C-minted
classifier projection and independently derives the controller source map.
C's six-function protocol remains an explicit missing integration dependency
until C round four supplies it. No protocol implementation or compatibility
mapping is manufactured here.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import inspect
from types import FunctionType

from . import native_attribution_controller_v2 as composition
from . import native_execution_authority_v2 as authority
from . import native_shared_controls as pure_controls
from . import native_shared_permissions as consumer


_PROTOCOL_NAME = 'data_sheets_schema.native_shared_permission_protocol'
_PROTOCOL_PATH = 'src/data_sheets_schema/native_shared_permission_protocol.py'
_PROTOCOL_FUNCTIONS = {
    'history_contract': (),
    'initialization_id': (),
    'policy_digest': ('value',),
    'initialize_frame': ('pretool_control',),
    'hook_output': ('classification', 'basis'),
    'permission_arguments': ('policy',),
}
_PROTOCOL_IMPORTS = frozenset(('__future__', 'copy', 'hashlib', 'json'))
_DYNAMIC_NAMES = frozenset((
    '__import__', '__builtins__', 'eval', 'exec', 'compile', 'FunctionType', 'CodeType',
    'getattr', 'setattr', 'delattr', 'hasattr', 'vars', 'globals', 'locals',
))
_DYNAMIC_ATTRIBUTES = frozenset((
    'import_module', 'exec_module', 'load_module', 'find_spec',
    'spec_from_file_location', 'spec_from_loader', 'module_from_spec',
    'SourceFileLoader', 'SourcelessFileLoader', 'ExtensionFileLoader',
    'run_path', 'run_module', '__import__', '__builtins__', '__dict__',
    '__globals__', '__code__', '__closure__', '__signature__', '__wrapped__',
))


def _validate_protocol_source(raw):
    """Inspect all bodies, including deferred imports, before compilation.

    This is a conservative local loading contract, not a Python sandbox. The
    reviewed C implementation must use only these four standard-library
    imports; any expansion needs an explicit integration review. No project
    dependency, reflected import, or dynamic code loader is admitted here.
    """
    if type(raw) is not bytes or not raw:
        raise ValueError('C pure permission protocol needs nonempty source bytes')
    try:
        tree = ast.parse(raw, filename=_PROTOCOL_PATH)
    except (SyntaxError, ValueError) as exc:
        raise ValueError('C pure permission protocol source is not inspectable') from exc
    functions = [node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and not node.name.startswith('_')]
    if (len(functions) != len(_PROTOCOL_FUNCTIONS)
            or {node.name for node in functions} != set(_PROTOCOL_FUNCTIONS)):
        raise ValueError('C pure permission protocol callable roster differs')
    for node in functions:
        arguments = node.args
        if (not isinstance(node, ast.FunctionDef) or node.decorator_list
                or arguments.posonlyargs or arguments.kwonlyargs
                or arguments.vararg or arguments.kwarg
                or arguments.defaults or arguments.kw_defaults
                or tuple(arg.arg for arg in arguments.args) != _PROTOCOL_FUNCTIONS[node.name]):
            raise ValueError('C pure permission protocol signature differs: ' + node.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name not in _PROTOCOL_IMPORTS for alias in node.names):
                raise ValueError('C pure permission protocol has a non-self-contained import')
        elif isinstance(node, ast.ImportFrom):
            if (node.level or node.module not in _PROTOCOL_IMPORTS
                    or any(alias.name == '*' for alias in node.names)):
                raise ValueError('C pure permission protocol has a non-self-contained import')
        if ((isinstance(node, ast.Name) and node.id in _DYNAMIC_NAMES)
                or (isinstance(node, ast.Attribute) and node.attr in _DYNAMIC_ATTRIBUTES)
                or (isinstance(node, ast.ImportFrom)
                    and any(alias.name in _DYNAMIC_NAMES | _DYNAMIC_ATTRIBUTES for alias in node.names))):
            raise ValueError('C pure permission protocol contains dynamic loading or reflection')


def _validate_protocol_interface(module):
    """Require the exact six source-defined callable signatures, not metadata."""
    exported = {name for name, value in vars(module).items()
                if not name.startswith('_') and callable(value)}
    if exported != set(_PROTOCOL_FUNCTIONS):
        raise ValueError('C pure permission protocol callable roster differs')
    for name, parameters in _PROTOCOL_FUNCTIONS.items():
        function = vars(module)[name]
        if (type(function) is not FunctionType or function.__module__ != _PROTOCOL_NAME
                or '__signature__' in function.__dict__ or '__wrapped__' in function.__dict__):
            raise ValueError('C pure permission protocol requires its source-defined function: ' + name)
        signature = inspect.signature(function, follow_wrapped=False)
        if (tuple(signature.parameters) != parameters
                or any(parameter.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD
                       or parameter.default is not inspect.Parameter.empty
                       for parameter in signature.parameters.values())):
            raise ValueError('C pure permission protocol signature differs: ' + name)


@contextmanager
def loaded_protocol(dependencies=None):
    """Compile only the fixed declared C protocol, never a caller module.

    The direct orchestration path preserves existing consumer/carrier class
    identities. Full consumer calls separately run inside A's graph loader.
    C's protocol must therefore be a self-contained pure package module: any
    further project dependency needs an explicitly reviewed loading contract.
    """
    if dependencies is None:
        dependencies = authority.dependency_identity()
    pins = dependencies['base']['package_sources']
    if _PROTOCOL_PATH not in pins:
        raise ValueError('C pure permission protocol is not in the declared source closure')
    path = authority.ROOT / _PROTOCOL_PATH
    digest = pins[_PROTOCOL_PATH]
    raw = authority._verified_source_bytes(path, digest)
    _validate_protocol_source(raw)
    graph = authority.refuse_legacy_consumer_imports(
        raw, name=_PROTOCOL_NAME, package_sources=pins)
    if graph != {_PROTOCOL_NAME: digest}:
        raise ValueError('C pure permission protocol needs a reviewed project dependency contract')
    with authority.verified_source_module(
            _PROTOCOL_NAME, path=path, raw=raw, sha256=digest) as module:
        identity = {'name': _PROTOCOL_NAME, 'path': str(path), 'sha256': digest}
        if authority.module_source_identity(module) != identity:
            raise ValueError('C pure permission protocol source identity differs')
        _validate_protocol_interface(module)
        yield module
        if authority.module_source_identity(module) != identity:
            raise ValueError('C pure permission protocol source identity changed')
        _validate_protocol_interface(module)


@contextmanager
def loaded_permission_inputs():
    """Supply current source authority plus the actual live classifier scope."""
    dependencies = authority.dependency_identity()
    controller_sources = composition.controller_sources()
    with loaded_protocol(dependencies):
        with pure_controls.loaded_controls(dependencies) as controls:
            yield controls, controller_sources


def verify_saved_probe(raw_manifest: bytes, *, expected: dict) -> dict:
    """Rebuild saved evidence with fresh inputs; never grant execution."""
    with loaded_permission_inputs() as (controls, controller_sources):
        return consumer.verify_saved_probe(raw_manifest, expected=expected,
            controls=controls, controller_sources=controller_sources)


def probe_argv(expected, probe_policy):
    """Source-bound argv construction, with no subprocess or effect."""
    with loaded_protocol():
        return consumer.probe_argv(expected, probe_policy)
