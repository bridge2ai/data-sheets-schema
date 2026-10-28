"""PR #5095 F1/F2/F4 regressions, 2026-10-28.

Inputs: temporary CHORUS registrations and copied schema closures.
Outputs: offline refusal and help-contract assertions; no provider calls.
"""

import copy
from pathlib import Path

from click.testing import CliRunner
import pytest

from scripts import build_api_registrations as builder
from data_sheets_schema import shared_generation as sg
from tests.test_wave4_5095_review import registration, stage_schema


@pytest.fixture
def checked_batch(tmp_path):
    reg = registration(tmp_path)
    reg_path = Path(reg["registration_path"])
    reg_path.write_bytes(sg.canonical(reg))
    roster_path = tmp_path / "roster_wave4_review.json"
    builder.build_roster([reg], roster_path=roster_path)
    args = ["-p", "CHORUS", "-l", "wave4_review", "-o", str(tmp_path), "--check"]
    result = CliRunner().invoke(builder.cli, args)
    assert result.exit_code == 0, result.output
    return reg, reg_path, roster_path, args


@pytest.mark.parametrize("drift", [False, True], ids=["intact-pins", "schema-drift"])
def test_check_verifies_roster_registration_and_requires_out_dir_path(checked_batch, tmp_path, drift):
    reg, _, roster_path, args = checked_batch
    alternate = copy.deepcopy(reg)
    alternate_path = tmp_path / "elsewhere" / "registration.json"
    alternate_path.parent.mkdir()
    alternate["registration_path"] = str(alternate_path)
    alternate["inputs"]["full_schema"] = stage_schema(reg["inputs"]["full_schema"], tmp_path / "resources")
    alternate_path.write_bytes(sg.canonical(alternate))
    builder.build_roster([alternate], roster_path=roster_path, replace=True)
    builder.verify_registration_input_pins(alternate)
    if drift:
        schema = Path(alternate["inputs"]["full_schema"]["root"])
        schema.write_bytes(schema.read_bytes() + b"\n# drift after roster registration\n")
        with pytest.raises(ValueError, match=r"Pinned inputs.full_schema.sources\[0\] SHA-256 mismatch"):
            builder.verify_registration_input_pins(alternate)
    result = CliRunner().invoke(builder.cli, args)
    assert result.exit_code != 0, result.output
    expected = ("Pinned inputs.full_schema.sources[0] SHA-256 mismatch" if drift
                else "Roster registration path differs from verified out-dir file")
    assert expected in result.output
    assert "All checks passed." not in result.output


def test_check_requires_out_dir_declared_registration_path(checked_batch, tmp_path):
    reg, reg_path, roster_path, args = checked_batch
    # Both files contain valid registration bytes; the roster's copy declares
    # its true path, while the out-dir copy declares somebody else's authority.
    alternate_path = tmp_path / "elsewhere.json"
    reg["registration_path"] = str(alternate_path)
    alternate_path.write_bytes(sg.canonical(reg))
    reg_path.write_bytes(sg.canonical(reg))
    builder.build_roster([reg], roster_path=roster_path, replace=True)
    result = CliRunner().invoke(builder.cli, args)
    assert result.exit_code != 0, result.output
    assert "Out-dir registration path differs from its declared authority" in result.output


def test_check_requires_same_registration_bytes_at_roster_capture(checked_batch, monkeypatch):
    reg, reg_path, roster_path, args = checked_batch
    validate = builder.validate_roster_file

    def replace_between_captures(path, pairs):
        reg["registration_id"] += "-changed"
        reg_path.write_bytes(sg.canonical(reg))
        builder.build_roster([reg], roster_path=roster_path, replace=True)
        return validate(path, pairs)

    monkeypatch.setattr(builder, "validate_roster_file", replace_between_captures)
    result = CliRunner().invoke(builder.cli, args)
    assert result.exit_code != 0, result.output
    assert "Roster registration SHA-256 differs from verified out-dir file" in result.output


def test_help_states_pin_check_scope_and_worktree_interpreter():
    result = CliRunner().invoke(builder.cli, ["--help"])
    assert result.exit_code == 0
    help_text = " ".join(result.output.split())
    assert "attests pinned bytes, not runtime admission" in help_text
    assert "selected checkout's own venv" in help_text
    assert "python -S with site-packages on PYTHONPATH" in help_text
