"""Optional native catalog reuse over a closed, unchanged pure dependency set.

Ordinary fixed-code imports bind the implementation once. Runtime lookup does
not read files or consult the environment; uncertainty takes the old producer.
"""
from __future__ import annotations

import copy
import _json
import functools
import json
import types

import yaml
from linkml_runtime.dumpers import json_dumper
from linkml_runtime.dumpers.json_dumper import JSONDumper
from linkml_runtime.utils import context_utils, formatutils, yamlutils, metamodelcore, strictness, uri_validator
from linkml_runtime.linkml_model import meta, annotations, extensions, units
import rdflib.namespace as rdf_namespaces
from linkml_runtime.utils.namespaces import Namespaces
import jsonasobj2._jsonobj as jsonobj

from . import audit_omissions as omissions
from . import native_shared_contract as contract
from . import duplicate_keys, grounding, schema_snapshot as snapshots, schema_view as views, support_targets
from .cache_dependencies import FunctionBindings, _methods_key, _schema_state, constructor_key, setting_key


_MODULES = frozenset({
    'data_sheets_schema.audit_omissions', 'data_sheets_schema.duplicate_keys',
    'data_sheets_schema.grounding', 'data_sheets_schema.schema_snapshot',
    'data_sheets_schema.support_targets',
    'data_sheets_schema.native_shared_contract',
    'yaml.reader', 'yaml.scanner', 'yaml.parser', 'yaml.composer', 'yaml.loader',
    'yaml.events', 'yaml.nodes', 'yaml.error', 'yaml.tokens', 'yaml.cyaml',
    'linkml_runtime.dumpers.json_dumper', 'linkml_runtime.dumpers.dumper_root',
    'linkml_runtime.utils.context_utils', 'linkml_runtime.utils.namespaces',
    'linkml_runtime.utils.formatutils', 'jsonasobj2.extendednamespace',
    'json', 'json.encoder', 'json.decoder', 'json.scanner', 'copy',
    'requests.structures',
    'linkml_runtime.linkml_model.annotations', 'linkml_runtime.linkml_model.extensions',
    'linkml_runtime.linkml_model.units', 'linkml_runtime.utils.strictness',
    'linkml_runtime.utils.uri_validator', 'rdflib.namespace',
})
_FUNCTIONS = FunctionBindings(additional_modules=_MODULES, callable_defaults=True)
_READY = object()
_STATE = None
_INITIALIZED_STATE = None
_PARSE = yaml.parse
_DEFAULT_LOADER = yaml.Loader

_YAML_DEFINITIONS = (yaml.events, yaml.tokens, yaml.nodes, yaml.error)
_YAML_EXTRAS = ((yaml.scanner, 'SimpleKey'), (yaml.scanner, 'ScannerError'),
               (yaml.parser, 'ParserError'), (yaml.composer, 'ComposerError'),
               (yaml.constructor, 'ConstructorError'), (yaml.reader, 'ReaderError'))
_YAML_NAMES = frozenset(name for module in _YAML_DEFINITIONS for name, cls in vars(module).items()
                        if isinstance(cls, type) and cls.__module__ == module.__name__) | frozenset(
                        name for _module, name in _YAML_EXTRAS) | frozenset({
                        'Reader', 'Scanner', 'Parser', 'Composer', 'CParser', 'SafeConstructor',
                        'BaseConstructor', 'Resolver', 'BaseResolver', 'SafeLoader', 'CSafeLoader',
                        'DupCheckYamlLoader', 'YAMLMark', 'TypedNode',
                        'extended_str', 'extended_int', 'extended_float'})


def _yaml_constructor_state():
    classes = tuple((module.__name__, name, constructor_key(cls, _FUNCTIONS),
                     _methods_key(cls, _FUNCTIONS, views), setting_key(getattr(cls, 'id', None)))
                    for module in _YAML_DEFINITIONS for name, cls in sorted(vars(module).items())
                    if isinstance(cls, type) and cls.__module__ == module.__name__)
    extra = tuple((module.__name__, name, constructor_key(getattr(module, name), _FUNCTIONS),
                   _methods_key(getattr(module, name), _FUNCTIONS, views))
                  for module, name in _YAML_EXTRAS)
    modules = (*_YAML_DEFINITIONS, yaml, yaml.reader, yaml.scanner, yaml.parser,
               yaml.composer, yaml.constructor, yaml.loader, yaml.resolver, yamlutils, views)
    if hasattr(yaml, 'cyaml'):
        modules += (yaml.cyaml,)
    aliases = tuple((module.__name__, tuple((name, vars(module)[name]) for name in sorted(_YAML_NAMES)
                                            if name in vars(module))) for module in modules)
    extended = tuple((constructor_key(cls, _FUNCTIONS), _methods_key(cls, _FUNCTIONS, views))
                     for cls in (yamlutils.YAMLMark, yamlutils.TypedNode,
                                 yamlutils.extended_str, yamlutils.extended_int, yamlutils.extended_float))
    bases = tuple((constructor_key(cls, _FUNCTIONS), _methods_key(cls, _FUNCTIONS, views))
                  for cls in yamlutils.SafeLoader.__mro__)
    return classes, extra, aliases, extended, bases


def _primitive_state():
    primitives = tuple((constructor_key(cls, _FUNCTIONS), _methods_key(cls, _FUNCTIONS, views))
        for cls in (metamodelcore.NCName, metamodelcore.Identifier, metamodelcore.URIorCURIE,
                    metamodelcore.URI, metamodelcore.Curie, metamodelcore.Bool,
                    metamodelcore.XSDTime, metamodelcore.XSDDate, metamodelcore.XSDDateTime))
    imported = tuple((module.__name__, name, constructor_key(cls, _FUNCTIONS),
                      _methods_key(cls, _FUNCTIONS, views))
                     for module in (annotations, extensions, units)
                     for name, cls in sorted(vars(module).items())
                     if isinstance(cls, type) and cls.__module__ == module.__name__)
    aliases = tuple((module.__name__, tuple((name, vars(module).get(name)) for name in (
        'URI', 'Bool', 'NCName', 'URIorCURIE', 'XSDDateTime', 'Annotation', 'AnnotationTag',
        'Extension', 'ExtensionTag', 'UnitOfMeasure', 'YAMLRoot', 'extended_str')))
        for module in (meta, annotations, extensions, units))
    functions = tuple(_FUNCTIONS.key(fn) for fn in (metamodelcore.is_strict, strictness.is_strict,
        strictness.BOOL.__bool__, metamodelcore.validate_uri, metamodelcore.validate_uri_reference,
        metamodelcore.validate_curie, metamodelcore.is_ncname, rdf_namespaces.is_ncname,
        rdf_namespaces.category))
    if (type(strictness.GLOBAL_STRICT) is not strictness.BOOL
            or set(vars(strictness.GLOBAL_STRICT)) != {'v'}
            or type(strictness.GLOBAL_STRICT.v) is not bool):
        raise TypeError('unsupported LinkML strictness state')
    settings = setting_key({
        'strict': strictness.GLOBAL_STRICT.v,
        'patterns': (metamodelcore.Bool.bool_true, metamodelcore.Bool.bool_false,
                     metamodelcore.Curie.term_name, uri_validator.uri_validator,
                     uri_validator.uri_relative_ref_validator, uri_validator.curie_validator),
        'ncname': (rdf_namespaces.NAME_START_CATEGORIES, rdf_namespaces.NAME_CATEGORIES,
                   rdf_namespaces.ALLOWED_NAME_CHARS),
    })
    return primitives, imported, aliases, functions, strictness.BOOL, settings


def _loader_handlers():
    """Accept only the inherited table or the complete supported initialization."""
    if yamlutils.DupCheckYamlLoader is not views.DupCheckYamlLoader:
        raise TypeError('duplicate-check loader alias differs')
    loader = views.DupCheckYamlLoader
    base = yamlutils.SafeLoader
    if (base is not getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
            or loader.__bases__ != (base,)):
        raise TypeError('unsupported duplicate-check loader base')
    handlers = {
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG: loader.map_constructor,
        yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG: loader.seq_constructor,
        'tag:yaml.org,2002:str': loader.construct_yaml_str,
        'tag:yaml.org,2002:int': loader.construct_yaml_int,
        'tag:yaml.org,2002:float': loader.construct_yaml_float,
    }
    inherited = base.yaml_constructors
    if type(inherited) is not dict or not set(handlers) <= inherited.keys():
        raise TypeError('unsupported inherited duplicate-check table')
    actual = loader.yaml_constructors
    if 'yaml_constructors' not in vars(loader):
        if actual is not inherited:
            raise TypeError('unsupported inherited duplicate-check table ownership')
    else:
        expected = tuple((tag, handlers.get(tag, function)) for tag, function in inherited.items())
        if type(actual) is not dict or tuple(actual.items()) != expected:
            raise TypeError('incomplete or changed duplicate-check initialization')
    return handlers


def _initialized_schema_state(state):
    """Exactly the five assignments in the already-bound loader initializer."""
    handlers = _loader_handlers()
    tables = []
    for name, rows in state[-2]:
        if name == 'yaml_constructors':
            if not set(handlers) <= {tag for tag, _key in rows}:
                raise TypeError('unsupported initial duplicate-check table')
            rows = tuple((tag, _FUNCTIONS.key(handlers[tag]) if tag in handlers else key)
                         for tag, key in rows)
        tables.append((name, rows))
    return (*state[:-2], tuple(tables), state[-1])


def _explicit_loader_parse():
    """Both bound producers explicitly pass Loader, so its default is unused."""
    function = yaml.parse
    if (function is not _PARSE or type(function) is not types.FunctionType
            or function.__module__ != yaml.__name__ or function.__globals__ is not vars(yaml)
            or function.__code__.co_filename != yaml.__file__ or function.__name__ != 'parse'
            or function.__closure__ is not None or function.__kwdefaults__ is not None
            or getattr(function, '__wrapped__', None) is not None
            or type(function.__defaults__) is not tuple or len(function.__defaults__) != 1
            or function.__defaults__[0] is not _DEFAULT_LOADER or yaml.Loader is not _DEFAULT_LOADER):
        raise TypeError('unsupported explicitly supplied YAML loader binding')
    # The producer functions and the actual supplied loader's methods/tables
    # are separately guarded. No mutable class gains generic default admission.
    return function, function.__code__, _DEFAULT_LOADER


def _constant_parser(function):
    constants = json.decoder._CONSTANTS
    if (type(constants) is not dict or type(function) is not types.BuiltinFunctionType
            or function.__self__ is not constants
            or function != dict.__getitem__.__get__(constants, dict)):
        raise TypeError('unfamiliar JSON constants receiver')
    return function, setting_key(constants)


def _json_state():
    encoder, decoder = json._default_encoder, json._default_decoder
    if type(encoder) is not json.JSONEncoder or type(decoder) is not json.JSONDecoder:
        raise TypeError('unfamiliar default JSON codec')
    if set(vars(decoder)) != {'object_hook', 'parse_float', 'parse_int', 'parse_constant',
            'strict', 'object_pairs_hook', 'parse_object', 'parse_array', 'parse_string', 'memo', 'scan_once'}:
        raise TypeError('unfamiliar JSON decoder fields')
    scanner = decoder.scan_once
    if (type(scanner) is not _json.make_scanner or json.scanner.make_scanner is not _json.make_scanner
            or json.scanner.c_make_scanner is not _json.make_scanner):
        raise TypeError('unfamiliar JSON scanner')
    fields = []
    for owner in (decoder, scanner):
        if (owner.object_hook is not None or owner.object_pairs_hook is not None
                or owner.strict is not True or owner.parse_float is not float or owner.parse_int is not int):
            raise TypeError('unsupported effective JSON scanner fields')
        fields.append(_constant_parser(owner.parse_constant))
    if type(decoder.memo) is not dict or decoder.memo:
        raise TypeError('unfamiliar JSON decoder memo')
    bindings = tuple(_FUNCTIONS.key(fn) for fn in (
        decoder.parse_object, decoder.parse_array, decoder.parse_string,
        json.encoder.encode_basestring, json.encoder.encode_basestring_ascii,
        json.decoder.scanstring, json.decoder.c_scanstring))
    constants = setting_key({
        'encoder': {name: getattr(json.encoder, name) for name in ('ESCAPE', 'ESCAPE_ASCII', 'ESCAPE_DCT', 'INFINITY')},
        'decoder': {name: getattr(json.decoder, name) for name in ('WHITESPACE', 'WHITESPACE_STR', 'BACKSLASH', 'STRINGCHUNK')},
        'scanner_number': json.scanner.NUMBER_RE,
    })
    return (encoder, decoder, scanner, setting_key(vars(encoder)), tuple(fields), bindings, constants,
            json.encoder.c_make_encoder, _json.make_scanner)


def _loader(loader):
    constructors = tuple((name, tuple((tag, _FUNCTIONS.key(fn)) for tag, fn in
        getattr(loader, name).items())) for name in ('yaml_constructors', 'yaml_multi_constructors'))
    settings = tuple((name, setting_key(getattr(loader, name))) for name in (
        'yaml_implicit_resolvers', 'yaml_path_resolvers', 'DEFAULT_SCALAR_TAG',
        'DEFAULT_SEQUENCE_TAG', 'DEFAULT_MAPPING_TAG', 'DEFAULT_TAGS',
        'ESCAPE_REPLACEMENTS', 'ESCAPE_CODES', 'bool_values', 'timestamp_regexp', 'NON_PRINTABLE')
        if hasattr(loader, name))
    return constructor_key(loader, _FUNCTIONS), _methods_key(loader, _FUNCTIONS, views), constructors, settings


def _selected_methods(cls, names):
    rows = []
    for name in names:
        member = getattr(cls, name)
        if isinstance(member, types.MethodType):
            member = member.__func__
        rows.append((name, _FUNCTIONS.key(member)))
    return cls, tuple(rows)


def _metadata():
    function = snapshots._metadata
    if type(function) is not functools._lru_cache_wrapper:
        raise TypeError('unfamiliar schema metadata wrapper')
    return function, setting_key(function.cache_parameters()), _FUNCTIONS.key(function.__wrapped__)


def _state():
    # Fixed bindings actually used by the two schema producers. Unfamiliar
    # replacements cannot become bound merely by being the first observation.
    functions = tuple(_FUNCTIONS.key(fn) for fn in (
        omissions._schema, omissions._schema_product, omissions._schema_with_root_bases,
        omissions._mapping, omissions._read, omissions._load_yaml, omissions._legacy_yaml,
        omissions._event_text_bytes, omissions._sha, omissions._json,
        omissions.nesting_exceeds, omissions._validate_json,
        duplicate_keys.nesting_exceeds, support_targets._validate_json,
        grounding.declared_bases_of,
        snapshots.capture_schema, snapshots._capture_schema, snapshots._metadata_document,
        snapshots.resolve_import_path, snapshots.map_import,
        views.captured_view, views.resolve_import_path,
        yaml.load, yaml.safe_load,
        json.dumps, json.loads, json.encoder._make_iterencode,
        json.decoder.JSONObject, json.decoder.JSONArray, json.decoder.py_scanstring,
        json.scanner.py_make_scanner,
        JSONDumper.dumps, yamlutils.as_json_object, yamlutils.merge_contexts,
        yamlutils.copy, formatutils.remove_empty_items,
        formatutils.is_list, formatutils.is_dict, formatutils.items, formatutils.is_empty,
        formatutils.as_dict, jsonobj.is_list, jsonobj.is_dict, jsonobj.items, jsonobj.as_dict,
        copy.copy, copy._reconstruct,
        contract.strict_json, contract.canonical, contract._pairs, contract._reject_constant,
        contract._lexical_budget, contract._json_values, contract.positive_int,
        contract._JSONValidationCache.contains, contract._JSONValidationCache.remember,
    ))
    # The installed singleton is stateless on this path. An injected instance
    # method or any opaque attribute prevents reuse instead of becoming a key.
    if type(json_dumper) is not JSONDumper or vars(json_dumper):
        raise TypeError('unfamiliar JSON dumper state')
    import linkml_runtime.dumpers as dumpers
    # Import syntax can resolve the package singleton; use the function globals
    # for the actual module-level bindings executed by dumps.
    namespace = JSONDumper.dumps.__globals__
    if dumpers.json_dumper is not json_dumper:
        raise TypeError('JSON dumper singleton changed')
    dumper_bindings = tuple(_FUNCTIONS.key(namespace[name]) for name in ('as_json_object', 'remove_empty_items'))
    json_classes = tuple((constructor_key(cls, _FUNCTIONS), _methods_key(cls, _FUNCTIONS, views))
                        for cls in (json.JSONEncoder, json.JSONDecoder))
    json_state = _json_state()
    yaml_root = _selected_methods(yamlutils.YAMLRoot, (
        '__post_init__', '_normalize_inlined', '_normalize_inlined_as_list', '_normalize_inlined_as_dict'))
    object_methods = _methods_key(jsonobj.JsonObj, _FUNCTIONS, views)
    copy_methods = tuple((name, cls, tuple((method, _FUNCTIONS.key(getattr(cls, method, None)))
                         for method in ('__copy__', '__reduce_ex__', '__reduce__', '__getstate__',
                                        '__setstate__', '__getattribute__', '__getitem__', '__setitem__')))
                         for name, cls in sorted(vars(meta).items())
                         if isinstance(cls, type) and cls.__module__ == meta.__name__)
    copy_dispatch = tuple((cls, _FUNCTIONS.key(fn)) for cls, fn in copy._copy_dispatch.items())
    # An unfamiliar reducer cannot be treated as immutable merely because it
    # is callable. These reducers are normally empty for the LinkML classes.
    reducers = tuple((cls, _FUNCTIONS.key(copy.dispatch_table[cls])) for _name, cls in sorted(vars(meta).items())
                     if isinstance(cls, type) and cls.__module__ == meta.__name__ and cls in copy.dispatch_table)
    namespaces = _selected_methods(Namespaces, ('__init__', '__setitem__', '__getitem__', '_cased_key', 'add_prefixmap'))
    settings = setting_key({
        'limits': tuple(getattr(omissions, name) for name in (
            'MAX_INPUT_BYTES', 'MAX_SCHEMA_BYTES', 'MAX_NODES', 'MAX_DEPTH',
            '_YAML_REPLAY_MAX_EVENTS', '_YAML_REPLAY_MAX_TEXT_BYTES')),
        'uri_to_local': snapshots.URI_TO_LOCAL,
        'schema_directory': str(snapshots.SCHEMA_DIRECTORY),
        'contract_limits': dict(contract.HARD_LIMITS),
        'jsonobj_hide': jsonobj.hide,
        'jsonobj_idempotent': jsonobj.JsonObj._idempotent,
    })
    _loader_handlers()
    return (functions, _explicit_loader_parse(), _schema_state(_FUNCTIONS), _metadata(),
            tuple(_loader(cls) for cls in (yaml.SafeLoader, yamlutils.SafeLoader,
                                          omissions._UniqueLoader, omissions._EventReplayLoader)),
            constructor_key(snapshots.SchemaSnapshot, _FUNCTIONS),
            constructor_key(snapshots.SchemaDefinition, _FUNCTIONS),
            constructor_key(Namespaces, _FUNCTIONS), namespaces,
            JSONDumper, json_dumper, _FUNCTIONS.key(JSONDumper.__getattribute__), dumper_bindings,
            json_classes, json_state, yaml_root, object_methods, copy_methods, copy_dispatch, reducers, settings,
            _yaml_constructor_state(), _primitive_state())


def _bind():
    global _STATE, _INITIALIZED_STATE
    _STATE = _state()
    _INITIALIZED_STATE = (*_STATE[:2], _initialized_schema_state(_STATE[2]), *_STATE[3:])


_FUNCTIONS.bind(_bind)


def runtime_token():
    """A constant-size marker only for the still-supported bound implementation."""
    try:
        if _FUNCTIONS.ready:
            actual = _state()
            if actual == _STATE or actual == _INITIALIZED_STATE:
                return _READY
    except Exception:
        pass
    return None


def supported_snapshot(snapshot):
    """The initial optimization excludes all ambient import/prefix-map state."""
    try:
        if (type(snapshot) is not snapshots.SchemaSnapshot or type(snapshot.sources) is not tuple
                or len(snapshot.sources) != 1):
            return False
        _name, _imports, _prefixes, maps = snapshots._metadata(snapshot.sources[0][2])
        return not _imports and not maps
    except Exception:
        return False


class _CatalogLookup:
    """Private native context association; carries no caller-provided catalog."""
    __slots__ = ('_context', '_selection')

    def __init__(self, context, selection):
        self._context, self._selection = context, selection

    def for_snapshot(self, path, snapshot):
        from .native_shared_receipts import _ReceiptCatalogContext
        if type(self._context) is not _ReceiptCatalogContext:
            return None
        return self._context._typed_catalog(self._selection, path, snapshot)
