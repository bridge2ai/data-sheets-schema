#!/usr/bin/env python
"""The recall absence lexicon v3 gives up on `rsn.source-ranking` (#3705).

v3 (#3520) matches a ranking term applied to a source (tier-N source,
higher-ranked, ranks higher, ...) only when a preference or resolution verb
lies within 80 characters of it in the same sentence. Over the 303 records
`notes/absence_claims_baseline.md` pins, that drops 88 of v2's 336 matches of
the pattern. This script names those 88, draws a seeded sample of them, and
writes `notes/absence_v3_recall.md` from the per-phrase judgements in the
file its `RECALL` entry names: how many of the dropped matches do narrate the
record's construction, and so how much recall v3 gave up for its precision.

It is a measurement of v3, not a change to it. It registers no lexicon, and
the counts in the baseline note do not move.

The note also measures the precision of the 248 matches v3 keeps (#3793):
a seeded draw of them (`--kept-sample`), judged per phrase in the file its
`KEPT` entry names with the same readings, turns the recall the note reports
from an upper bound (every kept match in class) into a point estimate with
an interval.

A *dropped match* is a v2 match of the pattern that no v3 match of the same
pattern ends at, in the same leaf. Every v3 match ends at a term v2 matched
(the v3 file says so, and `dropped` refuses a record where one does not), so
the dropped matches number v2's count less v3's. For each, the script also
records two things it computes rather than judges:

  cause     why v3 does not match it, tried in this order:
              absorbed        the term lies inside a v3 match that starts at an
                              earlier verb (#3732): its text is still flagged
              consumed        the 80-character rule admits it, but its only
                              verb is inside an earlier v3 match (#3732)
              window          a listed verb is in v3's sentence (to a `;` or a
                              full stop), more than 80 characters away
              semicolon       a listed verb is past a `;`, before any full stop
              other_sentence  a listed verb is in the leaf, past a full stop
              no_verb         no listed verb is anywhere in the leaf
            A full stop is v3's: a `.` followed by whitespace, so the `.` in
            `v3.1.0` is not one and the `.` in "St. Louis" is.
            Each is decided by the v3 regex itself with one of its bounds
            lifted, so it describes v3's bytes and not a paraphrase of them.
  flagged   the v3 record_self_narration patterns whose phrases overlap the
            dropped term's sentence, to its full stop (a `.` followed by
            whitespace; a clause after `;` is part of it, as it is when the
            phrase is judged). Empty when v3 counts nothing in that sentence.

The judgement file is in the form of the precision judgements
(`notes/absence_precision_judgements_bd0c63ed.yaml`) and is checked by the
same reader (`absence_claims_baseline.read_judgements`): its phrases must be
the draw the entry names, and its verdict tally the entry's counts, or the
note is refused. The entry's draw hash must in turn be the draw its `sample`
and `seed` make, recomputed from the pinned records (#3891), so `--check`
refuses a hand-picked or re-seeded set that the constant and the file agree on. Each row also carries its computed `cause` and `flagged`,
which must be what this script computes, and a judged `reading`, which fixes
its verdict (`READINGS`; the judgement file's header defines each): whether
the phrase's sentence narrates how the record was built, as the class
`record_self_narration` defines it, read in context.

Usage:
    poetry run python scripts/absence_v3_recall.py            # rewrite the note
    poetry run python scripts/absence_v3_recall.py --check    # read-only: exit 1 when stale
    poetry run python scripts/absence_v3_recall.py --sample 88 --seed 2919
        # read-only: print the seeded draw with each phrase's sentence and its
        # computed cause, for judging, and the draw's sha256 last
    poetry run python scripts/absence_v3_recall.py --kept-sample 50 --seed 2919
        # read-only: the same for a seeded draw of the matches v3 keeps (#3793)
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema import absence_lint  # noqa: E402
from data_sheets_schema import lexicon as lx  # noqa: E402


def _baseline():
    """The baseline script, whose pins, record reader and judgement reader
    this measurement shares rather than repeats."""
    path = ROOT / "scripts" / "absence_claims_baseline.py"
    spec = importlib.util.spec_from_file_location("absence_claims_baseline", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


baseline = _baseline()

OUT_MD = ROOT / "notes" / "absence_v3_recall.md"
PATTERN = "rsn.source-ranking"
RSN = "record_self_narration"
FROM_VERSION, TO_VERSION = 2, 3
#: A judged reading of a dropped phrase's sentence, and the verdict it
#: carries (the judgement file's header defines each).
READINGS = {"construction": "in_class", "referent": "in_class", "source": "borderline", "absence": "not_in_class"}
CAUSES = ("absorbed", "consumed", "window", "semicolon", "other_sentence", "no_verb")
#: The possible v4 changes the recall note reports, each as the `_variants`
#: name that makes it: first each bound lifted on its own, then the bounds
#: lifted cumulatively (the causes' order). A row admitted by a change is
#: one whose cause is not `absorbed` or `consumed` (those need no bound
#: lifted) and that the changed regex admits on its own (#3806).
LIFTS = (
    ("window", "Widen the window only", "window"),
    ("semicolon_alone", "Cross `;` only (80-character window kept)", "semicolon_alone"),
    ("full_stop_alone", "Cross a full stop only (80-character window and `;` kept)", "full_stop_alone"),
    ("window", "Widen the window", "cumulative_window"),
    ("semicolon", "Widen the window and cross `;`", "cumulative_semicolon"),
    ("other_sentence", "Widen the window, cross `;` and cross a full stop", "cumulative_full_stop"),
)
#: The bounds of v3's rule as its regex spells them. `_variants` refuses a
#: pattern that does not spell them so, rather than lifting nothing.
_WINDOW = "{0,80}?"
_GAP = r"(?:[^.;]|\.(?!\s))"
_FULL_STOP = re.compile(r"\.(?=\s)")

#: The judged draw of the dropped matches, keyed like the baseline's
#: PRECISION entries so the same reader checks it. The draw is every dropped
#: match (the sample is the population, 88), in the order
#: `random.Random(seed).sample` puts them. One rater, the agent implementing
#: #3705: not an independent review.
RECALL: dict[str, Any] = {
    "from_lexicon_sha256": "e5f35547ca9862c8dc7d5f8996e0e67712549591334b9f726003fd4b3c257708",   # v2
    "lexicon_sha256": "f1657b94067ebb8fbdfd83bccdad1780b83d1b9e8dba245664b9fe54d41df7b6",        # v3
    "record_set_sha256": "cb4b5b8ae826da7ec9ede78ffc920725df39e6b9a3140b18ca01e54b54a6b711",     # 303 records
    "sample": 88, "seed": baseline.SAMPLE_SEED,
    "draw_sha256": "241e910ec4781ea3467152b31e89aa6a302a2385370544d69ac5f427a47641aa",
    "classes": {RSN: (35, 50, 3)},
    "judgements": "notes/absence_v3_recall_judgements_241e910e.yaml",
}
#: The judged draw of the matches v3 keeps (#3793), keyed like RECALL: a
#: seeded sample of them, in the order `random.Random(seed).sample` puts
#: them, judged with `READINGS`. One rater, the agent implementing #3793: not
#: an independent review.
KEPT: dict[str, Any] = {
    "lexicon_sha256": RECALL["lexicon_sha256"],                                                  # v3
    "record_set_sha256": RECALL["record_set_sha256"],                                            # 303 records
    "sample": 50, "seed": baseline.SAMPLE_SEED,
    "draw_sha256": "ec97ce4b8e0f6d135c9b6ed1a7d55adbad1cdc3b9805c4c8b8dd14e6aaf8e61f",
    "classes": {RSN: (45, 5, 0)},
    "judgements": "notes/absence_v3_precision_source_ranking_judgements_ec97ce4b.yaml",
}
#: The normal quantile of the Wilson interval the precision is reported with.
_Z95 = 1.959963984540054


class Refused(Exception):
    """The lexicons or the records are not the ones this measurement names."""


def _alternatives(source: str) -> list[str]:
    """A regex's top-level alternatives: split at each `|` outside a group
    and a character class."""
    parts, depth, klass, start, i = [], 0, False, 0, 0
    while i < len(source):
        ch = source[i]
        if ch == "\\":
            i += 2
            continue
        if klass:
            klass = ch != "]"
        elif ch == "[":
            klass = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "|" and depth == 0:
            parts.append(source[start:i])
            start = i + 1
        i += 1
    return parts + [source[start:]]


def _variants(pattern: lx.Pattern) -> dict[str, tuple[re.Pattern, re.Pattern, re.Pattern]]:
    """v3's pattern split into its three alternatives — the names of the
    declared ranking, verb then term, term then verb — as v3 spells them
    (`rule`), with its bounds lifted in turn, each on top of the last (the
    80-character window, then `;` as an end, then every full stop: `window`,
    `semicolon`, `other_sentence`), and with each bound lifted on its own
    while the others stay as v3 spells them (`window`, `semicolon_alone`,
    `full_stop_alone`; see `LIFTS`). Each value is (names, verb-first,
    term-first)."""
    alts = _alternatives(pattern.regex.pattern)
    if len(alts) != 3 or any(a.count(_WINDOW) != 1 or a.count(_GAP) != 1 for a in alts[1:]):
        raise Refused(f"{PATTERN} is not v3's three alternatives with one 80-character window each")
    flags = pattern.regex.flags
    lifted = {
        "rule": (_WINDOW, _GAP),
        "window": ("*?", _GAP),
        "semicolon": ("*?", r"(?:[^.]|\.(?!\s))"),
        "other_sentence": ("*?", r"[\s\S]"),
        # One bound lifted on its own, the others kept as v3 spells them.
        "semicolon_alone": (_WINDOW, r"(?:[^.]|\.(?!\s))"),
        "full_stop_alone": (_WINDOW, r"[^;]"),
    }
    return {name: tuple(re.compile(a if i == 0 else a.replace(_WINDOW, w).replace(_GAP, g), flags)
                        for i, a in enumerate(alts))
            for name, (w, g) in lifted.items()}


def _admits(variant: tuple[re.Pattern, re.Pattern, re.Pattern], text: str, start: int, end: int) -> bool:
    """Whether a variant of v3's rule admits the term at [start, end) on its
    own: a verb-first match ending exactly there, or a term-first match
    starting there, with no earlier match to overlap it."""
    _, verb_first, term_first = variant
    m = term_first.match(text, start)
    if m and m.end() == end:
        return True
    return any(verb_first.fullmatch(text, p, end) for p in range(start))


def _sentence(text: str, start: int, end: int) -> tuple[int, int]:
    """The sentence around [start, end), as the phrase is judged: from after
    the last `.`-before-whitespace before it to the next one after it. A `;`
    does not end it, although it ends v3's window."""
    s = max((m.end() for m in _FULL_STOP.finditer(text, 0, start)), default=0)
    after = _FULL_STOP.search(text, end)
    return s, after.start() if after else len(text)


def cause(variants: dict, text: str, start: int, end: int, v3_spans: list[tuple[int, int]]) -> str:
    """Why v3 does not match the v2 term at [start, end) (see the module
    docstring for the order)."""
    if any(s <= start and end <= e for s, e in v3_spans):
        return "absorbed"
    for name, label in (("rule", "consumed"), ("window", "window"), ("semicolon", "semicolon"),
                        ("other_sentence", "other_sentence")):
        if _admits(variants[name], text, start, end):
            return label
    return "no_verb"


def dropped(corpus: Path, pins: dict[str, str]) -> dict[str, Any]:
    """Every v2 match of the pattern that no v3 match ends at, over the
    pinned records, in record then leaf then offset order, with its cause and
    the v3 phrases in its sentence."""
    v2, v3 = (lx.load(absence_lint.LEXICON, v) for v in (FROM_VERSION, TO_VERSION))
    for have, want in ((v2.sha256, RECALL["from_lexicon_sha256"]), (v3.sha256, RECALL["lexicon_sha256"])):
        if have != want:
            raise Refused(f"a registered lexicon hashes to {have[:12]}…, not the {want[:12]}… "
                          "this measurement names")
    p2 = next(p for p in v2.patterns if p.id == PATTERN).regex
    p3 = next(p for p in v3.patterns if p.id == PATTERN)
    variants = _variants(p3)
    scope = absence_lint._scope(v3)
    rows: list[tuple[str, dict]] = []
    kept_rows: list[tuple[str, dict]] = []
    totals = {"v2": 0, "v3": 0}
    records, changed, missing = [], [], []
    for rel in sorted(pins):
        try:
            raw = (corpus / rel).read_bytes()
        except OSError:
            missing.append(rel)
            continue
        sha = hashlib.sha256(raw).hexdigest()
        if sha != pins[rel]:
            changed.append(rel)
            continue
        records.append({"path": rel, "sha256": sha})
        try:
            record = yaml.safe_load(raw.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError):
            continue
        if not isinstance(record, dict):
            continue
        phrases: dict[str, list[dict]] = {}
        for h in absence_lint.lint(record, v3)["hits"]:
            if h["class"] == RSN:
                phrases.setdefault(h["pointer"], []).append(h)
        for pointer, _, leaf in absence_lint.free_text_leaves(record, scope):
            text = " ".join(leaf.split())
            old = [(m.start(), m.end()) for m in p2.finditer(text)]
            new = [(m.start(), m.end()) for m in p3.regex.finditer(text)]
            totals["v2"] += len(old)
            totals["v3"] += len(new)
            ends = {e for _, e in old}
            if any(e not in ends for _, e in new):
                raise Refused(f"{rel} {pointer}: a v3 match ends where no v2 match does")
            kept = {e for _, e in new}
            for s, e in new:
                ss, se = _sentence(text, s, e)
                kept_rows.append((rel, {"pointer": pointer, "start": s, "end": e, "text": text[s:e],
                                        "patterns": [PATTERN], "sentence": (ss, se)}))
            for s, e in old:
                if e in kept:
                    continue
                ss, se = _sentence(text, s, e)
                flagged = sorted({pid for h in phrases.get(pointer, []) if h["start"] < se and ss < h["end"]
                                  for pid in h["patterns"]})
                why = cause(variants, text, s, e, new)
                admitted = sorted({key for name, _, key in LIFTS
                                   if why not in ("absorbed", "consumed")
                                   and _admits(variants[name], text, s, e)})
                rows.append((rel, {"pointer": pointer, "start": s, "end": e, "text": text[s:e],
                                   "patterns": [PATTERN], "cause": why, "admitted_by": admitted,
                                   "flagged": flagged, "sentence": (ss, se)}))
    if changed or missing:
        raise baseline.Stale(f"{len(changed)} pinned record(s) changed and {len(missing)} gone", changed, missing)
    digest = hashlib.sha256("".join(f"{r['path']} {r['sha256']}\n" for r in records).encode()).hexdigest()
    return {"corpus": corpus, "records": len(records), "record_set_sha256": digest, "rows": rows,
            "kept": kept_rows, "totals": totals}


def draw(found: dict[str, Any], n: int, seed: int, population: str = "rows"
         ) -> dict[str, tuple[int, list[tuple[str, dict]]]]:
    """The seeded draw, shaped as the baseline's so its `draw_sha256` names it:
    of the dropped matches (`rows`), or of the matches v3 keeps (`kept`)."""
    rows = found[population]
    return {RSN: (len(rows), random.Random(seed).sample(rows, min(n, len(rows))))}


def sample(found: dict[str, Any], n: int, seed: int, population: str = "rows") -> list[str]:
    """The draw with each phrase's sentence and a margin, for judging."""
    out, texts = [], {}
    drawn = draw(found, n, seed, population)
    total, picked = drawn[RSN]
    kept = population == "kept"
    out.append(f"## {RSN}: {len(picked)} of {total} {'kept' if kept else 'dropped'} {PATTERN} matches")
    for i, (path, h) in enumerate(picked, 1):
        if path not in texts:
            texts[path] = yaml.safe_load((found["corpus"] / path).read_text(encoding="utf-8"))
        text = " ".join(baseline._at(texts[path], h["pointer"]).split())
        ss, se = h["sentence"]
        lo, hi = max(0, ss - 160), min(len(text), se + 80)
        shown = text[lo:h["start"]] + "[[" + h["text"] + "]]" + text[h["end"]:hi]
        computed = "" if kept else f" cause={h['cause']} flagged={h['flagged']}"
        out.append(f"{i}. {path} {h['pointer']} {h['start']}-{h['end']}{computed}\n   …{shown}…")
    flag = "--kept-sample" if kept else "--sample"
    out.append(f"draw sha256 {baseline.draw_sha256(drawn)} ({flag} {n} --seed {seed})")
    return out


def _seeded_draw(found: dict[str, Any], entry: dict[str, Any], population: str) -> None:
    """Refused unless the entry's `draw_sha256` is the draw its `sample` and
    `seed` make of `population`, recomputed from the pinned records (#3891).
    The baseline's reader ties the file's phrases to the pinned hash; this
    ties the pinned hash to the seed the note prints, so a hand-picked or
    re-seeded set cannot pass as `random.Random(seed).sample`."""
    want = baseline.draw_sha256(draw(found, entry["sample"], entry["seed"], population))
    if want != entry["draw_sha256"]:
        flag = "--kept-sample" if population == "kept" else "--sample"
        raise Refused(f"{entry['judgements']}: its draw {entry['draw_sha256'][:12]}… is not the seeded draw "
                      f"{want[:12]}… that {flag} {entry['sample']} --seed {entry['seed']} makes of the pinned records")


def read_judgements(found: dict[str, Any]) -> dict[str, Any]:
    """The judgement file, checked by the baseline's reader against this
    entry, and each row's computed cause and sentence flags against a fresh
    computation: a row that says otherwise is refused."""
    if found["record_set_sha256"] != RECALL["record_set_sha256"]:
        raise Refused("the pinned record set is not the one the judgements were drawn from")
    try:
        data = baseline.read_judgements(RECALL["lexicon_sha256"], RECALL)
    except baseline.Refused as exc:
        raise Refused(str(exc)) from exc
    if data.get("from_lexicon_sha256") != RECALL["from_lexicon_sha256"]:
        raise Refused(f"{RECALL['judgements']}: from_lexicon_sha256 is not v2's")
    computed = {(p, h["pointer"], h["start"], h["end"]): h for p, h in found["rows"]}
    for row in data["judgements"][RSN]:
        h = computed[(row["record"], row["pointer"], row["start"], row["end"])]
        if READINGS.get(row.get("reading")) != row["verdict"]:
            raise Refused(f"{RECALL['judgements']} #{row.get('n')}: reading {row.get('reading')!r} does not carry "
                          f"the verdict {row['verdict']!r}")
        if row.get("cause") != h["cause"] or row.get("flagged") != h["flagged"]:
            raise Refused(f"{RECALL['judgements']} #{row.get('n')}: cause {row.get('cause')!r} and flagged "
                          f"{row.get('flagged')!r} are not the computed {h['cause']!r} and {h['flagged']!r}")
    _seeded_draw(found, RECALL, "rows")
    return data


def read_kept_judgements(found: dict[str, Any]) -> dict[str, Any]:
    """The kept-match judgement file, checked by the baseline's reader against
    `KEPT`, with each reading carrying its verdict and each phrase a match v3
    keeps (the draw's hash already names them; this says which one is not),
    and the pinned hash the seeded draw of the kept matches (#3891)."""
    if found["record_set_sha256"] != KEPT["record_set_sha256"]:
        raise Refused("the pinned record set is not the one the kept-match judgements were drawn from")
    try:
        data = baseline.read_judgements(KEPT["lexicon_sha256"], KEPT)
    except baseline.Refused as exc:
        raise Refused(str(exc)) from exc
    kept = {(p, h["pointer"], h["start"], h["end"]) for p, h in found["kept"]}
    for row in data["judgements"][RSN]:
        if (row["record"], row["pointer"], row["start"], row["end"]) not in kept:
            raise Refused(f"{KEPT['judgements']} #{row.get('n')}: not a match v3 keeps")
        if READINGS.get(row.get("reading")) != row["verdict"]:
            raise Refused(f"{KEPT['judgements']} #{row.get('n')}: reading {row.get('reading')!r} does not carry "
                          f"the verdict {row['verdict']!r}")
    _seeded_draw(found, KEPT, "kept")
    return data


def wilson(k: int, n: int, z: float = _Z95) -> tuple[float, float]:
    """The Wilson score interval for k successes in n draws."""
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def render_markdown(found: dict[str, Any]) -> str:
    data = read_judgements(found)
    kept_data = read_kept_judgements(found)
    kept_rows = kept_data["judgements"][RSN]
    rows = data["judgements"][RSN]
    totals, n_dropped, kept = found["totals"], len(found["rows"]), found["totals"]["v3"]
    in_class = [r for r in rows if r["verdict"] == "in_class"]
    lost = [r for r in in_class if not r["flagged"]]
    census = len(rows) == n_dropped
    lines = [
        "# Absence lexicon v3: the recall `rsn.source-ranking` gives up",
        "",
        "Generated by `scripts/absence_v3_recall.py` (#3705). Do not edit by hand: run the script",
        "to regenerate it, or `--check` to ask whether it still matches its records and judgements.",
        "",
        f"- **Lexicons:** absence_self_narration v2 (sha256 `{RECALL['from_lexicon_sha256']}`) and",
        f"  v3 (sha256 `{RECALL['lexicon_sha256']}`), both registered; this note registers nothing",
        "  and moves no count in `notes/absence_claims_baseline.md`.",
        f"- **Records:** the {found['records']} records that note pins, record-set sha256",
        f"  `{found['record_set_sha256']}`.",
        f"- **Dropped matches:** v2 matches `{PATTERN}` {totals['v2']} times and v3 {kept} times; the "
        f"{n_dropped} v2",
        "  matches no v3 match of the pattern ends at, in the same leaf, are the dropped ones. Every v3",
        "  match ends at a v2 match, so they are the difference.",
        f"- **Draw:** `--sample {RECALL['sample']} --seed {RECALL['seed']}`, sha256 `{RECALL['draw_sha256']}`"
        + (": every dropped match." if census else f": {len(rows)} of {n_dropped} dropped matches."),
        f"- **Judgements:** `{RECALL['judgements']}`, recorded {data['recorded']}. One rater, the agent",
        "  implementing #3705, reading each phrase in its sentence and the sentences around it: not an",
        "  independent review.",
        "",
        "Each phrase's sentence was read as written, to its full stop, a clause after `;` included.",
        "Its *reading*, and the verdict that follows from it:",
        "",
        "- `construction` (in class): the sentence says what the record did (preferred, used, recorded,",
        "  left a slot empty) and the ranking term bears on it.",
        "- `referent` (in class): the sentence says which dataset or release this record describes,",
        "  justified by the ranking, judged in class as the v1 and v3 precision samples judged it.",
        "- `source` (borderline): the sentence reports the sources (a conflict, a rank, what one states)",
        "  and says nothing of what the record did; v1's precision sample judged its three phrases of",
        "  this kind borderline, and v3 made them counterexamples.",
        "- `absence` (not in class): an absence asserted across the sources (\"no tier-1 source states",
        "  them\"), which `bundle_wide_absence` describes.",
        "",
        "## By reading",
        "",
        "*Sentence flagged* means another v3 record_self_narration phrase overlaps the term's sentence,",
        "to its full stop as it was judged, so v3 still counts that sentence though not this term.",
        "",
        "| reading | verdict | dropped | sentence flagged by v3 | sentence not flagged |",
        "|---|---|---:|---:|---:|",
    ]
    for reading, verdict in READINGS.items():
        rs = [r for r in rows if r["reading"] == reading]
        lines.append(f"| {reading} | {verdict} | {len(rs)} | {sum(bool(r['flagged']) for r in rs)} | "
                     f"{sum(not r['flagged'] for r in rs)} |")
    lines.append(f"| **all** | | {len(rows)} | {sum(bool(r['flagged']) for r in rows)} | "
                 f"{sum(not r['flagged'] for r in rows)} |")
    lines += [
        "",
        "## By cause",
        "",
        "The cause is computed, not judged: the v3 regex with its bounds lifted in turn, as the",
        "script's docstring defines. The bounds are cumulative. An unbounded window admits the `window`",
        "rows; one that also crosses `;` admits the `semicolon` rows; `other_sentence` needs it to cross",
        "a full stop, and `no_verb` a verb the list lacks. Each admits its rows whatever their reading,",
        "on a listed verb anywhere in reach, which need not be the verb the sentence turns on.",
        "`absorbed` and `consumed` need no bound lifted.",
        "",
        "| cause | dropped | construction | referent | source | absence | in class, sentence not flagged |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for cz in CAUSES:
        cs = [r for r in rows if r["cause"] == cz]
        tally = Counter(r["reading"] for r in cs)
        lines.append(f"| `{cz}` | {len(cs)} | " + " | ".join(str(tally[k]) for k in READINGS)
                     + f" | {sum(1 for r in cs if r in lost)} |")
    computed = {(p, h["pointer"], h["start"], h["end"]): h for p, h in found["rows"]}
    admitted = {r["n"]: computed[(r["record"], r["pointer"], r["start"], r["end"])]["admitted_by"] for r in rows}
    lines += [
        "",
        "## What each change would admit",
        "",
        "Each possible change to v3's rule is its regex with that change made, run over the dropped",
        "rows as the cause is (`absorbed` and `consumed` rows need no bound lifted and are left out).",
        "The first three rows lift one bound and keep the others as v3 spells them. The last three",
        "lift them cumulatively, in the causes' order, so each includes the rows above it; their",
        "counts are the cause table's rows summed. The two readings differ: the `semicolon` rows",
        "are the ones that need *both* the window widened and `;` crossed, so crossing `;` alone",
        "admits only some of them. A single lift can also admit a row of another cause, through a",
        "listed verb it brings into reach that is not the one the sentence turns on.",
        "",
        "| change | admits | construction | referent | source | absence | in class, sentence not flagged |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for i, (_, label, key) in enumerate(LIFTS):
        if i == 3:
            lines.append("| *cumulative* | | | | | | |")
        cs = [r for r in rows if key in admitted[r["n"]]]
        tally = Counter(r["reading"] for r in cs)
        lines.append(f"| {label} | {len(cs)} | " + " | ".join(str(tally[k]) for k in READINGS)
                     + f" | {sum(1 for r in cs if r in lost)} |")
    lines += [
        "",
        "A verb the list lacks is not a bound: the "
        f"{sum(r['cause'] == 'no_verb' for r in rows)} `no_verb` rows are admitted by none of",
        "these, and what adding verbs would admit depends on which verbs.",
    ]
    n_kept = len(kept_rows)
    k_in = sum(r["verdict"] == "in_class" for r in kept_rows)
    kept_census = n_kept == kept
    # A census has no sampling error; a sample's interval ignores the finite
    # population, so it is wider than it need be.
    lo, hi = (k_in / n_kept,) * 2 if kept_census else wilson(k_in, n_kept)
    lines += [
        "",
        "## Precision of the kept matches",
        "",
        f"- **Draw:** `--kept-sample {KEPT['sample']} --seed {KEPT['seed']}`, sha256 `{KEPT['draw_sha256']}`"
        + (": every kept match." if kept_census else f": {n_kept} of the {kept} matches v3 keeps (#3793)."),
        f"- **Judgements:** `{KEPT['judgements']}`, recorded {kept_data['recorded']}. One rater, the agent",
        "  implementing #3793, reading each phrase with the readings above: not an independent review.",
        "",
        "| reading | verdict | kept, drawn |",
        "|---|---|---:|",
    ]
    for reading, verdict in READINGS.items():
        lines.append(f"| {reading} | {verdict} | {sum(r['reading'] == reading for r in kept_rows)} |")
    lines += [
        f"| **all** | | {n_kept} |",
        "",
        f"{k_in} of the {n_kept} drawn are in class: a precision of {100 * k_in / n_kept:.1f}% "
        + ("" if kept_census else f"(Wilson 95% interval {100 * lo:.1f}% to {100 * hi:.1f}%)"),
        "for the matches v3 keeps of this pattern.",
    ]
    if k_in < n_kept and all(r["reading"] == "source" for r in kept_rows if r["verdict"] != "in_class"):
        lines[-1] += (" The rest are borderline: sentences that report what a source, or the manifest,"
                      "\nstates and say nothing of what the record did.")
    est, est_lo, est_hi = (kept * p for p in (k_in / n_kept, lo, hi))
    recall = lambda x: 100 * x / (x + len(in_class))  # noqa: E731
    lines += [
        "",
        "## Recall",
        "",
        f"Of the {len(rows)} dropped matches, {len(in_class)} are in class, "
        f"{sum(r['verdict'] == 'borderline' for r in rows)} borderline and "
        f"{sum(r['verdict'] == 'not_in_class' for r in rows)} not in class.",
        f"v3 therefore gives up {len(in_class)} in-class matches of `{PATTERN}`. If all {kept} of v3's matches",
        f"were in class it would keep {kept} of {kept + len(in_class)} "
        f"({recall(kept):.1f}%) of the in-class matches v2 had; that is the upper bound.",
        f"At the measured precision it keeps an estimated {est:.0f} in-class matches ({kept} × {k_in}/{n_kept}),",
        f"so its recall of this pattern relative to v2 is an estimated **{recall(est):.1f}%**"
        + (". Borderline phrases are counted" if kept_census else ""),
    ] + ([] if kept_census else [
        f"({recall(est_lo):.1f}% to {recall(est_hi):.1f}% over the precision's interval, which carries only the",
        "sampling error of the kept draw: the dropped matches are a census). Borderline phrases are counted",
    ]) + [
        "in class on neither side, kept or dropped.",
        "",
        f"By sentence the loss is smaller. {len(in_class) - len(lost)} of the {len(in_class)} in-class "
        "phrases sit in a sentence another v3",
        f"record_self_narration phrase still flags; {len(lost)} do not, and v3 counts nothing in their",
        "sentences.",
        "",
        "Whether a v4 should widen the window, cross `;` or add verbs is the owner's call (#3705). The",
        "cause table and the change table are the evidence for it: what each lifted bound would",
        "recover in class, on its own and on top of the others, and what it would also admit.",
        "`absorbed` terms are still inside a flagged span, and `consumed` ones are",
        "the non-overlap `notes/absence_lexicon_v3_2026-09-30.md` describes (#3732).",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="read-only: exit 1 when the note is stale")
    mode.add_argument("--sample", type=baseline._count, metavar="N",
                      help="read-only: print N dropped matches with context, and the draw's sha256")
    mode.add_argument("--kept-sample", type=baseline._count, metavar="N",
                      help="read-only: print N of the matches v3 keeps with context, and the draw's sha256")
    ap.add_argument("--seed", type=int, metavar="S",
                    help=f"the draw's seed (default {baseline.SAMPLE_SEED}); refused without --sample "
                         "or --kept-sample")
    args = ap.parse_args(argv)
    if args.seed is not None and args.sample is None and args.kept_sample is None:
        ap.error("--seed applies only with --sample or --kept-sample")
    try:
        found = dropped(baseline.CORPUS, baseline.read_pins(baseline.PINS))
    except (baseline.Stale, Refused) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    seed = baseline.SAMPLE_SEED if args.seed is None else args.seed
    if args.sample is not None:
        print("\n".join(sample(found, args.sample, seed)))
        return 0
    if args.kept_sample is not None:
        print("\n".join(sample(found, args.kept_sample, seed, "kept")))
        return 0
    try:
        text = render_markdown(found)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    if args.check:
        if not OUT_MD.exists() or OUT_MD.read_text(encoding="utf-8") != text:
            print(f"stale: {baseline._shown(OUT_MD)} does not match; run scripts/absence_v3_recall.py",
                  file=sys.stderr)
            return 1
        print(f"{baseline._shown(OUT_MD)} is current")
        return 0
    OUT_MD.write_text(text, encoding="utf-8")
    print(f"wrote {baseline._shown(OUT_MD)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
