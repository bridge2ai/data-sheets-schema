# Purpose: probe the residual cases of 0460a69d8's recorder recovery (Claude 3):
#   (a) nested render, root record, but the recorder is given RELATIVE spellings;
#   (b) root render (relative), record from a nested cwd with absolute spellings;
#   (c) nested render, root record, --input-bundle names a DIFFERENT byte-identical
#       file - must never be admitted with a match.
# Inputs: the project_tree fixture from tests/test_manifest_corpus_root (synthetic).
# Outputs: printed recorder outcome / verify_request status; no repository writes.
# Date: 2026-11-01. Serves the Claude D76 re-check of PR #5213. Offline.
import hashlib
import shutil

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import chunking, runs
from data_sheets_schema.resources import resource_path
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from tests.test_manifest_corpus_root import project_tree  # noqa: F401


def _render(project_tree, monkeypatch, render_cwd):
    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    chunks = chunks.absolute()
    nested = root / "analysis"
    nested.mkdir()
    monkeypatch.chdir(nested if render_cwd == "nested" else root)
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", bundle=bundle,
                 manifest=manifest, runtime="Claude Code", provider="offline", chunk_manifest=chunks)
    prompt = root / "instruction.txt"
    prompt.write_text(spec.instruction)
    spec.full_path.parent.mkdir(parents=True, exist_ok=True)
    spec.core_path.parent.mkdir(parents=True, exist_ok=True)
    header = (spec.manifest_line + "\n# Source bundle: " + str(bundle)
              + "\n# Provider: offline\n# Agent runtime: Claude Code\n")
    for path in (spec.full_path, spec.core_path):
        path.write_text(header + "id: https://example.org/clinical\ntitle: Synthetic\n")
    spec.report_path.write_text("# Synthetic report\n")
    return root, nested, manifest, bundle, chunks, spec, prompt


def _record(spec, prompt, manifest_arg, bundle_arg, chunks_arg, explicit_date):
    return CliRunner().invoke(cli, ["provenance", "record", "--manifest", str(manifest_arg),
        "--project", spec.project, "--method", spec.method, "--label", spec.label,
        "--input-bundle", str(bundle_arg), "--chunk-manifest", str(chunks_arg),
        "--condition", spec.condition, "--runtime", spec.runtime, "--provider", "offline",
        "--prompt-text", str(prompt),
        *[a for p in spec.prompt_files for a in ("--prompt", str(resource_path(p)))],
        *(["--run-date", spec.run_date] if explicit_date else [])])


@pytest.mark.parametrize("explicit_date", [False, True])
def test_a_nested_render_root_record_relative_spellings(project_tree, monkeypatch, explicit_date):
    root, nested, manifest, bundle, chunks, spec, prompt = _render(project_tree, monkeypatch, "nested")
    monkeypatch.chdir(root)
    result = _record(spec, prompt, manifest.relative_to(root), bundle.relative_to(root),
                     chunks.relative_to(root), explicit_date)
    print("(a) exit", result.exit_code, "|", result.output.strip().splitlines()[-1:] if result.output else "")
    if result.exit_code == 0:
        print("(a) verify_request:", runs.verify_request(spec.method, spec.label, spec.project))


@pytest.mark.parametrize("explicit_date", [False, True])
def test_b_root_render_nested_record_absolute(project_tree, monkeypatch, explicit_date):
    root, nested, manifest, bundle, chunks, spec, prompt = _render(project_tree, monkeypatch, "root")
    monkeypatch.chdir(nested)
    result = _record(spec, prompt, manifest, bundle, chunks, explicit_date)
    print("(b) exit", result.exit_code, "|", result.output.strip().splitlines()[-1:] if result.output else "")
    if result.exit_code == 0:
        monkeypatch.chdir(root)
        print("(b) verify_request:", runs.verify_request(spec.method, spec.label, spec.project))


def test_c_different_byte_identical_bundle_is_never_a_match(project_tree, monkeypatch):
    root, nested, manifest, bundle, chunks, spec, prompt = _render(project_tree, monkeypatch, "nested")
    other = root.parent / "byte_identical_copy" / bundle.name
    other.parent.mkdir()
    shutil.copyfile(bundle, other)
    monkeypatch.chdir(root)
    result = _record(spec, prompt, manifest, other, chunks, True)
    print("(c) exit", result.exit_code, "|", result.output.strip().splitlines()[-1:] if result.output else "")
    if result.exit_code == 0:
        data = yaml.safe_load(spec.provenance_path.read_text())
        req = data["prompts"]["request"]
        status = runs.verify_request(spec.method, spec.label, spec.project)
        print("(c) recorded spec bundle:", (req.get("spec") or {}).get("bundle"), "status:", status)
        assert status[0] != "match" or (req.get("spec") or {}).get("bundle") == str(spec.bundle)
    assert hashlib.sha256(prompt.read_bytes()).hexdigest()
