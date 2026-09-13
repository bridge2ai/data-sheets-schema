"""Validate scope and applicability of general-context semantic assessments.

Older instruments retain their historical contracts. Version 2 adds explicit
context and per-resource scores without changing semantic score domains.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from data_sheets_schema.evaluation_context import (
    COLLECTION_POLICY, context_digest, dataset_units, normalize_context,
)
from data_sheets_schema.judge_contract import _equal, _number, evaluation_contract

_CLASSIFICATION_ONLY = object()


def validate_scope(result: dict, *, document: dict | None = None, input_sha256: str | None = None,
                   expected_context: dict | None | object = _CLASSIFICATION_ONLY):
    if result.get("version") != "2.0":
        return
    rubric_name = result.get("rubric", "").removesuffix("-semantic")
    if rubric_name not in {"rubric10", "rubric20"}:
        raise ValueError("unknown general-context semantic rubric")
    context = normalize_context(result.get("applicability_context"))
    # Historical structural classification can check internal consistency.
    # New-output acceptance with an input must use independent caller context;
    # omission means unknown, never the evaluator's own N/A declaration.
    if expected_context is not _CLASSIFICATION_ONLY or document is not None or input_sha256 is not None:
        trusted = normalize_context(None if expected_context is _CLASSIFICATION_ONLY else expected_context)
        if context != trusted:
            raise ValueError("evaluation applicability context does not match the supplied caller context")
        context = trusted
    scope = result.get("evaluation_scope")
    if not isinstance(scope, dict) or scope.get("collection_metadata_inherited") is not False:
        raise ValueError("version 2 requires an explicit non-inherited evaluation scope")
    units = scope.get("units")
    if not isinstance(units, list) or not units or any(
            not isinstance(unit, dict) or not isinstance(unit.get("path"), str) for unit in units):
        raise ValueError("evaluation scope must list every resource path")
    paths = [unit["path"] for unit in units]
    if len(paths) != len(set(paths)) or any(not path.startswith("#") for path in paths):
        raise ValueError("resource paths must be unique JSON pointers")
    policy = COLLECTION_POLICY if len(paths) > 1 else "single_dataset"
    if scope.get("policy") != policy:
        raise ValueError("evaluation scope has an unsupported aggregation policy")
    if document is not None:
        actual = [{"path": path, "id": unit.get("id")} for path, unit in dataset_units(document)]
        if units != actual:
            raise ValueError("evaluation scope omits or changes input resource identities")
    metadata = result.get("metadata") or {}
    if metadata.get("context_sha256") != context_digest(context):
        raise ValueError("evaluation context does not match its recorded digest")
    if input_sha256 is not None and metadata.get("input_sha256") != input_sha256:
        raise ValueError("evaluation input does not match its recorded digest")

    # Version-2 rules are the source rubric's declared predicate assignments.
    # The instrument boundary records these bytes; future rule revisions need
    # another version instead of reinterpreting previously accepted scores.
    rubric_path = Path(__file__).resolve().parents[2] / "data/rubric" / f"{rubric_name}.txt"
    raw = rubric_path.read_bytes()
    specification = yaml.safe_load(raw)
    if metadata.get("rubric_sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("semantic assessment uses another rubric; validate with its pinned instrument")
    contract = evaluation_contract(rubric_name, specification, context, {"id": "scope-contract"})
    rules = contract["items"]
    seen = set()
    excluded = []
    total = adjusted = 0
    groups = result.get("elements" if rubric_name == "rubric10" else "categories", [])
    for group in groups:
        items = group.get("sub_elements" if rubric_name == "rubric10" else "questions", [])
        group_points = group_adjusted = group_fixed = 0
        for item in items:
            key = item.get("item_id") if rubric_name == "rubric10" else f"Q{item.get('id')}"
            if key not in rules or key in seen:
                raise ValueError(f"unknown or duplicate semantic item: {key}")
            if rubric_name == "rubric10" and not key.startswith(f"E{group['id']}."):
                raise ValueError(f"{key}: sub-element assigned to another element")
            seen.add(key)
            rule = rules[key]
            if item.get("name") != rule["name"]:
                raise ValueError(f"{key}: item name does not match the source rubric")
            value = item.get("applicable")
            applicable = value is True or value == "true"
            if value not in (True, False, "true", "false") or isinstance(value, int) and not isinstance(value, bool):
                raise ValueError(f"{key}: explicit applicability is required")
            if applicable != rule["applicable"]:
                raise ValueError(f"{key}: applicability contradicts the declared context")
            if item.get("applicability_status") != rule["status"]:
                raise ValueError(f"{key}: applicability status contradicts the declared context")
            if not isinstance(item.get("applicability_evidence"), str) or not item["applicability_evidence"].strip():
                raise ValueError(f"{key}: applicability evidence is required")
            rows = item.get("unit_scores")
            if not isinstance(rows, list) or len(rows) != len(paths) or any(
                    not isinstance(row, dict) for row in rows) or sorted(
                        str(row.get("path")) for row in rows) != sorted(paths):
                raise ValueError(f"{key}: score every input resource exactly once")
            scores = []
            for row in rows:
                if not isinstance(row.get("evidence"), str) or not row["evidence"].strip():
                    raise ValueError(f"{key}: every resource needs evidence or an explicit gap")
                if not applicable:
                    if row.get("score") is not None:
                        raise ValueError(f"{key}: an excluded resource needs a null score")
                else:
                    score = _number(row.get("score"), f"{key}.unit_score")
                    domain = (0, 1) if rule["fixed_max_score"] == 1 else (0, 3, 5)
                    if score not in domain:
                        raise ValueError(f"{key}: resource score is outside the semantic domain")
                    scores.append(score)
            if applicable:
                _equal(item.get("score"), min(scores), f"{key}.score")
                group_points += min(scores)
                group_adjusted += rule["max_score"]
            else:
                if item.get("score") is not None:
                    raise ValueError(f"{key}: an excluded item needs a null score")
                excluded.append(key)
            group_fixed += rule["fixed_max_score"]
            if rubric_name == "rubric20":
                _equal(item.get("max_score"), rule["fixed_max_score"], f"{key}.max_score")
        if rubric_name == "rubric10":
            _equal(group.get("element_score"), group_points, "element_score")
            _equal(group.get("element_max"), group_adjusted, "element_max")
        else:
            _equal(group.get("category_score"), group_points, "category_score")
            _equal(group.get("category_max"), group_fixed, "category_max")
        total += group_points
        adjusted += group_adjusted
    if seen != set(rules):
        raise ValueError("semantic assessment must cover every rubric item")
    fixed = sum(rule["fixed_max_score"] for rule in rules.values())
    overall = result["overall_score"]
    for key, expected in (("total_points", total), ("max_points", fixed),
                          ("adjusted_max_points", adjusted), ("excluded_max_points", fixed - adjusted),
                          ("sub_elements_not_applicable" if rubric_name == "rubric10" else "questions_not_applicable",
                           len(excluded))):
        _equal(overall.get(key), expected, key)
    if adjusted:
        _equal(overall.get("normalized_percentage"), 100 * total / adjusted, "normalized_percentage", 0.051)
    elif overall.get("normalized_percentage") is not None:
        raise ValueError("zero applicable maximum requires null normalized_percentage")
