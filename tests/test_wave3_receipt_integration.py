"""Wave3 #5225 canary/origin integration boundaries; synthetic inputs only."""
import json

import pytest
import yaml

from data_sheets_schema import receipt_origin as ro, receipts as rc
from data_sheets_schema.canary import receipt_floors
from tests.test_receipt_origin import Run


def document(tool=None, snippet=None):
    pair = {"slot": "total_files"}
    if tool is not None:
        pair["tool"] = tool
    if snippet is not None:
        pair["snippet"] = snippet
    return yaml.safe_dump({"chunks": [{"id": "c001", "status": "extracted", "extracted": [pair]}]})


@pytest.mark.parametrize("version", [3, 4, 5])
def test_tool_vacuity_is_versioned(version):
    block = {"instrument": rc.receipt_instrument(version), "chunks": {"total": 1, "reviewed": 1},
             "snippets": {"verified": 0}, "tool_receipts": {"verified": 1}}
    assert receipt_floors(block)["receipts vacuous"] == (0 if version == 5 else 1)


def test_tool_only_receipt_marker_cannot_activate_v5_disk_check(tmp_path, monkeypatch):
    from data_sheets_schema.chunking import build_manifest, dump_manifest
    monkeypatch.delenv("RECEIPTS_V5_INSTRUMENT", raising=False)
    bundle = tmp_path / "P_preprocessed.txt"
    bundle.write_text("Archive release source text.\n", encoding="utf-8")
    manifest = build_manifest(bundle)
    count = len(manifest["chunks"])
    rec = {"receipt_format_version": 5, "bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": chunk["id"], "status": "extracted", "extracted": [{"slot": "total_files",
         "tool": {"name": "manifest_chunk_count", "result": count}}]}
        for chunk in manifest["chunks"]]}
    manifest_path = tmp_path / "P_chunks.yaml"
    manifest_path.write_text(dump_manifest(manifest))
    full = tmp_path / "P_d4d.yaml"
    full.write_text(yaml.safe_dump({"total_files": count}))
    receipt = tmp_path / "P_coverage_receipt.yaml"
    receipt.write_text(yaml.safe_dump(rec))
    block = rc.block_for(full, receipt, bundle, manifest["bundle_md5"], expected=True, manifest=manifest_path)
    assert block["checked"]
    assert block["instrument"] == rc.RECEIPTS_INSTRUMENT
    assert "tool_receipts" not in block
    assert block["snippets"]["verified"] == 0
    assert block["slots"]["with_receipt"] == 1
    assert receipt_floors(block)["receipts vacuous"] == 1
    assert any(f["kind"] == "receipt_format_version_mismatch" for f in block["findings"])


def test_legacy_origin_key_and_digest_stay_identical():
    import hashlib
    rows = ro.triples(document(snippet="quoted source"))
    assert rows == [("c001", "quoted source", "total_files")]
    assert ro._digest(rows[0][1]) == hashlib.sha256(b"quoted source").hexdigest()


def test_tool_origin_key_order_is_irrelevant_and_cannot_be_impersonated_by_snippet():
    tool = {"name": "record_count", "args": {"path": "items"}, "result": 2}
    rows = ro.triples(document(tool))
    reverse = dict(reversed(list(tool.items())))
    assert rows == ro.triples(document(reverse))
    snippet = json.dumps(rows[0][1], ensure_ascii=True, separators=(",", ":"))
    assert rows != ro.triples(document(snippet=snippet))
    assert ro._digest(rows[0][1]) != ro._digest(snippet)


@pytest.mark.parametrize("field,value", [("name", "record_sum"), ("args", {"path": "other"}),
                                        ("result", 3), ("target", "snippet")])
def test_changed_tool_payload_is_post_draft(field, value):
    tool = {"name": "record_count", "args": {"path": "items"}, "result": 2}
    before = ro.triples(document(tool))
    after = ro.triples(document({**tool, field: value}))
    report = ro.classify(before, before, after)
    assert report["origin"]["contemporaneous"] == 0
    assert report["origin"]["phase3_backport"] == 1
    assert report["removed_contemporaneous"] == 1


def test_tool_and_snippet_are_both_bound():
    tool = {"name": "md5", "target": "snippet", "result": "x"}
    assert ro.triples(document(tool, "one")) != ro.triples(document(tool, "two"))


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_tool_origin_is_unknown(value):
    assert ro.triples(document({"name": "record_count", "result": value})) is None


def test_tool_origin_report_has_distinct_identity(tmp_path):
    run = Run(tmp_path)
    before = document({"name": "record_count", "args": {"path": "items"}, "result": 2})
    after = document({"name": "record_count", "args": {"path": "other"}, "result": 2})
    run.write(run.receipt, before)
    run.write(run.full, "total_files: 2\n")
    run.derive()
    run.write(run.receipt, after)
    block = run.report()
    assert block["status"] == "checked", block["reasons"]
    assert block["instrument"] == ro.TOOL_INSTRUMENT
    assert block["origin"]["phase3_backport"] == 1
