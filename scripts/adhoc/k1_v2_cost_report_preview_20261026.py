#!/usr/bin/env python3
"""K1 v2/#5155/#5157, 2026-10-26: offline granularity/cache/overflow report.

Inputs: pinned K1 calibration, A17 request measurements and preserved-ledger
audit. Outputs: JSON, Markdown and a complete nonfitting-component TSV. No
network, tokenizer, model call or production registration. Component tokens
are allocations of scenario estimates, not independently measured token counts.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from scripts.adhoc.k1_build_cost_report_20261025 import (
    BASE_PHASES, RATES, calibrated_stage, pin, stage_rows,
)

# This report's historical narrative and 1/4 timing-transfer assumption were
# independently reviewed against these exact audit bytes. Changed evidence
# requires a revised analysis, not silent reuse of the old narrative.
REVIEWED_LEDGER_AUDIT_SHA256 = "c08021250e34ba6b6a1dad7cfa09c6a36415657484c5ddea7b01b72ffe9150dc"
REVIEWED_TTL_GUARD_SHA256 = "0aef1b59d05fd9a1f7f6e2f83b863800fb48e6c35e22030cbcbcfc373c5375e2"


def reviewed_input(path, expected):
    identity = pin(path)
    if identity["sha256"] != expected:
        raise ValueError(f"reviewed narrative authority changed: {path}")
    return identity


def payload_for(scenario, row):
    payloads = scenario["payloads"]
    phase = row["phase"]
    if phase == "typed_audit_integration":
        return next(p for p in payloads if p["payload"]["sha256"] ==
                    scenario["selected_integration_payload_sha256"])
    name = row.get("request_name", {"typed_audit_omission": "omission",
               "report_after_repair": "report"}.get(phase, phase))
    return next(p for p in payloads if p["name"] == name)


def allocate_components(row, payload, stats, estimate):
    """Exact sum within floating precision; assign carries once, not to bytes."""
    total = row[estimate]
    if total is None:
        return None
    byte_parts = payload["parts"]["component_bytes"]
    size = payload["parts"]["payload_bytes"]
    if sum(byte_parts.values()) != size or size != row["payload_bytes"]:
        raise ValueError("component bytes do not match selected request")
    sources = payload["placeholder_sources"]
    placeholder = row.get("placeholder_tokens", 0)
    if sum(sources.values()) != placeholder:
        raise ValueError("carry sources do not match selected estimate")
    fit = stats.get("fit_tokens_per_byte") if stats else None
    fixed = size * fit if fit is not None else row["estimated_input_tokens"] - placeholder
    carry = max(total - fixed, 0) if estimate == "expected_input_tokens" else placeholder
    if not placeholder:
        carry = 0
    fixed = total - carry
    if fixed < 0:
        raise ValueError("negative fixed request allocation")
    parts = {key: fixed * value / size for key, value in byte_parts.items()}
    mapping = {"assembled_audit": "audit_carry", "omission_response": "audit_carry",
               "rejected_report": "rejected_report", "worker_outputs": "worker_outputs",
               "readdress_response": "records"}
    for source, value in sources.items():
        if source not in mapping:
            raise ValueError(f"unclassified placeholder source: {source}")
        parts[mapping[source]] += carry * value / placeholder if placeholder else 0
    if abs(sum(parts.values()) - total) > .001:
        raise ValueError("component tokens do not sum to input estimate")
    return {"token_allocations": parts, "input_total": total,
            "fixed_input_allocation": fixed, "carry_allocation": carry,
            "input_percent": {k: 100 * v / total if total else 0 for k, v in parts.items()},
            "output_reserve": row["max_output_tokens"],
            "context_total": total + row["max_output_tokens"],
            "basis": "Fixed input apportioned by disjoint serialized bytes; inferred carry apportioned by explicit placeholder sources. No tokenizer or independent semantic token measurement."}


def cache_scenario(workers, payloads, prefix, baseline, input_rate, fit, hit_fraction):
    """Price only the estimated common prefix; the first worker always writes."""
    if not workers or baseline is None:
        return None
    current = prefix.get("serialized_prefix_proxy_bytes", 0)
    shared = [p["shared_prefix"]["shared_context_outer_payload_byte_contribution"]
              for p in payloads if "shared_prefix" in p]
    if len(shared) != len(workers):
        raise ValueError("shared prefix/worker roster mismatch")
    # Counterfactual: move the identical shared_context before varying schema.
    # Its nested escaped contribution is a proxy for a not-yet-built new wire.
    estimates = [min(w["expected_input_tokens"], (current + n) * fit)
                 for w, n in zip(workers, shared)]
    effective_rates = [RATES["cache_write"]] + [
        hit_fraction * RATES["cache_read"] + (1 - hit_fraction) * RATES["cache_write"]
        for _ in workers[1:]]
    delta = sum(tokens * (rate - input_rate) for tokens, rate in zip(estimates, effective_rates))
    return {"expected_usd": baseline + delta, "delta_usd": delta,
            "prefix_estimated_tokens_per_worker": estimates,
            "later_worker_hit_fraction": hit_fraction,
            "worker_count": len(workers), "first_worker_cache_write": True,
            "basis": "Counterfactual reordered shared prefix; escaped-byte token proxy. Existing per-stage cache-aware baseline retained outside this prefix. Output, context size and aggregate input unchanged."}


def calculate(measurements, prior, ledger):
    rows = []
    stats = ledger["stage_calibration"]
    factors = prior["scenario_calibration"]["factors"]
    for scenario in measurements:
        stages = [calibrated_stage(r, stats, factors) for r in stage_rows(scenario)]
        by_phase = {s["phase"]: s for s in stages}
        complete = set(BASE_PHASES) <= by_phase.keys() and "report_regate" in by_phase
        base = [r for r in stages if r["phase"] in BASE_PHASES]
        expected = (sum(r["expected_cache_aware_usd"] for r in base) +
                    .5 * by_phase["report_regate"]["expected_cache_aware_usd"]) if complete else None
        typed = [s for s in stages if s["phase"].startswith("typed_audit_")]
        typed_complete = {"typed_audit_worker", "typed_audit_omission", "typed_audit_integration"} <= by_phase.keys()
        ordinary = {"full", "reconcile_full", "report", "report_regate"}
        ordinary_cost = sum(s["expected_cache_aware_usd"] for s in base if s["phase"] in ordinary)
        if "report_regate" in by_phase:
            ordinary_cost += .5 * by_phase["report_regate"]["expected_cache_aware_usd"]
        overflow = []
        margins = []
        for stage in stages:
            family = {"report_after_repair": "report", "full_receipt_completion_after_readdress":
                      "full_receipt_completion"}.get(stage["phase"], stage["phase"])
            for estimate in ("expected_input_tokens", "at_cap_input_estimate"):
                total = stage[estimate]
                if total is None:
                    continue
                if family in ("report", "report_regate") and total + stage["max_output_tokens"] > 850_000:
                    margins.append({"phase": stage["phase"], "estimate": estimate,
                                    "context_total": total + stage["max_output_tokens"]})
                if total + stage["max_output_tokens"] <= 1_000_000:
                    continue
                payload = payload_for(scenario, stage)
                overflow.append({"phase": stage["phase"], "id": stage["id"], "estimate": estimate,
                    "request": payload["payload"], "payload_bytes": payload["parts"]["component_bytes"],
                    "placeholder_sources": payload["placeholder_sources"],
                    "record_basis": "Unchanged report proxy; repaired future record unknown" if stage["phase"] == "report_after_repair" else "retained/conformed record and explicit carry scenario",
                    **allocate_components(stage, payload, stats.get(family), estimate)})
        workers = [s for s in stages if s["phase"] == "typed_audit_worker"]
        cache = {}
        if workers and scenario.get("hypothetical_shared_prefix_identical"):
            for name, hit in (("no_hits_all_writes", 0), ("300s_start_clock_transfer", .25),
                              ("all_later_calls_hit_upper_scenario", 1)):
                cache[name] = cache_scenario(workers, scenario["payloads"],
                    scenario["current_wire_common_worker_prefix"], expected,
                    stats["typed_audit_worker"]["input_cost_per_total_token"],
                    stats["typed_audit_worker"]["fit_tokens_per_byte"], hit)
        rows.append({"project": scenario["project"], "label": scenario["label"],
            "plan_mode": scenario["plan_mode"], "primary": scenario["primary"],
            "selected_limits": scenario["selected_limits"], "status": scenario["measurements"].get("typed"),
            "record_proxy_for": scenario.get("record_proxy_for"),
            "plan": scenario.get("plan"), "stages": stages,
            "expected_usd_with_assisted_regate_scenario": expected,
            "ordinary_partial_retry_tail_usd": ordinary_cost * prior["ordinary_partial_retry_fraction"] if complete else None,
            "typed_expected_input": sum(s["expected_input_tokens"] for s in typed) if typed_complete else None,
            "typed_at_cap_input": sum(s["at_cap_input_estimate"] for s in typed) if typed_complete else None,
            "builder_5155_allowance": scenario.get("builder_5155_allowance"),
            "current_wire_common_worker_prefix": scenario.get("current_wire_common_worker_prefix"),
            "cache_scenarios": cache, "nonfitting_requests": overflow, "report_850k_margin_exposures": margins,
            "carry_basis": scenario["measurements"].get("findings_basis")})
    return rows


def number(value):
    return "UNKNOWN" if value is None else f"{value:,.0f}"


def money(value):
    return "UNKNOWN" if value is None else f"${value:.2f}"


def budget_subtotal(results, mode):
    counts = {"CHORUS": 4, "AI_READI": 4, "CM4AI": 3, "VOICE": 3, "VOICE_PEDIATRIC": 1}
    primary = {r["project"]: r for r in results if r["primary"] and r["plan_mode"] == mode}
    if not counts.keys() <= primary.keys() or any(primary[p]["expected_usd_with_assisted_regate_scenario"] is None for p in counts):
        return None
    return {"known_runs": sum(counts.values()), "counts": counts,
        "expected_usd": sum(n * primary[p]["expected_usd_with_assisted_regate_scenario"] for p, n in counts.items()),
        "ordinary_partial_retry_tail_usd": sum(n * primary[p]["ordinary_partial_retry_tail_usd"] for p, n in counts.items()),
        "basis": "Primary retained record per project transferred to campaign counts, not sum of different retained replicate measurements. Excludes UNKNOWN actual-context Kids First and optional with-crate CHORUS."}


def markdown(report):
    lines = ["# K1 v2: A17 granularity, cache scenarios and context exposure", "",
        "Offline decision evidence; **not launch clearance**. All costs transfer two assisted CHORUS histories to conformed old records. Actual v10 outputs and tokenization are unknown. Actual Kids First context rejects the AI-READI proxy, so its typed total stays UNKNOWN.", "",
        "## Decision implications", "",
        "D33's no-trim admission decision has exposure beyond Kids First. The table and complete component TSV distinguish expected-size failures from at-cap scenarios. Adding a cache breakpoint changes billing, not context admission. Finer workers reduce assigned inventory but repeat shared inputs and increase aggregate carry.", "",
        "Recommendation: retain the fail-closed admission check and hold A21 while the owner chooses a bounded integration/carry design for the exposed projects. Reducing duplicated fixed context, constraining the worker response contract, or staged integration each changes model-facing inputs and needs a reviewed implementation before the D35 freeze. Raising aggregate budget or enabling cache alone cannot make an oversized individual request fit. Do not silently trim source or audit evidence.", "",
        "The measured composition is A16 plus exact A17 partitioning and inherited #5087 sizing, not the later D39 launch contract. #5155's separate max-roster allowance uses its exact cached sizing functions; it is not the actual-roster expected cost.", "",
        "## Cost against granularity", "",
        "Costs include a 0.5 report-regate scenario from assisted history; this is not an estimated clean retry probability or authorization to repeat typed calls. Ordinary partial retry allowance is separate in JSON.", "",
        "| Project / retained record | Plan | Workers | Largest assigned bytes / 12,288 | Expected dollars | Typed expected input | Typed at-cap input |", "|---|---|---:|---:|---:|---:|---:|"]
    for r in report["results"]:
        plan = r.get("plan") or {}
        lines.append(f"| {r['project']} / {r['label']} | {r['plan_mode']} | {plan.get('worker_count', 'UNKNOWN')} | {number(plan.get('largest_worker_inventory_bytes'))} | {money(r['expected_usd_with_assisted_regate_scenario'])} | {number(r['typed_expected_input'])} | {number(r['typed_at_cap_input'])} |")
    lines += ["", "For the same 15-run known subtotal (4 CHORUS, 4 AI-READI, 3 CM4AI, 3 VOICE, 1 pediatric; primary retained record per project), excluding actual-context Kids First and optional crate arm:"]
    for mode, subtotal in report["known_budget_subtotals"].items():
        if subtotal:
            lines.append(f"- {mode}: {money(subtotal['expected_usd'])} plus {money(subtotal['ordinary_partial_retry_tail_usd'])} ordinary partial-usage scenario.")
    lines += ["", "12,288 bytes bounds assigned inventory, not response tokens. Each request also repeats the full inventory. A 64k output cap has no proven semantic adequacy guarantee; the JSON includes each worker's schema-valid response floor at four bytes/token, which is only a lower-size scenario.", "",
        "## Hypothetical typed shared-prefix cache", "",
        "The current wire puts worker-specific schema before the late shared_context. It cannot cache the requested whole bundle/records/receipt/manifest/schema content by merely marking the last block. A reorder/split is required and must be reviewed before D35. These numbers allocate a token proxy to that proposed common prefix; they do not implement or price a captured new request.", "",
        "Existing cache-aware stage input rates are preserved outside that prefix. First call writes; later writes cost $6.25/M and reads $0.50/M using the historical K1 rate schedule. These scenarios change worker input billing only; omission/integration costs, output charges, context size and aggregate input stay fixed. The six completed 64k workers took 153.741–541.771s; start gaps 545/241/519/440s imply only one of four later calls within 300s if TTL starts at request start. A late-refresh interpretation gives four of four, but is unverified. Observed worker cache reads were zero. The 25% transfer and 100% later-hit cases are scenarios, not predictions. 3600s is unpriced; the pinned notes/matched_cborg_2026-09-13/budgeted_cborg.py _prepare guard rejects 1h on that registered pricing path.", "",
        "| Project (primary A17) | Current cache-aware baseline | 300s start-clock transfer | All later hits, upper scenario |", "|---|---:|---:|---:|"]
    for r in report["results"]:
        if r["primary"] and r["plan_mode"] == "a17":
            c = r["cache_scenarios"]
            lines.append(f"| {r['project']} | {money(r['expected_usd_with_assisted_regate_scenario'])} | {money((c.get('300s_start_clock_transfer') or {}).get('expected_usd'))} | {money((c.get('all_later_calls_hit_upper_scenario') or {}).get('expected_usd'))} |")
    lines += ["", "## Every nonfitting measured request", "",
        "Token shares are disjoint allocations of calibrated input estimates by serialized byte contribution, plus separately assigned future-response carries. They are not tokenizer measurements. `nonfitting_components.tsv` has every component and input percentage, including bundle, records, schema, worker outputs, audit/evidence carry and rejected report. Output reserve is separate. `report_after_repair` repeats the report proxy; future repaired record growth is unknown. Unbounded contradiction-list growth is not covered by a hard bound.", "",
        "| Project / plan / retained record | Request | Scenario | Input | Output reserve | Total | Largest input components |", "|---|---|---|---:|---:|---:|---|"]
    for r in report["results"]:
        for f in r["nonfitting_requests"]:
            largest = sorted(f["token_allocations"].items(), key=lambda kv: kv[1], reverse=True)[:3]
            shares = "; ".join(f"{k} {number(v)} ({f['input_percent'][k]:.1f}%)" for k, v in largest)
            lines.append(f"| {r['project']} / {r['plan_mode']} / {r['label']} | {f['phase']} | {f['estimate']} | {number(f['input_total'])} | {number(f['output_reserve'])} | {number(f['context_total'])} | {shares} |")
    lines += ["", "## #5155 aggregate allowances", "",
        "Per-record actual roster expected/at-cap totals appear above and in JSON. The JSON separately retains the #5155 builder allowance and formula inputs: max permitted workers, largest request, omission, and integration empty body plus 3.5 input tokens per worker/omission response token at two bytes per input token. A permitted max roster is not an observed roster and is not a hard bound on arbitrary output expansion.", "",
        "| Project (primary A17) | Actual / max workers | #5155 integration input allowance | #5155 aggregate input allowance |", "|---|---:|---:|---:|"]
    for r in report["results"]:
        if r["primary"] and r["plan_mode"] == "a17":
            b = r.get("builder_5155_allowance") or {}
            lines.append(f"| {r['project']} | {b.get('plan_workers', 'UNKNOWN')} / {b.get('max_workers', 'UNKNOWN')} | {number(b.get('integration_input_tokens'))} | {number(b.get('aggregate_input_tokens'))} |")
    lines += ["",
        "## Ledger integrity and retained uncertainty", "",
        "See `ledger_originals.md` and its JSON pins. Ten matched 10-20 usage rows preserve numeric counters/caps/phase/stop reason, while report 72ac… changed admission and response hash. Later additions lack an original counterpart. No standalone 10-22 original was found in the ignored-inclusive 178-file preserved subtree; its edited outcomes cannot be authenticated independently. Both runs are evidence-only. Historical K1 outputs remain unchanged.", "",
        "All inputs, composition and helper identities are pinned in JSON. No provider or tokenizer calls, live registrations, prompt edits or launch authorization. Offline scratch registrations are construction fixtures only.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", nargs="+", required=True, type=Path)
    parser.add_argument("--prior", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--ledger-audit", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    ttl_guard = Path(__file__).resolve().parents[2] / "notes/matched_cborg_2026-09-13/budgeted_cborg.py"
    inputs = {"prior": pin(args.prior), "ledger": pin(args.ledger),
              "ledger_audit": reviewed_input(args.ledger_audit, REVIEWED_LEDGER_AUDIT_SHA256),
              "ttl_guard": reviewed_input(ttl_guard, REVIEWED_TTL_GUARD_SHA256),
              "measurements": [pin(p) for p in args.measurements], "script": pin(__file__),
              "cost_helper": pin(Path(__file__).with_name("k1_build_cost_report_20261025.py"))}
    rows = []
    for path in args.measurements:
        obj = json.loads(path.read_bytes())
        if not obj["complete"] or obj["network_attempts"]:
            raise ValueError("refuse incomplete or network-tainted measurement")
        rows.extend(obj["rows"])
    identities = [(r["project"], r["label"], r["plan_mode"]) for r in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate measurement identity")
    prior = json.loads(args.prior.read_bytes())
    if prior["regate_observed_frequency"] != .5:
        raise ValueError("assisted-regate scenario calibration changed")
    report = {"format": "k1_v2_cost_report_v1", "inputs": inputs,
        "results": calculate(rows, prior, json.loads(args.ledger.read_bytes())),
        "rates": RATES, "network_calls": 0}
    report["known_budget_subtotals"] = {mode: budget_subtotal(report["results"], mode) for mode in ("a17", "k1_minimum")}
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "cost_model.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (args.out / "README.md").write_text(markdown(report))
    with (args.out / "nonfitting_components.tsv").open("w") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["project", "label", "plan", "phase", "estimate", "component", "tokens", "input_percent", "input_total", "output_reserve", "context_total", "payload_sha256"])
        for r in report["results"]:
            for f in r["nonfitting_requests"]:
                for k, v in f["token_allocations"].items():
                    writer.writerow([r["project"], r["label"], r["plan_mode"], f["phase"], f["estimate"], k, v,
                                     f["input_percent"][k], f["input_total"], f["output_reserve"], f["context_total"], f["request"]["sha256"]])
    print(f"Wrote {len(rows)} scenarios; {sum(len(r['nonfitting_requests']) for r in report['results'])} nonfitting request/scenarios")


if __name__ == "__main__":
    main()
