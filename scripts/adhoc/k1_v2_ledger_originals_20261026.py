#!/usr/bin/env python3
"""Audit K1 ledger rows and observed worker timing, 2026-10-26.

Inputs: K1 calibration JSON, read-only launch-base ledgers/journals, preserved
AGY archive/manifest, and PR #5096 review N1/N2. Outputs: pinned JSON/Markdown
under notes/k1_v2_2026-10-26. Serves K1v2/#5150/#5157. Offline only. Historical
accounting is not scientific acceptance; TTLs are assumptions, not route facts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[2]
DATES = ("2026-10-20a", "2026-10-22a")
LEDGER_NAMES = ("CHORUS_api_usage_8d1427f7e332bdc2.json",
                "CHORUS_api_usage_90e59e50c9d423fe.json")
NUMERIC_FIELDS = ("input_tokens", "output_tokens", "thinking_tokens", "cache_read",
                  "cache_write", "max_tokens")
AUDIT_FIELDS = (*NUMERIC_FIELDS, "phase", "attempt", "started_at", "seconds",
                "stop_reason", "outcome", "source_review_admission")
MISSING = object()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique_object)


class Reader:
    def __init__(self):
        self.pins = {}

    def raw(self, path):
        path = Path(path).resolve()
        raw = path.read_bytes()
        pin = {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}
        if str(path) in self.pins and self.pins[str(path)] != pin:
            raise ValueError(f"input changed during analysis: {path}")
        self.pins[str(path)] = pin
        return raw

    def json(self, path):
        return decode(self.raw(path))

    def pin(self, path):
        self.raw(path)
        return self.pins[str(Path(path).resolve())]

    def verify(self):
        for path, pin in self.pins.items():
            if digest(Path(path).read_bytes()) != pin["sha256"]:
                raise ValueError(f"input changed after analysis: {path}")


def indexed(rows):
    result = {}
    for row in rows:
        key = row["usage_id"]
        if not isinstance(key, str) or not key or key in result:
            raise ValueError("missing, invalid or duplicate usage ID")
        result[key] = row
    return result


def encoded(value):
    return {"present": False} if value is MISSING else {"present": True, "value": value}


def differences(before, after, path=""):
    """All changed leaves, distinguishing missing, null, false, zero and type."""
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(before.keys() | after.keys()):
            escaped = key.replace("~", "~0").replace("/", "~1")
            result.extend(differences(before.get(key, MISSING), after.get(key, MISSING),
                                      f"{path}/{escaped}"))
        return result
    if isinstance(before, list) and isinstance(after, list):
        result = []
        for i in range(max(len(before), len(after))):
            result.extend(differences(before[i] if i < len(before) else MISSING,
                                      after[i] if i < len(after) else MISSING, f"{path}/{i}"))
        return result
    if before is after or (type(before) is type(after) and before == after):
        return []
    return [{"path": path or "/", "before": encoded(before), "after": encoded(after)}]


def compare_rows(before_rows, after_rows, *, derived_after=False):
    before, after = indexed(before_rows), indexed(after_rows)
    matched = []
    for usage_id in sorted(before.keys() & after.keys()):
        left, right = before[usage_id], after[usage_id]
        if derived_after:
            # K1 adds estimator fields. Preserve every original/raw field and
            # every audit field; absence must not be normalized to zero/null.
            fields = left.keys() | set(AUDIT_FIELDS)
            right = {key: right[key] for key in fields if key in right}
        delta = differences(left, right)
        matched.append({"usage_id": usage_id, "phase_before": left.get("phase"),
                        "phase_after": right.get("phase"), "identical": not delta,
                        "differences": delta})
    return {"before_count": len(before), "after_count": len(after),
            "matched_count": len(matched), "matched_rows": matched,
            "changed_matched_row_count": sum(not r["identical"] for r in matched),
            "removed_rows": [before[key] for key in sorted(before.keys() - after.keys())],
            "added_rows": [after[key] for key in sorted(after.keys() - before.keys())],
            "added_row_limit": "Absent from the earlier snapshot; addition alone does not establish an improper edit."}


def verify_archive(reader, preserved):
    manifest = preserved / "MANIFEST.sha256"
    entries = {}
    for line in reader.raw(manifest).decode().splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(maxsplit=1)
        relative = relative.removeprefix("*")
        path = (preserved / relative).resolve()
        path.relative_to(preserved.resolve())
        if str(path) in entries:
            raise ValueError("duplicate manifest path")
        entries[str(path)] = expected
    archive = preserved / "chorus_rep1_unmodified_archive"
    verified = []
    for path in sorted(archive.iterdir()):
        if not path.is_file():
            raise ValueError("unexpected non-file in original archive")
        raw = reader.raw(path)
        if entries.get(str(path.resolve())) != digest(raw):
            raise ValueError(f"archive manifest mismatch or missing entry: {path}")
        verified.append(reader.pin(path))
    return {"manifest": reader.pin(manifest), "verified_archive_files": verified,
            "scope": "Every regular file in chorus_rep1_unmodified_archive; no claim to validate unrelated preserved scratch files against the manifest."}


def original_search(reader, preserved):
    """Ignored/hidden-inclusive bounded file/content inventory; no git search."""
    files, candidates, mentions, nonregular = [], [], [], []
    needles = (b"2026-10-22a", b"90e59e50c9d423fe", b"77aec593797d45d9a83cd474a70cff0f")
    for directory, dirs, names in os.walk(preserved, followlinks=False):
        dirs.sort()
        for name in list(dirs):
            path = Path(directory) / name
            if path.is_symlink():
                nonregular.append(str(path.relative_to(preserved)))
                dirs.remove(name)
        for name in sorted(names):
            path = Path(directory) / name
            relative = str(path.relative_to(preserved))
            if path.is_symlink() or not path.is_file():
                nonregular.append(relative)
                continue
            raw = reader.raw(path)
            files.append({"relative_path": relative, "bytes": len(raw), "sha256": digest(raw)})
            if any(needle in raw or needle in relative.encode() for needle in needles):
                mentions.append(relative)
            if raw.lstrip().startswith(b"{"):
                try:
                    value = decode(raw)
                except (ValueError, UnicodeDecodeError):
                    continue
                if isinstance(value, dict) and isinstance(value.get("rows"), list) and "identity" in value:
                    candidates.append({"relative_path": relative, "identity": value["identity"],
                                       "generation_id": value.get("generation_id"), "row_count": len(value["rows"])})
    originals_22 = [r for r in candidates if r.get("identity", {}).get("label", "").startswith(DATES[1])]
    return {"scope": str(preserved), "method": "os.walk without ignore rules, includes hidden names; read and SHA256 every regular file, search all bytes for 10-22 identifiers, parse standalone JSON objects for ledger identity/rows",
            "ignored_and_hidden_included": True, "files": files, "nonregular_not_followed": nonregular,
            "standalone_ledger_candidates": candidates, "ten22_identifier_mentions": mentions,
            "ten22_standalone_ledger_count": len(originals_22),
            "conclusion": "No standalone 10-22 ledger found in this preserved subtree." if not originals_22 else "10-22 ledger candidates require provenance review.",
            "limit": "Bounded to this subtree. Does not prove absence from every worktree, Git history, private transcript, encoded blob or remote storage; no 10-22 pre-edit ledger is independently verified."}


def timestamp(row):
    value = datetime.fromisoformat(row["started_at"])
    if value.tzinfo is None:
        raise ValueError("timestamp lacks timezone")
    seconds = row["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError("invalid call duration")
    return value


def transition(before, after):
    start_before, start_after = timestamp(before), timestamp(after)
    end_before = start_before + timedelta(seconds=before["seconds"])
    return {"from_usage_id": before["usage_id"], "to_usage_id": after["usage_id"],
            "from_phase": before["phase"], "to_phase": after["phase"],
            "start_to_start_seconds": round((start_after - start_before).total_seconds(), 6),
            "previous_end_to_start_seconds": round((start_after - end_before).total_seconds(), 6),
            "previous_seconds": before["seconds"]}


def ttl_classification(pair, ttl):
    if not math.isfinite(ttl) or ttl <= 0:
        raise ValueError("TTL must be positive")
    youngest, oldest = pair["previous_end_to_start_seconds"], pair["start_to_start_seconds"]
    if youngest < 0:
        return "overlap_cache_publication_unknown"
    if oldest < ttl:
        return "within_ttl_for_both_timestamp_endpoints"
    if youngest >= ttl:
        return "expired_for_both_timestamp_endpoints"
    return "depends_on_cache_write_or_refresh_time"


def timing(runs):
    workers, excluded, all_transitions, worker_transitions, durations = [], [], [], [], []
    for run in runs:
        rows = sorted(run["rows"], key=timestamp)
        for a, b in zip(rows, rows[1:]):
            all_transitions.append({"date": run["date"], **transition(a, b)})
        selected = []
        for row in rows:
            durations.append({"date": run["date"], **{k: row[k] for k in ("usage_id", "phase", "started_at", "seconds", "max_tokens", "stop_reason")}})
            if row["phase"] != "typed_audit_worker":
                continue
            record = {"date": run["date"], **row,
                      "timing_matches_preserved_original": row["usage_id"] in run["original_matching_timing_ids"]}
            if row["stop_reason"] == "end_turn" and row["max_tokens"] == 64000:
                selected.append(row)
                workers.append(record)
            else:
                excluded.append({**record, "reason": "Different cap or incomplete response; not a routine successful worker/retry-rate sample."})
        for a, b in zip(selected, selected[1:]):
            worker_transitions.append({"date": run["date"], **transition(a, b)})
    scenarios = []
    for ttl in (300, 3600):
        pairs = [{**pair, "classification": ttl_classification(pair, ttl)} for pair in worker_transitions]
        lower = sum(p["classification"] == "within_ttl_for_both_timestamp_endpoints" for p in pairs)
        upper = sum(p["classification"] != "expired_for_both_timestamp_endpoints" for p in pairs)
        scenarios.append({"assumed_ttl_seconds": ttl, "transitions": pairs,
                          "assumed_cold_calls_one_per_run": len(runs),
                          "possible_hits_min": lower, "possible_hits_max": upper,
                          "worker_calls": len(workers),
                          "possible_hit_share_min": lower / len(workers),
                          "possible_hit_share_max": upper / len(workers),
                          "assumptions": "Identical shared prefix implemented and accepted for caching; one cold start per canary; cache created/refreshed during each preceding call; no eviction, route change or intervening activity. Bounds concern timing only, not provider availability or measured hit probability."})
    secs = [r["seconds"] for r in workers]
    gaps = [r["previous_end_to_start_seconds"] for r in worker_transitions]
    return {"selected_completed_workers": workers, "excluded_workers": excluded,
            "all_settled_durations": durations, "all_adjacent_settled_transitions": all_transitions,
            "adjacent_completed_worker_transitions": worker_transitions,
            "completed_worker_seconds": {"count": len(secs), "minimum": min(secs), "maximum": max(secs),
                                          "mean": statistics.mean(secs), "median": statistics.median(secs)},
            "end_to_next_start_seconds": {"count": len(gaps), "minimum": min(gaps), "maximum": max(gaps)},
            "observed_worker_cache_tokens": {key: sum(r[key] for r in workers) for key in ("input_tokens", "cache_write", "cache_read")},
            "ttl_scenarios": scenarios,
            "limits": ["No provider/cache API was queried. 300s and 3600s are hypothetical TTL scenarios, not confirmed current route settings or prices.",
                       "Timestamps are second-resolution ledger values, durations have millisecond precision; boundary classifications are conditional on those recorded values.",
                       "Cache publication/refresh instant, prefix eligibility and actual eviction are unobserved. No assumed hit is an observed saving.",
                       "All six selected worker rows have zero observed cache-read tokens. Only the 10-20 worker rows are independently matched to the preserved original.",
                       "Both canaries are evidence-only; 10-22 was manually resumed and has no verified pre-edit ledger. Do not infer permitted production retries or accepted-run outcomes."]}


def analyze(repo, executions):
    reader = Reader()
    calibration_path = repo / "notes/k1_cost_model_2026-10-25/ledger_calibration.json"
    calibration = reader.json(calibration_path)
    preserved = executions / "evidence/agy-scratch-preserved-2026-10-25"
    review_path = executions / "plans/reviews/pr5096_3a292504f_review_2026-10-24.md"
    review_pin = reader.pin(review_path)
    archive_check = verify_archive(reader, preserved)
    search = original_search(reader, preserved)
    originals = [(path, reader.json(path)) for path in sorted((preserved / "chorus_rep1_unmodified_archive").glob("CHORUS_api_usage_*.json"))]
    results, timing_runs = [], []
    for date, name in zip(DATES, LEDGER_NAMES):
        folder = executions / "launch-base/data/d4d_concatenated/claudecode_api_core" / f"{date}_claude-opus-5-api-generic-v10_rep1"
        ledger_path, abandoned_path = folder / name, folder / "CHORUS_abandoned_attempts.jsonl"
        ledger = reader.json(ledger_path)
        abandoned = [decode(line) for line in reader.raw(abandoned_path).splitlines() if line.strip()]
        rows, calibrated = ledger["rows"], [r for r in calibration["settled_rows"] if r["date"] == date]
        if ledger["identity"]["label"] != f"{date}_claude-opus-5-api-generic-v10_rep1":
            raise ValueError("unexpected ledger identity")
        settled_ids, abandoned_ids = indexed(rows), indexed(abandoned)
        if settled_ids.keys() & abandoned_ids.keys():
            raise ValueError("overlapping settled/abandoned usage IDs")
        comparisons, verified_timing = [], set()
        for path, original in originals:
            if original["identity"] != ledger["identity"]:
                continue
            comparison = compare_rows(original["rows"], rows)
            matched_original = indexed(original["rows"])
            for row in rows:
                prior = matched_original.get(row["usage_id"])
                if prior and all(prior.get(key, MISSING) == row.get(key, MISSING) for key in ("phase", "started_at", "seconds", "max_tokens", "stop_reason")):
                    verified_timing.add(row["usage_id"])
            comparisons.append({"original": reader.pin(path), "original_to_edited_rows": comparison,
                                "original_to_k1_rows": compare_rows(original["rows"], calibrated, derived_after=True),
                                "all_nonrow_ledger_differences": differences({k:v for k,v in original.items() if k != "rows"}, {k:v for k,v in ledger.items() if k != "rows"})})
        prior_pin = next(run["ledger"] for run in calibration["runs"] if run["date"] == date)
        results.append({"date": date, "edited_ledger": reader.pin(ledger_path),
                        "k1_recorded_ledger_pin": prior_pin,
                        "k1_source_bytes_still_match": prior_pin["sha256"] == reader.pin(ledger_path)["sha256"],
                        "edited_to_k1_rows": compare_rows(rows, calibrated, derived_after=True),
                        "original_comparisons": comparisons,
                        "abandoned_journal": reader.pin(abandoned_path),
                        "abandoned_rows": abandoned,
                        "abandoned_to_k1_rows": compare_rows(abandoned, [r for r in calibration["abandoned_rows"] if r["date"] == date], derived_after=True),
                        "original_evidence_limit": "Archive is a partial later snapshot, not a pre-run provenance authority; it already contains registration/receipt re-pinning documented by N2." if comparisons else "UNKNOWN: no pre-edit ledger verified. N1 documents state/stage/failure edits and deleted usage-ID reference; those statements do not independently prove every usage counter survived unchanged."})
        timing_runs.append({"date": date, "rows": rows, "original_matching_timing_ids": verified_timing})
    report = {"format": "d4d_k1_v2_original_ledger_audit_v1", "calibration": reader.pin(calibration_path),
              "review_n1_n2": review_pin, "archive_verification": archive_check,
              "bounded_original_search": search, "runs": results, "worker_timing": timing(timing_runs),
              "interpretation": ["Compare raw accounting fields separately from source_review_admission, typed-stage state and response hashes; end_turn is a transport/model completion, not scientific acceptance.",
                                 "Both canaries remain evidence-only (D31/D40). Historical spend/timing may inform conditional estimates; do not rehabilitate outcomes, infer ordinary retry permission, or use them for scoring.",
                                 "No 10-22 pre-edit original was verified. The documented edit targeted state/stage/failure metadata and a usage-ID reference; usage-row invariance cannot be certified from the edited ledger alone.",
                                 "Every matched raw-row difference and every non-row ledger difference against each available original is retained below; new rows absent from an earlier snapshot are listed separately."]}
    reader.verify()
    report["input_pins"] = sorted(reader.pins.values(), key=lambda p:p["path"])
    return report


def markdown(report):
    lines = ["# K1 v2: original-ledger and timing audit", "", "Generated offline on 2026-10-26. Both canaries remain evidence-only; this report does not establish scientific acceptance or billing reconciliation.", "",
             "## Original-row comparison", "", "| Run / preserved snapshot | Matched rows | Changed matched rows | Added later rows |", "|---|---:|---:|---:|"]
    for run in report["runs"]:
        for comparison in run["original_comparisons"]:
            value = comparison["original_to_edited_rows"]
            lines.append(f"| {run['date']} / {Path(comparison['original']['path']).name} | {value['matched_count']} | {value['changed_matched_row_count']} | {len(value['added_rows'])} |")
        if not run["original_comparisons"]:
            lines.append(f"| {run['date']} / no verified pre-edit original | unknown | unknown | unknown |")
    covered_ids, changed_core = set(), []
    core_fields = set(AUDIT_FIELDS) - {"source_review_admission"}
    for run in report["runs"]:
        for comparison in run["original_comparisons"]:
            for row in comparison["original_to_edited_rows"]["matched_rows"]:
                covered_ids.add(row["usage_id"])
                changed_core.extend((row["usage_id"], d["path"]) for d in row["differences"]
                                    if d["path"].split("/")[1] in core_fields)
    k1_comparisons = [run[key] for run in report["runs"] for key in ("edited_to_k1_rows", "abandoned_to_k1_rows")]
    all_rows_match = all(not c["changed_matched_row_count"] and not c["added_rows"] and not c["removed_rows"] for c in k1_comparisons)
    settled_count = sum(run["edited_to_k1_rows"]["after_count"] for run in report["runs"])
    abandoned_count = sum(run["abandoned_to_k1_rows"]["after_count"] for run in report["runs"])
    all_pins_match = all(run["k1_source_bytes_still_match"] for run in report["runs"])
    lines += ["", f"The preserved snapshots cover {len(covered_ids)} distinct usage IDs. There are {len(set(changed_core))} distinct changed input/output/thinking, cache read/write, maximum-output, phase, attempt, duration, timestamp, model-stop or outcome fields among matched rows. Admission/response-pin changes are listed separately below. Later rows absent from every original remain independently unverified.", "",
              f"Surviving ledger hashes match K1's recorded source hashes: **{all_pins_match}**. Raw fields in the {settled_count} settled rows and {abandoned_count} abandoned rows match K1's extracted copies: **{all_rows_match}**. That internal consistency cannot authenticate edited outcomes or substitute for the missing 10-22 original.", "",
              "Every changed matched row (all raw fields; missing is distinct from null):", ""]
    for run in report["runs"]:
        for comparison in run["original_comparisons"]:
            for row in comparison["original_to_edited_rows"]["matched_rows"]:
                for delta in row["differences"]:
                    lines.append(f"- `{row['usage_id']}` `{delta['path']}`: `{json.dumps(delta['before'], sort_keys=True)}` → `{json.dumps(delta['after'], sort_keys=True)}`.")
    lines += ["", "The JSON records every comparison, including K1-versus-edited rows, all non-row ledger differences, and later additions. A later row absent from an earlier snapshot is not by itself evidence of an improper edit. The 10-20 originals already follow earlier registration/receipt re-pinning documented in review N2.", "",
              "For 10-22, N1 documents a manual terminal-state reset, stage edits, deletion of a failure field and usage-ID reference, and another paid integration call. The surviving edited counters cannot independently prove that all original usage rows are unchanged. Accepted/checked states are not trusted outcomes.", "",
              "## Bounded absence evidence", "",
              f"The ignored/hidden-inclusive inventory read all {len(report['bounded_original_search']['files'])} regular files under `{report['bounded_original_search']['scope']}`. It found {report['bounded_original_search']['ten22_standalone_ledger_count']} standalone 10-22 ledger candidates. Filename/content matches, hashes, nonregular exclusions and parsed ledger candidates are retained in the JSON. This is a subtree-limited finding, not a global absence claim.", "",
              "## Worker duration and cache timing", "", "| Run | Usage ID | Seconds | Original timing matched |", "|---|---|---:|---|"]
    for row in report["worker_timing"]["selected_completed_workers"]:
        lines.append(f"| {row['date']} | `{row['usage_id']}` | {row['seconds']:.3f} | {row['timing_matches_preserved_original']} |")
    stats = report["worker_timing"]["completed_worker_seconds"]
    lines += ["", f"Six completed 64k-cap workers took {stats['minimum']:.3f}–{stats['maximum']:.3f}s (mean {stats['mean']:.3f}s). The separate truncated 25k-cap attempt is excluded from this timing sample and cannot establish ordinary retry permission.", "",
              "| Run | Start-to-start seconds | Previous-end-to-start seconds |", "|---|---:|---:|"]
    for pair in report["worker_timing"]["adjacent_completed_worker_transitions"]:
        lines.append(f"| {pair['date']} | {pair['start_to_start_seconds']:.3f} | {pair['previous_end_to_start_seconds']:.3f} |")
    lines += ["", "A hypothetical shared-prefix cache has two cold starts across these two three-worker runs. Assuming each preceding request creates/refreshes it sometime between that request's start and end, the observed timing yields:", "", "| Assumed TTL | Possible timing hits / six calls | Caveat |", "|---|---:|---|"]
    for scenario in report["worker_timing"]["ttl_scenarios"]:
        lines.append(f"| {scenario['assumed_ttl_seconds']}s | {scenario['possible_hits_min']}–{scenario['possible_hits_max']} / {scenario['worker_calls']} | Conditional timing bounds, not observed cache hits |")
    lines += ["", "All six workers recorded zero cache-read tokens. A 300s or 3600s TTL, creation/refresh timing, stable shared prefix, route support and eviction policy are scenario assumptions; no current provider fact or price is asserted. Do not credit these hypothetical savings to the baseline budget before implementation and route verification. Timestamp rounding matters near boundaries.", "",
              "Input SHA256s, exact raw differences, stage timing and abandoned-attempt fields are in [ledger_originals.json](ledger_originals.json). The helper is [k1_v2_ledger_originals_20261026.py](../../scripts/adhoc/k1_v2_ledger_originals_20261026.py)."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--executions", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "notes/k1_v2_2026-10-26")
    args = parser.parse_args()
    report = analyze(args.repo.resolve(), args.executions.resolve())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "ledger_originals.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    (args.output / "ledger_originals.md").write_text(markdown(report))
    print(json.dumps({"output": str(args.output), "runs": [{"date":r["date"], "k1_source_bytes_still_match":r["k1_source_bytes_still_match"], "edited_to_k1_changed":r["edited_to_k1_rows"]["changed_matched_row_count"], "originals":len(r["original_comparisons"])} for r in report["runs"]], "worker_timing": report["worker_timing"]["completed_worker_seconds"]}))


if __name__ == "__main__":
    main()
