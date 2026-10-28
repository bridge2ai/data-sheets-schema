"""Independent R_V5 regressions, 2026-10-26; inputs: exact 662b5c4c8.

Offline expected-correct assertions for #5224–#5227; known failures are review
evidence, not xfails. Positive controls exercise all ten registered tools.
"""
from __future__ import annotations

import hashlib

import pytest
import yaml

from data_sheets_schema import receipts as rc
from data_sheets_schema import provedown as pd
from data_sheets_schema import report_claims as reports


TEXT = "The archive contains 2 MB of observations.\nAlpha beta alpha.\n"
MD5 = hashlib.md5(TEXT.encode()).hexdigest()
MANIFEST = {
    "bundle_md5": MD5, "bundle_sha256": hashlib.sha256(TEXT.encode()).hexdigest(),
    "chunks": [{"id": "c001", "bytes": len(TEXT.encode()), "md5": MD5}],
}
TEXTS = {"c001": TEXT}


def pair(name, result, *, args=None, slot="total_files"):
    return {"slot": slot, "tool": {"name": name, "result": result, "args": args or {}}}


def receipt(p):
    return {"bundle_md5": MD5, "chunks": [{"id": "c001", "status": "extracted", "extracted": [p]}]}


@pytest.mark.parametrize("name,args,result", [
    ("md5", {}, MD5),
    ("sha256", {}, hashlib.sha256(TEXT.encode()).hexdigest()),
    ("byte_length", {}, len(TEXT.encode())),
    ("line_count", {}, 2),
    ("regex_count", {"pattern": "[Aa]lpha"}, 2),
    ("manifest_chunk_count", {}, 1),
    ("manifest_total_bytes", {}, len(TEXT.encode())),
    ("record_count", {"path": "items"}, 2),
    ("record_sum", {"path": "items", "field": "bytes"}, 5),
    ("unit_convert", {"value": 2, "from_unit": "mb", "to_unit": "b"}, 2000000),
])
def test_positive_all_ten_tools(name, args, result):
    full = {"total_files": result, "items": [{"bytes": 2}, {"bytes": 3}]}
    ok, reason, actual = rc.verify_tool_receipt(pair(name, result, args=args), "c001", TEXTS, MANIFEST, full)
    assert ok, reason
    assert actual == result


def test_unit_conversion_requires_observed_source_quantity():
    p = pair("unit_convert", 999000000, args={"value": 999, "from_unit": "mb", "to_unit": "b"}, slot="total_bytes")
    block = rc.check(receipt(p), MANIFEST, TEXTS, {"total_bytes": 999000000}, MD5, instrument_version=5)
    assert block["tool_receipts"]["verified"] == 0
    assert block["slots"]["with_receipt"] == 0


@pytest.mark.parametrize("slot_value", [2, "1000"])
def test_count_result_must_equal_record_value(slot_value):
    ok, reason, _ = rc.verify_tool_receipt(pair("manifest_chunk_count", 1), "c001", TEXTS, MANIFEST, {"total_files": slot_value})
    assert not ok, reason


def test_neutral_is_not_positive_attestation():
    p = {"slot": "description", "snippet": TEXT.splitlines()[0], "supports": "NEUTRAL"}
    block = rc.check(receipt(p), MANIFEST, TEXTS, {"description": TEXT.splitlines()[0]}, MD5, instrument_version=5)
    assert block["by_polarity"]["NEUTRAL"] == 1
    assert block["slots"]["with_receipt"] == 0


def test_nonfinite_tool_input_returns_structured_refusal():
    p = pair("unit_convert", 1, args={"value": float("inf"), "from_unit": "mb", "to_unit": "b"})
    ok, _, _ = rc.verify_tool_receipt(p, "c001", TEXTS, MANIFEST, {"total_files": 1})
    assert not ok


def test_tool_phase1_uses_original_record_for_d37_accounting():
    original = {"total_files": 2, "items": [1, 2]}
    final = {"total_files": 3, "items": [1, 2, 3]}
    p = pair("record_count", 2, args={"path": "items"})
    ok, reason, result = rc.verify_tool_receipt(p, "c001", TEXTS, MANIFEST, final, original)
    assert ok, (reason, result)


def test_d37_tool_numerator_is_invariant_to_later_record_edit():
    from pathlib import Path
    assert Path(rc.__file__).resolve() == Path(__file__).resolve().parents[1] / "src/data_sheets_schema/receipts.py"
    original = {"total_files": 2, "file_collections": [{"id": "example:f1"}, {"id": "example:f2"}]}
    final = {"total_files": 3, "file_collections": original["file_collections"] + [{"id": "example:f3"}]}
    doc = receipt(pair("record_count", 2, args={"path": "file_collections"}))
    before = rc.check(doc, MANIFEST, TEXTS, original, MD5, original, instrument_version=5)
    after = rc.check(doc, MANIFEST, TEXTS, final, MD5, original, instrument_version=5)
    assert before["slots"]["with_receipt_at_receipt"] == 1
    assert after["slots"]["receiptable_at_receipt"] == before["slots"]["receiptable_at_receipt"]
    assert after["slots"]["with_receipt_at_receipt"] == before["slots"]["with_receipt_at_receipt"]


def test_hash_tool_honors_declared_snippet_target():
    p = pair("md5", MD5, slot="md5")
    p["tool"]["target"] = "snippet"
    p["snippet"] = "Alpha beta alpha."
    assert hashlib.md5(p["snippet"].encode()).hexdigest() != MD5
    ok, reason, _ = rc.verify_tool_receipt(p, "c001", TEXTS, MANIFEST, {"md5": MD5})
    assert not ok, reason


@pytest.mark.parametrize("value,snippet", [
    ("100 MB", "The archive requires 100 GB of storage."),
    ("2026-11-30", "Released October 23, 2026."),
    ("200 participants at 5 sites", "There were 300 participants at 5 sites."),
])
def test_entailment_does_not_accept_one_shared_number(value, snippet):
    ok, reason = rc.check_fast_entailment(value, snippet)
    assert not ok, reason


def test_number_words_include_million():
    ok, reason = rc.check_fast_entailment(1000000, "The release contains one million observations.")
    assert ok, reason


def test_watermark_optin_cannot_retain_v7_instrument_identity():
    text = "Count `999`{pd: full:/total_files}"
    declared = {"Dataset": {"total_files"}, "CoreDataset": {"total_files"}}
    baseline = reports.check_report(text, {"total_files": 2}, {}, declared, instrument_version=7)
    enabled = reports.check_report(text, {"total_files": 2}, {}, declared, instrument_version=7, check_watermarks=True)
    assert enabled["instrument"] != baseline["instrument"]


def test_malformed_watermark_is_not_silently_absent():
    result = pd.verify_watermarks("Count `999`{pd: full:/total_files", full={"total_files": 2})
    assert result["findings"]


def test_pointer_empty_key_is_not_silently_discarded():
    result = pd.verify_watermarks("Value `2`{pd: full:/a//b}", full={"a": {"b": 2, "": {"b": 3}}})
    assert result["verified"] == 0


def test_default_claim_receipt_preserves_historical_output_shape():
    p = {"slot": "description", "snippet": TEXT, "origin": "rereceipt"}
    claims = rc.claim_receipts(receipt(p))
    assert claims["slots"]["description"]["receipts"] == [{"chunk": "c001", "snippet": TEXT}]


@pytest.mark.parametrize("selection", ["env", "document"])
def test_declared_v5_optin_reaches_real_block_for(tmp_path, monkeypatch, selection):
    from data_sheets_schema.chunking import build_manifest, dump_manifest
    bundle = tmp_path / "P_preprocessed.txt"
    bundle.write_text(TEXT)
    manifest = build_manifest(bundle)
    cid = manifest["chunks"][0]["id"]
    rp = {"bundle_md5": MD5, "chunks": [{"id": cid, "status": "extracted", "extracted": [{"slot": "description", "snippet": TEXT}]}]}
    if selection == "env":
        monkeypatch.setenv("RECEIPTS_V5_INSTRUMENT", "1")
    else:
        monkeypatch.delenv("RECEIPTS_V5_INSTRUMENT", raising=False)
        rp["receipt_format_version"] = 5
    manifest_path = tmp_path / "P_chunks.yaml"
    manifest_path.write_text(dump_manifest(manifest))
    full = tmp_path / "P_d4d.yaml"
    full.write_text(yaml.safe_dump({"description": TEXT}))
    receipt_path = tmp_path / "P_coverage_receipt.yaml"
    receipt_path.write_text(yaml.safe_dump(rp))
    block = rc.block_for(full, receipt_path, bundle, MD5, expected=True, manifest=manifest_path)
    assert block["checked"]
    assert block["instrument"] == rc.RECEIPTS_V5_INSTRUMENT


def test_tool_only_v5_receipt_is_not_vacuous():
    from data_sheets_schema.canary import receipt_floors
    p = pair("manifest_chunk_count", 1)
    block = rc.check(receipt(p), MANIFEST, TEXTS, {"total_files": 1}, MD5, instrument_version=5)
    assert block["tool_receipts"]["verified"] == 1
    assert block["slots"]["with_receipt"] == 1
    assert receipt_floors(block)["receipts vacuous"] == 0


def test_transformation_receipt_rejects_forged_counts():
    from data_sheets_schema import transformation_receipts as tr
    from data_sheets_schema.derive_core import derive_core
    full = {"id": "example:dataset", "title": "Example", "description": TEXT}
    core = derive_core(full)
    emitted = tr.emit_transformation_receipt(full, core)
    assert tr.verify_transformation_receipt(emitted, full, core)["verified"]
    emitted["counts"]["identity_copied"] = 999999
    assert not tr.verify_transformation_receipt(emitted, full, core)["verified"]


def test_declarative_mapping_does_not_silently_ignore_changed_expression(tmp_path):
    from data_sheets_schema import transformation_receipts as tr
    document = yaml.safe_load(tr.DEFAULT_MAPPING_PATH.read_text())
    document["class_derivations"]["CoreDataset"]["slot_derivations"]["dialect"]["expr"] = "'changed-dialect'"
    path = tmp_path / "changed-map.yaml"
    path.write_text(yaml.safe_dump(document))
    spec, _, _ = tr.load_transformation_spec(path)
    # Either implement the declared expression, or explicitly reject unsupported
    # mapping semantics. A valid mapping must not silently execute another rule.
    validation = tr.validate_spec_against_pair_schema(spec)
    if not validation["valid"]:
        return
    result = tr.derive_core_declarative({"id": "example:dataset"}, spec_path=path)
    assert result.get("dialect") == "changed-dialect"


def test_origin_identity_distinguishes_changed_tool_payload():
    from data_sheets_schema import receipt_origin
    first = receipt(pair("record_count", 2, args={"path": "items"}))
    second = receipt(pair("record_count", 900, args={"path": "other_items"}))
    before = receipt_origin.triples(yaml.safe_dump(first))
    after = receipt_origin.triples(yaml.safe_dump(second))
    assert before != after
