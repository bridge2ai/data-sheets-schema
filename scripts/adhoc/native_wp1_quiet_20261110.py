"""WP1 owned quiet-window capability, 2026-11-10 (5757/5760).

Inputs: trusted role scripts/source identities, one physical exclusive lock and
an inherited readonly witness FD. Outputs: immutable lease/witness evidence and
an explicit release/retain result. This module performs no work at import time.
It does not qualify the host, launch processes, change an inherited runner or
grant a timing/production acceptance. Callers own those separately bounded steps.
"""
from __future__ import annotations

from datetime import datetime, timezone
import ctypes
import errno
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import time


ROLES = ('outer', 'supervised', 'driver', 'worker', 'child-check')
_FLAGS = {'supervised': '--supervised', 'driver': '--driver',
          'worker': '--worker', 'child-check': '--child-check'}
_MAX = 32768


class LeaseLost(RuntimeError):
    """A previously claimed lease cannot be authenticated; never resume it."""


class LeaseBusy(LeaseLost):
    """An existing lock, including a stale or symlink lock, is not ours."""


def _raw(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _path(value):
    value = Path(value)
    if (not value.is_absolute() or value.name in {'', '.', '..'}
            or value.parent.resolve(strict=True) != value.parent):
        raise LeaseLost('physical absolute parent required: ' + str(value))
    return value


def _output(value):
    value = _path(value)
    if os.path.lexists(value) and (value.resolve(strict=True) != value or not value.is_dir()):
        raise LeaseLost('quiet output must be an absent leaf or a physical directory')
    return value


def _regular(info):
    if not stat.S_ISREG(info.st_mode):
        raise LeaseLost('lease and witness must be regular files')
    return (info.st_dev, info.st_ino)


def _identity(info):
    dev, ino = _regular(info)
    return {'device': dev, 'inode': ino}


def _read_fd(fd):
    info = os.fstat(fd)
    _regular(info)
    if info.st_size <= 0 or info.st_size > _MAX:
        raise LeaseLost('empty or oversized quiet capability')
    raw = os.pread(fd, _MAX + 1, 0)
    if len(raw) != info.st_size or len(raw) > _MAX:
        raise LeaseLost('quiet capability changed during read')
    value = json.loads(raw)
    if _raw(value) != raw:
        raise LeaseLost('quiet capability must have canonical, duplicate-free JSON')
    return raw, value, info


def _open_read(path):
    # A raced FIFO must refuse rather than block at open. _read_fd checks the
    # descriptor's regular-file type before pread, independently of path checks.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        raw, value, info = _read_fd(fd)
        if _regular(os.lstat(path)) != _regular(info):
            raise LeaseLost('quiet capability path changed during read')
        return raw, value, info
    finally:
        os.close(fd)


def _scripts(value):
    if set(value) != set(ROLES):
        raise LeaseLost('exact five-role script map required')
    result = {}
    for role, filename in value.items():
        path = _path(filename)
        if path.resolve(strict=True) != path or not path.is_file():
            raise LeaseLost('role script is not a physical regular file')
        result[role] = str(path)
    return result


def _script_hashes(scripts):
    return {path: _sha(Path(path).read_bytes()) for path in sorted(set(scripts.values()))}


def _hex(value, length, name):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{' + str(length) + '}', value):
        raise LeaseLost(name + ' must be a full lowercase hexadecimal identity')
    return value


def _process(process, role, scripts, output, executable):
    """Read actual executable/argv; never infer role or output from env text."""
    if not process.is_running() or process.status() in {'zombie', 'dead'}:
        raise LeaseLost('quiet role process is not live: ' + role)
    argv = process.cmdline()
    target = scripts[role]
    if not argv or argv.count(target) != 1:
        raise LeaseLost('live ' + role + ' script differs')
    position = argv.index(target)
    if position < 1 or any(arg not in {'-I', '-S', '-P', '-B', '-u', '-s'}
                           for arg in argv[1:position]):
        raise LeaseLost('unexpected interpreter entry for ' + role)
    if str(Path(process.exe()).resolve(strict=True)) != executable:
        raise LeaseLost('live ' + role + ' interpreter differs')
    tail = argv[position + 1:]
    flags = {name: tail.count(flag) for name, flag in _FLAGS.items()}
    if role == 'outer':
        valid_flags = not any(flags.values())
    elif role == 'driver':
        valid_flags = flags['driver'] <= 1 and not any(
            count for name, count in flags.items() if name != 'driver')
    else:
        valid_flags = flags[role] == 1 and not any(
            count for name, count in flags.items() if name != role)
    if not valid_flags:
        raise LeaseLost('live role flags differ for ' + role)
    # Outer may use --out for a fixture campaign root. Production outer uses
    # kind/label. Child-check has no output argument: its output comes from FD.
    if role != 'outer':
        count = tail.count('--out')
        if count > 1 or (role in {'driver', 'worker'} and count != 1):
            raise LeaseLost('live ' + role + ' output argument differs')
        if count:
            index = tail.index('--out')
            if index + 1 >= len(tail) or tail[index + 1] != str(output):
                raise LeaseLost('live ' + role + ' output differs from the witness')
    created = process.create_time()
    if not math.isfinite(created):
        raise LeaseLost('invalid live process creation time')
    return {'role': role, 'pid': process.pid, 'ppid': process.ppid(),
            'created': created, 'sid': os.getsid(process.pid),
            'pgid': os.getpgid(process.pid), 'script': target,
            'executable': executable, 'argv_sha256': _sha(_raw(argv))}


def refuse_existing(lock_path):
    """Canary and acquisition refuse every existing leaf without altering it."""
    path = _path(lock_path)
    if os.path.lexists(path):
        raise LeaseBusy('quiet lock already exists: ' + str(path))


class LeaseReader:
    def __init__(self, witness_fd, *, role, expected_lock, expected_manifest_sha256,
                 expected_source_commit, role_scripts, psutil_module):
        self.witness_fd = witness_fd
        self.failure_reason = None
        self._role = role
        self._lock = _path(expected_lock)
        self._manifest = _hex(expected_manifest_sha256, 64, 'manifest')
        self._source = _hex(expected_source_commit, 40, 'source commit')
        self._scripts = _scripts(role_scripts)
        self._psutil = psutil_module
        self._snapshots = []
        self._raw_witness = None
        self._witness_identity = None
        self._record = None
        self.output = None
        self._witness_path = None
        self.validate()

    def _validate(self):
        _path(self._lock)
        _scripts(self._scripts)
        if self._role not in ROLES or type(self.witness_fd) is not int or self.witness_fd < 3:
            raise LeaseLost('valid quiet role and inherited witness FD required')
        if fcntl.fcntl(self.witness_fd, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDONLY:
            raise LeaseLost('quiet witness descriptor must be readonly')
        raw, witness, descriptor_info = _read_fd(self.witness_fd)
        expected = {'kind', 'version', 'lock_path', 'lock_identity', 'lock_sha256',
                    'witness_path', 'nonce', 'output', 'manifest_sha256', 'source_commit'}
        if (set(witness) != expected or witness['kind'] != 'native_wp1_quiet_witness'
                or type(witness['version']) is not int or witness['version'] != 1):
            raise LeaseLost('closed quiet witness required')
        witness_path = _path(witness['witness_path'])
        if witness_path.resolve(strict=True) != witness_path:
            raise LeaseLost('quiet witness is an alias')
        if _regular(os.lstat(witness_path)) != _regular(descriptor_info):
            raise LeaseLost('quiet witness descriptor no longer names its original file')
        output = _output(witness['output'])
        if witness_path != output.parent / (output.name + '.quiet-witness.json'):
            raise LeaseLost('quiet witness/output binding differs')
        if (witness['lock_path'] != str(self._lock)
                or witness['manifest_sha256'] != self._manifest
                or witness['source_commit'] != self._source):
            raise LeaseLost('quiet witness authority differs from trusted caller')
        if self._raw_witness is not None and (raw != self._raw_witness
                or _identity(descriptor_info) != self._witness_identity):
            raise LeaseLost('quiet witness changed after admission')
        lock_raw, record, lock_info = _open_read(self._lock)
        if (_identity(lock_info) != witness['lock_identity']
                or _sha(lock_raw) != witness['lock_sha256']):
            raise LeaseLost('quiet lock bytes or inode changed')
        record_keys = {'kind', 'version', 'nonce', 'owner', 'output',
                       'manifest_sha256', 'source_commit', 'role_scripts',
                       'role_script_sha256', 'witness_path', 'witness_identity',
                       'started_utc', 'expected_end_utc', 'started_monotonic',
                       'expected_end_monotonic', 'qualification_seconds', 'arm_seconds'}
        if (set(record) != record_keys or record['kind'] != 'native_wp1_quiet_lease'
                or type(record['version']) is not int or record['version'] != 1):
            raise LeaseLost('closed quiet lease required')
        _hex(record['nonce'], 64, 'lease nonce')
        if (record['nonce'] != witness['nonce'] or record['output'] != str(output)
                or record['manifest_sha256'] != self._manifest or record['source_commit'] != self._source
                or record['witness_path'] != str(witness_path)
                or record['witness_identity'] != _identity(descriptor_info)
                or record['role_scripts'] != self._scripts
                or record['role_script_sha256'] != _script_hashes(self._scripts)):
            raise LeaseLost('quiet lease binding or script bytes differ')
        qualification, arm = record['qualification_seconds'], record['arm_seconds']
        if (type(qualification) is not int or not 0 < qualification <= 150
                or type(arm) is not int or not 0 < arm <= 900):
            raise LeaseLost('quiet lease budgets are not bounded')
        start = record['started_monotonic']
        end = record['expected_end_monotonic']
        start_utc = datetime.fromisoformat(record['started_utc'])
        end_utc = datetime.fromisoformat(record['expected_end_utc'])
        if (type(start) not in (int, float) or type(end) not in (int, float)
                or not math.isfinite(start) or not math.isfinite(end)
                or abs(end - start - qualification - arm) > 0.000001
                or start_utc.tzinfo is None or end_utc.tzinfo is None
                or abs((end_utc - start_utc).total_seconds() - qualification - arm) > 0.000001
                or not start <= time.monotonic() <= end
                or datetime.now(timezone.utc) > end_utc):
            raise LeaseLost('quiet lease time bound is invalid or expired')
        owner = record['owner']
        if not isinstance(owner, dict) or owner.get('role') != 'outer':
            raise LeaseLost('quiet owner identity is invalid')
        process = self._psutil.Process(os.getpid())
        snapshots = []
        for index in range(ROLES.index(self._role), -1, -1):
            snapshot = _process(process, ROLES[index], self._scripts, output, owner['executable'])
            snapshots.append(snapshot)
            if index:
                process = self._psutil.Process(snapshot['ppid'])
        snapshots.reverse()
        if snapshots[0] != owner:
            raise LeaseLost('live outer PID, creation time or command identity differs')
        for index, snapshot in enumerate(snapshots[1:], 1):
            if snapshot['ppid'] != snapshots[index - 1]['pid']:
                raise LeaseLost('quiet process ancestry differs')
            if index in (1, 3):
                if snapshot['sid'] != snapshot['pid'] or snapshot['pgid'] != snapshot['pid']:
                    raise LeaseLost('expected new session at ' + snapshot['role'])
            elif (snapshot['sid'] != snapshots[index - 1]['sid']
                  or snapshot['pgid'] != snapshots[index - 1]['pgid']):
                raise LeaseLost('unexpected session change at ' + snapshot['role'])
        self._raw_witness = raw
        self._witness_identity = _identity(descriptor_info)
        self._record = record
        self.output = output
        self._witness_path = witness_path
        self._snapshots = snapshots

    def validate(self):
        if self.failure_reason is not None:
            raise LeaseLost(self.failure_reason)
        try:
            self._validate()
        except Exception as exc:
            self.failure_reason = type(exc).__name__ + ': ' + str(exc)
            raise LeaseLost(self.failure_reason) from exc
        return self

    def environment(self):
        self.validate()
        return {'U3WP1_LEASE_FD': str(self.witness_fd), 'U3WP1_OUTPUT': str(self.output)}

    def witness(self):
        return {'role': self._role, 'lock_path': str(self._lock),
                'witness_path': None if self._witness_path is None else str(self._witness_path),
                'witness_sha256': None if self._raw_witness is None else _sha(self._raw_witness),
                'output': None if self.output is None else str(self.output),
                'failure_reason': self.failure_reason,
                'processes': [dict(row) for row in self._snapshots]}

    def lock_view(self):
        return LockView(self)

    def os_proxy(self):
        return OsProxy(self)


class LockView(os.PathLike):
    def __init__(self, reader):
        self.reader = reader

    def __fspath__(self):
        return str(self.reader._lock)

    def __str__(self):
        return os.fspath(self)

    def exists(self):
        self.reader.validate()
        return False

    def lexists(self):
        self.reader.validate()
        return False


class _PathProxy:
    def __init__(self, reader):
        self.reader = reader

    def lexists(self, path):
        if os.fspath(path) == str(self.reader._lock):
            self.reader.validate()
            return False
        return os.path.lexists(path)

    def __getattr__(self, name):
        return getattr(os.path, name)


class OsProxy:
    """Private module proxy; never monkeypatch the process-global os module."""
    def __init__(self, reader):
        self.path = _PathProxy(reader)

    def __getattr__(self, name):
        return getattr(os, name)


def _rename_exclusive(source, destination):
    """Darwin atomic rename without replacing a destination; no unlink fallback.

    RENAME_EXCL=0x4 and renamex_np are declared in the installed SDK's
    usr/include/sys/stdio.h. Both paths have physical parents; symlink leaves
    are moved as symlinks, never followed. This is not a conditional-inode CAS.
    """
    source, destination = _path(source), _path(destination)
    if sys.platform != 'darwin':
        raise LeaseLost('quiet release requires Darwin exclusive rename')
    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    rename = library.renamex_np
    rename.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
    rename.restype = ctypes.c_int
    if rename(os.fsencode(source), os.fsencode(destination), 0x00000004) != 0:
        number = ctypes.get_errno() or errno.EIO
        raise OSError(number, os.strerror(number) + '; destination=' + str(destination), str(source))


def _capture_lock(lock_path, candidate_path):
    """Single fixture injection boundary after validation, before atomic capture."""
    _rename_exclusive(lock_path, candidate_path)


class OwnerLease(LeaseReader):
    def __init__(self, *args, lock_fd, **kwargs):
        self._lock_fd = lock_fd
        self._closed = False
        super().__init__(*args, role='outer', **kwargs)

    def _close(self):
        if not self._closed:
            os.close(self.witness_fd)
            os.close(self._lock_fd)
            self._closed = True

    def retain(self, reason='unknown_cleanup'):
        self._close()
        return {'released': False, 'retained': True, 'reason': reason,
                'lock_path': str(self._lock), 'witness_path': str(self._witness_path)}

    def release(self, cleanup_verified):
        if cleanup_verified is not True:
            return self.retain('cleanup_not_verified')
        result = {'released': False, 'retained': True, 'reason': None,
                  'lock_path': str(self._lock), 'witness_path': str(self._witness_path),
                  'quarantine_path': None, 'captured_path': None, 'recovery_path': str(self._lock),
                  'foreign_restored': False, 'canonical_already_occupied': False,
                  'canonical_continuity_established': False,
                  'scope': 'Cooperative local coordination only. Atomic capture may briefly vacate '
                           'the canonical path; displaced objects are preserved, never unlinked. '
                           'No hostile same-user pathname-security guarantee is claimed.'}
        try:
            self.validate()
            raw, _, info = _read_fd(self._lock_fd)
            witness = json.loads(self._raw_witness)
            if (_identity(info) != witness['lock_identity'] or _sha(raw) != witness['lock_sha256']
                    or _regular(os.lstat(self._lock)) != _regular(info)):
                raise LeaseLost('owned lock changed immediately before release')
            quarantine = _path(self._witness_path.with_name(
                self._witness_path.name + '.release-' + witness['nonce'][:16]))
            quarantine.mkdir(mode=0o700)  # Exclusive fresh directory; never reuse or clean it.
            candidate = quarantine / 'captured-lock'
            result.update(quarantine_path=str(quarantine), captured_path=str(candidate))
            if stat.S_IMODE(quarantine.stat().st_mode) != 0o700:
                raise LeaseLost('release evidence directory is not private')
            _capture_lock(self._lock, candidate)
            result['recovery_path'] = str(candidate)
            matching = False
            try:
                _regular(os.lstat(candidate))
                captured_raw, _, captured_info = _open_read(candidate)
                matching = (_identity(captured_info) == witness['lock_identity']
                            and _sha(captured_raw) == witness['lock_sha256'])
            except Exception as exc:
                # A raced foreign file need not contain JSON or be regular. Its
                # captured object is preserved and the exclusive restore still runs.
                result['capture_inspection_error'] = type(exc).__name__ + ': ' + str(exc)
            if matching:
                result.update(released=True, retained=False,
                    reason='cleanup_verified_owned_lock_archived')
            else:
                self.failure_reason = 'foreign object captured during quiet release'
                result['reason'] = self.failure_reason
                try:
                    _rename_exclusive(candidate, self._lock)
                    result.update(foreign_restored=True, recovery_path=str(self._lock),
                        reason='foreign_capture_restored_exclusively')
                except FileExistsError:
                    result.update(canonical_already_occupied=True,
                        reason='foreign_capture_preserved_canonical_already_occupied')
                except Exception as exc:
                    result['reason'] = 'foreign_capture_preserved_restore_failed'
                    result['restore_error'] = type(exc).__name__ + ': ' + str(exc)
        except Exception as exc:
            if self.failure_reason is None:
                self.failure_reason = type(exc).__name__ + ': ' + str(exc)
            result['reason'] = self.failure_reason
        finally:
            self._close()
        return result


def read_lease(witness_fd, *, role, expected_lock, expected_manifest_sha256,
               expected_source_commit, role_scripts, psutil_module):
    return LeaseReader(witness_fd, role=role, expected_lock=expected_lock,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_source_commit=expected_source_commit, role_scripts=role_scripts,
        psutil_module=psutil_module)


def acquire(lock_path, output, *, manifest_sha256, source_commit,
            qualification_seconds, arm_seconds=900, role_scripts, psutil_module):
    """Acquire before qualification. Never repair/remove a pre-existing lock."""
    lock_path, output = _path(lock_path), _output(output)
    refuse_existing(lock_path)
    scripts = _scripts(role_scripts)
    _hex(manifest_sha256, 64, 'manifest')
    _hex(source_commit, 40, 'source commit')
    if (type(qualification_seconds) is not int or not 0 < qualification_seconds <= 150
            or type(arm_seconds) is not int or not 0 < arm_seconds <= 900):
        raise LeaseLost('positive bounded qualification/arm budgets required')
    witness_path = output.parent / (output.name + '.quiet-witness.json')
    if (lock_path == witness_path or lock_path == output
            or lock_path.is_relative_to(output) or witness_path.is_relative_to(output)):
        raise LeaseLost('lock and witness must remain outside test output')
    if os.path.lexists(witness_path):
        raise LeaseBusy('quiet witness output already exists')
    executable = str(Path(sys.executable).resolve(strict=True))
    owner = _process(psutil_module.Process(os.getpid()), 'outer', scripts, output, executable)
    scripts_sha = _script_hashes(scripts)
    # Exclusive creation, O_NOFOLLOW and retained inode identities. An I/O failure
    # after creation retains artifacts for inspection; it never removes a lock
    # that another actor may have replaced while acquisition was incomplete.
    try:
        lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError as exc:
        raise LeaseBusy('quiet lock was acquired concurrently') from exc
    writable_witness = readonly_witness = None
    try:
        start_mono = time.monotonic()
        start_epoch = time.time()
        span = qualification_seconds + arm_seconds
        writable_witness = os.open(witness_path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        nonce = secrets.token_hex(32)
        record = {'kind': 'native_wp1_quiet_lease', 'version': 1, 'nonce': nonce,
            'owner': owner, 'output': str(output), 'manifest_sha256': manifest_sha256,
            'source_commit': source_commit, 'role_scripts': scripts,
            'role_script_sha256': scripts_sha, 'witness_path': str(witness_path),
            'witness_identity': _identity(os.fstat(writable_witness)),
            'started_utc': datetime.fromtimestamp(start_epoch, timezone.utc).isoformat(),
            'expected_end_utc': datetime.fromtimestamp(start_epoch + span, timezone.utc).isoformat(),
            'started_monotonic': start_mono, 'expected_end_monotonic': start_mono + span,
            'qualification_seconds': qualification_seconds, 'arm_seconds': arm_seconds}
        raw = _raw(record)
        if os.write(lock_fd, raw) != len(raw):
            raise LeaseLost('quiet lease write was incomplete')
        os.fsync(lock_fd)
        witness = {'kind': 'native_wp1_quiet_witness', 'version': 1,
            'lock_path': str(lock_path), 'lock_identity': _identity(os.fstat(lock_fd)),
            'lock_sha256': _sha(raw), 'witness_path': str(witness_path), 'nonce': nonce,
            'output': str(output), 'manifest_sha256': manifest_sha256, 'source_commit': source_commit}
        witness_raw = _raw(witness)
        if os.write(writable_witness, witness_raw) != len(witness_raw):
            raise LeaseLost('quiet witness write was incomplete')
        os.fsync(writable_witness)
        os.fchmod(writable_witness, 0o400)
        readonly_witness = os.open(witness_path, os.O_RDONLY | os.O_NOFOLLOW)
        os.close(writable_witness)
        writable_witness = None
        return OwnerLease(readonly_witness, lock_fd=lock_fd, expected_lock=lock_path,
            expected_manifest_sha256=manifest_sha256, expected_source_commit=source_commit,
            role_scripts=scripts, psutil_module=psutil_module)
    except BaseException:
        for fd in (writable_witness, readonly_witness, lock_fd):
            if fd is not None:
                os.close(fd)
        raise
