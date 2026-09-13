"""Round 3 review: flat output ownership and relative rendering recovery."""
import hashlib
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, chunking, provenance as pv, runs
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from tests.test_manifest_corpus_root import project_tree


@pytest.mark.parametrize("damage", ["unchanged", "modified", "missing"])
def test_flat_artifact_pins_never_use_an_ancestor_duplicate(project_tree, monkeypatch, damage):
    root, manifest, bundle = project_tree
    nested = root / "analysis"
    nested.mkdir()
    monkeypatch.chdir(nested)
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic", bundle=bundle,
        manifest=manifest, out_dir="out")
    for owner in (root, nested):
        (owner / "out").mkdir()
        for suffix in ("d4d.yaml", "d4d_core.yaml"):
            (owner / "out" / f"CLINICAL_X_{suffix}").write_text("id: https://example.org/clinical\n")
    block = api.validation_block(spec, [])
    data = {"run": {"project": spec.project, "method": spec.method, "label": spec.label},
            "record_mode": "live", "validation": block}
    spec.provenance_path.write_text(yaml.safe_dump(data))
    if damage == "modified":
        spec.full_path.write_text("id: https://example.org/modified\n")
    elif damage == "missing":
        spec.full_path.unlink()
    for address in (spec.provenance_path, spec.provenance_path.absolute()):
        result = runs.check_provenance(spec.method, spec.label, spec.project, record=address)
        assert result["ok"] is (damage == "unchanged"), result
    assert pv.preservable_validation(spec.provenance_path.absolute(), {}) == (block if damage == "unchanged" else None)


def test_flat_api_execution_survives_an_ancestor_manifest(project_tree, monkeypatch):
    from tests.test_download.test_api_runner import FakeClient
    root, manifest, bundle = project_tree
    nested = root / "analysis"
    nested.mkdir()
    monkeypatch.chdir(nested)
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic", bundle=bundle,
        manifest=manifest, out_dir="out")
    api.execute(spec, client=FakeClient())
    data = yaml.safe_load(spec.provenance_path.read_text())
    assert Path(data["outputs"]["full"]["path"]).is_absolute()
    assert runs.check_provenance(spec.method, spec.label, spec.project, record=spec.provenance_path)["ok"]


def test_legacy_absolute_flat_record_does_not_guess_a_relative_pins_base(project_tree, monkeypatch):
    root, _, _ = project_tree
    nested = root / "analysis"
    nested.mkdir()
    for owner, body in ((root, b"original"), (nested, b"modified")):
        path = owner / "out/record.yaml"
        path.parent.mkdir()
        path.write_bytes(body)
    monkeypatch.chdir(nested)
    entry = {"path": "out/record.yaml", "sha256": hashlib.sha256(b"original").hexdigest()}
    # The record's absolute flat address carries no original launch base.
    assert pv.verify_entry(entry, record=nested / "out/provenance.yaml") is None
    assert pv.verify_entry(entry, record=Path("out/provenance.yaml")) is False


@pytest.mark.parametrize("absolute_record", [False, True])
def test_project_root_backfill_recovers_the_original_relative_destinations(project_tree, monkeypatch, absolute_record):
    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", bundle=bundle,
        manifest=manifest, runtime="Claude Code", provider="offline", chunk_manifest=chunks)
    assert not spec.full_path.is_absolute()
    instruction = spec.instruction
    prompt = root / "instruction.txt"
    prompt.write_text(instruction)
    spec.full_path.parent.mkdir(parents=True)
    spec.core_path.parent.mkdir(parents=True)
    header = (spec.manifest_line + "\n# Source bundle: " + str(bundle)
              + "\n# Provider: offline\n# Agent runtime: Claude Code\n")
    spec.full_path.write_text(header + "id: https://example.org/clinical\ntitle: Synthetic\n")
    spec.core_path.write_text(header + "id: https://example.org/clinical\ntitle: Synthetic\n")
    spec.report_path.write_text("# Synthetic report\n")
    result = CliRunner().invoke(cli, ["provenance", "record", "--manifest", str(manifest),
        "--project", spec.project, "--method", spec.method, "--label", spec.label,
        "--input-bundle", str(bundle), "--chunk-manifest", str(chunks), "--prompt-text", str(prompt)])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load(spec.provenance_path.read_text())
    if absolute_record:
        # Earlier recorders used absolute output paths for this same prompt.
        for entry in data["outputs"].values():
            if entry:
                entry["path"] = str(Path(entry["path"]).absolute())
        spec.provenance_path.write_text(yaml.safe_dump(data))
    result = CliRunner().invoke(cli, ["provenance", "backfill-spec", "--project", spec.project,
        "--method", spec.method, "--label", spec.label, "--condition", spec.condition,
        "--runtime", spec.runtime, "--execute"])
    assert result.exit_code == 0, result.output
    recorded = yaml.safe_load(spec.provenance_path.read_text())["prompts"]["request"]["spec"]
    restored = api.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)
    assert restored.instruction == instruction
