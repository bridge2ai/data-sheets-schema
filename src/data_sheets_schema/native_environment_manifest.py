"""Versioned identity of the current interpreter's installed distributions.

Discovery reads distribution metadata on every current import path; it never
imports a third-party package or executes another interpreter. Every non-pyc
hashed RECORD entry is checked against fresh installed bytes; other unhashed
entries remain explicitly unverified. All .pyc files are excluded from payload
and unowned inventories and totals; the exact RECORD metadata stays pinned.
Repository sources have their separate source pins.
"""
from __future__ import annotations

import base64
import csv
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import io
from importlib import metadata
import os
from pathlib import Path
import platform
import re
import stat
import sys
import sysconfig
import threading

from . import native_shared_contract as c
from .native_shared_evidence import read_regular

KIND = 'd4d_native_environment_manifest'
# Lead addenda: no production registration used the earlier shapes. Refine v1
# in place with RECORD-entry and unowned lstat baselines for the 2026-11-14
# light-check ruling. Earlier synthetic manifests must be regenerated.
VERSION = 1
MAX_BYTES = 8_000_000
MAX_RECORD_BYTES = 32_000_000
MAX_DISTRIBUTIONS = 10_000
MAX_IMPORT_ENTRIES = 500_000
MAX_PAYLOAD_BYTES = 2_000_000_000
MAX_VERIFIED_BYTES = 32_000_000_000
PAYLOAD_CHUNK_BYTES = 1_048_576
OWN_DISTRIBUTION = 'data-sheets-schema'
UNVERIFIED_KINDS = frozenset(('record', 'bytecode', 'other'))
EXCLUDED_REASONS = frozenset(('first_party_source_pins', 'standard_library_interpreter_identity'))
ROOT = Path(__file__).resolve().parents[2]
_NAME = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
_STAT_TYPES = frozenset((0, stat.S_IFREG, stat.S_IFLNK, stat.S_IFDIR,
                         stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFCHR, stat.S_IFBLK))
_PROCESS_STATE_NAME = '_d4d_environment_manifest_verification_v1'



_census_resolver = ContextVar('environment_census_resolver', default=None)
_generation_capture = ContextVar('environment_generation_capture', default=None)
_IMPLEMENTATION_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _ancestor_identity(info):
    """Bind resolution to the object, independent of sibling entry changes."""
    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)


class _CensusResolver:
    """Reuse directory resolution only within one checked live census."""

    def __init__(self):
        self.directories = {}
        self.identities = {}
        self.links = {}
        self.statuses = {}
        self.followed_statuses = {}

    def status(self, path, *, follow=False):
        key = os.fspath(path)
        cache = self.followed_statuses if follow else self.statuses
        if key not in cache:
            try:
                cache[key] = os.stat(key) if follow else os.lstat(key)
            except FileNotFoundError:
                cache[key] = None
        info = cache[key]
        if info is None:
            raise FileNotFoundError(key)
        return info

    def begin_second_capture(self):
        # Full generation deliberately rediscovers metadata and identities.
        # Preserve ancestor witnesses, but take fresh observations in this pass.
        self.statuses.clear()
        self.followed_statuses.clear()
        self.directories.clear()

    def resolve(self, path, *, strict=True, pending=None):
        path = Path(path)
        if not path.is_absolute():
            path = Path.cwd() / path
        return Path(self._resolve_string(str(path), strict=strict, pending=pending))

    def _resolve_string(self, key, *, strict=True, pending=None):
        if key in self.directories:
            return self.directories[key]
        if pending is None:
            pending = set()
        if key in pending:
            raise ValueError('symlink loop during environment census: ' + key)
        pending.add(key)
        try:
            parent_key, name = os.path.split(key)
            if parent_key == key:
                physical = key
            else:
                parent = self._resolve_string(parent_key, strict=strict, pending=pending)
                physical = os.path.dirname(parent) if name == '..' else os.path.join(parent, name)
            try:
                info = self.status(physical)
            except FileNotFoundError:
                if strict:
                    raise
                return physical
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(physical)
                identity = (_ancestor_identity(info), target)
                previous = self.links.setdefault(physical, identity)
                if previous != identity:
                    raise ValueError('symlink changed during environment census: ' + physical)
                destination = Path(target)
                if not destination.is_absolute():
                    destination = Path(os.path.dirname(physical)) / destination
                resolved = self._resolve_string(str(destination), strict=strict, pending=pending)
                if _path_kind(resolved, stat.S_ISDIR):
                    self.directories[key] = resolved
                return resolved
            if stat.S_ISDIR(info.st_mode):
                identity = _ancestor_identity(info)
                previous = self.identities.setdefault(physical, identity)
                if previous != identity:
                    raise ValueError('ancestor changed during environment census: ' + physical)
                self.directories[key] = physical
            return physical
        finally:
            pending.remove(key)

    def require_stable(self):
        for path, identity in self.identities.items():
            if _ancestor_identity(os.lstat(path)) != identity:
                raise ValueError('ancestor changed during environment census: ' + path)
        for path, identity in self.links.items():
            if (_ancestor_identity(os.lstat(path)), os.readlink(path)) != identity:
                raise ValueError('symlink changed during environment census: ' + path)


def _resolve(path, *, strict=True):
    resolver = _census_resolver.get()
    if resolver is None:
        return Path(path).resolve(strict=strict)
    return resolver.resolve(path, strict=strict)


def _path_status(path):
    resolver = _census_resolver.get()
    return os.lstat(path) if resolver is None else resolver.status(path)


def _path_kind(path, predicate):
    try:
        info = _path_status(path)
        if stat.S_ISLNK(info.st_mode):
            resolver = _census_resolver.get()
            info = os.stat(path) if resolver is None else resolver.status(path, follow=True)
        return predicate(info.st_mode)
    except (FileNotFoundError, NotADirectoryError):
        return False


def _run_census(operation, *args):
    resolver = _CensusResolver()
    token = _census_resolver.set(resolver)
    try:
        result = operation(*args)
        resolver.require_stable()
        return result
    except OSError as exc:
        raise ValueError('environment census path disappeared or became unreadable') from exc
    finally:
        _census_resolver.reset(token)


def _fingerprints(captures, census):
    fingerprints = {path: pin for row in captures for path, pin in row['stat_identities'].items()}
    for row in census['payloads']:
        fingerprints[row['path']] = row['alias_identity']
        fingerprints[row['physical']] = row['identity']
    for capture in captures:
        for row in capture['payloads']:
            fingerprints[row['path']] = row['alias_identity']
            fingerprints[row['physical']] = row['identity']
    return fingerprints


def _process_state():
    # Source-attested imports may instantiate this module more than once. Keep
    # only this interpreter process's memo on sys, not in a reloaded module or
    # on disk. A fork must replace the holder before touching its inherited lock.
    state = getattr(sys, _PROCESS_STATE_NAME, None)
    if state is None or state['pid'] != os.getpid():
        state = {'pid': os.getpid(), 'lock': threading.RLock(), 'full': {},
                 'mode': ContextVar('d4d_environment_preparation_mode', default='full')}
        if getattr(sys, _PROCESS_STATE_NAME, None) is None:
            # Concurrent first callers share the winning holder too.
            state = sys.__dict__.setdefault(_PROCESS_STATE_NAME, state)
        elif getattr(sys, _PROCESS_STATE_NAME)['pid'] != os.getpid():
            setattr(sys, _PROCESS_STATE_NAME, state)
        else:
            state = getattr(sys, _PROCESS_STATE_NAME)
    return state


def preparation_mode():
    """Full unless an explicit helper reconstruction scope selects light."""
    return _process_state()['mode'].get()


@contextmanager
def verification_scope(*, mode):
    """Select reconstruction cost only; explicit verify(mode='full') wins."""
    if mode not in ('full', 'light'):
        raise ValueError('unknown environment verification mode')
    variable = _process_state()['mode']
    token = variable.set(mode)
    try:
        yield
    finally:
        variable.reset(token)


def _stat_shape(value):
    c.exact(value, {'type', 'bytes'}, 'installed lstat identity')
    if (type(value['type']) is not int or value['type'] not in _STAT_TYPES
            or type(value['bytes']) is not int or not 0 <= value['bytes'] <= max(MAX_PAYLOAD_BYTES, MAX_RECORD_BYTES)
            or (value['type'] == 0 and value['bytes'] != 0)):
        raise ValueError('invalid installed lstat size or type')
    return value


def _record_stat_shape(value):
    # A fixed [file type, byte size] pair preserves both lstat fields without
    # repeating their keys for every installed file. Full dev environments
    # must fit the existing shared JSON structural budget, not raise it.
    if type(value) is not list or len(value) != 2:
        raise ValueError('installed RECORD lstat requires a type and size pair')
    return _stat_shape({'type': value[0], 'bytes': value[1]})


def _lstat(path, *, fresh=False):
    try:
        info = os.lstat(path) if fresh else _path_status(path)
    except FileNotFoundError:
        # Unhashed RECORD entries have always been explicitly unverified and
        # may be absent. Pin that absence too; a later addition is a change.
        return {'type': 0, 'bytes': 0}, None
    return _stat_shape({'type': stat.S_IFMT(info.st_mode), 'bytes': info.st_size}), _file_identity(info)


def _name(value):
    c._text(value, 'distribution name')
    normalized = re.sub(r'[-_.]+', '-', value).lower()
    if _NAME.fullmatch(normalized) is None:
        raise ValueError('distribution name is not a normalized project name')
    return normalized


def validate(value):
    """Validate the closed data shape without querying an environment."""
    c.exact(value, {'kind', 'version', 'interpreter', 'distributions', 'unowned_files', 'excluded_roots'},
            'environment manifest')
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
        c.exact(row, {'name', 'version', 'record_sha256', 'verified_files', 'unverified_files', 'file_stats'},
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
                if path.endswith('.pyc'):
                    raise ValueError('pyc bytecode is excluded from the environment manifest')
            if paths != sorted(set(paths)):
                raise ValueError('unverified installed file paths must be sorted and unique')
            kinds.append(kind)
            entries.extend(paths)
        if (kinds != sorted(set(kinds)) or 'record' not in kinds
                or len(entries) != len(set(entries))
                or len(entries) + verified['count'] > MAX_IMPORT_ENTRIES):
            raise ValueError('unverified installed file inventory is ambiguous or oversized')
        stats = row['file_stats']
        if type(stats) is not dict or len(stats) != verified['count'] + len(entries):
            raise ValueError('installed lstat inventory differs from RECORD entries')
        if not set(entries) <= stats.keys():
            raise ValueError('unverified installed entries lack lstat identities')
        for path, item in stats.items():
            _record_name(path)
            if path.endswith('.pyc'):
                raise ValueError('pyc bytecode is excluded from the environment manifest')
            _record_stat_shape(item)
        names.append(row['name'])
    if names != sorted(set(names)):
        raise ValueError('environment distributions must be sorted and unique')
    exclusions = value['excluded_roots']
    if type(exclusions) is not list or len(exclusions) > MAX_IMPORT_ENTRIES:
        raise ValueError('environment exclusions require a bounded root inventory')
    roots = []
    for item in exclusions:
        c.exact(item, {'root', 'reason'}, 'excluded import root')
        c.canonical_path(_record_name(item['root']), 'excluded import root')
        if item['reason'] not in EXCLUDED_REASONS:
            raise ValueError('unknown excluded import root authority')
        roots.append(item['root'])
    if roots != sorted(set(roots)):
        raise ValueError('excluded import roots must be sorted and unique')
    unowned = value['unowned_files']
    if type(unowned) is not list or len(unowned) > MAX_IMPORT_ENTRIES:
        raise ValueError('unowned files require a bounded inventory')
    keys, total_bytes = [], 0
    for item in unowned:
        c.exact(item, {'root', 'path', 'bytes', 'sha256', 'stat'}, 'unowned file')
        _stat_shape(item['stat'])
        if item['stat']['type'] not in (stat.S_IFREG, stat.S_IFLNK):
            raise ValueError('unowned file lacks regular or symlink lstat identity')
        root = c.canonical_path(_record_name(item['root']), 'unowned import root')
        path = _record_name(item['path'])
        if path.endswith('.pyc'):
            raise ValueError('pyc bytecode is excluded from the environment manifest')
        if (path in ('.', '..') or Path(path).is_absolute() or str(Path(path)) != path
                or any(part in ('.', '..') for part in Path(path).parts)):
            raise ValueError('unowned file path must be normalized and relative to its root')
        if root in roots:
            raise ValueError('unowned file cannot name an excluded import root')
        if type(item['bytes']) is not int or not 0 <= item['bytes'] <= MAX_PAYLOAD_BYTES:
            raise ValueError('unowned file exceeds its byte bound')
        c._hash(item['sha256'], 'unowned file hash')
        keys.append((root, path))
        total_bytes += item['bytes']
    if (keys != sorted(set(keys))
            or total_bytes + sum(row['verified_files']['bytes'] for row in rows) > MAX_VERIFIED_BYTES):
        raise ValueError('unowned file inventory is ambiguous or oversized')
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


def _record_size(recorded_size):
    if not re.fullmatch(r'0|[1-9][0-9]*', recorded_size):
        raise ValueError('hashed installed RECORD entry requires a canonical byte count')
    size = int(recorded_size)
    if not 0 <= size <= MAX_PAYLOAD_BYTES:
        raise ValueError('installed payload exceeds its file byte bound')
    return size


def _verify_payload(path, recorded_hash, recorded_size):
    """Stream one bounded payload and bind its hash to stable path/file identity."""
    digest, expected = _record_hash(recorded_hash)
    size = _record_size(recorded_size)
    original = Path(path)
    physical = _resolve(original, strict=True)
    alias_identity = _file_identity(_path_status(original))
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
            or _resolve(original, strict=True) != physical
            or _file_identity(original.lstat()) != alias_identity):
        raise ValueError('installed payload changed during verification: ' + str(original))
    return {'path': str(original), 'physical': str(physical), 'identity': _file_identity(after),
            'alias_identity': alias_identity, 'bytes': total}


def _require_stable_payloads(captures):
    for capture in captures:
        for item in capture['payloads']:
            path, physical = Path(item['path']), Path(item['physical'])
            if (_resolve(path, strict=True) != physical or _file_identity(path.lstat()) != item['alias_identity']
                    or _file_identity(physical.lstat()) != item['identity']):
                raise ValueError('installed payload changed during environment census: ' + str(path))


def _capture_unowned_file(path):
    """Fresh bounded hash, including stable physical and alias identities."""
    physical = _resolve(path, strict=True)
    alias_identity = _file_identity(_path_status(path))
    descriptor = os.open(physical, os.O_RDONLY | os.O_NOFOLLOW)
    digest = hashlib.sha256()
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= MAX_PAYLOAD_BYTES:
            raise ValueError('unowned file is not regular or exceeds its byte bound: ' + str(path))
        total = 0
        while True:
            chunk = stream.read(min(PAYLOAD_CHUNK_BYTES, before.st_size - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > before.st_size:
                raise ValueError('unowned file grew during verification: ' + str(path))
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    if (total != before.st_size or _file_identity(before) != _file_identity(after)
            or _file_identity(after) != _file_identity(physical.lstat())
            or _resolve(path, strict=True) != physical
            or _file_identity(path.lstat()) != alias_identity):
        raise ValueError('unowned file changed during verification: ' + str(path))
    return {'path': str(path), 'physical': str(physical), 'identity': _file_identity(after),
            'alias_identity': alias_identity, 'bytes': total, 'sha256': digest.hexdigest()}


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


def _capture_distribution(distribution, *, verify_payloads=True, light=False):
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
    path = _resolve(distribution.locate_file(records[0]), strict=True)
    record_identity = _file_identity(_path_status(path))
    raw = read_regular(str(path), 'distribution_record', max_bytes=MAX_RECORD_BYTES).captured.raw
    if not raw:
        raise ValueError('distribution has empty installed RECORD: ' + name)
    direct_url = path.parent / 'direct_url.json'
    installation = None
    if _path_kind(direct_url, lambda mode: True):
        if light:
            # Metadata parsing still rejects editable installs, but light mode
            # hashes only the manifest and RECORD bytes, never other payloads.
            with direct_url.open('rb') as stream:
                installation = stream.read(1_000_001)
            if len(installation) > 1_000_000:
                raise ValueError('distribution direct URL exceeds its byte bound')
        else:
            installation = read_regular(str(direct_url), 'distribution_direct_url', max_bytes=1_000_000).captured.raw
        origin = c.strict_json(installation, 'distribution direct URL', 1_000_000)
        if type(origin) is not dict or type(origin.get('dir_info', {})) is not dict:
            raise ValueError('malformed distribution installation metadata: ' + name)
        if not own and origin.get('dir_info', {}).get('editable', False) is not False:
            raise ValueError('editable or development third-party distribution holds: ' + name)
    owned, spellings, payloads, unverified, claims = set(), set(), [], {}, []
    file_stats, stat_identities = {}, {}
    verified_bytes = verified_count = 0
    for row in csv.reader(io.StringIO(raw.decode('utf-8'), newline=''), strict=True):
        if len(row) != 3:
            raise ValueError('distribution has malformed installed RECORD: ' + name)
        entry = _record_name(row[0])
        # Lead addendum 08:26:25Z: imports may create/change caches outside
        # registered runs. Even a hashed or hashless RECORD cache contributes
        # neither an entry nor a count; RECORD itself remains byte-exact.
        if entry.endswith('.pyc'):
            continue
        if not own and (Path(entry).name.startswith('__editable__') or entry.endswith('.egg-link')):
            raise ValueError('editable or development third-party distribution holds: ' + name)
        target = _resolve(distribution.locate_file(row[0]), strict=False)
        if own:
            _own_record_entry(target, path)
        if target in owned:
            raise ValueError('distribution has duplicate installed RECORD paths: ' + name)
        owned.add(target)
        spellings.add(os.path.abspath(distribution.locate_file(row[0])))
        claims.append((str(target), row[1]))
        if len(owned) > MAX_IMPORT_ENTRIES:
            raise ValueError('distribution RECORD exceeds its entry count bound')
        original = Path(distribution.locate_file(entry))
        observed_stat, stat_identities[str(original)] = _lstat(original)
        file_stats[entry] = [observed_stat['type'], observed_stat['bytes']]
        if row[1]:
            # A generate call hashes each payload once. Its second capture
            # rereads metadata/RECORD and the final pass checks every original
            # file identity; no payload or metadata cache survives the call.
            if verify_payloads:
                payload = _verify_payload(distribution.locate_file(entry), row[1], row[2])
                payloads.append(payload)
                size = payload['bytes']
            else:
                _record_hash(row[1])
                size = _record_size(row[2])
                if light:
                    physical = _resolve(original, strict=True)
                    observed, identity = _lstat(physical)
                    if observed != {'type': stat.S_IFREG, 'bytes': size}:
                        raise ValueError('installed payload size or type differs from RECORD: ' + str(original))
                    stat_identities[str(physical)] = identity
            verified_count += 1
            verified_bytes += size
            if verified_bytes > MAX_VERIFIED_BYTES:
                raise ValueError('distribution payload exceeds its total byte bound')
        else:
            if row[2] and re.fullmatch(r'0|[1-9][0-9]*', row[2]) is None:
                raise ValueError('unhashed installed RECORD entry has a malformed size')
            kind = 'record' if target == path else 'bytecode' if entry.endswith('.pyo') else 'other'
            unverified.setdefault(kind, []).append(entry)
    if path not in owned:
        raise ValueError('distribution RECORD must identify itself: ' + name)
    if 'record' not in unverified:
        raise ValueError('distribution RECORD must name itself without a recursive hash: ' + name)
    if _file_identity(path.lstat()) != record_identity:
        raise ValueError('distribution RECORD changed during environment census: ' + name)
    stat_identities[str(path)] = record_identity
    return {'row': {'name': name, 'version': version, 'record_sha256': c.sha(raw),
                'verified_files': {'count': verified_count, 'bytes': verified_bytes},
                'file_stats': file_stats,
                'unverified_files': [{'kind': kind, 'count': len(entries), 'paths': sorted(entries)}
                                     for kind, entries in sorted(unverified.items())]},
            'record_path': str(path), 'metadata': tuple(message.items()),
            'owned': tuple(sorted(str(item) for item in owned)), 'owned_spellings': tuple(sorted(spellings)),
            'installation': installation,
            'payloads': payloads, 'claims': tuple(sorted(claims)), 'own_project': own,
            'stat_identities': stat_identities}


def _capture_environment(paths, *, verify_payloads=True, light=False):
    captures = []
    owners = {}
    total_files = total_bytes = 0
    for distribution in metadata.distributions(path=paths):
        captured = _capture_distribution(distribution, verify_payloads=verify_payloads, light=light)
        captures.append(captured)
        for path, declared_hash in captured['claims']:
            if path in owners and owners[path] != declared_hash:
                raise ValueError('ambiguous distribution RECORD ownership with different hashes: ' + path)
            owners[path] = declared_hash
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


def _metadata_snapshot(captures):
    return [{key: value for key, value in capture.items() if key != 'payloads'} for capture in captures]


def _import_paths():
    return list(dict.fromkeys(str(_resolve(p or os.getcwd(), strict=True))
                             for p in sys.path if _path_kind(p or os.getcwd(), lambda mode: True)))


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


def _require_owned_import_roots(paths, captures, *, light_unowned=None):
    """Inventory every unowned file within the explicitly declared scope.

    The lead's scope ruling excludes exact first-party and standard-library
    import roots. A separately listed site-packages root is never excluded by
    its stdlib ancestor. Nested actual roots are traversed separately, giving
    each file its deepest root. All .pyc files are excluded, whether or not
    they have a source file, standard cache tag or distribution RECORD entry.
    """
    actual = {Path(path) for path in paths}
    first_party, stdlib = _first_party_roots(), _stdlib_roots()
    exclusions = [{'root': str(root), 'reason': 'first_party_source_pins' if root in first_party
                   else 'standard_library_interpreter_identity'}
                  for root in sorted(actual & (first_party | stdlib))]
    exempt = {Path(item['root']) for item in exclusions}
    owned = _owned_files(captures)
    owned_spellings = {Path(path) for capture in captures for path in capture['owned_spellings']}
    snapshots, files, unowned, payloads = {}, {}, [], []
    count = 0
    pending = [(root, root) for root in sorted(actual - exempt)]
    while pending:
        root, directory = pending.pop()
        if not _path_kind(directory, stat.S_ISDIR):
            raise ValueError('unsupported archive or non-directory third-party import root: ' + str(directory))
        snapshots[directory] = _file_identity(_path_status(directory))
        # Shared-parent resolution also follows the independent 8acf20b47
        # optimization; leaf symlinks still receive strict resolution.
        physical_directory = _resolve(directory, strict=True)
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            # DirEntry can answer ordinary entries from the directory listing;
            # symlink following shares the census's separate stat observation.
            is_directory = (_path_kind(entry.path, stat.S_ISDIR)
                            if entry.is_symlink() else entry.is_dir())
            if not is_directory and entry.name.endswith('.pyc'):
                continue
            count += 1
            if count > MAX_IMPORT_ENTRIES:
                raise ValueError('third-party import ownership census exceeds its entry bound')
            path = Path(entry.path)
            if entry.name.endswith('.egg-link'):
                raise ValueError('editable or development import root holds: ' + str(path))
            if is_directory:
                if entry.is_symlink():
                    raise ValueError('unsupported symlinked third-party import directory: ' + str(path))
                if path not in actual:
                    pending.append((root, path))
            else:
                info = _path_status(path)
                physical = (_resolve(path, strict=True) if stat.S_ISLNK(info.st_mode)
                            else physical_directory / entry.name)
                if not _path_kind(path, stat.S_ISREG):
                    raise ValueError('unsupported non-regular import-root file: ' + str(path))
                files[path] = (root, physical)
    total_bytes = sum(capture['row']['verified_files']['bytes'] for capture in captures)
    for path, (root, physical) in sorted(files.items()):
        # A newly added symlink to an owned payload is itself an unowned path:
        # treating its target's ownership as its own would hide new imports.
        if physical in owned and (not stat.S_ISLNK(_path_status(path).st_mode) or path in owned_spellings):
            continue
        if light_unowned is None:
            captured = _capture_unowned_file(path)
        else:
            expected = light_unowned.get((str(root), path.relative_to(root).as_posix()))
            if expected is None:
                raise ValueError('environment manifest is stale: unowned file inventory differs')
            observed, identity = _lstat(physical)
            alias, alias_identity = _lstat(path)
            if (observed != {'type': stat.S_IFREG, 'bytes': expected['bytes']}
                    or alias != expected['stat']):
                raise ValueError('environment manifest is stale: unowned file lstat size or type differs')
            captured = {'path': str(path), 'physical': str(physical), 'identity': identity,
                        'alias_identity': alias_identity, 'bytes': observed['bytes'],
                        'sha256': expected['sha256']}
        payloads.append(captured)
        total_bytes += captured['bytes']
        if total_bytes > MAX_VERIFIED_BYTES:
            raise ValueError('unowned inventory exceeds its aggregate byte bound')
        unowned.append({'root': str(root), 'path': path.relative_to(root).as_posix(),
                        'bytes': captured['bytes'], 'sha256': captured['sha256'],
                        'stat': _lstat(path)[0]})
    _require_stable_directories(snapshots)
    return {'directories': snapshots, 'payloads': payloads,
            'unowned_files': sorted(unowned, key=lambda item: (item['root'], item['path'])),
            'excluded_roots': exclusions}


def generate():
    return _run_census(_generate)


def _generate():
    """Regenerate semantic identity and verify each installed hashed payload.

    Do not narrow this to packages already imported: registered helpers may
    import another installed distribution after registration. Missing metadata,
    duplicate normalized names and non-file RECORDs are refusal conditions.
    """
    try:
        paths = _import_paths()
        identity = _interpreter_identity()
        captures = _capture_environment(paths)
        census = _require_owned_import_roots(paths, captures)
        # The census may be long. Re-discover the roster, metadata and RECORDs,
        # then recheck every freshly hashed payload identity. Only this call's
        # initial full content verification is reused, never a previous call.
        _census_resolver.get().begin_second_capture()
        if (_import_paths() != paths or _interpreter_identity() != identity
                or _metadata_snapshot(_capture_environment(paths, verify_payloads=False)) != _metadata_snapshot(captures)):
            raise ValueError('interpreter, distribution metadata or payload changed during environment census')
        _require_stable_directories(census['directories'])
        _require_stable_payloads([*captures, census])
        value = {'kind': KIND, 'version': VERSION, 'interpreter': identity,
                 'distributions': [capture['row'] for capture in captures if not capture['own_project']],
                 'unowned_files': census['unowned_files'], 'excluded_roots': census['excluded_roots']}
        result = validate(value)
        holder = _generation_capture.get()
        if holder is not None:
            holder.append(tuple(sorted(_fingerprints(captures, census).items())))
        return result
    except (OSError, UnicodeError, TypeError, AttributeError, csv.Error) as exc:
        raise ValueError('environment metadata is missing, ambiguous or unreadable') from exc


def _light_live(value):
    return _run_census(_light_census, value)


def _light_census(value):
    """Re-read RECORD hashes and lstat the complete included inventory.

    Same-size payload edits are intentionally outside this mode's guarantee.
    Full mode owns payload hashing; no light result becomes a full result.
    """
    try:
        paths, identity = _import_paths(), _interpreter_identity()
        captures = _capture_environment(paths, verify_payloads=False, light=True)
        expected = {(row['root'], row['path']): row for row in value['unowned_files']}
        census = _require_owned_import_roots(paths, captures, light_unowned=expected)
        current = {'kind': KIND, 'version': VERSION, 'interpreter': identity,
                   'distributions': [row['row'] for row in captures if not row['own_project']],
                   'unowned_files': census['unowned_files'], 'excluded_roots': census['excluded_roots']}
        if (_import_paths() != paths or _interpreter_identity() != identity
                or c.canonical(current) != c.canonical(value)):
            raise ValueError('environment manifest is stale for the current interpreter environment')
        _require_stable_directories(census['directories'])
        _require_stable_payloads([census])
        fingerprints = _fingerprints(captures, census)
        # Stat identities are only a process-local full-cache invalidation key,
        # never serialized as environment authority or used to hash payloads.
        for path, expected_stat in fingerprints.items():
            # Deliberate final second look, never served by the census cache.
            if _lstat(path, fresh=True)[1] != expected_stat:
                raise ValueError('installed metadata or payload changed during environment census (light)')
        return tuple(sorted(fingerprints.items()))
    except (OSError, UnicodeError, TypeError, AttributeError, csv.Error) as exc:
        raise ValueError('environment metadata or payload is missing, ambiguous or unreadable') from exc


def _verification_key(pin):
    implementation = read_regular(str(Path(__file__).resolve(strict=True)),
        'environment_manifest_implementation', max_bytes=MAX_BYTES).captured
    if implementation.pin.sha256 != _IMPLEMENTATION_SHA256:
        raise ValueError('environment manifest implementation changed since loading')
    executable = Path(sys.executable).resolve(strict=True)
    return (_IMPLEMENTATION_SHA256, str(ROOT), tuple(sorted(pin.items())), c.canonical(_interpreter_identity()),
            str(executable), _file_identity(executable.lstat()), sys.prefix, sys.base_prefix,
            tuple(_import_paths()))


def verify(pin, *, mode='full'):
    """Check current pin bytes, then full regeneration or explicit light census.

    A full result is reused only in this process for the same pin/interpreter.
    Every reuse still performs the light live census and checks the original
    full result's file identities; a changed payload refuses without rehashing.
    Prepared mode requires that baseline and never regenerates after capture.
    """
    if mode not in ('full', 'light', 'prepared'):
        raise ValueError('unknown environment verification mode')
    c.file_pin(pin, 'environment manifest pin')
    captured = read_regular(pin['path'], 'environment_manifest', max_bytes=MAX_BYTES).captured
    if {'path': captured.pin.path, 'bytes': captured.pin.bytes,
            'sha256': captured.pin.sha256} != pin:
        raise ValueError('environment manifest differs from its registered pin')
    value = validate(c.strict_json(captured.raw, 'environment manifest', MAX_BYTES))
    if captured.raw != c.canonical(value):
        raise ValueError('environment manifest must use canonical bytes')
    if mode == 'light':
        _light_live(value)
        return value
    state = _process_state()
    key = _verification_key(pin)
    with state['lock']:
        memo = state['full'].get(key)
        if memo is None:
            if mode == 'prepared':
                raise ValueError('prepared environment verification requires a process full baseline')
            if len(state['full']) >= 64:
                raise ValueError('process environment verification pin bound exceeded')
            # Store refusals too: fixing a failed environment requires a new
            # process or pin, not repeated expensive regeneration of this key.
            try:
                fingerprints = _light_live(value)
                if captured.raw != c.canonical(generate()):
                    raise ValueError('environment manifest is stale for the current interpreter environment')
                if _light_live(value) != fingerprints:
                    raise ValueError('installed payload changed during process full verification')
            except ValueError as exc:
                state['full'][key] = (str(exc), None)
                raise
            state['full'][key] = (None, fingerprints)
        else:
            error, fingerprints = memo
            if error is not None:
                raise ValueError(error)
            if _light_live(value) != fingerprints:
                raise ValueError('environment manifest is stale: installed payload changed since process full verification')
    return value


def write(path):
    """Create one manifest without overwriting an existing file, returning its pin."""
    path = c.canonical_path(str(path), 'environment manifest path')
    if str(Path(path).parent.resolve(strict=True) / Path(path).name) != path:
        raise ValueError('environment manifest parent must be its physical path')
    fingerprints = []
    token = _generation_capture.set(fingerprints)
    try:
        value = generate()
    finally:
        _generation_capture.reset(token)
    raw = c.canonical(value)
    if len(fingerprints) != 1 or _light_live(value) != fingerprints[0]:
        raise ValueError('installed payload changed during manifest generation')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    pin = {'path': path, 'bytes': len(raw), 'sha256': c.sha(raw)}
    state = _process_state()
    with state['lock']:
        key = _verification_key(pin)
        if len(state['full']) >= 64 and key not in state['full']:
            raise ValueError('process environment verification pin bound exceeded')
        if key not in state['full']:
            state['full'][key] = (None, fingerprints[0])
        # Re-read the persisted pin and recheck the live census after publication.
        verify(pin, mode='full')
    return pin
