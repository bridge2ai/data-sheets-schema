"""Bounded regular-file captures and a flat, immutable selected evidence pool.

Decoding and replay use captured bytes only. Stable stream identifiers bind
observed prefixes without pretending their eventual final contents were known.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import os
from pathlib import Path
import stat

from data_sheets_schema.native_shared_contract import (
    ArtifactPin, CapturedArtifact, EvidencePrefix, EventRef, HARD_LIMITS, KINDS,
    canonical, canonical_path, exact, pin_dict, positive_int, sha, strict_json,
)

_METADATA = frozenset(('exists','regular','symlink','links','device','inode','size','mtime_ns'))


def _metadata(value, size):
    exact(value, _METADATA, 'captured file metadata')
    if (value['exists'] is not True or value['regular'] is not True or value['symlink'] is not False
            or type(value['links']) is not int or value['links'] != 1
            or any(type(value[k]) is not int or value[k] < 0 for k in ('device','inode','size'))
            or type(value['mtime_ns']) is not int or value['size'] != size):
        raise ValueError('captured member requires exact regular single-link metadata')
    return value


def _stat(info):
    return {'exists':True,'regular':stat.S_ISREG(info.st_mode),'symlink':stat.S_ISLNK(info.st_mode),
        'links':info.st_nlink,'device':info.st_dev,'inode':info.st_ino,'size':info.st_size,
        'mtime_ns':info.st_mtime_ns}


def read_regular(path, role, *, max_bytes):
    """Capture one regular file through limit+1 reads and stable open metadata.

    The caller supplies its fixed role's limit, already intersected with S/R.
    This function neither discovers resources nor substitutes another path.
    """
    canonical_path(path, 'capture path')
    positive_int(max_bytes, 'capture byte limit', HARD_LIMITS['stream_bytes'])
    target=Path(path)
    if str(target.resolve(strict=True)) != path:
        raise ValueError('captured path is not its exact physical path')
    before=_stat(target.lstat())
    _metadata(before,before['size'])
    if before['size'] > max_bytes:
        raise ValueError('captured file exceeds its role byte bound')
    flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    fd=os.open(path,flags)
    try:
        opened=_stat(os.fstat(fd))
        if opened != before:
            raise ValueError('captured file changed before open')
        pieces=[];remaining=max_bytes+1
        while remaining:
            part=os.read(fd,min(65536,remaining))
            if not part:break
            pieces.append(part);remaining-=len(part)
        raw=b''.join(pieces)
        after=_stat(os.fstat(fd))
    finally:
        os.close(fd)
    if (len(raw)>max_bytes or len(raw)!=before['size'] or before!=after
            or _stat(target.lstat())!=before or str(target.resolve(strict=True))!=path):
        raise ValueError('captured file changed or exceeded its role byte bound')
    captured=CapturedArtifact(pin=ArtifactPin(role=role,path=path,bytes=len(raw),sha256=sha(raw)),raw=raw)
    return PoolMember(captured=captured,metadata_json=canonical(before))


@dataclass(frozen=True)
class PoolMember:
    captured: CapturedArtifact
    metadata_json: bytes

    def __post_init__(self):
        if type(self.captured) is not CapturedArtifact or type(self.metadata_json) is not bytes:
            raise ValueError('pool member requires immutable captured bytes and metadata')
        metadata=_metadata(strict_json(self.metadata_json,'member metadata'),self.captured.pin.bytes)
        if canonical(metadata)!=self.metadata_json:
            raise ValueError('member metadata must retain canonical closed bytes')

    @property
    def member_id(self):
        return sha(canonical({'domain':'native_shared_member_v1',
            'pin':pin_dict(self.captured.pin),'metadata':strict_json(self.metadata_json)}))

    def document(self):
        return {'member_id':self.member_id,'pin':pin_dict(self.captured.pin),
                'metadata':strict_json(self.metadata_json),
                'raw_base64':base64.b64encode(self.captured.raw).decode('ascii')}


def stream_id(execution_sha256,stream,path):
    # ArtifactPin validates the exact hash without creating any file claim.
    canonical_path(path,'stream path')
    if (type(execution_sha256) is not str or len(execution_sha256)!=64
            or any(c not in '0123456789abcdef' for c in execution_sha256)
            or stream not in ('transcript','control')):
        raise ValueError('stream identity requires exact execution and role')
    return sha(canonical({'domain':'native_shared_stream_v1','execution_sha256':execution_sha256,
                          'stream':stream,'path':path}))


@dataclass(frozen=True)
class CapturePool:
    members: tuple[PoolMember,...]
    stream_bindings: tuple[tuple[str,str],...]

    def __post_init__(self):
        if (type(self.members) is not tuple or any(type(m) is not PoolMember for m in self.members)
                or type(self.stream_bindings) is not tuple):
            raise ValueError('capture pool must be an immutable closed collection')
        if len(self.members)>HARD_LIMITS['captured_members']:
            raise ValueError('capture pool exceeds its member count')
        ids=[m.member_id for m in self.members]
        if len(set(ids))!=len(ids):
            raise ValueError('capture pool contains duplicate member identities')
        if sum(m.captured.pin.bytes for m in self.members)>HARD_LIMITS['evidence_raw_total_bytes']:
            raise ValueError('capture pool exceeds its complete decoded byte bound')
        seen=set()
        for row in self.stream_bindings:
            if (type(row) is not tuple or len(row)!=2 or any(type(v) is not str for v in row)
                    or len(row[0])!=64 or any(c not in '0123456789abcdef' for c in row[0])
                    or row[0] in seen or row[1] not in ids):
                raise ValueError('capture pool has ambiguous or missing stream bindings')
            seen.add(row[0])
        if len(seen)>2:
            raise ValueError('one capture supports exactly its parent transcript and control streams')

    def member(self,member_id):
        found=[m for m in self.members if m.member_id==member_id]
        if len(found)!=1:raise ValueError('captured member reference is absent or ambiguous')
        return found[0]

    def encode(self):
        metadata={'kind':KINDS['capture_pool'],'version':1,
            'members':[{'member_id':m.member_id,'pin':pin_dict(m.captured.pin),
                        'metadata':strict_json(m.metadata_json)} for m in self.members],
            'stream_bindings':[{'stream_id':s,'member_id':m} for s,m in self.stream_bindings]}
        if len(canonical(metadata))>HARD_LIMITS['evidence_metadata_wire_bytes']:
            raise ValueError('capture pool exceeds its metadata byte bound')
        # Bound the exact base64 allocation before constructing complete JSON.
        base64_size=sum(4*((m.captured.pin.bytes+2)//3) for m in self.members)
        if len(canonical(metadata))+base64_size+32*len(self.members)>HARD_LIMITS['evidence_wire_bytes']:
            raise ValueError('capture pool exceeds its complete encoded byte bound')
        document={**metadata,'members':[m.document() for m in self.members]}
        raw=canonical(document)
        if len(raw)>HARD_LIMITS['evidence_wire_bytes']:
            raise ValueError('capture pool exceeds its complete encoded byte bound')
        return raw

    def prefix(self,reference,*,execution_sha256):
        exact(reference,{'stream_id','stream','path','through_bytes','lines','sha256'},'stream prefix reference')
        selected=stream_id(execution_sha256,reference['stream'],reference['path'])
        if selected!=reference['stream_id']:
            raise ValueError('prefix reference differs from selected execution/stream/path')
        bindings=dict(self.stream_bindings)
        if selected not in bindings:raise ValueError('prefix has no captured stream binding')
        member=self.member(bindings[selected]).captured
        if member.pin.role!=reference['stream'] or member.pin.path!=reference['path']:
            raise ValueError('stream binding has a foreign role or path')
        end=reference['through_bytes']
        if type(end) is not int or end<0 or end>len(member.raw):
            raise ValueError('prefix endpoint exceeds the captured stream')
        return EvidencePrefix(stream=reference['stream'],path=reference['path'],raw=member.raw[:end],
            bytes=end,lines=reference['lines'],sha256=reference['sha256'])


def decode(raw):
    document=strict_json(raw,'flat native capture pool',HARD_LIMITS['evidence_wire_bytes'])
    exact(document,{'kind','version','members','stream_bindings'},'capture pool')
    if document['kind']!=KINDS['capture_pool'] or type(document['version']) is not int or document['version']!=1:
        raise ValueError('unknown capture pool kind/version')
    rows=document['members'];bindings=document['stream_bindings']
    if (type(rows) is not list or len(rows)>HARD_LIMITS['captured_members']
            or type(bindings) is not list or len(bindings)>2):
        raise ValueError('capture pool collections exceed their typed bounds')
    total=0;members=[];metadata=[]
    for row in rows:
        exact(row,{'member_id','pin','metadata','raw_base64'},'capture member')
        exact(row['pin'],{'role','path','bytes','sha256'},'capture member pin')
        pin=ArtifactPin(**row['pin'])
        if pin.bytes>HARD_LIMITS['stream_bytes']:
            raise ValueError('capture member exceeds all supported role maxima')
        total+=pin.bytes
        if total>HARD_LIMITS['evidence_raw_total_bytes']:
            raise ValueError('decoded capture exceeds complete byte bound')
        encoded=row['raw_base64']
        if type(encoded) is not str or len(encoded)!=4*((pin.bytes+2)//3):
            raise ValueError('capture member has noncanonical or oversized base64')
        try:body=base64.b64decode(encoded,validate=True)
        except (ValueError,binascii.Error) as exc:raise ValueError('invalid captured base64') from exc
        if base64.b64encode(body).decode('ascii')!=encoded:
            raise ValueError('capture member base64 has noncanonical padding bits')
        member=PoolMember(captured=CapturedArtifact(pin=pin,raw=body),metadata_json=canonical(_metadata(row['metadata'],pin.bytes)))
        if member.member_id!=row['member_id']:
            raise ValueError('capture member identity differs from raw bytes/metadata')
        members.append(member);metadata.append({k:v for k,v in row.items() if k!='raw_base64'})
    pairs=[]
    for row in bindings:
        exact(row,{'stream_id','member_id'},'stream binding');pairs.append((row['stream_id'],row['member_id']))
    if len(canonical({**document,'members':metadata}))>HARD_LIMITS['evidence_metadata_wire_bytes']:
        raise ValueError('capture pool exceeds metadata byte bound')
    return CapturePool(members=tuple(members),stream_bindings=tuple(pairs))


def prefix_reference(prefix,*,execution_sha256):
    if type(prefix) is not EvidencePrefix:raise ValueError('expected exact observed prefix')
    return {'stream_id':stream_id(execution_sha256,prefix.stream,prefix.path),'stream':prefix.stream,
        'path':prefix.path,'through_bytes':prefix.bytes,'lines':prefix.lines,'sha256':prefix.sha256}


def event(prefix,reference):
    """Resolve only an exact event inside the actual observed prefix."""
    if type(prefix) is not EvidencePrefix or type(reference) is not EventRef or reference.stream!=prefix.stream:
        raise ValueError('event reference differs from its observed stream prefix')
    lines=[part+b'\n' for part in prefix.raw.split(b'\n')[:-1]]
    if reference.line>len(lines):raise ValueError('event lies beyond its observed prefix')
    raw=lines[reference.line-1]
    if sha(raw)!=reference.raw_line_sha256:raise ValueError('event physical line hash differs')
    value=strict_json(raw,'observed event',HARD_LIMITS['stream_bytes'])
    if reference.block is not None:
        message=value.get('message') if type(value) is dict else None
        content=message.get('content') if type(message) is dict else None
        if type(content) is not list or reference.block>=len(content):
            raise ValueError('event block is absent from the captured physical line')
        value=content[reference.block]
    if sha(canonical(value))!=reference.value_sha256:raise ValueError('event value hash differs')
    return value


def require_append_only(earlier,later):
    if (type(earlier) is not EvidencePrefix or type(later) is not EvidencePrefix
            or earlier.stream!=later.stream or earlier.path!=later.path
            or not later.raw.startswith(earlier.raw)):
        raise ValueError('observed stream prefixes are not the same append-only stream')
