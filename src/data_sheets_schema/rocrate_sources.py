"""Root-scoped RO-Crate lookup and lossless mapping-source evidence.

A Dataset selector in the static mapper describes the record's root, never
the first child that happens to carry a value. Member assertions are retained
separately for audit; they cannot fill a missing root property.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Any
from urllib.parse import urlsplit

GRAPH_RE = re.compile(
    r"^@graph\[\?@type='(?P<type>[^']+)'\]\['(?P<prop>[^']+)'\]"
    r"(?:\[\?name='(?P<name>[^']+)'\]\['(?P<prop2>[^']+)'\])?$"
)
NOT_A_PATH = re.compile(r"^(N/A|\s*|.*\s+MIME\s+parameter|d4d:.*)$", re.IGNORECASE)

# Each adapter declares every root key it may read. Referenced IRB records
# are included separately; no other graph entity supplies a missing key.
RULE_KEYS = {
    "human_subjects": ("humanSubjectResearch", "humanSubjects", "humanSubjectExemption", "irb", "irbProtocolId"),
    "imputation": ("rai:dataImputationProtocol", "rai:imputationProtocol"),
    "typed_parents": ("isPartOf",),
}


def _types_of(entity: dict) -> list:
    value = entity.get("@type")
    return value if isinstance(value, list) else ([] if value is None else [value])


def _type_matches(entity: dict, wanted: str) -> bool:
    return any(t == wanted or re.search(rf"[#/:]{re.escape(wanted)}$", str(t))
               for t in _types_of(entity))


def present(value: Any) -> bool:
    """False and zero are source values; null and empty containers are not."""
    return value is not None and value != "" and value != [] and value != {}


def select_root(graph: list[dict]) -> tuple[dict | None, str]:
    entities = [e for e in graph if isinstance(e, dict)]
    descriptors = []
    for entity in entities:
        identifier = entity.get("@id")
        if not isinstance(identifier, str):
            continue
        try:
            basename = urlsplit(identifier).path.rsplit("/", 1)[-1]
        except ValueError:
            continue
        if basename == "ro-crate-metadata.json":
            descriptors.append(entity)
    about = [e["about"] for e in descriptors if "about" in e]
    if about:
        refs = []
        for value in about:
            items = value if isinstance(value, list) else [value]
            if not items:
                return None, "metadata descriptor has an empty about reference"
            for item in items:
                ref = item.get("@id") if isinstance(item, dict) else item
                if not isinstance(ref, str) or not ref:
                    return None, "metadata descriptor has an invalid about reference"
                if ref not in refs:
                    refs.append(ref)
        if len(refs) != 1:
            return None, "metadata descriptors disagree about the crate root"
        targets = [e for e in entities if e.get("@id") == refs[0]]
        if len(targets) != 1:
            return None, "metadata about reference is unresolved or has duplicate entity IDs"
        root = targets[0]
        if not (_type_matches(root, "Dataset") or _type_matches(root, "ROCrate")):
            return None, "metadata about target is not typed Dataset or ROCrate"
        return root, "metadata descriptor about reference"

    # Conventional './' is explicit identity, not graph position. Duplicate
    # identities or two conventional roots are ambiguous even if values agree.
    conventional = [e for e in entities if e.get("@id") in ("./", ".")
                    and (_type_matches(e, "Dataset") or _type_matches(e, "ROCrate"))]
    if conventional:
        if len(conventional) != 1:
            return None, "multiple conventional crate roots"
        candidate = conventional[0]
        if sum(e.get("@id") == candidate["@id"] for e in entities) != 1:
            return None, "conventional root has duplicate entity IDs"
        return candidate, "conventional root identifier"
    for kind in ("ROCrate", "Dataset"):
        candidates = [e for e in entities if _type_matches(e, kind)]
        if len(candidates) > 1:
            return None, f"multiple {kind} entities without an explicit root reference"
        if candidates:
            candidate = candidates[0]
            if candidate.get("@id") is not None and sum(
                    e.get("@id") == candidate["@id"] for e in entities) != 1:
                return None, "candidate root has duplicate entity IDs"
            return candidate, f"unique {kind} entity"
    return None, "no identifiable crate root"


def crate_root(graph: list[dict]) -> dict | None:
    return select_root(graph)[0]


def resolve_path(expr: str, graph: list[dict], root: dict | None) -> tuple[Any, str]:
    expr = (expr or "").strip()
    if NOT_A_PATH.match(expr):
        return None, "not a crate path"
    if root is None:
        return None, "no unambiguous crate root entity"
    match = GRAPH_RE.match(expr)
    if match:
        wanted, prop = match.group("type"), match.group("prop")
        if not _type_matches(root, wanted):
            return None, f"crate root is not @type={wanted}"
        value = root.get(prop)
        if match.group("name") and present(value):
            items = value if isinstance(value, list) else [value]
            found = [item.get(match.group("prop2")) for item in items
                     if isinstance(item, dict) and item.get("name") == match.group("name")
                     and present(item.get(match.group("prop2")))]
            if len(found) > 1:
                return None, f"multiple root '{prop}' entries named {match.group('name')!r}"
            if found:
                return found[0], ""
            return None, f"root '{prop}' has no nonempty named entry {match.group('name')!r}"
        return ((value, "") if present(value)
                else (None, f"crate root '{prop}' empty or absent; member values are not used"))
    if expr.startswith("@graph"):
        return None, "unsupported graph selector"
    value = root.get(expr)
    if present(value):
        return value, ""
    return None, ("root property empty" if expr in root else f"'{expr}' not present on crate root")


def crate_property(expr: str) -> str | None:
    expr = (expr or "").strip()
    if NOT_A_PATH.match(expr):
        return None
    match = GRAPH_RE.match(expr)
    if not match:
        return None if expr.startswith("@graph") else expr
    if match.group("name"):
        return f"{match.group('prop')}[?name='{match.group('name')}']['{match.group('prop2')}']"
    return match.group("prop")


def _pointer(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def source_report(graph, root, rows, fields, placement, root_note, dataset_slots):
    """Preserve original values, including deferred and member-only evidence.

    This inventories evidence, not support/recall scores. In particular, an
    inactive rule remains in the same denominator and retains its assertions.
    """
    entries = []
    root_index = next((i for i, e in enumerate(graph) if e is root), None)
    for row, result in zip(rows, [f for f in fields if f.from_table], strict=True):
        expr = (row.get("RO_Crate_JSON_Path") or "").strip()
        rule = (row.get("Mapping_Rule") or "").strip()
        match = GRAPH_RE.match(expr)
        keys = RULE_KEYS.get(rule, (match.group("prop"),) if match else
                             (() if crate_property(expr) is None else (expr,)))
        root_values, member_values, linked_values = [], [], []
        for index, entity in enumerate(graph):
            if not isinstance(entity, dict):
                continue
            if match and not rule and not _type_matches(entity, match.group("type")):
                continue
            for key in keys:
                if key not in entity:
                    continue
                value = entity[key]
                found = [(f"/@graph/{index}/{_pointer(key)}", value)]
                if match and match.group("name") and not rule:
                    items = value if isinstance(value, list) else [value]
                    found = [(f"/@graph/{index}/{_pointer(key)}" +
                              (f"/{j}" if isinstance(value, list) else "") +
                              f"/{_pointer(match.group('prop2'))}", item[match.group("prop2")])
                             for j, item in enumerate(items) if isinstance(item, dict)
                             and item.get("name") == match.group("name") and match.group("prop2") in item]
                for pointer, original in found:
                    (root_values if entity is root else member_values).append({
                        "entity_id": entity.get("@id"), "json_pointer": pointer,
                        "property": key, "value": deepcopy(original)})
        if root is not None and rule in ("human_subjects", "typed_parents"):
            key = "irb" if rule == "human_subjects" else "isPartOf"
            refs = root.get(key, [])
            refs = refs if isinstance(refs, list) else [refs]
            ids = {v.get("@id") if isinstance(v, dict) else v for v in refs
                   if isinstance(v, str) or (isinstance(v, dict) and isinstance(v.get("@id"), str))}
            for index, entity in enumerate(graph):
                if isinstance(entity, dict) and isinstance(entity.get("@id"), str) and entity["@id"] in ids:
                    linked_values.append({"entity_id": entity["@id"], "json_pointer": f"/@graph/{index}",
                                          "property": f"referenced by root {key}", "value": deepcopy(entity)})
        cls, _, slot = result.d4d_path.partition(".")
        entries.append({"rule_id": result.rule_id, "execution": result.execution,
                        "d4d_path": result.d4d_path,
                        "destination_slot": (slot if slot in dataset_slots else None)
                        if cls == "Dataset" else placement.get(cls),
                        "mapping_rule": rule, "source_expression": expr, "status": result.status,
                        "resolution_note": result.detail,
                        "root_assertions": root_values, "member_assertions": member_values,
                        "linked_assertions": linked_values})
    return {"format_version": 1,
            "root": {"id": root.get("@id") if root is not None else None,
                     "graph_index": root_index, "selection_note": root_note,
                     "properties": deepcopy(root)},
            "rows": entries}
