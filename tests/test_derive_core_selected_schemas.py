"""Explicit derivation schemas govern projection, identity and validation."""
import hashlib
import inspect
import json
from pathlib import Path
import socket
import subprocess

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import derive_core as projection
from data_sheets_schema.cli import cli
from data_sheets_schema.d4d_pair_consistency import load_pair_schema, validate_pair_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("derivation requires no network or provider calls")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.fixture(scope="module")
def selected_schemas(tmp_path_factory):
    root = tmp_path_factory.mktemp("selected-complete-schemas")
    paths = []
    for filename, cls in (("data_sheets_schema_all.yaml", "Dataset"),
                          ("data_sheets_schema_core_all.yaml", "CoreDataset")):
        # Keep the complete production schema, including the File,
        # FileCollection and CoreDistribution projection contracts.
        value = yaml.safe_load((ROOT / "src/data_sheets_schema/schema" / filename).read_bytes())
        value["classes"][cls].setdefault("attributes", {})["selected_note"] = {
            "range": "string", "required": True, "pattern": "^selected:"}
        path = root / filename
        path.write_text(yaml.safe_dump(value, sort_keys=False))
        paths.append(path)
    return tuple(paths)


def full_record():
    return {"id": "https://example.org/offline-dataset", "name": "Offline",
            "title": "Offline derivation", "description": "Synthetic local validation only.",
            "selected_note": "selected: supplied full record",
            "file_collections": [{"id": "https://example.org/files", "name": "Files",
                "resources": [{"id": "https://example.org/data.csv", "name": "data.csv",
                               "format": "CSV", "bytes": 5}]}]}


def write_full(tmp_path, value=None):
    path = tmp_path / "full.yaml"
    text = ("# D4D Datasheet for Offline Dataset\n"
            "# Generation Method: offline fixture\n"
            "# Source bundle: offline.txt\n"
            "# Schema: selected-full.yaml\n\n")
    path.write_text(text + yaml.safe_dump(full_record() if value is None else value))
    return path


@pytest.mark.parametrize("option", ["--full-schema", "--core-schema"])
@pytest.mark.parametrize("validate", [True, False])
def test_one_schema_option_refuses_before_write_or_validation(tmp_path, monkeypatch, option, validate):
    full = write_full(tmp_path)
    schema = tmp_path / "schema.yaml"
    schema.write_text("name: unused\n")
    out = tmp_path / "out" / "core.yaml"
    def forbidden(*args, **kwargs):
        pytest.fail("unpaired schema selection reached a writer or subprocess")
    monkeypatch.setattr(projection, "write_core", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    argv = ["derive", "core", "--full", str(full), "--out", str(out), option, str(schema)]
    if not validate:
        argv.append("--no-validate")
    result = CliRunner().invoke(cli, argv)
    assert result.exit_code == 2, result.output
    assert "--full-schema and --core-schema must be supplied together" in result.output
    assert not out.parent.exists()


@pytest.mark.parametrize("phase4", [False, True])
def test_actual_cli_uses_selected_projection_identity_and_validator(tmp_path, selected_schemas, phase4):
    full_schema, core_schema = selected_schemas
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in selected_schemas}
    full = write_full(tmp_path)
    full_before = full.read_bytes()
    out = tmp_path / "core.yaml"
    argv = ["derive", "core", "--full", str(full), "--out", str(out),
            "--full-schema", str(full_schema), "--core-schema", str(core_schema)]
    if phase4:
        argv.append("--phase4-complete")
    result = CliRunner().invoke(cli, argv)
    assert result.exit_code == 0, result.output
    assert "linkml-validate: No issues found" in result.output
    text = out.read_text()
    core = yaml.safe_load(text)
    assert core["selected_note"] == full_record()["selected_note"]
    assert core["conforms_to_schema"] == str(core_schema)
    assert f"# Schema: {core_schema}\n" in text
    assert ("# Phase 4 reconciliation: completed" in text) is phase4
    assert core["distributions"][1]["format"] == "CSV"
    assert core["distributions"][1]["bytes"] == 5
    pair = load_pair_schema(full_schema, core_schema)
    assert not validate_pair_data(full_record(), core, pair).errors
    assert json.loads(result.output.splitlines()[1])["derived"] is True
    assert full.read_bytes() == full_before
    assert before == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in selected_schemas}


def test_actual_cli_selected_validation_rejects_missing_selected_required_slot(tmp_path, selected_schemas):
    value = full_record()
    del value["selected_note"]
    full = write_full(tmp_path, value)
    out = tmp_path / "core.yaml"
    full_schema, core_schema = selected_schemas
    result = CliRunner().invoke(cli, ["derive", "core", "--full", str(full), "--out", str(out),
        "--full-schema", str(full_schema), "--core-schema", str(core_schema)])
    assert result.exit_code == 1, result.output
    assert "derived core does not validate" in result.output
    assert "selected_note" in result.output
    # Failed output is retained, as on the original CLI path.
    assert out.exists()
    assert yaml.safe_load(out.read_text())["conforms_to_schema"] == str(core_schema)


def test_identity_keyword_reaches_all_library_outputs(tmp_path, selected_schemas):
    full_schema, core_schema = selected_schemas
    pair = load_pair_schema(full_schema, core_schema)
    full = write_full(tmp_path)
    identity = str(core_schema)
    for function in (projection.derive_core, projection.core_header, projection.core_text, projection.write_core):
        assert inspect.signature(function).parameters["core_schema_identity"].kind is inspect.Parameter.KEYWORD_ONLY
    derived = projection.derive_core(full_record(), pair, core_schema_identity=identity)
    header = projection.core_header(full.read_text(), full, core_schema_identity=identity)
    text, facts = projection.core_text(full, pair, core_schema_identity=identity)
    out = tmp_path / "core.yaml"
    written_facts = projection.write_core(full, out, pair, core_schema_identity=identity)
    assert derived["conforms_to_schema"] == identity
    assert f"# Schema: {identity}" in header
    assert yaml.safe_load(text)["conforms_to_schema"] == identity
    assert out.read_text() == text and written_facts == facts


def test_omitted_cli_flags_retain_default_call_and_validation_path(tmp_path, monkeypatch):
    """Assert the original public call shape as well as the default identity."""
    from data_sheets_schema import resources
    full = write_full(tmp_path)
    out = tmp_path / "core.yaml"
    writes = []
    commands = []
    def write(*args, **kwargs):
        writes.append((args, kwargs))
        return {"derived": True}
    def run(argv, **kwargs):
        commands.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, "No issues found", "")
    monkeypatch.setattr(projection, "write_core", write)
    monkeypatch.setattr(subprocess, "run", run)
    result = CliRunner().invoke(cli, ["derive", "core", "--full", str(full), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert writes == [((full, out), {"phase4_complete": False})]
    assert commands == [([*resources.linkml_validate(), "-s", str(resources.resource_path(projection.CORE_SCHEMA_REL)),
                          "-C", "CoreDataset", str(out)], {"capture_output": True, "text": True})]
