"""Hash and parse one snapshot even when a file changes between reads (#1260)."""

from pathlib import Path

import pytest

from data_sheets_schema import schema_digest as digest, schema_view


def schema(slot):
    return ("id: https://example.org/snapshot\nname: snapshot\n"
            "default_range: string\nclasses:\n  Example:\n"
            f"    attributes:\n      {slot}: {{}}\n").encode()


def replace_after_read(monkeypatch, path, replacement):
    read = Path.read_bytes
    replaced = False

    def racing_read(p):
        nonlocal replaced
        content = read(p)
        if p.resolve() == path.resolve() and not replaced:
            replaced = True
            path.write_bytes(replacement)
        return content

    monkeypatch.setattr(Path, "read_bytes", racing_read)


@pytest.mark.parametrize("consumer", ["build", "text", "view"])
def test_schema_replacement_after_hashing_cannot_poison_cache(tmp_path, monkeypatch, consumer):
    path = tmp_path / "schema.yaml"
    original = schema("alpha")
    path.write_bytes(original)
    replace_after_read(monkeypatch, path, schema("bravo"))

    def read():
        if consumer == "text":
            return digest.digest_text("Example", path)
        if consumer == "build":
            return [s.name for s in digest.build("Example", path).slots]
        return [str(s.name) for s in schema_view.shared_view(path).class_induced_slots("Example")]

    first = read()
    assert ("## `alpha`" in first if consumer == "text" else first == ["alpha"])
    path.write_bytes(original)
    assert read() == first


@pytest.mark.parametrize("consumer", ["vocabulary", "text"])
def test_vocabulary_replacement_after_hashing_cannot_poison_cache(tmp_path, monkeypatch, consumer):
    path = tmp_path / "schema.yaml"
    path.write_bytes(schema("alpha").replace(b"alpha: {}", b"alpha:\n        values_from: [TEST]"))
    pin = tmp_path / "vocabularies.yaml"
    original = b"vocabularies:\n  TEST:\n    TEST:1: first\n"
    pin.write_bytes(original)
    monkeypatch.setattr(digest, "VOCABULARY_PIN", pin)
    monkeypatch.setattr(digest, "_VOCABULARIES", None)
    replace_after_read(monkeypatch, pin, original.replace(b"first", b"other"))

    def read():
        if consumer == "vocabulary":
            return digest.vocabularies()["TEST"]["TEST:1"]
        return digest.digest_text("Example", path)

    first = read()
    assert (first == "first" if consumer == "vocabulary" else "1=first" in first)
    pin.write_bytes(original)
    assert read() == first


def test_snapshot_view_resolves_relative_imports_from_the_original_directory(tmp_path, monkeypatch):
    directory = tmp_path / "schemas"
    directory.mkdir()
    (directory / "base.yaml").write_text(
        "id: https://example.org/base\nname: base\ndefault_range: string\n"
        "classes:\n  Base:\n    attributes:\n      alpha: {}\n")
    path = directory / "schema.yaml"
    path.write_text("id: https://example.org/child\nname: child\nimports: [base]\n"
                    "classes:\n  Example:\n    is_a: Base\n")
    monkeypatch.chdir(tmp_path)
    assert [str(s.name) for s in schema_view.shared_view(path).class_induced_slots("Example")] == ["alpha"]
