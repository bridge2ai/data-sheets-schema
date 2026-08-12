"""British spellings in generated prose — but not in quoted source text (#502).

From Camille Nebeker's review: *"Standardize on American English in the D4D
generated docs ie no 'programme'."* Measured on the 2026-08-11 arm, the records
carry `programme` ×10, `organis*` ×10, `characteris*` ×15 and more.

**A find-and-replace would be wrong.** The bundles themselves contain British
spellings — `licence` 13 times, `programme` 6 — so rewriting every occurrence
would silently alter what a source said, which is the one thing the provenance
guard exists to prevent. One line in the corpus shows both at once:

    programme funding as "the Bridge2AI Program (NIH Common Fund; …"

The record's own prose says *programme* while the text it quotes says *Program*.

So this reports only occurrences it can show are **not** quoted: an occurrence
is treated as quoted when a window of surrounding text appears verbatim in the
run's declared bundle. That is deliberately conservative in the direction of
silence — a false "quoted" merely fails to report, while a false "generated"
would invite someone to edit evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

#: British → American, restricted to forms with no American homograph. `practice`
#: and `licence` are deliberately handled below rather than here: `practice` is a
#: valid American noun, and `license` is the American spelling of both noun and
#: verb, so a blanket rule on either produces false positives on correct text.
BRITISH: dict[str, str] = {
    "programme": "program",
    "programmes": "programs",
    "organisation": "organization",
    "organisations": "organizations",
    "organisational": "organizational",
    "organise": "organize",
    "organised": "organized",
    "organising": "organizing",
    "analyse": "analyze",
    "analysed": "analyzed",
    "analysing": "analyzing",
    "behaviour": "behavior",
    "behavioural": "behavioral",
    "catalogue": "catalog",
    "catalogued": "cataloged",
    "centre": "center",
    "centres": "centers",
    "prioritise": "prioritize",
    "prioritised": "prioritized",
    "characterise": "characterize",
    "characterised": "characterized",
    "characterising": "characterizing",
    "summarise": "summarize",
    "summarised": "summarized",
    "utilise": "utilize",
    "utilised": "utilized",
    "recognise": "recognize",
    "recognised": "recognized",
    "standardise": "standardize",
    "standardised": "standardized",
    "harmonise": "harmonize",
    "harmonised": "harmonized",
    "normalise": "normalize",
    "normalised": "normalized",
    "anonymise": "anonymize",
    "anonymised": "anonymized",
    "pseudonymise": "pseudonymize",
    "pseudonymised": "pseudonymized",
    "labelled": "labeled",
    "labelling": "labeling",
    "modelling": "modeling",
    "fulfil": "fulfill",
    "enrolment": "enrollment",
    "licence": "license",
    "defence": "defense",
    "grey": "gray",
}

#: Characters either side of an occurrence used to decide whether it is quoted.
#: Wide enough that a coincidental match is implausible, narrow enough to survive
#: a record reflowing prose it took from a source.
CONTEXT = 40

_WORD = re.compile("|".join(rf"\b{w}\b" for w in sorted(BRITISH, key=len,
                                                        reverse=True)),
                   re.IGNORECASE)


@dataclass
class Occurrence:
    slot: str
    word: str
    suggestion: str
    context: str
    quoted: bool


def _walk(node: Any, slot: str | None) -> Iterator[tuple[str, str]]:
    """Yield (top-level slot, string). The *outermost* key is reported, so a
    finding is attributed to the slot a reader would go looking in."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, slot or key)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value, slot)
    elif isinstance(node, str):
        yield (slot or "?", node)


def _walk_leaf(node: Any, key: str | None) -> Iterator[tuple[str, str]]:
    """Yield (immediate key, string).

    Separate from `_walk`, which deliberately keeps the outermost slot so a
    finding is reported where a reader would look for it. That is wrong for
    identifiers: a nested `id` would be attributed to `purposes` and never
    recognised as an id at all, which is how the first version of
    `in_identifiers` silently found nothing.
    """
    if isinstance(node, dict):
        for k, value in node.items():
            yield from _walk_leaf(value, k)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_leaf(value, key)
    elif isinstance(node, str):
        yield (key or "?", node)


def _squash(text: str) -> str:
    """Collapse whitespace so a reflowed quote still matches its source.

    A record wraps prose at a different width than the document it took it
    from, so a literal comparison would call almost everything generated.
    """
    return re.sub(r"\s+", " ", text).strip().lower()


def occurrences(record: dict, bundle_text: str | None) -> list[Occurrence]:
    """Every British spelling in a record, each marked quoted or not.

    `bundle_text` is the run's *declared* bundle. Passing None marks nothing as
    quoted, which is honest for a record whose bundle cannot be identified —
    the caller then knows the quoted/generated split was not established rather
    than being told everything is generated.
    """
    haystack = _squash(bundle_text) if bundle_text else None
    found: list[Occurrence] = []
    for slot, text in _walk(record, None):
        for match in _WORD.finditer(text):
            start = max(0, match.start() - CONTEXT)
            end = min(len(text), match.end() + CONTEXT)
            window = text[start:end]
            quoted = bool(haystack and _squash(window) in haystack)
            found.append(Occurrence(
                slot=slot, word=match.group(0),
                suggestion=BRITISH[match.group(0).lower()],
                context=" ".join(window.split()), quoted=quoted))
    return found


def in_identifiers(record: dict) -> list[Occurrence]:
    """British spellings inside `id` values.

    Structural rather than stylistic: an id is a token other records and
    mappings may key on, so it cannot be fixed by a later copy-edit. The
    2026-08-11 arm carries `aireadi:external-training-programme`.
    """
    out: list[Occurrence] = []
    for slot, text in _walk_leaf(record, None):
        if slot != "id":
            continue
        for match in _WORD.finditer(text):
            out.append(Occurrence(slot=slot, word=match.group(0),
                                  suggestion=BRITISH[match.group(0).lower()],
                                  context=text, quoted=False))
    return out
