"""An output write refreshes that file without reparsing unrelated schemas."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import threading

import pytest
import yaml

from data_sheets_schema import schema_cache as cache


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def write(path, text, timestamp=1_000_000_000):
    path.write_text(text)
    os.utime(path, ns=(timestamp, timestamp))


def test_writing_a_record_keeps_an_unrelated_schema_cached(tmp_path, monkeypatch):
    schema, record = tmp_path / "schema.yaml", tmp_path / "record.yaml"
    write(schema, "classes: {Dataset: {}}\n")
    write(record, "value: 1\n")
    expected = cache.load_yaml(schema)
    assert cache.load_yaml(record) == {"value": 1}
    write(record, "value: 2\n")
    cache.forget(record)
    assert cache.load_yaml(record) == {"value": 2}

    def unexpected_parse(*args, **kwargs):
        pytest.fail("writing a record evicted the unchanged schema")

    monkeypatch.setattr(cache.yaml, "safe_load", unexpected_parse)
    assert cache.load_yaml(schema) == expected


@pytest.mark.parametrize("alias", ["relative", "symlink", "hardlink"])
def test_forget_invalidates_aliases_after_an_invisible_rewrite(tmp_path, monkeypatch, alias):
    path = tmp_path / "record.yaml"
    write(path, "value: 1\n")
    if alias == "relative":
        monkeypatch.chdir(tmp_path)
        other = Path("record.yaml")
    else:
        other = tmp_path / "alias.yaml"
        if alias == "symlink":
            other.symlink_to(path)
        else:
            os.link(path, other)
    assert cache.load_yaml(path) == cache.load_yaml(other) == {"value": 1}
    before = cache.sha256_of(path)
    assert cache.sha256_of(other) == before
    write(other, "value: 2\n")
    cache.forget(other)
    assert cache.load_yaml(path) == cache.load_yaml(other) == {"value": 2}
    assert cache.sha256_of(path) == cache.sha256_of(other) != before


def test_atomic_replacement_is_fresh_even_with_identical_size_and_mtime(tmp_path):
    path, replacement = tmp_path / "record.yaml", tmp_path / "replacement.yaml"
    write(path, "value: 1\n")
    assert cache.load_yaml(path) == {"value": 1}
    before = cache.sha256_of(path)
    write(replacement, "value: 2\n")
    replacement.replace(path)
    assert cache.load_yaml(path) == {"value": 2}
    assert cache.sha256_of(path) != before


def test_forgetting_a_deleted_file_also_invalidates_its_cached_hardlink(tmp_path):
    path, alias = tmp_path / "record.yaml", tmp_path / "alias.yaml"
    write(path, "value: 1\n")
    os.link(path, alias)
    assert cache.load_yaml(path) == cache.load_yaml(alias) == {"value": 1}
    path.unlink()
    write(alias, "value: 2\n")
    cache.forget(path)
    assert cache.load_yaml(alias) == {"value": 2}
    with pytest.raises(FileNotFoundError):
        cache.load_yaml(path)


def test_invalid_yaml_is_not_retained_as_a_successful_read(tmp_path):
    path = tmp_path / "bad.yaml"
    write(path, "value: [\n")
    with pytest.raises(yaml.YAMLError):
        cache.load_yaml(path)
    write(path, "value: 2\n")
    assert cache.load_yaml(path) == {"value": 2}


def test_cache_is_bounded_and_reuses_the_most_recent_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "_MAX_PARSED_FILES", 2)
    paths = [tmp_path / f"{i}.yaml" for i in range(3)]
    for i, path in enumerate(paths):
        write(path, f"value: {i}\n")
    for path in (paths[0], paths[1], paths[0], paths[2]):
        cache.load_yaml(path)
    assert len(cache._PARSED) == 2

    with monkeypatch.context() as hit:
        hit.setattr(cache.yaml, "safe_load", lambda *args: pytest.fail("recent entry evicted"))
        assert cache.load_yaml(paths[0]) == {"value": 0}
    assert cache.load_yaml(paths[1]) == {"value": 1}
    assert len(cache._PARSED) == 2


def test_an_in_flight_parse_cannot_reinsert_stale_data_after_forget(tmp_path, monkeypatch):
    path = tmp_path / "record.yaml"
    write(path, "value: 1\n")
    captured, release, invalidating = threading.Event(), threading.Event(), threading.Event()
    original = cache.yaml.safe_load

    def paused(text):
        captured.set()
        assert release.wait(10)
        return original(text)

    def invalidate():
        invalidating.set()
        cache.forget(path)

    monkeypatch.setattr(cache.yaml, "safe_load", paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        reading = pool.submit(cache.load_yaml, path)
        try:
            assert captured.wait(10)
            write(path, "value: 2\n")
            writing = pool.submit(invalidate)
            assert invalidating.wait(10)
        finally:
            release.set()
        assert reading.result(timeout=10) == {"value": 1}
        writing.result(timeout=10)
    assert cache.load_yaml(path) == {"value": 2}
