"""Publication failures must never expose a partial record or overwrite a winner."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from data_sheets_schema import rocrate_normalize as normalizer


@pytest.fixture
def publication(tmp_path):
    packages = tmp_path / "packages"
    source = packages / "ALPHA" / "processed" / "ALPHA_crate_d4d.yaml"
    source.parent.mkdir(parents=True)
    source.write_text("# normalizer header\nid: ALPHA\nname: Café\n", encoding="utf-8")
    concat = tmp_path / "published"
    target = concat / "rocrate_mapped" / "v1" / "ALPHA_d4d.yaml"

    def publish():
        return normalizer.emit_deterministic_arm("ALPHA", "v1", packages, concat)
    return publish, target


def test_partial_write_failure_leaves_no_record_and_can_be_retried(publication, monkeypatch):
    publish, target = publication
    real_tempfile = normalizer.tempfile.NamedTemporaryFile

    class PartialWrite:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.stream.close()

        def write(self, text):
            self.stream.write(text[:len(text) // 2])
            self.stream.flush()
            assert not target.exists()
            raise OSError("disk full")

    def temporary(**kwargs):
        wrapper = PartialWrite()
        wrapper.stream = real_tempfile(**kwargs)
        wrapper.name = wrapper.stream.name
        return wrapper

    with monkeypatch.context() as patch:
        patch.setattr(normalizer.tempfile, "NamedTemporaryFile", temporary)
        with pytest.raises(OSError, match="disk full"):
            publish()
    assert not target.exists()
    assert list(target.parent.iterdir()) == []
    assert publish() == target
    assert "name: Café\n" in target.read_text(encoding="utf-8")
    assert "normalizer header" not in target.read_text(encoding="utf-8")
    assert list(target.parent.iterdir()) == [target]


def test_link_failure_leaves_no_record_or_staging_file(publication, monkeypatch):
    publish, target = publication

    def fail(*args):
        raise PermissionError("cannot publish")
    monkeypatch.setattr(normalizer.os, "link", fail)
    with pytest.raises(PermissionError, match="cannot publish"):
        publish()
    assert list(target.parent.iterdir()) == []


def test_concurrent_publish_has_one_winner_and_never_overwrites(publication, monkeypatch):
    publish, target = publication
    link = normalizer.os.link
    ready = Barrier(2)

    def synchronized_link(source, destination):
        ready.wait(timeout=10)
        link(source, destination)
    monkeypatch.setattr(normalizer.os, "link", synchronized_link)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish) for _ in range(2)]
        errors = [future.exception() for future in futures]
    assert errors.count(None) == 1
    loser = next(error for error in errors if error is not None)
    assert isinstance(loser, FileExistsError)
    assert "use a new version label" in str(loser)
    assert list(target.parent.iterdir()) == [target]
    assert target.read_text(encoding="utf-8").endswith("id: ALPHA\nname: Café\n")


def test_dangling_symlink_is_not_replaced(publication):
    publish, target = publication
    target.parent.mkdir(parents=True)
    target.symlink_to(target.parent / "missing")
    with pytest.raises(FileExistsError, match="use a new version label"):
        publish()
    assert target.is_symlink()
    assert list(target.parent.iterdir()) == [target]


def test_staging_cleanup_failure_does_not_report_published_record_as_failed(
        publication, monkeypatch, caplog):
    publish, target = publication
    unlink = Path.unlink

    def fail_for_staging(path, *args, **kwargs):
        if path.suffix == ".tmp":
            raise PermissionError("cleanup denied")
        return unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", fail_for_staging)
    assert publish() == target
    assert target.read_text(encoding="utf-8").endswith("id: ALPHA\nname: Café\n")
    assert "Could not remove publication temporary file" in caplog.text
