"""Offline reproductions of the round-10 input-routing review."""
from dataclasses import replace
import hashlib
from pathlib import Path
import shlex
import socket

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking, provenance, receipts
from data_sheets_schema.cli import cli
from tests.test_receipts import BUNDLE, FULL, _receipt
from tests.test_generation_manifest_identity import external


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network is forbidden in input-routing tests")
    monkeypatch.setattr(socket.socket, "connect", refuse)


def receipt_files(tmp_path, monkeypatch):
    study = tmp_path / "study"
    study.mkdir()
    monkeypatch.setattr(chunking, "CONCAT_DIR", study)
    bundle = study / "P_preprocessed.txt"
    bundle.write_text(BUNDLE)
    alias = tmp_path / "alias.txt"
    alias.symlink_to(bundle)
    full = tmp_path / "P_d4d.yaml"
    full.write_text(yaml.safe_dump(FULL))
    receipt = tmp_path / "P_coverage_receipt.yaml"
    md5 = hashlib.md5(BUNDLE.encode()).hexdigest()
    receipt.write_text(yaml.safe_dump(_receipt(md5)))
    manifest = tmp_path / "selected chunks.yaml"
    manifest.write_text(chunking.dump_manifest(chunking.build_manifest(alias)))
    return bundle, alias, full, receipt, md5, manifest


@pytest.mark.parametrize("legacy", [False, True])
def test_alias_receipts_reconstruct_the_same_manifest_after_its_file_is_lost(tmp_path, monkeypatch, legacy):
    bundle, alias, full, receipt, md5, manifest = receipt_files(tmp_path, monkeypatch)
    attestation = chunking.chunks_input(alias, md5, manifest=manifest)
    assert attestation
    if legacy:
        attestation.pop("bundle_name", None)
    before = receipts.block_for(full, receipt, alias, md5, True, manifest=manifest, record_chunks=attestation)
    assert before["checked"] and not before["findings"]
    manifest.unlink()
    after = receipts.block_for(full, receipt, alias, md5, True, manifest=manifest, record_chunks=attestation)
    assert after["checked"], after
    assert not after["findings"]
    assert after["artifacts"]["manifest"]["path"] is None
    # Reconstruction still refuses even a one-byte change to the attested
    # manifest identity; a matching count alone must not permit recovery.
    bad = {**attestation, "sha256": "0" * 64}
    refused = receipts.block_for(full, receipt, alias, md5, True, manifest=manifest, record_chunks=bad)
    assert not refused["checked"] and "does not reproduce" in refused["reason"]


@pytest.mark.parametrize("stale_fallback", [False, True])
def test_preprocess_and_concatenate_use_the_same_declared_directory(tmp_path, stale_fallback):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "protocol.txt").write_text("Fresh external cohort protocol.\n" * 30)
    declared = tmp_path / "declared"
    pipeline = tmp_path / "pipeline"
    if stale_fallback:
        (pipeline / "EXTERNAL").mkdir(parents=True)
        (pipeline / "EXTERNAL/protocol.txt").write_text("OLD RECORD CONTENT.\n")
    bundle = tmp_path / "bundle.txt"
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(yaml.safe_dump({"projects": {"EXTERNAL": {
        "raw_dir": str(raw), "source_dir": str(declared), "bundle": str(bundle),
        "sources": [{"id": "protocol", "raw_file": "protocol.txt", "processed_file": "protocol.txt",
                     "source_type": "documentation", "priority": 1}]}}}))
    prepared = CliRunner().invoke(cli, ["download", "preprocess", "--project", "EXTERNAL",
                                       "--manifest", str(manifest), "--input-dir", str(tmp_path / "unused"),
                                       "--output-dir", str(pipeline)])
    assert prepared.exit_code == 0, prepared.output
    assert (declared / "protocol.txt").is_file()
    result = CliRunner().invoke(cli, ["download", "concatenate", "--project", "EXTERNAL",
                                     "--manifest", str(manifest), "--input-dir", str(pipeline)])
    assert result.exit_code == 0, result.output
    assert "Fresh external cohort protocol." in bundle.read_text()
    assert "OLD RECORD CONTENT." not in bundle.read_text()


@pytest.mark.parametrize("with_registry", [False, True])
def test_explicit_manifest_can_pass_the_real_pre_provenance_cli_gate(tmp_path, monkeypatch, with_registry):
    bundle, alias, full, receipt, md5, manifest = receipt_files(tmp_path, monkeypatch)
    core_dir = tmp_path / "outputs/agent_core/L"
    full_dir = tmp_path / "outputs/agent/L"
    core_dir.mkdir(parents=True)
    full_dir.mkdir(parents=True)
    (full_dir / "P_d4d.yaml").write_text(f"# Source bundle: {alias}\n" + full.read_text())
    (core_dir / "P_coverage_receipt.yaml").write_bytes(receipt.read_bytes())
    registry = tmp_path / "registry.yaml"
    registry.write_text("projects:\n  P: []\n")
    monkeypatch.setattr(provenance, "CONCAT_DIR", tmp_path / "outputs")
    prefix = ["--manifest", str(registry)] if with_registry else []
    result = CliRunner().invoke(cli, [*prefix, "receipts", "check",
                                     "--method", "agent", "--project", "P", "--label", "L",
                                     "--chunk-manifest", str(manifest), "--strict"])
    assert result.exit_code == 0, result.output
    assert "3/3" in result.output
    assert not (core_dir / "P_provenance.yaml").exists()


def test_recorded_name_survives_loss_of_the_original_symlink_target(tmp_path, monkeypatch):
    bundle, alias, full, receipt, md5, manifest = receipt_files(tmp_path, monkeypatch)
    attestation = chunking.chunks_input(alias, md5, manifest=manifest)
    assert attestation["bundle_name"] == "P_preprocessed.txt"
    raw = alias.read_bytes()
    alias.unlink()
    bundle.unlink()
    alias.write_bytes(raw)
    manifest.unlink()
    result = receipts.block_for(full, receipt, alias, md5, True,
                                manifest=manifest, record_chunks=attestation)
    assert result["checked"] and not result["findings"], result


def test_recorded_name_reconstructs_a_recovered_git_blob_with_no_live_bundle(tmp_path, monkeypatch):
    bundle, alias, full, receipt, md5, manifest = receipt_files(tmp_path, monkeypatch)
    attestation = chunking.chunks_input(alias, md5, manifest=manifest)
    raw = alias.read_bytes()
    manifest.unlink()
    monkeypatch.setattr(provenance, "bundle_bytes_for", lambda *args, **kwargs: (raw, {
        "commit": "a" * 40, "date": "2026-09-13", "md5": md5,
        "sha256": hashlib.sha256(raw).hexdigest(), "matched_on": ["md5"]}))
    result = receipts.block_for(full, receipt, None, md5, True,
                                bundle_rel_path="lost-alias.txt", record_chunks=attestation)
    assert result["checked"] and not result["findings"], result


def test_new_agentic_renderer_carries_the_pre_provenance_selection(external):
    spec = replace(external, condition="generic_v9", runtime="Claude Code", out_dir=None)
    lines = [line for line in spec.instruction.splitlines() if "receipts check" in line and "--chunk-manifest" in line]
    assert len(lines) == 1
    arguments = shlex.split(lines[0])
    assert arguments[arguments.index("--chunk-manifest") + 1] == str(spec.chunk_manifest)
    assert arguments[arguments.index("--manifest") + 1] == str(spec.manifest)
    assert arguments[arguments.index("--method") + 1] == spec.method
    for version in (1, 2):
        old = replace(spec, render_version=version)
        assert not any("receipts check" in line and "--chunk-manifest" in line for line in old.instruction.splitlines())
