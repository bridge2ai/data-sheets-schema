"""Offline, versioned nested support targets (#3342).

This is a request-building contract, not a calibrated judge or an executor.
It deliberately does not read v2 caches, initialize providers, or change v2.
Relationship edges and attribute values are separate measurement strata.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

import yaml

INSTRUMENT = "support_targets v3 draft (#3342)"
AXIS = "grounding_v3"
POLICY = "relationship_edge_and_attribute_value_v1"
KINDS = ("relationship_edge", "attribute_value")
DECLARATIONS = ("attributed_to", "claim_status", "source_status")
IDENTITY = ("id", "name", "title", "doi", "version")
BLOCKERS = ("independent_empirical_calibration_3343", "paid_run_authorization",
            "nested_planner_integration_3342", "instrument_review_3342")

SYSTEM = """Judge the specified assertion facet against the supplied source documents.
The target is identified by its exact document pointer, class/slot chain and
specification. value_yaml preserves native YAML dates/timestamps; the JSON value
preview tags those temporal values rather than turning them into quoted strings.
For relationship_edge, judge only whether this entity/reference
occupies the relationship the containing slot asserts; do not grade all its
descendant attributes again. For attribute_value, judge this value in its owning
field's meaning. Context, sibling prose and declarations are claims under test,
never evidence. Ancestor context does not establish that collection metadata
applies to a resource. Follow governing source headings, modal verbs, dates and
document boundaries. Attribution written in the value's prose also counts;
matching text elsewhere does not establish the named source supports it.
Publication status and derivation identifiers are not source citations.
Choose exactly one verdict, the first applicable to this facet:
contradicted (explicit incompatible fact, other than status);
status_shifted (planned/instruction/capability/in-progress made current/applied);
relationship_unsupported (fact exists but not in the asserted role);
wrong_document (fact exists but not in the explicitly attributed document);
unsupported (fact not stated); partially_supported (only part stated);
supported (stated in this role, status and attributed source).
A text value may contain several clauses: this precedence yields one verdict,
not a claim that every clause was independently measured. Do not judge unrelated
facets, infer that an unsupported fact is false, or treat a caveat as permission
for an unsupported structured role. Reply with exactly a JSON object containing
verdict and a nonempty reason, with no other keys. This draft is uncalibrated.
"""


def _canonical(value: Any) -> str:
    def temporal(item):
        if isinstance(item, datetime):
            return {"$yaml_type": "datetime", "value": item.isoformat(timespec="microseconds")}
        if isinstance(item, date):
            return {"$yaml_type": "date", "value": item.isoformat()}
        raise ValueError(f"unsupported value type: {type(item).__name__}")
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False, default=temporal)


def _typed(value: Any) -> list:
    """Tag every node so native dates, strings and tag-like maps stay distinct."""
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        return ["float", value.hex()]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat(timespec="microseconds")]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, list):
        return ["list", [_typed(v) for v in value]]
    if isinstance(value, dict):
        return ["map", [[k, _typed(v)] for k, v in sorted(value.items())]]
    raise ValueError(f"unsupported value type: {type(value).__name__}")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(_typed(value)).encode("utf-8")).hexdigest()


def _token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def pointer_tokens(pointer: str) -> list[str]:
    """Strict RFC 6901 string form (not URI fragment or wildcard form)."""
    if not isinstance(pointer, str) or pointer and not pointer.startswith("/"):
        raise ValueError("pointer must be an RFC 6901 string starting with /, or empty")
    if re.search(r"~(?![01])", pointer):
        raise ValueError("invalid JSON Pointer escape")
    return [s.replace("~1", "/").replace("~0", "~") for s in pointer.split("/")[1:]]


def resolve_pointer(document: Any, pointer: str) -> Any:
    """Resolve without coercing object keys, negative indices or list appends."""
    value = document
    for token in pointer_tokens(pointer):
        if isinstance(value, dict):
            if token not in value:
                raise ValueError(f"missing mapping key at {pointer!r}")
            value = value[token]
        elif isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ValueError(f"invalid array index at {pointer!r}")
            index = int(token)
            if index >= len(value):
                raise ValueError(f"array index out of range at {pointer!r}")
            value = value[index]
        else:
            raise ValueError(f"pointer descends through a scalar at {pointer!r}")
    return value


class _UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str):
            raise ValueError("record mapping keys must be strings (YAML merges unsupported)")
        if key in result:
            raise ValueError(f"duplicate record key {key!r}")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _validate_json(value: Any, *, max_nodes: int, max_depth: int) -> None:
    count = 0
    active = set()

    def visit(v, depth):
        nonlocal count
        count += 1
        if count > max_nodes or depth > max_depth:
            raise ValueError("record exceeds explicit traversal limits")
        if isinstance(v, (dict, list)):
            if id(v) in active:
                raise ValueError("cyclic record values are unsupported")
            active.add(id(v))
            if isinstance(v, dict) and any(not isinstance(k, str) for k in v):
                raise ValueError("record mapping keys must be strings")
            for child in v.values() if isinstance(v, dict) else v:
                visit(child, depth + 1)
            active.remove(id(v))
        elif v is not None and not isinstance(v, (str, bool, int, float, date, datetime)):
            raise ValueError(f"unsupported record value type: {type(v).__name__}")
        elif isinstance(v, float) and not math.isfinite(v):
            raise ValueError("nonfinite record numbers are unsupported")
    visit(value, 0)


def _populated(value):
    return value is not None and value != "" and value != [] and value != {}


@dataclass(frozen=True)
class NestedSupportSchema:
    """Immutable captured specifications, including induced nested slot text.

    The vocabulary is an explicit caller snapshot; no ambient profile is read.
    Missing required values_from vocabularies block affected targets.
    """
    payload_json: str

    @property
    def digest(self):
        return hashlib.sha256(self.payload_json.encode("utf-8")).hexdigest()

    def to_dict(self):
        return json.loads(self.payload_json)

    @classmethod
    def from_schema(cls, path: Path, *, root_class: str = "Dataset",
                    vocabulary: dict | None = None):
        from linkml_runtime.dumpers import json_dumper
        from data_sheets_schema.schema_snapshot import capture_schema
        from data_sheets_schema.schema_view import shared_view
        captured = capture_schema(path, strict=True)
        view = shared_view(path, snapshot=captured)
        if view.get_class(root_class) is None:
            raise ValueError(f"unknown root class {root_class!r}")
        classes, enums, pending = {}, {}, [root_class]
        while pending:
            name = pending.pop()
            if name in classes:
                continue
            definition = view.get_class(name)
            slots = {}
            classes[name] = {"definition": json.loads(json_dumper.dumps(definition)), "slots": slots}
            for slot in view.class_induced_slots(name):
                raw = json.loads(json_dumper.dumps(slot))
                rng = str(slot.range) if slot.range else None
                target = view.get_class(rng) if rng else None
                slots[str(slot.name)] = {"definition": raw, "range_class": bool(target),
                                         "inline": bool(target and view.is_inlined(slot))}
                if target:
                    pending.append(rng)
                enum = view.get_enum(rng) if rng else None
                if enum:
                    enums[rng] = json.loads(json_dumper.dumps(enum))
        sources = sorted((name, hashlib.sha256(data).hexdigest())
                         for name, _path, data in captured.sources)
        payload = {"root_class": root_class, "schema_sources": sources,
                   "classes": classes, "enums": enums, "vocabulary": vocabulary or {}}
        return cls(_canonical(payload))


@dataclass(frozen=True)
class SupportTarget:
    payload_json: str

    def to_dict(self):
        """A fresh copy; callers cannot modify the captured request identity."""
        return json.loads(self.payload_json)

    @property
    def pointer(self):
        return self.to_dict()["pointer"]

    @property
    def kind(self):
        return self.to_dict()["kind"]

    @property
    def digest(self):
        return hashlib.sha256(self.payload_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TargetInventory:
    targets: tuple[SupportTarget, ...]
    blocked_json: str
    artifact_json: str

    def target(self, pointer: str, *, kind: str) -> SupportTarget:
        pointer_tokens(pointer)
        for target in self.targets:
            if target.pointer == pointer and target.kind == kind:
                return target
        raise ValueError(f"no eligible {kind!r} target at {pointer!r}")

    def to_dict(self):
        counts = Counter(t.kind for t in self.targets)
        return {"instrument": INSTRUMENT, "axis": AXIS, "policy": POLICY,
                "artifact": json.loads(self.artifact_json),
                "eligible_by_kind": {k: counts[k] for k in KINDS},
                "blocked": json.loads(self.blocked_json),
                "readiness_blockers": list(BLOCKERS),
                "fitness_basis": "top_level_only; many nested targets map to one parent field",
                "targets": [t.to_dict() for t in self.targets]}


def inventory_targets(record_bytes: bytes, specification: NestedSupportSchema, *,
                      artifact_kind: str, max_nodes: int = 100_000,
                      max_depth: int = 64, max_input_bytes: int = 4_000_000,
                      max_inventory_bytes: int = 64_000_000) -> TargetInventory:
    """Capture a deterministic inventory from exact input bytes, without I/O.

    No wrappers are unwrapped: every pointer addresses these exact bytes.
    Malformed shapes and unsupported schema constructs are explicit blockers.
    Fitness mappings refer to the original document's top-level field only.
    """
    if artifact_kind not in {"full", "core", "collection"}:
        raise ValueError("artifact_kind must be full, core or collection")
    limits = (max_nodes, max_depth, max_input_bytes, max_inventory_bytes)
    if any(type(n) is not int or n < 1 for n in limits):
        raise ValueError("traversal limits must be positive integers")
    if not isinstance(record_bytes, bytes) or len(record_bytes) > max_input_bytes:
        raise ValueError("record must be bytes within max_input_bytes")
    document = yaml.load(record_bytes, Loader=_UniqueLoader)
    _validate_json(document, max_nodes=max_nodes, max_depth=max_depth)
    if not isinstance(document, dict):
        raise ValueError("record must be a mapping of the selected root class")
    schema = specification.to_dict()
    classes = schema["classes"]
    root_class = schema["root_class"]
    artifact = {"input_sha256": hashlib.sha256(record_bytes).hexdigest(),
                "kind": artifact_kind, "root_class": root_class,
                "root_fields": sorted(document), "specification_sha256": specification.digest,
                "max_nodes": max_nodes, "max_depth": max_depth,
                "max_input_bytes": max_input_bytes, "max_inventory_bytes": max_inventory_bytes}
    targets, blocked = [], []
    rendered_bytes = 0

    def block(pointer, code):
        blocked.append({"pointer": pointer, "code": code})

    def declarations(value, pointer):
        result = {}
        if isinstance(value, dict):
            for k, v in value.items():
                here = pointer + "/" + _token(k)
                if k in DECLARATIONS:
                    result[here] = v
                result.update(declarations(v, here))
        elif isinstance(value, list):
            for i, v in enumerate(value):
                result.update(declarations(v, pointer + f"/{i}"))
        return result

    def emit(pointer, kind, value, owner, owner_pointer, owner_class, chain, ancestors):
        nonlocal rendered_bytes
        # Complete nearest mapping preserves anonymous subjects and sibling
        # qualifiers. Ancestors carry identity/path only; no metadata inheritance.
        declared = declarations(value, pointer)
        for k in DECLARATIONS:
            if k in owner:
                declared[owner_pointer + "/" + _token(k)] = owner[k]
        selected = chain[-1]
        spec = {"class_slot_chain": chain, "owning_class": classes[owner_class]["definition"],
                "slot": selected["slot"], "range_class": selected["range_class"],
                "enums": schema["enums"], "vocabulary": schema["vocabulary"]}
        context = {"containing_entity": {"pointer": owner_pointer, "class": owner_class,
                                          "value": owner, "sha256": _digest(owner),
                                          "value_yaml": yaml.safe_dump(owner, sort_keys=True)},
                   "ancestors": ancestors, "declarations": declared,
                   "collection_metadata_inherited": False}
        first = pointer_tokens(pointer)[0]
        payload = {"instrument": INSTRUMENT, "axis": AXIS, "policy": POLICY,
                   "pointer": pointer, "kind": kind, "artifact": artifact,
                   "value": value, "value_sha256": _digest(value),
                   "value_type": _typed(value)[0], "value_yaml": yaml.safe_dump(value, sort_keys=True),
                   "specification": spec, "context": context,
                   "context_sha256": _digest(context),
                   "fitness": {"basis": "top_level_only", "mapping": "many_to_one",
                               "pointer": "/" + _token(first)}}
        encoded = _canonical(payload)
        rendered_bytes += len(encoded.encode("utf-8"))
        if rendered_bytes > max_inventory_bytes:
            raise ValueError("target context exceeds max_inventory_bytes; no partial inventory returned")
        targets.append(SupportTarget(encoded))

    def walk(entity, class_name, pointer, chain, ancestors):
        cls = classes[class_name]
        identity = {k: entity[k] for k in IDENTITY if k in entity and
                    isinstance(entity[k], (str, int, float)) and not isinstance(entity[k], bool)}
        ancestry = ancestors + [{"pointer": pointer, "class": class_name, "identity": identity}]
        for name in sorted(entity):
            value = entity[name]
            here = pointer + "/" + _token(name)
            if not _populated(value):
                continue
            entry = cls["slots"].get(name)
            if entry is None:
                block(here, "unknown_schema_slot")
                continue
            slot = entry["definition"]
            if any(slot.get(k) for k in ("any_of", "all_of", "exactly_one_of", "none_of", "designates_type")):
                block(here, "unsupported_schema_constraint_or_polymorphism")
                continue
            if any(str(v) not in schema["vocabulary"] for v in slot.get("values_from", [])):
                block(here, "missing_values_from_vocabulary")
                continue
            rng = slot.get("range")
            edge = {"owner_class": class_name, "slot": slot,
                    "range_class": classes[rng]["definition"] if entry["range_class"] else None}
            next_chain = chain + [edge]
            many = bool(slot.get("multivalued"))
            if many != isinstance(value, list):
                block(here, "unsupported_keyed_map_or_cardinality")
                continue
            members = list(enumerate(value)) if many else [(None, value)]
            for index, member in members:
                path = here + f"/{index}" if index is not None else here
                if not _populated(member):
                    block(path, "unpopulated_list_member")
                    continue
                if entry["range_class"]:
                    if entry["inline"]:
                        if not isinstance(member, dict):
                            block(path, "inline_class_requires_mapping")
                            continue
                        emit(path, "relationship_edge", member, entity, pointer, class_name,
                             next_chain, ancestors)
                        walk(member, rng, path, next_chain, ancestry)
                    elif isinstance(member, str):
                        emit(path, "relationship_edge", member, entity, pointer, class_name,
                             next_chain, ancestors)
                    else:
                        block(path, "reference_requires_string_no_dereference")
                elif isinstance(member, (dict, list)):
                    block(path, "scalar_slot_has_container")
                else:
                    emit(path, "attribute_value", member, entity, pointer, class_name,
                         next_chain, ancestors)

    walk(document, root_class, "", [], [])
    return TargetInventory(tuple(targets), _canonical(blocked), _canonical(artifact))


def render_request(target: SupportTarget, *, bundle: str, model: str,
                   max_tokens: int = 8000) -> dict:
    """Pure draft provider arguments; no client, retry, cache or execution path."""
    if not isinstance(bundle, str) or not bundle.strip():
        raise ValueError("source bundle text is required")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("explicit model is required")
    if type(max_tokens) is not int or max_tokens < 1:
        raise ValueError("max_tokens must be a positive integer")
    return {"model": model, "max_tokens": max_tokens, "temperature": None,
            "system": SYSTEM, "messages": [{"role": "user", "content": [
                {"type": "text", "text": "# Source documents\n\n" + bundle,
                 "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "# Exact assertion target and untrusted record context\n\n"
                 + target.payload_json}]}]}


def request_identity(target: SupportTarget, *, bundle: str, model: str,
                     max_tokens: int = 8000) -> str:
    """All rendered arguments participate; this is not permission to reuse v2."""
    return _digest(render_request(target, bundle=bundle, model=model, max_tokens=max_tokens))
