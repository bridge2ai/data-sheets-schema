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
        # class, with context, for a precision check; writes nothing
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
_SHA256 = re.compile(r"[0-9a-f]{64}")

#: Hand-checked precision samples, keyed by the lexicon sha256 they were drawn
#: under, so a note regenerated under another lexicon says none was checked
#: rather than repeating a figure that describes other patterns. Each sample is
#: `--sample 50 --seed 2919` over the pinned records named by
#: `record_set_sha256`; a note over another record set says the sample was
#: drawn from another one. Each phrase was read in context against its class
#: definition by the agent that registered the lexicon — not an independent
#: review. It measures class membership, not whether a statement should be
#: removed: a source conflict is legitimate content for `source_caveats`, and
#: one worded with the ranking vocabulary is still counted in
#: `record_self_narration`, as borderline. Class values: (in class,
#: borderline, not in class).
PRECISION: dict[str, dict[str, Any]] = {
    "7b5c2237df5a0c2fa71446f472abb8aefc7458ea5c9d9f15228f172b5325ef1e": {     # v1
        "checked": "2026-09-28",
        "record_set_sha256": "cb4b5b8ae826da7ec9ede78ffc920725df39e6b9a3140b18ca01e54b54a6b711",   # 303 records
        "classes": {"bundle_wide_absence": (50, 0, 0), "record_self_narration": (47, 3, 0)},
        "note": "The three borderline phrases are source conflicts worded with the ranking "
                "vocabulary (\"two tier-1 sources disagree\").",
    },
}


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
    lexicon = lexicon or lx.load(absence_lint.LEXICON)
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
            f"A seeded sample (`--sample 50 --seed {SAMPLE_SEED}`) of each class's phrases, checked",
            f"{checked['checked']}. Each phrase was read in context against its class definition by",
            "the agent that registered the lexicon, not by an independent reviewer. The sample",
            "measures class membership, not whether a statement should be removed.",
            *drawn,
            "",
            "| class | in class | borderline | not in class |",
            "|---|---:|---:|---:|",
        ]
        for c in classes:
            if c in checked["classes"]:
                a, b, n = checked["classes"][c]
                lines.append(f"| {c} | {a} | {b} | {n} |")
        if checked.get("note"):
            lines += ["", checked["note"]]
    return "\n".join(lines) + "\n"


def _leaves_sentence(scope: dict[str, Any]) -> str:
    keys = ", ".join(f"`{k}`" for k in scope["free_text_keys"])
    suffixes = ", ".join(f"`*{s}`" for s in scope["free_text_key_suffixes"])
    excluded = [f"`{k}`" for k in scope["excluded_keys"]]
    excluded_text = ", ".join(excluded[:-1]) + " or " + excluded[-1] if len(excluded) > 1 else "".join(excluded)
    return f"{keys} and every {suffixes}, at any depth; never inside {excluded_text}"


def sample(collected: dict[str, Any], n: int, seed: int) -> list[str]:
    """A seeded sample of each class's phrases, each with its context."""
    out: list[str] = []
    texts: dict[str, dict] = {}
    for cls in collected["lexicon"].classes:
        hits = [(row["path"], h) for row in collected["records"] if row["result"]
                for h in row["result"]["hits"] if h["class"] == cls]
        picked = random.Random(seed).sample(hits, min(n, len(hits)))
        out.append(f"## {cls}: {len(picked)} of {len(hits)} phrases")
        for i, (path, h) in enumerate(picked, 1):
            if path not in texts:
                texts[path] = yaml.safe_load((collected["corpus"] / path).read_text(encoding="utf-8"))
            text = " ".join(_at(texts[path], h["pointer"]).split())
            before, after = text[max(0, h["start"] - 110):h["start"]], text[h["end"]:h["end"] + 70]
            out.append(f"{i}. {path} {h['pointer']} {h['patterns']}\n   …{before}[[{h['text']}]]{after}…")
    return out


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
    mode.add_argument("--sample", type=int, default=0, metavar="N",
                      help="read-only: print N of the pinned records' phrases per class for a precision check")
    ap.add_argument("--seed", type=int, default=SAMPLE_SEED)
    args = ap.parse_args(argv)
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
    if args.sample:
        print("\n".join(sample(collected, args.sample, args.seed)))
        return 0
    text = render_markdown(collected)
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
