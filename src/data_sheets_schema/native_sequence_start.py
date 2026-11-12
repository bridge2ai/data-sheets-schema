"""Registration-scoped start records; a delegated direction is consumed once.

The recorded UTC direction time is its identity within this registration. Host
confirmation can be renewed but cannot renew a direction. These are supplied
owner records, not authenticated identities. Owner starts are individually kept.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import uuid
from . import native_subscription_guard as wire


def _directory(path):
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    if not path.is_dir() or path.resolve(strict=True) != path:
        raise ValueError('sequence start state must be a physical directory')
    _sync(path.parent)


def _sync(path):
    fd=os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def claim(registration_raw, *, direction, confirmation, packet, started_at):
    """Keep an exclusive start record outside caller-selected packet paths.

    No capture/word journal or attempt reservation is created. An interrupted
    or failed delegated start consumes this direction; its claim is never reset.
    Full registration/current authority is still validated by the child gates.
    """
    value=wire.strict_json(registration_raw)
    attempt=Path(value['registration']['attempt_directory'])
    if (not attempt.is_absolute() or attempt.parent.resolve(strict=True) != attempt.parent
            or attempt.is_symlink() or str(attempt) != value['registration']['attempt_directory']):
        raise ValueError('sequence start needs the physical registered attempt parent')
    root=attempt.parent/'.native-sequence-starts'
    _directory(root)
    digest=wire.sha(registration_raw)
    root=root/digest
    _directory(root)
    identity=None
    if direction is not None:
        # Normalize equivalent strict UTC spellings before choosing the claim.
        if type(direction) is not str or re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z', direction) is None:
            raise ValueError('direction identity requires strict UTC')
        identity=datetime.fromisoformat(direction[:-1]+'+00:00').astimezone(timezone.utc).isoformat(timespec='microseconds')
        name='direction-'+wire.sha(identity.encode())
    else:
        name='owner-'+uuid.uuid4().hex
    path=root/(name+'.json')
    raw=wire.canonical({'registration_sha256':digest,'direction_identity':identity,
        'direction_recorded_at':direction,'host_confirmed_at':confirmation,
        'packet_directory':str(packet),'started_at':started_at})
    try:
        fd=os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError as exc:
        raise ValueError('delegated direction already consumed; a new recorded direction is required') from exc
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    _sync(root)
    return str(path)
