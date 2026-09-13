"""Recover historical render specs after the source declaration moves."""
from dataclasses import replace
import hashlib
from click.testing import CliRunner
import pytest
import yaml
from data_sheets_schema import api_runner as api, provenance as pv
from data_sheets_schema.cli import cli
from data_sheets_schema.runs import verify_request
from tests.test_generation_manifest_identity import external, offline  # noqa: F401

@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("state", ["missing", "malformed", "changed"])
def test_backfill_does_not_revalidate_historical_source_context(external, monkeypatch, version, state):
    spec = replace(external, render_version=version, runtime="Claude Code")
    body = api.resolve_prompt(spec)
    data = {"run": {"project": spec.project, "method": spec.method, "label": spec.label},
            "model": {"provider": spec.render_spec()["provider"]},
            "record_generated_at": spec.run_date,
            "inputs": {"bundle_path": str(spec.bundle), "source_manifest": {"path": str(spec.manifest)},
                       "chunks": {"path": str(spec.chunk_manifest)}},
            "prompts": {"request": {"sha256": hashlib.sha256(body.encode()).hexdigest()}}}
    monkeypatch.setattr(pv, "CONCAT_DIR", spec.out_dir)
    path = pv.record_path_for(spec.project, spec.method, spec.label, spec.out_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data))
    if state == "missing": spec.manifest.unlink()
    elif state == "malformed": spec.manifest.write_text("[broken")
    else: spec.manifest.write_text("projects: {}\nnaming: []\n")
    result = CliRunner().invoke(cli, ["provenance", "backfill-spec", "--project", spec.project,
        "--method", spec.method, "--label", spec.label, "--condition", spec.condition, "--execute"])
    assert result.exit_code == 0, result.output
    assert verify_request(spec.method, spec.label, spec.project, spec.out_dir) == ("match", None)
    restored = yaml.safe_load(path.read_text())
    assert restored["inputs"] == data["inputs"]
    assert restored["prompts"]["request"]["spec"]["render_version"] == version
