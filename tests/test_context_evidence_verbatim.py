"""Strict bundle-literal acceptance gate requested by #5517.

This deliberately does not accept shared vocabulary as proof of a whole claim.
Existing narrative contexts need human authoring before this gate can pass.
Citation and curator-decision metadata are not represented as source quotations.
"""
from pathlib import Path
import hashlib
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTEXTS = sorted((ROOT / "data/context").glob("*_context.yaml"))


def test_context_inventory_is_not_empty_or_partial():
    assert {path.stem for path in CONTEXTS} == {
        "ai_readi_context", "chorus_context", "cm4ai_context", "kids_first_context",
        "voice_context", "voice_pediatric_context",
    }


def evidence_body(evidence):
    return re.sub(r"^(?:\[(?:chunks:|curator_assertion:)[^]]+\]\s*)+", "", evidence)


def test_literal_check_does_not_accept_terms_or_casefolding():
    bundle = "The resultant bam is de-dupped and base score recalibrated."
    assert evidence_body("[chunks: c006] " + bundle) in bundle
    assert evidence_body("[chunks: c006] GATK Base Quality Score Recalibration") not in bundle
    assert evidence_body("[chunks: c006] " + bundle.upper()) not in bundle
    assert evidence_body("[chunks: c006] " + bundle + " HMB") not in bundle


@pytest.mark.corpus
@pytest.mark.parametrize("path", CONTEXTS, ids=lambda p: p.stem)
def test_every_evidence_string_occurs_verbatim_in_its_bundle(path):
    project = path.stem.removesuffix("_context")
    if project == "kids_first":
        manifest_path = ROOT / "notes/matched_cborg_2026-09-13/kids_first/chunks.yaml"
        bundle_directory = manifest_path.parent
    else:
        source_manifest = yaml.safe_load((ROOT / "data/preprocessed/source_manifest.yaml").read_text())
        assert project.upper() in source_manifest["projects"]
        manifest_path = ROOT / f"data/preprocessed/chunks/{project.upper()}_chunks.yaml"
        bundle_directory = ROOT / "data/preprocessed/concatenated"
    manifest = yaml.safe_load(manifest_path.read_text())
    bundle_path = bundle_directory / manifest["bundle"]
    assert hashlib.sha256(bundle_path.read_bytes()).hexdigest() == manifest["bundle_sha256"]
    bundle = bundle_path.read_text()
    context = yaml.safe_load(path.read_text())
    assert set(context) == {"human_subjects", "regulated_access", "shared_dataset",
                            "data_collection", "data_processing", "processing_software", "ml_training_dataset"}
    unmatched = [predicate for predicate, entry in context.items()
                 if not evidence_body(entry["evidence"]) or evidence_body(entry["evidence"]) not in bundle]
    assert not unmatched, f"{path.name}: needs human authoring of literal evidence: {unmatched}"
