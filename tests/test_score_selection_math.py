"""Fixture-only controls for registered score_gap_v1 arithmetic, issue 6385."""

from copy import deepcopy
import math

import pytest

from data_sheets_schema._score_selection_math import decide, pooled_variation, summarize


def row(label, first, second=None, *, slots=10, project="Example", valid=True):
    second = first if second is None else second
    value = {"label": label, "project": project, "validity": "valid" if valid else "invalid",
             "slots": slots, "instrument_id": "instrument-x", "eligibility_problems": [], "rubrics": {}}
    for rubric, scores in (("rubric10", first), ("rubric20", second)):
        value["rubrics"][rubric] = {"scorings": [
            {"scoring_number": number, "status": "measured", "points": score,
             "maximum": 100, "percentage": score, "attempt": 1,
             "measurement_identity": {"definition": rubric, "record": label}}
            for number, score in enumerate(scores, 1)]}
    return value


def noise(s=1):
    return {"s": s, "degrees_of_freedom": 10, "instrument_id": "instrument-x"}


def test_strict_gap_just_below_above_and_exact_threshold():
    threshold = 2 * math.sqrt(2 / 3)
    incumbent = row("a", [0, 0, 0], slots=20)
    for gap, expected in ((threshold - 1e-8, "a"), (threshold, "a"), (threshold + 1e-8, "b")):
        result = decide([incumbent, row("b", [gap] * 3)], noise(), "instrument-x")
        assert result["selected"] == expected
        assert result["score_policy"]["T"] == threshold
        assert result["score_policy"]["rule"] == ("score_gap" if expected == "b" else "policy_fallback")


def test_one_rubric_reversing_cannot_be_carried_by_the_other():
    rows = [row("a", [50] * 3, slots=20), row("b", [90] * 3, [49] * 3)]
    result = decide(rows, noise(), "instrument-x")
    assert result["selected"] == "a"
    assert result["score_policy"]["gap"] == 19.5
    assert "rubric20" in result["score_policy"]["fallback_reason"]


def test_missing_scoring_causes_fallback_not_zero_or_silent_drop():
    high = row("b", [100, 100, 100])
    high["rubrics"]["rubric10"]["scorings"].pop()
    result = decide([row("a", [50] * 3, slots=20), high], noise(), "instrument-x")
    assert result["selected"] == "a"
    assert "fewer than three" in result["score_policy"]["fallback_reason"]
    assert result["score_policy"]["candidates"][1]["rubrics"]["rubric10"]["mean"] == 100


def test_not_measured_cell_and_missing_column_remain_none():
    high = row("b", [100] * 3)
    for cell in high["rubrics"]["rubric10"]["scorings"]:
        cell.update(status="not measured", points=None, maximum=None, percentage=None)
    result = decide([row("a", [50] * 3, slots=20), high], noise(), "instrument-x")
    assert result["selected"] == "a"
    summary = result["score_policy"]["candidates"][1]
    assert summary["rubrics"]["rubric10"] == {"mean": None, "spread": None, "count": 0}
    assert summary["paired"]["mean"] is None
    assert "not measured" in result["score_policy"]["fallback_reason"]


def test_invalid_top_score_never_wins_or_blocks_valid_candidates():
    invalid = row("invalid", [100] * 3, slots=100, valid=False)
    invalid["instrument_id"] = "wrong"
    invalid["eligibility_problems"] = ["unmeasured"]
    result = decide([row("a", [50] * 3, slots=20), row("b", [70] * 3), invalid], noise(), "instrument-x")
    assert result["selected"] == "b"


def test_tied_score_does_not_replace_current_policy_and_label_is_deterministic():
    rows = [row("b", [50] * 3), row("a", [50] * 3)]
    before = deepcopy(rows)
    first = decide(rows, noise(0), "instrument-x")
    assert first["selected"] == "a"
    assert first == decide(list(reversed(rows)), noise(0), "instrument-x")
    assert rows == before


def test_duplicate_attempt_is_not_a_second_measurement():
    high = row("b", [70] * 3)
    cell = high["rubrics"]["rubric10"]["scorings"][2]
    cell.update(attempt=2, receipt="attempt2/receipt.json", receipt_sha256="2" * 64,
                refused_attempt={"path": "attempt1/receipt.json", "sha256": "1" * 64,
                                 "reason": "synthetic output refused"})
    selected = decide([row("a", [50] * 3, slots=20), high], noise(), "instrument-x")
    assert selected["selected"] == "b"
    assert selected["score_policy"]["replaced_cells"] == [{
        "label": "b", "project": "Example", "rubric": "rubric10", "scoring_number": 3,
        "attempt": 2, "receipt": "attempt2/receipt.json", "receipt_sha256": "2" * 64,
        "refused_attempt": {"path": "attempt1/receipt.json", "sha256": "1" * 64,
                            "reason": "synthetic output refused"}}]
    high["rubrics"]["rubric10"]["scorings"].append(deepcopy(high["rubrics"]["rubric10"]["scorings"][2]))
    result = decide([row("a", [50] * 3, slots=20), high], noise(), "instrument-x")
    assert result["selected"] == "a"
    assert "duplicate scoring" in result["score_policy"]["fallback_reason"]


def test_changed_measured_input_or_instrument_falls_back():
    rows = [row("a", [50] * 3, slots=20), row("b", [70] * 3)]
    rows[1]["rubrics"]["rubric10"]["scorings"][1]["measurement_identity"]["record"] = "changed"
    assert "measured inputs differ" in decide(rows, noise(), "instrument-x")["score_policy"]["fallback_reason"]
    rows[1] = row("b", [70] * 3)
    rows[1]["instrument_id"] = "another-instrument"
    result = decide(rows, noise(), "instrument-x")
    assert result["selected"] == "a"
    assert "instrument differs" in result["score_policy"]["fallback_reason"]
    with pytest.raises(ValueError, match="one named instrument"):
        pooled_variation(rows)


def test_unknown_or_wrong_instrument_noise_is_not_zero():
    rows = [row("a", [50] * 3, slots=20), row("b", [70] * 3)]
    for pooled in ({"s": None, "degrees_of_freedom": 0, "instrument_id": "instrument-x"},
                   {"s": 0, "degrees_of_freedom": 2, "instrument_id": "other"}):
        result = decide(rows, pooled, "instrument-x")
        assert result["selected"] == "a"
        assert result["score_policy"]["rule"] == "policy_fallback"
    empty = pooled_variation([])
    assert empty["s"] is None and empty["degrees_of_freedom"] == 0


def test_pooled_within_record_degrees_of_freedom_and_equal_rubric_weights():
    # Combined sequences [20,22,24] and [11,17]: SS 8 + 18, df 2 + 1.
    rows = [row("a", [10, 12, 14], [30, 32, 34]),
            row("b", [10, 16], [12, 18], project="Other", valid=False),
            row("c", [99], project="Other")]
    actual = pooled_variation(rows)
    assert actual["degrees_of_freedom"] == 3
    assert actual["records"] == 2
    assert actual["s"] == pytest.approx(math.sqrt(26 / 3))
    assert actual["per_project"]["Example"]["s"] == 2
    assert actual["per_project"]["Other"]["s"] == pytest.approx(math.sqrt(18))
    assert actual["per_rubric"]["rubric10"]["s"] == pytest.approx(math.sqrt(26 / 3))


def test_pairing_uses_scoring_numbers_and_more_than_three_is_allowed():
    candidate = row("b", [70, 80, 90, 100], [90, 80, 70, 60])
    candidate["rubrics"]["rubric20"]["scorings"].reverse()
    assert summarize(candidate)["paired"] == {"mean": 80.0, "spread": 0.0, "count": 4}
    assert decide([row("a", [50] * 3, slots=20), candidate], noise(), "instrument-x")["selected"] == "b"


def test_review_counts_do_not_rank_or_veto_and_zero_is_measured():
    rows = [row("a", [0] * 3, slots=20), row("b", [20] * 3)]
    rows[1]["content_review"] = {"adverse": 9999}
    result = decide(rows, noise(0), "instrument-x")
    assert result["selected"] == "b"
    assert result["score_policy"]["candidates"][0]["paired"]["mean"] == 0


def test_instrument_definition_bytes_cannot_change_between_records_under_one_name():
    rows = [row("a", [50] * 3, slots=20), row("b", [70] * 3)]
    for item in rows:
        for cells in item["rubrics"].values():
            for cell in cells["scorings"]:
                cell["measurement_identity"]["definition_sha256"] = item["label"] * 64
    result = decide(rows, noise(), "instrument-x")
    assert result["selected"] == "a"
    assert "definition_sha256 differs across records" in result["score_policy"]["fallback_reason"]
    with pytest.raises(ValueError, match="definition_sha256 differs across records"):
        pooled_variation(rows)
    for cells in rows[1]["rubrics"].values():
        for cell in cells["scorings"]:
            del cell["measurement_identity"]["definition_sha256"]
    with pytest.raises(ValueError, match="definition_sha256 differs across records"):
        pooled_variation(rows)
