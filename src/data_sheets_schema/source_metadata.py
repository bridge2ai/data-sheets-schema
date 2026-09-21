"""Exact registered input provenance, not dataset evidence (protocol 5).

No filesystem access or ambient registry lookup occurs here. The projection
intentionally excludes free-form curator notes, URLs and arbitrary pointers.
Its values establish declarations, not scientific truth or prose entailment.
"""
from __future__ import annotations

from datetime import date, datetime
import hashlib
import math
import re

import yaml

FIELDS = frozenset({"source_type", "effective_priority", "priority_basis", "captured_at", "superseded_by"})
ASSERTION_KEYS = frozenset({"provenance", "sha256", "source_id", "source", "field", "value"})
UNRANKED = 99  # The established source_priority effective fallback, not a declared tier.


class _Loader(yaml.SafeLoader):
    """Reject ambiguous mappings, including implicit YAML merge precedence."""

    def construct_mapping(self, node, deep=False):
        out = {}
        for key_node, value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise ValueError("source manifest merge keys are ambiguous authority")
            key = self.construct_object(key_node, deep=deep)
            try:
                if key in out:
                    raise ValueError("source manifest has duplicate mapping keys")
                out[key] = self.construct_object(value_node, deep=deep)
            except TypeError as exc:
                raise ValueError("source manifest has an unusable mapping key") from exc
        return out


def _finite(value, ancestors=frozenset()):
    if isinstance(value, (dict, list)):
        if id(value) in ancestors:
            raise ValueError("source manifest cannot contain cycles")
        ancestors = ancestors | {id(value)}
        for child in (list(value.keys()) + list(value.values()) if isinstance(value, dict) else value):
            _finite(child, ancestors)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("source manifest cannot contain nonfinite numbers")


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"source manifest {label} must be nonempty text")
    return value


def _tier(value):
    if type(value) is not int or value <= 0:
        raise ValueError("source manifest priority must be an exact positive integer")
    return value


def _captured(value):
    if isinstance(value, (date, datetime)):
        value = value.isoformat()
    if not isinstance(value, str):
        raise ValueError("captured_at must be an ISO date or datetime")
    # An arbitrary free-form note cannot enter the authority through this field.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        date.fromisoformat(value)
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?", value):
        datetime.fromisoformat(value)
    else:
        raise ValueError("captured_at must be an ISO date or datetime")
    return value


def projection(raw: bytes | str, project: str) -> dict:
    """Project a caller-selected manifest, binding its exact UTF-8 bytes.

    Explicit source priority overrides the source-type table. Unranked entries
    receive effective_priority 99, just as source_priority.priority_of does.
    Source order remains the declared order; it does not break tied priorities.
    """
    if not isinstance(raw, (bytes, str)):
        raise ValueError("source manifest authority must be exact bytes or text")
    encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
    text = encoded.decode("utf-8")
    _text(project, "selected project")
    data = yaml.load(text, Loader=_Loader)
    _finite(data)
    if not isinstance(data, dict) or not isinstance(data.get("projects"), dict):
        raise ValueError("source manifest must declare projects")
    if project not in data["projects"]:
        raise ValueError("selected project is not declared by the source manifest")
    selected = data["projects"][project]
    sources = selected.get("sources") if isinstance(selected, dict) else selected
    if not isinstance(sources, list) or not sources:
        raise ValueError("selected project needs a nonempty source list")
    table = data.get("source_priority", {})
    if not isinstance(table, dict):
        raise ValueError("source_priority must be a mapping")
    tiers = {}
    for tier, types in table.items():
        _tier(tier)
        if not isinstance(types, list):
            raise ValueError("source priority tiers must contain source-type lists")
        for source_type in types:
            _text(source_type, "source type")
            if source_type in tiers:
                raise ValueError("source type has duplicate or ambiguous priority assignments")
            tiers[source_type] = tier
    rows, ids, names = [], set(), set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("selected source must be a mapping")
        sid = _text(source.get("id"), "source ID")
        name = _text(source.get("processed_file"), "processed-file source")
        source_type = _text(source.get("source_type"), "source type")
        if sid in ids or name in names:
            raise ValueError("selected project has duplicate source IDs or processed-file sources")
        ids.add(sid)
        names.add(name)
        priority = (_tier(source["priority"]) if "priority" in source
                    else tiers.get(source_type, UNRANKED))
        row = {"source_id": sid, "source": name, "source_type": source_type,
               "effective_priority": priority,
               "priority_basis": ("source_override" if "priority" in source else
                                  "source_type" if source_type in tiers else "unranked")}
        if "captured_at" in source:
            row["captured_at"] = _captured(source["captured_at"])
        if "superseded_by" in source:
            row["superseded_by"] = _text(source["superseded_by"], "supersession target")
        rows.append(row)
    links = {row["source_id"]: row["superseded_by"] for row in rows if "superseded_by" in row}
    for sid in links:
        seen, current = set(), sid
        while current in links:
            if current in seen or links[current] not in ids:
                raise ValueError("supersession must be acyclic and target a selected-project source")
            seen.add(current)
            current = links[current]
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "project": project, "sources": rows}


def check_assertion(entry, *, authority: dict | None) -> None:
    """Raise ValueError unless this exact typed declaration is in the projection."""
    if not isinstance(entry, dict) or set(entry) != ASSERTION_KEYS:
        raise ValueError("provenance assertion needs exactly provenance, sha256, source_id, source, field and value")
    if entry["provenance"] != "source_manifest" or authority is None:
        raise ValueError("provenance assertion requires registered source-manifest authority")
    if entry["sha256"] != authority["sha256"]:
        raise ValueError("provenance assertion does not bind the exact source-manifest bytes")
    if not isinstance(entry["field"], str) or entry["field"] not in FIELDS:
        raise ValueError("provenance assertion field is outside the structural metadata whitelist")
    if not isinstance(entry["source_id"], str) or not isinstance(entry["source"], str):
        raise ValueError("provenance assertion must name an exact source ID and processed-file source")
    row = next((row for row in authority["sources"]
                if row["source_id"] == entry["source_id"] and row["source"] == entry["source"]), None)
    if row is None or entry["field"] not in row:
        raise ValueError("provenance assertion does not name selected source metadata")
    value = row[entry["field"]]
    if type(entry["value"]) is not type(value) or entry["value"] != value:
        raise ValueError("provenance assertion contradicts the exact typed metadata value")
