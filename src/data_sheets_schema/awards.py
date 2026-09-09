"""NIH award numbers in a bundle and in a record — prediction 2's denominator (#1028).

The plan registered per-bundle ceilings "by the pattern `\\b[A-Z]\\d{2}[A-Z]{2}\\d{6}\\b`
and kin" and counted them by hand. The narrow form matches only an
activity code of one letter and two digits (R01, P30, P41) with no
application-type prefix; the bundles write `1OT2OD032742-01`,
`5U24HG012107`, `UL1TR003096` and, in the papers' prose, `OT2 OD032742`
and `U54 CA274502` — a leading type digit, a suffix, activity codes of
two letters and a digit, and a space or hyphen before the institute
code. Counted by hand under "and kin", AI_READI's ceiling came out 2
where its bundle carries three awards in the flagship paper's funding
statement; the first version of this module missed the spaced form and
so undercounted CM4AI by two awards (#1161 review).

`NIH_AWARD` is the pattern actually used: an optional application-type
digit, the activity code (one letter and two digits, or two letters and
one digit — the two shapes NIH issues), an optional single space or
hyphen, the two-letter institute code, six serial digits, an optional
`-NN` suffix with a revision tag; the core eleven characters, separator
stripped, are the award. Every mention is returned with the source file
it sits in and a context window, because the count a prediction needs is
not "award-shaped tokens" but "awards stated as funding this dataset":
the plan note's rule is an award the dataset paper's funding statement
attributes to this research or this work — not one it attributes to
named investigators (the CM4AI Nature resource paper's acknowledgement,
an AI_READI author's competing interest), to another named project, or
to the platform hosting the release (PhysioNet's grants on every VOICE
page) — and only the context decides. The classification is the note's
to register; this module makes the mechanical count reproducible and the
reading auditable.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

#: An NIH award number "and kin" (#1028), as the bundles write it: an
#: optional application-type digit; an activity code of one letter and two
#: digits (R01, P30, U54, T32) or two letters and one digit (OT2, UL1, DP2);
#: an optional space or hyphen before the institute code, the rendering NIH
#: itself uses in prose and the flagship papers use (`OT2 OD032742`,
#: `U54 CA274502`) — the form the first pattern missed, the way the
#: registered narrow one missed the type digit; the two-letter institute
#: code; six serial digits; an optional `-NN` suffix with a revision tag.
#: The core is normalised to its eleven characters. Case-sensitive: no
#: lower-case award appears in any bundle (#1161 review), and lower-casing
#: would admit ordinary words.
NIH_AWARD = re.compile(r"\b\d?((?:[A-Z]\d{2}|[A-Z]{2}\d)[ -]?[A-Z]{2}\d{6})(?:-\d{2}[A-Z0-9]*)?\b")

#: The registered narrow form, kept so the two counts can be compared.
NIH_AWARD_NARROW = re.compile(r"\b[A-Z]\d{2}[A-Z]{2}\d{6}\b")


def _core(match: re.Match) -> str:
    return match.group(1).replace(" ", "").replace("-", "")


def award_numbers(text: str) -> Counter[str]:
    """Distinct award numbers in `text` (core form) with their mention counts."""
    return Counter(_core(m) for m in NIH_AWARD.finditer(text))


def award_mentions(text: str, window: int = 160) -> list[dict[str, Any]]:
    """Every mention with its source file (the `FILE:` header above it) and a
    context window, whitespace-collapsed, for the reading that decides
    whether an award funds this dataset."""
    out = []
    for m in NIH_AWARD.finditer(text):
        head = text.rfind("FILE:", 0, m.start())
        source = text[head:text.find("\n", head)].strip() if head >= 0 else None
        s, e = max(0, m.start() - window), min(len(text), m.end() + window // 2)
        out.append({"award": _core(m), "as_written": m.group(0), "source": source,
                    "context": re.sub(r"\s+", " ", text[s:e]).strip()})
    return out


def record_award_numbers(record: Any) -> list[str]:
    """Distinct award numbers a record populates under `grant_number`, at any
    depth, in record order — the numerator prediction 2 counts. A value that
    is not award-shaped (`Frederick Thomas Fund`) is kept as written, so the
    caller can see it and not count it."""
    out: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "grant_number":
                    for v in (value if isinstance(value, list) else [value]):
                        if v is None:
                            continue
                        m = NIH_AWARD.search(str(v))
                        text = _core(m) if m else str(v).strip()
                        if text and text not in out:
                            out.append(text)
                walk(value)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(record)
    return out


def bundle_awards(bundle: Path) -> dict[str, Any]:
    """The mechanical count for one bundle: md5 (so the count is pinned to
    the bytes), distinct awards with mention counts, the narrow pattern's
    count for comparison, and every mention with its source and context."""
    import hashlib

    raw = bundle.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    return {"bundle": str(bundle), "bundle_md5": hashlib.md5(raw).hexdigest(),
            "awards": dict(award_numbers(text)), "narrow": dict(Counter(NIH_AWARD_NARROW.findall(text))),
            "mentions": award_mentions(text)}
