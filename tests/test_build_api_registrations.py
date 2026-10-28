"""Tests for shared generation API registration builder (Step A3 / #1763, #4345, #2926)."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest
from click.testing import CliRunner
import jsonschema

# Ensure scripts directory is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_api_registrations import (
    DEFAULT_AUDIT_LIMITS,
    DEFAULT_PROJECTS,
    DEFAULT_RECEIPT_LIMITS,
    build_draft_context,
    build_registration,
    build_roster,
    cli,
    parse_coverage_floor,
    validate_registration_document,
    validate_roster_file,
)
from data_sheets_schema import audit_omissions, shared_generation as sg
from data_sheets_schema.cli.api import ARMS


def test_build_draft_context_valid_schema(tmp_path: Path) -> None:
    """Draft context document conforms to omission_inventory_v1/context.schema.json."""
    context_file = tmp_path / "test_context.json"
    doc = build_draft_context(
        project="CHORUS",
        context_path=context_file,
        write_to_disk=True,
    )
    assert context_file.is_file()
    assert doc["format"] == "omission_context_v1"
    assert doc["root_class"] == "Dataset"
    assert len(doc["scopes"]) == 1
    assert doc["scopes"][0]["owner"] == ""
    assert "CHoRUS" in doc["scopes"][0]["referent"]

    # Validate against context.schema.json
    schema_file = audit_omissions.ASSETS / "context.schema.json"
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def test_build_draft_context_source_manifest_metadata(tmp_path: Path) -> None:
    """Draft context incorporates source manifest scope and priority if available."""
    sm_path = tmp_path / "source_manifest.yaml"
    sm_path.write_text(
        """
scope:
  CHORUS:
    referent: "CHORUS Patient Cohort"
    referent_id: "CHORUS-2026-v1"
    referent_note: "Comprehensive EHR and ICU waveform data."
source_priority:
  tier_1: ["protocol", "dataset_profile"]
  tier_2: ["publication"]
""",
        encoding="utf-8",
    )
    doc = build_draft_context(
        project="CHORUS",
        source_manifest_path=sm_path,
        write_to_disk=False,
    )
    assert doc["scopes"][0]["referent"] == "CHORUS Patient Cohort"
    assert doc["scopes"][0]["release"] == "CHORUS-2026-v1"
    assert doc["scopes"][0]["scope"] == "Comprehensive EHR and ICU waveform data."
    assert "protocol, dataset_profile" in doc["source_policy"]["priority"]


def test_build_registration_chorus_baseline(tmp_path: Path) -> None:
    """Build a complete registration for CHORUS baseline and parse strictly."""
    reg_path = tmp_path / "reg_chorus.json"
    reg = build_registration(
        project="CHORUS",
        label="2026-10-test_chorus",
        registration_path=reg_path,
        write_to_disk=True,
    )

    assert reg_path.is_file()
    assert reg["format"] == sg.FORMAT
    assert reg["registration_id"] == "generic-v10-chorus-2026-10-test_chorus"
    assert reg["registration_path"] == str(reg_path.resolve())
    assert reg["run"]["project"] == "CHORUS"
    assert reg["run"]["arm"] == ARMS["baseline"][0]
    assert reg["run"]["method"] == ARMS["baseline"][1]
    assert reg["run"]["label"] == "2026-10-test_chorus"

    # Inputs verification
    inputs = reg["inputs"]
    assert inputs["project"] == "CHORUS"
    assert inputs["bundle"]["path"].endswith("CHORUS_preprocessed.txt")
    assert inputs["chunk_manifest"]["path"].endswith("CHORUS_chunks.yaml")
    assert inputs["context"]["path"].endswith("chorus_omission_context.json")
    assert "root" in inputs["full_schema"]
    assert "sources" in inputs["full_schema"]
    assert "root" in inputs["core_schema"]
    assert "sources" in inputs["core_schema"]
    assert inputs["profile"]["name"] is not None

    # Runtime verification
    runtime = reg["runtime"]
    assert runtime["provider"] == "LBL CBORG (proxy to Anthropic)"
    assert runtime["base_url"] == "https://api.cborg.lbl.gov"
    assert runtime["model"] == "claude-opus-5"
    assert runtime["temperature"] is None
    assert runtime["thinking"] == {"type": "adaptive", "display": "summarized"}

    # Receipt verification
    receipt = reg["receipt"]
    assert receipt["format"] == "receipt_completion_registration_v2"
    assert receipt["condition"] == "generic_v10"
    assert receipt["receipt_instrument_version"] == 4
    assert receipt["runtime_policy_sha256"] is not None

    # Parsing verification
    validated = validate_registration_document(reg)
    assert validated["registration_id"] == reg["registration_id"]


def test_build_registration_arms(tmp_path: Path) -> None:
    """Build registrations for de_novo and crate_only arms."""
    for arm_key in ("de_novo", "crate_only"):
        reg_path = tmp_path / f"reg_{arm_key}.json"
        reg = build_registration(
            project="CHORUS",
            label=f"2026-10-test_{arm_key}",
            arm=arm_key,
            registration_path=reg_path,
            write_to_disk=True,
        )
        assert reg_path.is_file()
        assert reg["run"]["arm"] == ARMS[arm_key][0]
        assert reg["run"]["method"] == ARMS[arm_key][1]
        assert validate_registration_document(reg)["registration_id"] == reg["registration_id"]


def test_build_registration_custom_limits_and_prefix(tmp_path: Path) -> None:
    """Build registration with custom id_prefix and audit limits."""
    reg_path = tmp_path / "custom_reg.json"
    custom_audit = {"max_calls": 25, "aggregate_input_tokens": 5000000}
    custom_receipt = {"context_limit_basis": "Empirical run"}

    reg = build_registration(
        project="CHORUS",
        label="custom_label",
        registration_path=reg_path,
        id_prefix="pilot-run",
        audit_limits=custom_audit,
        receipt_limits=custom_receipt,
        write_to_disk=False,
    )
    assert reg["registration_id"] == "pilot-run-chorus-custom_label"
    assert reg["audit_limits"]["max_calls"] == 25
    assert reg["audit_limits"]["aggregate_input_tokens"] == 5000000
    assert reg["receipt"]["context_limit_basis"] == "Empirical run"
    validate_registration_document(reg)


def test_build_registration_error_cases(tmp_path: Path) -> None:
    """Test error handling in build_registration for invalid arguments."""
    reg_path = tmp_path / "err_reg.json"

    # Invalid arm
    with pytest.raises(ValueError, match="unknown arm 'bad_arm'"):
        build_registration(
            project="CHORUS",
            label="test",
            arm="bad_arm",
            registration_path=reg_path,
        )

    # Missing bundle path
    with pytest.raises(FileNotFoundError, match="bundle file not found"):
        build_registration(
            project="CHORUS",
            label="test",
            bundle_path=tmp_path / "nonexistent_bundle.txt",
            registration_path=reg_path,
        )

    # Missing context path
    with pytest.raises(FileNotFoundError, match="specified context file not found"):
        build_registration(
            project="CHORUS",
            label="test",
            context_path=tmp_path / "nonexistent_context.json",
            registration_path=reg_path,
        )

    # None registration_path
    with pytest.raises(ValueError, match="registration_path must be specified"):
        build_registration(
            project="CHORUS",
            label="test",
            registration_path=None,
        )

    # Missing implicit context file fails closed unless synthesize_draft_context=True
    dummy_bundle = tmp_path / "bundle.txt"
    dummy_chunks = tmp_path / "chunks.yaml"
    dummy_bundle.write_text("BUNDLE\n", encoding="utf-8")
    dummy_chunks.write_text("version: 2\nchunks: []\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="no omission context file found"):
        build_registration(
            project="UNREGISTERED_PROJECT_XYZ",
            label="test",
            bundle_path=dummy_bundle,
            chunk_manifest_path=dummy_chunks,
            registration_path=reg_path,
            synthesize_draft_context=False,
        )


def test_build_roster_success_and_validation(tmp_path: Path) -> None:
    """Build a batch roster from multiple registrations and validate with validate_roster_file."""
    reg1_path = tmp_path / "reg1.json"
    reg2_path = tmp_path / "reg2.json"
    roster_path = tmp_path / "roster.json"

    reg1 = build_registration(
        project="CHORUS",
        label="test_batch",
        registration_path=reg1_path,
        write_to_disk=True,
    )
    reg2 = build_registration(
        project="AI_READI",
        label="test_batch",
        registration_path=reg2_path,
        write_to_disk=True,
    )

    roster = build_roster([reg1, reg2], roster_path=roster_path, write_to_disk=True)
    assert roster_path.is_file()
    assert roster["format"] == "shared_generation_batch_roster_v2"
    assert len(roster["registrations"]) == 2
    for row, reg_file in zip(roster["registrations"], (reg1_path, reg2_path)):
        import hashlib
        assert row["registration_sha256"] == hashlib.sha256(reg_file.read_bytes()).hexdigest()

    validated_roster = validate_roster_file(roster_path)
    assert len(validated_roster["registrations"]) == 2

    # Tampering with a registration file after building the v2 roster is refused by _shared_roster
    orig_bytes = reg1_path.read_bytes()
    reg1_path.write_bytes(orig_bytes + b"\n")
    with pytest.raises( Exception, match="shared registration sha256 mismatch"):
        validate_roster_file(roster_path)
    reg1_path.write_bytes(orig_bytes)


def test_build_roster_duplicate_rejection(tmp_path: Path) -> None:
    """Ensure duplicate (project, label), paths, or registration_ids raise ValueError."""
    reg1_path = tmp_path / "reg1.json"
    reg1 = build_registration(
        project="CHORUS",
        label="test_dup",
        registration_path=reg1_path,
        write_to_disk=False,
    )

    # Duplicate project & label
    with pytest.raises(ValueError, match="duplicate \\(project, label\\) pair"):
        build_roster([reg1, reg1])

    # Duplicate registration path
    reg2 = dict(reg1)
    reg2["run"] = {"project": "AI_READI", "label": "test_dup"}
    with pytest.raises(ValueError, match="duplicate registration path"):
        build_roster([reg1, reg2])

    # Duplicate registration id
    reg3 = dict(reg1)
    reg3["run"] = {"project": "AI_READI", "label": "test_dup"}
    reg3["registration_path"] = str(tmp_path / "reg3.json")
    with pytest.raises(ValueError, match="duplicate registration_id"):
        build_roster([reg1, reg3])


def test_cli_dry_run_single_and_all() -> None:
    """CLI --dry-run succeeds without writing to disk for single and all projects."""
    runner = CliRunner()

    # Single project
    result = runner.invoke(cli, ["-p", "CHORUS", "-l", "test_dry_single", "--dry-run"])
    assert result.exit_code == 0
    assert "✓ CHORUS: registration_id=" in result.output
    assert "[dry-run]" in result.output

    # All projects
    result_all = runner.invoke(cli, ["--all", "-l", "test_dry_all", "--dry-run"])
    assert result_all.exit_code == 0
    for proj in DEFAULT_PROJECTS:
        assert f"✓ {proj}:" in result_all.output
    assert "✓ Roster with 4 rows:" in result_all.output


def test_cli_file_generation_and_check(tmp_path: Path) -> None:
    """CLI generates files on disk and --check validates them (failing if roster missing)."""
    runner = CliRunner()
    out_dir = tmp_path / "registrations"
    roster_file = out_dir / "roster_check_test.json"

    # Build on disk
    res = runner.invoke(
        cli,
        [
            "-p", "CHORUS,AI_READI",
            "-l", "test_check",
            "-o", str(out_dir),
            "-r", str(roster_file),
        ],
    )
    assert res.exit_code == 0
    assert (out_dir / "registration_chorus_test_check.json").is_file()
    assert (out_dir / "registration_ai_readi_test_check.json").is_file()
    assert roster_file.is_file()

    # Verify with --check
    check_res = runner.invoke(
        cli,
        [
            "-p", "CHORUS,AI_READI",
            "-l", "test_check",
            "-o", str(out_dir),
            "-r", str(roster_file),
            "--check",
        ],
    )
    assert check_res.exit_code == 0
    assert "All checks passed." in check_res.output

    # Verify --check fails if roster path does not exist
    missing_roster = out_dir / "missing_roster.json"
    check_missing = runner.invoke(
        cli,
        [
            "-p", "CHORUS,AI_READI",
            "-l", "test_check",
            "-o", str(out_dir),
            "-r", str(missing_roster),
            "--check",
        ],
    )
    assert check_missing.exit_code != 0
    assert "Missing roster file" in check_missing.output


def test_cli_error_validation(tmp_path: Path) -> None:
    """CLI reports usage errors on invalid arguments."""
    runner = CliRunner()

    # Missing project and not --all
    res_no_proj = runner.invoke(cli, ["-l", "test_lbl"])
    assert res_no_proj.exit_code != 0
    assert "Specify at least one --project or use --all" in res_no_proj.output

    # --context with multiple projects
    dummy_context = tmp_path / "dummy_context.json"
    dummy_context.write_text("{}", encoding="utf-8")
    res_multi_ctx = runner.invoke(
        cli,
        ["-p", "CHORUS", "-p", "AI_READI", "-l", "test_lbl", "-c", str(dummy_context)],
    )
    assert res_multi_ctx.exit_code != 0
    assert "--context can only be used with a single project" in res_multi_ctx.output


def test_parse_coverage_floor() -> None:
    """Test coverage_floor parsing for pending, NUM/DEN, and decimal inputs."""
    assert parse_coverage_floor(None) == {"state": "pending", "mode": "diagnostic_pilot"}
    assert parse_coverage_floor("pending") == {"state": "pending", "mode": "diagnostic_pilot"}
    assert parse_coverage_floor("13/20") == {"state": "registered", "numerator": 13, "denominator": 20}
    assert parse_coverage_floor("0.65") == {"state": "registered", "numerator": 13, "denominator": 20}

    with pytest.raises(ValueError, match="require 0 < numerator <= denominator <= 1000"):
        parse_coverage_floor("25/20")
    with pytest.raises(ValueError, match="must be in \\(0, 1\\]"):
        parse_coverage_floor("0.0")


def test_build_registration_kids_first_neutral_profile(tmp_path: Path) -> None:
    """Build registration for KIDS_FIRST with neutral profile and registered coverage floor (Step A19-reg)."""
    reg_path = tmp_path / "reg_kids_first.json"
    reg = build_registration(
        project="KIDS_FIRST",
        label="2026-10-kfa_claude-opus-5-api-generic-v10_rep1",
        registration_path=reg_path,
        coverage_floor="13/20",
        write_to_disk=True,
    )
    assert reg_path.is_file()
    assert reg["inputs"]["project"] == "KIDS_FIRST"
    assert reg["inputs"]["bundle"]["path"].endswith("KIDS_FIRST_preprocessed.txt")
    assert reg["inputs"]["chunk_manifest"]["path"].endswith("kids_first/chunks.yaml")
    assert reg["inputs"]["profile"]["name"] == "neutral"
    assert reg["inputs"]["profile"]["vocabulary"] is None
    assert reg["receipt"]["coverage_floor"] == {"state": "registered", "numerator": 13, "denominator": 20}
    validate_registration_document(reg)


def test_cli_multi_replicate_roster_and_custom_limits(tmp_path: Path) -> None:
    """CLI --label-prefix --replicates 3 --coverage-floor 13/20 builds a valid 3-row production roster."""
    runner = CliRunner()
    out_dir = tmp_path / "prod_registrations"
    prefix = "2026-10-pda_claude-opus-5-api-generic-v10"

    res = runner.invoke(
        cli,
        [
            "-p", "CHORUS",
            "--label-prefix", prefix,
            "--replicates", "3",
            "--coverage-floor", "13/20",
            "--max-paths", "144",
            "--max-workers", "18",
            "--max-calls", "20",
            "-o", str(out_dir),
        ],
    )
    assert res.exit_code == 0, res.output
    roster_file = out_dir / f"roster_{prefix}.json"
    assert roster_file.is_file()

    expected_pairs = [("CHORUS", f"{prefix}_rep{i}") for i in (1, 2, 3)]
    validated = validate_roster_file(roster_file, expected_pairs)
    assert len(validated["registrations"]) == 3

    reg1 = json.loads((out_dir / f"registration_chorus_{prefix}_rep1.json").read_text(encoding="utf-8"))
    assert reg1["audit_limits"]["max_paths"] == 144
    assert reg1["audit_limits"]["max_workers"] == 18
    assert reg1["audit_limits"]["max_calls"] == 20
    assert reg1["receipt"]["coverage_floor"] == {"state": "registered", "numerator": 13, "denominator": 20}

    # Check mode succeeds for multi-replicate roster
    check_res = runner.invoke(
        cli,
        [
            "-p", "CHORUS",
            "--label-prefix", prefix,
            "--replicates", "3",
            "-o", str(out_dir),
            "--check",
        ],
    )
    assert check_res.exit_code == 0, check_res.output


def test_overwrite_guard_requires_replace_on_changed_content(tmp_path: Path) -> None:
    """Rebuilding at an existing path with different parameters refuses unless replace=True / --replace."""
    reg_path = tmp_path / "reg_guard.json"
    build_registration(
        project="CHORUS",
        label="test_guard",
        registration_path=reg_path,
        coverage_floor="pending",
        write_to_disk=True,
    )
    # Identical rebuild succeeds without replace
    build_registration(
        project="CHORUS",
        label="test_guard",
        registration_path=reg_path,
        coverage_floor="pending",
        write_to_disk=True,
    )
    # Changed parameter refuses without replace
    with pytest.raises(FileExistsError, match="already exists with different bytes; pass --replace to overwrite"):
        build_registration(
            project="CHORUS",
            label="test_guard",
            registration_path=reg_path,
            coverage_floor="13/20",
            write_to_disk=True,
        )
    # Succeeds with replace=True
    updated = build_registration(
        project="CHORUS",
        label="test_guard",
        registration_path=reg_path,
        coverage_floor="13/20",
        write_to_disk=True,
        replace=True,
    )
    assert updated["receipt"]["coverage_floor"] == {"state": "registered", "numerator": 13, "denominator": 20}

    # CLI outputs sha256= and honors --replace
    runner = CliRunner()
    cli_dir = tmp_path / "cli_guard"
    res1 = runner.invoke(cli, ["-p", "CHORUS", "-l", "cli_lbl", "-o", str(cli_dir), "--max-calls", "18"])
    assert res1.exit_code == 0
    assert "sha256=" in res1.output

    res2 = runner.invoke(cli, ["-p", "CHORUS", "-l", "cli_lbl", "-o", str(cli_dir), "--max-calls", "20"])
    assert res2.exit_code != 0
    assert "already exists with different bytes; pass --replace to overwrite" in str(res2.exception)

    res3 = runner.invoke(cli, ["-p", "CHORUS", "-l", "cli_lbl", "-o", str(cli_dir), "--max-calls", "20", "--replace"])
    assert res3.exit_code == 0
    assert "sha256=" in res3.output

