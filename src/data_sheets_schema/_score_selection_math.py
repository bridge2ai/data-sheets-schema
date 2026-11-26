"""Pure arithmetic for the registered score_gap_v1 policy, issue 6385.

Inputs are evidence-table rows, never scorer files. Missing measurements stay
None. The conservative lead rulings for review issues 6388 to 6394 are recorded
as reasons, without changing the registered arithmetic or inventing a spread
heterogeneity cutoff.
"""

from __future__ import annotations

from copy import deepcopy
import math
from pathlib import PurePosixPath, PureWindowsPath
import re
from statistics import mean, stdev


RUBRICS = ("rubric10", "rubric20")
FIXED_MAXIMA = {"rubric10": 50, "rubric20": 88}
INSTRUMENT_HASHES = ("definition_sha256", "schema_sha256", "rubric_sha256",
                     "runner_sha256", "evidence_authority_sha256")
MEASURED_HASHES = (*INSTRUMENT_HASHES, "record_sha256", "scope_sha256",
                   "context_sha256", "prompt_sha256")


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _statistics(values):
    return {"mean": mean(values) if values else None,
            "spread": stdev(values) if len(values) >= 2 else None,
            "count": len(values)}


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _portable_text(value):
    # Error messages can embed the path that failed. Keep the specific failure
    # but never turn a machine-local evidence root into canonical metadata.
    return re.sub(r"(?<![\w:./\\])(?:[A-Za-z]:[\\/]|\\\\|/)[^\s\"'<>;,]+", "[external path]", str(value))


def _portable(value):
    if isinstance(value, dict):
        return {key: _portable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_portable(item) for item in value]
    return _portable_text(value) if isinstance(value, str) else deepcopy(value)


def _publication(cell):
    path = cell.get("publication_path", cell.get("publication", cell.get("path")))
    if not isinstance(path, str) or not path:
        return None
    if PurePosixPath(path).is_absolute() or PureWindowsPath(path).is_absolute():
        return None
    if ".." in PurePosixPath(path).parts or ".." in PureWindowsPath(path).parts:
        return None
    return path


def _portable_cell(cell):
    refused = cell.get("refused_attempt")
    return {"scoring_number": cell.get("scoring_number"), "status": cell.get("status"),
            "points": cell.get("points"), "maximum": cell.get("maximum"),
            "adjusted_max_points": cell.get("adjusted_max_points"),
            "percentage": cell.get("percentage"), "attempt": cell.get("attempt"),
            "publication_path": _publication(cell),
            "publication_sha256": cell.get("publication_sha256", cell.get("sha256")),
            "receipt_sha256": cell.get("receipt_sha256"), "plan_sha256": cell.get("plan_sha256"),
            "manifest_sha256": cell.get("manifest_sha256"),
            "measurement_identity": _portable(cell.get("measurement_identity")),
            "reason": _portable_text(cell["reason"]) if cell.get("reason") else None,
            "refused_attempt": ({"receipt_sha256": refused.get("receipt_sha256", refused.get("sha256")),
                                 "plan_sha256": refused.get("plan_sha256"),
                                 "reason": _portable_text(refused.get("reason", "refused attempt"))}
                                if isinstance(refused, dict) else None)}


def _identity_problem(identity, instrument_id):
    if not isinstance(identity, dict):
        return "measured input identity missing"
    missing = [key for key in MEASURED_HASHES if not _digest(identity.get(key))]
    if missing:
        return "missing or invalid pinned identity: " + ", ".join(missing)
    if not isinstance(identity.get("instrument_id"), str) or not identity["instrument_id"]:
        return "measured instrument id missing"
    if identity["instrument_id"] != instrument_id:
        return "measured instrument id differs from row"
    return None


def summarize(row):
    """Summarize accepted measurements and preserve every unusable cell.

    A duplicate never gives an attempt another vote. Identity drift makes the
    rubric ineligible. Missing standard cells are synthesized for the census;
    all observed extra cells remain visible, although T only covers three.
    """
    problems = list(row.get("eligibility_problems") or []) + list(row.get("evidence_issues") or [])
    measured, rubrics, evidence, missing = {}, {}, {}, []
    for rubric in RUBRICS:
        family = row.get("rubrics", {}).get(rubric, {})
        problems.extend(f"{rubric}: {item}" for item in family.get("eligibility_problems", []))
        cells = list(family.get("scorings", []))
        observed = {cell.get("scoring_number") for cell in cells
                    if type(cell.get("scoring_number")) is int}
        for number in (1, 2, 3):
            if number not in observed:
                cells.append({"scoring_number": number, "status": "not measured",
                              "reason": "scoring cell is absent"})
        numbers, values, identities, portable_cells = set(), {}, [], []
        for cell in sorted(cells, key=lambda item: str(item.get("scoring_number"))):
            number = cell.get("scoring_number")
            saved = _portable_cell(cell)
            saved["usable"] = False
            portable_cells.append(saved)
            issue = None
            if type(number) is not int or number < 1:
                issue = "invalid scoring number"
            elif number in numbers:
                issue = f"duplicate scoring number {number}"
                values.pop(number, None)
                for prior in portable_cells:
                    if prior["scoring_number"] == number:
                        prior["usable"] = False
            else:
                numbers.add(number)
                if cell.get("status") != "measured":
                    issue = "not measured: " + str(cell.get("reason") or "no accepted measurement")
                else:
                    points, maximum = cell.get("points"), cell.get("maximum")
                    identity = cell.get("measurement_identity")
                    if not (_number(points) and _number(maximum) and maximum > 0 and 0 <= points <= maximum):
                        issue = "invalid points or maximum"
                    elif maximum != FIXED_MAXIMA[rubric]:
                        issue = "maximum differs from fixed rubric maximum"
                    elif cell.get("adjusted_max_points") != maximum:
                        issue = "adjusted maximum differs from fixed maximum"
                    elif (not _number(cell.get("percentage"))
                          or not math.isclose(100.0 * points / maximum, cell["percentage"], rel_tol=0, abs_tol=1e-9)):
                        issue = "percentage differs from points"
                    else:
                        issue = _identity_problem(identity, row.get("instrument_id"))
                    if issue is None and (type(cell.get("attempt")) is not int or cell["attempt"] not in (1, 2)):
                        issue = "invalid published attempt"
                    if issue is None:
                        identities.append(identity)
                        values[number] = 100.0 * points / maximum
                        saved["usable"] = True
            if issue:
                reason = _portable_text(issue)
                problems.append(f"{rubric} scoring {number}: {reason}")
                saved["reason"] = reason
                missing.append({"rubric": rubric, "scoring_number": number, "reason": reason})
        if identities and any(identity != identities[0] for identity in identities[1:]):
            problems.append(f"{rubric}: measured inputs differ between scorings")
            values = {}
            for cell in portable_cells:
                if cell["usable"]:
                    cell["reason"] = "measured inputs differ between scorings; cell is unusable"
                    missing.append({"rubric": rubric, "scoring_number": cell["scoring_number"],
                                    "reason": cell["reason"]})
                cell["usable"] = False
        if any(type(number) is int and number > 3 for number in observed):
            problems.append(f"{rubric}: more than three scorings; threshold is defined for means of three")
        measured[rubric], evidence[rubric] = values, portable_cells
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
            "usable_paired_count": len(paired_numbers), "not_measured_cells": missing,
            "cells": evidence, "problems": sorted({_portable_text(item) for item in problems}),
            "_values": measured, "_paired_values": paired}


def _pool(groups):
    usable = [values for values in groups if len(values) >= 2]
    degrees = sum(len(values) - 1 for values in usable)
    square_sum = math.fsum(math.fsum((value - mean(values)) ** 2 for value in values)
                          for values in usable)
    return {"s": math.sqrt(square_sum / degrees) if degrees else None,
            "degrees_of_freedom": degrees, "records": len(usable)}


def _instrument_problems(rows):
    """Require all pins, and one set of instrument bytes per rubric."""
    problems = []
    for rubric in RUBRICS:
        identities = []
        for row in rows:
            for cell in row.get("rubrics", {}).get(rubric, {}).get("scorings", []):
                if cell.get("status") != "measured":
                    continue
                identity = cell.get("measurement_identity")
                issue = _identity_problem(identity, row.get("instrument_id"))
                if issue:
                    problems.append(f"{row['project']}/{row['label']} {rubric}: {issue}")
                identities.append(identity if isinstance(identity, dict) else {})
        for key in INSTRUMENT_HASHES:
            values = [identity.get(key) for identity in identities]
            if values and any(value is None or value != values[0] for value in values):
                problems.append(f"{rubric}: instrument {key} differs across records")
    return sorted(set(problems))


def _context_problems(rows):
    problems = []
    for project in sorted({row["project"] for row in rows}):
        contexts = set()
        for row in rows:
            if row["project"] != project:
                continue
            for rubric in RUBRICS:
                for cell in row.get("rubrics", {}).get(rubric, {}).get("scorings", []):
                    if cell.get("status") == "measured":
                        identity = cell.get("measurement_identity")
                        context = identity.get("context_sha256") if isinstance(identity, dict) else None
                        if isinstance(context, str):
                            contexts.add(context)
        if len(contexts) > 1:
            problems.append(f"{project}: applicability context differs across candidates or rubrics")
    return problems


def _census(summaries):
    return [{key: deepcopy(value) for key, value in row.items() if not key.startswith("_")}
            for row in summaries]


def pooled_variation(rows):
    """Return the full series census, diagnostic spread and fallback reasons.

    All records, including invalid records, enter the census. A partial pool may
    still be shown diagnostically, but any unusable cell makes every project
    fall back. Different instrument bytes are never pooled together.
    """
    rows = sorted(rows, key=lambda row: (row["project"], row["label"]))
    summaries = [summarize(row) for row in rows]
    identities = {row.get("instrument_id") for row in rows}
    incompatible = _instrument_problems(rows) + _context_problems(rows)
    if len(identities) > 1 or (identities and (None in identities or "" in identities)):
        incompatible.append("pooled variation requires exactly one named instrument")
    record_ids = [(row["project"], row["label"]) for row in rows]
    if len(set(record_ids)) != len(record_ids):
        incompatible.append("pooled variation contains a duplicate record")
    result = _pool([row["_paired_values"] for row in summaries])
    if incompatible:
        result = _pool([])
    result["instrument_id"] = next(iter(identities)) if len(identities) == 1 else None
    result["per_rubric"] = {
        rubric: _pool([list(row["_values"][rubric].values()) for row in summaries] if not incompatible else [])
        for rubric in RUBRICS}
    result["per_project"] = {}
    for project in sorted({row["project"] for row in summaries}):
        selected = [row for row in summaries if row["project"] == project]
        project_result = _pool([row["_paired_values"] for row in selected] if not incompatible else [])
        project_result["per_rubric"] = {
            rubric: _pool([list(row["_values"][rubric].values()) for row in selected] if not incompatible else [])
            for rubric in RUBRICS}
        result["per_project"][project] = project_result
    reasons = incompatible + [f"{row['project']}/{row['label']}: {problem}"
                              for row in summaries for problem in row["problems"]]
    if result["records"] < 2 and not incompatible:
        reasons.append("pooled variation has fewer than two records; noise estimate unavailable")
    if result["s"] == 0:
        reasons.append("pooled within-record variation is zero; noise estimate unavailable")
    result["series_census"] = _census(summaries)
    result["pool_suppressed"] = bool(incompatible)
    result["fallback_reasons"] = sorted({_portable_text(reason) for reason in reasons})
    result["not_measured_reason"] = "; ".join(result["fallback_reasons"]) or None
    result["percentage_base"] = {"kind": "fixed_max_points", "maxima": dict(FIXED_MAXIMA),
                                 "adjusted_max_points_must_equal_max_points": True}
    return result


def _coverage_key(row):
    slots = row.get("slots")
    return (-(slots if _number(slots) else -1), row["label"])


def _replacement_disclosures(summaries):
    result = []
    for row in summaries:
        for rubric in RUBRICS:
            for cell in row["cells"][rubric]:
                if cell.get("status") == "measured" and cell.get("attempt") == 2:
                    result.append({"label": row["label"], "project": row["project"], "rubric": rubric,
                                   **deepcopy(cell)})
    return result


def decide(table, pooled, instrument_id, *, policy_pick=None):
    """Return a portable decision record, using the caller's policy pick once."""
    rows = list(table)
    if not isinstance(instrument_id, str) or not instrument_id:
        raise ValueError("a named score instrument is required")
    if len({row["project"] for row in rows}) > 1:
        raise ValueError("selection table must describe one project")
    if len({row["label"] for row in rows}) != len(rows):
        raise ValueError("selection table contains a duplicate replicate")
    summaries = [summarize(row) for row in sorted(rows, key=lambda row: row["label"])]
    eligible = sorted((row for row in summaries if row["validity"] == "valid"), key=_coverage_key)
    if not eligible and policy_pick is None:
        raise ValueError("no valid replicate can be selected")
    if policy_pick is None:
        current = eligible[0]
    else:
        matches = [row for row in summaries if row["label"] == policy_pick]
        if len(matches) != 1:
            raise ValueError("supplied current policy pick is not one candidate")
        current = matches[0]
    record = {"name": "score_gap_v1", "instrument_id": instrument_id,
              "current_policy_pick": current["label"], "highest_mean_pick": None,
              "candidates": _census(summaries), "series_census": _portable(pooled.get("series_census", _census(summaries))),
              "s": None, "degrees_of_freedom": pooled.get("degrees_of_freedom", 0),
              "T": None, "gap": None, "rule": "policy_fallback", "fallback_reason": None,
              "variation": _portable(pooled), "replaced_cells": _replacement_disclosures(summaries),
              "percentage_base": {"kind": "fixed_max_points", "maxima": dict(FIXED_MAXIMA),
                                  "adjusted_max_points_must_equal_max_points": True},
              "tied_highest_mean": [], "tie_resolution": None}
    problems = _instrument_problems(rows) + _context_problems(rows)
    if current["validity"] != "valid":
        problems.append("current policy pick is not current-valid for score comparison")
    problems.extend(pooled.get("fallback_reasons") or [])
    for row in summaries:
        problems.extend(f"{row['label']}: {problem}" for problem in row["problems"])
    for row in eligible:
        if row["instrument_id"] != instrument_id:
            problems.append(f"{row['label']}: instrument differs")
        if len(row["paired_numbers"]) < 3:
            problems.append(f"{row['label']}: fewer than three paired scorings per rubric")
        elif len(row["paired_numbers"]) > 3 or row["paired_numbers"] != [1, 2, 3]:
            problems.append(f"{row['label']}: exactly scorings 1, 2 and 3 required; threshold is defined for means of three")
    s, degrees = pooled.get("s"), pooled.get("degrees_of_freedom")
    if pooled.get("instrument_id") != instrument_id:
        problems.append("pooled variation instrument differs or is not measured")
    if not pooled.get("pool_suppressed") and (type(pooled.get("records")) is not int or pooled["records"] < 2):
        problems.append("pooled variation has fewer than two records; noise estimate unavailable")
    if not (_number(s) and s > 0 and type(degrees) is int and degrees > 0):
        reason = pooled.get("not_measured_reason")
        problems.append(("pooled within-record variation is zero; noise estimate unavailable" if s == 0
                         else "pooled within-record variation is not measured")
                        + (": " + str(reason) if reason else ""))
    else:
        record["s"] = s
        record["T"] = 2 * s * math.sqrt(2 / 3)
    if problems:
        record["fallback_reason"] = "; ".join(sorted({_portable_text(problem) for problem in problems}))
        return {"selected": current["label"], "score_policy": record}
    highest = min(eligible, key=lambda row: (-row["paired"]["mean"], *_coverage_key(row)))
    tied = [row["label"] for row in eligible if row["paired"]["mean"] == highest["paired"]["mean"]]
    if len(tied) > 1:
        record["tied_highest_mean"] = sorted(tied)
        record["tie_resolution"] = ("conservative highest-mean tie: coverage then label chooses one H; "
                                    "if that H reverses a rubric, retain P without trying another tied candidate")
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
