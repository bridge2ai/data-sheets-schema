"""Structural agreement across generation replicates (#2932).

The unit tests pin the comparator's definitions; the corpus test reproduces
the issue's figures, restated as the brief does: the 354 class-ranged cells
filled in all three replicates include 69 single objects with no item count,
so the entry-count figures are over 285 list-valued cells.
"""
import importlib.util
from collections import Counter
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.replicate_structure import (
    align, compare_slot, compare_structure, dataset_slots, is_empty, summarize,
)

ROOT = Path(__file__).resolve().parents[1]


def _slot(*values):
    return compare_slot({f"rep{i}": v for i, v in enumerate(values, 1)})


def test_equal_counts_have_spread_zero():
    r = _slot([{"a": 1}, {"a": 2}], [{"a": 3}, {"a": 4}], [{"a": 1}, {"a": 2}])
    assert r["counted"] and r["counts"] == {"rep1": 2, "rep2": 2, "rep3": 2}
    assert (r["spread"], r["max_over_min"], r["counts_differ"]) == (0, 1.0, False)
    assert r["state"] == "two_agree"


def test_unequal_counts_give_their_spread_and_ratio():
    r = _slot([1], [1, 2], [1, 2, 3, 4, 5])
    assert r["counts"] == {"rep1": 1, "rep2": 2, "rep3": 5}
    assert (r["spread"], r["max_over_min"], r["counts_differ"]) == (4, 5.0, True)
    assert r["state"] == "all_differ"


def test_a_slot_missing_from_one_replicate_is_intermittent():
    r = _slot(["x"], None, ["x", "y"])
    assert r["state"] == "intermittent" and r["n_present"] == 2
    assert r["present"] == {"rep1": True, "rep2": False, "rep3": True}
    assert r["counts"] == {"rep1": 1, "rep3": 2}          # the absent replicate has no count


def test_empty_values_are_absent_not_present():
    for empty in ([], {}, "", None):
        assert is_empty(empty)
        assert _slot(empty, empty, empty)["state"] == "absent"
        assert _slot("v", empty, "v")["state"] == "intermittent"
    assert not is_empty([None]) and not is_empty(0) and not is_empty(False)


def test_whitespace_and_key_order_do_not_make_values_differ():
    r = _slot({"a": "x  y", "b": 1}, {"b": 1, "a": " x y"}, {"a": "x\ny", "b": 1})
    assert r["state"] == "identical"


def test_a_single_object_has_no_count_and_stays_out_of_count_denominators():
    r = _slot({"name": "A"}, {"name": "B"}, {"name": "A", "x": 1})
    assert not r["counted"]
    assert r["counts"] is None and r["spread"] is None and r["max_over_min"] is None
    assert r["alignment"] is None
    # Mixed: a list in one replicate and an object in another has no count either.
    assert not _slot([{"name": "A"}], {"name": "A"}, [{"name": "A"}])["counted"]
    # And the summary keeps it out of the counted nested slots.
    res = compare_structure({"r1": {"s": {"name": "A"}, "t": [1]}, "r2": {"s": {"name": "B"}, "t": [1, 2]}},
                            {"s": "nested", "t": "nested"})
    s = summarize(res)
    assert (s["nested_in_all"], s["nested_counted"], s["counts_differ"], s["ratio_ge_2"]) == (2, 1, ["t"], ["t"])


def test_key_sets_report_union_intersection_and_agreement():
    r = _slot([{"a": 1, "b": 2}], [{"a": 1}, {"c": 3}], [{"a": 1, "b": 2}])
    k = r["keys"]
    assert k["union"] == ["a", "b", "c"] and k["intersection"] == ["a"] and k["agree"] is False
    assert _slot([{"a": 1}], [{"a": 2}], [{"a": 3}])["keys"]["agree"] is True
    assert _slot(["x"], ["y"], ["z"])["keys"] is None


def test_alignment_joins_keyed_entries_by_key_and_keyless_by_position():
    """Keyed entries join on their key wherever they sit; keyless entries only
    by index, and that count is reported apart (#908)."""
    a = [{"name": "Ada"}, {"description": "p"}, {"name": "Bo"}]
    b = [{"name": "Bo"}, {"description": "q"}, {"name": "Cy"}]
    got = align(a, b)
    # Bo joins by name at another index; the keyless entry by position; Ada and Cy do not join.
    assert got == {"joined_by_key": {"name": 1}, "joined_by_position": 1, "unaligned": 2}


def test_position_never_takes_a_keyed_entry():
    got = align([{"description": "p"}], [{"name": "Ada"}])
    assert got == {"joined_by_key": {}, "joined_by_position": 0, "unaligned": 2}


def test_slot_alignment_sums_every_pair_of_replicates():
    r = _slot([{"id": "x:1"}, {"d": 1}], [{"id": "x:1"}, {"d": 2}], [{"id": "x:1"}])
    assert r["alignment"] == {"pairs": 3, "joined_by_key": {"id": 3}, "joined_by_position": 1,
                              "unaligned": 2}


def test_a_record_key_outside_the_universe_is_reported_not_compared():
    res = compare_structure({"r1": {"a": 1, "zz": "v", "source_caveats": "c", "e": None},
                             "r2": {"a": 1}}, ["a"])
    assert list(res["slots"]) == ["a"]
    assert res["outside_universe"] == ["zz"]              # source_caveats excluded, e empty


def test_the_universe_is_dataset_less_source_caveats():
    slots = dataset_slots()
    assert "source_caveats" not in slots
    assert slots["purposes"] == "nested" and slots["title"] == "scalar"
    assert set(slots.values()) <= {"nested", "list", "scalar"}


def _arm_comparison():
    spec = importlib.util.spec_from_file_location("arm_comparison_2932", ROOT / "scripts" / "arm_comparison.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_section_marks_non_replicates_and_single_records(tmp_path, monkeypatch):
    m = _arm_comparison()
    monkeypatch.setattr(m, "CONCAT", tmp_path)
    monkeypatch.setattr(m, "_method_for", lambda label, project: "claudecode_api")
    data = {k: {p: [] for p in m.PROJECTS} for k, *_ in m.ARMS}
    recs = {"L_rep1": {"purposes": [{"response": "a"}], "title": "T", "publisher": "P"},
            "L_rep2": {"purposes": [{"response": "a"}, {"response": "b"}], "title": "T"},
            "L_rep3": {"purposes": [{"response": "b"}], "title": "T"}}
    for label, rec in recs.items():
        d = tmp_path / "claudecode_api" / label
        d.mkdir(parents=True)
        (d / "CHORUS_d4d.yaml").write_text(yaml.safe_dump(rec))
    data["v8prod"]["CHORUS"] = [{"label": label} for label in recs]
    data["v8prod"]["VOICE"] = [{"label": "L_rep1"}]
    data["v7api"]["CHORUS"] = [{"label": "L_rep1"}, {"label": "L_rep2"}]
    text = "\n".join(m.replicate_structure_section(data))
    assert "| v7 API canaries (2026-08-28…d, exploratory) | – | – | not replicates:" in text
    assert "| v8 API production (2026-09-04f/g) | VOICE | 1 | – |" in text
    row = next(l for l in text.splitlines() if l.startswith("| v8 API production (2026-09-04f/g) | CHORUS |"))
    # purposes and title in all; publisher intermittent; purposes counts 1/2/1.
    assert "| 3 | 2 / 1 / " in row and "`publisher` (1/3)" in row
    assert "| 1: 1 / 1 / 1 |" in row
    assert "`purposes` 1/2/1" in text
    # Arms without both production arms print no pooled restatement.
    assert "over the v7 and v8 production arms" not in text


@pytest.mark.corpus
def test_the_v7_and_v8_production_arms_reproduce_the_issue_figures():
    """#2932, restated: 97 intermittent cells; 354 class-ranged cells filled
    in all three, 285 of them lists; 165 differ in count, 75 by max/min >= 2."""
    m = _arm_comparison()
    slots = dataset_slots()
    assert len(slots) == 97
    per_group, tot = {}, Counter()
    differ, held = Counter(), Counter()
    for arm in ("v7prod", "v8prod"):
        prefix = next(pfx for key, _d, pfx, *_ in m.ARMS if key == arm)
        for p in m.PROJECTS:
            recs = {}
            for label in m.arm_labels(prefix):
                method = m._method_for(label, p)
                full = m.CONCAT / method / label / f"{p}_d4d.yaml"
                prov = m.CONCAT / f"{method}_core" / label / f"{p}_provenance.yaml"
                if not full.exists():
                    continue
                if (yaml.safe_load(prov.read_text()).get("validation") or {}).get("passed") is False:
                    continue                          # the #1029 exclusion arm_comparison applies
                recs[label] = yaml.safe_load(full.read_text())
            assert len(recs) == 3, (arm, p, sorted(recs))
            res = compare_structure(recs, slots)
            s = summarize(res)
            per_group[(p, arm)] = s["some"]
            tot.update(some=s["some"], nested=s["nested_in_all"], counted=s["nested_counted"],
                       differ=len(s["counts_differ"]), ge2=len(s["ratio_ge_2"]))
            for name in s["counts_differ"]:
                differ[name] += 1
            for name, r in res["slots"].items():
                if r.get("kind") == "nested" and r["counted"] and r["n_present"] == 3:
                    held[name] += 1
    assert per_group == {("AI_READI", "v7prod"): 8, ("AI_READI", "v8prod"): 8,
                         ("CHORUS", "v7prod"): 9, ("CHORUS", "v8prod"): 14,
                         ("CM4AI", "v7prod"): 24, ("CM4AI", "v8prod"): 17,
                         ("VOICE", "v7prod"): 8, ("VOICE", "v8prod"): 9}
    assert tot["some"] == 97
    assert (tot["nested"], tot["counted"], tot["differ"], tot["ge2"]) == (354, 285, 165, 75)
    for name, n in {"purposes": 8, "external_resources": 8, "preprocessing_strategies": 7,
                    "subpopulations": 6, "related_datasets": 6}.items():
        assert (differ[name], held[name]) == (n, n), name
