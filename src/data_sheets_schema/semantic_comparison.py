"""Expose both score bases and applicability differences in semantic reports (#829)."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import json
from math import isfinite
from typing import Any, Iterable, Sequence


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
        if "fixed_max_points" in overall:
            maximum = overall["fixed_max_points"]
            adjusted = overall.get("max_points")
            if "adjusted_max_points" in overall and overall["adjusted_max_points"] != adjusted:
                raise ValueError("API adjusted maxima disagree")
        else:
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
        metadata = result.get("metadata") or {}
        model = result.get("model") or {}
        groups.setdefault(key, []).append((bases.fixed_max, bases.adjusted_max,
                                          excluded_items(result), model.get("name"),
                                          metadata.get("instrument_sha256"),
                                          metadata.get("context_sha256"),
                                          json.dumps(result.get("evaluation_scope"), sort_keys=True)))
    warnings = []
    for (project, rubric), signatures in sorted(groups.items()):
        if any(s[2] is None for s in signatures):
            warnings.append(f"{project} / {rubric}: excluded item identities are unreported; "
                            "applicability comparability is unknown.")
        if len({signature[:3] for signature in signatures}) > 1:
            warnings.append(f"{project} / {rubric}: mixed denominators or excluded items; "
                            "do not rank or pool adjusted percentages across these bases.")
        if len({signature[3:] for signature in signatures}) > 1:
            warnings.append(f"{project} / {rubric}: mixed evaluator, instrument, context or collection scope; "
                            "compare within matching conditions before interpreting score differences.")
    return warnings


# --- Item discrimination and the within-project ordering gate (#2927) -------
#
# The semantic rubrics agree well between projects and poorly inside them:
# on the 2026-09-12 reference set every AI_READI record scores 49/50 on
# rubric10, so no within-project ordering can be read from it. These
# functions measure how much a cohort of evaluations can discriminate and
# refuse a within-project order where it cannot. They read the evaluations
# they are given and write nothing.

ORDER_WITHHELD_AT_MOST = 2
"""A project with this many distinct totals or fewer on a basis gets no
within-project order or better/worse verdict on that basis (#2927)."""

BASES = ("adjusted", "fixed")
BASIS_NAMES = {"adjusted": "N/A-adjusted (points / applicable maximum)",
               "fixed": "fixed (points / full rubric maximum)"}


def _rubric_default_max(rubric: str) -> int:
    return 50 if str(rubric).startswith("rubric10") else 88


def record_label(result: dict[str, Any]) -> str | None:
    """The generation label an evaluation names: top level (rubric10), else
    `metadata.label` (rubric20 writes it there)."""
    label = result.get("label") or (result.get("metadata") or {}).get("label")
    return str(label) if label else None


def item_scores(result: dict[str, Any]) -> dict[str, tuple[float | None, float]]:
    """Item id -> (score or None when excluded as N/A, item maximum).

    Rubric10 sub-elements are named by position (`E3.4` is element 3's fourth
    sub-element, maximum 1); rubric20 questions by id (`Q16`), with their
    declared `max_score`.
    """
    items: dict[str, tuple[float | None, float]] = {}
    for element in result.get("elements") or []:
        for position, sub in enumerate(element.get("sub_elements") or [], start=1):
            score = None if _excluded(sub) else sub.get("score")
            items[f"E{element['id']}.{position}"] = (score, sub.get("max_score", 1))
    categories = result.get("categories") or []
    if isinstance(categories, dict):
        categories = categories.values()
    questions = list(result.get("questions") or [])
    for category in categories:
        questions.extend(category.get("questions") or [])
    for q in questions:
        maximum = q.get("max_score", 1 if q.get("score_type") == "pass_fail" else 5)
        items[f"Q{q['id']}"] = (None if _excluded(q) else q.get("score"), maximum)
    return items


def _item_order(name: str) -> tuple:
    return tuple(int(part) for part in name[1:].split("."))


def _basis_value(bases: ScoreBases, basis: str) -> Fraction | None:
    """The exact fraction a basis orders by; None where it is undefined."""
    denominator = bases.fixed_max if basis == "fixed" else bases.adjusted_max
    if not denominator:
        return None
    return Fraction(bases.total).limit_denominator() / Fraction(denominator).limit_denominator()


def _pair_counts() -> dict[str, int]:
    return {"pairs": 0, "same": 0, "opposite": 0, "tied": 0, "undefined": 0}


def _classify(a: tuple, b: tuple, counts: dict[str, int]) -> None:
    """a, b: (rubric-one value, rubric-two value) for two records."""
    counts["pairs"] += 1
    if None in a or None in b:
        counts["undefined"] += 1
        return
    first, second = a[0] - b[0], a[1] - b[1]
    if first == 0 or second == 0:
        counts["tied"] += 1
    elif (first > 0) == (second > 0):
        counts["same"] += 1
    else:
        counts["opposite"] += 1


def withholding_reason(distinct: int) -> str | None:
    """Why a within-project order is withheld on a basis, or None if it is not."""
    if distinct > ORDER_WITHHELD_AT_MOST:
        return None
    return (f"{distinct} distinct total{'s' if distinct != 1 else ''}; at most "
            f"{ORDER_WITHHELD_AT_MOST} cannot rank records within the project, so no "
            "order or better/worse verdict is given")


def _instrument_names(results: list[dict[str, Any]]) -> dict[tuple[str, str | None], str]:
    """(rubric, version) -> the name its totals are counted under. A rubric
    the cohort holds under one version keeps its bare name; one it holds under
    several is split by version, so a version offset is never counted as a
    distinct total or as a pair ordering (#3290)."""
    versions: dict[str, set] = {}
    for result in results:
        version = result.get("version")
        versions.setdefault(result.get("rubric", "unknown"), set()).add(
            None if version is None else str(version))
    return {(rubric, version): rubric if len(found) == 1 else
            f"{rubric} v{version if version is not None else 'unrecorded'}"
            for rubric, found in versions.items() for version in found}



def evaluator_key(doc: dict) -> str | None:
    """The evaluator an evaluation is measured under: `model.evaluator_model`,
    else `model.model_id`, else `model.name`; None when it records none.
    `model.name` is a display label on some evaluations ("Opus 5 (1M
    context)" beside evaluator_model "claude-opus-5[1m]"), so it comes last
    (#3319); an evaluation that records only a name is still its own
    evaluator, never pooled with the unrecorded (Codex review of #3275).
    Both reports key their per-evaluator blocks on this."""
    model = doc.get("model") or {}
    return model.get("evaluator_model") or model.get("model_id") or model.get("name") or None

def discrimination(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """How far a cohort of semantic evaluations can separate its records.

    Per rubric instrument: the items at ceiling or floor wherever they were
    scored; per project, the distinct totals, the items that vary, the tied
    record pairs and whether a within-project order is withheld — each on both
    the N/A-adjusted and the fixed basis. Across the two rubrics: record pairs
    joined by (project, label), classified as ordered the same way, opposite
    ways, or tied on at least one rubric, within and between projects, on each
    basis — one table per pair of instruments.

    A rubric present under more than one `version` is split by version and
    each version measured on its own (#3290): totals under different versions
    are neither distinct totals of one another nor ordered against each other.

    One evaluation per (project, label, instrument) is assumed; a record rated
    more than once is named under `duplicates` and left out of every count
    rather than having one of its ratings chosen for it. Its rating under the
    other rubric then joins nothing, and is listed under
    `cross_rubric.partner_duplicated`, not as having no partner (#3291).
    """
    results = list(results)
    names = _instrument_names(results)

    def instrument(result):
        version = result.get("version")
        return names[(result.get("rubric", "unknown"), None if version is None else str(version))]

    seen: dict[tuple, int] = {}
    for result in results:
        label = record_label(result)
        if label is not None:
            key = (result.get("project", "unknown"), label, instrument(result))
            seen[key] = seen.get(key, 0) + 1
    duplicates = sorted(key for key, n in seen.items() if n > 1)
    dropped = set(duplicates)
    rows = []
    for result in results:
        rubric, name = result.get("rubric", "unknown"), instrument(result)
        project, label = result.get("project", "unknown"), record_label(result)
        if label is not None and (project, label, name) in dropped:
            continue
        rows.append({"rubric": name, "family": rubric, "project": project, "label": label,
                     "version": result.get("version"),
                     "bases": score_bases(result, _rubric_default_max(rubric)),
                     "items": item_scores(result)})

    rubrics: dict[str, Any] = {}
    for rubric in sorted({row["rubric"] for row in rows}):
        members = [row for row in rows if row["rubric"] == rubric]
        items = sorted({name for row in members for name in row["items"]}, key=_item_order)
        ceiling, floor, never, not_scored = [], [], [], {}
        for name in items:
            scored = [row["items"][name] for row in members
                      if name in row["items"] and row["items"][name][0] is not None]
            missing = len(members) - len(scored)
            if missing:
                not_scored[name] = missing
            if not scored:
                never.append(name)
            elif all(score == maximum for score, maximum in scored):
                ceiling.append(name)
            elif all(score == 0 for score, _maximum in scored):
                floor.append(name)
        projects = {}
        for project in sorted({row["project"] for row in members}):
            group = [row for row in members if row["project"] == project]
            varying = [name for name in items
                       if len({row["items"].get(name, ("absent",))[0] for row in group}) > 1]
            entry = {"records": len(group), "pairs": len(group) * (len(group) - 1) // 2,
                     "varying_items": varying, "distinct_totals": {}, "tied_pairs": {},
                     "withheld": {}}
            for basis in BASES:
                values = [_basis_value(row["bases"], basis) for row in group]
                defined = [v for v in values if v is not None]
                entry["distinct_totals"][basis] = len(set(defined))
                entry["tied_pairs"][basis] = sum(
                    1 for i, a in enumerate(values) for b in values[i + 1:]
                    if a is not None and a == b)
                entry["withheld"][basis] = withholding_reason(len(set(defined)))
            projects[project] = entry
        rubrics[rubric] = {"family": members[0]["family"], "records": len(members),
                           "items": len(items), "ceiling": ceiling, "floor": floor,
                           "never_scored": never, "not_scored": not_scored,
                           "projects": projects}

    cross: dict[str, Any] = {"rubrics": None, "tables": [], "unjoined": [],
                             "partner_duplicated": [], "reason": None}
    families = sorted({row["family"] for row in rows})
    if len(families) != 2:
        cross["reason"] = (f"{len(families)} rubric{'s' if len(families) != 1 else ''} in the cohort; "
                           "the cross-rubric comparison needs exactly two")
    else:
        cross["rubrics"] = tuple(families)
        keyed = {name: {(row["project"], row["label"]): row for row in rows
                        if row["rubric"] == name and row["label"] is not None}
                 for name in rubrics}
        joined_anywhere: set[tuple[str, str, str]] = set()
        for first in sorted(n for n in rubrics if rubrics[n]["family"] == families[0]):
            for second in sorted(n for n in rubrics if rubrics[n]["family"] == families[1]):
                joined = sorted(set(keyed[first]) & set(keyed[second]))
                if not joined:
                    continue
                joined_anywhere |= {(name, *key) for key in joined for name in (first, second)}
                table = {"rubrics": (first, second), "joined_records": len(joined), "bases": {}}
                for basis in BASES:
                    values = {key: tuple(_basis_value(keyed[name][key]["bases"], basis)
                                         for name in (first, second)) for key in joined}
                    within, between = _pair_counts(), _pair_counts()
                    for i, a in enumerate(joined):
                        for b in joined[i + 1:]:
                            _classify(values[a], values[b], within if a[0] == b[0] else between)
                    table["bases"][basis] = {"within": within, "between": between}
                cross["tables"].append(table)
        family_of = {name: rubric for (rubric, _version), name in names.items()}
        duplicated = {(project, label, family_of[name]) for project, label, name in duplicates}
        for row in sorted(rows, key=lambda r: (r["rubric"], r["project"], r["label"] or "")):
            if row["label"] is not None and (row["rubric"], row["project"], row["label"]) in joined_anywhere:
                continue
            item = (row["rubric"], row["project"], row["label"] or "unlabelled")
            other = families[1] if row["family"] == families[0] else families[0]
            if row["label"] is not None and (row["project"], row["label"], other) in duplicated:
                cross["partner_duplicated"].append(item)
            else:
                cross["unjoined"].append(item)
    return {"withheld_at_most": ORDER_WITHHELD_AT_MOST, "duplicates": duplicates,
            "rubrics": rubrics, "cross_rubric": cross}


def withheld_projects(block: dict[str, Any], rubric: str) -> dict[str, dict[str, str]]:
    """project -> {basis: reason} for every basis whose order is withheld, on
    the instrument named `rubric` (a rubric's bare name, or its versioned name
    where the cohort splits it)."""
    out = {}
    for project, entry in (block["rubrics"].get(rubric) or {}).get("projects", {}).items():
        reasons = {basis: reason for basis, reason in entry["withheld"].items() if reason}
        if reasons:
            out[project] = reasons
    return out


def instruments_of(block: dict[str, Any], rubric: str) -> list[str]:
    """The instrument names a rubric is measured under in a block: its bare
    name, or one per version where the cohort held more than one (#3290)."""
    return [name for name, entry in block["rubrics"].items() if entry["family"] == rubric]


def render_discrimination(block: dict[str, Any], heading: str = "##", scope: str = "",
                          left_out: Sequence[str] = (), evaluator: str | None = None,
                          measured_on: str | None = None) -> list[str]:
    """Markdown lines for a discrimination block; the basis is named on every
    figure that depends on one. `scope` qualifies the heading. `left_out` names
    the evaluations listed above the block that it does not measure (a report
    whose cohort is narrower than its table, #3303); they are named, so the
    block never claims to measure every evaluation above it. `evaluator`
    scopes the block to one evaluator's evaluations where the tables above
    hold more than one evaluator's (#3309, #3310): the block then says it
    measured that evaluator's evaluations only. `measured_on` replaces the
    phrase naming what was measured ("Measured on <measured_on>, one rating
    per record.") where the cohort is a counted part of the evaluations above
    that names too many left out to list (#3570); it excludes `left_out`."""
    if measured_on is not None and left_out:
        raise ValueError("measured_on states the cohort itself; pass it or left_out, not both")
    whose = ("the evaluations above" if evaluator is None else f"the {evaluator} evaluations above"
             ) if measured_on is None else measured_on
    measured = (f"Measured on {whose}, one rating per record." if not left_out else
                f"Measured on {whose} except the {len(left_out)} left out of this "
                "block's cohort, one rating per record. Left out, and in no count below: "
                + ", ".join(f"`{name}`" for name in left_out) + ".")
    if evaluator is not None:
        # "In this block", not "below": every caller that names an evaluator
        # renders one block per evaluator, and the blocks after this one do
        # count the other evaluators' evaluations (#3598).
        measured += (" Evaluations by any other evaluator are in no count in this block: an "
                     "evaluator is an instrument (#1058), and pooling two would count their "
                     "offset as distinct totals.")
    lines = [f"{heading} Item discrimination and within-project orderings{scope} (#2927)", "",
             measured + " An item at ceiling "
             "(or floor) scored its maximum (or 0) on every record where it was scored, so it "
             "separates none of them. A project with at most "
             f"{block['withheld_at_most']} distinct totals on a basis gets no within-project "
             "order or better/worse verdict on that basis. Totals are compared exactly, as "
             "points over the basis's denominator. This is descriptive of these ratings; it is "
             "not an evaluator-reliability estimate.", ""]
    if block["duplicates"]:
        lines += ["Rated more than once, and left out of every count below rather than having "
                  "one rating chosen: " + ", ".join(f"{p} `{l}` ({r})" for p, l, r in block["duplicates"])
                  + ".", ""]
    if not block["rubrics"]:
        return lines + ["No evaluations to measure.", ""]
    for rubric, entry in block["rubrics"].items():
        def listed(names):
            return ", ".join(f"{n} (not scored on {entry['not_scored'][n]})" if n in entry["not_scored"]
                             else n for n in names) or "none"
        lines += [f"**{rubric}** — {entry['records']} records, {entry['items']} items. "
                  f"At ceiling: {len(entry['ceiling'])}/{entry['items']} ({listed(entry['ceiling'])}). "
                  f"At floor: {len(entry['floor'])}/{entry['items']} ({listed(entry['floor'])})."
                  + (f" Never scored: {', '.join(entry['never_scored'])}." if entry["never_scored"] else ""),
                  "",
                  "| project | records | distinct totals (adjusted / fixed) | tied pairs (adjusted / fixed) | items that vary | within-project order |",
                  "|---|---|---|---|---|---|"]
        for project, p in entry["projects"].items():
            pairs = p["pairs"]
            ties = " / ".join(f"{p['tied_pairs'][b]}/{pairs}" + (f" ({100 * p['tied_pairs'][b] / pairs:.0f}%)" if pairs else "")
                              for b in BASES)
            reasons = {b: r for b, r in p["withheld"].items() if r}
            if not reasons:
                order = "not withheld on either basis"
            elif len(reasons) == len(BASES) and len(set(reasons.values())) == 1:
                order = f"**withheld on both bases**: {reasons[BASES[0]]}"
            else:
                order = "; ".join(f"**withheld ({b})**: {r}" for b, r in reasons.items())
            lines.append(f"| {project} | {p['records']} | "
                         f"{p['distinct_totals']['adjusted']} / {p['distinct_totals']['fixed']} | {ties} | "
                         f"{len(p['varying_items'])}: {', '.join(p['varying_items']) or 'none'} | {order} |")
        lines.append("")
    split = sorted({entry["family"] for name, entry in block["rubrics"].items()
                    if name != entry["family"]})
    if split:
        lines += [f"Split by instrument version: {', '.join(split)}. Each version is measured on "
                  "its own; totals under different versions are not counted as distinct totals of "
                  "one another nor ordered against each other (#3290).", ""]
    cross = block["cross_rubric"]
    if cross["rubrics"] is None:
        return lines + [f"Cross-rubric agreement: not computed — {cross['reason']}.", ""]
    for table in cross["tables"]:
        first, second = table["rubrics"]
        undefined = any(c[s]["undefined"] for c in table["bases"].values() for s in c)
        lines += [f"**Cross-rubric agreement** — record pairs ordered the same way by {first} and "
                  f"{second}, opposite ways, or tied on at least one rubric; {table['joined_records']} "
                  "records joined by (project, label). Each basis is shown: adjusted-basis agreement is "
                  "confounded by what each evaluation judged applicable (#2912).", "",
                  "| basis | scope | pairs | same order | opposite | tied on at least one rubric |"
                  + (" undefined |" if undefined else ""),
                  "|---|---|---|---|---|---|" + ("---|" if undefined else "")]
        for basis in BASES:
            for scope in ("within", "between"):
                c = table["bases"][basis][scope]
                lines.append(f"| {BASIS_NAMES[basis]} | {scope} {'project' if scope == 'within' else 'projects'} | {c['pairs']} | {c['same']} | "
                             f"{c['opposite']} | {c['tied']} |" + (f" {c['undefined']} |" if undefined else ""))
        lines.append("")
    if not cross["tables"]:
        lines += [f"Cross-rubric agreement: not computed — no record is rated under both "
                  f"{cross['rubrics'][0]} and {cross['rubrics'][1]}.", ""]
    if cross["unjoined"]:
        lines += ["Not joined (no rating of the same (project, label) under the other rubric): "
                  + ", ".join(f"{p} `{l}` ({r})" for r, p, l in cross["unjoined"]) + ".", ""]
    if cross["partner_duplicated"]:
        lines += ["Not joined because the record's rating under the other rubric was rated more "
                  "than once and left out: "
                  + ", ".join(f"{p} `{l}` ({r})" for r, p, l in cross["partner_duplicated"]) + ".", ""]
    return lines


# --- The legacy summarizers' own cohorts (#3281) ------------------------------
#
# scripts/summarize_rubric{10,20}_results.py read data/evaluation_llm/rubric10
# and rubric20: the presence/direct-API evaluations, whose items already have
# the shape item_scores() reads (rubric10 `elements[].sub_elements[]`, rubric20
# `questions[]` with `max_score`). What they lack is a generation label, and
# each directory mixes evaluators and record kinds, so the block is measured
# per cohort rather than over the folder. The cohort is also split by fixed
# maximum as a safeguard (#275): a rubric20 directory could hold two maxima,
# though the committed one holds only 84 (#3599).

def legacy_record(result: dict[str, Any]) -> dict[str, Any]:
    """A legacy evaluation as discrimination() reads it. It names no
    generation label; the record it rated is `d4d_file`, so that is its label
    where it names none, and a file rated twice in one cohort is a duplicate
    rather than two records. The evaluation itself is not modified."""
    if record_label(result) is not None or not result.get("d4d_file"):
        return result
    return {**result, "label": str(result["d4d_file"])}


def legacy_cohorts(results: Iterable[dict[str, Any]]
                   ) -> list[tuple[tuple[str, str | None, float], list[dict[str, Any]]]]:
    """((evaluation type, evaluator, fixed maximum), evaluations), sorted.

    An individual (single-source) record and a concatenated synthesis are
    different kinds of record; an evaluator is an instrument (#1058); and a
    total over another maximum is not a distinct total of this one (#275). Any
    of the three pooled would count its offset as separation."""
    groups: dict[tuple[str, str | None, float], list[dict[str, Any]]] = {}
    for result in results:
        maximum = score_bases(result, _rubric_default_max(result.get("rubric", "unknown"))).fixed_max
        key = (str(result.get("evaluation_type") or "unknown"), evaluator_key(result), maximum)
        groups.setdefault(key, []).append(result)
    return sorted(groups.items(), key=lambda item: (item[0][0], item[0][1] or "", item[0][2]))


def render_legacy_discrimination(results: Iterable[dict[str, Any]],
                                 heading: str = "##") -> list[str]:
    """The #2927 block for each of a legacy summarizer's cohorts (#3281)."""
    results = list(results)
    lines: list[str] = []
    for (kind, evaluator, maximum), members in legacy_cohorts(results):
        who = evaluator or "an unrecorded evaluator"
        block = discrimination(legacy_record(result) for result in members)
        # The report above lists every evaluation the summarizer loaded, of
        # every kind, evaluator and maximum; the block measures one cohort of
        # them, so it counts what it measures against what is above (#3570).
        others = len(results) - len(members)
        measured_on = (f"{len(members)} of the {len(results)} evaluations above: the {kind} "
                       f"evaluations by {who} scored out of {maximum:g}"
                       + (f". The other {others} are in no count in this block; each is "
                          "measured in a block of its own" if others else ""))
        lines += render_discrimination(
            block, heading, scope=f", {kind} evaluations by {who} scored out of {maximum:g}",
            evaluator=evaluator, measured_on=measured_on)
        lines += [f"This cohort is the {len(members)} {kind} evaluation"
                  f"{'s' if len(members) != 1 else ''} by {who} scored out of {maximum:g}, "
                  "each record named by the D4D file it rated. Evaluations of another kind "
                  "(individual or concatenated), by another evaluator or over another maximum "
                  "are measured in a block of their own: pooled, their offsets would be counted "
                  "as distinct totals (#1058, #275).", ""]
    return lines
