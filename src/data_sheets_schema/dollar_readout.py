"""Read-only live dollar readout for D4D API generation runs (Step A3b / #1763, #4345, #4829).

Prices settled ledger rows using CBORG opus-5 rates from ``run_telemetry.py`` and
projects worst-case costs for in-flight pending calls across all generation phases:
- ``full`` (128,000 output cap)
- ``full_readdress`` (8,000 output cap / READDRESS_MAX_TOKENS)
- ``receipt_completion`` (cap and input from saved request and counted context)
- ``reconcile_full`` (96,000 output cap)
- ``report`` (96,000 output cap)
- ``report_regate`` (96,000 output cap)
- ``repair_full`` (96,000 output cap)
- ``report_after_repair`` (96,000 output cap)
- typed audit stages (cap and input from saved stage request and context)

Operator trigger logic alerts when projected total cost reaches the operator stop trigger
(cap minus worst-case in-flight call) to prevent overrunning allocations.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from data_sheets_schema.run_telemetry import (
    RATE_CACHE_READ,
    RATE_CACHE_WRITE,
    RATE_INPUT,
    RATE_OUTPUT,
)

# Phase output caps (tokens)
CAP_FULL = 128000
CAP_FULL_READDRESS = 8000
CAP_REPORT_FAMILY = 96000  # reconcile_full, report, report_regate, repair_full, report_after_repair
CAP_DEFAULT_ORDINARY = 128000
CAP_DEFAULT_TYPED = 24000

# Standard phase output caps mapping
PHASE_OUTPUT_CAPS: dict[str, int] = {
    "full": CAP_FULL,
    "full_readdress": CAP_FULL_READDRESS,
    "reconcile_full": CAP_REPORT_FAMILY,
    "report": CAP_REPORT_FAMILY,
    "report_regate": CAP_REPORT_FAMILY,
    "repair_full": CAP_REPORT_FAMILY,
    "report_after_repair": CAP_REPORT_FAMILY,
}

# Baseline reference input bounds (tokens or split) from preserved empirical runs:
# - CHORUS: v9 full input (9,636 uncached + 31,703 cache_write = 41,339 tokens)
# - AI_READI: v8 full input (6,361 uncached + 203,662 cache_write = 210,023 tokens)
PROJECT_BASELINE_INPUT_BOUNDS: dict[str, dict[str, Any]] = {
    "CHORUS": {
        "full": {"input_tokens": 9636, "cache_write": 31703, "cache_read": 0},
        "full_readdress": {"input_tokens": 41339 + 46182},  # input + v9 full response
        "reconcile_full": {"input_tokens": 22057, "cache_write": 0, "cache_read": 31703},
        "report": {"input_tokens": 44534, "cache_write": 0, "cache_read": 31703},
        "report_regate": {"input_tokens": 76237 + 96000 + 1500},  # report + 96k report + regate instructions
        "repair_full": {"input_tokens": 8914, "cache_write": 17406, "cache_read": 0},
        "report_after_repair": {"input_tokens": 44563, "cache_write": 0, "cache_read": 31703},
    },
    "AI_READI": {
        "full": {"input_tokens": 6361, "cache_write": 203662, "cache_read": 0},
        "full_readdress": {"input_tokens": 210023 + 115616},  # input + v8 full response
        "reconcile_full": {"input_tokens": 43279, "cache_write": 0, "cache_read": 203662},
        "report": {"input_tokens": 134946, "cache_write": 186293, "cache_read": 17369},
        "report_regate": {"input_tokens": 338608 + 96000 + 1500},  # report + 96k report + regate instructions
        "repair_full": {"input_tokens": 37011, "cache_write": 17419, "cache_read": 0},
        "report_after_repair": {"input_tokens": 134823, "cache_write": 186293, "cache_read": 17369},
    },
}


def price_tokens(
    *,
    input_tokens: int = 0,
    cache_write: int = 0,
    cache_read: int = 0,
    output_tokens: int = 0,
) -> float:
    """Calculate exact price in dollars for given token counts."""
    return (
        int(input_tokens or 0) * RATE_INPUT
        + int(cache_write or 0) * RATE_CACHE_WRITE
        + int(cache_read or 0) * RATE_CACHE_READ
        + int(output_tokens or 0) * RATE_OUTPUT
    )


def price_settled_row(row: Mapping[str, Any]) -> float:
    """Price a single settled API usage row from a ledger."""
    return price_tokens(
        input_tokens=row.get("input_tokens") or 0,
        cache_write=row.get("cache_write") or 0,
        cache_read=row.get("cache_read") or 0,
        output_tokens=row.get("output_tokens") or 0,
    )


def price_settled_rows(rows: list[Mapping[str, Any]]) -> float:
    """Price all settled rows in an API usage ledger."""
    return sum(price_settled_row(row) for row in rows)


def price_input_bound(bound: Any, *, worst_case_cache: bool = False) -> float:
    """Calculate input cost in dollars for an input bound.

    Can be a dict with {input_tokens, cache_write, cache_read} or an int/float count.
    If given as an integer token count:
    - Default (uncached): priced at RATE_INPUT ($5/M).
    - If worst_case_cache=True: priced at RATE_CACHE_WRITE ($6.25/M).
    """
    if isinstance(bound, Mapping):
        return price_tokens(
            input_tokens=bound.get("input_tokens") or 0,
            cache_write=bound.get("cache_write") or 0,
            cache_read=bound.get("cache_read") or 0,
        )
    if isinstance(bound, (int, float)):
        rate = RATE_CACHE_WRITE if worst_case_cache else RATE_INPUT
        return float(bound) * rate
    return 0.0


def extract_saved_snapshot(pin: Any) -> dict[str, Any] | None:
    """Attempt to load and hash-verify a snapshot JSON dict from a pin dict or file path."""
    expected_sha: str | None = None
    if isinstance(pin, Mapping) and "path" in pin:
        target = Path(pin["path"])
        sha_val = pin.get("sha256")
        if isinstance(sha_val, str) and sha_val.strip():
            expected_sha = sha_val.strip().lower()
    elif isinstance(pin, (str, Path)):
        target = Path(pin)
    else:
        return None
    if target.is_file():
        try:
            raw_bytes = target.read_bytes()
            if expected_sha is not None:
                actual_sha = hashlib.sha256(raw_bytes).hexdigest().lower()
                if actual_sha != expected_sha:
                    return None
            return json.loads(raw_bytes.decode("utf-8"))
        except (OSError, ValueError):
            return None
    return None


def get_phase_output_cap(
    phase: str,
    *,
    saved_request: Mapping[str, Any] | None = None,
    registration: Mapping[str, Any] | None = None,
) -> int:
    """Determine the worst-case output cap for a phase string."""
    # If a saved request payload with max_tokens exists, it takes precedence (e.g. typed / receipt)
    if saved_request and isinstance(saved_request.get("max_tokens"), int):
        return saved_request["max_tokens"]

    # Known ordinary phase caps
    if phase in PHASE_OUTPUT_CAPS:
        return PHASE_OUTPUT_CAPS[phase]

    # Receipt completion fallback
    if phase in {"receipt_completion", "full_receipt_completion"}:
        return CAP_FULL

    # Typed audit stage names
    if "worker" in phase:
        if registration and "audit_limits" in registration:
            lim = registration["audit_limits"].get("worker_output_tokens")
            if isinstance(lim, int):
                return lim
        return CAP_DEFAULT_TYPED
    if "omission" in phase:
        if registration and "audit_limits" in registration:
            lim = registration["audit_limits"].get("omission_output_tokens")
            if isinstance(lim, int):
                return lim
        return CAP_DEFAULT_TYPED
    if "integration" in phase:
        if registration and "audit_limits" in registration:
            lim = registration["audit_limits"].get("integration_output_tokens")
            if isinstance(lim, int):
                return lim
        return CAP_DEFAULT_TYPED

    return CAP_DEFAULT_ORDINARY


def resolve_pending_input_bound(
    phase: str,
    project: str | None = None,
    *,
    ledger_data: Mapping[str, Any] | None = None,
    custom_bounds: Mapping[str, Any] | None = None,
    metadata_dir: Path | None = None,
) -> tuple[Any, str]:
    """Resolve the input bound and source attribution for a pending phase call.

    Returns:
        (bound, source_description) where bound is None if unresolved.
    """
    # 1. Custom bounds supplied by caller take first precedence
    if custom_bounds:
        if project and project in custom_bounds and isinstance(custom_bounds[project], Mapping):
            if phase in custom_bounds[project]:
                return custom_bounds[project][phase], f"custom_bounds[{project}][{phase}]"
        if phase in custom_bounds:
            return custom_bounds[phase], f"custom_bounds[{phase}]"

    # 2. Receipt completion: inspect saved context
    if phase in {"receipt_completion", "full_receipt_completion"}:
        if ledger_data:
            rc_state = ledger_data.get("receipt_completion")
            if isinstance(rc_state, Mapping):
                context_data = extract_saved_snapshot(rc_state.get("context"))
                if context_data and isinstance(context_data.get("input_tokens"), int):
                    return context_data["input_tokens"], "receipt_completion_context.json"
        # Search metadata_dir if available
        if metadata_dir and metadata_dir.is_dir():
            for p in metadata_dir.glob("*receipt_completion_context*.json"):
                data = extract_saved_snapshot(p)
                if data and isinstance(data.get("input_tokens"), int):
                    return data["input_tokens"], p.name

    # 3. Typed audit stages: inspect saved stage context
    if "typed_audit" in phase or phase in {"typed_audit_worker", "typed_audit_omission", "typed_audit_integration"}:
        if ledger_data:
            ta_state = ledger_data.get("typed_audit")
            if isinstance(ta_state, Mapping) and "stages" in ta_state:
                stages = ta_state.get("stages", [])
                if stages and isinstance(stages[-1], Mapping):
                    context_data = extract_saved_snapshot(stages[-1].get("context"))
                    if context_data and isinstance(context_data.get("input_tokens"), int):
                        return context_data["input_tokens"], "typed_audit_stage_context.json"
        if metadata_dir and metadata_dir.is_dir():
            candidates = sorted(metadata_dir.glob("*typed_audit*context*.json"))
            if candidates:
                data = extract_saved_snapshot(candidates[-1])
                if data and isinstance(data.get("input_tokens"), int):
                    return data["input_tokens"], candidates[-1].name

    # 4. Project-specific empirical baseline bounds
    if project and project in PROJECT_BASELINE_INPUT_BOUNDS:
        proj_bounds = PROJECT_BASELINE_INPUT_BOUNDS[project]
        if phase in proj_bounds:
            return proj_bounds[phase], f"baseline[{project}][{phase}]"

    # 5. Unresolved input bound: return None so caller fails closed rather than pricing as $0.00
    return None, "unknown"


def price_pending_call(
    pending: Mapping[str, Any],
    *,
    project: str | None = None,
    ledger_data: Mapping[str, Any] | None = None,
    custom_bounds: Mapping[str, Any] | None = None,
    registration: Mapping[str, Any] | None = None,
    metadata_dir: Path | None = None,
    worst_case_cache: bool = False,
) -> dict[str, Any]:
    """Calculate worst-case cost breakdown for an in-flight pending call."""
    phase = str(pending.get("phase") or "unknown")
    attempt = pending.get("attempt") or 1
    started_at = pending.get("started_at")
    usage_id = pending.get("usage_id")

    # Look for saved request payload if available
    saved_request = None
    if phase in {"receipt_completion", "full_receipt_completion"} and ledger_data:
        rc_state = ledger_data.get("receipt_completion")
        if isinstance(rc_state, Mapping):
            saved_request = extract_saved_snapshot(rc_state.get("request"))
    elif "typed_audit" in phase and ledger_data:
        ta_state = ledger_data.get("typed_audit")
        if isinstance(ta_state, Mapping) and "stages" in ta_state:
            stages = ta_state.get("stages", [])
            if stages and isinstance(stages[-1], Mapping):
                saved_request = extract_saved_snapshot(stages[-1].get("request"))

    output_cap = get_phase_output_cap(phase, saved_request=saved_request, registration=registration)
    output_cost = output_cap * RATE_OUTPUT

    input_bound, input_source = resolve_pending_input_bound(
        phase,
        project=project,
        ledger_data=ledger_data,
        custom_bounds=custom_bounds,
        metadata_dir=metadata_dir,
    )
    if input_bound is None:
        input_bound_unknown = True
        input_cost: float | None = None
        total_pending_worst_case: float | None = None
    else:
        input_bound_unknown = False
        input_cost = price_input_bound(input_bound, worst_case_cache=worst_case_cache)
        total_pending_worst_case = output_cost + input_cost

    return {
        "phase": phase,
        "attempt": attempt,
        "started_at": started_at,
        "usage_id": usage_id,
        "output_cap_tokens": output_cap,
        "output_worst_case_dollars": output_cost,
        "input_bound": input_bound,
        "input_bound_source": input_source,
        "input_bound_unknown": input_bound_unknown,
        "input_worst_case_dollars": input_cost,
        "pending_worst_case_dollars": total_pending_worst_case,
    }


def compute_readout(
    ledger_source: Mapping[str, Any] | str | Path,
    *,
    cap: float | None = None,
    trigger: float | None = None,
    project: str | None = None,
    custom_bounds: Mapping[str, Any] | None = None,
    registration: Mapping[str, Any] | None = None,
    worst_case_cache: bool = False,
) -> dict[str, Any]:
    """Compute the complete live dollar readout for an API run ledger."""
    metadata_dir = None
    if isinstance(ledger_source, (str, Path)):
        path = Path(ledger_source)
        if not path.is_file():
            raise FileNotFoundError(f"Ledger file not found: {path}")
        metadata_dir = path.parent
        ledger_data = json.loads(path.read_text(encoding="utf-8"))
        ledger_file_str = str(path)
    else:
        ledger_data = dict(ledger_source)
        ledger_file_str = None

    identity = ledger_data.get("identity") or {}
    resolved_project = project or identity.get("project")
    label = identity.get("label")
    method = identity.get("method")
    condition = identity.get("condition")

    rows = ledger_data.get("rows") or []
    settled_cost = price_settled_rows(rows)
    settled_call_count = len(rows)

    pending_raw = ledger_data.get("pending_call")
    pending_info = None
    pending_worst_case: float | None = 0.0
    pending_unknown = False

    if pending_raw and isinstance(pending_raw, Mapping) and pending_raw.get("phase"):
        pending_info = price_pending_call(
            pending_raw,
            project=resolved_project,
            ledger_data=ledger_data,
            custom_bounds=custom_bounds,
            registration=registration,
            metadata_dir=metadata_dir,
            worst_case_cache=worst_case_cache,
        )
        pending_unknown = bool(pending_info.get("input_bound_unknown"))
        pending_worst_case = pending_info["pending_worst_case_dollars"]

    if pending_unknown or pending_worst_case is None:
        total_projected_worst_case: float | None = None
        headroom = None
        # Fail closed when pending input bound is unknown and a trigger or cap is active
        trigger_reached = trigger is not None or (settled_cost >= trigger if trigger is not None else False)
        cap_reached = cap is not None or (settled_cost >= cap if cap is not None else False)
    else:
        total_projected_worst_case = settled_cost + pending_worst_case
        headroom = (cap - total_projected_worst_case) if cap is not None else None
        trigger_reached = bool(trigger is not None and total_projected_worst_case >= trigger)
        cap_reached = bool(cap is not None and total_projected_worst_case >= cap)

    return {
        "ledger_file": ledger_file_str,
        "identity": {
            "project": resolved_project,
            "label": label,
            "method": method,
            "condition": condition,
        },
        "settled_calls": settled_call_count,
        "settled_dollars": settled_cost,
        "has_pending_call": pending_info is not None,
        "pending_input_bound_unknown": pending_unknown,
        "pending_call": pending_info,
        "total_projected_dollars": total_projected_worst_case,
        "cap_dollars": cap,
        "remaining_headroom_dollars": headroom,
        "trigger_dollars": trigger,
        "trigger_reached": trigger_reached,
        "cap_reached": cap_reached,
    }


def format_readout(summary: Mapping[str, Any]) -> str:
    """Format readout summary dict into human-readable operator display."""
    lines = []
    ident = summary.get("identity") or {}
    proj = ident.get("project") or "unknown"
    lbl = ident.get("label") or "unknown"

    lines.append(f"=== Live Dollar Readout: {proj} ({lbl}) ===")
    if summary.get("ledger_file"):
        lines.append(f"Ledger: {summary['ledger_file']}")

    settled_dollars = summary["settled_dollars"]
    lines.append(f"Settled calls: {summary['settled_calls']:3d} | Spent: ${settled_dollars:10.8f}")

    if summary.get("has_pending_call"):
        p = summary["pending_call"]
        if p.get("input_bound_unknown"):
            lines.append(
                f"Pending call : phase={p['phase']} (attempt {p['attempt']}) | "
                f"cap={p['output_cap_tokens']:,} tokens (${p['output_worst_case_dollars']:.4f}) | "
                f"input_est=UNKNOWN | worst_case=UNKNOWN"
            )
        else:
            lines.append(
                f"Pending call : phase={p['phase']} (attempt {p['attempt']}) | "
                f"cap={p['output_cap_tokens']:,} tokens (${p['output_worst_case_dollars']:.4f}) | "
                f"input_est=${p['input_worst_case_dollars']:.4f} | "
                f"worst_case=+${p['pending_worst_case_dollars']:.4f}"
            )
    else:
        lines.append("Pending call : (none in-flight)")

    total = summary.get("total_projected_dollars")
    if total is None:
        lines.append("Total worst-case: UNKNOWN (unresolved pending input bound)")
    else:
        lines.append(f"Total worst-case: ${total:10.8f}")

    cap = summary.get("cap_dollars")
    trigger = summary.get("trigger_dollars")
    headroom = summary.get("remaining_headroom_dollars")

    if cap is not None:
        if headroom is None:
            lines.append(f"Cap: ${cap:.2f} | Remaining headroom: UNKNOWN")
        else:
            lines.append(f"Cap: ${cap:.2f} | Remaining headroom: ${headroom:.4f}")
    if trigger is not None:
        lines.append(f"Operator stop trigger: ${trigger:.2f}")

    if summary.get("cap_reached"):
        lines.append(">>> ALERT: CAP EXCEEDED! Run 'd4d api stop --label-prefix <prefix>' immediately! <<<")
    elif summary.get("trigger_reached"):
        lines.append(">>> ALERT: TRIGGER REACHED! Projected worst-case meets or exceeds operator stop trigger! <<<")

    return "\n".join(lines)
