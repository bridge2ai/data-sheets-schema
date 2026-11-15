"""Optional native catalog reuse over a closed, unchanged pure dependency set.

Ordinary fixed-code imports bind the implementation once. Runtime lookup does
not read files or consult the environment; uncertainty takes the old producer.
"""
from __future__ import annotations

import copy
import _json
import functools
import json
import os
import posixpath
import sys
import types

try:
    import posix as _native_posix
except ImportError:
    _native_posix = None

import yaml
from linkml_runtime.dumpers import json_dumper
from linkml_runtime.dumpers.json_dumper import JSONDumper
from linkml_runtime.utils import context_utils, formatutils, yamlutils, metamodelcore, strictness, uri_validator
from linkml_runtime.linkml_model import meta, annotations, extensions, units
import rdflib.namespace as rdf_namespaces
from linkml_runtime.utils.namespaces import Namespaces
import jsonasobj2._jsonobj as jsonobj

from . import audit_omissions as omissions
from . import native_catalog_initialization as initialization
from . import native_schema_event_reuse as events
from . import native_shared_contract as contract
from . import duplicate_keys, grounding, schema_snapshot as snapshots, schema_view as views, support_targets
from .cache_dependencies import FunctionBindings, _methods_key, _schema_state, constructor_key, setting_key


_MODULES = frozenset({
    'data_sheets_schema.audit_omissions', 'data_sheets_schema.duplicate_keys',
    'data_sheets_schema.grounding', 'data_sheets_schema.schema_snapshot',
    'data_sheets_schema.support_targets',
    'data_sheets_schema.native_shared_contract',
    'data_sheets_schema.native_schema_event_reuse',
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
_FAST_PLANS = {}
_LIMIT_READERS = (sys.getrecursionlimit, getattr(sys, 'get_int_max_str_digits', None))
_RUNTIME_LIMITS = tuple(reader() if reader is not None else None for reader in _LIMIT_READERS)
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
                        'extended_str', 'extended_int', 'extended_float', 'Mark'})


def _yaml_constructor_state():
    classes = tuple((module.__name__, name, constructor_key(cls, _FUNCTIONS),
                     _methods_key(cls, _FUNCTIONS, views), setting_key(getattr(cls, 'id', None)))
                    for module in _YAML_DEFINITIONS for name, cls in sorted(
                         (dict(vars(module), Mark=initialization.ORIGINAL_MARK)
                          if module is yaml.error else vars(module)).items())
                    if isinstance(cls, type) and cls.__module__ == module.__name__)
    extra = tuple((module.__name__, name, constructor_key(getattr(module, name), _FUNCTIONS),
                   _methods_key(getattr(module, name), _FUNCTIONS, views))
                  for module, name in _YAML_EXTRAS)
    modules = (*_YAML_DEFINITIONS, yaml, yaml.reader, yaml.scanner, yaml.parser,
               yaml.composer, yaml.constructor, yaml.loader, yaml.resolver, yamlutils, views)
    if hasattr(yaml, 'cyaml'):
        modules += (yaml.cyaml,)
    aliases = tuple((module.__name__, tuple((name, initialization.ORIGINAL_MARK
                                            if module is yaml.error and name == 'Mark' else vars(module)[name])
                                            for name in sorted(_YAML_NAMES)
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


def _native_path_state():
    """Pure frozen/ordinary stdlib path binding state, without widening bindings.

    Generic FunctionBindings intentionally rejects frozen stdlib origins.
    Retain these two effective callables' exact identities/code/defaults instead;
    the original donor's _STATE is never rebound after another package import.
    Unknown callable shapes disable reuse.
    """
    module = os.path
    if (snapshots.os is not os or snapshots.os.path is not module
            or module is not posixpath or posixpath.os is not os
            or snapshots.Namespaces is not Namespaces):
        raise TypeError('native schema path or namespace alias differs')
    functions = []
    fspath = os.fspath
    if (_native_posix is None or type(fspath) is not types.BuiltinFunctionType
            or fspath is not getattr(_native_posix, 'fspath', None)
            or fspath.__self__ is not _native_posix or fspath.__name__ != 'fspath'):
        raise TypeError('unrecognized native filesystem-path conversion')
    for name in ('normpath', 'abspath'):
        function = getattr(module, name)
        # CPython 3.13's posixpath uses this immutable C builtin, not a
        # Python normpath function. Its concrete object/receiver are guarded.
        if (name == 'normpath' and type(function) is types.BuiltinFunctionType
                and function is getattr(_native_posix, '_path_normpath', None)
                and function.__self__ is _native_posix
                and function.__name__ == '_path_normpath'):
            functions.append((function, None, None, None))
            continue
        if (type(function) is not types.FunctionType
                or function.__module__ != module.__name__
                or function.__name__ != name
                or function.__globals__ is not vars(module)
                or function.__closure__ is not None or function.__dict__
                or function.__code__.co_filename not in (
                    module.__file__, '<frozen ' + module.__name__ + '>')):
            raise TypeError('unrecognized native schema path callable')
        functions.append((function, function.__code__,
                          setting_key(function.__defaults__),
                          setting_key(function.__kwdefaults__)))
    return os, module, posixpath.os, _native_posix, fspath, snapshots.Namespaces, tuple(functions)


def _bound_schema_state():
    """Same tuple as cache_dependencies._schema_state over this bound view.

    The shared helper imports today's sys.modules binding. A retained donor must
    instead check the original attested producer after another loader replaces
    that binding. No ambient import or mutable module substitution is needed.
    """
    parsers = tuple(_FUNCTIONS.key(fn) for fn in
                    (views.version_document, views.version_view, views.yaml.load))
    models = tuple((name, constructor_key(cls, _FUNCTIONS))
                   for name, cls in sorted(vars(meta).items())
                   if isinstance(cls, type) and cls.__module__ == meta.__name__)
    constructors = tuple(constructor_key(cls, _FUNCTIONS) for cls in
                         (views.SchemaDefinition, views._ReleasableView, views.DupCheckYamlLoader))
    tables = tuple((name, tuple((prefix, _FUNCTIONS.key(fn)) for prefix, fn in
                               getattr(views.DupCheckYamlLoader, name).items()))
                   for name in ('yaml_constructors', 'yaml_multi_constructors'))
    resolvers = tuple((name, setting_key(getattr(views.DupCheckYamlLoader, name)))
                      for name in ('yaml_implicit_resolvers', 'yaml_path_resolvers'))
    return (parsers, models, constructors,
            _methods_key(views._ReleasableView, _FUNCTIONS, views),
            _methods_key(views.DupCheckYamlLoader, _FUNCTIONS, views), tables, resolvers)


def _model_attributes():
    """Include noncallable metamodel attributes in the full fallback too."""
    def snapshot(value, seen=frozenset()):
        kind = type(value)
        if id(value) in seen:
            return kind, id(value)
        seen = seen | {id(value)}
        if kind is dict:
            return kind, tuple((snapshot(k, seen), snapshot(v, seen)) for k, v in value.items())
        if kind in (list, tuple):
            return kind, tuple(snapshot(v, seen) for v in value)
        if kind in (set, frozenset):
            return kind, frozenset(snapshot(v, seen) for v in value)
        if value is None or kind in (str, bytes, int, float, bool):
            return kind, value
        return kind, id(value)
    return tuple((name, tuple((key, snapshot(value)) for key, value in sorted(vars(cls).items())
                             if key not in ('__slotnames__', 'MissingRequiredField')))
                 for name, cls in sorted(vars(meta).items())
                 if isinstance(cls, type) and cls.__module__ == meta.__name__)


def _state():
    # Fixed bindings actually used by the two schema producers. Unfamiliar
    # replacements cannot become bound merely by being the first observation.
    if (omissions.yaml is not yaml or snapshots.yaml is not yaml or views.yaml is not yaml
            or omissions.json is not json or snapshots.json is not json or contract.json is not json
            or snapshots.SchemaDefinition is not meta.SchemaDefinition):
        raise TypeError('schema producer module alias differs')
    # copyreg lazily records an empty slot roster for these nonslotted models.
    # Any nonempty or unfamiliar replacement changes reduction semantics.
    for cls in vars(meta).values():
        if isinstance(cls, type) and cls.__module__ == meta.__name__:
            slots = vars(cls).get('__slotnames__', [])
            if type(slots) is not list or slots:
                raise TypeError('unsupported metamodel reduction slots')
    functions = tuple(_FUNCTIONS.key(fn) for fn in (
        omissions._schema, omissions._schema_product, omissions._schema_with_root_bases,
        omissions._mapping, omissions._read,
        omissions._schema_yaml,
        events.mapping, events.load_native, events.retain_native, events._token,
        events._fallback, events._fresh_events, events._fresh_mark, events._mark,
        events._freeze, events._thaw, events._bindings, events._setting,
        omissions._sha, omissions._json,
        omissions.nesting_exceeds, omissions._validate_json,
        duplicate_keys.nesting_exceeds, support_targets._validate_json,
        grounding.declared_bases_of,
        snapshots.capture_schema, snapshots._capture_schema, snapshots._capture_native_schema,
        snapshots._cold_metadata, snapshots._launch_cached_metadata,
        snapshots._lossless_json_tree, snapshots._ordered_json_equal,
        snapshots._encode_metadata_fields, snapshots._decode_metadata_fields,
        snapshots._MetadataDerivationCache._key, snapshots._MetadataDerivationCache.get,
        snapshots._MetadataDerivationCache.put, snapshots._MetadataDerivationCache.snapshot,
        snapshots._MetadataDerivationCache.clear,
        snapshots._metadata_document,
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
        copy.copy, copy.deepcopy, copy._keep_alive, copy._reconstruct,
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
            'MAX_SCHEMA_EVENTS', 'MAX_SCHEMA_EVENT_CHARS')),
        'uri_to_local': snapshots.URI_TO_LOCAL,
        'schema_directory': str(snapshots.SCHEMA_DIRECTORY),
        'contract_limits': dict(contract.HARD_LIMITS),
        'jsonobj_hide': jsonobj.hide,
        'jsonobj_idempotent': jsonobj.JsonObj._idempotent,
        'native_events': (events.MAX_ENTRIES, events.MAX_EVENTS_PER_ENTRY,
                          events.MAX_TOTAL_EVENTS, events.MAX_EVENT_CHARS,
                          events.MAX_PAYLOAD_BYTES, events.MAX_INPUT_BYTES),
        'metadata_cache': (snapshots._METADATA_FIELDS,
                           snapshots._METADATA_CACHE_ENTRIES,
                           snapshots._METADATA_CACHE_BYTES),
    })
    _loader_handlers()
    return (functions, _explicit_loader_parse(), _bound_schema_state(), _metadata(),
            tuple(_loader(cls) for cls in (yaml.SafeLoader, yamlutils.SafeLoader,
                                          omissions._UniqueLoader,
                                          omissions._SchemaEventLoader)),
            constructor_key(snapshots.SchemaSnapshot, _FUNCTIONS),
            constructor_key(snapshots.SchemaDefinition, _FUNCTIONS),
            constructor_key(Namespaces, _FUNCTIONS), namespaces,
            JSONDumper, json_dumper, _FUNCTIONS.key(JSONDumper.__getattribute__), dumper_bindings,
            json_classes, json_state, yaml_root, object_methods, copy_methods, copy_dispatch, reducers, settings,
            _yaml_constructor_state(), _primitive_state(),
            # Effective aliases and dispatch used by native captured-byte schemas.
            (snapshots.Path, views.Path, snapshots.deepcopy, copy.deepcopy),
            tuple((cls, _FUNCTIONS.key(fn)) for cls, fn in copy._deepcopy_dispatch.items()),
            _native_path_state(), _model_attributes())


def _bind():
    global _STATE, _INITIALIZED_STATE
    initialization.phase()
    _STATE = _state()
    _INITIALIZED_STATE = (*_STATE[:2], _initialized_schema_state(_STATE[2]), *_STATE[3:])


_FUNCTIONS.bind(_bind)


def _compile_guards(actual):
    """Compile conservative identity checks only after full state acceptance.

    The state readers' attribute vocabulary includes literal getattr names and
    nested comprehension code. Module bindings and class rosters are checked
    separately from mutable containers and function signatures. No producer
    result or validation verdict is retained here.
    """
    readers = (_state, _explicit_loader_parse, _bound_schema_state, _metadata,
        _loader, _yaml_constructor_state, _primitive_state, _loader_handlers,
        _json_state, _constant_parser, _native_path_state, _selected_methods, _model_attributes)
    names = set(_YAML_NAMES)
    def vocabulary(code):
        names.update(code.co_names)
        for value in code.co_consts:
            if type(value) is types.CodeType:
                vocabulary(value)
            elif type(value) is str:
                names.add(value)
            elif type(value) is tuple:
                names.update(item for item in value if type(item) is str)
    for reader in readers:
        vocabulary(reader.__code__)
    attributes, mappings, sequences, functions, cells, rosters = [], [], [], [], [], []
    namespaces = []
    model_dicts = []
    seen = set()
    missing = object()
    def attribute(owner, name):
        value = getattr(owner, name, missing)
        attributes.append((owner, name, value))
        visit(value)
    def visit(value):
        if id(value) in seen:
            return
        seen.add(id(value))
        kind = type(value)
        if kind is types.ModuleType:
            if value is sys:
                return
            for name in names:
                if name in vars(value) or name in _YAML_NAMES and value.__name__.startswith('yaml'):
                    attribute(value, name)
            if value in (meta, annotations, extensions, units, *_YAML_DEFINITIONS):
                roster = {name: cls for name, cls in vars(value).items()
                          if isinstance(cls, type) and cls.__module__ == value.__name__}
                rosters.append((value, roster))
                for cls in roster.values():
                    visit(cls)
        elif isinstance(value, type):
            if value.__module__ == 'builtins':
                return
            attributes.append((value, '__bases__', value.__bases__))
            snapshot = dict(vars(value))
            if value.__module__ == meta.__name__:
                snapshot.pop('__slotnames__', None)
                model_dicts.append((value, snapshot))
            else:
                mappings.append((vars(value), snapshot))
            for member in snapshot.values():
                visit(member)
            for base in value.__bases__:
                visit(base)
        elif kind is types.FunctionType:
            functions.append((value, value.__code__, value.__defaults__,
                              value.__kwdefaults__, value.__closure__))
            attributes.append((value, '__name__', value.__name__))
            attributes.append((value, '__module__', value.__module__))
            attributes.append((value, '__dict__', value.__dict__))
            visit(value.__dict__)
            visit(value.__defaults__)
            visit(value.__kwdefaults__)
            for cell in value.__closure__ or ():
                member = cell.cell_contents
                cells.append((cell, member))
                visit(member)
        elif kind is functools._lru_cache_wrapper:
            visit(vars(value))
            attribute(value, '__wrapped__')
        elif kind is dict:
            mappings.append((value, value.copy()))
            for key, member in value.items():
                visit(key)
                visit(member)
        elif kind in (list, tuple, set, frozenset):
            if kind in (list, set):
                sequences.append((value, value.copy()))
            for member in value:
                visit(member)
        elif kind in (staticmethod, classmethod):
            visit(value.__func__)
        elif kind is property:
            for member in (value.fget, value.fset, value.fdel):
                visit(member)
        elif isinstance(value, views._InstanceCached):
            for name in ('function', 'name', 'maxsize', 'typed'):
                attribute(value, name)
    for reader in readers:
        for name in reader.__code__.co_names:
            if name in reader.__globals__ and name not in ('_FUNCTIONS', 'sys'):
                namespaces.append((reader.__globals__, name, reader.__globals__[name]))
                visit(reader.__globals__[name])
    visit(actual)
    for function in _FUNCTIONS._functions:
        visit(function)
    # Instance state and C-scanner descriptors are not class dictionary state.
    for owner in (json_dumper, json._default_encoder, json._default_decoder,
                  strictness.GLOBAL_STRICT):
        attributes.append((owner, '__class__', type(owner)))
        attributes.append((owner, '__dict__', vars(owner)))
        mappings.append((vars(owner), dict(vars(owner))))
        for value in vars(owner).values():
            visit(value)
    for name in ('object_hook', 'object_pairs_hook', 'strict', 'parse_float',
                 'parse_int', 'parse_constant'):
        attribute(json._default_decoder.scan_once, name)
    visit(copy.dispatch_table)
    import linkml_runtime.dumpers as dumpers
    attribute(dumpers, 'json_dumper')
    for name in ('as_json_object', 'remove_empty_items'):
        namespace = JSONDumper.dumps.__globals__
        namespaces.append((namespace, name, namespace[name]))
    import dataclasses
    import _thread
    import builtins
    for name in ('_recursive_repr', '_thread'):
        attribute(dataclasses, name)
    attribute(_thread, 'get_ident')
    attribute(dataclasses, 'id')
    attribute(dataclasses, '__builtins__')
    attribute(builtins, 'id')
    return (tuple(attributes), tuple(mappings), tuple(sequences), tuple(functions),
            tuple(cells), tuple(rosters), missing, snapshots._metadata.cache_parameters(),
            tuple(namespaces), tuple(model_dicts))


def _guards_match(plan):
    attributes, mappings, sequences, functions, cells, rosters, missing, parameters, namespaces, model_dicts = plan
    for namespace, name, expected in namespaces:
        if namespace.get(name, missing) is not expected:
            return False
    for cls, expected in model_dicts:
        current = vars(cls)
        slots = current.get('__slotnames__', missing)
        if slots is not missing and (type(slots) is not list or slots):
            return False
        if (len(current) != len(expected) + (slots is not missing)
                or any(current.get(name, missing) is not value for name, value in expected.items())):
            return False
    for owner, name, expected in attributes:
        if getattr(owner, name, missing) is not expected:
            return False
    for current, expected in mappings:
        if (len(current) != len(expected) or any(key is not prior_key or value is not prior_value
                for (key, value), (prior_key, prior_value) in zip(current.items(), expected.items()))):
            return False
    for current, expected in sequences:
        if (type(current) is list and (len(current) != len(expected)
                or any(value is not prior for value, prior in zip(current, expected)))
                or type(current) is set and {id(value) for value in current} != {id(value) for value in expected}):
            return False
    for fn, code, defaults, kwdefaults, closure in functions:
        if (fn.__code__ is not code or fn.__defaults__ is not defaults
                or fn.__kwdefaults__ is not kwdefaults or fn.__closure__ is not closure):
            return False
    for cell, expected in cells:
        if cell.cell_contents is not expected:
            return False
    for module, expected in rosters:
        if {name: cls for name, cls in vars(module).items()
                if isinstance(cls, type) and cls.__module__ == module.__name__} != expected:
            return False
    return snapshots._metadata.cache_parameters() == parameters


def runtime_token():
    """A constant-size marker only for the still-supported bound implementation."""
    try:
        if _FUNCTIONS.ready:
            marker = initialization.marker()
            if (sys.getrecursionlimit is not _LIMIT_READERS[0]
                    or getattr(sys, 'get_int_max_str_digits', None) is not _LIMIT_READERS[1]):
                _state()
                return None
            limits = tuple(reader() if reader is not None else None for reader in _LIMIT_READERS)
            plans = _FAST_PLANS.get(marker, {})
            for plan in plans.values():
                try:
                    if _guards_match(plan) and limits == _RUNTIME_LIMITS:
                        if initialization.marker() is marker:
                            return marker
                except Exception:
                    pass
            actual = _state()
            if limits == _RUNTIME_LIMITS and (actual == _STATE or actual == _INITIALIZED_STATE):
                if initialization.marker() is marker:
                    state = 0 if actual == _STATE else 1
                    if state not in plans:
                        plan = _compile_guards(actual)
                        if _state() != actual or initialization.marker() is not marker:
                            return None
                        _FAST_PLANS.setdefault(marker, {})[state] = plan
                    if initialization.marker() is marker:
                        return marker
    except Exception:
        pass
    return None


def schema_metadata_state(*, metadata, metadata_document, schema_definition,
                          yaml_alias, json_alias):
    """Pure recognized state for YAML import-metadata reuse; no filesystem I/O."""
    try:
        if (metadata is not snapshots._metadata
                or metadata_document is not snapshots._metadata_document
                or schema_definition is not snapshots.SchemaDefinition
                or schema_definition is not meta.SchemaDefinition
                or yaml_alias is not yaml
                or json_alias is not json
                or snapshots.yaml is not yaml
                or snapshots.json is not json
                or snapshots.Path is not views.Path
                or snapshots.deepcopy is not copy.deepcopy
                or type(snapshots._METADATA_DERIVATIONS) is not snapshots._MetadataDerivationCache):
            return None
        marker = runtime_token()
        if marker is None:
            return None
        phase = initialization.phase()
        if initialization.marker() is not marker:
            return None
        return phase, marker
    except Exception:
        return None


def schema_derivation_state(*, capture, view, contract_alias, path_alias):
    """Pure recognized state for schema metadata; no filesystem or resolver reads.

    The local marker is deliberately not transferable between loaded modules.
    A retains the original donor's guard, and transports only the phase number
    with exact-byte/domain keys. Aliases are part of the effective producer.
    """
    try:
        if (capture is not snapshots._capture_native_schema
                or view is not views.captured_view
                or contract_alias is not contract
                or path_alias is not snapshots.Path
                or snapshots.Path is not views.Path
                or snapshots.deepcopy is not copy.deepcopy):
            return None
        return schema_metadata_state(
            metadata=snapshots._metadata,
            metadata_document=snapshots._metadata_document,
            schema_definition=snapshots.SchemaDefinition,
            yaml_alias=snapshots.yaml,
            json_alias=snapshots.json,
        )
    except Exception:
        return None


def supported_snapshot(snapshot):
    """The initial optimization excludes all ambient import/prefix-map state."""
    try:
        if (type(snapshot) is not snapshots.SchemaSnapshot or type(snapshot.sources) is not tuple
                or not snapshot.sources):
            return False
        if len(snapshot.sources) == 1:
            _name, _imports, _prefixes, maps = snapshots._metadata(snapshot.sources[0][2])
            return not _imports and not maps
        return all(not snapshots._metadata(raw)[3]
                   and all(imp == 'linkml:types' for imp in snapshots._metadata(raw)[1])
                   for _name, _path, raw in snapshot.sources)
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
