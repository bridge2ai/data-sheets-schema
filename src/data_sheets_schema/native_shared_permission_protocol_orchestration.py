"""Source-bound loading of C's six pure permission functions, 2026-11-07.

Only orchestration imports A. The protocol itself remains self-contained.
The projection checks its fixed source, members and lifetime around each call;
this is a reviewed source contract, not a sandbox for arbitrary Python code.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import inspect
import json
from types import FunctionType

from . import native_execution_authority_v2 as authority


_NAME = 'data_sheets_schema.native_shared_permission_protocol'
_PATH = 'src/data_sheets_schema/native_shared_permission_protocol.py'
_FUNCTIONS = {
    'history_contract': (), 'initialization_id': (), 'policy_digest': ('value',),
    'initialize_frame': ('pretool_control',), 'hook_output': ('classification', 'basis'),
    'permission_arguments': ('policy',),
}
_IMPORTS = frozenset(('__future__', 'copy', 'hashlib', 'json'))
_DYNAMIC_NAMES = frozenset((
    '__import__', '__builtins__', 'eval', 'exec', 'compile', 'FunctionType', 'CodeType',
    'getattr', 'setattr', 'delattr', 'hasattr', 'vars', 'globals', 'locals'))
_DYNAMIC_ATTRIBUTES = frozenset((
    'import_module', 'exec_module', 'load_module', 'find_spec',
    'spec_from_file_location', 'spec_from_loader', 'module_from_spec',
    'SourceFileLoader', 'SourcelessFileLoader', 'ExtensionFileLoader',
    'run_path', 'run_module', '__import__', '__builtins__', '__dict__',
    '__globals__', '__code__', '__closure__', '__signature__', '__wrapped__'))
_CONSTANTS = ('_CONTRACT', '_HISTORY_CONTRACT', '_INIT_ID')
_BINDINGS = ('_deepcopy', '_hashlib', '_json')


def _validate_source(raw):
    if type(raw) is not bytes or not raw:
        raise ValueError('C pure permission protocol needs nonempty source bytes')
    try:
        tree = ast.parse(raw, filename=_PATH)
    except (SyntaxError, ValueError) as exc:
        raise ValueError('C pure permission protocol source is not inspectable') from exc
    functions = [node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and not node.name.startswith('_')]
    if len(functions) != len(_FUNCTIONS) or {node.name for node in functions} != set(_FUNCTIONS):
        raise ValueError('C pure permission protocol callable roster differs')
    for node in functions:
        arguments = node.args
        if (not isinstance(node, ast.FunctionDef) or node.decorator_list
                or arguments.posonlyargs or arguments.kwonlyargs or arguments.vararg
                or arguments.kwarg or arguments.defaults or arguments.kw_defaults
                or tuple(arg.arg for arg in arguments.args) != _FUNCTIONS[node.name]):
            raise ValueError('C pure permission protocol signature differs: ' + node.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name not in _IMPORTS or not alias.asname
                   or not alias.asname.startswith('_') for alias in node.names):
                raise ValueError('C pure permission protocol requires self-contained private imports')
        elif isinstance(node, ast.ImportFrom):
            if (node.level or node.module not in _IMPORTS
                    or any(alias.name == '*' or (node.module != '__future__'
                           and (not alias.asname or not alias.asname.startswith('_')))
                           for alias in node.names)):
                raise ValueError('C pure permission protocol requires self-contained private imports')
        if ((isinstance(node, ast.Name) and node.id in _DYNAMIC_NAMES)
                or (isinstance(node, ast.Attribute) and node.attr in _DYNAMIC_ATTRIBUTES)
                or (isinstance(node, ast.ImportFrom)
                    and any(alias.name in _DYNAMIC_NAMES | _DYNAMIC_ATTRIBUTES for alias in node.names))):
            raise ValueError('C pure permission protocol contains dynamic loading or reflection')


def _validate_interface(module):
    exported = {name for name, value in vars(module).items()
                if not name.startswith('_') and callable(value)}
    if exported != set(_FUNCTIONS):
        raise ValueError('C pure permission protocol callable roster differs')
    for name, parameters in _FUNCTIONS.items():
        function = vars(module)[name]
        if (type(function) is not FunctionType or function.__module__ != _NAME
                or '__signature__' in function.__dict__ or '__wrapped__' in function.__dict__):
            raise ValueError('C pure permission protocol requires its source-defined function: ' + name)
        signature = inspect.signature(function, follow_wrapped=False)
        if (tuple(signature.parameters) != parameters
                or any(parameter.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD
                       or parameter.default is not inspect.Parameter.empty
                       for parameter in signature.parameters.values())):
            raise ValueError('C pure permission protocol signature differs: ' + name)


class _Protocol:
    __slots__ = ('_module', '_identity', '_path', '_constants', '_bindings', '_active')

    def __init__(self, module, identity, path):
        self._module, self._identity, self._path = module, dict(identity), path
        self._constants = {name: json.dumps(vars(module)[name], sort_keys=True, allow_nan=False)
                           for name in _CONSTANTS}
        self._bindings = {name: vars(module)[name] for name in _BINDINGS}
        self._active = True
        self._check()

    def _check(self):
        if not self._active:
            raise ValueError('C pure permission protocol scope is closed')
        if authority.module_source_identity(self._module) != self._identity:
            raise ValueError('C pure permission protocol source identity changed')
        authority._verified_source_bytes(self._path, self._identity['sha256'])
        _validate_interface(self._module)
        values = vars(self._module)
        for name, value in self._constants.items():
            if name not in values or json.dumps(values[name], sort_keys=True, allow_nan=False) != value:
                raise ValueError('C pure permission protocol constant changed: ' + name)
        if any(values.get(name) is not value for name, value in self._bindings.items()):
            raise ValueError('C pure permission protocol import binding changed')

    def _call(self, name, *arguments):
        self._check()
        try:
            return vars(self._module)[name](*arguments)
        finally:
            self._check()

    def history_contract(self):
        return self._call('history_contract')

    def initialization_id(self):
        return self._call('initialization_id')

    def policy_digest(self, value):
        return self._call('policy_digest', value)

    def initialize_frame(self, pretool_control):
        return self._call('initialize_frame', pretool_control)

    def hook_output(self, classification, basis):
        return self._call('hook_output', classification, basis)

    def permission_arguments(self, policy):
        return self._call('permission_arguments', policy)


@contextmanager
def loaded_protocol(dependencies=None):
    """Yield a live six-method projection; source and call results stay checked.

    Callers supply current verified dependencies or derive them here. This
    loading operation does not replace the caller's committed-source proof,
    execution admission, or validation of C's classifier-projection carrier.
    """
    dependencies = authority.dependency_identity() if dependencies is None else dependencies
    pins = dependencies['base']['package_sources']
    if _PATH not in pins:
        raise ValueError('C pure permission protocol is not in the declared source closure')
    path, digest = authority.ROOT / _PATH, pins[_PATH]
    raw = authority._verified_source_bytes(path, digest)
    _validate_source(raw)
    graph = authority.refuse_legacy_consumer_imports(raw, name=_NAME, package_sources=pins)
    if graph != {_NAME: digest}:
        raise ValueError('C pure permission protocol needs a reviewed project dependency contract')
    with authority.verified_source_module(_NAME, path=path, raw=raw, sha256=digest) as module:
        identity = {'name': _NAME, 'path': str(path), 'sha256': digest}
        if authority.module_source_identity(module) != identity:
            raise ValueError('C pure permission protocol source identity differs')
        _validate_interface(module)
        projected = _Protocol(module, identity, path)
        try:
            yield projected
            projected._check()
        finally:
            projected._active = False
