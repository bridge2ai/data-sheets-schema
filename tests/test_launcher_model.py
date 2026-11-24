"""The model a launcher states for an agentic renderer 6 to 8 instruction (#6311, #6312, 2026-11-24).

The header's `# Model:` line comes from the shared configuration. The
2026-11-22 series ran on another model and worked around that with a
branch-only commit to the configuration file, so its 16 records quote a value
no commit on main carries, and three had their render specification removed
when it could not reproduce the line. `launcher_model` puts the statement in
the rendering specification instead.

Offline; synthetic corpus only. Inputs: generated fixture; outputs: temporary records.
"""
import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import chunking, runs
from data_sheets_schema.api_runner import RunSpec, _model_settings
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from tests.test_complete_recorder_line import PHASES, _outputs, _recorder_argv
from tests.test_manifest_corpus_root import project_tree  # noqa: F401

OTHER = "example-model-9"


def _pair(project_tree, monkeypatch, **kw):
    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    common = dict(bundle=bundle, manifest=manifest, runtime="Claude Code", provider="offline",
                  chunk_manifest=chunks.absolute(), method="claudecode_agent")
    return (root, _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", **common),
            _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", **common, launcher_model=OTHER, **kw))


def test_the_stated_model_replaces_the_configured_one_in_the_header_lines_only(project_tree, monkeypatch):
    _, plain, stated = _pair(project_tree, monkeypatch)
    configured = _model_settings("generic_v9")["name"]
    assert configured != OTHER
    assert "launcher_model" not in plain.render_spec()
    assert stated.render_spec() == {**plain.render_spec(), "launcher_model": OTHER}
    changed = [(a, b) for a, b in zip(plain.instruction.splitlines(), stated.instruction.splitlines(), strict=True)
               if a != b]
    assert changed and all(a.strip() == f"# Model: {configured}" and b.strip() == f"# Model: {OTHER}"
                           for a, b in changed), changed


def test_the_key_round_trips_and_is_refused_where_it_states_nothing(project_tree, monkeypatch):
    _, plain, stated = _pair(project_tree, monkeypatch)
    literal = stated.render_spec()
    restored = RunSpec.from_render_spec(literal, project=stated.project, method=stated.method, label=stated.label)
    assert restored.render_spec() == literal and restored.instruction == stated.instruction
    for value in (None, 5, True, ["x"]):
        with pytest.raises(ValueError, match="launcher_model"):
            RunSpec.from_render_spec({**literal, "launcher_model": value}, project=stated.project,
                                     method=stated.method, label=stated.label)
    base = dict(project=plain.project, arm=plain.arm, method=plain.method, bundle=plain.bundle, label=plain.label,
                condition=plain.condition, manifest=plain.manifest, chunk_manifest=plain.chunk_manifest,
                provider="offline")
    for name in ("two words", "line\nbreak", "", "-leading", "x" * 200, "semi;colon", "$(id)"):
        with pytest.raises(ValueError, match="launcher_model"):
            RunSpec(**base, runtime="Claude Code", launcher_model=name)
    for kw in (dict(runtime="Claude API (direct)"), dict(runtime="Claude Code", render_version=5)):
        with pytest.raises(ValueError, match="agentic renderers 6 to 8"):
            RunSpec(**base, launcher_model=OTHER, **kw)
    assert RunSpec(**base, runtime="Claude Code", launcher_model="vendor/model-5[1m]").launcher_model


def test_a_run_on_the_stated_model_records_a_specification_the_gate_confirms(project_tree, monkeypatch):
    """What the 2026-11-22 series could not do: the spec states the model, so nothing is removed."""
    root, _, spec = _pair(project_tree, monkeypatch, complete_recorder_line=True, reasoning_effort="high")
    sent = _outputs(spec, root)
    # The session heads its records as the instruction told it to.
    for path in (spec.full_path, spec.core_path):
        path.write_text(f"# Model: {OTHER}\n" + path.read_text())
    command = _recorder_argv(spec.instruction) + [flag for phase in PHASES for flag in ("--phase", phase)]
    result = CliRunner().invoke(cli, command, env={"D4D_LAUNCH_INSTRUCTION": str(sent)})
    assert result.exit_code == 0, (result.output, result.exception)
    record = yaml.safe_load(spec.provenance_path.read_text())
    assert record["prompts"]["request"]["spec"]["launcher_model"] == OTHER
    assert record["model"]["model"] == OTHER
    assert runs.verify_request(spec.method, spec.label, spec.project)[0] == "match"


def test_prompt_render_offers_the_option(project_tree, monkeypatch):
    root, _, spec = _pair(project_tree, monkeypatch)
    out = root / "rendered.md"
    result = CliRunner().invoke(cli, ["prompt", "render", "--project", spec.project, "--label", spec.label,
                                      "--condition", spec.condition, "--bundle", str(spec.bundle),
                                      "--manifest", str(spec.manifest), "--chunk-manifest", str(spec.chunk_manifest),
                                      "--runtime", "Claude Code", "--provider", "offline",
                                      "--launcher-model", OTHER, "--out", str(out)])
    assert result.exit_code == 0, (result.output, result.exception)
    assert out.read_text() == spec.instruction
