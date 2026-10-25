"""Captured-only pool/prefix replay and bounded exact regular-file evidence."""
from dataclasses import replace
from pathlib import Path
import os

import pytest

from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema.native_shared_contract import (
    ArtifactPin,CapturedArtifact,EvidencePrefix,EventRef,canonical,sha,
)


def member(raw,role='transcript',path='/selected/transcript.jsonl',inode=1,mtime=1):
    captured=CapturedArtifact(pin=ArtifactPin(role=role,path=path,bytes=len(raw),sha256=sha(raw)),raw=raw)
    return evidence.PoolMember(captured=captured,metadata_json=canonical({'exists':True,'regular':True,
        'symlink':False,'links':1,'device':1,'inode':inode,'size':len(raw),'mtime_ns':mtime}))


def prefix(raw,path='/selected/transcript.jsonl'):
    return EvidencePrefix(stream='transcript',path=path,raw=raw,bytes=len(raw),lines=raw.count(b'\n'),sha256=sha(raw))


def test_extended_final_stream_resolves_original_observed_prefix_without_future_bytes(monkeypatch):
    first=canonical({'type':'first'})+b'\n';future=canonical({'type':'future'})+b'\n'
    old=member(first);final=member(first+future,mtime=2)
    sid=evidence.stream_id('a'*64,'transcript',old.captured.pin.path)
    old_pool=evidence.CapturePool(members=(old,),stream_bindings=((sid,old.member_id),))
    final_pool=evidence.CapturePool(members=(old,final),stream_bindings=((sid,final.member_id),))
    ref=evidence.prefix_reference(prefix(first),execution_sha256='a'*64)
    raw=final_pool.encode()
    def trap(*a,**k):raise AssertionError('saved replay attempted filesystem access')
    for attr in ('read_bytes','read_text','open','stat','resolve','exists'):
        monkeypatch.setattr(Path,attr,trap)
    restored=evidence.decode(raw)
    assert restored==final_pool
    before=old_pool.prefix(ref,execution_sha256='a'*64)
    after=restored.prefix(ref,execution_sha256='a'*64)
    assert before==after==prefix(first)
    current=EventRef(stream='transcript',line=1,block=None,raw_line_sha256=sha(first),value_sha256=sha(canonical({'type':'first'})))
    assert evidence.event(after,current)=={'type':'first'}
    with pytest.raises(ValueError,match='beyond'):
        evidence.event(after,replace(current,line=2,raw_line_sha256=sha(future)))
    with pytest.raises(ValueError,match='execution/stream/path'):
        restored.prefix(ref,execution_sha256='b'*64)


def test_content_path_and_metadata_versions_are_distinct_identities():
    original=member(b'{}\n')
    variants=(original,member(b'{}\n',path='/other/transcript.jsonl'),member(b'{}\n',mtime=2),member(b'{ }\n'))
    assert len({m.member_id for m in variants})==4
    pool=evidence.CapturePool(members=variants,stream_bindings=())
    assert evidence.decode(pool.encode())==pool
    with pytest.raises(ValueError,match='duplicate'):
        evidence.CapturePool(members=(original,original),stream_bindings=())


@pytest.mark.parametrize('field,value',[('exists',1),('regular',1),('symlink',0),('links',True),
    ('links',2),('device',False),('inode',-1),('size',True),('mtime_ns',1.0)])
def test_metadata_cannot_hide_aliases_or_type_substitution(field,value):
    row=member(b'{}').document();row['metadata'][field]=value
    document={'kind':'d4d_native_shared_capture_pool','version':1,'members':[row],'stream_bindings':[]}
    with pytest.raises(ValueError):evidence.decode(canonical(document))


@pytest.mark.parametrize('change',['raw','pin','id','padding','unknown','duplicate_binding'])
def test_rehashed_container_still_checks_each_member_and_binding(change):
    current=member(b'{}\n');sid=evidence.stream_id('a'*64,'transcript',current.captured.pin.path)
    row=current.document();bindings=[{'stream_id':sid,'member_id':current.member_id}]
    if change=='raw':row['raw_base64']='e30K'.replace('e','a',1)
    if change=='pin':row['pin']['sha256']='f'*64
    if change=='id':row['member_id']='f'*64
    if change=='padding':row['raw_base64']='e30K\n'
    if change=='unknown':row['unknown']='not an extension'
    if change=='duplicate_binding':bindings*=2
    with pytest.raises(ValueError):evidence.decode(canonical({'kind':'d4d_native_shared_capture_pool','version':1,
        'members':[row],'stream_bindings':bindings}))


def test_regular_file_capture_and_exact_bound(tmp_path):
    source=tmp_path/'source';source.write_bytes(b'1234')
    captured=evidence.read_regular(str(source),'source',max_bytes=4)
    assert captured.captured.raw==b'1234'
    assert captured.captured.pin.sha256==sha(b'1234')
    with pytest.raises(ValueError,match='bound'):
        evidence.read_regular(str(source),'source',max_bytes=3)
    assert source.read_bytes()==b'1234'


@pytest.mark.parametrize('alias',['symlink','hardlink'])
def test_nonregular_or_multiple_link_capture_refuses_without_mutation(tmp_path,alias):
    source=tmp_path/'source';source.write_bytes(b'unchanged')
    linked=tmp_path/'alias'
    if alias=='symlink':linked.symlink_to(source)
    else:os.link(source,linked)
    with pytest.raises(ValueError):evidence.read_regular(str(linked),'source',max_bytes=100)
    assert source.read_bytes()==b'unchanged'


def test_file_change_after_open_is_refused(tmp_path,monkeypatch):
    source=tmp_path/'source';source.write_bytes(b'before')
    read=evidence.os.read;once=[]
    def changed(fd,n):
        raw=read(fd,n)
        if not once:
            once.append(True);source.write_bytes(b'after!')
        return raw
    monkeypatch.setattr(evidence.os,'read',changed)
    with pytest.raises(ValueError,match='changed'):
        evidence.read_regular(str(source),'source',max_bytes=100)


def test_physical_line_and_block_reference_are_independent():
    value={'message':{'content':[{'type':'text','text':'one'},{'type':'text','text':'two'}]}}
    raw=canonical(value)+b'\n';seen=prefix(raw)
    ref=EventRef(stream='transcript',line=1,block=1,raw_line_sha256=sha(raw),value_sha256=sha(canonical(value['message']['content'][1])))
    assert evidence.event(seen,ref)==value['message']['content'][1]
    with pytest.raises(ValueError,match='value hash'):evidence.event(seen,replace(ref,block=0))
    with pytest.raises(ValueError,match='line hash'):evidence.event(seen,replace(ref,raw_line_sha256='a'*64))
    with pytest.raises(ValueError,match='append-only'):evidence.require_append_only(seen,prefix(b'{}\n'))
    evidence.require_append_only(seen,prefix(raw+b'{}\n'))
