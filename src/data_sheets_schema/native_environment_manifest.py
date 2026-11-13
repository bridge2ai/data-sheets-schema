"""Versioned identity of the current interpreter's installed distributions.

Discovery reads distribution metadata on every current import path; it never
imports a third-party package or executes another interpreter. Every hashed
RECORD entry is checked against fresh installed bytes; unhashed entries remain
explicitly unverified. Repository sources have their separate source pins.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
from importlib import metadata
from importlib.machinery import EXTENSION_SUFFIXES
from importlib.util import source_from_cache
import os
from pathlib import Path
import platform
import re
import stat
import sys
import sysconfig

from . import native_shared_contract as c
from .native_shared_evidence import read_regular

KIND = 'd4d_native_environment_manifest'
VERSION = 2
MAX_BYTES = 8_000_000
MAX_RECORD_BYTES = 32_000_000
MAX_DISTRIBUTIONS = 10_000
MAX_IMPORT_ENTRIES = 500_000
MAX_PAYLOAD_BYTES = 2_000_000_000
MAX_VERIFIED_BYTES = 32_000_000_000
PAYLOAD_CHUNK_BYTES = 1_048_576
OWN_DISTRIBUTION = 'data-sheets-schema'
UNVERIFIED_KINDS = frozenset(('record', 'bytecode', 'other'))
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
        c.exact(row, {'name', 'version', 'record_sha256', 'verified_files', 'unverified_files'},
                'environment distribution')
        if row['name'] != _name(row['name']):
            raise ValueError('environment distribution name is not normalized')
        c._text(row['version'], 'distribution version')
        c._hash(row['record_sha256'], 'distribution RECORD hash')
        if row['name'] == OWN_DISTRIBUTION:
            raise ValueError('project source authority is not a third-party distribution')
        verified = c.exact(row['verified_files'], {'count', 'bytes'}, 'verified installed files')
        for key, maximum in (('count', MAX_IMPORT_ENTRIES), ('bytes', MAX_VERIFIED_BYTES)):
            if type(verified[key]) is not int or not 0 <= verified[key] <= maximum:
                raise ValueError('verified installed file totals are outside their bounds')
        if verified['count'] == 0 and verified['bytes'] != 0:
            raise ValueError('empty verified file inventory cannot contain payload bytes')
        groups = row['unverified_files']
        if type(groups) is not list or not groups or len(groups) > len(UNVERIFIED_KINDS):
            raise ValueError('unverified installed files require a closed kind inventory')
        kinds, entries = [], []
        for group in groups:
            c.exact(group, {'kind', 'count', 'paths'}, 'unverified installed file kind')
            kind, paths = group['kind'], group['paths']
            if kind not in UNVERIFIED_KINDS or type(paths) is not list or not paths:
                raise ValueError('unknown or empty unverified installed file kind')
            if type(group['count']) is not int or group['count'] != len(paths):
                raise ValueError('unverified installed file count differs from named entries')
            if kind == 'record' and group['count'] != 1:
                raise ValueError('one distribution must have exactly one unverified RECORD')
            for path in paths:
                _record_name(path)
            if paths != sorted(set(paths)):
                raise ValueError('unverified installed file paths must be sorted and unique')
            kinds.append(kind)
            entries.extend(paths)
        if (kinds != sorted(set(kinds)) or 'record' not in kinds
                or len(entries) != len(set(entries))
                or len(entries) + verified['count'] > MAX_IMPORT_ENTRIES):
            raise ValueError('unverified installed file inventory is ambiguous or oversized')
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


def _record_name(value):
    c._text(value, 'installed RECORD entry path')
    if len(value) > 4096 or any(character in value for character in ('\x00', '\r', '\n')):
        raise ValueError('malformed installed RECORD entry path')
    return value


def _file_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _record_hash(value):
    if type(value) is not str or value.count('=') != 1:
        raise ValueError('malformed installed RECORD hash')
    algorithm, encoded = value.split('=')
    if (algorithm not in hashlib.algorithms_guaranteed or algorithm.startswith('shake_')
            or not re.fullmatch(r'[A-Za-z0-9_-]+', encoded)):
        raise ValueError('unsupported or malformed installed RECORD hash')
    digest = hashlib.new(algorithm)
    try:
        decoded = base64.b64decode(encoded + '=' * (-len(encoded) % 4), altchars=b'-_', validate=True)
    except ValueError as exc:
        raise ValueError('malformed installed RECORD hash digest') from exc
    if (len(decoded) != digest.digest_size or
            base64.urlsafe_b64encode(decoded).decode().rstrip('=') != encoded):
        raise ValueError('malformed installed RECORD hash digest')
    return digest, decoded


def _verify_payload(path, recorded_hash, recorded_size):
    """Stream one bounded payload and bind its hash to stable path/file identity."""
    digest, expected = _record_hash(recorded_hash)
    if not re.fullmatch(r'0|[1-9][0-9]*', recorded_size):
        raise ValueError('hashed installed RECORD entry requires a canonical byte count')
    size = int(recorded_size)
    if not 0 <= size <= MAX_PAYLOAD_BYTES:
        raise ValueError('installed payload exceeds its file byte bound')
    original = Path(path)
    physical = original.resolve(strict=True)
    alias_identity = _file_identity(original.lstat())
    descriptor = os.open(physical, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != size:
            raise ValueError('installed payload size or regular-file identity differs: ' + str(original))
        total = 0
        while True:
            chunk = stream.read(min(PAYLOAD_CHUNK_BYTES, size - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > size:
                raise ValueError('installed payload grew during verification: ' + str(original))
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    if (total != size or digest.digest() != expected):
        raise ValueError('installed payload hash or byte count differs: ' + str(original))
    if (_file_identity(before) != _file_identity(after)
            or _file_identity(after) != _file_identity(physical.lstat())
            or original.resolve(strict=True) != physical
            or _file_identity(original.lstat()) != alias_identity):
        raise ValueError('installed payload changed during verification: ' + str(original))
    return {'path': str(original), 'physical': str(physical), 'identity': _file_identity(after),
            'alias_identity': alias_identity, 'bytes': total}


def _require_stable_payloads(captures):
    for capture in captures:
        for item in capture['payloads']:
            path, physical = Path(item['path']), Path(item['physical'])
            if (path.resolve(strict=True) != physical or _file_identity(path.lstat()) != item['alias_identity']
                    or _file_identity(physical.lstat()) != item['identity']):
                raise ValueError('installed payload changed during environment census: ' + str(path))


def _own_source_authority():
    package = sys.modules.get('data_sheets_schema')
    roots = getattr(package, '__path__', ())
    if {Path(path).resolve(strict=True) for path in roots} != {ROOT / 'src/data_sheets_schema'}:
        raise ValueError('own distribution exclusion requires the exact pinned project namespace')


def _own_record_entry(target, record):
    # The installed own-project metadata may describe another worktree of the
    # same project. Only its metadata, own package/path helper and named project
    # entrypoints can receive first-party ownership; the name cannot conceal an
    # unrelated importable package. Actual namespace source remains ROOT/src.
    site = record.parent.parent
    package = site / 'data_sheets_schema'
    try:
        target.relative_to(record.parent)
        return
    except ValueError:
        pass
    try:
        target.relative_to(package)
        return
    except ValueError:
        pass
    if target == site / 'data_sheets_schema.pth':
        return
    prefix = site.parent.parent.parent
    if target in {prefix / 'bin/d4d', prefix / 'bin/fairscape-cli'}:
        return
    raise ValueError('own distribution metadata cannot own unrelated package files: ' + str(target))


def _capture_distribution(distribution):
    # Keep Name and Version from one metadata read, and derive ownership only
    # from the exact RECORD bytes whose digest is registered.
    message = distribution.metadata
    name = _name(_metadata_field(message, 'Name'))
    version = _metadata_field(message, 'Version')
    own = name == OWN_DISTRIBUTION
    if own:
        _own_source_authority()
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
    direct_url = path.parent / 'direct_url.json'
    installation = None
    if direct_url.exists():
        installation = read_regular(str(direct_url), 'distribution_direct_url', max_bytes=1_000_000).captured.raw
        origin = c.strict_json(installation, 'distribution direct URL', 1_000_000)
        if type(origin) is not dict or type(origin.get('dir_info', {})) is not dict:
            raise ValueError('malformed distribution installation metadata: ' + name)
        if not own and origin.get('dir_info', {}).get('editable', False) is not False:
            raise ValueError('editable or development third-party distribution holds: ' + name)
    owned, payloads, unverified = set(), [], {}
    verified_bytes = 0
    for row in csv.reader(io.StringIO(raw.decode('utf-8'), newline=''), strict=True):
        if len(row) != 3:
            raise ValueError('distribution has malformed installed RECORD: ' + name)
        entry = _record_name(row[0])
        if not own and (Path(entry).name.startswith('__editable__') or entry.endswith('.egg-link')):
            raise ValueError('editable or development third-party distribution holds: ' + name)
        target = Path(distribution.locate_file(row[0])).resolve(strict=False)
        if own:
            _own_record_entry(target, path)
        if target in owned:
            raise ValueError('distribution has duplicate installed RECORD paths: ' + name)
        owned.add(target)
        if len(owned) > MAX_IMPORT_ENTRIES:
            raise ValueError('distribution RECORD exceeds its entry count bound')
        if row[1]:
            payload = _verify_payload(distribution.locate_file(entry), row[1], row[2])
            payloads.append(payload)
            verified_bytes += payload['bytes']
            if verified_bytes > MAX_VERIFIED_BYTES:
                raise ValueError('distribution payload exceeds its total byte bound')
        else:
            if row[2] and re.fullmatch(r'0|[1-9][0-9]*', row[2]) is None:
                raise ValueError('unhashed installed RECORD entry has a malformed size')
            kind = 'record' if target == path else 'bytecode' if entry.endswith(('.pyc', '.pyo')) else 'other'
            unverified.setdefault(kind, []).append(entry)
    if path not in owned:
        raise ValueError('distribution RECORD must identify itself: ' + name)
    if 'record' not in unverified:
        raise ValueError('distribution RECORD must name itself without a recursive hash: ' + name)
    return {'row': {'name': name, 'version': version, 'record_sha256': c.sha(raw),
                'verified_files': {'count': len(payloads), 'bytes': verified_bytes},
                'unverified_files': [{'kind': kind, 'count': len(entries), 'paths': sorted(entries)}
                                     for kind, entries in sorted(unverified.items())]},
            'record_path': str(path), 'metadata': tuple(message.items()),
            'owned': tuple(sorted(str(item) for item in owned)), 'installation': installation,
            'payloads': payloads, 'own_project': own}


def _capture_environment(paths):
    captures = []
    total_files = total_bytes = 0
    for distribution in metadata.distributions(path=paths):
        captured = _capture_distribution(distribution)
        captures.append(captured)
        total_files += len(captured['owned'])
        total_bytes += captured['row']['verified_files']['bytes']
        if total_files > MAX_IMPORT_ENTRIES or total_bytes > MAX_VERIFIED_BYTES:
            raise ValueError('installed environment payload inventory exceeds its aggregate bound')
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
    info = path.lstat()
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
    bytecode may use its RECORD-owned source. Hashed owned files are separately
    verified against installed contents. Standard-library and exact repository roots
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
            if entry.name.endswith('.egg-link'):
                raise ValueError('editable or development import root holds: ' + str(path))
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
    """Regenerate semantic identity and verify each installed hashed payload.

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
        _require_stable_payloads(captures)
        value = {'kind': KIND, 'version': VERSION, 'interpreter': identity,
                 'distributions': [capture['row'] for capture in captures if not capture['own_project']]}
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
