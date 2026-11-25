"""Controls for the chained PR6325 D128 successor helper (2026-11-24).

Invented small arrays only; never D128 source evidence. The helper's stop rule
is the lead's for this assignment (STATUS 2026-11-24T20:59:12Z, 21:01:28Z):
against the predecessor's approved arrays only line-only relocations pass,
with at most one hit that differs in `line` and in a `model_text_function`
whose text changes only in the line number it ends with.
"""
from copy import deepcopy

import pytest

from scripts.adhoc import compare_pr6325_d128_successor_20261124 as helper

SENT = "PHASE_INSTRUCTIONS (sent in a PhaseRequest at src/x.py:{})"


def _arrays():
    hit = dict(path="src/x.py", line=10, match="token", snippet="text", category="c", pattern="p", context="string_literal")
    described = dict(hit, line=20, snippet="other", model_text_function=SENT.format(300))
    violation = dict(path="notes/y.py", line=3, match="NAME", snippet="v", category="gc_project", pattern="q", context="code_table")
    dependency = dict(path="tests/test_z.py", line=7, match="NAME", snippet="assert", category="gc_project", context="test_assertion")
    before = dict(hits=[hit, described], violations=[violation], test_dependencies=[dependency])
    after = deepcopy(before)
    after["hits"][0]["line"] = 12
    after["hits"][1].update(line=22, model_text_function=SENT.format(302))
    after["test_dependencies"][0]["line"] = 9
    return before, after


def _delta(before, after):
    return {name: {key: value for key, value in ledger.items() if key not in ("positional_differences", "exact_arrays_equal")}
            for name, ledger in helper.compare("toy", before, after)["arrays"].items()}


def test_line_only_moves_and_the_one_disposed_row_pass():
    before, after = _arrays()
    delta = _delta(before, after)
    assert [len(delta["hits"][kind]) for kind in ("relocations", "changed_fields")] == [1, 1]
    assert delta["hits"]["changed_fields"][0]["differing_fields"] == ["line", "model_text_function"]
    assert helper.require_stop_rule(delta) == 1
    assert helper.moved_reference_only(SENT.format(300), SENT.format(302))


@pytest.mark.parametrize("change", ["added_hit", "removed_hit", "snippet", "second_exception", "other_description",
                                    "description_without_line_move", "violation_line", "dependency_text",
                                    "exception_in_dependencies"])
def test_anything_else_stops_with_no_proposal(change):
    before, after = _arrays()
    if change == "added_hit": after["hits"].append(dict(after["hits"][0], line=99, snippet="new text"))
    elif change == "removed_hit": after["hits"].pop(0)
    elif change == "snippet": after["hits"][0]["snippet"] = "edited"
    elif change == "second_exception":
        before["hits"].append(dict(before["hits"][1], line=40, snippet="third"))
        after["hits"].append(dict(after["hits"][1], line=44, snippet="third", model_text_function=SENT.format(305)))
    elif change == "other_description": after["hits"][1]["model_text_function"] = "OTHER (sent at src/x.py:302)"
    elif change == "description_without_line_move": after["hits"][1]["line"] = 20
    elif change == "violation_line": after["violations"][0]["line"] = 4
    elif change == "dependency_text": after["test_dependencies"][0]["snippet"] = "assert other"
    else:
        before["test_dependencies"][0]["model_text_function"] = SENT.format(1)
        after["test_dependencies"][0]["model_text_function"] = SENT.format(2)
    with pytest.raises(ValueError):
        helper.require_stop_rule(_delta(before, after))


@pytest.mark.parametrize(("before", "after"), [
    (SENT.format(300), SENT.format(300)),                       # no change is not a move
    (SENT.format(300), SENT.format(300).replace("PHASE", "OTHER")[:-5] + ":302)"),
    (SENT.format(300), "sent at src/x.py:302"),                 # no closing form
    (None, SENT.format(302)), (SENT.format(300), None), (300, 302),
])
def test_only_a_trailing_line_number_may_differ(before, after):
    assert helper.moved_reference_only(before, after) is False


def test_the_helper_pins_the_unchanged_pr6302_successor_and_its_own_assignment():
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert hashlib.sha256((root / helper.PREDECESSOR_FIXTURE).read_bytes()).hexdigest() == helper.PREDECESSOR_SHA
    from tests import test_native_d128_scanner_comparison as gate
    assert gate.SUCCESSOR_SHA256 == helper.PREDECESSOR_SHA
    assert helper.ASSIGNMENT.startswith("PR6325 lead assignment 2026-11-24: line-only relocations")
    assert helper.ASSIGNMENT.endswith("historical D128 decision and PR6302 successor unchanged")


# Review 2 (D1 to D3): nothing a ledger declares is taken on trust.

def _honest():
    before, after = _arrays()
    return before, after, _delta(before, after)


def test_a_delta_that_declares_nothing_does_not_pass():
    """D1: right counts and hashes with empty lists accounted no occurrence."""
    _, _, delta = _honest()
    for ledger in delta.values():
        ledger.update(exact_matches=[], relocations=[], changed_fields=[])
    with pytest.raises(ValueError, match="occurrence accounting"):
        helper.require_stop_rule(delta)


@pytest.mark.parametrize("forgery", ["duplicate_index", "missing_index", "index_out_of_range"])
def test_every_occurrence_is_accounted_exactly_once(forgery):
    before, after = _arrays()
    before["hits"].append(dict(before["hits"][0], line=50, snippet="plain"))
    after["hits"].append(deepcopy(before["hits"][2]))
    delta = _delta(before, after)
    assert delta["hits"]["exact_matches"] == [[2, 2]] and helper.require_stop_rule(delta) == 1
    if forgery == "duplicate_index": delta["hits"]["exact_matches"].append([2, 2])
    elif forgery == "missing_index": delta["hits"]["exact_matches"] = []
    else: delta["hits"]["exact_matches"] = [[3, 3]]
    with pytest.raises(ValueError, match="occurrence accounting"):
        helper.require_stop_rule(delta)


def test_declared_differing_fields_are_recomputed_from_the_row_objects():
    """D2: a content change declared as a line-only move."""
    _, _, delta = _honest()
    row = delta["hits"]["relocations"][0]
    row["after"]["snippet"] = "edited"
    assert row["differing_fields"] == ["line"]
    with pytest.raises(ValueError, match="declares other fields"):
        helper.require_stop_rule(delta)


def test_a_pure_reorder_stops():
    """D3: the same objects in another order are not line-only relocations."""
    before, _ = _arrays()
    before["hits"].append(dict(before["hits"][0], line=50, snippet="plain"))
    after = deepcopy(before)
    after["hits"][0], after["hits"][2] = after["hits"][2], after["hits"][0]
    with pytest.raises(ValueError, match="changed position"):
        helper.require_stop_rule(_delta(before, after))


def _chain():
    """A toy baseline, the arrays a toy PR6302 successor approved, and a candidate."""
    middle, after = _arrays()
    baseline = deepcopy(middle)
    baseline["hits"][0]["line"] = 8                      # a relocation the earlier successor approved
    baseline["hits"].pop(1)                              # and a hit it approved as added
    predecessor = dict(kind=helper.PREDECESSOR_KIND, arrays=_delta(baseline, middle))
    return baseline, middle, after, predecessor


def test_the_predecessor_arrays_are_rebuilt_from_the_baseline_and_its_ledger():
    baseline, middle, _, predecessor = _chain()
    assert [len(predecessor["arrays"]["hits"][kind]) for kind in ("relocations", "added")] == [1, 1]
    assert helper.same(helper.predecessor_arrays(predecessor, baseline), middle)
    other = deepcopy(baseline)
    other["hits"][0]["snippet"] = "not the baseline"
    with pytest.raises(ValueError, match="starts from"):
        helper.predecessor_arrays(predecessor, other)
    forged = deepcopy(predecessor)
    forged["arrays"]["hits"]["added"][0]["after"]["snippet"] = "edited"
    with pytest.raises(ValueError, match="cannot be rebuilt"):
        helper.predecessor_arrays(forged, baseline)
    with pytest.raises(ValueError, match="not the PR6302 successor"):
        helper.predecessor_arrays(dict(predecessor, kind="other"), baseline)


def test_the_chained_delta_is_bound_to_the_scanned_arrays():
    baseline, middle, after, predecessor = _chain()
    value = dict(predecessor=dict(delta=_delta(middle, after)))
    assert helper.require_delta_on_arrays(value, predecessor, baseline, after) == 1
    # D1 as reproduced by the review: the candidate's content changes with the count kept,
    # and the delta is the honest one of other arrays or declares an in-place exact match.
    changed = deepcopy(after)
    changed["hits"][0]["snippet"] = "edited"
    with pytest.raises(ValueError):
        helper.require_delta_on_arrays(value, predecessor, baseline, changed)
    declared = deepcopy(value)
    ledger = declared["predecessor"]["delta"]["hits"]
    ledger.update(exact_matches=[[0, 0], [1, 1]], relocations=[], changed_fields=[],
                  after_sha256=helper.sha(helper.encoded(changed["hits"])))
    assert helper.require_stop_rule(declared["predecessor"]["delta"]) == 0   # self-consistent as declared
    with pytest.raises(ValueError, match="exact occurrence changed"):
        helper.require_delta_on_arrays(declared, predecessor, baseline, changed)
    with pytest.raises(ValueError):
        helper.require_delta_on_arrays(dict(predecessor=dict()), predecessor, baseline, after)


# Review 2 (MN3): controls for the two stop-rule checks no earlier control could fail without.

def test_a_cross_index_row_stops():
    """A relocation and a changed row that swap their after indexes, accounting otherwise consistent."""
    _, _, delta = _honest()
    relocation, changed = delta["hits"]["relocations"][0], delta["hits"]["changed_fields"][0]
    assert (relocation["before_index"], changed["before_index"]) == (0, 1)
    relocation["after_index"], changed["after_index"] = 1, 0     # both sides still a permutation of 0..1
    assert relocation["differing_fields"] == helper.fields(relocation["before"], relocation["after"])
    with pytest.raises(ValueError, match="changed position"):
        helper.require_stop_rule(delta)


@pytest.mark.parametrize("fields", [["line", "snippet"], []])
def test_a_relocation_must_differ_in_line_alone(fields):
    """A relocation row whose recomputed differing fields, declared honestly, are not exactly ['line']."""
    _, _, delta = _honest()
    row = delta["hits"]["relocations"][0]
    if fields:
        row["after"]["snippet"] = "edited"
    else:
        row["after"] = deepcopy(row["before"])
    row["differing_fields"] = helper.fields(row["before"], row["after"])
    assert row["differing_fields"] == fields
    with pytest.raises(ValueError, match="non-coordinate relocation"):
        helper.require_stop_rule(delta)
