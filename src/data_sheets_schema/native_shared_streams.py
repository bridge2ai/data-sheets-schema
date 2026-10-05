"""Finite append-tolerant snapshots for the two active native streams only.

Immutable artifacts and final captures still use evidence.read_regular. A live
snapshot retains the exact opened-size bytes and opened metadata; permission
credit belongs to a separate, complete-line observed prefix.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import native_shared_contract as c
from . import native_shared_evidence as evidence

ROLES = ('transcript', 'control')


def _identity(value):
    c.exact(value, {'device', 'inode'}, 'native stream file identity')
    if any(type(value[k]) is not int or value[k] < 0 for k in value):
        raise ValueError('native stream file identity requires nonnegative integers')
    return dict(value)


def identities(value):
    c.exact(value, set(ROLES), 'native stream files')
    return {role: _identity(value[role]) for role in ROLES}


def stream_files(members):
    """Physical anchors from actual captured metadata, never current host I/O."""
    found = {}
    for member in members:
        if type(member) is not evidence.PoolMember or member.captured.pin.role not in ROLES:
            raise ValueError('native stream anchors require the two captured streams')
        role = member.captured.pin.role
        if role in found:
            raise ValueError('duplicate native stream anchor')
        meta = c.strict_json(member.metadata_json)
        found[role] = {key: meta[key] for key in ('device', 'inode')}
    return identities(found)


def _progress(earlier, later, maximum):
    evidence._metadata(later, later['size'])
    if any(later[k] != earlier[k] for k in ('device', 'inode', 'regular', 'symlink', 'links')):
        raise ValueError('live native stream physical identity changed')
    if later['size'] < earlier['size'] or later['size'] > maximum:
        raise ValueError('live native stream shrank or exceeded its byte bound')
    if later['size'] == earlier['size'] and later['mtime_ns'] != earlier['mtime_ns']:
        raise ValueError('live native stream changed without appending bytes')
    return later


def read_live_stream(path, role, *, max_bytes, previous=None, identity=None):
    """Read the fixed opened extent twice; never chase a growing EOF.

    Later append is allowed on the same regular single-link inode. The return
    metadata describes the actual opened-size observation, not a later EOF.
    Visible truncation, prefix mutation and replacement refuse. Finite reads
    cannot authenticate an arbitrary host or an ABA hidden between all checks.
    """
    c.canonical_path(path, 'live native stream path')
    c.positive_int(max_bytes, 'live stream byte limit', c.HARD_LIMITS['stream_bytes'])
    if role not in ROLES:
        raise ValueError('live snapshots are restricted to native stream roles')
    expected = _identity(identity) if identity is not None else None
    if previous is not None and (type(previous) is not c.EvidencePrefix
            or previous.stream != role or previous.path != path):
        raise ValueError('previous observed prefix belongs to another stream')
    target = Path(path)
    if str(target.resolve(strict=True)) != path:
        raise ValueError('live native stream is not its exact physical path')
    before = evidence._stat(target.lstat())
    evidence._metadata(before, before['size'])
    if before['size'] > max_bytes:
        raise ValueError('live native stream exceeds its byte bound')
    if expected is not None and any(before[k] != expected[k] for k in expected):
        raise ValueError('live native stream differs from its observed file identity')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        opened = _progress(before, evidence._stat(os.fstat(fd)), max_bytes)
        size = opened['size']
        if previous is not None and previous.bytes > size:
            raise ValueError('live native stream lost an observed prefix')
        last = opened
        pieces = []
        offset = 0
        while offset < size:
            last = _progress(last, evidence._stat(os.fstat(fd)), max_bytes)
            count = min(65536, size - offset)
            part = os.pread(fd, count, offset)
            if not part or len(part) > count:
                raise ValueError('live native stream ended inside its opened extent')
            pieces.append(part)
            offset += len(part)
            last = _progress(last, evidence._stat(os.fstat(fd)), max_bytes)
        raw = b''.join(pieces)
        del pieces
        offset = 0
        while offset < size:
            last = _progress(last, evidence._stat(os.fstat(fd)), max_bytes)
            count = min(65536, size - offset)
            part = os.pread(fd, count, offset)
            if not part or len(part) > count or part != raw[offset:offset + len(part)]:
                raise ValueError('live native stream prefix changed during capture')
            offset += len(part)
            last = _progress(last, evidence._stat(os.fstat(fd)), max_bytes)
        last = _progress(last, evidence._stat(os.fstat(fd)), max_bytes)
        _progress(last, evidence._stat(target.lstat()), max_bytes)
        if str(target.resolve(strict=True)) != path:
            raise ValueError('live native stream path changed during capture')
        if previous is not None and raw[:previous.bytes] != previous.raw:
            raise ValueError('previously observed native stream prefix changed')
    finally:
        os.close(fd)
    return evidence.PoolMember(c.CapturedArtifact(c.ArtifactPin(role, path, size, c.sha(raw)), raw),
                               c.canonical(opened))


def prefix(member, endpoint=None):
    """Expose only a complete-LF prefix; leave any acquired future tail raw."""
    if type(member) is not evidence.PoolMember or member.captured.pin.role not in ROLES:
        raise ValueError('live prefix requires a captured native stream')
    item = member.captured
    end = item.raw.rfind(b'\n') + 1 if endpoint is None else endpoint
    if type(end) is not int or not 0 <= end <= len(item.raw):
        raise ValueError('observed stream endpoint exceeds its captured bytes')
    raw = item.raw[:end]
    return c.EvidencePrefix(item.pin.role, item.pin.path, raw, end, c.sha(raw), raw.count(b'\n'))
