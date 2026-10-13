"""Independent arithmetic on actual captured support/fitness pairs; no study labels."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import shutil

from click.testing import CliRunner
import pytest

from data_sheets_schema import cross_family_judge_analysis as analysis
from data_sheets_schema import cross_family_judge_panel as panel
from data_sheets_schema import cross_family_panel_analysis as kernel
from data_sheets_schema.cli.evaluate import evaluate
from data_sheets_schema.support_plan import canonical, sha256
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401
from tests.test_evaluation.test_cross_family_judge_panel import (
    ROLES, make_case, make_results, snapshot, write,
)

SUPPORT = ("contradicted", "status_shifted", "relationship_unsupported", "wrong_document",
           "unsupported", "partially_supported", "supported")
FAILURES = ("none", "form", "target", "substance")
THRESHOLD = ("does_not_meet_threshold", "meets_threshold")
ANALYSIS_KEYS = {"format", "specification", "results", "policy", "pending_parameters", "slots", "pairs",
    "agreement_groups", "gap_groups", "counts", "coverage", "pending_decisions", "readiness", "authority",
    "limits", "scientific_eligibility", "execution_authorized"}


def policy(case, *, selected=None, favorable=None, threshold=None, strata=None, blocks=None, resamples=24):
    ids = [p["pair_id"] for p in case.panel["pairs"]] if selected is None else selected
    selected_set = set(ids)
    records = sorted({p["record_id"] for p in case.panel["pairs"] if p["pair_id"] in selected_set})
    return {"format": "cross_family_judge_analysis_declaration_v1", "analysis_id": "invented-analysis",
        "panel_sha256": sha256((case.panel_path / "panel.json").read_bytes()), "pair_ids": ids,
        "agreement": {"weighting": "equal_target"}, "gap": {"weighting": "equal_record"},
        "support_indicator": {"favorable_verdicts": favorable}, "fitness_threshold": threshold,
        "grouping": "instrument_context_kind_ordered_rater_configuration_and_evidence_basis",
        "uncertainty": {"method": "paired_cluster_percentile_v1", "confidence": 0.9,
            "resamples": resamples, "seed": 7, "quantile": "linear_n_minus_one",
            "blocks": [{"block_id": "block-" + r, "record_ids": [r]} for r in records] if blocks is None else blocks,
            "strata": ([{"stratum_id": "all", "record_ids": records}] if records else []) if strata is None else strata}}


def run(case, results, declared=None, *, name="analysis"):
    declared = policy(case) if declared is None else declared
    declaration = write(case.root / (name + "-declaration.json"), declared)
    spec_path = case.root / (name + "-specification")
    spec = analysis.prepare_analysis_spec(case.panel_path, declaration, spec_path)
    output = case.root / name
    report = analysis.analyze_panel_results(spec_path, results.path, output)
    return report, output, spec_path, spec


def group(report, metric):
    rows = [g for name in ("agreement_groups", "gap_groups") for g in report[name] if g["metric"] == metric]
    assert len(rows) == 1, (metric, [g["identity"] for g in rows])
    return rows[0]


def categorical_oracle(pairs, categories):
    """Hand-counted nominal table and exact arithmetic, independent of source helpers."""
    table = [[sum(a == x and b == y for a, b in pairs) for y in categories] for x in categories]
    n = len(pairs)
    if not n:
        return table, None, None, None
    po = Fraction(sum(a == b for a, b in pairs), n)
    left, right = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(Fraction(left[c] * right[c], n * n) for c in categories)
    return table, po, pe, None if pe == 1 else (po - pe) / (1 - pe)


def check_nominal(actual, pairs, categories):
    table, po, pe, kappa = categorical_oracle(pairs, categories)
    assert actual["categories"] == list(categories)
    assert actual["confusion_matrix"] == table
    assert actual["row_totals"] == [sum(row) for row in table]
    assert actual["column_totals"] == [sum(row[i] for row in table) for i in range(len(categories))]
    assert actual["n"] == len(pairs)
    assert actual["observed_agreement"] == (None if po is None else float(po))
    assert actual["expected_agreement"] == (None if pe is None else float(pe))
    assert actual["kappa"] == (None if kappa is None else float(kappa))


def quantile(values, probability):
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    low = index.numerator // index.denominator
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] * (1 - (index - low)) + ordered[high] * (index - low)


def interval_oracle(actual, values, confidence, observed):
    missing = sum(v is None for v in values)
    assert actual["undefined_draws"] == missing
    if missing or observed is None:
        assert actual["lower"] is None and actual["upper"] is None and actual["reason"]
    else:
        tail = (1 - Fraction(confidence)) / 2
        assert actual["lower"] == float(quantile(values, tail))
        assert actual["upper"] == float(quantile(values, 1 - tail))
        assert actual["reason"] is None


def independent_schedule(blocks, strata, *, seed, resamples):
    """Literal adopted SHA256 counter specification; never calls the production RNG."""
    counter = 0
    draws = []
    for index in range(resamples):
        rows = []
        for stratum in sorted(strata, key=lambda r: r["stratum_id"]):
            members = set(stratum["record_ids"])
            names = sorted(b["block_id"] for b in blocks if members.intersection(b["record_ids"]))
            selected = []
            while len(selected) < len(names):
                raw = b"cross-family-analysis-index-v1\0" + seed.to_bytes(8, "big") + counter.to_bytes(8, "big")
                value = int.from_bytes(hashlib.sha256(raw).digest(), "big")
                counter += 1
                ceiling = (2 ** 256 // len(names)) * len(names)
                if value < ceiling:
                    selected.append(names[value % len(names)])
            rows.append({"stratum_id": stratum["stratum_id"], "blocks": selected})
        draws.append({"index": index, "strata": rows})
    return draws, counter


def test_actual_analysis_cli_complete_capture_relocates_without_originals(fixture, tmp_path, monkeypatch):
    case = make_case(fixture, tmp_path, count=2)
    result = make_results(case)
    declared = policy(case, favorable=["supported"], threshold={"cutoff": .5, "boundary": "ge"})
    declaration = write(tmp_path / "analysis-declaration.json", declared)
    cli = CliRunner()
    prepared = cli.invoke(evaluate, ["cross-family-judges", "prepare-analysis", "--panel", str(case.panel_path),
        "--declaration", str(declaration), "--output", str(tmp_path / "specification")])
    assert prepared.exit_code == 0, prepared.output
    rechecked = cli.invoke(evaluate, ["cross-family-judges", "recheck-analysis-spec", "--specification", str(tmp_path / "specification")])
    assert rechecked.exit_code == 0, rechecked.output
    assert json.loads(rechecked.output) == json.loads(prepared.output)
    executed = cli.invoke(evaluate, ["cross-family-judges", "analyze", "--specification", str(tmp_path / "specification"),
        "--results", str(result.path), "--output", str(tmp_path / "analysis")])
    assert executed.exit_code == 0, executed.output
    report = json.loads(executed.output)
    assert set(report) == ANALYSIS_KEYS
    assert report["scientific_eligibility"] is False and report["execution_authorized"] is False
    assert set(report["pending_decisions"]) == set(case.panel["pending_decisions"])
    assert len(report["slots"]) == 16 and len(report["pairs"]) == 8
    moved = tmp_path / "portable"
    shutil.copytree(tmp_path / "analysis", moved)
    for path in list(tmp_path.iterdir()):
        if path != moved:
            path.rename(path.with_name("unavailable-" + path.name))
    original = Path.read_bytes
    def captured_only(path):
        assert path.is_relative_to(moved), path
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", captured_only)
    checked = cli.invoke(evaluate, ["cross-family-judges", "recheck-analysis", "--analysis", str(moved)])
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.output) == report


def test_seven_support_categories_are_nominal_not_numeric_or_binary(fixture, tmp_path):
    case = make_case(fixture, tmp_path, count=4, axes=("grounding_v3",), pointers=("/count", "/enabled"))
    values = [(SUPPORT[i % 7], SUPPORT[(i + 1) % 7] if i in (2, 6) else SUPPORT[i % 7]) for i in range(8)]
    index = {p["pair_id"]: i for i, p in enumerate(case.panel["pairs"])}
    result = make_results(case, values=lambda p, r: {"verdict": values[index[p["pair_id"]]][ROLES.index(r)]})
    report, *_ = run(case, result)
    check_nominal(group(report, "support_agreement")["metrics"], values, SUPPORT)
    gap = group(report, "favorable_support_indicator_difference")
    assert gap["metrics"]["mean"] is None and gap["metrics"]["reason"]
    assert gap["counts"]["expected_targets"] == 8 and gap["counts"]["paired_targets"] == 0


def test_continuous_fitness_and_four_failure_categories_have_separate_denominators(fixture, tmp_path):
    case = make_case(fixture, tmp_path, count=4, axes=("fitness",), pointers=("/count",))
    scores = [(0.63, 0.62), (1, 1.0), (-0.0, 0), (0.1, 0.10000000000000002)]
    failures = [("none", "none"), ("form", "target"), ("target", "substance"), ("substance", "substance")]
    def values(p, r):
        i = int(p["record_id"].split("-")[-1]); j = ROLES.index(r)
        return {"fitness": scores[i][j], "failure": failures[i][j]}
    report, *_ = run(case, make_results(case, values=values))
    continuous = group(report, "fitness_agreement")["metrics"]
    assert continuous["n"] == 4 and continuous["agreeing"] == 2
    assert continuous["observed_agreement"] == .5
    assert continuous["categories"] is None and continuous["kappa"] is None and continuous["kappa_reason"]
    check_nominal(group(report, "fitness_failure_agreement")["metrics"], failures, FAILURES)
    gap = group(report, "continuous_fitness_difference")["metrics"]
    expected = sum(Fraction(a) - Fraction(b) for a, b in scores) / 4
    assert gap["mean"] == float(expected) and gap["n"] == 4
    zero = next(p for p in report["pairs"] if p["record_id"] == "record-2")
    assert type(zero["operands"]["same_family"]["fitness"]) is float
    assert math.copysign(1, zero["operands"]["same_family"]["fitness"]) == -1


@pytest.mark.parametrize("boundary", ["ge", "gt"])
def test_explicit_threshold_uses_accepted_value_and_declared_boundary(fixture, tmp_path, boundary):
    case = make_case(fixture, tmp_path, axes=("fitness",), pointers=("/count",))
    result = make_results(case, values=lambda p, r: {"fitness": .63 if r == "same_family" else .62})
    report, *_ = run(case, result, policy(case, threshold={"cutoff": .63, "boundary": boundary}))
    mapped = (THRESHOLD[1] if boundary == "ge" else THRESHOLD[0], THRESHOLD[0])
    check_nominal(group(report, "threshold_agreement")["metrics"], [mapped], THRESHOLD)
    assert group(report, "fitness_threshold_indicator_difference")["metrics"]["mean"] == (1.0 if boundary == "ge" else 0.0)
    assert group(report, "continuous_fitness_difference")["metrics"]["mean"] == float(Fraction(.63) - Fraction(.62))
    assert report["pairs"][0]["selection_stratum"] == {"status": "pending", "label": None, "reference": None}


@pytest.mark.parametrize("favorable", [[], list(SUPPORT), ["supported"]], ids=["empty", "all", "explicit-subset"])
def test_named_support_indicator_is_explicit_and_does_not_relabel_selection(fixture, tmp_path, favorable):
    case = make_case(fixture, tmp_path, axes=("grounding_v3",), pointers=("/count",))
    result = make_results(case, values=lambda p, r: {"verdict": "supported" if r == "same_family" else "unsupported"})
    report, *_ = run(case, result, policy(case, favorable=favorable))
    expected = int("supported" in favorable) - int("unsupported" in favorable)
    assert group(report, "favorable_support_indicator_difference")["metrics"]["mean"] == expected
    assert report["pairs"][0]["selection_stratum"]["status"] == "pending"
    assert group(report, "support_agreement")["metrics"]["observed_agreement"] == 0.0


@pytest.mark.parametrize("case_name", ["unknown_family", "missing_rater", "missing_route", "swapped_roles"])
def test_undirected_agreement_survives_unavailable_family_direction(fixture, tmp_path, case_name):
    def change(d):
        for p in d["pairs"]:
            if case_name == "swapped_roles":
                p["slots"]["same_family"], p["slots"]["cross_family"] = p["slots"]["cross_family"], p["slots"]["same_family"]
            elif case_name in ("missing_rater", "missing_route"):
                p["slots"]["same_family"]["rater"][case_name[8:]] = None
    models = ("unrecognized-fixture-model", "gpt-5") if case_name == "unknown_family" else ("claude-opus-5", "gpt-5")
    case = make_case(fixture, tmp_path, count=2, axes=("fitness",), pointers=("/count",),
                     models=models, change_declaration=change)
    if case_name == "swapped_roles":
        # Reply models follow genuine descriptor bindings, not the caller's role words.
        case.models = {"same_family": "gpt-5", "cross_family": "claude-opus-5"}
    result = make_results(case, values=lambda p, r: {"fitness": .8 if r == "same_family" else .2})
    report, *_ = run(case, result)
    agreement = group(report, "fitness_agreement")
    assert agreement["metrics"]["n"] == 2 and agreement["metrics"]["observed_agreement"] == 0.0
    assert agreement["attribution_counts"]["unattributed"] == 2
    assert all(p["accepted_pair"] and not p["attributed_role_pair"] for p in report["pairs"])
    gap = group(report, "continuous_fitness_difference")
    assert gap["metrics"]["n"] == 0 and gap["metrics"]["mean"] is None
    assert gap["counts"]["expected_targets"] == 2 and gap["counts"]["paired_targets"] == 0
    assert all(p["attribution_reasons"] for p in report["pairs"])


def test_pure_operand_sign_and_integrated_order_invariance_are_different_controls(fixture, tmp_path):
    assert analysis.signed_difference(.8, .2) == -analysis.signed_difference(.2, .8)
    case = make_case(fixture, tmp_path, count=2, axes=("fitness",), pointers=("/count", "/enabled"))
    result = make_results(case, values=lambda p, r: {"fitness": .8 if r == "same_family" else .2})
    first, *_ = run(case, result)
    changed = deepcopy(result.submissions); changed["slots"].reverse()
    path = tmp_path / "reordered-results"
    reordered = panel.accept_panel_results(case.panel_path, write(tmp_path / "reordered-submissions.json", changed), path, root=tmp_path)
    assert reordered["pairs"] == result.report["pairs"]
    declared = policy(case); declared["pair_ids"].reverse(); declared["uncertainty"]["blocks"].reverse()
    result.path = path
    second, *_ = run(case, result, declared, name="reordered-analysis")
    for key in ("pairs", "agreement_groups", "gap_groups"):
        assert second[key] == first[key]
    assert group(first, "continuous_fitness_difference")["metrics"]["mean"] > 0


def test_record_gap_averages_only_shared_paired_targets_then_equal_records(fixture, tmp_path):
    case = make_case(fixture, tmp_path, count=2, axes=("fitness",), pointers=("/count", "/enabled"))
    omitted_pair = next(p for p in case.panel["pairs"] if p["record_id"] == "record-0" and p["pointer"] == "/enabled")
    def values(p, r):
        if p["record_id"] == "record-0":
            return {"fitness": (1 if r == "same_family" else 0) if p["pointer"] == "/count" else 0}
        return {"fitness": .2 if r == "same_family" else .4}
    result = make_results(case, values=values, omitted={(omitted_pair["pair_id"], "cross_family")})
    report, *_ = run(case, result)
    g = group(report, "continuous_fitness_difference")
    expected = (Fraction(1) + Fraction(.2) - Fraction(.4)) / 2
    assert g["metrics"]["mean"] == float(expected)
    assert g["metrics"]["n"] == 2 and g["counts"]["paired_targets"] == 3
    first = next(r for r in g["record_rows"] if r["record_id"] == "record-0")
    assert first["same_mean"] == 1.0 and first["cross_mean"] == 0.0 and first["difference"] == 1.0
    assert first["counts"]["expected_targets"] == 2 and first["counts"]["paired_targets"] == 1
    assert first["excluded_pair_ids"] == [omitted_pair["pair_id"]]
    assert group(report, "fitness_agreement")["metrics"]["n"] == 3


def test_per_target_selection_labels_do_not_split_record_uncertainty_blocks(fixture, tmp_path):
    reference = write(tmp_path / "invented-selection.json", {"status": "synthetic control only"})
    def change(d):
        for i, p in enumerate(d["pairs"]):
            p["selection_stratum"] = {"status": "declared", "label": "fit" if i % 2 else "unfit",
                "reference": {"path": reference.name, "sha256": sha256(reference.read_bytes())}}
    case = make_case(fixture, tmp_path, count=2, axes=("fitness",), change_declaration=change)
    report, *_ = run(case, make_results(case))
    g = group(report, "continuous_fitness_difference")
    assert len(g["record_rows"]) == 2 and all(len(r["paired_pair_ids"]) == 2 for r in g["record_rows"])
    assert {p["selection_stratum"]["label"] for p in report["pairs"]} == {"fit", "unfit"}
    assert len(g["uncertainty"]["strata"]) == 1
    assert g["uncertainty"]["strata"][0]["record_count"] == 2


@pytest.mark.parametrize("mode", ["empty_selection", "all_missing", "one_missing", "pending_weight"])
def test_empty_and_incomplete_analysis_retains_full_roster_and_no_imputed_zero(fixture, tmp_path, mode):
    case = make_case(fixture, tmp_path, count=2, axes=("fitness",), pointers=("/count",))
    omitted = {(p["pair_id"], r) for p in case.panel["pairs"] for r in ROLES} if mode == "all_missing" else set()
    if mode == "one_missing":
        omitted.add((case.panel["pairs"][0]["pair_id"], "cross_family"))
    result = make_results(case, omitted=omitted)
    declared = policy(case, selected=[] if mode == "empty_selection" else None)
    if mode == "pending_weight":
        declared["agreement"]["weighting"] = None; declared["gap"]["weighting"] = None
    report, *_ = run(case, result, declared)
    assert len(report["pairs"]) == 2 and len(report["slots"]) == 4
    if mode == "empty_selection":
        assert not report["agreement_groups"] and not report["gap_groups"]
        assert not any(p["selected"] for p in report["pairs"])
    else:
        n = 1 if mode == "one_missing" else 0
        g = group(report, "continuous_fitness_difference")
        assert g["metrics"]["n"] == n
        assert g["counts"]["expected_targets"] == 2
        if not n:
            assert g["metrics"]["mean"] is None and g["metrics"]["reason"]
        assert len(g["record_rows"]) == 2
        assert all(i["lower"] is None for i in g["uncertainty"]["intervals"].values())


@pytest.mark.parametrize("cutoff", [True, -0.01, 1.01, "0.5"], ids=["boolean", "below", "above", "string"])
def test_threshold_refuses_undeclared_numeric_interpretation(fixture, tmp_path, cutoff):
    case = make_case(fixture, tmp_path, axes=("fitness",), pointers=("/count",))
    declared = policy(case, threshold={"cutoff": cutoff, "boundary": "ge"})
    with pytest.raises(ValueError):
        analysis.prepare_analysis_spec(case.panel_path, write(tmp_path / "bad.json", declared), tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


def test_whole_block_fixed_stratum_bootstrap_matches_independent_fraction_oracle(fixture, tmp_path):
    case = make_case(fixture, tmp_path, count=6, axes=("grounding_v3",), pointers=("/count", "/enabled"))
    # Unequal record cluster sizes (3 vs 1), and unequal accepted target counts.
    ids = [f"record-{i}" for i in range(6)]
    blocks = [{"block_id": "large-A", "record_ids": ids[:3]}, {"block_id": "small-A", "record_ids": ids[3:4]},
              {"block_id": "one-B", "record_ids": ids[4:5]}, {"block_id": "two-B", "record_ids": ids[5:]}]
    strata = [{"stratum_id": "A", "record_ids": ids[:4]}, {"stratum_id": "B", "record_ids": ids[4:]}]
    table = {"record-0": [("supported", "supported"), ("supported", "unsupported")],
             "record-1": [("unsupported", "supported"), ("unsupported", "unsupported")],
             "record-2": [("supported", "supported"), ("unsupported", "supported")],
             "record-3": [("supported", "unsupported"), ("supported", "supported")],
             "record-4": [("unsupported", "unsupported"), ("supported", "unsupported")],
             "record-5": [("supported", "supported"), ("unsupported", "unsupported")]}
    missing = next(p for p in case.panel["pairs"] if p["record_id"] == "record-0" and p["pointer"] == "/enabled")
    def values(p, r):
        return {"verdict": table[p["record_id"]][p["pointer"] == "/enabled"][ROLES.index(r)]}
    result = make_results(case, values=values, omitted={(missing["pair_id"], "cross_family")})
    declared = policy(case, favorable=["supported"], strata=strata, blocks=blocks, resamples=32)
    report, *_ = run(case, result, declared)
    accepted = {rid: rows[:] for rid, rows in table.items()}; accepted["record-0"] = accepted["record-0"][:1]
    all_pairs = [pair for rows in accepted.values() for pair in rows]
    agreement = group(report, "support_agreement")
    check_nominal(agreement["metrics"], all_pairs, SUPPORT)
    schedule, consumed = independent_schedule(blocks, strata, seed=7, resamples=32)
    block_records = {b["block_id"]: b["record_ids"] for b in blocks}
    by_stratum = {s["stratum_id"]: s["record_ids"] for s in strata}
    original_n = {name: sum(len(accepted[r]) for r in rids) for name, rids in by_stratum.items()}
    gap_values = {rid: sum(Fraction(int(a == "supported") - int(b == "supported")) for a, b in rows) / len(rows)
                  for rid, rows in accepted.items()}
    for g, kind in ((agreement, "agreement"), (group(report, "favorable_support_indicator_difference"), "gap")):
        u = g["uncertainty"]
        assert [{k: draw[k] for k in ("index", "strata")} for draw in u["draws"]] == schedule
        assert u["rng_counters_consumed"] == consumed and u["draws_completed"] == 32
        assert u["schedule_sha256"] == sha256(b"".join(canonical(d) + b"\n" for d in schedule))
        assert any(len(set(s["blocks"])) < len(s["blocks"]) for d in schedule for s in d["strata"])
        expected_draws = {"exact_agreement": [], "kappa": []} if kind == "agreement" else {"mean": []}
        for observed, draw in zip(u["draws"], schedule):
            cells = [[Fraction(0) for _ in SUPPORT] for _ in SUPPORT]
            mean = Fraction(0)
            for stratum in draw["strata"]:
                name = stratum["stratum_id"]
                repeated = [rid for bid in stratum["blocks"] for rid in block_records[bid]]
                if kind == "agreement":
                    sampled = [p for rid in repeated for p in accepted[rid]]
                    weight = Fraction(original_n[name], len(all_pairs))
                    for i, a in enumerate(SUPPORT):
                        for j, b in enumerate(SUPPORT):
                            cells[i][j] += weight * Fraction(sum(x == a and y == b for x, y in sampled), len(sampled))
                else:
                    weight = Fraction(len(by_stratum[name]), len(ids))
                    mean += weight * sum(gap_values[rid] for rid in repeated) / len(repeated)
            if kind == "agreement":
                po = sum(cells[i][i] for i in range(7))
                pe = sum(sum(cells[i]) * sum(row[i] for row in cells) for i in range(7))
                expected = {"exact_agreement": po, "kappa": None if pe == 1 else (po - pe) / (1 - pe)}
            else:
                expected = {"mean": mean}
            for metric, value in expected.items():
                assert observed["metrics"][metric] == (None if value is None else float(value))
                expected_draws[metric].append(value)
        for row in u["strata"]:
            expected_weight = (Fraction(original_n[row["stratum_id"]], len(all_pairs)) if kind == "agreement"
                               else Fraction(len(by_stratum[row["stratum_id"]]), len(ids)))
            assert row["weight"] == float(expected_weight)
        for name, values in expected_draws.items():
            observed = g["metrics"]["observed_agreement" if name == "exact_agreement" else name]
            interval_oracle(u["intervals"][name], values, .9, observed)


def test_undefined_kappa_draws_are_counted_not_discarded(fixture, tmp_path):
    case = make_case(fixture, tmp_path, count=2, axes=("grounding_v3",), pointers=("/count",))
    result = make_results(case, values=lambda p, r: {"verdict": "supported" if p["record_id"] == "record-0" else "unsupported"})
    report, *_ = run(case, result, policy(case, resamples=32))
    g = group(report, "support_agreement")
    assert g["metrics"]["kappa"] == 1.0
    values = [draw["metrics"]["kappa"] for draw in g["uncertainty"]["draws"]]
    assert 0 < sum(v is None for v in values) < 32
    assert g["uncertainty"]["draws_completed"] == 32
    interval = g["uncertainty"]["intervals"]["kappa"]
    assert interval["undefined_draws"] == values.count(None)
    assert interval["lower"] is None and interval["upper"] is None and interval["reason"]
    assert g["uncertainty"]["intervals"]["exact_agreement"]["lower"] == 1.0


def test_constant_categories_with_nonbinary_weights_keep_exact_pe_one(fixture, tmp_path):
    case = make_case(fixture, tmp_path, count=6, axes=("grounding_v3",), pointers=("/count",))
    strata = [{"stratum_id": "two", "record_ids": ["record-0", "record-1"]},
              {"stratum_id": "four", "record_ids": [f"record-{i}" for i in range(2, 6)]}]
    report, *_ = run(case, make_results(case), policy(case, strata=strata, resamples=8))
    g = group(report, "support_agreement")
    assert g["metrics"]["expected_agreement"] == 1.0 and g["metrics"]["kappa"] is None
    assert all(d["metrics"]["kappa"] is None for d in g["uncertainty"]["draws"])
    assert g["uncertainty"]["intervals"]["kappa"]["undefined_draws"] == 8


@pytest.mark.parametrize("contributing", [0, 1], ids=["zero-stratum", "singleton-stratum"])
def test_every_declared_stratum_is_required_even_at_zero_weight(fixture, tmp_path, contributing):
    case = make_case(fixture, tmp_path, count=4, axes=("fitness",), pointers=("/count",))
    b = [p for p in case.panel["pairs"] if p["record_id"] in ("record-2", "record-3")]
    omitted = {(p["pair_id"], "cross_family") for p in b[contributing:]}
    result = make_results(case, omitted=omitted)
    strata = [{"stratum_id": "A", "record_ids": ["record-0", "record-1"]},
              {"stratum_id": "B", "record_ids": ["record-2", "record-3"]}]
    report, *_ = run(case, result, policy(case, strata=strata))
    for metric in ("fitness_agreement", "continuous_fitness_difference"):
        g = group(report, metric)
        assert g["metrics"]["n"] == 2 + contributing
        u = g["uncertainty"]
        assert u["draws"] == [] and u["draws_completed"] == 0 and u["unavailable_reasons"]
        last = next(s for s in u["strata"] if s["stratum_id"] == "B")
        assert len(last["contributing_record_ids"]) == contributing
        assert last["weight"] == float(Fraction(contributing, 2 + contributing))
        assert all(v["lower"] is None and v["upper"] is None and v["reason"] for v in u["intervals"].values())


def test_identical_input_replicates_remain_distinct_but_cannot_split_blocks(fixture, tmp_path):
    case = make_case(fixture, tmp_path, count=2, axes=("fitness",), pointers=("/count",), same_input=True)
    assert len(case.panel["records"]) == 2
    assert len({r["record"]["sha256"] for r in case.panel["records"]}) == 1
    invalid = policy(case)
    with pytest.raises(ValueError):
        analysis.prepare_analysis_spec(case.panel_path, write(tmp_path / "split.json", invalid), tmp_path / "split")
    blocks = [{"block_id": "shared", "record_ids": ["record-0", "record-1"]}]
    declared = policy(case, blocks=blocks)
    report, *_ = run(case, make_results(case), declared)
    g = group(report, "continuous_fitness_difference")
    assert g["metrics"]["n"] == 2 and len(g["record_rows"]) == 2
    assert g["uncertainty"]["draws"] == [] and g["uncertainty"]["unavailable_reasons"]


def test_cross_stratum_block_is_not_split_to_manufacture_interval(fixture, tmp_path):
    case = make_case(fixture, tmp_path, count=4, axes=("fitness",), pointers=("/count",))
    blocks = [{"block_id": "crossing", "record_ids": ["record-0", "record-2"]},
              {"block_id": "a", "record_ids": ["record-1"]}, {"block_id": "b", "record_ids": ["record-3"]}]
    strata = [{"stratum_id": "A", "record_ids": ["record-0", "record-1"]},
              {"stratum_id": "B", "record_ids": ["record-2", "record-3"]}]
    report, *_ = run(case, make_results(case), policy(case, blocks=blocks, strata=strata))
    g = group(report, "continuous_fitness_difference")
    assert g["metrics"]["n"] == 4 and g["metrics"]["mean"] == 0.0
    assert g["uncertainty"]["draws"] == [] and g["uncertainty"]["unavailable_reasons"]


def test_accepted_scores_not_rounded_display_values_determine_threshold(fixture, tmp_path):
    case = make_case(fixture, tmp_path, axes=("fitness",), pointers=("/count",))
    # Adjacent binary64 values would both display as 0.50; no tolerance or anchor mapping is permitted.
    low, high = .5, math.nextafter(.5, 1.0)
    result = make_results(case, values=lambda p, r: {"fitness": high if r == "same_family" else low})
    report, *_ = run(case, result, policy(case, threshold={"cutoff": high, "boundary": "ge"}))
    assert group(report, "fitness_agreement")["metrics"]["observed_agreement"] == 0.0
    assert group(report, "continuous_fitness_difference")["metrics"]["mean"] == float(Fraction(high) - Fraction(low))
    assert group(report, "fitness_threshold_indicator_difference")["metrics"]["mean"] == 1.0


def test_actual_work_bound_and_output_bound_refuse_before_publication(fixture, tmp_path, monkeypatch):
    case = make_case(fixture, tmp_path, count=2, axes=("fitness",), pointers=("/count",))
    result = make_results(case)
    spec_path = tmp_path / "spec"
    analysis.prepare_analysis_spec(case.panel_path, write(tmp_path / "policy.json", policy(case)), spec_path)
    before = snapshot(tmp_path)
    with monkeypatch.context() as m:
        m.setattr(analysis, "MAX_BOOTSTRAP_WORK", 1)
        with pytest.raises(ValueError, match="bound"):
            analysis.analyze_panel_results(spec_path, result.path, tmp_path / "too-much-work")
    assert before == snapshot(tmp_path)
    with monkeypatch.context() as m:
        m.setattr(analysis, "MAX_BYTES", 1)
        with pytest.raises(ValueError, match="bound"):
            analysis.analyze_panel_results(spec_path, result.path, tmp_path / "too-many-bytes")
    assert before == snapshot(tmp_path)


def test_analysis_tamper_no_overwrite_and_nul_refuse(fixture, tmp_path):
    case = make_case(fixture, tmp_path, axes=("fitness",), pointers=("/count",))
    result = make_results(case)
    report, path, spec, _ = run(case, result)
    before = snapshot(tmp_path)
    with pytest.raises((ValueError, OSError)):
        analysis.analyze_panel_results(spec, result.path, path)
    with pytest.raises(ValueError):
        analysis.analyze_panel_results(spec, result.path, tmp_path / "truncated\0suffix")
    assert before == snapshot(tmp_path) and not (tmp_path / "truncated").exists()
    forged = deepcopy(report); forged["gap_groups"][0]["metrics"]["mean"] = .999
    write(path / "analysis.json", forged)
    with pytest.raises(ValueError):
        analysis.recheck_panel_analysis(path)


def test_analysis_mid_artifact_failure_preserves_complete_inputs_and_absent_output(fixture, tmp_path, monkeypatch):
    case = make_case(fixture, tmp_path, axes=("fitness",), pointers=("/count",))
    result = make_results(case)
    spec = tmp_path / "specification"
    analysis.prepare_analysis_spec(case.panel_path, write(tmp_path / "policy.json", policy(case)), spec)
    before = snapshot(tmp_path)
    original, calls = kernel._write_bytes, []
    def fail(path, raw):
        calls.append(path)
        if len(calls) == 2:
            raise OSError("invented analysis artifact failure")
        return original(path, raw)
    monkeypatch.setattr(kernel, "_write_bytes", fail)
    with pytest.raises(OSError, match="analysis artifact"):
        analysis.analyze_panel_results(spec, result.path, tmp_path / "analysis")
    assert len(calls) == 2 and not (tmp_path / "analysis").exists()
    assert before == snapshot(tmp_path)


def test_actual_score_exchange_negates_gap_with_family_bindings_fixed(fixture, tmp_path):
    case = make_case(fixture, tmp_path, count=2, axes=("fitness",), pointers=("/count", "/enabled"))
    values = {("record-0", "/count"): (.8, .2), ("record-0", "/enabled"): (.6, .4),
              ("record-1", "/count"): (.3, .7), ("record-1", "/enabled"): (.9, .1)}
    first_results = make_results(case, values=lambda p, r: {
        "fitness": values[p["record_id"], p["pointer"]][ROLES.index(r)]}, name="original-scores")
    exchanged_results = make_results(case, values=lambda p, r: {
        "fitness": values[p["record_id"], p["pointer"]][1 - ROLES.index(r)]}, name="exchanged-scores")
    first, *_ = run(case, first_results, name="original-score-analysis")
    exchanged, *_ = run(case, exchanged_results, name="exchanged-score-analysis")
    old_gap = group(first, "continuous_fitness_difference")
    new_gap = group(exchanged, "continuous_fitness_difference")
    assert old_gap["identity"] == new_gap["identity"]
    assert old_gap["metrics"]["mean"] > 0
    assert new_gap["metrics"]["mean"] == -old_gap["metrics"]["mean"]
    assert group(first, "fitness_agreement")["metrics"] == group(exchanged, "fitness_agreement")["metrics"]
    for old, new in zip(first["pairs"], exchanged["pairs"]):
        assert old["attributed_role_pair"] is True and new["attributed_role_pair"] is True
        assert old["common_subject_sha256"] == new["common_subject_sha256"]
        for role in ROLES:
            assert old["slots"][role]["binding"] == new["slots"][role]["binding"]
            assert old["slots"][role]["rater"] == new["slots"][role]["rater"]
