"""#5989 offline direction-replay regressions, 2026-11-12.
Only synthetic start records and fabricated command output; no actual capture.
"""
from pathlib import Path
import pytest
from data_sheets_schema import native_launch_sequence as seq
from data_sheets_schema import native_sequence_start as start
from tests import test_native_launch_sequence as fixtures
from tests.test_native_launch_sequence import deny_real_commands


def test_different_packet_retry_needs_new_direction(tmp_path, monkeypatch):
    p=fixtures.paths(tmp_path)
    monkeypatch.setattr(seq,'_utc_now',lambda:'2026-11-12T12:00:00Z')
    flags=['--direction-recorded-at','2026-11-12T11:59:00Z',
           '--host-confirmed-at','2026-11-12T11:59:00Z']
    calls=fixtures.fake_commands(monkeypatch,p,fail=seq.COMMANDS[0])
    assert seq.main([*fixtures.argv(p),*flags])==1
    assert len(calls)==1
    old=Path(fixtures.record(p)['start_claim']); raw=old.read_bytes()
    first_manifest=fixtures.manifest(p)
    p['packet-directory']=tmp_path/'second-packet'
    p['subscription-guard']=tmp_path/'second-guard.json'
    calls=fixtures.fake_commands(monkeypatch,p)
    # Equivalent UTC spelling and a refreshed host confirmation do not renew it.
    flags[1]='2026-11-12T11:59:00.000000Z'; flags[3]='2026-11-12T12:00:00Z'
    assert seq.main([*fixtures.argv(p),*flags])==1
    assert calls==[] and old.read_bytes()==raw
    p['packet-directory']=tmp_path/'third-packet'
    flags[1]='2026-11-12T11:59:01Z'
    monkeypatch.setattr(fixtures,'manifest',lambda paths:first_manifest.parent.parent/'capture-2/capture.json')
    calls=fixtures.fake_commands(monkeypatch,p)
    assert seq.main([*fixtures.argv(p),*flags])==0
    assert len(calls)==3 and old.read_bytes()==raw
    assert Path(fixtures.record(p)['start_claim']) != old
    assert not (tmp_path/'NEVER-RESERVED-ATTEMPT').exists()


def test_owner_start_records_are_repeatable(tmp_path):
    p=fixtures.paths(tmp_path)
    args=dict(direction=None,confirmation=None,packet=p['packet-directory'],started_at='2026-11-12T12:00:00Z')
    a=Path(start.claim(p['registration'].read_bytes(),**args))
    b=Path(start.claim(p['registration'].read_bytes(),**args))
    assert a!=b and a.read_bytes()==b.read_bytes()
    assert not p['output-directory'].exists()


def test_direction_claim_refuses_symlink_state(tmp_path):
    p=fixtures.paths(tmp_path); elsewhere=tmp_path/'elsewhere'; elsewhere.mkdir()
    (tmp_path/'.native-sequence-starts').symlink_to(elsewhere,target_is_directory=True)
    with pytest.raises(ValueError,match='physical directory'):
        start.claim(p['registration'].read_bytes(),direction=None,confirmation=None,
                    packet=p['packet-directory'],started_at='2026-11-12T12:00:00Z')
    assert not list(elsewhere.iterdir())
