"""Bounded one-use file rendezvous for a prepared launch process.

Records carry identities, never admission verdicts. The launch worker owns
fresh verification and dispatch. This module never creates an attempt path.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import secrets
import time

from . import native_subscription_guard as wire

LIMIT = 64 * 1024
POLL_SECONDS = 0.1


class PreparedIdentity:
    """Invocation-local comparison bytes; every resume freshly checks live inputs.

    Construction follows full registration and classifier verification. This
    object grants no admission and is never serialized as a reusable verdict.
    """

    def __init__(self, registration_raw, value, authorization):
        from . import native_execution_authority_v2 as authority
        from . import native_shared_registration_orchestration as registration
        from .native_shared_controller import captured_preparation_body
        if wire.canonical(registration.verified(registration_raw)) != wire.canonical(value):
            raise ValueError('prepared worker requires freshly verified registration')
        self.registration_raw = registration_raw
        self.value_raw = wire.canonical(value)
        self.inputs = tuple((path, authorization['raw'][name])
                            for name, path in authorization['inputs'].items())
        dependencies = value['dependencies']
        self.source_sha256 = wire.sha(wire.canonical(dependencies))
        preparation = captured_preparation_body(value['preparation_raw_json'].encode())
        self.environment_sha256 = preparation['environment_manifest']['sha256']
        paths = dict(dependencies['base']['package_sources'])
        paths.update((pin['path'], pin['sha256'])
                     for pin in dependencies['base']['modules'].values())
        paths.update((pin['path'], pin['sha256'])
                     for pin in dependencies['additional_modules'].values())
        self.sources = tuple((authority.ROOT / path, digest)
                             for path, digest in sorted(paths.items()))

    def recheck(self):
        from . import native_execution_authority_v2 as authority
        from . import native_shared_registration_orchestration as registration
        for path, digest in self.sources:
            try:
                authority._verified_source_bytes(path, digest)
            except (OSError, ValueError) as exc:
                raise ValueError('prepared worker source bytes changed') from exc
        for path, raw in self.inputs:
            if wire.read_regular(path, limit=32 * 1024 * 1024) != raw:
                raise ValueError('prepared worker authority bytes changed')
        # This reconstructs the live dependency identity (including Git HEAD,
        # package roster/pins and interpreter), checks committed source blobs,
        # all preparation/composition pins and runtime, and runs a light census.
        value = registration._recheck_verified(self.registration_raw,
            wire.strict_json(self.value_raw), environment_mode='light')
        if wire.canonical(value) != self.value_raw:
            raise ValueError('prepared worker registration changed')
        return value


def checked_value(identity, registration_raw):
    if type(identity) is not PreparedIdentity or identity.registration_raw != registration_raw:
        raise ValueError('prepared registration differs from capture authority')
    return identity.recheck()


def exchange(directory, *, identity, attempt, max_age_seconds):
    """Publish readiness only after preparation; return the one-use guard pin."""
    raw = publish_prepared(directory, registration_raw=identity.registration_raw,
        attempt=attempt, max_age_seconds=max_age_seconds,
        source_sha256=identity.source_sha256,
        environment_sha256=identity.environment_sha256)
    result = wait_proceed(directory, prepared_raw=raw,
        registration_raw=identity.registration_raw, attempt=attempt,
        max_age_seconds=max_age_seconds)
    checked_value(identity, identity.registration_raw)
    return result


def _directory(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path or not path.is_dir():
        raise ValueError('worker IPC directory must be canonical and resolved')
    return path


def _hash(value):
    if (type(value) is not str or len(value) != 64
            or any(char not in '0123456789abcdef' for char in value)):
        raise ValueError('worker identity requires a lowercase SHA256')
    return value


def _duration(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError('worker wait limit must be positive and finite')
    return value


def _publish(directory, name, value):
    """Publish complete bytes atomically, retaining the exclusive staging file.

    A racing reader cannot see a half-written JSON record. Both names are
    one-use; a crash during staging spends this rendezvous rather than retries.
    """
    raw = wire.canonical(value)
    if len(raw) > LIMIT:
        raise ValueError('worker record exceeds its byte bound')
    stage = directory / (name + '.staging')
    fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(stage, directory / name, follow_symlinks=False)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return raw


def _read(directory, name):
    raw = wire.read_regular(directory / name, limit=LIMIT)
    value = wire.strict_json(raw)
    if type(value) is not dict or wire.canonical(value) != raw:
        raise ValueError('worker record must be a canonical object')
    return raw, value


def _binding(registration_raw, attempt):
    attempt = Path(attempt)
    if (not attempt.is_absolute() or attempt.parent.resolve(strict=True) != attempt.parent
            or attempt.is_symlink()):
        raise ValueError('worker attempt must be canonical')
    if type(registration_raw) is not bytes or not registration_raw:
        raise ValueError('worker requires exact registration bytes')
    return {'registration_sha256': wire.sha(registration_raw), 'attempt_path': str(attempt)}


def _prepared(directory, registration_raw, attempt, max_age_seconds, now):
    raw, value = _read(directory, 'prepared.json')
    binding = _binding(registration_raw, attempt)
    keys = {*binding, 'kind', 'version', 'pid', 'nonce', 'prepared_at',
            'source_sha256', 'environment_sha256', 'max_age_seconds'}
    if (set(value) != keys or value['kind'] != 'd4d_native_prepared_worker'
            or type(value['version']) is not int or value['version'] != 1
            or any(value[key] != item for key, item in binding.items())
            or type(value['pid']) is not int or value['pid'] <= 0
            or type(value['nonce']) is not str or len(value['nonce']) != 64
            or type(value['prepared_at']) not in (int, float)
            or not math.isfinite(value['prepared_at'])
            or value['max_age_seconds'] != _duration(max_age_seconds)
            or not 0 <= now - value['prepared_at'] < max_age_seconds):
        raise ValueError('stale or foreign prepared worker record')
    for key in ('nonce', 'source_sha256', 'environment_sha256'):
        _hash(value[key])
    return raw, value


def publish_prepared(directory, *, registration_raw, attempt, source_sha256,
                     environment_sha256, max_age_seconds):
    directory = _directory(directory)
    from .native_path_identity import overlaps
    if overlaps(directory, Path(attempt)):
        raise ValueError('worker IPC overlaps the registered attempt')
    if os.path.lexists(attempt):
        raise ValueError('prepared worker requires an unspent attempt')
    value = {**_binding(registration_raw, attempt),
        'kind': 'd4d_native_prepared_worker', 'version': 1, 'pid': os.getpid(),
        'nonce': secrets.token_hex(32), 'prepared_at': time.time(),
        'source_sha256': _hash(source_sha256),
        'environment_sha256': _hash(environment_sha256),
        'max_age_seconds': _duration(max_age_seconds)}
    return _publish(directory, 'prepared.json', value)


def require_prepared(directory, *, registration_raw, attempt, max_age_seconds, pid):
    raw, value = _prepared(_directory(directory), registration_raw, attempt,
                           max_age_seconds, time.time())
    if value['pid'] != pid:
        raise ValueError('prepared record belongs to another process')
    return raw


def publish_proceed(directory, *, prepared_raw, guard_path, guard_sha256):
    directory = _directory(directory)
    if _read(directory, 'prepared.json')[0] != prepared_raw:
        raise ValueError('prepared record changed before proceed')
    path = Path(guard_path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError('proceed guard path must be canonical')
    if wire.sha(wire.read_regular(path)) != _hash(guard_sha256):
        raise ValueError('proceed guard digest differs from exact bytes')
    return _publish(directory, 'proceed.json', {
        'prepared_sha256': wire.sha(prepared_raw), 'guard_path': str(path),
        'guard_sha256': guard_sha256})


def wait_proceed(directory, *, prepared_raw, registration_raw, attempt, max_age_seconds):
    directory = _directory(directory)
    started = time.monotonic()
    _duration(max_age_seconds)
    while True:
        if time.monotonic() - started >= max_age_seconds:
            raise ValueError('prepared worker timed out')
        raw, value = _prepared(directory, registration_raw, attempt,
                               max_age_seconds, time.time())
        if raw != prepared_raw or value['pid'] != os.getpid():
            raise ValueError('prepared worker identity changed')
        if os.path.lexists(directory / 'proceed.json'):
            proceed_raw, proceed = _read(directory, 'proceed.json')
            if (set(proceed) != {'prepared_sha256', 'guard_path', 'guard_sha256'}
                    or proceed['prepared_sha256'] != wire.sha(prepared_raw)):
                raise ValueError('foreign proceed record')
            path = Path(proceed['guard_path'])
            if not path.is_absolute() or path.resolve(strict=True) != path:
                raise ValueError('proceed guard path must be canonical')
            if wire.sha(wire.read_regular(path)) != _hash(proceed['guard_sha256']):
                raise ValueError('proceed guard bytes changed')
            _publish(directory, 'consumed.json', {'proceed_sha256': wire.sha(proceed_raw)})
            # Persistence is intervening work: check the clocks again.
            _prepared(directory, registration_raw, attempt, max_age_seconds, time.time())
            if time.monotonic() - started >= max_age_seconds:
                raise ValueError('prepared worker timed out')
            return proceed
        time.sleep(min(POLL_SECONDS, max_age_seconds))
