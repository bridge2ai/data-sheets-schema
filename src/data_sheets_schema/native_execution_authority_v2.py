"""Closed version-2 source authority for explicit native execution (U3-A).

The v2 controller/supervisor supply the preparers. Only the unchanged
keep-awake primitives are added here; importing them never launches a child.
Version-1 authority and its globals remain independent.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import ast
import builtins
import collections
import hashlib
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import types
from types import FunctionType, ModuleType, GenericAlias, GetSetDescriptorType, MemberDescriptorType
from weakref import WeakKeyDictionary

from data_sheets_schema import native_attribution_registration_v2 as draft
from data_sheets_schema import native_supervisor_authority_v2 as neutral
from data_sheets_schema.resources import git_env
from data_sheets_schema.cache_dependencies import FunctionBindings, setting_key

ROOT = neutral.ROOT
VERSION = 2
ADDITIONAL = {
    'run_direct_canary_awake': {
        'path': 'notes/claudecode_direct/run_direct_canary_awake.py',
        'sha256': 'd0ad068e83a1ddf40c4c2c401ea5a264403e02c569391cf5433c47d14c5b69a5',
    },
}
PACKAGE = 'src/data_sheets_schema'
SOURCE_SUFFIXES = frozenset(('.py', '.yaml', '.json'))
EXPOSED_CONTROLS = frozenset(('prepare_registration_v2', 'run_direct_canary_awake'))
_SOURCE_MODULES = WeakKeyDictionary()
_VERIFIED_PACKAGE_MODULES = {}
_SCHEMA_BINDINGS = WeakKeyDictionary()
_LAUNCH_DERIVATIONS = threading.local()
_SELECTION_MODULE = 'data_sheets_schema.native_shared_selection'
_SNAPSHOT_MODULE = 'data_sheets_schema.schema_snapshot'
_SNAPSHOT_RELATIVE = 'src/data_sheets_schema/schema_snapshot.py'
_LEGACY_CONSUMER_MODULES = frozenset('data_sheets_schema.' + name for name in (
    'native_execution', 'native_execution_registration', 'native_execution_authority',
    'native_supervisor', 'native_attempt_supervisor', 'native_supervisor_authority', 'native_attribution_registration',
    'native_attribution_controller'))
_TRUSTED_CONSUMER_BOUNDARIES = frozenset((
    'data_sheets_schema.native_execution_registration_v2',
    'data_sheets_schema.native_execution_authority_v2'))
CONSUMER_OWNED_MODULES = frozenset('data_sheets_schema.' + name for name in (
    'native_shared_attribution', 'native_shared_capture', 'native_shared_controller',
    'native_shared_authority_wire', 'native_shared_controls', 'native_shared_evidence',
    'native_shared_permission_protocol', 'native_shared_runtime_constants',
    'native_shared_current', 'native_shared_effects', 'native_shared_observations',
    'native_shared_phase', 'native_shared_policy', 'native_shared_receipts',
    'native_shared_stage', 'native_shared_streams', 'native_shared_execution',
    'native_shared_gates', 'native_shared_permissions', 'native_shared_publication',
    'native_shared_registration', 'native_shared_results', 'native_shared_schema_gates',
    'native_shared_gate_primitives', 'native_shared_runtime_values', 'native_runtime_profiles', 'native_helper_cache',
    'native_execution_engine', 'native_gate_engine', 'native_subscription_guard'))


def _import_time_nodes(tree):
    """Dependency function bodies are checked when their imports are reached.

    Existing shared utilities contain deferred v1 routes. Merely defining those
    functions does not import v1. The consumer finder refuses their use if called.
    Consumer-owned source is linted in full instead, including deferred bodies.
    """
    yield tree
    if not isinstance(tree, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        for child in ast.iter_child_nodes(tree):
            yield from _import_time_nodes(child)


def _import_facts(source, filename, owned):
    """Immutable syntax facts only; graph resolution and lint decisions stay live."""
    tree = ast.parse(source, filename=filename)
    nodes = list(ast.walk(tree) if owned else _import_time_nodes(tree))
    aliases = {'__builtins__': 'builtins'}
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split('.')[0]] = (
                    alias.name if alias.asname else alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            for alias in node.names:
                aliases[alias.asname or alias.name] = (node.module or '') + '.' + alias.name

    def qualified(node):
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return qualified(node.value) + '.' + node.attr
        return ''

    facts = []
    for node in nodes:
        if isinstance(node, ast.Name):
            facts.append(('name', node.id, qualified(node)))
        elif isinstance(node, ast.Attribute):
            facts.append(('attribute', node.attr, qualified(node),
                          qualified(node.value).split('.')[0], isinstance(node.ctx, ast.Store)))
        elif isinstance(node, ast.Call):
            # Native AST constants are immutable. Only strings can match the
            # closed attribute-name sets; other literal values are irrelevant.
            attribute = (node.args[1].value if len(node.args) >= 2
                         and isinstance(node.args[1], ast.Constant) else None)
            facts.append(('call', qualified(node.func).split('.')[-1], len(node.args),
                          attribute if type(attribute) is str else None,
                          qualified(node.args[0]).split('.')[0] if node.args else ''))
        elif isinstance(node, ast.Import):
            facts.append(('import', tuple(alias.name for alias in node.names)))
        elif isinstance(node, ast.ImportFrom):
            facts.append(('from', node.level, node.module or '', tuple(alias.name for alias in node.names)))
    return tuple(facts)


_IMPORT_FACT_FUNCTIONS = FunctionBindings(
    additional_modules=frozenset({'ast', __name__}), callable_defaults=True)
_IMPORT_FACT_TYPE_ALIASES = (GenericAlias,) + ((types.UnionType,) if hasattr(types, 'UnionType') else ())


def _import_fact_setting(value):
    """Freeze the small stdlib AST producer's effective bindings, not its output."""
    if isinstance(value, type):
        return type, value
    if type(value) in _IMPORT_FACT_TYPE_ALIASES:
        return type(value), getattr(value, '__origin__', None), tuple(value.__args__)
    if type(value) in (GetSetDescriptorType, MemberDescriptorType):
        return type(value), value
    if type(value) in (tuple, list):
        return type(value), tuple(_import_fact_setting(item) for item in value)
    if type(value) is dict:
        return dict, tuple((key, _import_fact_setting(item)) for key, item in value.items())
    if isinstance(value, (staticmethod, classmethod)):
        return type(value), _IMPORT_FACT_FUNCTIONS.key(value.__func__)
    if isinstance(value, property):
        return property, tuple(_IMPORT_FACT_FUNCTIONS.key(fn) for fn in
                               (value.fget, value.fset, value.fdel))
    if callable(value):
        return _IMPORT_FACT_FUNCTIONS.key(value)
    return setting_key(value)


def _import_fact_state():
    if type(ast) is not ModuleType or type(collections) is not ModuleType:
        raise TypeError('unfamiliar parser dependency module')
    functions = (ast.parse, ast.walk, ast.iter_child_nodes, ast.iter_fields,
                 _import_time_nodes, _import_facts)
    keys = tuple(_IMPORT_FACT_FUNCTIONS.key(fn) for fn in functions)
    # ast.parse uses effective globals/builtins, and ast.walk imports deque at
    # call time. Function identity alone would miss these mutable bindings.
    names = ('compile', '__import__', 'isinstance', 'getattr', 'list', 'tuple', 'len', 'str', 'type')
    globals_ = tuple(tuple(_import_fact_setting(fn.__globals__.get(
        name, fn.__builtins__.get(name))) for name in names) for fn in functions)
    # CPython 3.13 keeps the private _ast_Ellipsis alias (ast.py:633). It is
    # not an effective parser/classifier name; public AST aliases remain bound.
    ast_classes = tuple((name, cls) for name, cls in vars(ast).items()
                        if not name.startswith('_') and isinstance(cls, type)
                        and issubclass(cls, ast.AST))
    if any(cls.__name__ != name or cls.__module__ not in {'ast', '_ast'}
           for name, cls in ast_classes):
        raise TypeError('unfamiliar AST class binding')
    classes = tuple((name, cls, cls.__bases__, tuple(
        (key, _import_fact_setting(value)) for key, value in vars(cls).items()))
        for name, cls in ast_classes)
    flags = tuple((name, _import_fact_setting(getattr(ast, name, None))) for name in
                  ('PyCF_ONLY_AST', 'PyCF_TYPE_COMMENTS', 'PyCF_OPTIMIZED_AST'))
    deque_state = (collections.deque, collections.deque.__bases__, tuple(
        (key, _import_fact_setting(value)) for key, value in vars(collections.deque).items()))
    return (keys, globals_, classes, flags, ast.AST, collections.deque,
            sys.modules.get('collections') is collections, deque_state,
            _IMPORT_FACT_FUNCTIONS.key(collections.deque.popleft),
            _IMPORT_FACT_FUNCTIONS.key(collections.deque.extend),
            _IMPORT_FACT_FUNCTIONS.key(builtins.compile))


_IMPORT_FACT_STATE = None
_IMPORT_FACT_BINDING_ERROR = None


def _bind_import_facts():
    global _IMPORT_FACT_STATE, _IMPORT_FACT_BINDING_ERROR
    try:
        _IMPORT_FACT_STATE = _import_fact_state()
    except Exception as exc:
        # FunctionBindings deliberately keeps unfamiliar producers cold. Keep
        # its diagnostic available without treating cold operation as reuse.
        _IMPORT_FACT_BINDING_ERROR = type(exc).__name__ + ': ' + str(exc)
        raise


_IMPORT_FACT_FUNCTIONS.bind(_bind_import_facts)
# Bound retention, not an exact RSS claim: sources + text + row/entry counts.
_IMPORT_FACTS = collections.OrderedDict()
_IMPORT_FACT_LIMITS = (256, 8_000_000, 131_072, 8_000_000)
_IMPORT_FACT_TOTALS = (0, 0, 0)
_IMPORT_FACT_LOCK = threading.RLock()


def _current_import_facts():
    """Unrecognized producer state uses the original cold implementation."""
    global _IMPORT_FACT_TOTALS
    try:
        supported = (_IMPORT_FACT_FUNCTIONS.ready
                     and _import_fact_state() == _IMPORT_FACT_STATE)
    except Exception:
        supported = False
    if not supported:
        with _IMPORT_FACT_LOCK:
            _IMPORT_FACTS.clear()
            _IMPORT_FACT_TOTALS = (0, 0, 0)
    return supported


def _cached_import_facts(source, filename, owned):
    global _IMPORT_FACT_TOTALS
    # Avoid guard overhead on small sources after the measured tiny regression.
    # This byte-size heuristic keeps the original AST path, not a universal optimum.
    if len(source) < 4096:
        return None
    if not _current_import_facts():
        return None
    key = (source, filename, owned)
    with _IMPORT_FACT_LOCK:
        if key in _IMPORT_FACTS:
            facts, _ = _IMPORT_FACTS[key]
            _IMPORT_FACTS.move_to_end(key)
            return facts
    facts = _import_facts(source, filename, owned)
    # Strings/tuples only, with integers/bools used solely as syntax fields.
    def text_size(value):
        if type(value) is str:
            return len(value.encode('utf-8', 'surrogatepass'))
        if type(value) is tuple:
            return sum(text_size(item) for item in value)
        if value is None or type(value) in (int, bool):
            return 0
        raise TypeError('import facts contain a mutable or unsupported value')
    sizes = (len(source) + len(filename.encode('utf-8', 'surrogatepass')), len(facts), text_size(facts))
    if not _current_import_facts():
        return None
    if any(size > bound for size, bound in zip(sizes, _IMPORT_FACT_LIMITS[1:])):
        return facts
    with _IMPORT_FACT_LOCK:
        if key in _IMPORT_FACTS:
            return _IMPORT_FACTS[key][0]
        while _IMPORT_FACTS and (len(_IMPORT_FACTS) >= _IMPORT_FACT_LIMITS[0]
                or any(total + size > bound for total, size, bound in
                       zip(_IMPORT_FACT_TOTALS, sizes, _IMPORT_FACT_LIMITS[1:]))):
            _, (_, old) = _IMPORT_FACTS.popitem(last=False)
            _IMPORT_FACT_TOTALS = tuple(total - size for total, size in zip(_IMPORT_FACT_TOTALS, old))
        _IMPORT_FACTS[key] = facts, sizes
        _IMPORT_FACT_TOTALS = tuple(total + size for total, size in zip(_IMPORT_FACT_TOTALS, sizes))
    return facts


def _fact_targets(facts, *, module, package, owned, package_sources,
                  dynamic_names, dynamic_attributes, introspection):
    """Apply current lint policy and resolve imports; no decision is cached."""
    machinery = {'importlib', 'builtins', 'runpy', 'pkgutil', 'pydoc', 'zipimport'}
    targets = []
    for fact in facts:
        kind = fact[0]
        dynamic = False
        if kind == 'name':
            _, name, qualified = fact
            dynamic = name in dynamic_names or qualified.split('.')[-1] in dynamic_names
            if owned and qualified.split('.')[-1] in introspection:
                raise ValueError('consumer lint forbids introspection or signature assignment: ' + module)
        elif kind == 'attribute':
            _, attribute, qualified, receiver, stored = fact
            dynamic = attribute in dynamic_attributes or attribute == '__dict__' and receiver in machinery
            if owned:
                if attribute in introspection or attribute == '__signature__' and stored:
                    raise ValueError('consumer lint forbids introspection or signature assignment: ' + module)
                if any(qualified == legacy or qualified.startswith(legacy + '.')
                       for legacy in _LEGACY_CONSUMER_MODULES):
                    raise ValueError('consumer imports forbidden v1 execution authority: ' + module)
        elif kind == 'call':
            _, operation, count, attribute, receiver = fact
            if operation in {'getattr', 'hasattr'} and count >= 2:
                dynamic = attribute in dynamic_names | dynamic_attributes | introspection or receiver in machinery
            elif operation == 'vars' and count:
                dynamic = receiver in machinery
        if owned and dynamic:
            raise ValueError('consumer import graph contains dynamic loading or evaluation: ' + module)
        if kind == 'import':
            targets.extend(fact[1])
        elif kind == 'from':
            _, level, imported, names = fact
            if owned and '*' in names:
                raise ValueError('consumer import graph contains an ambiguous star import: ' + module)
            if owned and any(name in dynamic_names | dynamic_attributes for name in names):
                raise ValueError('consumer import graph contains dynamic loading or evaluation: ' + module)
            if level:
                try:
                    imported = importlib.util.resolve_name('.' * level + imported, package)
                except (ImportError, ValueError) as exc:
                    raise ValueError('consumer import graph has invalid relative import: ' + module) from exc
            imported = _canonical_import(imported)
            if imported == 'data_sheets_schema':
                targets.extend(imported + '.' + name for name in names)
            else:
                targets.append(imported)
                for name in names:
                    child = imported + '.' + name
                    stem = 'src/' + child.replace('.', '/')
                    if stem + '.py' in package_sources or stem + '/__init__.py' in package_sources:
                        targets.append(child)
    return targets


def _package_name(path):
    """Classify physical package sources independently of their import spelling."""
    if not path:
        return None
    resolved = Path(path).resolve()
    root = (ROOT / PACKAGE).resolve()
    if not resolved.is_relative_to(root):
        return None
    if resolved.suffix != '.py':
        raise ValueError('consumer package import is not Python source')
    parts = resolved.relative_to(root).with_suffix('').parts
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(('data_sheets_schema', *parts))


def _resolved_import(name):
    """Find an import origin without importing or executing parent packages."""
    search = None
    spec = None
    parts = name.split('.')
    for index in range(len(parts)):
        # Resolve each leaf against the captured parent search path. A dotted
        # namespace spec would consult sys.modules for unexecuted parents.
        spec = importlib.machinery.PathFinder.find_spec(parts[index], search)
        if spec is None:
            return None
        search = (list(spec.submodule_search_locations)
                  if spec.submodule_search_locations is not None else None)
        if index < len(parts) - 1 and search is None:
            return None
    return spec


def _canonical_import(name):
    if name == 'data_sheets_schema' or name.startswith('data_sheets_schema.'):
        return name
    spec = _resolved_import(name)
    canonical = _spec_package_name(spec)
    if canonical:
        return canonical
    if name.split('.')[0] in {'src', 'tests', 'scripts', 'notes'}:
        raise ValueError('consumer import crosses an unverified checkout namespace: ' + name)
    return name


def _spec_package_name(spec):
    if spec is None:
        return None
    if spec.origin:
        return _package_name(spec.origin)
    locations = [Path(item).resolve() for item in (spec.submodule_search_locations or ())]
    root = (ROOT / PACKAGE).resolve()
    if root in locations:
        if any(item != root for item in locations):
            raise ValueError('consumer package namespace has mixed physical origins')
        return 'data_sheets_schema'
    return None


def refuse_legacy_consumer_imports(raw, *, name, package_sources):
    """Check the fixed consumer's explicit, pinned package import graph.

    This is lint, enforced by review and digest pins, not a Python sandbox.
    Dynamic constructs and star imports are linted only in the closed C/D-owned
    list. Reached v1 imports refuse throughout the graph. U3-A boundary imports
    refuse rather than exposing their normally imported bootstrap attributes.
    Every package dependency and implicit parent initializer below the trusted
    top-level package is read from its declared pin. Nested namespace parents
    are not supported here: an absent or ambiguous initializer refuses.
    """
    if (type(raw) is not bytes or not raw or type(name) is not str
            or not name.startswith('data_sheets_schema.') or type(package_sources) is not dict):
        raise ValueError('invalid fixed consumer import graph')
    dynamic_names = {'__import__', 'exec', 'eval', 'compile', 'FunctionType', 'CodeType'}
    dynamic_attributes = {'import_module', 'exec_module', 'load_module',
        'spec_from_file_location', 'spec_from_loader', 'module_from_spec',
        'SourceFileLoader', 'SourcelessFileLoader', 'ExtensionFileLoader', 'run_path', 'run_module',
        '__import__', 'resolve_name'}
    introspection = {'modules', 'meta_path', 'path_hooks', 'path_importer_cache',
        '_getframe', 'currentframe', 'stack', 'tb_frame', 'f_back', 'f_locals',
        'f_globals', 'gi_frame', 'cr_frame'}

    def source_path(module):
        stem = 'src/' + module.replace('.', '/')
        candidates = [path for path in (stem + '.py', stem + '/__init__.py')
                      if path in package_sources]
        if len(candidates) != 1:
            raise ValueError('consumer package import has missing or ambiguous source: ' + module)
        return candidates[0]

    visited, pending = {}, [(name, raw)]
    while pending:
        module, source = pending.pop()
        if module in _LEGACY_CONSUMER_MODULES:
            raise ValueError('consumer imports forbidden v1 execution authority: ' + module)
        if module in _TRUSTED_CONSUMER_BOUNDARIES:
            raise ValueError('consumer cannot import verifier bootstrap boundary: ' + module)
        if module in visited:
            continue
        if len(visited) >= 256:
            raise ValueError('consumer package import graph exceeds its fixed bound')
        # Importing pkg.child executes pkg.__init__ even if the child's source
        # never names pkg. Close that implicit import edge before any loading.
        parts = module.split('.')
        for length in range(2, len(parts)):
            parent = '.'.join(parts[:length])
            stem = 'src/' + parent.replace('.', '/')
            if stem + '/__init__.py' not in package_sources:
                raise ValueError('consumer parent package initializer is not pinned: ' + parent)
            if stem + '.py' in package_sources:
                raise ValueError('consumer parent package initializer is ambiguous: ' + parent)
            if parent not in visited:
                pending.append((parent, None))
        relative = source_path(module)
        digest = package_sources[relative]
        if source is None:
            source = _verified_source_bytes(ROOT / relative, digest)
        if hashlib.sha256(source).hexdigest() != digest:
            raise ValueError('consumer import graph source differs from its pin: ' + module)
        visited[module] = digest
        owned = module in CONSUMER_OWNED_MODULES
        try:
            facts = _cached_import_facts(source, str(ROOT / relative), owned)
        except (SyntaxError, ValueError) as exc:
            raise ValueError('consumer source has no inspectable import graph: ' + module) from exc
        package = module if relative.endswith('/__init__.py') else module.rpartition('.')[0]
        if facts is not None:
            targets = _fact_targets(facts, module=module, package=package, owned=owned,
                package_sources=package_sources, dynamic_names=dynamic_names,
                dynamic_attributes=dynamic_attributes, introspection=introspection)
        else:
            # Preserve the original AST path for unfamiliar effective producer
            # state, including replacements installed before the first lookup.
            try:
                tree = ast.parse(source, filename=str(ROOT / relative))
            except (SyntaxError, ValueError) as exc:
                raise ValueError('consumer source has no inspectable import graph: ' + module) from exc
            targets = []
            aliases = {'__builtins__': 'builtins'}
            nodes = list(ast.walk(tree) if owned else _import_time_nodes(tree))
            for node in nodes:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        aliases[alias.asname or alias.name.split('.')[0]] = (
                            alias.name if alias.asname else alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    for alias in node.names:
                        aliases[alias.asname or alias.name] = (node.module or '') + '.' + alias.name

            def qualified(node):
                if isinstance(node, ast.Name):
                    return aliases.get(node.id, node.id)
                if isinstance(node, ast.Attribute):
                    return qualified(node.value) + '.' + node.attr
                return ''

            def import_machinery(node):
                return qualified(node).split('.')[0] in {'importlib', 'builtins', 'runpy',
                    'pkgutil', 'pydoc', 'zipimport'}

            for node in nodes:
                dynamic = (isinstance(node, ast.Name) and
                           (node.id in dynamic_names or qualified(node).split('.')[-1] in dynamic_names)
                           or isinstance(node, ast.Attribute) and
                           (node.attr in dynamic_attributes or
                            node.attr == '__dict__' and import_machinery(node.value)))
                if isinstance(node, ast.Call):
                    operation = qualified(node.func).split('.')[-1]
                    if operation in {'getattr', 'hasattr'} and len(node.args) >= 2:
                        attribute = node.args[1]
                        dynamic |= (isinstance(attribute, ast.Constant) and
                                    attribute.value in dynamic_names | dynamic_attributes | introspection)
                        dynamic |= import_machinery(node.args[0])
                    elif operation == 'vars' and node.args:
                        dynamic |= import_machinery(node.args[0])
                if owned and isinstance(node, ast.Attribute):
                    if (node.attr in introspection
                            or node.attr == '__signature__' and isinstance(node.ctx, ast.Store)):
                        raise ValueError('consumer lint forbids introspection or signature assignment: ' + module)
                    if any(qualified(node) == legacy or qualified(node).startswith(legacy + '.')
                           for legacy in _LEGACY_CONSUMER_MODULES):
                        raise ValueError('consumer imports forbidden v1 execution authority: ' + module)
                if owned and isinstance(node, ast.Name) and qualified(node).split('.')[-1] in introspection:
                    raise ValueError('consumer lint forbids introspection or signature assignment: ' + module)
                if owned and dynamic:
                    raise ValueError('consumer import graph contains dynamic loading or evaluation: ' + module)
                if isinstance(node, ast.Import):
                    targets.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if owned and any(alias.name == '*' for alias in node.names):
                        raise ValueError('consumer import graph contains an ambiguous star import: ' + module)
                    if owned and any(alias.name in dynamic_names | dynamic_attributes for alias in node.names):
                        raise ValueError('consumer import graph contains dynamic loading or evaluation: ' + module)
                    imported = node.module or ''
                    if node.level:
                        try:
                            imported = importlib.util.resolve_name('.' * node.level + imported, package)
                        except (ImportError, ValueError) as exc:
                            raise ValueError('consumer import graph has invalid relative import: ' + module) from exc
                    imported = _canonical_import(imported)
                    if imported == 'data_sheets_schema':
                        targets.extend(imported + '.' + alias.name for alias in node.names)
                    else:
                        targets.append(imported)
                        for alias in node.names:
                            child = imported + '.' + alias.name
                            stem = 'src/' + child.replace('.', '/')
                            if stem + '.py' in package_sources or stem + '/__init__.py' in package_sources:
                                targets.append(child)
        for target in sorted(set(targets), reverse=True):
            target = _canonical_import(target)
            if target == 'data_sheets_schema':
                raise ValueError('consumer import graph imports an ambiguous package namespace')
            if target.startswith('data_sheets_schema.'):
                if target in _LEGACY_CONSUMER_MODULES:
                    raise ValueError('consumer imports forbidden v1 execution authority: ' + target)
                if target in _TRUSTED_CONSUMER_BOUNDARIES:
                    raise ValueError('consumer cannot import verifier bootstrap boundary: ' + target)
                if target not in visited:
                    source_path(target)
                    pending.append((target, None))
    return dict(sorted(visited.items()))


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('native source loading requires the main thread')


def _source_identity(name, path, raw, sha256, *, allow_empty_package=False):
    """Validate a caller-captured source before compilation; never read a pyc."""
    path = Path(path)
    if (type(name) is not str or not name or any(not part.isidentifier() for part in name.split('.'))
            or not path.is_absolute() or path.suffix != '.py'
            or type(raw) is not bytes
            or not raw and not (allow_empty_package and path.name == '__init__.py')
            or type(sha256) is not str or re.fullmatch('[0-9a-f]{64}', sha256) is None
            or hashlib.sha256(raw).hexdigest() != sha256):
        raise ValueError('invalid verified Python source identity')
    return {'name': name, 'path': str(path), 'sha256': sha256}


def _own_callables(module):
    """Retain code identity, including class methods, without invoking descriptors."""
    result = []
    for name, value in vars(module).items():
        if isinstance(value, FunctionType) and value.__module__ == module.__name__:
            result.append((name, value, value.__code__))
        elif isinstance(value, type) and value.__module__ == module.__name__:
            for member, method in vars(value).items():
                methods = ((method.__func__,) if isinstance(method, (staticmethod, classmethod))
                           else (method.fget, method.fset, method.fdel) if isinstance(method, property)
                           else (method,))
                for index, function in enumerate(methods):
                    if isinstance(function, FunctionType):
                        result.append((name + '.' + member + ':' + str(index), function, function.__code__))
    return tuple(sorted(result, key=lambda row: row[0]))


def module_source_identity(module):
    """Return provenance only for this loader's unchanged source-compiled module.

    This proves the initial executed bytes and its own current callable code,
    not arbitrary interpreter globals or the authorship of the pinned source.
    Ordinary preexisting package imports belong to the caller's bootstrap.
    """
    if type(module) is not ModuleType or module not in _SOURCE_MODULES:
        raise ValueError('module was not compiled from verified source bytes')
    identity, loader, callables = _SOURCE_MODULES[module]
    if (module.__name__ != identity['name'] or module.__file__ != identity['path']
            or module.__loader__ is not loader or module.__cached__ is not None
            or _own_callables(module) != callables):
        raise ValueError('verified source module identity or callable code changed')
    expected = _SCHEMA_BINDINGS.get(module)
    if expected is not None:
        context, guard = expected
        if (vars(module).get('_SCHEMA_LAUNCH_CONTEXT') is not context
                or vars(module).get('_schema_dependencies') is not guard):
            raise ValueError('verified schema transfer context changed')
    return dict(identity)


def _schema_memo_state(module):
    """A-side attestation plus a neutral, no-I/O dependency-state check."""
    module_source_identity(module)
    guard = module._schema_dependencies
    if guard is None:
        return None
    module_source_identity(guard)
    snapshots = getattr(guard, 'snapshots', None)
    if snapshots is None:
        return None
    module_source_identity(snapshots)
    if (vars(snapshots).get('_schema_dependencies') is not guard
            or vars(module).get('_capture_native_schema') is not vars(snapshots).get('_capture_native_schema')):
        return None
    return guard.schema_derivation_state(
        capture=module._capture_native_schema, view=module.captured_view,
        contract_alias=module.contract, path_alias=module.Path)


def _snapshot_domain(package_sources, selection_identity, snapshot_identity):
    return repr((
        'native_launch_schema_import_metadata_v1', str(ROOT),
        tuple(sorted(package_sources.items())),
        tuple(sorted(selection_identity.items())),
        tuple(sorted(snapshot_identity.items())),
        'schema_snapshot._metadata_v1',
        sys.implementation.name, sys.implementation.cache_tag, sys.version,
    )).encode('utf-8')


def _verified_snapshot_identity(snapshots, package_sources):
    if snapshots is None or type(package_sources) is not dict:
        raise ValueError('verified schema snapshot binding differs from catalog guard')
    identity = module_source_identity(snapshots)
    digest = package_sources.get(_SNAPSHOT_RELATIVE)
    path = ROOT / _SNAPSHOT_RELATIVE
    if (digest is None
            or identity != {'name': _SNAPSHOT_MODULE, 'path': str(path), 'sha256': digest}):
        raise ValueError('verified schema snapshot binding differs from catalog guard')
    _verified_source_bytes(path, digest)
    return identity


class _LaunchDerivations:
    """Bounded immutable payloads; the original donor guard is never rebound."""
    def __init__(self):
        self.donor = None
        self.phase = None
        self.payload = ()
        self.metadata_payload = ()
        self.domain = None
        self.metadata_domain = None
        self.disabled = False
        self.modules = WeakKeyDictionary()
        self.snapshots = WeakKeyDictionary()

    def _clear_snapshot_lrus(self):
        for snapshots in list(self.snapshots):
            snapshots._METADATA_DERIVATIONS.clear()
            snapshots._metadata.cache_clear()

    def current_donor(self):
        if self.donor is None:
            return None
        state = _schema_memo_state(self.donor)
        if state is None:
            self.payload = ()
            self.metadata_payload = ()
            self._clear_snapshot_lrus()
            return None
        if state[0] != self.phase:
            self.payload = ()
            self.metadata_payload = ()
            self._clear_snapshot_lrus()
            self.phase = state[0]
        return state

    def before_load(self):
        # Check the original guard before a fresh source-loaded guard can bind.
        # Never let a later import adopt changed dependencies as a new baseline.
        self.current_donor()

    def bind(self, module, package_sources):
        self.current_donor()
        identity = module_source_identity(module)
        # Includes ALL declared source pins, the executing source identity,
        # physical root and interpreter identity; schema raw bytes form the
        # other half of each key. No graph/admission result is retained.
        domain = repr((
            'native_launch_schema_metadata_v1', str(ROOT),
            tuple(sorted(package_sources.items())), tuple(sorted(identity.items())),
            sys.implementation.name, sys.implementation.cache_tag, sys.version,
        )).encode('utf-8')
        prior = self.modules.get(module)
        if prior is not None:
            guard = module._schema_dependencies
            snapshots = getattr(guard, 'snapshots', None)
            if (prior[0] == domain and prior[1] and not self.disabled
                    and guard is not None and snapshots in self.snapshots
                    and self.snapshots[snapshots][1]):
                module_source_identity(guard)
                snapshot_identity = _verified_snapshot_identity(snapshots, package_sources)
                if self.snapshots[snapshots][0] == _snapshot_domain(
                        package_sources, identity, snapshot_identity):
                    return
            # Nested loaders can reuse the same attested selection object.
            # A changed full package domain must not inherit its earlier cache.
            # Keep both caches cold for the remainder of this launch, including
            # when the outer scope resumes; no per-scope context restoration.
            self.disabled = True
            context = (domain, False)
            module._SCHEMA_DERIVATIONS.clear()
            module._SCHEMA_LAUNCH_CONTEXT = context
            _SCHEMA_BINDINGS[module] = (context, guard)
            self.modules[module] = context
            if snapshots is not None:
                snapshot_identity = module_source_identity(snapshots)
                snapshot_domain = _snapshot_domain(package_sources, identity, snapshot_identity)
                snapshot_context = (snapshot_domain, False)
                snapshots._METADATA_DERIVATIONS.clear()
                snapshots._metadata.cache_clear()
                snapshots._SCHEMA_LAUNCH_CONTEXT = snapshot_context
                _SCHEMA_BINDINGS[snapshots] = (snapshot_context, guard)
                self.snapshots[snapshots] = snapshot_context
            self.payload = ()
            self.metadata_payload = ()
            self.domain = None
            self.metadata_domain = None
            return
        # Fixed neutral dependency, loaded through the already-installed A
        # source finder. This is not a verifier callback and consumers never
        # import authority. The guard has finished loading before association.
        guard = importlib.import_module('data_sheets_schema.native_catalog_reuse')
        module_source_identity(guard)
        snapshots = getattr(guard, 'snapshots', None)
        snapshot_identity = _verified_snapshot_identity(snapshots, package_sources)
        snapshot_domain = _snapshot_domain(package_sources, identity, snapshot_identity)
        prior_snapshot = self.snapshots.get(snapshots)
        if prior_snapshot is not None and (prior_snapshot[0] != snapshot_domain or not prior_snapshot[1]):
            self.disabled = True
        _SCHEMA_BINDINGS.pop(snapshots, None)
        module._schema_dependencies = guard
        snapshots._schema_dependencies = guard
        current = _schema_memo_state(module)
        if self.donor is None:
            self.donor = module
            self.phase = None if current is None else current[0]
        donor = self.current_donor()
        enabled = (not self.disabled and current is not None and donor is not None
                   and current[0] == donor[0])
        context = (domain, enabled)
        snapshot_context = (snapshot_domain, enabled)
        module._SCHEMA_DERIVATIONS.clear()
        module._SCHEMA_LAUNCH_CONTEXT = context
        _SCHEMA_BINDINGS[module] = (context, guard)
        self.modules[module] = context
        snapshots._METADATA_DERIVATIONS.clear()
        snapshots._metadata.cache_clear()
        snapshots._SCHEMA_LAUNCH_CONTEXT = snapshot_context
        _SCHEMA_BINDINGS[snapshots] = (snapshot_context, guard)
        self.snapshots[snapshots] = snapshot_context
        if enabled and self.domain == domain:
            for key, metadata in self.payload:
                module._SCHEMA_DERIVATIONS.put(key, metadata)
        if enabled and self.metadata_domain == snapshot_domain:
            for key, metadata in self.metadata_payload:
                snapshots._METADATA_DERIVATIONS.put(key, metadata)

    def publish(self, module):
        context = self.modules.get(module)
        if context is None:
            return
        module_source_identity(module)
        guard = module._schema_dependencies
        snapshots = getattr(guard, 'snapshots', None) if guard is not None else None
        snapshot_context = self.snapshots.get(snapshots) if snapshots is not None else None
        current, donor = _schema_memo_state(module), self.current_donor()
        if (self.disabled or not context[1] or snapshot_context is None or not snapshot_context[1]
                or current is None or donor is None or current[0] != donor[0]):
            if snapshots is not None:
                snapshots._metadata.cache_clear()
            self.payload = ()
            self.metadata_payload = ()
            self.domain = None
            self.metadata_domain = None
            return
        rows = module._SCHEMA_DERIVATIONS.snapshot()
        prefix = context[0] + b'\nphase:' + str(current[0]).encode('ascii') + b'\n'
        # Entries from the recognized earlier initialization phase never transfer.
        self.payload = tuple((key, metadata) for key, metadata in rows
                             if key[0].startswith(prefix))
        self.domain = context[0]
        metadata_rows = snapshots._METADATA_DERIVATIONS.snapshot()
        metadata_prefix = (
            snapshot_context[0]
            + b'\nproducer:schema_snapshot._metadata_v1\nphase:'
            + str(current[0]).encode('ascii')
            + b'\n'
        )
        self.metadata_payload = tuple((key, metadata) for key, metadata in metadata_rows
                                      if key[0].startswith(metadata_prefix))
        self.metadata_domain = snapshot_context[0]

    def close(self):
        for module in list(self.modules):
            module._SCHEMA_DERIVATIONS.clear()
            module._SCHEMA_LAUNCH_CONTEXT = None
            module._schema_dependencies = None
            _SCHEMA_BINDINGS.pop(module, None)
        for snapshots in list(self.snapshots):
            snapshots._METADATA_DERIVATIONS.clear()
            snapshots._metadata.cache_clear()
            snapshots._SCHEMA_LAUNCH_CONTEXT = None
            snapshots._schema_dependencies = None
            _SCHEMA_BINDINGS.pop(snapshots, None)
        self.modules.clear()
        self.snapshots.clear()
        self.payload = ()
        self.metadata_payload = ()
        self.domain = None
        self.metadata_domain = None
        self.donor = None
        self.phase = None
        self.disabled = False


@contextmanager
def launch_derivations():
    """A-owned, re-entrant main-thread launch lifetime; outer exit clears all.

    This context grants no verification or execution authority. The caller still
    uses the existing attested loader and every existing live admission check.
    """
    _main_thread()
    existing = getattr(_LAUNCH_DERIVATIONS, 'memo', None)
    if existing is not None:
        yield
        return
    memo = _LaunchDerivations()
    _LAUNCH_DERIVATIONS.memo = memo
    try:
        yield
    finally:
        try:
            memo.close()
        finally:
            del _LAUNCH_DERIVATIONS.memo


class _VerifiedBytesLoader(importlib.abc.Loader):
    """A deliberately source-only loader: no SourceFileLoader/cache operations."""
    def __init__(self, name, path, raw, digest, *, package=False, verified_package=False,
                 package_sources=None):
        self.identity = _source_identity(name, path, raw, digest, allow_empty_package=package)
        self.raw, self.package = raw, package
        self.verified_package = verified_package
        self.package_sources = package_sources

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.__file__ = self.identity['path']
        module.__cached__ = None
        module.__loader__ = self
        module.__package__ = (self.identity['name'] if self.package
                              else self.identity['name'].rpartition('.')[0])
        if self.package:
            module.__path__ = [str(Path(self.identity['path']).parent)]
        code = compile(self.raw, self.identity['path'], 'exec', dont_inherit=True)
        exec(code, module.__dict__)
        _SOURCE_MODULES[module] = (dict(self.identity), self, _own_callables(module))
        if self.verified_package:
            _VERIFIED_PACKAGE_MODULES[module.__name__] = module
            memo = getattr(_LAUNCH_DERIVATIONS, 'memo', None)
            if memo is not None and module.__name__ == _SELECTION_MODULE:
                memo.bind(module, self.package_sources)


class _VerifiedBytesFinder(importlib.abc.MetaPathFinder):
    def __init__(self, sources, *, consumer=False, checked=(), package_sources=None):
        self.sources = sources
        self.package_sources = None if package_sources is None else dict(package_sources)
        self.consumer = consumer
        self.checked = set(checked)

    def find_spec(self, fullname, path=None, target=None):
        canonical = fullname
        if self.consumer and not fullname.startswith('data_sheets_schema.'):
            spec = importlib.machinery.PathFinder.find_spec(fullname, path)
            canonical = _spec_package_name(spec)
            canonical = canonical or fullname
            if canonical != fullname:
                if canonical == 'data_sheets_schema' and spec.origin is None:
                    return None  # The root namespace has no executable initializer.
                relative = str(Path(spec.origin).resolve().relative_to(ROOT))
                pinned = next((item for item in self.sources.values()
                               if str(item[0].relative_to(ROOT)) == relative), None)
                if pinned is None:
                    raise ValueError('consumer package import is not pinned: ' + fullname)
                self.sources[fullname] = pinned
            elif (fullname.split('.')[0] in {'tests', 'scripts', 'notes'} or
                  fullname == 'src' and spec and spec.origin is not None):
                raise ValueError('consumer import crosses an unverified checkout namespace: ' + fullname)
        if self.consumer and canonical in _LEGACY_CONSUMER_MODULES:
            raise ValueError('consumer imports forbidden v1 execution authority: ' + fullname)
        if self.consumer and canonical in _TRUSTED_CONSUMER_BOUNDARIES:
            raise ValueError('consumer cannot import verifier bootstrap boundary: ' + fullname)
        source = self.sources.get(fullname)
        if source is None:
            if self.consumer and fullname.startswith('data_sheets_schema.'):
                raise ValueError('consumer package import is not pinned: ' + fullname)
            return None
        filename, raw, digest, package = source
        if self.consumer and canonical != fullname:
            loader = _VerifiedAliasLoader(canonical)
            return importlib.util.spec_from_loader(fullname, loader, origin=str(filename), is_package=package)
        if raw is None:
            raw = _verified_source_bytes(filename, digest)
        if self.consumer and raw and canonical not in self.checked and canonical != 'data_sheets_schema':
            pins = {str(item[0].relative_to(ROOT)): item[2] for item in self.sources.values()}
            self.checked.update(refuse_legacy_consumer_imports(raw, name=canonical, package_sources=pins))
        loader = _VerifiedBytesLoader(fullname, filename, raw, digest, package=package,
                                      verified_package=self.consumer and fullname == canonical,
                                      package_sources=self.package_sources)
        return importlib.util.spec_from_loader(fullname, loader, origin=str(filename), is_package=package)


class _VerifiedAliasLoader(importlib.abc.Loader):
    """Bind another spelling to the same source-only canonical object."""
    def __init__(self, canonical):
        self.canonical = canonical

    def create_module(self, spec):
        module = importlib.import_module(self.canonical)
        module_source_identity(module)
        self.canonical_spec = module.__spec__
        return module

    def exec_module(self, module):
        # Import machinery assigns the alias spec even to a preexisting object.
        module.__spec__ = self.canonical_spec
        module_source_identity(module)


def _verified_source_bytes(path, digest):
    target = Path(path)
    before = target.lstat()
    if not stat.S_ISREG(before.st_mode) or target.resolve(strict=True) != target:
        raise ValueError('verified source must be an exact regular physical file')
    raw = target.read_bytes()
    after = target.lstat()
    # A read may legitimately update atime. Compare only source identity and
    # mutation metadata; the exact captured bytes must still match their pin.
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if (tuple(getattr(before, key) for key in fields) != tuple(getattr(after, key) for key in fields)
            or hashlib.sha256(raw).hexdigest() != digest):
        raise ValueError('verified module source bytes differ from their pin')
    return raw


@contextmanager
def verified_source_module(name, *, path, raw, sha256, package_sources=None):
    """Execute exactly captured source with a temporary canonical module binding.

    The fixed caller supplies the name/path/pin; serialized input cannot choose
    them. Existing bindings are restored, never trusted as executable proof.
    No bytecode is read or written for this module. With package_sources, all
    package dependencies are freshly compiled unless held in this loader's
    verified set by an enclosing context. Eviction remains process-wide: callers
    must ensure no other thread imports or uses package modules during the scope.
    Verifier boundaries refuse; external libraries remain outside this scope.
    """
    _main_thread()
    memo = getattr(_LAUNCH_DERIVATIONS, 'memo', None)
    if memo is not None:
        memo.before_load()
    _source_identity(name, path, raw, sha256)
    sources = {name: (Path(path), raw, sha256, False)}
    graph = {}
    if package_sources is not None:
        graph = refuse_legacy_consumer_imports(raw, name=name, package_sources=package_sources)
        for imported, digest in graph.items():
            stem = 'src/' + imported.replace('.', '/')
            relative = next((item for item in (stem + '.py', stem + '/__init__.py')
                             if item in package_sources), None)
            source_path = ROOT / relative
            if imported == name:
                if source_path != Path(path) or digest != sha256:
                    raise ValueError('consumer source differs from its inspected package graph')
                source = raw
            else:
                source = _verified_source_bytes(source_path, digest)
            sources[imported] = (source_path, source, digest, relative.endswith('/__init__.py'))
        # Cover runtime imports as well as the statically inspected graph. Drop
        # every pinned cached package binding so no import spelling can reuse
        # ordinary bytecode. The finder checks each newly reached module.
        for relative, digest in package_sources.items():
            if relative.endswith('.py'):
                parts = Path(relative).relative_to('src').with_suffix('').parts
                package = parts[-1] == '__init__'
                imported = '.'.join(parts[:-1] if package else parts)
                if imported not in sources:
                    sources[imported] = (ROOT / relative, None, digest, package)
    reused = {}
    if package_sources is not None:
        for key, loaded in _VERIFIED_PACKAGE_MODULES.items():
            if key not in sources or key in _LEGACY_CONSUMER_MODULES | _TRUSTED_CONSUMER_BOUNDARIES:
                continue
            actual = module_source_identity(loaded)
            filename, _, digest, _ = sources[key]
            if actual != {'name': key, 'path': str(filename), 'sha256': digest}:
                raise ValueError('verified module differs from consumer source pin')
            _verified_source_bytes(filename, digest)
            reused[key] = loaded
    absent = object()
    bindings = set(sources) - {'data_sheets_schema'}
    if package_sources is not None:
        bindings.update(key for key, loaded in list(sys.modules.items())
                        if key.startswith('data_sheets_schema.') or
                        key != 'data_sheets_schema' and _package_name(getattr(loaded, '__file__', None)))
    previous = {key: sys.modules.get(key, absent) for key in bindings}
    parents = {}
    for key in bindings:
        parent_name, _, child = key.rpartition('.')
        parent = sys.modules.get(parent_name)
        if parent is not None:
            parents[key] = (parent, child, vars(parent).get(child, absent))
    old_bytecode = sys.dont_write_bytecode
    old_path = list(sys.path)
    old_meta = list(sys.meta_path)
    old_verified = dict(_VERIFIED_PACKAGE_MODULES)
    finder = _VerifiedBytesFinder(sources, consumer=package_sources is not None, checked=graph,
                                  package_sources=package_sources)
    try:
        sys.dont_write_bytecode = True
        sys.meta_path.insert(0, finder)
        for key in bindings:
            sys.modules.pop(key, None)
            if key in parents:
                parent, child, _ = parents[key]
                vars(parent).pop(child, None)
        for key, loaded in reused.items():
            sys.modules[key] = loaded
            parent_name, _, child = key.rpartition('.')
            if parent_name in sys.modules:
                setattr(sys.modules[parent_name], child, loaded)
        module = importlib.import_module(name)
        module_source_identity(module)
        initial_modules = {key: sys.modules[key] for key in sources
                           if key != 'data_sheets_schema' and key in sys.modules}
        if package_sources is not None:
            _VERIFIED_PACKAGE_MODULES.update({key: loaded for key, loaded in initial_modules.items()
                                              if key == loaded.__name__})
        if memo is not None and package_sources is not None:
            selected = _VERIFIED_PACKAGE_MODULES.get(_SELECTION_MODULE)
            if selected is not None:
                memo.bind(selected, package_sources)
        yield module
        for key in sources:
            if key == 'data_sheets_schema':
                continue
            loaded = sys.modules.get(key)
            if key in initial_modules and loaded is not initial_modules[key]:
                raise ValueError('verified consumer graph module binding changed')
            if loaded is not None:
                actual = module_source_identity(loaded)
                filename, _, digest, _ = sources[key]
                expected_name = _package_name(filename) if package_sources is not None else key
                if (actual['name'], actual['path'], actual['sha256']) != (expected_name, str(filename), digest):
                    raise ValueError('consumer graph module differs from its captured source identity')
        if memo is not None and package_sources is not None:
            selected = _VERIFIED_PACKAGE_MODULES.get(_SELECTION_MODULE)
            if selected is not None:
                memo.publish(selected)
    finally:
        _VERIFIED_PACKAGE_MODULES.clear()
        _VERIFIED_PACKAGE_MODULES.update(old_verified)
        sys.path[:] = old_path
        sys.meta_path[:] = old_meta
        sys.dont_write_bytecode = old_bytecode
        for key in set(sources) - set(previous) - {'data_sheets_schema'}:
            loaded = sys.modules.pop(key, None)
            parent_name, _, child = key.rpartition('.')
            parent = sys.modules.get(parent_name)
            if parent is not None and vars(parent).get(child) is loaded:
                vars(parent).pop(child, None)
        for key, prior in previous.items():
            if prior is absent:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = prior
        for parent, child, prior in parents.values():
            if prior is absent:
                vars(parent).pop(child, None)
            else:
                setattr(parent, child, prior)


@contextmanager
def loaded_verified_package_module(name, *, package_sources):
    """Orchestration entry for C's projection; keep open through consumer use.

    The supplied source closure must already be verified by orchestration.
    Only A-compiled objects enter the scoped verified set, never ordinary imports.
    """
    if not name.startswith('data_sheets_schema.'):
        raise ValueError('verified package entry requires a canonical module name')
    stem = 'src/' + name.replace('.', '/')
    candidates = [item for item in (stem + '.py', stem + '/__init__.py') if item in package_sources]
    if len(candidates) != 1:
        raise ValueError('verified package entry requires one pinned source')
    path = ROOT / candidates[0]
    digest = package_sources[candidates[0]]
    raw = _verified_source_bytes(path, digest)
    with verified_source_module(name, path=path, raw=raw, sha256=digest,
                                package_sources=package_sources) as module:
        yield module


def _require_v2(identity):
    if (type(identity) is not dict or type(identity.get('version')) is not int
            or identity['version'] != VERSION
            or type(identity.get('base')) is not dict
            or type(identity['base'].get('authority_version')) is not int
            or identity['base']['authority_version'] != VERSION):
        raise ValueError('native execution requires version-2 source authority')


def dependency_identity():
    """Capture the exact v2 package, preparer, interpreter and helper closure."""
    base = neutral.dependency_identity()
    identity = {'version': VERSION, 'base': base,
                'additional_modules': deepcopy(ADDITIONAL)}
    _require_v2(identity)
    for name, pin in ADDITIONAL.items():
        target = ROOT / pin['path']
        if draft._sha(target.read_bytes()) != pin['sha256']:
            raise ValueError(f'additional native execution dependency changed: {name}')
        loaded = sys.modules.get(name)
        if loaded is not None and Path(getattr(loaded, '__file__', '')).resolve() != target.resolve():
            raise ValueError(f'native execution dependency imported from another origin: {name}')
    return identity


def _package_roster(raw):
    """Read literal NUL-delimited tree paths; never follow links or an index."""
    if not raw or not raw.endswith(b'\0'):
        raise ValueError('incomplete committed package tree')
    seen, trees, sources = set(), set(), set()
    for record in raw[:-1].split(b'\0'):
        header, separator, path_raw = record.partition(b'\t')
        parts = header.split(b' ')
        if (not separator or len(parts) != 3
                or not re.fullmatch(rb'[0-9a-f]{40}|[0-9a-f]{64}', parts[2])):
            raise ValueError('malformed committed package tree entry')
        try:
            path = path_raw.decode('utf-8')
        except UnicodeDecodeError as error:
            raise ValueError('committed package path is not UTF-8') from error
        if (not path or any(part in ('', '.', '..') for part in path.split('/'))
                or path in seen
                or not (path in ('src', PACKAGE) or path.startswith(PACKAGE + '/'))):
            raise ValueError('duplicate or invalid committed package path')
        seen.add(path)
        mode, kind = parts[:2]
        if mode == b'040000' and kind == b'tree':
            trees.add(path)
            continue
        if path in ('src', PACKAGE) or mode == b'160000' or kind == b'commit':
            raise ValueError('committed package contains a non-tree boundary or Gitlink')
        if kind != b'blob' or mode not in (b'100644', b'100755', b'120000'):
            raise ValueError('invalid committed package object kind or mode')
        if Path(path).suffix in SOURCE_SUFFIXES:
            if mode not in (b'100644', b'100755'):
                raise ValueError('committed package source is not a regular blob: ' + path)
            if '\n' in path or '\r' in path:
                raise ValueError('committed package source has an unsupported line-break path')
            sources.add(path)
    if not {'src', PACKAGE} <= trees:
        raise ValueError('committed package tree is missing')
    return sources


def _require_package_roster(source_commit, package_sources):
    if (type(source_commit) is not str
            or re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', source_commit) is None
            or type(package_sources) is not dict
            or any(type(path) is not str for path in package_sources)):
        raise ValueError('invalid committed package source declaration')
    tree = subprocess.run(
        ['git', '--no-replace-objects', 'ls-tree', '-r', '-t', '-z', '--full-tree',
         source_commit, '--', PACKAGE + '/'],
        cwd=ROOT, env=git_env(), capture_output=True, timeout=30, check=True)
    expected = _package_roster(tree.stdout)
    current = set(package_sources)
    if expected != current:
        raise ValueError('committed package source roster differs: missing=' +
                         repr(sorted(expected - current)) + '; extra=' + repr(sorted(current - expected)))


def require_committed(identity):
    """Require all consumed sources to equal the complete named Git closure.

    Queries use local Git objects with replacement objects disabled. git_env
    removes worktree/index selection overrides; object-store and other Git
    configuration may remain, so the returned blobs are independently hashed.
    Tests/docs outside the consumed closure do not affect admission. A v1
    declaration cannot be upgraded by this check.
    """
    _require_v2(identity)
    if draft._encoded(dependency_identity()) != draft._encoded(identity):
        raise ValueError('native execution dependency identity changed')
    base = identity['base']
    _require_package_roster(base['source_commit'], base['package_sources'])
    paths = dict(base['package_sources'])
    paths.update({pin['path']: pin['sha256'] for pin in base['modules'].values()})
    paths.update({pin['path']: pin['sha256'] for pin in identity['additional_modules'].values()})
    query = ''.join(f"{base['source_commit']}:{path}\n" for path in sorted(paths)).encode()
    proc = subprocess.run(['git', '--no-replace-objects', 'cat-file', '--batch'], cwd=ROOT,
                          env=git_env(), input=query, capture_output=True, timeout=30, check=True)
    offset = 0
    for path in sorted(paths):
        end = proc.stdout.find(b'\n', offset)
        if end < 0:
            raise ValueError('incomplete source-object proof')
        header = proc.stdout[offset:end].split(b' ')
        if (len(header) != 3 or header[1] != b'blob'
                or re.fullmatch(rb'[0-9a-f]{40}|[0-9a-f]{64}', header[0]) is None
                or re.fullmatch(rb'0|[1-9][0-9]*', header[2]) is None):
            raise ValueError(f'consumed source is not committed at the reviewed head: {path}')
        size = int(header[2])
        raw = proc.stdout[end + 1:end + 1 + size]
        offset = end + size + 2
        if (len(raw) != size or proc.stdout[offset - 1:offset] != b'\n'
                or hashlib.sha256(raw).hexdigest() != paths[path]):
            raise ValueError(f'consumed source differs from the reviewed commit: {path}')
    if offset != len(proc.stdout):
        raise ValueError('unexpected source-object proof tail')


@contextmanager
def loaded_dependencies(expected):
    """Compile the inherited pinned closure without calling its path loaders.

    U2 source files and globals remain untouched. Its two preparer aliases
    share one source-compiled module, while every helper import is handled by
    the exact byte-only roster. Existing wrong-origin aliases refuse; other
    aliases, the finder, paths and bytecode policy are restored on all exits.
    Fresh package imports also use their declared source bytes. Preexisting
    package imports and this module's initial import are the trusted caller
    bootstrap, not a claim of whole-interpreter bytecode attestation.
    """
    _main_thread()
    _require_v2(expected)
    if draft._encoded(dependency_identity()) != draft._encoded(expected):
        raise ValueError('native execution dependency identity changed')
    absent = object()
    names = set(expected['base']['modules']) | set(ADDITIONAL)
    previous = {name: sys.modules.get(name, absent) for name in names}
    if any(module is None for module in previous.values()):
        raise ModuleNotFoundError('a pinned native helper has an explicit import blocker')
    sources = {}
    for name, pin in {**expected['base']['modules'], **expected['additional_modules']}.items():
        path = ROOT / pin['path']
        sources[name] = (path, _verified_source_bytes(path, pin['sha256']), pin['sha256'], False)
    for relative, digest in expected['base']['package_sources'].items():
        if relative.endswith('.py'):
            parts = Path(relative).relative_to('src').with_suffix('').parts
            package = parts[-1] == '__init__'
            name = '.'.join(parts[:-1] if package else parts)
            sources[name] = (ROOT / relative, None, digest, package)
    finder = _VerifiedBytesFinder(sources)
    old_path = list(sys.path)
    old_meta = list(sys.meta_path)
    old_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        sys.meta_path.insert(0, finder)
        for name in names:
            sys.modules.pop(name, None)
        prepared = importlib.import_module('prepare_registration')
        sys.modules['prepare_registration_v2'] = prepared
        modules = {name: importlib.import_module(name) for name in sorted(names)}
        if draft._encoded(dependency_identity()) != draft._encoded(expected):
            raise ValueError('loaded native execution dependency identity changed')
        for name, module in modules.items():
            identity = module_source_identity(module)
            path, _, digest, _ = sources[name]
            if (identity['path'], identity['sha256']) != (str(path), digest):
                raise ValueError('loaded helper differs from verified source bytes')
        yield {name: modules[name] for name in sorted(EXPOSED_CONTROLS)}
        for module in modules.values():
            module_source_identity(module)
    finally:
        sys.path[:] = old_path
        sys.meta_path[:] = old_meta
        sys.dont_write_bytecode = old_bytecode
        for name, module in previous.items():
            if module is absent:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
