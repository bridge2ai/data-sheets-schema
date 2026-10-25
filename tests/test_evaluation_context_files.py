"""Verify explicit Step E3 (#2912) applicability context files for all 6 projects."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation_context import PREDICATES, context_digest, load_context
from data_sheets_schema.judge_contract import evaluation_contract

ROOT = Path(__file__).resolve().parent.parent
CONTEXT_DIR = ROOT / "data" / "context"

PROJECT_CONTEXTS = (
    ("cm4ai_context.yaml", False, False, 44, 78),
    ("ai_readi_context.yaml", True, True, 50, 88),
    ("chorus_context.yaml", True, True, 50, 88),
    ("voice_context.yaml", True, True, 50, 88),
    ("voice_pediatric_context.yaml", True, True, 50, 88),
    ("kids_first_context.yaml", True, True, 50, 88),
)


@pytest.mark.parametrize(
    "filename,human_subjects,regulated_access,r10_max,r20_max",
    PROJECT_CONTEXTS,
)
def test_project_context_files_normalize_and_calibrate_rubrics(
    filename: str,
    human_subjects: bool,
    regulated_access: bool,
    r10_max: int,
    r20_max: int,
) -> None:
    path = CONTEXT_DIR / filename
    assert path.is_file(), f"Missing context file: {path}"
    ctx = load_context(path)
    assert set(ctx) == PREDICATES
    assert ctx["human_subjects"]["value"] is human_subjects
    assert ctx["regulated_access"]["value"] is regulated_access
    assert len(context_digest(ctx)) == 64

    doc = {"id": "example:dataset", "name": "Synthetic dataset"}
    r10_spec = yaml.safe_load((ROOT / "data/rubric/rubric10.txt").read_bytes())
    r20_spec = yaml.safe_load((ROOT / "data/rubric/rubric20.txt").read_bytes())
    c10 = evaluation_contract("rubric10", r10_spec, ctx, doc)
    c20 = evaluation_contract("rubric20", r20_spec, ctx, doc)
    assert sum(item["max_score"] for item in c10["items"].values()) == r10_max
    assert sum(item["max_score"] for item in c20["items"].values()) == r20_max


@pytest.mark.parametrize(
    "template_name",
    ("clinical_human_template.yaml", "in_vitro_molecular_template.yaml"),
)
def test_context_templates_load_cleanly(template_name: str) -> None:
    path = CONTEXT_DIR / "templates" / template_name
    assert path.is_file()
    ctx = load_context(path)
    assert set(ctx) == PREDICATES


PROJECT_CHUNK_MANIFESTS = (
    ("cm4ai_context.yaml", "data/preprocessed/chunks/CM4AI_chunks.yaml"),
    ("ai_readi_context.yaml", "data/preprocessed/chunks/AI_READI_chunks.yaml"),
    ("chorus_context.yaml", "data/preprocessed/chunks/CHORUS_chunks.yaml"),
    ("voice_context.yaml", "data/preprocessed/chunks/VOICE_chunks.yaml"),
    ("voice_pediatric_context.yaml", "data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml"),
    ("kids_first_context.yaml", "notes/matched_cborg_2026-09-13/kids_first/chunks.yaml"),
)


@pytest.mark.parametrize("filename,chunk_manifest_rel", PROJECT_CHUNK_MANIFESTS)
def test_project_context_evidence_chunk_grounding(
    filename: str,
    chunk_manifest_rel: str,
) -> None:
    """Verify every predicate evidence string cites valid v2 bundle chunk IDs or curator_assertion (#5121)."""
    import re

    ctx = load_context(CONTEXT_DIR / filename)
    chunks_doc = yaml.safe_load((ROOT / chunk_manifest_rel).read_text(encoding="utf-8"))
    valid_chunk_ids = {c["id"] for c in chunks_doc["chunks"]}

    chunk_tag_re = re.compile(r"\[chunks:\s*([c0-9,\s]+)\]")
    for pred, entry in ctx.items():
        ev = entry["evidence"]
        m = chunk_tag_re.search(ev)
        has_curator = "curator_assertion: true" in ev
        assert m is not None or has_curator, (
            f"{filename}:{pred} must cite [chunks: cNNN, ...] or [curator_assertion: true]"
        )
        if m is not None:
            cited = [tok.strip() for tok in m.group(1).split(",") if tok.strip()]
            assert cited, f"{filename}:{pred} has empty [chunks: ...] tag"
            for cid in cited:
                assert cid in valid_chunk_ids, (
                    f"{filename}:{pred} cites unknown chunk {cid!r} not in {chunk_manifest_rel}"
                )

    if filename == "cm4ai_context.yaml":
        assert "HeLa" not in ctx["human_subjects"]["evidence"]
    if filename == "chorus_context.yaml":
        assert "PhysioNet" not in ctx["regulated_access"]["evidence"]
        assert "CITI" not in ctx["regulated_access"]["evidence"]

