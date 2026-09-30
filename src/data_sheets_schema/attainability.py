"""What an input bundle can support, per rubric item and bundle version (#2925).

A rubric zero says the record lacks the documentation. It does not say
why: the generator dropped a fact the bundle states, or the bundle never
states it. The CHORUS bundle (md5 9b2ef4b6…) carries no DOI, no RRID and
no consent text, so no generator reading it can earn E1.1's DOI route,
E10.2 or E4.4 without inventing the value — and the rubric, which never
reads the bundle, scores those zeros exactly like an omission. This module
records the other half as data, keyed to the bytes a record read.

**One file per bundle version**, `data/attainability/<bundle stem>_<md5>.yaml`
(not `data/rubric/`, a resource directory the wheel ships). A version, not
a project: the v7 and v8 reference records read different AI_READI and
VOICE bytes, so an entry about "the AI_READI bundle" would describe one of
them and be applied to both. The file states once the identities every
entry is keyed to::

    format: d4d-attainability
    format_version: 1
    bundle: {path, md5, sha256, bytes}   # the bytes every entry is about
    chunk_rule: {...}                    # the rule the chunk ids are named under, in full
    rubrics:
      rubric10: {path: data/rubric/rubric10.txt, sha256: ...}
    entries:
    - rubric: rubric10
      item_id: E4.4
      route: null                        # or a named route of the item
      status: supported | partly_supported | not_stated_in_source | unknown
      method: deterministic:<check> | curator | judge:<id>
      evidence:
        pattern: ...                     # deterministic entries only
        hit_count: 0                     # bundle lines the pattern matches
        snippets:                        # {chunk, lines: [first, last], sha256}
        - {chunk: c003, lines: [414, 414], sha256: ...}
      note: ...

**Only absence is deterministic.** A check is a pattern every statement of
the item's content would match; zero matching lines establish
`not_stated_in_source`. The bundles are hard-wrapped, so a line matches
when a match touches it with the text read line by line *and* whole, each
line break read as a space and, after a hyphen, as a split word or a
hyphenated compound (`matching_lines`, #3179): a statement a break splits
is not an absence. The breaks after a hyphen are read each on its own,
not all alike, within any `MIXED_WINDOW_LINES` (six) consecutive lines, so
a compound hyphen and a split-word hyphen in one statement ('a data-'
'protec-' 'tion impact') still match (#3238). A word a break splits with no
hyphen is not read that way, nor a statement over more than six lines
whose hyphens need different readings, and every entry's note says so. A match establishes nothing — the four CHORUS
"IRB" lines are a training curriculum, its "license" lines the MIT
software license and a course agreement, its "version" lines Python
version control — so a check
with any hit writes `unknown` and lists the lines for a curator. No
deterministic check ever writes `supported` or `partly_supported`; those
need a curator or a judge (`method: curator` / `judge:<id>`), whose
snippets the validator verifies against the bytes but whose reading it
cannot.

**A route is part of an item.** E1.1 accepts a DOI, an RRID or another
persistent URI, and no pattern settles the third; its entry here is scoped
`route: doi_rrid` and speaks for that route alone. An entry with a route
never settles the item; one without a route does.

**The validator re-derives the file from the bytes.** It resolves the
bundle the way a receipt recompute does (#1140): the file on disk where
it hashes to both recorded hashes, else the committed version of the
declared path that does (`provenance.bundle_bytes_for`), and refuses the
file when neither does — so an entry about a drifted bundle stays
checkable and a tampered hash is not accepted. `chunk_rule` must be a rule
the chunker implements, written out in full (`chunking.validate_rule`):
`chunk_text` reads only its two window bounds and reads an empty rule as
this checkout's default, so without that check a file could state a rule
nobody chunked under, or none (#3107). Every deterministic entry must be
identical to what its check writes over those bytes under that rule —
type for type, since Python's `False == 0` and `45.0 == 45` would let a
file the generator never wrote pass (#3182) — and every entry names its
`route`, `null` included; every snippet must hash to the lines it names.
The format is closed: a key it does not name — at the top, in `bundle`, in
a `rubrics` identity, in an entry or a snippet — is refused, so a file
cannot carry an `overrides:` block nothing reads and still be valid (#3239).
The pinned rubric is resolved the same way. Curator and judge entries are
hand-written, so a valid file is not always the generator's output; its
deterministic entries are. A file that cannot be read, is not UTF-8 or
names a path no file can have is reported with its problems like any
other invalid file, not raised past them (#3180, #3217).

`credited_despite_absence` is the generator-side check the issue asks
for: items an evaluation credited although the bundle it scored was
marked `not_stated_in_source` for them — content from outside the bundle,
or an invented value. A credit on an item only a route entry marks absent
is not one: the credit may rest on another route, so it is listed as
`credited_on_other_route` for a curator and neither counted as a finding
nor failed by `credited --strict` (#3219). An evaluation that is not JSON,
or whose items cannot be keyed, or whose record's provenance cannot be read,
is reported on its own row as `unreadable` and fails the run; the
evaluations after it are still reported (#3200). Nothing here changes a score: the rubric, its
agents and every evaluation stay as they are, and reporting an
attained-over-attainable basis is a later change.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import itertools
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

FORMAT = "d4d-attainability"
FORMAT_VERSION = 1
ATTAINABILITY_DIR = Path("data/attainability")
STATUSES = ("supported", "partly_supported", "not_stated_in_source", "unknown")
#: Kinds `credited_despite_absence` reports that are findings; any other
#: kind (`credited_on_other_route`) is listed for review, never gated (#3219).
FINDING_KINDS = ("credited", "unjoined")
#: Statuses that assert support: never written by a deterministic check.
SUPPORT_STATUSES = ("supported", "partly_supported")
RUBRIC_PATHS = {"rubric10": "data/rubric/rubric10.txt", "rubric20": "data/rubric/rubric20.txt"}
#: The document is closed at every level (#3239): a key nothing reads — an
#: `overrides:` block, a `bundle.note` — would sit in a file the validator
#: attests as valid and read as part of it.
_DOCUMENT_KEYS = {"format", "format_version", "bundle", "chunk_rule", "rubrics", "entries"}
_BUNDLE_KEYS = {"path", "md5", "sha256", "bytes"}
_RUBRIC_KEYS = {"path", "sha256"}
_ENTRY_KEYS = {"rubric", "item_id", "route", "status", "method", "evidence", "note"}
_SNIPPET_KEYS = {"chunk", "lines", "sha256"}
_HEX = {"md5": re.compile(r"[0-9a-f]{32}"), "sha256": re.compile(r"[0-9a-f]{64}")}


class AttainabilityError(ValueError):
    """An attainability file that cannot be accepted, with every reason."""

    def __init__(self, path: Any, problems: list[str]):
        self.path, self.problems = path, list(problems)
        super().__init__(f"{path}: " + "; ".join(self.problems))


@dataclass(frozen=True)
class AbsenceCheck:
    """A pattern every statement of an item's content matches, so that no
    matching line in the bundle means the bundle does not state it. `claim`
    says what absence establishes and what the pattern cannot see."""
    name: str
    rubric: str
    item_id: str
    route: str | None
    pattern: str
    claim: str


# A broader pattern only moves a result from absent to unknown, never the
# other way, so each errs towards matching: a stem is matched inside longer
# words (`bioethics`, `unconsented`) unless that makes an unrelated common
# word match (`doing`, `excite`, `conversion`). Letters around a token are
# excluded with lookarounds rather than `\b`, which treats `_` and digits
# as word characters: `doi_url` must match. Every inflection of a form a
# claim names must match too — `exemptions`, `opting out`, `HRECs`, a
# version number that ends a sentence (#3109); `test_every_form_a_claim_names_matches`
# lists them. So must a compound written hyphenated or spaced alike
# (`human-subjects`, #3183): the words of one are joined by `[-\s]+`, or
# by `[-\s]*` where the claim also names the joined form (`optout`), so a
# run of separators — two spaces, 'opt- out' — never breaks one (#3237). A
# statement a line break splits is matched by reading the text whole
# (`matching_lines`, #3179), not by the patterns. A pattern carries no
# literal space (`\s` instead), so the YAML writer never folds one across
# lines.
_DOI = r"(?<![a-z])dois?(?![a-z])|10\.\d+(?:\.\d+)*/"
_RRID = r"(?<![a-z])rrids?(?![a-z])|(?<![a-z0-9])(?:scr|ab|cvcl|nlx)_\d"
_WAIVER = r"(?<![a-z])waiv(?:e|ed|er|ers|es|ing)(?![a-z])"

CHECKS: tuple[AbsenceCheck, ...] = (
    AbsenceCheck(
        "doi_rrid", "rubric10", "E1.1", "doi_rrid",
        f"(?i){_DOI}|{_RRID}",
        "A DOI in any written form carries '10.<registrant>/', a registrant subdivided by full stops "
        "('10.1000.10/') included, or is named DOI; an RRID is named RRID "
        "or written as a SCR_/AB_/CVCL_/NLX_ accession, so zero matching lines mean the bundle states "
        "no DOI and no RRID. E1.1 also accepts another persistent URI, which no pattern settles: "
        "this entry speaks for the DOI/RRID route only."),
    AbsenceCheck(
        "ethics_review", "rubric10", "E4.1", None,
        r"(?i)(?<![a-z])irbs?(?![a-z])|institutional[-\s]+review|ethic"
        r"|(?<![a-z])(?:hrec|reb|dpia)s?(?![a-z])|exempt|" + _WAIVER +
        r"|data[-\s]+protection[-\s]+impact|privacy[-\s]+board|human[-\s]+subjects?"
        r"|(?<![a-z])oversights?(?![a-z])",
        "An ethics review, its waiver or exemption, or a data protection impact assessment is named "
        "IRB, institutional review, ethics/ethical, HREC/REB, exemption, waiver, DPIA, privacy "
        "board, human subjects or oversight, a compound hyphenated or spaced alike "
        "('human-subjects'), so zero matching lines mean the bundle states none."),
    AbsenceCheck(
        "consent_text", "rubric10", "E4.4", None,
        f"(?i)consent|(?<![a-z])assent|{_WAIVER}|permission"
        r"|authori[sz]ation|(?<![a-z])opt(?:ed|s|ing)?[-\s]*(?:in|out)s?(?![a-z])",
        "Any statement of informed consent names consent, assent, a waiver, parental permission, "
        "a HIPAA authorization or an opt-in/opt-out model (written joined, hyphenated or spaced, "
        "'opt  out' and 'opt- out' included), so zero matching lines mean the bundle "
        "states no consent procedure. Not seen: consent described without any of these words "
        "('participants agreed to ...')."),
    AbsenceCheck(
        "version_string", "rubric10", "E6.1", None,
        r"(?i)(?<![a-z])version(?:s|ed|ing)?(?![a-z])|releas(?:e|es|ed|ing)(?![a-z])"
        r"|(?<![a-z])(?:edition|revision)s?(?![a-z])|(?<![a-z0-9])v\d+(?:\.\d+)*(?![a-z])"
        r"|(?<![\d.])\d+(?:\.\d+){2,}(?!\.?\d)",
        "A dataset version is named version/release/edition/revision, or written v<n> or as a "
        "dotted number of three or more parts (also at the end of a sentence), so zero matching "
        "lines mean the bundle states no version. Not seen: a bare two-part number with no such "
        "word ('X 2.0')."),
    AbsenceCheck(
        "dataset_citation", "rubric10", "E10.2", None,
        f"(?i){_DOI}|(?<![a-z])cit(?:e[sd]?|ing|ations?)(?![a-z])|(?<![a-z])bibtex(?![a-z])"
        r"|(?<![a-z])acknowledg|(?:please|how\s+to|when|should|must|kindly)\s+(?:be\s+)?referenc"
        r"|recommended\s+referenc",
        "E10.2 accepts a recommended citation or a DOI. A DOI matches as for E1.1; a citation "
        "request names cite/citation, BibTeX or acknowledgement, or asks the reader to reference "
        "the data (please, how to, when, should, must or kindly, then reference or be referenced; "
        "or a recommended reference), so zero matching lines mean the bundle states neither. Not "
        "seen: a bare formatted reference carrying none of those words."),
)
CHECKS_BY_NAME = {c.name: c for c in CHECKS}

#: How a line break after a hyphen is read: as a space, as nothing with the
#: hyphen dropped (a split word, 'con-' 'sent') or with the hyphen kept (a
#: hyphenated compound, 'human-' 'subjects').
HYPHEN_READINGS = ("space", "drop", "keep")
#: The most consecutive lines over which the breaks after a hyphen are read
#: each on its own (#3238): one statement can carry a compound hyphen at one
#: break and a split-word hyphen at the next ('a data-' 'protec-' 'tion
#: impact'), which no reading of every break alike joins. Every way of
#: reading every such break in every run of this many lines is searched.
MIXED_WINDOW_LINES = 6


#: What every claim's "matching line" means (#3179). The bundles are
#: hard-wrapped PDF and HTML text, so a statement a line break splits
#: ('should\nreference', 'con-\nsent') is a statement too, and a check that
#: read one line at a time would certify its absence.
LINE_READING = ("A matching line is one a match touches, the text read line by line and whole: a line "
                "break read as a space and, after a hyphen, as nothing (a split word) or as the hyphen "
                "alone (a hyphenated compound), each such break read on its own within any "
                f"{MIXED_WINDOW_LINES} consecutive lines. Not seen: a word a break splits with no hyphen, "
                f"or a statement over more than {MIXED_WINDOW_LINES} lines whose hyphens need different "
                "readings.")


# --------------------------------------------------------------------------
# Bytes


def resolve_bytes(path: str, *, md5: str | None = None, sha256: str | None = None,
                  disk: Path | None = None) -> tuple[bytes, dict[str, Any]]:
    """The bytes every given hash names: the file on disk where it hashes to
    all of them, else the newest committed version of `path` that does
    (`provenance.bundle_bytes_for`, #1140). Raises `AttainabilityError`
    naming why when neither does — including when git cannot answer, which
    is not evidence that no version matches."""
    from data_sheets_schema.provenance import GitUnavailable, bundle_bytes_for
    if not md5 and not sha256:
        raise AttainabilityError(path, ["no md5 or sha256 to resolve the bytes by"])
    if "\0" in path:           # `git` would raise ValueError, not answer (#3180)
        raise AttainabilityError(path.replace("\0", "\\0"), ["the path carries a NUL byte, which no file "
                                                             "or committed path can"])
    on_disk = disk if disk is not None else _anchored(path)
    try:
        # `is_file` raises, not answers, on a component longer than NAME_MAX
        # or a directory it may not search (#3217): unreadable here, so the
        # committed version may still answer.
        raw = on_disk.read_bytes() if on_disk.is_file() else None
    except OSError:
        raw = None
    if raw is not None and _hashes_match(raw, md5, sha256):
        return raw, {"source": "file on disk", "path": path}
    try:
        found = bundle_bytes_for(path, md5=md5, sha256=sha256)
    except GitUnavailable as exc:
        raise AttainabilityError(path, [f"the file on disk is not the pinned bytes and git could not "
                                        f"supply a committed version: {exc}"]) from exc
    except (OSError, ValueError) as exc:    # a path git cannot take is not a committed path (#3217)
        raise AttainabilityError(path, [f"neither the file on disk nor git can read this path: {exc}"]) from exc
    if found is None:
        named = " and ".join(f"{k} {v}" for k, v in (("md5", md5), ("sha256", sha256)) if v)
        raise AttainabilityError(path, [f"neither the file on disk nor any committed version of it "
                                        f"hashes to {named}"])
    raw, entry = found
    return raw, {"source": "git blob", "path": path, "commit": entry["commit"],
                 "committed_on": entry["date"], "matched_on": entry.get("matched_on")}


def _hashes_match(raw: bytes, md5: str | None, sha256: str | None) -> bool:
    return ((not md5 or hashlib.md5(raw).hexdigest() == md5)
            and (not sha256 or hashlib.sha256(raw).hexdigest() == sha256))


def _anchored(path: str) -> Path:
    if path.startswith("data/rubric/"):
        from data_sheets_schema.resources import resource_path
        return resource_path(path)
    from data_sheets_schema.corpus import anchored
    return anchored(Path(path))


def _lines_by_chunk(text: str, rule: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[int, tuple[str, str]]]:
    """The chunks of `text` under `rule` (`chunking.chunk_text`, the ids a
    receipt names) and, for every bundle line, its chunk id and text."""
    from data_sheets_schema.chunking import chunk_text, chunk_texts
    chunks = chunk_text(text, rule)
    lines: dict[int, tuple[str, str]] = {}
    for chunk, body in zip(chunks, chunk_texts(text, chunks)):
        first, last = chunk["lines"]
        parts = body.split("\n")
        for offset, line in enumerate(parts[: last - first + 1]):
            lines[first + offset] = (chunk["id"], line)
    return chunks, lines


def snippet_sha256(lines: dict[int, tuple[str, str]], first: int, last: int) -> str:
    """sha256 of bundle lines first..last joined by newlines, no trailing one."""
    return hashlib.sha256("\n".join(lines[n][1] for n in range(first, last + 1)).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Deterministic entries


def _read(lines: dict[int, tuple[str, str]], numbers: list[int],
          reading: dict[int, str]) -> tuple[str, list[tuple[int, int, int]]]:
    """Lines `numbers` joined into one text, each break a space except after
    a line `reading` maps to `drop` or `keep`, with every line's
    `(number, start, end)` span in that text. After a dropped or kept hyphen
    the continuation line's indentation is part of the break ('con-' '  sent'
    is 'consent', #3218): layout-preserving PDF and HTML text indents it."""
    parts, spans, at, joined = [], [], 0, False
    for n in numbers:
        body, sep = lines[n][1], " "
        if joined:
            body = body.lstrip()
        hyphen = reading.get(n, "space")
        joined = hyphen != "space"
        if joined:
            stripped = body.rstrip()
            body, sep = (stripped[:-1] if hyphen == "drop" else stripped), ""
        parts += [body, sep]
        spans.append((n, at, at + len(body)))
        at += len(body) + len(sep)
    return "".join(parts), spans


def _hyphenated(lines: dict[int, tuple[str, str]]) -> set[int]:
    return {n for n, (_, text) in lines.items() if text.rstrip().endswith("-")}


def _readings(lines: dict[int, tuple[str, str]]) -> Iterable[tuple[str, list[tuple[int, int, int]]]]:
    """The bundle's text read whole, once per way of reading its line breaks
    after a hyphen (`HYPHEN_READINGS`): every break read alike over the whole
    text, then — in every run of `MIXED_WINDOW_LINES` lines holding two or
    more such breaks — each of those breaks read on its own, every
    combination that is not all alike (#3238). Each reading comes with every
    line's `(number, start, end)` span in its text."""
    numbers = sorted(lines)
    hyphenated = _hyphenated(lines)
    for hyphen in HYPHEN_READINGS[:1] + (HYPHEN_READINGS[1:] if hyphenated else ()):
        yield _read(lines, numbers, {n: hyphen for n in hyphenated})
    for start in range(len(numbers)):
        window = numbers[start:start + MIXED_WINDOW_LINES]
        breaks = [n for n in window[:-1] if n in hyphenated]
        if len(breaks) < 2:
            continue
        for combo in itertools.product(HYPHEN_READINGS, repeat=len(breaks)):
            if len(set(combo)) > 1:
                yield _read(lines, window, dict(zip(breaks, combo)))


def matching_lines(pattern: str, lines: dict[int, tuple[str, str]]) -> list[int]:
    """Every bundle line a match of `pattern` takes a character from (not a
    blank line a match crosses): each line searched alone, and the text
    searched whole under each of `_readings` for the leftmost match at
    every start position — restarting one character after a match's start,
    not at its end, so that one match does not hide another it overlaps.
    Zero lines means no line, and no run of lines under any of the
    readings, carries a match (#3179); a break inside a word with no hyphen
    is not one of them, nor a statement over more than `MIXED_WINDOW_LINES`
    lines whose hyphenated breaks must be read differently (#3238)."""
    rx = re.compile(pattern)
    hits = {n for n, (_, text) in lines.items() if rx.search(text)}
    for text, spans in _readings(lines):
        starts = [start for _, start, _ in spans]
        pos = 0
        while (m := rx.search(text, pos)) is not None:
            begin, end = m.span()
            i = max(bisect.bisect_right(starts, begin) - 1, 0)
            while i < len(spans) and spans[i][1] < end:
                n, start, stop = spans[i]
                if max(start, begin) < min(stop, end):     # a character of the line is in the match
                    hits.add(n)
                i += 1
            pos = begin + 1
    return sorted(hits)


def deterministic_entry(check: AbsenceCheck, lines: dict[int, tuple[str, str]]) -> dict[str, Any]:
    """The entry `check` writes over a bundle's lines: `not_stated_in_source`
    at zero matching lines (`matching_lines`), else `unknown` with every
    matching line listed — never a support status."""
    hits = matching_lines(check.pattern, lines)
    if hits:
        outcome = (f"Result: {len(hits)} matching line(s). A match is not evidence the item is "
                   "supported (the words recur in other senses), so the status stays unknown "
                   "until a curator or judge reads the lines listed.")
    else:
        outcome = "Result: no matching line."
    return {
        "rubric": check.rubric, "item_id": check.item_id, "route": check.route,
        "status": "unknown" if hits else "not_stated_in_source",
        "method": f"deterministic:{check.name}",
        "evidence": {"pattern": check.pattern, "hit_count": len(hits),
                     "snippets": [{"chunk": lines[n][0], "lines": [n, n],
                                   "sha256": snippet_sha256(lines, n, n)} for n in hits]},
        "note": f"{check.claim} {LINE_READING} {outcome}",
    }


def rubric_items(raw: bytes, rubric: str) -> dict[str, str]:
    """Item id → name for a source rubric, under the ids the judge contract
    uses (`E<element>.<position>`, `Q<id>`). A rubric10 text that declares
    its own `item_id` must agree with the position."""
    spec = yaml.safe_load(raw.decode("utf-8"))
    if rubric == "rubric10":
        out = {}
        for element in spec["d4d_complex_proxy_rubric"]["rubric"]:
            for index, item in enumerate(element["sub_elements"], 1):
                key = f"E{element['id']}.{index}"
                if item.get("item_id") not in (None, key):
                    raise ValueError(f"rubric10 declares {item['item_id']} at position {key}")
                out[key] = item["name"]
        return out
    if rubric == "rubric20":
        return {f"Q{item['id']}": item["name"] for item in spec["d4d_evaluation_rubric"]["rubric"]}
    raise ValueError(f"unknown rubric {rubric!r}")


def build_document(bundle_path: str, *, md5: str | None = None, sha256: str | None = None,
                   checks: Iterable[AbsenceCheck] = CHECKS) -> dict[str, Any]:
    """Every deterministic entry for the bundle version `md5`/`sha256` names
    (the file on disk when neither is given), keyed to the rubric texts in
    this checkout."""
    from data_sheets_schema.chunking import DEFAULT_RULE
    if md5 or sha256:
        raw, _ = resolve_bytes(bundle_path, md5=md5, sha256=sha256)
    else:
        raw = _anchored(bundle_path).read_bytes()
    rule = dict(DEFAULT_RULE)
    _, lines = _lines_by_chunk(raw.decode("utf-8"), rule)
    checks = list(checks)
    rubrics = {}
    for name in sorted({c.rubric for c in checks}):
        rubric_raw = _anchored(RUBRIC_PATHS[name]).read_bytes()
        rubrics[name] = {"path": RUBRIC_PATHS[name], "sha256": hashlib.sha256(rubric_raw).hexdigest()}
    return {
        "format": FORMAT, "format_version": FORMAT_VERSION,
        "bundle": {"path": bundle_path, "md5": hashlib.md5(raw).hexdigest(),
                   "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
        "chunk_rule": rule,
        "rubrics": rubrics,
        "entries": [deterministic_entry(c, lines) for c in checks],
    }


def file_name(document: dict[str, Any]) -> str:
    bundle = document["bundle"]
    return f"{Path(bundle['path']).stem}_{bundle['md5']}.yaml"


_HEADER = ("# Attainability of rubric items on one bundle version (#2925); format in\n"
           "# src/data_sheets_schema/attainability.py. Deterministic entries are derived by\n"
           "#   python -m data_sheets_schema.attainability derive --bundle PATH --md5 MD5 --write\n"
           "# and re-derived by the validator; curator and judge entries are kept on a rewrite.\n")


class _Dumper(yaml.SafeDumper):
    """Block style, except a snippet, which reads best on one line."""

    def represent_dict(self, data):
        flow = set(data) == _SNIPPET_KEYS
        return self.represent_mapping("tag:yaml.org,2002:map", data.items(), flow_style=flow or None)

    def represent_list(self, data):
        flow = bool(data) and all(type(v) is int for v in data)
        return self.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow or None)


_Dumper.add_representer(dict, _Dumper.represent_dict)
_Dumper.add_representer(list, _Dumper.represent_list)


def dump(document: dict[str, Any]) -> str:
    return _HEADER + yaml.dump(document, Dumper=_Dumper, sort_keys=False, allow_unicode=True,
                               width=100, default_flow_style=False)


def write_document(document: dict[str, Any], directory: Path = ATTAINABILITY_DIR) -> Path:
    """Write `document` to its file name, keeping every curator or judge
    entry the existing file holds: a regeneration never drops a reading
    someone made, and a deterministic entry is not written over one. A kept
    entry was read under the existing file's chunk rule and rubric texts, so
    a rewrite that would change either is refused rather than re-keying
    those readings to chunk ids or item texts nobody read them under."""
    from data_sheets_schema.corpus import anchored
    target = anchored(Path(directory)) / file_name(document)
    entries, pinned = document["entries"], dict(document["rubrics"])
    if target.exists():
        existing = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        kept = [e for e in existing.get("entries") or []
                if isinstance(e, dict) and not str(e.get("method", "")).startswith("deterministic:")]
        rubrics = existing.get("rubrics") or {}
        moved = (["chunk_rule"] if kept and not identical(existing.get("chunk_rule"), document["chunk_rule"])
                 else []) + \
            sorted({f"rubric {e.get('rubric')}" for e in kept
                    if e.get("rubric") in document["rubrics"]
                    and not identical(rubrics.get(e.get("rubric")), document["rubrics"][e.get("rubric")])})
        if moved:
            raise AttainabilityError(target, [f"{len(kept)} curator or judge entr(ies) were read under "
                                              f"another {', '.join(moved)}; re-read them before rewriting"])
        held = {_key(e) for e in kept}
        entries = [e for e in entries if _key(e) not in held] + kept
        for rubric, identity in rubrics.items():
            pinned.setdefault(rubric, identity)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dump({**document, "rubrics": pinned, "entries": entries}), encoding="utf-8")
    return target


def _key(entry: dict[str, Any]) -> tuple:
    return entry.get("rubric"), entry.get("item_id"), entry.get("route")


# --------------------------------------------------------------------------
# Validation


def identical(a: Any, b: Any) -> bool:
    """Equal with the same types all the way down. Python's `==` holds for
    `False == 0`, `True == 1` and `45.0 == 45`, so a file carrying
    `hit_count: false`, snippet lines `[45.0, 45]` or `format_version: true`
    would compare equal to the generator's output it is not (#3182)."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(identical(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(identical(x, y) for x, y in zip(a, b))
    return a == b


@dataclass(frozen=True)
class Attainability:
    """A validated file: the document, where its bytes came from, and the
    item names of each rubric it pins (the join key for evaluations)."""
    path: Path | None
    document: dict[str, Any]
    bundle_basis: dict[str, Any]
    rubric_items: dict[str, dict[str, str]]

    def entries(self, status: str | None = None) -> list[dict[str, Any]]:
        return [e for e in self.document["entries"] if status is None or e["status"] == status]


def validate_text(text: str, name: str | None = None) -> tuple[list[str], Attainability | None]:
    """Every problem with an attainability file's text (empty when it is
    valid) and, when valid, the loaded file. `name` is its file name, which
    must be the one its bundle identity gives."""
    from data_sheets_schema.duplicate_keys import describe, find_duplicate_keys
    dups = find_duplicate_keys(text)
    if dups:
        return [describe(dups)], None
    try:
        doc = yaml.safe_load(text)
    except (yaml.YAMLError, RecursionError) as exc:
        return [f"not YAML: {exc!r}" if isinstance(exc, RecursionError) else f"not YAML: {exc}"], None
    if not isinstance(doc, dict):
        return ["not a mapping"], None
    problems = _key_problems(doc, _DOCUMENT_KEYS) + \
        [f"bundle: {p}" for p in _key_problems(doc.get("bundle"), _BUNDLE_KEYS)]
    if not (identical(doc.get("format"), FORMAT) and identical(doc.get("format_version"), FORMAT_VERSION)):
        problems.append(f"format must be {FORMAT} version {FORMAT_VERSION} (the integer)")
    bundle = doc.get("bundle")
    if not isinstance(bundle, dict) or not isinstance(bundle.get("path"), str) or not all(
            isinstance(bundle.get(k), str) and _HEX[k].fullmatch(bundle[k]) for k in ("md5", "sha256")):
        return problems + ["bundle must give its path, md5 and sha256"], None
    if name is not None and name != file_name(doc):
        problems.append(f"file name {name} is not {file_name(doc)}, the name its bundle identity gives")
    try:
        raw, basis = resolve_bytes(bundle["path"], md5=bundle["md5"], sha256=bundle["sha256"])
    except AttainabilityError as exc:
        return problems + [f"bundle: {p}" for p in exc.problems], None
    if not identical(bundle.get("bytes"), len(raw)):
        problems.append(f"bundle bytes {bundle.get('bytes')!r} is not {len(raw)}, the size of the pinned bytes")
    rule = doc.get("chunk_rule")
    if not isinstance(rule, dict):
        return problems + ["chunk_rule must be the chunking rule the chunk ids are named under"], None
    from data_sheets_schema.chunking import validate_rule
    try:
        validate_rule(rule)
    except ValueError as exc:
        # `chunk_text` reads only the two bounds and an empty rule as this
        # checkout's default: chunking under a rule attests nothing else (#3107).
        return problems + [f"chunk_rule is not a rule the chunker implements, written in full: {exc}"], None
    try:
        _, lines = _lines_by_chunk(raw.decode("utf-8"), rule)
    except (UnicodeDecodeError, KeyError, TypeError) as exc:
        return problems + [f"the pinned bytes cannot be chunked under chunk_rule: {exc!r}"], None
    chunk_of = {}
    for n, (chunk, _) in lines.items():
        chunk_of.setdefault(chunk, [n, n])[1] = n
    items: dict[str, dict[str, str]] = {}
    rubrics = doc.get("rubrics")
    if not isinstance(rubrics, dict):
        problems.append("rubrics must map each rubric to its path and sha256")
        rubrics = {}
    for rubric, identity in rubrics.items():
        problems.extend(f"rubric {rubric}: {p}" for p in _key_problems(identity, _RUBRIC_KEYS))
        if rubric not in RUBRIC_PATHS or not isinstance(identity, dict) or \
                identity.get("path") != RUBRIC_PATHS[rubric] or \
                not (isinstance(identity.get("sha256"), str) and _HEX["sha256"].fullmatch(identity["sha256"])):
            problems.append(f"rubric {rubric}: must name {RUBRIC_PATHS.get(rubric, 'a known rubric')} and its sha256")
            continue
        try:
            rubric_raw, _ = resolve_bytes(identity["path"], sha256=identity["sha256"])
            items[rubric] = rubric_items(rubric_raw, rubric)
        except (AttainabilityError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
            problems.append(f"rubric {rubric}: {exc}")
    entries = doc.get("entries")
    if not isinstance(entries, list):
        return problems + ["entries must be a list"], None
    seen: set[tuple] = set()
    for i, entry in enumerate(entries):
        problems.extend(f"entries[{i}]: {p}" for p in _entry_problems(entry, items, lines, chunk_of, seen))
    if problems:
        return problems, None
    return [], Attainability(None, doc, basis, items)


def _key_problems(value: Any, keys: set[str]) -> list[str]:
    """An unknown key in a mapping whose keys the format closes (#3239); a
    missing one is reported by the check that needs it."""
    extra = sorted(map(str, set(value) - keys)) if isinstance(value, dict) else []
    return [f"unknown keys {', '.join(extra)}"] if extra else []


def _entry_problems(entry: Any, items: dict[str, dict[str, str]], lines: dict[int, tuple[str, str]],
                    chunk_of: dict[str, list[int]], seen: set[tuple]) -> list[str]:
    if not isinstance(entry, dict):
        return ["not a mapping"]
    extra = sorted(set(entry) - _ENTRY_KEYS)
    # `route` too: an entry that leaves it out is not an entry with no route
    # to every reader, and `credited` reads it by key (#3182).
    missing = sorted(_ENTRY_KEYS - set(entry))
    if extra or missing:
        return ([f"unknown keys {', '.join(extra)}"] if extra else []) + \
               ([f"missing keys {', '.join(missing)}"] if missing else [])
    rubric, item, route, status, method = (entry.get(k) for k in ("rubric", "item_id", "route", "status", "method"))
    if not all(isinstance(v, str) and v.strip() for v in (rubric, item)) or \
            not (route is None or isinstance(route, str) and route.strip()):
        return ["rubric and item_id must be names, and route null or a name"]
    out: list[str] = []
    label = f"{rubric} {item}" + (f" route {route}" if route is not None else "")
    if rubric not in items:
        out.append(f"{label}: rubric {rubric!r} is not pinned under rubrics")
    elif item not in items[rubric]:
        out.append(f"{label}: no item {item!r} in the pinned rubric")
    if _key(entry) in seen:
        out.append(f"{label}: a second entry for the same item and route")
    seen.add(_key(entry))
    if status not in STATUSES:
        out.append(f"{label}: status {status!r} is not one of {', '.join(STATUSES)}")
    if not isinstance(entry["note"], str) or not entry["note"].strip():
        out.append(f"{label}: note must say what was decided and why")
    if not isinstance(method, str):
        return out + [f"{label}: method must be deterministic:<check>, curator or judge:<id>"]
    if method.startswith("deterministic:"):
        check = CHECKS_BY_NAME.get(method.removeprefix("deterministic:"))
        if check is None:
            return out + [f"{label}: no deterministic check named {method.removeprefix('deterministic:')!r}"]
        if (check.rubric, check.item_id, check.route) != (rubric, item, route):
            return out + [f"{label}: {method} decides {check.rubric} {check.item_id}"
                          + (f" route {check.route}" if check.route else "") + ", not this item"]
        expected = deterministic_entry(check, lines)
        differs = sorted(k for k in _ENTRY_KEYS if not identical(entry[k], expected[k]))
        if differs:
            out.append(f"{label}: is not what {method} writes over the pinned bytes "
                       f"(differs in {', '.join(differs)}; expected status {expected['status']}, "
                       f"hit_count {expected['evidence']['hit_count']})")
        return out
    if method != "curator" and not (method.startswith("judge:") and method.removeprefix("judge:").strip()):
        return out + [f"{label}: method must be deterministic:<check>, curator or judge:<id>"]
    evidence = entry["evidence"]
    if not isinstance(evidence, dict) or set(evidence) != {"snippets"} or not isinstance(evidence["snippets"], list):
        return out + [f"{label}: {method} evidence must be snippets: [{{chunk, lines, sha256}}]"]
    if status in SUPPORT_STATUSES and not evidence["snippets"]:
        out.append(f"{label}: {status} needs at least one snippet of the bundle that supports it")
    for j, snip in enumerate(evidence["snippets"]):
        out.extend(f"{label}: snippets[{j}]: {p}" for p in _snippet_problems(snip, lines, chunk_of))
    return out


def _snippet_problems(snip: Any, lines: dict[int, tuple[str, str]], chunk_of: dict[str, list[int]]) -> list[str]:
    if not isinstance(snip, dict) or set(snip) != _SNIPPET_KEYS:
        return ["must be {chunk, lines: [first, last], sha256}"]
    span = snip["lines"]
    if not (isinstance(span, list) and len(span) == 2 and all(type(n) is int for n in span)):
        return ["lines must be [first, last]"]
    if not isinstance(snip["chunk"], str):          # a list or mapping is not a key (#3108)
        return [f"chunk must be a chunk id, not {type(snip['chunk']).__name__}"]
    bounds = chunk_of.get(snip["chunk"])
    if bounds is None:
        return [f"no chunk {snip['chunk']!r} under chunk_rule"]
    first, last = span
    if not bounds[0] <= first <= last <= bounds[1]:
        return [f"lines {first}-{last} are not inside {snip['chunk']} (lines {bounds[0]}-{bounds[1]})"]
    if snip["sha256"] != snippet_sha256(lines, first, last):
        return [f"sha256 does not match lines {first}-{last} of the pinned bytes"]
    return []


def load(path: Path) -> Attainability:
    """A validated attainability file; raises `AttainabilityError` with every
    problem when it is not one — a file that cannot be read or is not UTF-8,
    or one naming a path no file can have (a NUL byte, a component longer
    than the file system allows, a directory it may not search) included, so
    `check` reports it and goes on to the next (#3180, #3217)."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AttainabilityError(path, [f"not UTF-8 text: {exc}"]) from exc
    except OSError as exc:
        raise AttainabilityError(path, [f"cannot be read: {exc.strerror or exc}"]) from exc
    try:
        problems, loaded = validate_text(text, path.name)
    except OSError as exc:     # a read the validator makes that no guard names (#3217)
        raise AttainabilityError(path, [f"a file it names cannot be read: {exc}"]) from exc
    if loaded is None:
        raise AttainabilityError(path, problems)
    return Attainability(path, loaded.document, loaded.bundle_basis, loaded.rubric_items)


def document_for(bundle_path: str, md5: str, directory: Path = ATTAINABILITY_DIR) -> Path | None:
    """The attainability file for one bundle version, if there is one.
    Raises `OSError` when the name the version gives cannot be looked up —
    a component longer than the file system allows, say, from a record
    whose md5 or path is malformed — and `ValueError` when the path or md5
    carries a NUL byte, which no file name can: `Path.is_file` would answer
    False for it rather than raise, and the row would read as a bundle
    version with no file (#3541). `credited_report` reports either row as
    unreadable (#3469)."""
    from data_sheets_schema.corpus import anchored
    if "\0" in bundle_path or "\0" in md5:
        raise ValueError("the bundle_path or bundle_md5 carries a NUL byte, which no file name can")
    candidate = anchored(Path(directory)) / f"{Path(bundle_path).stem}_{md5}.yaml"
    return candidate if candidate.is_file() else None


# --------------------------------------------------------------------------
# Scored although not stated in the source


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def evaluation_items(evaluation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Item id → the evaluation's own item, under the judge contract's ids."""
    out = {}
    for element in evaluation.get("elements") or []:
        for index, sub in enumerate(element.get("sub_elements") or [], 1):
            out[sub.get("item_id") or f"E{element['id']}.{index}"] = sub
    categories = evaluation.get("categories") or []
    if isinstance(categories, dict):
        categories = categories.values()
    for question in [q for c in categories for q in c.get("questions") or []] + list(evaluation.get("questions") or []):
        out[f"Q{question['id']}"] = question
    return out


def evaluation_rubric(evaluation: dict[str, Any]) -> str:
    """The rubric an evaluation scored, as an attainability file names it."""
    return str(evaluation.get("rubric", "")).removesuffix("-semantic")


def _label(entry: dict[str, Any]) -> str:
    return entry["item_id"] + (f" route {entry['route']}" if entry["route"] else "")


def absences_checked(evaluation: dict[str, Any], attainability: Attainability) -> list[str]:
    """The `not_stated_in_source` entries of `attainability` on the rubric
    `evaluation` scored — the only items `credited_despite_absence` can
    name. Empty means no finding was possible, which is not a zero."""
    rubric = evaluation_rubric(evaluation)
    return [_label(e) for e in attainability.entries("not_stated_in_source") if e["rubric"] == rubric]


def unchecked_reason(evaluation: dict[str, Any], attainability: Attainability) -> str | None:
    """Why the file can yield no finding for `evaluation`, or None when it
    can: it pins no text of the evaluation's rubric (the CHORUS file and a
    rubric20 evaluation), or marks none of that rubric's items absent."""
    if absences_checked(evaluation, attainability):
        return None
    rubric = evaluation_rubric(evaluation)
    if rubric not in attainability.rubric_items:
        pinned = ", ".join(sorted(attainability.rubric_items)) or "none"
        return (f"the file pins no {rubric or 'rubric the evaluation names'} text (it pins {pinned}), "
                "so it decides nothing for this evaluation")
    return f"the file marks no {rubric} item not_stated_in_source"


def credited_despite_absence(evaluation: dict[str, Any], attainability: Attainability) -> list[dict[str, Any]]:
    """Items `evaluation` credited (a positive score on an applicable item)
    that `attainability` marks `not_stated_in_source` — a value from outside
    the bundle, or an invented one: kind `credited`. A route entry never
    settles the item, so a credit on it is kind `credited_on_other_route`
    (#3219): it cannot rest on that route, but may rest on another the
    rubric admits (E1.1's persistent URI), which a curator must read — it
    is reported for review and is not a finding. An
    item whose name differs from the pinned rubric's is reported as
    `unjoined`, never skipped. An empty list is a measured zero only where
    `absences_checked` is not empty: a file that pins no text of the
    evaluation's rubric, or marks none of its items absent, cannot yield a
    finding (#3181). Reads `evaluation`; changes nothing."""
    rubric = evaluation_rubric(evaluation)
    names = attainability.rubric_items.get(rubric)
    if names is None:
        return []
    items = evaluation_items(evaluation)
    out = []
    for entry in attainability.entries("not_stated_in_source"):
        if entry["rubric"] != rubric:
            continue
        item = items.get(entry["item_id"])
        base = {"item_id": entry["item_id"], "route": entry["route"], "method": entry["method"]}
        if item is None or item.get("name") != names[entry["item_id"]]:
            out.append({**base, "kind": "unjoined",
                        "detail": "the evaluation has no item of this id and name in the pinned rubric"})
            continue
        excluded = (item.get("applicable") in (False, "false", "False")
                    or item.get("applicability_status") == "not_applicable")
        score = _number(item.get("score"))
        if not excluded and score is not None and score > 0:
            if entry["route"] is None:
                out.append({**base, "kind": "credited", "score": score})
            else:
                out.append({**base, "kind": "credited_on_other_route", "score": score,
                            "detail": f"the bundle states nothing by the {entry['route']} route; "
                                      "the credit may rest on another route, for a curator to read"})
    return out


class UnreadableEvaluation(ValueError):
    """An evaluation, or the provenance record it names, that cannot be read
    as one: `credited` reports its row with the reason and goes on (#3200)."""


def evaluation_bundle(evaluation: dict[str, Any]) -> dict[str, Any] | None:
    """The bundle path and md5 the evaluated record read, from its
    provenance record — never from the project name, whose bundle has more
    than one version. None when no record is found or it names no bundle;
    raises `UnreadableEvaluation` naming the record when it is there and
    cannot be read as one (#3200)."""
    from data_sheets_schema.provenance import record_path_for
    from data_sheets_schema.schema_cache import load_yaml
    parts = Path(str(evaluation.get("d4d_file", ""))).parts
    if len(parts) < 3 or not parts[-1].endswith("_d4d.yaml"):
        return None
    project = evaluation.get("project") or parts[-1].removesuffix("_d4d.yaml")
    if not isinstance(project, str):
        raise UnreadableEvaluation(f"the evaluation's project is not a name: {project!r}")
    record = record_path_for(project, parts[-3], parts[-2])
    try:
        if not record.is_file():
            return None
        document = load_yaml(record)
    except UnicodeDecodeError as exc:
        raise UnreadableEvaluation(f"the provenance record {record} is not UTF-8 text: {exc}") from exc
    except OSError as exc:
        raise UnreadableEvaluation(f"the provenance record {record} cannot be read: {exc.strerror or exc}") from exc
    except (yaml.YAMLError, RecursionError) as exc:
        raise UnreadableEvaluation(f"the provenance record {record} is not YAML: {exc}") from exc
    except ValueError as exc:                  # a path the readers refuse rather than answer
        raise UnreadableEvaluation(f"the provenance record {record!r} cannot be read: {exc}") from exc
    document = {} if document is None else document
    # Each type is tested on the value as written, before any emptiness test:
    # a falsy non-mapping `inputs` ([], '', false) or a falsy non-string
    # bundle field (0, []) is a damaged record, not one that names no bundle
    # (#3489). A record names no bundle only when `inputs` is absent, null
    # or a mapping, and in it `bundle_path` or `bundle_md5` is absent, null
    # or an empty string. An empty string for `inputs` itself is unreadable.
    inputs = document.get("inputs") if isinstance(document, dict) else None
    if not isinstance(document, dict) or not (inputs is None or isinstance(inputs, dict)):
        raise UnreadableEvaluation(f"the provenance record {record} is not a mapping with an inputs mapping")
    inputs = inputs or {}
    if any(inputs.get(k) is not None and not isinstance(inputs[k], str) for k in ("bundle_path", "bundle_md5")):
        raise UnreadableEvaluation(f"the provenance record {record} names a bundle_path or bundle_md5 "
                                   "that is not a string")
    if not inputs.get("bundle_path") or not inputs.get("bundle_md5"):
        return None
    return {"path": inputs["bundle_path"], "md5": inputs["bundle_md5"], "record": str(record)}


def read_evaluation(path: Path) -> dict[str, Any]:
    """The evaluation at `path`, checked as far as `credited` reads it: a
    JSON object whose items can be keyed (`evaluation_items`). Raises
    `UnreadableEvaluation` naming the file and why (#3200)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise UnreadableEvaluation(f"the evaluation {path} is not UTF-8 text: {exc}") from exc
    except OSError as exc:
        raise UnreadableEvaluation(f"the evaluation {path} cannot be read: {exc.strerror or exc}") from exc
    try:
        evaluation = json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise UnreadableEvaluation(f"the evaluation {path} is not JSON: {exc}") from exc
    if not isinstance(evaluation, dict):
        raise UnreadableEvaluation(f"the evaluation {path} is not a JSON object")
    try:
        evaluation_items(evaluation)
    except (KeyError, TypeError, AttributeError) as exc:
        # An element with no `id`, a sub-element or question that is not an
        # object: the items cannot be joined to the rubric's ids.
        raise UnreadableEvaluation(f"the evaluation {path} has items that cannot be keyed: "
                                   f"{type(exc).__name__}: {exc}") from exc
    return evaluation


def credited_report(evaluation_paths: Iterable[Path], directory: Path = ATTAINABILITY_DIR) -> list[dict[str, Any]]:
    """One row per evaluation: the bundle it scored, the attainability file
    for that bundle version if there is one, the absences it was checked
    against, and its findings. `unchecked` says why a row could yield no
    finding — no bundle version, no file, or a file that decides nothing for
    the evaluation's rubric — and is None only on a row whose empty
    `findings` is a measured zero (#3181). A row whose evaluation or
    provenance record cannot be read is `unreadable`, its `unchecked` the
    reason, and the evaluations after it are still reported (#3200)."""
    loaded: dict[Path, Attainability] = {}
    rows = []
    for path in evaluation_paths:
        try:
            evaluation = read_evaluation(path)
            bundle = evaluation_bundle(evaluation)
            try:
                doc = document_for(bundle["path"], bundle["md5"], directory) if bundle else None
            except (OSError, ValueError) as exc:
                # A bundle_path or bundle_md5 that is a string but names no
                # file the system can look up: too long a component
                # (OSError, #3469), a NUL byte (`document_for` refuses it
                # with ValueError, #3541).
                raise UnreadableEvaluation(
                    f"the provenance record {bundle['record']} names a bundle version whose "
                    f"attainability file cannot be looked up: {getattr(exc, 'strerror', None) or exc}") from exc
        except UnreadableEvaluation as exc:
            rows.append({"evaluation": str(path), "bundle": None, "rubric": None, "attainability": None,
                         "absences_checked": [], "findings": [], "unchecked": str(exc), "unreadable": True})
            continue
        row: dict[str, Any] = {"evaluation": str(path), "bundle": bundle, "rubric": evaluation_rubric(evaluation),
                               "unreadable": False}
        if doc is None:
            row.update(attainability=None, absences_checked=[], findings=[],
                       unchecked="no attainability file for this bundle version" if bundle else
                       "no bundle version: the evaluated record's provenance was not found or names none")
        else:
            if doc not in loaded:
                loaded[doc] = load(doc)
            got = loaded[doc]
            row.update(attainability=str(doc), absences_checked=absences_checked(evaluation, got),
                       unchecked=unchecked_reason(evaluation, got),
                       findings=credited_despite_absence(evaluation, got))
        rows.append(row)
    return rows


# --------------------------------------------------------------------------
# Command line


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m data_sheets_schema.attainability",
                                     description="Per-bundle attainability of rubric items (#2925).")
    sub = parser.add_subparsers(dest="command", required=True)
    derive = sub.add_parser("derive", help="deterministic entries for one bundle version")
    derive.add_argument("--bundle", required=True, help="repository-relative bundle path")
    derive.add_argument("--md5", help="the version to derive (default: the file on disk)")
    derive.add_argument("--sha256")
    derive.add_argument("--write", action="store_true", help=f"write under {ATTAINABILITY_DIR}/")
    check = sub.add_parser("check", help="validate attainability files against their pinned bytes")
    check.add_argument("files", nargs="*", type=Path)
    credited = sub.add_parser("credited", help="items credited although marked not_stated_in_source; "
                                               "exits 1 when an evaluation cannot be read")
    credited.add_argument("evaluations", nargs="+", type=Path)
    credited.add_argument("--strict", action="store_true",
                          help="exit 1 on any finding (a row reported unchecked, or a credit "
                               "on an item a route entry leaves open, is not one)")
    args = parser.parse_args(argv)

    if args.command == "derive":
        doc = build_document(args.bundle, md5=args.md5, sha256=args.sha256)
        if args.write:
            print(write_document(doc))
        else:
            sys.stdout.write(dump(doc))
        return 0
    if args.command == "check":
        from data_sheets_schema.corpus import anchored
        files = args.files or sorted(anchored(ATTAINABILITY_DIR).glob("*.yaml"))
        failed = 0
        for path in files:
            try:
                got = load(path)
            except AttainabilityError as exc:
                failed += 1
                print(f"INVALID {path}")
                for problem in exc.problems:
                    print(f"  - {problem}")
                continue
            counts = {s: len(got.entries(s)) for s in STATUSES if got.entries(s)}
            print(f"ok {path} ({got.bundle_basis['source']}): "
                  + ", ".join(f"{n} {s}" for s, n in counts.items()))
        if not files:
            print(f"no attainability files under {ATTAINABILITY_DIR}")
        return 1 if failed else 0
    try:
        rows = credited_report(args.evaluations)
    except AttainabilityError as exc:
        print(f"INVALID {exc.path}")
        for problem in exc.problems:
            print(f"  - {problem}")
        return 1
    findings = to_review = 0
    for row in rows:
        bundle = row["bundle"]
        parts = [bundle["md5"][:8] if bundle else "bundle unknown"] + ([row["attainability"]] if row["attainability"] else [])
        parts.append(f"{'unreadable' if row['unreadable'] else 'unchecked'}: {row['unchecked']}" if row["unchecked"]
                     else f"{row['rubric']} checked against {', '.join(row['absences_checked'])}")
        print(f"{row['evaluation']}: " + " — ".join(parts))
        for f in row["findings"]:
            if f["kind"] in FINDING_KINDS:
                findings += 1
            else:
                to_review += 1
            route = f" (route {f['route']})" if f["route"] else ""
            print(f"  {f['kind']}: {f['item_id']}{route} {f.get('score', '')} {f.get('detail', '')}".rstrip())
    covered = sum(1 for row in rows if row["attainability"])
    checked = sum(1 for row in rows if row["unchecked"] is None)
    unreadable = sum(1 for row in rows if row["unreadable"])
    # A row that could yield no finding is counted apart from a measured zero
    # (#3181), and one that could not be read apart from both (#3200).
    print(f"{len(rows)} evaluation(s), "
          + (f"{unreadable} that could not be read, " if unreadable else "")
          + f"{covered} on a bundle version with an attainability file, "
          f"{checked} checked against at least one absence, {findings} finding(s)"
          + (f", {to_review} credit(s) on another route to review" if to_review else ""))
    # An input that cannot be read fails the run as an INVALID file fails
    # `check`, with or without --strict: it is not a pass (#3200).
    return 1 if unreadable or (args.strict and findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
