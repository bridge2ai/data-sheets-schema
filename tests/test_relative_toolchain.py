"""Checkout-relative toolchain locations in an agentic instruction (#6314, 2026-11-24).

The renderer-6 toolchain is bound by absolute path, and the instruction prints
it into the datasheet's `# Schema:` header and into every command. All 16
datasheets of 2026-11-22 therefore carry the operator's worktree path. Under
the opt-in `relative_toolchain`, a location under the checkout the run is
launched from is spelled relative to it.

Rendering only; nothing is written. Inputs: this checkout's study manifest and
CHORUS bundle (read to render, never sent anywhere).
"""
import sys
from pathlib import Path

import pytest

from data_sheets_schema.agentic_runtime import (RELATIVE_TOOLCHAIN_NOTE, SCHEMAS, checkout_relative, toolchain,
                                                validate_toolchain)
from data_sheets_schema.api_runner import RunSpec
from data_sheets_schema.cli.api import _spec

ROOT = Path(__file__).resolve().parents[1]
LABEL = "2099-01-01_example-claudecode-generic-v9_rep1"


def _render(monkeypatch, **kw):
    monkeypatch.chdir(ROOT)
    return _spec("CHORUS", "baseline", LABEL, "generic_v9", runtime="Claude Code", provider="Anthropic",
                 method="claudecode_agent", **kw)


def test_every_location_under_the_checkout_is_spelled_relative(monkeypatch):
    monkeypatch.setattr(sys, "executable", str(ROOT / ".venv/bin/python"))
    spec = _render(monkeypatch, relative_toolchain=True)
    bound = spec.render_spec()["agentic_toolchain"]
    assert bound["python"] == ".venv/bin/python"
    assert all(path == name for name, path in bound["resources"].items()), bound["resources"]
    text = spec.instruction
    assert str(ROOT) not in text
    assert "    # Schema: " + SCHEMAS[0] + "\n" in text
    assert "    # Schema: " + SCHEMAS[1] + "\n" in text
    assert "\n    .venv/bin/python -m data_sheets_schema.cli provenance record " in text
    assert text.endswith(RELATIVE_TOOLCHAIN_NOTE)


def test_an_interpreter_outside_the_checkout_keeps_its_absolute_path(monkeypatch):
    monkeypatch.setattr(sys, "executable", "/opt/elsewhere/bin/python")
    spec = _render(monkeypatch, relative_toolchain=True)
    bound = spec.render_spec()["agentic_toolchain"]
    assert bound["python"] == "/opt/elsewhere/bin/python"
    assert bound["resources"][SCHEMAS[0]] == SCHEMAS[0]


def test_without_the_key_the_instruction_is_the_absolute_one_and_emits_no_key(monkeypatch):
    monkeypatch.setattr(sys, "executable", str(ROOT / ".venv/bin/python"))
    absolute = _render(monkeypatch)
    relative = _render(monkeypatch, relative_toolchain=True)
    assert "relative_toolchain" not in absolute.render_spec()
    assert all(Path(path).is_absolute() for path in absolute.render_spec()["agentic_toolchain"]["resources"].values())
    # The two instructions differ only in how the locations are spelled, and in the note.
    assert (relative.instruction[:-len(RELATIVE_TOOLCHAIN_NOTE)]
            == absolute.instruction.replace(str(ROOT) + "/", ""))


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
    (dict(runtime="Claude API (direct)", relative_toolchain=True), "agentic renderers 6 to 8"),
    (dict(runtime="Claude Code", render_version=5, relative_toolchain=True), "agentic renderers 6 to 8"),
    (dict(runtime="Claude Code", relative_toolchain="yes"), "must be a boolean"),
])
def test_the_key_is_refused_where_it_binds_nothing(monkeypatch, kw, message):
    base = _render(monkeypatch)
    with pytest.raises(ValueError, match=message):
        RunSpec(project=base.project, arm=base.arm, method=base.method, bundle=base.bundle, label=base.label,
                condition=base.condition, manifest=base.manifest, provider="Anthropic", **kw)


def test_with_the_complete_recorder_line_the_specification_on_the_line_is_relative_too(monkeypatch):
    """The release driver's combination (#6320 with #6314): nothing on the line names the operator's tree."""
    import json
    import shlex

    monkeypatch.setattr(sys, "executable", str(ROOT / ".venv/bin/python"))
    spec = _render(monkeypatch, relative_toolchain=True, complete_recorder_line=True, reasoning_effort="high")
    assert str(ROOT) not in spec.instruction
    line = next(row for row in spec.instruction.splitlines() if "--render-spec-json" in row)
    argv = shlex.split(line.strip())
    assert argv[:4] == [".venv/bin/python", "-m", "data_sheets_schema.cli", "provenance"]
    carried = json.loads(argv[argv.index("--render-spec-json") + 1])
    assert carried == spec.render_spec()
    assert carried["relative_toolchain"] is True and carried["complete_recorder_line"] is True
    restored = RunSpec.from_render_spec(carried, project=spec.project, method=spec.method, label=spec.label)
    assert restored.instruction == spec.instruction
