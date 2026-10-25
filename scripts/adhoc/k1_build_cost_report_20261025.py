#!/usr/bin/env python3
"""K1 cost/size synthesis, 2026-10-25 (#5112/#5150/#5155/#5157).

Inputs: saved K1 request-sizing JSON and archived-ledger calibration JSON.
Outputs: reproducible cost-model JSON and Markdown; no provider or network I/O.
Expected costs are two-CHORUS transfer scenarios, not statistical guarantees.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics

RATES = {"input_tokens": 5e-6, "output_tokens": 25e-6,
         "cache_write": 6.25e-6, "cache_read": .5e-6}
BASE_PHASES = ("full", "full_receipt_completion", "typed_audit_worker",
               "typed_audit_omission", "typed_audit_integration", "reconcile_full", "report")
MATRIX = (("Re-canary", "CHORUS", 1), ("AI_READI pilot", "AI_READI", 1),
          ("CHORUS production", "CHORUS", 3), ("CM4AI production", "CM4AI", 3),
          ("VOICE production", "VOICE", 3), ("AI_READI production", "AI_READI", 3),
          ("VOICE_PEDIATRIC", "VOICE_PEDIATRIC", 1), ("KIDS_FIRST", "KIDS_FIRST", 1))


def pin(path):
    raw = Path(path).read_bytes()
    return {"path": str(Path(path).resolve()), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def stage_rows(scenario):
    measured = scenario["measurements"]
    rows = [{"phase": "typed_audit_worker", "id": w["worker_id"], **w}
            for w in measured.get("typed", {}).get("workers", [])]
    rows.extend({"phase": phase, "id": phase, **value}
                for phase, value in measured.get("stages", {}).items()
                if phase != "report_regate_with_v8_report")
    return rows


def scenario_calibration(sizing, ledger):
    """Same-record target-builder estimates versus historical observed inputs.

    These are scenario transfer factors, not exact historical byte calibration.
    Cross-canary errors exclude fitting on the canary being predicted.
    """
    joined = []
    for run in sizing["rows"]:
        if run["project"] != "CHORUS" or run.get("arm", "baseline") != "baseline":
            continue
        date = run["label"].split("_", 1)[0]
        observed = [r for r in ledger["settled_rows"] if r["date"] == date
                    and r["stop_reason"] == "end_turn"]
        by_phase = defaultdict(list)
        for row in stage_rows(run):
            by_phase[row["phase"]].append(row)
        for phase, estimated in by_phase.items():
            actual = [r for r in observed if r["phase"] == phase]
            if not actual:
                continue
            if len(actual) != len(estimated):
                raise ValueError(f"ambiguous calibration roster: {date}/{phase}")
            predicted = sum(r["estimated_input_tokens"] for r in estimated)
            total = sum(r["total_input_tokens"] for r in actual)
            joined.append({"date": date, "phase": phase, "scenario_input_tokens": predicted,
                           "observed_input_tokens": total, "factor": total / predicted,
                           "raw_scenario_error_percent": 100 * (predicted / total - 1)})
    factors = {}
    for phase in {r["phase"] for r in joined}:
        group = [r for r in joined if r["phase"] == phase]
        factors[phase] = statistics.mean(r["factor"] for r in group)
        for row in group:
            others = [r for r in group if r["date"] != row["date"]]
            row["held_out_error_percent"] = (100 * (row["scenario_input_tokens"] *
                statistics.mean(r["factor"] for r in others) / row["observed_input_tokens"] - 1)
                if others else None)
    return {"factors": factors, "rows": joined,
            "basis": "Target A16 builders on each historical canary record; cap carries scaled to observed total input. This is scenario calibration, not identical historical requests."}


def calibrated_stage(row, calibration, factors):
    phase = row["phase"]
    family = {"report_after_repair": "report", "full_receipt_completion_after_readdress":
              "full_receipt_completion"}.get(phase, phase)
    stats = calibration.get(family)
    scenario_inputs = row["estimated_input_tokens"]
    cap = row["max_output_tokens"]
    input_floor_applied = False
    if stats is None:
        # Optional readdress/repair are unobserved in these two canaries.
        expected_inputs = expected_output = expected_cost = None
        input_basis = "unobserved optional stage"
    else:
        factor = factors.get(family)
        if factor is None:
            raise ValueError(f"missing scenario calibration for observed phase {family}")
        if stats["fit_tokens_per_byte"] is not None and not row.get("placeholder_tokens", 0):
            expected_inputs = row["payload_bytes"] * stats["fit_tokens_per_byte"]
            input_basis = "historical exact/reconstructed payload token-per-byte fit applied to current bytes"
        else:
            expected_inputs = scenario_inputs * factor
            fixed_inputs = (row["payload_bytes"] * stats["fit_tokens_per_byte"]
                            if stats["fit_tokens_per_byte"] is not None else
                            scenario_inputs - row.get("placeholder_tokens", 0))
            input_floor_applied = expected_inputs < fixed_inputs
            expected_inputs = max(expected_inputs, fixed_inputs)
            input_basis = "historical-record cap-carry scenario transfer; cannot isolate new fixed-prompt cost"
        expected_output = cap * stats["completed_output_cap_fraction_mean"]
        expected_cost = expected_inputs * stats["input_cost_per_total_token"] + expected_output * RATES["output_tokens"]
    # Preserve A1's conservative scenario alongside a calibrated byte scenario;
    # no cap-carry shrink is used in this at-cap exposure calculation.
    fit = stats["fit_tokens_per_byte"] if stats else None
    byte_calibrated = row["payload_bytes"] * fit + row.get("placeholder_tokens", 0) if fit else scenario_inputs
    envelope_inputs = max(scenario_inputs, byte_calibrated)
    return {**row, "expected_input_tokens": expected_inputs,
            "expected_input_basis": input_basis,
            "expected_input_fixed_component_floor_applied": input_floor_applied,
            "expected_output_tokens": expected_output, "expected_cache_aware_usd": expected_cost,
            "at_cap_input_estimate": envelope_inputs,
            "uncached_at_cap_usd": envelope_inputs * RATES["input_tokens"] + cap * RATES["output_tokens"],
            "all_cache_write_at_cap_usd": envelope_inputs * RATES["cache_write"] + cap * RATES["output_tokens"],
            "context_total_at_cap_estimate": envelope_inputs + cap,
            "context_fit_1m_estimate": envelope_inputs + cap <= 1_000_000,
            "report_margin_850k_estimate": envelope_inputs + cap <= 850_000 if family in ("report", "report_regate") else None}


def calculate(sizing, ledger):
    if not sizing.get("complete"):
        raise ValueError("refuse unfinished sizing evidence")
    calibration = scenario_calibration(sizing, ledger)
    if len({r["date"] for r in calibration["rows"]}) != 2:
        raise ValueError("both canaries are required for scenario calibration")
    stages = ledger["stage_calibration"]
    regate_frequency = len({r["date"] for r in ledger["settled_rows"] if r["phase"] == "report_regate"}) / len(ledger["runs"])
    # Only ordinary abandoned streams belong in the ordinary retry tail. A
    # manually resumed typed stage and an old low-cap truncation stay separate.
    ordinary = {"full", "reconcile_full", "report", "report_regate"}
    ordinary_partial = sum(r["cost_usd_observed_lower_bound"] for r in ledger["abandoned_rows"] if r["phase"] in ordinary)
    ordinary_settled = sum(r["cost_usd"] for r in ledger["settled_rows"] if r["phase"] in ordinary)
    partial_fraction = ordinary_partial / ordinary_settled
    results = []
    for scenario in sizing["rows"]:
        rows = [calibrated_stage(row, stages, calibration["factors"]) for row in stage_rows(scenario)]
        phases = {r["phase"] for r in rows}
        complete = set(BASE_PHASES) <= phases and (not regate_frequency or "report_regate" in phases)
        base = [r for r in rows if r["phase"] in BASE_PHASES]
        optional = {r["phase"]: r for r in rows if r["phase"] not in BASE_PHASES}
        expected = sum(r["expected_cache_aware_usd"] for r in base) if complete else None
        regate = optional.get("report_regate")
        if expected is not None and regate:
            expected += regate_frequency * regate["expected_cache_aware_usd"]
        ordinary_expected = sum(r["expected_cache_aware_usd"] for r in base if r["phase"] in ordinary)
        if regate:
            ordinary_expected += regate_frequency * regate["expected_cache_aware_usd"]
        tail = ordinary_expected * partial_fraction if complete else None
        # Conditional controller-call envelope. This is deliberately separate
        # from both the one-pass column and observed partial retry usage.
        multiplicities = {"full": 25, "full_receipt_completion": 1, "typed_audit_worker": 1,
                          "typed_audit_omission": 1, "typed_audit_integration": 1,
                          "reconcile_full": 25, "report": 5, "report_regate": 5,
                          "full_readdress": 25, "repair_full": 20, "report_after_repair": 5}
        stress_complete = set(multiplicities) <= phases
        stress = sum(r["uncached_at_cap_usd"] * multiplicities.get(r["phase"], 0) for r in rows)
        typed = [r for r in rows if r["phase"].startswith("typed_audit_")]
        typed_complete = {"typed_audit_worker", "typed_audit_omission", "typed_audit_integration"} <= phases
        aggregate = scenario["measurements"].get("audit_limits", {}).get("aggregate_input_tokens")
        results.append({"project": scenario["project"], "arm": scenario.get("arm", "baseline"),
            "label": scenario["label"], "proxy": scenario.get("record_proxy_for"),
            "scenario_qualifiers": {key: scenario[key] for key in
                ("proxy_basis", "receipt_basis", "future_output_basis", "context_basis", "conditional_decision")
                if key in scenario},
            "selected_limits": scenario["selected_limits"], "planning": scenario["planning"],
            "staged_record_conformance_edits": scenario["staged_record_conformance_edits"],
            "measured_status": scenario["measurements"].get("status"),
            "typed_status": scenario["measurements"].get("typed"),
            "complete_stage_roster": complete, "stages": rows,
            "expected_cache_aware_usd": expected, "ordinary_partial_retry_tail_usd": tail,
            "expected_plus_observed_ordinary_tail_usd": expected + tail if complete else None,
            "one_pass_uncached_at_caps_usd": sum(r["uncached_at_cap_usd"] for r in base) if complete else None,
            "one_pass_all_cache_write_at_caps_usd": sum(r["all_cache_write_at_cap_usd"] for r in base) if complete else None,
            "conditional_controller_retry_repair_envelope_usd": stress if stress_complete else None,
            "retry_repair_envelope_missing_phases": sorted(set(multiplicities) - phases),
            "typed_aggregate_input_limit": aggregate,
            "typed_aggregate_expected_input": sum(r["expected_input_tokens"] for r in typed) if typed_complete else None,
            "typed_aggregate_cap_scenario_input": sum(r["at_cap_input_estimate"] for r in typed) if typed_complete else None,
            "typed_aggregate_fits_cap_scenario": bool(aggregate is not None and sum(r["at_cap_input_estimate"] for r in typed) <= aggregate) if typed_complete else None,
            "nonfitting_requests": [r["id"] for r in rows if not r["context_fit_1m_estimate"]]})
    primary = {}
    for run in results:
        primary.setdefault((run["project"], run["arm"]), run)
    matrix = []
    columns = ("expected_cache_aware_usd", "ordinary_partial_retry_tail_usd",
               "one_pass_uncached_at_caps_usd", "one_pass_all_cache_write_at_caps_usd",
               "conditional_controller_retry_repair_envelope_usd")
    for label, project, count in MATRIX:
        run = primary.get((project, "baseline"))
        matrix.append({"cell": label, "project": project, "runs": count,
                       **{key: run[key] * count if run and run[key] is not None else None for key in columns}})
    crate = primary.get(("CHORUS", "with_crate"))
    conditional = {"cell": "D04 B only: with-crate CHORUS", "runs": 4,
                   **{key: 4 * crate[key] if crate and crate[key] is not None else None for key in columns}}
    totals = {key: sum(r[key] for r in matrix) if all(r[key] is not None for r in matrix) else None for key in columns}
    known_subtotal = {key: sum(r[key] for r in matrix if r[key] is not None) for key in columns}
    proxy = primary.get(("KIDS_FIRST", "baseline_draft_context_proxy"))
    proxy_totals = {key: sum(r[key] if r[key] is not None else proxy[key] * r["runs"]
                            for r in matrix) if proxy and all(r[key] is not None or
                            r["project"] == "KIDS_FIRST" and proxy[key] is not None for r in matrix) else None
                    for key in columns}
    d04b_totals = {key: totals[key] + conditional[key] if totals[key] is not None and conditional[key] is not None else None for key in columns}
    return {"format": "d4d_k1_cost_model_v1", "scenario_calibration": calibration,
            "rates_usd_per_token": RATES, "regate_observed_frequency": regate_frequency,
            "ordinary_partial_retry_fraction": partial_fraction,
            "results": results, "matrix": matrix, "matrix_totals": totals,
            "known_matrix_subtotal": known_subtotal, "draft_context_proxy_matrix_totals": proxy_totals,
            "d04b_conditional": conditional, "d04b_totals": d04b_totals, "network_calls": 0}


def money(value):
    return "UNKNOWN" if value is None else f"${value:,.2f}"


def tokens(value):
    return "UNKNOWN" if value is None else f"{value:,.0f}"


def markdown(model, ledger):
    lines = ["# K1: offline generation cost and size model — 2026-10-25", "",
        "This is an offline planning model on A16 `56c41163f`, composed with the two #5087 sizing files from `4c52b8e6f`. No provider calls, token-count calls or live runs occurred. It is not a launch registration or a budget guarantee.", "",
        "The expected column is a two-CHORUS transfer scenario. It includes the observed one-in-two report-regate frequency; the ordinary partial retry tail is separate. Other projects' outputs and cache behavior have not been observed under v10. Context failures and aggregate-input refusals prevent these arithmetic totals from authorizing a runnable matrix.", "",
        "The selected partition minimizes each indivisible-root path/byte bound, then uses the worker count needed by production packing. It does not minimize dollars: larger per-worker bounds can reduce workers but require new output-cap and request sizing. A17 may change these costs; this report does not assume its unmerged behavior.", "",
        "## Generation matrix", "",
        "| Cell | Runs | Expected, cache-aware | Observed ordinary tail extrapolation | One pass uncached at caps | One pass all-cache-write stress | Conditional controller retry/repair envelope |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for row in [*model["matrix"], {"cell": "Total before D04 B", "runs": sum(r["runs"] for r in model["matrix"]), **model["matrix_totals"]},
                {"cell": "Subtotal of priced cells (excludes unknown cells)", "runs": "—", **model["known_matrix_subtotal"]},
                {"cell": "Conditional 16-run total using old draft-context KIDS_FIRST proxy", "runs": 16, **model["draft_context_proxy_matrix_totals"]},
                model["d04b_conditional"], {"cell": "Total if D04 B (actual contexts)", "runs": 20, **model["d04b_totals"]}]:
        lines.append(f"| {row['cell']} | {row['runs']} | " + " | ".join(money(row[key]) for key in (
            "expected_cache_aware_usd", "ordinary_partial_retry_tail_usd", "one_pass_uncached_at_caps_usd",
            "one_pass_all_cache_write_at_caps_usd", "conditional_controller_retry_repair_envelope_usd")) + " |")
    lines += ["", "The matrix excludes prior sunk costs, evaluation ratings, native subscription/runtime cost and discretionary reruns. D04 B is conditional; a with-crate proxy is not baseline CHORUS multiplied by four.", "",
        f"Budget implication: priced cells already total {money(model['known_matrix_subtotal']['expected_cache_aware_usd'])} before unknown cells, the separate ordinary tail and evaluation, against the stated $420 campaign ceiling. Resolve partition/carry/aggregate-input limits before choosing a launch allocation. This is not proof that a different validated partition could not lower cost.", "",
        "KIDS_FIRST's AI_READI proxy contains `/instances/0/data_topic: B2AI_TOPIC:43`; the actual neutral omission context supplies no B2AI_TOPIC vocabulary, so typed preparation refuses. This is a proxy incompatibility, not an established production defect. The old A1 draft-context cost is retained only as a conditional sensitivity; an actual-context typed cost and complete matrix total remain UNKNOWN.", "",
        "## Primary scenario constraints", "",
        "| Project / arm | Actual workers | Typed input, expected / cap-scenario | Registered aggregate | Requests exceeding 1M at caps |",
        "|---|---:|---:|---:|---|"]
    seen = set()
    for run in model["results"]:
        identity = run["project"], run["arm"]
        if identity in seen:
            continue
        seen.add(identity)
        workers = sum(row["phase"] == "typed_audit_worker" for row in run["stages"])
        lines.append(f"| {' / '.join(identity)} | {workers if run['typed_aggregate_expected_input'] is not None else 'UNKNOWN'} | {tokens(run['typed_aggregate_expected_input'])} / {tokens(run['typed_aggregate_cap_scenario_input'])} | {run['typed_aggregate_input_limit']} | {', '.join(run['nonfitting_requests']) or 'None among constructed requests'} |")
    lines += ["", "These are token estimates, including future cap-sized carries. A failure identifies exposure; a fit does not clear a production request. The detailed sections include every worker, optional request, clearance and the stricter report margin.", "", "## Method and limits", "",
        "- Actual context tokens are input_tokens + cache_read + cache_write. Dollars price those categories at 5e-6, 0.5e-6 and 6.25e-6 respectively; output is 25e-6. Thinking is already in output tokens.",
        "- Production request builders are used with historical records and explicit synthetic carries. The retained JSON records every source pin, normalization/conformance edit, proxy and indivisible root. Future model-written records can exceed these planning bounds.",
        "- For full, receipt, workers and omission (no synthetic carry), expected input applies the fitted historical payload token/byte ratio to current A16 bytes, preserving the cost of new fixed text. Carry-dependent integration/reconcile/report use a separate mean observed-input/scenario-input transfer factor, floored at the estimated current non-placeholder input so mandatory text cannot disappear. That transfer cannot isolate new fixed prompt/schema cost from future carry size: these stages remain a conditional scenario, not a calibrated production forecast. Every row records its basis and whether this floor applied.",
        "- Expected output uses the completed-call mean fraction of the phase cap. For report this transfers historical 96k-cap utilization to the new 128k cap, rather than holding output at its historical token mean. This is an explicit low-information transfer assumption, not a claim that cap-sized thinking is carried as text.",
        "- Matrix primary records are the first listed scenario per project/arm (10-22a for CHORUS); they are disclosed stand-ins, not newly selected scientific representatives. Other historical replicates and future output variation are not automatically bounded by this point forecast.",
        "- The uncached at-cap column takes the larger of A1 input estimates and fitted historical payload-byte estimates plus cap placeholders, then charges one cap per base stage. It is a scenario envelope, not a mathematical upper bound on arbitrary future text or billable usage. Cache writes cost more than uncached input, hence the separate stress column.",
        "- Retry/repair exposure permits 25 controller attempts each for full/reconcile, five for each report-family call, 25 readdress dispatches across five usable-body attempts, four repair rounds × five transport attempts, plus one typed/receipt call each. SDK retries and unbounded changed/error text prevent interpreting that finite scenario as a complete invoice ceiling. No retry probabilities were inferred from two runs.",
        "- Both the actual 1M context threshold and the older A1 850k report margin are shown. Report-family output caps are 128,000. Typed aggregate input is checked separately against the registered 4M allowance (#5155).", "",
        "## Archived ledger calibration", "",
        "| Run | Settled token-accounted cost | Partial abandoned usage | Observed sum |", "|---|---:|---:|---:|"]
    for run in ledger["runs"]:
        settled, tail = run["cost_usd_settled_usage"], run["abandoned_cost_usd_observed_lower_bound"]
        lines.append(f"| {run['date']} | {money(settled)} | {money(tail)} | {money(settled+tail)} |")
    lines += ["", "Abandoned counters are partial observations. The historical low-cap worker truncation and manual typed-stage recovery are not ordinary retry frequencies. Detailed exact-byte calibration and every joined input pin are in `ledger_calibration.json` and `ledger_calibration.md`.", "",
        "| Stage | Exact/reconstructed payload pairs | A1 byte error % | Other-canary max absolute error % |", "|---|---:|---|---|"]
    for phase, stats in ledger["stage_calibration"].items():
        lines.append(f"| {phase} | {stats['paired_request_rows']} | {stats['raw_a1_error_percent_range']} | {stats['cross_canary_absolute_error_percent_max']} |")
    lines += ["", "`None` means no exact historical payload calibration; it is not zero error. The following target-builder scenario errors are distinct from exact-request calibration:", "",
        "| Canary | Stage | Raw scenario error % | Held-out calibrated error % |", "|---|---|---:|---:|"]
    for row in model["scenario_calibration"]["rows"]:
        cross = row["held_out_error_percent"]
        lines.append(f"| {row['date']} | {row['phase']} | {row['raw_scenario_error_percent']:.2f} | {cross if cross is not None else 'UNKNOWN (one observation)'} |")
    lines += ["", "## Per-record planning bounds and requests", ""]
    for run in model["results"]:
        p = run["planning"]
        lines += [f"### {run['project']} / {run['arm']} / {run['label']}", "",
            f"Selected bounds: `{run['selected_limits']}`. Componentwise minimum: `{p['componentwise_minimum']}`. Four-worker lexicographic point: `{p['four_worker_lexicographic_point']}`.", "",
            f"Record proxy: `{run['proxy']}`. Conformance edits: `{run['staged_record_conformance_edits']}`.", "",
            f"Additional scenario qualifications: `{run['scenario_qualifiers']}`.", "",
            "| Indivisible root | Paths | Canonical inventory bytes |", "|---|---:|---:|"]
        lines += [f"| {r['root']} | {r['paths']} | {r['inventory_bytes']} |" for r in p["indivisible_roots"]]
        lines += ["", "| Request | A1 cap-scenario input | Calibrated expected input | Input used for cap fit | Output cap | 1M clearance | At-cap 1M fit | 850k report margin |", "|---|---:|---:|---:|---:|---:|---|---|"]
        for row in run["stages"]:
            expected = row["expected_input_tokens"]
            lines.append(f"| {row['id']} | {row['estimated_input_tokens']:,} | {round(expected):,}" if expected is not None else f"| {row['id']} | {row['estimated_input_tokens']:,} | UNKNOWN")
            lines[-1] += f" | {row['at_cap_input_estimate']:,.0f} | {row['max_output_tokens']:,} | {1_000_000-row['context_total_at_cap_estimate']:,.0f} | {'fits estimate' if row['context_fit_1m_estimate'] else 'EXCEEDS estimate'} | {row['report_margin_850k_estimate']} |"
        lines += ["", f"Typed aggregate: expected {tokens(run['typed_aggregate_expected_input'])}; cap scenario {tokens(run['typed_aggregate_cap_scenario_input'])}; registered allowance {run['typed_aggregate_input_limit']}; cap-scenario fit `{run['typed_aggregate_fits_cap_scenario']}`.",
                  f"Typed construction status: `{run['typed_status'].get('status')}`; refusal: `{run['typed_status'].get('reason')}`.",
                  f"Every non-fitting request: `{run['nonfitting_requests']}`. Complete stage roster: `{run['complete_stage_roster']}`.", ""]
    if model.get("planning_sensitivity"):
        lines += ["## Known-record planning sensitivity", "",
            "These envelopes plan every listed schema-conformed stand-in, not unseen v10 records. The cost matrix above uses the explicitly measured primary record. CHORUS retains its required 80 / 12,288 / 4 profile; the historical envelope is an A17 diagnostic, not an authorized replacement.", "",
            "| Project | Staged records | Known-record envelope paths / bytes / workers |", "|---|---:|---|"]
        for project, data in model["planning_sensitivity"]["projects"].items():
            limits = data["known_record_envelope"]
            lines.append(f"| {project} | {data['record_count']} | {limits['max_paths']} / {limits['max_inventory_bytes']} / {limits['max_workers']} |")
        lines.append("")
    lines += ["## Provenance", "", "Scripts are retained in `scripts/adhoc/` on the K1 branch. Inputs below are SHA256-pinned; no upstream ledger or source bundle was edited.", ""]
    lines += [f"- `{p['path']}` — `{p['sha256']}` ({p['bytes']} bytes)" for p in model["inputs"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizing", type=Path, required=True)
    parser.add_argument("--supplement", type=Path, action="append", default=[])
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--planning", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sizing = json.loads(args.sizing.read_bytes())
    for path in args.supplement:
        extra = json.loads(path.read_bytes())
        if not extra.get("complete"):
            raise ValueError("refuse unfinished sizing supplement")
        if extra.get("replaces") or any(row.get("replaces") for row in extra["rows"]):
            identities = {(row["project"], row["label"], row.get("arm", "baseline")) for row in extra["rows"]}
            before = len(sizing["rows"])
            replaced = [row for row in sizing["rows"] if (row["project"], row["label"], row.get("arm", "baseline")) in identities]
            sizing["rows"] = [row for row in sizing["rows"] if
                              (row["project"], row["label"], row.get("arm", "baseline")) not in identities]
            if before - len(sizing["rows"]) != len(extra["rows"]):
                raise ValueError("sizing replacement must identify exactly one existing row per replacement")
            for row in replaced:
                if row["project"] == "KIDS_FIRST":
                    sizing["rows"].append({**row, "arm": "baseline_draft_context_proxy",
                        "context_basis": "Superseded inherited A1 draft context, not actual A16 Kids First context; cost sensitivity only."})
        sizing["rows"].extend(extra["rows"])
    ledger = json.loads(args.ledger.read_bytes())
    model = calculate(sizing, ledger)
    model["inputs"] = [pin(args.sizing), *(pin(path) for path in args.supplement), pin(args.ledger), pin(__file__)]
    if args.planning:
        planning = json.loads(args.planning.read_bytes())
        model["planning_sensitivity"] = {"projects": {project: {
            "record_count": len(data["rows"]), "known_record_envelope": data["known_record_envelope"],
            "envelope_worker_counts": data["envelope_worker_counts"]}
            for project, data in planning["projects"].items()}}
        model["inputs"].append(pin(args.planning))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cost_model.json").write_text(json.dumps(model, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (args.out / "k1_cost_model_2026-10-25.md").write_text(markdown(model, ledger), encoding="utf-8")


if __name__ == "__main__":
    main()
