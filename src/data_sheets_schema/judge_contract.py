"""Acceptance contract for the direct API judge's general-context instrument.

This is distinct from the semantic agents' score domains. Rubric10 is binary;
rubric20 numeric questions retain the direct judge's continuous 0–5 scale.
"""
from __future__ import annotations

import math

from data_sheets_schema.evaluation_context import (
    COLLECTION_POLICY, applicability, dataset_units, normalize_context,
)

VERSION = "2.0-general-context"


def evaluation_contract(rubric_name, rubric, context, document):
    context = normalize_context(context)
    units = [{"path": path, "id": unit.get("id")} for path, unit in dataset_units(document)]
    if rubric_name == "rubric10":
        items = [(f"E{element['id']}.{index}", item, 1)
                 for element in rubric["d4d_complex_proxy_rubric"]["rubric"]
                 for index, item in enumerate(element["sub_elements"], 1)]
    else:
        items = [(f"Q{item['id']}", item, 1 if item["score_type"] == "pass_fail" else 5)
                 for item in rubric["d4d_evaluation_rubric"]["rubric"]]
    decisions = {}
    for key, item, maximum in items:
        decision = applicability(item.get("applies_to"), context)
        decisions[key] = {
            "name": item["name"],
            "applicable": decision.applicable, "status": decision.status,
            "evidence": decision.evidence, "fixed_max_score": maximum,
            "max_score": maximum if decision.applicable else 0,
        }
    return {
        "version": VERSION, "context": context, "items": decisions,
        "scope": {"policy": COLLECTION_POLICY if len(units) > 1 else "single_dataset",
                  "units": units, "collection_metadata_inherited": False},
    }


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


def _equal(actual, expected, name, tolerance=1e-8):
    if abs(_number(actual, name) - expected) > tolerance:
        raise ValueError(f"{name} disagrees with the item scores or applicable maxima")


def validate_result(result, rubric_name, project, method, contract):
    """Refuse mismatched identity, applicability, coverage, domains or totals."""
    if not isinstance(result, dict):
        raise ValueError("the judge result must be an object")
    if result.get("metadata") is not None and not isinstance(result["metadata"], dict):
        raise ValueError("judge metadata must be an object")
    for name, expected in (("rubric", rubric_name), ("project", project),
                           ("method", method), ("version", VERSION)):
        if result.get(name) != expected:
            raise ValueError(f"judge {name} does not match the requested evaluation")
    expected_items = contract["items"]
    seen = set()
    excluded = []
    unit_paths = [unit["path"] for unit in contract["scope"]["units"]]

    def item_score(item, key):
        if not isinstance(item, dict) or key not in expected_items or key in seen:
            raise ValueError(f"unknown or duplicate judge item: {key}")
        seen.add(key)
        rule = expected_items[key]
        if item.get("name") != rule["name"]:
            raise ValueError(f"{key}: item name does not match the source rubric")
        if item.get("applicable") is not rule["applicable"]:
            raise ValueError(f"{key}: applicability contradicts the declared context")
        _equal(item.get("max_score"), rule["max_score"], f"{key}.max_score")
        if not rule["applicable"]:
            if item.get("score") is not None or not isinstance(item.get("na_reason"), str) or not item["na_reason"].strip():
                raise ValueError(f"{key}: N/A requires null score and a reason")
            excluded.append(key)
        rows = item.get("unit_scores")
        if not isinstance(rows, list) or len(rows) != len(unit_paths):
            raise ValueError(f"{key}: score every dataset resource")
        if any(not isinstance(row, dict) for row in rows) or sorted(
                str(row.get("path")) for row in rows) != sorted(unit_paths):
            raise ValueError(f"{key}: unit paths must cover the declared resources exactly")
        scores = []
        for row in rows:
            if not isinstance(row.get("evidence"), str) or not row["evidence"].strip():
                raise ValueError(f"{key}: each resource needs evidence or an explicit missing-evidence statement")
            if not rule["applicable"]:
                if row.get("score") is not None:
                    raise ValueError(f"{key}: N/A resource score must be null")
                continue
            value = _number(row.get("score"), f"{key}.unit_score")
            if rule["fixed_max_score"] == 1:
                if value not in (0, 1):
                    raise ValueError(f"{key}: binary score must be 0 or 1")
            elif not 0 <= value <= rule["fixed_max_score"]:
                raise ValueError(f"{key}: numeric score is outside 0–5")
            scores.append(value)
        if not rule["applicable"]:
            return 0, 0
        minimum = min(scores)
        _equal(item.get("score"), minimum, f"{key}.score")
        return minimum, rule["max_score"]

    total = maximum = 0
    if rubric_name == "rubric10":
        groups = result.get("elements")
        if not isinstance(groups, list):
            raise ValueError("rubric10 requires elements")
        ids = set()
        expected_groups = {int(key.split(".")[0][1:]) for key in expected_items}
        for group in groups:
            if not isinstance(group, dict) or type(group.get("id")) is not int or group["id"] in ids:
                raise ValueError("element identities must be unique integers")
            if group["id"] not in expected_groups:
                raise ValueError("unknown rubric element")
            ids.add(group["id"])
            subs = group.get("sub_elements")
            if not isinstance(subs, list) or not subs:
                raise ValueError("every element requires sub_elements")
            points = cap = 0
            for item in subs:
                key = item.get("id") if isinstance(item, dict) else None
                if not isinstance(key, str) or not key.startswith(f"E{group['id']}."):
                    raise ValueError("sub-element identity must name its parent element")
                value, limit = item_score(item, key)
                points += value
                cap += limit
            _equal(group.get("element_score"), points, "element_score")
            _equal(group.get("element_max"), cap, "element_max")
            total += points
            maximum += cap
    else:
        groups = result.get("categories")
        if not isinstance(groups, list):
            raise ValueError("rubric20 requires categories")
        blocks = set()
        for group in groups:
            questions = group.get("questions") if isinstance(group, dict) else None
            if not isinstance(questions, list) or not questions:
                raise ValueError("every category requires questions")
            members = {((item["id"] - 1) // 5) for item in questions
                       if isinstance(item, dict) and type(item.get("id")) is int}
            if len(members) != 1 or members & blocks:
                raise ValueError("rubric20 categories must separately cover Q1–5, Q6–10, Q11–15 and Q16–20")
            blocks.update(members)
            points = cap = 0
            for item in questions:
                if not isinstance(item, dict) or type(item.get("id")) is not int:
                    raise ValueError("question identities must be integers")
                value, limit = item_score(item, f"Q{item['id']}")
                points += value
                cap += limit
            _equal(group.get("category_score"), points, "category_score")
            _equal(group.get("category_max"), cap, "category_max")
            total += points
            maximum += cap
    if seen != set(expected_items):
        raise ValueError("judge result does not cover every rubric item")
    overall = result.get("overall_score")
    if not isinstance(overall, dict):
        raise ValueError("overall_score is required")
    _equal(overall.get("total_points"), total, "overall total_points")
    _equal(overall.get("max_points"), maximum, "overall max_points")
    if maximum:
        _equal(overall.get("percentage"), 100 * total / maximum, "overall percentage", 0.051)
    elif overall.get("percentage") is not None:
        raise ValueError("zero applicable maximum requires null percentage")
    fixed = sum(item["fixed_max_score"] for item in expected_items.values())
    overall.update({"fixed_max_points": fixed,
                    "fixed_percentage": 100 * total / fixed if fixed else None,
                    "excluded_items": excluded})
    result["applicability_context"] = contract["context"]
    result["evaluation_scope"] = contract["scope"]
    return result
