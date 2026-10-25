"""Unit tests for Step A5d: Draft Scope Contexts Builder.

Validates that draft omission_context_v1 files comply with:
- omission_inventory_v1/context.schema.json
- shared_generation.py capture assertions (root owner once, distinct owners)
- Decision D04 (CHORUS release is null)
- Issue #422 (no diagnoses, labels, or prior-arm content)
- Integration with scripts/build_api_registrations.py
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator

from data_sheets_schema import audit_omissions as omissions
from data_sheets_schema import shared_generation as sg
from scripts.build_draft_contexts import (
    ALL_CAMPAIGN_PROJECTS,
    ALL_GC_PROJECTS,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_OUT_DIR,
    DEFAULT_PROJECTS,
    KIDS_FIRST_MANIFEST_PATH,
    SCHEMA_PATH,
    build_draft_scope_context,
    generate_draft_contexts,
    load_context_schema,
    main,
)
from scripts.build_api_registrations import build_registration


@pytest.fixture
def manifest_data():
    import yaml
    return yaml.safe_load(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8")) or {}


@pytest.fixture
def context_schema():
    return load_context_schema()


def test_schema_file_matches_frozen_asset():
    """Verify that SCHEMA_PATH matches the frozen asset sha256."""
    raw = SCHEMA_PATH.read_bytes()
    expected_raw = omissions._asset("context.schema.json")
    assert raw == expected_raw


def test_chorus_draft_context(manifest_data, context_schema):
    """Test CHORUS draft context properties and Decision D04 (release null)."""
    doc = build_draft_scope_context("CHORUS", manifest_data)

    assert doc["format"] == "omission_context_v1"
    assert doc["root_class"] == "Dataset"
    assert "B2AI_SUBSTRATE" in doc["vocabulary"]
    assert "B2AI_TOPIC" in doc["vocabulary"]
    assert len(doc["scopes"]) == 1

    root_scope = doc["scopes"][0]
    assert root_scope["owner"] == ""
    assert "CHoRUS" in root_scope["referent"]
    # Decision D04: release must be null
    assert root_scope["release"] is None
    assert root_scope["scope"]

    # Validate against context.schema.json
    validator = Draft202012Validator(context_schema)
    errors = list(validator.iter_errors(doc))
    assert not errors, f"CHORUS draft context validation errors: {errors}"
    assert omissions._shape(doc, context_schema) == []


def test_ai_readi_draft_context(manifest_data, context_schema):
    """Test AI_READI draft context properties."""
    doc = build_draft_scope_context("AI_READI", manifest_data)

    assert doc["format"] == "omission_context_v1"
    assert doc["root_class"] == "Dataset"
    assert len(doc["scopes"]) == 1

    root_scope = doc["scopes"][0]
    assert root_scope["owner"] == ""
    assert "AI-READI" in root_scope["referent"]
    assert root_scope["release"] == "https://doi.org/10.60775/fairhub.3"
    assert "fairhub" in root_scope["scope"]

    validator = Draft202012Validator(context_schema)
    errors = list(validator.iter_errors(doc))
    assert not errors, f"AI_READI draft context validation errors: {errors}"
    assert omissions._shape(doc, context_schema) == []


def test_all_gc_projects_valid(manifest_data, context_schema):
    """Test that all declared Grand Challenge projects can generate valid draft contexts."""
    for proj in ALL_GC_PROJECTS:
        doc = build_draft_scope_context(proj, manifest_data)
        errors = list(Draft202012Validator(context_schema).iter_errors(doc))
        assert not errors, f"{proj} context validation errors: {errors}"

        # shared_generation root owner assertions
        owners = [s["owner"] for s in doc["scopes"]]
        assert owners.count("") == 1
        assert len(owners) == len(set(owners))


def test_source_policy_structure(manifest_data):
    """Test source_policy extraction conforms to source_manifest.yaml tiers."""
    doc = build_draft_scope_context("CHORUS", manifest_data)
    policy = doc["source_policy"]
    assert "priority" in policy
    assert "basis" in policy
    assert len(policy["priority"]) == 5
    assert "RO-Crate" in policy["priority"][0]
    assert "historical" in policy["priority"][4]


def test_no_issue_422_forbidden_content(manifest_data):
    """Ensure no diagnoses or run arm contamination in any project draft (#422)."""
    forbidden_terms = ["diagnosis", "diagnoses", "prior-arm", "baseline arm", "de novo arm"]
    for proj in ALL_GC_PROJECTS:
        doc = build_draft_scope_context(proj, manifest_data)
        serialized = json.dumps(doc).lower()
        for term in forbidden_terms:
            assert term not in serialized, f"Forbidden term '{term}' found in {proj} draft context"


def test_generate_and_check_cli(tmp_path):
    """Test CLI generation and verification in temporary directory."""
    out_dir = tmp_path / "contexts"

    # Step 1: Generate
    ret = main(["--projects", "CHORUS,AI_READI", "--out-dir", str(out_dir)])
    assert ret == 0
    assert (out_dir / "chorus_omission_context.json").is_file()
    assert (out_dir / "ai_readi_omission_context.json").is_file()

    # Step 2: Check (should pass)
    ret_check = main(["--projects", "CHORUS,AI_READI", "--out-dir", str(out_dir), "--check"])
    assert ret_check == 0

    # Step 3: Tamper file and check should fail
    tampered_file = out_dir / "chorus_omission_context.json"
    tampered_data = json.loads(tampered_file.read_text(encoding="utf-8"))
    tampered_data["scopes"][0]["referent"] = "Tampered Referent"
    tampered_file.write_text(json.dumps(tampered_data), encoding="utf-8")

    ret_tampered = main(["--projects", "CHORUS,AI_READI", "--out-dir", str(out_dir), "--check"])
    assert ret_tampered == 1


def test_build_registration_finds_draft_contexts(tmp_path):
    """Test that build_api_registrations automatically resolves candidate draft context from data/omission_contexts."""
    reg_path = tmp_path / "test_reg.json"
    bundle_path = tmp_path / "bundle.txt"
    chunks_path = tmp_path / "chunks.yaml"
    bundle_path.write_text("DUMMY BUNDLE CONTENT\n", encoding="utf-8")
    chunks_path.write_text("version: 2\nchunks: []\n", encoding="utf-8")

    reg = build_registration(
        project="CHORUS",
        label="test_label",
        registration_path=reg_path,
        bundle_path=bundle_path,
        chunk_manifest_path=chunks_path,
    )

    # Context should resolve to the newly created data/omission_contexts/chorus_omission_context.json
    expected_context_path = str(DEFAULT_OUT_DIR / "chorus_omission_context.json")
    assert reg["inputs"]["context"]["path"] == expected_context_path


def test_kids_first_draft_context_neutral_profile(context_schema):
    """Test KIDS_FIRST draft context uses neutral profile with empty vocabulary and valid source_policy."""
    import yaml

    kf_data = yaml.safe_load(KIDS_FIRST_MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    doc = build_draft_scope_context("KIDS_FIRST", kf_data)

    assert doc["format"] == "omission_context_v1"
    assert doc["root_class"] == "Dataset"
    assert doc["vocabulary"] == {}
    assert len(doc["scopes"]) == 1
    assert doc["scopes"][0]["owner"] == ""
    assert "Kids First Data Resource" in doc["scopes"][0]["referent"]
    assert doc["scopes"][0]["release"] == "https://kidsfirstdrc.org/"
    assert len(doc["source_policy"]["priority"]) >= 3
    assert "publication abstract" in doc["source_policy"]["priority"]

    errors = list(Draft202012Validator(context_schema).iter_errors(doc))
    assert not errors, f"KIDS_FIRST context validation errors: {errors}"
    assert omissions._shape(doc, context_schema) == []
    assert "KIDS_FIRST" in ALL_CAMPAIGN_PROJECTS


def test_chorus_omission_context_frozen_sha256(manifest_data):
    """Verify CHORUS context bytes stay identical (#5120) and release=null comes from source_manifest.yaml."""
    import hashlib

    assert "release" in manifest_data["scope"]["CHORUS"]
    assert manifest_data["scope"]["CHORUS"]["release"] is None

    chorus_path = DEFAULT_OUT_DIR / "chorus_omission_context.json"
    raw = chorus_path.read_bytes()
    assert len(raw) == 6476
    assert (
        hashlib.sha256(raw).hexdigest()
        == "ac94a74bd0d7d6c656564d67e656c7dbcf6627dca4c147a876eded072a81a3b0"
    )


def test_voice_carries_related_but_distinct(manifest_data):
    """Verify VOICE and VOICE_PEDIATRIC carry related_but_distinct into scopes[0].scope (#5120)."""
    voice_doc = build_draft_scope_context("VOICE", manifest_data)
    assert "datasets that are NOT this one:" in voice_doc["scopes"][0]["scope"]
    assert "b2ai-voice-pediatric" in voice_doc["scopes"][0]["scope"]

    vp_doc = build_draft_scope_context("VOICE_PEDIATRIC", manifest_data)
    assert "datasets that are NOT this one:" in vp_doc["scopes"][0]["scope"]
    assert "37yb-1t42" in vp_doc["scopes"][0]["scope"]


def test_single_synthesizer_agreement_between_builders(manifest_data):
    """Verify build_api_registrations.build_draft_context and build_draft_contexts agree on all 6 projects (#5120)."""
    import yaml
    from scripts.build_api_registrations import build_draft_context

    kf_data = yaml.safe_load(KIDS_FIRST_MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    for proj in ALL_CAMPAIGN_PROJECTS:
        mdata = kf_data if proj == "KIDS_FIRST" else manifest_data
        from_draft_builder = build_draft_scope_context(proj, mdata)
        from_reg_builder = build_draft_context(proj)
        assert from_reg_builder == from_draft_builder, f"Synthesizer mismatch for {proj}"
        if proj == "KIDS_FIRST":
            assert from_reg_builder["vocabulary"] == {}

