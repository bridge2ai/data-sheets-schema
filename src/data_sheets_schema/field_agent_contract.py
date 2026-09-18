"""Non-mutating acceptance of version-2 field-agent evaluations (#2091).

These are neither API-template judgements nor semantic-agent evaluations.
Rubric20 field quality uses its six integer levels, including 1, 2 and 4.
For new serialized outputs, ``percentage`` (if present) is a fixed-base
alias; fixed_percentage and normalized_percentage are always required.
That serialization rule must be stated in the caller's registration: the
definitions' all-zero examples alone do not establish the alias's meaning.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

import yaml

from data_sheets_schema.duplicate_keys import find_duplicate_keys
from data_sheets_schema.evaluation_context import (
    context_digest, identity, normalize_context, unwrap_document,
)
from data_sheets_schema.judge_contract import evaluation_contract
from data_sheets_schema.resources import resource_path

RUBRICS = frozenset({"rubric10", "rubric20"})


def _object(value, name):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _text(value, name):
    return identity(value, name)


def _equal(actual, expected, name, tolerance=0):
    if (isinstance(actual, bool) or not isinstance(actual, (int, float)) or
            isinstance(actual, float) and not math.isfinite(actual) or
            not expected - tolerance <= actual <= expected + tolerance):
        raise ValueError(f"{name} differs from the trusted item scores or denominators")


def _strict_json(raw):
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError(f"duplicate evaluation JSON key: {key}")
            obj[key] = value
        return obj

    def constant(value):
        raise ValueError(f"nonfinite evaluation JSON constant: {value}")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            return constant(value)
        return number

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float)


def _yaml(raw, name):
    try:
        text = raw.decode("utf-8")
        if find_duplicate_keys(text):
            raise ValueError(f"{name} contains duplicate YAML keys")
        return yaml.safe_load(text)
    except (yaml.YAMLError, UnicodeError, RecursionError) as exc:
        raise ValueError(f"{name} is malformed YAML") from exc


def validate_result(result, *, rubric, project, method, document, input_sha256,
                    definition, context=None):
    """Check a candidate against caller-owned identity/context without repair.

    ``definition`` is the exact definition bytes. The caller independently
    pins those bytes and verifies the agent check-echo and observed runtime.
    This verifies structure, coverage and arithmetic, not evidence truth.
    """
    if not isinstance(rubric, str) or rubric not in RUBRICS:
        raise ValueError("unknown field-agent rubric")
    _object(result, "evaluation")
    for key, expected in (("rubric", rubric), ("version", "2.0"),
                          ("project", _text(project, "requested project")),
                          ("method", _text(method, "requested method"))):
        if result.get(key) != expected:
            raise ValueError(f"field-agent {key} does not match the requested evaluation")
    for key in ("d4d_file", "evaluation_timestamp"):
        _text(result.get(key), key)
    model = _object(result.get("model"), "model")
    _text(model.get("name"), "model.name")
    _text(model.get("evaluation_type"), "model.evaluation_type")
    # Model self-report is retained as such; transport evidence attests runtime.
    if "temperature" not in model:
        raise ValueError("model.temperature is required; use null when it was not observed")
    temperature = model["temperature"]
    if temperature is not None:
        if (isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or
                isinstance(temperature, float) and not math.isfinite(temperature)):
            raise ValueError("model.temperature must be finite or null")
    try:
        frontmatter = definition.decode("utf-8").split("---", 2)
        header = _yaml(frontmatter[1].encode(), "agent definition") if len(frontmatter) == 3 and not frontmatter[0].strip() else None
    except UnicodeError as exc:
        raise ValueError("agent definition is not UTF-8") from exc
    if not isinstance(header, dict) or header.get("name") != f"d4d-{rubric}":
        raise ValueError("agent definition does not name the requested field agent")

    context = normalize_context(context)
    if normalize_context(result.get("applicability_context")) != context:
        raise ValueError("evaluation applicability context differs from trusted caller context")
    raw = resource_path(f"data/rubric/{rubric}.txt").read_bytes()
    specification = _yaml(raw, "source rubric")
    metadata = _object(result.get("metadata"), "metadata")
    if not isinstance(input_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", input_sha256):
        raise ValueError("trusted input_sha256 must be a complete SHA256 digest")
    for key, expected in (("input_sha256", input_sha256),
                          ("instrument_sha256", hashlib.sha256(definition).hexdigest()),
                          ("rubric_sha256", hashlib.sha256(raw).hexdigest()),
                          ("context_sha256", context_digest(context))):
        if metadata.get(key) != expected:
            raise ValueError(f"metadata.{key} differs from the supplied input/instrument/context")
    contract = evaluation_contract(rubric, specification, context, document)
    scope = _object(result.get("evaluation_scope"), "evaluation_scope")
    if scope.get("collection_metadata_inherited") is not False or scope != contract["scope"]:
        raise ValueError("evaluation scope differs from input dataset/resource identities")
    if "applicability_context" not in result:
        raise ValueError("applicability_context is required, including an empty unknown context")
    unit_paths = [unit["path"] for unit in contract["scope"]["units"]]
    rules = contract["items"]
    is10 = rubric == "rubric10"
    groups = result.get("elements" if is10 else "categories")
    if not isinstance(groups, list) or len(groups) != (10 if is10 else 4):
        raise ValueError("field evaluation must contain every rubric group exactly once")
    source_groups = specification["d4d_complex_proxy_rubric"]["rubric"] if is10 else None
    source_questions = {q["id"]: q for q in specification["d4d_evaluation_rubric"]["rubric"]} if not is10 else {}
    seen, group_ids, excluded = set(), set(), []
    total = adjusted = 0
    for group in groups:
        _object(group, "rubric group")
        _text(group.get("name"), "group.name")
        items = group.get("sub_elements" if is10 else "questions")
        if not isinstance(items, list) or len(items) != 5:
            raise ValueError("every rubric group requires its five distinct items")
        if is10:
            group_id = group.get("id")
            if type(group_id) is not int or not 1 <= group_id <= 10:
                raise ValueError("element id must be an integer from 1 to 10")
            if group["name"] != source_groups[group_id - 1]["name"]:
                raise ValueError("element name differs from source rubric")
        else:
            if any(not isinstance(item, dict) or type(item.get("id")) is not int for item in items):
                raise ValueError("question ids must be integers")
            blocks = {(item["id"] - 1) // 5 for item in items}
            if len(blocks) != 1 or not blocks <= {0, 1, 2, 3}:
                raise ValueError("categories must separately cover Q1–5, Q6–10, Q11–15 and Q16–20")
            group_id = next(iter(blocks))
        if group_id in group_ids:
            raise ValueError("duplicate rubric group")
        group_ids.add(group_id)
        points = cap = fixed_group = 0
        for item in items:
            _object(item, "rubric item")
            key = item.get("item_id") if is10 else f"Q{item['id']}"
            if not isinstance(key, str) or key not in rules or key in seen:
                raise ValueError("unknown or duplicate field-agent item")
            if is10 and not key.startswith(f"E{group_id}."):
                raise ValueError("sub-element belongs to another element")
            seen.add(key)
            rule = rules[key]
            if item.get("name") != rule["name"]:
                raise ValueError(f"{key}: name differs from source rubric")
            if item.get("applicable") is not rule["applicable"] or item.get("applicability_status") != rule["status"]:
                raise ValueError(f"{key}: applicability differs from trusted caller context")
            for name in ("evidence", "quality_note", "applicability_evidence"):
                _text(item.get(name), f"{key}.{name}")
            if not is10:
                if item.get("score_type") != source_questions[item["id"]]["score_type"]:
                    raise ValueError(f"{key}: score_type differs from source rubric")
                _text(item.get("score_label"), f"{key}.score_label")
                _equal(item.get("max_score"), rule["fixed_max_score"], f"{key}.max_score")
            rows = item.get("unit_scores")
            if (not isinstance(rows, list) or len(rows) != len(unit_paths) or
                    any(not isinstance(row, dict) or not isinstance(row.get("path"), str) for row in rows) or
                    sorted(row["path"] for row in rows) != sorted(unit_paths)):
                raise ValueError(f"{key}: score every input resource exactly once")
            scores = []
            for row in rows:
                _text(row.get("evidence"), f"{key}.unit.evidence")
                score = row.get("score")
                if not rule["applicable"]:
                    if score is not None:
                        raise ValueError(f"{key}: excluded resource score must be null")
                else:
                    if type(score) is not int or not 0 <= score <= rule["fixed_max_score"]:
                        raise ValueError(f"{key}: resource score outside field-agent integer domain")
                    scores.append(score)
            if rule["applicable"]:
                if type(item.get("score")) is not int:
                    raise ValueError(f"{key}: item score must be an integer")
                _equal(item["score"], min(scores), f"{key}.score")
                points += min(scores)
                cap += rule["max_score"]
            else:
                if item.get("score") is not None:
                    raise ValueError(f"{key}: excluded item score must be null")
                excluded.append(key)
            fixed_group += rule["fixed_max_score"]
        _equal(group.get("element_score" if is10 else "category_score"), points, "group score")
        _equal(group.get("element_max" if is10 else "category_max"), cap if is10 else fixed_group, "group maximum")
        total += points
        adjusted += cap
    if seen != set(rules):
        raise ValueError("evaluation does not cover every source rubric item")
    fixed = sum(rule["fixed_max_score"] for rule in rules.values())
    overall = _object(result.get("overall_score"), "overall_score")
    for key, expected in (("total_points", total), ("max_points", fixed),
                          ("adjusted_max_points", adjusted), ("excluded_max_points", fixed - adjusted),
                          ("sub_elements_not_applicable" if is10 else "questions_not_applicable", len(excluded))):
        _equal(overall.get(key), expected, f"overall.{key}")
    _equal(overall.get("fixed_percentage"), 100 * total / fixed, "fixed_percentage", .051)
    if "percentage" in overall:
        _equal(overall["percentage"], 100 * total / fixed, "percentage fixed-base alias", .051)
    if adjusted:
        _equal(overall.get("normalized_percentage"), 100 * total / adjusted, "normalized_percentage", .051)
    elif overall.get("normalized_percentage") is not None or "normalized_percentage" not in overall:
        raise ValueError("zero applicable maximum requires null normalized_percentage")
    return {"rubric": rubric, "version": "2.0", "items_checked": len(seen),
            "units_checked": len(unit_paths), "excluded_items": sorted(excluded),
            "total_points": total, "fixed_max_points": fixed, "adjusted_max_points": adjusted}


def validate_output(path, *, rubric, project, method, input_path, definition_path, context_path=None):
    """Validate one named output, without reading sibling ratings or writing."""
    if input_path is None or definition_path is None:
        raise ValueError("field-agent validation requires --input and --agent-definition")
    try:
        result = _strict_json(Path(path).read_bytes())
        raw = Path(input_path).read_bytes()
        document = unwrap_document(_yaml(raw, "input D4D"))
        context = _yaml(Path(context_path).read_bytes(), "caller context") if context_path is not None else None
        return validate_result(result, rubric=rubric, project=project, method=method,
            document=document, input_sha256=hashlib.sha256(raw).hexdigest(),
            definition=Path(definition_path).read_bytes(), context=context)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("field-agent output/input is malformed or recursively nested") from exc
