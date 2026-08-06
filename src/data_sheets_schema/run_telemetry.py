"""Collect process telemetry for six-phase D4D generation runs.

Harvests what the runs already record — provenance ``api_usage`` rows, the
reasoning log, the repair log, validation outcome, artifact mtimes — into a
report conforming to ``schema/d4d_run_telemetry.yaml``. Nothing here calls an
API or mutates a run directory.

Evidence honesty rules, mirrored in the schema:

* ``timing_basis`` says where time figures come from. Runs made before
  per-attempt timestamps existed (#367) can only be dated by artifact mtimes
  and the provenance stamp; ``wall_seconds_estimate`` is then absent rather
  than guessed, because an artifact mtime is the *last* write (a repaired
  record's mtime dates the repair, not the phase).
* ``invocations`` is derived from gaps between recorded timestamps and is
  absent for legacy runs — repair-round numbering alone cannot distinguish a
  resumed invocation from a second artifact's rounds.
* Attempts join to reasoning entries by (phase, order of appearance), not by
  attempt number: both files accumulate across invocations, so numbers repeat
  while order is preserved.
* The ``repair_rounds`` outcomes come from the provenance repair block, which
  records only the latest invocation until #366 is fixed; every repair *call*
  still appears under ``phases`` from the cumulative usage rows.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from data_sheets_schema.api_runner import CONCAT_DIR

SCHEMA_PATH = Path("src/data_sheets_schema/schema/d4d_run_telemetry.yaml")
SCHEMA_VERSION = "1.0.0"

# CBORG-posted opus-5 rates (2026-08-05, /model/info): $ per token. Cache
# writes bill at 1.25x input, cache reads at 0.1x. No premium tier above 200k.
RATE_INPUT = 5e-6
RATE_CACHE_WRITE = 6.25e-6
RATE_CACHE_READ = 0.5e-6
RATE_OUTPUT = 25e-6

# Which artifact each phase writes, for attaching the one mtime evidence
# point to the phase that actually left it behind (the last writer).
_ARTIFACT_WRITERS = {
    "full": ("full", "reconcile_full", "repair_full"),
    "core": ("core", "reconcile_core", "repair_core"),
    "report": ("report",),
}

_STOP_REASONS = {"end_turn", "max_tokens", "stop_sequence"}
# 6 minutes: longer than any observed inter-phase gap within one invocation
# (validator runs included), far shorter than any operator round trip.
_INVOCATION_GAP_SECONDS = 360


def _mtime_iso(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime,
                                  tz=timezone.utc).isoformat(timespec="seconds")


def _reasoning_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _attempt(row: dict[str, Any],
             reasoning_entry: dict[str, Any] | None) -> dict[str, Any]:
    a: dict[str, Any] = {"attempt": int(row.get("attempt") or 0)}
    for src, dst in (("started_at", "started_at"), ("seconds", "seconds"),
                     ("input_tokens", "input_tokens"),
                     ("output_tokens", "output_tokens"),
                     ("cache_read", "cache_read_tokens"),
                     ("cache_write", "cache_write_tokens"),
                     ("max_tokens", "max_tokens")):
        if row.get(src) is not None:
            a[dst] = row[src]
    stop = row.get("stop_reason")
    if stop is not None:
        a["stop_reason"] = stop if stop in _STOP_REASONS else "other"
    if reasoning_entry:
        for src, dst in (("reasoning_tokens_estimate",
                          "reasoning_tokens_estimate"),
                         ("visible_text_chars", "visible_text_chars"),
                         ("reasoning_present", "reasoning_present"),
                         ("reasoning_available", "reasoning_available")):
            if reasoning_entry.get(src) is not None:
                a[dst] = reasoning_entry[src]
    return a


def _invocations(rows: list[dict[str, Any]]) -> int | None:
    """1 + the number of recorded-timestamp gaps longer than an invocation gap.

    None without timestamps: repair-round numbering alone cannot tell a
    resumed invocation from a second artifact's rounds, and a wrong count is
    worse than no count.
    """
    stamps = []
    for r in rows:
        if r.get("started_at"):
            try:
                stamps.append(datetime.fromisoformat(r["started_at"]))
            except ValueError:
                return None
    if len(stamps) != len(rows) or not stamps:
        return None
    gaps = sum(1 for a, b in zip(stamps, stamps[1:])
               if (b - a).total_seconds() > _INVOCATION_GAP_SECONDS)
    return 1 + gaps


def run_telemetry(run_dir: Path, project: str) -> dict[str, Any] | None:
    """One RunTelemetry object, or None when no provenance exists yet."""
    prov_path = run_dir / f"{project}_provenance.yaml"
    if not prov_path.exists():
        return None
    prov = yaml.safe_load(prov_path.read_text(encoding="utf-8")) or {}
    rows = prov.get("api_usage") or []
    reasoning = _reasoning_entries(run_dir / f"{project}_reasoning.jsonl")

    # Join by (phase, occurrence index): both logs accumulate across
    # invocations in the same order, so numbers repeat while order holds.
    by_phase_reasoning: dict[str, list[dict[str, Any]]] = {}
    for e in reasoning:
        by_phase_reasoning.setdefault(e.get("phase", ""), []).append(e)
    seen_per_phase: dict[str, int] = {}

    phases: dict[str, dict[str, Any]] = {}
    for row in rows:
        ph = row.get("phase") or "other"
        idx = seen_per_phase.get(ph, 0)
        seen_per_phase[ph] = idx + 1
        entries = by_phase_reasoning.get(ph, [])
        entry = entries[idx] if idx < len(entries) else None
        phases.setdefault(ph, {"phase": ph, "attempts": []})
        phases[ph]["attempts"].append(_attempt(row, entry))

    # The single mtime evidence point goes to the artifact's last writer.
    method_dir = run_dir.parent.parent
    label = run_dir.name
    artifact_paths = {
        "full": method_dir / (prov.get("run", {}).get("method")
                              or "claudecode_agent") / label
                / f"{project}_d4d.yaml",
        "core": run_dir / f"{project}_d4d_core.yaml",
        "report": run_dir / f"{project}_reconciliation.md",
    }
    for artifact, writers in _ARTIFACT_WRITERS.items():
        last = next((w for w in reversed(writers) if w in phases), None)
        if last:
            stamp = _mtime_iso(artifact_paths[artifact])
            if stamp:
                phases[last]["artifact_written_at"] = stamp

    validation = prov.get("validation")
    if isinstance(validation, dict):
        probs = validation.get("problems") or []
        state = "valid" if not probs else "invalid"
        prob_count = len(probs)
    else:
        state, prob_count = "unchecked", None

    total = {k: sum(r.get(k) or 0 for r in rows)
             for k in ("input_tokens", "output_tokens",
                       "cache_read", "cache_write")}
    reasoning_total = sum(e.get("reasoning_tokens_estimate") or 0
                          for e in reasoning)
    cost = (total["input_tokens"] * RATE_INPUT
            + total["cache_write"] * RATE_CACHE_WRITE
            + total["cache_read"] * RATE_CACHE_READ
            + total["output_tokens"] * RATE_OUTPUT)

    timed = [r for r in rows if r.get("seconds") is not None]
    if timed and len(timed) == len(rows):
        basis = "recorded"
        wall = round(sum(r["seconds"] for r in rows), 1)
    elif any(p.get("artifact_written_at") for p in phases.values()):
        basis, wall = "file_mtime", None
    else:
        basis, wall = "absent", None

    run_block = prov.get("run") or {}
    model_block = prov.get("model") or {}
    out: dict[str, Any] = {
        "project": project,
        "label": run_block.get("label") or label,
        "validation_state": state,
        "timing_basis": basis,
        "phases": list(phases.values()),
    }
    if run_block.get("replicate") is not None:
        out["replicate"] = run_block["replicate"]
    # No condition: provenance does not record it as a field — the pinned
    # prompt file is its witness, and inferring a name from a filename here
    # would put an unrecorded claim into the report.
    for k, v in (("model", model_block.get("model")),
                 ("provider", model_block.get("provider")),
                 ("arm", run_block.get("arm"))):
        if v:
            out[k] = v
    if prov.get("record_generated_at"):
        out["finished_at"] = prov["record_generated_at"]
    if wall is not None:
        out["wall_seconds_estimate"] = wall
    if prob_count is not None:
        out["validation_problem_count"] = prob_count
    out["total_input_tokens"] = total["input_tokens"]
    out["total_output_tokens"] = total["output_tokens"]
    out["total_cache_read_tokens"] = total["cache_read"]
    out["total_cache_write_tokens"] = total["cache_write"]
    out["total_reasoning_tokens_estimate"] = reasoning_total
    out["approx_cost_usd"] = round(cost, 2)
    inv = _invocations(rows)
    if inv is not None:
        out["invocations"] = inv
    repair = prov.get("repair") or []
    if repair:
        out["repair_rounds"] = [
            {"artifact": r["phase"].replace("repair_", ""),
             "round": r["round"], "outcome": r["outcome"],
             **({"findings": r["findings"]} if r.get("findings") is not None
                else {})}
            for r in repair]
    return out


def collect_report(label_prefix: str,
                   method: str = "claudecode_agent",
                   root: Path | None = None) -> dict[str, Any]:
    """A RunTelemetryReport over every run dir matching the label prefix."""
    base = (root or CONCAT_DIR) / f"{method}_core"
    runs: list[dict[str, Any]] = []
    dirs = sorted(p for p in base.glob(f"{label_prefix}*") if p.is_dir())
    for d in dirs:
        for prov in sorted(d.glob("*_provenance.yaml")):
            project = prov.name.replace("_provenance.yaml", "")
            t = run_telemetry(d, project)
            if t:
                runs.append(t)
    return {
        "label": label_prefix,
        "method": method,
        "generated_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "schema_version": SCHEMA_VERSION,
        "runs": runs,
    }
