"""Explicit descriptive paired analysis of captured support/fitness judgments.

No thresholds, favorable verdicts, strata, confidence level or seed are chosen
for the caller. Unknown attribution leaves agreement observable, not a family
preference claim. Historical semantic analysis authority remains unchanged.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
import math
from pathlib import Path

from . import cross_family_judge_panel as panels
from . import cross_family_panel_analysis as kernel
from . import nested_support_results as saved
from .support_plan import canonical, sha256

SPEC_FORMAT = "cross_family_judge_analysis_spec_v1"
FORMAT = "cross_family_judge_analysis_v1"
DECLARATION_FORMAT = "cross_family_judge_analysis_declaration_v1"
GROUPING = "instrument_context_kind_ordered_rater_configuration_and_evidence_basis"
SUPPORT_VERDICTS = ("contradicted", "status_shifted", "relationship_unsupported", "wrong_document",
                    "unsupported", "partially_supported", "supported")
FITNESS_FAILURES = ("none", "form", "target", "substance")
THRESHOLD_CATEGORIES = ("does_not_meet_threshold", "meets_threshold")
MAX_BYTES = saved.MAX_MANIFEST_BYTES
MAX_BOOTSTRAP_WORK = kernel.MAX_BOOTSTRAP_WORK
MAX_RESAMPLES = kernel.MAX_RESAMPLES
AnalysisError = panels.PanelError
_need, _closed = panels._need, panels._closed
LIMITS = {**panels.LIMITS, "bootstrap_work": MAX_BOOTSTRAP_WORK, "resamples": MAX_RESAMPLES}


def _number(value):
    _need(type(value) in (int, float) and math.isfinite(value), "finite nonboolean number required")
    return Fraction(value)  # float conversion uses its exact binary64 ratio.


def signed_difference(same, cross):
    """Pure ordered-operand arithmetic; family attribution is checked separately."""
    return float(_number(same) - _number(cross))


def _policy(raw, panel, panel_raw):
    value = _closed(panels._read(raw, "analysis declaration"), {"format", "analysis_id", "panel_sha256",
        "pair_ids", "agreement", "gap", "support_indicator", "fitness_threshold", "grouping", "uncertainty"}, "analysis declaration")
    _need(value["format"] == DECLARATION_FORMAT and value["panel_sha256"] == sha256(panel_raw), "analysis names another panel")
    panels._identifier(value["analysis_id"], "analysis_id")
    _need(value["grouping"] == GROUPING, "unsupported grouping")
    selected = panels._list(value["pair_ids"], "pair_ids", panels.MAX_PAIRS)
    by_id = {p["pair_id"]: p for p in panel["pairs"]}
    _need(all(type(p) is str and p in by_id for p in selected) and len(set(selected)) == len(selected), "foreign/duplicate selected pair")
    pending = []
    for key, expected in (("agreement", "equal_target"), ("gap", "equal_record")):
        choice = _closed(value[key], {"weighting"}, key)["weighting"]
        _need(choice is None or choice == expected, "unsupported " + key + " weighting")
        if choice is None:
            pending.append(key + ".weighting")
    favorable = _closed(value["support_indicator"], {"favorable_verdicts"}, "support indicator")["favorable_verdicts"]
    if favorable is None:
        pending.append("support_indicator.favorable_verdicts")
    else:
        panels._list(favorable, "favorable verdicts", len(SUPPORT_VERDICTS))
        _need(all(type(v) is str and v in SUPPORT_VERDICTS for v in favorable) and len(set(favorable)) == len(favorable), "invalid favorable verdict set")
    threshold = value["fitness_threshold"]
    if threshold is None:
        pending.append("fitness_threshold")
    else:
        _closed(threshold, {"cutoff", "boundary"}, "fitness threshold")
        _need(0 <= _number(threshold["cutoff"]) <= 1 and threshold["boundary"] in ("ge", "gt"), "invalid fitness threshold")
    u = _closed(value["uncertainty"], {"method", "confidence", "resamples", "seed", "quantile", "blocks", "strata"}, "uncertainty")
    for name, expected in (("method", "paired_cluster_percentile_v1"), ("quantile", "linear_n_minus_one")):
        _need(u[name] is None or u[name] == expected, "unsupported uncertainty " + name)
    if u["confidence"] is not None:
        _need(0 < _number(u["confidence"]) < 1, "confidence must lie strictly between zero and one")
    if u["resamples"] is not None:
        _need(type(u["resamples"]) is int and 2 <= u["resamples"] <= MAX_RESAMPLES, "invalid resample bound")
    if u["seed"] is not None:
        _need(type(u["seed"]) is int and 0 <= u["seed"] < 2**64, "invalid seed")
    for name in ("method", "confidence", "resamples", "seed", "quantile"):
        if u[name] is None:
            pending.append("uncertainty." + name)
    record_ids = sorted({by_id[pid]["record_id"] for pid in selected})
    for key in ("blocks", "strata"):
        kernel._partition(u[key], key, set(record_ids), pending)
    if u["blocks"] is not None:
        block_of = {rid: row["block_id"] for row in u["blocks"] for rid in row["record_ids"]}
        for row in panel["records"]:
            ids = set(row["duplicate_input_record_ids"]) & set(record_ids)
            _need(len({block_of[rid] for rid in ids}) <= 1, "identical record bytes must share one uncertainty block")
    # Stable selected order is independent of declaration/submission array order.
    result = panels._detached(value)
    result["pair_ids"] = sorted(selected)
    for key, id_key in (("blocks", "block_id"), ("strata", "stratum_id")):
        if result["uncertainty"][key] is not None:
            result["uncertainty"][key] = sorted(
                [{id_key: r[id_key], "record_ids": sorted(r["record_ids"])} for r in u[key]], key=lambda r: r[id_key])
    if favorable is not None:
        result["support_indicator"]["favorable_verdicts"] = [v for v in SUPPORT_VERDICTS if v in favorable]
    return result, sorted(pending)


def _specification(capture, panel_raw, declaration_raw):
    panel = panels._checked_panel(capture, panel_raw)
    policy, pending = _policy(declaration_raw, panel, panel_raw)
    return panels._detached({"format": SPEC_FORMAT, "declaration": capture.add(declaration_raw), "panel": capture.add(panel_raw),
        "policy": policy, "pending_parameters": pending, "authority": panels._authority(capture), "limits": LIMITS,
        "readiness": panel["readiness"], "scientific_eligibility": False, "execution_authorized": False})


def _checked_spec(capture, raw):
    old = panels._read(raw, "judge analysis specification")
    _need(type(old) is dict and old.get("format") == SPEC_FORMAT, "unsupported judge analysis specification")
    rebuilt = _specification(capture, capture.get(old["panel"]), capture.get(old["declaration"]))
    _need(canonical(old) == canonical(rebuilt), "analysis specification differs from captured reconstruction")
    return rebuilt


def _configuration(capture, slot):
    if slot["descriptor"] is None:
        return None
    rater = slot["rater"]
    transport = None
    if slot["execution_registration"] is not None:
        registration = executor_registration(capture, slot["execution_registration"])
        transport = registration["declaration"]["transport"]
    return {"model": rater["model"], "family": rater["family"], "rater": rater["rater"], "route": rater["route"],
        "max_tokens": slot["binding"]["max_tokens"], "transport": transport, "evidence_basis": slot["evidence_basis"],
        "anonymous_descriptor": slot["descriptor"] if rater["rater"] is None or rater["route"] is None else None}


def executor_registration(capture, pin):
    return panels.executor._load(capture, capture.get(pin))


def _identity(capture, pair):
    subject = pair["common_subject"]
    return {"axis": pair["axis"], "kind": pair["kind"], "artifact_kind": subject["artifact_kind"],
            "schema": subject["schema"], "instrument": subject["instrument"],
            "raters": {role: _configuration(capture, pair["slots"][role]) for role in panels.ROLES},
            "orientation": "declared_slot_A_same_family_then_slot_B_cross_family; attribution_checked_separately"}


def _threshold(number, policy):
    value, cutoff = _number(number), _number(policy["cutoff"])
    return int(value >= cutoff if policy["boundary"] == "ge" else value > cutoff)


def _operands(pair, metric, policy):
    if not pair["accepted_pair"]:
        return None
    a, b = (pair["slots"][role]["assessment"] for role in panels.ROLES)
    if metric == "support_agreement":
        return a["verdict"], b["verdict"]
    if metric in ("fitness_agreement", "continuous_fitness_difference"):
        return _number(a["fitness"]), _number(b["fitness"])
    if metric == "fitness_failure_agreement":
        return a["failure"], b["failure"]
    if metric == "favorable_support_indicator_difference":
        favorable = policy["support_indicator"]["favorable_verdicts"]
        return None if favorable is None else (int(a["verdict"] in favorable), int(b["verdict"] in favorable))
    threshold = policy["fitness_threshold"]
    if threshold is None:
        return None
    mapped = (_threshold(a["fitness"], threshold), _threshold(b["fitness"], threshold))
    return tuple(THRESHOLD_CATEGORIES[n] for n in mapped) if metric == "threshold_agreement" else mapped


def _categories(metric):
    return {"support_agreement": SUPPORT_VERDICTS, "fitness_failure_agreement": FITNESS_FAILURES,
            "threshold_agreement": THRESHOLD_CATEGORIES}.get(metric)


def _pending_metric(metric, policy):
    reasons = []
    agreement = metric.endswith("agreement")
    if policy["agreement" if agreement else "gap"]["weighting"] is None:
        reasons.append("agreement_policy_pending" if agreement else "gap_policy_pending")
    if metric == "favorable_support_indicator_difference" and policy["support_indicator"]["favorable_verdicts"] is None:
        reasons.append("favorable_verdicts_pending")
    if metric in ("threshold_agreement", "fitness_threshold_indicator_difference") and policy["fitness_threshold"] is None:
        reasons.append("fitness_threshold_pending")
    return reasons


def _quantile(values, p):
    ordered = sorted(values)
    h = (len(ordered) - 1) * p
    low = h.numerator // h.denominator
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (h - low) * (ordered[high] - ordered[low])


def _exact_metrics(matrix):
    total = sum(map(sum, matrix))
    if not total:
        return {"exact_agreement": None, "kappa": None}
    po = sum(matrix[i][i] for i in range(len(matrix))) / total
    pe = sum(sum(matrix[i]) * sum(row[i] for row in matrix) for i in range(len(matrix))) / total**2
    return {"exact_agreement": po, "kappa": None if pe == 1 else (po - pe) / (1 - pe)}


def _uncertainty(identity, contributions, categories, u, pending, observed, budget, *, equality=False):
    """Reuse one historical schedule, recomputing from original exact operands.

    The source kernel retains every-declared-stratum refusal, fixed weights and
    undefined draws. Its float outputs never become arithmetic operands here.
    """
    categorical = categories is not None
    kind = "agreement" if categorical else "gap"
    ready = not any(p.startswith("uncertainty.") for p in pending)
    # Reserve all additional rational replay work before asking the existing
    # kernel to draw anything. Its own work/output bounds remain independently
    # enforced as well. This is a worst-case bound, not elapsed-cost evidence.
    if ready and contributions:
        blocks = u["blocks"]
        strata = u["strata"]
        block_records = {r["block_id"]: [rid for rid in r["record_ids"] if rid in contributions] for r in blocks}
        projected = []
        for s in strata:
            names = [b["block_id"] for b in blocks if set(block_records[b["block_id"]]) & set(s["record_ids"])]
            projected.append(names)
        can_draw = all(len(names) >= 2 for names in projected) and bool(projected)
        if can_draw:
            extra = u["resamples"] * (1 + sum(len(names) * (1 + max(len(block_records[n]) for n in names))
                for names in projected) * max(1, len(categories or ())**2))
            # Includes sorting rational draws for the quantile.
            extra += u["resamples"] * max(1, u["resamples"].bit_length())
            budget["work"] += extra
            _need(budget["work"] <= MAX_BOOTSTRAP_WORK, "bootstrap rational work bound exceeded")
    output = kernel._bootstrap(identity, contributions, kind, list(categories or ()), u, pending, observed, budget)
    _need(budget["work"] <= MAX_BOOTSTRAP_WORK and budget["bytes"] <= MAX_BYTES, "judge bootstrap work/output bound exceeded")
    exact = []
    if output["draws"]:
        blocks = {r["block_id"]: [rid for rid in r["record_ids"] if rid in contributions] for r in u["blocks"]}
        weights = {s["stratum_id"]: Fraction(*s["weight_fraction"]) for s in output["strata"]}
        for draw in output["draws"]:
            matrix = [[Fraction(0) for _ in categories] for _ in categories] if categorical else None
            mean, unavailable = Fraction(0), []
            for sampled in draw["strata"]:
                ids = [rid for bid in sampled["blocks"] for rid in blocks[bid]]
                n = sum(contributions[rid]["n"] for rid in ids)
                if not n:
                    unavailable.append("empty_draw_stratum:" + sampled["stratum_id"])
                    continue
                weight = weights[sampled["stratum_id"]]
                if categorical:
                    for i in range(len(categories)):
                        for j in range(len(categories)):
                            matrix[i][j] += weight * Fraction(sum(contributions[rid]["matrix"][i][j] for rid in ids), n)
                else:
                    mean += weight * sum(contributions[rid]["sum"] for rid in ids) / n
            values = _exact_metrics(matrix) if categorical else {"mean": mean}
            if unavailable:
                values = {name: None for name in values}
            exact.append(values)
            draw["metrics"] = {name: None if v is None else float(v) for name, v in values.items()}
            draw["undefined_reasons"] = {name: ";".join(unavailable) if unavailable else "expected_agreement_is_one"
                for name, v in values.items() if v is None}
        tail = (1 - _number(u["confidence"])) / 2
        for name, interval in output["intervals"].items():
            values = [v[name] for v in exact]
            missing = sum(v is None for v in values)
            reason = "observed_statistic_undefined" if observed[name] is None else "undefined_bootstrap_draws" if missing else None
            interval.update(lower=None if reason else float(_quantile(values, tail)),
                            upper=None if reason else float(_quantile(values, 1-tail)),
                            reason=reason, undefined_draws=missing)
    if equality:
        for row in output["strata"]:
            row["observation_count"] = sum(contributions[rid]["n"] for rid in row["contributing_record_ids"])
        for draw in output["draws"]:
            draw["metrics"] = {"exact_agreement": draw["metrics"]["mean"]}
            draw["undefined_reasons"] = {"exact_agreement": v for _, v in draw["undefined_reasons"].items()}
        output["intervals"] = {"exact_agreement": output["intervals"]["mean"]}
    return output


def _agreement(capture, identity, metric, pairs, policy, pending, budget):
    categories = _categories(metric)
    policy_reasons = _pending_metric(metric, policy)
    eligible = [p for p in pairs if p["accepted_pair"] and not policy_reasons]
    values = [_operands(p, metric, policy) for p in eligible]
    contributions = {}
    if categories is not None:
        matrix = [[0 for _ in categories] for _ in categories]
        for p, (a, b) in zip(eligible, values):
            i, j = categories.index(a), categories.index(b)
            matrix[i][j] += 1
            c = contributions.setdefault(p["record_id"], {"n": 0, "matrix": [[0 for _ in categories] for _ in categories]})
            c["n"] += 1
            c["matrix"][i][j] += 1
        metrics = kernel._metric(matrix, categories)
        observed = {"exact_agreement": metrics["observed_agreement"], "kappa": metrics["kappa"]}
    else:
        agreeing = sum(a == b for a, b in values)
        metrics = {"n": len(values), "agreeing": agreeing, "categories": None, "confusion_matrix": None,
            "row_totals": None, "column_totals": None,
            "observed_agreement": float(Fraction(agreeing, len(values))) if values else None,
            "expected_agreement": None, "kappa": None, "agreement_reason": None if values else "no_observed_pairs",
            "kappa_reason": "not_a_categorical_metric"}
        for p, (a, b) in zip(eligible, values):
            c = contributions.setdefault(p["record_id"], {"n": 0, "sum": Fraction(0)})
            c["n"] += 1
            c["sum"] += int(a == b)
        observed = {"mean": metrics["observed_agreement"]}
    if policy_reasons:
        metrics["agreement_reason"] = ";".join(policy_reasons)
        if categories:
            metrics["kappa_reason"] = ";".join(policy_reasons)
    counts = _counts(pairs, eligible)
    return {"identity": identity, "metric": metric, "pair_ids": [p["pair_id"] for p in pairs],
        "record_ids": sorted({p["record_id"] for p in eligible}), "counts": counts, "metrics": metrics,
        "attribution_counts": {"attributed": sum(p["attributed_role_pair"] for p in eligible),
            "unattributed": sum(not p["attributed_role_pair"] for p in eligible),
            "reasons": dict(Counter(r for p in eligible for r in p["attribution_reasons"]))},
        "uncertainty": _uncertainty(identity, contributions, categories, policy["uncertainty"], pending, observed, budget,
                                    equality=categories is None)}


def _counts(pairs, eligible):
    eligible_ids = {p["pair_id"] for p in eligible}
    return {"expected_targets": len(pairs), "paired_targets": len(eligible), "excluded_targets": len(pairs) - len(eligible),
        "missing_or_rejected_targets": sum(not p["accepted_pair"] for p in pairs),
        "expected_records": len({p["record_id"] for p in pairs}),
        "paired_records": len({p["record_id"] for p in eligible}),
        "excluded_pair_ids": [p["pair_id"] for p in pairs if p["pair_id"] not in eligible_ids]}


def _gap(identity, metric, pairs, policy, pending, budget):
    reasons = _pending_metric(metric, policy)
    eligible = [p for p in pairs if p["accepted_pair"] and p["attributed_role_pair"] and not reasons]
    by_record = defaultdict(list)
    for p in pairs:
        by_record[p["record_id"]].append(p)
    eligible_ids = {p["pair_id"] for p in eligible}
    rows, contributions = [], {}
    all_differences = []
    for rid, record_pairs in sorted(by_record.items()):
        chosen = [p for p in record_pairs if p["pair_id"] in eligible_ids]
        values = [_operands(p, metric, policy) for p in chosen]
        same = sum(Fraction(a) for a, _ in values) / len(values) if values else None
        cross = sum(Fraction(b) for _, b in values) / len(values) if values else None
        difference = same - cross if values else None
        differences = [Fraction(a) - Fraction(b) for a, b in values]
        all_differences.extend(differences)
        if difference is not None:
            contributions[rid] = {"n": 1, "sum": difference}
        rows.append({"record_id": rid, "expected_pair_ids": [p["pair_id"] for p in record_pairs],
            "paired_pair_ids": [p["pair_id"] for p in chosen],
            "excluded_pair_ids": [p["pair_id"] for p in record_pairs if p["pair_id"] not in eligible_ids],
            "counts": _counts(record_pairs, chosen),
            "same_mean": None if same is None else float(same), "cross_mean": None if cross is None else float(cross),
            "difference": None if difference is None else float(difference),
            "positive": sum(v > 0 for v in differences), "negative": sum(v < 0 for v in differences), "ties": sum(v == 0 for v in differences),
            "reason": None if chosen else ";".join(reasons) if reasons else "no_attributed_paired_targets"})
    differences = [c["sum"] for c in contributions.values()]
    mean = sum(differences) / len(differences) if differences else None
    metrics = {"n": len(differences), "mean": None if mean is None else float(mean),
        "positive": sum(v > 0 for v in differences), "negative": sum(v < 0 for v in differences),
        "ties": sum(v == 0 for v in differences), "reason": None if differences else ";".join(reasons) if reasons else "no_attributed_paired_targets"}
    counts = _counts(pairs, eligible)
    counts["target_signs"] = {"positive": sum(v > 0 for v in all_differences), "negative": sum(v < 0 for v in all_differences), "ties": sum(v == 0 for v in all_differences)}
    return {"identity": identity, "metric": metric, "pair_ids": [p["pair_id"] for p in pairs],
        "record_ids": sorted(contributions), "counts": counts, "record_rows": rows, "metrics": metrics,
        "uncertainty": _uncertainty(identity, contributions, None, policy["uncertainty"], pending, {"mean": metrics["mean"]}, budget)}


def _analysis(capture, spec_raw, results_raw):
    spec = _checked_spec(capture, spec_raw)
    results = panels._checked_results(capture, results_raw)
    _need(spec["panel"] == results["panel"], "specification and results name different panel bytes")
    policy, pending = spec["policy"], spec["pending_parameters"]
    selected = set(policy["pair_ids"])
    pairs, groups = [], {}
    for source in results["pairs"]:
        pair = panels._detached(source)
        pair["selected"] = pair["pair_id"] in selected
        gap_names = ("favorable_support_indicator_difference",) if pair["axis"] == "grounding_v3" else (
            "continuous_fitness_difference", "fitness_threshold_indicator_difference")
        mapped, gaps, explanations = {}, {}, {}
        for metric in gap_names:
            values = _operands(pair, metric, policy)
            if values is not None:
                mapped[metric] = {role: float(v) if isinstance(v, Fraction) else v for role, v in zip(panels.ROLES, values)}
            reasons = list(pair["eligibility_reasons"]) + pair["attribution_reasons"] + _pending_metric(metric, policy)
            gaps[metric] = None if reasons or values is None else float(Fraction(values[0]) - Fraction(values[1]))
            explanations[metric] = list(dict.fromkeys(reasons))
        pair["mapped_operands"], pair["gap_values"] = mapped, gaps
        pair["eligibility_reasons"] = {"accepted_pair": pair["eligibility_reasons"], "gaps": explanations}
        pairs.append(pair)
        if pair["selected"]:
            identity = _identity(capture, pair)
            key = canonical(identity)
            group = groups.setdefault(key, (identity, []))
            group[1].append(pair)
    u = policy["uncertainty"]
    # Bound group/stratum/record projection before invoking any resampling loop.
    projection_work = len(pairs) * 8 + len(groups) * 6 * (1 + len(selected)
        + len(u["strata"] or []) * (1 + len(u["blocks"] or [])))
    _need(projection_work <= MAX_BOOTSTRAP_WORK, "analysis grouping work bound exceeded")
    budget = {"work": projection_work, "bytes": 0}
    agreement, gaps = [], []
    for key in sorted(groups):
        identity, group_pairs = groups[key]
        support = identity["axis"] == "grounding_v3"
        agreement_names = ("support_agreement",) if support else ("fitness_agreement", "fitness_failure_agreement", "threshold_agreement")
        gap_names = ("favorable_support_indicator_difference",) if support else ("continuous_fitness_difference", "fitness_threshold_indicator_difference")
        for metric in agreement_names:
            agreement.append(_agreement(capture, identity, metric, group_pairs, policy, pending, budget))
        for metric in gap_names:
            gaps.append(_gap(identity, metric, group_pairs, policy, pending, budget))
    value = {"format": FORMAT, "specification": capture.add(spec_raw), "results": capture.add(results_raw),
        "policy": policy, "pending_parameters": pending, "slots": results["slots"], "pairs": pairs,
        "agreement_groups": agreement, "gap_groups": gaps,
        "counts": {**results["counts"], "selected_pairs": len(selected), "unselected_pairs": len(pairs)-len(selected),
            "selected_accepted_pairs": sum(p["selected"] and p["accepted_pair"] for p in pairs),
            "selected_attributed_pairs": sum(p["selected"] and p["accepted_pair"] and p["attributed_role_pair"] for p in pairs),
            "work": budget},
        "coverage": results["coverage"], "pending_decisions": results["pending_decisions"], "readiness": results["readiness"],
        "authority": panels._authority(capture), "limits": LIMITS, "scientific_eligibility": False, "execution_authorized": False}
    _need(len(canonical(value)) + 1 <= MAX_BYTES, "judge analysis output byte bound exceeded")
    return panels._detached(value)


def prepare_analysis_spec(panel: Path, declaration: Path, output: Path) -> dict:
    output = kernel._publication_path(output)
    watch = panels._Watch()
    capture = panels._Capture(panel, watch)
    raw = saved._file(Path(declaration), MAX_BYTES)
    watch.file(declaration, raw)
    value = _specification(capture, capture.entry("panel.json"), raw)
    watch.verify()
    kernel._publish_new(output, capture, "specification.json", value, protected=(panel, declaration))
    return value


def recheck_analysis_spec(directory: Path) -> dict:
    capture = saved.Capture(directory)
    return _checked_spec(capture, capture.entry("specification.json"))


def analyze_panel_results(specification: Path, results: Path, output: Path) -> dict:
    output = kernel._publication_path(output)
    watch = panels._Watch()
    capture = panels._Capture(specification, watch)
    spec_raw = capture.entry("specification.json")
    other = panels._Capture(results, watch)
    results_raw = other.entry("results.json")
    panels._checked_results(other, results_raw)
    panels._copy(capture, other)
    value = _analysis(capture, spec_raw, results_raw)
    watch.verify()
    kernel._publish_new(output, capture, "analysis.json", value, protected=(specification, results))
    return value


def recheck_panel_analysis(directory: Path) -> dict:
    capture = saved.Capture(directory)
    old = panels._read(capture.entry("analysis.json"), "judge analysis")
    _need(type(old) is dict and old.get("format") == FORMAT, "unsupported judge analysis format")
    value = _analysis(capture, capture.get(old["specification"]), capture.get(old["results"]))
    _need(canonical(old) == canonical(value), "analysis differs from exact captured reconstruction")
    return value
