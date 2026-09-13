"""Run the selected agentic playbook checks with external-only inputs (#1507)."""
from dataclasses import replace
from pathlib import Path
import shlex
import socket

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking
from data_sheets_schema.cli import cli
from tests.test_generation_manifest_identity import external


@pytest.fixture
def selected(external, monkeypatch, tmp_path):
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("network forbidden"))
    monkeypatch.setattr(api, "CONCAT_DIR", tmp_path / "outputs")
    data = yaml.safe_load(external.manifest.read_bytes())
    data["scope"] = {external.project: {"referent": "External cohort", "referent_id": "example:cohort",
        "related_but_distinct": [{"name": "Other cohort", "id": "example:other", "express_as": "related_datasets"}]}}
    external.manifest.write_text(yaml.safe_dump(data))
    custom = tmp_path / "selected chunk map.yaml"
    custom.write_text(chunking.dump_manifest(chunking.build_manifest(external.bundle,
        {**chunking.DEFAULT_RULE, "max_lines": 3, "version": "2-custom"})))
    # A usable default sidecar must never hide failure to select the custom map.
    external.chunk_manifest.unlink()
    return replace(external, chunk_manifest=custom, runtime="Claude Code", condition="generic_v9",
                   out_dir=None, method="external_agent", label="synthetic label")


def commands(spec):
    marker = "## Selected inputs for all four phases (renderer v4)"
    assert marker in spec.instruction
    text = spec.instruction.split(marker, 1)[1]
    return [shlex.split(line)[3:] for line in text.splitlines() if line.startswith("poetry run d4d ")]


def test_agentic_prescribed_checks_read_only_selected_inputs_and_current_records(selected):
    spec = selected
    rows = commands(spec)
    chunk = next(row for row in rows if row[:2] == ["bundle", "chunk"])
    assert chunk[chunk.index("--bundle") + 1] == str(spec.bundle)
    assert chunk[chunk.index("--chunk-manifest") + 1] == str(spec.chunk_manifest)
    before = spec.bundle.read_bytes(), spec.manifest.read_bytes(), spec.chunk_manifest.read_bytes()
    checked = CliRunner().invoke(cli, chunk)
    assert checked.exit_code == 0 and "current" in checked.output, checked.output
    scopes = [row for row in rows if row[:2] == ["download", "scope"]]
    assert len(scopes) == 2
    for path in (spec.full_path, spec.core_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("id: example:cohort\n")
    previous = spec.full_path.parent.parent / "prior" / spec.full_path.name
    previous.parent.mkdir()
    previous.write_text("id: example:other\n")
    for row in scopes:
        assert row[row.index("--manifest") + 1] == str(spec.manifest)
        result = CliRunner().invoke(cli, row)
        assert result.exit_code == 0, result.output
        assert str(previous) not in result.output
        if "--check" in row:
            assert "2 record(s) checked" in result.output
    assert before == (spec.bundle.read_bytes(), spec.manifest.read_bytes(), spec.chunk_manifest.read_bytes())
    spec.full_path.write_text("id: example:other\n")
    check = next(row for row in scopes if "--check" in row)
    refused = CliRunner().invoke(cli, check)
    assert refused.exit_code == 1, refused.output


@pytest.mark.parametrize("damage", ["missing", "empty", "reordered", "digest"])
def test_prescribed_chunk_check_refuses_an_invalid_selected_map_without_rewriting(selected, damage):
    spec = selected
    row = next(row for row in commands(spec) if row[:2] == ["bundle", "chunk"])
    if damage == "missing":
        spec.chunk_manifest.unlink()
    else:
        data = yaml.safe_load(spec.chunk_manifest.read_bytes())
        if damage == "empty":
            data["chunks"], data["chunk_count"] = [], 0
        elif damage == "reordered":
            data["chunks"].reverse()
        else:
            data["bundle_sha256"] = "0" * 64
        spec.chunk_manifest.write_text(chunking.dump_manifest(data))
    before = spec.chunk_manifest.read_bytes() if spec.chunk_manifest.exists() else None
    result = CliRunner().invoke(cli, row)
    assert result.exit_code == 1, result.output
    assert (spec.chunk_manifest.read_bytes() if spec.chunk_manifest.exists() else None) == before
    assert not chunking.manifest_for(spec.bundle).exists()


def test_no_source_manifest_skips_scope_checks_and_records_the_resolved_chunk_path(selected):
    selected.chunk_manifest.replace(chunking.manifest_for(selected.bundle))
    spec = replace(selected, manifest=None, chunk_manifest=None,
                   manifest_line=api.RunSpec.__dataclass_fields__["manifest_line"].default)
    rows = commands(spec)
    assert not any(row[:2] == ["download", "scope"] for row in rows)
    assert "No source manifest is used" in spec.instruction
    assert spec.render_spec()["chunk_manifest"] == str(chunking.manifest_for(spec.bundle))
    restored = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                           method=spec.method, label=spec.label)
    assert restored.instruction == spec.instruction
    row = next(row for row in rows if row[:2] == ["bundle", "chunk"])
    result = CliRunner().invoke(cli, row)
    assert result.exit_code == 0, result.output


def test_agentic_scope_and_transcript_paths_replay_after_output_root_moves(selected, monkeypatch, tmp_path):
    instruction = selected.instruction
    recorded = selected.render_spec()
    monkeypatch.setattr(api, "CONCAT_DIR", tmp_path / "another output root")
    restored = api.RunSpec.from_render_spec(recorded, project=selected.project,
        method=selected.method, label=selected.label)
    assert restored.instruction == instruction
    assert restored.render_spec() == recorded
