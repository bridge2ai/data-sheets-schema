"""A running generator must describe the schema that is currently on disk (#942)."""

import os
from pathlib import Path

import pytest

from data_sheets_schema import schema_digest as digest


def schema(slot):
    return ("id: https://example.org/cache\nname: cache\n"
            "default_range: string\nclasses:\n  Example:\n"
            f"    attributes:\n      {slot}: {{}}\n")


def test_same_size_same_timestamp_rewrite_refreshes_inventory_and_prompt(tmp_path):
    path = tmp_path / "schema.yaml"
    original = schema("alpha")
    path.write_text(original)
    first = digest.digest_text("Example", path)
    original_stat = path.stat()
    builds, texts = len(digest._BUILD_CACHE), len(digest._TEXT_CACHE)

    for name in ("bravo", "delta", "alpha"):
        path.write_text(schema(name))
        os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        assert path.stat().st_size == original_stat.st_size
        assert path.stat().st_mtime_ns == original_stat.st_mtime_ns
        assert digest.slot_names("Example", path) == [name]
        current = digest.digest_text("Example", path)
        assert f"## `{name}`" in current
        if name != "alpha":
            assert "## `alpha`" not in current
            assert digest.fingerprint(current) != digest.fingerprint(first)
        else:
            assert current == first
        assert len(digest._BUILD_CACHE) == builds
        assert len(digest._TEXT_CACHE) == texts


@pytest.mark.parametrize("explicit", [False, True])
def test_same_relative_path_in_different_working_directories(tmp_path, monkeypatch, explicit):
    monkeypatch.setitem(digest.CLASS_SCHEMA, "Example", Path("schema.yaml"))
    fingerprints = []
    for name in ("alpha", "bravo"):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "schema.yaml").write_text(schema(name))
        monkeypatch.chdir(directory)
        path = Path("schema.yaml") if explicit else None
        assert digest.slot_names("Example", path) == [name]
        fingerprints.append(digest.fingerprint(digest.digest_text("Example", path)))
    assert len(set(fingerprints)) == 2


def test_unchanged_schema_reuses_inventory_without_exposing_mutable_cache(tmp_path, monkeypatch):
    path = tmp_path / "schema.yaml"
    path.write_text(schema("alpha"))
    first = digest.build("Example", path)
    first.slots[0].name = "corrupted"
    text = digest.digest_text("Example", path)

    def unexpected_rebuild(*args, **kwargs):
        pytest.fail("an unchanged schema should reuse its cached inventory")

    monkeypatch.setattr(digest, "_build_uncached", unexpected_rebuild)
    assert digest.slot_names("Example", path) == ["alpha"]
    assert digest.digest_text("Example", path) == text


def test_custom_path_rendering_is_preserved_for_relative_and_absolute_calls(tmp_path, monkeypatch):
    path = tmp_path / "schema.yaml"
    path.write_text(schema("alpha"))
    monkeypatch.chdir(tmp_path)
    for source in (Path("schema.yaml"), path):
        text = digest.digest_text("Example", source)
        assert f"Derived from `{source}`." in text


def test_vocabulary_rewrite_refreshes_terms_and_prompt_without_schema_edit(tmp_path, monkeypatch):
    path = tmp_path / "schema.yaml"
    path.write_text(schema("alpha").replace("alpha: {}", "alpha:\n        values_from: [TEST]"))
    pin = tmp_path / "vocabularies.yaml"
    monkeypatch.setattr(digest, "VOCABULARY_PIN", pin)
    monkeypatch.setattr(digest, "_VOCABULARIES", None)
    fingerprints = []
    for word in ("first", "other"):
        pin.write_text(f"vocabularies:\n  TEST:\n    TEST:1: {word}\n")
        assert digest.vocabularies()["TEST"]["TEST:1"] == word
        text = digest.digest_text("Example", path)
        assert f"1={word}" in text
        fingerprints.append(digest.fingerprint(text))
    assert len(set(fingerprints)) == 2
