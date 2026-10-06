"""Guard boundaries and the supported loader initialization; no native execution."""
import builtins
import json
import os
from pathlib import Path
import re

import pytest

from data_sheets_schema import cache_dependencies as deps
from data_sheets_schema import native_catalog_reuse as guard


def registry(*, optional):
    return deps.FunctionBindings(additional_modules=guard._MODULES, callable_defaults=optional)


def test_actual_serializer_defaults_need_explicit_opt_in():
    function = json.encoder._make_iterencode
    historical, native = registry(optional=False), registry(optional=True)
    historical.bind(lambda: historical.key(function))
    native.bind(lambda: native.key(function))
    assert not historical.ready
    assert native.ready and native.key(function)
    # Python 3.13 uses a builtin_method subclass for these immutable receivers.
    regex = registry(optional=True)
    regex.bind(lambda: regex.key(json.JSONDecoder.decode))
    assert regex.ready and regex.key(json.JSONDecoder.decode)


def test_only_native_opt_in_admits_frozen_dataclass_object_closure():
    function = guard.snapshots.SchemaSnapshot.__init__
    historical, native = registry(optional=False), registry(optional=True)
    historical.bind(lambda: historical.key(function))
    native.bind(lambda: native.key(function))
    assert not historical.ready and native.ready


@pytest.mark.parametrize('value', ['self', 'container', 'foreign', 'opaque', 'mutable_class'])
def test_unsupported_or_cyclic_defaults_refuse_at_bind(monkeypatch, value):
    function = json.encoder._make_iterencode
    if value == 'self':
        default = function
    elif value == 'container':
        default = []
        default.append(default)
    elif value == 'foreign':
        default = lambda: None
    elif value == 'opaque':
        class Callable:
            def __call__(self):
                return None
        default = Callable()
    else:
        class Mutable:
            pass
        default = Mutable
    monkeypatch.setattr(function, '__defaults__', (default,))
    native = registry(optional=True)
    native.bind(lambda: native.key(function))
    assert not native.ready


def test_mutual_default_cycle_refuses(monkeypatch):
    first, second = json.encoder._make_iterencode, json.decoder.JSONArray
    monkeypatch.setattr(first, '__defaults__', (second,))
    monkeypatch.setattr(second, '__defaults__', (first,))
    native = registry(optional=True)
    native.bind(lambda: native.key(first))
    assert not native.ready


def test_default_containers_are_snapshotted_not_kept_as_mutable_verdict(monkeypatch):
    function = json.encoder._make_iterencode
    value = {'items': [1]}
    monkeypatch.setattr(function, '__defaults__', (value,))
    native = registry(optional=True)
    native.bind(lambda: native.key(function))
    assert native.ready and native.key(function)
    value['items'].append(2)
    with pytest.raises(TypeError, match='modified'):
        native.key(function)


@pytest.mark.parametrize('kind', ['schema_wrapper', 'view_method', 'loader_table', 'dumper',
    'code', 'defaults', 'decoder_only', 'scanner_only', 'constant_contents', 'constant_receiver',
    'regex_default', 'snapshot_constructor', 'serializer_copy'])
def test_effective_runtime_changes_disable_ready_marker(monkeypatch, kind):
    assert guard.runtime_token() is not None
    if kind == 'schema_wrapper':
        monkeypatch.setattr(guard.omissions, '_schema', lambda *a, **k: {})
    elif kind == 'view_method':
        monkeypatch.setattr(guard.views._ReleasableView, 'get_class', lambda *a, **k: None)
    elif kind == 'loader_table':
        monkeypatch.setitem(guard.yaml.SafeLoader.yaml_constructors, '!new', lambda *a: {})
    elif kind == 'dumper':
        monkeypatch.setattr(guard.JSONDumper, 'dumps', lambda *a, **k: '{}')
    elif kind == 'code':
        monkeypatch.setattr(guard.omissions._schema, '__code__', (lambda *a, **k: {}).__code__)
    elif kind == 'defaults':
        monkeypatch.setattr(guard.omissions._read, '__kwdefaults__', {'json_only': True, 'limit': 1})
    elif kind == 'decoder_only':
        monkeypatch.setattr(json._default_decoder, 'parse_float', int)
    elif kind == 'scanner_only':
        alternate = json.JSONDecoder(parse_float=int)
        monkeypatch.setattr(json._default_decoder, 'scan_once', alternate.scan_once)
    elif kind == 'constant_contents':
        monkeypatch.setitem(json.decoder._CONSTANTS, 'Infinity', 1.0)
    elif kind == 'constant_receiver':
        alternate = dict(json.decoder._CONSTANTS)
        monkeypatch.setattr(json._default_decoder, 'parse_constant', alternate.__getitem__)
    elif kind == 'regex_default':
        monkeypatch.setattr(json.JSONDecoder.decode, '__defaults__', (re.compile('x').match,))
    elif kind == 'snapshot_constructor':
        monkeypatch.setattr(guard.snapshots.SchemaSnapshot, '__init__', lambda *a, **k: None)
    else:
        monkeypatch.setattr(guard.meta.ClassDefinition, '__copy__', lambda *a: {}, raising=False)
    assert guard.runtime_token() is None


def test_ready_state_lookup_performs_no_ambient_io(monkeypatch):
    assert guard.runtime_token() is not None
    denied = []
    def reject(*args, **kwargs):
        denied.append(args)
        raise AssertionError('runtime dependency lookup attempted ambient I/O')
    monkeypatch.setattr(builtins, 'open', reject)
    monkeypatch.setattr(Path, 'read_bytes', reject)
    monkeypatch.setattr(Path, 'read_text', reject)
    monkeypatch.setattr(os, 'getenv', reject)
    monkeypatch.setattr(os.environ, 'get', reject)
    assert guard.runtime_token() is not None
    assert denied == []


@pytest.mark.parametrize('owner,name', [
    (guard.yaml.events.ScalarEvent, '__init__'),
    (guard.yaml.tokens.ScalarToken, '__init__'),
    (guard.yaml.nodes.ScalarNode, '__init__'),
    (guard.yaml.error.Mark, '__init__'),
    (guard.yamlutils.YAMLMark, '__init__'),
    (guard.yamlutils.TypedNode, 'add_node'),
    (guard.yamlutils.extended_int, '__new__'),
    (guard.yaml.parser, 'ScalarEvent'),
    (guard.yamlutils, 'YAMLMark'),
    (guard.yamlutils, 'extended_str'),
    (guard.yamlutils, 'SafeLoader'),
    (guard.yaml.cyaml, 'SafeConstructor'),
    (guard.yaml.cyaml, 'Resolver'),
    (guard.yaml.cyaml, 'CParser'),
])
def test_effective_yaml_constructor_and_alias_changes_refuse(monkeypatch, owner, name):
    assert guard.runtime_token() is not None
    monkeypatch.setattr(owner, name, lambda *args, **kwargs: None)
    assert guard.runtime_token() is None


def test_actual_complete_loader_initialization_keeps_ready_marker():
    before = guard.runtime_token()
    assert before is not None
    loader = guard.yamlutils.DupCheckYamlLoader('number: 2\nlabel: example\n')
    try:
        value = loader.get_single_data()
        assert value == {'number': 2, 'label': 'example'}
    finally:
        loader.dispose()
    assert 'yaml_constructors' in vars(guard.yamlutils.DupCheckYamlLoader)
    assert guard.runtime_token() is before


@pytest.mark.parametrize('kind', ['partial', 'owned_pre', 'reordered', 'other_row'])
def test_initial_partial_or_changed_loader_tables_refuse(monkeypatch, kind):
    loader = guard.yamlutils.DupCheckYamlLoader
    table = dict(guard.yamlutils.SafeLoader.yaml_constructors)
    handlers = guard._loader_handlers()
    if kind == 'partial':
        tag = next(iter(handlers))
        table[tag] = handlers[tag]
    elif kind in ('reordered', 'other_row'):
        table.update(handlers)
        if kind == 'reordered':
            table = dict(reversed(tuple(table.items())))
        else:
            table[None] = loader.construct_yaml_str
    monkeypatch.setattr(loader, 'yaml_constructors', table)
    with pytest.raises(TypeError, match='incomplete or changed'):
        guard._loader_handlers()
    candidate = registry(optional=True)
    candidate.bind(guard._state)
    assert not candidate.ready
    assert guard.runtime_token() is None
