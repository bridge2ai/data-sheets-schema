"""D105 offline saved-record boundary and separation from registered v4."""
from __future__ import annotations

import hashlib
import json
import importlib.util
from pathlib import Path
import sys

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
    assert report["diagnostic"]["counts"]["mismatched"] >= 1
    assert report["verification_result"]["verified"] is False
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
    assert first["diagnostic"]["input_digests"] == second["diagnostic"]["input_digests"]


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
    row = next(row for row in result["diagnostic"]["core_leaves"] if row["target_path"] == "/description")
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


@pytest.mark.parametrize("suffix", [".json", ".yaml"])
def test_json_exponents_use_json_number_semantics(tmp_path, suffix):
    path = tmp_path / ("record" + suffix)
    path.write_text('{"id":"a","bytes":1e5,"other":2E-3}')
    value, _ = io.read_record(path)
    assert type(value["bytes"]) is float and value["bytes"] == 100000.0
    assert type(value["other"]) is float and value["other"] == 0.002


@pytest.mark.parametrize("text,pattern", [
    ('{"a": {"id":"x", "id":"y"}}', "duplicate record key"),
    ('{"a": 1e999}', "nonfinite"), ('{"a": NaN}', "nonfinite"),
    ('{"a": [Infinity]}', "nonfinite"), ('{a: 1}', "invalid JSON record"),
])
def test_strict_json_refusals(tmp_path, text, pattern):
    path = tmp_path / "invalid.json"
    path.write_text(text)
    with pytest.raises(ValueError, match=pattern):
        io.read_record(path)


def test_yaml_tag_errors_are_not_mislabelled_as_encoding_errors(tmp_path):
    path = tmp_path / "record.yaml"
    path.write_text("id: a\nx: !unknown value\n")
    with pytest.raises(ValueError, match="invalid YAML record") as exc:
        io.read_record(path)
    assert "UTF-8" not in str(exc.value)


@pytest.mark.parametrize("case", ["alias", "cycle", "depth", "size", "nonfinite", "key", "type"])
def test_library_measure_enforces_input_bounds_before_schema_loading(tmp_path, monkeypatch, case):
    from data_sheets_schema import transformation_measure as subject
    shared = []
    if case == "alias":
        full = {"a": shared, "b": shared}
    elif case == "cycle":
        shared.append(shared)
        full = {"a": shared}
    elif case == "depth":
        nested = 0
        for _ in range(io.MAX_DEPTH + 1):
            nested = [nested]
        full = {"a": nested}
    elif case == "size":
        monkeypatch.setattr(io, "MAX_RECORD_BYTES", 64)
        full = {"a": "x" * 65}
    elif case == "nonfinite":
        full = {"a": float("nan")}
    elif case == "key":
        full = {1: "value"}
    else:
        full = {"a": {"set-member"}}

    def must_not_load(*args, **kwargs):
        pytest.fail("unsafe input reached schema loading")
    monkeypatch.setattr(subject, "capture_schema", must_not_load)
    with pytest.raises(ValueError):
        subject.measure(full, {})
    with pytest.raises(ValueError):
        subject.measure({}, full)


def test_cli_missing_dev_dependency_has_actionable_error(tmp_path, monkeypatch):
    full, core = tmp_path / "full.json", tmp_path / "core.json"
    full.write_text('{"id":"x"}')
    core.write_text('{"id":"x"}')
    monkeypatch.setitem(sys.modules, "data_sheets_schema.transformation_measure", None)
    result = CliRunner().invoke(receipts, ["transform", "--full", str(full), "--core", str(core)])
    assert result.exit_code == 1
    assert "needs a checkout with dev dependencies" in result.output
    assert "linkml-map" in result.output
    assert "Traceback" not in result.output


def test_validation_runner_refuses_unknown_quiet_window_location(tmp_path, monkeypatch, capsys):
    script = Path(__file__).resolve().parents[1] / "scripts/adhoc/validate_d105_20261109.py"
    spec = importlib.util.spec_from_file_location("d105_runner", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "EXECUTIONS", tmp_path / "wrong-parent")
    monkeypatch.setattr(sys, "argv", [str(script), "--label", "never-run", "tests/test_derive_core.py"])
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: pytest.fail("must refuse before launch"))
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2
    assert "quiet-window location cannot be established" in capsys.readouterr().err
    assert not (tmp_path / "wrong-parent").exists()


@pytest.mark.parametrize("subdirectory", [False, True])
def test_foreign_working_checkout_is_refused_instead_of_mixing_schemas(tmp_path, monkeypatch, subdirectory):
    # Reuses the minimal second-checkout shape from cwd_checkout_divergence.py
    # in the independent PR review; no source schema needs alteration.
    other = tmp_path / "other-checkout"
    source = other / "src/data_sheets_schema"
    source.mkdir(parents=True)
    (other / "pyproject.toml").write_text('[tool.poetry]\nname = "data-sheets-schema"\n')
    full, core = tmp_path / "full.json", tmp_path / "core.json"
    full.write_text('{"id":"example:foreign"}')
    core.write_text('{"id":"example:foreign"}')
    monkeypatch.chdir(source if subdirectory else other)
    result = CliRunner().invoke(receipts, ["transform", "--full", str(full), "--core", str(core)])
    assert result.exit_code == 1
    assert "checkout" in result.output.lower()
    assert "refused" in result.output.lower()
    assert str(other) in result.output


def test_loader_and_schema_modules_are_pinned_once(tmp_path):
    full, core = tmp_path / "full.json", tmp_path / "core.json"
    full.write_text('{"id":"example:pins"}')
    core.write_text(json.dumps(derive_core({"id": "example:pins"})))
    result = io.measure_files(full, core)
    pins = result["basis"]["derivation_sources"]
    root = Path(__file__).resolve().parents[1]
    for module in ("transformation_measure_io", "schema_snapshot", "schema_view"):
        expected = root / f"src/data_sheets_schema/{module}.py"
        assert pins[module]["sha256"] == hashlib.sha256(expected.read_bytes()).hexdigest()
    def instrument_keys(value):
        if isinstance(value, dict):
            return sum(key == "instrument" for key in value) + sum(instrument_keys(v) for v in value.values())
        if isinstance(value, list):
            return sum(instrument_keys(v) for v in value)
        return 0
    assert instrument_keys(result) == 1
