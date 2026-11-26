"""Fixture-only controls for score_gap_v1 and review issues 6388 to 6394."""

from copy import deepcopy
import hashlib
import json
import math

import pytest

from data_sheets_schema._score_selection_math import (
    FIXED_MAXIMA, MEASURED_HASHES, _portable_text, decide, pooled_variation, summarize,
)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def row(label, first, second=None, *, slots=10, project="Example", valid=True):
    second = first if second is None else second
    value = {"label": label, "project": project, "validity": "valid" if valid else "invalid",
             "slots": slots, "instrument_id": "instrument-x", "eligibility_problems": [], "rubrics": {}}
    for rubric, scores in (("rubric10", first), ("rubric20", second)):
        identity = {key: digest(key + rubric) for key in MEASURED_HASHES}
        identity.update(instrument_id="instrument-x", record_sha256=digest(project + label),
                        context_sha256=digest("shared applicability"))
        maximum = FIXED_MAXIMA[rubric]
        value["rubrics"][rubric] = {"scorings": [
            {"scoring_number": number, "status": "measured", "points": score * maximum / 100,
             "maximum": maximum, "adjusted_max_points": maximum, "percentage": score,
             "attempt": 1, "measurement_identity": deepcopy(identity),
             "publication_path": f"data/evaluation_repeats/{project}/{label}/{rubric}/{number}.json",
             "publication_sha256": digest(f"publication {project} {label} {rubric} {number}"),
             "receipt_sha256": digest(f"receipt {project} {label} {rubric} {number}"),
             "plan_sha256": digest(f"plan {project} {label} {rubric} {number}")}
            for number, score in enumerate(scores, 1)]}
    return value


def noise(s=1):
    return {"s": s, "degrees_of_freedom": 10, "records": 5, "instrument_id": "instrument-x"}


def test_strict_gap_just_below_above_and_exact_threshold():
    # These percentages and this s give exactly 2.0 in binary float, not a
    # below-threshold rounding artefact. M01 must fail on the exact case.
    s = math.nextafter(1 / math.sqrt(2 / 3), math.inf)
    threshold = 2 * s * math.sqrt(2 / 3)
    assert threshold == 2.0
    incumbent = row("a", [0, 0, 0], slots=20)
    for gap, expected in ((2.0 - 1e-8, "a"), (2.0, "a"), (2.0 + 1e-8, "b")):
        result = decide([incumbent, row("b", [gap] * 3)], noise(s), "instrument-x")
        assert result["selected"] == expected
        assert result["score_policy"]["T"] == threshold
        if gap == 2.0:
            assert result["score_policy"]["gap"] == result["score_policy"]["T"]
        assert result["score_policy"]["rule"] == ("score_gap" if expected == "b" else "policy_fallback")


def test_one_rubric_reversing_cannot_be_carried_by_the_other():
    rows = [row("a", [50] * 3, slots=20), row("b", [90] * 3, [49] * 3)]
    result = decide(rows, noise(), "instrument-x")
    assert result["selected"] == "a"
    assert result["score_policy"]["gap"] == 19.5
    assert "rubric20" in result["score_policy"]["fallback_reason"]


def test_reversal_is_judged_on_mean_not_scoring_one_m08():
    rows = [row("a", [50] * 3, slots=20), row("b", [90] * 3, [51, 45, 45])]
    result = decide(rows, noise(), "instrument-x")
    assert result["selected"] == "a"
    assert result["score_policy"]["fallback_reason"] == "rubric mean reverses: rubric20"


def test_equal_rubric_means_are_not_a_reversal_m09():
    rows = [row("a", [50] * 3, slots=20), row("b", [70] * 3, [49, 50, 51])]
    result = decide(rows, noise(), "instrument-x")
    assert result["selected"] == "b"
    assert result["score_policy"]["rule"] == "score_gap"


def test_missing_scoring_causes_fallback_not_zero_or_silent_drop():
    high = row("b", [100, 100, 100])
    high["rubrics"]["rubric10"]["scorings"].pop()
    result = decide([row("a", [50] * 3, slots=20), high], noise(), "instrument-x")
    assert result["selected"] == "a"
    assert "fewer than three" in result["score_policy"]["fallback_reason"]
    assert result["score_policy"]["candidates"][1]["rubrics"]["rubric10"]["mean"] == 100
    missing = result["score_policy"]["candidates"][1]["not_measured_cells"]
    assert missing == [{"rubric": "rubric10", "scoring_number": 3,
                        "reason": "not measured: scoring cell is absent"}]


def test_not_measured_cell_and_missing_column_remain_none():
    high = row("b", [100] * 3)
    for cell in high["rubrics"]["rubric10"]["scorings"]:
        cell.update(status="not measured", points=None, maximum=None, percentage=None,
                    reason="scoring receipt was refused")
    result = decide([row("a", [50] * 3, slots=20), high], noise(), "instrument-x")
    assert result["selected"] == "a"
    summary = result["score_policy"]["candidates"][1]
    assert summary["rubrics"]["rubric10"] == {"mean": None, "spread": None, "count": 0}
    assert summary["paired"]["mean"] is None
    assert "scoring receipt was refused" in result["score_policy"]["fallback_reason"]


def test_invalid_top_score_never_wins():
    invalid = row("invalid", [100] * 3, slots=100, valid=False)
    result = decide([row("a", [50] * 3, slots=20), row("b", [70] * 3), invalid], noise(), "instrument-x")
    assert result["selected"] == "b"


def test_tied_score_does_not_replace_current_policy_and_label_is_deterministic():
    rows = [row("b", [50] * 3), row("a", [50] * 3)]
    before = deepcopy(rows)
    first = decide(rows, noise(), "instrument-x")
    assert first["selected"] == "a"
    assert first == decide(list(reversed(rows)), noise(), "instrument-x")
    assert first["score_policy"]["tied_highest_mean"] == ["a", "b"]
    assert "coverage then label" in first["score_policy"]["tie_resolution"]
    assert rows == before


def test_highest_tie_does_not_try_a_second_tied_candidate_after_reversal():
    rows = [row("p", [50] * 3, slots=30), row("b", [80] * 3, [40] * 3, slots=20),
            row("c", [60] * 3, slots=10)]
    result = decide(rows, noise(), "instrument-x")
    assert result["selected"] == "p"
    assert result["score_policy"]["highest_mean_pick"] == "b"
    assert result["score_policy"]["tied_highest_mean"] == ["b", "c"]
    assert "retain P" in result["score_policy"]["tie_resolution"]


def test_duplicate_attempt_is_not_a_second_measurement_and_paths_are_portable():
    high = row("b", [70] * 3)
    cell = high["rubrics"]["rubric10"]["scorings"][2]
    cell.update(attempt=2, receipt="/synthetic-evidence/operator/attempt2/receipt.json", receipt_sha256="2" * 64,
                refused_attempt={"path": "/synthetic-evidence/operator/attempt1/receipt.json", "sha256": "1" * 64,
                                 "reason": "synthetic output refused at /synthetic-evidence/operator/private/output.json"})
    selected = decide([row("a", [50] * 3, slots=20), high], noise(), "instrument-x")
    assert selected["selected"] == "b"
    replacements = selected["score_policy"]["replaced_cells"]
    assert len(replacements) == 1
    assert replacements[0]["receipt_sha256"] == "2" * 64
    assert replacements[0]["refused_attempt"]["receipt_sha256"] == "1" * 64
    assert "synthetic output refused" in replacements[0]["refused_attempt"]["reason"]
    assert "/synthetic-evidence/" not in json.dumps(selected["score_policy"])
    high["rubrics"]["rubric10"]["scorings"].append(deepcopy(cell))
    result = decide([row("a", [50] * 3, slots=20), high], noise(), "instrument-x")
    assert result["selected"] == "a"
    assert "duplicate scoring" in result["score_policy"]["fallback_reason"]


def test_changed_measured_input_or_instrument_falls_back_without_raising():
    rows = [row("a", [50] * 3, slots=20), row("b", [70] * 3)]
    rows[1]["rubrics"]["rubric10"]["scorings"][1]["measurement_identity"]["record_sha256"] = digest("changed")
    assert "measured inputs differ" in decide(rows, noise(), "instrument-x")["score_policy"]["fallback_reason"]
    summary = summarize(rows[1])
    assert len(summary["not_measured_cells"]) == 3
    assert all("measured inputs differ" in cell["reason"] for cell in summary["not_measured_cells"])
    assert all(cell["reason"] and not cell["usable"] for cell in summary["cells"]["rubric10"])
    rows[1] = row("b", [70] * 3)
    rows[1]["instrument_id"] = "another-instrument"
    pooled = pooled_variation(rows)
    assert pooled["s"] is None
    assert "one named instrument" in pooled["not_measured_reason"]
    assert pooled["pool_suppressed"] is True
    assert "fewer than two records" not in pooled["not_measured_reason"]
    result = decide(rows, pooled, "instrument-x")
    assert result["selected"] == "a"
    assert "instrument differs" in result["score_policy"]["fallback_reason"]


def test_unknown_wrong_zero_or_single_record_noise_falls_back():
    rows = [row("a", [50] * 3, slots=20), row("b", [70] * 3)]
    for pooled, reason in ((noise(None), "not measured"), (noise(0), "variation is zero"),
                           ({**noise(), "instrument_id": "other"}, "instrument differs"),
                           ({**noise(), "records": 1}, "fewer than two records")):
        result = decide(rows, pooled, "instrument-x")
        assert result["selected"] == "a"
        assert reason in result["score_policy"]["fallback_reason"]
    empty = pooled_variation([])
    assert empty["s"] is None and empty["degrees_of_freedom"] == 0


def test_pooled_within_record_degrees_of_freedom_and_unequal_rubric_spreads_m02_m15_m17():
    # Combined [20,24,28] and [11,15]: SS 32 + 8, df 2 + 1.
    # Rubric10 instead has SS 8 + 18, so M15 cannot give the same answer.
    rows = [row("a", [10, 12, 14], [30, 36, 42]),
            row("b", [10, 16], [12, 14], project="Other", valid=False),
            row("c", [99], project="Other")]
    actual = pooled_variation(rows)
    assert actual["degrees_of_freedom"] == 3
    assert actual["records"] == 2
    assert actual["s"] == pytest.approx(math.sqrt(40 / 3))
    assert actual["per_project"]["Example"]["s"] == pytest.approx(4)
    assert actual["per_project"]["Other"]["s"] == pytest.approx(math.sqrt(8))
    assert actual["per_rubric"]["rubric10"]["s"] == pytest.approx(math.sqrt(26 / 3))
    assert actual["fallback_reasons"]  # diagnostic partial pool cannot decide
    assert [item["usable_paired_count"] for item in actual["series_census"]] == [3, 2, 1]


def test_candidate_spread_uses_sample_sd_m11():
    summary = summarize(row("a", [10, 12, 14], [30, 36, 42]))
    assert summary["rubrics"]["rubric10"]["spread"] == pytest.approx(2)
    assert summary["rubrics"]["rubric20"]["spread"] == pytest.approx(6)
    assert summary["paired"]["spread"] == pytest.approx(4)


def test_pairing_uses_scoring_numbers_and_fourth_scoring_forces_fallback():
    candidate = row("b", [70, 80, 90, 100], [90, 80, 70, 60])
    candidate["rubrics"]["rubric20"]["scorings"].reverse()
    assert summarize(candidate)["paired"] == {"mean": 80.0, "spread": 0.0, "count": 4}
    result = decide([row("a", [50] * 3, slots=20), candidate], noise(), "instrument-x")
    assert result["selected"] == "a"
    assert "threshold is defined for means of three" in result["score_policy"]["fallback_reason"]


def test_review_counts_do_not_rank_or_veto_and_zero_score_is_measured():
    rows = [row("a", [0] * 3, slots=20), row("b", [20] * 3)]
    rows[1]["content_review"] = {"adverse": 9999}
    result = decide(rows, noise(), "instrument-x")
    assert result["selected"] == "b"
    assert result["score_policy"]["candidates"][0]["paired"]["mean"] == 0


def test_instrument_definition_bytes_cannot_change_between_records_under_one_name():
    rows = [row("a", [50] * 3, slots=20), row("b", [70] * 3)]
    for cells in rows[1]["rubrics"].values():
        for cell in cells["scorings"]:
            cell["measurement_identity"]["definition_sha256"] = digest("different definition")
    pooled = pooled_variation(rows)
    assert pooled["s"] is None
    assert "definition_sha256 differs across records" in pooled["not_measured_reason"]
    result = decide(rows, pooled, "instrument-x")
    assert result["selected"] == "a"
    assert "definition_sha256 differs across records" in result["score_policy"]["fallback_reason"]


def test_every_measured_cell_requires_pinned_identity_keys(missing):
    rows = [row("a", [50] * 3, slots=20), row("b", [70] * 3)]
    for item in rows:
        for family in item["rubrics"].values():
            for cell in family["scorings"]:
                del cell["measurement_identity"][missing]
    result = decide(rows, pooled_variation(rows), "instrument-x")
    assert result["selected"] == "a"
    assert (missing in result["score_policy"]["fallback_reason"]
            or "instrument id missing" in result["score_policy"]["fallback_reason"])


def test_fixed_denominator_and_context_compatibility(kind):
    rows = [row("a", [50] * 3, slots=20), row("b", [70] * 3)]
    cells = rows[1]["rubrics"]["rubric20"]["scorings"]
    if kind == "maximum":
        for cell in cells:
            cell.update(points=35, maximum=44, adjusted_max_points=44, percentage=100 * 35 / 44)
    elif kind == "adjusted maximum":
        for cell in cells:
            cell["adjusted_max_points"] = 44
    elif kind == "candidate context":
        cells = cells + rows[1]["rubrics"]["rubric10"]["scorings"]
        for cell in cells:
            cell["measurement_identity"]["context_sha256"] = digest("changed applicability")
    else:
        for item in rows:
            for cell in item["rubrics"]["rubric20"]["scorings"]:
                cell["measurement_identity"]["context_sha256"] = digest("changed applicability")
    result = decide(rows, pooled_variation(rows), "instrument-x")
    assert result["selected"] == "a"
    assert ("maximum" if "maximum" in kind else "context differs") in result["score_policy"]["fallback_reason"]
    assert result["score_policy"]["percentage_base"]["maxima"] == {"rubric10": 50, "rubric20": 88}


def test_unreadable_other_project_preserved_and_blocks_every_project():
    selected = [row("a", [49, 50, 51], slots=20), row("b", [69, 70, 71])]
    other = row("x", [10, 11, 12], project="Other", valid=False)
    other["eligibility_problems"] = ["record YAML cannot be parsed at /synthetic-evidence/operator/records/x.yaml"]
    for family in other["rubrics"].values():
        for cell in family["scorings"]:
            cell.update(status="not measured", reason="record YAML cannot be parsed")
    pooled = pooled_variation(selected + [other])
    assert len(pooled["series_census"]) == 3
    census = pooled["series_census"][2]
    assert census["usable_paired_count"] == 0 and len(census["not_measured_cells"]) == 6
    result = decide(selected, pooled, "instrument-x")
    assert result["selected"] == "a"
    assert "Other/x" in result["score_policy"]["fallback_reason"]
    assert "cannot be parsed" in result["score_policy"]["fallback_reason"]
    assert "/synthetic-evidence/" not in json.dumps(result["score_policy"])
    assert result["score_policy"]["series_census"] == pooled["series_census"]


def test_unattributed_refusal_eligibility_reason_blocks_complete_series():
    selected = [row("a", [49, 50, 51], slots=20), row("b", [69, 70, 71])]
    other = row("x", [10, 11, 12], project="Other", valid=False)
    other["rubrics"]["rubric10"]["eligibility_problems"] = ["undeclared matching REFUSED receipt"]
    pooled = pooled_variation(selected + [other])
    assert pooled["series_census"][2]["usable_paired_count"] == 3
    assert "undeclared matching REFUSED receipt" in pooled["not_measured_reason"]
    assert decide(selected, pooled, "instrument-x")["selected"] == "a"


def test_canonical_contains_cells_needed_to_rederive_scores():
    rows = [row("a", [49, 50, 51], slots=20), row("b", [69, 70, 71])]
    decision = decide(rows, pooled_variation(rows), "instrument-x")
    block = decision["score_policy"]
    for candidate in block["candidates"]:
        for rubric, cells in candidate["cells"].items():
            assert len(cells) == 3
            for cell in cells:
                assert cell["publication_path"].startswith("data/")
                assert len(cell["publication_sha256"]) == len(cell["receipt_sha256"]) == 64
                assert cell["percentage"] == pytest.approx(100 * cell["points"] / cell["maximum"])
                assert cell["maximum"] == FIXED_MAXIMA[rubric]
    assert block["series_census"] == block["candidates"]


def test_explicit_policy_pick_is_used_once_without_reselecting_it():
    rows = [row("a", [50] * 3, slots=20), row("b", [70] * 3)]
    result = decide(rows, noise(), "instrument-x", policy_pick="b")
    assert result["score_policy"]["current_policy_pick"] == "b"
    assert result["selected"] == "b"
    with pytest.raises(ValueError, match="supplied current policy pick"):
        decide(rows, noise(), "instrument-x", policy_pick="unknown")


def test_explicit_unverified_policy_pick_is_retained_without_score_promotion():
    rows = [row("a", [50] * 3, slots=20, valid=False), row("b", [70] * 3)]
    rows[0]["validity"] = "unverified"
    result = decide(rows, noise(), "instrument-x", policy_pick="a")
    assert result["selected"] == "a"
    assert result["score_policy"]["rule"] == "policy_fallback"
    assert "not current-valid for score comparison" in result["score_policy"]["fallback_reason"]


def test_portable_text_preserves_web_and_relative_references():
    for text in ("https://example.org/ref", "http://example.org/a/b", "notes/owner-word.md",
                 "./notes/owner-word.md", "../notes/owner-word.md", r"notes\owner-word.md"):
        assert _portable_text(text) == text
        assert _portable_text("reference: " + text) == "reference: " + text


def test_portable_text_removes_absolute_unix_and_windows_paths():
    for text in ("/synthetic-evidence/operator/receipt.json", "C:/evidence/receipt.json",
                 r"C:\evidence\receipt.json", r"\\host\share\receipt.json"):
        assert _portable_text(text) == "[external path]"
        assert _portable_text("failed reading '" + text + "'") == "failed reading '[external path]'"


test_every_measured_cell_requires_pinned_identity_keys = pytest.mark.parametrize(
    "missing", (*MEASURED_HASHES, "instrument_id")
)(test_every_measured_cell_requires_pinned_identity_keys)
test_fixed_denominator_and_context_compatibility = pytest.mark.parametrize(
    "kind", ("maximum", "adjusted maximum", "candidate context", "rubric context")
)(test_fixed_denominator_and_context_compatibility)
