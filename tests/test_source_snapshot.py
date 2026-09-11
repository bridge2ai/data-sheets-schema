"""Rebuild keys and generator inputs must use the same captured source bytes (#1262)."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest

from data_sheets_schema import schema_sync


def source_text(word):
    return ("id: https://example.org/source\nname: source\ndefault_range: string\n"
            "classes:\n  Dataset:\n    attributes:\n      title:\n"
            f"        description: Enter a {word}.\n")


@pytest.mark.parametrize("part", ["source", "module"])
def test_same_size_same_mtime_source_change_invalidates_a_warm_rebuild(tmp_path, monkeypatch, part):
    source = tmp_path / "source.yaml"
    source.write_text("id: https://example.org/source\nname: source\nimports: [module]\n")
    module = tmp_path / "module.yaml"
    module.write_text(source_text("country"))
    if part == "source":
        source.write_text(source_text("country"))
    target = tmp_path / "data_sheets_schema_all.yaml"
    calls = []

    def generate(command, **kwargs):
        calls.append(command)
        root = Path(command[-1])
        content = root.read_bytes() if part == "source" else root.with_name("module.yaml").read_bytes()
        Path(command[command.index("-o") + 1]).write_bytes(content)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(schema_sync.subprocess, "run", generate)
    assert schema_sync._regenerate(source, target, False) == (True, None)
    before = target.read_bytes()
    changed = source if part == "source" else module
    stat = changed.stat()
    changed.write_text(changed.read_text().replace("country", "species"))
    os.utime(changed, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert changed.stat().st_size == stat.st_size
    assert schema_sync._regenerate(source, target, False) == (True, None)
    assert len(calls) == 2
    assert target.read_bytes() != before
    assert b"species" in target.read_bytes()


def test_generator_reads_the_snapshot_when_live_source_changes(tmp_path, monkeypatch):
    source = tmp_path / "source.yaml"
    original = source_text("country")
    source.write_text(original)
    target = tmp_path / "data_sheets_schema_all.yaml"

    def generate(command, **kwargs):
        source.write_text(source_text("species"))
        Path(command[command.index("-o") + 1]).write_bytes(Path(command[-1]).read_bytes())
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(schema_sync.subprocess, "run", generate)
    assert schema_sync._regenerate(source, target, False) == (True, None)
    assert target.read_text() == original


def test_real_gate_rejects_same_timestamp_source_edit_after_cache_warmup(tmp_path):
    source = tmp_path / "source.yaml"
    source.write_text(source_text("country"))
    merged = tmp_path / "data_sheets_schema_all.yaml"
    assert schema_sync._regenerate(source, merged, False) == (True, None)
    assert schema_sync.check_one(merged, source, "Dataset")["status"] == schema_sync.IN_SYNC
    stat = source.stat()
    source.write_text(source_text("species"))
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    row = schema_sync.check_one(merged, source, "Dataset")
    try:
        assert row["status"] == schema_sync.STALE, row
    finally:
        if "rebuilt_at" in row:
            shutil.rmtree(Path(row["rebuilt_at"]).parent)


def test_relative_import_outside_source_directory_is_captured(tmp_path, monkeypatch):
    directory = tmp_path / "source"
    directory.mkdir()
    dependencies = tmp_path / "definitions"
    dependencies.mkdir()
    module = dependencies / "base.yaml"
    original = source_text("country")
    module.write_text(original)
    source = directory / "source.yaml"
    source.write_text("id: https://example.org/source\nname: source\nimports: [../definitions/base]\n")
    target = directory / "data_sheets_schema_all.yaml"

    def generate(command, **kwargs):
        module.write_text(source_text("species"))
        copied_module = Path(command[-1]).parent / "../definitions/base.yaml"
        Path(command[command.index("-o") + 1]).write_bytes(copied_module.read_bytes())
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(schema_sync.subprocess, "run", generate)
    assert schema_sync._regenerate(source, target, False) == (True, None)
    assert target.read_text() == original


def test_logical_source_name_is_preserved_when_yaml_wraps_a_path_with_spaces(tmp_path):
    import yaml
    directory = tmp_path / ("a long directory name with spaces " * 3)
    directory.mkdir()
    source = directory / "my schema.yaml"
    source.write_text(source_text("country"))
    target = tmp_path / "data_sheets_schema_all.yaml"
    assert schema_sync._regenerate(source, target, False) == (True, None)
    assert yaml.safe_load(target.read_bytes())["source_file"] == str(source)


@pytest.mark.parametrize("layout", ["import_alias", "source_alias", "unicode"])
def test_snapshot_matches_direct_generation_for_supported_source_paths(tmp_path, layout):
    directory = tmp_path / "input"
    directory.mkdir()
    source = directory / ("schéma.yaml" if layout == "unicode" else "source.yaml")
    if layout == "import_alias":
        common = tmp_path / "common"
        common.mkdir()
        base = common / "base.yaml"
        base.write_text(source_text("country"))
        (directory / "base.yaml").symlink_to(base)
        source.write_text("id: https://example.org/root\nname: root\nimports: [base]\n")
    elif layout == "source_alias":
        original = tmp_path / "original.yaml"
        original.write_text(source_text("country"))
        source.symlink_to(original)
    else:
        source.write_text(source_text("country"))
    direct = tmp_path / "direct.yaml"
    subprocess.run(["poetry", "run", "gen-linkml", "-f", "yaml", "-o", str(direct), str(source)],
                   check=True, capture_output=True, text=True)
    rebuilt = tmp_path / "rebuilt.yaml"
    assert schema_sync._regenerate(source, rebuilt, False) == (True, None)
    assert rebuilt.read_bytes() == direct.read_bytes()
