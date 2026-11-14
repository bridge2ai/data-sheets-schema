"""Fault injection for retained create-once evidence; no native execution."""
import pytest

from data_sheets_schema import native_shared_callback_io as io
from data_sheets_schema.native_shared_evidence import read_regular


@pytest.mark.parametrize('persistent', [False, True])
def test_post_link_sync_failure_retains_readable_single_link(tmp_path, monkeypatch, persistent):
    target = tmp_path / '000000.json'
    original = OSError('publication sync failed')
    calls = []

    def fail(path):
        calls.append(path)
        if len(calls) == 1:
            raise original
        if persistent:
            raise OSError('cleanup sync failed')

    monkeypatch.setattr(io, '_sync_directory', fail)
    with pytest.raises(OSError) as caught:
        io.durable_new(target, b'complete evidence')
    assert caught.value is original
    assert len(calls) == 2
    assert list(tmp_path.iterdir()) == [target]
    assert target.stat().st_nlink == 1
    assert read_regular(str(target), 'observation', max_bytes=100).captured.raw == b'complete evidence'


def test_failed_observation_staging_preserves_bytes_outside_namespace(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from data_sheets_schema import native_shared_capture as capture
    from data_sheets_schema import native_shared_capture_orchestration as host

    root = tmp_path / 'stage'
    root.mkdir()
    observations = root / 'observations'
    selection = SimpleNamespace(role=lambda role: str(
        root if role == 'stage_root' else observations))
    monkeypatch.setattr(host, '_Reader', lambda _: SimpleNamespace(destination=lambda *a: 100))
    original_link = io.os.link

    def fail_link(*args):
        raise OSError('injected pre-publication failure')

    monkeypatch.setattr(io.os, 'link', fail_link)
    with pytest.raises(OSError, match='injected'):
        host._create(selection, 'observation', b'failed evidence', ordinal=0)
    assert capture._observation_paths(selection) == ()
    failed = list((root / 'observations.pending').iterdir())
    assert len(failed) == 1
    assert read_regular(str(failed[0]), 'failed', max_bytes=100).captured.raw == b'failed evidence'
    monkeypatch.setattr(io.os, 'link', original_link)
    published = host._create(selection, 'observation', b'complete evidence', ordinal=0)
    assert capture._observation_paths(selection) == (published.pin.path,)
    assert failed[0].read_bytes() == b'failed evidence'
