"""Strict audits check targets; historical instruction replay uses its record."""
from dataclasses import replace
import hashlib

import click
from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import api_runner as api, provenance
from data_sheets_schema.cli import cli
from data_sheets_schema.review_pack import instruction_text
from data_sheets_schema.runs import verify_request
from tests.test_download.test_api_runner import FakeClient
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


@pytest.mark.parametrize("document", [
    {}, {"projects": {}}, {"projects": []}, {"projects": {"BROKEN": None}},
    {"projects": {"VALID": [], "BROKEN": "not a project"}},
    {"projects": {"VALID": {"sources": "not a list"}}},
])
def test_strict_audit_refuses_empty_and_malformed_declarations(tmp_path, document):
    manifest = tmp_path / "registry.yaml"
    manifest.write_text(yaml.safe_dump(document))
    result = CliRunner().invoke(cli, [
        "download", "audit-bundles", "--manifest", str(manifest), "--strict"])
    assert result.exit_code != 0, result.output
    assert any(word in result.output for word in ("mapping", "targets", "declarations", "sources"))
    assert "0 derived bundle(s)" not in result.output


def test_non_strict_empty_audit_explains_that_nothing_was_checked(tmp_path):
    manifest = tmp_path / "registry.yaml"
    manifest.write_text("projects: {}\n")
    result = CliRunner().invoke(cli, ["download", "audit-bundles", "--manifest", str(manifest)])
    assert result.exit_code == 0, result.output
    assert "no bundle was checked" in result.output


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("runtime", ["Claude Code", "Claude API (direct)"])
@pytest.mark.parametrize("current", ["missing", "malformed", "changed"])
def test_recorded_instruction_replays_without_live_manifest_validation(external, version, runtime, current):
    spec = replace(external, render_version=version, runtime=runtime)
    body = api.resolve_prompt(spec)
    recorded = spec.render_spec()
    data = {
        "run": {"project": spec.project, "method": spec.method, "label": spec.label},
        "prompts": {"request": {"spec": recorded, "sha256": hashlib.sha256(body.encode()).hexdigest()}},
    }
    path = provenance.record_path_for(spec.project, spec.method, spec.label, spec.out_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data))
    before = path.read_bytes()
    if current == "missing":
        spec.manifest.unlink()
    elif current == "malformed":
        spec.manifest.write_text("[broken")
    else:
        spec.manifest.write_text("projects: {}\nnaming: {}\n")
    replay = api.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)
    assert api.resolve_prompt(replay) == body
    assert replay.manifest == spec.manifest
    assert replay.render_spec() == recorded
    recovered, basis = instruction_text(data, None)
    assert recovered == body and "sha256 matches" in basis
    assert verify_request(spec.method, spec.label, spec.project, spec.out_dir) == ("match", None)
    assert path.read_bytes() == before
    client = FakeClient()
    with pytest.raises(ValueError, match="replay cannot execute"):
        api.execute(replay, client=client)
    assert client.messages.calls == []
    if current != "changed":
        with pytest.raises(click.ClickException):
            replace(spec)


def test_legacy_renderer_without_manifest_field_uses_only_recorded_substitutions(external):
    spec = replace(external, render_version=1)
    body = api.resolve_prompt(spec)
    recorded = spec.render_spec()
    del recorded["manifest"], recorded["render_version"], recorded["chunk_manifest"]
    spec.manifest.unlink()
    replay = api.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)
    assert replay.render_version == 1
    assert api.resolve_prompt(replay) == body
