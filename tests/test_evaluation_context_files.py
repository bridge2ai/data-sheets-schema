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

