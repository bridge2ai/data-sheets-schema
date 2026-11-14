"""Fault injection for retained create-once evidence; no native execution."""
import pytest

from data_sheets_schema import native_shared_callback_io as io
from data_sheets_schema.native_shared_evidence import read_regular


def test_attempt_engine_uses_single_link_failure_writer(tmp_path, monkeypatch):
    from data_sheets_schema import native_shared_execution_orchestration as engine
    effects = engine._engine_bindings()[1]
    for name in ('started.json', 'final.json'):
        directory = tmp_path / name
        directory.mkdir()
        _check_failure_writer(effects.durable_new, directory / name, monkeypatch)


def test_stage_uses_single_link_failure_writer(tmp_path, monkeypatch):
    from data_sheets_schema import native_shared_publication_orchestration as stage
    _check_failure_writer(stage.durable_new, tmp_path / 'stage.json', monkeypatch)


def test_results_uses_single_link_failure_writer(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from data_sheets_schema import native_shared_results_orchestration as results
    destination = tmp_path / 'attribution-replay.json'
    prepared = {'value': {'evidence_directory': str(tmp_path)}, 'pool': '{}',
                'snapshot': SimpleNamespace(verify_unchanged=lambda: None)}
    # Exercise the real results call site through its first create-once write.
    _check_failure_writer(lambda path, raw: results.write_report(prepared, path),
                          destination, monkeypatch, results=True)


def _check_failure_writer(writer, target, monkeypatch, results=False):
    original = OSError('post-link directory failure')
    def fail(path):
        raise original
    monkeypatch.setattr(io, '_sync_directory', fail)
    with pytest.raises(OSError) as caught:
        writer(target, b'complete')
    assert caught.value is original
    files = list(target.parent.iterdir())
    assert len(files) == 1 and files[0].stat().st_nlink == 1
    raw = read_regular(str(files[0]), 'retained', max_bytes=100000).captured.raw
    assert raw
    if not results:
        assert raw == b'complete'


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
