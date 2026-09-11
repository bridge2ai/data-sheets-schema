"""Expose both score bases and applicability differences in semantic reports (#829)."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Iterable


@dataclass(frozen=True)
class ScoreBases:
    total: float
    fixed_max: float
    adjusted_max: float

    @property
    def fixed_percentage(self) -> float:
        return 100 * self.total / self.fixed_max

    @property
    def adjusted_percentage(self) -> float | None:
        return 100 * self.total / self.adjusted_max if self.adjusted_max else None

    def labels(self) -> tuple[str, str]:
        fixed = f"Fixed: {self.total:g}/{self.fixed_max:g} ({self.fixed_percentage:.1f}%)"
        adjusted = f"N/A-adjusted: {self.total:g}/{self.adjusted_max:g}"
        pct = self.adjusted_percentage
        return fixed, adjusted + (f" ({pct:.1f}%)" if pct is not None else " (undefined)")


def score_bases(result: dict[str, Any], default_max: int) -> ScoreBases:
    """Read current or legacy totals without treating zero as missing.

    Percentages are derived from each named denominator. An old, unlabelled
    percentage must not be silently presented as an N/A-adjusted measurement.
    """
    overall = result.get("overall_score")
    if overall:
        total = overall["total_points"]
        maximum = overall.get("max_points", default_max)
        adjusted = overall.get("adjusted_max_points")
        if adjusted is None:
            adjusted = maximum - overall.get("excluded_max_points", 0)
    else:
        summary = result["summary_scores"]
        total = summary["total_score"]
        maximum = summary.get("total_max_score", default_max)
        adjusted = summary.get("adjusted_max_points")
        if adjusted is None:
            adjusted = maximum - summary.get("excluded_max_points", 0)
    values = (total, maximum, adjusted)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
           for v in values):
        raise ValueError("score totals and maxima must be finite numbers")
    if not (maximum > 0 and 0 <= total <= adjusted <= maximum):
        raise ValueError(f"invalid score bases: total={total}, fixed={maximum}, adjusted={adjusted}")
    source = overall or result["summary_scores"]
    if (source.get("excluded_max_points") is not None
            and source["excluded_max_points"] != maximum - adjusted):
        raise ValueError("excluded points disagree with the fixed and adjusted maxima")
    return ScoreBases(total, maximum, adjusted)


def _excluded(item: dict) -> bool:
    return (item.get("applicable") in (False, "false")
            or item.get("applicability_status") == "not_applicable"
            or ("score" in item and item["score"] is None))


def excluded_items(result: dict[str, Any]) -> tuple[str, ...] | None:
    """Item identities excluded by this evaluation; None means unspecified.

    Equal adjusted maxima do not establish equal applicability: excluding
    Q11 instead of Q14 used to cost the same five points.
    """
    names = []
    categories = result.get("categories") or []
    if isinstance(categories, dict):
        categories = categories.values()
    questions = list(result.get("questions") or [])
    for category in categories:
        questions.extend(category.get("questions") or [])
    for q in questions:
        if _excluded(q):
            names.append(f"Q{q['id']}")
    for element in result.get("elements") or []:
        for sub in element.get("sub_elements") or []:
            if _excluded(sub):
                names.append(f"E{element['id']}: {sub['name']}")
    overall = result.get("overall_score") or result.get("summary_scores") or {}
    maximum = overall.get("max_points", overall.get("total_max_score"))
    adjusted = overall.get("adjusted_max_points")
    excluded = overall.get("excluded_max_points", 0)
    if maximum is not None and adjusted is not None:
        excluded = maximum - adjusted
    if not names and excluded:
        return None
    return tuple(sorted(set(names)))


def comparison_warnings(results: Iterable[dict[str, Any]]) -> list[str]:
    """Flag differences within each project/rubric; do not infer a winner."""
    groups: dict[tuple[str, str], list[tuple]] = {}
    for result in results:
        rubric = result.get("rubric", "unknown")
        default = 50 if rubric.startswith("rubric10") else 88
        bases = score_bases(result, default)
        key = (result.get("project", "unknown"), rubric)
        groups.setdefault(key, []).append((bases.fixed_max, bases.adjusted_max,
                                          excluded_items(result)))
    warnings = []
    for (project, rubric), signatures in sorted(groups.items()):
        if any(s[2] is None for s in signatures):
            warnings.append(f"{project} / {rubric}: excluded item identities are unreported; "
                            "applicability comparability is unknown.")
        if len(set(signatures)) > 1:
            warnings.append(f"{project} / {rubric}: mixed denominators or excluded items; "
                            "do not rank or pool adjusted percentages across these bases.")
    return warnings
