"""The saved pool retains the caller's bound, including unvisited members.

Initialization and permission observations are synthetic offline fixtures.
The extra member exists only in memory; no native process or provider runs.
"""
import builtins
import os
from pathlib import Path
import socket
import subprocess

import pytest

from tests.test_native_shared_results import initial
from tests.test_native_shared_live_capture import started
from tests.test_native_shared_registration import execution, bound, native_spec
from tests.test_native_shared_selection import declaration as original_declaration, save
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_results as results
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_selection as selection


@pytest.fixture
def declaration(original_declaration):
    # Explicit test allowance above the unchanged 32 MB finalization reserve.
    document = original_declaration
    document['bounds']['max_evidence_bytes'] = 33_000_000
    save(document)
    return document


def _extra_member(path, raw):
    artifact = c.CapturedArtifact(c.ArtifactPin('synthetic-extra', str(path), len(raw), c.sha(raw)), raw)
    metadata = {'exists': True, 'regular': True, 'symlink': False, 'links': 1,
                'device': 0, 'inode': 123, 'size': len(raw), 'mtime_ns': 0}
    return evidence.PoolMember(artifact, c.canonical(metadata))


def test_saved_pool_selected_cap_counts_every_member_without_io(started, monkeypatch, tmp_path):
    live, pool = initial(started)
    original_pool = pool.encode()
    original_value = c.canonical(live.value)
    original_files = {path: c.sha(path.read_bytes()) for path in tmp_path.rglob('*') if path.is_file()}
    maximum = live.selection.bounds()['max_evidence_bytes']
    total = sum(member.captured.pin.bytes for member in pool.members)
    assert total < maximum < c.HARD_LIMITS['evidence_raw_total_bytes']
    path = tmp_path / 'not-written.bin'
    at_cap = evidence.CapturePool(pool.members + (_extra_member(path, b'x' * (maximum - total)),),
                                  pool.stream_bindings)
    over_cap = evidence.CapturePool(pool.members + (_extra_member(path, b'x' * (maximum - total + 1)),),
                                    pool.stream_bindings)
    assert sum(member.captured.pin.bytes for member in at_cap.members) == maximum
    assert sum(member.captured.pin.bytes for member in over_cap.members) == maximum + 1

    def forbidden(*args, **kwargs):
        pytest.fail('saved evidence bound consulted ambient I/O or execution')

    with monkeypatch.context() as patch:
        for owner, name in ((evidence, 'read_regular'), (selection, 'capture'),
                            (selection, 'capture_assets'), (capture, '_load')):
            patch.setattr(owner, name, forbidden)
        for name in ('cwd', 'absolute', 'resolve', 'read_bytes', 'read_text', 'open',
                     'stat', 'lstat', 'exists', 'is_file', 'is_dir'):
            patch.setattr(Path, name, forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(os, 'open', forbidden)
        for name in ('run', 'Popen', 'check_output'):
            patch.setattr(subprocess, name, forbidden)
        patch.setattr(socket.socket, 'connect', forbidden)
        assert results.rebuild(pool, live.value).binding == live.binding
        assert results.rebuild(at_cap, live.value).binding == live.binding
        with pytest.raises(ValueError, match='complete capture exceeds the selected evidence bound'):
            results.rebuild(over_cap, live.value)
        assert pool.encode() == original_pool
        assert c.canonical(live.value) == original_value

    assert not path.exists()
    assert {path: c.sha(path.read_bytes()) for path in original_files} == original_files
