#!/usr/bin/env python
"""How often a bundle splits a word across lines with no hyphen (#3199).

`attainability.matching_lines` reads a line break as a space and, after a
hyphen, as a split word or a hyphenated compound. A break inside a word
with no hyphen ('priori' / 'ty for the ...') is read as a space, so a check
whose form such a break splits could certify an absence the bundle does
not have. Reading every break as nothing would join ordinary wraps ('over'
/ 'sight'), which is why the reading was left out. This measures both
sides, per bundle version a provenance record names, before more versions
are certified:

- `letter_breaks`: line pairs where one line ends and the next starts in a
  letter, in any script — the breaks the split-word test judges;
- `joinable_breaks`: every break between two lines that are not blank,
  except one after a hyphen (that break is read already) — every break the
  missing reading could apply to, whatever ends and starts the lines: a
  letter/digit break ('for v' / '2.0.0'), a digit/digit one, one beside
  punctuation or a letter outside ASCII (#3438);
- `split_words`: those whose two halves joined are a word while neither
  half is (the issue's method), each listed with its line;
- `wraps_that_join`: those whose halves are both words and join to one
  ('over' / 'sight') — what reading every such break as nothing would join
  as well;
- `moved`: the checks with a match across one of the `split_words`
  breaks read as nothing (the two lines joined with no space), and
  `moved_if_every_break_joins` across any of the `joinable_breaks` — the
  reading the issue weighs adding, spurious joins and all. `status` where the check
  is `not_stated_in_source` on the bytes as they are, so the reading would
  move it to `unknown`; `lines` where it is `unknown` already and would only
  list more lines. A match that needs this join and another break's
  reading at once is not searched;
- the cost of those windows (#3246): hyphenated breaks, the windows of
  `MIXED_WINDOW_LINES` lines holding two or more, and the most in one
  (each such window is read 3^k - 3 ways for its k breaks); and, with
  `--compare-window N`, the checks whose matching lines differ when the
  breaks are read each on its own within N lines instead, with the same
  two window counts at N lines — the cost of the wider window, which is
  not the cost at `MIXED_WINDOW_LINES` (#3439).

"A word" is a line-interior token of the same bundle (the first and last
token of a line are left out: they are the halves being judged) or an
entry of the word list `--words` names (default `/usr/share/dict/words`).
The list carries no inflections, which the bundle's own vocabulary
supplies. A word neither knows is missed, so `split_words` is a lower
bound; the list's path and sha256 are printed with the table.

The bundle bytes are resolved as the attainability validator resolves them
(`attainability.resolve_bytes`: the file on disk, else the committed version
whose md5 the record names). Nothing is written; records are only read.

Usage:
    poetry run python scripts/measure_unhyphenated_line_splits.py          # markdown table
    poetry run python scripts/measure_unhyphenated_line_splits.py --json
    poetry run python scripts/measure_unhyphenated_line_splits.py --words /path/to/wordlist
    poetry run python scripts/measure_unhyphenated_line_splits.py --compare-window 10
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema import attainability as at  # noqa: E402
from data_sheets_schema.chunking import DEFAULT_RULE  # noqa: E402

CORPUS = Path("data/d4d_concatenated")
DEFAULT_WORDS = Path("/usr/share/dict/words")
# A letter in any script: a word character that is neither a digit nor '_'.
_LETTERS = r"[^\W\d_]+"
_TAIL = re.compile(rf"({_LETTERS})$")
_HEAD = re.compile(rf"^({_LETTERS})")
_TOKEN = re.compile(_LETTERS)


def bundle_versions(corpus: Path) -> tuple[dict[tuple[str, str], int], list[str]]:
    """(bundle path, md5) -> the number of provenance records naming it, and
    the records that could not be read (listed, not counted)."""
    versions: dict[tuple[str, str], int] = {}
    unreadable = []
    for record in sorted(corpus.rglob("*_provenance.yaml")):
        try:
            document = yaml.safe_load(record.read_text(encoding="utf-8"))
            inputs = document.get("inputs") or {}
            path, md5 = inputs.get("bundle_path"), inputs.get("bundle_md5")
        except (OSError, UnicodeDecodeError, yaml.YAMLError, AttributeError) as exc:
            unreadable.append(f"{record} ({type(exc).__name__})")
            continue
        if isinstance(path, str) and isinstance(md5, str) and path and md5:
            versions[(path, md5)] = versions.get((path, md5), 0) + 1
    return versions, unreadable


def interior_words(lines: Iterable[str]) -> set[str]:
    """Every token of a line except its first and last, lower-cased."""
    return {t.lower() for line in lines for t in _TOKEN.findall(line)[1:-1]}


def letter_breaks(lines: list[str]) -> list[tuple[int, str, str]]:
    """(line number, the letters ending it, the letters starting the next)
    for every break with a letter on both sides, after trailing and leading
    white space. A line ending in a hyphen is not one: that break is read."""
    out = []
    for n, (this, after) in enumerate(zip(lines, lines[1:]), 1):
        tail, head = _TAIL.search(this.rstrip()), _HEAD.match(after.lstrip())
        if tail and head:
            out.append((n, tail.group(1), head.group(1)))
    return out


def joinable_breaks(lines: list[str]) -> list[int]:
    """The line number of every break the missing reading could apply to:
    both lines carry something other than white space, and the first does
    not end in a hyphen, whose break `matching_lines` reads already (the
    compound reading is this join). What ends and starts the lines is not
    judged, so a letter/digit, digit/digit or punctuation break is one."""
    return [n for n, (this, after) in enumerate(zip(lines, lines[1:]), 1)
            if this.strip() and after.strip() and not this.rstrip().endswith("-")]


def window_load(lines: dict[int, tuple[str, str]], width: int) -> tuple[int, int]:
    """(windows of `width` consecutive lines holding two or more hyphenated
    breaks, the most such breaks in one window): the windows `_readings`
    reads 3^k - 3 ways each when `MIXED_WINDOW_LINES` is `width`."""
    hyphenated = at._hyphenated(lines)
    numbers = sorted(lines)
    per_window = [sum(1 for n in numbers[i:i + width][:-1] if n in hyphenated) for i in range(len(numbers))]
    return sum(1 for k in per_window if k >= 2), max(per_window, default=0)


def crossing_checks(lines: list[str], line: int) -> set[str]:
    """The checks with a match across the break after `line` (1-based) read
    as nothing: a match of the check's pattern on that line and the next,
    joined with their facing white space removed, that takes a character
    from each side. Each start position is searched, as in `matching_lines`."""
    this, after = lines[line - 1].rstrip(), lines[line].lstrip()
    text, join = this + after, len(this)
    out = set()
    for check in at.CHECKS:
        rx, pos = re.compile(check.pattern), 0
        while (m := rx.search(text, pos)) is not None:
            if m.start() < join < m.end():
                out.add(check.name)
                break
            pos = m.start() + 1
    return out


def moved_checks(lines: list[str], joined: Iterable[int], hits: dict[str, set[int]]) -> dict[str, str]:
    """Check name -> `status` where a match across one of the `joined`
    breaks would take a check with no matching line (`hits`, from
    `matching_lines` on the bytes as they are) to `unknown`, else `lines`
    where it would add a line to those of a check already `unknown`."""
    out: dict[str, str] = {}
    for line in joined:
        for name in crossing_checks(lines, line):
            if not hits[name]:
                out[name] = "status"
            elif {line, line + 1} - hits[name]:
                out.setdefault(name, "lines")
    return out


def window_moves(lines: dict[int, tuple[str, str]], window: int,
                 hits: dict[str, set[int]]) -> dict[str, list[int]]:
    """Check name -> [lines now, lines under `window`] for every check whose
    matching lines differ when the hyphenated breaks are read each on its
    own within `window` consecutive lines rather than `MIXED_WINDOW_LINES`."""
    kept = at.MIXED_WINDOW_LINES
    at.MIXED_WINDOW_LINES = window
    try:
        wider = {c.name: set(at.matching_lines(c.pattern, lines)) for c in at.CHECKS}
    finally:
        at.MIXED_WINDOW_LINES = kept
    return {name: [len(hits[name]), len(wider[name])] for name in hits if wider[name] != hits[name]}


def measure(text: str, dictionary: set[str] = frozenset(), compare_window: int | None = None) -> dict[str, Any]:
    """The counts the module docstring names, for one bundle's text."""
    raw_lines = text.split("\n")
    words = set(dictionary) | interior_words(raw_lines)
    splits, joins = [], 0
    breaks = letter_breaks(raw_lines)
    for n, tail, head in breaks:
        joined = (tail + head).lower()
        if joined not in words:
            continue
        if tail.lower() in words and head.lower() in words:
            joins += 1
        elif tail.lower() not in words and head.lower() not in words:
            splits.append({"line": n, "tail": tail, "head": head, "word": joined})
    _, lines = at._lines_by_chunk(text, dict(DEFAULT_RULE))
    hits = {c.name: set(at.matching_lines(c.pattern, lines)) for c in at.CHECKS}
    moved = moved_checks(raw_lines, [s["line"] for s in splits], hits)
    joinable = joinable_breaks(raw_lines)
    moved_all = moved_checks(raw_lines, joinable, hits)
    mixed, most = window_load(lines, at.MIXED_WINDOW_LINES)
    wider: dict[str, Any] = {}
    if compare_window:
        wider_mixed, wider_most = window_load(lines, compare_window)
        wider = {"window_moves": window_moves(lines, compare_window, hits),
                 "compare_mixed_windows": wider_mixed, "compare_most_in_one_window": wider_most}
    return {"lines": len(raw_lines), "letter_breaks": len(breaks), "joinable_breaks": len(joinable),
            "split_words": splits, "wraps_that_join": joins, "moved": moved,
            "moved_if_every_break_joins": moved_all, **wider,
            "hyphenated_breaks": len(at._hyphenated(lines)),
            "mixed_windows": mixed, "most_in_one_window": most}


def load_words(path: Path | None) -> tuple[set[str], dict[str, Any]]:
    if path is None:
        return set(), {"path": None, "sha256": None, "entries": 0}
    raw = path.read_bytes()
    words = {w.strip().lower() for w in raw.decode("utf-8", "replace").splitlines() if w.strip()}
    return words, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "entries": len(words)}


def report(corpus: Path, words_path: Path | None, compare_window: int | None = None) -> dict[str, Any]:
    from data_sheets_schema.corpus import anchored
    dictionary, identity = load_words(words_path)
    versions, unreadable = bundle_versions(anchored(corpus))
    rows = []
    for (path, md5), records in sorted(versions.items()):
        try:
            raw, basis = at.resolve_bytes(path, md5=md5)
            text = raw.decode("utf-8")
        except (at.AttainabilityError, UnicodeDecodeError) as exc:
            rows.append({"bundle": path, "md5": md5, "records": records, "error": str(exc)})
            continue
        rows.append({"bundle": path, "md5": md5, "records": records, "source": basis["source"],
                     **measure(text, dictionary, compare_window)})
    return {"words": identity, "mixed_window_lines": at.MIXED_WINDOW_LINES, "compare_window": compare_window,
            "unreadable_records": unreadable, "rows": rows}


def markdown(result: dict[str, Any]) -> str:
    words = result["words"]
    out = [f"Word list: `{words['path']}` (sha256 `{words['sha256']}`, {words['entries']} entries), "
           "plus each bundle's own line-interior tokens.", "",
           "| Bundle | md5 | Records | Letter/letter breaks | Split words | Wraps that join | Checks moved | "
           "Breaks joined | Moved if every break joins | Hyphenated breaks | Mixed windows | Most in one |",
           "|---|---|---:|---:|---|---:|---|---:|---|---:|---:|---:|"]
    for r in result["rows"]:
        if "error" in r:
            out.append(f"| `{Path(r['bundle']).name}` | `{r['md5'][:8]}` | {r['records']} | "
                       f"not measured: {r['error']} | | | | | | | | |")
            continue
        splits = ", ".join(f"{s['tail']}/{s['head']} (line {s['line']})" for s in r["split_words"]) or "0"
        moved, moved_all = (", ".join(f"{k} ({v})" for k, v in sorted(m.items())) or "none"
                            for m in (r["moved"], r["moved_if_every_break_joins"]))
        out.append(f"| `{Path(r['bundle']).name}` | `{r['md5'][:8]}` | {r['records']} | {r['letter_breaks']} | "
                   f"{splits} | {r['wraps_that_join']} | {moved} | {r['joinable_breaks']} | {moved_all} | "
                   f"{r['hyphenated_breaks']} | "
                   f"{r['mixed_windows']} | {r['most_in_one_window']} |")
    if result["compare_window"]:
        moved = [f"`{Path(r['bundle']).name}` `{r['md5'][:8]}`: "
                 + ", ".join(f"{k} {a} -> {b} lines" for k, (a, b) in sorted(r["window_moves"].items()))
                 for r in result["rows"] if r.get("window_moves")]
        out += ["", f"Read each on its own within {result['compare_window']} lines rather than "
                    f"{result['mixed_window_lines']}, the hyphenated breaks move "
                    + ("the matching lines of: " + "; ".join(moved) if moved else
                       "no check's matching lines on any version measured") + "."]
        measured = [r for r in result["rows"] if "error" not in r]
        if measured:
            top = max(measured, key=lambda r: r["compare_most_in_one_window"])
            out += ["", f"At {result['compare_window']} lines the most hyphenated breaks in one window is "
                        f"{top['compare_most_in_one_window']} (`{Path(top['bundle']).name}` `{top['md5'][:8]}`, "
                        f"{top['compare_mixed_windows']} windows with two or more), read "
                        f"{3 ** top['compare_most_in_one_window'] - 3} ways; the table's last two columns "
                        f"are at {result['mixed_window_lines']} lines."]
    if result["unreadable_records"]:
        out += ["", "Provenance records that could not be read: " + "; ".join(result["unreadable_records"])]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--corpus", type=Path, default=CORPUS, help="where the provenance records are")
    parser.add_argument("--words", type=Path, default=DEFAULT_WORDS,
                        help="a word list, one per line (default: %(default)s)")
    parser.add_argument("--no-word-list", action="store_true",
                        help="judge words by each bundle's own vocabulary alone")
    parser.add_argument("--compare-window", type=int, metavar="N",
                        help="also report the checks whose matching lines differ with a mixed-reading "
                             "window of N lines (slow: the readings grow as 3^k per window)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    words = None if args.no_word_list else args.words
    if words is not None and not words.is_file():
        print(f"no word list at {words}: name one with --words, or pass --no-word-list", file=sys.stderr)
        return 2
    if args.compare_window is not None and args.compare_window < 2:
        print("--compare-window must be at least 2 lines", file=sys.stderr)
        return 2
    result = report(args.corpus, words, args.compare_window)
    sys.stdout.write(json.dumps(result, indent=2) + "\n" if args.json else markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
