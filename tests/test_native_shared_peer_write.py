"""Bounded filesystem behavior of the ordinary-Python native test peer."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import socket
import subprocess

import pytest


@pytest.fixture
def peer(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('peer writer regression attempted a child or network call')

    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    path = Path(__file__).parent / 'fixtures/native_shared_execution/fake_cli.py'
    spec = spec_from_file_location('native_shared_peer_write_fixture', path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert Path(module.__file__).resolve() == path.resolve()
    return module


def test_granted_write_creates_missing_response_parent(peer, tmp_path):
    unrelated = tmp_path / 'unrelated.txt'
    unrelated.write_bytes(b'retain this original\n')
    target = tmp_path / 'stage' / 'responses' / '000001.bin'
    assert not target.parent.exists()
    raw = '{"disposition":"unsupported","text":"café"}\n'

    peer._write_file(target, raw)

    assert target.read_bytes() == raw.encode()
    assert sorted(p.name for p in target.parent.iterdir()) == ['000001.bin']
    assert unrelated.read_bytes() == b'retain this original\n'


def test_granted_write_replaces_existing_content(peer, tmp_path):
    target = tmp_path / 'report.md'
    target.write_bytes(b'first draft\n')
    other = tmp_path / 'original_receipt.yaml'
    other.write_bytes(b'keep sealed receipt\n')

    peer._write_file(target, 'corrected report\n')

    assert target.read_bytes() == b'corrected report\n'
    assert other.read_bytes() == b'keep sealed receipt\n'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['original_receipt.yaml', 'report.md']


def test_granted_write_refuses_file_as_parent(peer, tmp_path):
    blocker = tmp_path / 'responses'
    blocker.write_bytes(b'preserve invalid parent\n')

    with pytest.raises(OSError):
        peer._write_file(blocker / '000001.bin', '{}\n')

    assert blocker.read_bytes() == b'preserve invalid parent\n'
    assert list(tmp_path.iterdir()) == [blocker]
