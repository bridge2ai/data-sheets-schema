"""Status context: a status marker lost between a source passage and a
record value (#2917, a sub-issue of #1782). A diagnostic, never a gate.

`receipts.check()` verifies that a snippet occurs in its chunk; it does not
check that the snippet supports its value (`receipts.NON_CHECKS`). A clause
cut from "this project will A) ... E) standardize data ..." therefore
verifies, and the record can state the planned work in the present tense.
`source_review.check()` compares the two statuses a reviewer declares; it
does not compare a declared `planned` status with the value text. This
module reads the same inputs and reports, lexically, where a registered
status marker was lost. It changes no verdict, writes nothing, and is not
part of any provenance block.

One marker registry (`STATUS_MARKERS`, classes `planned`, `prospective` and
`in_progress`) serves two rules.

Rule 1, receipt context (`receipt_context`). For each snippet a coverage
receipt verifies in its own chunk, the snippet is located in the chunk's
raw text through a map from `receipts.normalise` offsets back to raw
offsets, and two contexts are read:

(a) its enclosing sentence, extended across an enumeration — inline
    `A) ... E)` / `(a)` / `1)` items or bulleted and numbered lines — back
    to the governing clause. Only the governing clause and the snippet's
    own item are read; a sibling item's marker governs that item, not this
    one. The governing clause is the open clause before the first item
    (ending in `:` or in no sentence terminator), or a finished sentence
    that announces the list ("the following", "as follows"); any other
    finished sentence — the end of the paragraph above a bulleted list or a
    numbered section heading — governs nothing after it, and only the
    item is read. Without item markers a sentence is narrowed to the
    `;`-clauses the snippet spans (and any lead-in up to a `:`), since `;`
    then separates independent clauses or the terms of a list.
(b) the nearest preceding heading-like line, or lead-in clause ending in
    `:`, in the same block that carries a status marker. Count labels in a
    flattened panel are heading-like and carry none, so they are passed
    over; a heading with a counter marker and no status marker ("Current
    Released Dataset") closes the scope first, including one on the line
    the snippet's own sentence or item starts on (a snippet that quotes the
    counter-heading is under it); a one-word line is neither a status nor a
    counter heading (a flattened table's "Planned" or "Completed" cell); a
    prose line, a document separator or two blank lines end the block.

Each `...`-part of a snippet is read in its own context, so the text a
snippet elides counts where it shares a part's sentence and not where it
runs across a flattened table.

`governor_outside_snippet`: that context carries a marker of a class the
snippet does not carry, and the value at the receipt's slot carries no
marker expressing that status. `modal_dropped`: the snippet itself carries
the marker and the value does not. A snippet that occurs more than once in
its chunk is flagged only when every occurrence's context carries the
class.

Rule 2, source-review status expression (`review_status_expression`). For
each `supported` claim of an audit's `source_review`:
`status_unexpressed` when the claim is declared `planned` or `in_progress`
and its text carries no marker expressing that status (with the record the
review is bound to, a marker elsewhere in the same value counts as
expressed); `planned_evidence_declared_fact` when the claim is declared
`fact` and an evidence quote, or its context as in rule 1, carries a
planned or prospective marker.

Label-like slots (`name`, `title`, `label`) are reported in their own bucket
by both rules: a name rarely carries status and would dominate either list.

What a flag is, and what it is not, is `ASSURANCE`.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from data_sheets_schema import receipts as rc

INSTRUMENT = "status_context v1 (#2917)"
RULE_RECEIPT = "receipt status context (governor_outside_snippet, modal_dropped)"
RULE_REVIEW = "source-review status expression (status_unexpressed, planned_evidence_declared_fact)"

ASSURANCE = (
    "Lexical and non-gating: this detects the loss of a registered status marker between a source "
    "passage and a value. A flag is not a defect — another passage can independently support the "
    "unqualified value, and a marker in the context need not govern the quoted words. The absence "
    "of a flag establishes neither semantic support nor the absence of a status defect.")

# ------------------------------------------------------------------ registry
#: Status marker classes, as patterns over `receipts.normalise` text (case
#: folded, punctuation to space, whitespace collapsed). The terms are
#: dataset-neutral; which of them count is a curator's judgement (#2917),
#: and the vocabulary's digest is recorded in every output so a reader can
#: tell revisions apart.
STATUS_MARKERS: dict[str, tuple[tuple[str, str], ...]] = {
    "planned": (
        ("will", r"\bwill\b"),
        ("planned", r"\bplanned\b"),
        ("plan to", r"\bplan(?:s|ning)? to\b"),
        ("intend to", r"\bintend(?:s|ing)? to\b"),
        ("proposed", r"\bpropos(?:ed|es|e|ing)\b"),
        # "to be used" is an instruction, not a status (a licence's "is not
        # to be used for"), so it is left out of the participle form; it is
        # listed in EXCLUDED_TERMS with the other exclusions.
        ("to be <participle>", r"\bto be (?!used\b)\w+(?:ed|en)\b"),
    ),
    "prospective": (
        ("anticipated", r"\banticipat(?:ed|es|e|ing)\b"),
        ("expected to", r"\bexpected to\b"),
        ("projected to", r"\bprojected to\b"),
        ("future", r"\bfuture\b"),
        ("goal", r"\bgoals?\b"),
        ("aim to", r"\baims? to\b"),
        ("forthcoming", r"\b(?:forthcoming|upcoming)\b"),
    ),
    "in_progress": (
        ("in progress", r"\bin progress\b"),
        ("in process", r"\bin process\b|\bin the process of\b"),
        ("ongoing", r"\bongoing\b"),
        ("underway", r"\bunder ?way\b"),
        ("under development", r"\bunder (?:active )?development\b"),
        ("being <participle>", r"\b(?:is|are) (?:currently )?being \w+(?:ed|en)\b"),
    ),
}

#: Terms deliberately not registered, with the reason — the list a curator
#: signs off together with STATUS_MARKERS (#2917, owner decision 3). An
#: exclusion carved out of a registered pattern (a negative lookahead) is
#: listed here too, so the list is complete without reading the patterns.
EXCLUDED_TERMS: dict[str, str] = {
    "target": "the noun sense dominates (target population, target variable)",
    "intended": "purpose vocabulary (intended uses), not a status",
    "prospective": "a study-design term (a prospective cohort), not a status",
    "shall": "an obligation in licences and agreements, not a plan",
    "expected": "the statistical sense (expected value); only 'expected to' is registered",
    "plan": "the noun (a data management plan); only 'planned' and 'plan(s) to' are registered",
    "to be used": ("an instruction, not a status (a licence's 'is not to be used for'); excluded from the "
                   "registered 'to be <participle>' pattern by a negative lookahead"),
}

#: Which marker classes express which status. A prospective marker
#: ("anticipated", "future") expresses the same not-yet status a planned one
#: does, so each satisfies the other; in-progress is its own status.
EXPRESSED_BY: dict[str, tuple[str, ...]] = {
    "planned": ("planned", "prospective"),
    "prospective": ("planned", "prospective"),
    "in_progress": ("in_progress",),
}

#: A source-review `claim_status` whose text should carry a marker, and the
#: marker class it names. `fact` is rule 2's other half.
DECLARED_STATUS: dict[str, str] = {"planned": "planned", "in_progress": "in_progress"}

#: Classes whose presence in the evidence contradicts a claim declared `fact`.
PLANNED_EVIDENCE_CLASSES: tuple[str, ...] = ("planned", "prospective")

#: A heading carrying one of these, and no status marker, closes a status
#: heading's scope ("Current Released Dataset" below "Anticipated Final
#: Dataset"). Whether "Current ..." closes a scope is owner decision 3.
COUNTER_MARKERS: tuple[tuple[str, str], ...] = (
    ("current", r"\bcurrent(?:ly)?\b"),
    ("released", r"\breleased\b"),
    ("completed", r"\bcompleted\b"),
    ("existing", r"\bexisting\b"),
    ("available now", r"\bnow available\b|\bavailable now\b"),
    ("to date", r"\bto date\b"),
    ("as of", r"\bas of\b"),
)

#: Leaf keys whose values are labels, reported in their own bucket.
LABEL_LEAVES = frozenset({"name", "title", "label"})


def _vocabulary() -> dict[str, Any]:
    body = {"status": STATUS_MARKERS, "counter": COUNTER_MARKERS, "expressed_by": EXPRESSED_BY,
            "declared": DECLARED_STATUS, "planned_evidence": PLANNED_EVIDENCE_CLASSES,
            "label_leaves": sorted(LABEL_LEAVES)}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
    return {"version": 1, "sha256": digest}


VOCABULARY = _vocabulary()

_STATUS_RES = tuple((cls, term, re.compile(pat)) for cls, terms in STATUS_MARKERS.items()
                    for term, pat in terms)
_COUNTER_RES = tuple((term, re.compile(pat)) for term, pat in COUNTER_MARKERS)


def markers(normalised: str) -> list[tuple[str, str, int]]:
    """(class, term, offset) for every registered status marker in text
    already folded by `receipts.normalise`, in text order."""
    found = [(cls, term, m.start()) for cls, term, rx in _STATUS_RES for m in rx.finditer(normalised)]
    return sorted(found, key=lambda f: f[2])


def classes(text: str) -> dict[str, str]:
    """{class: first term} for the status markers in raw `text`."""
    out: dict[str, str] = {}
    for cls, term, _off in markers(rc.normalise(text)):
        out.setdefault(cls, term)
    return out


def expresses(value_classes, status_class: str) -> bool:
    """Whether markers of `value_classes` express `status_class`."""
    return any(c in value_classes for c in EXPRESSED_BY[status_class])


def _counter(normalised: str) -> str | None:
    return next((term for term, rx in _COUNTER_RES if rx.search(normalised)), None)


def slot_class(path: str) -> str:
    """`label` for a label-like leaf (`creators[0].name`, `/title`), else
    `value`. Takes a dotted receipt path or a JSON Pointer."""
    tokens = [t for t in re.split(r"[./\[\]]+", path or "") if t and not t.isdigit()]
    return "label" if tokens and tokens[-1] in LABEL_LEAVES else "value"


def _value_text(value: Any) -> str:
    """The scalar text of a value or subtree, keys excluded."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_value_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_value_text(v) for v in value)
    return "" if value is None else str(value)


# ------------------------------------------------------- normalised offsets
_WORD_OR_SPACE = re.compile(r"[\w\s]", re.UNICODE)
_SPACE = re.compile(r"\s", re.UNICODE)


def normalised_offsets(text: str) -> tuple[str, list[int]] | None:
    """`receipts.normalise(text)` and, for each of its characters, the offset
    in `text` it came from — the map that locates a verified snippet back in
    the raw chunk.

    The folds are replayed in the validator's order: JSON-escaped whitespace
    and quotes, NFKC and case folding (per base character with its combining
    marks), punctuation to space, whitespace collapsed and stripped. None
    when the replay does not reproduce `receipts.normalise(text)` exactly —
    a composition NFKC makes across characters this replay keeps apart — so
    a caller never reports a location the validator's own folding would not
    give."""
    s1: list[str] = []
    o1: list[int] = []
    i, n = 0, len(text)
    while i < n:                                   # re.sub(r"\\[ntr]", " ", ...)
        if text[i] == "\\" and i + 1 < n and text[i + 1] in "ntr":
            s1.append(" "); o1.append(i); i += 2
        else:
            s1.append(text[i]); o1.append(i); i += 1
    s2: list[str] = []
    o2: list[int] = []
    i, n = 0, len(s1)
    while i < n:                                   # .replace('\\"', '"')
        if s1[i] == "\\" and i + 1 < n and s1[i + 1] == '"':
            s2.append('"'); o2.append(o1[i]); i += 2
        else:
            s2.append(s1[i]); o2.append(o1[i]); i += 1
    out: list[str] = []
    offs: list[int] = []
    i, n = 0, len(s2)
    while i < n:
        j = i + 1
        while j < n and unicodedata.combining(s2[j]):
            j += 1
        for ch in unicodedata.normalize("NFKC", "".join(s2[i:j])).casefold():
            if not _WORD_OR_SPACE.match(ch) or _SPACE.match(ch):
                if not out or out[-1] == " ":
                    continue
                ch = " "
            out.append(ch); offs.append(o2[i])
        i = j
    if out and out[-1] == " ":
        out.pop(); offs.pop()
    norm = "".join(out)
    return (norm, offs) if norm == rc.normalise(text) else None


# ------------------------------------------------------------ bundle view
#: A sentence ends at one or more of .!? (and closing quotes or brackets)
#: before whitespace — not after an initial, a listed abbreviation, or a
#: one- or two-digit list number at the start of a line.
_TERMINATOR = re.compile(r"[.!?]+[\"'”’)\]]*(?=\s|$)")
_ABBREVIATIONS = frozenset({"al", "approx", "dept", "dr", "eq", "fig", "figs", "inc", "jr", "ltd", "mr",
                            "mrs", "ms", "no", "prof", "ref", "refs", "sr", "st", "univ", "vol", "vs"})
#: An inline enumeration item: "A) ", "(a) ", "3) " after whitespace or ;,:
_INLINE_ITEM = re.compile(r"(?:^|(?<=[\s;,:]))(?:\((?P<a>[A-Za-z]|\d{1,2})\)|(?P<b>[A-Za-z]|\d{1,2})\))(?=\s)")
#: A bulleted or numbered line.
_LINE_ITEM = re.compile(r"^[ \t]*(?:[-•*·–—▪◦‣]|\(?(?:[A-Za-z]|\d{1,2})[.)])[ \t]+")
_SEPARATOR = re.compile(r"^(?:={10,}|-{10,})$|^(?:FILE|PATH|SIZE|ROLE): ")

MAX_SENTENCE_LINES = 12     # a sentence is followed across at most this many wrapped lines
MAX_ITEMS = 26              # an enumeration is followed back across at most this many items
HEADING_WINDOW = 30         # non-blank lines scanned above a snippet for a status heading
HEADING_MAX_CHARS = 60
HEADING_MAX_WORDS = 8
PROSE_LINE_CHARS = 160      # a line this long is a paragraph, and ends a block


def _heading_like(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > HEADING_MAX_CHARS or len(s.split()) > HEADING_MAX_WORDS:
        return False
    if _LINE_ITEM.match(line) or _SEPARATOR.match(s) or s[-1] in ".;,!?":
        return False
    first = next((ch for ch in s if ch.isalpha()), None)
    return first is not None and (first.isupper() or s[0].isdigit() or s[0] == "#")


def _prose_line(line: str) -> bool:
    s = line.strip().rstrip("\"'”’)]")
    if not s or _LINE_ITEM.match(line):
        return False
    return len(s) > PROSE_LINE_CHARS or (s[-1] in ".!?" and len(s.split()) >= 5)


def _continues(prev: str, cur: str) -> bool:
    """A line wrapped mid-sentence: the previous line is text that has not
    ended, and this one starts in lower case and is not a list item."""
    p, c = prev.rstrip(), cur.lstrip()
    if not p or not c or _SEPARATOR.match(p.strip()) or _LINE_ITEM.match(cur):
        return False
    return p.rstrip("\"'”’)]")[-1:] not in (".", "!", "?") and c[0].islower()


def _is_terminator(line: str, m: re.Match) -> bool:
    if m.group().rstrip("\"'”’)]") != ".":
        return True
    before = line[:m.start()]
    w = re.search(r"(\w+)$", before)
    if not w:
        return True
    word = w.group(1)
    if len(word) == 1 and word.isalpha():
        return False
    if word.casefold() in _ABBREVIATIONS:
        return False
    return not (word.isdigit() and len(word) <= 2 and not before[:w.start()].strip())


#: A finished sentence that announces the list after it ("... the
#: following data.", "... as follows.").
_ANNOUNCES_LIST = re.compile(r"\b(?:the following|as follows)\b")


def _governs_enumeration(lead: str) -> bool:
    """Whether the text before an enumeration's first item is its governing
    clause. An open clause is: one ending in ':' or in no sentence
    terminator ("this project will A) ..."). A finished sentence is only
    when it announces the list ("The study will collect the following
    data."); otherwise it is the last sentence of whatever came before — a
    previous paragraph above a bulleted list or a numbered section heading
    — and governs nothing after it (#3167). Terminators are read as a
    sentence end is (`_is_terminator`), so "approx." does not finish one."""
    s = lead.rstrip()
    if not s:
        return False
    last = s.rsplit("\n", 1)[-1]
    m = next((m for m in _TERMINATOR.finditer(last) if m.end() == len(last)), None)
    if m is None or not _is_terminator(last, m):
        return True
    return bool(_ANNOUNCES_LIST.search(rc.normalise(s)))


class BundleView:
    """A bundle's text with its chunk manifest: chunk texts, bundle line
    numbers, and the contexts rule 1 reads. The chunk texts are the bundle
    sliced at the manifest's line ranges — `chunking.chunk_texts` exactly."""

    def __init__(self, text: str, manifest: dict[str, Any]):
        self.text = text
        self.starts = [0] + [m.end() for m in re.finditer("\n", text)]
        self.chunks: dict[str, tuple[int, int, str | None]] = {}
        for c in manifest.get("chunks") or []:
            if not isinstance(c, dict) or not isinstance(c.get("id"), str) or "lines" not in c:
                continue
            a, b = (c["lines"] + [None, None])[:2] if isinstance(c["lines"], list) else (None, None)
            if not (type(a) is int and type(b) is int and 1 <= a <= b <= len(self.starts)):
                continue                   # not a line range of this text
            lo = self.starts[a - 1]
            hi = self.starts[b] if b < len(self.starts) else len(text)
            self.chunks[c["id"]] = (lo, hi, c.get("source"))
        self._norm: dict[str, tuple[str, list[int]] | None] = {}
        self._hays: dict[str, tuple[str, str, str, str]] = {}

    # --- lines
    def line_of(self, off: int) -> int:
        return bisect.bisect_right(self.starts, off)

    def bounds(self, ln: int) -> tuple[int, int]:
        ls = self.starts[ln - 1]
        le = self.starts[ln] - 1 if ln < len(self.starts) else len(self.text)
        return ls, le

    def line(self, ln: int) -> str:
        ls, le = self.bounds(ln)
        return self.text[ls:le]

    def chunk_text(self, cid: str) -> str:
        lo, hi, _src = self.chunks[cid]
        return self.text[lo:hi]

    # --- verification and location
    def verified(self, cid: str, snippet: str) -> bool:
        """Whether `receipts.snippet_in` verifies the snippet in its own
        chunk — the validator's verdict, not a second one."""
        text = self.chunk_text(cid)
        if cid not in self._hays:
            self._hays[cid] = (rc.normalise(text), rc.normalise_joined(text),
                               rc.normalise(rc.elide_artifact_lines(text)),
                               rc.normalise_joined(rc.elide_artifact_lines(text)))
        return rc.snippet_in(snippet, text, *self._hays[cid])[0]

    def locate(self, cid: str, snippet: str) -> list[list[tuple[int, int]]]:
        """Every occurrence of the snippet in its chunk, each as the bundle
        (start, end) span of every part. Parts split at `...`, else at the
        snippet's own line breaks, as the validator splits them; a snippet
        the validator verified only across a joined line break or an elided
        artifact line is not located here (reported as unlocated)."""
        if cid not in self._norm:
            self._norm[cid] = normalised_offsets(self.chunk_text(cid))
        mapped = self._norm[cid]
        if mapped is None:
            return []
        norm, offs = mapped
        base = self.chunks[cid][0]
        splits = [rc._ELLIPSIS.split(snippet)]
        if "\n" in snippet:
            splits.append(snippet.split("\n"))
        for raw_parts in splits:
            parts = [p for p in (rc.normalise(x) for x in raw_parts) if p]
            if not parts:
                continue
            found: list[list[tuple[int, int]]] = []
            i = norm.find(parts[0])
            while i >= 0 and len(found) < 50:
                spans = [(i, i + len(parts[0]))]
                for p in parts[1:]:
                    j = norm.find(p, spans[-1][1])
                    if j < 0:
                        break
                    spans.append((j, j + len(p)))
                if len(spans) < len(parts):
                    break                  # a later start cannot find what this one did not
                found.append([(base + offs[s], base + offs[e - 1] + 1) for s, e in spans])
                i = norm.find(parts[0], i + 1)
            if found:
                return found
        return []

    # --- sentences
    def _sentence_start(self, pos: int) -> tuple[int, int | None]:
        """(start of the sentence holding `pos`, start of the terminator
        that bounds it, or None where a line start bounds it)."""
        for _ in range(MAX_SENTENCE_LINES):
            ln = self.line_of(pos)
            ls, _le = self.bounds(ln)
            line = self.text[ls:pos]
            last = None
            for m in _TERMINATOR.finditer(line):
                if _is_terminator(line, m):
                    last = m
            if last is not None:
                s = ls + last.end()
                while s < pos and self.text[s].isspace():
                    s += 1
                return s, ls + last.start()
            if ln > 1 and _continues(self.line(ln - 1), self.line(ln)):
                pos = self.bounds(ln - 1)[1]
                continue
            s = ls
            while s < pos and self.text[s] in " \t":
                s += 1
            return s, None
        return self.bounds(self.line_of(pos))[0], None

    def _sentence_end(self, pos: int) -> int:
        for _ in range(MAX_SENTENCE_LINES):
            ln = self.line_of(pos)
            ls, le = self.bounds(ln)
            line = self.text[ls:le]
            for m in _TERMINATOR.finditer(line, pos - ls):
                if _is_terminator(line, m):
                    return ls + m.end()
            if ln < len(self.starts) and _continues(line, self.line(ln + 1)):
                pos = self.starts[ln]
                continue
            return le
        return self.bounds(self.line_of(pos))[1]

    def _starts_with_item(self, start: int) -> bool:
        ls, le = self.bounds(self.line_of(start))
        if not self.text[ls:start].strip() and _LINE_ITEM.match(self.text[ls:le]):
            return True
        return bool(_INLINE_ITEM.match(self.text, start))

    def _previous_unit(self, start: int, term: int | None) -> tuple[int, int | None] | None:
        """The sentence before the one starting at `start`: before its
        terminator on the same line, else the last sentence of the previous
        non-blank line (one blank line is passed over; a separator or a
        second blank line ends the walk). Whether the unit reached governs
        the items after it is `_governs_enumeration`'s question, not this
        one's."""
        if term is not None:
            return self._sentence_start(term)
        k, blanks = self.line_of(start) - 1, 0
        while k >= 1:
            line = self.line(k)
            if not line.strip():
                blanks += 1
                if blanks > 1:
                    return None
                k -= 1
                continue
            if _SEPARATOR.match(line.strip()):
                return None
            ls, _le = self.bounds(k)
            end = ls + len(line.rstrip().rstrip("\"'”’)]").rstrip(".!?"))
            return self._sentence_start(end)
        return None

    def _item_markers(self, start: int, end: int) -> tuple[list[list[tuple[int, str, int]]], list[int]]:
        """(inline runs of two or more consecutive labels, line-item offsets)
        within [start, end)."""
        line_items: list[int] = []
        for ln in range(self.line_of(start), self.line_of(max(start, end - 1)) + 1):
            ls, le = self.bounds(ln)
            m = _LINE_ITEM.match(self.text[ls:le])
            if m and ls + (len(m.group()) - len(m.group().lstrip())) >= start:
                line_items.append(ls + len(m.group()) - len(m.group().lstrip()))
        runs: list[list[tuple[int, str, int]]] = []
        open_runs: dict[str, list[tuple[int, str, int]]] = {}
        for m in _INLINE_ITEM.finditer(self.text, start, end):
            if m.start() in line_items:
                continue
            label = m.group("a") or m.group("b")
            kind = "digit" if label.isdigit() else ("upper" if label.isupper() else "lower")
            ordinal = int(label) if label.isdigit() else ord(label.lower()) - 96
            run = open_runs.get(kind)
            if run is not None and ordinal == run[-1][2] + 1:
                run.append((m.start(), kind, ordinal))
            else:
                run = [(m.start(), kind, ordinal)]
                runs.append(run)
                open_runs[kind] = run
        return [r for r in runs if len(r) >= 2], line_items

    def _read_as_heading(self, k: int) -> tuple[str, str] | None:
        """(text, via) when line `k` reads as a lead-in clause ending in ':'
        (via `lead-in`, the text from its sentence start) or as a heading-like
        line that does not wrap onto a lower-case line (via `heading`); None
        for any other line."""
        line = self.line(k)
        s = line.strip()
        if s.endswith(":") and not _LINE_ITEM.match(line):
            ls, _le = self.bounds(k)
            start, _t = self._sentence_start(ls + len(line.rstrip()) - 1)
            return self.text[start:ls + len(line.rstrip())].strip(), "lead-in"
        wrapped = k < len(self.starts) and _continues(line, self.line(k + 1))
        if _heading_like(line) and not wrapped:
            return s, "heading"
        return None

    @staticmethod
    def _scope(k: int, read: tuple[str, str]) -> dict[str, Any]:
        """What line `k`, read as a heading or lead-in (`read`, from
        `_read_as_heading`), says about the lines below it: a status marker
        governs them ({"line", "text", "classes", "via"}); a counter marker
        with no status marker closes the scope ({"closed_by", "text"}); {}
        otherwise, and the line is passed over.

        A line carrying a status marker never closes a scope, whatever
        counter word it also carries ("Current Planned Release" is a status
        heading). A heading-like line needs two words to do either: a
        one-word line — "Planned", "Completed", "Current" — is a flattened
        table cell as often as a heading, and a cell does not govern the
        rows below it, so a one-word status cell does not open a scope and a
        one-word counter cell does not close one (#3166). A lead-in's ':'
        says it governs, so "Planned:" or "Completed:" is enough."""
        text, via = read
        norm = rc.normalise(text)
        if via != "lead-in" and len(norm.split()) < 2:
            return {}
        found = markers(norm)
        if found:
            cls: dict[str, str] = {}
            for c, term, _o in found:
                cls.setdefault(c, term)
            return {"line": k, "text": text, "classes": cls, "via": via}
        return {"closed_by": k, "text": text} if _counter(norm) else {}

    def _counter_heading(self, k: int) -> dict[str, Any]:
        """{"closed_by": k, "text"} when line `k` reads as a heading or
        lead-in that closes a scope (`_scope`), else {}."""
        read = self._read_as_heading(k) if 1 <= k <= len(self.starts) and self.line(k).strip() else None
        scope = self._scope(k, read) if read is not None else {}
        return scope if "closed_by" in scope else {}

    def _heading(self, from_line: int) -> dict[str, Any]:
        """Scan up from `from_line` for what governs the lines below it.

        A lead-in clause ending in ':' ("Training will include:") and a
        heading-like line are read the same way (`_scope`): a status marker
        governs ({"line", "text", "classes", "via"}); a counter marker with
        no status marker closes the scope ({"closed_by": line}); anything
        else is passed over, so a count label between a status heading and
        its figures does not hide the heading. Neither a status nor a
        counter heading can be one word: a one-word line is a flattened
        table cell as often as a heading. A heading-like line that wraps
        onto a lower-case line is a list item or a phrase, not a heading. A
        prose line, a document separator, two blank lines or HEADING_WINDOW
        non-blank lines end the block. {} when nothing governs."""
        k, scanned, blanks = from_line, 0, 0
        while k >= 1 and scanned < HEADING_WINDOW:
            line = self.line(k)
            s = line.strip()
            if not s:
                blanks += 1
                if blanks >= 2:
                    return {}
                k -= 1
                continue
            blanks = 0
            if _SEPARATOR.match(s):
                return {}
            read = self._read_as_heading(k)
            if read is None and _prose_line(line):
                return {}
            scope = self._scope(k, read) if read is not None else {}
            if scope:
                return scope
            scanned += 1
            k -= 1
        return {}

    def context(self, span: tuple[int, int]) -> dict[str, Any]:
        """The status classes in one located part's context: {class: {term,
        via, source_line}} for its sentence or enumeration (governing clause
        and own item) and, for classes not found there, the heading or
        lead-in clause above it. The walk back from an item stops at the
        first unit that is not an item; that unit is read as the governing
        clause only when `_governs_enumeration` says it is one."""
        a, b = span
        s_start, term = self._sentence_start(a)
        s_end = max(self._sentence_end(b), b)
        start, ext = s_start, 0
        while ext < MAX_ITEMS and self._starts_with_item(start):
            prev = self._previous_unit(start, term)
            if prev is None:
                break
            start, term = prev
            ext += 1
        runs, line_items = self._item_markers(start, s_end)
        candidates = []
        for run in runs + ([[(p, "line", 0) for p in line_items]] if line_items else []):
            before = [m[0] for m in run if m[0] <= a]
            if before:
                candidates.append((before[-1], run))
        if candidates:
            item, run = max(candidates, key=lambda c: c[0])
            after = [m[0] for m in run if m[0] >= b]
            pieces = [(item, min(after) if after else s_end)]
            if _governs_enumeration(self.text[start:run[0][0]]):
                pieces.insert(0, (start, run[0][0]))
            via, own = "enumeration", item
        else:
            # No enumeration governs the part: its sentence, cut at the
            # first enumeration after it (items do not govern their lead-in)
            # and narrowed to the ';'-clauses the part spans — in a sentence
            # with no item markers ';' separates independent clauses or the
            # terms of a list ("Critical Care;...;Goals;..."). A lead-in the
            # sentence carries up to a ':' still governs its clauses.
            later = [r[0][0] for r in runs if r[0][0] >= b]
            lo, hi = s_start, (min(later) if later else s_end)
            seg = self.text[lo:hi]
            c_lo = lo + seg.rfind(";", 0, max(0, a - lo)) + 1
            k = seg.find(";", max(0, b - lo))
            c_hi = lo + k if k >= 0 else hi
            pieces = [(c_lo, c_hi)]
            colon = seg.rfind(":", 0, c_lo - lo)
            if c_lo > lo and colon >= 0:
                pieces.insert(0, (lo, lo + colon + 1))
            via, own = "sentence", s_start
        found: dict[str, dict[str, Any]] = {}
        for lo, hi in pieces:
            piece = self.text[lo:hi]
            mapped = normalised_offsets(piece)
            norm, offs = mapped if mapped is not None else (rc.normalise(piece), None)
            for cls, term_, off in markers(norm):
                at = lo + (offs[off] if offs is not None else 0)
                dist = a - at if at < a else max(0, at - b)
                if cls not in found or dist < found[cls]["_dist"]:
                    found[cls] = {"term": term_, "via": via, "source_line": self.line_of(at), "_dist": dist}
        for d in found.values():
            d.pop("_dist")
        # The line the part's own sentence or item starts on is read first: a
        # part that begins on a counter-heading ("Current Released Dataset")
        # is under that heading, so the status heading above it does not
        # govern. A counter-heading the part quotes only after its first line
        # closes nothing for the text before it, which the status heading
        # does govern (#3089).
        own_line = self.line_of(own)
        heading = self._counter_heading(own_line) or self._heading(own_line - 1)
        for cls, term_ in (heading.get("classes") or {}).items():
            found.setdefault(cls, {"term": term_, "via": heading["via"], "source_line": heading["line"],
                                   "governor": heading["text"]})
        return found

    def lost_classes(self, cid: str, snippet: str, occurrences: list[list[tuple[int, int]]] | None = None
                     ) -> tuple[dict[str, dict[str, Any]] | None, int]:
        """({class: detail} carried by the context of every occurrence and not
        by the snippet, occurrences), or (None, 0) when the snippet cannot be
        located. An occurrence's context is the union of its parts' contexts:
        each quoted part is read in its own sentence, so the text a `...`
        elides counts where it shares a part's sentence and not where it
        runs across a flattened table."""
        occurrences = self.locate(cid, snippet) if occurrences is None else occurrences
        if not occurrences:
            return None, 0
        own = classes(snippet)
        per = []
        for parts in occurrences:
            merged: dict[str, dict[str, Any]] = {}
            for part in parts:
                for c, d in self.context(part).items():
                    if c not in own:
                        merged.setdefault(c, d)
            per.append(merged)
        common = set(per[0]).intersection(*per[1:])
        return {c: per[0][c] for c in sorted(common)}, len(occurrences)


# ------------------------------------------------------------------ rule 1
def receipt_context(receipt: dict[str, Any], manifest: dict[str, Any], bundle_text: str,
                    record: dict[str, Any], *, final: dict[str, Any] | None = None) -> dict[str, Any]:
    """Rule 1 over a receipt, its chunk manifest, the bundle and the record
    the receipt addresses (the API path's phase-1 snapshot, else the full
    record). With `final` as well, each flag says whether the final value,
    followed by entry identity (`receipts.remap_path`), expresses the
    status. Pure and read-only: nothing passed in is modified.

    The receipt is model output, so a malformed entry is counted, never
    raised (#724): exactly the entries `receipts.check` reports as
    `malformed_entry` — one that is not a mapping with a string id, or an
    `extracted` entry whose `extracted` is not a list of mappings — are
    counted under `malformed_entries` and none of their pairs is read, as
    the validator reads none of them."""
    view = BundleView(bundle_text, manifest)
    counts = {"snippets": 0, "verified": 0, "not_verified": 0, "value_unresolved": 0,
              "located": 0, "unlocated": 0, "malformed_entries": 0}
    flags: dict[str, list[dict[str, Any]]] = {"value": [], "label": []}
    unlocated: list[dict[str, Any]] = []
    for entry in receipt.get("chunks") or []:
        pairs = entry.get("extracted") if isinstance(entry, dict) else None
        if (not isinstance(entry, dict) or not isinstance(entry.get("id"), str)
                or (entry.get("status") == "extracted" and pairs is not None
                    and not (isinstance(pairs, list) and all(isinstance(p, dict) for p in pairs)))):
            counts["malformed_entries"] += 1
            continue
        if entry.get("status") != "extracted":
            continue
        cid = entry["id"]
        for pair in pairs or []:
            counts["snippets"] += 1
            slot, snippet = str(pair.get("slot") or ""), pair.get("snippet")
            if (not isinstance(snippet, str) or not snippet.strip() or cid not in view.chunks
                    or not view.verified(cid, snippet)):
                counts["not_verified"] += 1
                continue
            counts["verified"] += 1
            ok, value = rc._resolve_value(record, slot)
            if not ok:
                counts["value_unresolved"] += 1
                continue
            value_classes = classes(_value_text(value))
            found = view.locate(cid, snippet)
            lost, occurrences = view.lost_classes(cid, snippet, found)
            if lost is None:
                counts["unlocated"] += 1
                unlocated.append({"chunk": cid, "slot": slot, "snippet": snippet[:60]})
            else:
                counts["located"] += 1
            bucket = flags[slot_class(slot)]
            base = {"slot": slot, "chunk": cid, "snippet": snippet[:80],
                    "snippet_line": view.line_of(found[0][0][0]) if found else None}
            for cls, term in classes(snippet).items():
                if not expresses(value_classes, cls):
                    bucket.append({"rule": "modal_dropped", **base, "class": cls, "marker": term,
                                   "source_line": base["snippet_line"],
                                   **_final(final, record, slot, cls)})
            for cls, d in (lost or {}).items():
                if not expresses(value_classes, cls):
                    bucket.append({"rule": "governor_outside_snippet", **base, "class": cls,
                                   "marker": d["term"], "via": d["via"], "source_line": d["source_line"],
                                   **({"governor": d["governor"]} if "governor" in d else {}),
                                   **({"occurrences": occurrences} if occurrences > 1 else {}),
                                   **_final(final, record, slot, cls)})
    by_rule = {r: {k: sum(1 for f in flags[k] if f["rule"] == r) for k in ("value", "label")}
               for r in ("governor_outside_snippet", "modal_dropped")}
    slots = {k: len({f["slot"] for f in flags[k]}) for k in ("value", "label")}
    summary = (f"snippets {counts['verified']}/{counts['snippets']} verified · {counts['located']} located"
               + (f" ({counts['unlocated']} unlocated)" if counts["unlocated"] else "")
               + (f" · {counts['malformed_entries']} malformed receipt entr"
                  f"{'y' if counts['malformed_entries'] == 1 else 'ies'} not read" if counts["malformed_entries"] else "")
               + f" · governor_outside_snippet {by_rule['governor_outside_snippet']['value']}"
               + f" (+{by_rule['governor_outside_snippet']['label']} label)"
               + f" · modal_dropped {by_rule['modal_dropped']['value']} (+{by_rule['modal_dropped']['label']} label)"
               + f" · {slots['value']} slot(s) flagged (+{slots['label']} label)")
    return {"instrument": INSTRUMENT, "vocabulary": VOCABULARY, "rule": RULE_RECEIPT, "checked": True,
            "gating": False, "counts": {**counts, "flags": by_rule, "slots_flagged": slots},
            "flags": flags["value"], "label_slot": flags["label"], "unlocated": unlocated[:20],
            "summary": summary, "assurance": ASSURANCE}


def _final(final: dict[str, Any] | None, record: dict[str, Any], slot: str, cls: str) -> dict[str, Any]:
    if final is None or final is record:
        return {}
    rm = rc.remap_path(slot, record, final)
    if not rm.get("path"):
        return {"final_path": None, "final_expresses_status": None}
    ok, value = rc._resolve_value(final, rm["path"])
    return {"final_path": rm["path"],
            "final_expresses_status": expresses(classes(_value_text(value)), cls) if ok else None}


# ------------------------------------------------------------------ rule 2
def review_status_expression(audit: dict[str, Any], *, record_raw: str | None = None,
                             view: BundleView | None = None) -> dict[str, Any]:
    """Rule 2 over an audit's `source_review` (or a bare source_review).

    `record_raw` is the artifact the review is bound to (its sha256 must be
    the review's): a claim whose own text carries no marker is then counted
    as expressed when the whole value at its path carries one. `view` (the
    bundle and its manifest) lets an evidence quote's context count, as in
    rule 1. Pure and read-only.

    The review is model output: a malformed row, claim or evidence entry is
    passed over or counted, never raised. An evidence entry whose `chunk`
    names no chunk of the bundle (a list, a number, an unknown id) has its
    context left unread and is counted under `quotes_chunk_not_in_bundle`."""
    review = audit.get("source_review") if isinstance(audit, dict) and "source_review" in audit else audit
    if not isinstance(review, dict) or not isinstance(review.get("values"), list):
        raise ValueError("no source_review with a values list")
    value_texts: dict[str, str] | None = None
    if record_raw is not None:
        from data_sheets_schema.source_review import inventory
        if not isinstance(review.get("artifact"), str):
            raise ValueError("the source_review names no artifact, so no record can be bound to it")
        inv = inventory(record_raw, review.get("artifact"))
        if inv["sha256"] != review.get("sha256"):
            raise ValueError("the record is not the artifact this source_review is bound to (sha256 differs)")
        value_texts = {row["path"]: row["text"] for row in inv["values"]}
    counts = {"claims": 0, "supported": 0, "declared": {}, "expressed": 0,
              "expressed_elsewhere_in_value": 0, "fact_claims": 0, "unlocated_quotes": 0,
              "quotes_chunk_not_in_bundle": 0}
    flags: dict[str, list[dict[str, Any]]] = {"value": [], "label": []}
    for row in review["values"]:
        if not isinstance(row, dict) or not isinstance(row.get("claims"), list):
            continue
        path = str(row.get("path") or "")
        bucket = flags[slot_class(path)]
        for index, claim in enumerate(row["claims"]):
            if not isinstance(claim, dict):
                continue
            counts["claims"] += 1
            if claim.get("verdict") != "supported":
                continue
            counts["supported"] += 1
            status = claim.get("claim_status") if isinstance(claim.get("claim_status"), str) else None
            counts["declared"][str(status)] = counts["declared"].get(str(status), 0) + 1
            text = claim.get("text") if isinstance(claim.get("text"), str) else ""
            if status in DECLARED_STATUS:
                cls = DECLARED_STATUS[status]
                own = classes(text)
                if expresses(own, cls):
                    counts["expressed"] += 1
                elif value_texts is not None and expresses(classes(value_texts.get(path, "")), cls):
                    counts["expressed_elsewhere_in_value"] += 1
                else:
                    bucket.append({"rule": "status_unexpressed", "path": path, "claim": index,
                                   "declared": status, "text": text[:80],
                                   "other_markers": sorted(own)})
            elif status == "fact":
                counts["fact_claims"] += 1
                hit = _planned_evidence(claim.get("evidence"), view, counts)
                if hit:
                    bucket.append({"rule": "planned_evidence_declared_fact", "path": path, "claim": index,
                                   "text": text[:80], **hit})
    by_rule = {r: {k: sum(1 for f in flags[k] if f["rule"] == r) for k in ("value", "label")}
               for r in ("status_unexpressed", "planned_evidence_declared_fact")}
    summary = (f"claims {counts['supported']}/{counts['claims']} supported · "
               + ", ".join(f"{n} {s}" for s, n in sorted(counts["declared"].items()))
               + f" · status_unexpressed {by_rule['status_unexpressed']['value']}"
               + f" (+{by_rule['status_unexpressed']['label']} label)"
               + f" · planned_evidence_declared_fact {by_rule['planned_evidence_declared_fact']['value']}"
               + f" (+{by_rule['planned_evidence_declared_fact']['label']} label)"
               + ("" if value_texts is not None else " · value text not read (no record supplied)")
               + ("" if view is not None else " · evidence context not read (no bundle supplied)")
               + (f" · {counts['quotes_chunk_not_in_bundle']} evidence quote(s) name no chunk of the bundle"
                  if counts["quotes_chunk_not_in_bundle"] else ""))
    return {"instrument": INSTRUMENT, "vocabulary": VOCABULARY, "rule": RULE_REVIEW, "checked": True,
            "gating": False, "artifact": review.get("artifact"), "sha256": review.get("sha256"),
            "value_text_read": value_texts is not None, "evidence_context_read": view is not None,
            "counts": {**counts, "flags": by_rule}, "flags": flags["value"], "label_slot": flags["label"],
            "summary": summary, "assurance": ASSURANCE}


def _planned_evidence(evidence: Any, view: BundleView | None, counts: dict[str, Any]) -> dict[str, Any] | None:
    """The first evidence quote that carries, or whose context carries, a
    planned or prospective marker."""
    for i, e in enumerate(evidence if isinstance(evidence, list) else []):
        if not isinstance(e, dict) or not isinstance(e.get("quote"), str):
            continue
        own = classes(e["quote"])
        cls = next((c for c in PLANNED_EVIDENCE_CLASSES if c in own), None)
        if cls:
            return {"evidence": i, "chunk": e.get("chunk"), "class": cls, "marker": own[cls], "via": "quote"}
        if view is None:
            continue
        if not isinstance(e.get("chunk"), str) or e["chunk"] not in view.chunks:
            counts["quotes_chunk_not_in_bundle"] += 1
            continue
        lost, _n = view.lost_classes(e["chunk"], e["quote"])
        if lost is None:
            counts["unlocated_quotes"] += 1
            continue
        cls = next((c for c in PLANNED_EVIDENCE_CLASSES if c in lost), None)
        if cls:
            d = lost[cls]
            return {"evidence": i, "chunk": e.get("chunk"), "class": cls, "marker": d["term"],
                    "via": d["via"], "source_line": d["source_line"],
                    **({"governor": d["governor"]} if "governor" in d else {})}
    return None


# ----------------------------------------------------------------- on disk
_MD5 = re.compile(r"^[0-9a-f]{32}$")


def _unchecked(rule: str, reason: str) -> dict[str, Any]:
    return {"instrument": INSTRUMENT, "vocabulary": VOCABULARY, "rule": rule, "checked": False,
            "gating": False, "reason": reason, "assurance": ASSURANCE}


def _load_yaml(path: Path) -> Any:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _disk_manifest(raw: bytes, path: Path) -> dict[str, Any]:
    """A chunk manifest that must reproduce these bytes' canonical chunks
    under its recorded rule (`chunking.validate_manifest_mapping`)."""
    from data_sheets_schema.chunking import validate_manifest_mapping
    m = _load_yaml(path)
    if not isinstance(m, dict):
        raise ValueError(f"{path} is not a chunk manifest")
    validate_manifest_mapping(m, raw, str(m.get("bundle")))
    return m


def _receipt_md5_problem(receipt: dict[str, Any], raw: bytes) -> str | None:
    named = receipt.get("bundle_md5")
    got = hashlib.md5(raw).hexdigest()
    if isinstance(named, str) and _MD5.match(named) and named != got:
        return f"the receipt names bundle md5 {named}, these bytes are {got}"
    return None


def file_status_context(receipt: Path, bundle: Path, record: Path, *, chunk_manifest: Path | None = None,
                        final: Path | None = None) -> dict[str, Any]:
    """Rule 1 over named files: a receipt, its bundle, the record it
    addresses, and the bundle's chunk manifest (the one beside the bundle,
    or the study's, when not named). The receipt must name these bytes."""
    from data_sheets_schema.chunking import manifest_for
    raw = bundle.read_bytes()
    mpath = chunk_manifest if chunk_manifest is not None else manifest_for(bundle)
    if not mpath.exists():
        return _unchecked(RULE_RECEIPT, f"no chunk manifest at {mpath}; pass --chunk-manifest")
    try:
        manifest = _disk_manifest(raw, mpath)
    except ValueError as exc:
        return _unchecked(RULE_RECEIPT, f"{mpath}: {exc}")
    rec = rc.load_receipt(receipt)
    named = rec.get("bundle_md5")
    if not (isinstance(named, str) and _MD5.match(named)):
        return _unchecked(RULE_RECEIPT, "the receipt names no bundle md5, so nothing says these are the bytes "
                                        "it was written against; use --label/--project, where the run's record does")
    problem = _receipt_md5_problem(rec, raw)
    if problem:
        return _unchecked(RULE_RECEIPT, problem)
    addressed = _load_yaml(record)
    fin = _load_yaml(final) if final is not None else None
    out = receipt_context(rec, manifest, raw.decode("utf-8"), addressed or {}, final=fin)
    out["value_basis"] = f"record {record}"
    out["bundle_basis"] = {"source": "bundle on disk", "path": str(bundle), "manifest": str(mpath)}
    return out


def run_status_context(provenance: Path, receipt: Path, full: Path) -> dict[str, Any]:
    """Rule 1 for a run, from its provenance record: the bundle the record
    hashed (on disk, else the committed version with its hashes, #1140),
    chunked under the record's own `inputs.chunks.rule`; the phase-1
    snapshot as the addressed record where the run wrote one (the API path),
    with the final record for `final_expresses_status`; else the full
    record."""
    from data_sheets_schema import backfill_checks as bc
    from data_sheets_schema.chunking import canonical_name, manifest_for, manifest_from_bytes
    if not receipt.exists():
        return _unchecked(RULE_RECEIPT, f"no coverage receipt at {receipt}")
    if not provenance.exists():
        return _unchecked(RULE_RECEIPT, f"no provenance record at {provenance}; name the files with "
                                        "--receipt/--bundle/--record")
    import yaml
    record = yaml.safe_load(bc._split_header(provenance.read_text(encoding="utf-8"))[1]) or {}
    if not isinstance(record, dict) or not isinstance(record.get("inputs") or {}, dict):
        return _unchecked(RULE_RECEIPT, f"{provenance} is not a provenance record with an inputs mapping")
    inputs = record.get("inputs") or {}
    bundle = bc.declared_bundle(record, provenance)
    raw, basis, why = _record_bytes(bundle, inputs)
    if raw is None:
        return _unchecked(RULE_RECEIPT, why)
    chunks_in = inputs.get("chunks") if isinstance(inputs.get("chunks"), dict) else {}
    try:
        if chunks_in.get("rule"):
            name = chunks_in.get("bundle_name") or (canonical_name(bundle) if bundle is not None
                                                    else Path(str(inputs.get("bundle_path"))).name)
            manifest = manifest_from_bytes(raw, name, chunks_in["rule"])
            basis["manifest"] = "chunked in memory under the record's own inputs.chunks.rule"
            if chunks_in.get("chunk_count") is not None and manifest["chunk_count"] != chunks_in["chunk_count"]:
                return _unchecked(RULE_RECEIPT, f"the record's rule chunks these bytes to {manifest['chunk_count']}, "
                                                f"not the {chunks_in['chunk_count']} it cites")
        elif bundle is not None and manifest_for(bundle).exists():
            manifest = _disk_manifest(raw, manifest_for(bundle))
            basis["manifest"] = str(manifest_for(bundle))
        else:
            return _unchecked(RULE_RECEIPT, "the record names no chunking rule and no manifest on disk chunks its bundle")
    except (KeyError, TypeError, ValueError) as exc:
        return _unchecked(RULE_RECEIPT, f"the chunks the receipt names cannot be rebuilt: {exc}")
    rec = rc.load_receipt(receipt)
    problem = _receipt_md5_problem(rec, raw)
    if problem:
        return _unchecked(RULE_RECEIPT, problem)
    state, spath, snapshot, snap_why = rc.phase1_snapshot_state(receipt, record=record)
    if state == "unusable":
        return _unchecked(RULE_RECEIPT, f"the phase-1 snapshot {spath} is present but not usable ({snap_why})")
    final = _load_yaml(full) if full.exists() else None
    if snapshot is not None:
        addressed, fin, value_basis = snapshot, final, f"phase-1 snapshot {spath}"
    elif isinstance(final, dict):
        addressed, fin, value_basis = final, None, f"record {full}"
    else:
        return _unchecked(RULE_RECEIPT, f"no record at {full} and no phase-1 snapshot")
    out = receipt_context(rec, manifest, raw.decode("utf-8"), addressed, final=fin)
    out["value_basis"] = value_basis
    out["bundle_basis"] = basis
    return out


def _record_bytes(bundle: Path | None, inputs: dict[str, Any]) -> tuple[bytes | None, dict[str, Any], str | None]:
    """The bytes the record hashed: the bundle on disk when it hashes to the
    record's md5/sha256, else the committed version that does."""
    md5, sha = inputs.get("bundle_md5"), inputs.get("bundle_sha256")
    if bundle is not None and bundle.exists():
        raw = bundle.read_bytes()
        if ((not md5 or hashlib.md5(raw).hexdigest() == md5)
                and (not sha or hashlib.sha256(raw).hexdigest() == sha)):
            return raw, {"source": "bundle on disk", "path": str(bundle)}, None
    if not (md5 or sha):
        return None, {}, "the record declares no bundle hash, and its bundle is not on disk"
    rel = inputs.get("bundle_path")
    if not rel:
        return None, {}, "the bundle on disk is not the bytes the record hashed, and the record declares no path"
    from data_sheets_schema.provenance import GitUnavailable, bundle_bytes_for
    try:
        recovered = bundle_bytes_for(rel, md5=md5, sha256=sha)
    except GitUnavailable as exc:
        return None, {}, f"the bundle drifted and git could not supply the version the record hashed: {exc}"
    if recovered is None:
        return None, {}, "the bundle drifted and no committed version hashes to the record's"
    raw, entry = recovered
    return raw, {"source": "git blob", "path": rel, "commit": entry["commit"]}, None


def file_status_expression(audit: Path, *, record: Path | None = None, bundle: Path | None = None,
                           chunk_manifest: Path | None = None) -> dict[str, Any]:
    """Rule 2 over named files: an audit JSON carrying `source_review` (or a
    bare source_review), and optionally the artifact it is bound to and the
    bundle with its chunk manifest."""
    from data_sheets_schema.evidence_assertions import load_json
    parsed = load_json(audit.read_bytes())
    view = None
    if bundle is not None:
        from data_sheets_schema.chunking import manifest_for
        raw = bundle.read_bytes()
        mpath = chunk_manifest if chunk_manifest is not None else manifest_for(bundle)
        view = BundleView(raw.decode("utf-8"), _disk_manifest(raw, mpath))
    record_raw = record.read_bytes().decode("utf-8") if record is not None else None
    return review_status_expression(parsed, record_raw=record_raw, view=view)


def report_lines(out: dict[str, Any]) -> list[str]:
    """The human-readable form the CLI prints beside the existing summaries."""
    lines = [f"   {out['instrument']} · {out['rule']} · non-gating"]
    if not out.get("checked"):
        return lines + [f"   · unchecked: {out['reason']}"]
    lines.append(f"   {out['summary']}")
    for bucket, title in (("flags", None), ("label_slot", "label slots")):
        items = out.get(bucket) or []
        if title and items:
            lines.append(f"   {title}:")
        for f in items:
            where = f.get("slot") or f.get("path")
            detail = ", ".join(f"{k}={v}" for k, v in f.items() if k not in {"rule", "slot", "path"})
            lines.append(f"   flag {f['rule']} {where}: {detail}")
    for u in out.get("unlocated") or []:
        lines.append(f"   · unlocated: chunk={u['chunk']} slot={u['slot']}")
    lines.append(f"   · assurance: {out['assurance']}")
    return lines
