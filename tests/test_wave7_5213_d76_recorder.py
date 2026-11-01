"""D76 recorder regressions (#5213, 2026-10-31), adapted from Claude's probe.

An agentic instruction rendered
outside the corpus root (absolute input spellings), recorded WITH --condition so
`provenance record` re-renders a *fresh* RunSpec. Mirrors
tests/test_manifest_corpus_review_r6.py::test_root_recording_recovers_a_prompt_rendered_in_a_subdirectory,
which records without --condition. record_cwd=nested is the same-cwd control.
Offline; synthetic corpus only. Inputs: generated fixture; outputs: temporary records.
"""
import hashlib

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import chunking, runs
from data_sheets_schema.resources import resource_path
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from tests.test_manifest_corpus_root import project_tree  # noqa: F401


@pytest.mark.parametrize("record_cwd", ["nested", "root"])
@pytest.mark.parametrize("explicit_date", [False, True])
@pytest.mark.parametrize("explicit_chunk", [False, True])
def test_record_with_condition_after_render_in_subdirectory(project_tree, monkeypatch, record_cwd, explicit_date, explicit_chunk):
    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    chunks = chunks.absolute()
    nested = root / "analysis"
    nested.mkdir()
    monkeypatch.chdir(nested)
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", bundle=bundle,
        manifest=manifest, runtime="Claude Code", provider="offline", chunk_manifest=chunks if explicit_chunk else None)
    instruction = spec.instruction
    print("rendered spellings:", spec.bundle, spec.manifest, spec.chunk_manifest)
    prompt = root / "instruction.txt"
    prompt.write_text(instruction)
    spec.full_path.parent.mkdir(parents=True)
    spec.core_path.parent.mkdir(parents=True)
    header = (spec.manifest_line + "\n# Source bundle: " + str(bundle)
        + "\n# Provider: offline\n# Agent runtime: Claude Code\n")
    for path in (spec.full_path, spec.core_path):
        path.write_text(header + "id: https://example.org/clinical\ntitle: Synthetic\n")
    spec.report_path.write_text("# Synthetic report\n")
    monkeypatch.chdir(root if record_cwd == "root" else nested)
    result = CliRunner().invoke(cli, ["provenance", "record", "--manifest", str(manifest),
        "--project", spec.project, "--method", spec.method, "--label", spec.label,
        "--input-bundle", str(bundle),
        *(["--chunk-manifest", str(chunks)] if explicit_chunk else []),
        "--condition", spec.condition, "--runtime", spec.runtime, "--provider", "offline",
        "--prompt-text", str(prompt),
        *[arg for path in spec.prompt_files for arg in ("--prompt", str(resource_path(path)))],
        *(["--run-date", spec.run_date] if explicit_date else [])])
    print("record exit", result.exit_code)
    print(result.output)
    assert result.exit_code == 0, result.output
    data = yaml.safe_load(spec.provenance_path.read_text())
    req = data["prompts"]["request"]
    print("recorded sha == instruction sha:", req["sha256"] == hashlib.sha256(instruction.encode()).hexdigest())
    print("recorded spec bundle:", (req.get("spec") or {}).get("bundle"))
    print("recorded inputs.bundle_path:", data["inputs"]["bundle_path"])
    monkeypatch.chdir(root)
    status = runs.verify_request(spec.method, spec.label, spec.project)
    print("verify_request:", status)
    assert status[0] == "match", status
    assert req["sha256"] == hashlib.sha256(instruction.encode()).hexdigest()
    assert req["spec"]["bundle"] == str(spec.bundle)
    assert req["spec"]["manifest"] == str(spec.manifest)
    assert req["spec"]["chunk_manifest"] == str(spec.chunk_manifest)


@pytest.mark.parametrize("bundle", [42, True, ["documents.txt"], {"path": "documents.txt"}])
def test_backfill_non_string_bundle_is_a_controlled_no_match(tmp_path, monkeypatch, bundle):
    from data_sheets_schema import provenance as pv

    record = tmp_path / "EXAMPLE_provenance.yaml"
    data = {
        "run": {"project": "EXAMPLE", "method": "external", "label": "malformed"},
        "model": {"provider": "offline"},
        "record_generated_at": "2026-10-31T00:00:00+00:00",
        "inputs": {"bundle_path": bundle},
        "prompts": {"request": {"sha256": "0" * 64}},
    }
    original = yaml.safe_dump(data)
    record.write_text(original)
    monkeypatch.setattr(pv, "record_path_for", lambda *args, **kwargs: record)
    result = CliRunner().invoke(cli, ["provenance", "backfill-spec", "--project", "EXAMPLE",
        "--method", "external", "--label", "malformed", "--condition", "generic_v9", "--execute"])
    assert result.exit_code != 0
    assert "no spec under" in result.output, (result.output, result.exception)
    assert not isinstance(result.exception, TypeError)
    assert record.read_text() == original
