"""The complete recorder line of an agentic renderer 6 to 8 instruction (#6320, 2026-11-24).

Series 2026-11-22b was sent the bare recorder line: seven of fifteen sessions
wrote a record that failed its gates (no instruction, or no phase history) and
all sixteen records said no effort was recorded. Under the opt-in
`complete_recorder_line` the line carries the launcher's rendering
specification and names the variable holding the instruction; the session
adds only `--phase`.

The done criterion here is the release driver's: the rendered line, run as
written with only the launcher's variable set and the phases appended, writes
a record whose render gate reads `match`.

Offline; synthetic corpus only. Inputs: generated fixture; outputs: temporary records.
"""
import hashlib
import json
import shlex

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import chunking, runs
from data_sheets_schema.api_runner import COMPLETE_RECORDER_LINE_NOTE, RunSpec
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from tests.test_manifest_corpus_root import project_tree  # noqa: F401

PHASES = ['{"name":"generate_full","completed":true}', '{"name":"derive_core","completed":true}',
          '{"name":"source_audit","completed":true}', '{"name":"reconcile","completed":true,"iterations":1}',
          '{"name":"report","completed":true}']


def _specs(project_tree, monkeypatch, **kw):
    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    common = dict(bundle=bundle, manifest=manifest, runtime="Claude Code", provider="offline",
                  chunk_manifest=chunks.absolute(), method="claudecode_agent")
    bare = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", **common)
    complete = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", **common,
                     complete_recorder_line=True, **kw)
    return root, bare, complete


def _recorder_argv(instruction):
    lines = [line for line in instruction.splitlines() if " provenance record " in line and "--render-spec-json" in line]
    assert len(lines) == 1, lines
    argv = shlex.split(lines[0].strip())
    return argv[argv.index("provenance"):]


def _outputs(spec, root):
    sent = root / "instruction.txt"
    sent.write_text(spec.instruction)
    spec.full_path.parent.mkdir(parents=True, exist_ok=True)
    spec.core_path.parent.mkdir(parents=True, exist_ok=True)
    header = (spec.manifest_line + "\n# Source bundle: " + str(spec.bundle)
              + "\n# Provider: offline\n# Agent runtime: Claude Code\n")
    for path in (spec.full_path, spec.core_path):
        path.write_text(header + "id: https://example.org/clinical\ntitle: Synthetic\n")
    spec.report_path.write_text("# Synthetic report\n")
    return sent


def test_the_key_changes_only_the_recorder_line_and_appends_its_note(project_tree, monkeypatch):
    _, bare, complete = _specs(project_tree, monkeypatch, reasoning_effort="high")
    assert complete.instruction.endswith(COMPLETE_RECORDER_LINE_NOTE)
    old = bare.instruction.splitlines()
    new = complete.instruction[:-len(COMPLETE_RECORDER_LINE_NOTE)].splitlines()
    changed = [(a, b) for a, b in zip(old, new, strict=True) if a != b]
    assert len(changed) == 1
    before, after = changed[0]
    assert after.startswith(before + " --reasoning-effort high --render-spec-json ")
    assert after.endswith(" --prompt-text-env D4D_LAUNCH_INSTRUCTION")
    argv = _recorder_argv(complete.instruction)
    assert json.loads(argv[argv.index("--render-spec-json") + 1]) == complete.render_spec()


def test_a_spec_without_the_key_is_byte_identical_and_emits_no_key(project_tree, monkeypatch):
    _, bare, complete = _specs(project_tree, monkeypatch)
    assert "complete_recorder_line" not in bare.render_spec()
    assert "prompt_text_env" not in bare.render_spec()
    assert "--render-spec-json" not in bare.instruction
    assert complete.render_spec() == {**bare.render_spec(), "complete_recorder_line": True, "prompt_text_env": True}


def test_the_key_round_trips_and_a_non_boolean_is_refused(project_tree, monkeypatch):
    _, _, complete = _specs(project_tree, monkeypatch, reasoning_effort="high")
    literal = complete.render_spec()
    restored = RunSpec.from_render_spec(literal, project=complete.project, method=complete.method, label=complete.label)
    assert restored.complete_recorder_line is True
    assert restored.render_spec() == literal
    assert restored.instruction == complete.instruction
    for value in (False, 1, "true", None):
        with pytest.raises(ValueError, match="complete_recorder_line"):
            RunSpec.from_render_spec({**literal, "complete_recorder_line": value}, project=complete.project,
                                     method=complete.method, label=complete.label)


@pytest.mark.parametrize(("kw", "message"), [
    (dict(runtime="Claude API (direct)", complete_recorder_line=True, prompt_text_env=True), "agentic renderers 6 to 8"),
    (dict(runtime="Claude Code", render_version=5, complete_recorder_line=True, prompt_text_env=True), "agentic renderers 6 to 8"),
    (dict(runtime="Claude Code", complete_recorder_line=True), "requires prompt_text_env"),
    (dict(runtime="Claude Code", complete_recorder_line=1, prompt_text_env=True), "must be a boolean"),
    (dict(runtime="Claude Code", prompt_text_env=True), "agentic renderers 9 and later"),
])
def test_the_key_is_refused_where_it_renders_nothing(project_tree, monkeypatch, kw, message):
    root, bare, _ = _specs(project_tree, monkeypatch)
    with pytest.raises(ValueError, match=message):
        RunSpec(project=bare.project, arm=bare.arm, method=bare.method, bundle=bare.bundle, label=bare.label,
                condition=bare.condition, manifest=bare.manifest, chunk_manifest=bare.chunk_manifest,
                provider="offline", **kw)


def test_the_line_as_written_with_phases_records_what_the_launcher_rendered(project_tree, monkeypatch):
    root, _, spec = _specs(project_tree, monkeypatch, reasoning_effort="high")
    sent = _outputs(spec, root)
    command = _recorder_argv(spec.instruction) + [flag for phase in PHASES for flag in ("--phase", phase)]
    result = CliRunner().invoke(cli, command, env={"D4D_LAUNCH_INSTRUCTION": str(sent)})
    assert result.exit_code == 0, (result.output, result.exception)
    record = yaml.safe_load(spec.provenance_path.read_text())
    request = record["prompts"]["request"]
    assert request["sha256"] == hashlib.sha256(spec.instruction.encode()).hexdigest()
    assert request["spec"] == spec.render_spec()
    assert runs.verify_request(spec.method, spec.label, spec.project)[0] == "match"
    assert record["run"]["condition"] == "generic_v9"
    assert record["model"]["reasoning_effort"] == "high"
    assert record["inputs"]["receipt_expected"] is True
    assert [row["phase"] for row in record["phase_log"]["phases"]] == [json.loads(p)["name"] for p in PHASES]
    assert record["phase_log"]["recorded_by"] == "the run itself, as the playbook directs"
    assert runs.phase_log_status(spec.method, spec.label, spec.project)[0] == runs.PHASES_RECORDED
    hashed = {entry["path"] for entry in record["prompts"]["files"]}
    assert any(str(path) in name or name.endswith(str(path)) for path in spec.prompt_files for name in hashed), hashed
    assert len(hashed) == len(spec.prompt_files)


def test_the_line_without_phases_is_refused_and_says_what_to_append(project_tree, monkeypatch):
    root, _, spec = _specs(project_tree, monkeypatch)
    sent = _outputs(spec, root)
    result = CliRunner().invoke(cli, _recorder_argv(spec.instruction), env={"D4D_LAUNCH_INSTRUCTION": str(sent)})
    assert result.exit_code != 0
    assert "requires the run's phase history" in result.output and "--phase" in result.output, result.output
    assert not spec.provenance_path.exists()


def test_a_flag_that_disagrees_with_the_specification_is_refused(project_tree, monkeypatch):
    root, _, spec = _specs(project_tree, monkeypatch, reasoning_effort="high")
    sent = _outputs(spec, root)
    command = _recorder_argv(spec.instruction) + ["--phase", PHASES[0]]
    for extra in (["--reasoning-effort", "max"], ["--condition", "generic_v8"], ["--runtime", "Claude Code (direct)"]):
        result = CliRunner().invoke(cli, command + extra, env={"D4D_LAUNCH_INSTRUCTION": str(sent)})
        assert result.exit_code != 0, extra
        assert "conflicts with the registered specification" in result.output, result.output
    assert not spec.provenance_path.exists()


def test_another_instruction_in_the_variable_is_refused(project_tree, monkeypatch):
    root, _, spec = _specs(project_tree, monkeypatch)
    _outputs(spec, root)
    other = root / "other.txt"
    other.write_text(spec.instruction + "\nUse a different source-ranking policy.\n")
    command = _recorder_argv(spec.instruction) + ["--phase", PHASES[0]]
    result = CliRunner().invoke(cli, command, env={"D4D_LAUNCH_INSTRUCTION": str(other)})
    assert result.exit_code != 0
    assert "does not reproduce the supplied instruction" in result.output, result.output
    assert not spec.provenance_path.exists()


def test_a_bare_renderer_7_specification_is_still_refused_on_the_specification_route(project_tree, monkeypatch):
    root, bare, _ = _specs(project_tree, monkeypatch)
    sent = _outputs(bare, root)
    result = CliRunner().invoke(cli, ["provenance", "record", "--project", bare.project, "--method", bare.method,
                                      "--label", bare.label, "--input-bundle", str(bare.bundle),
                                      "--render-spec-json", json.dumps(bare.render_spec()), "--prompt-text", str(sent)])
    assert result.exit_code != 0
    assert "renderer-9-or-newer" in result.output, result.output


def test_prompt_render_offers_the_two_options(project_tree, monkeypatch):
    root, _, spec = _specs(project_tree, monkeypatch, reasoning_effort="high")
    out = root / "rendered.md"
    result = CliRunner().invoke(cli, ["prompt", "render", "--project", spec.project, "--label", spec.label,
                                      "--condition", spec.condition, "--bundle", str(spec.bundle),
                                      "--manifest", str(spec.manifest), "--chunk-manifest", str(spec.chunk_manifest),
                                      "--runtime", "Claude Code", "--provider", "offline",
                                      "--reasoning-effort", "high", "--complete-recorder-line", "--out", str(out)])
    assert result.exit_code == 0, (result.output, result.exception)
    assert out.read_text() == spec.instruction
    refused = CliRunner().invoke(cli, ["prompt", "render", "--project", spec.project, "--label", spec.label,
                                       "--condition", spec.condition, "--bundle", str(spec.bundle),
                                       "--manifest", str(spec.manifest), "--runtime", "Claude Code",
                                       "--reasoning-effort", "default"])
    assert refused.exit_code != 0
