"""Adapt accepted API item maxima for the semantic HTML presentation."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math

import yaml

from data_sheets_schema.judge_contract import evaluation_contract
from data_sheets_schema.resources import resource_path


def for_rendering(result: dict) -> dict:
    """Return a presentation copy; never change the stored evaluation."""
    result = deepcopy(result)
    overall = result.get("overall_score") or {}
    if "fixed_max_points" not in overall:
        return result  # Semantic and earlier result formats already use fixed item maxima.
    rubric = result.get("rubric")
    if rubric not in {"rubric10", "rubric20"}:
        raise ValueError("fixed_max_points requires a recognized API rubric")
    r10 = rubric == "rubric10"
    groups = result["elements" if r10 else "categories"]
    items = [item for group in groups for item in group["sub_elements" if r10 else "questions"]]
    rules = None
    if any("fixed_max_score" not in item for item in items):
        # Earlier API outputs retained the rubric hash but omitted fixed
        # item maxima. Recover only from those exact rubric bytes.
        raw = resource_path(f"data/rubric/{rubric}.txt").read_bytes()
        if (result.get("metadata") or {}).get("rubric_hash") != hashlib.sha256(raw).hexdigest():
            raise ValueError("API item maxima require the recorded rubric; its bytes are unavailable or changed")
        rules = evaluation_contract(rubric, yaml.safe_load(raw), None, {"id": "render-contract"})["items"]
    fixed_total = adjusted_total = 0
    for item in items:
        fixed = item.get("fixed_max_score")
        if fixed is None:
            key = item["id"] if r10 else f"Q{item['id']}"
            if rules is None or key not in rules:
                raise ValueError("API item identity is not in the recorded rubric")
            fixed = rules[key]["fixed_max_score"]
        if isinstance(fixed, bool) or not isinstance(fixed, (int, float)) or not math.isfinite(fixed) or fixed <= 0:
            raise ValueError("API fixed item maxima must be positive finite numbers")
        adjusted = item.get("max_score")
        expected_adjusted = 0 if item.get("score") is None else fixed
        if adjusted != expected_adjusted:
            raise ValueError("API item fixed and adjusted maxima disagree")
        fixed_total += fixed
        adjusted_total += adjusted
        # Semantic category cards sum fixed maxima, excluding null scores
        # separately for their adjusted denominator.
        item["max_score"] = fixed
    if fixed_total != overall["fixed_max_points"] or adjusted_total != overall.get("max_points"):
        raise ValueError("API item maxima disagree with the overall denominators")
    return result
