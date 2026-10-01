#!/usr/bin/env python
"""Agreement between the first reading and a blind second reading of the
record_self_narration judgements behind the absence v3/v4 notes (#3876).

The first reading is the three committed judgement files `FIRST` names; the
second is `SECOND`, a separately run agent's reading of the same 188 phrases
from a packet and rubric that carried none of the first reading's verdicts.
This script writes `notes/absence_second_reading_agreement_2026-09-30.md`:
raw agreement, Cohen's kappa with a 95% interval, the confusion matrix and
agreement by class, on the verdict for all 188 and on the reading where both
readers gave one, and every disagreement by id with both readings and both
reasons.

It also says what the recall note (`notes/absence_v3_recall.md`) would read
if the second reading's verdicts stood in for the first's: a sensitivity
figure, computed with that note's own arithmetic over the same pinned
records. It changes no first-reader verdict, no committed count and no lint;
the first reading stays the one every note is rendered from.

Usage:
    poetry run python scripts/absence_second_reading_agreement.py           # rewrite the note
    poetry run python scripts/absence_second_reading_agreement.py --check   # read-only: exit 1 when stale

The sensitivity section walks the pinned corpus (as `absence_v3_recall.py
--check` does); `agreement()` and `agreement_lines()` read the judgement files
only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "notes" / "absence_second_reading_agreement_2026-09-30.md"
SECOND = "notes/absence_v3_v4_second_reading_judgements_3876.yaml"
RECALL_FILE = "notes/absence_v3_recall_judgements_241e910e.yaml"
KEPT_FILE = "notes/absence_v3_precision_source_ranking_judgements_ec97ce4b.yaml"
V4_FILE = "notes/absence_precision_judgements_574f03c2.yaml"
#: The first reading: every record_self_narration row of these files.
FIRST = (RECALL_FILE, KEPT_FILE, V4_FILE)
RSN = "record_self_narration"
VERDICTS = ("in_class", "borderline", "not_in_class")
READINGS = {"construction": "in_class", "referent": "in_class", "source": "borderline",
            "absence": "not_in_class"}
SOURCE_RANKING = "rsn.source-ranking"
#: The normal quantile of the 95% intervals.
_Z95 = 1.959963984540054


class Refused(Exception):
    """The two readings are not of the same items, or use a class the rubric does not define."""


def _load(rel: str) -> dict[str, Any]:
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


def _sha256(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def rubric_classes(text: str) -> tuple[set[str], set[str]]:
    """The verdicts and readings the rubric defines: its `Verdicts:` line,
    and the first word of each line of its readings table."""
    verdicts = next(line for line in text.splitlines() if line.startswith("Verdicts:"))
    verdict_set = {w.strip(" .`") for w in verdicts[len("Verdicts:"):].split(",")}
    section = text.split("## Readings", 1)[1].split("\n## ", 1)[0]
    readings = {line.split()[0] for line in section.splitlines()
                if line.startswith("    ") and line.split() and line.split()[0] in READINGS}
    return verdict_set, readings


def pairs() -> list[tuple[dict, dict]]:
    """(first row, second row) for every item, in the second file's order.
    Refused unless the second reading covers exactly the first reading's
    rows, at the same record, pointer and span, with the rubric's classes."""
    second = _load(SECOND)
    if second.get("rubric_sha256") != _sha256(second["rubric"]):
        raise Refused(f"{second['rubric']} is not the rubric the second reading names")
    verdicts, readings = rubric_classes((ROOT / second["rubric"]).read_text(encoding="utf-8"))
    first = {(f, r["n"]): r for f in FIRST for r in _load(f)["judgements"][RSN]}
    rows = second["judgements"][RSN]
    keys = [(r["source_file"], r["n"]) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != set(first):
        raise Refused(f"{SECOND} does not cover exactly the first reading's {len(first)} rows")
    out = []
    for r in rows:
        f = first[(r["source_file"], r["n"])]
        if any(f[k] != r[k] for k in ("record", "pointer", "start", "end", "patterns", "text")):
            raise Refused(f"{SECOND} {r['id']}: not the phrase {r['source_file']} #{r['n']} judges")
        if r["verdict"] not in verdicts or ("reading" in r and r["reading"] not in readings):
            raise Refused(f"{SECOND} {r['id']}: a class the rubric does not define")
        if "reading" in r and READINGS[r["reading"]] != r["verdict"]:
            raise Refused(f"{SECOND} {r['id']}: reading {r['reading']!r} does not carry {r['verdict']!r}")
        if ("reading" in r) != (SOURCE_RANKING in r["patterns"]):
            raise Refused(f"{SECOND} {r['id']}: a reading is given exactly where the patterns "
                          f"include {SOURCE_RANKING}")
        out.append((f, r))
    return out


def kappa(a: list[str], b: list[str], classes: tuple[str, ...]) -> dict[str, Any]:
    """Cohen's kappa for two raters over the same items, with the large-sample
    standard error of Fleiss, Cohen and Everitt (1969) and a 95% normal
    interval, clipped to [-1, 1]."""
    n = len(a)
    m = {(i, j): sum(1 for x, y in zip(a, b) if (x, y) == (i, j)) / n for i in classes for j in classes}
    row = {i: sum(m[(i, j)] for j in classes) for i in classes}
    col = {j: sum(m[(i, j)] for i in classes) for j in classes}
    po = sum(m[(i, i)] for i in classes)
    pe = sum(row[i] * col[i] for i in classes)
    k = (po - pe) / (1 - pe)
    var = (sum(m[(i, i)] * (1 - (row[i] + col[i]) * (1 - k)) ** 2 for i in classes)
           + (1 - k) ** 2 * sum(m[(i, j)] * (col[i] + row[j]) ** 2
                                for i in classes for j in classes if i != j)
           - (k - pe * (1 - k)) ** 2) / (n * (1 - pe) ** 2)
    se = math.sqrt(max(var, 0.0))
    return {"n": n, "agree": round(po * n), "po": po, "pe": pe, "kappa": k, "se": se,
            "lo": max(-1.0, k - _Z95 * se), "hi": min(1.0, k + _Z95 * se)}


def wilson(k: int, n: int, z: float = _Z95) -> tuple[float, float]:
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def agreement() -> dict[str, Any]:
    """Every figure the note's agreement sections state, from the judgement files alone."""
    ps = pairs()
    first_v = [f["verdict"] for f, _ in ps]
    second_v = [s["verdict"] for _, s in ps]
    both_read = [(f, s) for f, s in ps if "reading" in f and "reading" in s]
    reading_classes = tuple(READINGS)
    by_file = {}
    for name in FIRST:
        sub = [(f, s) for f, s in ps if s["source_file"] == name]
        by_file[name] = (sum(f["verdict"] == s["verdict"] for f, s in sub), len(sub))
    return {
        "n": len(ps),
        "verdict": kappa(first_v, second_v, VERDICTS),
        "confusion": Counter(zip(first_v, second_v)),
        "by_class": {c: (first_v.count(c), second_v.count(c),
                         sum(1 for x, y in zip(first_v, second_v) if x == y == c)) for c in VERDICTS},
        "by_file": by_file,
        "reading": kappa([f["reading"] for f, _ in both_read], [s["reading"] for _, s in both_read],
                         reading_classes),
        "reading_confusion": Counter((f["reading"], s["reading"]) for f, s in both_read),
        "reading_only_second": [s["id"] for f, s in ps if "reading" in s and "reading" not in f],
        "disagree": [(f, s) for f, s in ps
                     if f["verdict"] != s["verdict"] or ("reading" in f and f.get("reading") != s.get("reading"))],
        "unsure": [s["id"] for _, s in ps if s["unsure"]],
        "reasons": Counter(s["reason"] for _, s in ps),
    }


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _confusion(counts: Counter, classes: tuple[str, ...], label: str) -> list[str]:
    lines = [f"| {label} first \\ second | " + " | ".join(classes) + " | total |",
             "|---|" + "---:|" * (len(classes) + 1)]
    for i in classes:
        lines.append(f"| {i} | " + " | ".join(str(counts[(i, j)]) for j in classes)
                     + f" | {sum(counts[(i, j)] for j in classes)} |")
    lines.append("| total | " + " | ".join(str(sum(counts[(i, j)] for i in classes)) for j in classes)
                 + f" | {sum(counts.values())} |")
    return lines


def _kappa_line(k: dict[str, Any]) -> str:
    lo, hi = wilson(k["agree"], k["n"])
    return (f"{k['agree']} of {k['n']} agree: raw agreement {_pct(k['po'])} (Wilson 95% {_pct(lo)} to "
            f"{_pct(hi)}), chance agreement {_pct(k['pe'])}, Cohen's kappa {k['kappa']:.3f} "
            f"(standard error {k['se']:.3f}, 95% interval {k['lo']:.3f} to {k['hi']:.3f}).")


def agreement_lines(a: dict[str, Any]) -> list[str]:
    second = _load(SECOND)
    v, r = a["verdict"], a["reading"]
    lines = [
        "## Inputs",
        "",
        f"- **First reading:** every record_self_narration row of `{RECALL_FILE}` (88),",
        f"  `{KEPT_FILE}` (50) and `{V4_FILE}` (50; its",
        "  bundle_wide_absence rows were carried over from v1, not read, and are not compared).",
        "  One rater each time, the agent implementing #3705, #3793 and #3791.",
        f"- **Second reading:** `{SECOND}`, recorded {second['recorded']}: {a['n']} rows,",
        "  by a separately run agent that saw only the packet and the rubric, not an independent human",
        f"  rater. Packet `{second['packet']}` sha256 `{second['packet_sha256']}`; rubric",
        f"  `{second['rubric']}` sha256 `{second['rubric_sha256']}`; the agent's output sha256",
        f"  `{second['second_reading_sha256']}`.",
        "- Both readers are instances of the same kind of model. Agreement says how far the verdicts",
        "  depend on one reading, not on one kind of reader.",
        "",
        "## Verdict, all items",
        "",
        _kappa_line(v),
        "",
        *_confusion(a["confusion"], VERDICTS, "verdict:"),
        "",
        "By class: *specific agreement* is 2 × both ÷ (first + second), the share of one reader's",
        "uses of the class the other shares.",
        "",
        "| class | first | second | both | specific agreement |",
        "|---|---:|---:|---:|---:|",
    ]
    for c, (n1, n2, both) in a["by_class"].items():
        lines.append(f"| {c} | {n1} | {n2} | {both} | "
                     + (f"{_pct(2 * both / (n1 + n2))} |" if n1 + n2 else "— |"))
    lines += ["", "| first-reading file | agree | items |", "|---|---:|---:|"]
    for name, (k, n) in a["by_file"].items():
        lines.append(f"| `{name}` | {k} | {n} |")
    lines += [
        "",
        "## Reading, where both readers gave one",
        "",
        f"The rubric asks for a reading on every {SOURCE_RANKING} match. The first reading gave one in the",
        f"recall and kept-match files; `{V4_FILE}` predates the readings and",
        f"gives none, so its {len(a['reading_only_second'])} {SOURCE_RANKING} rows are compared on the",
        f"verdict only ({', '.join(a['reading_only_second'])}).",
        "",
        _kappa_line(r),
        "",
        *_confusion(a["reading_confusion"], tuple(READINGS), "reading:"),
        "",
        "## Disagreements",
        "",
    ]
    if not a["disagree"]:
        lines.append("None.")
    for f, s in a["disagree"]:
        fr = f"{f['verdict']}" + (f" ({f['reading']})" if "reading" in f else "")
        sr = f"{s['verdict']}" + (f" ({s['reading']})" if "reading" in s else "")
        lines += [
            f"### {s['id']} (`{s['source_file']}` #{s['n']})",
            "",
            f"- Phrase `{s['text']}` at `{s['record']}` `{s['pointer']}` [{s['start']}, {s['end']}).",
            f"- **First:** {fr}. {f['reason']}",
            f"- **Second:** {sr}" + (", marked unsure" if s["unsure"] else "") + f". {s['reason']}",
            "",
        ]
    common = a["reasons"].most_common(1)[0]
    lines += [
        "## The second reading's own marks",
        "",
        f"It marked {len(a['unsure'])} items unsure: {', '.join(a['unsure'])}.",
        f"Its {a['n']} reasons are {len(a['reasons'])} distinct texts; the commonest is given {common[1]} times",
        f"(\"{common[0]}\"). Most restate the rubric's reading rather than quote the sentence, so",
        "they say which reading was applied, not what in the sentence decided it.",
    ]
    return lines


def _recall_script():
    spec = importlib.util.spec_from_file_location("absence_v3_recall", ROOT / "scripts" / "absence_v3_recall.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def recall_figures(found: dict[str, Any], rows: list[dict], kept_rows: list[dict]) -> dict[str, float]:
    """The headline figures of `notes/absence_v3_recall.md`, by its arithmetic
    (`absence_v3_recall.render_markdown` and `_v4_section`), from the given
    verdicts: `rows` the dropped matches, `kept_rows` the kept draw."""
    m = _recall_script()
    kept = found["totals"]["v3"]
    computed = {(p, h["pointer"], h["start"], h["end"]): h for p, h in found["rows"]}
    v4 = {r["n"]: computed[(r["record"], r["pointer"], r["start"], r["end"])]["v4"] for r in rows}
    in_class = [r for r in rows if r["verdict"] == "in_class"]
    lost = [r for r in in_class if not r["flagged"]]
    k_in, n_kept = sum(r["verdict"] == "in_class" for r in kept_rows), len(kept_rows)
    lo, hi = m.wilson(k_in, n_kept)
    recovered = [r for r in rows if v4[r["n"]] == "recovered"]
    rec_in = sum(r["verdict"] == "in_class" for r in recovered)
    retained = kept - found["totals"]["v3_not_ended_by_v4"]
    judged = retained + len(recovered)
    v3_in = [kept * p for p in (k_in / n_kept, lo, hi)]
    v4_in = [retained * p + rec_in for p in (k_in / n_kept, lo, hi)]
    return {
        "dropped_in_class": len(in_class),
        "dropped_borderline": sum(r["verdict"] == "borderline" for r in rows),
        "dropped_not_in_class": sum(r["verdict"] == "not_in_class" for r in rows),
        "lost": len(lost), "lost_recovered": sum(v4[r["n"]] == "recovered" for r in lost),
        "kept_in_class": k_in, "kept_drawn": n_kept,
        "kept_precision": 100 * k_in / n_kept, "kept_precision_lo": 100 * lo, "kept_precision_hi": 100 * hi,
        "v3_upper": 100 * kept / (kept + len(in_class)),
        "v3_recall": 100 * v3_in[0] / (v3_in[0] + len(in_class)),
        "v3_recall_lo": 100 * v3_in[1] / (v3_in[1] + len(in_class)),
        "v3_recall_hi": 100 * v3_in[2] / (v3_in[2] + len(in_class)),
        "v4_recovered_in_class": rec_in,
        "v4_precision": 100 * v4_in[0] / judged,
        "v4_recall": 100 * v4_in[0] / (v3_in[0] + len(in_class)),
        "v4_recall_lo": 100 * v4_in[1] / (v3_in[1] + len(in_class)),
        "v4_recall_hi": 100 * v4_in[2] / (v3_in[2] + len(in_class)),
    }


def sensitivity(found: dict[str, Any]) -> tuple[dict[str, float], dict[str, float], dict[str, int]]:
    """The recall note's figures under the first reading (as committed) and
    with the second reading's verdicts in its place, and the v4 precision
    sample's in-class tally under each."""
    second = {(r["source_file"], r["n"]): r for r in _load(SECOND)["judgements"][RSN]}

    def swap(rows: list[dict], name: str) -> list[dict]:
        return [dict(r, verdict=second[(name, r["n"])]["verdict"]) for r in rows]

    rows = _load(RECALL_FILE)["judgements"][RSN]
    kept_rows = _load(KEPT_FILE)["judgements"][RSN]
    v4_rows = _load(V4_FILE)["judgements"][RSN]
    first = recall_figures(found, rows, kept_rows)
    alt = recall_figures(found, swap(rows, RECALL_FILE), swap(kept_rows, KEPT_FILE))
    v4_tally = {"first": sum(r["verdict"] == "in_class" for r in v4_rows),
                "second": sum(r["verdict"] == "in_class" for r in swap(v4_rows, V4_FILE)),
                "n": len(v4_rows)}
    return first, alt, v4_tally


SENSITIVITY_ROWS = (
    ("dropped matches in class (v3 gives up)", "dropped_in_class", "{:.0f}"),
    ("dropped matches borderline", "dropped_borderline", "{:.0f}"),
    ("in-class dropped phrases in a sentence v3 counts nothing in", "lost", "{:.0f}"),
    ("of those, recovered by v4", "lost_recovered", "{:.0f}"),
    ("kept-draw precision (in class of 50)", "kept_precision", "{:.1f}%"),
    ("v3 recall, upper bound", "v3_upper", "{:.1f}%"),
    ("v3 recall, estimated", "v3_recall", "{:.1f}%"),
    ("v4 recovered rows in class", "v4_recovered_in_class", "{:.0f}"),
    ("v4 precision, estimated", "v4_precision", "{:.1f}%"),
    ("v4 recall, estimated", "v4_recall", "{:.1f}%"),
)


def sensitivity_lines(first: dict, alt: dict, v4_tally: dict) -> list[str]:
    lines = [
        "## Sensitivity: the recall note under the second reading",
        "",
        "Not a change. `notes/absence_v3_recall.md` and `notes/absence_claims_baseline.md` stay rendered",
        "from the first reading; this is what their figures would read with the second reading's",
        "verdicts in its place, by the recall note's own arithmetic over the same pinned records.",
        "",
        "| figure | first reading (committed) | second reading |",
        "|---|---:|---:|",
    ]
    for label, key, fmt in SENSITIVITY_ROWS:
        lines.append(f"| {label} | {fmt.format(first[key])} | {fmt.format(alt[key])} |")
    lines += [
        "",
        f"Intervals, first then second: v3 recall {first['v3_recall_lo']:.1f}% to {first['v3_recall_hi']:.1f}%"
        f" and {alt['v3_recall_lo']:.1f}% to {alt['v3_recall_hi']:.1f}%; v4 recall"
        f" {first['v4_recall_lo']:.1f}% to {first['v4_recall_hi']:.1f}% and"
        f" {alt['v4_recall_lo']:.1f}% to {alt['v4_recall_hi']:.1f}%.",
        f"The v4 precision sample (`{V4_FILE}`, record_self_narration) has"
        f" {v4_tally['first']} of {v4_tally['n']} in class under the first reading and"
        f" {v4_tally['second']} under the second, so the baseline note's precision row would"
        + (" not move." if v4_tally["first"] == v4_tally["second"] else " move."),
    ]
    return lines


def render_markdown(found: dict[str, Any]) -> str:
    lines = [
        "# Absence judgements: agreement with a blind second reading (2026-09-30)",
        "",
        "Generated by `scripts/absence_second_reading_agreement.py` (#3876). Do not edit by hand: run",
        "the script to regenerate it, or `--check` to ask whether it still matches its inputs.",
        "",
        *agreement_lines(agreement()),
        "",
        *sensitivity_lines(*sensitivity(found)),
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="read-only: exit 1 when the note is stale")
    args = ap.parse_args(argv)
    m = _recall_script()
    try:
        found = m.dropped(m.baseline.CORPUS, m.baseline.read_pins(m.baseline.PINS))
        text = render_markdown(found)
    except (m.baseline.Stale, m.Refused, Refused) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    if args.check:
        if not OUT_MD.exists() or OUT_MD.read_text(encoding="utf-8") != text:
            print(f"stale: {OUT_MD.relative_to(ROOT)} does not match; run "
                  "scripts/absence_second_reading_agreement.py", file=sys.stderr)
            return 1
        print(f"{OUT_MD.relative_to(ROOT)} is current")
        return 0
    OUT_MD.write_text(text, encoding="utf-8")
    print(f"wrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
