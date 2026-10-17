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
    align, compare_nested, compare_slot, compare_structure, dataset_slots, entry_omission_candidates,
    is_empty, nested_omission_candidates, omission_candidates, receipted_where_empty, record_chunk_texts,
    removal_status, resolve_verified, summarize, summarize_nested, top_slot, verified_by_path, verified_by_slot,
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


def test_keyed_alignment_is_one_to_one():
    """Two entries sharing a key cannot both join the one entry that carries it."""
    out = align([{"name": "A"}, {"name": "A"}], [{"name": "A"}])
    assert out["joined_by_key"] == {"name": 1}
    assert out["unaligned"] == 1


# ------------------------------------------------ omission candidates (#3335)
CHUNKS = {"c001": "The dataset includes 42 voice variables recorded per participant session.",
          "c002": "Participants were recruited at five clinical sites across North America."}


def _receipt(*pairs, status="extracted"):
    """A receipt with one entry per (chunk, slot, snippet)."""
    entries = {}
    for chunk, slot, snippet in pairs:
        entries.setdefault(chunk, {"id": chunk, "status": status, "extracted": []})["extracted"].append(
            {"slot": slot, "snippet": snippet})
    return {"bundle_md5": "x", "chunks": list(entries.values())}


def test_top_slot_reads_the_first_segment_and_drops_commentary():
    assert top_slot("variables[3].name") == "variables"
    assert top_slot("purposes") == "purposes"
    assert top_slot("human_subject_research.source_caveats") is None
    assert top_slot("source_caveats[0]") is None
    assert top_slot("variables[0].notes") is None and top_slot("notes") is None      # #3893
    assert top_slot("conforms_to_schema") is None
    assert top_slot("") is None and top_slot(None) is None


def test_commentary_keys_are_the_receipts_instruments_own_exempt_keys():
    """Imported, not copied (#3893): what the receipts instrument does not
    read as a claim is what this one does not either."""
    from data_sheets_schema import receipts
    from data_sheets_schema.replicate_structure import COMMENTARY_KEYS
    assert set(COMMENTARY_KEYS) == receipts.EXEMPT_LEAVES | receipts.EXEMPT_SLOTS
    assert {"notes", "source_caveats"} <= set(COMMENTARY_KEYS)


def test_only_a_snippet_verified_in_its_own_chunk_counts():
    """The verification `receipts.check` counts as verified: a snippet found
    only in another chunk, one below the #720 floors, an empty one and one
    citing a chunk with no text are not."""
    rec = _receipt(("c001", "variables[0].name", "42 voice variables recorded"),
                   ("c001", "variables[1]", "recorded per participant session"),
                   ("c001", "subpopulations", "five clinical sites across"),        # in c002, not c001
                   ("c002", "subpopulations", "five"),                               # too short
                   ("c002", "purposes", ""),                                         # empty
                   ("c001", "variables[2].notes", "42 voice variables recorded"),    # commentary (#3893)
                   ("c009", "splits", "five clinical sites across"),                 # no such chunk
                   ("c002", "subpopulations.source_caveats", "recruited at five clinical sites"))
    assert verified_by_slot(rec, CHUNKS) == {"variables": 2}


def test_a_malformed_receipt_entry_is_set_aside_not_raised():
    rec = {"chunks": ["not a mapping", {"id": "c001", "status": "extracted", "extracted": "nope"},
                      {"id": "c002", "status": "extracted",
                       "extracted": [{"slot": "subpopulations", "snippet": "five clinical sites across"}]}]}
    assert verified_by_slot(rec, CHUNKS) == {"subpopulations": 1}


def _intermittent():
    recs = {"rep1": {"variables": [{"name": "a"}], "splits": ["x"], "title": "T"},
            "rep2": {"variables": [{"name": "a"}], "title": "T"},
            "rep3": {"splits": ["y"], "title": "T", "purposes": "n"}}
    return compare_structure(recs, ["variables", "splits", "title", "purposes"])


def test_a_slot_receipted_in_a_replicate_that_fills_it_is_a_candidate():
    res = _intermittent()
    oc = omission_candidates(res, {"rep1": {"variables": 2}, "rep2": {}, "rep3": {"variables": 1}})
    s = oc["slots"]
    assert s["variables"] == {"status": "candidate", "filled_by": ["rep1", "rep2"],
                              "receipted_in": ["rep1"], "unreceipted": []}
    # rep3's receipt names `variables` but rep3 does not fill it: not evidence here.
    assert s["splits"]["status"] == "not_candidate" and s["purposes"]["status"] == "not_candidate"
    assert "title" not in s                                         # filled in all, not intermittent
    assert oc["per_replicate"] == {"rep1": [], "rep2": [], "rep3": ["variables"]}
    assert oc["counts"] == {"candidate": 1, "not_candidate": 2, "unmeasured": 0, "commentary": 0}


def test_a_filling_replicate_without_a_receipt_leaves_the_slot_unmeasured_not_clear():
    oc = omission_candidates(_intermittent(), {"rep1": None, "rep2": {}, "rep3": {"purposes": 1}})
    s = oc["slots"]
    # rep1 and rep2 fill `variables`; rep2's receipt verifies nothing for it, and
    # rep1 has none to read — so nothing clears it.
    assert s["variables"]["status"] == "unmeasured" and s["variables"]["unreceipted"] == ["rep1"]
    assert s["splits"]["status"] == "unmeasured"                     # rep1 and rep3 fill; rep3 verifies none
    assert s["purposes"]["status"] == "candidate"                    # one receipted filler is enough
    assert oc["measured"] and oc["per_replicate"] == {"rep1": ["purposes"], "rep2": ["purposes"], "rep3": []}
    assert oc["counts"] == {"candidate": 1, "not_candidate": 0, "unmeasured": 2, "commentary": 0}


def test_a_group_with_no_receipt_is_unmeasured_never_zero():
    oc = omission_candidates(_intermittent(), {"rep1": None, "rep2": None, "rep3": None})
    assert not oc["measured"]
    assert oc["per_replicate"] == {"rep1": None, "rep2": None, "rep3": None}
    assert oc["counts"] == {"candidate": 0, "not_candidate": 0, "unmeasured": 3, "commentary": 0}
    # A measured group with no intermittent slot is measured, with nothing omitted.
    same = compare_structure({"a": {"title": "T"}, "b": {"title": "T"}}, ["title"])
    assert omission_candidates(same, {"a": {}, "b": {}})["per_replicate"] == {"a": [], "b": []}


def test_a_group_with_receipts_is_measured_even_when_every_slot_is_unmeasured():
    """#3892: rep1 alone fills `splits` and has no receipt; rep2 and rep3
    have readable receipts. The group is measured — its row is not the `–`
    of a group with no receipt — and its one slot is counted unmeasured."""
    res = compare_structure({"rep1": {"title": "T", "splits": ["x"]}, "rep2": {"title": "T"},
                             "rep3": {"title": "T"}}, ["title", "splits"])
    oc = omission_candidates(res, {"rep1": None, "rep2": {"splits": 3}, "rep3": {}})
    assert oc["measured"]
    assert oc["slots"]["splits"]["status"] == "unmeasured"
    assert oc["per_replicate"] == {"rep1": [], "rep2": [], "rep3": []}
    assert oc["counts"] == {"candidate": 0, "not_candidate": 0, "unmeasured": 1, "commentary": 0}


def test_an_intermittent_commentary_slot_is_counted_never_a_candidate():
    """#3893: `notes` receipted in the replicate that fills it is commentary,
    not a slot the other replicates omitted; the counts still sum to the
    intermittent slots."""
    res = compare_structure({"rep1": {"title": "T", "notes": "n", "splits": ["x"]},
                             "rep2": {"title": "T"}, "rep3": {"title": "T", "conforms_to_class": "c"}},
                            ["title", "notes", "splits", "conforms_to_class"])
    oc = omission_candidates(res, {"rep1": {"notes": 2, "splits": 1}, "rep2": {}, "rep3": {}})
    assert oc["slots"]["notes"]["status"] == "commentary" and oc["slots"]["notes"]["receipted_in"] == []
    assert oc["slots"]["conforms_to_class"]["status"] == "commentary"
    assert oc["per_replicate"] == {"rep1": [], "rep2": ["splits"], "rep3": ["splits"]}
    assert oc["counts"] == {"candidate": 1, "not_candidate": 0, "unmeasured": 0, "commentary": 2}
    assert sum(oc["counts"].values()) == len(oc["slots"])


def _bundle_inputs(root, text):
    import hashlib
    from data_sheets_schema.chunking import DEFAULT_RULE, dump_manifest, manifest_from_bytes
    raw = text.encode("utf-8")
    (root / "b").mkdir(exist_ok=True)
    (root / "b" / "P_preprocessed.txt").write_bytes(raw)
    built = manifest_from_bytes(raw, "P_preprocessed.txt", DEFAULT_RULE)
    return {"bundle_path": "b/P_preprocessed.txt", "bundle_md5": hashlib.md5(raw).hexdigest(),
            "chunks": {"rule": DEFAULT_RULE, "chunk_count": built["chunk_count"],
                       "sha256": hashlib.sha256(dump_manifest(built).encode("utf-8")).hexdigest()}}


BUNDLE = ("summary\n" + "FILE: a.txt\nPATH: x/a.txt\nSIZE: 1 bytes\n" + "-" * 80 + "\nalpha text line\n"
          + "FILE: b.txt\nPATH: x/b.txt\nSIZE: 1 bytes\n" + "-" * 80 + "\nbeta text line\n")


def test_chunk_texts_come_from_the_bytes_the_record_hashed(tmp_path):
    inputs = _bundle_inputs(tmp_path, BUNDLE)
    texts, basis = record_chunk_texts(inputs, tmp_path)
    assert basis == "bundle on disk" and len(texts) == inputs["chunks"]["chunk_count"]
    assert "".join(texts.values()) == BUNDLE and any("beta text line" in t for t in texts.values())


def test_chunk_texts_are_refused_where_the_record_cannot_be_reproduced(tmp_path, monkeypatch):
    import data_sheets_schema.provenance as prov
    inputs = _bundle_inputs(tmp_path, BUNDLE)
    monkeypatch.setattr(prov, "committed_bytes_for", lambda *a, **k: None)
    for broken, why in (({"chunks": {**inputs["chunks"], "chunk_count": 99}}, "chunk count"),
                        ({"chunks": {**inputs["chunks"], "sha256": "0" * 64}}, "manifest sha256"),
                        ({"chunks": {"chunk_count": 3}}, "no chunking rule"),
                        ({"bundle_md5": "0" * 32}, "no committed version"),
                        ({"bundle_path": None}, "no bundle path")):
        texts, basis = record_chunk_texts({**inputs, **broken}, tmp_path)
        assert texts is None and why in basis, (broken, basis)


def test_drifted_bytes_are_recovered_from_the_committed_version(tmp_path, monkeypatch):
    import data_sheets_schema.provenance as prov
    inputs = _bundle_inputs(tmp_path, BUNDLE)
    (tmp_path / "b" / "P_preprocessed.txt").write_text("drifted since the run\n")
    monkeypatch.setattr(prov, "committed_bytes_for",
                        lambda path, md5=None, sha256=None: (BUNDLE.encode(), {"commit": "abc123def4567"})
                        if md5 == inputs["bundle_md5"] else None)
    texts, basis = record_chunk_texts({**inputs, "bundle_path": "b/P_preprocessed.txt"}, tmp_path / ".")
    assert basis == "git blob abc123def456" and "".join(texts.values()) == BUNDLE


def test_the_section_shows_a_dash_for_an_arm_without_receipts_and_counts_one_with(tmp_path, monkeypatch):
    m = _arm_comparison()
    monkeypatch.setattr(m, "CONCAT", tmp_path)
    monkeypatch.setattr(m, "_method_for", lambda label, project: "claudecode_api")
    recs = {"rep1": {"variables": [{"name": "a"}], "title": "T"},
            "rep2": {"variables": [{"name": "a"}], "title": "T"},
            "rep3": {"title": "T"}}
    data = {k: {p: [] for p in m.PROJECTS} for k, *_ in m.ARMS}
    for arm, prefix in (("v4", "2026-08-13_a"), ("v8prod", "2026-09-04_b")):
        for rep, rec in recs.items():
            d = tmp_path / "claudecode_api" / f"{prefix}_{rep}"
            d.mkdir(parents=True)
            (d / "VOICE_d4d.yaml").write_text(yaml.safe_dump(rec))
            data[arm]["VOICE"].append({"label": f"{prefix}_{rep}"})
    # Arm A wrote no receipt; arm B's rep1 receipts `variables`, rep2 and rep3 nothing.
    monkeypatch.setattr(m, "_replicate_verified", lambda label, project: (
        None if label.startswith("2026-08-13_a") else {"variables": 1} if label == "2026-09-04_b_rep1" else {}))
    text = "\n".join(m.omission_candidate_section(data))
    assert "| v4 API (2026-08-13) | VOICE | 1 | – | – | – |" in text
    row = next(l for l in text.splitlines() if l.startswith("| v8 API production (2026-09-04f/g) | VOICE |"))
    assert "| 1 | 1 / 0 / 0 / 0 |" in row and "`variables` (filled 2/3, receipted in rep1)" in row
    assert row.endswith("| rep1 0 · rep2 0 · rep3 1 (`variables`) |")
    assert "| **v8 API production (2026-09-04f/g)** | **all projects** | 1 | 1 / 0 / 0 / 0 | | |" in text
    assert "**v4 API (2026-08-13)** | **all projects**" not in text


def test_the_section_dashes_only_receiptless_groups_and_its_arm_total_sums(tmp_path, monkeypatch):
    """#3892: a group whose only filling replicate lacks a receipt, beside
    replicates that have one, is a full row with its slot unmeasured; a
    group with no receipt at all is `–`; and the arm's total sums the two."""
    m = _arm_comparison()
    monkeypatch.setattr(m, "CONCAT", tmp_path)
    monkeypatch.setattr(m, "_method_for", lambda label, project: "claudecode_api")
    recs = {"rep1": {"splits": ["x"], "title": "T"}, "rep2": {"title": "T"}, "rep3": {"title": "T"}}
    data = {k: {p: [] for p in m.PROJECTS} for k, *_ in m.ARMS}
    for project in ("VOICE", "CM4AI"):
        for rep, rec in recs.items():
            label = f"2026-09-04_{project}_{rep}"
            d = tmp_path / "claudecode_api" / label
            d.mkdir(parents=True)
            (d / f"{project}_d4d.yaml").write_text(yaml.safe_dump(rec))
            data["v8prod"][project].append({"label": label})
    # VOICE: rep1 (the only filler) has no receipt, rep2 and rep3 do. CM4AI: none has one.
    monkeypatch.setattr(m, "_replicate_verified", lambda label, project: (
        None if project == "CM4AI" or label.endswith("rep1") else {}))
    text = "\n".join(m.omission_candidate_section(data))
    assert "| v8 API production (2026-09-04f/g) | CM4AI | 1 | – | – | – |" in text
    assert "| v8 API production (2026-09-04f/g) | VOICE | 1 | 0 / 0 / 1 / 0 | none | rep1 0 · rep2 0 · rep3 0 |" in text
    assert "| **v8 API production (2026-09-04f/g)** | **all projects** | 2 | 0 / 0 / 2 / 0 | | |" in text


@pytest.mark.corpus
def test_receipt_verification_reproduces_every_stored_block_and_finds_the_issue_example(monkeypatch):
    """Summed over every path, commentary included, `verified_by_slot` is the
    stored block's `snippets.verified` on every checked receipt; and VOICE v7
    `variables` (#3335's example) is a candidate, receipted in rep1 and
    omitted by rep3 (rep2's only receipt for it runs through `notes`)."""
    import data_sheets_schema.replicate_structure as rs
    from data_sheets_schema.receipts import load_receipt
    m = _arm_comparison()
    monkeypatch.setattr(rs, "COMMENTARY_KEYS", ())
    n = 0
    for core in sorted(m.CONCAT.glob("*_core/*")):
        for receipt in sorted(core.glob("*_coverage_receipt.yaml")):
            project = receipt.name.split("_coverage_receipt")[0]
            prov = core / f"{project}_provenance.yaml"
            block = (yaml.safe_load(prov.read_text()) if prov.exists() else {}).get("receipts") or {}
            if not block.get("checked"):
                continue
            texts, basis = record_chunk_texts(yaml.safe_load(prov.read_text()).get("inputs") or {}, ROOT)
            assert texts is not None, (core.name, project, basis)
            got = sum(verified_by_slot(load_receipt(receipt), texts).values())
            assert got == block["snippets"]["verified"], (core.name, project)
            n += 1
    assert n >= 48
    monkeypatch.undo()
    prefix = next(pfx for key, _d, pfx, *_ in m.ARMS if key == "v7prod")
    labels = m.arm_labels(prefix)
    recs = {m._rep_tag(lab): yaml.safe_load((m.CONCAT / m._method_for(lab, "VOICE") / lab / "VOICE_d4d.yaml").read_text())
            for lab in labels}
    oc = omission_candidates(compare_structure(recs, dataset_slots()),
                             {m._rep_tag(lab): m._replicate_verified(lab, "VOICE") for lab in labels})
    assert oc["slots"]["variables"]["status"] == "candidate"
    # rep2's only `variables` receipt is `variables[0].notes`: commentary (#3893).
    assert oc["slots"]["variables"]["receipted_in"] == ["rep1"]
    assert oc["slots"]["notes"]["status"] == "commentary"
    assert oc["per_replicate"]["rep3"] and "variables" in oc["per_replicate"]["rep3"]


# ------------------------------------------- below the top level (#3337)
def _nested(recs, names=None):
    names = names or sorted({k for r in recs.values() for k in r})
    res = compare_structure(recs, names)
    return compare_nested(recs, res), res


def test_nested_paths_are_counted_under_their_join_basis():
    recs = {"r1": {"license": {"name": "CC", "url": "u"},
                   "creators": [{"name": "Ada", "orcid": "1"}, {"description": "p", "role": "x"}]},
            "r2": {"license": {"name": "CC"},
                   "creators": [{"name": "Ada", "orcid": "2"}, {"description": "q"}]}}
    nested, _ = _nested(recs)
    paths = nested["paths"]
    assert "license" not in paths and "creators" not in paths          # the top level is not repeated
    assert paths["license.name"]["by_basis"] == {"single": {"identical": 1, "differ": 0, "one_side": 0}}
    assert paths["license.url"]["by_basis"] == {"single": {"identical": 0, "differ": 0, "one_side": 1}}
    assert paths["creators[*]"]["by_basis"] == {"key": {"identical": 0, "differ": 1, "one_side": 0},
                                                "position": {"identical": 0, "differ": 1, "one_side": 0}}
    assert paths["creators[*].orcid"]["by_basis"] == {"key": {"identical": 0, "differ": 1, "one_side": 0}}
    assert paths["creators[*].role"]["by_basis"] == {"position": {"identical": 0, "differ": 0, "one_side": 1}}
    assert nested["slots"] == ["creators", "license"] and nested["pairs"] == 1


def test_a_path_takes_the_weakest_join_on_the_way_down():
    """A keyed list inside a position-joined entry is a position comparison:
    the entries above it may be two different ones."""
    recs = {"r1": {"s": [{"d": "a", "people": [{"name": "Ada", "x": 1}]}]},
            "r2": {"s": [{"d": "b", "people": [{"name": "Ada", "x": 2}]}]}}
    paths = _nested(recs)[0]["paths"]
    assert set(paths["s[*].people[*].x"]["by_basis"]) == {"position"}
    # And a keyed entry's single-object field stays keyed.
    recs = {"r1": {"s": [{"name": "A", "o": {"v": 1}}]}, "r2": {"s": [{"name": "A", "o": {"v": 2}}]}}
    assert set(_nested(recs)[0]["paths"]["s[*].o.v"]["by_basis"]) == {"key"}


def test_unpaired_entries_are_unaligned_and_not_descended():
    recs = {"r1": {"s": [{"name": "A", "deep": {"v": 1}}, {"name": "B", "deep": {"v": 1}}]},
            "r2": {"s": [{"name": "A", "deep": {"v": 1}}, {"name": "C"}]}}
    paths = _nested(recs)[0]["paths"]
    assert paths["s[*]"]["unaligned"] == 2
    assert paths["s[*].deep.v"]["by_basis"] == {"key": {"identical": 1, "differ": 0, "one_side": 0}}


def test_only_slots_filled_in_every_replicate_are_walked_and_source_caveats_is_skipped():
    recs = {"r1": {"s": {"a": 1, "source_caveats": "c"}, "t": {"a": 1}, "u": "scalar"},
            "r2": {"s": {"a": 2, "source_caveats": "d"}, "u": "scalar"},
            "r3": {"s": {"a": 1}, "u": "scalar"}}
    res = compare_structure(recs, {"s": "nested", "t": "nested", "u": "scalar"})
    nested = compare_nested(recs, res)
    assert nested["slots"] == ["s"] and nested["pairs"] == 3
    assert list(nested["paths"]) == ["s.a"]
    assert nested["paths"]["s.a"]["by_basis"]["single"] == {"identical": 1, "differ": 2, "one_side": 0}


def test_a_list_against_an_object_is_compared_not_descended():
    recs = {"r1": {"s": {"x": [{"name": "A"}]}}, "r2": {"s": {"x": {"name": "A"}}}}
    paths = _nested(recs)[0]["paths"]
    assert list(paths) == ["s.x"] and paths["s.x"]["by_basis"]["single"]["differ"] == 1


def test_summarize_nested_totals_by_basis():
    recs = {"r1": {"s": [{"name": "A", "v": 1}, {"d": 1}], "o": {"k": 1}},
            "r2": {"s": [{"name": "A"}, {"d": 2}, {"name": "Z"}], "o": {"k": 1}}}
    s = summarize_nested(_nested(recs)[0])
    assert s["compared"] == {"single": 1, "key": 3, "position": 2}
    assert s["one_side"] == {"single": 0, "key": 1, "position": 0}
    assert s["differ"] == {"single": 0, "key": 1, "position": 2}
    assert s["unaligned"] == 1 and s["paths"] == 5


def test_first_level_entry_joins_are_the_top_level_alignment():
    """At `slot[*]`, the key and position comparisons of a list slot filled in
    every replicate are the top-level table's joined entries, and its
    unaligned count theirs."""
    recs = {"r1": {"s": [{"id": "x:1"}, {"d": 1}, {"name": "B"}]},
            "r2": {"s": [{"id": "x:1"}, {"d": 2}]},
            "r3": {"s": [{"name": "B"}, {"id": "x:1"}, {"d": 1}]}}
    nested, res = _nested(recs)
    row = nested["paths"]["s[*]"]
    al = res["slots"]["s"]["alignment"]
    assert sum(row["by_basis"]["key"].values()) == sum(al["joined_by_key"].values())
    assert sum(row["by_basis"]["position"].values()) == al["joined_by_position"]
    assert row["unaligned"] == al["unaligned"]


def test_join_is_what_align_counts():
    from data_sheets_schema.replicate_structure import _join
    a = [{"name": "Ada"}, {"description": "p"}, {"name": "Bo"}, "v"]
    b = [{"name": "Bo"}, {"description": "q"}, {"name": "Cy"}, "v"]
    assert sorted(_join(a, b)) == [(1, 1, None), (2, 0, "name"), (3, 3, "value")]


# --------------------------- entry candidates and receipted-where-empty (#3880)
def test_verified_by_path_sums_to_verified_by_slot():
    rec = _receipt(("c001", "variables[0].name", "42 voice variables recorded"),
                   ("c001", "variables[1]", "recorded per participant session"),
                   ("c001", "variables[2].notes", "42 voice variables recorded"),
                   ("c002", "subpopulations", "recruited at five clinical sites"))
    assert verified_by_path(rec, CHUNKS) == {"subpopulations": 1, "variables[0].name": 1, "variables[1]": 1}
    assert verified_by_slot(rec, CHUNKS) == {"subpopulations": 1, "variables": 2}


def test_receipt_paths_follow_the_entry_by_identity_where_a_snapshot_exists():
    snapshot = {"s": [{"name": "A"}, {"name": "B"}, {"name": "C"}], "t": "x"}
    final = {"s": [{"name": "B"}, {"name": "A"}], "t": "x", "u": "added after the receipt"}
    got = resolve_verified({"s[0].name": 2, "s[2]": 1, "u": 1, "t": 1}, snapshot, final)
    # A moved; C dropped; u was never in phase 1, so a receipt on it vouches
    # for nothing even though the final record now holds a `u`.
    assert got["paths"] == {"s[1].name": 2, "t": 1}
    assert got["basis"] == {"by_name": 2, "entry_dropped": 1, "not_in_snapshot": 1, "same": 1}
    # Without a snapshot the path is read as written: an index join.
    got = resolve_verified({"s[0].name": 2, "s[5]": 1}, None, final)
    assert got["paths"] == {"s[0].name": 2} and got["basis"] == {"no_snapshot": 3}


def test_an_unusable_snapshot_is_refused_not_read_as_absent():
    """#3954: a snapshot that is present and unusable is not an absent one;
    no index join stands in for it (#1124)."""
    final = {"s": [{"name": "B"}]}
    got = resolve_verified({"s[0].name": 1, "t": 2}, None, final, unusable="the document is a list, not a mapping")
    assert got == {"paths": None, "basis": {"snapshot_unusable": 3}}


def test_an_unparseable_receipt_path_is_unresolved_with_or_without_a_snapshot():
    """#3986: `remap_path` tests the parse before the snapshot, so a path
    that is not a slot path is `unresolved`, never read as written."""
    final = {"s": [{"name": "A"}]}
    for snapshot in (None, {"s": [{"name": "A"}]}):
        got = resolve_verified({"s[0]..name": 2, "s[0].name": 1}, snapshot, final)
        assert got["paths"] == {"s[0].name": 1}
        assert got["basis"]["unresolved"] == 2



def test_structure_disagreement_is_unresolved_only_when_the_snapshot_has_the_list():
    """#3997: `remap_path`'s `unresolved` for a structural disagreement is
    one-way. A list in the snapshot where the final record has none is
    `unresolved`; an object in the snapshot where the final record has a
    list is `leaf_dropped` at a key step and `not_in_snapshot` at an index
    step. All three resolve nowhere."""
    as_list, as_object = {"s": [{"name": "A"}]}, {"s": {"name": "A"}}
    cases = [("s[0].name", as_list, as_object, "unresolved"),
             ("s.name", as_object, as_list, "leaf_dropped"),
             ("s[0].name", as_object, as_list, "not_in_snapshot")]
    for path, snapshot, final, basis in cases:
        got = resolve_verified({path: 1}, snapshot, final)
        assert got == {"paths": {}, "basis": {basis: 1}}, (path, basis)

def _entry_group():
    recs = {"r1": {"s": [{"name": "A"}, {"name": "B"}, {"description": "k"}], "t": ["x"]},
            "r2": {"s": [{"name": "A"}, {"description": "k"}], "t": ["x"]},
            "r3": {"s": [{"name": "A"}, {"name": "B"}, {"name": "C"}, {"name": "C"}], "t": ["y"]}}
    return recs, compare_structure(recs, {"s": "nested", "t": "list"})


def test_an_entry_receipted_where_it_is_held_is_a_candidate_and_keyless_entries_are_not_classified():
    recs, res = _entry_group()
    # r1 receipts B (its s[1]); r3 receipts only the list itself and its first C.
    eo = entry_omission_candidates(recs, res, {"r1": {"s[1].name": 1}, "r2": {}, "r3": {"s": 3, "s[2]": 1}})
    by_key = {e["key"]: e for e in eo["entries"]}
    assert set(by_key) == {"name=B", "name=C", "name=C (#2)"}      # A is in all three
    assert by_key["name=B"]["status"] == "candidate" and by_key["name=B"]["receipted_in"] == ["r1"]
    assert by_key["name=C"]["status"] == "candidate"
    assert by_key["name=C (#2)"]["status"] == "not_candidate"        # a receipt on the list covers only the list
    assert eo["keyless"] == 2 and eo["measured"]
    assert eo["per_replicate"] == {"r1": 1, "r2": 2, "r3": 0}
    assert eo["counts"] == {"candidate": 2, "not_candidate": 1, "unmeasured": 0}


def test_a_receipt_on_entry_ten_does_not_credit_entry_one():
    """#3986: `s[10]` is not below `s[1]`. The entry string carries its
    closing bracket, so the boundary holds; a test that drops it (matching on
    `s[1`) credits E1 with E10's receipt."""
    full = [{"name": f"E{i}"} for i in range(11)]
    recs = {"r1": {"s": full}, "r2": {"s": [e for e in full if e["name"] != "E1"]}}
    res = compare_structure(recs, {"s": "nested"})
    eo = entry_omission_candidates(recs, res, {"r1": {"s[10].name": 1}, "r2": {}})
    assert {e["key"]: e["status"] for e in eo["entries"]} == {"name=E1": "not_candidate"}
    eo = entry_omission_candidates(recs, res, {"r1": {"s[1].name": 1}, "r2": {}})
    assert {e["key"]: e["status"] for e in eo["entries"]} == {"name=E1": "candidate"}


def test_entry_candidates_without_receipts_are_unmeasured():
    recs, res = _entry_group()
    eo = entry_omission_candidates(recs, res, {"r1": None, "r2": {}, "r3": {}})
    assert {e["key"]: e["status"] for e in eo["entries"]}["name=B"] == "unmeasured"
    eo = entry_omission_candidates(recs, res, {"r1": None, "r2": None, "r3": None})
    assert not eo["measured"] and eo["per_replicate"] == {"r1": None, "r2": None, "r3": None}


# ------------------------------- fields and nested list entries (#3934)
def _deep_group():
    """Three replicates with structure below the first level: a keyed list
    whose shared entries hold a nested list of objects (one keyless), a
    nested list of values and an object; a top-level keyless entry with a
    list inside it; a key repeated within one list; a string entry in that
    class-ranged list, in r1 only (#4437); a slot holding one object; a slot
    that is a list in two replicates and an object in the third, whose
    entry carries a field in r1 that the others' do not (#4436); a
    top-level list of values and an intermittent slot."""
    recs = {
        "r1": {"s": [{"name": "A", "affiliations": [{"name": "MIT"}, {"name": "UCL"}, {"role": "k"}], "orcid": "o1",
                      "roles": ["lead", "writing"]},
                     {"name": "B"},
                     {"description": "keyless", "x": [{"name": "Q"}]},
                     {"id": "x:1", "license": {"name": "CC", "url": "u"}},
                     {"name": "D"}, {"name": "D"}, {"name": "E"}, "S1"],
               "o": {"irb": "yes", "board": {"name": "IRB-1", "notes": "n"}, "source_caveats": "c"},
               "m": [{"name": "Z", "role": "chair"}], "t": ["k1", "k2"], "u": [{"name": "U"}]},
        "r2": {"s": [{"name": "A", "affiliations": [{"name": "MIT"}], "roles": ["lead"]},
                     {"description": "keyless", "x": [{"name": "R"}]},
                     {"id": "x:1", "license": {"name": "CC"}},
                     {"name": "D"}, {"name": "E"}],
               "o": {"irb": "yes", "board": {"name": "IRB-1"}},
               "m": {"name": "Z"}, "t": ["k1"]},
        "r3": {"s": [{"name": "B"},
                     {"name": "A", "affiliations": [{"name": "UCL"}, {"name": "MIT"}], "orcid": "o3",
                      "roles": ["writing", "lead"]},
                     {"id": "x:1", "license": {"name": "CC", "url": "u"}},
                     {"name": "D"}, {"name": "D"}, {"name": "D"}],
               "o": {"board": {"name": "IRB-1"}},
               "m": [{"name": "Z"}], "t": ["k2"]},
    }
    return recs, compare_structure(recs, {"s": "nested", "o": "nested", "m": "nested", "t": "list", "u": "nested"})


#: Verified receipt paths, resolved into each replicate's final record. r1
#: receipts entry B, its string entry "S1", A's UCL affiliation and x:1's
#: licence url — and also the list `s`, a zero count on D's second entry,
#: A's value "writing", a sibling key of `o.irb` and the object `o` above
#: it, none of which credits a node. r2's receipt verifies nothing; r3 has
#: none to read.
DEEP_RESOLVED = {"r1": {"s": 2, "s[1].name": 1, "s[5]": 0, "s[0].affiliations[1].name": 1,
                        "s[0].roles[1]": 1, "s[3].license.url": 1, "s[7]": 1, "o.irb_date": 1, "o": 1},
                 "r2": {}, "r3": None}


def test_the_first_level_entry_reading_is_unchanged_by_the_nested_one():
    """The output of `entry_omission_candidates` as main produced it before
    #3934, on a group with structure below its first level: the nested
    reading neither moves a first-level row nor adds one. The literal was
    produced by origin/main's module (bc1f41d69) on this fixture. Its
    string entry "S1" is the one input the shared `_keyed`'s `objects_only`
    switch reads differently: main keys it by its text and classifies it
    (`value=S1`), and the first level must still do so (#4437)."""
    recs, res = _deep_group()
    assert entry_omission_candidates(recs, res, DEEP_RESOLVED) == {
        "entries": [
            {"slot": "s", "key": "name=B", "held_by": ["r1", "r3"], "receipted_in": ["r1"],
             "unreceipted": ["r3"], "status": "candidate"},
            {"slot": "s", "key": "name=D (#2)", "held_by": ["r1", "r3"], "receipted_in": [],
             "unreceipted": ["r3"], "status": "unmeasured"},
            {"slot": "s", "key": "name=E", "held_by": ["r1", "r2"], "receipted_in": [],
             "unreceipted": [], "status": "not_candidate"},
            {"slot": "s", "key": "value=S1", "held_by": ["r1"], "receipted_in": ["r1"],
             "unreceipted": [], "status": "candidate"},
            {"slot": "s", "key": "name=D (#3)", "held_by": ["r3"], "receipted_in": [],
             "unreceipted": ["r3"], "status": "unmeasured"}],
        "keyless": 2, "measured": True, "per_replicate": {"r1": 0, "r2": 2, "r3": 1},
        "counts": {"candidate": 2, "not_candidate": 1, "unmeasured": 2}}


def test_nested_rows_are_the_fields_of_held_objects_and_the_entries_of_nested_lists():
    """Below A (held by all three) its UCL affiliation is in r1 and r3, and
    its `orcid` filled in r1 and r3; x:1's licence url likewise; the single
    object `o` has `irb` in r1 and r2 and its board's `notes` in r1 only.
    A's `roles` are values, counted and never classified, although
    "writing" is in r1 and r3 only and r1 receipts it. Nothing is read
    below the keyless entry, below B or the string entry "S1" (first-level
    rows), in `m` (a list and an object: its `role`, in r1 only, would be a
    row if the walk read through the disagreement, #4436), in the top-level
    value list `t` or in `u`."""
    recs, res = _deep_group()
    got = nested_omission_candidates(recs, res, DEEP_RESOLVED)
    rows = {r["chain"]: r for r in got["rows"]}
    assert [(r["kind"], r["path"], r["basis"], r["status"]) for r in got["rows"]] == [
        ("entry", "s[*].affiliations[*]", "key", "candidate"),
        ("field", "s[*].orcid", "key", "unmeasured"),
        ("field", "s[*].license.url", "key", "candidate"),
        ("field", "o.board.notes", "single", "commentary"),
        ("field", "o.irb", "single", "not_candidate")]
    assert list(rows) == ["s[name=A].affiliations[name=UCL]", "s[name=A].orcid", "s[id=x:1].license.url",
                          "o.board.notes", "o.irb"]
    assert rows["s[name=A].affiliations[name=UCL]"] == {
        "kind": "entry", "path": "s[*].affiliations[*]", "chain": "s[name=A].affiliations[name=UCL]",
        "basis": "key", "held_by": ["r1", "r3"], "receipted_in": ["r1"], "unreceipted": ["r3"],
        "status": "candidate"}
    # `o.irb`: r1's receipts on `o.irb_date` and on `o` do not credit it, and
    # both holders have a readable receipt, so it is not a candidate.
    assert rows["o.irb"]["held_by"] == ["r1", "r2"] and rows["o.irb"]["receipted_in"] == []
    assert got["keyless"] == 1                       # A's `{role: k}`; the first level's two are the entry table's
    assert got["values"] == 5                        # A's roles: 2 + 1 + 2
    assert got["measured"]
    assert got["per_replicate"] == {"r1": {"field": 0, "entry": 0}, "r2": {"field": 1, "entry": 1},
                                    "r3": {"field": 0, "entry": 0}}
    assert got["counts"] == {"field": {"candidate": 1, "not_candidate": 1, "unmeasured": 1, "commentary": 1},
                             "entry": {"candidate": 1, "not_candidate": 0, "unmeasured": 0, "commentary": 0}}
    # The two readings are disjoint: no nested row is a first-level entry,
    # and none is read through `m`'s list/object disagreement.
    assert not {r["path"] for r in got["rows"]} & {"s[*]", "m[*]", "u[*]"}
    assert not [r for r in got["rows"] if r["path"].startswith("m")]


def test_a_value_in_a_nested_list_is_counted_never_classified():
    """A string entry's only identity is its text, so one replicate's
    rewording of another's item would read as two items, each missing from
    the other: below the first level, values are counted and never
    classified. The list's own presence is still a field — `irb` here, the
    shape of #3934's `human_subject_research.irb_approval` example."""
    recs = {"r1": {"o": {"versions": ["v1.1, published 2025-01-17", "v2.0.0"], "irb": ["Approved by the IRB"]}},
            "r2": {"o": {"versions": ["1.1 (17 January 2025)", "v2.0.0"]}}}
    res = compare_structure(recs, {"o": "nested"})
    got = nested_omission_candidates(recs, res, {"r1": {"o.versions[0]": 1, "o.irb[0]": 1}, "r2": {}})
    assert [(r["kind"], r["chain"], r["held_by"], r["status"]) for r in got["rows"]] == [
        ("field", "o.irb", ["r1"], "candidate")]
    assert got["values"] == 4 and got["keyless"] == 0
    assert got["per_replicate"] == {"r1": {"field": 0, "entry": 0}, "r2": {"field": 1, "entry": 0}}


def test_a_receipt_credits_a_nested_node_only_through_its_own_chain():
    """A is r1's `s[0]` and r2's `s[1]`, and r2's `s[0]` is B: a receipt
    path credits a node only at that node's own path in the replicate that
    wrote it, on the node or below it — never on a list holding it (#721),
    the entry or object above it, a sibling sharing its prefix, another
    entry's field of the same name, or the node's index in another
    replicate."""
    recs = {"r1": {"s": [{"name": "A", "aff": [{"name": "MIT"}]}, {"name": "B", "orcid": "b"}]},
            "r2": {"s": [{"name": "B", "orcid": "b"},
                         {"name": "A", "orcid": "a", "aff": [{"name": "MIT"}, {"name": "UCL"}]}]}}
    res = compare_structure(recs, {"s": "nested"})

    def status(r2_paths, chain):
        rows = nested_omission_candidates(recs, res, {"r1": {}, "r2": r2_paths})["rows"]
        return next(r["status"] for r in rows if r["chain"] == chain)

    for path in ("s", "s[1]", "s[0].orcid", "s[1].orcid_url", "s[1].aff"):
        assert status({path: 1}, "s[name=A].orcid") == "not_candidate", path
    assert status({"s[1].orcid": 1}, "s[name=A].orcid") == "candidate"
    for path in ("s[1].aff", "s[1].aff[0].name", "s[0].aff[1]"):
        assert status({path: 1}, "s[name=A].aff[name=UCL]") == "not_candidate", path
    for path in ("s[1].aff[1]", "s[1].aff[1].name"):
        assert status({path: 1}, "s[name=A].aff[name=UCL]") == "candidate", path


def test_a_receipt_at_another_holders_path_for_a_nested_node_credits_nothing():
    """#4435: A's `orcid` has two holders at different indices — r1's
    `s[0]` and r2's `s[1]` — and B's the reverse. Each holder receipts B's
    `orcid` at its own index for B, which is the other holder's index for
    A: that credits B's `orcid`, never A's. On v6 agentic VOICE an
    affiliation held at `creators[6].affiliations[0]` in rep1 and at
    `creators[8].affiliations[0]` in rep2, with rep2's verified receipt at
    `creators[6].affiliations[0].description`, is this case."""
    recs = {"r1": {"s": [{"name": "A", "orcid": "a"}, {"name": "B", "orcid": "b"}]},
            "r2": {"s": [{"name": "B", "orcid": "b"}, {"name": "A", "orcid": "a"}]},
            "r3": {"s": [{"name": "A"}, {"name": "B"}]}}
    res = compare_structure(recs, {"s": "nested"})

    def rows(resolved):
        got = nested_omission_candidates(recs, res, resolved)
        return {r["chain"]: (r["held_by"], r["receipted_in"], r["status"]) for r in got["rows"]}, got

    got_rows, got = rows({"r1": {"s[1].orcid": 1}, "r2": {"s[0].orcid": 1}, "r3": {}})
    assert got_rows == {"s[name=A].orcid": (["r1", "r2"], [], "not_candidate"),
                        "s[name=B].orcid": (["r1", "r2"], ["r1", "r2"], "candidate")}
    assert got["per_replicate"]["r3"] == {"field": 1, "entry": 0}
    # Each holder's receipt at its own path for A credits A.
    for resolved, by in (({"r1": {"s[0].orcid": 1}, "r2": {}, "r3": {}}, ["r1"]),
                         ({"r1": {}, "r2": {"s[1].orcid": 1}, "r3": {}}, ["r2"])):
        assert rows(resolved)[0]["s[name=A].orcid"] == (["r1", "r2"], by, "candidate"), resolved


def test_a_receipt_at_another_holders_index_for_a_first_level_entry_credits_nothing():
    """#4435, at the first level, which shares `_status`: B is r1's `s[1]`
    and r3's `s[0]`, and r2 lacks it. r1's receipt on its A (`s[0]`) and
    r3's on its A (`s[1]`) each sit at the other holder's index for B and
    credit nothing; r3's at its own index for B credits B."""
    recs = {"r1": {"s": [{"name": "A", "x": "a"}, {"name": "B", "x": "b"}]},
            "r2": {"s": [{"name": "A", "x": "a"}]},
            "r3": {"s": [{"name": "B", "x": "b"}, {"name": "A", "x": "a"}]}}
    res = compare_structure(recs, {"s": "nested"})

    def entries(resolved):
        return {e["key"]: (e["held_by"], e["receipted_in"], e["status"])
                for e in entry_omission_candidates(recs, res, resolved)["entries"]}

    assert entries({"r1": {"s[0].x": 1}, "r2": {}, "r3": {"s[1].x": 1}}) == {
        "name=B": (["r1", "r3"], [], "not_candidate")}
    assert entries({"r1": {}, "r2": {}, "r3": {"s[0].x": 1}}) == {"name=B": (["r1", "r3"], ["r3"], "candidate")}


def test_nothing_is_read_below_a_keyless_entry_a_partly_held_entry_or_a_shape_disagreement():
    """A keyless entry is joined by position, no evidence of identity
    (#908); B, held by r1 and r2 and not r3, is a first-level row, with no
    identity across every replicate below it, although its two holders
    disagree on UCL; a list in one replicate and an object in another has
    none either. Receipts on all three credit nothing: there is no row.

    The disagreeing values differ below it (#4436): Q carries `role` in r1
    only, so a walk that read through the disagreement — wrapping r2's
    object as a one-entry list, or unwrapping the one-entry lists — would
    find a `role` field some replicates lack; one that iterated r2's
    object as a list would meet its key as a value. `o.r` is a list in two
    replicates and a string in the third: reading it as a list would count
    values."""
    recs = {"r1": {"s": [{"d": "x", "aff": [{"name": "MIT"}]},
                         {"name": "B", "aff": [{"name": "MIT"}, {"name": "UCL"}]}],
                   "o": {"p": [{"name": "Q", "role": "chair"}], "q": "v", "r": ["w"]}},
            "r2": {"s": [{"d": "y", "aff": [{"name": "UCL"}]}, {"name": "B", "aff": [{"name": "MIT"}]}],
                   "o": {"p": {"name": "Q"}, "q": "v", "r": "w"}},
            "r3": {"s": [{"d": "z"}], "o": {"p": [{"name": "Q"}], "q": "v", "r": ["w"]}}}
    res = compare_structure(recs, {"s": "nested", "o": "nested"})
    got = nested_omission_candidates(recs, res, {"r1": {"s[0].aff[0]": 1, "s[1].aff[1]": 1, "o.p[0]": 1,
                                                        "o.p[0].role": 1, "o.p.role": 1},
                                                 "r2": {"s[0].aff[0]": 1, "o.p": 1}, "r3": {}})
    assert got["rows"] == [] and got["keyless"] == 0 and got["values"] == 0
    assert got["per_replicate"] == {r: {"field": 0, "entry": 0} for r in ("r1", "r2", "r3")}


def test_nested_candidates_without_receipts_are_unmeasured_never_zero():
    recs, res = _deep_group()
    got = nested_omission_candidates(recs, res, {"r1": None, "r2": {}, "r3": None})
    assert {r["chain"]: r["status"] for r in got["rows"]} == {
        "s[name=A].affiliations[name=UCL]": "unmeasured", "s[name=A].orcid": "unmeasured",
        "s[id=x:1].license.url": "unmeasured", "o.board.notes": "commentary", "o.irb": "unmeasured"}
    got = nested_omission_candidates(recs, res, {"r1": None, "r2": None, "r3": None})
    assert not got["measured"] and got["per_replicate"] == {"r1": None, "r2": None, "r3": None}
    assert got["counts"]["field"] == {"candidate": 0, "not_candidate": 0, "unmeasured": 3, "commentary": 1}


def test_only_the_receipts_instruments_exempt_keys_are_nested_commentary():
    """#4434: `conforms_to_standard` and `conforms_to` match the wildcard
    `conforms_to_*` but carry facts from the bundle, and the receipts
    instrument does not exempt them, so a nested one is classified like any
    other field — here a candidate r3 omits. `conforms_to_class` beside it
    is commentary, receipt or not, and `source_caveats` is skipped."""
    recs = {"r1": {"resources": [{"id": "x:1", "conforms_to_standard": "OMOP", "conforms_to": "DICOM",
                                  "conforms_to_class": "Dataset", "source_caveats": "c"}]},
            "r2": {"resources": [{"id": "x:1", "conforms_to_standard": "OMOP", "conforms_to": "DICOM",
                                  "conforms_to_class": "Dataset"}]},
            "r3": {"resources": [{"id": "x:1"}]}}
    res = compare_structure(recs, {"resources": "nested"})
    got = nested_omission_candidates(recs, res, {
        "r1": {"resources[0].conforms_to_standard": 1, "resources[0].conforms_to_class": 1,
               "resources[0].source_caveats": 1}, "r2": {}, "r3": {}})
    assert {r["chain"]: (r["held_by"], r["status"]) for r in got["rows"]} == {
        "resources[id=x:1].conforms_to": (["r1", "r2"], "not_candidate"),
        "resources[id=x:1].conforms_to_class": (["r1", "r2"], "commentary"),
        "resources[id=x:1].conforms_to_standard": (["r1", "r2"], "candidate")}
    assert got["per_replicate"]["r3"] == {"field": 1, "entry": 0}


def test_a_nested_entry_is_identified_by_its_key_as_entry_key_reads_it():
    """#4439: a keyed identity is the key's value as `receipts._entry_key`
    reads it, not its exact text: a resolver URL of a declared prefix is
    its CURIE (`https://doi.org/…` and `doi:…`) and surrounding whitespace
    is stripped, so the three replicates hold one affiliation. Nothing else
    is normalised: a DOI suffix in another case is another entry."""
    def rows(r3_id):
        recs = {"r1": {"s": [{"name": "A", "aff": [{"id": "https://doi.org/10.13026/abc"}]}]},
                "r2": {"s": [{"name": "A", "aff": [{"id": "doi:10.13026/abc"}]}]},
                "r3": {"s": [{"name": "A", "aff": [{"id": r3_id}]}]}}
        got = nested_omission_candidates(recs, compare_structure(recs, {"s": "nested"}),
                                         {"r1": {}, "r2": {}, "r3": {}})
        return [(r["chain"], r["held_by"]) for r in got["rows"]]

    assert rows(" doi:10.13026/abc ") == []
    assert rows("HTTPS://DOI.ORG/10.13026/abc") == []
    assert rows("doi:10.13026/ABC") == [("s[name=A].aff[id=doi:10.13026/abc]", ["r1", "r2"]),
                                        ("s[name=A].aff[id=doi:10.13026/ABC]", ["r3"])]


def test_receipted_where_empty_lists_replicates_that_leave_a_slot_empty_and_receipt_it():
    recs = {"r1": {"a": "x", "b": ["y"]}, "r2": {"b": ["y"]}, "r3": {"b": ["z"]}}
    res = compare_structure(recs, ["a", "b", "c", "notes"])
    got = receipted_where_empty(res, {"r1": {"a": 1}, "r2": {"a": 2, "b": 1, "c": 1, "notes": 4},
                                      "r3": None})
    assert got == {"a": ["r2"], "c": ["r2"]}          # b is filled in all; notes is commentary; r3 has no receipt


def test_removal_status_reads_the_removals_rows():
    block = {"checked": True, "flattened_paths": [{"path": "a[0].x"}], "unfounded_paths": [{"path": "b"}],
             "founded_paths": [{"path": "ab"}, {"path": "a[1]"}]}
    assert removal_status(block, "a") == "deleted"
    assert removal_status({"checked": True, "flattened_paths": [{"path": "a.x"}]}, "a") == "flattened"
    assert removal_status(block, "b") == "deleted"
    assert removal_status(block, "c") == "no removal row"
    assert removal_status({**block, "unsorted_paths_truncated": 3}, "c") == "rows truncated"
    assert removal_status({"checked": False}, "a") == "removals unchecked"
    assert removal_status(None, "a") == "removals unchecked"


def test_removal_status_does_not_read_a_longer_slot_name_as_below_the_slot():
    """#3986: a row for `ab` (or `ab[0]`, `ab.x`) is not a row for `a`; the
    decoy in the test above cannot show it, since `a[1]` is deleted too."""
    for path in ("ab", "ab[0]", "ab.x"):
        block = {"checked": True, "founded_paths": [{"path": path}]}
        assert removal_status(block, "a") == "no removal row"
        assert removal_status(block, "ab") == "deleted"
    assert removal_status({"checked": True, "flattened_paths": [{"path": "ab.x"}]}, "a") == "no removal row"


def _section_fixture(tmp_path, monkeypatch, recs, arm="v8prod", project="VOICE"):
    m = _arm_comparison()
    monkeypatch.setattr(m, "CONCAT", tmp_path)
    monkeypatch.setattr(m, "_method_for", lambda label, project: "claudecode_api")
    data = {k: {p: [] for p in m.PROJECTS} for k, *_ in m.ARMS}
    for rep, rec in recs.items():
        d = tmp_path / "claudecode_api" / f"2026-09-04_x_{rep}"
        d.mkdir(parents=True)
        (d / f"{project}_d4d.yaml").write_text(yaml.safe_dump(rec))
        data[arm][project].append({"label": f"2026-09-04_x_{rep}"})
    return m, data


def test_the_nested_section_prints_counts_by_basis(tmp_path, monkeypatch):
    recs = {"rep1": {"purposes": [{"response": "a", "x": 1}], "updates": {"name": "CC"}},
            "rep2": {"purposes": [{"response": "b"}], "updates": {"name": "CC", "url": "u"}}}
    m, data = _section_fixture(tmp_path, monkeypatch, recs)
    text = "\n".join(m.nested_structure_section(data))
    row = next(l for l in text.splitlines() if l.startswith("| v8 API production (2026-09-04f/g) | VOICE |"))
    # purposes[*] (position), .response (position), .x (position, one side); updates.name, .url (single).
    assert row == "| v8 API production (2026-09-04f/g) | VOICE | 2 | 5 | 2 / 0 / 3 | 1 / 0 / 1 | 0 / 0 / 2 | 0 |"
    assert "| **v8 API production (2026-09-04f/g)** | **all projects** | | | 2 / 0 / 3 | 1 / 0 / 1 | 0 / 0 / 2 | 0 |" in text
    assert "`updates.url` 1 (single 1)" in text and "`purposes[*].x` 1 (position 1)" in text


def test_the_entry_section_dashes_a_group_without_receipts(tmp_path, monkeypatch):
    recs = {"rep1": {"purposes": [{"name": "A"}, {"name": "B"}]}, "rep2": {"purposes": [{"name": "A"}]}}
    m, data = _section_fixture(tmp_path, monkeypatch, recs)
    monkeypatch.setattr(m, "_replicate_receipt", lambda label, project: (None, None, None))
    text = "\n".join(m.entry_omission_section(data))
    assert "| v8 API production (2026-09-04f/g) | VOICE | 1 | – | 0 | – | – |" in text
    assert "**all projects**" not in text
    monkeypatch.setattr(m, "_replicate_receipt", lambda label, project: (
        ({"purposes[1].name": 1}, None, None) if label.endswith("rep1") else ({}, None, None)))
    text = "\n".join(m.entry_omission_section(data))
    assert "| v8 API production (2026-09-04f/g) | VOICE | 1 | 1 / 0 / 0 | 0 | no_snapshot 1 | rep1 0 · rep2 1 |" in text
    # The same receipt beside an unusable snapshot (#3954): not read by
    # index, so the only holder has no readable receipt for the entry.
    monkeypatch.setattr(m, "_replicate_receipt", lambda label, project: (
        ({"purposes[1].name": 1}, None, "empty document") if label.endswith("rep1") else ({}, None, None)))
    text = "\n".join(m.entry_omission_section(data))
    assert "| v8 API production (2026-09-04f/g) | VOICE | 1 | 0 / 0 / 1 | 0 | snapshot_unusable 1 | rep1 0 · rep2 0 |" in text


def test_the_nested_section_counts_fields_and_nested_entries_and_dashes_a_group_without_receipts(
        tmp_path, monkeypatch):
    """#3934: below shared entry A, its UCL affiliation is in rep1 only and
    its roles are values (one in rep1, two in rep2: counted, not rows); in
    the single object `updates`, `url`, `version` and `notes` (commentary)
    are in rep1 only."""
    recs = {"rep1": {"purposes": [{"name": "A", "aff": [{"name": "MIT"}, {"name": "UCL"}], "roles": ["lead"]}],
                     "updates": {"name": "CC", "url": "u", "version": "v1", "notes": "n"}},
            "rep2": {"purposes": [{"name": "A", "aff": [{"name": "MIT"}], "roles": ["lead", "x"]}],
                     "updates": {"name": "CC"}}}
    m, data = _section_fixture(tmp_path, monkeypatch, recs)
    monkeypatch.setattr(m, "_replicate_receipt", lambda label, project: (None, None, None))
    text = "\n".join(m.nested_omission_section(data))
    assert "| v8 API production (2026-09-04f/g) | VOICE | 3 | – | 1 | – | 0 / 3 | – |" in text
    assert "**all projects**" not in text and "| – | none |" in text
    receipt = {"purposes[0].aff[1].name": 1, "updates.url": 1, "updates.version": 2}
    monkeypatch.setattr(m, "_replicate_receipt", lambda label, project: (
        (receipt, None, None) if label.endswith("rep1") else ({}, None, None)))
    text = "\n".join(m.nested_omission_section(data))
    assert ("| v8 API production (2026-09-04f/g) | VOICE | 3 | 2 / 0 / 0 / 1 | 1 | 1 / 0 / 0 | 0 / 3 | "
            "rep1 0 + 0 · rep2 2 + 1 |") in text
    assert ("| **v8 API production (2026-09-04f/g)** | **all projects** | 3 | 2 / 0 / 0 / 1 | 1 | 1 / 0 / 0 | "
            "0 / 3 | |") in text
    assert ("| v8 API production (2026-09-04f/g) | `purposes[*].aff[*]` 1, `updates.url` 1, "
            "`updates.version` 1 |") in text
    # Beside an unusable snapshot (#3954) rep1's receipt is not read by
    # index: the only holder has no readable receipt, so all are unmeasured.
    monkeypatch.setattr(m, "_replicate_receipt", lambda label, project: (
        (receipt, None, "empty document") if label.endswith("rep1") else ({}, None, None)))
    text = "\n".join(m.nested_omission_section(data))
    assert ("| v8 API production (2026-09-04f/g) | VOICE | 3 | 0 / 0 / 2 / 1 | 1 | 0 / 0 / 1 | 0 / 3 | "
            "rep1 0 + 0 · rep2 0 + 0 |") in text


def test_the_nested_section_names_the_commentary_keys_the_walk_reads(tmp_path, monkeypatch):
    """#4434: the legend names the keys the walk reads as commentary — the
    receipts instrument's exempt keys less `EXCLUDED_SLOTS`, which it skips
    — from the code, never the wildcard `conforms_to_*`, which
    `conforms_to_standard` matches and the walk classifies. #4439: it says
    a keyed identity is the key's value as `receipts._entry_key` reads it,
    not its exact value."""
    from data_sheets_schema.replicate_structure import COMMENTARY_KEYS, EXCLUDED_SLOTS
    m, data = _section_fixture(tmp_path, monkeypatch, {"rep1": {"purposes": [{"name": "A"}]},
                                                       "rep2": {"purposes": [{"name": "A"}]}})
    monkeypatch.setattr(m, "_replicate_receipt", lambda label, project: (None, None, None))
    legend = m.nested_omission_section(data)[2]
    commentary = ", ".join(f"`{k}`" for k in COMMENTARY_KEYS if k not in EXCLUDED_SLOTS)
    assert f"({commentary}) is **commentary**" in legend
    assert ", ".join(f"`{k}`" for k in EXCLUDED_SLOTS) + " is skipped at any depth" in legend
    assert "conforms_to_*" not in legend
    assert "that key's value as `receipts._entry_key` reads it" in legend and "exact value" not in legend


def test_replicate_receipt_tells_an_unusable_snapshot_from_an_absent_one(tmp_path, monkeypatch):
    """#3954: `_replicate_receipt` reads `phase1_snapshot_state`, so a
    snapshot file that parses to a list is reported unusable, not absent."""
    import data_sheets_schema.receipts as receipts
    import data_sheets_schema.replicate_structure as rs
    m = _arm_comparison()
    monkeypatch.setattr(m, "CONCAT", tmp_path)
    monkeypatch.setattr(m, "_method_for", lambda label, project: "claudecode_api")
    monkeypatch.setattr(m, "_RECEIPT_CACHE", {})
    monkeypatch.setattr(receipts, "load_receipt", lambda path: {"chunks": []})
    monkeypatch.setattr(rs, "record_chunk_texts", lambda inputs, root: ({"c001": "x"}, "bundle on disk"))
    monkeypatch.setattr(rs, "verified_by_path", lambda rec, texts: {"s[0].name": 1})
    for label, snap in (("L_absent", None), ("L_list", "- a\n"), ("L_ok", "s: [{name: A}]\n")):
        d = tmp_path / "claudecode_api_core" / label
        (d / "intermediate").mkdir(parents=True)
        (d / "VOICE_coverage_receipt.yaml").write_text("chunks: []\n")
        (d / "VOICE_provenance.yaml").write_text("run: {project: VOICE}\ninputs: {}\n")
        if snap is not None:
            (d / "intermediate" / "VOICE_full.yaml").write_text(snap)
    assert m._replicate_receipt("L_absent", "VOICE") == ({"s[0].name": 1}, None, None)
    paths, snapshot, why = m._replicate_receipt("L_list", "VOICE")
    assert paths == {"s[0].name": 1} and snapshot is None and why and "list" in why
    assert m._replicate_receipt("L_ok", "VOICE") == ({"s[0].name": 1}, {"s": [{"name": "A"}]}, None)


def test_the_receipted_where_empty_section_cross_references_removals(tmp_path, monkeypatch):
    import data_sheets_schema.removals as removals
    recs = {"rep1": {"splits": ["x"]}, "rep2": {"title": "T"}}
    m, data = _section_fixture(tmp_path, monkeypatch, recs)
    for rep in recs:
        d = tmp_path / "claudecode_api_core" / f"2026-09-04_x_{rep}"
        d.mkdir(parents=True)
        (d / "VOICE_provenance.yaml").write_text("{}\n")
    monkeypatch.setattr(m, "_replicate_verified", lambda label, project: {"splits": 2} if label.endswith("rep2") else {})
    monkeypatch.setattr(removals, "for_record", lambda prov, record=None: {
        "checked": True, "unfounded_paths": [{"path": "splits[0]"}]})
    text = "\n".join(m.receipted_where_empty_section(data))
    assert "| v8 API production (2026-09-04f/g) | VOICE | 1 | `splits` (filled 1/2; rep2 2, deleted) |" in text
    assert ("Receipting replicates by removals status (distinct arm × project × replicate; one with slots "
            "of two statuses is counted under each): deleted 1. Slot × replicate instances by removals "
            "status: deleted 1.") in text


def test_the_receipted_where_empty_total_counts_replicates_not_slot_instances(tmp_path, monkeypatch):
    """#3955: one replicate receipting three slots it leaves empty is one
    replicate and three slot instances; a second status counts it again."""
    import data_sheets_schema.removals as removals
    recs = {"rep1": {"splits": ["x"], "subsets": ["y"], "title": "T"}, "rep2": {"license": "L"}}
    m, data = _section_fixture(tmp_path, monkeypatch, recs)
    for rep in recs:
        d = tmp_path / "claudecode_api_core" / f"2026-09-04_x_{rep}"
        d.mkdir(parents=True)
        (d / "VOICE_provenance.yaml").write_text("{}\n")
    monkeypatch.setattr(m, "_replicate_verified", lambda label, project: (
        {"splits": 1, "subsets": 1, "title": 1} if label.endswith("rep2") else {}))
    monkeypatch.setattr(removals, "for_record", lambda prov, record=None: {
        "checked": True, "unfounded_paths": [{"path": "splits[0]"}, {"path": "subsets"}]})
    text = "\n".join(m.receipted_where_empty_section(data))
    assert ("counted under each): deleted 1, no removal row 1. Slot × replicate instances by removals "
            "status: deleted 2, no removal row 1.") in text


@pytest.mark.corpus
def test_the_issue_examples_are_rows_of_the_nested_reading():
    """#3934's two examples. A field in one replicate's single object and
    not in another's: `human_subject_research.irb_approval`, filled by v4
    CM4AI's rep1 only — unmeasured, since that arm wrote no receipt. An
    entry of a list inside entries: on v6 VOICE, Yael Bensoussan's
    University of South Florida affiliation, receipted in both replicates
    holding it, is a candidate rep3 lacks; rep3 names the affiliation more
    specifically, which a keyed identity reads as another entry."""
    m = _arm_comparison()
    slots = dataset_slots()

    def rows(arm, project):
        prefix = next(pfx for key, _d, pfx, *_ in m.ARMS if key == arm)
        tags = {m._rep_tag(lab): lab for lab in m.arm_labels(prefix)}
        recs = {t: yaml.safe_load((m.CONCAT / m._method_for(lab, project) / lab / f"{project}_d4d.yaml").read_text())
                for t, lab in tags.items()}
        assert len(recs) == 3, (arm, project)
        resolved, _basis = m._replicate_resolved(tags, project, recs)
        got = nested_omission_candidates(recs, compare_structure(recs, slots), resolved)
        return {r["chain"]: r for r in got["rows"]}

    irb = rows("v4", "CM4AI")["human_subject_research.irb_approval"]
    assert (irb["kind"], irb["basis"], irb["held_by"], irb["status"]) == ("field", "single", ["rep1"], "unmeasured")
    voice = rows("v6agentic", "VOICE")
    usf = voice["creators[name=Yael Bensoussan].affiliations[name=University of South Florida]"]
    assert (usf["kind"], usf["held_by"], usf["receipted_in"], usf["status"]) == (
        "entry", ["rep1", "rep2"], ["rep1", "rep2"], "candidate")
    assert [r["held_by"] for c, r in voice.items()
            if c.startswith("creators[name=Yael Bensoussan].affiliations[name=USF Health")] == [["rep3"]]


@pytest.mark.corpus
def test_the_nested_walk_reproduces_the_top_level_alignment_on_v7_production():
    """#3337's figure: on v7 production, 135 top-level entries join by key
    against 1048 by position; the nested walk's first-level `slot[*]`
    comparisons over the same list slots are those joins."""
    m = _arm_comparison()
    slots = dataset_slots()
    prefix = next(pfx for key, _d, pfx, *_ in m.ARMS if key == "v7prod")
    key = pos = 0
    for p in m.PROJECTS:
        labels = m.arm_labels(prefix)
        recs = {lab: yaml.safe_load((m.CONCAT / m._method_for(lab, p) / lab / f"{p}_d4d.yaml").read_text())
                for lab in labels}
        res = compare_structure(recs, slots)
        nested = compare_nested(recs, res)
        assert len(nested["slots"]) == summarize(res)["nested_in_all"]
        for name, r in res["slots"].items():
            if r.get("kind") == "nested" and r["counted"] and r["state"] in ("identical", "two_agree", "all_differ"):
                cell = nested["paths"].get(f"{name}[*]", {"by_basis": {}})["by_basis"]
                key += sum(cell.get("key", {}).values())
                pos += sum(cell.get("position", {}).values())
    assert (key, pos) == (135, 1048)
