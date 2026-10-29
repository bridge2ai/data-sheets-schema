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
    active_text = _without_retired_quotations(note_text)
    assert "6e3c6b6d" not in active_text
    assert "10.18130/V3/F3TD5R" not in active_text


# Historical quotations the decision record keeps verbatim from the retired D46 entry (§5.10). Each is
# exempt only inside its own section and only once; a forbidden token anywhere else is an active claim.
RETIRED_QUOTATIONS = (
    ("## 2. ", "the hash the retired entry gave (`6e3c6b6d…`)"),
    ("## 4. ", "including `#5120` fixes for `CM4AI` (`release: \"https://doi.org/10.18130/V3/F3TD5R\"`, tier 1 `[\"ro_crate\"]`)"),
    ("## 4. ", "`CHORUS` omission context bytes remain unchanged (`6e3c6b6d…`)"),
    ("### 5.9 ", "`CM4AI` `scopes[0].release` set to `\"https://doi.org/10.18130/V3/F3TD5R\"`"),
    ("### 5.9 ", "`CHORUS` omission context bytes remain unchanged (`6e3c6b6d4be3201b6511fb3fd0f3761874a6cfbe94d7280cd1b983863bf56ca3`)"),
)


def _section_bounds(lines: list[str], heading_prefix: str) -> tuple[int, int]:
    """Line range of the one section whose heading starts with heading_prefix, up to the next heading of its level or higher."""
    starts = [i for i, line in enumerate(lines) if line.startswith(heading_prefix)]
    assert len(starts) == 1, f"expected exactly one section {heading_prefix!r}, found {len(starts)}"
    level = len(heading_prefix) - len(heading_prefix.lstrip("#"))
    end = starts[0] + 1
    while end < len(lines):
        line = lines[end]
        if line.startswith("#") and len(line) - len(line.lstrip("#")) <= level:
            break
        end += 1
    return starts[0], end


def _without_retired_quotations(note_text: str) -> str:
    """Remove each retired quotation from its own section, requiring exactly one occurrence there."""
    lines = note_text.split("\n")
    for heading_prefix, quotation in RETIRED_QUOTATIONS:
        start, end = _section_bounds(lines, heading_prefix)
        section = "\n".join(lines[start:end])
        assert section.count(quotation) == 1, (
            f"retired quotation must occur exactly once in section {heading_prefix!r}: {quotation[:60]!r}"
        )
        lines[start:end] = section.replace(quotation, "").split("\n")
    return "\n".join(lines)


@pytest.mark.parametrize("token", ("10.18130/V3/F3TD5R", "6e3c6b6d"))
@pytest.mark.parametrize(
    "claim",
    (
        "5. **`D46`** — Current approved setting\nCurrent approved value: {token}",
        "| **`D46`** | Current approved setting | {token} |",
        "- **Not an owner ruling** in the past; current approved value: {token}",
        "Current approved value: {token}",
    ),
)
def test_an_active_claim_cannot_borrow_the_retired_exemption(claim: str, token: str) -> None:
    """A forbidden token outside the retired quotations stays visible, however it is dressed (codex wave-5 A23 review)."""
    note_path = ROOT / "notes" / "reviews" / "v10_human_decisions_and_context_review_2026-10-20.md"
    mutated = note_path.read_text(encoding="utf-8") + "\n\n## Active current setting\n\n" + claim.format(token=token) + "\n"
    assert token in _without_retired_quotations(mutated)


def test_a_duplicated_retired_quotation_is_refused() -> None:
    note_path = ROOT / "notes" / "reviews" / "v10_human_decisions_and_context_review_2026-10-20.md"
    note_text = note_path.read_text(encoding="utf-8")
    quotation = RETIRED_QUOTATIONS[2][1]
    mutated = note_text.replace(quotation, quotation + " " + quotation, 1)
    with pytest.raises(AssertionError, match="exactly once"):
        _without_retired_quotations(mutated)
