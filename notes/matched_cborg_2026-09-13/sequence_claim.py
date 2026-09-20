"""Opt-in exact-byte evidence of an observed ownership transition (#2137).

Call only while holding the existing origin sequence lock. A claim is historical
evidence, not authority to restore a missing owner or retry a consumed attempt.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

from budgeted_cborg import BudgetStop
from audit_controls import registration as audit_registration

ClaimLock = audit_registration.SequenceLock

PROTOCOL = 'durable_sequence_claim_v1'
IMPLEMENTATION = Path(__file__).resolve()
IMPLEMENTATIONS = {IMPLEMENTATION, Path(audit_registration.__file__).resolve()}


def enabled(manifest):
    if 'sequence_claim' not in manifest:
        return False
    if manifest['sequence_claim'] != {'protocol': PROTOCOL}:
        raise BudgetStop('unsupported durable sequence claim protocol')
    return True


def select(manifest, requested):
    if type(requested) is not bool:
        raise BudgetStop('durable sequence claim requires an explicit boolean')
    manifest.pop('sequence_claim', None)
    if requested:
        manifest['sequence_claim'] = {'protocol': PROTOCOL}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _encode(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')) + '\n').encode()


def _json(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise BudgetStop('duplicate sequence claim field')
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(BudgetStop('nonfinite claim JSON')))


def _path(value):
    path = Path(value)
    if not path.is_absolute() or path.resolve() != path or path.is_symlink():
        raise BudgetStop('sequence claim paths must be canonical and nonsymlinked')
    return path


def _read(path, *, links=1):
    try:
        descriptor = os.open(_path(path), os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != links:
                raise BudgetStop('sequence claim evidence must be a regular unaliased file')
            return stream.read()
    except OSError as error:
        raise BudgetStop('sequence claim evidence is unavailable') from error


def _fsync(descriptor):
    os.fsync(descriptor)


def _sync(path):
    descriptor = os.open(_path(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        _fsync(descriptor)
    finally:
        os.close(descriptor)


def _write(path, raw):
    path = _path(path)
    temporary = path.with_name('.' + path.name + '.tmp')
    descriptor = os.open(_path(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw);stream.flush();_fsync(stream.fileno())
    os.link(temporary, path, follow_symlinks=False)  # Atomic publication without replacement.
    temporary.unlink()



def context(manifest, registration_path, registration_sha, state_path, origin, stage):
    """Validate the bound destination before canonical ownership changes."""
    if not enabled(manifest):
        return None
    registration_path = _path(registration_path)
    ledger = _path(manifest['budget']['ledger_path'])
    state_path = _path(state_path)
    _path(str(state_path) + '.lock')
    if (registration_path.name != 'registration.json' or ledger != registration_path.parent / 'billing.json' or
            _sha(_read(registration_path)) != registration_sha or _json(_read(registration_path)) != manifest or
            any(manifest['pinned_files'].get(str(p)) != _sha(_read(p)) for p in IMPLEMENTATIONS)):
        raise BudgetStop('durable sequence claim registration, layout or implementation differs')
    if (set(origin) != {'registration_sha256', 'ledger_path'} or
            _path(origin['ledger_path']).with_name('audit_sequence.json') != state_path):
        raise BudgetStop('durable sequence claim origin differs from canonical ownership')
    directory = _path(registration_path.parent / 'sequence_claim')
    failure = _path(registration_path.parent / 'sequence_claim_failed.json')
    for name in manifest['pinned_files']:
        frozen = _path(name)
        if frozen == directory or directory in frozen.parents or frozen == failure:
            raise BudgetStop('durable claim destination overlaps registered immutable evidence')
    return {'directory': directory, 'failure': failure, 'state': state_path,
            'identity': {'schema_version': 1, 'protocol': PROTOCOL,
                'kind': 'observed_sequence_owner_transition', 'canonical_state_path': str(state_path),
                'claiming_registration_path': str(registration_path),
                'claiming_registration_sha256': registration_sha, 'origin': origin, 'stage': stage,
                'implementation_sha256': _sha(_read(IMPLEMENTATION))}}


def _document(claim, owner, predecessor):
    return {**claim['identity'], 'owner_sha256': _sha(owner),
            'predecessor_sha256': None if predecessor is None else _sha(predecessor),
            'predecessor_absent': predecessor is None}


def verify(claim, expected_state, predecessor, *, complete=True):
    """Read-only same-owner check; never create, repair or adopt a claim."""
    if claim is None:
        return
    directory = _path(claim['directory'])
    failure_temporary = claim['failure'].with_name('.' + claim['failure'].name + '.tmp')
    if any(p.exists() or p.is_symlink() for p in (claim['failure'], failure_temporary)):
        raise BudgetStop('durable sequence claim recorded failed preservation; review required')
    names = {'owner.json', 'manifest.json'} | ({'predecessor.json'} if predecessor is not None else set())
    if complete:
        names.add('ready.json')
    if not directory.is_dir() or {p.name for p in directory.iterdir()} != names:
        raise BudgetStop('durable sequence claim is missing, incomplete or foreign')
    owner = _read(directory / 'owner.json')
    if complete:
        ready = _path(directory / 'ready.json')
        if not os.path.samefile(directory / 'manifest.json', ready):
            raise BudgetStop('durable claim success witness names another inode')
    if (_read(claim['state']) != owner or _json(owner) != expected_state or
            _read(directory / 'manifest.json', links=2 if complete else 1) != _encode(_document(claim, owner, predecessor)) or
            (predecessor is not None and _read(directory / 'predecessor.json') != predecessor)):
        raise BudgetStop('durable sequence claim bytes or predecessor identity changed')


def record(claim, expected_state, predecessor):
    """After owner advancement, preserve exclusively and fsync before admission.

    Failure consumes the owner. Preserve partial files and a best-effort failure
    marker; never roll back ownership or turn reentry into a snapshot retry.
    """
    if claim is None:
        return
    try:
        if claim['failure'].exists() or claim['failure'].is_symlink():
            raise BudgetStop('durable sequence claim previously failed')
        directory = claim['directory']
        _sync(claim['state']);_sync(claim['state'].parent)
        directory.mkdir(mode=0o700, exist_ok=False)
        owner = _read(claim['state'])
        if _json(owner) != expected_state:
            raise BudgetStop('canonical owner changed before durable preservation')
        _write(directory / 'owner.json', owner)
        if predecessor is not None:
            _write(directory / 'predecessor.json', predecessor)
        _write(directory / 'manifest.json', _encode(_document(claim, owner, predecessor)))
        _sync(directory);_sync(directory.parent)
        verify(claim, expected_state, predecessor, complete=False)
        # LAST fallible operation: no fsync after publication. The snapshot and
        # its directory are already synced; this extra success witness may be
        # lost on reboot, which fails closed. It can never witness a failed
        # earlier fsync, even if writing the failure receipt also fails.
        os.link(directory / 'manifest.json', directory / 'ready.json', follow_symlinks=False)
    except (OSError, ValueError, TypeError, BudgetStop) as error:
        try:
            _write(claim['failure'], _encode({**claim['identity'],
                'kind': 'sequence_claim_preservation_failed', 'error_type': type(error).__name__,
                'owner_remains_consumed': True, 'provider_admission_reached': False}))
            _sync(claim['failure'].parent)
        except (OSError, ValueError, TypeError, BudgetStop):
            pass  # A failing filesystem cannot guarantee even a failure receipt.
        raise BudgetStop('durable sequence claim preservation failed; owner remains consumed') from error
