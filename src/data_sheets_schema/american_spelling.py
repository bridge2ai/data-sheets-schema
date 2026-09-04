"""Write-time American spelling for the prose a record states (#1002).

The prompt has asked for American English since v4 (Camille Nebeker's review:
*no 'programme'*), the form block counts British forms under instrument v3
(`grounding.BRITISH_PATTERNS`, #836/#859), and the count is a canary metric
(prediction 5 of the v5 plan). It has stayed a rule with no mechanism: the
v6 and v7 arms sat at 0–2 by variance and the VOICE v8 canary wrote
`programme` four times in its own prose (8 counted, against a v7 worst of
2). This is the mechanism behind that rule, the same shape as the CURIE
(#974) and `mailto:` (#981) normalisers: text-level, so the `#` provenance
header and the model's own YAML layout survive; every rewrite logged, so
the record says what the model actually wrote.

**One rule per instrument pattern.** `RULES` mirrors `BRITISH_PATTERNS`
one for one, and a test asserts that every instrument pattern is covered
and that the instrument counts 0 on what this module writes. The
instrument is the authority on *what* is British; this module only says
what the American form is.

**What is left alone**, in the instrument's terms and beyond them:

- double-quoted spans (`"…"`), the instrument's own exemption for quoted
  source text — a title or a direct quotation keeps its source's spelling;
- YAML keys, the `#` header, and block-scalar indicators;
- identifier-shaped tokens: anything with `://`, a `/`, an `@`, a `:` or a
  `.` inside the token (`https://x.org/programme/`, `programme.csv`,
  `doi:10.1/programme`) — the instrument counts these, so a record naming
  such a file still shows a count, which is honest: the count is a fact
  about the text and the file name is a fact about the source.

**What this cannot know**: a proper noun in unquoted prose ("the Wellcome
Centre", "Programme Director") is rewritten like any other word. The
instrument counts it the same way, so the model was already asked to quote
it; the log names every rewrite, and a curator can restore one through
`d4d review disposition --amend` (#903).
"""

from __future__ import annotations

import re
from typing import Any, Callable

from data_sheets_schema.grounding import BRITISH_PATTERNS, british_spellings

#: Instrument note the normalisation block carries, so a reader knows which
#: rule set rewrote a record (the instrument's own version is on the form
#: block; this is the mechanism's).
NORMALISER_VERSION = "v1 (#1002): one rule per BRITISH_PATTERNS v3 entry; double-quoted spans and identifier-shaped tokens exempt"


def _swap(british: str, american: str) -> Callable[[str], str]:
    """Replace the first occurrence of a stem in the lowercased match."""
    return lambda w: w.replace(british, american, 1)


def _ise(w: str) -> str:
    """The -ise family: the stem ends in `is`; `iz` takes its place."""
    i = w.rfind("is")
    return w[:i] + "iz" + w[i + 2:]


def _centr(w: str) -> str:
    return "center" + {"e": "", "es": "s", "ed": "ed", "ing": "ing"}[w[5:]]


def _catalogu(w: str) -> str:
    return "catalog" + {"e": "", "es": "s", "ed": "ed", "ing": "ing"}[w[8:]]


#: (instrument pattern source, American form of the lowercased match). Order
#: and text follow `BRITISH_PATTERNS`; the coverage test pairs them by source.
_RULE_TABLE: tuple[tuple[str, Callable[[str], str]], ...] = (
    (r"\blicenc(?:es?|ed|ing)\b", _swap("licenc", "licens")),
    (r"\banalys(?:e|ed|ing)\b", _swap("analys", "analyz")),
    (r"\borganis(?:e|ed|es|ing|ers?|ations?|ational(?:ly)?)\b", _swap("organis", "organiz")),
    (r"\benrol(?:s|ments?)?\b", _swap("enrol", "enroll")),
    (r"\bprogrammes?\b", _swap("programme", "program")),
    (r"\bstandardis(?:e|ed|es|ing|ations?)\b", _swap("standardis", "standardiz")),
    (r"\blabell(?:ing|ed)\b", _swap("labell", "label")),
    (r"\bcentr(?:e|es|ed|ing)\b", _centr),
    (r"\brecognis(?:e|ed|es|ing)\b", _swap("recognis", "recogniz")),
    (r"\butilis(?:e|ed|es|ing|ations?)\b", _swap("utilis", "utiliz")),
    (r"\bcatalogu(?:e|es|ed|ing)\b", _catalogu),
    (r"\bsummaris(?:e|ed|es|ing)\b", _swap("summaris", "summariz")),
    (r"\bbehaviours?(?:al(?:ly)?)?\b", _swap("behaviour", "behavior")),
    (r"\bcolour(?:s|ed|ings?|ful)?\b", _swap("colour", "color")),
    (r"\b(?:un)?favour(?:s|ed|ing|abl[ye]|ites?)?\b", _swap("favour", "favor")),
    (r"\bhonour(?:s|ed|ing|able)?\b", _swap("honour", "honor")),
    (r"\b(?:centi|milli|kilo)?metres?\b", _swap("metre", "meter")),
    (r"\btumours?\b", _swap("tumour", "tumor")),
    (r"\boedema(?:tous)?\b", _swap("oedema", "edema")),
    (r"\bpaediatrics?\b", _swap("paediatric", "pediatric")),
    (r"\bhaem(?:o\w*|atolog\w*|orrhag\w*)\b", _swap("haem", "hem")),
    (r"\banaemi[ac]\b", _swap("anaemi", "anemi")),
    (r"\bageing\b", _swap("ageing", "aging")),
    (r"\btravell(?:ing|ed|ers?)\b", _swap("travell", "travel")),
    (r"\bcounsell(?:ing|ed|ors?)\b", _swap("counsell", "counsel")),
    (r"\bcancell(?:ed|ing)\b", _swap("cancell", "cancel")),
    (r"\bmodell(?:ing|ed|ers?)\b", _swap("modell", "model")),
    (r"\btotall(?:ing|ed)\b", _swap("totall", "total")),
    (r"\bartefacts?\b", _swap("artefact", "artifact")),
    (r"\bfibres?\b", _swap("fibre", "fiber")),
    (r"\blitres?\b", _swap("litre", "liter")),
    (r"\b(?:neighbour|labour|harbour|humour|vapour|flavour|rumour|armour|endeavour)"
     r"(?:s|ed|ing|hoods?|ous|able)?\b", _swap("our", "or")),
    (r"\b(?:defence|offence|pretence)s?\b", _swap("nce", "nse")),
    (r"\bfulfil(?:s|ment)?\b", _swap("fulfil", "fulfill")),
    (r"\bpractis(?:e|ed|es|ing)\b", _swap("practis", "practic")),
    (r"\bsceptic(?:al|ism|s)?\b", _swap("sceptic", "skeptic")),
    (r"\bsulphur\w*\b", _swap("sulphur", "sulfur")),
    (r"\b(?:minimis|maximis|optimis|personalis|generalis|prioritis|characteris|harmonis|"
     r"normalis|anonymis|pseudonymis|visualis|randomis|customis|centralis|finalis|"
     r"stabilis|sterilis|immunis|sensitis|categoris|capitalis|mobilis|realis|specialis|"
     r"emphasis|hypothesis|synthesis|digitis|authoris|criticis|italicis|localis|"
     r"marginalis|neutralis|operationalis|popularis|scrutinis|serialis|symbolis|"
     r"tokenis|vaporis|vocalis|westernis)(?:e|ed|es|ing|ations?|ability|ers?)\b", _ise),
)

RULES: tuple[tuple[re.Pattern[str], Callable[[str], str]], ...] = tuple(
    (re.compile(src, re.IGNORECASE), fn) for src, fn in _RULE_TABLE)

#: Spans left as written: the instrument's quoted-text exemption, and tokens
#: shaped like an identifier, a path or a file name rather than a word.
_QUOTED = re.compile(r'"[^"\n]*"')
_IDENTIFIER_TOKEN = re.compile(r"\S*(?:://|/|@|:\S|\.\S)\S*")
_PROTECTED = re.compile(f"{_QUOTED.pattern}|{_IDENTIFIER_TOKEN.pattern}")

#: The YAML lines this walks: a mapping key (possibly a list item), a bare
#: list item, and a block-scalar indicator on a key line.
_KEY = re.compile(r"^(?P<indent>[ \t]*)(?P<dash>-[ \t]+)?(?P<slot>[A-Za-z_][\w.-]*):(?:[ \t]+(?P<value>.*)|$)")
_ITEM = re.compile(r"^(?P<indent>[ \t]*)-(?:[ \t]+|$)")
_BLOCK = re.compile(r"^[|>][+-]?\d?[+-]?(?:[ \t]+#.*)?$")

def _case_like(source: str, american: str) -> str:
    if len(source) > 1 and source.isupper():
        return american.upper()
    if source[:1].isupper():
        return american[:1].upper() + american[1:]
    return american


def americanise(prose: str) -> tuple[str, list[tuple[str, str]]]:
    """Rewrite one span of prose; returns the text and the (from, to) pairs.

    Protected spans (quoted text, identifier-shaped tokens) are cut out first
    and put back untouched, so a rule never sees them.
    """
    rewrites: list[tuple[str, str]] = []

    def rewrite(segment: str) -> str:
        for pattern, fn in RULES:
            def sub(m: re.Match[str]) -> str:
                src = m.group(0)
                out = _case_like(src, fn(src.lower()))
                if out != src:
                    rewrites.append((src, out))
                return out
            segment = pattern.sub(sub, segment)
        return segment

    out: list[str] = []
    pos = 0
    for m in _PROTECTED.finditer(prose):
        out.append(rewrite(prose[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(rewrite(prose[pos:]))
    return "".join(out), rewrites


def normalise_british_spellings(text: str, *, phase: str | None = None,
                                log: list[dict[str, Any]] | None = None) -> str:
    """Rewrite British forms in a record's YAML text, value by value.

    Keys are never touched. On a mapping line only the value is read; a
    list item and a block-scalar body line are read whole. Lines of the
    `#` header are skipped. Each rewrite is appended to `log` when one is
    given (the runner passes its rewrite log), as `{phase, kind:
    "british_spelling", slot, from, to}` with `slot` the enclosing key, so
    the record can say what the model wrote
    (`normalisation.british_spellings`).
    """
    out: list[str] = []
    enclosing: list[tuple[int, str]] = []
    block_indent: int | None = None

    def width(s: str) -> int:
        return len(s.expandtabs(8))

    def emit(segment: str, owner: str | None) -> str:
        new, pairs = americanise(segment)
        if log is not None:
            for src, dst in pairs:
                log.append({"phase": phase, "kind": "british_spelling", "slot": owner,
                            "from": src, "to": dst})
        return new

    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        eol = line[len(body):]
        if block_indent is not None:
            if not body.strip() or width(body[:len(body) - len(body.lstrip())]) > block_indent:
                owner = enclosing[-1][1] if enclosing else None
                out.append(emit(body, owner) + eol)
                continue
            block_indent = None
        if body.lstrip().startswith("#") or not body.strip():
            out.append(line)
            continue
        k = _KEY.match(body)
        if k:
            col = width(k.group("indent")) + (width(k.group("dash")) if k.group("dash") else 0)
            enclosing = [(c, sl) for c, sl in enclosing if c < col]
            enclosing.append((col, k.group("slot")))
            value = k.group("value")
            if value is None:
                out.append(line)
                continue
            if _BLOCK.match(value):
                block_indent = col
                out.append(line)
                continue
            head = body[:k.start("value")]
            out.append(head + emit(value, k.group("slot")) + eol)
            continue
        it = _ITEM.match(body)
        if it:
            col = width(it.group("indent"))
            enclosing = [(c, sl) for c, sl in enclosing if c <= col]
            owner = enclosing[-1][1] if enclosing else None
            out.append(body[:it.end()] + emit(body[it.end():], owner) + eol)
            continue
        owner = enclosing[-1][1] if enclosing else None
        out.append(emit(body, owner) + eol)
    return "".join(out)


def rules_cover_instrument() -> list[str]:
    """Instrument patterns with no rule of the same source — empty when the
    two are in step. A test asserts it; the function exists so a reviewer
    can ask the question at the prompt."""
    have = {src for src, _ in _RULE_TABLE}
    return [p.pattern for p in BRITISH_PATTERNS if p.pattern not in have]


def residual_count(text: str) -> int:
    """What the instrument still counts after this module has run."""
    return british_spellings(normalise_british_spellings(text))
