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
