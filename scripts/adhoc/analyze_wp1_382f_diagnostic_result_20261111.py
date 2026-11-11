#!/usr/bin/env python3
"""Read-only analysis of the completed D132 382f0dfd1ce8 cpu-monitoring diagnostic run.

Purpose:
  Extract and compute all phase metrics, per-function call/CPU tables,
  cross-run launch-phase comparisons (3cc113e2606c, 458887766eff, 382f0dfd1ce8),
  Stage A (through accept_saved_capture) vs Stage B (post-acceptance through
  before_reservation) decomposition, call-tree / unmonitored-gap breakdowns, and
  capture-to-reservation freshness arithmetic from the retained WP1 diagnostic JSON records.

Inputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111{,.outer.json,.supervisor.json}
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-458887766eff-cpu-monitoring-post-5834-20261111{,.outer.json,.supervisor.json}
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111{,.outer.json,.supervisor.json}
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111{,.outer.json,.supervisor.json}

Outputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/diagnostic-result-20261111/result-analysis.json

Serves:
  Claude lead assignment claude-lead-agy4-diagnostic-result-analysis.md (owner decision D132).

Date: 2026-11-11
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any


EXEC_ROOT = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions")
SCRATCH_U3M = EXEC_ROOT / "scratch-native-u1u3/u3m"
EFFICIENCY_ROOT = EXEC_ROOT / "codex-development-efficiency-20261111"
OUT_DIR = EFFICIENCY_ROOT / "tmp/diagnostic-result-20261111"
OUT_JSON = OUT_DIR / "result-analysis.json"


RUN_SPECS = {
    "3cc113e2606c": {
        "short_commit": "3cc113e2606c",
        "dir": SCRATCH_U3M / "wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111",
    },
    "458887766eff": {
        "short_commit": "458887766eff",
        "dir": SCRATCH_U3M / "wp1-458887766eff-cpu-monitoring-post-5834-20261111",
    },
    "382f0dfd1ce8_rerun": {
        "short_commit": "382f0dfd1ce8",
        "dir": SCRATCH_U3M / "wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111",
    },
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def parse_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def summarize_phase(phase: dict[str, Any]) -> dict[str, Any]:
    el = phase["elapsed"]
    reaped_user = el["reaped_child_user_cpu"]
    reaped_sys = el["reaped_child_system_cpu"]
    reaped_total = reaped_user + reaped_sys
    self_user = el["self_user_cpu"]
    self_sys = el["self_system_cpu"]
    self_total = self_user + self_sys
    first_row = phase["first_call_row"]
    last_row = phase["last_call_row_exclusive"]
    return {
        "name": phase["name"],
        "outcome": phase["outcome"],
        "error": phase["error"],
        "profiled": phase["profiled"],
        "before_utc": phase["before"]["utc"],
        "after_utc": phase["after"]["utc"],
        "before_wall_monotonic": phase["before"]["wall_monotonic"],
        "after_wall_monotonic": phase["after"]["wall_monotonic"],
        "first_call_row": first_row,
        "last_call_row_exclusive": last_row,
        "call_row_count": last_row - first_row,
        "elapsed": {
            "process_cpu": el["process_cpu"],
            "thread_cpu": el["thread_cpu"],
            "wall_monotonic": el["wall_monotonic"],
            "self_user_cpu": self_user,
            "self_system_cpu": self_sys,
            "self_total_cpu": self_total,
            "reaped_child_user_cpu": reaped_user,
            "reaped_child_system_cpu": reaped_sys,
            "reaped_child_total_cpu": reaped_total,
            "self_plus_reaped_child_cpu": self_total + reaped_total,
        },
    }


def analyze_phase_calls(calls: list[dict[str, Any]], first_idx: int, last_idx: int) -> dict[str, Any]:
    slice_rows = calls[first_idx:last_idx]
    threads = sorted({r["thread"] for r in slice_rows})

    by_label: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for offset, row in enumerate(slice_rows):
        abs_idx = first_idx + offset
        by_label.setdefault(row["label"], []).append((abs_idx, row))

    label_summaries: dict[str, Any] = {}
    for label, indexed_rows in sorted(by_label.items()):
        intervals = []
        self_nested_count = 0
        for abs_idx, r in indexed_rows:
            start_w = r["entered_wall"]
            end_w = start_w + r["inclusive_wall"]
            for prev_s, prev_e in intervals:
                if start_w >= prev_s and end_w <= prev_e:
                    self_nested_count += 1
                    break
            intervals.append((start_w, end_w))

        inc_cpu = [r["inclusive_thread_cpu"] for _, r in indexed_rows]
        inc_wall = [r["inclusive_wall"] for _, r in indexed_rows]
        outcomes = {}
        names_seen = {}
        lines_seen = {}
        for _, r in indexed_rows:
            outcomes[r["outcome"]] = outcomes.get(r["outcome"], 0) + 1
            names_seen[r["name"]] = names_seen.get(r["name"], 0) + 1
            lines_seen[str(r["first_line"])] = lines_seen.get(str(r["first_line"]), 0) + 1

        sample_row = indexed_rows[0][1]
        short_file = Path(sample_row["file"]).name
        summary: dict[str, Any] = {
            "label": label,
            "file": short_file,
            "full_file": sample_row["file"],
            "name": sample_row["name"],
            "names_seen": names_seen,
            "first_line": sample_row["first_line"],
            "first_lines_seen": lines_seen,
            "count": len(indexed_rows),
            "outcomes": outcomes,
            "self_nested_calls": self_nested_count,
            "inclusive_thread_cpu_sum": sum(inc_cpu),
            "inclusive_thread_cpu_mean": sum(inc_cpu) / len(inc_cpu),
            "inclusive_thread_cpu_min": min(inc_cpu),
            "inclusive_thread_cpu_max": max(inc_cpu),
            "inclusive_wall_sum": sum(inc_wall),
            "inclusive_wall_mean": sum(inc_wall) / len(inc_wall),
            "inclusive_wall_min": min(inc_wall),
            "inclusive_wall_max": max(inc_wall),
            "has_coarse_elapsed": "coarse_elapsed" in sample_row,
        }
        if "coarse_elapsed" in sample_row:
            c_rows = [r["coarse_elapsed"] for _, r in indexed_rows if "coarse_elapsed" in r]
            summary["coarse_elapsed_sum"] = {
                "process_cpu": sum(c["process_cpu"] for c in c_rows),
                "thread_cpu": sum(c["thread_cpu"] for c in c_rows),
                "wall_monotonic": sum(c["wall_monotonic"] for c in c_rows),
                "self_user_cpu": sum(c["self_user_cpu"] for c in c_rows),
                "self_system_cpu": sum(c["self_system_cpu"] for c in c_rows),
                "reaped_child_user_cpu": sum(c["reaped_child_user_cpu"] for c in c_rows),
                "reaped_child_system_cpu": sum(c["reaped_child_system_cpu"] for c in c_rows),
                "reaped_child_total_cpu": sum(
                    c["reaped_child_user_cpu"] + c["reaped_child_system_cpu"] for c in c_rows
                ),
            }
            if len(c_rows) > 0:
                first_c = c_rows[0]
                summary["coarse_elapsed_first_call"] = {
                    "process_cpu": first_c["process_cpu"],
                    "thread_cpu": first_c["thread_cpu"],
                    "wall_monotonic": first_c["wall_monotonic"],
                    "self_user_cpu": first_c["self_user_cpu"],
                    "self_system_cpu": first_c["self_system_cpu"],
                    "reaped_child_user_cpu": first_c["reaped_child_user_cpu"],
                    "reaped_child_system_cpu": first_c["reaped_child_system_cpu"],
                    "reaped_child_total_cpu": (
                        first_c["reaped_child_user_cpu"] + first_c["reaped_child_system_cpu"]
                    ),
                }
        label_summaries[label] = summary

    # Reconstruct call tree inside this phase using interval containment
    n = len(slice_rows)
    parent_of: list[int | None] = [None] * n
    children_of: list[list[int]] = [[] for _ in range(n)]
    exits = [r["entered_wall"] + r["inclusive_wall"] for r in slice_rows]
    stack: list[int] = []
    for i, r in enumerate(slice_rows):
        start_w = r["entered_wall"]
        while stack and exits[stack[-1]] < start_w - 1e-7:
            stack.pop()
        if stack:
            parent_of[i] = stack[-1]
            children_of[stack[-1]].append(i)
        stack.append(i)

    exclusive_by_label: dict[str, dict[str, float]] = {}
    parent_child_edges: dict[str, dict[str, Any]] = {}
    major_calls_sequence: list[dict[str, Any]] = []
    for i, r in enumerate(slice_rows):
        lbl = r["label"]
        direct_children = children_of[i]
        children_cpu = sum(slice_rows[c]["inclusive_thread_cpu"] for c in direct_children)
        children_wall = sum(slice_rows[c]["inclusive_wall"] for c in direct_children)
        unmonitored_cpu = r["inclusive_thread_cpu"] - children_cpu
        unmonitored_wall = r["inclusive_wall"] - children_wall
        slot = exclusive_by_label.setdefault(
            lbl,
            {
                "count": 0.0,
                "inclusive_thread_cpu_sum": 0.0,
                "direct_monitored_children_thread_cpu_sum": 0.0,
                "unmonitored_self_thread_cpu_sum": 0.0,
                "inclusive_wall_sum": 0.0,
                "direct_monitored_children_wall_sum": 0.0,
                "unmonitored_self_wall_sum": 0.0,
            },
        )
        slot["count"] += 1
        slot["inclusive_thread_cpu_sum"] += r["inclusive_thread_cpu"]
        slot["direct_monitored_children_thread_cpu_sum"] += children_cpu
        slot["unmonitored_self_thread_cpu_sum"] += unmonitored_cpu
        slot["inclusive_wall_sum"] += r["inclusive_wall"]
        slot["direct_monitored_children_wall_sum"] += children_wall
        slot["unmonitored_self_wall_sum"] += unmonitored_wall

        parent_lbl = "<phase_root>" if parent_of[i] is None else slice_rows[parent_of[i]]["label"]
        edge_key = f"{parent_lbl} -> {lbl}"
        eslot = parent_child_edges.setdefault(
            edge_key,
            {
                "parent": parent_lbl,
                "child": lbl,
                "count": 0,
                "child_inclusive_thread_cpu_sum": 0.0,
                "child_inclusive_wall_sum": 0.0,
            },
        )
        eslot["count"] += 1
        eslot["child_inclusive_thread_cpu_sum"] += r["inclusive_thread_cpu"]
        eslot["child_inclusive_wall_sum"] += r["inclusive_wall"]

        if lbl in (
            "public_launch",
            "engine_entry",
            "launch_engine",
            "shared_registration_verified",
            "fresh_admission",
            "controller_prewarm",
            "accept_saved_capture",
            "freshness_before_dispatch",
            "freshness_before_reservation",
            "freshness_check",
        ):
            major_calls_sequence.append(
                {
                    "row_index": first_idx + i,
                    "parent_row_index": (first_idx + parent_of[i]) if parent_of[i] is not None else None,
                    "parent_label": parent_lbl,
                    "label": lbl,
                    "name": r["name"],
                    "file": Path(r["file"]).name,
                    "first_line": r["first_line"],
                    "outcome": r["outcome"],
                    "entered_utc": r["entered_utc"],
                    "left_utc": r.get("left_utc"),
                    "entered_wall": r["entered_wall"],
                    "inclusive_wall": r["inclusive_wall"],
                    "inclusive_thread_cpu": r["inclusive_thread_cpu"],
                    "unmonitored_self_thread_cpu": unmonitored_cpu,
                    "unmonitored_self_wall": unmonitored_wall,
                }
            )

    return {
        "row_count": n,
        "threads": threads,
        "by_label": label_summaries,
        "call_tree_decomposition_by_label": exclusive_by_label,
        "parent_child_edges": parent_child_edges,
        "major_calls_sequence": major_calls_sequence,
    }


def analyze_launch_stages(calls: list[dict[str, Any]], launch_phase: dict[str, Any]) -> dict[str, Any]:
    """Split launch into Stage A (through exit of accept_saved_capture) and Stage B (post-acceptance)."""
    first_idx = launch_phase["first_call_row"]
    last_idx = launch_phase["last_call_row_exclusive"]
    slice_rows = calls[first_idx:last_idx]

    # Find outer accept_saved_capture row (accept_current_selection) in launch
    accept_outer_offset = None
    for i, r in enumerate(slice_rows):
        if r["label"] == "accept_saved_capture" and r["name"] == "accept_current_selection":
            accept_outer_offset = i
            break
    assert accept_outer_offset is not None, "Expected accept_current_selection in launch"
    accept_row = slice_rows[accept_outer_offset]
    accept_end_wall = accept_row["entered_wall"] + accept_row["inclusive_wall"]

    # Find last row nested inside accept_current_selection (entered before accept_end_wall)
    stage_a_end_offset = accept_outer_offset + 1
    for i in range(accept_outer_offset + 1, len(slice_rows)):
        if slice_rows[i]["entered_wall"] <= accept_end_wall + 1e-7:
            stage_a_end_offset = i + 1
        else:
            break

    stage_a_rows = slice_rows[:stage_a_end_offset]
    stage_b_rows = slice_rows[stage_a_end_offset:]

    def count_by_label(rows: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in rows:
            counts[r["label"]] = counts.get(r["label"], 0) + 1
        return dict(sorted(counts.items()))

    launch_start_wall = launch_phase["before_wall_monotonic"]
    launch_end_wall = launch_phase["after_wall_monotonic"]
    stage_a_wall_s = accept_end_wall - launch_start_wall
    stage_b_wall_s = launch_end_wall - accept_end_wall

    # Sum top-level children inside Stage B (direct children of launch_engine after accept_saved_capture)
    # Using interval containment within stage_b_rows:
    b_top_cpu = 0.0
    b_top_wall = 0.0
    b_cur_end = -1.0
    b_top_calls = []
    for offset, r in enumerate(stage_b_rows):
        abs_idx = first_idx + stage_a_end_offset + offset
        r_start = r["entered_wall"]
        r_end = r_start + r["inclusive_wall"]
        if r_start >= b_cur_end - 1e-7:
            b_top_cpu += r["inclusive_thread_cpu"]
            b_top_wall += r["inclusive_wall"]
            b_cur_end = r_end
            b_top_calls.append(
                {
                    "row_index": abs_idx,
                    "label": r["label"],
                    "name": r["name"],
                    "inclusive_thread_cpu": r["inclusive_thread_cpu"],
                    "inclusive_wall": r["inclusive_wall"],
                    "outcome": r["outcome"],
                }
            )

    return {
        "accept_outer_row_index": first_idx + accept_outer_offset,
        "accept_outcome": accept_row["outcome"],
        "accept_entered_utc": accept_row["entered_utc"],
        "accept_left_utc": accept_row.get("left_utc"),
        "stage_a_first_row": first_idx,
        "stage_a_last_row_exclusive": first_idx + stage_a_end_offset,
        "stage_a_row_count": len(stage_a_rows),
        "stage_a_wall_s": stage_a_wall_s,
        "stage_a_counts_by_label": count_by_label(stage_a_rows),
        "stage_b_first_row": first_idx + stage_a_end_offset,
        "stage_b_last_row_exclusive": last_idx,
        "stage_b_row_count": len(stage_b_rows),
        "stage_b_wall_s": stage_b_wall_s,
        "stage_b_monitored_top_children_thread_cpu_s": b_top_cpu,
        "stage_b_monitored_top_children_wall_s": b_top_wall,
        "stage_b_top_calls": b_top_calls,
        "stage_b_counts_by_label": count_by_label(stage_b_rows),
    }


def load_completed_run(key: str, spec: dict[str, Any]) -> dict[str, Any]:
    run_dir: Path = spec["dir"]
    outer_path = run_dir.with_suffix(".outer.json")
    sup_path = run_dir.with_suffix(".supervisor.json")
    diag_files = sorted((run_dir / "phase-metrics").glob("*-diagnostic.json"))
    meas_files = sorted((run_dir / "phase-metrics").glob("*-measurement.json"))
    assert len(diag_files) == 1 and len(meas_files) == 1, f"Expected 1 diag and 1 meas in {run_dir}"
    diag_path = diag_files[0]
    meas_path = meas_files[0]
    host_load_path = run_dir / "host-load.json"
    plan_path = run_dir / "plan.json"

    outer = read_json(outer_path)
    sup = read_json(sup_path)
    diag = read_json(diag_path)
    meas = read_json(meas_path)
    host_load = read_json(host_load_path)
    plan = read_json(plan_path)

    fixture_phase = summarize_phase(meas["phases"][0])
    launch_phase = summarize_phase(meas["phases"][1])

    fixture_calls = analyze_phase_calls(
        meas["calls"],
        fixture_phase["first_call_row"],
        fixture_phase["last_call_row_exclusive"],
    )
    launch_calls = analyze_phase_calls(
        meas["calls"],
        launch_phase["first_call_row"],
        launch_phase["last_call_row_exclusive"],
    )
    launch_stages = analyze_launch_stages(meas["calls"], launch_phase)

    special_rows = []
    launch_accept_rows = []
    for idx, r in enumerate(meas["calls"]):
        if r["label"] == "accept_saved_capture" and r["phase"] == "launch":
            launch_accept_rows.append((idx, r))
            continue
        if r["label"] in (
            "accept_saved_capture",
            "freshness_before_reservation",
            "freshness_before_dispatch",
            "freshness_check",
            "public_fixture",
            "public_test_launch",
            "public_launch",
            "engine_entry",
            "launch_engine",
        ):
            special_rows.append(
                {
                    "row_index": idx,
                    "phase": r["phase"],
                    "label": r["label"],
                    "name": r["name"],
                    "file": Path(r["file"]).name,
                    "outcome": r["outcome"],
                    "entered_utc": r["entered_utc"],
                    "left_utc": r.get("left_utc"),
                    "entered_wall": r["entered_wall"],
                    "inclusive_wall": r.get("inclusive_wall"),
                    "inclusive_thread_cpu": r.get("inclusive_thread_cpu"),
                    "capture": r.get("capture"),
                    "guard_accepted_at": r.get("guard_accepted_at"),
                    "coarse_elapsed": r.get("coarse_elapsed"),
                }
            )
    if launch_accept_rows:
        for idx, r in (launch_accept_rows[0], launch_accept_rows[-1]):
            special_rows.append(
                {
                    "row_index": idx,
                    "phase": r["phase"],
                    "label": r["label"],
                    "name": r["name"],
                    "file": Path(r["file"]).name,
                    "outcome": r["outcome"],
                    "entered_utc": r["entered_utc"],
                    "left_utc": r.get("left_utc"),
                    "entered_wall": r["entered_wall"],
                    "inclusive_wall": r.get("inclusive_wall"),
                    "inclusive_thread_cpu": r.get("inclusive_thread_cpu"),
                    "capture": r.get("capture"),
                    "guard_accepted_at": r.get("guard_accepted_at"),
                    "coarse_elapsed": r.get("coarse_elapsed"),
                }
            )

    return {
        "key": key,
        "short_commit": spec["short_commit"],
        "run_dir": str(run_dir),
        "plan_source_commit": plan["source_commit"],
        "files": {
            "outer_json": {"path": str(outer_path), "sha256": sha256_file(outer_path)},
            "supervisor_json": {"path": str(sup_path), "sha256": sha256_file(sup_path)},
            "diagnostic_json": {"path": str(diag_path), "sha256": sha256_file(diag_path)},
            "measurement_json": {"path": str(meas_path), "sha256": sha256_file(meas_path)},
            "host_load_json": {"path": str(host_load_path), "sha256": sha256_file(host_load_path)},
        },
        "supervisor": {
            "returncode": sup["returncode"],
            "seconds": sup["seconds"],
            "limit_seconds": sup["limit_seconds"],
            "cleanup_verified": sup["cleanup_verified"],
            "forced_cleanup": sup["forced_cleanup"],
            "interrupted": sup["interrupted"],
            "manifest": sup["manifest"],
            "manifest_sha256": sup["manifest_sha256"],
        },
        "outer_host_contention": outer["host_contention"],
        "host_load_snapshots": {
            "before": host_load["before"],
            "after_load": host_load["after"]["load"],
        },
        "diagnostic": diag,
        "measurement_metadata": {
            "pid": meas["pid"],
            "node": meas["node"],
            "mode": meas["mode"],
            "worker": meas["worker"],
            "open_call_rows": meas["open_call_rows"],
            "total_call_rows": len(meas["calls"]),
            "cpu_policy": meas["cpu_policy"],
            "scope": meas["scope"],
            "call_counts": meas["call_counts"],
            "registered_code_objects": meas["registered_code_objects"],
            "observed_reservation_windows": meas["observed_reservation_windows"],
            "pytest_phases": meas["pytest_phases"],
        },
        "phases": {
            "fixture": fixture_phase,
            "launch": launch_phase,
            "combined_fixture_plus_launch": {
                "process_cpu": fixture_phase["elapsed"]["process_cpu"]
                + launch_phase["elapsed"]["process_cpu"],
                "thread_cpu": fixture_phase["elapsed"]["thread_cpu"]
                + launch_phase["elapsed"]["thread_cpu"],
                "wall_monotonic": fixture_phase["elapsed"]["wall_monotonic"]
                + launch_phase["elapsed"]["wall_monotonic"],
                "self_user_cpu": fixture_phase["elapsed"]["self_user_cpu"]
                + launch_phase["elapsed"]["self_user_cpu"],
                "self_system_cpu": fixture_phase["elapsed"]["self_system_cpu"]
                + launch_phase["elapsed"]["self_system_cpu"],
                "reaped_child_user_cpu": fixture_phase["elapsed"]["reaped_child_user_cpu"]
                + launch_phase["elapsed"]["reaped_child_user_cpu"],
                "reaped_child_system_cpu": fixture_phase["elapsed"]["reaped_child_system_cpu"]
                + launch_phase["elapsed"]["reaped_child_system_cpu"],
                "reaped_child_total_cpu": fixture_phase["elapsed"]["reaped_child_total_cpu"]
                + launch_phase["elapsed"]["reaped_child_total_cpu"],
            },
        },
        "fixture_call_analysis": fixture_calls,
        "launch_call_analysis": launch_calls,
        "launch_stage_breakdown": launch_stages,
        "special_rows": special_rows,
    }


def compare_launch_phases(
    run_a: dict[str, Any],
    run_b: dict[str, Any],
    key_a: str,
    key_b: str,
) -> dict[str, Any]:
    p_a = run_a["phases"]["launch"]["elapsed"]
    p_b = run_b["phases"]["launch"]["elapsed"]
    phase_deltas = {
        k: {
            key_a: p_a[k],
            key_b: p_b[k],
            f"delta_{key_b}_minus_{key_a}": p_b[k] - p_a[k],
            "pct_change": ((p_b[k] - p_a[k]) / p_a[k] * 100.0) if p_a[k] else None,
        }
        for k in p_a
    }

    labels_a = run_a["launch_call_analysis"]["by_label"]
    labels_b = run_b["launch_call_analysis"]["by_label"]
    all_labels = sorted(set(labels_a) | set(labels_b))

    per_label_comparison = {}
    for lbl in all_labels:
        a = labels_a.get(lbl)
        b = labels_b.get(lbl)
        status = "unchanged_presence"
        if a is None:
            status = f"new_in_{key_b}"
        elif b is None:
            status = f"gone_in_{key_b}"

        count_a = a["count"] if a else 0
        count_b = b["count"] if b else 0
        cpu_a = a["inclusive_thread_cpu_sum"] if a else 0.0
        cpu_b = b["inclusive_thread_cpu_sum"] if b else 0.0
        wall_a = a["inclusive_wall_sum"] if a else 0.0
        wall_b = b["inclusive_wall_sum"] if b else 0.0
        mean_cpu_a = a["inclusive_thread_cpu_mean"] if a else None
        mean_cpu_b = b["inclusive_thread_cpu_mean"] if b else None

        row_cmp: dict[str, Any] = {
            "label": lbl,
            "status": status,
            "file": (b or a)["file"],
            "name": (b or a)["name"],
            f"first_line_{key_a}": a["first_line"] if a else None,
            f"first_line_{key_b}": b["first_line"] if b else None,
            f"count_{key_a}": count_a,
            f"count_{key_b}": count_b,
            "count_delta": count_b - count_a,
            f"inclusive_thread_cpu_sum_{key_a}": cpu_a,
            f"inclusive_thread_cpu_sum_{key_b}": cpu_b,
            "inclusive_thread_cpu_sum_delta": cpu_b - cpu_a,
            f"inclusive_thread_cpu_mean_{key_a}": mean_cpu_a,
            f"inclusive_thread_cpu_mean_{key_b}": mean_cpu_b,
            "inclusive_thread_cpu_mean_delta": (
                (mean_cpu_b - mean_cpu_a)
                if (mean_cpu_a is not None and mean_cpu_b is not None)
                else None
            ),
            f"inclusive_wall_sum_{key_a}": wall_a,
            f"inclusive_wall_sum_{key_b}": wall_b,
            "inclusive_wall_sum_delta": wall_b - wall_a,
        }
        if (a and a.get("has_coarse_elapsed")) or (b and b.get("has_coarse_elapsed")):
            ca = a["coarse_elapsed_sum"] if (a and "coarse_elapsed_sum" in a) else {}
            cb = b["coarse_elapsed_sum"] if (b and "coarse_elapsed_sum" in b) else {}
            row_cmp["coarse_elapsed_sum_comparison"] = {
                k: {
                    key_a: ca.get(k, 0.0),
                    key_b: cb.get(k, 0.0),
                    "delta": cb.get(k, 0.0) - ca.get(k, 0.0),
                }
                for k in (
                    "process_cpu",
                    "thread_cpu",
                    "wall_monotonic",
                    "self_user_cpu",
                    "self_system_cpu",
                    "reaped_child_user_cpu",
                    "reaped_child_system_cpu",
                    "reaped_child_total_cpu",
                )
            }
            cfa = a["coarse_elapsed_first_call"] if (a and "coarse_elapsed_first_call" in a) else {}
            cfb = b["coarse_elapsed_first_call"] if (b and "coarse_elapsed_first_call" in b) else {}
            row_cmp["coarse_elapsed_first_call_comparison"] = {
                k: {
                    key_a: cfa.get(k, 0.0),
                    key_b: cfb.get(k, 0.0),
                    "delta": cfb.get(k, 0.0) - cfa.get(k, 0.0),
                }
                for k in (
                    "process_cpu",
                    "thread_cpu",
                    "wall_monotonic",
                    "self_user_cpu",
                    "self_system_cpu",
                    "reaped_child_user_cpu",
                    "reaped_child_system_cpu",
                    "reaped_child_total_cpu",
                )
            }
        per_label_comparison[lbl] = row_cmp

    tree_a = run_a["launch_call_analysis"]["call_tree_decomposition_by_label"]
    tree_b = run_b["launch_call_analysis"]["call_tree_decomposition_by_label"]
    unmonitored_comparison = {}
    for lbl in all_labels:
        ta = tree_a.get(lbl, {})
        tb = tree_b.get(lbl, {})
        unmonitored_comparison[lbl] = {
            f"unmonitored_self_thread_cpu_{key_a}": ta.get("unmonitored_self_thread_cpu_sum", 0.0),
            f"unmonitored_self_thread_cpu_{key_b}": tb.get("unmonitored_self_thread_cpu_sum", 0.0),
            "unmonitored_self_thread_cpu_delta": tb.get("unmonitored_self_thread_cpu_sum", 0.0)
            - ta.get("unmonitored_self_thread_cpu_sum", 0.0),
            f"unmonitored_self_wall_{key_a}": ta.get("unmonitored_self_wall_sum", 0.0),
            f"unmonitored_self_wall_{key_b}": tb.get("unmonitored_self_wall_sum", 0.0),
            "unmonitored_self_wall_delta": tb.get("unmonitored_self_wall_sum", 0.0)
            - ta.get("unmonitored_self_wall_sum", 0.0),
        }

    # Stage A vs Stage B row count comparison by label
    sa_a = run_a["launch_stage_breakdown"]["stage_a_counts_by_label"]
    sa_b = run_b["launch_stage_breakdown"]["stage_a_counts_by_label"]
    sb_a = run_a["launch_stage_breakdown"]["stage_b_counts_by_label"]
    sb_b = run_b["launch_stage_breakdown"]["stage_b_counts_by_label"]
    stage_row_deltas_by_label = {}
    for lbl in all_labels:
        ca_stage_a = sa_a.get(lbl, 0)
        cb_stage_a = sa_b.get(lbl, 0)
        ca_stage_b = sb_a.get(lbl, 0)
        cb_stage_b = sb_b.get(lbl, 0)
        stage_row_deltas_by_label[lbl] = {
            f"stage_a_{key_a}": ca_stage_a,
            f"stage_a_{key_b}": cb_stage_a,
            "stage_a_delta": cb_stage_a - ca_stage_a,
            f"stage_b_{key_a}": ca_stage_b,
            f"stage_b_{key_b}": cb_stage_b,
            "stage_b_delta": cb_stage_b - ca_stage_b,
            "total_delta": (cb_stage_a + cb_stage_b) - (ca_stage_a + ca_stage_b),
        }

    return {
        f"row_count_{key_a}": run_a["launch_call_analysis"]["row_count"],
        f"row_count_{key_b}": run_b["launch_call_analysis"]["row_count"],
        "row_count_delta": run_b["launch_call_analysis"]["row_count"]
        - run_a["launch_call_analysis"]["row_count"],
        "stage_row_deltas_by_label": stage_row_deltas_by_label,
        "phase_elapsed_comparison": phase_deltas,
        "per_label_comparison": per_label_comparison,
        "unmonitored_self_comparison": unmonitored_comparison,
        f"edges_{key_a}": run_a["launch_call_analysis"]["parent_child_edges"],
        f"edges_{key_b}": run_b["launch_call_analysis"]["parent_child_edges"],
    }


def compute_freshness_arithmetic(run_data: dict[str, Any]) -> dict[str, Any]:
    diag = run_data["diagnostic"]
    fix = run_data["phases"]["fixture"]
    lnch = run_data["phases"]["launch"]

    capture_ts = parse_utc(diag["capture_timestamp"])
    observed_at_ts = parse_utc(diag["observed_at"])
    fix_before_ts = parse_utc(fix["before_utc"])
    fix_after_ts = parse_utc(fix["after_utc"])
    lnch_before_ts = parse_utc(lnch["before_utc"])
    lnch_after_ts = parse_utc(lnch["after_utc"])

    limit_s = float(diag["capture_age_limit_seconds"])
    margin_s = float(diag["capture_margin_seconds"])
    effective_target_s = limit_s - margin_s  # 300 - 90 = 210.0

    # Collect all freshness_* rows in launch in chronological order
    freshness_rows = [
        r
        for r in run_data["special_rows"]
        if r["phase"] == "launch"
        and r["label"]
        in (
            "freshness_before_reservation",
            "freshness_before_dispatch",
            "freshness_check",
        )
    ]
    detailed_freshness_calls = []
    for r in freshness_rows:
        ent_ts = parse_utc(r["entered_utc"])
        lft_ts = parse_utc(r["left_utc"]) if r.get("left_utc") else None
        age_entry = (ent_ts - capture_ts).total_seconds()
        age_exit = (lft_ts - capture_ts).total_seconds() if lft_ts else None
        detailed_freshness_calls.append(
            {
                "row_index": r["row_index"],
                "label": r["label"],
                "name": r["name"],
                "outcome": r["outcome"],
                "entered_utc": r["entered_utc"],
                "left_utc": r.get("left_utc"),
                "age_since_capture_at_entry_s": age_entry,
                "age_since_capture_at_exit_s": age_exit,
                "excess_over_210_at_entry_s": age_entry - effective_target_s,
                "excess_over_300_at_entry_s": age_entry - limit_s,
                "launch_monotonic_elapsed_at_entry_s": (
                    r["entered_wall"] - lnch["before_wall_monotonic"]
                ),
            }
        )

    before_res_row = next(
        (r for r in detailed_freshness_calls if r["label"] == "freshness_before_reservation"),
        None,
    )
    failing_fresh_check_row = next(
        (
            r
            for r in detailed_freshness_calls
            if r["label"] == "freshness_check" and r["outcome"].startswith("exception")
        ),
        None,
    )

    capture_to_fixture_end_s = (fix_after_ts - capture_ts).total_seconds()
    capture_to_launch_start_s = (lnch_before_ts - capture_ts).total_seconds()
    capture_to_launch_end_s = (lnch_after_ts - capture_ts).total_seconds()
    capture_to_diagnostic_observed_s = (observed_at_ts - capture_ts).total_seconds()

    launch_wall_s = lnch["elapsed"]["wall_monotonic"]
    launch_process_cpu_s = lnch["elapsed"]["process_cpu"]
    launch_self_total_cpu_s = lnch["elapsed"]["self_total_cpu"]
    launch_reaped_child_total_cpu_s = lnch["elapsed"]["reaped_child_total_cpu"]
    launch_self_plus_reaped_cpu_s = lnch["elapsed"]["self_plus_reaped_child_cpu"]

    remaining_budget_at_launch_start_s = effective_target_s - capture_to_launch_start_s
    remaining_300_at_launch_start_s = limit_s - capture_to_launch_start_s

    excess_over_210_at_launch_end_s = capture_to_launch_end_s - effective_target_s
    excess_over_210_at_diagnostic_observed_s = capture_to_diagnostic_observed_s - effective_target_s
    excess_over_210_at_refusal_check_entry_s = (
        failing_fresh_check_row["excess_over_210_at_entry_s"] if failing_fresh_check_row else None
    )
    excess_over_300_at_refusal_check_entry_s = (
        failing_fresh_check_row["excess_over_300_at_entry_s"] if failing_fresh_check_row else None
    )

    required_launch_wall_reduction_for_210_s = launch_wall_s - remaining_budget_at_launch_start_s
    required_launch_wall_reduction_for_210_pct = (
        required_launch_wall_reduction_for_210_s / launch_wall_s * 100.0
    )
    required_launch_wall_reduction_at_refusal_call_for_210_s = (
        failing_fresh_check_row["launch_monotonic_elapsed_at_entry_s"]
        - remaining_budget_at_launch_start_s
        if failing_fresh_check_row
        else None
    )

    return {
        "capture_age_limit_seconds": limit_s,
        "capture_margin_seconds": margin_s,
        "effective_freshness_target_seconds": effective_target_s,
        "timestamps": {
            "fixture_before_utc": fix["before_utc"],
            "capture_timestamp_utc": diag["capture_timestamp"],
            "fixture_after_utc": fix["after_utc"],
            "launch_before_utc": lnch["before_utc"],
            "freshness_before_reservation_entered_utc": (
                before_res_row["entered_utc"] if before_res_row else None
            ),
            "failing_freshness_check_entered_utc": (
                failing_fresh_check_row["entered_utc"] if failing_fresh_check_row else None
            ),
            "failing_freshness_check_left_utc": (
                failing_fresh_check_row["left_utc"] if failing_fresh_check_row else None
            ),
            "launch_after_utc": lnch["after_utc"],
            "diagnostic_observed_at_utc": diag["observed_at"],
        },
        "intervals_seconds": {
            "fixture_start_to_capture_utc_s": (capture_ts - fix_before_ts).total_seconds(),
            "capture_to_fixture_end_utc_s": capture_to_fixture_end_s,
            "fixture_end_to_launch_start_utc_s": (lnch_before_ts - fix_after_ts).total_seconds(),
            "capture_to_launch_start_utc_s": capture_to_launch_start_s,
            "launch_start_to_failing_freshness_check_entry_monotonic_s": (
                failing_fresh_check_row["launch_monotonic_elapsed_at_entry_s"]
                if failing_fresh_check_row
                else None
            ),
            "launch_phase_wall_monotonic_s": launch_wall_s,
            "capture_to_freshness_before_reservation_entry_utc_s": (
                before_res_row["age_since_capture_at_entry_s"] if before_res_row else None
            ),
            "capture_to_failing_freshness_check_entry_utc_s": (
                failing_fresh_check_row["age_since_capture_at_entry_s"]
                if failing_fresh_check_row
                else None
            ),
            "capture_to_failing_freshness_check_exit_utc_s": (
                failing_fresh_check_row["age_since_capture_at_exit_s"]
                if failing_fresh_check_row
                else None
            ),
            "capture_to_launch_end_utc_s": capture_to_launch_end_s,
            "capture_to_diagnostic_observed_utc_s": capture_to_diagnostic_observed_s,
        },
        "all_launch_freshness_calls": detailed_freshness_calls,
        "budget_and_reduction_needed": {
            "remaining_210_wall_budget_at_launch_start_s": remaining_budget_at_launch_start_s,
            "remaining_300_wall_budget_at_launch_start_s": remaining_300_at_launch_start_s,
            "excess_wall_over_210_at_failing_freshness_check_entry_s": (
                excess_over_210_at_refusal_check_entry_s
            ),
            "excess_wall_over_300_at_failing_freshness_check_entry_s": (
                excess_over_300_at_refusal_check_entry_s
            ),
            "excess_wall_over_210_at_launch_end_s": excess_over_210_at_launch_end_s,
            "excess_wall_over_210_at_diagnostic_observed_s": excess_over_210_at_diagnostic_observed_s,
            "required_launch_wall_reduction_at_refusal_call_for_210_s": (
                required_launch_wall_reduction_at_refusal_call_for_210_s
            ),
            "required_launch_wall_reduction_at_launch_end_for_210_s": (
                required_launch_wall_reduction_for_210_s
            ),
            "required_launch_wall_reduction_at_launch_end_for_210_pct": (
                required_launch_wall_reduction_for_210_pct
            ),
            "launch_process_cpu_s": launch_process_cpu_s,
            "launch_self_total_cpu_s": launch_self_total_cpu_s,
            "launch_reaped_child_total_cpu_s": launch_reaped_child_total_cpu_s,
            "launch_self_plus_reaped_child_cpu_s": launch_self_plus_reaped_cpu_s,
            "excess_launch_process_cpu_over_210_target_s": launch_process_cpu_s - effective_target_s,
            "excess_launch_process_cpu_over_remaining_210_budget_at_launch_start_s": (
                launch_process_cpu_s - remaining_budget_at_launch_start_s
            ),
            "excess_launch_self_plus_reaped_cpu_over_210_target_s": (
                launch_self_plus_reaped_cpu_s - effective_target_s
            ),
            "excess_launch_self_plus_reaped_cpu_over_remaining_210_budget_at_launch_start_s": (
                launch_self_plus_reaped_cpu_s - remaining_budget_at_launch_start_s
            ),
        },
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    runs = {k: load_completed_run(k, spec) for k, spec in RUN_SPECS.items()}

    interrupted_dir = SCRATCH_U3M / "wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111"
    interrupted_outer = read_json(interrupted_dir.with_suffix(".outer.json"))
    interrupted_sup = read_json(interrupted_dir.with_suffix(".supervisor.json"))
    interrupted_host_load = read_json(interrupted_dir / "host-load.json")
    interrupted_cutoff = read_json(interrupted_dir / "wp1-cutoff.json")

    code_objects_by_label: dict[str, dict[str, Any]] = {}
    for k in ("3cc113e2606c", "458887766eff", "382f0dfd1ce8_rerun"):
        for co in runs[k]["measurement_metadata"]["registered_code_objects"]:
            lbl = co["label"]
            slot = code_objects_by_label.setdefault(
                lbl,
                {
                    "label": lbl,
                    "file": Path(co["file"]).name,
                    "name": co["name"],
                    "by_run": {},
                },
            )
            slot["by_run"].setdefault(k, []).append(
                {
                    "name": co["name"],
                    "first_line": co["first_line"],
                    "bytecode_sha256": co["bytecode_sha256"],
                }
            )
    for lbl, slot in code_objects_by_label.items():
        br = slot["by_run"]
        hashes_3cc = sorted({x["bytecode_sha256"] for x in br.get("3cc113e2606c", [])})
        hashes_4588 = sorted({x["bytecode_sha256"] for x in br.get("458887766eff", [])})
        hashes_382f = sorted({x["bytecode_sha256"] for x in br.get("382f0dfd1ce8_rerun", [])})
        slot["unique_bytecode_sha256_by_run"] = {
            "3cc113e2606c": hashes_3cc,
            "458887766eff": hashes_4588,
            "382f0dfd1ce8_rerun": hashes_382f,
        }
        slot["bytecode_changed_4588_to_382f"] = hashes_4588 != hashes_382f
        slot["bytecode_changed_3cc_to_4588"] = hashes_3cc != hashes_4588
        del slot["by_run"]

    comparison_4588_vs_382f = compare_launch_phases(
        runs["458887766eff"],
        runs["382f0dfd1ce8_rerun"],
        "458887766eff",
        "382f0dfd1ce8",
    )
    comparison_3cc_vs_382f = compare_launch_phases(
        runs["3cc113e2606c"],
        runs["382f0dfd1ce8_rerun"],
        "3cc113e2606c",
        "382f0dfd1ce8",
    )

    freshness_by_run = {k: compute_freshness_arithmetic(v) for k, v in runs.items()}

    lead_table_verification = []
    for k in ("3cc113e2606c", "458887766eff", "382f0dfd1ce8_rerun"):
        r = runs[k]
        fix_el = r["phases"]["fixture"]["elapsed"]
        lnch_el = r["phases"]["launch"]["elapsed"]
        hc = r["outer_host_contention"]
        hl = r["host_load_snapshots"]
        lead_table_verification.append(
            {
                "key": k,
                "short_commit": r["short_commit"],
                "fixture_process_cpu_s": fix_el["process_cpu"],
                "fixture_self_user_cpu_s": fix_el["self_user_cpu"],
                "fixture_self_system_cpu_s": fix_el["self_system_cpu"],
                "fixture_reaped_child_user_cpu_s": fix_el["reaped_child_user_cpu"],
                "fixture_reaped_child_system_cpu_s": fix_el["reaped_child_system_cpu"],
                "fixture_reaped_child_total_cpu_s": fix_el["reaped_child_total_cpu"],
                "fixture_wall_s": fix_el["wall_monotonic"],
                "launch_process_cpu_s": lnch_el["process_cpu"],
                "launch_self_user_cpu_s": lnch_el["self_user_cpu"],
                "launch_self_system_cpu_s": lnch_el["self_system_cpu"],
                "launch_reaped_child_user_cpu_s": lnch_el["reaped_child_user_cpu"],
                "launch_reaped_child_system_cpu_s": lnch_el["reaped_child_system_cpu"],
                "launch_reaped_child_total_cpu_s": lnch_el["reaped_child_total_cpu"],
                "launch_wall_s": lnch_el["wall_monotonic"],
                "combined_process_cpu_s": r["phases"]["combined_fixture_plus_launch"][
                    "process_cpu"
                ],
                "combined_wall_s": r["phases"]["combined_fixture_plus_launch"]["wall_monotonic"],
                "supervisor_wall_s": r["supervisor"]["seconds"],
                "start_one_minute_load_per_cpu": hl["before"]["load"][0]
                / hl["before"]["logical_cpus"],
                "end_one_minute_load_per_cpu": hl["after_load"][0]
                / hl["before"]["logical_cpus"],
                "max_one_minute_load_per_cpu": hc["max_one_minute_load_per_cpu"],
                "mean_cpu_percent": hc["mean_cpu_percent"],
                "peak_cpu_percent": hc["peak_cpu_percent"],
                "outcome": r["diagnostic"]["outcome"],
                "error": r["diagnostic"]["error"],
                "audit_events": r["diagnostic"]["profile_stability"]["audit_events"],
            }
        )

    output_payload = {
        "lead_table_verification": lead_table_verification,
        "runs": runs,
        "registered_code_objects_comparison": code_objects_by_label,
        "comparison_458887766eff_vs_382f0dfd1ce8": comparison_4588_vs_382f,
        "comparison_3cc113e2606c_vs_382f0dfd1ce8": comparison_3cc_vs_382f,
        "freshness_arithmetic": freshness_by_run,
        "interrupted_382f0dfd1ce8_run": {
            "dir": str(interrupted_dir),
            "supervisor_returncode": interrupted_sup["returncode"],
            "supervisor_seconds": interrupted_sup["seconds"],
            "outer_returncode": interrupted_outer["returncode"],
            "outer_seconds": interrupted_outer["seconds"],
            "outer_host_contention": interrupted_outer["host_contention"],
            "host_load_before": interrupted_host_load["before"],
            "host_load_after_load": interrupted_host_load["after"]["load"],
            "wp1_cutoff": interrupted_cutoff,
        },
    }

    raw = (json.dumps(output_payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    OUT_JSON.write_bytes(raw)
    print(
        json.dumps(
            {
                "output": str(OUT_JSON),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
