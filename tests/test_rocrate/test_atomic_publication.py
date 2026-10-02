"""Publication failures must never expose a partial record or overwrite a winner."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import stat
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
    write_text = Path.write_text

    def partial_write(path, text, **kwargs):
        if path.suffix != ".tmp":
            return write_text(path, text, **kwargs)
        write_text(path, text[:len(text) // 2], **kwargs)
        assert not target.exists()
        raise OSError("disk full")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "write_text", partial_write)
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
    assert "Could not remove publication temporary path" in caplog.text


@pytest.mark.parametrize("mask", [0o022, 0o002, 0o077])
def test_published_permissions_match_ordinary_file_creation(publication, tmp_path, mask):
    publish, target = publication
    # Only the test changes umask, restoring it even on failure. Production
    # leaves that process-global setting alone.
    previous = os.umask(mask)
    try:
        ordinary = tmp_path / "ordinary.yaml"
        ordinary.write_text("id: ALPHA\n", encoding="utf-8")
        publish()
    finally:
        os.umask(previous)
    assert stat.S_IMODE(target.stat().st_mode) == stat.S_IMODE(ordinary.stat().st_mode)
    assert stat.S_IMODE(target.stat().st_mode) == 0o666 & ~mask
