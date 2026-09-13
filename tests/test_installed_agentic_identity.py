"""Installed challenges and command locations must be replayable and fail closed."""
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from data_sheets_schema import agent_pin, agentic_runtime, api_runner, resources
from tests.test_generation_manifest_identity import external


@pytest.mark.parametrize("damage", [None, "version", "current", "previous", "missing"])
def test_installed_definition_preimages_are_verified(tmp_path, monkeypatch, damage):
    previous = "## Procedure\n\nAn older definition with a different scoring rule.\n"
    row = {"current_sha256": "a" * 64, "previous_text": previous,
           "previous_sha256": hashlib.sha256(previous.encode()).hexdigest()}
    data = {"version": 1, "agents": {"synthetic": row}}
    if damage == "version":
        data["version"] = 2
    elif damage == "current":
        row["current_sha256"] = "b" * 64
    elif damage == "previous":
        row["previous_text"] += "This tampered preimage must not be used."
    path = tmp_path / "_preimages.json"
    if damage != "missing":
        path.write_text(json.dumps(data))
    monkeypatch.setattr(resources, "CHECKOUT_ROOT", None)
    monkeypatch.setattr(resources, "resource_root", lambda: (tmp_path, "install"))
    monkeypatch.setattr(resources, "resource_path", lambda logical: path)
    monkeypatch.setattr(agent_pin, "agent_digest", lambda name: "a" * 64)
    monkeypatch.setattr(agent_pin, "_git", lambda *args: pytest.fail("installed challenge must not consult Git"))
    assert agent_pin._previous_text("synthetic") == (previous if damage is None else None)


def test_recorded_toolchain_replays_without_live_environment(external, monkeypatch, tmp_path):
    spec = replace(external, runtime="Codex CLI", render_version=6)
    instruction, recorded = spec.instruction, spec.render_spec()
    moved = tmp_path / "another launch directory"
    moved.mkdir()
    monkeypatch.chdir(moved)
    monkeypatch.setattr(agentic_runtime.sys, "executable", "/different/install/python")
    restored = api_runner.RunSpec.from_render_spec(recorded, project=spec.project,
        method=spec.method, label=spec.label)
    assert restored.instruction == instruction
    assert restored.render_spec() == recorded


@pytest.mark.parametrize("damage", ["missing", "relative_python", "missing_schema", "relative_resource"])
def test_renderer6_rejects_unusable_recorded_toolchains(external, damage):
    spec = replace(external, runtime="Codex CLI", render_version=6)
    recorded = spec.render_spec()
    if damage == "missing":
        recorded.pop("agentic_toolchain")
    elif damage == "relative_python":
        recorded["agentic_toolchain"]["python"] = "python"
    elif damage == "missing_schema":
        recorded["agentic_toolchain"]["resources"].pop(agentic_runtime.SCHEMAS[0])
    else:
        recorded["agentic_toolchain"]["resources"][agentic_runtime.SCHEMAS[0]] = "schema.yaml"
    with pytest.raises(ValueError, match="agentic toolchain"):
        api_runner.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)


@pytest.mark.parametrize("imported_checkout", [True, False])
def test_definition_challenge_uses_the_checkout_that_supplies_the_definition(tmp_path, monkeypatch, imported_checkout):
    import subprocess
    roots = []
    for name in ("imported", "selected"):
        root = tmp_path / name
        (root / "src/data_sheets_schema").mkdir(parents=True)
        (root / "pyproject.toml").write_text('name = "data-sheets-schema"\n')
        path = root / ".claude/agents/synthetic.md"
        path.parent.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        for revision in ("previous", "current"):
            path.write_text(f"## Procedure\n\nThe {name} checkout's {revision} rule is distinct.\n")
            subprocess.run(["git", "-C", str(root), "add", ".claude/agents/synthetic.md"], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Offline test",
                "-c", "user.email=offline@example.invalid", "commit", "-qm", revision], check=True)
        roots.append(root)
    monkeypatch.setattr(agent_pin, "REPO", roots[0])
    monkeypatch.setattr(resources, "CHECKOUT_ROOT", roots[0] if imported_checkout else None)
    monkeypatch.chdir(roots[1])
    assert agent_pin._previous_text("synthetic") == "## Procedure\n\nThe selected checkout's previous rule is distinct.\n"
