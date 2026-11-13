"""Versioned identity of the current interpreter's installed distributions.

Discovery reads distribution metadata on every current import path; it never
imports a third-party package or executes another interpreter. RECORD hashes
identify installation metadata, not a fresh hash of every installed file.
Repository sources are bound separately by the preparation's source pins.
"""
from __future__ import annotations

import csv
import io
from importlib import metadata
from importlib.machinery import EXTENSION_SUFFIXES
from importlib.util import source_from_cache
import os
from pathlib import Path
import platform
import re
import sys
import sysconfig

from . import native_shared_contract as c
from .native_shared_evidence import read_regular

KIND = 'd4d_native_environment_manifest'
VERSION = 1
MAX_BYTES = 8_000_000
MAX_RECORD_BYTES = 32_000_000
MAX_DISTRIBUTIONS = 10_000
MAX_IMPORT_ENTRIES = 500_000
ROOT = Path(__file__).resolve().parents[2]
_NAME = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')


def _name(value):
    c._text(value, 'distribution name')
    normalized = re.sub(r'[-_.]+', '-', value).lower()
    if _NAME.fullmatch(normalized) is None:
        raise ValueError('distribution name is not a normalized project name')
    return normalized


def validate(value):
    """Validate the closed data shape without querying an environment."""
    c.exact(value, {'kind', 'version', 'interpreter', 'distributions'}, 'environment manifest')
    if (value['kind'] != KIND or type(value['version']) is not int
            or value['version'] != VERSION):
        raise ValueError('unknown environment manifest kind/version')
    identity = c.exact(value['interpreter'], {'implementation', 'version', 'build'},
                       'environment interpreter')
    for name in ('implementation', 'version'):
        c._text(identity[name], 'interpreter ' + name)
    if type(identity['build']) is not list or len(identity['build']) != 2:
        raise ValueError('interpreter build requires its two semantic components')
    for item in identity['build']:
        c._text(item, 'interpreter build component')
    rows = value['distributions']
    if type(rows) is not list or not rows or len(rows) > MAX_DISTRIBUTIONS:
        raise ValueError('environment requires a bounded nonempty distribution inventory')
    names = []
    for row in rows:
        c.exact(row, {'name', 'version', 'record_sha256'}, 'environment distribution')
        if row['name'] != _name(row['name']):
            raise ValueError('environment distribution name is not normalized')
        c._text(row['version'], 'distribution version')
        c._hash(row['record_sha256'], 'distribution RECORD hash')
        names.append(row['name'])
    if names != sorted(set(names)):
        raise ValueError('environment distributions must be sorted and unique')
    if len(c.canonical(value)) > MAX_BYTES:
        raise ValueError('environment manifest exceeds its byte bound')
    return value


def _metadata_field(message, key):
    values = message.get_all(key, [])
    if len(values) != 1:
        raise ValueError('distribution has missing or ambiguous ' + key + ' metadata')
    return c._text(values[0], 'distribution ' + key)


def _capture_distribution(distribution):
    # Keep Name and Version from one metadata read, and derive ownership only
    # from the exact RECORD bytes whose digest is registered.
    message = distribution.metadata
    name = _name(_metadata_field(message, 'Name'))
    version = _metadata_field(message, 'Version')
    files = distribution.files
    if files is None:
        raise ValueError('distribution is missing installed RECORD metadata: ' + name)
    records = [f for f in files if str(f).endswith('.dist-info/RECORD')]
    if len(records) != 1:
        raise ValueError('distribution has missing or ambiguous installed RECORD: ' + name)
    path = Path(distribution.locate_file(records[0])).resolve(strict=True)
    raw = read_regular(str(path), 'distribution_record', max_bytes=MAX_RECORD_BYTES).captured.raw
    if not raw:
        raise ValueError('distribution has empty installed RECORD: ' + name)
    owned = set()
    for row in csv.reader(io.StringIO(raw.decode('utf-8'), newline=''), strict=True):
        if len(row) != 3 or not row[0] or '\x00' in row[0]:
            raise ValueError('distribution has malformed installed RECORD: ' + name)
        target = Path(distribution.locate_file(row[0])).resolve(strict=False)
        if target in owned:
            raise ValueError('distribution has duplicate installed RECORD paths: ' + name)
        owned.add(target)
    if path not in owned:
        raise ValueError('distribution RECORD must identify itself: ' + name)
    return {'row': {'name': name, 'version': version, 'record_sha256': c.sha(raw)},
            'record_path': str(path), 'metadata': tuple(message.items()),
            'owned': tuple(sorted(str(item) for item in owned))}


def _capture_environment(paths):
    captures = []
    for distribution in metadata.distributions(path=paths):
        captures.append(_capture_distribution(distribution))
        if len(captures) > MAX_DISTRIBUTIONS:
            raise ValueError('environment exceeds its distribution count bound')
    captures.sort(key=lambda item: (item['row']['name'], item['record_path']))
    names = [item['row']['name'] for item in captures]
    if names != sorted(set(names)):
        raise ValueError('environment distributions must be sorted and unique')
    return captures


def _import_paths():
    return list(dict.fromkeys(str(Path(p or os.getcwd()).resolve(strict=True))
                             for p in sys.path if Path(p or os.getcwd()).exists()))


def _interpreter_identity():
    return {'implementation': sys.implementation.name,
            'version': platform.python_version(), 'build': list(platform.python_build())}


def _directory_identity(path):
    info = path.stat(follow_symlinks=False)
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _require_stable_directories(snapshots):
    for path, expected in snapshots.items():
        if _directory_identity(path) != expected:
            raise ValueError('third-party import directory changed during environment census: ' + str(path))


def _first_party_roots():
    # These exact import roots are covered by the separate repository authority.
    # An unrelated checkout or an arbitrary descendant is never exempted.
    return {ROOT, ROOT / 'src', ROOT / 'fairscape_models'}


def _stdlib_roots():
    roots = {Path(sysconfig.get_path(key)).resolve(strict=True)
             for key in ('stdlib', 'platstdlib')}
    return roots | {root / 'lib-dynload' for root in roots}


def _owned_files(captures):
    return {Path(path) for capture in captures for path in capture['owned']}


def _requires_owner(path):
    name = path.name
    return (name.endswith(('.py', '.pyc', '.pth'))
            or any(name.endswith(suffix) for suffix in EXTENSION_SUFFIXES))


def _require_owned_import_roots(paths, captures):
    """Hold for code with no installation metadata, including namespace portions.

    Every importable code file in a third-party root needs a RECORD entry;
    ownership of only the top-level namespace is insufficient. Ordinary cached
    bytecode may use its RECORD-owned source. This checks metadata coverage,
    not installed file contents. Standard-library and exact repository roots
    have their own interpreter/source authority and are excluded explicitly.
    """
    exempt = _first_party_roots() | _stdlib_roots()
    owned = _owned_files(captures)
    visited = set()
    snapshots = {}
    count = 0
    pending = [Path(path) for path in paths if Path(path) not in exempt]
    while pending:
        directory = pending.pop()
        if directory in visited:
            continue
        visited.add(directory)
        if not directory.is_dir():
            raise ValueError('unsupported archive or non-directory third-party import root: ' + str(directory))
        snapshots[directory] = _directory_identity(directory)
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            count += 1
            if count > MAX_IMPORT_ENTRIES:
                raise ValueError('third-party import ownership census exceeds its entry bound')
            path = Path(entry.path)
            if entry.is_dir():
                if entry.is_symlink():
                    raise ValueError('unsupported symlinked third-party import directory: ' + str(path))
                if not entry.name.endswith(('.dist-info', '.egg-info')):
                    pending.append(path)
            elif _requires_owner(path):
                if path.suffix == '.pyc' and path.parent.name == '__pycache__':
                    # Python's import machinery does not load pytest's tagged
                    # rewrite caches or caches for another interpreter here.
                    # Loose sourceless .pyc files outside __pycache__ still need
                    # their own RECORD entry, regardless of their filename.
                    tag = sys.implementation.cache_tag
                    if tag is None or re.fullmatch(
                            r'.+\.' + re.escape(tag) + r'(?:\.opt-[0-9]+)?\.pyc',
                            path.name) is None:
                        continue
                physical = path.resolve(strict=True)
                if physical in owned:
                    continue
                if path.suffix == '.pyc' and path.parent.name == '__pycache__':
                    try:
                        source = Path(source_from_cache(str(path))).resolve(strict=True)
                    except (ValueError, FileNotFoundError):
                        source = None
                    if source in owned:
                        continue
                raise ValueError('importable code has missing distribution RECORD ownership: ' + str(path))
    _require_stable_directories(snapshots)
    return snapshots


def generate():
    """Regenerate semantic identity and every discoverable installed RECORD.

    Do not narrow this to packages already imported: registered helpers may
    import another installed distribution after registration. Missing metadata,
    duplicate normalized names and non-file RECORDs are refusal conditions.
    """
    try:
        paths = _import_paths()
        identity = _interpreter_identity()
        captures = _capture_environment(paths)
        directories = _require_owned_import_roots(paths, captures)
        # The census may be long. Re-discover the roster, metadata and RECORDs;
        # cached rows from before the census must never establish current state.
        if (_import_paths() != paths or _interpreter_identity() != identity
                or _capture_environment(paths) != captures):
            raise ValueError('interpreter or distribution metadata changed during environment census')
        _require_stable_directories(directories)
        value = {'kind': KIND, 'version': VERSION, 'interpreter': identity,
                 'distributions': [capture['row'] for capture in captures]}
        return validate(value)
    except (OSError, UnicodeError, TypeError, AttributeError, csv.Error) as exc:
        raise ValueError('environment metadata is missing, ambiguous or unreadable') from exc


def verify(pin):
    """Read a pinned manifest and compare it with the current environment."""
    c.file_pin(pin, 'environment manifest pin')
    captured = read_regular(pin['path'], 'environment_manifest', max_bytes=MAX_BYTES).captured
    if {'path': captured.pin.path, 'bytes': captured.pin.bytes,
            'sha256': captured.pin.sha256} != pin:
        raise ValueError('environment manifest differs from its registered pin')
    value = validate(c.strict_json(captured.raw, 'environment manifest', MAX_BYTES))
    if captured.raw != c.canonical(value):
        raise ValueError('environment manifest must use canonical bytes')
    if captured.raw != c.canonical(generate()):
        raise ValueError('environment manifest is stale for the current interpreter environment')
    return value


def write(path):
    """Create one manifest without overwriting an existing file, returning its pin."""
    path = c.canonical_path(str(path), 'environment manifest path')
    if str(Path(path).parent.resolve(strict=True) / Path(path).name) != path:
        raise ValueError('environment manifest parent must be its physical path')
    raw = c.canonical(generate())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    pin = {'path': path, 'bytes': len(raw), 'sha256': c.sha(raw)}
    verify(pin)
    return pin
