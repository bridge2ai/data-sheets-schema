"""R_V5 F1/F2/F3/F4/F6/F8 boundaries for #5224/#5225/#5227, 2026-10-27.

Inputs are synthetic source/record fixtures; output is offline pytest evidence.
No historical generation or evaluation instrument is activated by these tests.
"""
import copy
import hashlib

import pytest

from data_sheets_schema import receipts as rc


TEXT = "The archive contains 2 MB of observations.\nAlpha beta alpha.\n"
MD5 = hashlib.md5(TEXT.encode()).hexdigest()
MANIFEST = {"bundle_md5": MD5, "chunks": [{"id": "c001", "bytes": len(TEXT.encode())}]}
TEXTS = {"c001": TEXT}


def document(pair):
    return {"bundle_md5": MD5, "chunks": [{"id": "c001", "status": "extracted", "extracted": [pair]}]}


def tool(name, result, *, slot="total_files", **args):
    return {"slot": slot, "tool": {"name": name, "result": result, "args": args}}


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan"), True])
def test_nonfinite_or_boolean_conversion_is_refused(value):
    pair = tool("unit_convert", 2000000, value=value, from_unit="mb", to_unit="b")
    assert not rc.verify_tool_receipt(pair, "c001", TEXTS, MANIFEST, {"total_files": 2000000})[0]


def test_negative_source_cannot_support_positive_conversion():
    pair = tool("unit_convert", 2000000, value=2, from_unit="mb", to_unit="b")
    assert not rc.verify_tool_receipt(pair, "c001", {"c001": "The adjustment is -2 MB."}, MANIFEST,
                                      {"total_files": 2000000})[0]


@pytest.mark.parametrize("target_location", ["tool", "args"])
def test_snippet_hash_uses_exact_bound_bytes(target_location):
    snippet = "Alpha beta alpha."
    digest = hashlib.md5(snippet.encode()).hexdigest()
    pair = tool("md5", digest, slot="md5")
    pair["snippet"] = snippet
    pair["tool"]["target"] = "snippet"
    if target_location == "args":
        pair["tool"].pop("target")
        pair["tool"]["args"]["target"] = "snippet"
    assert rc.verify_tool_receipt(pair, "c001", TEXTS, MANIFEST, {"md5": digest})[0]
    pair["snippet"] = "Unobserved invented snippet."
    pair["tool"]["result"] = hashlib.md5(pair["snippet"].encode()).hexdigest()
    assert not rc.verify_tool_receipt(pair, "c001", TEXTS, MANIFEST,
                                      {"md5": pair["tool"]["result"]})[0]


def test_conflicting_targets_are_refused():
    pair = tool("md5", MD5, slot="md5", target="chunk")
    pair["tool"]["target"] = "snippet"
    pair["snippet"] = TEXT
    assert not rc.verify_tool_receipt(pair, "c001", TEXTS, MANIFEST, {"md5": MD5})[0]


@pytest.mark.parametrize("value", [True, "1 file", "1000", 2, 1.00000001])
def test_discrete_tool_scalar_match_is_exact(value):
    assert not rc.verify_tool_receipt(tool("manifest_chunk_count", 1), "c001", TEXTS, MANIFEST,
                                      {"total_files": value})[0]


def test_large_integer_record_sum_keeps_integer_precision():
    huge = 10 ** 400
    pair = tool("record_sum", huge + 1, path="items", field="bytes")
    full = {"items": [{"bytes": huge}, {"bytes": 1}], "total_files": huge + 1}
    assert rc.verify_tool_receipt(pair, "c001", TEXTS, MANIFEST, full)[0]
    full["total_files"] = huge
    assert not rc.verify_tool_receipt(pair, "c001", TEXTS, MANIFEST, full)[0]


@pytest.mark.parametrize("polarity", ["NEUTRAL", "REFUTE", "NO_EVIDENCE", "typo", None, []])
def test_nonaffirmative_polarity_never_covers_or_hides_completion_work(polarity):
    pair = {"slot": "description", "snippet": TEXT, "supports": polarity}
    full = {"description": TEXT}
    doc = document(pair)
    result = rc.check(doc, MANIFEST, TEXTS, full, MD5, instrument_version=5)
    assert result["slots"]["with_receipt"] == 0
    assert rc.uncovered_receiptable_leaves(doc, MANIFEST, TEXTS, full, instrument_version=5) == ["description"]
    if polarity == "NEUTRAL":
        assert result["by_polarity"]["NEUTRAL"] == 1


def test_d37_stays_original_but_changed_final_tool_value_loses_final_coverage():
    original = {"total_files": 2, "file_collections": [{"id": "example:a"}, {"id": "example:b"}]}
    final = copy.deepcopy(original)
    final["total_files"] = 3
    final["file_collections"].append({"id": "example:c"})
    doc = document(tool("record_count", 2, path="file_collections"))
    before = rc.check(doc, MANIFEST, TEXTS, original, MD5, original, instrument_version=5)
    after = rc.check(doc, MANIFEST, TEXTS, final, MD5, original, instrument_version=5)
    assert before["slots"]["with_receipt_at_receipt"] == after["slots"]["with_receipt_at_receipt"] == 1
    assert after["slots"]["with_receipt"] == 0
    assert any(f["kind"] == "tool_receipt_final_record_mismatch" for f in after["findings"])
    assert "total_files" in rc.uncovered_receiptable_leaves(doc, MANIFEST, TEXTS, final, original=original,
                                                            instrument_version=5)


def test_snapshot_tool_never_falls_through_to_new_final_path():
    pair = tool("record_count", 2, path="file_collections")
    final = {"total_files": 2, "file_collections": [1, 2]}
    assert not rc.verify_tool_receipt(pair, "c001", TEXTS, MANIFEST, final, {})[0]


def test_completion_polarity_change_is_not_deduplicated_as_old_neutral():
    pair = {"slot": "description", "snippet": TEXT, "supports": "NEUTRAL"}
    doc = document(pair)
    full = {"description": TEXT}
    result = rc.apply_rereceipt(doc, full,
                              [{"path": "description", "receipt": {"chunk": "c001", "snippet": TEXT,
                                                                      "supports": "SUPPORT"}}],
                              TEXTS, listed=["description"], manifest=MANIFEST, instrument_version=5)
    assert result["added"] == 1
    assert rc.uncovered_receiptable_leaves(result["receipt"], MANIFEST, TEXTS, full, instrument_version=5) == []


def test_rereceipt_snippet_hash_keeps_verified_source_binding():
    digest = hashlib.md5(TEXT.encode()).hexdigest()
    doc = {"bundle_md5": MD5, "chunks": [{"id": "c001", "status": "nothing_relevant", "reason": "pending"}]}
    answer = {"path": "md5", "receipt": {"chunk": "c001", "snippet": TEXT,
                                          "tool": {"name": "md5", "target": "snippet", "result": digest}}}
    result = rc.apply_rereceipt(doc, {"md5": digest}, [answer], TEXTS, listed=["md5"],
                               manifest=MANIFEST, instrument_version=5)
    assert result["added"] == 1
    assert rc.check(result["receipt"], MANIFEST, TEXTS, {"md5": digest}, MD5,
                    instrument_version=5)["tool_receipts"]["verified"] == 1


def test_sidecar_and_completion_explicit_v4_ignore_ambient_v5(monkeypatch):
    monkeypatch.setenv("RECEIPTS_V5_INSTRUMENT", "1")
    pair = {"slot": "description", "snippet": TEXT, "origin": "rereceipt", "supports": "NEUTRAL"}
    doc = document(pair)
    doc["receipt_format_version"] = 5
    assert rc.claim_receipts(doc, instrument_version=4)["slots"]["description"]["receipts"] == [
        {"chunk": "c001", "snippet": TEXT}]
    assert rc.claim_receipts(doc)["slots"]["description"]["receipts"] == [
        {"chunk": "c001", "snippet": TEXT}]
    assert rc.claim_receipts(doc, instrument_version=5)["slots"]["description"]["receipts"][0]["supports"] == "NEUTRAL"
    assert rc.uncovered_receiptable_leaves(doc, MANIFEST, TEXTS, {"description": TEXT}) == []


@pytest.mark.parametrize("value,snippet", [(1, "There were 1000 observations."),
                                           (100, "There were -100 observations."),
                                           (2026, "Released October 23, 2026."),
                                           (200, "300 participants at 200 sites.")])
def test_numeric_diagnostic_refuses_ambiguous_or_partial_number_matches(value, snippet):
    assert not rc.check_fast_entailment(value, snippet)[0]


def test_million_phrase_is_compound_and_can_end_sentence():
    assert rc.check_fast_entailment(1000000, "The sample contains one million.") == (True, "numeric_equivalence")
    assert not rc.check_fast_entailment(1, "The sample contains one million.")[0]


@pytest.mark.parametrize("value,words", [(0, "zero million"), (205, "two hundred and five"),
                                       (1234567, "one million two hundred and thirty-four thousand five hundred and sixty-seven")])
def test_number_word_grammar_preserves_complete_counts(value, words):
    assert rc.check_fast_entailment(value, f"The sample contains {words} observations.") == (True, "numeric_equivalence")


@pytest.mark.parametrize("value,words", [(1000000, "zero million"), (3, "one two"),
                                       (31, "twenty eleven"), (2000000, "one million million"),
                                       (1001000, "one thousand million"), (3, "one and two")])
def test_unsupported_number_word_phrases_do_not_invent_counts(value, words):
    assert not rc.check_fast_entailment(value, f"The sample contains {words} observations.")[0]


@pytest.mark.parametrize("origin", [None, "rereceipt"])
def test_completed_tool_receipt_keeps_snapshot_identity_after_final_reorder(origin):
    original = {"file_collections": [
        {"id": "example:a", "total_files": 2, "resources": ["x", "y"]},
        {"id": "example:b", "total_files": 1, "resources": ["z"]},
    ]}
    final = {"file_collections": list(reversed(copy.deepcopy(original["file_collections"])))}
    pair = tool("record_count", 2, slot="file_collections[0].total_files", path="file_collections[0].resources")
    if origin is not None:
        pair["origin"] = origin
    doc = document(pair)
    result = rc.check(doc, MANIFEST, TEXTS, final, MD5, original, instrument_version=5)
    assert result["tool_receipts"]["verified"] == 1
    assert result["tool_receipts"]["mismatched"] == 0
    assert result["slots"]["with_receipt_at_receipt"] == 1
    assert result["slots"]["with_receipt"] == 1
    assert not [f for f in result["findings"] if f["kind"].startswith("tool_receipt")]
    assert "file_collections[1].total_files" not in rc.uncovered_receiptable_leaves(
        doc, MANIFEST, TEXTS, final, original=original, instrument_version=5)


def test_final_path_join_does_not_repair_malformed_tool_args():
    full = {"total_files": 2, "file_collections": [{"id": "example:a"}, {"id": "example:b"}]}
    pair = {"slot": "total_files", "tool": {"name": "record_count", "result": 2,
                                            "path": "file_collections", "args": None}}
    doc = document(pair)
    block = rc.check(doc, MANIFEST, TEXTS, full, MD5, original=full, instrument_version=5)
    assert block["tool_receipts"]["verified"] == 0
    assert block["slots"]["with_receipt"] == 0
    assert block["slots"]["with_receipt_at_receipt"] == 0
    assert "total_files" in rc.uncovered_receiptable_leaves(
        doc, MANIFEST, TEXTS, full, original=full, instrument_version=5)
