"""Conservative function bindings for optional pure-work caches.

Bindings are captured once during the consumer module's initialization. An
unfamiliar replacement never becomes cacheable merely by being observed first.
We do not attempt to discover arbitrary replacement-function global state.
"""
from __future__ import annotations

import dataclasses
import contextlib
from enum import Enum
import hashlib
from pathlib import Path
import re
import reprlib
import sys
import types
from typing import Any, Callable

_SHIPPED_MODULES = frozenset({
    'data_sheets_schema.historical_digest', 'data_sheets_schema.schema_digest',
    'data_sheets_schema.schema_view', 'importlib.metadata', 'dataclasses',
    'linkml_runtime.utils.schemaview', 'linkml_runtime.linkml_model.meta',
    'linkml_runtime.utils.yamlutils', 'linkml_runtime.utils.enumerations',
    'linkml_runtime.utils.metamodelcore', 'jsonasobj2._jsonobj',
    'yaml', 'yaml.constructor', 'yaml._yaml', 'yaml.resolver',
})


def setting_key(value: Any) -> tuple:
    """Snapshot supported settings; unfamiliar mutable state is not cacheable."""
    if value is dataclasses.MISSING or value is dataclasses._HAS_DEFAULT_FACTORY:
        return type(value), value
    if isinstance(value, Enum):
        return type(value), value.name, setting_key(value.value)
    if isinstance(value, re.Pattern):
        return type(value), value.pattern, value.flags
    if value is None or type(value) in (bool, int, float, str, bytes):
        return type(value), value
    if type(value) in (tuple, list):
        return type(value), tuple(setting_key(item) for item in value)
    if type(value) is dict:
        return dict, tuple((setting_key(k), setting_key(v)) for k, v in value.items())
    if type(value) in (set, frozenset):
        return type(value), frozenset(setting_key(item) for item in value)
    raise TypeError('unsupported mutable cache dependency')


class FunctionBindings:
    """A closed set of effective functions; changes bypass the consumer cache."""

    def __init__(self) -> None:
        self._functions: dict[Any, tuple[tuple, int]] = {}
        self._binding = False
        self._bound = False
        self.ready = False

    def bind(self, capture: Callable[[], Any]) -> None:
        if self._bound:
            raise RuntimeError('cache function bindings are already closed')
        self._bound = self._binding = True
        try:
            capture()
        except Exception:
            self._functions.clear()
        else:
            self.ready = True
        finally:
            self._binding = False

    def _closure_key(self, value: Any, seen: frozenset[int]) -> tuple:
        if id(value) in seen:
            raise ValueError('cyclic cache dependency closure')
        nested = seen | {id(value)}
        if isinstance(value, types.FunctionType):
            return self.key(value, seen)
        if any(value is cls for cls in (list, dict, set, tuple, frozenset)):
            return type(value), value
        if type(value) in (tuple, list):
            return type(value), tuple(self._closure_key(item, nested) for item in value)
        if type(value) is dict:
            return dict, tuple((self._closure_key(k, nested), self._closure_key(v, nested))
                               for k, v in value.items())
        if type(value) in (set, frozenset):
            return type(value), frozenset(self._closure_key(item, nested) for item in value)
        return setting_key(value)

    def key(self, function: Any, seen: frozenset[int] = frozenset()) -> tuple:
        from yaml._yaml import CParser
        if function is None:
            return ()
        if not self._binding and (not self.ready or function not in self._functions):
            raise TypeError('unfamiliar cache dependency callable')
        if not isinstance(function, (types.FunctionType, types.BuiltinFunctionType,
                types.MethodDescriptorType, types.WrapperDescriptorType,
                types.ClassMethodDescriptorType, type(CParser.check_event))):
            raise TypeError('unsupported cache dependency callable state')
        if (self._binding and isinstance(function, types.FunctionType)
                and function.__module__ not in _SHIPPED_MODULES):
            raise TypeError('replacement function present before cache binding')
        if self._binding and isinstance(function, types.FunctionType):
            module_path = getattr(sys.modules.get(function.__module__), '__file__', None)
            origin = function.__code__.co_filename
            generated = origin == '<string>' and function.__name__ in (
                '__init__', '__repr__', '__eq__', '__hash__')
            if not generated and origin not in (module_path, contextlib.__file__, reprlib.__file__):
                raise TypeError('replacement function has an unbound source origin')
        bound = getattr(function, '__self__', None)
        if bound is not None and not isinstance(bound, (types.ModuleType, type)):
            raise TypeError('unsupported bound cache dependency callable state')
        if id(function) in seen:
            raise ValueError('cyclic cache dependency callable')
        nested = seen | {id(function)}
        code = getattr(function, '__code__', None)
        cells = getattr(function, '__closure__', None) or ()
        names = getattr(code, 'co_freevars', ())
        if len(cells) != len(names):
            raise ValueError('uninspectable cache dependency closure')
        closure = []
        for name, cell in zip(names, cells):
            value = cell.cell_contents
            if name == '__class__' and isinstance(value, type):
                state = (type(value), value)
            else:
                state = self._closure_key(value, nested)
            closure.append((name, state))
        state = (function, code, setting_key(getattr(function, '__defaults__', None)),
                 setting_key(getattr(function, '__kwdefaults__', None)), tuple(closure),
                 self.key(getattr(function, '__wrapped__', None), nested))
        if self._binding:
            token = self._functions.get(function, ((), len(self._functions)))[1]
            self._functions[function] = state, token
        # __wrapped__ is introspection metadata; some installed decorators
        # remove it on first use. Every function it names is checked above,
        # while code/defaults/actual closure state must remain as bound.
        elif state[:-1] != self._functions[function][0][:-1]:
            raise TypeError('modified cache dependency callable')
        # The closed registry has validated the full effective signature above.
        # A small stable token avoids retaining the same fixed implementation
        # metadata in every content-key entry. Registries are never rebound.
        return (self._functions[function][1],)


def constructor_key(cls: type, functions: FunctionBindings) -> tuple:
    return (cls, functions.key(type(cls).__call__),
            tuple((name, functions.key(getattr(cls, name, None)))
                  for name in ('__new__', '__init__', '__post_init__')))


def _methods_key(cls: type, functions: FunctionBindings, views) -> tuple:
    effective = {}
    for base in cls.__mro__:
        for name, member in vars(base).items():
            effective.setdefault(name, member)
    methods = []
    for name, member in sorted(effective.items()):
        if isinstance(member, views._InstanceCached):
            state = (member, functions.key(member.function), member.name, member.maxsize, member.typed)
        elif isinstance(member, (staticmethod, classmethod)):
            state = functions.key(member.__func__)
        elif isinstance(member, property):
            state = tuple(functions.key(fn) for fn in (member.fget, member.fset, member.fdel))
        elif callable(member):
            state = functions.key(member)
        else:
            continue
        methods.append((name, state))
    return tuple(methods)


def schema_key(functions: FunctionBindings) -> tuple:
    """The parser, constructors and effective view methods used by both caches."""
    from data_sheets_schema import schema_view as views
    from linkml_runtime.linkml_model import meta
    parsers = tuple(functions.key(fn) for fn in
                    (views.version_document, views.version_view, views.yaml.load))
    models = tuple((name, constructor_key(cls, functions)) for name, cls in sorted(vars(meta).items())
                   if isinstance(cls, type) and cls.__module__ == meta.__name__)
    constructors = tuple(constructor_key(cls, functions) for cls in
                         (views.SchemaDefinition, views._ReleasableView, views.DupCheckYamlLoader))
    yaml_tables = tuple((name, tuple((prefix, functions.key(fn)) for prefix, fn in
                                    getattr(views.DupCheckYamlLoader, name).items()))
                        for name in ('yaml_constructors', 'yaml_multi_constructors'))
    resolvers = tuple((name, setting_key(getattr(views.DupCheckYamlLoader, name)))
                      for name in ('yaml_implicit_resolvers', 'yaml_path_resolvers'))
    return (hashlib.sha256(Path(views.__file__).read_bytes()).digest(), parsers, models, constructors,
            _methods_key(views._ReleasableView, functions, views),
            _methods_key(views.DupCheckYamlLoader, functions, views), yaml_tables, resolvers)
