"""Native catalog reuse: exactly recognized LinkML initialization, 2026-11-06.

The optional catalog guard compiles shipped callback definitions once, without
importing/executing rawloader. Runtime checks use only bound objects and code.
Unknown dependencies disable reuse; this module never changes loader state.
"""
from __future__ import annotations
import ast
import builtins
import hashlib
import importlib.util
from pathlib import Path
import sys
import types

import yaml
from linkml_runtime.linkml_model import meta
from linkml_runtime.utils import yamlutils

ORIGINAL_MARK = None
LINKML_MARK = getattr(yamlutils, 'YAMLMark', None)
_SCHEMA = meta.SchemaDefinition
_ROOT = yamlutils.YAMLRoot
_DEFAULT = _ROOT.MissingRequiredField
_BUILTINS = {name: getattr(builtins, name) for name in ('isinstance', 'type', 'str', 'ValueError')}
_MARKERS = (object(), object())
_CODE = None
_DEFAULT_CODE = None
_PATH = None
SOURCE_SHA256 = None
DEFAULT_SOURCE_SHA256 = None
_root_path = None
INITIALIZATION_ERROR = None


def _definition(code, name):
    found = [item for item in code.co_consts if type(item) is types.CodeType and item.co_name == name]
    if len(found) != 1:
        raise TypeError('shipped callback definition is not unique')
    return found[0]


def _supported_body(raw, name, expected, owner=None):
    """Only the supported callback bodies may establish provenance."""
    nodes = ast.parse(raw).body
    if owner is not None:
        classes = [node for node in nodes if isinstance(node, ast.ClassDef) and node.name == owner]
        if len(classes) != 1:
            raise TypeError('unsupported callback owner')
        nodes = classes[0].body
    functions = [node for node in nodes if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(functions) != 1:
        raise TypeError('unsupported callback definition')
    body = functions[0].body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    actual = ast.dump(ast.Module(body=body, type_ignores=[]), include_attributes=False)
    if actual != ast.dump(ast.parse(expected), include_attributes=False):
        raise TypeError('unrecognized shipped initialization callback body')


try:
    if (not isinstance(LINKML_MARK, type) or len(LINKML_MARK.__bases__) != 1
            or LINKML_MARK.__module__ != yamlutils.__name__ or LINKML_MARK.__name__ != 'YAMLMark'):
        raise TypeError('unsupported initial LinkML mark definition')
    ORIGINAL_MARK = LINKML_MARK.__bases__[0]
    specification = importlib.util.find_spec('linkml')
    if specification is None or specification.origin is None:
        raise TypeError('LinkML distribution is unavailable')
    _PATH = str(Path(specification.origin).parent / 'utils/rawloader.py')
    _raw = Path(_PATH).read_bytes()
    _supported_body(_raw, 'mrf', '''if isinstance(self, SchemaDefinition) and field_name == "name" and self.id:
    id_parts = self.id.replace("#", "/").rsplit("/")
    self.name = id_parts[-1]
else:
    YAMLRoot.MissingRequiredField(self, f"{type(self).__name__}.{field_name}")
''')
    SOURCE_SHA256 = hashlib.sha256(_raw).hexdigest()
    _CODE = _definition(compile(_raw, _PATH, 'exec', dont_inherit=True), 'mrf')
    _root_path = yamlutils.__file__
    _root_raw = Path(_root_path).read_bytes()
    _supported_body(_root_raw, 'MissingRequiredField',
                    'raise ValueError(f"{field_name} must be supplied")', owner='YAMLRoot')
    DEFAULT_SOURCE_SHA256 = hashlib.sha256(_root_raw).hexdigest()
    _root_code = compile(_root_raw, _root_path, 'exec', dont_inherit=True)
    _DEFAULT_CODE = _definition(_definition(_root_code, 'YAMLRoot'), 'MissingRequiredField')
except Exception as exc:
    INITIALIZATION_ERROR = type(exc).__name__ + ': ' + str(exc)


def _function(function, code, namespace, name, module):
    if (type(function) is not types.FunctionType or code is None or function.__code__ != code
            or function.__globals__ is not namespace or function.__module__ != module
            or function.__name__ != name or function.__closure__ is not None
            or function.__defaults__ is not None or function.__kwdefaults__ is not None
            or function.__dict__):
        raise TypeError('unsupported initialization callback')
    effective_builtins = function.__builtins__
    declared_builtins = namespace.get('__builtins__')
    if type(declared_builtins) is types.ModuleType:
        declared_builtins = vars(declared_builtins)
    if type(effective_builtins) is not dict or declared_builtins is not effective_builtins:
        raise TypeError('initialization callback builtin namespace differs')
    for builtin, expected in _BUILTINS.items():
        if (getattr(builtins, builtin) is not expected
                or effective_builtins.get(builtin) is not expected
                or namespace.get(builtin, effective_builtins.get(builtin)) is not expected):
            raise TypeError('initialization callback builtin differs')


def phase():
    """Exact original or shipped initialized state; uncertainty is an error."""
    if INITIALIZATION_ERROR is not None:
        raise TypeError('shipped initialization provenance is unavailable')
    if (yamlutils.YAMLMark is not LINKML_MARK or LINKML_MARK.__bases__ != (ORIGINAL_MARK,)
            or ORIGINAL_MARK.__module__ != 'yaml.error' or ORIGINAL_MARK.__name__ != 'Mark'
            or LINKML_MARK.__module__ != yamlutils.__name__ or LINKML_MARK.__name__ != 'YAMLMark'
            or yaml.reader.Mark is not ORIGINAL_MARK or yaml.Mark is not ORIGINAL_MARK
            or meta.SchemaDefinition is not _SCHEMA or yamlutils.YAMLRoot is not _ROOT
            or _ROOT.MissingRequiredField is not _DEFAULT
            or vars(_ROOT).get('MissingRequiredField') is not _DEFAULT):
        raise TypeError('initialization class or default callback binding differs')
    _function(_DEFAULT, _DEFAULT_CODE, vars(yamlutils), 'MissingRequiredField', yamlutils.__name__)
    for cls in vars(meta).values():
        if (isinstance(cls, type) and cls not in (_SCHEMA, _ROOT)
                and 'MissingRequiredField' in vars(cls)):
            raise TypeError('unexpected metamodel callback ownership')
    callback = _SCHEMA.MissingRequiredField
    if yaml.error.Mark is ORIGINAL_MARK and callback is _DEFAULT:
        if 'MissingRequiredField' in vars(_SCHEMA):
            raise TypeError('unexpected original callback ownership')
        return 0
    if yaml.error.Mark is LINKML_MARK:
        module = sys.modules.get('linkml.utils.rawloader')
        if (type(module) is not types.ModuleType or vars(module).get('__name__') != 'linkml.utils.rawloader'
                or vars(module).get('__file__') != _PATH
                or vars(module).get('SchemaDefinition') is not _SCHEMA
                or vars(module).get('YAMLRoot') is not _ROOT
                or vars(module).get('YAMLMark') is not LINKML_MARK
                or vars(module).get('mrf') is not callback
                or vars(_SCHEMA).get('MissingRequiredField') is not callback):
            raise TypeError('unsupported initialized callback globals')
        _function(callback, _CODE, vars(module), 'mrf', 'linkml.utils.rawloader')
        return 1
    raise TypeError('unsupported Mark/callback initialization pairing')


def marker():
    return _MARKERS[phase()]
