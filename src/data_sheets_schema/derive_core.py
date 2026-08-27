"""Derive the core record from the audited full record (#694).

`CoreDataset` is by definition a subset of `Dataset`, and on the 2026-08-24
agentic arm a deterministic projection reproduced 98.2% of every core
record's slot values byte-for-byte; the remainder was exactly the two
CoreDataset-only slots. So the core need not be *generated* at all — a model
call reconciled after the fact, which on the API arm left 0–18 pair errors and
the #675 spelling splits — it can be *derived*:

1. every schema-identical shared slot (derived at runtime from `Dataset` and
   `CoreDataset` with SchemaView — the same list the pair checker uses) is
   copied from the full record;
2. `resources` is projected by the pair checker's existing rule (matched by
   id, full-only nested slots dropped), recursively;
3. `distributions` (CoreDataset-only) is built from `file_collections` by
   copying the slots `CoreDistribution` and `FileCollection` share
   (`compression, conforms_to, conforms_to_standard, description, id, name,
   notes, path, source_caveats`) and dropping the rest (`collection_type`,
   `file_count`, `total_bytes`, …), at the top level and inside each
   projected resource;
4. `dialect` (CoreDataset-only, `FormatDialect`) has no full-record source and
   is not derived. Two of twelve v5 cores carried one; the full record has no
   slot for it, so a derived core cannot claim it without inventing it.
5. the per-record slots (`conforms_to_class`, `conforms_to_schema`) name the
   core class and schema.

The derivation is a pure function of the full record and the two schemas; it
introduces no fact. Pair consistency holds by construction, and the core's
evidence trail is the full record's. `derivation_facts()` is what a
provenance record carries to say so.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any, Mapping

import yaml

CORE_CLASS = "CoreDataset"
CORE_SCHEMA_REL = "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"

#: The one CoreDataset-only slot with no full-record source. Named so the
#: record can say it was left absent by rule rather than overlooked.
NOT_DERIVABLE = ("dialect",)

RULE = ("shared slots copied from the full record; resources projected by id "
        "with full-only nested slots dropped; distributions built from "
        "file_collections over the slots CoreDistribution and FileCollection "
        "share; dialect not derived (no full-record source)")


def _distribution_slots(pair_schema) -> list[str]:
    core = {s.name for s in pair_schema.core_view.class_induced_slots("CoreDistribution")}
    full = {s.name for s in pair_schema.full_view.class_induced_slots("FileCollection")}
    return sorted(core & full)


def _project_collections(items: Any, slots: list[str]) -> list[dict[str, Any]] | None:
    if not isinstance(items, list):
        return None
    out = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        out.append({k: copy.deepcopy(item[k]) for k in slots if k in item})
    return out or None


def _add_distributions(node: dict[str, Any], source: Mapping[str, Any],
                       slots: list[str]) -> None:
    """Write `distributions` into `node` from `source["file_collections"]`,
    then recurse into projected resources against the full record's
    corresponding resources (matched by id)."""
    dists = _project_collections(source.get("file_collections"), slots)
    if dists:
        node["distributions"] = dists
    full_res = {r.get("id"): r for r in source.get("resources") or []
                if isinstance(r, Mapping) and isinstance(r.get("id"), str)}
    for res in node.get("resources") or []:
        if isinstance(res, Mapping) and res.get("id") in full_res:
            _add_distributions(res, full_res[res["id"]], slots)


def derive_core(full: Mapping[str, Any], pair_schema=None) -> dict[str, Any]:
    """The core record implied by `full`, as a dict without header lines."""
    from data_sheets_schema.d4d_pair_consistency import (load_pair_schema,
                                                        synchronize_core_data)
    ps = pair_schema or load_pair_schema()
    core = synchronize_core_data(full, {}, ps)
    _add_distributions(core, full, _distribution_slots(ps))
    core["conforms_to_class"] = CORE_CLASS
    core["conforms_to_schema"] = CORE_SCHEMA_REL
    # Slot order as the core schema declares it, so two derivations of one
    # full record are byte-identical and a diff against a generated core is
    # readable.
    order = [s.name for s in ps.core_view.class_induced_slots(CORE_CLASS)]
    return {k: core[k] for k in order if k in core} | {k: v for k, v in core.items() if k not in order}


def derivation_facts(full_path: Path, pair_schema=None) -> dict[str, Any]:
    """What a provenance record says about a derived core (#694)."""
    from data_sheets_schema.d4d_pair_consistency import load_pair_schema
    ps = pair_schema or load_pair_schema()
    return {
        "derived": True,
        "rule": RULE,
        "from": {"path": str(full_path),
                 "md5": hashlib.md5(full_path.read_bytes()).hexdigest()},
        "identity_slots": len(ps.identity_slots),
        "projected_slots": list(ps.projected_slots),
        "distribution_slots": _distribution_slots(ps),
        "not_derived": list(NOT_DERIVABLE),
    }


def _header_lines(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        if line.startswith("#"):
            out.append(line)
        elif line.strip():
            break
    return out


def core_header(full_text: str, full_path: Path) -> list[str]:
    """The core's header, derived from the full record's: the same identity
    lines, with the method line saying what this record is and a `Sources:`
    line naming the full record it was projected from (the provenance guard
    reads it)."""
    out = []
    for line in _header_lines(full_text):
        if line.startswith("# D4D Datasheet for"):
            out.append(line.replace("# D4D Datasheet for", "# D4D Core Datasheet for", 1))
        elif line.startswith("# Generation Method:"):
            out.append("# Generation Method: derived by projection from the full record (#694)")
        elif line.startswith("# Schema:"):
            out.append(f"# Schema: {CORE_SCHEMA_REL}")
            out.append(f"# Sources: {full_path}")
        else:
            out.append(line)
    return out


def core_text(full_path: Path, pair_schema=None) -> tuple[str, dict[str, Any]]:
    """The derived core as text (header + YAML) and its derivation facts."""
    text = full_path.read_text(encoding="utf-8")
    full = yaml.safe_load(text) or {}
    core = derive_core(full, pair_schema)
    body = yaml.safe_dump(core, sort_keys=False, allow_unicode=True, width=88)
    header = "\n".join(core_header(text, full_path))
    return (header + "\n\n" if header else "") + body, derivation_facts(full_path, pair_schema)


def write_core(full_path: Path, core_path: Path, pair_schema=None) -> dict[str, Any]:
    """Derive and write the core beside its full record; return the facts."""
    text, facts = core_text(full_path, pair_schema)
    core_path.parent.mkdir(parents=True, exist_ok=True)
    core_path.write_text(text, encoding="utf-8")
    return facts
