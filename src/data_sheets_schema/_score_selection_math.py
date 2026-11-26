"""Pure arithmetic for the registered score_gap_v1 policy, issue 6385.

Inputs are evidence-table rows, never scorer files. Missing measurements stay
None. Percentage units are used throughout. The per-project variation report
supports owner review; this module invents no heterogeneity cutoff.
"""

from __future__ import annotations

from copy import deepcopy
import math
from statistics import mean, stdev


RUBRICS = ("rubric10", "rubric20")
INSTRUMENT_HASHES = ("definition_sha256", "schema_sha256", "rubric_sha256",
                     "runner_sha256", "evidence_authority_sha256")


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _statistics(values):
    return {"mean": mean(values) if values else None,
            "spread": stdev(values) if len(values) >= 2 else None,
            "count": len(values)}


def summarize(row):
    """Summarize comparable, accepted measurements without mutating evidence.

Duplicate scoring numbers never give an attempt a second vote. A duplicate or
identity mismatch makes that rubric ineligible, even if other cells suffice.
"""
    problems = list(row.get("eligibility_problems") or [])
    measured = {}
    rubrics = {}
    for rubric in RUBRICS:
        cells = row.get("rubrics", {}).get(rubric, {}).get("scorings", [])
        numbers = set()
        values = {}
        identities = []
        for cell in cells:
            number = cell.get("scoring_number")
            if not isinstance(number, int) or isinstance(number, bool) or number < 1:
                problems.append(f"{rubric}: invalid scoring number")
                continue
            if number in numbers:
                problems.append(f"{rubric}: duplicate scoring number {number}")
                values.pop(number, None)
                continue
            numbers.add(number)
            if cell.get("status") != "measured":
                problems.append(f"{rubric} scoring {number}: not measured")
                continue
            points, maximum = cell.get("points"), cell.get("maximum")
            identity = cell.get("measurement_identity")
            if not (_number(points) and _number(maximum) and maximum > 0 and 0 <= points <= maximum):
                problems.append(f"{rubric} scoring {number}: invalid points or maximum")
                continue
            percentage = 100.0 * points / maximum
            if (not _number(cell.get("percentage"))
                    or not math.isclose(percentage, cell["percentage"], rel_tol=0, abs_tol=1e-9)):
                problems.append(f"{rubric} scoring {number}: percentage differs from points")
                continue
            if not isinstance(identity, dict) or not identity or any(value is None for value in identity.values()):
                problems.append(f"{rubric} scoring {number}: measured input identity missing")
                continue
            if cell.get("attempt") not in (1, 2) or isinstance(cell.get("attempt"), bool):
                problems.append(f"{rubric} scoring {number}: invalid published attempt")
                continue
            identities.append(identity)
            values[number] = percentage
        if identities and any(identity != identities[0] for identity in identities[1:]):
            problems.append(f"{rubric}: measured inputs differ between scorings")
            values = {}
        measured[rubric] = values
        rubrics[rubric] = _statistics(list(values.values()))
    paired_numbers = sorted(set(measured[RUBRICS[0]]) & set(measured[RUBRICS[1]]))
    paired = [(measured[RUBRICS[0]][number] + measured[RUBRICS[1]][number]) / 2
              for number in paired_numbers]
    if set(measured[RUBRICS[0]]) != set(measured[RUBRICS[1]]):
        problems.append("rubric scoring numbers do not pair")
    return {"label": row["label"], "project": row["project"],
            "validity": row.get("validity"), "slots": row.get("slots"),
            "instrument_id": row.get("instrument_id"), "rubrics": rubrics,
            "paired": _statistics(paired), "paired_numbers": paired_numbers,
            "problems": sorted(set(problems)),
            "_values": measured, "_paired_values": paired}


def _pool(groups):
    usable = [values for values in groups if len(values) >= 2]
    degrees = sum(len(values) - 1 for values in usable)
    square_sum = math.fsum(math.fsum((value - mean(values)) ** 2 for value in values)
                          for values in usable)
    return {"s": math.sqrt(square_sum / degrees) if degrees else None,
            "degrees_of_freedom": degrees, "records": len(usable)}


def _instrument_problems(rows):
    """One instrument name cannot disguise different measured instrument bytes.

Record, scope, applicability context and prompt hashes vary by record. Rubric
definition and schema identities can differ between rubrics, but not between
records measured by the same named instrument. Generic pure-function fixtures
may omit these keys entirely; a partially present key never proves equality.
"""
    problems = []
    for rubric in RUBRICS:
        identities = []
        for row in rows:
            for cell in row.get("rubrics", {}).get(rubric, {}).get("scorings", []):
                if cell.get("status") != "measured":
                    continue
                identity = cell.get("measurement_identity")
                identity = identity if isinstance(identity, dict) else {}
                identities.append(identity)
                if "instrument_id" in identity and identity["instrument_id"] != row.get("instrument_id"):
                    problems.append(f"{rubric}: measured instrument id differs from row")
        for key in INSTRUMENT_HASHES:
            if any(key in identity for identity in identities):
                values = [identity.get(key) for identity in identities]
                if any(value is None or value != values[0] for value in values):
                    problems.append(f"{rubric}: instrument {key} differs across records")
    return sorted(set(problems))


def pooled_variation(rows):
    """Pooled within-record SD over one instrument's series, with sample df.

Selection validity does not exclude a record from the noise report: step 5
defines its population as all records with at least two comparable scorings.
Unpaired or missing cells contribute no score; they remain explicit in rows.
"""
    rows = list(rows)
    identities = {row.get("instrument_id") for row in rows}
    if len(identities) > 1 or (identities and (None in identities or "" in identities)):
        raise ValueError("pooled variation requires exactly one named instrument")
    record_ids = [(row["project"], row["label"]) for row in rows]
    if len(set(record_ids)) != len(record_ids):
        raise ValueError("pooled variation contains a duplicate record")
    instrument_problems = _instrument_problems(rows)
    if instrument_problems:
        raise ValueError("; ".join(instrument_problems))
    summaries = [summarize(row) for row in rows]
    result = _pool([row["_paired_values"] for row in summaries])
    result["instrument_id"] = next(iter(identities)) if identities else None
    result["per_rubric"] = {
        rubric: _pool([list(row["_values"][rubric].values()) for row in summaries])
        for rubric in RUBRICS}
    result["per_project"] = {}
    for project in sorted({row["project"] for row in summaries}):
        selected = [row for row in summaries if row["project"] == project]
        project_result = _pool([row["_paired_values"] for row in selected])
        project_result["per_rubric"] = {
            rubric: _pool([list(row["_values"][rubric].values()) for row in selected])
            for rubric in RUBRICS}
        result["per_project"][project] = project_result
    return result


def _coverage_key(row):
    slots = row.get("slots")
    return (-(slots if _number(slots) else -1), row["label"])


def _replacement_disclosures(rows):
    result = []
    for row in sorted(rows, key=lambda item: (item["project"], item["label"])):
        for rubric in RUBRICS:
            for cell in sorted(row.get("rubrics", {}).get(rubric, {}).get("scorings", []),
                               key=lambda item: str(item.get("scoring_number"))):
                if cell.get("status") == "measured" and cell.get("attempt") == 2:
                    result.append({"label": row["label"], "project": row["project"], "rubric": rubric,
                                   "scoring_number": cell["scoring_number"], "attempt": 2,
                                   "receipt": cell.get("receipt"), "receipt_sha256": cell.get("receipt_sha256"),
                                   "refused_attempt": deepcopy(cell.get("refused_attempt"))})
    return result


def decide(table, pooled, instrument_id):
    """Return the pick and complete score_policy record; do not write anything."""
    rows = list(table)
    if not isinstance(instrument_id, str) or not instrument_id:
        raise ValueError("a named score instrument is required")
    if len({row["project"] for row in rows}) > 1:
        raise ValueError("selection table must describe one project")
    if len({row["label"] for row in rows}) != len(rows):
        raise ValueError("selection table contains a duplicate replicate")
    summaries = [summarize(row) for row in sorted(rows, key=lambda row: row["label"])]
    eligible = sorted((row for row in summaries if row["validity"] == "valid"), key=_coverage_key)
    if not eligible:
        raise ValueError("no valid replicate can be selected")
    current = eligible[0]
    record = {"name": "score_gap_v1", "instrument_id": instrument_id,
              "current_policy_pick": current["label"], "highest_mean_pick": None,
              "candidates": [{key: deepcopy(value) for key, value in row.items() if not key.startswith("_")}
                             for row in summaries],
              "s": None, "degrees_of_freedom": pooled.get("degrees_of_freedom", 0),
              "T": None, "gap": None, "rule": "policy_fallback", "fallback_reason": None,
              "variation": deepcopy(pooled), "replaced_cells": _replacement_disclosures(rows)}
    problems = _instrument_problems([row for row in rows if row.get("validity") == "valid"])
    for row in eligible:
        if row["instrument_id"] != instrument_id:
            problems.append(f"{row['label']}: instrument differs")
        problems.extend(f"{row['label']}: {problem}" for problem in row["problems"])
        if len(row["paired_numbers"]) < 3:
            problems.append(f"{row['label']}: fewer than three paired scorings per rubric")
    s, degrees = pooled.get("s"), pooled.get("degrees_of_freedom")
    if pooled.get("instrument_id") != instrument_id:
        problems.append("pooled variation instrument differs or is not measured")
    if not (_number(s) and s >= 0 and isinstance(degrees, int) and not isinstance(degrees, bool) and degrees > 0):
        problems.append("pooled within-record variation is not measured")
    else:
        record["s"] = s
        record["T"] = 2 * s * math.sqrt(2 / 3)
    if problems:
        record["fallback_reason"] = "; ".join(sorted(set(problems)))
        return {"selected": current["label"], "score_policy": record}
    highest = min(eligible, key=lambda row: (-row["paired"]["mean"], *_coverage_key(row)))
    gap = highest["paired"]["mean"] - current["paired"]["mean"]
    record.update(highest_mean_pick=highest["label"], gap=gap)
    reversals = [rubric for rubric in RUBRICS
                 if highest["rubrics"][rubric]["mean"] < current["rubrics"][rubric]["mean"]]
    if highest["label"] == current["label"]:
        record["fallback_reason"] = "current policy pick has the highest mean"
    elif gap <= record["T"]:
        record["fallback_reason"] = "score gap is not greater than T"
    elif reversals:
        record["fallback_reason"] = "rubric mean reverses: " + ", ".join(reversals)
    else:
        record.update(rule="score_gap", fallback_reason=None)
        return {"selected": highest["label"], "score_policy": record}
    return {"selected": current["label"], "score_policy": record}
