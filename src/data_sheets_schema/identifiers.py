"""Identifier-syntax audit: what the validator accepts and the range does not (#402).

`trap-inventory` mines the corpus for validation *failures*. This is its
complement, and it exists because the more dangerous defect is the one that
passes. `uriorcurie` declares no `pattern`, so LinkML renders it as

    "id": {"type": ["string", "null"]}

and every string is legal. A bare token like `funder_nih` validates exactly as
cleanly as `https://ror.org/01cwqze88`. The declared range promises identifier
syntax; nothing enforces it, so nothing reports it, and four mutually
incompatible conventions coexisted across one label without a single warning.

Why it matters more than tidiness: the core record is a semantic exchange
layer, and entity resolution across records is the point. NIH currently appears
as `funder_nih`, `https://cm4ai.org/data-releases/#funder-nih`,
`d4d:VOICE-funding-nih-common-fund`, and as a name with no id at all. Nothing
joins those. A bare token is worse than an absent identifier, because it looks
like one and is scoped to nothing — two records both emitting `funder_nih`
collide by accident rather than agree by reference.

This module reports and never repairs. Adding a `pattern` to `uriorcurie` would
invalidate values in records already committed, which is the correct end state
and a migration rather than a flag flip; naming what is out there is the step
that has to come first.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterator

import yaml

CONCAT_DIR = Path("data/d4d_concatenated")
FULL_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")

#: An absolute IRI. Anything with a scheme is self-describing and resolvable in
#: principle, which is the property a bare token lacks.
_ABSOLUTE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")

#: `prefix:reference`. The prefix must be declared in the schema for the CURIE
#: to expand, so an undeclared prefix is reported separately from a declared
#: one: it is well-formed and still unresolvable.
_CURIE = re.compile(r"^([A-Za-z_][A-Za-z0-9._\-]*):(\S*)$")

URI = "uri"
CURIE_DECLARED = "curie_declared"
CURIE_UNDECLARED = "curie_undeclared"
BARE = "bare_token"

#: The two that cannot be resolved to anything. Reported as the headline; the
#: other two are recorded so a record's convention is visible rather than
#: merely its failures.
UNRESOLVABLE = (CURIE_UNDECLARED, BARE)


def declared_prefixes(schema_path: Path = FULL_SCHEMA) -> set[str]:
    """Prefixes the schema declares, against which a CURIE can be expanded.

    Read from the merged schema's own `prefixes:` block rather than a hardcoded
    list, so a prefix added to the schema is immediately admissible here and
    the audit cannot drift from what the schema would actually resolve.
    """
    doc = yaml.safe_load(schema_path.read_text(encoding="utf-8")) or {}
    return set(doc.get("prefixes") or {})


def classify(value: str, prefixes: set[str]) -> str:
    """Which of the four shapes an identifier value has."""
    v = value.strip()
    if _ABSOLUTE.match(v):
        return URI
    m = _CURIE.match(v)
    if m:
        return CURIE_DECLARED if m.group(1) in prefixes else CURIE_UNDECLARED
    return BARE


def walk_ids(node: Any, path: str = "$") -> Iterator[tuple[str, str]]:
    """Every `id` value in a parsed record, with the path that carries it.

    Indices are normalised to `[]` so occurrences aggregate by slot rather than
    by position — the same normalisation `trap_inventory` applies, for the same
    reason: 12 bad ids in one list is one defect, not twelve.
    """
    if isinstance(node, dict):
        raw = node.get("id")
        if isinstance(raw, str) and raw.strip():
            yield f"{path}.id", raw
        for key, child in node.items():
            if key != "id":
                yield from walk_ids(child, f"{path}.{key}")
    elif isinstance(node, list):
        for item in node:
            yield from walk_ids(item, f"{path}[]")


def audit_record(path: Path, prefixes: set[str]) -> dict[str, Any]:
    """Classify every identifier in one record."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    counts = {URI: 0, CURIE_DECLARED: 0, CURIE_UNDECLARED: 0, BARE: 0}
    offenders: list[dict[str, str]] = []
    for slot_path, value in walk_ids(doc):
        kind = classify(value, prefixes)
        counts[kind] += 1
        if kind in UNRESOLVABLE:
            offenders.append({"slot_path": slot_path, "value": value,
                              "kind": kind})
    total = sum(counts.values())
    return {"path": str(path), "total": total, "counts": counts,
            "offenders": offenders,
            # The convention this record actually used, where it used one. A
            # record that is 107/108 CURIE has a convention and one slip; a
            # record split down the middle has none, and the two want different
            # remedies.
            "dominant": (max(counts, key=lambda k: counts[k])
                         if total else None)}


def summarize(records: list[dict[str, Any]], prefixes_declared: int,
              unreadable: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Totals over exactly the records given.

    Separated from `audit` so a caller that filters — by label, method or
    project — recomputes the headline from what it kept. Reporting a filtered
    record list beside corpus-wide totals states two scopes in one breath and
    reads as one.
    """
    totals = {URI: 0, CURIE_DECLARED: 0, CURIE_UNDECLARED: 0, BARE: 0}
    for rec in records:
        for kind, n in rec["counts"].items():
            totals[kind] += n
    total = sum(totals.values())
    unresolvable = sum(totals[k] for k in UNRESOLVABLE)
    return {
        "records_scanned": len(records),
        "records_with_unresolvable_ids": len([r for r in records
                                              if r["offenders"]]),
        "identifiers": total,
        "counts": totals,
        "unresolvable": unresolvable,
        "unresolvable_share": (unresolvable / total) if total else 0.0,
        "prefixes_declared": prefixes_declared,
        "records": records,
        "unreadable": unreadable or None,
    }


def audit(root: Path = CONCAT_DIR, schema_path: Path = FULL_SCHEMA,
          include_archived: bool = False) -> dict[str, Any]:
    """Classify identifiers across every record under ``root``.

    ATTIC is excluded by default: those records were archived precisely because
    their provenance could not be established, and counting them would inflate
    a figure meant to describe the live corpus.
    """
    prefixes = declared_prefixes(schema_path)
    files = sorted(p for p in root.rglob("*_d4d.yaml")
                   if include_archived or "ATTIC" not in p.parts)
    files += sorted(p for p in root.rglob("*_d4d_core.yaml")
                    if include_archived or "ATTIC" not in p.parts)

    records: list[dict[str, Any]] = []
    unreadable: list[dict[str, str]] = []
    for f in files:
        try:
            records.append(audit_record(f, prefixes))
        except Exception as exc:  # noqa: BLE001 — a record that will not parse
            unreadable.append({"path": str(f),                # is a finding too
                               "error": f"{type(exc).__name__}: {exc}"})

    return summarize(records, len(prefixes), unreadable)
