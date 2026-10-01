"""Agreement between the two readings of the 122 Q19 recommendations (#3831).

Reads notes/q19_recommendations_3831_first_reading.yaml (the #3747 pins in
per-item form), notes/q19_recommendations_3831_second_reading.yaml (the blind
second reading of record, made with the rating files step 3b asks about) and
notes/q19_recommendations_3831_second_reading_without_sources.yaml (the
earlier blind reading made without them, a recorded deviation), and renders
the figures between the GENERATED markers of
notes/q19_recommendations_blind_agreement_2026-09-30.md: each second reading
against the first, and the two second readings against each other.

    python scripts/q19_blind_agreement.py           # print the block
    python scripts/q19_blind_agreement.py --write   # rewrite it in the note
    python scripts/q19_blind_agreement.py --check   # exit 1 if the note differs

Offline; no model calls. Changes no class, pin, count or lint behaviour: the
miss count under the second reading is reported as a sensitivity figure.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "notes"
PACKET = NOTES / "q19_recommendations_3831_packet.json"
FIRST = NOTES / "q19_recommendations_3831_first_reading.yaml"
SECOND = NOTES / "q19_recommendations_3831_second_reading.yaml"
SECOND_WITHOUT_SOURCES = NOTES / "q19_recommendations_3831_second_reading_without_sources.yaml"
NOTE = NOTES / "q19_recommendations_blind_agreement_2026-09-30.md"
BEGIN, END = "<!-- BEGIN GENERATED: scripts/q19_blind_agreement.py -->", "<!-- END GENERATED -->"

#: The rubric's classes in the order of its ordered test.
CLASSES = ("named_absence", "placement", "criticism", "request")
MISSES = ("named_absence", "placement")
Z95 = 1.959963984540054
#: The misses outside the 122, fixed by the 155 hand-read sentences (#3838):
#: 95 of 277 less the 64 the first reading finds among the 122.
MISSES_OUTSIDE_RECOMMENDATIONS, HAND_READ_TOTAL = 31, 277


def load(first=FIRST, second=SECOND, packet=PACKET, without=SECOND_WITHOUT_SOURCES):
    f = yaml.safe_load(Path(first).read_text(encoding="utf-8"))
    s = yaml.safe_load(Path(second).read_text(encoding="utf-8"))
    p = json.loads(Path(packet).read_text(encoding="utf-8"))
    w = yaml.safe_load(Path(without).read_text(encoding="utf-8"))
    return f, s, p, w


def kappa(pairs, classes):
    """Cohen's kappa with the Fleiss, Cohen and Everitt (1969) large-sample
    standard error and a 95% Wald interval, over (first, second) pairs."""
    n = len(pairs)
    k = len(classes)
    index = {c: i for i, c in enumerate(classes)}
    p = [[0.0] * k for _ in range(k)]
    for a, b in pairs:
        p[index[a]][index[b]] += 1 / n
    row = [sum(p[i]) for i in range(k)]
    col = [sum(p[i][j] for i in range(k)) for j in range(k)]
    po = sum(p[i][i] for i in range(k))
    pe = sum(row[i] * col[i] for i in range(k))
    kap = (po - pe) / (1 - pe)
    a = sum(p[i][i] * (1 - (row[i] + col[i]) * (1 - kap)) ** 2 for i in range(k))
    b = (1 - kap) ** 2 * sum(p[i][j] * (col[i] + row[j]) ** 2
                             for i in range(k) for j in range(k) if i != j)
    c = (kap - pe * (1 - kap)) ** 2
    se = math.sqrt(max(a + b - c, 0.0) / (n * (1 - pe) ** 2))
    return {"n": n, "observed": po, "expected": pe, "kappa": kap, "se": se,
            "ci95": (kap - Z95 * se, kap + Z95 * se)}


def classes_of(reading):
    """{id: class} of a second-reading file."""
    return {j["id"]: j["class"] for j in reading["judgements"]}


def agreement(one, two, unsure=None):
    """Every figure the note states for one pair of readings, given as
    {id: class} maps over the same ids (rows `one`, columns `two`)."""
    ids = sorted(one)
    pairs = [(one[i], two[i]) for i in ids]
    matrix = {a: {b: sum(1 for x, y in pairs if (x, y) == (a, b)) for b in CLASSES} for a in CLASSES}
    by_class = {}
    for c in CLASSES:
        n1, n2 = Counter(x for x, _ in pairs)[c], Counter(y for _, y in pairs)[c]
        both = matrix[c][c]
        by_class[c] = {"first": n1, "second": n2, "both": both,
                       "specific": (2 * both / (n1 + n2)) if n1 + n2 else None}
    miss = [("miss" if x in MISSES else "not", "miss" if y in MISSES else "not") for x, y in pairs]
    # Step 3 versus 4 among the items both readings take past steps 1-2.
    past = [(x, y) for x, y in pairs if x not in MISSES and y not in MISSES]
    misses = {"first": sum(x == "miss" for x, _ in miss), "second": sum(y == "miss" for _, y in miss)}
    disagreements = [i for i in ids if one[i] != two[i]]
    out = {
        "all": kappa(pairs, CLASSES),
        "matrix": matrix,
        "by_class": by_class,
        "steps_1_2": kappa(miss, ("miss", "not")),
        "step_3_4": kappa(past, ("criticism", "request")),
        "disagreements": disagreements,
        "misses": misses,
        "misses_277": {k: MISSES_OUTSIDE_RECOMMENDATIONS + v for k, v in misses.items()},
    }
    if unsure is not None:
        out["unsure"] = {"all": sum(unsure.values()),
                         "disagreeing": sum(unsure[i] for i in disagreements)}
    return out


def _k(r):
    lo, hi = r["ci95"]
    bound = f"{hi:.3f}" if hi <= 1 else f"1.000, the Wald bound {hi:.3f} truncated"
    return (f"{r['observed']:.3f} raw ({round(r['observed'] * r['n'])}/{r['n']}); "
            f"kappa {r['kappa']:.3f} (95% Wald CI {max(lo, -1):.3f} to {bound}; "
            f"chance agreement {r['expected']:.3f})")


def _matrix(r, rows, cols):
    out = [f"Confusion matrix (rows: {rows}; columns: {cols}):", "",
           f"| {rows} \\ {cols} | " + " | ".join(CLASSES) + " | total |",
           "|---|" + "---:|" * (len(CLASSES) + 1)]
    for a in CLASSES:
        out.append(f"| {a} | " + " | ".join(str(r["matrix"][a][b]) for b in CLASSES)
                   + f" | {sum(r['matrix'][a].values())} |")
    out.append("| total | " + " | ".join(str(r["by_class"][b]["second"]) for b in CLASSES)
               + f" | {r['all']['n']} |")
    return out


def _figures(r, rows, cols):
    return [f"- All four classes: {_k(r['all'])}.",
            f"- Steps 1-2 (miss = named_absence or placement, versus not): {_k(r['steps_1_2'])}.",
            f"- Step 3 versus 4, over the items both readings take past steps 1-2: {_k(r['step_3_4'])}.",
            "", *_matrix(r, rows, cols)]


def _sentence(item):
    src = item["sources"][0]
    return [f"> {item['sentence']}", "", f"Source: `{src['file']}` `{src['json_path']}`", ""]


def _second(label, j):
    return f"- {label}, {j['class']}{' (unsure)' if j['unsure'] else ''}: {j['reason']}"


def render(first, second, packet, without):
    one = first["classes"]
    two = {j["id"]: j for j in second["judgements"]}
    wo = {j["id"]: j for j in without["judgements"]}
    sentence = {i["id"]: i for i in packet["items"]}
    reasons = first.get("reasons", {})
    r = agreement(one, classes_of(second), {i: j["unsure"] for i, j in two.items()})
    rw = agreement(one, classes_of(without), {i: j["unsure"] for i, j in wo.items()})
    rr = agreement(classes_of(without), classes_of(second))

    def first_line(i):
        f_reason = reasons.get(i, {})
        return (f"- First, {one[i]} ({f_reason.get('basis', 'no reason recorded')}): "
                f"{f_reason.get('reason', '')}")

    out = [BEGIN, "", "### The second reading of record (with the step 3b sources) against the first", "",
           *_figures(r, "first reading", "second"),
           "",
           f"Disagreements: {len(r['disagreements'])}; the second reader marked "
           f"{r['unsure']['disagreeing']} of them unsure ({r['unsure']['all']} unsure of 122 in all).",
           "", "Agreement by class (specific agreement = 2 x both / (first + second)):", "",
           "| class | first | second | both | specific agreement |", "|---|---:|---:|---:|---:|"]
    for c in CLASSES:
        b = r["by_class"][c]
        out.append(f"| {c} | {b['first']} | {b['second']} | {b['both']} | {b['specific']:.3f} |")
    m, m2 = r["misses"], r["misses_277"]
    out += ["", "Sensitivity, not a change (the pins, the module docstring's counts and the lint are "
            "as on main):", "",
            f"- Q19 misses among the 122: {m['first']} under the first reading, {m['second']} under "
            f"the second ({m['second'] - m['first']:+d}).",
            f"- Misses among the 277 hand-read sentences (#3544): {m2['first']}/{HAND_READ_TOTAL} "
            f"under the first reading, {m2['second']}/{HAND_READ_TOTAL} with the second reading's "
            f"122 ({MISSES_OUTSIDE_RECOMMENDATIONS} outside the 122 held fixed).",
            "", "Every disagreement:", ""]
    for i in r["disagreements"]:
        out += [f"#### {i}: {one[i]} (first) / {two[i]['class']} (second)", "",
                *_sentence(sentence[i]), first_line(i), _second("Second", two[i]), ""]

    mw = rw["misses"]
    out += ["### The reading made without the step 3b sources (a recorded deviation) against the first", "",
            *_figures(rw, "first reading", "without sources"),
            "",
            f"Disagreements: {len(rw['disagreements'])}; marked unsure {rw['unsure']['disagreeing']} "
            f"({rw['unsure']['all']} unsure of 122 in all). Q19 misses among the 122: {mw['first']} "
            f"under the first reading, {mw['second']} under this one ({mw['second'] - mw['first']:+d}).",
            "", "| item | first | without sources | its reason |", "|---|---|---|---|"]
    for i in rw["disagreements"]:
        unsure = " (unsure)" if wo[i]["unsure"] else ""
        out.append(f"| {i} | {one[i]} | {wo[i]['class']}{unsure} | {wo[i]['reason']} |")

    out += ["", "### The two second readings against each other (what step 3b changed)", "",
            *_figures(rr, "without sources", "with sources"),
            "", f"Items the two second readings class differently: {len(rr['disagreements'])}.", ""]
    for i in rr["disagreements"]:
        moved = ("now agrees with the first" if two[i]["class"] == one[i]
                 else "now disagrees with the first" if wo[i]["class"] == one[i]
                 else "disagrees with the first either way")
        out += [f"#### {i}: {wo[i]['class']} (without) / {two[i]['class']} (with); first {one[i]}, "
                f"{moved}", "",
                *_sentence(sentence[i]),
                _second("Without sources", wo[i]), _second("With sources", two[i]), ""]
    out.append(END)
    return "\n".join(out)


def note_block(text):
    start, end = text.index(BEGIN), text.index(END) + len(END)
    return text[start:end]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    block = render(*load())
    if not (args.write or args.check):
        print(block)
        return 0
    text = NOTE.read_text(encoding="utf-8")
    if args.check:
        same = note_block(text) == block
        print("note matches" if same else "note differs from the readings")
        return 0 if same else 1
    NOTE.write_text(text.replace(note_block(text), block), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
