"""K1 v2 causal accounting tests, 2026-10-26 (#5155/#5157)."""
import pytest
from scripts.adhoc.k1_v2_cost_report_20261026 import allocate_components, cache_scenario, reviewed_input, pin


def sample():
    row = {"payload_bytes": 100, "estimated_input_tokens": 150, "placeholder_tokens": 100,
           "expected_input_tokens": 100, "at_cap_input_estimate": 150, "max_output_tokens": 32}
    payload = {"parts": {"payload_bytes": 100, "component_bytes": {
        "bundle": 70, "audit_carry": 10, "rejected_report": 0, "worker_outputs": 0, "records": 20}},
        "placeholder_sources": {"assembled_audit": 80, "rejected_report": 20}}
    return row, payload


def test_expected_and_cap_conserve_tokens_without_double_carry():
    row, payload = sample()
    expected = allocate_components(row, payload, None, "expected_input_tokens")
    cap = allocate_components(row, payload, None, "at_cap_input_estimate")
    assert expected["token_allocations"]["rejected_report"] == 10
    assert cap["token_allocations"]["rejected_report"] == 20
    assert sum(cap["token_allocations"].values()) == 150
    assert sum(expected["token_allocations"].values()) == 100
    assert expected["context_total"] == 132


def test_selected_payload_and_carry_mismatch_refuse():
    row, payload = sample()
    payload["parts"]["payload_bytes"] += 1
    with pytest.raises(ValueError, match="component bytes"):
        allocate_components(row, payload, None, "expected_input_tokens")
    row, payload = sample()
    payload["placeholder_sources"]["rejected_report"] += 1
    with pytest.raises(ValueError, match="carry sources"):
        allocate_components(row, payload, None, "expected_input_tokens")


def test_cache_first_call_writes_and_only_prefix_is_discounted():
    workers = [{"expected_input_tokens": 1000}] * 3
    payloads = [{"shared_prefix": {"shared_context_outer_payload_byte_contribution": 100}}] * 3
    baseline = 12
    one = cache_scenario(workers[:1], payloads[:1], {}, baseline, 6.25e-6, 1, 1)
    three = cache_scenario(workers, payloads, {}, baseline, 6.25e-6, 1, 1)
    nohit = cache_scenario(workers, payloads, {}, baseline, 6.25e-6, 1, 0)
    assert one["expected_usd"] == baseline
    assert nohit["expected_usd"] == baseline
    assert three["expected_usd"] == pytest.approx(baseline - 2 * 100 * 5.75e-6)


def test_actual_floor_payload_is_not_counted_again_as_worker_cap():
    row, payload = sample()
    row.update(placeholder_tokens=20, estimated_input_tokens=70, at_cap_input_estimate=70)
    payload["placeholder_sources"] = {"omission_response": 20}
    payload["parts"]["component_bytes"]["worker_outputs"] = 40
    payload["parts"]["component_bytes"]["bundle"] -= 40
    result = allocate_components(row, payload, None, "at_cap_input_estimate")
    assert result["carry_allocation"] == 20
    assert result["token_allocations"]["worker_outputs"] == 20


def test_changed_audit_cannot_reuse_reviewed_narrative(tmp_path):
    path = tmp_path / "audit.json"
    path.write_text('{"timing_hits": 1}')
    expected = pin(path)["sha256"]
    assert reviewed_input(path, expected)["sha256"] == expected
    path.write_text('{"timing_hits": 4}')
    with pytest.raises(ValueError, match="narrative authority changed"):
        reviewed_input(path, expected)
