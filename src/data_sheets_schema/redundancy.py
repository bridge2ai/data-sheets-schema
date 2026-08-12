"""How often one fact is stated in more than one slot (#501).

From Camille Nebeker's review: *"some fields have redundant content (eg multiple
mentions of SAFE Harbor) … we also want to prioritize new informative content vs
redundant content."*

**The decision was to accept the repetition.** The core record is read one slot
at a time — by a consumer deciding whether to ingest, by a mapping into RO-Crate
or DCAT, by a reviewer checking one question. A reader who opens
`is_deidentified` alone must learn that the release is Safe Harbor
de-identified; a cross-reference to another slot leaves them with a pointer
instead of an answer. Per-slot completeness wins, and the document reads
repetitively end to end as the price.

So this module measures and never enforces. The number exists to be watched: at
the time of the decision 7.4% of sentences in the canonical set participated in
a cross-slot restatement, and a later arm at 30% would mean something changed
that nobody chose.

## Why the measure works on meaning rather than strings

The restatements are **paraphrases**, not copies. The same Safe Harbor fact
appears as "removed from", "stripped from" and "excludes" in three slots of one
record. An exact-match pass over those records reports 8 restatements and misses
Safe Harbor entirely — which is how the first measurement of this understated
it. Comparison is therefore Jaccard overlap on content words.

## Two things deliberately not counted as redundancy

- **Structural repetition.** A URL in both `resources` and
  `distribution_formats`, or a nested `CoreDataset` under `resources` repeating
  its parent's title. Counted and reported separately: collapsing it would be
  wrong, and folding it into the headline would overstate the problem by a
  third.
- **Preserved disagreements.** `is_deidentified` and `participant_privacy` both
  record that FAIRhub says `deIdentType: "NoDeIdentification"` while the Nature
  Metabolism comment says Safe Harbor. That contradiction is the most valuable
  content in either slot. It is still counted — suppressing it from the count
  would hide a real restatement — but any future rule acting on these numbers
  must exempt it, or it will delete the best sentence to save the third-best.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

#: Function words excluded before overlap is computed. Short and deliberately
#: not a full stopword list: the aim is to stop "the/of/and" dominating the
#: intersection, not to do linguistics.
STOPWORDS = frozenset("""
a an and any all are as at be been by can for from in is it its may no not of
on or such that the their there this to was were which with
""".split())

#: Slots whose repetition is structural rather than redundant — a sub-resource
#: legitimately restates its parent, and a download URL legitimately appears
#: beside the format it belongs to.
NESTING_SLOTS = frozenset({"resources", "file_collections"})

#: Below this, two sentences are different statements that happen to share
#: vocabulary. Chosen by inspection against the Safe Harbor family, which sits
#: at 0.6-0.8 while unrelated sentences in the same record sit below 0.35.
THRESHOLD = 0.6

#: Shorter than this and a "sentence" is a fragment, label or bare identifier,
#: where vocabulary overlap says nothing about restatement.
MIN_CHARS = 60

#: Fewer content words than this and Jaccard is unstable — two 5-word sentences
#: sharing 3 words score 0.43 without restating anything.
MIN_CONTENT_WORDS = 8


@dataclass(frozen=True)
class Restatement:
    """One fact found in two slots."""

    slot_a: str
    slot_b: str
    text_a: str
    text_b: str
    similarity: float
    structural: bool


def _walk(node: Any, slot: str | None = None) -> Iterator[tuple[str, str]]:
    """Yield (outermost slot, string). The outermost key is kept so a finding
    is attributed to the slot a reader would go looking in."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, slot or key)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value, slot)
    elif isinstance(node, str):
        yield (slot or "?", node)


def sentences(text: str) -> list[str]:
    collapsed = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", collapsed)
            if len(s.strip()) >= MIN_CHARS]


def _content_words(sentence: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", sentence.lower())
            if w not in STOPWORDS and len(w) > 2}


def _is_bare_url(sentence: str) -> bool:
    return sentence.strip().lower().startswith(("http://", "https://", "doi:"))


def restatements(record: dict, threshold: float = THRESHOLD
                 ) -> list[Restatement]:
    """Every pair of sentences in different slots that state the same thing."""
    items = []
    for slot, text in _walk(record):
        for sentence in sentences(text):
            words = _content_words(sentence)
            if len(words) >= MIN_CONTENT_WORDS:
                items.append((slot, sentence, words))

    found = []
    for (slot_a, text_a, words_a), (slot_b, text_b, words_b) in \
            itertools.combinations(items, 2):
        if slot_a == slot_b:
            continue
        overlap = len(words_a & words_b) / len(words_a | words_b)
        if overlap < threshold:
            continue
        found.append(Restatement(
            slot_a=slot_a, slot_b=slot_b, text_a=text_a, text_b=text_b,
            similarity=overlap,
            structural=(_is_bare_url(text_a) or _is_bare_url(text_b)
                        or bool({slot_a, slot_b} & NESTING_SLOTS)),
        ))
    return found


def summarize(record: dict, threshold: float = THRESHOLD) -> dict:
    """Counts for one record, with the sentence total as the denominator.

    The rate is per sentence rather than per slot on purpose: a record with more
    slots populated is not thereby more repetitive, and a per-slot rate would
    fall simply by generating more content.
    """
    total = sum(1 for _slot, text in _walk(record)
                for s in sentences(text)
                if len(_content_words(s)) >= MIN_CONTENT_WORDS)
    found = restatements(record, threshold)
    prose = [r for r in found if not r.structural]
    return {
        "sentences": total,
        "prose_restatements": len(prose),
        "structural_restatements": len(found) - len(prose),
        "rate": (len(prose) / total) if total else 0.0,
        "slots_involved": sorted({s for r in prose
                                  for s in (r.slot_a, r.slot_b)}),
        "restatements": prose,
    }


def load(path: Path) -> dict:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
