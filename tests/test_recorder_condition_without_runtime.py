"""`d4d provenance record --condition` without `--runtime` (#6318, 2026-11-24).

Eight gate files of series 2026-11-22b recorded "rendering failed: TypeError:
replace() argument 2 must be str, not None": the recorder built a RunSpec with
`runtime=None`, the renderer substituted it into the header, and a bare
`except Exception` in the date search turned the error into a record with no
render specification. The render gate then read `unverifiable`, which
`runs check --strict` passes. The recorder now refuses by naming the option,
and a defect inside the renderer is raised instead of recorded as "no spec".

Offline; synthetic corpus only. Inputs: generated fixture; outputs: temporary records.
"""
import hashlib

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import chunking, runs
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from data_sheets_schema.resources import resource_path
from tests.test_manifest_corpus_root import project_tree  # noqa: F401


def _rendered_run(project_tree, monkeypatch):
    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", bundle=bundle,
                 manifest=manifest, runtime="Claude Code", provider="offline", chunk_manifest=chunks.absolute())
    prompt = root / "instruction.txt"
    prompt.write_text(spec.instruction)
    spec.full_path.parent.mkdir(parents=True)
    spec.core_path.parent.mkdir(parents=True)
    header = (spec.manifest_line + "\n# Source bundle: " + str(bundle)
              + "\n# Provider: offline\n# Agent runtime: Claude Code\n")
    for path in (spec.full_path, spec.core_path):
        path.write_text(header + "id: https://example.org/clinical\ntitle: Synthetic\n")
    spec.report_path.write_text("# Synthetic report\n")
    command = ["provenance", "record", "--manifest", str(manifest),
               "--project", spec.project, "--method", spec.method, "--label", spec.label,
               "--input-bundle", str(bundle), "--chunk-manifest", str(chunks.absolute()),
               "--condition", spec.condition, "--provider", "offline",
               "--prompt-text", str(prompt),
               *[arg for path in spec.prompt_files for arg in ("--prompt", str(resource_path(path)))]]
    return spec, command


def test_a_missing_runtime_is_refused_by_name_and_writes_nothing(project_tree, monkeypatch):
    spec, command = _rendered_run(project_tree, monkeypatch)
    result = CliRunner().invoke(cli, command)
    assert result.exit_code != 0
    assert "requires --runtime" in result.output, result.output
    assert "TypeError" not in result.output
    assert "no request spec recorded" not in result.output
    assert not spec.provenance_path.exists()


def test_the_same_line_with_the_runtime_records_a_spec_the_gate_confirms(project_tree, monkeypatch):
    spec, command = _rendered_run(project_tree, monkeypatch)
    result = CliRunner().invoke(cli, command + ["--runtime", "Claude Code"])
    assert result.exit_code == 0, result.output
    request = yaml.safe_load(spec.provenance_path.read_text())["prompts"]["request"]
    assert request["sha256"] == hashlib.sha256(spec.instruction.encode()).hexdigest()
    assert request["spec"]["runtime"] == "Claude Code"
    assert runs.verify_request(spec.method, spec.label, spec.project)[0] == "match"


def test_a_missing_runtime_is_refused_without_an_instruction_too(project_tree, monkeypatch):
    """Without --prompt-text nothing rendered, so the spec was stored with a null runtime."""
    spec, command = _rendered_run(project_tree, monkeypatch)
    at = command.index("--prompt-text")
    result = CliRunner().invoke(cli, command[:at] + command[at + 2:])
    assert result.exit_code != 0
    assert "requires --runtime" in result.output, result.output
    assert not spec.provenance_path.exists()


@pytest.mark.parametrize("failure", [TypeError("replace() argument 2 must be str, not None"),
                                     AttributeError("synthetic renderer defect")])
def test_a_renderer_defect_in_the_date_search_is_raised_not_recorded_as_no_spec(project_tree, monkeypatch, failure):
    """A programming error inside the renderer is not "the text does not reproduce"."""
    spec, command = _rendered_run(project_tree, monkeypatch)
    from data_sheets_schema import api_runner

    def broken(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(api_runner, "resolve_prompt", broken)
    result = CliRunner().invoke(cli, command + ["--runtime", "Claude Code"])
    assert result.exit_code != 0
    assert "no request spec recorded" not in result.output
    assert not spec.provenance_path.exists()
