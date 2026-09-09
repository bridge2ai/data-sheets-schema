"""One wrapper for the British-spelling instrument, shared by every guard
that sweeps authored text (#1151 review, S3: two suites had inlined it and
already differed).

`british_forms(text)` returns the distinct forms `grounding.BRITISH_PATTERNS`
match, applied the way `grounding.british_spellings` applies them —
lower-cased first (M1: the patterns are compiled without re.I and the
instrument lower-cases before matching). `exempt_quotes` strips
double-quoted spans first, which is right for a prompt that quotes sources
and wrong for text the repository authors (S1: an example the model is told
to copy is not a quotation).
"""
from __future__ import annotations


def british_forms(text: str, *, exempt_quotes: bool = True) -> list[str]:
    from data_sheets_schema import grounding
    prose = grounding._QUOTED.sub(" ", text) if exempt_quotes else text
    prose = prose.lower()
    return sorted({m.group(0) for rx in grounding.BRITISH_PATTERNS for m in rx.finditer(prose)})
