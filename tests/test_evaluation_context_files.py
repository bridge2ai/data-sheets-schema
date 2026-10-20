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
