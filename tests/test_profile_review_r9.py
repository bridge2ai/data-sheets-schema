"""Recovered review findings about legacy profiles and safe reconstruction."""
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import profiles, provenance, schema_digest, usage_ledger
from data_sheets_schema.cli.provenance import provenance as command
from tests.test_profile_review_r8 import generation  # noqa: F401


@pytest.fixture
def reconstruction(generation, monkeypatch):
    spec = replace(generation, runtime="Claude Code", provider="offline", run_date="2026-09-13",
                   out_dir=None)
    target = generation.metadata_dir / "reconstruct_provenance.yaml"
    data = {"record_generated_at": "2026-09-13T12:00:00Z",
            "model": {"provider": "offline"}, "schema": {},
            "inputs": {"bundle_path": str(spec.bundle),
                       "source_manifest": {"path": str(spec.manifest)},
                       "chunks": {"path": str(spec.chunk_manifest)}},
            # A fresh agentic instruction pins its selected output paths;
            # reconstruction needs the same evidence as a real record (#1753).
            "outputs": {key: {"path": str(getattr(spec, f"{key}_path"))}
                        for key in ("full", "core", "report")},
            "prompts": {"request": {"sha256": hashlib.sha256(spec.instruction.encode()).hexdigest()}}}
    monkeypatch.setattr(provenance, "record_path_for", lambda *a, **kw: target)
    args = ["backfill-spec", "--project", spec.project, "--method", spec.method,
            "--label", spec.label, "--condition", spec.condition, "--runtime", spec.runtime]
    return target, data, args


@pytest.mark.parametrize("schema", [None, {}, {"digest_md5": "older-digest"}])
def test_historical_profile_fallback_agrees_with_a_study_spec(schema):
    data = {"schema": schema, "prompts": {"request": {"spec": {"profile": "bridge2ai"}}}}
    assert provenance._spec_profile_disagreement(data) is None
    data["prompts"]["request"]["spec"]["profile"] = "neutral"
    assert "different instruments" in provenance._spec_profile_disagreement(data)


@pytest.mark.parametrize("execute", [False, True])
@pytest.mark.parametrize("conflicting", [False, True])
def test_backfill_checks_digest_evidence_before_reporting_or_writing(reconstruction, execute, conflicting):
    target, data, args = reconstruction
    data["schema"]["digest_md5"] = schema_digest.fingerprint(schema_digest.digest_text(
        "Dataset", profile=profiles.PROFILES["bridge2ai" if conflicting else "neutral"]))
    target.write_text(yaml.safe_dump(data))
    before = target.read_bytes()
    result = CliRunner().invoke(command, [*args, *(["--execute"] if execute else [])])
    assert result.exit_code == int(conflicting), (result.output, result.exception)
    if conflicting:
        assert "digest" in result.output
        assert target.read_bytes() == before
    elif execute:
        assert yaml.safe_load(target.read_text())["schema"]["profile"] == "neutral"
    else:
        assert target.read_bytes() == before


@pytest.mark.parametrize("value", [{}, [], False, 0, ""])
def test_backfill_refuses_false_valued_malformed_profiles(reconstruction, value):
    target, data, args = reconstruction
    data["schema"]["profile"] = value
    target.write_text(yaml.safe_dump(data))
    before = target.read_bytes()
    result = CliRunner().invoke(command, [*args, "--execute"])
    assert result.exit_code == 1, (result.output, result.exception)
    assert "schema.profile" in result.output
    assert target.read_bytes() == before


@pytest.mark.parametrize("block,value", [
    ("prompts", "text"), ("prompts", {"request": "text"}),
    ("schema", "text"), ("inputs", "text"), ("model", "text"),
    ("record_generated_at", 20260913), ("record_generated_at", "not-a-date"),
])
def test_backfill_reports_malformed_blocks_without_writing(reconstruction, block, value):
    target, data, args = reconstruction
    data[block] = value
    target.write_text(yaml.safe_dump(data))
    before = target.read_bytes()
    result = CliRunner().invoke(command, [*args, "--execute"])
    assert result.exit_code == 1 and isinstance(result.exception, SystemExit), (
        result.output, result.exception)
    assert block in result.output
    assert target.read_bytes() == before


@pytest.mark.parametrize("pin", [{}, {"instruction": {}}, {"instruction": "text"},
    {"instruction": {"spec": {"bundle": "b"}}},
    {"instruction": {"spec": {}, "sha256": "x"}}])
def test_damaged_pins_do_not_claim_a_historical_instruction(pin):
    assert not usage_ledger.pre_profile_pin(pin)
    reason = usage_ledger.identity_refusal(pin, "during resume")
    assert "restore the recorded inputs" in reason
    assert "cannot be resumed" not in reason


def test_recognizable_historical_instruction_retains_its_explanation(generation):
    pin = deepcopy(generation.input_identity())
    pin["instruction"]["spec"].pop("profile")
    assert usage_ledger.pre_profile_pin(pin)
    assert "cannot be resumed" in usage_ledger.identity_refusal(pin, "during resume")


def test_real_null_bundle_identity_is_self_comparable(generation):
    null = replace(generation, bundle=None, manifest=None, chunk_manifest=None).input_identity()
    assert null["bundle"] is None
    assert not usage_ledger._identity_differs(null, null)
    assert usage_ledger._identity_differs(null, generation.input_identity())
