"""Read-only live dollar readout for D4D API generation runs (Step A3b / #1763, #4345, #4829).

Prices settled ledger rows using CBORG opus-5 rates from ``run_telemetry.py`` and
projects worst-case costs for in-flight pending calls across all generation phases:
- ``full`` (128,000 output cap)
- ``full_readdress`` (8,000 output cap / READDRESS_MAX_TOKENS)
- ``receipt_completion`` (cap and input from saved request and counted context)
- ``reconcile_full`` (96,000 fallback output cap; 128,000 when pinned in ``{project}_{phase}_context.json`` under #5157)
- ``report`` (96,000 fallback output cap; 128,000 when pinned in ``{project}_{phase}_context.json`` under #5157)
- ``report_regate`` (96,000 fallback output cap; 128,000 when pinned in ``{project}_{phase}_context.json`` under #5157)
- ``repair_full`` (96,000 fallback output cap; 128,000 when pinned in ``{project}_{phase}_context.json`` under #5157)
- ``report_after_repair`` (96,000 fallback output cap; 128,000 when pinned in ``{project}_{phase}_context.json`` under #5157)
- typed audit stages (cap and input from saved stage request and context)

A pending call's input is bounded, in order, by an operator's custom bound; the
runner's own count of the request (the receipt completion and typed audit stage
contexts, `{project}_{phase}_context.json` where the runner pins one, #5157, and
shared generation 2's counted requests); a measured attempt of the same request
in this generation; the generation's measured `full` request plus the files the
phase carries, at one token per byte, within the room the context window leaves
beside max_tokens; and the static project baseline, which the display flags as
possibly low (#5117).

Abandoned attempts are priced from the journal: this generation's from its
boundary and a prior generation's wherever it lies. Without the stream's final
usage, an attempt's output is priced at the max_tokens it sent (#5117).

Operator trigger logic alerts when projected total cost reaches the operator stop trigger
(cap minus worst-case in-flight call) to prevent overrunning allocations.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from data_sheets_schema.run_telemetry import (
    RATE_CACHE_READ,
    RATE_CACHE_WRITE,
    RATE_INPUT,
    RATE_OUTPUT,
    RATES_MODEL,
    rates_cover,
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

#: Phases whose every attempt sends the same request, so a measured attempt in
#: this generation bounds the next one exactly.
RESENT_PHASES = frozenset({"full", "reconcile_full", "report"})

#: Each ordinary phase's request as the request it extends plus the files the
#: runner wrote that it adds (#5117). Names are snapshot names under
#: `intermediate/` (`api_runner._snapshot`); `full_response` is the full call's
#: response, and `record` and `core_record` are the records on disk.
#: `build_phase` sends the records and findings `PHASE_NEEDS` declares and
#: renders a record again as the schema-context owners (shared generation)
#: and, for the report, the source-review inventory, so that record is listed
#: once per block. The regate sends the report request with the report it
#: rejected (`_append_regate`); the readdress, the full exchange with the
#: unresolved receipt entries, a subset of that response (`build_readdress`);
#: a repair and the report after it, the records on disk.
DERIVED_PHASE_INPUTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "full_readdress": ("full", ("full_response", "full_response")),
    "reconcile_full": ("full", ("audit.json", "full.yaml", "full.yaml")),
    "report": ("full", ("audit.json", "full.yaml", "core.yaml", "reconcile_core.yaml",
                        "reconcile_full.yaml", "reconcile_full.yaml", "reconcile_full.yaml")),
    "report_regate": ("report", ("report_before_regate.md",)),
    "report_after_repair": ("report", ("record", "record", "record", "core_record")),
    "repair_full": ("full", ("record",)),
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


def has_final_usage(entry: Mapping[str, Any]) -> bool:
    """Whether an abandoned attempt's counts are its call's final usage.

    The runner records the stream's usage snapshot: message_start's, or nothing
    (`api_runner._record_incomplete_stream`). message_start reports the whole
    input and a placeholder output; only message_delta brings the final output.
    """
    trace = entry.get("stream_trace")
    return isinstance(trace, Mapping) and trace.get("message_delta_seen") is True


def price_abandoned_row(
    entry: Mapping[str, Any],
    *,
    project: str | None = None,
    ledger_data: Mapping[str, Any] | None = None,
    custom_bounds: Mapping[str, Any] | None = None,
    registration: Mapping[str, Any] | None = None,
    metadata_dir: Path | None = None,
    worst_case_cache: bool = False,
) -> dict[str, Any]:
    """Price one abandoned-attempt journal row (#1017, #5117).

    Without its final usage the call may have produced up to the max_tokens it
    sent, so output is priced there, with the recorded count as a floor. Input
    is the recorded count, or, with none (no message_start), the phase's input
    bound.
    """
    phase = str(entry.get("phase") or "unknown")
    final = has_final_usage(entry)
    output_tokens = _tokens(entry.get("output_tokens"))
    sent = entry.get("max_tokens")
    cap = sent if type(sent) is int and sent > 0 else get_phase_output_cap(phase, registration=registration)
    if not final:
        output_tokens = max(cap, output_tokens)
    recorded = {key: _tokens(entry.get(key)) for key in ("input_tokens", "cache_write", "cache_read")}
    if any(recorded.values()):
        input_dollars, input_source = price_tokens(**recorded), "recorded"
    else:
        bound, input_source = resolve_pending_input_bound(
            phase, project, ledger_data=ledger_data, custom_bounds=custom_bounds, metadata_dir=metadata_dir,
            registration=registration, max_tokens=cap,
        )
        input_dollars = price_input_bound(bound, worst_case_cache=worst_case_cache) if bound is not None else 0.0
    return {
        "phase": phase,
        "usage_id": entry.get("usage_id"),
        "generation_id": entry.get("generation_id"),
        "final_usage": final,
        "output_tokens_priced": output_tokens,
        "input_source": input_source,
        "input_bound_static": input_source.startswith("baseline["),
        "dollars": input_dollars + output_tokens * RATE_OUTPUT,
    }


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


def _candidate_pin_paths(target: Path, metadata_dir: Path | None = None) -> list[Path]:
    """Return candidate paths for a pin relative to metadata_dir, repo root, or CWD."""
    candidates: list[Path] = []
    seen: set[Path] = set()

    def _add(cand: Path) -> None:
        if cand.is_file():
            resolved = cand.resolve()
            if resolved not in seen:
                seen.add(resolved)
                candidates.append(cand)

    if target.is_absolute():
        _add(target)
    if metadata_dir is not None:
        meta_resolved = metadata_dir.resolve()
        if not target.is_absolute():
            for parent in (meta_resolved, *meta_resolved.parents):
                if (parent / "src" / "data_sheets_schema").is_dir() or (parent / "data" / "d4d_concatenated").is_dir():
                    _add(parent / target)
            for base in (meta_resolved, meta_resolved / "intermediate"):
                _add(base / target)
        for base in (meta_resolved, meta_resolved / "intermediate"):
            _add(base / target.name)
    if not target.is_absolute():
        _add(target)
    return candidates


def _resolve_pin_path(target: Path, metadata_dir: Path | None = None) -> Path:
    """Resolve a pin path relative to metadata_dir, metadata_dir/intermediate, repo root, or CWD."""
    candidates = _candidate_pin_paths(target, metadata_dir=metadata_dir)
    return candidates[0] if candidates else target


def extract_saved_snapshot(pin: Any, *, metadata_dir: Path | None = None) -> dict[str, Any] | None:
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
    for candidate in _candidate_pin_paths(target, metadata_dir=metadata_dir):
        try:
            raw_bytes = candidate.read_bytes()
            if expected_sha is not None:
                actual_sha = hashlib.sha256(raw_bytes).hexdigest().lower()
                if actual_sha != expected_sha:
                    continue
            parsed = json.loads(raw_bytes.decode("utf-8"))
            if isinstance(parsed, dict):
                return parsed
        except (OSError, ValueError):
            continue
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


def _tokens(value: Any) -> int:
    """A recorded token count, or 0 for a missing or non-numeric one."""
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else 0


def _measured_split(row: Mapping[str, Any]) -> dict[str, int] | None:
    """A measured request's input as a bound: its uncached tokens, and its cached
    prefix at the write rate, the worst case for a cache that may have expired."""
    uncached = _tokens(row.get("input_tokens"))
    prefix = _tokens(row.get("cache_write")) + _tokens(row.get("cache_read"))
    if uncached + prefix == 0:
        return None
    return {"input_tokens": uncached, "cache_write": prefix, "cache_read": 0}


def _abandoned_entries(
    ledger_data: Mapping[str, Any], metadata_dir: Path, project: str
) -> list[tuple[Mapping[str, Any], bool]]:
    """The abandoned-attempts journal rows this ledger's generations own (#1017, #5117).

    The journal is kept across generations. This generation's rows start at its
    `abandoned_journal_offset`; a generation named in `prior_generation_ids`
    owns its rows wherever they lie. Each row comes with whether it is this
    generation's. A line that does not parse is skipped, not the rest of the journal.
    """
    for search_dir in (metadata_dir, metadata_dir / "intermediate"):
        path = search_dir / f"{project}_abandoned_attempts.jsonl"
        if path.is_file():
            break
    else:
        return []
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    offset = ledger_data.get("abandoned_journal_offset")
    if type(offset) is not int or not 0 <= offset <= len(raw):
        offset = 0
    current = ledger_data.get("generation_id") if isinstance(ledger_data.get("generation_id"), str) else None
    prior = {gid for gid in ledger_data.get("prior_generation_ids") or [] if isinstance(gid, str) and gid}
    entries: list[tuple[Mapping[str, Any], bool]] = []
    start = 0
    for line in raw.split(b"\n"):
        position, start = start, start + len(line) + 1
        if not line.strip():
            continue
        try:
            entry = json.loads(line.decode("utf-8"))
        except (ValueError, RecursionError):
            continue
        if not isinstance(entry, Mapping):
            continue
        generation = entry.get("generation_id")
        if isinstance(generation, str) and generation in prior:
            entries.append((entry, False))
        elif position >= offset and (not isinstance(generation, str) or not generation
                                     or not current or generation == current):
            entries.append((entry, True))
    return entries


def _latest_snapshot(metadata_dir: Path, project: str, name: str, generation: Any) -> Path | None:
    """The newest file this generation wrote under a snapshot name (#1409).

    `api_runner._snapshot` never overwrites: a repeated name gets `_2`, `_3`, …
    before its extension, and `snapshot_store.record` lists every write in the
    generation's index. The index decides when it is this generation's; the
    numbering, for a run without one.
    """
    directory = metadata_dir / "intermediate"
    try:
        index = json.loads((directory / f"{project}_snapshot_index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        index = None
    if (isinstance(index, Mapping) and isinstance(generation, str) and generation
            and index.get("generation_id") == generation and isinstance(index.get("snapshots"), list)):
        written = [entry["path"] for entry in index["snapshots"]
                   if isinstance(entry, Mapping) and entry.get("name") == name and isinstance(entry.get("path"), str)]
        return directory / Path(written[-1]).name if written else None
    stem, dot, ext = name.rpartition(".")
    pattern = re.compile(re.escape(stem) + r"(?:_([0-9]+))?" + re.escape(dot + ext))
    numbered = []
    if directory.is_dir():
        for path in directory.iterdir():
            match = pattern.fullmatch(path.name)
            if match:
                numbered.append((int(match.group(1) or 1), path))
    return max(numbered)[1] if numbered else None


def _live_records(metadata_dir: Path, project: str, identity: Any) -> tuple[Path, Path]:
    """The full and core records where the runner writes them (`RunSpec.full_path`,
    `core_path`): the core beside the metadata, and the full record under
    `{method}/{label}/` beside `{method}_core/{label}/`, or beside the metadata
    in a flat layout."""
    method = identity.get("method") if isinstance(identity, Mapping) else None
    full_dir = metadata_dir
    if isinstance(method, str) and method and metadata_dir.parent.name == f"{method}_core":
        full_dir = metadata_dir.parent.parent / method / metadata_dir.name
    return full_dir / f"{project}_d4d.yaml", metadata_dir / f"{project}_d4d_core.yaml"


def _routing_requests(ledger_data: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    """Shared generation 2's admitted ordinary requests, newest first: each is
    counted and saved with its payload before dispatch, and journalled under
    `source_heading_admissions` (`source_heading_admission.prepare`)."""
    state = (ledger_data or {}).get("source_heading_admissions")
    rows = state.get("rows") if isinstance(state, Mapping) else None
    return [row for row in reversed(rows) if isinstance(row, Mapping)] if isinstance(rows, list) else []


def _phase_count_pin(
    phase: str, project: str | None, metadata_dir: Path | None, ledger_data: Mapping[str, Any] | None
) -> tuple[dict[str, Any], Path] | None:
    """The runner's count of this phase's request before dispatch, with its path:
    `{project}_{phase}_context.json` (#5157), or shared generation 2's saved
    request, whose payload carries the max_tokens sent. None without one."""
    if not project or metadata_dir is None:
        return None
    path = _latest_snapshot(metadata_dir, project, f"{project}_{phase}_context.json",
                            (ledger_data or {}).get("generation_id"))
    pin = extract_saved_snapshot(path) if path is not None else None
    if (isinstance(pin, dict) and pin.get("phase", phase) == phase
            and type(pin.get("input_tokens")) is int and pin["input_tokens"] >= 0):
        return pin, path
    for row in _routing_requests(ledger_data):
        if row.get("phase") != phase:
            continue
        saved = extract_saved_snapshot(row.get("request"), metadata_dir=metadata_dir)
        count = saved.get("count") if isinstance(saved, dict) else None
        if isinstance(count, Mapping) and type(count.get("input_tokens")) is int and count["input_tokens"] >= 0:
            payload = saved.get("payload") if isinstance(saved.get("payload"), Mapping) else {}
            return {"input_tokens": count["input_tokens"], "max_tokens": payload.get("max_tokens")}, Path(
                row["request"]["path"])
    return None


def _context_window(
    registration: Mapping[str, Any] | None, ledger_data: Mapping[str, Any] | None, metadata_dir: Path | None
) -> int | None:
    """The context window the runner's admission checks hold a request's input
    plus max_tokens to: the registration's routing limits under shared
    generation 2, else its `audit_limits` (#5157 and the typed audit stages).
    Without a registration, the window this generation's own counts recorded
    against those same limits. None when neither is available."""
    if isinstance(registration, Mapping):
        routing = registration.get("routing")
        for limits in (routing.get("generation_limits") if isinstance(routing, Mapping) else None,
                       registration.get("audit_limits")):
            window = limits.get("context_limit_tokens") if isinstance(limits, Mapping) else None
            if type(window) is int and window > 0:
                return window
    pins = [row.get("request") for row in _routing_requests(ledger_data)]
    typed = (ledger_data or {}).get("typed_audit")
    stages = typed.get("stages") if isinstance(typed, Mapping) else None
    if isinstance(stages, list):
        pins += [stage.get("context") for stage in reversed(stages) if isinstance(stage, Mapping)]
    for pin in pins:
        saved = extract_saved_snapshot(pin, metadata_dir=metadata_dir) if pin is not None else None
        count = saved.get("count", saved) if isinstance(saved, dict) else None
        window = count.get("context_limit_tokens") if isinstance(count, Mapping) else None
        if type(window) is int and window > 0:
            return window
    return None


def _derived_input_bound(
    phase: str, project: str, ledger_data: Mapping[str, Any], metadata_dir: Path | None
) -> tuple[dict[str, int], str] | None:
    """A pending request's input from this generation's own evidence (#5117).

    A measured attempt of a request every attempt resends bounds it exactly;
    the abandoned attempts count, since message_start reports the whole input.
    Otherwise the phase extends a measured request by the files it carries, at
    one token per byte: no token is shorter than a byte. None when a measured
    anchor or a file is missing.
    """
    rows: list[tuple[str, int, Mapping[str, Any]]] = [
        (str(row.get("started_at") or ""), 1, row) for row in ledger_data.get("rows") or [] if isinstance(row, Mapping)]
    if metadata_dir is not None:
        # A dropped transport attempt shares its call's started_at and comes first.
        rows += [(str(entry.get("started_at") or ""), 0, entry)
                 for entry, current in _abandoned_entries(ledger_data, metadata_dir, project) if current]
    measured: dict[str, list[Mapping[str, Any]]] = {}
    for _, _, row in sorted(rows, key=lambda item: item[:2]):
        if _measured_split(row) is not None:
            measured.setdefault(str(row.get("phase")), []).append(row)
    generation = ledger_data.get("generation_id")
    full_record, core_record = (_live_records(metadata_dir, project, ledger_data.get("identity"))
                                if metadata_dir is not None else (None, None))

    def resolve(ph: str) -> tuple[dict[str, int], Mapping[str, Any], str] | None:
        if ph in RESENT_PHASES and measured.get(ph):
            row = measured[ph][-1]
            return _measured_split(row), row, f"measured[{ph}]"
        if ph not in DERIVED_PHASE_INPUTS or metadata_dir is None:
            return None
        anchor_phase, names = DERIVED_PHASE_INPUTS[ph]
        base = resolve(anchor_phase)
        if base is None:
            return None
        split, anchor, source = base
        added = 0
        counts: dict[str, int] = {}
        for name in names:
            counts[name] = counts.get(name, 0) + 1
            if name == "full_response":
                path = _latest_snapshot(metadata_dir, project,
                                        f"{project}_full_response_{anchor.get('usage_id')}.txt", generation)
            elif name in ("record", "core_record"):
                path = full_record if name == "record" else core_record
            else:
                path = _latest_snapshot(metadata_dir, project, f"{project}_{name}", generation)
            if path is None or not path.is_file():
                return None
            added += path.stat().st_size
        listed = ", ".join(f"{n}x {name}" if n > 1 else name for name, n in counts.items())
        return ({**split, "input_tokens": split["input_tokens"] + added}, anchor,
                f"{source} + {added:,} bytes ({listed})")

    found = resolve(phase)
    if found is None:
        return None
    return found[0], found[2] if found[2] == f"measured[{phase}]" else f"derived[{phase}]: {found[2]}"


def resolve_pending_input_bound(
    phase: str,
    project: str | None = None,
    *,
    ledger_data: Mapping[str, Any] | None = None,
    custom_bounds: Mapping[str, Any] | None = None,
    metadata_dir: Path | None = None,
    registration: Mapping[str, Any] | None = None,
    max_tokens: int | None = None,
) -> tuple[Any, str]:
    """Resolve the input bound and source attribution for a pending phase call.

    `max_tokens` is the cap the call sends; with the context window it caps a
    bound derived from files.

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
                context_data = extract_saved_snapshot(rc_state.get("context"), metadata_dir=metadata_dir)
                if context_data and isinstance(context_data.get("input_tokens"), int):
                    return context_data["input_tokens"], "receipt_completion_context.json"
        # Search metadata_dir and intermediate/ if available
        if metadata_dir and metadata_dir.is_dir():
            for search_dir in (metadata_dir, metadata_dir / "intermediate"):
                if search_dir.is_dir():
                    for p in sorted(search_dir.glob("*receipt_completion_context*.json")):
                        data = extract_saved_snapshot(p, metadata_dir=metadata_dir)
                        if data and isinstance(data.get("input_tokens"), int):
                            return data["input_tokens"], p.name

    # 3. Typed audit stages: inspect saved stage context
    if "typed_audit" in phase or phase in {"typed_audit_worker", "typed_audit_omission", "typed_audit_integration"}:
        if ledger_data:
            ta_state = ledger_data.get("typed_audit")
            if isinstance(ta_state, Mapping) and "stages" in ta_state:
                stages = ta_state.get("stages", [])
                if stages and isinstance(stages[-1], Mapping):
                    context_data = extract_saved_snapshot(stages[-1].get("context"), metadata_dir=metadata_dir)
                    if context_data and isinstance(context_data.get("input_tokens"), int):
                        return context_data["input_tokens"], "typed_audit_stage_context.json"
        if metadata_dir and metadata_dir.is_dir():
            candidates: list[Path] = []
            for search_dir in (metadata_dir, metadata_dir / "intermediate"):
                if search_dir.is_dir():
                    candidates.extend(sorted(search_dir.glob("*typed_audit*context*.json")))
            if candidates:
                data = extract_saved_snapshot(candidates[-1], metadata_dir=metadata_dir)
                if data and isinstance(data.get("input_tokens"), int):
                    return data["input_tokens"], candidates[-1].name

    # 4. The runner's count of this request before dispatch (#5157; shared generation 2)
    if metadata_dir is not None and metadata_dir.is_dir():
        counted = _phase_count_pin(phase, project, metadata_dir, ledger_data)
        if counted is not None:
            return counted[0]["input_tokens"], counted[1].name

    # 5. A measured attempt of the same request, or the generation's measured
    #    request plus the files this phase carries (#5117), no larger than the
    #    room the context window leaves beside max_tokens: no larger request
    #    is dispatched
    if project and ledger_data:
        directory = metadata_dir if metadata_dir is not None and metadata_dir.is_dir() else None
        derived = _derived_input_bound(phase, project, ledger_data, directory)
        if derived is not None:
            bound, source = derived
            window = _context_window(registration, ledger_data, directory) if type(max_tokens) is int else None
            if window is not None and window > max_tokens and sum(bound.values()) > window - max_tokens:
                excess = sum(bound.values()) - (window - max_tokens)
                uncached_cut = min(bound["input_tokens"], excess)
                bound = {
                    **bound,
                    "input_tokens": bound["input_tokens"] - uncached_cut,
                    "cache_write": max(0, bound["cache_write"] - (excess - uncached_cut)),
                }
                source += f"; capped at the {window:,}-token window less {max_tokens:,} max_tokens"
            return bound, source

    # 6. Project-specific empirical baseline bounds
    if project and project in PROJECT_BASELINE_INPUT_BOUNDS:
        proj_bounds = PROJECT_BASELINE_INPUT_BOUNDS[project]
        if phase in proj_bounds:
            return proj_bounds[phase], f"baseline[{project}][{phase}]"

    # 7. Unresolved input bound: return None so caller fails closed rather than pricing as $0.00
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
            saved_request = extract_saved_snapshot(rc_state.get("request"), metadata_dir=metadata_dir)
    elif "typed_audit" in phase and ledger_data:
        ta_state = ledger_data.get("typed_audit")
        if isinstance(ta_state, Mapping) and "stages" in ta_state:
            stages = ta_state.get("stages", [])
            if stages and isinstance(stages[-1], Mapping):
                saved_request = extract_saved_snapshot(stages[-1].get("request"), metadata_dir=metadata_dir)
    if saved_request is None and metadata_dir is not None and metadata_dir.is_dir():
        # A count records the max_tokens its request was counted with (#5157; shared generation 2).
        counted = _phase_count_pin(phase, project, metadata_dir, ledger_data)
        saved_request = counted[0] if counted is not None else None

    output_cap = get_phase_output_cap(phase, saved_request=saved_request, registration=registration)
    output_cost = output_cap * RATE_OUTPUT

    input_bound, input_source = resolve_pending_input_bound(
        phase,
        project=project,
        ledger_data=ledger_data,
        custom_bounds=custom_bounds,
        metadata_dir=metadata_dir,
        registration=registration,
        max_tokens=output_cap,
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
        # Sized from earlier runs, not this one: the v10 CHORUS full request is
        # about 33k tokens over its baseline (#5117).
        "input_bound_static": input_source.startswith("baseline["),
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
    metadata_dir: Path | None = None,
    worst_case_cache: bool = False,
) -> dict[str, Any]:
    """Compute the complete live dollar readout for an API run ledger."""
    if isinstance(ledger_source, (str, Path)):
        path = Path(ledger_source)
        if not path.is_file():
            raise FileNotFoundError(f"Ledger file not found: {path}")
        if metadata_dir is None:
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
    candidate_models: list[str] = []
    if isinstance(identity.get("model"), str) and identity["model"].strip():
        candidate_models.append(identity["model"].strip())
    if registration and isinstance(registration.get("runtime"), Mapping):
        reg_model = registration["runtime"].get("model")
        if isinstance(reg_model, str) and reg_model.strip():
            candidate_models.append(reg_model.strip())
    for row in rows:
        if isinstance(row, Mapping) and isinstance(row.get("model"), str) and row["model"].strip():
            candidate_models.append(row["model"].strip())
    for model_name in candidate_models:
        if not rates_cover(model_name):
            raise ValueError(
                f"Dollar readout is priced at {RATES_MODEL} rates, which do not cover model {model_name!r}"
            )

    settled_cost = price_settled_rows(rows)
    settled_call_count = len(rows)
    seen_usage_ids: set[str] = {
        str(r["usage_id"])
        for r in rows
        if isinstance(r, Mapping) and isinstance(r.get("usage_id"), str) and r["usage_id"]
    }
    prior_gen_ids: set[str] = {
        str(gid) for gid in (ledger_data.get("prior_generation_ids") or []) if isinstance(gid, str) and gid
    }
    valid_gen_ids: set[str] = set(prior_gen_ids)
    if isinstance(ledger_data.get("generation_id"), str) and ledger_data["generation_id"]:
        valid_gen_ids.add(ledger_data["generation_id"])
    abandoned: list[dict[str, Any]] = []

    if metadata_dir and metadata_dir.is_dir() and resolved_project:
        # 1. Include archived sibling ledgers from prior_generation_ids if present
        if prior_gen_ids:
            for search_dir in (metadata_dir, metadata_dir / "intermediate"):
                if search_dir.is_dir():
                    for sib in sorted(search_dir.glob(f"*{resolved_project}*api_usage*.json")):
                        if ledger_file_str and sib.resolve() == Path(ledger_file_str).resolve():
                            continue
                        try:
                            sib_data = json.loads(sib.read_text(encoding="utf-8"))
                        except (OSError, ValueError):
                            continue
                        if not isinstance(sib_data, Mapping):
                            continue
                        if sib_data.get("generation_id") not in prior_gen_ids:
                            continue
                        for sib_row in sib_data.get("rows") or []:
                            if not isinstance(sib_row, Mapping):
                                continue
                            uid = sib_row.get("usage_id")
                            if isinstance(uid, str) and uid in seen_usage_ids:
                                continue
                            if isinstance(uid, str) and uid:
                                seen_usage_ids.add(uid)
                            settled_cost += price_settled_row(sib_row)
                            settled_call_count += 1

        # 2. Include abandoned attempts not already in rows: this generation's from
        #    its journal boundary, a prior generation's wherever it lies (#5117)
        for entry, _ in _abandoned_entries(ledger_data, metadata_dir, resolved_project):
            uid = entry.get("usage_id")
            if isinstance(uid, str) and uid in seen_usage_ids:
                continue
            if isinstance(uid, str) and uid:
                seen_usage_ids.add(uid)
            priced = price_abandoned_row(
                entry,
                project=resolved_project,
                ledger_data=ledger_data,
                custom_bounds=custom_bounds,
                registration=registration,
                metadata_dir=metadata_dir,
                worst_case_cache=worst_case_cache,
            )
            abandoned.append(priced)
            settled_cost += priced["dollars"]

        # 3. Include unrecorded reasoning JSONL entries whose usage_id is not in seen_usage_ids
        for search_dir in (metadata_dir, metadata_dir.parent):
            reasoning_path = search_dir / f"{resolved_project}_reasoning.jsonl"
            if reasoning_path.is_file():
                try:
                    for line in reasoning_path.read_text(encoding="utf-8", errors="replace").splitlines():
                        if not line.strip():
                            continue
                        entry = json.loads(line)
                        if not isinstance(entry, Mapping):
                            continue
                        uid = entry.get("usage_id")
                        if isinstance(uid, str) and uid in seen_usage_ids:
                            continue
                        entry_gen = entry.get("generation_id")
                        if valid_gen_ids and isinstance(entry_gen, str) and entry_gen and entry_gen not in valid_gen_ids:
                            continue
                        usage_src = entry.get("usage") if isinstance(entry.get("usage"), Mapping) else entry
                        out_toks = usage_src.get("output_tokens")
                        if isinstance(out_toks, (int, float)) and out_toks > 0:
                            if isinstance(uid, str) and uid:
                                seen_usage_ids.add(uid)
                            settled_cost += float(out_toks) * RATE_OUTPUT
                except (OSError, ValueError):
                    pass
                break

    pending_raw = ledger_data.get("pending_call")
    pending_info = None
    pending_worst_case: float | None = 0.0
    pending_unknown = False

    if pending_raw and isinstance(pending_raw, Mapping) and pending_raw.get("phase"):
        pending_model = pending_raw.get("model")
        if isinstance(pending_model, str) and pending_model.strip() and not rates_cover(pending_model.strip()):
            raise ValueError(
                f"Dollar readout is priced at {RATES_MODEL} rates, which do not cover pending model {pending_model!r}"
            )
        pending_ident = pending_raw.get("run_identity")
        if isinstance(pending_ident, Mapping):
            for key in ("project", "label", "method", "condition"):
                expected_val = identity.get(key)
                actual_val = pending_ident.get(key)
                if expected_val and actual_val and expected_val != actual_val:
                    raise ValueError(
                        f"Pending call run_identity[{key!r}]={actual_val!r} conflicts with ledger identity {expected_val!r}"
                    )
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
        # Included in settled_dollars; listed so each price can be read.
        "abandoned_calls": len(abandoned),
        "abandoned_dollars": sum(row["dollars"] for row in abandoned),
        "abandoned_input_bound_static": any(bool(row.get("input_bound_static")) for row in abandoned),
        "abandoned_attempts": abandoned,
        "has_pending_call": pending_info is not None,
        "pending_input_bound_unknown": pending_unknown,
        "pending_input_bound_static": bool(pending_info and pending_info.get("input_bound_static")),
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
    abandoned = summary.get("abandoned_attempts") or []
    if abandoned:
        open_ended = sum(1 for row in abandoned if not row.get("final_usage"))
        lines.append(
            f"  of which abandoned attempts: {len(abandoned):3d} | ${summary['abandoned_dollars']:10.8f}"
            f" ({open_ended} without final usage, output priced at max_tokens)"
        )
        for row in abandoned:
            if row.get("input_bound_static"):
                lines.append(
                    f"WARNING: abandoned {row['phase']} input is a static baseline from earlier runs "
                    f"({row['input_source']}); it may be low for this run"
                )

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
        lines.append(f"Pending input bound: {p['input_bound_source']}")
        if p.get("input_bound_static"):
            lines.append(
                f"WARNING: pending {p['phase']} input is a static baseline from earlier runs "
                f"({p['input_bound_source']}); it may be low for this run"
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
