"""Duplicate mapping keys in a record's YAML text (#1029).

The AI_READI 2026-09-04f full record carried a top-level `source_caveats`
block scalar three times — the model wrote one after `variables`, one after
`distribution_formats`, and the reconcile/repair phases added one after
`external_resources`. `yaml.safe_load` keeps the last, so the parsed record
and the core derived from it silently lost two caveats, and `validation`
read `passed: true` on the last-wins parse. None of the 270 records on main
had a duplicate key, so this is a defect class with a clean floor of 0 that
no instrument counted.

The scan works on the composed node tree, not the loaded data — the data
has already forgotten — and reports each duplicated key with the mapping's
path and every line it appears on, so the validator's message can say
where, the record can carry it, and the repair round can be told what to
merge.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


def _key_identity(loader: yaml.SafeLoader, key_node: Any) -> Any:
    """What `safe_load` would use as the key: the constructed value, so `true`
    and `True` collide as they do in the loader, and `1` and `"1"` do not.
    Unhashable or unconstructable keys fall back to the node's text."""
    if not isinstance(key_node, yaml.ScalarNode):
        return ("node", id(key_node))
    try:
        value = loader.construct_object(key_node, deep=True)
        hash(value)
        # The value itself, compared as a dict key compares it: `true`, `1`
        # and `1.0` are one key to the loader, `1` and `"1"` are two.
        return ("value", value)
    except Exception:                                          # noqa: BLE001
        return ("text", key_node.value)


def _walk(loader: yaml.SafeLoader, node: Any, path: str, out: list[dict[str, Any]],
          seen_nodes: set[int]) -> None:
    # An alias is the same node object again: visited once, so a cyclic or
    # widely shared graph neither recurses forever nor scans exponentially
    # (#1032). `safe_load` accepts such documents.
    if id(node) in seen_nodes:
        return
    seen_nodes.add(id(node))
    if isinstance(node, yaml.MappingNode):
        seen: dict[Any, tuple[str, list[int]]] = {}
        for key_node, value_node in node.value:
            text = getattr(key_node, "value", None)
            # `<<` merges every mapping it names; SafeLoader honours each
            # occurrence, so two of them are not a duplicate in the loader's
            # sense.
            if text == "<<" and getattr(key_node, "tag", "") == "tag:yaml.org,2002:merge":
                _walk(loader, value_node, f"{path}.<<" if path else "<<", out, seen_nodes)
                continue
            ident = _key_identity(loader, key_node)
            label = text if isinstance(text, str) else str(text)
            seen.setdefault(ident, (label, []))[1].append(key_node.start_mark.line + 1)
            _walk(loader, value_node, f"{path}.{label}" if path else label, out, seen_nodes)
        for label, lines in seen.values():
            if len(lines) > 1:
                out.append({"path": path or "$", "key": label, "lines": lines, "count": len(lines)})
    elif isinstance(node, yaml.SequenceNode):
        for i, item in enumerate(node.value):
            _walk(loader, item, f"{path}[{i}]", out, seen_nodes)


#: libyaml's safe loader where PyYAML was built with it, else the pure-Python
#: one: what a caller scanning many files passes as `loader=` (#3704).
FAST_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

#: The deepest collection nesting a libyaml loader is asked to compose.
#: libyaml's composer recurses on the C stack, where the interpreter's
#: recursion limit does not apply: at 50,000 nested flow mappings it kills
#: the process with SIGSEGV instead of raising (#3817). A tree deeper than
#: the recursion limit cannot be walked anyway, so it is refused before
#: libyaml composes it; the bound is the smaller of the two.
LIBYAML_MAX_DEPTH = 1000

try:                                                       # PyYAML built without libyaml has none
    from yaml._yaml import CParser as _CParser
except ImportError:                                        # pragma: no cover
    _CParser = None

_COLLECTION_START = (yaml.MappingStartEvent, yaml.SequenceStartEvent)
_COLLECTION_END = (yaml.MappingEndEvent, yaml.SequenceEndEvent)


def nesting_exceeds(text: str, loader: type, limit: int) -> bool:
    """Whether `text` nests collections more than `limit` deep, decided
    without composing it (#3817, #3826): the loader's own event stream
    (`yaml.parse`), whose collection start and end events are counted. libyaml
    parses with explicit stacks rather than recursion, and its composer
    consumes exactly these events, so the count is the depth the composer
    would reach, whatever the text spells it with: a leading byte-order
    mark, flow or block style, indentation, anchors, tags or aliases (an
    alias is one event and nests nothing). A stream the parser rejects before
    passing the limit is not too deep here; the composer then reports its
    error at the same place. There is no textual shortcut: two of them were
    defeated in review (#3817, #3826), so every text is parsed once here and
    once more by the composer."""
    depth = 0
    try:
        for event in yaml.parse(text, Loader=loader):
            if isinstance(event, _COLLECTION_START):
                depth += 1
                if depth > limit:
                    return True
            elif isinstance(event, _COLLECTION_END):
                depth -= 1
    except yaml.YAMLError:
        return False
    return False


def find_duplicate_keys(text: str, loader: type = yaml.SafeLoader, *,
                        strict: bool = False) -> list[dict[str, Any]]:
    """Every mapping key that appears more than once in one mapping — keys
    compared as the loader would construct them — with the mapping's path
    (`$` for the top level) and the 1-based lines. `count` is occurrences
    of that key; the gate counts distinct duplicated keys.

    `loader` composes the node tree the rule walks; the rule is the same
    whichever composes it. The default is the pure-Python `SafeLoader`, as
    it always was; `FAST_LOADER` (libyaml's) gives the same findings about
    nine times faster (CPU time over the 1,616 YAML files under
    `data/d4d_concatenated` on 2026-09-30, the depth guard below included:
    58.4 s against 6.7 s, of which the guard's event pass is 2.3 s; #3704,
    #3800, #3817, #3826).

    A text that cannot be scanned — the reader or composer rejects it, or it
    nests past the interpreter's recursion limit — gives `[]` by default:
    nothing is claimed about its keys. With `strict=True` that failure is
    raised instead (the `yaml.YAMLError` or `RecursionError` itself), for a
    caller that must refuse what it cannot check. Under `FAST_LOADER` the walk
    can be the only step that fails: libyaml composes a tree deeper than the
    recursion limit (on the C stack) and PyYAML constructs one without
    recursing, so a caller that treats `[]` as "no duplicates" and then loads
    the value would accept a record whose duplicate keys it never looked at
    (#3799).

    libyaml's composer is never handed a tree nested more than
    `min(sys.getrecursionlimit(), LIBYAML_MAX_DEPTH)` deep: past some tens of
    thousands of levels its C recursion overflows the stack and the process
    dies with SIGSEGV, which no `except` can catch (#3817). Such a text is
    refused as one nested past the recursion limit — `[]`, or under `strict`
    a `RecursionError` — before libyaml composes it. The depth is counted on
    the loader's own event stream (`nesting_exceeds`), which libyaml builds
    without recursing, so it is the depth the composer would reach however
    the text spells it: a byte-order mark, flow or block style, properties.
    The walk could not have reached its keys; a tree nested that deep only in
    key position, which the walk does not enter, is refused too, as the
    pure-Python loader refuses it.
    The pure-Python `SafeLoader` is not checked: it raises `RecursionError`
    itself, so the default path is unchanged."""
    out: list[dict[str, Any]] = []
    if _CParser is not None and isinstance(loader, type) and issubclass(loader, _CParser):
        limit = min(sys.getrecursionlimit(), LIBYAML_MAX_DEPTH)
        if nesting_exceeds(text, loader, limit):
            if strict:
                raise RecursionError(f"the text nests collections more than {limit} deep; "
                                     "libyaml is not asked to compose it (#3817)")
            return out
    # A stream the reader rejects (a NUL byte), a document the composer
    # rejects (two documents), or one nested past the interpreter's limit
    # is not scannable here; `safe_load` fails on the same text and the
    # validator reports that. Nothing is claimed about its keys.
    try:
        composer = loader(text)
    except (yaml.YAMLError, RecursionError):
        if strict:
            raise
        return out
    try:
        node = composer.get_single_node()
        if node is not None:
            _walk(composer, node, "", out, set())
    except (yaml.YAMLError, RecursionError):
        if strict:
            raise
        return []
    finally:
        composer.dispose()
    out.sort(key=lambda d: d["lines"][0])
    return out


def duplicate_keys_in(path: Path) -> list[dict[str, Any]]:
    return find_duplicate_keys(Path(path).read_text(encoding="utf-8", errors="replace"))


def findings(dups: list[dict[str, Any]]) -> list[str]:
    """One finding per *extra* occurrence, so a repair that merges three
    copies into two has made progress the convergence rule can see
    (#1032 second pass)."""
    return [describe([d]) for d in dups for _ in range(max(1, d["count"] - 1))]


def describe(dups: list[dict[str, Any]]) -> str:
    """One validator-style line: what a standard loader would silently drop."""
    parts = [f"`{d['key']}` at {d['path']} on lines {', '.join(map(str, d['lines']))}" for d in dups]
    return ("duplicate mapping key" + ("s" if len(dups) > 1 else "") + ": " + "; ".join(parts)
            + " — a standard loader keeps only the last; merge the values into one key")
