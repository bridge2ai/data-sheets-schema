"""D76 round-2 F2 assertions, adapted from Claude's 2026-11-01 probes.

Inputs: synthetic project_tree and real instruction rendering/recording.
Outputs: temporary records, checked for complete instruction identity. Offline.
The two cross-cwd directions are regressions; wrong-locator cases are controls.
"""
import hashlib
import shutil

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import chunking, runs
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from data_sheets_schema.resources import resource_path
from tests.test_manifest_corpus_root import project_tree  # noqa: F401


def _render(project_tree, monkeypatch, render_cwd, explicit_chunk):
    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    chunks = chunks.absolute()
    nested = root / "analysis"
    nested.mkdir()
    monkeypatch.chdir(nested if render_cwd == "nested" else root)
    spec = _spec(
        "CLINICAL_X", "baseline", "external_run", "generic_v9", bundle=bundle,
        manifest=manifest, runtime="Claude Code", provider="offline",
        chunk_manifest=chunks if explicit_chunk else None,
    )
    original_spec = spec.render_spec()
    instruction = spec.instruction
    prompt = root / "instruction.txt"
    prompt.write_text(instruction)
    paths = {name: getattr(spec, name + "_path").absolute()
             for name in ("full", "core", "report", "provenance")}
    paths["full"].parent.mkdir(parents=True, exist_ok=True)
    paths["core"].parent.mkdir(parents=True, exist_ok=True)
    header = (spec.manifest_line + "\n# Source bundle: " + str(bundle)
              + "\n# Provider: offline\n# Agent runtime: Claude Code\n")
    for name in ("full", "core"):
        paths[name].write_text(header + "id: https://example.org/clinical\ntitle: Synthetic\n")
    paths["report"].write_text("# Synthetic report\n")
    return root, nested, manifest, bundle, chunks, spec, original_spec, instruction, prompt, paths


def _record(spec, prompt, manifest_arg, bundle_arg, chunks_arg, explicit_date):
    return CliRunner().invoke(cli, [
        "provenance", "record", "--manifest", str(manifest_arg),
        "--project", spec.project, "--method", spec.method, "--label", spec.label,
        "--input-bundle", str(bundle_arg),
        *(["--chunk-manifest", str(chunks_arg)] if chunks_arg is not None else []),
        "--condition", spec.condition, "--runtime", spec.runtime, "--provider", "offline",
        "--prompt-text", str(prompt),
        *[arg for path in spec.prompt_files for arg in ("--prompt", str(resource_path(path)))],
        *(["--run-date", spec.run_date] if explicit_date else []),
    ])


@pytest.mark.parametrize("direction", ["nested_to_root_relative", "root_to_nested_absolute"])
@pytest.mark.parametrize("explicit_date", [False, True])
@pytest.mark.parametrize("explicit_chunk", [False, True])
def test_both_recorder_directions_preserve_the_full_instruction(
    project_tree, monkeypatch, direction, explicit_date, explicit_chunk,
):
    render_cwd = "nested" if direction == "nested_to_root_relative" else "root"
    (root, nested, manifest, bundle, chunks, spec, original_spec, instruction,
     prompt, paths) = _render(project_tree, monkeypatch, render_cwd, explicit_chunk)
    originals = {path: path.read_bytes() for path in (manifest, bundle, chunks, prompt)}
    if direction == "nested_to_root_relative":
        monkeypatch.chdir(root)
        manifest_arg, bundle_arg, chunk_arg = (
            path.relative_to(root) for path in (manifest, bundle, chunks))
    else:
        monkeypatch.chdir(nested)
        manifest_arg, bundle_arg, chunk_arg = manifest, bundle, chunks
    result = _record(spec, prompt, manifest_arg, bundle_arg,
                     chunk_arg if explicit_chunk else None, explicit_date)
    assert result.exit_code == 0, (result.output, result.exception)
    assert paths["provenance"].is_file()
    record = yaml.safe_load(paths["provenance"].read_text())
    request = record["prompts"]["request"]
    assert request["sha256"] == hashlib.sha256(instruction.encode()).hexdigest()
    for field in ("bundle", "manifest", "chunk_manifest", "manifest_line", "agentic_artifact_paths"):
        assert request["spec"][field] == original_spec[field], field
    monkeypatch.chdir(root)
    assert runs.verify_request(spec.method, spec.label, spec.project) == ("match", None)
    assert {path: path.read_bytes() for path in originals} == originals


@pytest.mark.parametrize("replacement", ["copy", "symlink"])
def test_full_hash_still_refuses_a_different_byte_identical_locator(
    project_tree, monkeypatch, replacement,
):
    (root, nested, manifest, bundle, chunks, spec, original_spec, instruction,
     prompt, paths) = _render(project_tree, monkeypatch, "nested", True)
    other = root / "different_locator" / bundle.name
    other.parent.mkdir()
    if replacement == "copy":
        shutil.copyfile(bundle, other)
    else:
        other.symlink_to(bundle)
    assert other.read_bytes() == bundle.read_bytes()
    originals = {path: path.read_bytes() for path in (bundle, chunks, prompt,
                 paths["full"], paths["core"], paths["report"])}
    monkeypatch.chdir(root)
    result = _record(spec, prompt, manifest, other, chunks, True)
    assert result.exit_code != 0
    assert "does not reproduce --prompt-text" in result.output, (result.output, result.exception)
    assert not paths["provenance"].exists()
    assert {path: path.read_bytes() for path in originals} == originals
