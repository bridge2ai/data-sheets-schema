"""Derive the core record from the audited full record (#694).

`CoreDataset` is by definition a subset of `Dataset`, and on the 2026-08-24
agentic arm a deterministic projection reproduced 98.5% of every core
record's top-level slot values; the differences were confined to
`distributions` and `resources`. So the core need not be *generated* at all — a
model call reconciled after the fact, which on the API arm left 0–18 pair
errors and the #675 spelling splits — it can be *derived*:

1. every schema-identical shared slot (derived at runtime from `Dataset` and
   `CoreDataset` with SchemaView — the same list the pair checker uses) is
   copied from the full record;
2. `resources` is projected by the pair checker's existing rule (matched by
   id, full-only nested slots dropped), recursively;
3. `distributions` (CoreDataset-only) is built from `file_collections`: one
   entry per collection over the slots `CoreDistribution` and `FileCollection`
   share, with `total_bytes` carried as `bytes` (the same fact,
   dcat:byteSize), and one entry per `File` under the collection's
   `resources` over the slots `CoreDistribution` and `File` share — which is
   where the full record keeps `bytes`, `md5`, `sha256`, `format`,
   `media_type`, `encoding`. The #704 review found the first version dropped
   all of these (34 file-level hashes per CM4AI record); they are facts the
   full record states and the core must carry;
4. `dialect` (CoreDataset-only, `FormatDialect`) is derived from the `File`
   entries' `dialect` when they agree on exactly one value, and left absent
   otherwise — the full record has no dataset-level dialect slot, so a value
   the files do not agree on cannot be claimed;
5. the per-record slots (`conforms_to_class`, `conforms_to_schema`) name the
   core class and schema.

**What is deliberately lost.** The generated core phase was allowed to fill
core fields from the bundle that the full record left empty, and on the API
arm it did: core-only top-level content (~6.6 KB across the 12 22c records),
distribution-level `notes`, and the precision splits #675 counts. A derived
core cannot carry any of it, by design — a bundle-supported fact the full
lacks belongs in the full, added by the audit phase's back-port, from which
the core then inherits it. That is the trade: no fact enters through a path
the full record's evidence trail does not cover.

The derivation is a pure function of the full record and the two schemas.
Pair consistency holds by construction. `derivation_facts()` is what a
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

#: Slots derived only conditionally, so the record can say why one is absent.
CONDITIONAL = {"dialect": "derived only when every File-level dialect in the "
                          "full record agrees on one value"}

RULE = ("shared slots copied from the full record; resources projected by id "
        "with full-only nested slots dropped; distributions built from "
        "file_collections (one per collection over the shared slots, "
        "total_bytes as bytes) and from each collection's File entries (one "
        "per file over the slots CoreDistribution and File share); dialect "
        "from the File entries when they agree on one value, else absent")


def _shared(pair_schema, core_cls: str, full_cls: str) -> list[str]:
    core = {s.name for s in pair_schema.core_view.class_induced_slots(core_cls)}
    full = {s.name for s in pair_schema.full_view.class_induced_slots(full_cls)}
    return sorted(core & full)


def _distribution_slots(pair_schema) -> dict[str, list[str]]:
    return {"collection": _shared(pair_schema, "CoreDistribution", "FileCollection"),
            "file": _shared(pair_schema, "CoreDistribution", "File")}


def _entry(item: Mapping[str, Any], slots: list[str]) -> dict[str, Any]:
    return {k: copy.deepcopy(item[k]) for k in slots if k in item}


def _project_collections(items: Any, slots: dict[str, list[str]]) -> list[dict[str, Any]] | None:
    """One distribution per collection, then one per File it lists."""
    if not isinstance(items, list):
        return None
    out = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        entry = _entry(item, slots["collection"])
        if "bytes" not in entry and item.get("total_bytes") is not None:
            entry["bytes"] = copy.deepcopy(item["total_bytes"])
        if entry:
            out.append(entry)
        for f in item.get("resources") or []:
            if isinstance(f, Mapping):
                fe = _entry(f, slots["file"])
                if fe:
                    out.append(fe)
    return out or None


def _add_distributions(node: dict[str, Any], source: Mapping[str, Any],
                       slots: dict[str, list[str]]) -> None:
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


def _file_dialects(source: Mapping[str, Any]) -> list[Any]:
    out = []
    for coll in source.get("file_collections") or []:
        if isinstance(coll, Mapping):
            for f in coll.get("resources") or []:
                if isinstance(f, Mapping) and f.get("dialect"):
                    out.append(f["dialect"])
    return out


def derive_core(full: Mapping[str, Any], pair_schema=None) -> dict[str, Any]:
    """The core record implied by `full`, as a dict without header lines."""
    from data_sheets_schema.d4d_pair_consistency import (load_pair_schema,
                                                        synchronize_core_data)
    ps = pair_schema or load_pair_schema()
    core = synchronize_core_data(full, {}, ps)
    _add_distributions(core, full, _distribution_slots(ps))
    dialects = _file_dialects(full)
    if dialects and all(d == dialects[0] for d in dialects):
        core["dialect"] = copy.deepcopy(dialects[0])
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
        "conditional": dict(CONDITIONAL),
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
    sources_written = False
    for line in _header_lines(full_text):
        if line.startswith("# D4D Datasheet for"):
            out.append(line.replace("# D4D Datasheet for", "# D4D Core Datasheet for", 1))
        elif line.startswith("# Generation Method:"):
            out.append("# Generation Method: derived by projection from the full record (#694)")
        elif line.startswith("# Schema:"):
            out.append(f"# Schema: {CORE_SCHEMA_REL}")
            out.append(f"# Sources: {full_path}")
            sources_written = True
        else:
            out.append(line)
    if not sources_written:
        # The provenance guard reads `Sources:`; it must exist whatever the
        # full record's header carried.
        out.append(f"# Schema: {CORE_SCHEMA_REL}")
        out.append(f"# Sources: {full_path}")
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
