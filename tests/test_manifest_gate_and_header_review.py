"""Selected manifest declarations survive reconstruction and cannot fake coverage."""
from dataclasses import replace

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import chunking, provenance as pv
from data_sheets_schema.cli import cli
from tests.test_backfill_chunk_identity import prior  # noqa: F401
from tests.test_generation_manifest_identity import external, offline  # noqa: F401
from tests.test_final_input_routing_review import receipt_files


@pytest.mark.parametrize("shape", ["canonical", "empty", "truncated", "reordered", "wrong-count"])
def test_pre_provenance_strict_gate_requires_canonical_selected_coverage(tmp_path, monkeypatch, shape):
    bundle, alias, full, receipt, md5, manifest = receipt_files(tmp_path, monkeypatch)
    data = yaml.safe_load(manifest.read_text())
    if shape == "empty":
        data["chunks"], data["chunk_count"] = [], 0
    elif shape == "truncated":
        data["chunks"], data["chunk_count"] = data["chunks"][:2], 2
    elif shape == "reordered":
        data["chunks"].reverse()
    elif shape == "wrong-count":
        data["chunk_count"] = 0
    manifest.write_text(chunking.dump_manifest(data))
    root = tmp_path / "outputs"
    full_path = root / "agent/L/P_d4d.yaml"
    full_path.parent.mkdir(parents=True)
    full_path.write_text(f"# Source bundle: {alias}\n" + full.read_text())
    receipt_path = root / "agent_core/L/P_coverage_receipt.yaml"
    receipt_path.parent.mkdir(parents=True)
    receipt_data = yaml.safe_load(receipt.read_bytes())
    selected_ids = {chunk["id"] for chunk in data["chunks"]}
    receipt_data["chunks"] = [row for row in receipt_data["chunks"] if row["id"] in selected_ids]
    receipt_path.write_text(yaml.safe_dump(receipt_data))
    monkeypatch.setattr(pv, "CONCAT_DIR", root)
    result = CliRunner().invoke(cli, ["receipts", "check", "--method", "agent", "--label", "L",
        "--project", "P", "--chunk-manifest", str(manifest), "--strict"])
    assert result.exit_code == (0 if shape == "canonical" else 1), result.output
    assert not (root / "agent_core/L/P_provenance.yaml").exists()


@pytest.mark.parametrize("verified", [False, True])
@pytest.mark.parametrize("present", [False, True])
def test_missing_record_backfill_retains_the_positive_header_manifest(prior, verified, present):
    spec, chunks, target = prior
    target.unlink()
    selected = spec.bundle.parent / "chosen source manifest.yaml"
    if present:
        selected.write_bytes(spec.manifest.read_bytes())
    full = spec.out_dir / spec.method / spec.label / f"{spec.project}_d4d.yaml"
    full.write_text(f"# Source bundle: {spec.bundle}\n# Source manifest: {selected}\nid: example:cohort\n")
    args = ["provenance", "backfill"] + (["--verified-label", spec.label] if verified else [])
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    record = yaml.safe_load(target.read_text())
    assert record["inputs"]["source_manifest"]["path"] == str(selected)
    if present and verified:
        assert record["inputs"]["source_manifest"]["md5"] == pv._md5(selected)
    else:
        assert record["inputs"]["source_manifest"]["md5"] is None
        assert any(row["field"] == "inputs.source_manifest.md5" for row in record["unrecoverable"])


@pytest.mark.parametrize("explicit", [None, "path", "auto"])
def test_header_selection_preserves_unused_and_explicit_caller_choices(prior, explicit):
    spec, chunks, target = prior
    full = spec.out_dir / spec.method / spec.label / f"{spec.project}_d4d.yaml"
    full.write_text(f"# Source bundle: {spec.bundle}\n# Source manifest: not used (this arm)\nid: example:cohort\n")
    kwargs = {} if explicit == "auto" else {"manifest": spec.manifest if explicit == "path" else None}
    rec = pv.build_record(spec.project, spec.method, spec.label, mode="reconstructed",
                          input_verified=True, **kwargs)
    assert rec.data["inputs"]["source_manifest"]["path"] == (str(spec.manifest) if explicit == "path" else None)


@pytest.mark.parametrize("relative", [False, True])
def test_a_positive_manifest_path_containing_unused_words_is_still_selected(prior, monkeypatch, relative):
    spec, chunks, target = prior
    selected = spec.bundle.parent / "not used previously" / "selected.yaml"
    selected.parent.mkdir()
    selected.write_bytes(spec.manifest.read_bytes())
    full = spec.out_dir / spec.method / spec.label / f"{spec.project}_d4d.yaml"
    if relative:
        monkeypatch.chdir(spec.bundle.parent)
        selected = selected.relative_to(spec.bundle.parent)
    full.write_text(f"# Source bundle: {spec.bundle}\n# Source manifest: {selected}\nid: example:cohort\n")
    rec = pv.build_record(spec.project, spec.method, spec.label, mode="reconstructed", input_verified=True)
    assert rec.data["inputs"]["source_manifest"]["path"] == str(selected)
    changed = replace(spec, manifest=selected, manifest_line=spec.header_for_manifest(selected))
    assert changed.manifest_used

    from data_sheets_schema.api_runner import naming_block, source_ranking_block
    assert naming_block(spec.project, changed.manifest_line, manifest=selected)
    assert source_ranking_block(spec.project, changed.manifest_line, manifest=selected)


def test_unverified_external_inputs_never_claim_study_history(prior):
    spec, chunks, target = prior
    rec = pv.build_record(spec.project, spec.method, spec.label, mode="reconstructed",
                          input_verified=False, manifest=spec.manifest)
    reasons = {row["field"]: row["reason"] for row in rec.data["unrecoverable"]}
    assert "not been verified" in reasons["inputs.bundle_md5"]
    assert "not been verified" in reasons["inputs.source_manifest.md5"]
    assert "regenerated" not in reasons["inputs.bundle_md5"]
    assert "edited since" not in reasons["inputs.source_manifest.md5"]
