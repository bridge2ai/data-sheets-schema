"""K1 v2 accounting tests: input/output separation and encoded shared bytes."""
import copy
import json
from types import SimpleNamespace

import pytest

from scripts.adhoc import k1_v2_a17_sizing_20261026 as sizing


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def test_aggregate_counts_inputs_once_and_excludes_each_output_reservation():
    rows = [
        {"estimated_input_tokens": 140, "estimated_in_flight_range": [240, 280],
         "max_output_tokens": 120, "placeholder_tokens": 40, "payload_bytes": 200},
        {"estimated_input_tokens": 380, "estimated_in_flight_range": [390, 450],
         "max_output_tokens": 40, "placeholder_tokens": 80, "payload_bytes": 600},
    ]
    result = sizing.aggregate(rows)
    assert result["a1_estimated_input_tokens"] == 520
    assert result["a1_estimated_input_range"] == [470, 570]
    assert result["placeholder_tokens"] == 120
    assert result["call_count"] == 2


def test_shared_context_contribution_retains_nested_json_escaping_and_input():
    shared = canonical({"bundle": 'A "quote"\nnext line', "original_full": "Ω"}).decode()
    inner = {"kind": "typed_audit_worker_request_v1", "payload": {
        "shared_context": shared, "stage": "worker-specific", "worker_id": "worker_0001"}}
    payload = {"max_tokens": 64000, "messages": [{"role": "user", "content": [
        {"type": "text", "text": "# Exact typed stage request\n\n" + canonical(inner).decode()}]}]}
    before = copy.deepcopy(payload)
    modules = SimpleNamespace(sg=SimpleNamespace(canonical=canonical), typed=SimpleNamespace(_json=canonical))
    result = sizing.worker_shared(modules, payload, inner)
    assert result["shared_context_sha256"] == sizing.digest(shared.encode())
    assert result["shared_context_outer_payload_byte_contribution"] > result["shared_context_utf8_bytes"]
    assert payload == before
    with pytest.raises(AssertionError, match="differs"):
        sizing.worker_shared(modules, payload, {**inner, "kind": "foreign"})


def test_worker_inventory_metadata_must_match_exact_assigned_rows():
    row = {"path": "/creators/0/name", "text": "Ada"}
    batch = SimpleNamespace(canonical_bytes=lambda value: canonical(value) + b"\n")
    plan = {"sha256": "0" * 64, "limits": sizing.A17_LIMITS,
            "inventory": {"values": [row]}, "workers": [
                {"id": "worker_0001", "roots": ["/creators/0"], "paths": [row["path"]],
                 "inventory_bytes": len(batch.canonical_bytes([row]))}]}
    result = sizing.plan_summary(batch, plan)
    assert result["worker_count"] == 1
    assert result["largest_worker_inventory_bytes"] == len(batch.canonical_bytes([row]))
    plan["workers"][0]["inventory_bytes"] += 1
    with pytest.raises(AssertionError, match="exact assigned rows"):
        sizing.plan_summary(batch, plan)
