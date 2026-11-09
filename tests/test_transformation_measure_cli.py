"""D105 offline saved-record boundary and separation from registered v4."""
from __future__ import annotations

import hashlib
import json

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema.cli.receipts import receipts
from data_sheets_schema.cli import cli
from data_sheets_schema.derive_core import derive_core
from data_sheets_schema import transformation_measure_io as io


def test_transform_cli_canary_is_deterministic_and_read_only(tmp_path, monkeypatch):
    full = {"id": "example:d105", "name": "saved record", "receipts": {"coverage": 7}}
    core = derive_core(full)
    full_path, core_path = tmp_path / "full.yaml", tmp_path / "core.yaml"
    full_path.write_text(yaml.safe_dump(full), encoding="utf-8")
    core_path.write_text(yaml.safe_dump(core), encoding="utf-8")
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    monkeypatch.chdir(tmp_path)
    args = ["receipts", "transform", "--full", str(full_path), "--core", str(core_path)]
    first = CliRunner().invoke(cli, args)
    second = CliRunner().invoke(cli, args)
    assert first.exit_code == second.exit_code == 0, first.output
    assert first.output == second.output
    report = json.loads(first.output)
    assert report["matches_derived_core"] is True
    assert report["scope"]["gating"] is False
    assert report["scope"]["primary_receipt_instrument"] == "v4"
    assert "receipts" not in report and "tool_receipts" not in report
    assert report["input_file_sha256"] == {
        "full": hashlib.sha256(before[full_path]).hexdigest(),
        "core": hashlib.sha256(before[core_path]).hexdigest(),
    }
    assert {p: p.read_bytes() for p in tmp_path.iterdir()} == before
    (tmp_path / "canary_receipt.json").write_text(first.output, encoding="utf-8")
    assert json.loads((tmp_path / "canary_receipt.json").read_text()) == report


def test_mismatch_is_reported_without_gating(tmp_path):
    full, core = tmp_path / "full.json", tmp_path / "core.json"
    full.write_text('{"id": "example:full"}')
    core.write_text('{"id": "example:changed"}')
    result = CliRunner().invoke(receipts, ["transform", "--full", str(full), "--core", str(core)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["matches_derived_core"] is False
    assert report["counts"]["mismatched"] >= 1
    assert not report["scope"]["gating"]


@pytest.mark.parametrize("text", [
    "id: a\nid: b\n", '{"id":"a","id":"b"}',
    "1: value\n", "id: &a [*a]\n", "id: !unknown value\n",
    "id: a\n---\nid: b\n", "- not a record\n", "",
    "id: a\nx: {<<: {name: merged}}\n", "x: " + "[" * 130 + "0" + "]" * 130,
])
def test_unambiguous_record_boundary(tmp_path, text):
    path = tmp_path / "invalid.yaml"
    path.write_text(text)
    with pytest.raises(ValueError):
        io.read_record(path)


def test_byte_limit_and_invalid_utf8(tmp_path, monkeypatch):
    path = tmp_path / "record.yaml"
    monkeypatch.setattr(io, "MAX_RECORD_BYTES", 8)
    path.write_bytes(b"id: too big\n")
    with pytest.raises(ValueError, match="exceeds"):
        io.read_record(path)
    path.write_bytes(b"id: \xff")
    with pytest.raises(ValueError, match="UTF-8"):
        io.read_record(path)


def test_bytes_are_pinned_separately_from_semantics(tmp_path):
    full, core = tmp_path / "full.yaml", tmp_path / "core.yaml"
    full.write_text("id: example:saved\n")
    core.write_text(yaml.safe_dump(derive_core({"id": "example:saved"})))
    first = io.measure_files(full, core)
    full.write_text("# retained original header\nid: example:saved\n")
    second = io.measure_files(full, core)
    assert first["input_file_sha256"]["full"] != second["input_file_sha256"]["full"]
    assert first["input_digests"] == second["input_digests"]


def test_cli_has_no_gate_or_record_write_options():
    result = CliRunner().invoke(receipts, ["transform", "--help"])
    assert result.exit_code == 0
    assert "--strict" not in result.output
    assert "--write" not in result.output


@pytest.mark.parametrize("scalar", ["2026-11-09", "2026-11-09T01:02:03Z"])
def test_yaml_date_and_timestamp_are_distinct_from_text(tmp_path, scalar):
    full, core = tmp_path / "full.yaml", tmp_path / "core.yaml"
    full.write_text(f"id: example:dates\ndescription: {scalar}\n")
    doc, _ = io.read_record(full)
    projected = derive_core(doc)
    core.write_text(yaml.safe_dump(projected))
    assert io.measure_files(full, core)["matches_derived_core"] is True
    projected["description"] = scalar
    core.write_text(yaml.safe_dump(projected))
    result = io.measure_files(full, core)
    row = next(row for row in result["core_leaves"] if row["target_path"] == "/description")
    assert row["status"] == "mismatched"
    assert row["source_paths"] == []


@pytest.mark.parametrize("scalar", [".nan", ".inf", "-.inf", "!!binary YQ=="])
def test_unsupported_values_are_input_errors(tmp_path, scalar):
    full, core = tmp_path / "full.yaml", tmp_path / "core.yaml"
    full.write_text(f"id: example:invalid\ndescription: {scalar}\n")
    core.write_text("id: example:invalid\n")
    result = CliRunner().invoke(receipts, ["transform", "--full", str(full), "--core", str(core)])
    assert result.exit_code != 0
    assert "transformation measurement refused" in result.output
