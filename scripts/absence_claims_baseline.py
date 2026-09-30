#!/usr/bin/env python
"""Offline baseline of the absence lint over a pinned set of records (#2919).

Counts, by method directory, the full records under `data/d4d_concatenated/`
whose free-text leaves carry a bundle-wide absence claim or record
self-narration as the registered lexicon `absence_self_narration` defines
them (`data_sheets_schema.absence_lint`), and writes the table to
`notes/absence_claims_baseline.md`. The records are only read.

The note counts a pinned record set, not whatever the corpus holds today
(#3045). `notes/absence_claims_baseline_records.yaml` names each record it
counts by its path under the corpus and the sha256 of its bytes. A record
added to the corpus later is reported and not counted, so a data PR that only
adds records leaves the note current. A pinned record whose bytes changed, or
that is gone, makes the note stale: its counts would no longer describe the
bytes at that path. `--repin` selects the corpus as it stands and rewrites
both files. It is the one act that moves the baseline to other records.

The note counts under one named lexicon version, `LEXICON_VERSION`, not
whichever is newest (#3132): its precision table was judged under that
version's bytes. A later registered version is named in the note, so
registering one still makes the note stale until it is regenerated; moving
the counts to it is a deliberate change of `LEXICON_VERSION`, after which
the precision table reads unchecked until a sample is judged under the new
bytes.

A precision table is rendered only beside its per-phrase judgements (#3197):
the entry names a judgements file whose phrases must be the draw it names,
and whose verdict tally must equal its counts; otherwise the note is refused.

The note is regenerated, never edited by hand. A corpus-lane test rebuilds it
from the pinned records and fails when a pinned record changed or is gone, or
when the committed bytes differ. A new lexicon version therefore shows up as
a stale note rather than as a table that quietly describes other patterns.

Usage:
    poetry run python scripts/absence_claims_baseline.py            # rewrite the note from the pinned records
    poetry run python scripts/absence_claims_baseline.py --repin    # pin the corpus as it stands, then write both files
    poetry run python scripts/absence_claims_baseline.py --check    # read-only: exit 1 when stale
    poetry run python scripts/absence_claims_baseline.py --sample 50 --seed 2919
        # read-only: print a seeded sample of the pinned records' phrases per
        # class, with context, for a precision check, and the draw's sha256
        # last; writes nothing. N is at least 1, and --seed is refused
        # without --sample, so neither falls through to the rewrite (#3173).
"""
from __future__ import annotations

import argparse
import hashlib
import random
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema import absence_lint  # noqa: E402
from data_sheets_schema import lexicon as lx  # noqa: E402

CORPUS = ROOT / "data" / "d4d_concatenated"
OUT_MD = ROOT / "notes" / "absence_claims_baseline.md"
PINS = ROOT / "notes" / "absence_claims_baseline_records.yaml"
RECORD_GLOB = "*_d4d.yaml"
SAMPLE_SEED = 2919
#: The registered version of the lexicon the note counts under (#3132): v4
#: since #3791 (v3 from #3520), whose precision sample is judged in its own
#: file below.
LEXICON_VERSION = 4
#: A judgement's verdicts, in the order a precision entry's counts give them.
VERDICTS = ("in_class", "borderline", "not_in_class")
_SHA256 = re.compile(r"[0-9a-f]{64}")

#: Hand-checked precision samples, keyed by the lexicon sha256 they were drawn
#: under, so a note regenerated under another lexicon says none was checked
#: rather than repeating a figure that describes other patterns. Each sample is
#: `--sample {sample} --seed {seed}` over the pinned records named by
#: `record_set_sha256`; a note over another record set says the sample was
#: drawn from another one. Each phrase was read in context against its class
#: definition by the agent that registered the lexicon — not an independent
#: review. It measures class membership, not whether a statement should be
#: removed: a source conflict is legitimate content for `source_caveats`, and
#: one worded with the ranking vocabulary is still counted in
#: `record_self_narration`, as borderline. Class values: (in class,
#: borderline, not in class). `draw_sha256` names the phrases drawn
#: (`draw_sha256()`); a corpus test re-draws the sample from the pinned
#: records and compares it (#3173). The v1 value is the draw this code makes
#: over the record set named beside it; that it is the draw judged on the
#: date checked rests on the round-1 comparison of the printed sample
#: (#3045), not on anything recorded that day. `judgements` names the file
#: of per-phrase verdicts over that draw (#3197); `read_judgements` refuses an
#: entry whose file does not name this draw or whose tally is not `classes`.
#: The v3 entry (#3520) is over the same record set and seed; its verdicts
#: were written down per phrase when it was checked.
PRECISION: dict[str, dict[str, Any]] = {
    "7b5c2237df5a0c2fa71446f472abb8aefc7458ea5c9d9f15228f172b5325ef1e": {     # v1
        "checked": "2026-09-28",
        "record_set_sha256": "cb4b5b8ae826da7ec9ede78ffc920725df39e6b9a3140b18ca01e54b54a6b711",   # 303 records
        "sample": 50, "seed": SAMPLE_SEED,
        "draw_sha256": "99c92000a3c2ca4b27c8ab5ab6e345d1f3971684249767a5723d5dba4a961577",
        "classes": {"bundle_wide_absence": (50, 0, 0), "record_self_narration": (47, 3, 0)},
        "note": "The three borderline phrases are source conflicts worded with the ranking "
                "vocabulary (\"two tier-1 sources disagree\").",
        "judgements": "notes/absence_precision_judgements_99c92000.yaml",
    },
    "f1657b94067ebb8fbdfd83bccdad1780b83d1b9e8dba245664b9fe54d41df7b6": {     # v3 (#3520)
        "checked": "2026-09-30",
        "record_set_sha256": "cb4b5b8ae826da7ec9ede78ffc920725df39e6b9a3140b18ca01e54b54a6b711",   # 303 records
        "sample": 50, "seed": SAMPLE_SEED,
        "draw_sha256": "bd0c63eda8bc7d9700fedd2695a7fab4bb472810302b397274ccb2fc94b4b8a8",
        "classes": {"bundle_wide_absence": (50, 0, 0), "record_self_narration": (50, 0, 0)},
        "note": "v3 changes no bundle_wide_absence pattern, and that class's draw is the v1 draw phrase for "
                "phrase; its verdicts are carried over from the v1 judgements, not re-read.",
        "judgements": "notes/absence_precision_judgements_bd0c63ed.yaml",
    },
    "483950709a000f4f13c3f8f7638acd1baa06d6acd1be68edd9279721ec1bd83f": {     # v4 (#3791)
        "checked": "2026-09-30",
        "record_set_sha256": "cb4b5b8ae826da7ec9ede78ffc920725df39e6b9a3140b18ca01e54b54a6b711",   # 303 records
        "sample": 50, "seed": SAMPLE_SEED,
        "draw_sha256": "574f03c232ebf949de942601a97403b977ff193144cd8f4c453f868c7e1695c5",
        "classes": {"bundle_wide_absence": (50, 0, 0), "record_self_narration": (49, 1, 0)},
        "note": "v4 changes no bundle_wide_absence pattern, and that class's draw is the v1 and v3 draw phrase "
                "for phrase; its verdicts are carried over, not re-read. The borderline record_self_narration "
                "phrase is a name of the declared ranking in a sentence that reports the sources, which v2 to v4 "
                "all match without a verb (#3706).",
        "judgements": "notes/absence_precision_judgements_574f03c2.yaml",
    },
}


class Refused(Exception):
    """A precision entry its per-phrase judgements do not bear out (#3197):
    no judgements file, one naming another draw, or a tally that is not the
    entry's counts. The note is not rendered over it."""


class Stale(Exception):
    """The pinned record set cannot be counted as pinned: a pinned record
    changed or is gone, or the pin file is missing or malformed."""

    def __init__(self, message: str, changed: list[str] | None = None, missing: list[str] | None = None):
        super().__init__(message)
        self.changed = changed or []
        self.missing = missing or []


def record_paths(corpus: Path) -> list[Path]:
    """The full records: `*_d4d.yaml` in each method directory that does not
    end `_core`, and one label directory below it. Sorted, so the table and
    the record-set digest do not depend on directory order."""
    found: list[Path] = []
    for method in sorted(p for p in corpus.iterdir() if p.is_dir() and not p.name.endswith("_core")):
        found.extend(method.glob(RECORD_GLOB))
        found.extend(method.glob(f"*/{RECORD_GLOB}"))
    return sorted(found, key=lambda p: p.relative_to(corpus).as_posix())


def current_records(corpus: Path) -> dict[str, str]:
    """Every full record the corpus holds now, as the pins `--repin` writes:
    its path under the corpus -> the sha256 of its bytes."""
    return {p.relative_to(corpus).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in record_paths(corpus)}


def unpinned(corpus: Path, pins: dict[str, str]) -> list[str]:
    """The full records the corpus holds that the pins do not name: reported,
    never counted and never stale."""
    return [p.relative_to(corpus).as_posix() for p in record_paths(corpus)
            if p.relative_to(corpus).as_posix() not in pins]


def read_pins(path: Path | None = None) -> dict[str, str]:
    """The pinned record set: path under the corpus -> sha256. A pin file that
    is missing or malformed raises `Stale`: there is then no record set the
    note can be said to count."""
    path = path or PINS
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise Stale(f"{_shown(path)} could not be read ({exc.strerror})") from exc
    except yaml.YAMLError as exc:
        raise Stale(f"{_shown(path)} does not parse") from exc
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, dict) or not records:
        raise Stale(f"{_shown(path)} has no `records` mapping")
    for rel, sha in records.items():
        parts = PurePosixPath(rel).parts if isinstance(rel, str) else ()
        if (not parts or PurePosixPath(rel).is_absolute() or ".." in parts
                or not isinstance(sha, str) or not _SHA256.fullmatch(sha)):
            raise Stale(f"{_shown(path)}: {rel!r} is not a path under the corpus pinned to a sha256")
    return dict(records)


def write_pins(pins: dict[str, str], path: Path | None = None) -> None:
    """Write the pinned record set, sorted by path, under a header naming it."""
    path = path or PINS
    header = (f"# The records {_shown(OUT_MD)} counts (#2919, #3045): each full record's path\n"
              f"# under {_shown(CORPUS)}/ and the sha256 of its bytes. Written by\n"
              "# scripts/absence_claims_baseline.py --repin; never edited by hand. A record added to\n"
              "# the corpus later is not counted until the set is re-pinned.\n")
    body = yaml.safe_dump({"records": dict(sorted(pins.items()))}, sort_keys=False, width=1000)
    path.write_text(header + body, encoding="utf-8")


def collect(corpus: Path = CORPUS, lexicon: lx.Lexicon | None = None,
            pins: dict[str, str] | None = None) -> dict[str, Any]:
    """Lint the pinned records; keep each result beside its path, method and hash.

    Without `pins`, the records the corpus holds now, as `--repin` would pin
    them. A pinned record whose bytes are not its pin, or that is gone,
    raises `Stale` naming each, rather than being counted as bytes the pins
    do not name or dropped from a count that claims it.
    """
    lexicon = lexicon or lx.load(absence_lint.LEXICON, LEXICON_VERSION)
    pins = current_records(corpus) if pins is None else pins
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
        row: dict[str, Any] = {"path": rel, "method": rel.split("/", 1)[0],
                               "sha256": sha, "result": None, "error": None}
        try:
            data = yaml.safe_load(raw.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            row["error"] = type(exc).__name__
        else:
            if isinstance(data, dict):
                row["result"] = absence_lint.lint(data, lexicon)
            else:
                row["error"] = "not a mapping"
        records.append(row)
    if changed or missing:
        raise Stale(f"{len(changed)} pinned record(s) changed and {len(missing)} gone: "
                    + "; ".join([f"changed {r}" for r in changed] + [f"gone {r}" for r in missing]),
                    changed, missing)
    digest = hashlib.sha256("".join(f"{r['path']} {r['sha256']}\n" for r in records).encode()).hexdigest()
    return {"lexicon": lexicon, "corpus": corpus, "records": records, "record_set_sha256": digest}


def summarise(collected: dict[str, Any]) -> dict[str, Any]:
    lexicon: lx.Lexicon = collected["lexicon"]
    classes = list(lexicon.classes)
    methods: dict[str, dict[str, Any]] = {}
    patterns = {p.id: {"class": p.cls, "matches": 0, "records": 0} for p in lexicon.patterns}
    unreadable = []
    for row in collected["records"]:
        m = methods.setdefault(row["method"], {"records": 0, "unreadable": 0, "any": 0, "leaves": 0,
                                               **{c: {"records": 0, "phrases": 0} for c in classes}})
        m["records"] += 1
        result = row["result"]
        if result is None:
            m["unreadable"] += 1
            unreadable.append(f"{row['path']} ({row['error']})")
            continue
        m["leaves"] += result["leaves"]
        m["any"] += bool(result["phrases"])
        for c in classes:
            n = result["by_class"][c]["phrases"]
            m[c]["phrases"] += n
            m[c]["records"] += bool(n)
        for pid, n in result["by_pattern"].items():
            patterns[pid]["matches"] += n
            patterns[pid]["records"] += bool(n)
    total = {"records": 0, "unreadable": 0, "any": 0, "leaves": 0, **{c: {"records": 0, "phrases": 0} for c in classes}}
    for m in methods.values():
        for key in ("records", "unreadable", "any", "leaves"):
            total[key] += m[key]
        for c in classes:
            total[c]["records"] += m[c]["records"]
            total[c]["phrases"] += m[c]["phrases"]
    return {"classes": classes, "methods": dict(sorted(methods.items())), "total": total,
            "patterns": patterns, "unreadable": unreadable}


def _shown(path: Path) -> str:
    """A path as the note and the messages spell it: repository-relative
    where it is under the checkout, else as given. The default corpus is
    spelled under ROOT before any symlink is resolved, so a linked `data/`
    does not change the note's bytes."""
    for candidate in (path, path.resolve()):
        try:
            return candidate.relative_to(ROOT).as_posix()
        except ValueError:
            continue
    return str(path)


def render_markdown(collected: dict[str, Any]) -> str:
    lexicon: lx.Lexicon = collected["lexicon"]
    corpus: Path = collected["corpus"]
    s = summarise(collected)
    classes = s["classes"]
    t = s["total"]
    lines = [
        "# Absence claims and record self-narration: corpus baseline",
        "",
        "Generated by `scripts/absence_claims_baseline.py` (#2919). Do not edit by hand: run the",
        "script to regenerate it, or `--check` to ask whether it still matches its pinned records.",
        "",
        f"- **Instrument:** {lexicon.instrument}",
        f"- **Lexicon:** `src/data_sheets_schema/lexicons/{lexicon.file}`, sha256 `{lexicon.sha256}`",
        f"- **Records:** {t['records']} full records, pinned by path and sha256 in `{_shown(PINS)}`;",
        f"  record-set sha256 `{collected['record_set_sha256']}` over each record's path and bytes.",
        f"  `--repin` pins every `{RECORD_GLOB}` under `{_shown(corpus)}/` in a method directory whose",
        "  name does not end `_core`, and one label directory below it. A record added since the last",
        "  `--repin` is reported by `--check` and not counted here; a pinned record that changed or is",
        "  gone makes this note stale (#3045).",
        "- **Leaves:** " + _leaves_sentence(lexicon.scope),
        *_later_versions(lexicon),
        "",
        "**Regex caveat.** Every count here is a regular-expression match over whitespace-collapsed",
        "text, not a reviewed finding. The lexicon misses phrasings it does not list, and it matches",
        "some sentences that are not defects: a quoted source sentence, a dataset fact that happens",
        "to use the phrase, a source conflict worded with the ranking vocabulary. Counts compare",
        "only with counts made under the same lexicon sha256. The count in #2919 (84 of 303",
        "records) came from other patterns and does not compare with these. The lint is never",
        "gating, and nothing here writes a record or a provenance block.",
        "",
        "A *phrase* is a maximal span that one or more patterns of one class match in one leaf. A",
        "record counts in a class when it has at least one phrase of that class. A record whose",
        "text repeats a mapping key is read as parsed, where the last value wins (#1029).",
        "",
        "## By method",
        "",
        "| method | records | with any phrase | "
        + " | ".join(f"{c}: records | {c}: phrases" for c in classes) + " | free-text leaves |",
        "|---|---:|---:|" + "---:|---:|" * len(classes) + "---:|",
    ]
    for name, m in list(s["methods"].items()) + [("**all**", t)]:
        lines.append(f"| {name} | {m['records']} | {m['any']} | "
                     + " | ".join(f"{m[c]['records']} | {m[c]['phrases']}" for c in classes)
                     + f" | {m['leaves']} |")
    if t["unreadable"]:
        lines += ["", f"{t['unreadable']} record(s) did not parse as a mapping and are counted in "
                  "`records` only: " + "; ".join(f"`{u}`" for u in s["unreadable"]) + "."]
    lines += [
        "",
        "## By pattern",
        "",
        "Raw matches: a phrase two patterns match counts once under each of them.",
        "",
        "| pattern | class | matches | records |",
        "|---|---|---:|---:|",
    ]
    for pid, p in s["patterns"].items():
        lines.append(f"| `{pid}` | {p['class']} | {p['matches']} | {p['records']} |")
    lines += ["", "## Precision", ""]
    checked = PRECISION.get(lexicon.sha256)
    if not checked:
        lines.append("No precision sample has been checked under this lexicon's sha256.")
    else:
        drawn = (["It was drawn from the record set this note counts."]
                 if checked["record_set_sha256"] == collected["record_set_sha256"] else
                 ["It was drawn from another record set (record-set sha256",
                  f"`{checked['record_set_sha256']}`), not the one this note counts."])
        lines += [
            f"A seeded sample (`--sample {checked['sample']} --seed {checked['seed']}`) of each class's "
            "phrases, checked",
            f"{checked['checked']}. Each phrase was read in context against its class definition by",
            "the agent that registered the lexicon, not by an independent reviewer. The sample",
            "measures class membership, not whether a statement should be removed.",
            *drawn,
            "The draw's sha256, over each drawn phrase's class, record, pointer and span in order, is",
            f"`{checked['draw_sha256']}`; `--sample` prints it last.",
            "",
            "| class | in class | borderline | not in class |",
            "|---|---:|---:|---:|",
        ]
        judged = read_judgements(lexicon.sha256, checked)
        for c in classes:
            if c in checked["classes"]:
                a, b, n = checked["classes"][c]
                lines.append(f"| {c} | {a} | {b} | {n} |")
        if checked.get("note"):
            lines += ["", checked["note"]]
        lines += [
            "",
            *_judgements_sentence(checked, judged),
        ]
    return "\n".join(lines) + "\n"


def _judgements_sentence(checked: dict[str, Any], judged: dict[str, Any]) -> list[str]:
    """Where the per-phrase verdicts are and when they were written down: on
    the day the sample was checked (v3, #3520), or on a later reading of the
    same draw (v1, whose verdicts were not written down per phrase, #3197)."""
    lines = [f"Each phrase's verdict and reason are in `{checked['judgements']}`, recorded"]
    if judged["recorded"] == checked["checked"]:
        return lines + [f"{judged['recorded']} when the sample was checked; the table is rendered only while their "
                        "tally equals it (#3197)."]
    return lines + [
        f"{judged['recorded']} by reading this draw again. They are not the {checked['checked']} judgements, which",
        "were not written down per phrase; the table is rendered only while their tally equals it (#3197).",
    ]


def _later_versions(lexicon: lx.Lexicon) -> list[str]:
    """The note's line naming registered versions newer than the one it
    counts under, or none: a new version makes the note stale without
    moving its counts (#3132)."""
    later = [e for e in lx.registered().get(lexicon.name, []) if e["version"] > lexicon.version]
    if not later:
        return []
    named = "; ".join(f"v{e['version']} (`{e['file']}`, sha256 `{e['sha256']}`)"
                      for e in sorted(later, key=lambda e: e["version"]))
    return [f"- **Later versions:** {named}. This note counts under v{lexicon.version}, the version",
            "  its precision sample was judged under; counting under a later one is a deliberate change of",
            "  the script's `LEXICON_VERSION`, and its precision table then reads unchecked until a sample is",
            "  judged under those bytes."]


def read_judgements(lexicon_sha256: str, checked: dict[str, Any]) -> dict[str, Any]:
    """The per-phrase judgements a precision entry names, checked against it.

    Refused unless the file names the entry's draw, lexicon, record set,
    sample and seed; its phrases, in its order, hash to the entry's
    `draw_sha256`; every phrase has a verdict from `VERDICTS` and a reason;
    and each class's verdict tally is the entry's counts (#3197).
    """
    rel = checked.get("judgements")
    if not rel:
        raise Refused("the precision entry names no judgements file")
    path = ROOT / rel
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise Refused(f"{_shown(path)} could not be read ({exc.strerror})") from exc
    except yaml.YAMLError as exc:
        raise Refused(f"{_shown(path)} does not parse") from exc
    if not isinstance(data, dict) or not isinstance(data.get("judgements"), dict):
        raise Refused(f"{_shown(path)} has no `judgements` mapping")
    if not isinstance(data.get("recorded"), str):
        raise Refused(f"{_shown(path)} does not say when its verdicts were recorded")
    for key, want in (("draw_sha256", checked["draw_sha256"]), ("lexicon_sha256", lexicon_sha256),
                      ("record_set_sha256", checked["record_set_sha256"]), ("sample", checked["sample"]),
                      ("seed", checked["seed"])):
        if data.get(key) != want:
            raise Refused(f"{_shown(path)}: {key} is {data.get(key)!r}, not the precision entry's {want!r}")
    if set(data["judgements"]) != set(checked["classes"]):
        raise Refused(f"{_shown(path)} judges classes {sorted(data['judgements'])}, "
                      f"not the precision entry's {sorted(checked['classes'])}")
    drawn: dict[str, tuple[int, list[tuple[str, dict]]]] = {}
    tally: dict[str, tuple[int, ...]] = {}
    for cls in checked["classes"]:
        rows = data["judgements"][cls]
        if not isinstance(rows, list) or len(rows) > checked["sample"]:
            raise Refused(f"{_shown(path)}: {cls} is not a list of at most {checked['sample']} judgements")
        counts = dict.fromkeys(VERDICTS, 0)
        for row in rows:
            if (not isinstance(row, dict) or row.get("verdict") not in VERDICTS
                    or not isinstance(row.get("reason"), str) or not row["reason"].strip()
                    or not {"record", "pointer", "start", "end"} <= set(row)):
                raise Refused(f"{_shown(path)}: a {cls} judgement needs record, pointer, start, end, a reason "
                              f"and a verdict from {list(VERDICTS)}")
            counts[row["verdict"]] += 1
        drawn[cls] = (len(rows), [(row["record"], row) for row in rows])
        tally[cls] = tuple(counts[v] for v in VERDICTS)
    if draw_sha256(drawn) != checked["draw_sha256"]:
        raise Refused(f"{_shown(path)}: its phrases are not the draw {checked['draw_sha256'][:12]}… it names")
    counted = {cls: tuple(v) for cls, v in checked["classes"].items()}
    if tally != counted:
        raise Refused(f"{_shown(path)}: the verdict tally {tally} is not the precision entry's counts {counted}")
    return data


def _leaves_sentence(scope: dict[str, Any]) -> str:
    keys = ", ".join(f"`{k}`" for k in scope["free_text_keys"])
    suffixes = ", ".join(f"`*{s}`" for s in scope["free_text_key_suffixes"])
    excluded = [f"`{k}`" for k in scope["excluded_keys"]]
    excluded_text = ", ".join(excluded[:-1]) + " or " + excluded[-1] if len(excluded) > 1 else "".join(excluded)
    return f"{keys} and every {suffixes}, at any depth; never inside {excluded_text}"


def draw(collected: dict[str, Any], n: int, seed: int) -> dict[str, tuple[int, list[tuple[str, dict]]]]:
    """Each class's phrase count and its seeded draw of up to `n` phrases.

    The population is the class's phrases in the order `collect` holds them
    (record path, then as the lint reports them), and the draw is
    `random.Random(seed).sample` over it, one generator per class.
    """
    drawn: dict[str, tuple[int, list[tuple[str, dict]]]] = {}
    for cls in collected["lexicon"].classes:
        hits = [(row["path"], h) for row in collected["records"] if row["result"]
                for h in row["result"]["hits"] if h["class"] == cls]
        drawn[cls] = (len(hits), random.Random(seed).sample(hits, min(n, len(hits))))
    return drawn


def draw_sha256(drawn: dict[str, tuple[int, list[tuple[str, dict]]]]) -> str:
    """Which phrases a draw holds, in its order: the sha256 over each one's
    class, record, pointer and span. How the sample is printed does not move
    it; drawing other phrases, or the same ones in another order, does."""
    return hashlib.sha256("".join(
        f"{cls}\t{path}\t{h['pointer']}\t{h['start']}\t{h['end']}\n"
        for cls, (_, picked) in drawn.items() for path, h in picked).encode()).hexdigest()


def sample(collected: dict[str, Any], n: int, seed: int) -> list[str]:
    """A seeded sample of each class's phrases, each with its context, and
    the draw's sha256 last."""
    out: list[str] = []
    texts: dict[str, dict] = {}
    drawn = draw(collected, n, seed)
    for cls, (total, picked) in drawn.items():
        out.append(f"## {cls}: {len(picked)} of {total} phrases")
        for i, (path, h) in enumerate(picked, 1):
            if path not in texts:
                texts[path] = yaml.safe_load((collected["corpus"] / path).read_text(encoding="utf-8"))
            text = " ".join(_at(texts[path], h["pointer"]).split())
            before, after = text[max(0, h["start"] - 110):h["start"]], text[h["end"]:h["end"] + 70]
            out.append(f"{i}. {path} {h['pointer']} {h['patterns']}\n   …{before}[[{h['text']}]]{after}…")
    out.append(f"draw sha256 {draw_sha256(drawn)} (--sample {n} --seed {seed})")
    return out


def _count(text: str) -> int:
    """`--sample N`: a count of at least one. `--sample 0` asked for no sample
    and was read as no `--sample` at all, which rewrote the note (#3173)."""
    try:
        n = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not an integer") from None
    if n < 1:
        raise argparse.ArgumentTypeError(f"{n} is not a count of at least 1")
    return n


def _at(record: Any, pointer: str) -> str:
    node = record
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        node = node[int(token)] if isinstance(node, list) else node[token]
    return node


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="read-only: exit 1 when a pinned record changed or is gone, or the note does not "
                           "match the pinned records; a record the pins do not name is reported, not stale")
    mode.add_argument("--repin", action="store_true",
                      help="pin the full records the corpus holds now, then write the pins and the note")
    mode.add_argument("--sample", type=_count, metavar="N",
                      help="read-only: print N (at least 1) of the pinned records' phrases per class, with "
                           "context, for a precision check, and the draw's sha256; writes nothing")
    ap.add_argument("--seed", type=int, metavar="S",
                    help=f"the --sample draw's seed (default {SAMPLE_SEED}); refused without --sample")
    args = ap.parse_args(argv)
    if args.seed is not None and args.sample is None:
        ap.error("--seed applies only with --sample")
    try:
        pins = current_records(CORPUS) if args.repin else read_pins(PINS)
        collected = collect(CORPUS, pins=pins)
    except Stale as exc:
        print(f"stale: {exc}. Run scripts/absence_claims_baseline.py --repin to pin the corpus as it "
              "stands.", file=sys.stderr)
        return 1
    new = unpinned(CORPUS, pins)
    if new:
        named = "; ".join(new[:10]) + (f"; and {len(new) - 10} more" if len(new) > 10 else "")
        print(f"reported, not counted: {len(new)} full record(s) under {_shown(CORPUS)}/ are not in the "
              f"pinned set ({named}); --repin counts them", file=sys.stderr)
    if args.sample is not None:
        print("\n".join(sample(collected, args.sample, SAMPLE_SEED if args.seed is None else args.seed)))
        return 0
    try:
        text = render_markdown(collected)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    if args.check:
        if not OUT_MD.exists() or OUT_MD.read_text(encoding="utf-8") != text:
            print(f"stale: {_shown(OUT_MD)} does not match its {len(pins)} pinned records; "
                  "run scripts/absence_claims_baseline.py", file=sys.stderr)
            return 1
        print(f"{_shown(OUT_MD)} matches its {len(pins)} pinned records")
        return 0
    if args.repin:
        write_pins(pins, PINS)
        print(f"pinned {len(pins)} records in {_shown(PINS)}")
    OUT_MD.write_text(text, encoding="utf-8")
    print(f"wrote {_shown(OUT_MD)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
