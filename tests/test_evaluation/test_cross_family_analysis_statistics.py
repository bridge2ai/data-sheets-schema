"""Hand examples and an independent rational oracle for paired resampling.

The oracle consumes emitted block choices, not production RNG or estimators.
It expands whole blocks literally and never discards undefined replicates.
"""
from collections import Counter
from fractions import Fraction
from types import SimpleNamespace

import pytest

from data_sheets_schema import cross_family_panel_analysis as analysis
from tests.test_evaluation.test_cross_family_panel_analysis import (
    _score, make_case, no_network, pair, policy, run_analysis,
)
from tests.test_evaluation.test_semantic_evidence import _groups


@pytest.mark.parametrize("pairs,categories,confusion,po,pe,kappa", [
    ([(0, 0), (0, 1), (1, 1), (1, 1)], [0, 1], [[1, 1], [0, 2]], Fraction(3, 4), Fraction(1, 2), Fraction(1, 2)),
    ([(0, 0), (0, 3), (3, 5), (5, 5)], [0, 3, 5], [[1, 1, 0], [0, 0, 1], [0, 0, 1]], Fraction(1, 2), Fraction(5, 16), Fraction(3, 11)),
    ([(0, 1), (1, 0)], [0, 1], [[0, 1], [1, 0]], 0, Fraction(1, 2), -1),
])
def test_hand_calculated_unweighted_kappa(pairs, categories, confusion, po, pe, kappa):
    result = analysis.agreement_statistics(pairs, categories)
    assert result["n"] == len(pairs)
    assert result["categories"] == categories
    assert result["confusion_matrix"] == confusion
    assert result["agreeing"] == sum(a == b for a, b in pairs)
    assert result["observed_agreement"] == pytest.approx(float(po))
    assert result["expected_agreement"] == pytest.approx(float(pe))
    assert result["kappa"] == pytest.approx(float(kappa))
    swapped = analysis.agreement_statistics([(b, a) for a, b in pairs], categories)
    assert swapped["confusion_matrix"] == [list(column) for column in zip(*confusion)]
    for key in ("n", "agreeing", "observed_agreement", "expected_agreement", "kappa"):
        assert swapped[key] == result[key]


@pytest.mark.parametrize("pairs", [[], [(1, 1)], [(0, 0)] * 4])
def test_empty_or_certain_marginals_have_explicit_undefined_kappa(pairs):
    result = analysis.agreement_statistics(pairs, [0, 1])
    assert result["n"] == len(pairs)
    assert result["kappa"] is None and result["kappa_reason"]
    if pairs:
        assert result["observed_agreement"] == result["expected_agreement"] == 1
        assert result["agreement_reason"] is None
    else:
        assert result["observed_agreement"] is result["expected_agreement"] is None
        assert result["agreement_reason"]
        assert result["confusion_matrix"] == [[0, 0], [0, 0]]


def test_near_but_not_degenerate_marginals_are_not_tolerance_collapsed():
    result = analysis.agreement_statistics([(1, 1)] * 999 + [(0, 0)], [0, 1])
    assert result["expected_agreement"] == pytest.approx(Fraction(998002, 1000000))
    assert result["expected_agreement"] < 1 and result["kappa"] == 1
    assert result["kappa_reason"] is None


def test_portable_rng_matches_independently_derived_literal_vector():
    # Root computed this vector using only stdlib SHA256, independently of the
    # project module (cross-family-analysis4962-independent-rng-vector01).
    stream = analysis._IndexStream(7)
    assert [stream.index(3) for _ in range(12)] == [1, 2, 1, 2, 0, 2, 2, 0, 2, 0, 0, 2]


def test_rng_rejects_biased_tail_and_advances_counter_for_rejected_candidate(monkeypatch):
    seen = []
    candidates = iter([(2 ** 256 - 1).to_bytes(32, "big"), (4).to_bytes(32, "big"), (5).to_bytes(32, "big")])
    def digest(raw):
        seen.append(raw)
        value = next(candidates)
        return SimpleNamespace(digest=lambda: value)
    monkeypatch.setattr(analysis.hashlib, "sha256", digest)
    stream = analysis._IndexStream(7)
    assert stream.index(3) == 1
    assert stream.index(3) == 2
    prefix = bytes.fromhex("63726f73732d66616d696c792d616e616c797369732d696e6465782d7631000000000000000007")
    assert seen == [prefix + counter.to_bytes(8, "big") for counter in range(3)]


def rational_metrics(weighted_pairs, categories):
    """Combine already-weighted cell probabilities using exact fractions."""
    cells = Counter()
    for weight, pairs in weighted_pairs:
        assert pairs
        for a, b in pairs:
            cells[a, b] += weight / len(pairs)
    assert sum(cells.values()) == 1
    po = sum(cells[c, c] for c in categories)
    pe = sum(sum(cells[c, d] for d in categories) * sum(cells[d, c] for d in categories)
             for c in categories)
    return {"exact_agreement": po, "kappa": None if pe == 1 else (po - pe) / (1 - pe)}


def linear_percentile(values, probability):
    """Explicit linear interpolation of exact independent oracle values."""
    values = sorted(values)
    position = (len(values) - 1) * probability
    left = position.numerator // position.denominator
    remainder = position - left
    return values[left] if remainder == 0 else values[left] * (1 - remainder) + values[left + 1] * remainder


def assert_intervals(uncertainty, expected):
    confidence = Fraction(str(uncertainty["confidence"]))
    for metric in expected[0]:
        values = [row[metric] for row in expected]
        missing = sum(value is None for value in values)
        interval = uncertainty["intervals"][metric]
        assert interval["undefined_draws"] == missing
        if missing:
            assert interval["lower"] is interval["upper"] is None and interval["reason"]
        else:
            assert interval["lower"] == pytest.approx(float(linear_percentile(values, (1 - confidence) / 2)))
            assert interval["upper"] == pytest.approx(float(linear_percentile(values, (1 + confidence) / 2)))


def _draw_records(draw, block_members):
    return {row["stratum_id"]: [record for block in row["blocks"] for record in block_members[block]]
            for row in draw["strata"]}


def _assert_replicate(actual, expected):
    assert set(actual) == set(expected)
    for key, value in expected.items():
        if value is None:
            assert actual[key] is None
        else:
            assert actual[key] == pytest.approx(float(value))


def test_fixed_original_stratum_weights_and_whole_block_multiplicity(tmp_path):
    # Stratum A: one three-record block and one singleton. B: two singletons.
    # Repeating the large block must not change the original A:B allocation 4:2.
    scores = [(0, 1), (1, 0), (0, 1), (1, 1), (1, 0), (1, 1)]
    def change(value, slot):
        if slot["rubric"] == "rubric10":
            index = int(slot["record_id"].split("-")[1])
            _score(value, "E1.1", scores[index][slot["role"] == "cross_family"])
    case = make_case(tmp_path, count=6, change_rating=change)
    block_members = {"large": ["record-0", "record-1", "record-2"], "small": ["record-3"],
                     "b-first": ["record-4"], "b-second": ["record-5"]}
    stratum_members = {"A": ["record-0", "record-1", "record-2", "record-3"],
                       "B": ["record-4", "record-5"]}
    declaration = policy(case,
        blocks=[{"block_id": key, "record_ids": value} for key, value in block_members.items()],
        strata=[{"stratum_id": key, "record_ids": value} for key, value in stratum_members.items()])
    declaration["uncertainty"]["resamples"] = 32
    _, report, receipt, _, _ = run_analysis(case, declaration)
    assert receipt["counts"]["accepted"] == 24, receipt["rows"]
    agreement = next(row for row in report["agreement_groups"] if row["identity"]["rubric"] == "rubric10")
    gap = next(row for row in report["gap_groups"] if row["identity"]["rubric"] == "rubric10")
    values = {name: [row for row in report["observations"] if row["record_id"] == name
                    and row["rubric"] == "rubric10" and row["applicable"]]
              for names in stratum_members.values() for name in names}
    original_counts = {key: sum(len(values[name]) for name in names) for key, names in stratum_members.items()}
    original_weights = {key: Fraction(value, sum(original_counts.values())) for key, value in original_counts.items()}
    assert original_weights == {"A": Fraction(2, 3), "B": Fraction(1, 3)}
    for group in (agreement, gap):
        declared = {row["stratum_id"]: row for row in group["uncertainty"]["strata"]}
        assert {key: row["weight"] for key, row in declared.items()} == pytest.approx({"A": 2 / 3, "B": 1 / 3})
        assert {key: row["record_count"] for key, row in declared.items()} == {"A": 4, "B": 2}
        assert len(group["uncertainty"]["draws"]) == 32
    expected_gaps = {"record-" + str(i): Fraction(a - b) for i, (a, b) in enumerate(scores)}
    assert {name: pair(report, name)["gap"] for name in expected_gaps} == expected_gaps
    assert gap["metrics"]["mean"] == pytest.approx(float(sum(expected_gaps.values()) / 6))
    all_agreement, all_gap, multiplicities, changed_allocation = [], [], False, False
    for draw in agreement["uncertainty"]["draws"]:
        selected = _draw_records(draw, block_members)
        multiplicities |= any(len(names) != len(set(names)) for names in selected.values())
        changed_allocation |= Fraction(len(selected["A"]), len(selected["A"]) + len(selected["B"])) != Fraction(2, 3)
        expected = rational_metrics([(original_weights[key], [(row["same_score"], row["cross_score"])
                                    for name in names for row in values[name]])
                                    for key, names in selected.items()], [0, 1])
        _assert_replicate(draw["metrics"], expected)
        all_agreement.append(expected)
    for draw in gap["uncertainty"]["draws"]:
        selected = _draw_records(draw, block_members)
        expected = {"mean": sum(Fraction(len(stratum_members[key]), 6) *
                                sum(expected_gaps[name] for name in names) / len(names)
                                for key, names in selected.items())}
        _assert_replicate(draw["metrics"], expected)
        all_gap.append(expected)
    assert multiplicities and changed_allocation, "fixture must distinguish resampling from deduplication and drifting weights"
    assert_intervals(agreement["uncertainty"], all_agreement)
    assert_intervals(gap["uncertainty"], all_gap)


def test_undefined_bootstrap_draws_are_counted_not_discarded_or_redrawn(tmp_path):
    def change(value, slot):
        if slot["rubric"] == "rubric10" and slot["record_id"] == "record-1":
            for _, items in _groups(value):
                for item in items:
                    if item["applicable"]:
                        _score(value, item["item_id"], 0)
    case = make_case(tmp_path, count=2, change_rating=change)
    declaration = policy(case)
    declaration["uncertainty"]["resamples"] = 32
    _, report, receipt, _, _ = run_analysis(case, declaration)
    assert receipt["counts"]["accepted"] == 8
    group = next(row for row in report["agreement_groups"] if row["identity"]["rubric"] == "rubric10")
    assert group["metrics"]["kappa"] == 1
    uncertainty = group["uncertainty"]
    assert len(uncertainty["draws"]) == 32
    expected = []
    for draw in uncertainty["draws"]:
        blocks = draw["strata"][0]["blocks"]
        assert len(blocks) == 2
        scores = [(1, 1) if block == "b0" else (0, 0) for block in blocks]
        expected.append(rational_metrics([(Fraction(1), scores)], [0, 1]))
        _assert_replicate(draw["metrics"], expected[-1])
    missing = sum(row["kappa"] is None for row in expected)
    assert 0 < missing < 32
    assert_intervals(uncertainty, expected)
    assert uncertainty["intervals"]["exact_agreement"]["lower"] == uncertainty["intervals"]["exact_agreement"]["upper"] == 1


def test_constant_category_across_fractional_stratum_weights_is_exactly_degenerate(tmp_path):
    case = make_case(tmp_path, count=7)
    strata = [{"stratum_id": "two", "record_ids": ["record-0", "record-1"]},
              {"stratum_id": "five", "record_ids": ["record-" + str(i) for i in range(2, 7)]}]
    _, report, receipt, _, _ = run_analysis(case, policy(case, strata=strata))
    assert receipt["counts"]["accepted"] == 28
    group = next(row for row in report["agreement_groups"] if row["identity"]["rubric"] == "rubric10")
    assert group["metrics"]["expected_agreement"] == 1 and group["metrics"]["kappa"] is None
    uncertainty = group["uncertainty"]
    assert {row["stratum_id"]: row["weight"] for row in uncertainty["strata"]} == pytest.approx({"two": 2 / 7, "five": 5 / 7})
    assert uncertainty["intervals"]["kappa"]["lower"] is None
    assert all(row["metrics"]["kappa"] is None for row in uncertainty["draws"])


def test_single_contributing_block_keeps_point_metric_but_no_interval(tmp_path):
    case = make_case(tmp_path)
    _, report, _, _, _ = run_analysis(case)
    for group in report["agreement_groups"] + report["gap_groups"]:
        assert group["metrics"]["n"] > 0
        assert group["uncertainty"]["unavailable_reasons"]
        for interval in group["uncertainty"]["intervals"].values():
            assert interval["lower"] is interval["upper"] is None and interval["reason"]


def test_pending_gap_policy_does_not_erase_declared_agreement_point_metrics(tmp_path):
    case = make_case(tmp_path)
    declaration = policy(case)
    declaration["gap"]["scale"] = None
    declaration["uncertainty"]["seed"] = None
    _, report, _, _, _ = run_analysis(case, declaration)
    assert report["pending_parameters"]
    assert report["agreement_groups"]
    assert all(row["metrics"]["n"] > 0 and row["metrics"]["observed_agreement"] == 1
               for row in report["agreement_groups"])
    assert all(row["gap"] is None for row in report["pairs"])
    assert report["execution_authorized"] is report["scientific_eligibility"] is False


def test_group_filtering_retains_declared_zero_and_singleton_strata(tmp_path):
    def distinct_rater(value):
        for slot in value["slots"]:
            if slot["record_id"] == "record-2":
                slot["rater"] += "-other"
    case = make_case(tmp_path, count=3, change_declaration=distinct_rater)
    declaration = policy(case, strata=[
        {"stratum_id": "first", "record_ids": ["record-0", "record-1"]},
        {"stratum_id": "second", "record_ids": ["record-2"]}])
    _, report, receipt, _, _ = run_analysis(case, declaration)
    assert receipt["counts"]["accepted"] == 12
    groups = [row for row in report["gap_groups"] if row["identity"]["rubric"] == "rubric10"]
    assert len(groups) == 2
    for group in groups:
        uncertainty = group["uncertainty"]
        strata = {row["stratum_id"]: row for row in uncertainty["strata"]}
        assert set(strata) == {"first", "second"}
        assert strata["first"]["record_ids"] == ["record-0", "record-1"]
        assert strata["second"]["record_ids"] == ["record-2"]
        assert sorted(row["record_count"] for row in strata.values()) in ([0, 1], [0, 2])
        assert uncertainty["unavailable_reasons"]
        assert uncertainty["intervals"]["mean"]["lower"] is None
