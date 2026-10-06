"""Actual local calls plus interrupted admission; no provider/scoring claim."""
import copy

import pytest

from data_sheets_schema import nested_support_execution as ex
from tests.test_evaluation.test_nested_support_execution import (  # noqa: F401
    fixture, plan, peer, make,
)
from tests.test_evaluation.test_fitness_execution import make_fitness, fitness_peer  # noqa: F401


@pytest.mark.parametrize("builder", ["make", "make_fitness"])
def test_empty_entry_cannot_hide_a_later_actual_admission(request, builder):
    build = request.getfixturevalue(builder)
    registered, output, _, _ = build(count=2)
    original = ex.run(registered)
    assert original["admitted_calls"] == 2 and original["all_selected_accepted"]
    capture, ledger = ex.capture_run(output)
    assert ex.recheck_captured(capture, ledger) == original
    changed = copy.deepcopy(ledger)
    changed["attempts"][0] = {"admitted": None, "response": None, "settled": None}
    assert changed["attempts"][1] == ledger["attempts"][1]
    assert changed["attempts"][1]["admitted"] is not None
    with pytest.raises(ex.ExecutionError, match="empty entry must be terminal"):
        ex.recheck_captured(capture, changed)
    assert ex.recheck(output) == original


@pytest.mark.parametrize("builder", ["make", "make_fitness"])
def test_real_interruption_before_second_admission_keeps_terminal_empty_valid(request, builder, monkeypatch):
    build = request.getfixturevalue(builder)
    registered, output, _, _ = build(count=2)
    actual = ex._exclusive
    def interrupt(path, raw):
        if path.parent.name == "000001" and path.name == "admitted.json":
            raise OSError("invented interruption before second admission")
        return actual(path, raw)
    with monkeypatch.context() as local:
        local.setattr(ex, "_exclusive", interrupt)
        with pytest.raises(OSError, match="before second admission"):
            ex.run(registered)
    capture, ledger = ex.capture_run(output)
    assert len(ledger["attempts"]) == 2
    assert ledger["attempts"][0]["settled"] is not None
    assert ledger["attempts"][1] == {"admitted": None, "response": None, "settled": None}
    checked = ex.recheck_captured(capture, ledger)
    assert checked["admitted_calls"] == 1 and checked["rows"][0]["status"] == "accepted"
    assert sum(c["not_started"] for c in checked["selected_counts"].values()) == 1
    assert ex.recheck(output) == checked
    with pytest.raises(ValueError, match="exist"):
        ex.run(registered)
