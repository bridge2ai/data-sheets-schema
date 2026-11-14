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
