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
_LEGACY_CONSUMER_MODULES = frozenset('data_sheets_schema.' + name for name in (
    'native_execution', 'native_execution_registration', 'native_execution_authority',
    'native_supervisor', 'native_attempt_supervisor', 'native_supervisor_authority', 'native_attribution_registration',
    'native_attribution_controller'))
_TRUSTED_CONSUMER_BOUNDARIES = frozenset((
    'data_sheets_schema.native_execution_registration_v2',
    'data_sheets_schema.native_execution_authority_v2'))


def refuse_legacy_consumer_imports(raw, *, name, package_sources):
    """Check the fixed consumer's explicit, pinned package import graph.

    This is a conservative source contract, not a Python sandbox. It stops at
    U3-A's two reviewed v2 boundaries (which themselves use a pure v1 runtime
    validator); external libraries and the caller's bootstrap are out of this
    graph. Dynamic loading/evaluation refuses instead of guessing its target.
    Every package dependency inspected here is read from its declared pin.
    """
    if (type(raw) is not bytes or not raw or type(name) is not str
            or not name.startswith('data_sheets_schema.') or type(package_sources) is not dict):
        raise ValueError('invalid fixed consumer import graph')
    dynamic_names = {'__import__', 'exec', 'eval', 'compile', 'FunctionType', 'CodeType'}
    dynamic_attributes = {'import_module', 'exec_module', 'load_module',
        'spec_from_file_location', 'spec_from_loader', 'module_from_spec',
        'SourceFileLoader', 'SourcelessFileLoader', 'ExtensionFileLoader', 'run_path', 'run_module',
        '__import__'}

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
        if module in _TRUSTED_CONSUMER_BOUNDARIES or module in visited:
            continue
        if len(visited) >= 256:
            raise ValueError('consumer package import graph exceeds its fixed bound')
        relative = source_path(module)
        digest = package_sources[relative]
        if source is None:
            source = _verified_source_bytes(ROOT / relative, digest)
        if hashlib.sha256(source).hexdigest() != digest:
            raise ValueError('consumer import graph source differs from its pin: ' + module)
        visited[module] = digest
        try:
            tree = ast.parse(source, filename=str(ROOT / relative))
        except (SyntaxError, ValueError) as exc:
            raise ValueError('consumer source has no inspectable import graph: ' + module) from exc
        package = module if relative.endswith('/__init__.py') else module.rpartition('.')[0]
        targets = []
        aliases = {'__builtins__': 'builtins'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    aliases[alias.asname or alias.name.split('.')[0]] = alias.name
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
            return qualified(node).split('.')[0] in {'importlib', 'builtins', 'runpy'}

        for node in ast.walk(tree):
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
                                attribute.value in dynamic_names | dynamic_attributes)
                    dynamic |= import_machinery(node.args[0])
                elif operation == 'vars' and node.args:
                    dynamic |= import_machinery(node.args[0])
            if dynamic:
                raise ValueError('consumer import graph contains dynamic loading or evaluation: ' + module)
            if isinstance(node, ast.Import):
                targets.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if any(alias.name == '*' for alias in node.names):
                    raise ValueError('consumer import graph contains an ambiguous star import: ' + module)
                if any(alias.name in dynamic_names | dynamic_attributes for alias in node.names):
                    raise ValueError('consumer import graph contains dynamic loading or evaluation: ' + module)
                imported = node.module or ''
                if node.level:
                    try:
                        imported = importlib.util.resolve_name('.' * node.level + imported, package)
                    except (ImportError, ValueError) as exc:
                        raise ValueError('consumer import graph has invalid relative import: ' + module) from exc
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
            if target == 'data_sheets_schema':
                raise ValueError('consumer import graph imports an ambiguous package namespace')
            if target.startswith('data_sheets_schema.'):
                if target in _LEGACY_CONSUMER_MODULES:
                    raise ValueError('consumer imports forbidden v1 execution authority: ' + target)
                if target not in visited and target not in _TRUSTED_CONSUMER_BOUNDARIES:
                    source_path(target)
                    pending.append((target, None))
    return dict(sorted(visited.items()))


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('native source loading requires the main thread')


def _source_identity(name, path, raw, sha256):
    """Validate a caller-captured source before compilation; never read a pyc."""
    path = Path(path)
    if (type(name) is not str or not name or any(not part.isidentifier() for part in name.split('.'))
            or not path.is_absolute() or path.suffix != '.py'
            or type(raw) is not bytes or not raw
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
    def __init__(self, name, path, raw, digest, *, package=False):
        self.identity = _source_identity(name, path, raw, digest)
        self.raw, self.package = raw, package

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


class _VerifiedBytesFinder(importlib.abc.MetaPathFinder):
    def __init__(self, sources):
        self.sources = sources

    def find_spec(self, fullname, path=None, target=None):
        source = self.sources.get(fullname)
        if source is None:
            return None
        filename, raw, digest, package = source
        if raw is None:
            raw = _verified_source_bytes(filename, digest)
        loader = _VerifiedBytesLoader(fullname, filename, raw, digest, package=package)
        return importlib.util.spec_from_loader(fullname, loader, origin=str(filename), is_package=package)


def _verified_source_bytes(path, digest):
    target = Path(path)
    before = target.lstat()
    if not stat.S_ISREG(before.st_mode) or target.resolve(strict=True) != target:
        raise ValueError('verified source must be an exact regular physical file')
    raw = target.read_bytes()
    after = target.lstat()
    if (before != after or hashlib.sha256(raw).hexdigest() != digest):
        raise ValueError('verified module source bytes differ from their pin')
    return raw


@contextmanager
def verified_source_module(name, *, path, raw, sha256, package_sources=None):
    """Execute exactly captured source with a temporary canonical module binding.

    The fixed caller supplies the name/path/pin; serialized input cannot choose
    them. Existing bindings are restored, never trusted as executable proof.
    No bytecode is read or written for this module. With package_sources, all
    inspected package dependencies are also freshly compiled, replacing cached
    bindings only within this context. Trusted U3-A boundaries and external
    libraries remain the declared bootstrap residual.
    """
    _main_thread()
    _source_identity(name, path, raw, sha256)
    sources = {name: (Path(path), raw, sha256, False)}
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
    absent = object()
    previous = {key: sys.modules.get(key, absent) for key in sources}
    parents = {}
    for key in sources:
        parent_name, _, child = key.rpartition('.')
        parent = sys.modules.get(parent_name)
        if parent is not None:
            parents[key] = (parent, child, vars(parent).get(child, absent))
    old_bytecode = sys.dont_write_bytecode
    old_path = list(sys.path)
    old_meta = list(sys.meta_path)
    finder = _VerifiedBytesFinder(sources)
    try:
        sys.dont_write_bytecode = True
        sys.meta_path.insert(0, finder)
        for key in sources:
            sys.modules.pop(key, None)
            if key in parents:
                parent, child, _ = parents[key]
                vars(parent).pop(child, None)
        module = importlib.import_module(name)
        module_source_identity(module)
        initial_modules = {key: sys.modules[key] for key in sources if key in sys.modules}
        yield module
        for key in sources:
            loaded = sys.modules.get(key)
            if key in initial_modules and loaded is not initial_modules[key]:
                raise ValueError('verified consumer graph module binding changed')
            if loaded is not None:
                actual = module_source_identity(loaded)
                filename, _, digest, _ = sources[key]
                if (actual['name'], actual['path'], actual['sha256']) != (key, str(filename), digest):
                    raise ValueError('consumer graph module differs from its captured source identity')
    finally:
        sys.path[:] = old_path
        sys.meta_path[:] = old_meta
        sys.dont_write_bytecode = old_bytecode
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
