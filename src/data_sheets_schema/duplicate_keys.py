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
        return (type(value).__name__, value)
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


def find_duplicate_keys(text: str) -> list[dict[str, Any]]:
    """Every mapping key that appears more than once in one mapping — keys
    compared as the loader would construct them — with the mapping's path
    (`$` for the top level) and the 1-based lines. `count` is occurrences
    of that key; the gate counts distinct duplicated keys."""
    out: list[dict[str, Any]] = []
    loader = yaml.SafeLoader(text)
    try:
        node = loader.get_single_node()
    except yaml.YAMLError:
        loader.dispose()
        return out
    try:
        if node is not None:
            _walk(loader, node, "", out, set())
    finally:
        loader.dispose()
    out.sort(key=lambda d: d["lines"][0])
    return out


def duplicate_keys_in(path: Path) -> list[dict[str, Any]]:
    return find_duplicate_keys(Path(path).read_text(encoding="utf-8", errors="replace"))


def describe(dups: list[dict[str, Any]]) -> str:
    """One validator-style line: what a standard loader would silently drop."""
    parts = [f"`{d['key']}` at {d['path']} on lines {', '.join(map(str, d['lines']))}" for d in dups]
    return ("duplicate mapping key" + ("s" if len(dups) > 1 else "") + ": " + "; ".join(parts)
            + " — a standard loader keeps only the last; merge the values into one key")
