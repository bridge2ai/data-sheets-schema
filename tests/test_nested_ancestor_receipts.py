"""Opt-in factual receipt-path diagnostics; no new omission or support credit."""
from copy import deepcopy
import json
import sys

import pytest

from data_sheets_schema.replicate_structure import (
    compare_structure, nested_omission_candidates, resolve_verified,
)
from tests.test_replicate_structure import _arm_comparison, _section_fixture


def records():
    a = {"name": "A", "orcid": "x", "notes": "commentary",
         "aff": [{"name": "MIT"}, {"name": "UCL"}]}
    return {"r1": {"s": [deepcopy(a), {"name": "B"}]},
            "r2": {"s": [{"name": "B"}, deepcopy(a)]},
            "r3": {"s": [{"name": "A", "aff": [{"name": "MIT"}]}, {"name": "B"}]}}


def read(resolved, *, recs=None, diagnostics=True):
    recs = records() if recs is None else recs
    return nested_omission_candidates(
        recs, compare_structure(recs, {"s": "nested"}), resolved,
        ancestor_diagnostics=diagnostics)


def row(result, chain="s[name=A].orcid"):
    return next(r for r in result["rows"] if r["chain"] == chain)


def test_own_holder_paths_and_multiple_receipts_count_each_row_once():
    resolved = {"r1": {"s[0]": 3}, "r2": {"s[1]": 2}, "r3": {}}
    before = deepcopy(resolved)
    got = read(resolved)
    assert row(got)["ancestor_receipts"] == [
        {"holder": "r1", "target_path": "s[0].orcid", "receipt_path": "s[0]", "snippets": 3},
        {"holder": "r2", "target_path": "s[1].orcid", "receipt_path": "s[1]", "snippets": 2}]
    assert row(got)["status"] == "not_candidate" and row(got)["ancestor_only"]
    assert row(got, "s[name=A].aff[name=UCL]")["ancestor_only"]
    assert got["ancestor_only_counts"] == {"field": 1, "entry": 1}
    commentary = row(got, "s[name=A].notes")
    assert commentary["status"] == "commentary"
    assert commentary["ancestor_receipts"] == [] and not commentary["ancestor_only"]
    assert got["per_replicate"] == {r: {"field": 0, "entry": 0} for r in records()}
    assert resolved == before
    row(got)["ancestor_receipts"][0]["snippets"] = 999
    assert resolved == before  # Returned diagnostics do not alias the supplied evidence.


@pytest.mark.parametrize("path", [
    "s", "s[1]", "s[0].or", "s[0].orcid_url", "s[0].aff", "s[0].aff[0]",
])
def test_prefix_siblings_lists_and_other_entry_paths_do_not_credit_field(path):
    got = read({"r1": {path: 1}, "r2": {}, "r3": {}})
    assert row(got)["ancestor_receipts"] == []
    assert not row(got)["ancestor_only"]


@pytest.mark.parametrize("path", ["s", "s[0].aff", "s[0].aff[0]", "s[1].aff[1]"])
def test_list_boundary_and_wrong_nested_entry_do_not_credit_entry(path):
    got = read({"r1": {path: 1}, "r2": {}, "r3": {}})
    entry = row(got, "s[name=A].aff[name=UCL]")
    assert entry["ancestor_receipts"] == [] and not entry["ancestor_only"]


@pytest.mark.parametrize("path", ["s[0].orcid", "s[0].orcid.value"])
def test_direct_or_descendant_receipt_excludes_that_holder_from_ancestor_evidence(path):
    recs = records()
    recs["r1"]["s"][0]["orcid"] = {"value": "x"}
    got = read({"r1": {"s[0]": 3, path: 1}, "r2": {"s[1]": 2}, "r3": {}}, recs=recs)
    field = row(got)
    assert field["status"] == "candidate" and not field["ancestor_only"]
    assert field["ancestor_receipts"] == [
        {"holder": "r2", "target_path": "s[1].orcid", "receipt_path": "s[1]", "snippets": 2}]
    assert got["ancestor_only_counts"] == {"field": 0, "entry": 1}
    assert got["per_replicate"]["r3"] == {"field": 1, "entry": 0}


def test_another_holders_indices_and_nonpositive_counts_do_not_create_ancestors():
    got = read({"r1": {"s[1]": 10, "s[0]": 0}, "r2": {"s[0]": 10, "s[1]": -1}, "r3": {}})
    assert got["ancestor_only_counts"] == {"field": 0, "entry": 0}
    assert all(not r["ancestor_receipts"] for r in got["rows"])


def test_unreadable_holder_keeps_unmeasured_while_readable_empty_holder_allows_subset():
    got = read({"r1": {"s[0]": 1}, "r2": None, "r3": {}})
    assert row(got)["status"] == "unmeasured" and row(got)["ancestor_receipts"]
    assert not row(got)["ancestor_only"]
    assert got["ancestor_only_counts"] == {"field": 0, "entry": 0}
    known = read({"r1": {"s[0]": 1}, "r2": {}, "r3": {}})
    assert known["ancestor_only_counts"] == {"field": 1, "entry": 1}
    unknown = read({r: None for r in records()})
    assert unknown["per_replicate"] == {r: None for r in records()}
    assert unknown["ancestor_only_counts"] == {"field": 0, "entry": 0}


def test_final_paths_are_derived_by_existing_identity_remap_and_unusable_snapshot_refuses():
    recs = records()
    snapshot = {"s": list(reversed(deepcopy(recs["r1"]["s"])))}
    resolved = resolve_verified({"s[1]": 4}, snapshot, recs["r1"])
    got = read({"r1": resolved["paths"], "r2": {}, "r3": {}}, recs=recs)
    assert row(got)["ancestor_receipts"] == [
        {"holder": "r1", "target_path": "s[0].orcid", "receipt_path": "s[0]", "snippets": 4}]
    refused = resolve_verified({"s[1]": 4}, None, recs["r1"], unusable="invalid snapshot")
    got = read({"r1": refused["paths"], "r2": {}, "r3": {}}, recs=recs)
    assert row(got)["status"] == "unmeasured" and not row(got)["ancestor_receipts"]


def test_default_machine_shape_and_all_original_values_are_unchanged():
    recs = records()
    result = compare_structure(recs, {"s": "nested"})
    resolved = {"r1": {"s[0]": 1}, "r2": None, "r3": {}}
    default = nested_omission_candidates(recs, result, resolved)
    assert json.dumps(default) == json.dumps(read(resolved, diagnostics=False))
    enriched = read(resolved)
    del enriched["ancestor_only_counts"]
    for r in enriched["rows"]:
        del r["ancestor_receipts"], r["ancestor_only"]
    assert json.dumps(enriched) == json.dumps(default)
    assert "ancestor" not in json.dumps(default)


def test_single_object_false_is_present_and_multiple_ancestors_do_not_multiply_rows():
    recs = {"r1": {"o": {"board": {"consent": False}}}, "r2": {"o": {"board": {"name": "N"}}}}
    got = nested_omission_candidates(
        recs, compare_structure(recs, {"o": "nested"}),
        {"r1": {"o": 4, "o.board": 2}, "r2": {}}, ancestor_diagnostics=True)
    field = row(got, "o.board.consent")
    assert field["held_by"] == ["r1"] and field["ancestor_only"]
    assert field["ancestor_receipts"] == [
        {"holder": "r1", "target_path": "o.board.consent", "receipt_path": "o", "snippets": 4},
        {"holder": "r1", "target_path": "o.board.consent", "receipt_path": "o.board", "snippets": 2}]
    assert got["ancestor_only_counts"] == {"field": 1, "entry": 0}


def test_report_adds_only_opt_in_diagnostic_column_and_preserves_candidate_counts(tmp_path, monkeypatch):
    recs = {"rep1": {"purposes": [{"name": "A", "orcid": "x", "aff": [{"name": "UCL"}]}]},
            "rep2": {"purposes": [{"name": "A", "aff": [{"name": "MIT"}]}]}}
    m, data = _section_fixture(tmp_path, monkeypatch, recs)
    monkeypatch.setattr(m, "_replicate_receipt", lambda label, project: (
        ({"purposes[0]": 1}, None, None) if label.endswith("rep1") else ({}, None, None)))
    default = m.nested_omission_section(data)
    assert default == m.nested_omission_section(data, ancestor_diagnostics=False)
    legacy = "| v8 API production (2026-09-04f/g) | VOICE | 1 | 0 / 1 / 0 / 0 | 2 | 0 / 2 / 0 | 0 / 0 | rep1 0 + 0 · rep2 0 + 0 |"
    assert legacy in default
    enriched = m.nested_omission_section(data, ancestor_diagnostics=True)
    assert legacy.replace("| 0 / 0 | rep1", "| 1 + 1 | 0 / 0 | rep1") in enriched
    assert any("**all projects** | 1 | 0 / 1 / 0 / 0 | 2 | 0 / 2 / 0 | 1 + 1 |" in line for line in enriched)
    assert "ancestor-only" not in "\n".join(default)
    assert "do not establish scientific support or recall" in "\n".join(enriched)
    monkeypatch.setattr(m, "_replicate_receipt", lambda label, project: (None, None, None))
    unread = "\n".join(m.nested_omission_section(data, ancestor_diagnostics=True))
    assert "| VOICE | 1 | – | 2 | – | – | 0 / 0 | – |" in unread


@pytest.mark.parametrize("extra", [[], ["--no-figures"], ["--output", "unused"],
                                    ["--no-figures", "--output", "unused", "--check"]])
def test_cli_requires_explicit_new_report_route_before_collection(monkeypatch, extra):
    m = _arm_comparison()
    monkeypatch.setattr(m, "collect", lambda: pytest.fail("invalid selection reached corpus collection"))
    monkeypatch.setattr(sys, "argv", ["arm_comparison.py", "--ancestor-receipt-diagnostics", *extra])
    with pytest.raises(SystemExit) as refusal:
        m.main()
    assert refusal.value.code == 2


def test_cli_publishes_only_new_report_and_preserves_existing_destinations(tmp_path, monkeypatch):
    m = _arm_comparison()
    monkeypatch.setattr(m, "ARMS", [])
    monkeypatch.setattr(m, "PROJECTS", [])
    monkeypatch.setattr(m, "collect", lambda: {})
    monkeypatch.setattr(m, "release_inventory_section", lambda *_: ["Synthetic release inventory", ""])
    monkeypatch.setattr(m, "write_figures", lambda *_: pytest.fail("diagnostics must not render figures"))
    historical = tmp_path / "historical.md"
    historical.write_bytes(b"historical sentinel")
    monkeypatch.setattr(m, "OUT_MD", historical)
    output = tmp_path / "new.md"
    argv = ["arm_comparison.py", "--ancestor-receipt-diagnostics", "--no-figures", "--output"]
    monkeypatch.setattr(sys, "argv", [*argv, str(output)])
    assert m.main() == 0
    published = output.read_bytes()
    assert b"Ancestor-only diagnostics (#4397)" in published
    assert historical.read_bytes() == b"historical sentinel"
    with pytest.raises(SystemExit) as refusal:
        m.main()
    assert refusal.value.code == 2 and output.read_bytes() == published
    link = tmp_path / "alias.md"
    link.symlink_to(historical)
    monkeypatch.setattr(sys, "argv", [*argv, str(link)])
    with pytest.raises(SystemExit):
        m.main()
    assert historical.read_bytes() == b"historical sentinel" and link.is_symlink()


def test_cli_combines_attainability_without_changing_default_report_or_sidecar(tmp_path, monkeypatch):
    from tests.test_attainability_aggregation import fixture

    selected, _, _, _ = fixture(tmp_path / "selection")
    m = _arm_comparison()
    monkeypatch.setattr(m, "PROJECTS", ("CHORUS",))
    monkeypatch.setattr(m, "ARMS", (("fixture", "Fictional", "fictional", "offline", "reps"),))
    monkeypatch.setattr(m, "EVAL_DIRS", {"rubric10": selected.parent})
    monkeypatch.setattr(m, "generator_model", lambda *_: None)
    data = {"fixture": {"CHORUS": []}}
    monkeypatch.setattr(m, "collect", lambda: data)
    monkeypatch.setattr(m, "release_inventory_section", lambda *_: ["Synthetic release inventory", ""])
    scores = {"rubric10": {"fixture": {"CHORUS": m.rubric_scores("fictional", "CHORUS")}}}
    default = m.render_markdown(data, scores)
    assert default == m.render_markdown(data, scores, ancestor_diagnostics=False)
    output = tmp_path / "combined.md"
    monkeypatch.setattr(sys, "argv", ["arm_comparison.py", "--ancestor-receipt-diagnostics",
                                      "--attainability-selection", str(selected),
                                      "--no-figures", "--output", str(output)])
    assert m.main() == 0
    report = output.read_text()
    assert "Ancestor-only diagnostics (#4397)" in report and "Source-supported item basis" in report
    assert output.with_name(output.name + ".attainability.json").is_file()
    assert m.render_markdown(data, scores) == default
