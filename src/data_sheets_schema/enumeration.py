"""Enumeration depth, and how much of it can be checked at all (#332).

The agent runtime and the direct API differ on a thing rubric20 cannot see. On
the same prompt, same four-phase mode, differing only in runtime, the agent
enumerates about twice as many items into the list-valued slots:

    variables (AI_READI)    agent 45/record    API 22/record
    creators  (AI_READI)    agent 42/record    API omitted entirely

No rubric20 question rewards this — Q3 counts keywords, Q4 counts file types,
and nothing counts variables, creators or resources. A datasheet listing 30
variables instead of 200 reads as much worse to a reader and scores the same.

The obvious fix is the wrong one. **The judge never receives the source
documents** — `rubric20_system_prompt.md` says "Read the provided D4D YAML file"
and the record is all it gets — so an enumeration question could only score a
*count*, and a count rewards invention. Depth is meaningful only beside
grounding, and grounding needs the sources. Hence a measurement here rather than
a rubric question.

## Why this module reports coverage before it reports grounding

Grounding is established by finding a record's claim verbatim in the source
bundle. That works only for text specific enough that its presence is evidence
and its absence is evidence too — a DOI, an ORCID, a grant number, a version
string. Most enumerated content is not like that:

    creators           {"description": "Aaron Y. Lee, MD (ORCID 0000-...)"}
    known_limitations  {"description": "Cross-sectional design with a single..."}

Two thirds of all enumerated items across the 25 current records carry no
identifying label at all; the identity sits inside prose. Measured on AI_READI,
74 of 77 `variables` items and 9 of 9 `known_limitations` items carry nothing
checkable.

So a naive grounding rate would report ~100% while examining 4% of the content,
and that number would be worse than no number. `coverage` is reported first and
`grounding` raises rather than returning a figure when nothing was checkable.

**This measures verifiability, not truth.** An anchor found in the source shows
the record did not invent that token. It does not show the surrounding claim is
correct, and its absence may mean paraphrase rather than invention. Both arms are
measured identically, so the *comparison* is sound even where the absolute rate
is a lower bound.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

#: Substrings specific enough that finding them in the source is evidence.
#:
#: Deliberately narrow. A common English word appearing in both a record and a
#: 200 KB bundle says nothing, so matching one would inflate every rate towards
#: 100% and make the arms indistinguishable — the opposite of the point.
ANCHOR = re.compile(r"""
    (?P<doi>10\.\d{4,9}/[^\s"'),;]+)
  | (?P<orcid>\d{4}-\d{4}-\d{4}-\d{3}[\dX])
  | (?P<rrid>RRID:\s*[A-Za-z]+_\w+)
  | (?P<url>https?://[^\s"'),;]+)
  | (?P<code>\b(?=\w*\d)(?=\w*[A-Za-z])[A-Za-z0-9._-]{5,}\b)
""", re.X)

#: The `{5,}` above is the only length floor, deliberately. A separate
#: `MIN_ANCHOR_CHARS` check was unreachable: `\b` keeps trailing punctuation out
#: of a `code` match, so the strip below never shortens one, and the identifier
#: patterns are all longer than five characters anyway. Whoever relaxes the
#: quantifier should choose the new floor in the same place.


class NothingCheckable(ValueError):
    """A grounding rate was asked for where no anchor existed to check.

    `0.0` would read as "invented" and `1.0` as "fully grounded"; both are
    claims the evidence does not support. The measurement is absent, not zero —
    the same distinction `reported_percentage` draws for a missing percentage.
    """

    def __init__(self, slot: str, items: int):
        super().__init__(
            f"`{slot}` has {items} item(s) and no checkable anchor, so its "
            "grounding is unmeasured rather than zero. Read `coverage` first.")


@dataclass(frozen=True)
class SlotEnumeration:
    """One list-valued slot's depth, and how much of it could be checked."""

    slot: str
    items: int
    checkable_items: int
    anchors: int
    anchors_found: int

    @property
    def coverage(self) -> float:
        """Fraction of items carrying at least one checkable anchor.

        Read this before `grounding`. On the current corpus it runs from 0.0
        (`known_limitations`) to 1.0 (`external_resources`), so a grounding rate
        quoted without it can be a statement about 4% of the content.
        """
        return self.checkable_items / self.items if self.items else 0.0

    @property
    def grounding(self) -> float:
        """Fraction of anchors found verbatim in the source bundle."""
        if not self.anchors:
            raise NothingCheckable(self.slot, self.items)
        return self.anchors_found / self.anchors


def anchors_in(text: str) -> set[str]:
    """Every checkable substring in a piece of text."""
    found = set()
    for match in ANCHOR.finditer(text or ""):
        # Strips punctuation the DOI and URL patterns can swallow at the end
        # of a sentence: `10.13026/xyz.` is the same anchor as `10.13026/xyz`.
        value = match.group(0).rstrip(".,;)")
        if value:
            found.add(value)
    return found


def _text_of(item: Any) -> str:
    """Every scalar in an item, at any depth.

    Nested rather than top-level only: `creators` puts the ORCID inside
    `description`, and `file_collections` puts identifiers a level further down.
    """
    if isinstance(item, dict):
        return " ".join(_text_of(v) for v in item.values())
    if isinstance(item, list):
        return " ".join(_text_of(v) for v in item)
    return str(item) if isinstance(item, (str, int, float)) else ""


def measure_slot(slot: str, value: Any, source: str) -> SlotEnumeration:
    """Depth and checkability of one slot against a lowercased source bundle."""
    items = value if isinstance(value, list) else ([] if value is None else [value])
    checkable = anchors = found = 0
    for item in items:
        item_anchors = anchors_in(_text_of(item))
        if item_anchors:
            checkable += 1
        anchors += len(item_anchors)
        found += sum(1 for a in item_anchors if a.lower() in source)
    return SlotEnumeration(slot=slot, items=len(items), checkable_items=checkable,
                           anchors=anchors, anchors_found=found)


def measure(record: dict[str, Any], source: str,
            slots: Iterable[str] | None = None) -> dict[str, SlotEnumeration]:
    """Every list-valued slot in a record, or a named subset.

    `source` is lowercased once by the caller in a batch; doing it per record
    over a 200 KB bundle dominated the runtime.
    """
    lowered = source.lower()
    names = list(slots) if slots is not None else [
        k for k, v in record.items() if isinstance(v, list) and v]
    return {name: measure_slot(name, record.get(name), lowered) for name in names}


def total_depth(measured: dict[str, SlotEnumeration]) -> int:
    """Items enumerated across all measured slots — the headline of #332."""
    return sum(m.items for m in measured.values())
