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
    if filename == "voice_pediatric_context.yaml":
        assert "Hospital for Sick Children" in ctx["human_subjects"]["evidence"]
        assert "North America" not in ctx["human_subjects"]["evidence"]
        assert "Butterworth" not in ctx["data_processing"]["evidence"]
        assert "Whisper" not in ctx["processing_software"]["evidence"]
    if filename == "ai_readi_context.yaml":
        assert "WFDB (WaveForm DataBase) for 12-lead cardiac ECG" in ctx["data_processing"]["evidence"]
    if filename == "kids_first_context.yaml":
        assert "Six Bridges" not in ctx["data_processing"]["evidence"]
        assert "GenotypeGVCFs" not in ctx["processing_software"]["evidence"]
        assert "c013" in ctx["processing_software"]["evidence"]


def test_v10_decision_record_tables_match_committed_contexts() -> None:
    """Verify §1.1, §1.2, and §2 of the v10 decision record match committed context files (R4 F1)."""
    import importlib.util

    script_path = ROOT / "scripts" / "render_v10_context_review_tables.py"
    spec = importlib.util.spec_from_file_location("render_v10_context_review_tables", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    note_path = ROOT / "notes" / "reviews" / "v10_human_decisions_and_context_review_2026-10-20.md"
    note_text = note_path.read_text(encoding="utf-8")

    expected_s1_1 = mod.render_section_1_1_table(ROOT)
    expected_s2 = mod.render_section_2_table(ROOT)
    assert expected_s1_1 in note_text, "§1.1 evaluation-context table in v10 decision record is out of sync"
    assert expected_s2 in note_text, "§2 omission-context table in v10 decision record is out of sync"

    eval_rows = {row["project"]: row for row in mod.compute_eval_context_rows(ROOT)}
    cm4ai = eval_rows["CM4AI"]
    assert cm4ai["excluded_r10"] == ["E2.2", "E4.1", "E4.2", "E4.3", "E4.4", "E4.5"]
    assert cm4ai["excluded_r20"] == ["Q8", "Q15"]
    assert "`E2.2`, `E4.1`, `E4.2`, `E4.3`, `E4.4`, `E4.5`" in note_text
    assert "`Q8`, `Q15`" in note_text
    assert "`processing_software: true`" in note_text

    import hashlib

    chorus_omission_sha = hashlib.sha256(
        (ROOT / "data" / "omission_contexts" / "chorus_omission_context.json").read_bytes()
    ).hexdigest()
    assert chorus_omission_sha in note_text
    assert "6e3c6b6d" not in note_text
    assert "10.18130/V3/F3TD5R" not in note_text


