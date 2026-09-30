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
    align, compare_slot, compare_structure, dataset_slots, is_empty, omission_candidates,
    record_chunk_texts, summarize, top_slot, verified_by_slot,
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
