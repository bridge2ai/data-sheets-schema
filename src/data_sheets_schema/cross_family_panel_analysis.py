"""Captured, descriptive paired semantic analysis; never rating or authorization.

The declaration selects every statistical policy explicitly. Recheck rebuilds
both acceptance and analysis from captured bytes with the supported code; no
captured Python, original evidence paths, provider or network is executed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
import ctypes
import hashlib
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile

import yaml

from data_sheets_schema import cross_family_panel as panels
from data_sheets_schema import cross_family_panel_results as accepted
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema.evaluation_model import model_family, same_family
from data_sheets_schema.judge_contract import evaluation_contract
from data_sheets_schema.support_plan import canonical, sha256

DECLARATION_FORMAT = "cross_family_panel_analysis_declaration_v1"
SPEC_FORMAT = "cross_family_panel_analysis_spec_v1"
FORMAT = "cross_family_panel_analysis_v1"
SOURCE = "src/data_sheets_schema/cross_family_panel_analysis.py"
MAX_BYTES = saved.MAX_MANIFEST_BYTES
MAX_OBSERVATIONS = 200_000
MAX_RESAMPLES = 100_000
MAX_BOOTSTRAP_WORK = 2_000_000
MAX_INDEX_ATTEMPTS = 128
MAX_INSTRUMENT_NODES = saved.MAX_NODES
MAX_INSTRUMENT_DEPTH = saved.MAX_DEPTH
LIMITS = {"manifest_bytes": MAX_BYTES, "observations": MAX_OBSERVATIONS,
          "resamples": MAX_RESAMPLES, "bootstrap_work": MAX_BOOTSTRAP_WORK,
          "index_attempts": MAX_INDEX_ATTEMPTS, "instrument_nodes": MAX_INSTRUMENT_NODES,
          "instrument_depth": MAX_INSTRUMENT_DEPTH}
RNG = "sha256_counter_rejection_v1"
ROLES = panels.ROLES
AnalysisError = panels.PanelError
LIMITATIONS = [
    "Descriptive arithmetic conditional on captured accepted pairs, not scientific eligibility or authorization.",
    "Caller declarations and hashes do not authenticate raters, provider execution or pre-outcome registration.",
    "Missing/rejected/unsupported slots and unselected records remain visible; no retry or outcome selection is performed.",
    "Unknown applicability context is not false. Applicability is enforced by acceptance, not measured as rater agreement.",
    "Positive same-minus-cross differences do not isolate family preference from rater severity or route effects.",
    "Declared blocks/strata do not establish independence, representative sampling or population interval coverage.",
    "Identical input bytes are clustered without deduplication; different bytes do not prove independent observations.",
    "Fitness/support panels, actual second ratings, canaries and human/provider decisions remain separate.",
]


def _need(condition, message):
    if not condition:
        raise AnalysisError(message)


def _read(raw, label):
    return saved._read(raw, label, limit=MAX_BYTES)


def _detach(value):
    raw = canonical(value)
    _need(len(raw) + 1 <= MAX_BYTES, "analysis output exceeds manifest byte bound")
    return _read(raw, "analysis output")


def _authority(capture):
    pin = accepted._source_pin(SOURCE)
    raw = saved._file(Path(__file__), saved.MAX_ARTIFACT_BYTES)
    _need(saved._pin(raw) == {k: pin[k] for k in ("bytes", "sha256")}, "analysis source changed during capture")
    capture.add(raw)
    return pin


def _choice(value, choices, label, pending):
    if value is None:
        pending.append(label)
    else:
        _need(type(value) is str and value in choices, f"unsupported {label}")


def _partition(value, key, selected, pending):
    label = "uncertainty." + key
    if value is None:
        pending.append(label)
        return
    _need(type(value) is list and len(value) <= panels.MAX_RECORDS, f"invalid {label}")
    id_key = "block_id" if key == "blocks" else "stratum_id"
    names, members = set(), []
    for row in value:
        panels._closed(row, {id_key, "record_ids"}, label)
        name = panels._identifier(row[id_key], id_key)
        _need(name not in names, f"duplicate {id_key}")
        names.add(name)
        _need(type(row["record_ids"]) is list and bool(row["record_ids"]), f"empty {id_key}")
        for rid in row["record_ids"]:
            panels._identifier(rid, "record_id")
        members.extend(row["record_ids"])
    _need(len(members) == len(set(members)) and set(members) == selected,
          f"{label} must partition exactly the selected record IDs")


def _policy(raw, panel_raw, panel):
    d = panels._closed(_read(raw, "analysis declaration"), {
        "format", "analysis_id", "panel_sha256", "record_ids", "instruments",
        "agreement", "gap", "grouping", "uncertainty"}, "analysis declaration")
    _need(d["format"] == DECLARATION_FORMAT, "explicit analysis declaration v1 required")
    panels._identifier(d["analysis_id"], "analysis_id")
    _need(panels._digest(d["panel_sha256"], "panel_sha256") == sha256(panel_raw),
          "analysis declaration names different panel bytes")
    ids = panels._list(d["record_ids"], "record_ids", panels.MAX_RECORDS)
    for rid in ids:
        panels._identifier(rid, "record_id")
    selected = set(ids)
    _need(len(ids) == len(selected) and selected <= {r["record_id"] for r in panel["records"]},
          "unknown or duplicate selected record")
    instruments = panels._list(d["instruments"], "instruments", 2)
    _need(bool(instruments), "at least one instrument must be selected")
    names = set()
    available = {(i["rubric"], i["version"]) for i in panel["instruments"]}
    for row in instruments:
        panels._closed(row, {"rubric", "version"}, "analysis instrument")
        panels._text(row["rubric"], "rubric")
        panels._text(row["version"], "version")
        key = (row["rubric"], row["version"])
        _need(key in available and key not in names, "unknown or duplicate analysis instrument")
        names.add(key)
    pending = []
    a = panels._closed(d["agreement"], {"unit", "weighting"}, "agreement policy")
    _choice(a["unit"], ("record_item", "resource_item"), "agreement.unit", pending)
    _choice(a["weighting"], ("equal_observation",), "agreement.weighting", pending)
    g = panels._closed(d["gap"], {"scale", "weighting"}, "gap policy")
    _choice(g["scale"], ("raw_total_points", "fixed_percentage_points", "adjusted_percentage_points"),
            "gap.scale", pending)
    _choice(g["weighting"], ("equal_record",), "gap.weighting", pending)
    _need(d["grouping"] == "instrument_domain_ordered_rater_pair", "unsupported grouping policy")
    u = panels._closed(d["uncertainty"], {"method", "confidence", "resamples", "seed", "quantile", "blocks", "strata"},
                       "uncertainty policy")
    _choice(u["method"], ("paired_cluster_percentile_v1",), "uncertainty.method", pending)
    _choice(u["quantile"], ("linear_n_minus_one",), "uncertainty.quantile", pending)
    for name in ("confidence", "resamples", "seed"):
        value = u[name]
        if value is None:
            pending.append("uncertainty." + name)
        elif name == "confidence":
            _need(type(value) in (int, float) and 0 < value < 1, "confidence must be strictly between zero and one")
        elif name == "resamples":
            _need(type(value) is int and 2 <= value <= MAX_RESAMPLES, "resamples exceeds integer bounds")
        else:
            _need(type(value) is int and 0 <= value < 2 ** 64, "seed must be an unsigned 64-bit integer")
    for key in ("blocks", "strata"):
        _partition(u[key], key, selected, pending)
    if u["blocks"] is not None:
        by_record = {rid: row["block_id"] for row in u["blocks"] for rid in row["record_ids"]}
        for cluster in panel["duplicate_content_clusters"]:
            blocks = {by_record[rid] for rid in cluster["record_ids"] if rid in selected}
            _need(len(blocks) <= 1, "identical input records cannot be split across bootstrap blocks")
    return d, pending


def _spec(capture, panel_raw, declaration_raw):
    panel = panels._recheck(capture, panel_raw)
    policy, pending = _policy(declaration_raw, panel_raw, panel)
    return _detach({"format": SPEC_FORMAT, "panel": capture.add(panel_raw),
                    "declaration": capture.add(declaration_raw), "policy": policy,
                    "pending_parameters": pending, "analysis_authority": _authority(capture),
                    "limits": dict(LIMITS), "readiness": {k: panel[k] for k in (
                        "missing_cells", "missing_slots", "pending_decisions", "decisions", "duplicate_content_clusters")},
                    "execution_authorized": False, "scientific_eligibility": False,
                    "chronology_authenticated": False, "limitations": list(LIMITATIONS)}), panel


def _checked_spec(capture, raw):
    old = _read(raw, "analysis specification")
    _need(type(old) is dict and old.get("format") == SPEC_FORMAT, "unsupported analysis specification")
    # Require the recorded source artifact too. Reading today's equal source
    # cannot stand in for a missing/corrupt captured copy during recheck.
    capture.get(old["analysis_authority"])
    value, panel = _spec(capture, capture.get(old["panel"], limit=MAX_BYTES),
                         capture.get(old["declaration"], limit=MAX_BYTES))
    _need(canonical(old) == canonical(value), "specification differs from captured reconstruction or current analysis code")
    return value, panel


def _checked_results(capture, raw):
    """Same reconstructor as recheck_panel_results, on this one captured snapshot."""
    old = _read(raw, "captured panel results")
    _need(type(old) is dict and old.get("format") == accepted.FORMAT, "unsupported panel results")
    files = old.get("captured_files")
    _need(type(files) is dict, "panel results require captured_files")

    def read_result(name):
        _need(name in files, "submitted result capture is missing")
        return capture.get(files[name], limit=accepted.MAX_RESULT_BYTES)

    value = accepted._results(capture, capture.get(old["panel"], limit=panels.MAX_PANEL_BYTES),
                              capture.get(old["submissions"], limit=accepted.MAX_RESULTS_BYTES), read_result)
    _need(canonical(old) == canonical(value), "panel results differ from captured acceptance reconstruction")
    return value


def _metric(matrix, categories):
    n = sum(sum(row) for row in matrix)
    agreeing = sum(matrix[i][i] for i in range(len(categories)))
    marginals = {"row_totals": [sum(row) for row in matrix],
                 "column_totals": [sum(row[i] for row in matrix) for i in range(len(categories))]}
    if not n:
        return {"n": 0, "agreeing": 0, "categories": list(categories), "confusion_matrix": matrix, **marginals,
                "observed_agreement": None, "expected_agreement": None, "kappa": None,
                "agreement_reason": "no_observed_pairs", "kappa_reason": "no_observed_pairs"}
    po = Fraction(agreeing, n)
    pe = sum(Fraction(sum(matrix[i]) * sum(row[i] for row in matrix), n * n)
             for i in range(len(categories)))
    return {"n": n, "agreeing": agreeing, "categories": list(categories), "confusion_matrix": matrix, **marginals,
            "observed_agreement": float(po), "expected_agreement": float(pe),
            "kappa": None if pe == 1 else float((po - pe) / (1 - pe)),
            "agreement_reason": None, "kappa_reason": "expected_agreement_is_one" if pe == 1 else None}


def agreement_statistics(score_pairs, categories):
    """Unweighted nominal agreement on one explicit existing semantic domain."""
    _need(type(categories) in (tuple, list) and tuple(categories) in ((0, 1), (0, 3, 5))
          and all(type(c) is int for c in categories), "unsupported agreement categories")
    _need(type(score_pairs) in (list, tuple) and len(score_pairs) <= MAX_OBSERVATIONS, "score pair bound exceeded")
    matrix = [[0 for _ in categories] for _ in categories]
    for pair in score_pairs:
        _need(type(pair) in (list, tuple) and len(pair) == 2
              and all(type(v) is int and v in categories for v in pair), "score outside declared categorical domain")
        matrix[categories.index(pair[0])][categories.index(pair[1])] += 1
    return _metric(matrix, categories)


class _InstrumentLoader(yaml.SafeLoader):
    """Preserve rubric scalar keys, refusing collisions before they are lost."""

    def construct_mapping(self, node, deep=False):
        _need(isinstance(node, yaml.MappingNode), "instrument mapping node required")
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=True)
            _need(type(key) in (str, int, float, bool, type(None)), "unsupported instrument mapping key")
            _need(type(key) is not float or math.isfinite(key), "nonfinite instrument mapping key")
            # Python mapping equality also catches numeric/bool collisions;
            # quoted numeric strings remain distinct, without coercion.
            _need(key not in mapping, "duplicate instrument mapping key")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def _instrument_yaml(raw):
    """Bounded captured rubric YAML, separate from string-key record parsers."""
    _need(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "instrument exceeds byte bounds or is empty")
    try:
        text = raw.decode("utf-8")
        nodes = depth = 0
        # Refuse alias expansion and excessive structure before composition.
        for event in yaml.parse(text, Loader=yaml.SafeLoader):
            _need(not isinstance(event, yaml.AliasEvent), "instrument aliases are unsupported")
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent, yaml.ScalarEvent)):
                nodes += 1
                _need(nodes <= MAX_INSTRUMENT_NODES, "instrument node bound exceeded")
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                _need(depth <= MAX_INSTRUMENT_DEPTH, "instrument depth bound exceeded")
            elif isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
        value = yaml.load(text, Loader=_InstrumentLoader)
        _need(type(value) is dict, "instrument root must be a mapping")
        pending = [value]
        while pending:
            item = pending.pop()
            if type(item) is str:
                item.encode("utf-8")
            elif type(item) is dict:
                pending.extend(item)
                pending.extend(item.values())
            elif type(item) is list:
                pending.extend(item)
            else:
                _need(type(item) in (int, float, bool, type(None)), "unsupported instrument scalar")
                _need(type(item) is not float or math.isfinite(item), "nonfinite instrument scalar")
        return value
    except (ValueError, TypeError, RecursionError, UnicodeError, yaml.YAMLError) as exc:
        raise AnalysisError("captured instrument is not bounded, duplicate-free safe YAML") from exc


def _rules(capture, record, instrument):
    source = _instrument_yaml(capture.get(instrument["resources"]["rubric"], limit=MAX_BYTES))
    return evaluation_contract(instrument["rubric"], source, record["context"]["normalized"],
                               {"id": "scope-contract"})["items"]


def _scores(rating, rubric, rules):
    items = {}
    for group in rating["elements" if rubric == "rubric10" else "categories"]:
        for item in group["sub_elements" if rubric == "rubric10" else "questions"]:
            key = item["item_id"] if rubric == "rubric10" else f"Q{item['id']}"
            _need(key not in items, "duplicate accepted item identity")
            unit_scores = {row["path"]: None if row["score"] is None else int(row["score"])
                           for row in item["unit_scores"]}
            applicable = rules[key]["applicable"]
            value = min(unit_scores.values()) if applicable else None
            items[key] = {"score": value, "unit_scores": unit_scores}
    _need(set(items) == set(rules), "accepted item roster differs from captured rubric")
    total = sum(item["score"] for item in items.values() if item["score"] is not None)
    fixed = sum(rule["fixed_max_score"] for rule in rules.values())
    adjusted = sum(rule["fixed_max_score"] for rule in rules.values() if rule["applicable"])
    return {"total_points": total, "max_points": fixed, "adjusted_max_points": adjusted,
            "fixed_percentage": float(Fraction(100 * total, fixed)),
            "adjusted_percentage": float(Fraction(100 * total, adjusted)) if adjusted else None,
            "excluded_items": sorted(key for key, rule in rules.items() if not rule["applicable"])}, items


def _attribution(record, slots):
    problems = []
    generator = record["generator"]
    family = model_family(generator["model"])
    if family is None or family != generator["family"]:
        problems.append("generator_family_unknown_or_conflicting")
    relations = {}
    for role in ROLES:
        slot = slots[role]
        for field in ("model", "family", "rater", "route"):
            if slot[field] is None:
                problems.append(f"{role}.{field}_not_declared")
        if model_family(slot["model"]) is None or model_family(slot["model"]) != slot["family"]:
            problems.append(f"{role}.family_unknown_or_conflicting")
        relations[role] = same_family(slot["model"], generator["model"])
    if relations != {"same_family": True, "cross_family": False}:
        problems.append("roles_not_one_recognized_same_and_one_recognized_cross_family")
    return problems


def _gap_value(scores, scale):
    values = []
    for role in ROLES:
        score = scores[role]
        if scale == "raw_total_points":
            values.append(Fraction(score["total_points"]))
        else:
            maximum = score["max_points" if scale == "fixed_percentage_points" else "adjusted_max_points"]
            if not maximum:
                return None
            values.append(Fraction(100 * score["total_points"], maximum))
    return values[0] - values[1]


def _identity(instrument, slots, domain=None):
    value = {"rubric": instrument["rubric"], "version": instrument["version"],
             "instrument_sha256": sha256(canonical(instrument)),
             "raters": {role: {key: slots[role][key] for key in ("model", "family", "rater", "route")} for role in ROLES}}
    if domain is not None:
        value["domain"] = list(domain)
    return value


def _rows(capture, spec, panel, results):
    policy = spec["policy"]
    selected_ids = set(policy["record_ids"])
    selected_instruments = {(row["rubric"], row["version"]) for row in policy["instruments"]}
    slots = {(s["record_id"], s["rubric"], s["role"]): s for s in panel["slots"]}
    outcomes = {(s["record_id"], s["rubric"], s["role"]): s for s in results["rows"]}
    pairs, observations, agreement, gaps = [], [], {}, {}
    gap_ready = all(value is not None for value in policy["gap"].values())
    for record in panel["records"]:
        for instrument in panel["instruments"]:
            rid, rubric = record["record_id"], instrument["rubric"]
            chosen = rid in selected_ids and (rubric, instrument["version"]) in selected_instruments
            members = {role: slots[(rid, rubric, role)] for role in ROLES}
            rows = {role: outcomes[(rid, rubric, role)] for role in ROLES}
            complete = all(row["state"] == "accepted" for row in rows.values())
            attribution = _attribution(record, members)
            attributed = complete and not attribution
            rules = _rules(capture, record, instrument)
            scores, items = {}, {}
            for role, row in rows.items():
                if row["state"] == "accepted":
                    rating = saved._read(capture.get(row["result"], limit=accepted.MAX_RESULT_BYTES),
                                         "accepted rating", limit=accepted.MAX_RESULT_BYTES)
                    scores[role], items[role] = _scores(rating, rubric, rules)
                else:
                    scores[role] = None
            identity = _identity(instrument, members)
            reasons = ([] if chosen else ["record_or_instrument_not_selected"])
            if not complete:
                reasons.append("pair_not_complete")
            if attribution:
                reasons.append("pair_not_attributed")
            if not gap_ready:
                reasons.append("gap_policy_pending")
            gap = _gap_value(scores, policy["gap"]["scale"]) if not reasons else None
            if not reasons and gap is None:
                reasons.append("zero_applicable_maximum")
            pair = {"record_id": rid, "rubric": rubric, "version": instrument["version"],
                    "project": record["project"], "cohort": record["cohort"],
                    "input_sha256": record["input"]["sha256"], "binding_sha256": members[ROLES[0]]["binding_sha256"],
                    "selected": chosen, "states": {r: rows[r]["state"] for r in ROLES},
                    "attempts": {r: members[r]["attempt_id"] for r in ROLES}, "raters": identity["raters"],
                    "score_pair_complete": complete, "attributed_role_pair": attributed,
                    "attribution_reasons": attribution, "scores": scores,
                    "gap": None if gap is None else float(gap), "gap_unavailable_reasons": reasons,
                    "context": record["context"]}
            index = len(pairs)
            pairs.append(pair)
            if not chosen:
                continue
            key = canonical(identity)
            group = gaps.setdefault(key, {"identity": identity, "pair_indices": []})
            group["pair_indices"].append(index)
            for domain in sorted({(0, 1) if rule["fixed_max_score"] == 1 else (0, 3, 5) for rule in rules.values()}):
                aid = _identity(instrument, members, domain)
                ag = agreement.setdefault(canonical(aid), {"identity": aid, "pair_indices": [], "observation_indices": []})
                ag["pair_indices"].append(index)
            unit = policy["agreement"]["unit"]
            if unit is None:
                continue
            paths = [None] if unit == "record_item" else [u["path"] for u in record["evaluation_scope"]["units"]]
            _need(len(observations) + len(paths) * len(rules) <= MAX_OBSERVATIONS, "analysis observation bound exceeded")
            for item_id in sorted(rules):
                rule = rules[item_id]
                domain = [0, 1] if rule["fixed_max_score"] == 1 else [0, 3, 5]
                ag = agreement[canonical(_identity(instrument, members, domain))]
                for path in paths:
                    values = {r: (None if r not in items else items[r][item_id]["score"] if path is None
                                  else items[r][item_id]["unit_scores"][path]) for r in ROLES}
                    state = ("not_applicable" if not rule["applicable"] else "unavailable_partner" if not complete
                             else "unattributed" if not attributed else "observed")
                    ag["observation_indices"].append(len(observations))
                    observations.append({"record_id": rid, "rubric": rubric, "item_id": item_id,
                        "resource_path": path, "domain": domain, "applicable": rule["applicable"],
                        "same_score": values[ROLES[0]], "cross_score": values[ROLES[1]],
                        "attributed_role_pair": attributed, "state": state,
                        "agrees": values[ROLES[0]] == values[ROLES[1]] if complete and rule["applicable"] else None})
    return pairs, observations, [agreement[k] for k in sorted(agreement)], [gaps[k] for k in sorted(gaps)]


class _IndexStream:
    """Portable exact index draws; all byte/range semantics are versioned here."""
    def __init__(self, seed):
        self.prefix = b"cross-family-analysis-index-v1\0" + seed.to_bytes(8, "big")
        self.counter = 0

    def index(self, size):
        _need(type(size) is int and 0 < size <= panels.MAX_RECORDS, "invalid bootstrap index range")
        threshold = (2 ** 256 // size) * size
        for _ in range(MAX_INDEX_ATTEMPTS):
            _need(self.counter < 2 ** 64, "bootstrap counter exhausted")
            raw = hashlib.sha256(self.prefix + self.counter.to_bytes(8, "big")).digest()
            self.counter += 1
            value = int.from_bytes(raw, "big")
            if value < threshold:
                return value % size
        raise AnalysisError("bootstrap index rejection bound exceeded")


def _quantile(values, p):
    ordered = sorted(values)
    h = Fraction(len(ordered) - 1) * p
    low = h.numerator // h.denominator
    high = min(low + 1, len(ordered) - 1)
    f = float(h - low)
    return (1 - f) * ordered[low] + f * ordered[high]


def _bootstrap(identity, contributions, kind, categories, u, pending, observed, budget):
    names = ("exact_agreement", "kappa") if kind == "agreement" else ("mean",)
    result = {"method": u["method"], "confidence": u["confidence"], "resamples": u["resamples"],
              "seed": u["seed"], "quantile": u["quantile"], "rng": RNG,
              "rng_runtime_independent": True, "strata": [], "draws": [], "draws_completed": 0,
              "rng_counters_consumed": 0, "schedule_sha256": None,
              "intervals": {}, "unavailable_reasons": []}
    reasons = [name + "_pending" for name in pending if name.startswith("uncertainty.")]
    blocks = u["blocks"]
    strata = u["strata"]
    projection = []
    if strata is not None:
        stratum_by_record = {rid: s["stratum_id"] for s in strata for rid in s["record_ids"]}
        if blocks is not None:
            for b in sorted(blocks, key=lambda r: r["block_id"]):
                if len({stratum_by_record[rid] for rid in b["record_ids"]}) > 1:
                    reasons.append("block_crosses_strata:" + b["block_id"])
        total = sum(c["n"] for c in contributions.values())
        for s in sorted(strata, key=lambda r: r["stratum_id"]):
            ids = sorted(rid for rid in s["record_ids"] if rid in contributions)
            n = sum(contributions[rid]["n"] for rid in ids)
            names_in_stratum = []
            if blocks is not None:
                for b in sorted(blocks, key=lambda r: r["block_id"]):
                    if not set(b["record_ids"]) & set(ids):
                        continue
                    names_in_stratum.append(b["block_id"])
                if len(names_in_stratum) < 2:
                    reasons.append("fewer_than_two_contributing_blocks:" + s["stratum_id"])
            weight = Fraction(n, total) if total else Fraction(0)
            result["strata"].append({"stratum_id": s["stratum_id"], "record_ids": s["record_ids"],
                "contributing_record_ids": ids, "blocks": names_in_stratum,
                "observation_count": n if kind == "agreement" else None, "record_count": len(ids),
                "weight": float(weight), "weight_fraction": [weight.numerator, weight.denominator]})
            projection.append((s["stratum_id"], names_in_stratum, weight))
    if not contributions:
        reasons.append("no_eligible_contributions")
    if all(value is None for value in observed.values()):
        reasons.append("observed_statistics_undefined")
    reasons = list(dict.fromkeys(reasons))
    result["unavailable_reasons"] = reasons
    if reasons:
        for name in names:
            result["intervals"][name] = {"lower": None, "upper": None,
                "reason": ";".join(reasons), "undefined_draws": 0}
        return result
    # Preaggregated record contributions avoid resampling individual items.
    block_records = {b["block_id"]: sorted(rid for rid in b["record_ids"] if rid in contributions) for b in blocks}
    # A large block can be drawn G times, not merely once. Bound that worst
    # case before expanding any draw, including each contingency cell update.
    per_draw = sum(len(names) * (1 + max(len(block_records[b]) for b in names))
                   for _, names, _ in projection)
    work = u["resamples"] * (1 + per_draw * max(1, len(categories) ** 2))
    size = u["resamples"] * (500 + sum(len(b) * (140 + len(s)) for s, b, _ in projection))
    budget["work"] += work
    budget["bytes"] += size
    _need(budget["work"] <= MAX_BOOTSTRAP_WORK, "bootstrap computational work bound exceeded")
    _need(budget["bytes"] <= MAX_BYTES, "bootstrap output work bound exceeded")
    stream = _IndexStream(u["seed"])
    schedule = hashlib.sha256()
    for index in range(u["resamples"]):
        drawn = []
        mean = Fraction(0)
        matrix = [[Fraction(0) for _ in categories] for _ in categories] if kind == "agreement" else None
        undefined = []
        for stratum, candidates, weight in projection:
            choices = [candidates[stream.index(len(candidates))] for _ in candidates]
            drawn.append({"stratum_id": stratum, "blocks": choices})
            records = [rid for bid in choices for rid in block_records[bid]]
            n = sum(contributions[rid]["n"] for rid in records)
            if not n:
                undefined.append("empty_draw_stratum:" + stratum)
                continue
            if kind == "gap":
                mean += weight * sum(contributions[rid]["sum"] for rid in records) / n
            else:
                for i in range(len(categories)):
                    for j in range(len(categories)):
                        matrix[i][j] += weight * Fraction(sum(contributions[rid]["matrix"][i][j] for rid in records), n)
        metrics = {name: None for name in names}
        metric_reasons = {}
        if not undefined:
            if kind == "gap":
                metrics["mean"] = float(mean)
            else:
                po = sum(matrix[i][i] for i in range(len(categories)))
                pe = sum(sum(matrix[i]) * sum(row[i] for row in matrix) for i in range(len(categories)))
                metrics["exact_agreement"] = float(po)
                metrics["kappa"] = None if pe == 1 else float((po - pe) / (1 - pe))
                if pe == 1:
                    metric_reasons["kappa"] = "expected_agreement_is_one"
        else:
            metric_reasons = {name: ";".join(undefined) for name in names}
        schedule.update(canonical({"index": index, "strata": drawn}) + b"\n")
        result["draws"].append({"index": index, "strata": drawn, "metrics": metrics, "undefined_reasons": metric_reasons})
    result["schedule_sha256"] = schedule.hexdigest()
    result["draws_completed"] = len(result["draws"])
    result["rng_counters_consumed"] = stream.counter
    tail = (1 - Fraction(str(u["confidence"]))) / 2
    for name in names:
        values = [row["metrics"][name] for row in result["draws"]]
        missing = sum(value is None for value in values)
        reason = "observed_statistic_undefined" if observed[name] is None else "undefined_bootstrap_draws" if missing else None
        result["intervals"][name] = {"lower": _quantile(values, tail) if reason is None else None,
            "upper": _quantile(values, 1 - tail) if reason is None else None,
            "reason": reason, "undefined_draws": missing}
    return result


def _statistics(spec, pairs, observations, agreement, gaps):
    policy, pending = spec["policy"], spec["pending_parameters"]
    # Group reports retain every declared stratum, even when it contributes
    # nothing. Bound this Cartesian metadata work as well as actual draws.
    u = policy["uncertainty"]
    projection_work = (len(agreement) + len(gaps)) * (
        1 + len(policy["record_ids"]) + len(u["strata"] or []) * (1 + len(u["blocks"] or [])))
    _need(projection_work <= MAX_BOOTSTRAP_WORK, "bootstrap projection work bound exceeded")
    budget = {"work": projection_work, "bytes": 0}
    for group in agreement:
        categories = group["identity"]["domain"]
        eligible = [observations[i] for i in group["observation_indices"] if observations[i]["state"] == "observed"]
        ready = all(value is not None for value in policy["agreement"].values())
        chosen = eligible if ready else []
        metrics = agreement_statistics([(o["same_score"], o["cross_score"]) for o in chosen], categories)
        if not ready:
            metrics["agreement_reason"] = metrics["kappa_reason"] = "agreement_policy_pending"
        group["metrics"] = metrics
        group["selected_record_ids"] = [pairs[i]["record_id"] for i in group["pair_indices"]]
        group["record_ids"] = sorted({o["record_id"] for o in chosen})
        group["denominator"] = {"selected_records": len(group["pair_indices"]),
            "selected_observations": len(group["observation_indices"]),
            "states": dict(Counter(observations[i]["state"] for i in group["observation_indices"]))}
        contributions = {}
        for o in chosen:
            c = contributions.setdefault(o["record_id"], {"n": 0, "matrix": [[0 for _ in categories] for _ in categories]})
            c["n"] += 1
            c["matrix"][categories.index(o["same_score"])][categories.index(o["cross_score"])] += 1
        group["uncertainty"] = _bootstrap(group["identity"], contributions, "agreement", categories,
            policy["uncertainty"], pending, {"exact_agreement": metrics["observed_agreement"], "kappa": metrics["kappa"]}, budget)
    for group in gaps:
        chosen = [pairs[i] for i in group["pair_indices"] if pairs[i]["gap"] is not None]
        values = [_gap_value(p["scores"], policy["gap"]["scale"]) for p in chosen]
        reason = None if values else "gap_policy_pending" if any(v is None for v in policy["gap"].values()) else "no_eligible_pairs"
        group["metrics"] = {"n": len(values), "mean": float(sum(values) / len(values)) if values else None,
            "positive": sum(v > 0 for v in values), "negative": sum(v < 0 for v in values),
            "ties": sum(v == 0 for v in values), "reason": reason, "scale": policy["gap"]["scale"]}
        group["selected_record_ids"] = [pairs[i]["record_id"] for i in group["pair_indices"]]
        group["record_ids"] = [p["record_id"] for p in chosen]
        group["denominator"] = {"selected_records": len(group["pair_indices"]), "eligible_records": len(values),
            "excluded_records": [{"record_id": pairs[i]["record_id"], "reasons": pairs[i]["gap_unavailable_reasons"]}
                                 for i in group["pair_indices"] if pairs[i]["gap"] is None]}
        contributions = {p["record_id"]: {"n": 1, "sum": value} for p, value in zip(chosen, values)}
        group["uncertainty"] = _bootstrap(group["identity"], contributions, "gap", [], policy["uncertainty"], pending,
                                          {"mean": group["metrics"]["mean"]}, budget)
    return budget


def _analysis(capture, specification_raw, results_raw):
    spec, panel = _checked_spec(capture, specification_raw)
    results = _checked_results(capture, results_raw)
    _need(spec["panel"] == results["panel"], "analysis specification and results name different panel bytes")
    pairs, observations, agreement, gaps = _rows(capture, spec, panel, results)
    work = _statistics(spec, pairs, observations, agreement, gaps)
    selected = [p for p in pairs if p["selected"]]
    report = {"format": FORMAT, "specification": capture.add(specification_raw), "results": capture.add(results_raw),
        "analysis_authority": _authority(capture), "policy": spec["policy"], "pending_parameters": spec["pending_parameters"],
        "slots": results["rows"], "pairs": pairs, "observations": observations,
        "agreement_groups": agreement, "gap_groups": gaps, "work": work,
        "counts": {"slots": results["counts"], "required_pairs": len(pairs), "selected_pairs": len(selected),
            "unselected_pairs": len(pairs) - len(selected),
            "score_pair_complete": sum(p["score_pair_complete"] for p in selected),
            "attributed_role_pair": sum(p["attributed_role_pair"] for p in selected),
            "unattributed_complete_pairs": sum(p["score_pair_complete"] and not p["attributed_role_pair"] for p in selected),
            "observations": len(observations), "observation_states": dict(Counter(o["state"] for o in observations))},
        "readiness": results["readiness"], "coverage": {k: panel[k] for k in ("matrix", "cells", "counts")},
        "results_rechecked": True, "execution_authorized": False, "scientific_eligibility": False,
        "chronology_authenticated": False, "limitations": list(LIMITATIONS)}
    return _detach(report)


def _write_bytes(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _rename_new(source, destination):
    """Atomic directory installation that cannot replace an occupied pathname."""
    source_raw, destination_raw = os.fsencode(source), os.fsencode(destination)
    _need(b"\0" not in source_raw and b"\0" not in destination_raw, "NUL in native publication path")
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function = getattr(libc, "renamex_np", None)
        _need(function is not None, "atomic no-replace publication unavailable")
        function.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        function.restype = ctypes.c_int
        result = function(source_raw, destination_raw, 4)  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        function = getattr(libc, "renameat2", None)
        _need(function is not None, "atomic no-replace publication unavailable")
        function.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
        function.restype = ctypes.c_int
        result = function(-100, source_raw, -100, destination_raw, 1)  # AT_FDCWD, RENAME_NOREPLACE
    else:
        raise AnalysisError("atomic no-replace directory publication unsupported on this platform")
    if result:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), str(destination))


def _publication_path(output):
    _need(b"\0" not in os.fsencode(output), "NUL in publication output path")
    return Path(output)


def _publish_new(output, capture, filename, document, *, protected=()):
    output = _publication_path(output)
    raw = canonical(document) + b"\n"
    _need(len(raw) <= MAX_BYTES, "analysis output exceeds manifest byte bound")
    _need(not output.exists() and not output.is_symlink(), "output already exists")
    _need(output.parent.is_dir(), "output parent must exist")
    parent = output.parent.resolve()
    destination = parent / output.name
    for path in (capture.root, *(Path(p).resolve() for p in protected)):
        _need(not destination.is_relative_to(path), "output cannot be inside input evidence")
    stage = Path(tempfile.mkdtemp(prefix=".cross-family-analysis-", dir=parent))
    try:
        artifacts = stage / "artifacts"
        artifacts.mkdir()
        for digest, blob in sorted(capture.blobs.items()):
            _write_bytes(artifacts / digest, blob)
        _write_bytes(stage / filename, raw)
        _sync_directory(artifacts)
        _sync_directory(stage)
        _rename_new(stage, destination)
        _sync_directory(parent)
    finally:
        if stage.exists():
            failed = sys.exc_info()[0] is not None
            try:
                shutil.rmtree(stage)
            except OSError:
                if not failed:
                    raise


def prepare_analysis_spec(panel: Path, declaration: Path, output: Path) -> dict:
    """Capture explicit policies and exact panel; no result or chronology claim."""
    output = _publication_path(output)
    capture = saved.Capture(panel)
    panel_raw = capture.entry("panel.json", limit=panels.MAX_PANEL_BYTES)
    declaration_raw = saved._file(Path(declaration), MAX_BYTES)
    value, _ = _spec(capture, panel_raw, declaration_raw)
    _publish_new(output, capture, "specification.json", value, protected=(declaration,))
    return value


def recheck_analysis_spec(directory: Path) -> dict:
    """Reconstruct the captured policy/panel, without original paths."""
    capture = saved.Capture(directory)
    value, _ = _checked_spec(capture, capture.entry("specification.json", limit=MAX_BYTES))
    return value


def analyze_panel_results(specification: Path, results: Path, output: Path) -> dict:
    """Compute all selected metrics; unavailable estimates remain explicit."""
    output = _publication_path(output)
    capture = saved.Capture(specification)
    spec_raw = capture.entry("specification.json", limit=MAX_BYTES)
    _checked_spec(capture, spec_raw)
    source = saved.Capture(results)
    result_raw = source.entry("results.json", limit=accepted.MAX_RESULTS_BYTES)
    _checked_results(source, result_raw)
    for blob in source.blobs.values():
        capture.add(blob)
    value = _analysis(capture, spec_raw, result_raw)
    _publish_new(output, capture, "analysis.json", value, protected=(results,))
    return value


def recheck_panel_analysis(directory: Path) -> dict:
    """Rebuild acceptance, joins, every draw and numerical result portably."""
    capture = saved.Capture(directory)
    old = _read(capture.entry("analysis.json", limit=MAX_BYTES), "analysis report")
    _need(type(old) is dict and old.get("format") == FORMAT, "unsupported analysis report")
    expected = _analysis(capture, capture.get(old["specification"], limit=MAX_BYTES),
                         capture.get(old["results"], limit=accepted.MAX_RESULTS_BYTES))
    _need(canonical(old) == canonical(expected), "analysis differs from captured reconstruction")
    return expected
