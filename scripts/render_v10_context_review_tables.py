#!/usr/bin/env python3
"""Render §1.1 and §2 tables and verify §1.2 facts for the v10 decision record (R4 F1).

Computes the §1.1 evaluation-context table, the §1.2 CM4AI excluded-item lists,
and the §2 omission-context table directly from the committed files under
`data/context/`, `data/rubric/`, and `data/omission_contexts/`.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from data_sheets_schema.evaluation_context import context_digest, load_context  # noqa: E402
from data_sheets_schema.judge_contract import evaluation_contract  # noqa: E402

EVAL_PROJECTS: tuple[str, ...] = (
    "AI_READI",
    "CHORUS",
    "CM4AI",
    "VOICE",
    "VOICE_PEDIATRIC",
    "KIDS_FIRST",
)

OMISSION_PROJECTS: tuple[str, ...] = (
    "CHORUS",
    "AI_READI",
    "CM4AI",
    "VOICE",
    "VOICE_PEDIATRIC",
    "KIDS_FIRST",
)

PREDICATE_COLUMNS: tuple[str, ...] = (
    "human_subjects",
    "regulated_access",
    "shared_dataset",
    "data_collection",
    "data_processing",
    "processing_software",
    "ml_training_dataset",
)


def compute_eval_context_rows(root: Path = ROOT) -> list[dict[str, Any]]:
    """Compute §1.1 evaluation-context table rows and excluded rubric items."""
    r10_spec = yaml.safe_load((root / "data/rubric/rubric10.txt").read_bytes())
    r20_spec = yaml.safe_load((root / "data/rubric/rubric20.txt").read_bytes())
    synthetic_doc = {"id": "example:dataset", "name": "Synthetic dataset"}
    rows: list[dict[str, Any]] = []
    for project in EVAL_PROJECTS:
        rel_path = f"data/context/{project.lower()}_context.yaml"
        ctx = load_context(root / rel_path)
        digest = context_digest(ctx)
        c10 = evaluation_contract("rubric10", r10_spec, ctx, synthetic_doc)
        c20 = evaluation_contract("rubric20", r20_spec, ctx, synthetic_doc)
        r10_app = sum(1 for item in c10["items"].values() if item["applicable"])
        r10_tot = len(c10["items"])
        r10_max = float(sum(item["max_score"] for item in c10["items"].values()))
        r20_app = sum(1 for item in c20["items"].values() if item["applicable"])
        r20_tot = len(c20["items"])
        r20_max = float(sum(item["max_score"] for item in c20["items"].values()))
        excl10 = [k for k, v in c10["items"].items() if not v["applicable"]]
        excl20 = [k for k, v in c20["items"].items() if not v["applicable"]]
        rows.append(
            {
                "project": project,
                "context_file": rel_path,
                "digest": digest,
                "predicates": {col: bool(ctx[col]["value"]) for col in PREDICATE_COLUMNS},
                "r10_applicable": r10_app,
                "r10_total": r10_tot,
                "r10_max": r10_max,
                "r20_applicable": r20_app,
                "r20_total": r20_tot,
                "r20_max": r20_max,
                "excluded_r10": excl10,
                "excluded_r20": excl20,
            }
        )
    return rows


def render_section_1_1_table(root: Path = ROOT) -> str:
    """Render the Markdown table for §1.1."""
    header = (
        "| Project | Context File | Normalized Context Digest (`SHA-256`) | "
        "`human_subjects` | `regulated_access` | `shared_dataset` | `data_collection` | "
        "`data_processing` | `processing_software` | `ml_training_dataset` | "
        "Rubric 10 Applicable (`max`) | Rubric 20 Applicable (`max`) |"
    )
    sep = "| " + " | ".join(["---"] * 12) + " |"
    lines = [header, sep]
    for row in compute_eval_context_rows(root):
        preds = " | ".join(
            f"`{str(row['predicates'][col]).lower()}`" for col in PREDICATE_COLUMNS
        )
        r10_cell = f"`{row['r10_applicable']} / {row['r10_total']}` (`{row['r10_max']:.1f}`)"
        r20_cell = f"`{row['r20_applicable']} / {row['r20_total']}` (`{row['r20_max']:.1f}`)"
        lines.append(
            f"| **{row['project']}** | `{row['context_file']}` | `{row['digest']}` | "
            f"{preds} | {r10_cell} | {r20_cell} |"
        )
    return "\n".join(lines)


def compute_omission_context_rows(root: Path = ROOT) -> list[dict[str, Any]]:
    """Compute §2 omission-context table rows from `data/omission_contexts/`."""
    rows: list[dict[str, Any]] = []
    for project in OMISSION_PROJECTS:
        rel_path = f"data/omission_contexts/{project.lower()}_omission_context.json"
        doc = json.loads((root / rel_path).read_text(encoding="utf-8"))
        scope0 = doc["scopes"][0]
        vocab = doc.get("vocabulary") or {}
        rows.append(
            {
                "project": project,
                "context_file": rel_path,
                "referent": scope0["referent"],
                "release": scope0["release"],
                "basis": doc["source_policy"]["basis"],
                "vocabulary_counts": {k: len(v) for k, v in vocab.items()},
            }
        )
    return rows


def render_section_2_table(root: Path = ROOT) -> str:
    """Render the Markdown table for §2."""
    header = (
        "| Project | Draft Omission Context File | `scopes[0].referent` | "
        "`scopes[0].release` | `source_policy.basis` | `vocabulary` |"
    )
    sep = "| " + " | ".join(["---"] * 6) + " |"
    lines = [header, sep]
    for row in compute_omission_context_rows(root):
        if row["release"] is None:
            release_cell = "`null` (`D04` website-only URL mapped to `null`)"
        else:
            release_cell = f'`"{row["release"]}"`'
        vc = row["vocabulary_counts"]
        if not vc:
            vocab_cell = "`{}` (`0` terms; neutral profile)"
        else:
            vocab_cell = ", ".join(f"`{k}` (`{v}`)" for k, v in vc.items())
        lines.append(
            f'| **{row["project"]}** | `{row["context_file"]}` | `"{row["referent"]}"` | '
            f'{release_cell} | `"{row["basis"]}"` | {vocab_cell} |'
        )
    return "\n".join(lines)


def main() -> int:
    print("### §1.1 Table")
    print(render_section_1_1_table(ROOT))
    print("\n### §2 Table")
    print(render_section_2_table(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
