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


def _walk(node: Any, path: str, out: list[dict[str, Any]]) -> None:
    if isinstance(node, yaml.MappingNode):
        seen: dict[str, list[int]] = {}
        for key_node, value_node in node.value:
            key = getattr(key_node, "value", None)
            if isinstance(key, str):
                seen.setdefault(key, []).append(key_node.start_mark.line + 1)
            _walk(value_node, f"{path}.{key}" if path else str(key), out)
        for key, lines in seen.items():
            if len(lines) > 1:
                out.append({"path": path or "$", "key": key, "lines": lines, "count": len(lines)})
    elif isinstance(node, yaml.SequenceNode):
        for i, item in enumerate(node.value):
            _walk(item, f"{path}[{i}]", out)


def find_duplicate_keys(text: str) -> list[dict[str, Any]]:
    """Every mapping key that appears more than once in one mapping, with the
    mapping's path (`$` for the top level) and the 1-based lines."""
    out: list[dict[str, Any]] = []
    try:
        node = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError:
        return out
    if node is not None:
        _walk(node, "", out)
    out.sort(key=lambda d: d["lines"][0])
    return out


def duplicate_keys_in(path: Path) -> list[dict[str, Any]]:
    return find_duplicate_keys(Path(path).read_text(encoding="utf-8", errors="replace"))


def describe(dups: list[dict[str, Any]]) -> str:
    """One validator-style line: what a standard loader would silently drop."""
    parts = [f"`{d['key']}` at {d['path']} on lines {', '.join(map(str, d['lines']))}" for d in dups]
    return ("duplicate mapping key" + ("s" if len(dups) > 1 else "") + ": " + "; ".join(parts)
            + " — a standard loader keeps only the last; merge the values into one key")
