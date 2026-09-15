"""The registered native command records the exact instruction, including v9."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import runpy
import shlex

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import api_runner
from data_sheets_schema.cli import cli
from tests.test_evidence_generation_gate import specification


@pytest.fixture
def native(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    make_spec = runpy.run_path(str(root / "notes/matched_cborg_2026-09-13/prepare_registration.py"))["spec_for"]
    initial = specification(tmp_path, "Claude Code")
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(yaml.safe_dump({"profile": "neutral", "projects": {
        "EXAMPLE": {"bundle": str(initial.bundle), "sources": []}}}))
    job = {"project": initial.project, "method": initial.method,
           "bundle": str(initial.bundle), "label": initial.label,
           "manifest": str(manifest), "chunks": str(initial.chunk_manifest),
           "profile": "neutral", "runtime": "Claude Code", "render_version": 9,
           "run_date": "2026-09-15"}
    spec = replace(make_spec(job), out_dir=tmp_path / "output")
    instruction = spec.instruction
    sent = tmp_path / "exact launch instruction.txt"
    sent.write_text(instruction)
    spec.full_path.parent.mkdir(parents=True)
    header = ("# Agent runtime: Claude Code\n# Provider: LBL CBORG (proxy to Anthropic)\n"
              "# Model: synthetic-model\n# Temperature: not observed\n")
    for path in (spec.full_path, spec.core_path):
        path.write_text(header + "id: https://example.org/cohort\nname: Example\n")
    spec.report_path.write_text("# Reconciliation\n")
    commands = [line.strip() for line in instruction.splitlines()
                if " -m data_sheets_schema.cli provenance record " in line]
    assert len(commands) == 1
    argv = shlex.split(commands[0])
    assert argv[:3] == [spec._agentic_toolchain["python"], "-m", "data_sheets_schema.cli"]
    assert argv[-2] == "--prompt-text" and argv[-1].startswith("${D4D_LAUNCH_INSTRUCTION:?")
    argv[-1] = str(sent)  # the launcher's registered environment expansion
    monkeypatch.chdir(tmp_path)
    return spec, sent, argv[3:]


def test_registration_to_rendered_command_to_recording_to_exact_replay(native):
    spec, sent, command = native
    result = CliRunner().invoke(cli, command)
    assert result.exit_code == 0, (result.output, result.exception)
    record = yaml.safe_load(spec.provenance_path.read_text())
    request = record["prompts"]["request"]
    assert request["spec"] == spec.render_spec()
    assert request["sha256"] == hashlib.sha256(sent.read_bytes()).hexdigest()
    replay = api_runner.RunSpec.from_render_spec(request["spec"], project=spec.project,
                                                method=spec.method, label=spec.label)
    assert replay.instruction.encode() == sent.read_bytes()


@pytest.mark.parametrize("change", ["text", "renderer", "profile", "runtime", "bundle", "no-text"])
def test_mismatched_registered_instruction_is_refused_before_recording(native, change, tmp_path):
    spec, sent, command = native
    if change == "text":
        sent.write_text(sent.read_text() + "\nAltered after launch.\n")
    elif change == "renderer":
        at = command.index("--render-spec-json") + 1
        value = json.loads(command[at])
        value["render_version"] = 7
        command[at] = json.dumps(value)
    elif change == "bundle":
        other = tmp_path / "other.txt"
        other.write_bytes(spec.bundle.read_bytes())
        command[command.index("--input-bundle") + 1] = str(other)
    elif change == "no-text":
        del command[-2:]
    else:
        command += ["--" + change, "bridge2ai" if change == "profile" else "different-runtime"]
    result = CliRunner().invoke(cli, command)
    assert result.exit_code != 0, result.output
    assert not spec.provenance_path.exists()
