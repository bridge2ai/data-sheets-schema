"""Bundle-wide absence claims and record self-narration in free text (#2919).

Generated records carry two kinds of statement no passage in the bundle can
support. One is an absence asserted of the bundle as a whole ("No source in
the bundle states …", "not stated by any source"): it was found by searching,
and a search that came up empty is not a passage anyone can cite. The other
is the record narrating its own construction ("`keywords` is left empty",
"so those slots are omitted", "which is the count recorded here"). The
generation contract invites both — `source_caveats` asks for "questions the
sources leave unanswered" — and only the direct arm's audits reject them, so
audit-finding counts across arms apply different standards.

This is the measurement half of that issue: a read-only lint. It walks the
free-text leaves a lexicon's `scope` names — `description`, `notes`,
`source_caveats` and any `*_details`, at any depth, never inside `name`, `id`
or `keywords` — and reports each phrase the registered lexicon
`absence_self_narration` matches, by class, at its JSON pointer (RFC 6901).

What it does not establish: a match is a regular-expression hit on
whitespace-collapsed text, not a reviewed finding. The lexicon misses
phrasings it does not list and matches some sentences that are not defects —
a quoted source sentence, a dataset fact that happens to use the phrase — so
it is never gating, and a count is comparable only with a count made under
the same lexicon sha256. Nothing here writes a record or a provenance block;
wiring the count into the provenance checks comes with the condition that
changes the instruction.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import yaml

from data_sheets_schema import lexicon as lx

LEXICON = "absence_self_narration"

#: The `scope` keys this reader interprets; a lexicon without them cannot say
#: which leaves it measures, so it is refused rather than read with defaults.
SCOPE_KEYS = ("free_text_keys", "free_text_key_suffixes", "excluded_keys")


def _scope(lexicon: lx.Lexicon) -> dict[str, Any]:
    scope = lexicon.scope
    bad = [k for k in SCOPE_KEYS if not isinstance(scope.get(k), list)]
    if bad:
        raise lx.LexiconError(f"{lexicon.file}: scope must list {', '.join(bad)}")
    return scope


def _pointer(parent: str, token: Any) -> str:
    return parent + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _is_free_text(key: Any, scope: dict[str, Any]) -> bool:
    return isinstance(key, str) and (
        key in scope["free_text_keys"] or any(key.endswith(s) for s in scope["free_text_key_suffixes"]))


def _strings(node: Any, pointer: str, key: str) -> Iterator[tuple[str, str, str]]:
    """The strings a free-text slot holds: its own value, or each member of
    its list. A mapping inside the list is walked like any other node."""
    if isinstance(node, str):
        yield pointer, key, node
    elif isinstance(node, list):
        for i, item in enumerate(node):
            if isinstance(item, str):
                yield _pointer(pointer, i), key, item


def free_text_leaves(record: Any, scope: dict[str, Any]) -> Iterator[tuple[str, str, str]]:
    """(JSON pointer, slot, text) for every free-text string in the record.

    Excluded keys are skipped whole: a phrase in a `name`, an `id` or a
    `keywords` entry is never counted, and nothing nested under one is read.
    A node reached through a YAML alias is read at each pointer it appears
    at, since the parsed record carries it at each; a node that contains
    itself is read once.
    """
    excluded = set(scope["excluded_keys"])

    def walk(node: Any, pointer: str, ancestors: frozenset[int]) -> Iterator[tuple[str, str, str]]:
        if id(node) in ancestors:
            return
        ancestors = ancestors | {id(node)}
        if isinstance(node, dict):
            for key, value in node.items():
                if key in excluded:
                    continue
                here = _pointer(pointer, key)
                if _is_free_text(key, scope):
                    yield from _strings(value, here, key)
                if isinstance(value, (dict, list)):
                    yield from walk(value, here, ancestors)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                if isinstance(item, (dict, list)):
                    yield from walk(item, _pointer(pointer, i), ancestors)

    yield from walk(record, "", frozenset())


def _merge(spans: list[tuple[int, int, str]]) -> list[tuple[int, int, list[str]]]:
    """Overlapping spans of one class in one leaf are one phrase: two patterns
    matching the same words are not two claims."""
    merged: list[tuple[int, int, list[str]]] = []
    for start, end, pid in sorted(spans):
        if merged and start < merged[-1][1]:
            s, e, ids = merged[-1]
            merged[-1] = (s, max(e, end), ids + [pid])
        else:
            merged.append((start, end, [pid]))
    return merged


def lint(record: Any, lexicon: lx.Lexicon | None = None) -> dict[str, Any]:
    """The lint result for one parsed record.

    `phrases` counts merged phrases; `by_pattern` counts every pattern's raw
    matches, so a phrase two patterns match adds one to `phrases` and one to
    each pattern. Every declared class and pattern is present, at 0 where
    nothing matched, so a zero is a measurement and not a missing key.
    """
    lexicon = lexicon or lx.load(LEXICON)
    scope = _scope(lexicon)
    by_class = {cls: {"phrases": 0, "leaves": 0} for cls in lexicon.classes}
    by_pattern = {p.id: 0 for p in lexicon.patterns}
    hits: list[dict[str, Any]] = []
    leaves = 0
    for pointer, key, raw in free_text_leaves(record, scope):
        leaves += 1
        text = " ".join(raw.split())
        spans: dict[str, list[tuple[int, int, str]]] = {}
        for pattern in lexicon.patterns:
            for m in pattern.regex.finditer(text):
                by_pattern[pattern.id] += 1
                spans.setdefault(pattern.cls, []).append((m.start(), m.end(), pattern.id))
        for cls in lexicon.classes:                        # declared order, so output is stable
            phrases = _merge(spans.get(cls, []))
            if not phrases:
                continue
            by_class[cls]["leaves"] += 1
            by_class[cls]["phrases"] += len(phrases)
            hits.extend({"pointer": pointer, "slot": key, "class": cls, "start": s, "end": e,
                         "text": text[s:e], "patterns": sorted(set(ids))} for s, e, ids in phrases)
    return {"instrument": lexicon.instrument, "lexicon": lexicon.identity(), "gating": False,
            "text_basis": "whitespace-collapsed free-text leaves; offsets are into that text",
            "leaves": leaves, "phrases": sum(c["phrases"] for c in by_class.values()),
            "by_class": by_class, "by_pattern": by_pattern, "hits": hits}


def lint_path(path: Path, lexicon: lx.Lexicon | None = None) -> dict[str, Any]:
    """Lint a record file. The YAML is read as parsed: where a mapping key is
    repeated the last value wins (#1029), so an earlier one is not linted."""
    record = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError(f"{path} is not a mapping")
    return {"record": str(path), **lint(record, lexicon)}
