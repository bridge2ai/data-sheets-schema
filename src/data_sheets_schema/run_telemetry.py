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
* The ``repair_rounds`` outcomes come from the provenance repair block,
  seeded across invocations since #366; every repair *call* also appears
  under ``phases`` from the cumulative usage rows.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from data_sheets_schema.api_runner import CONCAT_DIR

SCHEMA_PATH = Path("src/data_sheets_schema/schema/d4d_run_telemetry.yaml")
SCHEMA_VERSION = "1.3.0"

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
    "report": ("report", "report_after_repair", "report_regate"),
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
    if row.get("outcome"):
        a["outcome"] = str(row["outcome"])                 # an abandoned attempt (#1017)
    if row.get("unusable_reason"):
        # Display only — no branch reads it (#1048): a billed attempt whose
        # body the parser refused, otherwise indistinguishable from the one
        # accepted. Wall time and the reasoning join are unaffected.
        a["unusable_reason"] = str(row["unusable_reason"])
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
    # Gap measured from the END of one call (start + seconds) to the start
    # of the next: a 20-minute full-phase stream is one call, not an
    # invocation boundary. Start-to-start comparison over-counted 7
    # invocations on a single-invocation run.
    ends = [t + __import__("datetime").timedelta(seconds=r.get("seconds") or 0)
            for t, r in zip(stamps, rows)]
    gaps = sum(1 for e, b in zip(ends, stamps[1:])
               if (b - e).total_seconds() > _INVOCATION_GAP_SECONDS)
    return 1 + gaps


def _is_hollow(v: Any) -> bool:
    """Null, blank, empty — or a container whose every member is.

    False and 0 are values, not hollows. A whitespace-only string is hollow:
    it renders as content and carries none, which is the defect's whole
    shape.
    """
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, dict):
        return all(_is_hollow(x) for x in v.values())
    if isinstance(v, list):
        return all(_is_hollow(x) for x in v)
    return False


def count_hollows(v: Any) -> int:
    """Maximal hollow subtrees at any depth.

    A hollow object counts once, not once per empty member — the question is
    "how many hollows does a reader meet", not "how many empty cells exist".
    Mechanical kin of the form-defects `hollow_object` class, which is
    LLM-judged; this one is structural and free.
    """
    if _is_hollow(v):
        return 1
    if isinstance(v, dict):
        return sum(count_hollows(x) for x in v.values())
    if isinstance(v, list):
        return sum(count_hollows(x) for x in v)
    return 0


def _record_stats(artifact: str, path: Path) -> dict[str, Any] | None:
    """File and content statistics for one final artifact.

    Content figures require the YAML to parse to a mapping; a report (or a
    record that does not parse) carries file figures only — measured facts,
    never guessed ones.
    """
    if not path.exists():
        return None
    data = path.read_bytes()
    out: dict[str, Any] = {
        "artifact": artifact,
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "lines": data.count(b"\n") + (0 if data.endswith(b"\n") else 1),
    }
    if path.suffix in (".yaml", ".yml"):
        try:
            parsed = yaml.safe_load(data.decode("utf-8", errors="ignore"))
        except yaml.YAMLError:
            parsed = None
        if isinstance(parsed, dict):
            out["root_slot_count"] = len(parsed)
            out["populated_root_slot_count"] = sum(
                1 for v in parsed.values() if not _is_hollow(v))
            out["hollow_value_count"] = count_hollows(parsed)
    return out


#: The rule prediction 9 is read under (#1026). Registered here, in one
#: place, after the AI_READI 2026-09-04f row was read three ways: by hand
#: from rep2's retried attempt (86,707, +3.2%), then over the two replicates
#: with a provenance row alone, rep3 dropped (78,646, +13.8%); the rule
#: reads +4.4% (85,721, rep3 recovered from its reasoning log).
PREDICTION_9_RULE = (
    "accepted attempt per phase: the last `full` attempt that ended with `end_turn`, carries "
    "no `outcome` marker (an abandoned transport attempt, #1017) and no `unusable_reason` "
    "(a billed reply the runner refused, #1048) and reports `output_tokens` — a retried "
    "attempt is excluded; the phase is `full` alone (`full_readdress` and `repair_full` are "
    "their own phases and are not counted); where the provenance yields no accepted `full` "
    "attempt (a run resumed past that phase) it is recovered from the reasoning log under the "
    "same selection; the per-project baseline is the mean over every replicate that yields "
    "one, reported with the replicate range, and a replicate that yields none is named, not "
    "skipped silently")


def _accepted(attempts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The accepted attempt of a phase under `PREDICTION_9_RULE`: the last
    `end_turn` attempt that is neither an abandoned transport attempt nor a
    reply the runner refused as unusable, and that reports its tokens."""
    ended = [a for a in attempts if a.get("stop_reason") == "end_turn" and not a.get("outcome")
             and not a.get("unusable_reason") and a.get("output_tokens") is not None]
    return ended[-1] if ended else None


def accepted_full_output(run_dir: Path, project: str) -> dict[str, Any]:
    """One replicate's accepted `full` output under `PREDICTION_9_RULE`.

    `source` says which log the row came from: `api_usage` (the provenance
    record) or `reasoning_log` (the record carried no `full` row — a resume
    past that phase, like AI_READI 2026-09-01 rep3), or None with the reason
    when neither yields an accepted attempt.
    """
    prov_path = run_dir / f"{project}_provenance.yaml"
    out: dict[str, Any] = {"project": project, "label": run_dir.name, "output_tokens": None,
                           "attempt": None, "source": None, "attempts_seen": 0, "retried": 0}
    if not prov_path.exists():
        out["reason"] = "no provenance record"
        return out
    prov = yaml.safe_load(prov_path.read_text(encoding="utf-8")) or {}
    rows = [r for r in (prov.get("api_usage") or []) if isinstance(r, dict) and r.get("phase") == "full"]
    source = "api_usage"
    acc = _accepted(rows)
    logged: list[dict[str, Any]] = []
    if acc is None:
        # No *accepted* row — not merely no row (#1155 review, S3): a record
        # whose only `full` row is an abandoned attempt must still consult
        # the log, which holds the completed call the ledger seeding lost.
        # The log is a recovery source for rows the provenance *lost*, never
        # an override of what the provenance says about the same attempt
        # (round 2, M1): the log carries no `unusable_reason`, so a log entry
        # whose attempt the provenance recorded as refused or abandoned is
        # dropped before the log is read.
        refused = {r.get("attempt") for r in rows if r.get("unusable_reason") or r.get("outcome")}
        logged = [e for e in _reasoning_entries(run_dir / f"{project}_reasoning.jsonl")
                  if e.get("phase") == "full" and e.get("attempt") not in refused]
        acc = _accepted(logged)
        if acc is not None:
            rows, source = logged, "reasoning_log"
    out["attempts_seen"] = len(rows)
    if acc is None:
        seen = (f"{len(rows)} full row(s) in the provenance" if rows else "no full row in the provenance")
        seen += (f", {len(logged)} in the reasoning log" if logged else ", none in the reasoning log")
        out["reason"] = f"no accepted full attempt: {seen}"
        return out
    out.update({"output_tokens": int(acc["output_tokens"]), "attempt": acc.get("attempt"), "source": source,
                "retried": sum(1 for r in rows if r is not acc and r.get("stop_reason") == "end_turn"
                               and not r.get("outcome"))})
    return out


def full_output_baseline(method: str, labels: list[str], projects: list[str],
                         concat_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Per-project `full` output baseline over `labels` under
    `PREDICTION_9_RULE`: the replicates read, their accepted rows, the mean
    over those that yield one, and the ones that yield none by name."""
    concat_dir = concat_dir or CONCAT_DIR                 # resolved at call time, so a test can point it elsewhere
    out: dict[str, dict[str, Any]] = {}
    for project in projects:
        reps = [accepted_full_output(concat_dir / f"{method}_core" / label, project) for label in labels]
        values = [r["output_tokens"] for r in reps if r["output_tokens"] is not None]
        out[project] = {"rule": PREDICTION_9_RULE, "replicates": reps,
                        "mean": round(sum(values) / len(values)) if values else None,
                        # The spread beside the mean (#1155 review, S5): CM4AI's v7
                        # replicates span 26,766–66,300 around a mean of 41,370, and a
                        # ±10% band on that mean is weaker than the mean alone suggests.
                        "min": min(values) if values else None, "max": max(values) if values else None,
                        "n": len(values), "without_a_row": [r["label"] for r in reps if r["output_tokens"] is None]}
    return out


# Metrics compared across runs. Each entry: (metric name, unit, extractor).
# The `full` figures are the accepted attempt under `PREDICTION_9_RULE`
# (#1026): the first version took the first `end_turn` attempt, which on a
# retried phase is the attempt the run threw away.
_COMPARISON_METRICS = (
    ("full_phase_output_tokens", "tokens",
     lambda r: next(((_accepted(p["attempts"]) or {}).get("output_tokens")
                     for p in r["phases"] if p["phase"] == "full"), None)),
    ("full_phase_reasoning_tokens_estimate", "tokens",
     lambda r: next(((_accepted(p["attempts"]) or {}).get("reasoning_tokens_estimate")
                     for p in r["phases"] if p["phase"] == "full"), None)),
    ("total_output_tokens", "tokens",
     lambda r: r.get("total_output_tokens")),
    ("approx_cost_usd", "USD", lambda r: r.get("approx_cost_usd")),
    ("repair_call_count", "calls",
     lambda r: sum(len(p["attempts"]) for p in r["phases"]
                   if p["phase"].startswith("repair_")) or None),
    ("full_root_slot_count", "slots",
     lambda r: next((s.get("root_slot_count")
                     for s in r.get("records", [])
                     if s["artifact"] == "full"), None)),
    ("core_root_slot_count", "slots",
     lambda r: next((s.get("root_slot_count")
                     for s in r.get("records", [])
                     if s["artifact"] == "core"), None)),
    ("full_hollow_value_count", "hollows",
     lambda r: next((s.get("hollow_value_count")
                     for s in r.get("records", [])
                     if s["artifact"] == "full"), None)),
    ("core_hollow_value_count", "hollows",
     lambda r: next((s.get("hollow_value_count")
                     for s in r.get("records", [])
                     if s["artifact"] == "core"), None)),
    ("validation_problem_count", "artifacts",
     lambda r: r.get("validation_problem_count")),
)


def comparisons(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mechanical cross-run comparisons: numbers side by side, no judgement.

    A metric appears only when at least two runs carry it — a single value
    compares nothing.
    """
    out = []
    for metric, unit, get in _COMPARISON_METRICS:
        values = []
        for r in runs:
            v = get(r)
            if v is not None:
                values.append({"subject": f"{r['project']} "
                                          f"rep{r.get('replicate', '?')}",
                               "value": float(v)})
        if len(values) >= 2:
            out.append({"metric": metric, "unit": unit, "values": values})
    return out


# Globs, not single files (#374): the legacy scores.json keys label-less
# paths, and label-aware evaluation runs write their own scores.json under
# subdirectories. Every file is scanned; only exact artifact-path matches
# attach, so overlapping files cannot double-claim a run.
PRESENCE_SCORES_GLOB = "data/evaluation/**/scores.json"
LLM_SCORES_GLOB = "data/evaluation_llm/**/scores.json"


def _evaluations_for(artifact_paths: dict[str, Path],
                     scores_glob: str,
                     evaluation_type: str) -> list[dict[str, Any]]:
    """Rubric scores whose recorded file path matches this run's artifacts.

    Exact path match only: the published evaluation outputs are keyed by
    label-less legacy paths (#286), so for label-addressed runs this returns
    empty until the evaluators are run against the label's files — an
    honest absence, not a missing feature.
    """
    import glob as _glob
    entries: list[Any] = []
    for sp in sorted(_glob.glob(scores_glob, recursive=True)):
        scores_path = Path(sp)
        try:
            batch = json.loads(scores_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(batch, list):
            for e in batch:
                if isinstance(e, dict):
                    e["_source"] = str(scores_path)
            entries.extend(batch)
    if not entries:
        return []
    by_path = {str(p): art for art, p in artifact_paths.items()
               if art in ("full", "core")}
    out = []
    for e in entries:
        art = by_path.get(str(e.get("file_path", "")))
        if art is None:
            continue
        for rubric in ("rubric10", "rubric20"):
            r = e.get(rubric)
            if not isinstance(r, dict) or r.get("total") is None:
                continue
            score: dict[str, Any] = {
                "evaluation_type": evaluation_type,
                "rubric": rubric,
                "artifact": art,
                "score": float(r["total"]),
                "max_score": float(r.get("max", 0)),
                "source": e.get("_source", ""),
            }
            if r.get("percentage") is not None:
                score["percent"] = float(r["percentage"])
            if e.get("timestamp"):
                # The evaluator stamps naive microsecond timestamps; the
                # schema range is datetime and the validator's format check
                # rejects fractional seconds. Normalize, don't fabricate.
                try:
                    # astimezone() interprets a naive stamp as local time —
                    # which is what the evaluator's clock was — and gives the
                    # offset the date-time format requires.
                    score["evaluated_at"] = datetime.fromisoformat(
                        e["timestamp"]).astimezone().isoformat(
                        timespec="seconds")
                except ValueError:
                    pass
            if e.get("judge_model") or e.get("model"):
                score["judge_model"] = e.get("judge_model") or e.get("model")
            out.append(score)
    return out


def load_findings(path: Path) -> list[dict[str, Any]]:
    """Authored findings from a curated YAML file: a list of Finding dicts."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a list of findings")
    return data


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
        if row.get("outcome"):
            # An abandoned attempt (#1017) made no call the reasoning log
            # saw; it must not take the completed call's entry.
            phases.setdefault(ph, {"phase": ph, "attempts": []})
            phases[ph]["attempts"].append(_attempt(row, None))
            continue
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
        # An abandoned attempt's seconds lie inside its completed attempt's
        # window (the attempt timer starts before the retry ladder), so
        # they are not added again (#1038).
        wall = round(sum(r["seconds"] for r in rows if not r.get("outcome")), 1)
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
    records = [s for s in (
        _record_stats("full", artifact_paths["full"]),
        _record_stats("core", artifact_paths["core"]),
        _record_stats("report", artifact_paths["report"]))
        if s is not None]
    if records:
        out["records"] = records
    presence = _evaluations_for(artifact_paths, PRESENCE_SCORES_GLOB,
                                "presence")
    if presence:
        out["presence_evaluations"] = presence
    judged = _evaluations_for(artifact_paths, LLM_SCORES_GLOB,
                              "llm_judge")
    if judged:
        out["llm_judge_evaluations"] = judged
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
                   method: str | None = None,
                   root: Path | None = None,
                   findings: list[dict[str, Any]] | None = None,
                   ) -> dict[str, Any]:
    """A RunTelemetryReport over every run dir matching the label prefix.

    Comparisons are computed mechanically across the collected runs;
    findings are authored analysis passed in, never generated here.
    """
    if method is None:
        from data_sheets_schema.runs import method_for_label
        method = method_for_label(label_prefix, concat_dir=root)          # #934
    base = (root or CONCAT_DIR) / f"{method}_core"
    runs: list[dict[str, Any]] = []
    # Quarantined runs (.superseded-*, .failed-*) are evidence for closed
    # issues, not members of the sweep they were removed from.
    dirs = sorted(p for p in base.glob(f"{label_prefix}*")
                  if p.is_dir() and ".superseded" not in p.name
                  and ".failed" not in p.name)
    for d in dirs:
        for prov in sorted(d.glob("*_provenance.yaml")):
            project = prov.name.replace("_provenance.yaml", "")
            t = run_telemetry(d, project)
            if t:
                runs.append(t)
    report = {
        "label": label_prefix,
        "method": method,
        "generated_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "schema_version": SCHEMA_VERSION,
        "runs": runs,
    }
    comp = comparisons(runs)
    if comp:
        report["comparisons"] = comp
    if findings:
        report["findings"] = findings
    return report


# ---------------------------------------------------------------------------
# Trap-slot inventory (#360): mine every generated record for validation-
# failure sites. Valid records contribute zero rows, which is evidence too.

_PATH_IN_MSG = __import__("re").compile(r"^(?P<msg>.*?) in (?P<path>/\S*)$")
_INDEX = __import__("re").compile(r"/\d+(?=/|$)")


def _classify_error(msg: str) -> tuple[str, str | None]:
    """(error_class, expected) from one validator message."""
    if " is not of type " in msg:
        expected = msg.split(" is not of type ", 1)[1].strip()
        return "wrong_type", expected
    if "is not valid under any of the given schemas" in msg:
        return "union_mismatch", None
    if " is not one of " in msg:
        return "invalid_enum_value", msg.split(" is not one of ", 1)[1][:120]
    if "Additional properties are not allowed" in msg:
        return "undeclared_slot", None
    if "is a required property" in msg:
        return "missing_required", None
    return "other", None


def _observed_shape(msg: str) -> str:
    m = msg.lstrip()
    if m.startswith("'"):
        return "string"
    if m.startswith("{"):
        return "object"
    if m.startswith("["):
        return "array"
    if m.startswith(("True", "False")):
        return "boolean"
    if m.startswith("None"):
        return "null"
    if m[:1].isdigit() or m.startswith("-"):
        return "number"
    return "unknown"


def parse_validator_line(line: str) -> dict[str, Any] | None:
    """One structured finding from one `[ERROR] [...] msg in /path` line."""
    if "[ERROR]" not in line:
        return None
    body = line.split("]", 2)[-1].strip()
    m = _PATH_IN_MSG.match(body)
    msg, path = (m.group("msg"), m.group("path")) if m else (body, "(root)")
    error_class, expected = _classify_error(msg)
    return {"slot_path": _INDEX.sub("/*", path),
            "error_class": error_class,
            "expected": expected,
            "observed_shape": _observed_shape(msg),
            "message": msg[:200]}


def trap_inventory(root: Path | None = None,
                   corpus_note: str = "") -> dict[str, Any]:
    """Validate every *_d4d.yaml / *_d4d_core.yaml under root; aggregate.

    Slow (one validator subprocess per record); run it deliberately, not on
    import. Quarantined `.failed-*` files and ATTIC are excluded — the former
    are evidence for closed issues, the latter is archived.
    """
    from data_sheets_schema.api_runner import (
        CORE_SCHEMA_PATH, FULL_SCHEMA_PATH, _validator_lines)
    base = root or CONCAT_DIR
    files = sorted(p for p in base.rglob("*_d4d.yaml")
                   if "ATTIC" not in p.parts) + \
        sorted(p for p in base.rglob("*_d4d_core.yaml")
               if "ATTIC" not in p.parts)
    traps: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    scanned = with_errors = 0
    for f in files:
        core = f.name.endswith("_d4d_core.yaml")
        project = f.name.replace("_d4d_core.yaml", "").replace(
            "_d4d.yaml", "")
        method = f.relative_to(base).parts[0]
        lines, failure = _validator_lines(
            f, CORE_SCHEMA_PATH if core else FULL_SCHEMA_PATH,
            "CoreDataset" if core else "Dataset")
        if failure is not None:
            continue
        scanned += 1
        if lines:
            with_errors += 1
        for line in lines:
            parsed = parse_validator_line(line)
            if not parsed:
                continue
            key = (parsed["slot_path"], parsed["error_class"],
                   parsed["expected"])
            t = traps.setdefault(key, {
                "slot_path": parsed["slot_path"],
                "error_class": parsed["error_class"],
                **({"expected": parsed["expected"]}
                   if parsed["expected"] else {}),
                "observed_shapes": [], "occurrence_count": 0,
                "_records": set(), "projects": [], "methods": [],
                "examples": []})
            t["occurrence_count"] += 1
            t["_records"].add(str(f))
            if parsed["observed_shape"] not in t["observed_shapes"]:
                t["observed_shapes"].append(parsed["observed_shape"])
            if project not in t["projects"]:
                t["projects"].append(project)
            if method not in t["methods"]:
                t["methods"].append(method)
            if len(t["examples"]) < 2:
                t["examples"].append(parsed["message"][:160])
    rows = []
    for t in traps.values():
        t["record_count"] = len(t.pop("_records"))
        rows.append(t)
    rows.sort(key=lambda r: -r["occurrence_count"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "schema_version": SCHEMA_VERSION,
        "corpus_note": corpus_note or (
            "All *_d4d.yaml and *_d4d_core.yaml under data/d4d_concatenated "
            "excluding ATTIC and quarantined .failed-* files. Valid records "
            "contribute zero rows."),
        "records_scanned": scanned,
        "records_with_errors": with_errors,
        "traps": rows,
    }
