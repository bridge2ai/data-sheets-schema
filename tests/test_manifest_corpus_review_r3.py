"""PR1587 round 2: verification must follow the record, never another corpus."""
import hashlib
import shlex
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, provenance as pv, runs
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from tests.test_manifest_corpus_root import project_tree


@pytest.mark.parametrize("damage", ["changed", "missing", "unchanged"])
def test_explicit_corpus_owns_artifact_verification_and_preservation(project_tree, monkeypatch, damage):
    root, manifest, _ = project_tree
    other = root.parent / "other"
    relative = Path("data/d4d_concatenated/external/run/CLINICAL_X_d4d.yaml")
    original = b"id: https://example.org/original\n"
    for owner in (root, other):
        full = owner / relative
        full.parent.mkdir(parents=True)
        full.write_bytes(original)
    full = other / relative
    record = other / "data/d4d_concatenated/external_core/run/CLINICAL_X_provenance.yaml"
    record.parent.mkdir(parents=True)
    validation = {"passed": True, "artifacts": {"full": {
        "path": str(relative), "sha256": hashlib.sha256(original).hexdigest()}}}
    record.write_text(yaml.safe_dump({"run": {"project": "CLINICAL_X", "method": "external", "label": "run"},
        "record_mode": "live", "validation": validation}))
    if damage == "changed":
        full.write_text("id: https://example.org/changed\n")
    elif damage == "missing":
        full.unlink()
    nested = root / "analysis"
    nested.mkdir()
    monkeypatch.chdir(nested)
    expected = {"changed": runs.STALE, "missing": runs.UNVERIFIED, "unchanged": runs.VALID}[damage]
    assert runs.validation_status("external", "run", "CLINICAL_X", other / "data/d4d_concatenated") == expected
    kept = pv.preservable_validation(record, {})
    assert kept == (validation if damage == "unchanged" else None)
    gate = runs.check_provenance("external", "run", "CLINICAL_X", other / "data/d4d_concatenated")
    assert "full" in (gate["drifted"] if damage == "changed" else
                      gate["unverifiable"] if damage == "missing" else ["full"])


def test_explicit_no_manifest_owns_only_caller_outputs(project_tree, monkeypatch):
    root, manifest, bundle = project_tree
    nested = root / "analysis"
    nested.mkdir()
    relative = Path("data/d4d_concatenated/external/run/CLINICAL_X_d4d.yaml")
    for owner, identity in ((root, "wrong"), (nested, "selected")):
        full = owner / relative
        full.parent.mkdir(parents=True)
        full.write_text(f"id: https://example.org/{identity}\n")
    monkeypatch.chdir(nested)
    record = pv.build_record("CLINICAL_X", "external", "run", mode="live",
        input_bundle=bundle, input_verified=True, manifest=None)
    assert Path(record.data["outputs"]["full"]["path"]).resolve() == nested / relative


@pytest.mark.parametrize("arm", ["crate_only", "healthsheet"])
@pytest.mark.parametrize("runtime", ["Claude Code", "Codex CLI"])
def test_unused_manifest_still_owns_receipt_commands(project_tree, arm, runtime):
    _, manifest, bundle = project_tree
    spec = _spec("CLINICAL_X", arm, "external_run", "generic_v9", bundle=bundle,
        manifest=manifest, runtime=runtime)
    assert not spec.manifest_used
    command = next(shlex.split(line)[3:] for line in spec.instruction.splitlines()
        if line.startswith("poetry run d4d ") and " receipts check " in line)
    assert command[:2] == ["--manifest", str(manifest)]


def test_no_manifest_receipt_check_explicitly_disables_ambient_selection(project_tree):
    _, _, bundle = project_tree
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", bundle=bundle,
        manifest=None, runtime="Claude Code")
    command = next(shlex.split(line)[3:] for line in spec.instruction.splitlines()
        if line.startswith("poetry run d4d ") and " receipts check " in line)
    assert command[:2] == ["--manifest", "none"]


def test_unused_manifest_recorder_keeps_the_selected_output_owner(project_tree):
    root, manifest, bundle = project_tree
    spec = _spec("CLINICAL_X", "crate_only", "external_run", "generic_v9", bundle=bundle,
        manifest=manifest, runtime="Claude Code")
    spec.full_path.parent.mkdir(parents=True)
    spec.full_path.write_text(spec.manifest_line + "\n# Source bundle: " + str(bundle)
        + "\nid: https://example.org/clinical\ntitle: Synthetic\n")
    result = CliRunner().invoke(cli, ["provenance", "record", "--manifest", str(manifest),
        "--project", spec.project, "--method", spec.method, "--label", spec.label,
        "--input-bundle", str(bundle)])
    assert result.exit_code == 0, result.output
    path = root / "data/d4d_concatenated" / (spec.method + "_core") / spec.label / "CLINICAL_X_provenance.yaml"
    data = yaml.safe_load(path.read_text())
    assert Path(data["outputs"]["full"]["path"]).resolve() == spec.full_path
    assert data["inputs"]["source_manifest"]["path"] is None


def test_nested_renderer5_backfill_restores_recorded_destinations(project_tree, monkeypatch):
    root, manifest, bundle = project_tree
    nested = root / "analysis"
    nested.mkdir()
    monkeypatch.chdir(nested)
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", bundle=bundle,
        manifest=manifest, runtime="Claude Code")
    spec.run_date = "2026-09-13"
    path = pv.record_path_for(spec.project, spec.method, spec.label)
    path.parent.mkdir(parents=True)
    data = {"record_generated_at": "2026-09-13T00:00:00+00:00",
        "run": {"project": spec.project, "method": spec.method, "label": spec.label},
        "model": {"provider": spec.provider},
        "inputs": {"bundle_path": str(bundle), "source_manifest": {"path": str(manifest)},
                   "chunks": {"path": str(spec.chunk_manifest)}},
        "outputs": {key: {"path": str(value)} for key, value in
                    (("full", spec.full_path), ("core", spec.core_path), ("report", spec.report_path))},
        "prompts": {"request": {"sha256": hashlib.sha256(spec.instruction.encode()).hexdigest()}}}
    path.write_text(yaml.safe_dump(data))
    result = CliRunner().invoke(cli, ["--manifest", str(manifest), "provenance", "backfill-spec",
        "--project", spec.project, "--method", spec.method, "--label", spec.label,
        "--condition", spec.condition, "--runtime", spec.runtime, "--execute"])
    assert result.exit_code == 0, result.output
    recorded = yaml.safe_load(path.read_text())["prompts"]["request"]["spec"]
    restored = api.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)
    assert restored.instruction == spec.instruction
