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
#: one: it is well-formed and still unresolvable. The reference is `\S+`, not
#: `\S*`: `d4d:` expands to the namespace itself and identifies nothing, so
#: accepting it would pass a value that names no entity.
_CURIE = re.compile(r"^([A-Za-z_][A-Za-z0-9._\-]*):(\S+)$")

#: URI schemes whose syntax has no authority component, so `://` never appears
#: and the `_ABSOLUTE` test above misses them (#530). They are URIs, not CURIEs:
#: `urn` is a scheme, not a namespace this schema could bind to a base IRI, and
#: declaring a prefix for it would produce an expansion that means nothing.
#:
#: 1,067 corpus values sit here — `urn:` 757, `ark:` 286, `doi:` 24 — and every
#: one was counted as an undeclared CURIE, inflating the migration #457 is sized
#: against by 28% of that bucket.
#:
#: **Kept deliberately short, and to registered schemes only.** Every name here
#: exempts a value from the audit, so a name that is *not* a scheme silently
#: excuses a real defect. `isbn`, `issn` and `uuid` were dropped for exactly
#: this reason: they are URN *namespaces* (`urn:isbn:…`), not schemes, and a
#: record writing `uuid:abc` would be minting a prefix, not citing one.
#:
#: `file` is the sharpest case and is **excluded**. It is a registered scheme,
#: but its 22 corpus occurrences are `file:torchaudio_spectrograms_parquet` —
#: a minted type-prefix in the same family as `org:`, `creator:` and
#: `software:` (#531), not `file:///path`. Adding it would erase 22 genuine
#: findings to accommodate a name collision.
NO_AUTHORITY_SCHEMES = frozenset({
    "urn", "doi", "ark", "mailto", "tel", "info",
})

URI = "uri"
#: Well-formed under its scheme, resolution not established. Separate from
#: `URI` on purpose: `urn:cm4ai:org:ucsd` is a syntactically valid URN whose
#: NID is not IANA-registered, and `ark:59853/…` depends on a NAAN that may not
#: be assigned. Filing those beside a resolvable `https://ror.org/…` would
#: overstate their standing as badly as calling them CURIEs understates it.
URI_UNVERIFIED = "uri_unverified"
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
    """Which of the five shapes an identifier value has.

    Scheme detection runs before the CURIE test, because the two grammars
    overlap: `urn:cm4ai:org:ucsd` matches `prefix:reference` perfectly well and
    is not a CURIE. Order is what separates them, and a declared prefix that
    collided with a scheme name would otherwise change a value's classification
    depending on which test ran first.
    """
    v = value.strip()
    if _ABSOLUTE.match(v):
        return URI
    m = _CURIE.match(v)
    if m:
        # A *declared* prefix wins over a scheme of the same name. `doi` is
        # both an IANA scheme and, since the CURIE rule, a prefix bound to
        # `https://doi.org/` — and the CURIE reading is strictly more
        # informative: it expands to a resolvable IRI, where the scheme
        # reading can only say "well-formed, resolution not established".
        #
        # This reverses the precedence #530 set. That order was right when no
        # such prefix was declared: `urn:cm4ai:org:ucsd` matches
        # `prefix:reference` and is not a CURIE, and nothing bound `urn` to a
        # namespace. It is still right for `urn` and `ark`, which remain
        # undeclared and still fall through to URI_UNVERIFIED below.
        if m.group(1) in prefixes:
            return CURIE_DECLARED
        if m.group(1).lower() in NO_AUTHORITY_SCHEMES:
            return URI_UNVERIFIED
        return CURIE_UNDECLARED
    return BARE


def uriorcurie_slots(schema_path: Path = FULL_SCHEMA) -> set[str]:
    """Every slot whose *induced* range is `uriorcurie`, from the schema.

    Derived rather than hardcoded to `id`, because `id` is one of several and
    the others hold the worse values (`unit`, since moved to `string` (#456),
    was 148 for 148 unresolvable — `%`, `years`); `publisher` carries bare names like `PhysioNet`,
    `latest_version_doi` carries bare DOIs, and `data_substrate` and
    `data_topic` carry whole prose sentences. An audit that checked only `id`
    would report a clean `unit` slot that has never once held an identifier.

    Induced, not declared, so a `slot_usage` narrowing some other slot to
    `uriorcurie` is picked up without anyone remembering to add it here.
    """
    from data_sheets_schema.schema_view import shared_view

    sv = shared_view(schema_path)
    found: set[str] = set()
    for class_name in sv.all_classes():
        for slot_name in sv.class_slots(class_name, attributes=True):
            try:
                slot = sv.induced_slot(slot_name, class_name)
            except Exception:  # noqa: BLE001 — a slot that will not resolve
                continue       # is not evidence about identifier syntax
            if str(slot.range) == "uriorcurie":
                found.add(slot_name)
    return found


def walk_identifiers(node: Any, slots: set[str],
                     path: str = "$") -> Iterator[tuple[str, str, str]]:
    """Every identifier-ranged value in a record, as (path, slot, value).

    Indices are normalised to `[]` so occurrences aggregate by slot rather than
    by position — the same normalisation `trap_inventory` applies, for the same
    reason: 12 bad ids in one list is one defect, not twelve.
    """
    if isinstance(node, dict):
        for key, child in node.items():
            here = f"{path}.{key}"
            if key in slots:
                for value in (child if isinstance(child, list) else [child]):
                    if isinstance(value, str) and value.strip():
                        yield here, key, value
            # Recurse regardless: an identifier-ranged key may itself hold an
            # inlined object elsewhere in the tree, and a nested `id` under a
            # `publisher` object is still an identifier.
            yield from walk_identifiers(child, slots, here)
    elif isinstance(node, list):
        for item in node:
            yield from walk_identifiers(item, slots, f"{path}[]")


def audit_record(path: Path, prefixes: set[str],
                 slots: set[str] | None = None) -> dict[str, Any]:
    """Classify every identifier-ranged value in one record."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    counts = {URI: 0, URI_UNVERIFIED: 0, CURIE_DECLARED: 0,
              CURIE_UNDECLARED: 0, BARE: 0}
    offenders: list[dict[str, str]] = []
    for slot_path, slot, value in walk_identifiers(doc, slots or {"id"}):
        kind = classify(value, prefixes)
        counts[kind] += 1
        if kind in UNRESOLVABLE:
            offenders.append({"slot_path": slot_path, "slot": slot,
                              "value": value, "kind": kind})
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
    totals = {URI: 0, URI_UNVERIFIED: 0, CURIE_DECLARED: 0,
              CURIE_UNDECLARED: 0, BARE: 0}
    for rec in records:
        for kind, n in rec["counts"].items():
            totals[kind] += n
    total = sum(totals.values())
    unresolvable = sum(totals[k] for k in UNRESOLVABLE)
    # Per-slot, because the remedies are not the same size. A slot that is
    # wholly unresolvable is a modelling error — `unit` was ranged
    # `uriorcurie` and only ever holds `%` — while a slot that is mostly fine
    # with a few strays is a data-entry problem.
    by_slot: dict[str, int] = {}
    for rec in records:
        for off in rec["offenders"]:
            by_slot[off.get("slot", "id")] = by_slot.get(off.get("slot", "id"), 0) + 1
    return {
        "records_scanned": len(records),
        "records_with_unresolvable_ids": len([r for r in records
                                              if r["offenders"]]),
        "identifiers": total,
        "counts": totals,
        "unresolvable": unresolvable,
        "unresolvable_share": (unresolvable / total) if total else 0.0,
        "unresolvable_by_slot": dict(sorted(by_slot.items(),
                                            key=lambda kv: -kv[1])),
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
    slots = uriorcurie_slots(schema_path)
    files = sorted(p for p in root.rglob("*_d4d.yaml")
                   if include_archived or "ATTIC" not in p.parts)
    files += sorted(p for p in root.rglob("*_d4d_core.yaml")
                    if include_archived or "ATTIC" not in p.parts)

    records: list[dict[str, Any]] = []
    unreadable: list[dict[str, str]] = []
    for f in files:
        try:
            records.append(audit_record(f, prefixes, slots))
        except Exception as exc:  # noqa: BLE001 — a record that will not parse
            unreadable.append({"path": str(f),                # is a finding too
                               "error": f"{type(exc).__name__}: {exc}"})

    report = summarize(records, len(prefixes), unreadable)
    report["slots_audited"] = sorted(slots)
    return report
