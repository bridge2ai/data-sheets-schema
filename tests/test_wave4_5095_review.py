"""Independent #5095 / #5122 / #5156 causal review, 2026-10-27.

Inputs: the selected checkout and synthetic temporary registrations/resources.
Outputs: offline pytest assertions, including retained failures. No providers,
historical run edits, source mutations or executable-authority guard patches.
"""

import copy
from pathlib import Path
import shutil

from click.testing import CliRunner
import pytest

from scripts import build_api_registrations as builder
from data_sheets_schema import shared_generation as sg


ROOT = Path(__file__).resolve().parents[1]


def registration(tmp_path):
    return builder.build_registration(
        project="CHORUS", label="wave4_review", registration_path=tmp_path / "registration_chorus_wave4_review.json",
        write_to_disk=False,
    )


def stage_schema(pin, target_root):
    """Copy the real import closure while retaining installed LinkML imports."""
    staged = copy.deepcopy(pin)
    for entry in staged["sources"]:
        original = Path(entry["path"])
        if original.is_relative_to(ROOT):
            target = target_root / original.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original.read_bytes())
            entry["path"] = str(target)
    staged["root"] = staged["sources"][0]["path"]
    return staged


@pytest.mark.parametrize("schema", ["full_schema", "core_schema"])
def test_check_cli_refuses_changed_pinned_schema_bytes(tmp_path, schema):
    reg = registration(tmp_path)
    reg["inputs"][schema] = stage_schema(reg["inputs"][schema], tmp_path / "resources")
    reg_path = Path(reg["registration_path"])
    reg_path.write_bytes(sg.canonical(reg))
    builder.build_roster([reg], roster_path=tmp_path / "roster_wave4_review.json")
    args = ["-p", "CHORUS", "-l", "wave4_review", "-o", str(tmp_path), "--check"]
    runner = CliRunner()
    before = runner.invoke(builder.cli, args)
    assert before.exit_code == 0, before.output

    pinned_schema = Path(reg["inputs"][schema]["root"])
    pinned_schema.write_bytes(pinned_schema.read_bytes() + b"\n# post-registration drift\n")
    after = runner.invoke(builder.cli, args)
    assert after.exit_code != 0, (
        f"#5122: --check accepted changed {schema} bytes and printed:\n{after.output}"
    )


def test_worktree_override_uses_selected_tree_schema_resources(tmp_path):
    initial = registration(tmp_path)
    target = tmp_path / "selected_worktree"
    target.mkdir()
    shutil.copyfile(ROOT / "pyproject.toml", target / "pyproject.toml")
    expected = {}
    for name in ("full_schema", "core_schema"):
        expected[name] = stage_schema(initial["inputs"][name], target)
    for name, raw in sg.captured_assets().items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    for pin in (initial["runtime"]["config"], initial["inputs"]["profile"]["vocabulary"]):
        if pin and Path(pin["path"]).is_relative_to(ROOT):
            original = Path(pin["path"])
            staged = target / original.relative_to(ROOT)
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(original.read_bytes())

    # All dataset inputs are explicitly supplied; the worktree selects the
    # schema/protocol resources. The caller intentionally remains in ROOT.
    reg = builder.build_registration(
        project="CHORUS", label="wave4_foreign_worktree",
        registration_path=tmp_path / "foreign_registration.json", worktree=target,
        bundle_path=initial["inputs"]["bundle"]["path"],
        chunk_manifest_path=initial["inputs"]["chunk_manifest"]["path"],
        source_manifest_path=initial["inputs"]["source_manifest"]["path"],
        context_path=initial["inputs"]["context"]["path"], write_to_disk=False,
    )
    assert reg["inputs"]["full_schema"]["root"] == expected["full_schema"]["root"], (
        "#5122: --worktree schema authority still comes from caller/import root"
    )
    assert reg["inputs"]["core_schema"]["root"] == expected["core_schema"]["root"]


def test_input_pin_verifier_still_refuses_changed_bundle(tmp_path):
    reg = registration(tmp_path)
    bundle = tmp_path / "bundle.txt"
    bundle.write_bytes(Path(reg["inputs"]["bundle"]["path"]).read_bytes())
    reg["inputs"]["bundle"] = sg.file_pin(bundle)
    builder.verify_registration_input_pins(reg)
    bundle.write_bytes(bundle.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="inputs.bundle SHA-256 mismatch"):
        builder.verify_registration_input_pins(reg)


def test_new_phase_cap_fields_preserve_row_precedence_and_disagreement(tmp_path):
    import yaml
    from data_sheets_schema.runs import arm_facts

    folder = tmp_path / "claudecode_api_core" / "wave4_caps_rep1"
    folder.mkdir(parents=True)
    (folder / "CHORUS_provenance.yaml").write_text(yaml.safe_dump({
        "run": {"project": "CHORUS", "label": "wave4_caps_rep1", "method": "claudecode_api"},
        "model": {"max_tokens_by_phase": {"reconcile_full": 32000, "report": 64000}},
        "api_usage": [
            {"phase": "reconcile_full", "max_tokens": 128000},
            {"phase": "reconcile_full", "max_tokens": 64000},
        ],
    }))
    facts = arm_facts("wave4_caps", method="claudecode_api", concat_dir=tmp_path)
    assert facts["values"]["reconcile_full max_tokens"] == ["128000", "64000"]
    assert facts["values"]["report max_tokens"] == ["64000"]
