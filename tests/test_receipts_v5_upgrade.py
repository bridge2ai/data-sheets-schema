"""Tests for the v5 receipts upgrade (Mungall 2026-10-23 JBIMS Workshop alignment).

Covers:
1. Structured polarity (`supports`), `evidence_source`, `explanation`, and
   `check_fast_entailment` in `receipts.py` (`instrument_version=5`).
2. Tool-computed / non-text evidence receipts (`verify_tool_receipt`) in
   `receipts.py` (`instrument_version=5`).
3. Provedown-style inline verifiable watermarks in `provedown.py` and opt-in
   integration in `report_claims.py` (`check_watermarks=True`, v9).
4. Declarative `linkml-map` transformation specification (`linkml_mappings/full-to-core-mapping.yaml`)
   and transformation receipts in `transformation_receipts.py` + `derive_core.py`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import derive_core as dc
from data_sheets_schema import provedown as pd
from data_sheets_schema import receipts as rc
from data_sheets_schema import report_claims as rclaims
from data_sheets_schema import transformation_receipts as tr


def _sample_bundle() -> tuple[dict, dict[str, str], str]:
    c1 = (
        "Dataset Title: Bridge2AI Voice Cohort Release 1.0 (grant OT2OD032701).\n"
        "The clinical cohort enrolled adult patients across 5 hospital sites.\n"
        "Storage allocation requires 2 GB of memory per worker node.\n"
    )
    c2 = (
        "Distribution archive voice_release_v1.tar.gz contains 3 files.\n"
        "No companion genomics assay was performed in this release.\n"
    )
    bundle = c1 + c2
    b_md5 = hashlib.md5(bundle.encode("utf-8")).hexdigest()
    manifest = {
        "bundle_md5": b_md5,
        "total_bytes": len(bundle.encode("utf-8")),
        "chunks": [
            {
                "id": "c001",
                "md5": hashlib.md5(c1.encode("utf-8")).hexdigest(),
                "sha256": hashlib.sha256(c1.encode("utf-8")).hexdigest(),
                "bytes": len(c1.encode("utf-8")),
                "lines": [1, 3],
            },
            {
                "id": "c002",
                "md5": hashlib.md5(c2.encode("utf-8")).hexdigest(),
                "sha256": hashlib.sha256(c2.encode("utf-8")).hexdigest(),
                "bytes": len(c2.encode("utf-8")),
                "lines": [4, 5],
            },
        ],
    }
    return manifest, {"c001": c1, "c002": c2}, b_md5


# ---------------------------------------------------------------------------
# 1. Structured Polarity, Evidence Source, Explanation & Fast Entailment (v5)
# ---------------------------------------------------------------------------


def test_fast_entailment_unit_and_numeric_equivalences():
    ok, why = rc.check_fast_entailment(
        "2048 MB",
        "Storage allocation requires 2 GB of memory per worker node.",
    )
    assert ok is True
    assert "unit_conversion" in why

    ok_num, why_num = rc.check_fast_entailment(
        165051,
        "The release includes 165,051 audio recordings across participants.",
    )
    assert ok_num is True
    assert why_num == "numeric_equivalence"

    ok_pct, why_pct = rc.check_fast_entailment(
        0.75,
        "Exactly 75% of participants completed the follow-up survey.",
    )
    assert ok_pct is True
    assert why_pct == "numeric_equivalence"


def test_fast_entailment_explained_bridge_vs_ungrounded_explanation():
    snippet = "The clinical cohort enrolled adult patients across 5 hospital sites."
    # Grounded explanation: shares tokens with snippet ("adult", "patients") and value ("homo", "sapiens")
    ok, why = rc.check_fast_entailment(
        "Homo sapiens",
        snippet,
        explanation="adult patients in a clinical cohort implies human (Homo sapiens)",
    )
    assert ok is True
    assert why == "explained_bridge"

    # Ungrounded explanation: shares no 4+ char tokens with snippet
    ok_bad, why_bad = rc.check_fast_entailment(
        "Homo sapiens",
        snippet,
        explanation="inferred from standard biomedical ontology defaults",
    )
    assert ok_bad is False
    assert why_bad == "ungrounded_explanation"


def test_check_v5_polarity_entailment_and_refuted_slot():
    manifest, chunk_texts, b_md5 = _sample_bundle()
    full = {
        "id": "bridge2ai:voice-v1",
        "title": "Bridge2AI Voice Cohort Release 1.0",
        "species": "Homo sapiens",
        "description": "2048 MB",
        " is_tabular": "companion genomics assay",
    }
    # Fix key name without leading space
    full = {
        "id": "bridge2ai:voice-v1",
        "title": "Bridge2AI Voice Cohort Release 1.0",
        "species": "Homo sapiens",
        "description": "2048 MB",
        "keywords": ["companion genomics assay"],
    }
    receipt = {
        "bundle_md5": b_md5,
        "chunks": [
            {
                "id": "c001",
                "status": "extracted",
                "extracted": [
                    {
                        "slot": "id",
                        "snippet": "Dataset Title: Bridge2AI Voice Cohort Release 1.0 (grant OT2OD032701).",
                        "supports": "SUPPORT",
                        "evidence_source": "BUNDLE_TEXT",
                    },
                    {
                        "slot": "title",
                        "snippet": "Dataset Title: Bridge2AI Voice Cohort Release 1.0 (grant OT2OD032701).",
                        "supports": "SUPPORT",
                        "evidence_source": "PUBLICATION",
                    },
                    {
                        "slot": "species",
                        "snippet": "The clinical cohort enrolled adult patients across 5 hospital sites.",
                        "supports": "SUPPORT",
                        "evidence_source": "HUMAN_CLINICAL",
                        "explanation": "adult patients in a clinical cohort implies Homo sapiens",
                    },
                    {
                        "slot": "description",
                        "snippet": "Storage allocation requires 2 GB of memory per worker node.",
                        "supports": "PARTIAL",
                        "evidence_source": "BUNDLE_TEXT",
                        "explanation": "2 GB equals 2048 MB",
                    },
                ],
            },
            {
                "id": "c002",
                "status": "extracted",
                "extracted": [
                    {
                        "slot": "keywords[0]",
                        "snippet": "No companion genomics assay was performed in this release.",
                        "supports": "REFUTE",
                        "evidence_source": "BUNDLE_TEXT",
                        "explanation": "Explicitly states no companion genomics assay was performed.",
                    }
                ],
            },
        ],
    }

    block_v5 = rc.check(receipt, manifest, chunk_texts, full, b_md5, instrument_version=5)
    assert block_v5["instrument"] == rc.RECEIPTS_V5_INSTRUMENT
    assert block_v5["by_polarity"] == {
        "SUPPORT": 3,
        "PARTIAL": 1,
        "REFUTE": 1,
        "NO_EVIDENCE": 0,
        "NEUTRAL": 0,
    }
    assert block_v5["by_evidence_source"]["HUMAN_CLINICAL"] == 1
    assert block_v5["by_evidence_source"]["PUBLICATION"] == 1
    # Both species (explained bridge) and description (2 GB -> 2048 MB) are entailed_non_literal, not no_value_overlap
    assert block_v5["snippets"]["entailed_non_literal"] == 2
    assert block_v5["snippets"]["no_value_overlap"] == 0
    # keywords[0] has only a REFUTE receipt -> excluded from with_receipt and emits populated_slot_refuted_by_receipt
    assert "keywords" in block_v5["slots"]["without_receipt"]
    assert any(
        f["kind"] == "populated_slot_refuted_by_receipt" and f["slot"] in ("keywords", "keywords[0]")
        for f in block_v5["findings"]
    )

    # Verify v3 and v4 remain untouched in their structure
    block_v3 = rc.check(receipt, manifest, chunk_texts, full, b_md5, instrument_version=3)
    assert block_v3["instrument"] == rc.RECEIPTS_INSTRUMENT
    assert "by_polarity" not in block_v3
    assert "entailed_non_literal" not in block_v3["snippets"]


# ---------------------------------------------------------------------------
# 2. Tool-Computed / Non-Text Evidence Receipts (v5)
# ---------------------------------------------------------------------------


def test_verify_tool_receipts_and_v5_coverage():
    manifest, chunk_texts, b_md5 = _sample_bundle()
    full = {
        "id": "bridge2ai:voice-v1",
        "title": "Bridge2AI Voice Cohort Release 1.0",
        "total_files": 3,
        "total_bytes": 600,
        "files": [
            {"id": "f1", "name": "a.wav", "bytes": 100},
            {"id": "f2", "name": "b.wav", "bytes": 200},
            {"id": "f3", "name": "c.wav", "bytes": 300},
        ],
    }
    receipt = {
        "bundle_md5": b_md5,
        "chunks": [
            {
                "id": "c001",
                "status": "extracted",
                "extracted": [
                    {
                        "slot": "id",
                        "snippet": "Dataset Title: Bridge2AI Voice Cohort Release 1.0 (grant OT2OD032701).",
                    },
                    {
                        "slot": "title",
                        "snippet": "Dataset Title: Bridge2AI Voice Cohort Release 1.0 (grant OT2OD032701).",
                    },
                    {
                        "slot": "total_files",
                        "supports": "SUPPORT",
                        "evidence_source": "TOOL_COMPUTATION",
                        "tool": {
                            "name": "record_count",
                            "target": "record:files",
                            "result": 3,
                        },
                        "explanation": "Counted 3 file entries in full.files.",
                    },
                    {
                        "slot": "total_bytes",
                        "supports": "SUPPORT",
                        "evidence_source": "TOOL_COMPUTATION",
                        "tool": {
                            "name": "record_sum",
                            "target": "record:files",
                            "args": {"field": "bytes"},
                            "result": 600,
                        },
                        "explanation": "Sum of bytes across full.files[0..2].",
                    },
                ],
            },
            {
                "id": "c002",
                "status": "nothing_relevant",
                "reason": "Summary text already covered.",
            },
        ],
    }

    block_v5 = rc.check(receipt, manifest, chunk_texts, full, b_md5, instrument_version=5)
    assert block_v5["tool_receipts"] == {
        "total": 2,
        "verified": 2,
        "mismatched": 0,
        "mismatched_sample": [],
    }
    assert "total_files" not in block_v5["slots"]["without_receipt"]
    assert "total_bytes" not in block_v5["slots"]["without_receipt"]

    # Now test a mismatched tool receipt
    bad_pair = {
        "slot": "total_files",
        "tool": {"name": "record_count", "target": "record:files", "result": 99},
    }
    ok, why, comp = rc.verify_tool_receipt(bad_pair, "c001", chunk_texts, manifest, full)
    assert ok is False
    assert comp == 3
    assert "3 != declared result 99" in why


def test_apply_rereceipt_v5_accepts_tool_and_metadata():
    manifest, chunk_texts, b_md5 = _sample_bundle()
    full = {
        "id": "bridge2ai:voice-v1",
        "title": "Bridge2AI Voice Cohort Release 1.0",
        "total_files": 2,
    }
    initial_receipt = {
        "bundle_md5": b_md5,
        "chunks": [
            {
                "id": "c001",
                "status": "extracted",
                "extracted": [
                    {
                        "slot": "id",
                        "snippet": "Dataset Title: Bridge2AI Voice Cohort Release 1.0 (grant OT2OD032701).",
                    },
                    {
                        "slot": "title",
                        "snippet": "Dataset Title: Bridge2AI Voice Cohort Release 1.0 (grant OT2OD032701).",
                    },
                ],
            },
            {"id": "c002", "status": "nothing_relevant", "reason": "Not yet extracted."},
        ],
    }
    rereceipt_answers = [
        {
            "path": "total_files",
            "receipt": {
                "chunk": "c002",
                "supports": "SUPPORT",
                "evidence_source": "TOOL_COMPUTATION",
                "explanation": "Manifest contains 2 chunks.",
                "tool": {"name": "manifest_chunk_count", "target": "manifest", "result": 2},
            },
        }
    ]
    res = rc.apply_rereceipt(
        initial_receipt,
        full,
        rereceipt_answers,
        chunk_texts,
        listed=["total_files"],
        instrument_version=5,
        manifest=manifest,
    )
    assert res["added"] == 1
    assert res["rejected"] == 0
    c2_pairs = res["receipt"]["chunks"][1]["extracted"]
    assert len(c2_pairs) == 1
    assert c2_pairs[0]["origin"] == "rereceipt"
    assert c2_pairs[0]["supports"] == "SUPPORT"
    assert c2_pairs[0]["evidence_source"] == "TOOL_COMPUTATION"
    assert c2_pairs[0]["tool"]["name"] == "manifest_chunk_count"


# ---------------------------------------------------------------------------
# 3. Provedown Inline Verifiable Watermarks (`provedown.py` & `report_claims.py`)
# ---------------------------------------------------------------------------


def test_provedown_extract_render_and_verify():
    manifest, chunk_texts, b_md5 = _sample_bundle()
    full = {
        "id": "bridge2ai:voice-v1",
        "title": "Bridge2AI Voice Cohort Release 1.0",
        "total_files": 165051,
        "creators": [{"name": "Alice"}, {"name": "Bob"}],
    }
    core = {"id": "bridge2ai:voice-v1", "distributions": [{"name": "dist1"}]}
    receipt_block = {
        "slots": {"with_receipt": 64, "receiptable": 75},
        "snippets": {"verified": 120, "total": 120},
    }

    report_md = (
        "# Reconciliation Report\n\n"
        "The dataset contains `165,051`{pd: full:/total_files} files authored by "
        "`2`{pd: count(full:/creators)} principal creators.\n"
        "Receipt coverage reached `64/75`{pd: ratio(receipt:/slots/with_receipt, receipt:/slots/receiptable)} "
        "(`85.3%`{pd: pct(receipt:/slots/with_receipt, receipt:/slots/receiptable)}).\n"
        "Grant [OT2OD032701]<!-- pd: chunk:c001 --> was verified in the bundle, and "
        "projected to `distributions`{pd: schema:CoreDataset.distributions}.\n"
    )

    wms = pd.extract_watermarks(report_md)
    assert len(wms) == 6

    v_res = pd.verify_watermarks(
        report_md,
        full=full,
        core=core,
        receipt_block=receipt_block,
        chunk_texts=chunk_texts,
    )
    assert v_res["checked"] is True
    assert v_res["total"] == 6
    assert v_res["verified"] == 6
    assert v_res["mismatched"] == 0
    assert v_res["findings"] == []

    # Introduce drift into the prose number (165,051 -> 165,999)
    drifted_md = report_md.replace("`165,051`", "`165,999`")
    v_drift = pd.verify_watermarks(
        drifted_md,
        full=full,
        core=core,
        receipt_block=receipt_block,
        chunk_texts=chunk_texts,
    )
    assert v_drift["mismatched"] == 1
    assert v_drift["findings"][0]["kind"] == "watermark_value_mismatch"

    # Check round-trip rendering helper
    rendered = pd.render_watermark(
        "pct(receipt:/slots/with_receipt, receipt:/slots/receiptable)",
        full=full,
        core=core,
        receipt_block=receipt_block,
    )
    assert rendered == "`85.3%`{pd: pct(receipt:/slots/with_receipt, receipt:/slots/receiptable)}"


def test_report_claims_v9_watermark_integration():
    full = {"id": "bridge2ai:voice-v1", "total_files": 42}
    core = {"id": "bridge2ai:voice-v1"}
    md_good = "Summary: `42`{pd: full:/total_files} files.\n"
    md_bad = "Summary: `99`{pd: full:/total_files} files.\n"

    # Default v8 ignores watermarks for backward compatibility
    res_v8 = rclaims.check_report(md_bad, full, core)
    assert res_v8["instrument"] == rclaims.REPORT_CLAIMS_INSTRUMENT
    assert "watermarks" not in res_v8
    assert res_v8["findings"] == []

    # Opt-in v9 checks watermarks and gates on drift
    res_v9_good = rclaims.check_report(md_good, full, core, check_watermarks=True)
    assert res_v9_good["instrument"] == rclaims.REPORT_CLAIMS_INSTRUMENT_V9
    assert res_v9_good["watermarks"]["verified"] == 1
    assert res_v9_good["findings"] == []

    res_v9_bad = rclaims.check_report(md_bad, full, core, check_watermarks=True)
    assert res_v9_bad["watermarks"]["mismatched"] == 1
    assert len(res_v9_bad["findings"]) == 1
    assert any(f["section"] == "provedown_watermarks" for f in res_v9_bad["findings"])


# ---------------------------------------------------------------------------
# 4. Declarative Transformation Receipts via `linkml-map`
# ---------------------------------------------------------------------------


def test_linkml_map_spec_matches_pair_schema():
    check = tr.validate_spec_against_pair_schema()
    assert check["valid"] is True, f"Spec drift against pair_schema: {check}"


def test_declarative_derivation_and_transformation_receipt():
    full = {
        "id": "bridge2ai:test-ds",
        "title": "Test Dataset",
        "description": "A test dataset for declarative linkml-map projection.",
        "language": "en",
        "conforms_to": "https://w3id.org/bridge2ai/data-sheets-schema/",
        "conforms_to_class": "Dataset",
        "conforms_to_schema": "https://w3id.org/bridge2ai/data-sheets-schema/full",
        "dialect": {"delimiter": ","},
        "file_collections": [
            {
                "id": "fc1",
                "name": "Tabular Collection",
                "total_bytes": 4096,
                "total_files": 2,
                "collection_type": "TABULAR",
                "files": [
                    {"id": "ignored_nested", "name": "nested.csv", "bytes": 2048},
                ],
            }
        ],
        "files": [
            {
                "id": "f_top",
                "name": "readme.md",
                "bytes": 512,
                "encoding": "UTF-8",
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
            }
        ],
    }

    imperative_core = dc.derive_core(full)
    declarative_core = tr.derive_core_declarative(full)
    assert declarative_core == imperative_core

    t_receipt = tr.emit_transformation_receipt(full, declarative_core)
    v_res = tr.verify_transformation_receipt(full, declarative_core, t_receipt)
    assert v_res["checked"] is True
    assert v_res["mismatched"] == 0
    assert v_res["findings"] == []

    # Tamper with a target value in CoreDataset and confirm verification fails
    tampered_core = dict(declarative_core)
    tampered_core["distributions"] = [dict(declarative_core["distributions"][0], bytes=999999)]
    v_tampered = tr.verify_transformation_receipt(full, tampered_core, t_receipt)
    assert v_tampered["mismatched"] >= 1
    assert any(f["kind"] == "transformation_value_mismatch" for f in v_tampered["findings"])

    # Confirm derive_core.derivation_facts supports include_transformation_receipt=True
    facts_default = dc.derivation_facts(full)
    assert "transformation_receipt" not in facts_default
    facts_with_tr = dc.derivation_facts(full, include_transformation_receipt=True)
    assert "transformation_receipt" in facts_with_tr
    assert facts_with_tr["transformation_receipt"]["verification"]["mismatched"] == 0


def test_declarative_derivation_parity_on_corpus_records():
    repo_root = Path(__file__).resolve().parent.parent
    full_files = sorted((repo_root / "data" / "d4d_concatenated" / "claudecode").glob("*_d4d.yaml"))
    assert full_files, "Expected at least one *_d4d.yaml in data/d4d_concatenated/claudecode"
    for p in full_files:
        full_doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        imp = dc.derive_core(full_doc)
        dec = tr.derive_core_declarative(full_doc)
        assert dec == imp, f"Declarative vs imperative mismatch on {p}"
        t_rec = tr.emit_transformation_receipt(full_doc, dec)
        v_res = tr.verify_transformation_receipt(full_doc, dec, t_rec)
        assert v_res["mismatched"] == 0, f"Transformation receipt failed on {p}: {v_res}"


def test_v5_instrument_names_at_receipt_counters_and_preserves_v4_string():
    """Verify RERECEIPTS_INSTRUMENT (v4) stays unchanged while RECEIPTS_V5_INSTRUMENT (v5)
    explicitly names `slots.receiptable_at_receipt` and `slots.with_receipt_at_receipt`,
    and both v4 and v5 compute those counters against the phase-1 snapshot (D37, replacing D32)."""
    # 1. RERECEIPTS_INSTRUMENT (v4) is unchanged so v4 rereceipt-policy and
    #    receipt-completion hashes are preserved.
    assert "receiptable_at_receipt" not in rc.RERECEIPTS_INSTRUMENT
    assert "with_receipt_at_receipt" not in rc.RERECEIPTS_INSTRUMENT
    assert "added_after_receipt_unmatched" not in rc.RERECEIPTS_INSTRUMENT
    assert rc.receipt_instrument(4) == rc.RERECEIPTS_INSTRUMENT

    # 2. RECEIPTS_V5_INSTRUMENT (v5) explicitly names `slots.receiptable_at_receipt`
    #    and `slots.with_receipt_at_receipt`, and removes D32's `added_after_receipt_unmatched`.
    assert "slots.receiptable_at_receipt" in rc.RECEIPTS_V5_INSTRUMENT
    assert "slots.with_receipt_at_receipt" in rc.RECEIPTS_V5_INSTRUMENT
    assert "added_after_receipt_unmatched" not in rc.RECEIPTS_V5_INSTRUMENT
    assert rc.receipt_instrument(5) == rc.RECEIPTS_V5_INSTRUMENT

    # 3. Both v4 and v5 compute `slots["receiptable_at_receipt"]` and
    #    `slots["with_receipt_at_receipt"]` directly on the phase-1 snapshot
    #    (where moved/renamed unreceipted phase-1 leaves remain uncovered in the
    #    snapshot and post-receipt additions are absent), while v3 omits the keys.
    manifest, chunk_texts, b_md5 = _sample_bundle()
    original = {
        "id": "bridge2ai:voice-v1",
        "title": "Bridge2AI Voice Cohort Release 1.0",
        "old_slot": "Unreceipted Phase-1 Value",
    }
    final = {
        "id": "bridge2ai:voice-v1",
        "title": "Bridge2AI Voice Cohort Release 1.0",
        "renamed_slot": "Unreceipted Phase-1 Value",  # moved/renamed from original -> uncovered in original!
        "genuinely_new_slot": "Added In Phase 3 Only",  # added after receipt -> not in original!
    }
    receipt = {
        "bundle_md5": b_md5,
        "chunks": [
            {
                "id": "c001",
                "status": "extracted",
                "extracted": [
                    {
                        "slot": "title",
                        "snippet": "Dataset Title: Bridge2AI Voice Cohort Release 1.0 (grant OT2OD032701).",
                    }
                ],
            },
            {"id": "c002", "status": "nothing_relevant", "reason": "No extra fields."},
        ],
    }

    block_v3 = rc.check(receipt, manifest, chunk_texts, final, b_md5, original=original, instrument_version=3)
    assert "receiptable_at_receipt" not in block_v3["slots"]
    assert "with_receipt_at_receipt" not in block_v3["slots"]
    assert "added_after_receipt_unmatched" not in block_v3["slots"]

    block_v4 = rc.check(receipt, manifest, chunk_texts, final, b_md5, original=original, instrument_version=4)
    assert block_v4["slots"]["added_after_receipt"] == 2
    assert "added_after_receipt_unmatched" not in block_v4["slots"]
    assert block_v4["slots"]["receiptable_at_receipt"] == 3
    assert block_v4["slots"]["with_receipt_at_receipt"] == 1

    block_v5 = rc.check(receipt, manifest, chunk_texts, final, b_md5, original=original, instrument_version=5)
    assert block_v5["slots"]["added_after_receipt"] == 2
    assert "added_after_receipt_unmatched" not in block_v5["slots"]
    assert block_v5["slots"]["receiptable_at_receipt"] == 3
    assert block_v5["slots"]["with_receipt_at_receipt"] == 1

    block_v5_no_snap = rc.check(receipt, manifest, chunk_texts, final, b_md5, original=None, instrument_version=5)
    assert block_v5_no_snap["slots"]["receiptable_at_receipt"] is None
    assert block_v5_no_snap["slots"]["with_receipt_at_receipt"] is None

