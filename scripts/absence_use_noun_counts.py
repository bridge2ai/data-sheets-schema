#!/usr/bin/env python
"""How often `use` is a noun in the pinned records' free text (#3875, #3992).

`notes/absence_lexicon_v5_2026-09-30.md` argues that the bare word `use` in
the records is overwhelmingly a noun, which is why lexicon v5 no longer
takes it for a preference verb after a determiner or before a noun such as
"agreement". This script produces the figures that sentence quotes, so they
can be regenerated rather than taken on trust.

The reading is fixed here and stated in the output:

- the records are the baseline's pinned set
  (`notes/absence_claims_baseline_records.yaml`), each read only if its
  bytes still hash to its pin;
- the text is every free-text leaf `absence_lint.free_text_leaves` yields
  under the scope of lexicon `absence_self_narration` at
  `absence_claims_baseline.LEXICON_VERSION`, as written: the patterns take
  any run of whitespace between their words, so collapsing it as
  `absence_lint.lint` does would change no count;
- each pattern counts non-overlapping occurrences, case-insensitively.

Usage:
    poetry run python scripts/absence_use_noun_counts.py
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Iterable

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import absence_claims_baseline as baseline  # noqa: E402
from data_sheets_schema import absence_lint, lexicon as lx  # noqa: E402

#: (label, pattern). Counted case-insensitively and independently: one
#: occurrence of "use agreement" counts under both the first and second row.
PATTERNS: tuple[tuple[str, str], ...] = (
    ("use/uses", r"\buses?\b"),
    ("use agreement(s)", r"\buses?\s+agreements?\b"),
    ("use of", r"\buse\s+of\b"),
    ("data use", r"\bdata\s+use\b"),
)


def count(texts: Iterable[str]) -> dict[str, int]:
    """Occurrences of each pattern over `texts`."""
    compiled = [(label, re.compile(rx, re.IGNORECASE)) for label, rx in PATTERNS]
    totals = {label: 0 for label, _ in PATTERNS}
    for text in texts:
        for label, rx in compiled:
            totals[label] += len(rx.findall(text))
    return totals


def pinned_texts(corpus: Path = baseline.CORPUS, pins: dict[str, str] | None = None) -> tuple[list[str], int]:
    """The free-text leaves of the pinned records, and how many records were read.

    A pinned record whose bytes are not its pin, or that is gone, raises
    `baseline.Stale` naming it, as the baseline does, rather than being
    counted as bytes the pins do not name.
    """
    pins = baseline.read_pins() if pins is None else pins
    scope = absence_lint._scope(lx.load(absence_lint.LEXICON, baseline.LEXICON_VERSION))
    texts: list[str] = []
    bad: list[str] = []
    read = 0
    for rel in sorted(pins):
        try:
            raw = (corpus / rel).read_bytes()
        except OSError:
            bad.append(f"gone {rel}")
            continue
        if hashlib.sha256(raw).hexdigest() != pins[rel]:
            bad.append(f"changed {rel}")
            continue
        read += 1
        try:
            data = yaml.safe_load(raw.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError):
            continue
        if isinstance(data, dict):
            texts.extend(text for _, _, text in absence_lint.free_text_leaves(data, scope))
    if bad:
        raise baseline.Stale("; ".join(bad))
    return texts, read


def main(argv: list[str] | None = None) -> int:
    texts, n = pinned_texts()
    totals = count(texts)
    print(f"{n} pinned records, {len(texts)} free-text leaves "
          f"(lexicon v{baseline.LEXICON_VERSION} scope, case-insensitive)")
    for label, _ in PATTERNS:
        print(f"{label}: {totals[label]:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
