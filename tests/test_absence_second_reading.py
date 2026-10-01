"""The second reading of the absence record_self_narration judgements (#3876),
blind on 187 of its 188 items.

The committed second reading must cover exactly the first reading's rows and
use only the classes its rubric defines; the agreement note's figures must
recompute from the two readings, over all items and over the blind ones (the
rubric's `absence` example is item recall_dropped-019's sentence with its
first-reader verdict, #3964). The corpus-marked tests also reproduce the
note's sensitivity section, check that its first-reading column is the
committed recall note's, and check that the items excluded as not blind are
exactly those whose judged sentence the rubric quotes.
"""
import copy
import hashlib
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "absence_second_reading_agreement.py"


def _script():
    spec = importlib.util.spec_from_file_location("absence_second_reading_agreement", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _yaml(rel):
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


M = _script()
SECOND = _yaml(M.SECOND)
NOTE = M.OUT_MD.read_text(encoding="utf-8")


def test_the_second_reading_covers_exactly_the_first_readings_rows():
    first = {(f, r["n"]): r for f in M.FIRST for r in _yaml(f)["judgements"][M.RSN]}
    rows = SECOND["judgements"][M.RSN]
    keys = [(r["source_file"], r["n"]) for r in rows]
    assert len(keys) == len(set(keys)) == len(first) == 188
    assert set(keys) == set(first)
    for r in rows:
        f = first[(r["source_file"], r["n"])]
        assert (r["record"], r["pointer"], r["start"], r["end"], r["text"]) == \
               (f["record"], f["pointer"], f["start"], f["end"], f["text"]), r["id"]
    assert len(M.pairs()) == 188                     # the script's own reader agrees


def test_the_second_reading_uses_only_the_rubrics_classes():
    rubric = ROOT / SECOND["rubric"]
    assert hashlib.sha256(rubric.read_bytes()).hexdigest() == SECOND["rubric_sha256"]
    verdicts, readings = M.rubric_classes(rubric.read_text(encoding="utf-8"))
    assert verdicts == {"in_class", "borderline", "not_in_class"}
    assert readings == {"construction", "referent", "source", "absence"}
    for r in SECOND["judgements"][M.RSN]:
        assert r["verdict"] in verdicts, r["id"]
        written = r["class_as_written"]
        if "reading" in r:
            assert r["reading"] in readings and written == f"reading: {r['reading']}", r["id"]
            assert M.READINGS[r["reading"]] == r["verdict"], r["id"]
        else:
            assert written == r["verdict"], r["id"]
        assert ("reading" in r) == (M.SOURCE_RANKING in r["patterns"]), r["id"]


@pytest.mark.parametrize("change, message", [
    ("drop_row", "does not cover exactly"),
    ("unknown_class", "a class the rubric does not define"),
    ("unknown_reading", "a class the rubric does not define"),
    ("moved_span", "not the phrase"),
])
def test_a_second_reading_that_is_not_the_first_readings_items_is_refused(monkeypatch, change, message):
    doc = copy.deepcopy(SECOND)
    rows = doc["judgements"][M.RSN]
    if change == "drop_row":
        rows.pop()
    elif change == "unknown_class":
        # Only the verdict changes, on a row that carries no reading, so no
        # check but the class check can refuse it (#3965).
        row = next(r for r in rows if "reading" not in r)
        row["verdict"] = "out_of_class"
    elif change == "unknown_reading":
        row = next(r for r in rows if "reading" in r)
        row["reading"] = "elsewhere"
    else:
        rows[0]["start"] += 1
    load = M._load
    monkeypatch.setattr(M, "_load", lambda rel: doc if rel == M.SECOND else load(rel))
    with pytest.raises(M.Refused, match=message):
        M.pairs()


def _kappa(a, b):
    """Cohen's kappa written out independently of the script."""
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in set(a) | set(b))
    return po, (po - pe) / (1 - pe)


def test_the_kappa_is_cohens_on_a_textbook_table():
    # 2x2 table [[20, 5], [10, 15]]: po = 0.7, pe = 0.5, kappa = 0.4.
    a = ["y"] * 25 + ["n"] * 25
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    k = M.kappa(a, b, ("y", "n"))
    assert k["po"] == pytest.approx(0.7) and k["pe"] == pytest.approx(0.5)
    assert k["kappa"] == pytest.approx(0.4)
    assert k["lo"] < 0.4 < k["hi"]


def test_the_notes_agreement_figures_recompute_from_the_two_readings():
    assert "\n".join(M.agreement_lines(M.agreement())) in NOTE
    first = {(f, r["n"]): r for f in M.FIRST for r in _yaml(f)["judgements"][M.RSN]}
    rows = SECOND["judgements"][M.RSN]
    a = [first[(r["source_file"], r["n"])]["verdict"] for r in rows]
    b = [r["verdict"] for r in rows]
    po, k = _kappa(a, b)
    agree = sum(x == y for x, y in zip(a, b))
    assert f"{agree} of {len(rows)} agree: raw agreement {100 * po:.1f}%" in NOTE
    assert f"Cohen's kappa {k:.3f}" in NOTE
    disagreeing = [(r, v) for r, v in zip(rows, a) if r["verdict"] != v]
    for r, v in disagreeing:
        section = NOTE.split(f"### {r['id']} ", 1)[1].split("\n## ", 1)[0]
        assert f"**First:** {v}" in section and f"**Second:** {r['verdict']}" in section
        assert r["reason"] in section and first[(r["source_file"], r["n"])]["reason"] in section
    assert NOTE.count("\n### ") == len(disagreeing)   # no reading-only disagreement either


def test_the_blind_figures_leave_out_exactly_the_items_the_rubric_gave_away():
    assert set(M.NOT_BLIND) == {"recall_dropped-019"}
    a = M.agreement()
    assert a["excluded"] == ["recall_dropped-019"] and a["n"] == 188
    first = {(f, r["n"]): r for f in M.FIRST for r in _yaml(f)["judgements"][M.RSN]}
    rows = [r for r in SECOND["judgements"][M.RSN] if r["id"] not in M.NOT_BLIND]
    assert len(rows) == 187
    fa = [first[(r["source_file"], r["n"])]["verdict"] for r in rows]
    po, k = _kappa(fa, [r["verdict"] for r in rows])
    agree = sum(x == r["verdict"] for x, r in zip(fa, rows))
    assert (a["blind_verdict"]["n"], a["blind_verdict"]["agree"]) == (187, agree)
    assert a["blind_verdict"]["kappa"] == pytest.approx(k)
    section = NOTE.split("## Verdict, the 187 blind items", 1)[1].split("\n## ", 1)[0]
    assert "Without recall_dropped-019" in section
    assert f"{agree} of 187 agree: raw agreement {100 * po:.1f}%" in section
    assert f"Cohen's kappa {k:.3f}" in section
    both = [(first[(r["source_file"], r["n"])], r) for r in rows]
    both = [(f["reading"], s["reading"]) for f, s in both if "reading" in f and "reading" in s]
    po_r, k_r = _kappa([x for x, _ in both], [y for _, y in both])
    agree_r = sum(x == y for x, y in both)
    assert (a["blind_reading"]["n"], a["blind_reading"]["agree"]) == (len(both), agree_r)
    assert a["blind_reading"]["kappa"] == pytest.approx(k_r)
    assert (f"The blind items, without recall_dropped-019: {agree_r} of {len(both)} agree: raw agreement "
            f"{100 * po_r:.1f}%") in NOTE
    assert f"Cohen's kappa {k_r:.3f}" in NOTE.split("The blind items, without", 1)[1].split("\n", 1)[0]
    # ... and the all-items figures still count all 188.
    assert "## Verdict, all items\n\n187 of 188 agree" in NOTE


def test_the_rubric_quotes_its_examples():
    text = (ROOT / SECOND["rubric"]).read_text(encoding="utf-8")
    assert "no tier-1 source states them" in M.rubric_quotes(text)


@pytest.mark.corpus   # reads pinned records under the committed corpus
def test_the_items_not_blind_are_exactly_those_whose_judged_sentence_the_rubric_quotes():
    hits = M.rubric_text_in_items(M.m_corpus())
    in_sentence = {i for i, found in hits.items() if any(w == "sentence" for _, w in found)}
    assert in_sentence == set(M.NOT_BLIND)
    assert hits["recall_dropped-019"] == [("no tier-1 source states them", "sentence")]
    # Elsewhere in a leaf, in a sentence the item does not judge: reported, not excluded.
    assert hits["recall_dropped-045"] == [("not stated in the bundle", "leaf")]
    assert set(hits) == {"recall_dropped-019", "recall_dropped-045"}


@pytest.mark.corpus   # walks the committed corpus
def test_the_committed_agreement_note_is_what_its_inputs_reproduce():
    assert M.main(["--check"]) == 0


@pytest.mark.corpus   # walks the committed corpus
def test_the_sensitivity_first_column_is_the_committed_recall_note():
    r = M._recall_script()
    found = r.dropped(r.baseline.CORPUS, r.baseline.read_pins(r.baseline.PINS))
    first, _, _ = M.sensitivity(found)
    recall_note = (ROOT / "notes" / "absence_v3_recall.md").read_text(encoding="utf-8")
    assert f"estimated **{first['v3_recall']:.1f}%**" in recall_note
    assert (f"({first['v3_recall_lo']:.1f}% to {first['v3_recall_hi']:.1f}% over the precision's interval"
            in recall_note)
    assert f"estimated **{first['v4_recall']:.1f}%** ({first['v4_recall_lo']:.1f}% to " in recall_note
    assert f"a precision of {first['v4_precision']:.1f}%" in recall_note
    assert f"Of the 88 dropped matches, {first['dropped_in_class']} are in class" in recall_note
