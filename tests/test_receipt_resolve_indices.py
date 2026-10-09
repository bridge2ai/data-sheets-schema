"""#4767: bounded index conversion preserves receipt path presence semantics."""
import sys

import pytest

from data_sheets_schema import receipts


@pytest.mark.parametrize("digits", ["9" * 6000, "٩" * 6000, "９" * 6000,
                                    "०" * 6000 + "2", "0٠०" * 2000 + "22"])
def test_huge_out_of_range_indices_are_false_without_changing_interpreter_limits(digits):
    before = sys.get_int_max_str_digits()
    assert receipts.resolve({"a": ["zero", "one"]}, f"a[{digits}]") is False
    assert sys.get_int_max_str_digits() == before


@pytest.mark.parametrize("zeros", ["0" * 6000, "٠" * 6000, "०" * 6000, "0٠०０" * 1500])
@pytest.mark.parametrize("suffix", ["", "1", "١", "१", "１"])
def test_all_zero_and_mixed_unicode_leading_zero_indices_still_resolve(zeros, suffix):
    assert receipts.resolve({"a": [False, None]}, f"a[{zeros}{suffix}]") is True


@pytest.mark.parametrize("node", [[], {}, {"0": "not a list"}, "text", (), None, False, 0])
def test_empty_or_non_list_nodes_refuse_even_giant_indices_without_conversion(monkeypatch, node):
    def unexpected(*args, **kwargs):
        raise AssertionError("an impossible list index was converted")
    monkeypatch.setattr(receipts, "int", unexpected, raising=False)
    assert receipts.resolve({"a": node}, "a[" + "9" * 6000 + "]") is False
    assert receipts.resolve({"a": node}, "a[0]") is False


def test_only_bounded_significant_digits_reach_integer_conversion(monkeypatch):
    calls = []
    real_int = int
    def observed(text):
        calls.append(text)
        assert len(text) <= 2
        return real_int(text)
    monkeypatch.setattr(receipts, "int", observed, raising=False)
    record = {"a": list(range(11))}
    assert receipts.resolve(record, "a[" + "٠0" * 3000 + "١٠]") is True
    assert calls == ["١٠"]
    assert receipts.resolve(record, "a[" + "0" * 6000 + "]") is True
    assert calls == ["١٠", "0"]
    assert receipts.resolve(record, "a[" + "9" * 6000 + "]") is False
    assert calls == ["١٠", "0"]
    assert receipts.resolve(record, "a[11]") is False
    assert calls[-1] == "11"  # Equal digit length still needs the numeric bound.


def test_nested_lists_keep_valid_paths_and_reject_each_out_of_range_segment():
    record = {"matrix": [[{"value": 0}], [{"value": False}]]}
    prefix = "0٠०" * 2000
    assert receipts.resolve(record, f"matrix[{prefix}١][{prefix}].value") is True
    assert receipts.resolve(record, f"matrix[{prefix}٢][0].value") is False
    assert receipts.resolve(record, f"matrix[1][{prefix}١].value") is False
    assert receipts.resolve(record, "matrix[1][0].value.missing") is False


@pytest.mark.parametrize(("path", "expected"), [
    ("a", True), ("a[0]", True), ("a[1]", True), ("a[01]", True), ("a[١]", True),
    ("a[1].value", True), ("a[2]", False), ("a[-1]", False), ("a[+1]", False),
    ("a[1.0]", False), ("a[²]", False), ("a[]", False), ("a[1]trailing", False),
    ("a[ 1]", False), ("a[1] ", False), ("a[1].missing", False),
    ("missing[0]", False), ("", False), ("a/1", False), ("a[1].", False),
])
def test_ordinary_path_grammar_and_presence_outcomes_are_unchanged(path, expected):
    assert receipts.resolve({"a": [0, {"value": None}]}, path) is expected
