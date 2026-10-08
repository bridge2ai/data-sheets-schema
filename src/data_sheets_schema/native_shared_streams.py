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
MAX_DIAGNOSTIC_BYTES = 16 * 1024


class _LiveStreamRefusal(ValueError):
    """The original refusal arguments plus immutable, bounded diagnostic bytes."""

    def __init__(self, original, diagnostic_json):
        super().__init__(*original.args)
        self._diagnostic_json = diagnostic_json

    @property
    def diagnostic_json(self):
        return self._diagnostic_json


def diagnostic_document(raw):
    """Decode a detached diagnostic; its contents never grant stream admission."""
    value = c.strict_json(raw, 'native live-stream diagnostic', MAX_DIAGNOSTIC_BYTES)
    if c.canonical(value) != raw:
        raise ValueError('native live-stream diagnostic is not canonical')
    return value


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


def _progress(earlier, later, maximum, *, diagnostic=None):
    try:
        evidence._metadata(later, later['size'])
        if any(later[k] != earlier[k] for k in ('device', 'inode', 'regular', 'symlink', 'links')):
            raise ValueError('live native stream physical identity changed')
        if later['size'] < earlier['size'] or later['size'] > maximum:
            raise ValueError('live native stream shrank or exceeded its byte bound')
        if later['size'] == earlier['size'] and later['mtime_ns'] != earlier['mtime_ns']:
            raise ValueError('live native stream changed without appending bytes')
    except ValueError as original:
        # Diagnostic work is best effort and happens only after the unchanged
        # refusal. Never acquire more metadata or bytes to explain a failure.
        if diagnostic is not None:
            try:
                raw = c.canonical({'kind': 'native_live_stream_refusal', 'version': 1,
                    **diagnostic, 'max_bytes': maximum, 'earlier': earlier, 'later': later})
                diagnostic_document(raw)
                enriched = _LiveStreamRefusal(original, raw)
            except Exception:
                raise original
            raise enriched from original
        raise
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
        def progress(earlier, later, stage, *, pass_number=None, offset=0, opened_extent=None):
            return _progress(earlier, later, max_bytes, diagnostic={
                'role': role, 'path': path, 'stage': stage,
                'pass_number': pass_number, 'offset': offset, 'opened_extent': opened_extent,
                'previous_prefix': None if previous is None else {
                    'bytes': previous.bytes, 'sha256': previous.sha256}})

        opened = progress(before, evidence._stat(os.fstat(fd)), 'opened')
        size = opened['size']
        if previous is not None and previous.bytes > size:
            raise ValueError('live native stream lost an observed prefix')
        last = opened
        pieces = []
        offset = 0
        while offset < size:
            last = progress(last, evidence._stat(os.fstat(fd)), 'before_read',
                            pass_number=1, offset=offset, opened_extent=size)
            count = min(65536, size - offset)
            part = os.pread(fd, count, offset)
            if not part or len(part) > count:
                raise ValueError('live native stream ended inside its opened extent')
            pieces.append(part)
            offset += len(part)
            last = progress(last, evidence._stat(os.fstat(fd)), 'after_read',
                            pass_number=1, offset=offset, opened_extent=size)
        raw = b''.join(pieces)
        del pieces
        offset = 0
        while offset < size:
            last = progress(last, evidence._stat(os.fstat(fd)), 'before_read',
                            pass_number=2, offset=offset, opened_extent=size)
            count = min(65536, size - offset)
            part = os.pread(fd, count, offset)
            if not part or len(part) > count or part != raw[offset:offset + len(part)]:
                raise ValueError('live native stream prefix changed during capture')
            offset += len(part)
            last = progress(last, evidence._stat(os.fstat(fd)), 'after_read',
                            pass_number=2, offset=offset, opened_extent=size)
        last = progress(last, evidence._stat(os.fstat(fd)), 'final_fd',
                        offset=offset, opened_extent=size)
        progress(last, evidence._stat(target.lstat()), 'final_path',
                 offset=offset, opened_extent=size)
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
