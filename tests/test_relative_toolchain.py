"""Checkout-relative toolchain locations in an agentic instruction (#6314, 2026-11-24).

The renderer-6 toolchain is bound by absolute path, and the instruction prints
it into the datasheet's `# Schema:` header and into every command. All 16
datasheets of 2026-11-22 therefore carry the operator's worktree path. Under
the opt-in `relative_toolchain`, a location under the checkout the run is
launched from is spelled relative to it. The key is stated only by the
complete recorder line (#6320), so it requires it.

Rendering only; nothing is written. Inputs: this checkout's study manifest and
CHORUS bundle (read to render, never sent anywhere).
"""
import hashlib
import re
import shlex
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from data_sheets_schema.agentic_runtime import (RELATIVE_TOOLCHAIN_NOTE, SCHEMAS, checkout_relative, toolchain,
                                                validate_toolchain)
from data_sheets_schema.api_runner import COMPLETE_RECORDER_LINE_NOTE, RunSpec, render_spec_payload
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec

ROOT = Path(__file__).resolve().parents[1]
LABEL = "2099-01-01_example-claudecode-generic-v9_rep1"
NOTE_SHA256 = "53d0caa3a792df808240d205d1acc56f4919f6eba03eaaaf6ab28e878e933d17"


def _render(monkeypatch, **kw):
    monkeypatch.chdir(ROOT)
    return _spec("CHORUS", "baseline", LABEL, "generic_v9", runtime="Claude Code", provider="Anthropic",
                 method="claudecode_agent", complete_recorder_line=True, **kw)


def test_every_location_under_the_checkout_is_spelled_relative(monkeypatch):
    monkeypatch.setattr(sys, "executable", str(ROOT / ".venv/bin/python"))
    spec = _render(monkeypatch, relative_toolchain=True)
    bound = spec.render_spec()["agentic_toolchain"]
    assert bound["python"] == ".venv/bin/python"
    assert all(path == name for name, path in bound["resources"].items()), bound["resources"]
    text = spec.instruction
    assert str(ROOT) not in text
    assert str(ROOT) not in render_spec_payload(spec)
    assert "    # Schema: " + SCHEMAS[0] + "\n" in text
    assert "    # Schema: " + SCHEMAS[1] + "\n" in text
    assert "\n    .venv/bin/python -m data_sheets_schema.cli provenance record " in text
    assert text.endswith(RELATIVE_TOOLCHAIN_NOTE + COMPLETE_RECORDER_LINE_NOTE)
    # The playbook view the instruction sends the session to is asked for in the same spelling.
    assert "\n.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain\n" in text


def test_the_note_is_pinned():
    """Part of every instruction rendered under the key; it changes only on purpose."""
    assert hashlib.sha256(RELATIVE_TOOLCHAIN_NOTE.encode()).hexdigest() == NOTE_SHA256


def test_the_playbook_view_is_printed_in_the_same_spelling(monkeypatch):
    """#6325 review, S1: the absolute view carried its own `# Schema:` header template."""
    monkeypatch.setattr(sys, "executable", str(ROOT / ".venv/bin/python"))
    monkeypatch.chdir(ROOT)
    relative = CliRunner().invoke(cli, ["agents", "playbook", "--relative-toolchain"])
    assert relative.exit_code == 0, relative.output
    assert str(ROOT) not in relative.output
    absolute = CliRunner().invoke(cli, ["agents", "playbook"])
    assert absolute.exit_code == 0 and str(ROOT) in absolute.output
    assert relative.output == absolute.output.replace(str(ROOT) + "/", "")


def test_the_playbook_view_refuses_the_spelling_away_from_the_checkout_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["agents", "playbook", "--relative-toolchain"])
    assert result.exit_code != 0
    assert "requires rendering from the root of the checkout" in result.output


def test_an_interpreter_outside_the_checkout_keeps_its_absolute_path_and_the_render_says_so(monkeypatch):
    monkeypatch.setattr(sys, "executable", "/opt/elsewhere/bin/python")
    spec = _render(monkeypatch, relative_toolchain=True)
    bound = spec.render_spec()["agentic_toolchain"]
    assert bound["python"] == "/opt/elsewhere/bin/python"
    assert bound["resources"][SCHEMAS[0]] == SCHEMAS[0]
    result = CliRunner().invoke(cli, ["prompt", "render", "--project", "CHORUS", "--label", LABEL,
                                      "--condition", "generic_v9", "--method", "claudecode_agent",
                                      "--runtime", "Claude Code", "--complete-recorder-line", "--relative-toolchain"])
    assert result.exit_code == 0, result.output
    assert "/opt/elsewhere/bin/python is outside the launch checkout and keeps its absolute path" in result.output


def test_without_the_key_the_instruction_is_the_absolute_one_and_emits_no_key(monkeypatch):
    monkeypatch.setattr(sys, "executable", str(ROOT / ".venv/bin/python"))
    absolute = _render(monkeypatch)
    relative = _render(monkeypatch, relative_toolchain=True)
    assert "relative_toolchain" not in absolute.render_spec()
    assert all(Path(path).is_absolute() for path in absolute.render_spec()["agentic_toolchain"]["resources"].values())
    # The two instructions differ only in how the locations are spelled, in the
    # hash that binds each specification, in the playbook view's flag, and in the note.
    def normal(text):
        text = re.sub(r"--render-spec-sha256 [0-9a-f]{64}", "--render-spec-sha256 X", text)
        return text.replace(" agents playbook --relative-toolchain", " agents playbook")
    assert (normal(relative.instruction).replace(RELATIVE_TOOLCHAIN_NOTE, "")
            == normal(absolute.instruction).replace(str(ROOT) + "/", ""))


def test_the_key_round_trips_and_a_non_boolean_is_refused(monkeypatch):
    monkeypatch.setattr(sys, "executable", str(ROOT / ".venv/bin/python"))
    spec = _render(monkeypatch, relative_toolchain=True)
    literal = spec.render_spec()
    restored = RunSpec.from_render_spec(literal, project=spec.project, method=spec.method, label=spec.label)
    assert restored.render_spec() == literal
    assert restored.instruction == spec.instruction
    for value in (False, 1, "true", None):
        with pytest.raises(ValueError, match="relative_toolchain"):
            RunSpec.from_render_spec({**literal, "relative_toolchain": value}, project=spec.project,
                                     method=spec.method, label=spec.label)
    # A relative location without the key is not a toolchain a historical spec could carry.
    with pytest.raises(ValueError, match="invalid recorded agentic toolchain"):
        RunSpec.from_render_spec({k: v for k, v in literal.items() if k != "relative_toolchain"},
                                 project=spec.project, method=spec.method, label=spec.label)


def test_rendering_away_from_the_checkout_root_is_refused(monkeypatch, tmp_path):
    with pytest.raises(ValueError, match="requires rendering from the root of the checkout"):
        monkeypatch.chdir(tmp_path)
        checkout_relative(toolchain())


def test_a_relative_location_never_climbs_out_of_the_launch_directory():
    good = {"python": ".venv/bin/python", "resources": {name: name for name in (*SCHEMAS, ".claude/commands/d4d-full-core.md")}}
    assert validate_toolchain(good, relative=True) == good
    with pytest.raises(ValueError):
        validate_toolchain(good)                                    # absolute is still the default contract
    for python in ("../other/bin/python", "", ".venv/../../bin/python"):
        with pytest.raises(ValueError):
            validate_toolchain({**good, "python": python}, relative=True)


@pytest.mark.parametrize(("kw", "message"), [
    # Without the complete line no recorder flag states the key, and the render gate would read mismatch.
    (dict(runtime="Claude Code", relative_toolchain=True), "require complete_recorder_line"),
    (dict(runtime="Claude API (direct)", relative_toolchain=True), "require complete_recorder_line"),
    (dict(runtime="Claude Code", relative_toolchain="yes"), "must be a boolean"),
])
def test_the_key_is_refused_where_it_binds_nothing(monkeypatch, kw, message):
    base = _render(monkeypatch)
    with pytest.raises(ValueError, match=message):
        RunSpec(project=base.project, arm=base.arm, method=base.method, bundle=base.bundle, label=base.label,
                condition=base.condition, manifest=base.manifest, provider="Anthropic", **kw)


def test_the_release_drivers_combination_names_nothing_under_the_operators_tree(monkeypatch):
    """Complete line, relative toolchain, stated model and effort (#6320, #6314, #6311)."""
    monkeypatch.setattr(sys, "executable", str(ROOT / ".venv/bin/python"))
    spec = _render(monkeypatch, relative_toolchain=True, reasoning_effort="high", launcher_model="example-model-9")
    assert str(ROOT) not in spec.instruction and str(ROOT) not in render_spec_payload(spec)
    line = next(row for row in spec.instruction.splitlines() if "--render-spec-env" in row)
    argv = shlex.split(line.strip())
    assert argv[:4] == [".venv/bin/python", "-m", "data_sheets_schema.cli", "provenance"]
    assert argv[-6:] == ["--render-spec-env", "D4D_RENDER_SPEC", "--render-spec-sha256",
                         hashlib.sha256(render_spec_payload(spec).encode()).hexdigest(),
                         "--prompt-text-env", "D4D_LAUNCH_INSTRUCTION"]
    carried = spec.render_spec()
    assert carried["relative_toolchain"] is True and carried["complete_recorder_line"] is True
    assert carried["launcher_model"] == "example-model-9" and carried["reasoning_effort"] == "high"
    restored = RunSpec.from_render_spec(carried, project=spec.project, method=spec.method, label=spec.label)
    assert restored.instruction == spec.instruction
