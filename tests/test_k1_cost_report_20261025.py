"""K1 cost arithmetic regressions; synthetic offline evidence, 2026-10-25."""
import copy

import pytest

from scripts.adhoc import k1_build_cost_report_20261025 as cost


def test_cached_context_counts_once_and_output_is_not_thinking_plus_output():
    row = {"phase": "full", "payload_bytes": 1000, "estimated_input_tokens": 400,
           "max_output_tokens": 100, "placeholder_tokens": 0}
    stats = {"fit_tokens_per_byte": .4, "input_cost_per_total_token": .5e-6,
             "completed_output_cap_fraction_mean": .5}
    value = cost.calibrated_stage(row, {"full": stats}, {"full": 1})
    assert value["expected_cache_aware_usd"] == pytest.approx(400 * .5e-6 + 50 * 25e-6)
    assert value["uncached_at_cap_usd"] == pytest.approx(.0045)
    assert value["all_cache_write_at_cap_usd"] > value["uncached_at_cap_usd"]


def test_cap_carry_stays_in_context_even_when_expected_transfer_is_smaller():
    row = {"phase": "report", "payload_bytes": 1_000_000, "estimated_input_tokens": 900_001,
           "max_output_tokens": 128_000, "placeholder_tokens": 500_001}
    stats = {"fit_tokens_per_byte": None, "input_cost_per_total_token": 5e-6,
             "completed_output_cap_fraction_mean": .5}
    value = cost.calibrated_stage(row, {"report": stats}, {"report": .1})
    assert value["expected_input_tokens"] == 400_000
    assert value["expected_input_fixed_component_floor_applied"] is True
    assert value["context_fit_1m_estimate"] is False
    assert value["report_margin_850k_estimate"] is False


def test_exact_byte_calibration_does_not_fit_away_new_fixed_prompt_text():
    stats = {"fit_tokens_per_byte": .4, "input_cost_per_total_token": 5e-6,
             "completed_output_cap_fraction_mean": .5}
    before = {"phase": "full", "payload_bytes": 1000, "estimated_input_tokens": 400,
              "max_output_tokens": 100}
    after = {**before, "payload_bytes": 2000, "estimated_input_tokens": 800}
    first = cost.calibrated_stage(before, {"full": stats}, {"full": 1})
    second = cost.calibrated_stage(after, {"full": stats}, {"full": .5})
    assert second["expected_input_tokens"] == 2 * first["expected_input_tokens"]


def test_unknown_repair_expectation_is_not_reported_as_zero():
    row = {"phase": "repair_full", "payload_bytes": 1000, "estimated_input_tokens": 400,
           "max_output_tokens": 96000}
    value = cost.calibrated_stage(row, {}, {})
    assert value["expected_cache_aware_usd"] is None
    assert value["uncached_at_cap_usd"] > 0


def test_incomplete_sweep_cannot_be_totalled():
    with pytest.raises(ValueError, match="unfinished sizing"):
        cost.calculate({"complete": False}, {})


def test_scenario_calibration_holdout_uses_other_canary():
    sizing = {"rows": [
        {"project": "CHORUS", "label": date + "_rep1", "measurements": {
            "stages": {"full": {"estimated_input_tokens": estimated}}}}
        for date, estimated in (("2026-10-20a", 100), ("2026-10-22a", 100))]}
    ledger = {"settled_rows": [
        {"date": date, "phase": "full", "stop_reason": "end_turn", "total_input_tokens": actual}
        for date, actual in (("2026-10-20a", 50), ("2026-10-22a", 100))]}
    rows = cost.scenario_calibration(sizing, ledger)["rows"]
    assert rows[0]["held_out_error_percent"] == 100
    assert rows[1]["held_out_error_percent"] == -50


def test_ambiguous_same_phase_joins_refuse():
    sizing = {"rows": [{"project": "CHORUS", "label": "2026-10-20a_rep1", "measurements": {
        "stages": {"full": {"estimated_input_tokens": 100}}}}]}
    row = {"date": "2026-10-20a", "phase": "full", "stop_reason": "end_turn", "total_input_tokens": 100}
    with pytest.raises(ValueError, match="ambiguous calibration roster"):
        cost.scenario_calibration(sizing, {"settled_rows": [row, row]})


def synthetic_case():
    phase_rows = {phase: {"payload_bytes": 1000, "estimated_input_tokens": 400,
                          "max_output_tokens": 100}
                  for phase in cost.BASE_PHASES if phase != "typed_audit_worker"}
    worker = {"worker_id": "worker1", "payload_bytes": 1000,
              "estimated_input_tokens": 400, "max_output_tokens": 100}
    measured = {"stages": phase_rows, "typed": {"workers": [worker]},
                "audit_limits": {"aggregate_input_tokens": 1000}}
    rows = [{"project": "CHORUS", "label": date + "_rep1", "measurements": measured,
             "selected_limits": {}, "planning": {}, "staged_record_conformance_edits": []}
            for date in ("2026-10-20a", "2026-10-22a")]
    observations = [{"date": date, "phase": phase, "stop_reason": "end_turn",
                     "total_input_tokens": 400, "cost_usd": .0045}
                    for date in ("2026-10-20a", "2026-10-22a") for phase in cost.BASE_PHASES]
    ledger = {"settled_rows": observations, "abandoned_rows": [], "runs": [{}, {}],
              "stage_calibration": {phase: {"fit_tokens_per_byte": .4,
                  "input_cost_per_total_token": 5e-6,
                  "completed_output_cap_fraction_mean": .5} for phase in cost.BASE_PHASES}}
    return {"complete": True, "rows": rows}, ledger


def test_missing_optional_scenarios_cannot_masquerade_as_retry_envelope():
    sizing, ledger = synthetic_case()
    model = cost.calculate(sizing, ledger)
    result = model["results"][0]
    assert result["complete_stage_roster"] is True
    assert result["expected_cache_aware_usd"] > 0
    assert result["conditional_controller_retry_repair_envelope_usd"] is None
    assert "report_regate" in result["retry_repair_envelope_missing_phases"]
    assert result["typed_aggregate_fits_cap_scenario"] is False
    assert all(row["context_fit_1m_estimate"] for row in result["stages"])


def test_legacy_kids_proxy_never_fills_actual_or_unrelated_unknowns():
    sizing, ledger = synthetic_case()
    prototype = sizing["rows"][0]
    for project in ("AI_READI", "CM4AI", "VOICE", "VOICE_PEDIATRIC", "KIDS_FIRST"):
        row = copy.deepcopy(prototype)
        row["project"] = project
        sizing["rows"].append(row)
    kids = sizing["rows"][-1]
    proxy = {**copy.deepcopy(kids), "arm": "baseline_draft_context_proxy"}
    sizing["rows"].append(proxy)
    sizing["rows"].append({**copy.deepcopy(prototype), "arm": "with_crate"})
    kids["measurements"]["typed"] = {"status": "REFUSED", "reason": "proxy mismatch"}
    for phase in ("typed_audit_omission", "typed_audit_integration"):
        del kids["measurements"]["stages"][phase]
    model = cost.calculate(sizing, ledger)
    actual = next(r for r in model["results"] if r["project"] == "KIDS_FIRST" and r["arm"] == "baseline")
    assert actual["expected_cache_aware_usd"] is None
    assert actual["typed_aggregate_expected_input"] is None
    assert model["matrix_totals"]["expected_cache_aware_usd"] is None
    assert model["d04b_totals"]["expected_cache_aware_usd"] is None
    assert model["known_matrix_subtotal"]["expected_cache_aware_usd"] > 0
    assert model["draft_context_proxy_matrix_totals"]["expected_cache_aware_usd"] > model["known_matrix_subtotal"]["expected_cache_aware_usd"]
    voice = next(r for r in sizing["rows"] if r["project"] == "VOICE")
    del voice["measurements"]["stages"]["full"]
    model = cost.calculate(sizing, ledger)
    assert model["draft_context_proxy_matrix_totals"]["expected_cache_aware_usd"] is None
