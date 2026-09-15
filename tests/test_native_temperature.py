"""Native headers distinguish an unobserved setting from zero (#1804)."""
from dataclasses import replace
import hashlib

import pytest
import yaml

from data_sheets_schema import agentic_runtime, api_runner as api, provenance, runs
from tests.test_generation_manifest_identity import external


def recorded_spec(version):
    return {
        "render_version": version, "condition": "generic_v9",
        "arm": "BASELINE (input documents only)", "bundle": "/input/cohort.txt",
        "manifest": None, "manifest_line": "# Source manifest: not used",
        "chunk_manifest": "/input/chunks.yaml", "chunk_check_uses_manifest": True,
        "run_date": "2026-09-15", "runtime": "Claude Code", "provider": "offline",
        "profile": "neutral", "profile_basis": "explicit",
        "agentic_artifact_paths": {name: f"/output/{name}" for name in ("full", "core", "receipt", "report")},
        "agentic_toolchain": {"python": "/installed/python", "resources": {
            name: "/installed/" + name for name in (*agentic_runtime.SCHEMAS, agentic_runtime.PLAYBOOK)}},
    }


def replay(version):
    return api.RunSpec.from_render_spec(recorded_spec(version),
        project="EXTERNAL", method="external_agent", label="synthetic")


def test_renderer6_keeps_the_original_instruction_bytes(monkeypatch):
    monkeypatch.setattr(api, "_model_settings", lambda: {"name": "synthetic-model"})
    assert hashlib.sha256(replay(6).instruction.encode()).hexdigest() == "14acf415f6e4caeac84aa1be70925351a60b88cb76fde3c644827dd3ae42f870"


@pytest.mark.parametrize("runtime", ["Claude Code", "Codex CLI"])
def test_fresh_native_instructions_and_replay_declare_temperature_unknown(external, runtime):
    spec = replace(external, runtime=runtime, condition="generic_v9", render_version=api.AUTO)
    assert spec.render_version == 7
    instruction = spec.instruction
    assert instruction.count("# Temperature: " + agentic_runtime.UNOBSERVED_TEMPERATURE) == 2
    assert "# Temperature: 0.0" not in instruction
    assert "Do not infer a sampling setting from a prompt" in instruction
    restored = api.RunSpec.from_render_spec(spec.render_spec(),
        project=spec.project, method=spec.method, label=spec.label)
    assert restored.instruction == instruction
    # Selecting the previous renderer still reproduces its old assertion.
    assert replace(spec, render_version=6).instruction.count("# Temperature: 0.0") == 2


@pytest.mark.parametrize("mode", ["live", "reconstructed"])
@pytest.mark.parametrize("runtime", ["Claude Code", "Codex CLI"])
def test_unknown_header_records_null_with_a_named_gap_without_changing_artifacts(tmp_path, monkeypatch, mode, runtime):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "records"
    paths = {kind: folder / ("external" if kind == "full" else "external_core") / "synthetic" /
             ("EXTERNAL_d4d.yaml" if kind == "full" else "EXTERNAL_d4d_core.yaml")
             for kind in ("full", "core")}
    header = (f"# Agent runtime: {runtime}\n# Model: synthetic-model\n"
              f"# Temperature: {agentic_runtime.UNOBSERVED_TEMPERATURE}\n")
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(header + "id: https://example.org/cohort\n")
    before = {key: path.read_bytes() for key, path in paths.items()}
    record = provenance.build_record("EXTERNAL", "external", "synthetic", mode=mode,
        concat_dir=folder, outputs=paths, manifest=None).data
    assert record["model"]["temperature"] is None
    assert "not observed" in record["model"]["temperature_basis"]
    assert any(row["field"] == "model.temperature" and row["value"] is None
               for row in record["unverified"])
    destination = paths["core"].with_name("EXTERNAL_provenance.yaml")
    destination.write_text(yaml.safe_dump(record))
    assert runs.header_disagreements("external", "synthetic", "EXTERNAL", concat_dir=folder) == []
    assert {key: path.read_bytes() for key, path in paths.items()} == before
    # Unknown does not agree with a record that asserts a measured value.
    record["model"]["temperature"] = 0.0
    destination.write_text(yaml.safe_dump(record))
    assert {row["artifact"] for row in runs.header_disagreements(
        "external", "synthetic", "EXTERNAL", concat_dir=folder)} == {"full", "core"}
