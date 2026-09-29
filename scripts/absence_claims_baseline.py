#!/usr/bin/env python
"""Offline baseline of the absence lint over the committed corpus (#2919).

Counts, by method directory, the full records under `data/d4d_concatenated/`
whose free-text leaves carry a bundle-wide absence claim or record
self-narration as the registered lexicon `absence_self_narration` defines
them (`data_sheets_schema.absence_lint`), and writes the table to
`notes/absence_claims_baseline.md`. The records are only read; the note is
the one file written.

The note is regenerated, never edited by hand: a corpus-lane test rebuilds it
from the records and fails when the committed bytes differ, so a new record,
an amended one or a new lexicon version shows up as a stale note rather than
as a table that quietly describes other bytes.

Usage:
    poetry run python scripts/absence_claims_baseline.py            # write the note
    poetry run python scripts/absence_claims_baseline.py --check    # read-only: exit 1 when stale
    poetry run python scripts/absence_claims_baseline.py --sample 50 --seed 2919
        # read-only: print a seeded sample of phrases per class, with context,
        # for a precision check; writes nothing
"""
from __future__ import annotations

import argparse
import hashlib
import random
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema import absence_lint  # noqa: E402
from data_sheets_schema import lexicon as lx  # noqa: E402

CORPUS = ROOT / "data" / "d4d_concatenated"
OUT_MD = ROOT / "notes" / "absence_claims_baseline.md"
RECORD_GLOB = "*_d4d.yaml"
SAMPLE_SEED = 2919

#: Hand-checked precision samples, keyed by the lexicon sha256 they were drawn
#: under, so a note regenerated under another lexicon says none was checked
#: rather than repeating a figure that describes other patterns. Each sample is
#: `--sample 50 --seed 2919` over the records the note counts; each phrase was
#: read in context against its class definition by the agent that registered
#: the lexicon — not an independent review. It measures class membership, not
#: whether a statement should be removed: a source conflict is legitimate
#: content for `source_caveats`, and one worded with the ranking vocabulary is
#: still counted in `record_self_narration`, as borderline. Class values:
#: (in class, borderline, not in class).
PRECISION: dict[str, dict[str, Any]] = {
    "7b5c2237df5a0c2fa71446f472abb8aefc7458ea5c9d9f15228f172b5325ef1e": {     # v1
        "checked": "2026-09-28, over the 303-record corpus",
        "classes": {"bundle_wide_absence": (50, 0, 0), "record_self_narration": (47, 3, 0)},
        "note": "The three borderline phrases are source conflicts worded with the ranking "
                "vocabulary (\"two tier-1 sources disagree\").",
    },
}


def record_paths(corpus: Path) -> list[Path]:
    """The full records: `*_d4d.yaml` in each method directory that does not
    end `_core`, and one label directory below it. Sorted, so the table and
    the corpus digest do not depend on directory order."""
    found: list[Path] = []
    for method in sorted(p for p in corpus.iterdir() if p.is_dir() and not p.name.endswith("_core")):
        found.extend(method.glob(RECORD_GLOB))
        found.extend(method.glob(f"*/{RECORD_GLOB}"))
    return sorted(found, key=lambda p: p.relative_to(corpus).as_posix())


def collect(corpus: Path = CORPUS, lexicon: lx.Lexicon | None = None) -> dict[str, Any]:
    """Lint every record; keep each result beside its path, method and hash."""
    lexicon = lexicon or lx.load(absence_lint.LEXICON)
    records = []
    for path in record_paths(corpus):
        raw = path.read_bytes()
        rel = path.relative_to(corpus).as_posix()
        row: dict[str, Any] = {"path": rel, "method": rel.split("/", 1)[0],
                               "sha256": hashlib.sha256(raw).hexdigest(), "result": None, "error": None}
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
    digest = hashlib.sha256("".join(f"{r['path']} {r['sha256']}\n" for r in records).encode()).hexdigest()
    return {"lexicon": lexicon, "corpus": corpus, "records": records, "corpus_sha256": digest}


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
        "script to regenerate it, or `--check` to ask whether it still matches the records.",
        "",
        f"- **Instrument:** {lexicon.instrument}",
        f"- **Lexicon:** `src/data_sheets_schema/lexicons/{lexicon.file}`, sha256 `{lexicon.sha256}`",
        f"- **Corpus:** {t['records']} full records (`{RECORD_GLOB}`) under `{_shown(corpus)}/`, in each",
        "  method directory whose name does not end `_core` and one label directory below it;",
        f"  corpus sha256 `{collected['corpus_sha256']}` over each record's path and bytes",
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
        lines += [
            f"A seeded sample (`--sample 50 --seed {SAMPLE_SEED}`) of each class's phrases, checked",
            f"{checked['checked']}. Each phrase was read in context against its class definition by",
            "the agent that registered the lexicon, not by an independent reviewer. The sample",
            "measures class membership, not whether a statement should be removed.",
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
    ap.add_argument("--check", action="store_true", help="read-only: exit 1 when the committed note is stale")
    ap.add_argument("--sample", type=int, default=0, metavar="N",
                    help="read-only: print N phrases per class for a precision check")
    ap.add_argument("--seed", type=int, default=SAMPLE_SEED)
    args = ap.parse_args(argv)
    collected = collect(CORPUS)
    if args.sample:
        print("\n".join(sample(collected, args.sample, args.seed)))
        return 0
    text = render_markdown(collected)
    if args.check:
        if not OUT_MD.exists() or OUT_MD.read_text(encoding="utf-8") != text:
            print(f"stale: {_shown(OUT_MD)} does not match the records; "
                  "run scripts/absence_claims_baseline.py", file=sys.stderr)
            return 1
        print(f"{_shown(OUT_MD)} matches the records")
        return 0
    OUT_MD.write_text(text, encoding="utf-8")
    print(f"wrote {_shown(OUT_MD)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
