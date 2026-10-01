"""The blind second reading of the absence record_self_narration judgements (#3876).

The committed second reading must cover exactly the first reading's rows and
use only the classes its rubric defines; the agreement note's figures must
recompute from the two readings. The corpus-marked tests also reproduce the
note's sensitivity section, and check that its first-reading column is the
committed recall note's.
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


@pytest.mark.parametrize("change", ["drop_row", "unknown_class", "moved_span"])
def test_a_second_reading_that_is_not_the_first_readings_items_is_refused(monkeypatch, change):
    doc = copy.deepcopy(SECOND)
    rows = doc["judgements"][M.RSN]
    if change == "drop_row":
        rows.pop()
    elif change == "unknown_class":
        rows[0]["verdict"] = "out_of_class"
        rows[0].pop("reading", None)
        rows[0]["patterns"] = ["rsn.recorded-here"]
    else:
        rows[0]["start"] += 1
    load = M._load
    monkeypatch.setattr(M, "_load", lambda rel: doc if rel == M.SECOND else load(rel))
    with pytest.raises(M.Refused):
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
