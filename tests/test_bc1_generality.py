"""G2/F1/F4/N6 causal declaration tests; offline, 2026-11-01."""
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import bc1_registration as sizing, bc1_context
from data_sheets_schema.schema_snapshot import capture_schema
from scripts import build_api_registrations as builder
from tests.test_bc1_registration import sizing_fixture
from tests.test_bc1_context import fixture as context_fixture


def synthetic(sizing_fixture):
    registration, files, inputs = sizing_fixture
    project = "SYNTHETIC"
    registration["run"]["project"] = registration["inputs"]["project"] = project
    for key in ("full", "core"):
        path = getattr(files, key)
        path.write_bytes(path.read_bytes().replace(b"KIDS_FIRST", project.encode()).replace(
            b"# Arm: de novo", ("# Arm: " + builder.ARMS["baseline"][0]).encode()))
    manifest = Path(registration["inputs"]["source_manifest"]["path"])
    manifest.write_text(yaml.safe_dump({"profile": "neutral", "projects": {project: {"sources": [
        {"id": "source", "processed_file": "source.txt", "source_type": "documentation"}]}}}))
    registration["inputs"]["source_manifest"] = sizing._pin(manifest, manifest.read_bytes())
    return registration, files, inputs, manifest


def test_declared_synthetic_project_sizes_registers_and_all_uses_selected_manifest(sizing_fixture, monkeypatch, tmp_path):
    import json
    registration, files, inputs, manifest = synthetic(sizing_fixture)
    # A declared synthetic prefix with explicit identifier forms (#5471).
    schema = yaml.safe_load(inputs["schema_path"].read_bytes())
    schema.setdefault("prefixes", {})["SYNTHETIC"] = "https://example.test/synthetic/"
    schema["classes"]["Instance"]["attributes"]["data_substrate"]["annotations"] = {
        "d4d:termSources": "SYNTHETIC",
        "d4d:termSourceIdentifierForms": json.dumps({"version": 1, "sources": [
            {"id": "synthetic", "label": "SYNTHETIC",
             "curies": [{"prefix": "SYNTHETIC", "local_prefix": ""}],
             "iri_bases": ["https://example.test/synthetic/"]},
        ]})}
    inputs["schema_path"].write_text(yaml.safe_dump(schema))
    monkeypatch.setattr(builder.api, "FULL_SCHEMA_PATH", inputs["schema_path"])
    monkeypatch.setattr(builder.api, "CORE_SCHEMA_PATH", inputs["schema_path"])
    # The real builder, BC1 packet renderer, sizing and acceptance gates all run.
    limits = {k: registration["audit_limits"][k] for k in builder.PARTITION_KEYS}
    limits["aggregate_input_tokens"] = 40_000_000
    record = builder.SizingRecord(files.full, files.core, files.receipt, files.receipt_result)
    options = dict(arm="baseline", bounded_carry_version=1, source_manifest_path=manifest,
        context_path=registration["inputs"]["context"]["path"],
        bundle_path=registration["inputs"]["bundle"]["path"],
        chunk_manifest_path=registration["inputs"]["chunk_manifest"]["path"],
        profile_name="neutral", audit_limits=limits, sizing_record=record,
        registration_path=tmp_path / "registration.json")
    actual, outputs, result = builder.prepare_registration("SYNTHETIC", "synthetic", **options)
    assert result["project"] == "SYNTHETIC" and result["own_project_and_arm_record"]
    assert actual["inputs"]["profile"]["vocabulary"] is None
    policy = bc1_context.derive_term_policy(selection=actual, context_raw=inputs["context"],
        schema_snapshot=capture_schema(inputs["schema_path"], strict=True))
    assert policy["external_terms"]["Instance"]["data_substrate"]["sources"] == [
        "SYNTHETIC"]
    assert outputs and not (tmp_path / "registration.json").exists()
    with pytest.raises(ValueError, match=f"UNDECLARED.*{manifest}"):
        builder.prepare_registration("UNDECLARED", "synthetic", **options)
    # CLI enumeration is observed separately; the preparation above is unmocked.
    observed = []
    def prepare(project, label, **kw):
        observed.append((project, kw["source_manifest_path"]))
        raise ValueError("enumeration reached preparation")
    monkeypatch.setattr(builder, "prepare_registration", prepare)
    args = ["--all", "--source-manifest", str(manifest), "--label", "fixture",
        "--bounded-carry-version", "1", "--dry-run"]
    for key, value in limits.items():
        args += ["--" + key.replace("_", "-"), str(value)]
    cli = CliRunner().invoke(builder.cli, args)
    assert "enumeration reached preparation" in cli.output
    assert observed == [("SYNTHETIC", manifest)]


def test_sizing_refuses_undeclared_project_and_changed_manifest_pin(sizing_fixture):
    registration, files, inputs, manifest = synthetic(sizing_fixture)
    options = dict(sizing_record=files, context_raw=inputs["context"], schema_snapshot=inputs["schema_snapshot"])
    registration["run"]["project"] = registration["inputs"]["project"] = "UNDECLARED"
    with pytest.raises(ValueError, match=f"UNDECLARED.*{manifest}"):
        sizing.size_inputs(registration, **options)
    manifest.write_text("projects: {UNDECLARED: {sources: []}}\n")
    with pytest.raises(ValueError, match="registered byte pin"):
        sizing.size_inputs(registration, **options)


def test_partition_declaration_controls_choices_and_calibration_exemption(sizing_fixture, tmp_path, monkeypatch):
    from tests.test_g2_round2 import calibration_case
    entry, covered, _, _, _ = calibration_case(sizing_fixture, tmp_path, monkeypatch, "SYNTHETIC")
    defaults = builder.resolve_audit_limits("SYNTHETIC", overrides=entry["limits"])
    for key in builder.ADMISSION_CEILING_KEYS:
        assert covered(entry), key
        assert not covered(entry, **{key: defaults[key] - 1}), key
    registration, files, inputs, manifest = synthetic(sizing_fixture)
    declaration = {"name": "synthetic-partition", "arms": ["baseline"],
        "limits": {"max_paths": 80, "max_inventory_bytes": 12288,
                   "max_workers": 4, "aggregate_input_tokens": 4000000},
        "sizing_record": {key: sizing._pin(getattr(files, key), getattr(files, key).read_bytes())
                          for key in ("full", "core", "receipt")}}
    def save(value):
        manifest.write_text(yaml.safe_dump({"projects": {"SYNTHETIC": {
            "sources": [], "audit_partition": value}}}))
    save(declaration)
    options = dict(source_manifest=manifest)
    limits = builder.resolve_audit_limits("SYNTHETIC", "synthetic-partition", **options)
    # Bounds remain usable, but an unpinned declaration cannot waive sizing.
    assert not builder.profile_covered("SYNTHETIC", "baseline", limits, **options)
    assert not builder.profile_covered("SYNTHETIC", "de_novo", limits, **options)
    for project, partition, arm in [("OTHER", "synthetic-partition", "baseline"),
                                     ("SYNTHETIC", "undeclared", "baseline"),
                                     ("SYNTHETIC", "synthetic-partition", "de_novo")]:
        with pytest.raises(ValueError, match="partition"):
            builder.resolve_audit_limits(project, partition, arm=arm, **options)
    damaged = deepcopy(declaration)
    del damaged["sizing_record"]
    save(damaged)
    with pytest.raises(ValueError, match="declaration"):
        builder.profile_covered("SYNTHETIC", "baseline", limits, **options)
    save(declaration)
    files.full.write_bytes(files.full.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="pin changed"):
        builder.profile_covered("SYNTHETIC", "baseline", limits, **options)
    files.full.write_bytes(files.full.read_bytes().replace(b"SYNTHETIC", b"OTHER"))
    declaration["sizing_record"]["full"] = sizing._pin(files.full, files.full.read_bytes())
    save(declaration)
    with pytest.raises(ValueError, match="own project/arm"):
        builder.profile_covered("SYNTHETIC", "baseline", limits, **options)
