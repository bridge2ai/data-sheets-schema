"""A17/A13 integration regressions, 2026-10-28; refs #5211/#5158.

Inputs: temporary offline registrations. Outputs: assertions that staged
replacement writes retain v2 roster byte authority and selected-root paths.
No provider calls, real run outputs or owner-worktree edits.
"""
import hashlib
import json
from pathlib import Path

from click.testing import CliRunner
from scripts import build_api_registrations as builder
from tests.test_preflight_resource_authority import selected_resources


def test_staged_replacement_roster_pins_the_new_registration(tmp_path):
    runner = CliRunner()
    output = tmp_path / "prepared"
    arguments = ["-p", "CHORUS", "-l", "replacement", "--partition", "chorus", "-o", str(output)]
    initial = runner.invoke(builder.cli, arguments)
    assert initial.exit_code == 0, initial.output
    registration = output / "registration_chorus_replacement.json"
    prior_bytes = registration.read_bytes()
    replacement = runner.invoke(builder.cli, [*arguments, "--max-calls", "20", "--replace"])
    assert replacement.exit_code == 0, replacement.output
    assert registration.read_bytes() != prior_bytes
    roster = json.loads((output / "roster_replacement.json").read_text())
    assert roster["registrations"][0]["registration_sha256"] == hashlib.sha256(registration.read_bytes()).hexdigest()
    checked = runner.invoke(builder.cli, [*arguments, "--check"])
    assert checked.exit_code == 0, checked.output


def test_existing_registration_roster_keeps_actual_serialization(tmp_path):
    registration = tmp_path / "pretty.json"
    reg = builder.build_registration("CHORUS", "pretty", partition="chorus",
                                     registration_path=registration, write_to_disk=False)
    registration.write_text(json.dumps(reg, indent=4) + "\n", encoding="utf-8")
    roster = builder.build_roster([reg], write_to_disk=False)
    assert roster["registrations"][0]["registration_sha256"] == hashlib.sha256(registration.read_bytes()).hexdigest()


def test_prepare_and_commit_keep_relative_paths_in_selected_worktree(selected_resources):
    selected, _, arguments = selected_resources
    before = Path.cwd()
    arguments["registration_path"] = Path("relative-output/registration.json")
    arguments["write_to_disk"] = True
    reg = builder.build_registration(**arguments)
    assert Path.cwd() == before
    assert Path(reg["registration_path"]) == selected / "relative-output/registration.json"
    assert Path(reg["registration_path"]).is_file()
    builder.verify_registration_input_pins(reg, worktree=selected)
    assert Path.cwd() == before
