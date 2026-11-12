#!/usr/bin/env python3
"""Compute the freshness value table from the three retained native diagnostics.

Purpose:
  Read the retained phase-metrics, diagnostic, host-load, and outer-summary JSON
  artifacts for the three completed native CPU-monitoring diagnostics
  (sources 458887766eff, 3cc113e2606c, and 382f0dfd1ce8 under
  d4d-executions/scratch-native-u1u3/u3m/), compute for each run:
    1. Capture time, launch start, and the gap between them.
    2. Every freshness check reached in order (kind, capture age, outcome).
    3. Fixture and launch phase process CPU and wall time.
    4. The smallest max_age_seconds at which the run would have passed every
       check it reached with the 90 s pre-reservation margin unchanged.
    5. The 1-minute load per CPU at the start and the highest during the run.
  Print the Markdown table to stdout and write the structured JSON deliverable.

Inputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-458887766eff-cpu-monitoring-post-5834-20261111/phase-metrics/34474-diagnostic.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-458887766eff-cpu-monitoring-post-5834-20261111/phase-metrics/34474-measurement.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-458887766eff-cpu-monitoring-post-5834-20261111/host-load.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-458887766eff-cpu-monitoring-post-5834-20261111.outer.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111/phase-metrics/7351-diagnostic.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111/phase-metrics/7351-measurement.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111/host-load.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111.outer.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111/phase-metrics/67941-diagnostic.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111/phase-metrics/67941-measurement.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111/host-load.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111.outer.json

Outputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy4-freshness-value-table-20261112.json
  - Markdown table printed to standard output.

Assignment:
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy4-freshness-value-table-20261112.md

Date:
  2026-11-12
"""

from __future__ import annotations

from datetime import datetime
import json
import math
from pathlib import Path
from typing import Any


U3M_ROOT = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m"
)
WORKTREE_ROOT = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111"
)
JSON_OUT = (
    WORKTREE_ROOT
    / "notes/development_efficiency_20261111/handoffs/agy4-freshness-value-table-20261112.json"
)

PRE_RESERVATION_MARGIN_SECONDS = 90

RUN_SPECS = [
    {
        "source_short": "458887766eff",
        "run_dir_name": "wp1-458887766eff-cpu-monitoring-post-5834-20261111",
        "pid": 34474,
    },
    {
        "source_short": "3cc113e2606c",
        "run_dir_name": "wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111",
        "pid": 7351,
    },
    {
        "source_short": "382f0dfd1ce8",
        "run_dir_name": "wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111",
        "pid": 67941,
    },
]


def parse_utc(stamp: str) -> datetime:
    if stamp.endswith("Z"):
        stamp = stamp[:-1] + "+00:00"
    return datetime.fromisoformat(stamp)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def find_enclosing_context(calls: list[dict[str, Any]], target_idx: int) -> str:
    target = calls[target_idx]
    t_start = target["entered_wall"]
    t_end = t_start + target["inclusive_wall"]
    enclosing: list[str] = []
    for idx, c in enumerate(calls):
        if idx == target_idx or c["phase"] != target["phase"]:
            continue
        c_start = c["entered_wall"]
        c_end = c_start + c["inclusive_wall"]
        if c_start <= t_start and c_end >= t_end:
            enclosing.append(f"{c['label']}({c['name']})")
    if not enclosing:
        return target["phase"]
    return enclosing[-1]


def extract_run(spec: dict[str, Any]) -> dict[str, Any]:
    run_dir = U3M_ROOT / spec["run_dir_name"]
    pid = spec["pid"]
    diag_path = run_dir / "phase-metrics" / f"{pid}-diagnostic.json"
    meas_path = run_dir / "phase-metrics" / f"{pid}-measurement.json"
    host_load_path = run_dir / "host-load.json"
    outer_path = U3M_ROOT / f"{spec['run_dir_name']}.outer.json"

    diag = load_json(diag_path)
    meas = load_json(meas_path)
    host_load = load_json(host_load_path)
    outer = load_json(outer_path)

    captured_at = diag["capture_timestamp"]
    captured_dt = parse_utc(captured_at)

    phases_by_name = {p["name"]: p for p in meas["phases"]}
    fixture_phase = phases_by_name["fixture"]
    launch_phase = phases_by_name["launch"]

    launch_start_utc = launch_phase["before"]["utc"]
    launch_start_dt = parse_utc(launch_start_utc)
    gap_seconds = round((launch_start_dt - captured_dt).total_seconds(), 6)

    calls = meas["calls"]

    checks: list[dict[str, Any]] = []
    reservation_passed = False
    for idx, c in enumerate(calls):
        label = c["label"]
        if label not in ("freshness_before_dispatch", "freshness_before_reservation"):
            continue
        if label == "freshness_before_reservation":
            kind = "pre-reservation"
            margin_applied = PRE_RESERVATION_MARGIN_SECONDS
        elif reservation_passed:
            kind = "dispatch"
            margin_applied = 0
        else:
            kind = "dispatch check only"
            margin_applied = 0

        entered_dt = parse_utc(c["entered_utc"])
        left_dt = parse_utc(c["left_utc"])
        age_entered = round((entered_dt - captured_dt).total_seconds(), 6)
        age_left = round((left_dt - captured_dt).total_seconds(), 6)

        inner_row = calls[idx + 1] if idx + 1 < len(calls) else None
        inner_fresh: dict[str, Any] | None = None
        if inner_row and inner_row.get("label") == "freshness_check":
            inner_entered = round(
                (parse_utc(inner_row["entered_utc"]) - captured_dt).total_seconds(), 6
            )
            inner_left = round(
                (parse_utc(inner_row["left_utc"]) - captured_dt).total_seconds(), 6
            )
            inner_fresh = {
                "call_index": idx + 1,
                "label": inner_row["label"],
                "name": inner_row["name"],
                "entered_utc": inner_row["entered_utc"],
                "left_utc": inner_row["left_utc"],
                "capture_age_entered_seconds": inner_entered,
                "capture_age_left_seconds": inner_left,
                "outcome": inner_row["outcome"],
            }

        req_entered_continuous = round(age_entered + margin_applied, 6)
        req_left_continuous = round(age_left + margin_applied, 6)
        req_int_entered = int(math.ceil(req_entered_continuous))
        req_int_left = int(math.ceil(req_left_continuous))
        assert req_int_entered == req_int_left, (
            f"Integer ceiling mismatch across check boundary: {req_int_entered} vs {req_int_left}"
        )

        enclosing = find_enclosing_context(calls, idx)

        checks.append(
            {
                "check_order": len(checks) + 1,
                "call_index": idx,
                "phase": c["phase"],
                "enclosing_call": enclosing,
                "label": label,
                "name": c["name"],
                "kind": kind,
                "entered_utc": c["entered_utc"],
                "left_utc": c["left_utc"],
                "capture_age_entered_seconds": age_entered,
                "capture_age_left_seconds": age_left,
                "outcome": c["outcome"],
                "margin_seconds_required_at_check": margin_applied,
                "min_max_age_continuous_entered_seconds": req_entered_continuous,
                "min_max_age_continuous_left_seconds": req_left_continuous,
                "min_max_age_seconds_int": req_int_left,
                "inner_fresh_row": inner_fresh,
            }
        )

        if label == "freshness_before_reservation" and c["outcome"] == "return":
            reservation_passed = True

    reached_pre_reservation = any(c["kind"] == "pre-reservation" for c in checks)
    reached_dispatch = any(c["kind"] == "dispatch" for c in checks)
    last_check = checks[-1]

    smallest_passing_int = max(c["min_max_age_seconds_int"] for c in checks)
    smallest_passing_continuous_entered = max(
        c["min_max_age_continuous_entered_seconds"] for c in checks
    )
    smallest_passing_continuous_left = max(
        c["min_max_age_continuous_left_seconds"] for c in checks
    )
    smallest_passing_fresh_only_int = max(
        int(math.ceil(c["capture_age_left_seconds"])) for c in checks
    )

    if not reached_pre_reservation:
        refusal_note = (
            f"Refused at check #{last_check['check_order']} ({last_check['kind']} in "
            f"{last_check['enclosing_call']}); pre-reservation age is unknown "
            "because the run never reached before_reservation()."
        )
    else:
        refusal_note = (
            f"Reached before_reservation() at check #{last_check['check_order']} "
            f"(capture age {last_check['capture_age_entered_seconds']:.6f} s entered / "
            f"{last_check['capture_age_left_seconds']:.6f} s left) and was refused there; "
            f"requires max_age_seconds >= {smallest_passing_int} s "
            f"(>= {smallest_passing_continuous_entered:.6f} s entered / "
            f"{smallest_passing_continuous_left:.6f} s left) with the "
            f"{PRE_RESERVATION_MARGIN_SECONDS} s pre-reservation margin unchanged "
            f"(_fresh() alone without the {PRE_RESERVATION_MARGIN_SECONDS} s margin would "
            f"require {smallest_passing_fresh_only_int} s); post-reservation dispatch age "
            "is unknown because the run was refused at before_reservation()."
        )

    logical_cpus = int(host_load["before"]["logical_cpus"])
    start_load1 = round(float(host_load["before"]["load"][0]), 6)
    start_load1_per_cpu = round(float(host_load["before"]["load"][0]) / logical_cpus, 6)
    after_load1 = round(float(host_load["after"]["load"][0]), 6)
    after_load1_per_cpu = round(float(host_load["after"]["load"][0]) / logical_cpus, 6)
    max_load1_per_cpu = round(
        float(outer["host_contention"]["max_one_minute_load_per_cpu"]), 6
    )
    load_samples = int(outer["host_contention"]["samples"])

    fixture_cpu = round(float(fixture_phase["elapsed"]["process_cpu"]), 6)
    fixture_wall = round(float(fixture_phase["elapsed"]["wall_monotonic"]), 6)
    launch_cpu = round(float(launch_phase["elapsed"]["process_cpu"]), 6)
    launch_wall = round(float(launch_phase["elapsed"]["wall_monotonic"]), 6)

    return {
        "source_short": spec["source_short"],
        "source_commit": outer["source_commit"],
        "run_directory": str(run_dir),
        "diagnostic_json": str(diag_path),
        "measurement_json": str(meas_path),
        "host_load_json": str(host_load_path),
        "outer_json": str(outer_path),
        "pid": pid,
        "captured_at": captured_at,
        "launch_start_utc": launch_start_utc,
        "capture_to_launch_gap_seconds": gap_seconds,
        "freshness_checks_reached": checks,
        "phases": {
            "fixture": {
                "process_cpu_seconds": fixture_cpu,
                "wall_monotonic_seconds": fixture_wall,
            },
            "launch": {
                "process_cpu_seconds": launch_cpu,
                "wall_monotonic_seconds": launch_wall,
            },
        },
        "freshness_threshold_analysis": {
            "configured_max_age_seconds": diag["capture_age_limit_seconds"],
            "configured_pre_reservation_margin_seconds": diag["capture_margin_seconds"],
            "reached_pre_reservation": reached_pre_reservation,
            "reached_post_reservation_dispatch": reached_dispatch,
            "refused_at_check_order": last_check["check_order"],
            "refused_at_check_kind": last_check["kind"],
            "refused_at_enclosing_call": last_check["enclosing_call"],
            "pre_reservation_age_entered_seconds": (
                last_check["capture_age_entered_seconds"]
                if reached_pre_reservation
                else None
            ),
            "pre_reservation_age_left_seconds": (
                last_check["capture_age_left_seconds"]
                if reached_pre_reservation
                else None
            ),
            "pre_reservation_age_status": (
                "measured"
                if reached_pre_reservation
                else "unknown (never reached before_reservation)"
            ),
            "smallest_passing_max_age_seconds_with_90s_margin": smallest_passing_int,
            "smallest_passing_max_age_continuous_entered_seconds_with_90s_margin": (
                smallest_passing_continuous_entered
            ),
            "smallest_passing_max_age_continuous_left_seconds_with_90s_margin": (
                smallest_passing_continuous_left
            ),
            "smallest_passing_max_age_seconds_fresh_only_without_margin": (
                smallest_passing_fresh_only_int
            ),
            "note": refusal_note,
        },
        "host_load_one_minute_per_cpu": {
            "logical_cpus": logical_cpus,
            "start_load1_raw": start_load1,
            "start_load1_per_cpu": start_load1_per_cpu,
            "max_during_run_load1_per_cpu": max_load1_per_cpu,
            "during_run_samples": load_samples,
            "after_load1_raw": after_load1,
            "after_load1_per_cpu": after_load1_per_cpu,
        },
    }


def format_checks_cell(checks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for c in checks:
        parts.append(
            f"{c['check_order']}. {c['kind']} ({c['phase']}/{c['enclosing_call']}, "
            f"call {c['call_index']}): age {c['capture_age_entered_seconds']:.6f} s entered / "
            f"{c['capture_age_left_seconds']:.6f} s left -> {c['outcome']}"
        )
    return "<br>".join(parts)


def render_markdown_table(runs: list[dict[str, Any]]) -> str:
    headers = [
        "Source commit / Run",
        "1. Capture time, launch start, and gap",
        "2. Freshness checks reached (in order: kind, capture age, outcome)",
        "3. Fixture and launch process CPU and wall time",
        "4. Smallest max_age_seconds to pass reached checks (90 s margin unchanged)",
        "5. 1-min load per CPU (start / max during run)",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|---|---|---|---|---|---|",
    ]
    for r in runs:
        col0 = (
            f"{r['source_short']} ({r['source_commit']})<br>"
            f"PID {r['pid']}"
        )
        col1 = (
            f"Capture: {r['captured_at']}<br>"
            f"Launch start: {r['launch_start_utc']}<br>"
            f"Gap: {r['capture_to_launch_gap_seconds']:.6f} s"
        )
        col2 = format_checks_cell(r["freshness_checks_reached"])
        fix = r["phases"]["fixture"]
        lch = r["phases"]["launch"]
        col3 = (
            f"Fixture: CPU {fix['process_cpu_seconds']:.6f} s, "
            f"wall {fix['wall_monotonic_seconds']:.6f} s<br>"
            f"Launch: CPU {lch['process_cpu_seconds']:.6f} s, "
            f"wall {lch['wall_monotonic_seconds']:.6f} s"
        )
        fta = r["freshness_threshold_analysis"]
        col4 = (
            f"**{fta['smallest_passing_max_age_seconds_with_90s_margin']} s** "
            f"(continuous >= {fta['smallest_passing_max_age_continuous_entered_seconds_with_90s_margin']:.6f} s entered / "
            f">= {fta['smallest_passing_max_age_continuous_left_seconds_with_90s_margin']:.6f} s left). "
            f"{fta['note']}"
        )
        hl = r["host_load_one_minute_per_cpu"]
        col5 = (
            f"Start: {hl['start_load1_per_cpu']:.6f} "
            f"({hl['start_load1_raw']:.6f} / {hl['logical_cpus']} CPUs)<br>"
            f"Max during run: {hl['max_during_run_load1_per_cpu']:.6f} "
            f"({hl['during_run_samples']} samples)"
        )
        lines.append("| " + " | ".join([col0, col1, col2, col3, col4, col5]) + " |")
    return "\n".join(lines)


def build_production_steps_inventory() -> list[dict[str, Any]]:
    return [
        {
            "step_order": 1,
            "step": "Timestamping captured_at on the rate_limit_event line during capture-subscription-event",
            "measured": "yes (timestamp boundary); no (live child process execution before rate_limit_event)",
            "production_source_ref": "382f0dfd1ce8:src/data_sheets_schema/native_subscription_capture.py lines 202-245 (_supervise spawns the registered native executable and records captured_at = _utc() when a rate_limit_event stdout line is read at lines 241-245)",
            "diagnostic_source_ref": "382f0dfd1ce8:tests/utils/native_synthetic_evidence.py lines 144-163 (authority_for sets capture_now = datetime.now(timezone.utc) and capture_stamp at lines 144-145 and builds synthetic observations with captured_at = capture_stamp at lines 162-163)",
        },
        {
            "step_order": 2,
            "step": "Remaining capture subprocess execution through terminal result line and process-group cleanup (_cleanup) inside _supervise()",
            "measured": "no",
            "production_source_ref": "382f0dfd1ce8:src/data_sheets_schema/native_subscription_capture.py lines 186-199 (_cleanup) and lines 218-270 (_supervise drains stdout/stderr through process exit and reaps the process group)",
            "diagnostic_source_ref": "382f0dfd1ce8:tests/utils/native_synthetic_evidence.py lines 150-163 (authority_for constructs the 3-line stdout byte string in memory without spawning a process)",
        },
        {
            "step_order": 3,
            "step": "Post-supervise capture authority recheck (_authority), terminal modelUsage limits check (_observed_limits_mismatch and _terminal), durable file creation (_new with os.fsync and _sync), and capture-subscription-event CLI exit",
            "measured": "yes (for _event, _terminal, and writing stdout.jsonl, stderr.txt, observations.json, and capture.json via Path.write_bytes); no (for the post-supervise _authority reconstruction at line 548, _observed_limits_mismatch scan, _new/_sync os.fsync calls, and CLI _unchanged/_emit)",
            "production_source_ref": "382f0dfd1ce8:src/data_sheets_schema/native_subscription_capture.py lines 547-587 (_perform_capture) and 382f0dfd1ce8:src/data_sheets_schema/native_generation.py lines 233-235, 248",
            "diagnostic_source_ref": "382f0dfd1ce8:tests/utils/native_synthetic_evidence.py lines 164-175 (authority_for calls capture._event and capture._terminal and writes the 4 files via Path.write_bytes without re-running _authority or os.fsync)",
        },
        {
            "step_order": 4,
            "step": "Operator/shell turnaround between capture-subscription-event and prepare-subscription-guard-v2, plus prepare-subscription-guard-v2 CLI startup and front-door verification (registration.verified, validate_metadata, require_u4_runtime, _account_choice, validate_prepared_runtime, review.validate_bundle, _unchanged)",
            "measured": "no",
            "production_source_ref": "382f0dfd1ce8:src/data_sheets_schema/native_generation.py lines 125-128, 153, 206-228, and 236 (separate CLI command runs registration.verified at line 209, validate_metadata at line 213, require_u4_runtime at line 214, _account_choice at line 215, validate_prepared_runtime at line 223, and review.validate_bundle at line 225 before read_capture)",
            "diagnostic_source_ref": "382f0dfd1ce8:tests/utils/native_synthetic_evidence.py lines 174-178 (authority_for calls capture.read_capture in-process immediately on line 176 after writing capture.json on line 175)",
        },
        {
            "step_order": 5,
            "step": "Saved capture readback (capture.read_capture) and guard v2 preparation (guard_v2.prepare_guard, including freshness check #1 SubscriptionGuard.__init__ -> before_dispatch(check_only=True))",
            "measured": "yes (for capture.read_capture, guard.prepare_guard, and Path.write_bytes in the fixture phase); no (for CLI _unchanged, _new_file os.fsync, and _emit at native_generation.py lines 245-248)",
            "production_source_ref": "382f0dfd1ce8:src/data_sheets_schema/native_generation.py lines 237-248; 382f0dfd1ce8:src/data_sheets_schema/native_subscription_capture.py lines 685-701 (read_capture); 382f0dfd1ce8:src/data_sheets_schema/native_subscription_guard_v2.py lines 383-399 and 677-704 (prepare_guard)",
            "diagnostic_source_ref": "382f0dfd1ce8:tests/utils/native_synthetic_evidence.py lines 176-190 (executed inside make_case during the fixture phase at 382f0dfd1ce8:tests/test_native_u3k_profile.py lines 208-209, producing the 16.434488 s, 23.950053 s, and 10.802291 s capture-to-launch gaps)",
        },
        {
            "step_order": 6,
            "step": "Operator/shell turnaround between prepare-subscription-guard-v2 exit and launch CLI invocation, plus launch CLI Python interpreter startup and module imports",
            "measured": "no",
            "production_source_ref": "382f0dfd1ce8:src/data_sheets_schema/native_generation.py lines 1-24, 129-141, 153, and 274-275",
            "diagnostic_source_ref": "382f0dfd1ce8:tests/test_native_u3k_profile.py lines 208-248 (launch phase starts in-process immediately after fixture phase completes)",
        },
        {
            "step_order": 7,
            "step": "native_generation.py launch CLI front-door verification before native_shared_execution_orchestration.launch() is called (registration.verified, validate_metadata, require_u4_runtime, _account_choice, _unchanged)",
            "measured": "no",
            "production_source_ref": "382f0dfd1ce8:src/data_sheets_schema/native_generation.py lines 206-217 and 259-265 (main runs registration.verified at line 209, validate_metadata at line 213, require_u4_runtime at line 214, _account_choice at line 215, and _unchanged at line 261 before calling native_shared_execution_orchestration.launch at line 262)",
            "diagnostic_source_ref": "382f0dfd1ce8:tests/test_native_u3k_profile.py line 248 (test_neutral_pre_reservation_diagnostic calls execute.synthetic_launch directly, bypassing native_generation.main)",
        },
        {
            "step_order": 8,
            "step": "Orchestration launch execution from native_shared_execution_orchestration.launch() / synthetic_launch() through launch_guard.before_reservation()",
            "measured": "yes",
            "production_source_ref": "382f0dfd1ce8:src/data_sheets_schema/native_shared_execution_orchestration.py lines 70-95 (launch); 382f0dfd1ce8:src/data_sheets_schema/native_execution_orchestration.py lines 253-276 (launch) and lines 315-385 (_launch through launch_guard.before_reservation())",
            "diagnostic_source_ref": "382f0dfd1ce8:src/data_sheets_schema/native_shared_execution_orchestration.py lines 97-129 (synthetic_launch); 382f0dfd1ce8:src/data_sheets_schema/native_execution_orchestration.py lines 278-296 (synthetic_launch) and lines 315-385 (_launch through launch_guard.before_reservation(), measured in phases[1] launch)",
        },
    ]


def main() -> None:
    runs = [extract_run(spec) for spec in RUN_SPECS]
    table_md = render_markdown_table(runs)
    steps_inventory = build_production_steps_inventory()

    payload = {
        "date": "2026-11-12",
        "assignment": str(
            WORKTREE_ROOT
            / "notes/development_efficiency_20261111/assignments/claude-lead-agy4-freshness-value-table-20261112.md"
        ),
        "script": str(
            WORKTREE_ROOT / "scripts/adhoc/native_freshness_value_table_20261112.py"
        ),
        "pre_reservation_margin_seconds": PRE_RESERVATION_MARGIN_SECONDS,
        "runs": runs,
        "production_steps_between_capture_and_launch_at_382f0dfd1ce8": steps_inventory,
        "markdown_table": table_md,
    }

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(table_md)


if __name__ == "__main__":
    main()
