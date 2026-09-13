"""Round-5 review: artifact namespaces, emitted preflight and cross-cwd recovery."""
import hashlib
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, chunking, provenance as pv, resources, runs
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from tests.test_manifest_corpus_root import project_tree
from tests.test_manifest_corpus_review_r5 import selected_alias
from tests.test_agentic_selected_playbook import commands


@pytest.mark.parametrize("damage", ["modified", "missing"])
def test_flat_output_prefix_does_not_enable_resource_fallback(project_tree, monkeypatch, damage):
    root, _, _ = project_tree
    caller = root / "analysis"
    caller.mkdir()
    pin = Path("project/run/CLINICAL_X_d4d.yaml")
    original = b"id: https://example.org/original\n"
    for owner in (root, caller):
        target = owner / pin
        target.parent.mkdir(parents=True)
        target.write_bytes(original)
    record = pin.parent / "CLINICAL_X_provenance.yaml"
    data = {"run": {"project": "CLINICAL_X", "method": "external", "label": "run"},
        "record_mode": "live", "validation": {"passed": True, "artifacts": {"full": {
            "path": str(pin), "sha256": hashlib.sha256(original).hexdigest()}}}}
    (caller / record).write_text(yaml.safe_dump(data))
    if damage == "missing":
        (caller / pin).unlink()
    else:
        (caller / pin).write_text("Changed output.")
    monkeypatch.setattr(resources, "CHECKOUT_ROOT", root)
    monkeypatch.chdir(caller)
    for address in (record, record.absolute()):
        assert not runs.check_provenance("external", "run", "CLINICAL_X", record=address)["ok"]
        assert pv.preservable_validation(address, {}) is None


@pytest.mark.parametrize("arm", ["baseline", "crate_only"])
def test_emitted_symlink_chunk_preflight_uses_selected_corpus(selected_alias, arm):
    _, manifest, _, _, alias = selected_alias
    spec = _spec("CLINICAL_X", arm, "run", "generic_v9", bundle=alias,
        manifest=manifest, runtime="Claude Code")
    command = next(row for row in commands(spec) if row[:2] == ["bundle", "chunk"])
    result = CliRunner().invoke(cli, command)
    assert result.exit_code == 0, result.output
    restored = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
        method=spec.method, label=spec.label)
    assert restored.instruction == spec.instruction


def test_emitted_chunk_preflight_explicitly_disables_ambient_manifest(selected_alias):
    _, _, bundle, mapping, _ = selected_alias
    spec = _spec("CLINICAL_X", "baseline", "run", "generic_v9", bundle=bundle,
        manifest=None, chunk_manifest=mapping, runtime="Claude Code")
    command = next(row for row in commands(spec) if row[:2] == ["bundle", "chunk"])
    assert command[command.index("--manifest") + 1] == "none"
    result = CliRunner().invoke(cli, command)
    assert result.exit_code == 0, result.output


def test_root_recording_recovers_a_prompt_rendered_in_a_subdirectory(project_tree, monkeypatch):
    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    chunks = chunks.absolute()
    nested = root / "analysis"
    nested.mkdir()
    monkeypatch.chdir(nested)
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", bundle=bundle,
        manifest=manifest, runtime="Claude Code", provider="offline", chunk_manifest=chunks)
    instruction = spec.instruction
    assert spec.full_path.is_absolute()
    prompt = root / "instruction.txt"
    prompt.write_text(instruction)
    spec.full_path.parent.mkdir(parents=True)
    spec.core_path.parent.mkdir(parents=True)
    header = (spec.manifest_line + "\n# Source bundle: " + str(bundle)
        + "\n# Provider: offline\n# Agent runtime: Claude Code\n")
    for path in (spec.full_path, spec.core_path):
        path.write_text(header + "id: https://example.org/clinical\ntitle: Synthetic\n")
    spec.report_path.write_text("# Synthetic report\n")
    monkeypatch.chdir(root)
    result = CliRunner().invoke(cli, ["provenance", "record", "--manifest", str(manifest),
        "--project", spec.project, "--method", spec.method, "--label", spec.label,
        "--input-bundle", str(bundle), "--chunk-manifest", str(chunks), "--prompt-text", str(prompt)])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load(spec.provenance_path.read_text())
    assert not Path(data["outputs"]["full"]["path"]).is_absolute()
    result = CliRunner().invoke(cli, ["provenance", "backfill-spec", "--project", spec.project,
        "--method", spec.method, "--label", spec.label, "--condition", spec.condition,
        "--runtime", spec.runtime, "--execute"])
    assert result.exit_code == 0, result.output
    saved = yaml.safe_load(spec.provenance_path.read_text())["prompts"]["request"]["spec"]
    restored = api.RunSpec.from_render_spec(saved, project=spec.project, method=spec.method, label=spec.label)
    assert restored.instruction == instruction
