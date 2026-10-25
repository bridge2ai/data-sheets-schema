#!/usr/bin/env python3
"""K1 offline ledger calibration, 2026-10-25.

Inputs: read-only launch-base 10-20a/10-22a usage ledgers, pinned request and
context snapshots, full exchanges. Outputs: JSON + Markdown cost/calibration
evidence. Serves the 2026-10-25 K1 assignment and #5150/#5157. Never calls a
provider. Partial abandoned usage is a lower bound, not a settled invoice.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import offline_sizing as sizing

DATES = ("2026-10-20a", "2026-10-22a")
RATES = {"input_tokens": 5e-6, "output_tokens": 25e-6,
         "cache_write": 6.25e-6, "cache_read": 0.5e-6}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def cost(row):
    return sum(row.get(key, 0) * rate for key, rate in RATES.items())


def total_input(row):
    return sum(row.get(key, 0) for key in ("input_tokens", "cache_read", "cache_write"))


class Reader:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.pins = {}

    def raw(self, path):
        path = Path(path).resolve()
        path.relative_to(self.root)
        raw = path.read_bytes()
        self.pins[str(path)] = {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}
        return raw

    def pinned(self, pin):
        path = Path(pin["path"])
        if not path.is_absolute():
            path = self.root / path
        raw = self.raw(path)
        if sha(raw) != pin["sha256"]:
            raise ValueError(f"changed archived snapshot: {path}")
        return json.loads(raw)


def request_mapping(reader, ledger):
    """Bind exact retained logical requests to settled usage IDs; no filename guesses."""
    requests = {}
    settled = {row["usage_id"]: row for row in ledger["rows"]}
    if len(settled) != len(ledger["rows"]):
        raise ValueError("duplicate settled usage ID")
    stages = [(ledger["receipt_completion"], "full_receipt_completion")]
    stages.extend((stage, stage["selection"]["phase"]) for stage in ledger["typed_audit"]["stages"])
    for stage, expected_phase in stages:
        usage_id = stage["usage_id"]
        if usage_id in requests:
            raise ValueError("duplicate retained stage usage ID")
        if usage_id not in settled or settled[usage_id]["phase"] != expected_phase:
            raise ValueError("retained stage does not join settled usage with expected phase")
        request = reader.pinned(stage["request"])
        context = reader.pinned(stage["context"])
        if context["request_sha256"] != sha(canonical(request)):
            raise ValueError("saved endpoint count does not bind logical request")
        requests[usage_id] = {
            "payload": request, "request_basis": "pinned retained logical request",
            "request_pin": stage["request"], "context_pin": stage["context"],
            "saved_endpoint_input_tokens": context["input_tokens"],
        }
    # The exact exchange is retained, but the envelope is reconstructed from
    # the registration's model/settings plus that row's cap. Do not describe
    # this as a retained request-body file or a measured endpoint count.
    transcript = reader.pinned(ledger["receipt_completion_transcript"])
    row = next(row for row in ledger["rows"] if row["usage_id"] == transcript["usage_id"])
    if transcript["usage_id"] in requests or transcript["phase"] != row["phase"] or row["phase"] != "full":
        raise ValueError("full transcript usage ID/phase is ambiguous")
    registration_pin = ledger["input_identity"]["shared_generation"]["registration"]
    if sha(registration_pin["raw_json"].encode()) != registration_pin["sha256"]:
        raise ValueError("embedded registration differs from its archived digest")
    registration = json.loads(registration_pin["raw_json"])
    runtime = registration["runtime"]
    payload = {"model": runtime["model"], "system": transcript["system"],
               "messages": transcript["messages"], "max_tokens": row["max_tokens"]}
    if runtime.get("temperature") is not None:
        payload["temperature"] = runtime["temperature"]
    if runtime.get("thinking") is not None:
        payload["thinking"] = runtime["thinking"]
    if runtime.get("effort") is not None:
        payload["output_config"] = {"effort": runtime["effort"]}
    requests[row["usage_id"]] = {
        "payload": payload, "request_basis": "reconstructed envelope from pinned full exchange and archived registration settings",
        "transcript_pin": ledger["receipt_completion_transcript"],
        "saved_endpoint_input_tokens": None,
    }
    return requests


def calibrate(rows):
    """Fit per-phase bytes→tokens on the other canary; keep raw A1 errors too."""
    selected = [r for r in rows if r["payload_bytes"] is not None]
    for row in rows:
        row["leave_other_canary_out"] = None
        if row["payload_bytes"] is None:
            continue
        other = [r for r in selected if r["date"] != row["date"] and r["phase"] == row["phase"]]
        if not other:
            continue
        ratio = sum(r["total_input_tokens"] for r in other) / sum(r["payload_bytes"] for r in other)
        prediction = round(row["payload_bytes"] * ratio)
        row["leave_other_canary_out"] = {
            "training_dates": sorted({r["date"] for r in other}), "training_rows": len(other),
            "tokens_per_byte": ratio, "predicted_input_tokens": prediction,
            "error_tokens": prediction - row["total_input_tokens"],
            "error_percent": 100 * (prediction / row["total_input_tokens"] - 1),
        }
    phases = {}
    for phase in sorted({r["phase"] for r in rows}):
        source = [r for r in rows if r["phase"] == phase]
        exact = [r for r in source if r["payload_bytes"] is not None]
        complete = [r for r in source if r["stop_reason"] == "end_turn"]
        totals = {key: sum(r[key] for r in source) for key in RATES}
        inputs = sum(r["total_input_tokens"] for r in source)
        phases[phase] = {
            "settled_rows": len(source), "paired_request_rows": len(exact),
            "calibration_status": "measured CHORUS logical-body bytes to observed usage" if exact else "UNKNOWN: no retained logical request body joined",
            "fit_tokens_per_byte": sum(r["total_input_tokens"] for r in exact) / sum(r["payload_bytes"] for r in exact) if exact else None,
            "fitted_canaries": sorted({r["date"] for r in exact}),
            "raw_a1_error_percent_range": [min(r["raw_a1_error_percent"] for r in exact), max(r["raw_a1_error_percent"] for r in exact)] if exact else None,
            "cross_canary_absolute_error_percent_max": max((abs(r["leave_other_canary_out"]["error_percent"]) for r in exact if r["leave_other_canary_out"]), default=None),
            "observed_cache_input_fractions": {key: totals[key] / inputs for key in ("input_tokens", "cache_read", "cache_write")},
            "output_tokens_completed_mean": statistics.mean(r["output_tokens"] for r in complete) if complete else None,
            "output_tokens_completed_range": [min(r["output_tokens"] for r in complete), max(r["output_tokens"] for r in complete)] if complete else None,
            "completed_output_cap_fraction_mean": statistics.mean(r["output_tokens"] / r["max_tokens"] for r in complete) if complete else None,
            "input_cost_per_total_token": sum(totals[key] * RATES[key] for key in ("input_tokens", "cache_read", "cache_write")) / inputs,
            "settled_cost_usd": sum(r["cost_usd"] for r in source),
        }
    return phases


def analyze(root):
    reader = Reader(root)
    runs, rows, abandoned_rows = [], [], []
    for date in DATES:
        folder = reader.root / "data/d4d_concatenated/claudecode_api_core" / f"{date}_claude-opus-5-api-generic-v10_rep1"
        files = sorted(folder.glob("CHORUS_api_usage_*.json"))
        if len(files) != 1:
            raise ValueError(f"expected one authoritative ledger for {date}: {files}")
        ledger = json.loads(reader.raw(files[0]))
        mapping = request_mapping(reader, ledger)
        seen = set()
        for original in ledger["rows"]:
            if original["usage_id"] in seen:
                raise ValueError("duplicate settled usage ID")
            seen.add(original["usage_id"])
            row = {"date": date, **original, "cost_usd": cost(original),
                   "total_input_tokens": total_input(original), "payload_bytes": None,
                   "request_basis": "unjoined: no retained logical request identified", "raw_a1_estimate": None,
                   "raw_a1_error_tokens": None, "raw_a1_error_percent": None}
            row["accounting_class"] = ("paid output-cap-exhausted attempt; not an accepted request or automatic ordinary-phase retry"
                                       if original.get("stop_reason") == "max_tokens" else "completed accounted response")
            if original["usage_id"] in mapping:
                request = mapping[original["usage_id"]]
                payload = request["payload"]
                payload_bytes = len(canonical(payload))
                if payload["max_tokens"] != row["max_tokens"]:
                    raise ValueError("request cap differs from accounted call")
                estimate = sizing.estimate("CHORUS", row["phase"], payload_bytes, row["max_tokens"])["estimated_input_tokens"]
                row.update({key: value for key, value in request.items() if key != "payload"})
                row.update(payload_bytes=payload_bytes, payload_sha256=sha(canonical(payload)),
                           raw_a1_estimate=estimate, raw_a1_error_tokens=estimate-row["total_input_tokens"],
                           raw_a1_error_percent=100*(estimate/row["total_input_tokens"]-1))
            rows.append(row)
        abandoned = [json.loads(line) for line in reader.raw(folder / "CHORUS_abandoned_attempts.jsonl").splitlines() if line.strip()]
        for row in abandoned:
            if row["usage_id"] in seen:
                raise ValueError("duplicate abandoned or overlapping settled usage ID: reconcile rather than double count")
            seen.add(row["usage_id"])
            if row["generation_id"] != ledger["generation_id"]:
                raise ValueError("foreign abandoned generation")
            abandoned_rows.append({"date": date, **row, "cost_usd_observed_lower_bound": cost(row)})
        stage_cost = defaultdict(float)
        for row in rows:
            if row["date"] == date:
                stage_cost[row["phase"]] += row["cost_usd"]
        runs.append({"date": date, "ledger": reader.pins[str(files[0].resolve())],
                     "settled_rows": len(ledger["rows"]), "cost_usd_settled_usage": sum(stage_cost.values()),
                     "stage_cost_usd": dict(stage_cost), "abandoned_rows": len(abandoned),
                     "abandoned_cost_usd_observed_lower_bound": sum(cost(r) for r in abandoned),
                     "accounting_limit": "token counters at supplied rates, not billing reconciliation; abandoned output counters may be incomplete"})
    phases = calibrate(rows)
    for pin in reader.pins.values():
        raw = Path(pin["path"]).read_bytes()
        if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
            raise ValueError("source changed during read-only calibration")
    return {"format": "d4d_k1_ledger_calibration_v1", "rates_usd_per_token": RATES,
            "runs": runs, "stage_calibration": phases, "settled_rows": rows,
            "abandoned_rows": abandoned_rows, "inputs": sorted(reader.pins.values(), key=lambda p:p["path"]),
            "method": "Compare A1's byte estimate with observed input+cache-read+cache-write; fit same-stage total tokens/payload-byte, cross-validate on the other CHORUS canary.",
            "limits": ["Only two CHORUS runs; not evidence of cross-project output/caching behavior.",
                       "Reported output_tokens already includes thinking; do not add thinking_tokens again.",
                       "Historical full envelope reconstructed from retained exchange; other calibrated stages have pinned logical payloads.",
                       "Reconcile/report/regate have observed token usage but no retained request-body join; their byte error is UNKNOWN.",
                       "10-20a includes one paid typed worker truncated at an earlier 25,000-token cap; this is not evidence for ordinary-phase retry probability or authorization for typed retries.",
                       "Abandoned rows are observed partial charges, not final invoices or a measured retry distribution."],
            "network_calls": 0}


def markdown(report):
    lines = ["# K1 archived usage and calibration", "", report["method"], "",
             "| Run | Settled calls | Settled usage cost | Abandoned partial usage | Sum (observed lower bound) |",
             "|---|---:|---:|---:|---:|"]
    for run in report["runs"]:
        base, tail = run["cost_usd_settled_usage"], run["abandoned_cost_usd_observed_lower_bound"]
        lines.append(f"| {run['date']} | {run['settled_rows']} | ${base:.6f} | ${tail:.6f} | ${base+tail:.6f} |")
    lines += ["", "| Stage | Joined requests / settled calls | Fitted tokens/byte | Raw A1 error % range | Other-canary max absolute error % | Completed output mean |",
              "|---|---:|---:|---|---:|---:|"]
    for phase, value in report["stage_calibration"].items():
        ratio = value["fit_tokens_per_byte"]
        error = value["raw_a1_error_percent_range"]
        cross = value["cross_canary_absolute_error_percent_max"]
        lines.append(f"| {phase} | {value['paired_request_rows']} / {value['settled_rows']} | {ratio if ratio is not None else 'UNKNOWN'} | {error if error is not None else 'UNKNOWN'} | {cross if cross is not None else 'UNKNOWN'} | {value['output_tokens_completed_mean']} |")
    lines += ["", *[f"- {text}" for text in report["limits"]], ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launch-base", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sizing.block_network()
    report = analyze(args.launch_base)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "ledger_calibration.json").write_bytes(canonical(report) + b"\n")
    (args.out / "ledger_calibration.md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    if sizing.NETWORK_ATTEMPTS:
        raise RuntimeError("network attempt occurred")


if __name__ == "__main__":
    main()
