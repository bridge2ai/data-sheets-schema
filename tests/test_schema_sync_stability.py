"""Schema preflight must fail closed on changing inputs and repeated failures (#946)."""

from pathlib import Path
import shutil
import subprocess

import pytest

from data_sheets_schema import schema_digest, schema_sync, schema_view


def schema(slot):
    return ("id: https://example.org/stability\nname: stability\n"
            "default_range: string\nclasses:\n  Dataset:\n"
            f"    attributes:\n      {slot}: {{}}\n").encode()


@pytest.fixture
def inputs(tmp_path):
    directory = tmp_path / "schema"
    directory.mkdir()
    merged = directory / schema_digest.FULL_SCHEMA.name
    source = directory / "source.yaml"
    merged.write_bytes(schema("alpha"))
    source.write_bytes(schema("alpha"))
    return merged, source


def test_a_merged_file_changed_after_comparison_cannot_pass(inputs, monkeypatch):
    merged, source = inputs

    def regenerate(source, target, marker, **kwargs):
        target.write_bytes(merged.read_bytes())
        return True, None

    original = schema_digest.digest_text

    def change_then_digest(*args, **kwargs):
        merged.write_bytes(schema("bravo"))
        return original(*args, **kwargs)

    monkeypatch.setattr(schema_sync, "_regenerate", regenerate)
    monkeypatch.setattr(schema_digest, "digest_text", change_then_digest)
    row = schema_sync.check_one(merged, source, "Dataset")
    assert row["status"] == schema_sync.UNCHECKED
    assert "changed during" in row["reason"]
    assert schema_sync.blocking([row]) == [row]


def test_changed_then_restored_merged_bytes_cannot_attest_a_different_digest(inputs, monkeypatch):
    merged, source = inputs
    merged.write_bytes(schema("bravo"))
    wrong_digest_text = schema_digest.digest_text("Dataset", merged)
    merged.write_bytes(schema("alpha"))

    def regenerate(source, target, marker, **kwargs):
        target.write_bytes(schema("alpha"))
        return True, None

    def changed_cached_digest(*args, **kwargs):
        merged.write_bytes(schema("bravo"))
        return wrong_digest_text

    original_build = schema_digest._build_uncached

    def build_then_restore(*args, **kwargs):
        value = original_build(*args, **kwargs)
        merged.write_bytes(schema("alpha"))
        return value

    monkeypatch.setattr(schema_sync, "_regenerate", regenerate)
    monkeypatch.setattr(schema_digest, "digest_text", changed_cached_digest)
    monkeypatch.setattr(schema_digest, "_build_uncached", build_then_restore)
    row = schema_sync.check_one(merged, source, "Dataset")
    assert row["status"] != schema_sync.IN_SYNC
    assert schema_sync.blocking([row]) == [row]


def test_a_source_changed_during_regeneration_cannot_pass(inputs, monkeypatch):
    merged, source = inputs

    def regenerate(source, target, marker, **kwargs):
        target.write_bytes(merged.read_bytes())
        source.write_bytes(schema("bravo"))
        return True, None

    monkeypatch.setattr(schema_sync, "_regenerate", regenerate)
    row = schema_sync.check_one(merged, source, "Dataset")
    assert row["status"] == schema_sync.UNCHECKED
    assert "changed during" in row["reason"]


def test_a_vocabulary_changed_during_digesting_cannot_pass(inputs, tmp_path, monkeypatch):
    merged, source = inputs
    pin = tmp_path / "vocabulary.yaml"
    pin.write_text("vocabularies: {}\n")
    monkeypatch.setattr(schema_digest, "VOCABULARY_PIN", pin)

    def regenerate(source, target, marker, **kwargs):
        target.write_bytes(merged.read_bytes())
        return True, None

    original = schema_digest.digest_text

    def change_then_digest(*args, **kwargs):
        pin.write_text("vocabularies: {}\n# changed\n")
        return original(*args, **kwargs)

    monkeypatch.setattr(schema_sync, "_regenerate", regenerate)
    monkeypatch.setattr(schema_digest, "digest_text", change_then_digest)
    row = schema_sync.check_one(merged, source, "Dataset")
    assert row["status"] == schema_sync.UNCHECKED
    assert "changed during" in row["reason"]


def test_repeated_stale_checks_do_not_retain_more_views_or_digest_entries(inputs, monkeypatch):
    merged, source = inputs

    def regenerate(source, target, marker, **kwargs):
        target.write_bytes(schema("bravo"))
        return True, None

    monkeypatch.setattr(schema_sync, "_regenerate", regenerate)
    counts, rebuilt_digests, evidence = [], [], []
    try:
        for _ in range(3):
            row = schema_sync.check_one(merged, source, "Dataset")
            assert row["status"] == schema_sync.STALE, row
            path = Path(row["rebuilt_at"])
            evidence.append(path.parent)
            assert path.read_bytes() == schema("bravo")
            assert row["digest"] != row["digest_rebuilt"]
            rebuilt_digests.append(row["digest_rebuilt"])
            counts.append((schema_view.views_held(), len(schema_digest._BUILD_CACHE),
                           len(schema_digest._TEXT_CACHE)))
        assert counts[0] == counts[1] == counts[2]
        assert len(set(rebuilt_digests)) == 1
    finally:
        for directory in evidence:
            shutil.rmtree(directory)


@pytest.mark.parametrize("relative", [False, True])
def test_custom_schema_display_paths_still_compare_in_sync(inputs, monkeypatch, relative):
    merged, source = inputs
    custom = merged.with_name("custom.yaml")
    merged.rename(custom)
    monkeypatch.chdir(custom.parent)

    def regenerate(source, target, marker, **kwargs):
        target.write_bytes(custom.read_bytes())
        return True, None

    monkeypatch.setattr(schema_sync, "_regenerate", regenerate)
    row = schema_sync.check_one(Path(custom.name) if relative else custom, source, "Dataset")
    assert row["status"] == schema_sync.IN_SYNC, row
    assert row["digest"] == row["digest_rebuilt"]


@pytest.mark.parametrize("failure", ["timeout", "nonzero", "malformed"])
def test_rebuild_digest_failure_blocks_generation(inputs, monkeypatch, failure):
    merged, source = inputs
    monkeypatch.setattr(schema_sync, "_REBUILT_DIGESTS", {})

    def regenerate(source, target, marker, **kwargs):
        target.write_bytes(merged.read_bytes())
        return True, None

    def failed(*args, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args[0], 60)
        return subprocess.CompletedProcess(args[0], 1 if failure == "nonzero" else 0,
                                           stdout="unexpected output", stderr="digest failure")

    monkeypatch.setattr(schema_sync, "_regenerate", regenerate)
    monkeypatch.setattr(schema_sync.subprocess, "run", failed)
    row = schema_sync.check_one(merged, source, "Dataset")
    assert row["status"] == schema_sync.UNCHECKED
    assert schema_sync.blocking([row]) == [row]
