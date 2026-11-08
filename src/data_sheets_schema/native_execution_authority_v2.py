"""Closed version-2 source authority for explicit native execution (U3-A).

The v2 controller/supervisor supply the preparers. Only the unchanged
keep-awake primitives are added here; importing them never launches a child.
Version-1 authority and its globals remain independent.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import ast
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
from types import FunctionType, ModuleType
from weakref import WeakKeyDictionary

from data_sheets_schema import native_attribution_registration_v2 as draft
from data_sheets_schema import native_supervisor_authority_v2 as neutral
from data_sheets_schema.resources import git_env

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
    'native_shared_gate_primitives', 'native_shared_runtime_values',
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
            tree = ast.parse(source, filename=str(ROOT / relative))
        except (SyntaxError, ValueError) as exc:
            raise ValueError('consumer source has no inspectable import graph: ' + module) from exc
        package = module if relative.endswith('/__init__.py') else module.rpartition('.')[0]
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
                    # A package import may name a child module rather than a
                    # symbol. Traverse declared children as well as its init.
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
    return dict(identity)


class _VerifiedBytesLoader(importlib.abc.Loader):
    """A deliberately source-only loader: no SourceFileLoader/cache operations."""
    def __init__(self, name, path, raw, digest, *, package=False, verified_package=False):
        self.identity = _source_identity(name, path, raw, digest, allow_empty_package=package)
        self.raw, self.package = raw, package
        self.verified_package = verified_package

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


class _VerifiedBytesFinder(importlib.abc.MetaPathFinder):
    def __init__(self, sources, *, consumer=False, checked=()):
        self.sources = sources
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
                                      verified_package=self.consumer and fullname == canonical)
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
    finder = _VerifiedBytesFinder(sources, consumer=package_sources is not None, checked=graph)
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
