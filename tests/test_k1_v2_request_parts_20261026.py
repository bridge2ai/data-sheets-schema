"""Causal accounting checks for K1 v2/#5155/#5157 (2026-10-26)."""
import copy
import pytest
from scripts.adhoc import k1_v2_request_parts_20261026 as parts


def request(text):
    return {"system": "rules", "max_tokens": 32000,
            "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}]}


def test_nested_multibyte_values_partition_without_double_counting():
    shared = parts.canonical({"bundle": "é\n\\\"", "original_full": "record", "schema": {"x": "slot"}}).decode()
    text = parts.TYPED_HEADER + parts.canonical({"payload": {"shared_context": shared,
        "workers": {"w": "answer"}, "omission_response": "omitted", "stage": "integration"}}).decode()
    original = request(text); saved = copy.deepcopy(original)
    result = parts.summarize_payload(original)
    assert original == saved
    assert sum(result["component_bytes"].values()) == len(parts.canonical(original))
    for key in ("bundle", "records", "schema_context", "worker_outputs", "audit_carry"):
        assert result["component_bytes"][key] > 0
    assert result["component_bytes"]["residual_structure"] > 0


def test_changing_one_leaf_changes_only_its_component():
    a = request(parts.TYPED_HEADER + parts.canonical({"payload": {"bundle": "short", "schema": "same"}}).decode())
    b = copy.deepcopy(a); b["messages"][0]["content"][0]["text"] = b["messages"][0]["content"][0]["text"].replace("short", "longer bundle")
    one, two = [parts.summarize_payload(p)["component_bytes"] for p in (a, b)]
    assert one["bundle"] != two["bundle"]
    assert {k: v for k, v in one.items() if k != "bundle"} == {k: v for k, v in two.items() if k != "bundle"}


def test_parent_is_not_added_again_and_rejected_report_has_own_component():
    p = request("# Reconciliation report as written\n\nreport")
    r = parts.summarize_payload(p)
    assert r["component_bytes"]["rejected_report"] > 0
    assert r["component_bytes"]["audit_carry"] == 0


def test_current_prefix_stops_before_worker_specific_schema():
    a = request("policy")
    a["messages"][0]["content"] += [{"type": "text", "text": "schema-A"}, {"type": "text", "text": "same bundle"}]
    b = copy.deepcopy(a); b["messages"][0]["content"][1]["text"] = "schema-B"
    assert parts.common_worker_prefix([a, b])["common_blocks"] == 1
    assert parts.common_worker_prefix([])["status"] == "unknown"
    b["messages"][0]["role"] = "assistant"
    with pytest.raises(ValueError, match="plain user"):
        parts.common_worker_prefix([a, b])


def test_receipt_yaml_source_inventory_and_assistant_are_not_instructions():
    p = request(parts.canonical({"record_yaml": "record", "receipt_yaml": "receipt"}).decode())
    p["messages"][0]["content"].append({"type": "text", "text": "# Required source-review inventory\n\nvalues"})
    p["messages"].append({"role": "assistant", "content": "full and receipt response"})
    result = parts.summarize_payload(p)["component_bytes"]
    assert all(result[key] > 0 for key in ("records", "receipt_evidence", "source_review_inventory", "transcript"))
    assert result["instructions"] == len("rules")


def test_production_nested_newline_preserved_but_pretty_json_refused():
    shared = parts.canonical({"bundle": "data", "receipt": "evidence"}).decode() + "\n"
    stage = parts.canonical({"assignment": {"path": "id"}}).decode() + "\n"
    p = request(parts.TYPED_HEADER + parts.canonical({"payload": {
        "shared_context": shared, "stage": stage}}).decode())
    result = parts.summarize_payload(p)
    assert result["component_bytes"]["bundle"] > 0
    assert result["component_bytes"]["receipt_evidence"] > 0
    assert sum(result["component_bytes"].values()) == len(parts.canonical(p))
    malformed = request(parts.TYPED_HEADER + parts.canonical({"payload": {
        "shared_context": '{ "bundle": "data" }\n'}}).decode())
    with pytest.raises(ValueError, match="not canonical"):
        parts.summarize_payload(malformed)
