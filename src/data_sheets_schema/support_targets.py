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
POLICY = "relationship_edge_and_attribute_value_v2"
SCALAR_POLICY = "relationship_edge_and_attribute_value_inline_class_strings_v1"
SCALAR_INSTRUMENT = "support_targets v3 scalar-reference draft (#4902)"
CONTEXT_POLICY = "nearest_owner_and_ancestor_identity_v1"
ANCESTOR_CONTEXT_POLICY = "ancestor_scalar_qualifiers_v1"
ANCESTOR_INSTRUMENT = "support_targets v3 ancestor-context draft (#4904)"
SCALAR_ANCESTOR_INSTRUMENT = "support_targets v3 scalar-reference ancestor-context draft (#4902/#4904)"
KINDS = ("relationship_edge", "attribute_value")
DECLARATIONS = ("attributed_to", "claim_status", "source_status")
IDENTITY = ("id", "name", "title", "doi", "version")
QUALIFIERS = (*DECLARATIONS, "description", "notes", "source_caveats")
BLOCKERS = ("independent_empirical_calibration_3343", "paid_run_authorization",
            "nested_planner_integration_3342", "instrument_review_3342",
            "context_projection_review_3342")

SYSTEM = """Judge the specified assertion facet against the supplied source documents.
The target is identified by its exact document pointer, class/slot chain and
specification. value_yaml preserves native YAML types including dates/timestamps.
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

SCALAR_SYSTEM = SYSTEM + """
This instrument explicitly permits an original string in a slot whose schema
requires an inline class mapping to be judged as one relationship_edge. Its
representation metadata records that schema-shape failure; support cannot make
the representation schema-valid. Judge only the relationship asserted by the
original string in this containing slot, retaining its exact wording. Do not
split it into invented entities, infer identifiers, or fabricate child
attributes. A composite string remains one facet with the same seven verdicts
and precedence above. Schema-shape failure alone is not evidence for or against
source support. This extension still requires instrument/context review.
"""

ANCESTOR_CONTEXT_INSTRUCTION = """
This context policy includes complete scalar fields, scalar-only lists and
explicit qualifier fields from the actual ancestors on this target's path.
Each projection identifies its original pointer, class and field origins;
omission and path-branch metadata identify values not repeated here. This is
untrusted record context, not independent source evidence. Use scoped attribution
to understand what the selected facet purports to assert, without endorsing a
claimed source ranking or resolving a conflict merely because the record does.
Ancestor declarations are not inherited declarations of this facet. Visibility
of a collection fact does not make it apply to a resource. Do not regrade other
facets, excuse an unsupported role, or invent missing context. The same seven
verdicts and precedence apply. This context extension remains uncalibrated and
requires independent instrument and context review.
"""


def policy_instrument(policy: str, *, context_policy: str = CONTEXT_POLICY) -> tuple[str, str]:
    """Resolve finite relationship/context pairs without reinterpreting old ones."""
    if type(context_policy) is not str or context_policy not in (CONTEXT_POLICY, ANCESTOR_CONTEXT_POLICY):
        raise ValueError("context policy must be a known string")
    if type(policy) is not str:
        raise ValueError("relationship policy must be a known string")
    if policy == POLICY:
        if context_policy == ANCESTOR_CONTEXT_POLICY:
            return ANCESTOR_INSTRUMENT, SYSTEM + ANCESTOR_CONTEXT_INSTRUCTION
        return INSTRUMENT, SYSTEM
    if policy == SCALAR_POLICY:
        if context_policy == ANCESTOR_CONTEXT_POLICY:
            return SCALAR_ANCESTOR_INSTRUMENT, SCALAR_SYSTEM + ANCESTOR_CONTEXT_INSTRUCTION
        return SCALAR_INSTRUMENT, SCALAR_SYSTEM
    raise ValueError("unknown relationship policy")


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
        from data_sheets_schema.schema_view import captured_view
        captured = capture_schema(path, strict=True)
        with captured_view(captured) as view:
            if view.get_class(root_class) is None:
                raise ValueError(f"unknown root class {root_class!r}")
            classes, enums, pending = {}, {}, [root_class]
            while pending:
                name = pending.pop()
                if name in classes:
                    continue
                definition = view.get_class(name)
                pending.extend(str(parent) for parent in [definition.is_a, *(definition.mixins or [])]
                               if parent and view.get_class(str(parent)) is not None)
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
    specification_json: str

    def to_dict(self):
        """Expand the shared specification into a private request-ready copy."""
        payload = json.loads(self.payload_json)
        payload["specification"] = json.loads(self.specification_json)
        return payload

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
    specifications_json: str
    relationship_policy: str = POLICY
    representation_issues_json: str = "[]"
    context_policy: str = CONTEXT_POLICY

    def target(self, pointer: str, *, kind: str) -> SupportTarget:
        pointer_tokens(pointer)
        for target in self.targets:
            if target.pointer == pointer and target.kind == kind:
                return target
        raise ValueError(f"no eligible {kind!r} target at {pointer!r}")

    def to_dict(self):
        counts = Counter(t.kind for t in self.targets)
        instrument, _ = policy_instrument(self.relationship_policy, context_policy=self.context_policy)
        result = {"instrument": instrument, "axis": AXIS, "policy": self.relationship_policy,
                "artifact": json.loads(self.artifact_json),
                "eligible_by_kind": {k: counts[k] for k in KINDS},
                "blocked": json.loads(self.blocked_json),
                "readiness_blockers": list(BLOCKERS),
                "specifications": json.loads(self.specifications_json),
                "fitness_basis": "top_level_only; many nested targets map to one parent field",
                "targets": [json.loads(t.payload_json) for t in self.targets]}
        if self.context_policy != CONTEXT_POLICY:
            result["context_policy"] = self.context_policy
        if self.relationship_policy == SCALAR_POLICY:
            issues = json.loads(self.representation_issues_json)
            result.update(representation_issues=issues, representation_issue_count=len(issues))
        return result


def inventory_targets(record_bytes: bytes, specification: NestedSupportSchema, *,
                      artifact_kind: str, max_nodes: int = 100_000,
                      max_depth: int = 64, max_input_bytes: int = 4_000_000,
                      max_inventory_bytes: int = 64_000_000,
                      relationship_policy: str = POLICY,
                      context_policy: str = CONTEXT_POLICY) -> TargetInventory:
    """Capture a deterministic inventory from exact input bytes, without I/O.

    No wrappers are unwrapped: every pointer addresses these exact bytes.
    Malformed shapes and unsupported schema constructs are explicit blockers.
    Fitness mappings refer to the original document's top-level field only.
    """
    instrument, _ = policy_instrument(relationship_policy, context_policy=context_policy)
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
    targets, blocked, specifications = [], [], {}
    representation_issues = []
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

    def has_class_constraint(name):
        # A subclass keeps its parent/mixin constraints. The projected class
        # meaning intentionally does not interpret these rules, so refuse the
        # same constructs anywhere in its effective ancestry. A visited set
        # handles shared ancestors and cycles without recursive traversal.
        pending, seen = [name], set()
        while pending:
            current = pending.pop()
            if not current or current in seen:
                continue
            seen.add(current)
            definition = classes[current]["definition"]
            if any(definition.get(k) for k in
                   ("rules", "any_of", "all_of", "exactly_one_of", "none_of")):
                return True
            pending.extend([definition.get("is_a"), *definition.get("mixins", [])])
        return False

    def class_meaning(name):
        # Slots are induced separately. Repeating a complete ClassDefinition
        # would inject unrelated attributes and every sibling collection.
        definition = classes[name]["definition"]
        meaning = {k: definition[k] for k in ("name", "description", "is_a", "mixins", "class_uri")
                   if k in definition}
        pending = [definition.get("is_a"), *definition.get("mixins", [])]
        parents, seen = [], {name}
        while pending:
            parent = pending.pop()
            if not parent or parent in seen:
                continue
            seen.add(parent)
            inherited = classes[parent]["definition"]
            parents.append({k: inherited[k] for k in ("name", "description", "class_uri") if k in inherited})
            pending.extend([inherited.get("is_a"), *inherited.get("mixins", [])])
        if parents:
            meaning["ancestor_meanings"] = sorted(parents, key=lambda item: item["name"])
        return meaning

    def owner_context(owner, pointer, selected_slot):
        kept, omitted = {}, []
        for name, value in owner.items():
            if name == selected_slot:
                continue  # the exact selected value is supplied separately
            scalar_or_scalar_list = (not isinstance(value, (dict, list)) or
                                    isinstance(value, list) and
                                    all(not isinstance(v, (dict, list)) for v in value))
            if scalar_or_scalar_list or name in QUALIFIERS or name in IDENTITY:
                kept[name] = value
            else:
                omitted.append({"pointer": pointer + "/" + _token(name),
                                "sha256": _digest(value), "size": len(value),
                                "reason": "other_container_not_selected_assertion"})
        return kept, sorted(omitted, key=lambda item: item["pointer"])

    def ancestor_context(owner, pointer, class_name, branch_slot, child_pointer):
        kept, omitted = {}, []
        for name, value in owner.items():
            if name == branch_slot:
                continue
            scalar_or_scalar_list = (not isinstance(value, (dict, list)) or
                                    isinstance(value, list) and
                                    all(not isinstance(v, (dict, list)) for v in value))
            if scalar_or_scalar_list or name in QUALIFIERS:
                kept[name] = value
            else:
                omitted.append({"pointer": pointer + "/" + _token(name),
                                "sha256": _digest(value), "size": len(value),
                                "reason": "other_container_not_selected_assertion"})
        branch = owner[branch_slot]
        return {"pointer": pointer, "class": class_name, "projection": ANCESTOR_CONTEXT_POLICY,
                "value": kept, "value_yaml": yaml.safe_dump(kept, sort_keys=True),
                "source_mapping_sha256": _digest(owner), "value_sha256": _digest(kept),
                "field_origins": {name: pointer + "/" + _token(name) for name in sorted(kept)},
                "omitted_containers": sorted(omitted, key=lambda item: item["pointer"]),
                "path_branch": {"pointer": pointer + "/" + _token(branch_slot),
                                "selected_entity_pointer": child_pointer,
                                "sha256": _digest(branch), "size": len(branch),
                                "reason": "selected_path_branch_represented_separately"}}

    def emit(pointer, kind, value, owner, owner_pointer, owner_class, chain, ancestors,
             representation=None):
        nonlocal rendered_bytes
        # Retain complete scalar siblings and named qualifier fields without
        # repeating unrelated containers. Every omission is explicit and pinned.
        declared = declarations(value, pointer)
        for k in DECLARATIONS:
            if k in owner:
                declared[owner_pointer + "/" + _token(k)] = owner[k]
        selected = chain[-1]
        enum_names = {edge["slot"].get("range") for edge in chain}
        vocabulary_names = {str(v) for edge in chain for v in edge["slot"].get("values_from", [])}
        spec = {"class_slot_chain": chain, "owning_class": class_meaning(owner_class),
                "slot": selected["slot"], "range_class": selected["range_class"],
                "enums": {name: schema["enums"][name] for name in sorted(enum_names - {None})
                          if name in schema["enums"]},
                "vocabulary": {name: schema["vocabulary"][name] for name in sorted(vocabulary_names)}}
        spec_json = _canonical(spec)
        spec_key = hashlib.sha256(spec_json.encode("utf-8")).hexdigest()
        if spec_key not in specifications:
            specifications[spec_key] = spec_json
            rendered_bytes += len(spec_json.encode("utf-8"))
        kept, omitted = owner_context(owner, owner_pointer, selected["slot"]["name"])
        context = {"containing_entity": {"pointer": owner_pointer, "class": owner_class,
                                          "value": kept, "source_mapping_sha256": _digest(owner),
                                          "value_sha256": _digest(kept),
                                          "value_yaml": yaml.safe_dump(kept, sort_keys=True),
                                          "projection": "scalar_siblings_and_explicit_qualifiers_v1",
                                          "selected_slot_supplied_as_target": selected["slot"]["name"],
                                          "omitted_containers": omitted},
                   "ancestors": ancestors, "declarations": declared,
                   "collection_metadata_inherited": False}
        if context_policy != CONTEXT_POLICY:
            context["context_policy"] = context_policy
        first = pointer_tokens(pointer)[0]
        payload = {"instrument": instrument, "axis": AXIS, "policy": relationship_policy,
                   "pointer": pointer, "kind": kind, "artifact": artifact,
                   "value": value, "value_sha256": _digest(value),
                   "value_type": _typed(value)[0], "value_yaml": yaml.safe_dump(value, sort_keys=True),
                   "specification_ref": spec_key, "context": context,
                   "context_sha256": _digest(context),
                   "fitness": {"basis": "top_level_only", "mapping": "many_to_one",
                               "pointer": "/" + _token(first)}}
        if context_policy != CONTEXT_POLICY:
            payload["context_policy"] = context_policy
        if representation is not None:
            payload["representation"] = representation
        encoded = _canonical(payload)
        rendered_bytes += len(encoded.encode("utf-8"))
        if rendered_bytes > max_inventory_bytes:
            raise ValueError("target context exceeds max_inventory_bytes; no partial inventory returned")
        targets.append(SupportTarget(encoded, specifications[spec_key]))

    def walk(entity, class_name, pointer, chain, ancestors):
        nonlocal rendered_bytes
        cls = classes[class_name]
        if has_class_constraint(class_name):
            block(pointer, "unsupported_class_constraint")
            return
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
                    "range_class": class_meaning(rng) if entry["range_class"] else None}
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
                            if relationship_policy == SCALAR_POLICY and type(member) is str:
                                if has_class_constraint(rng):
                                    block(path, "unsupported_class_constraint")
                                    continue
                                issue = {"pointer": path, "kind": "relationship_edge",
                                         "code": "inline_class_requires_mapping", "range": rng}
                                representation_issues.append(issue)
                                rendered_issue = _canonical(issue).encode("utf-8")
                                # The extra ledger is retained alongside the target.
                                # Charge it to the same finite inventory budget.
                                rendered_bytes += len(rendered_issue)
                                emit(path, "relationship_edge", member, entity, pointer, class_name,
                                     next_chain, ancestors, representation={
                                         "status": "schema_invalid_inline_class_string",
                                         "expected": "mapping", "observed": "str", "range": rng})
                                continue
                            block(path, "inline_class_requires_mapping")
                            continue
                        emit(path, "relationship_edge", member, entity, pointer, class_name,
                             next_chain, ancestors)
                        next_ancestors = (ancestors + [ancestor_context(entity, pointer, class_name, name, path)]
                                          if context_policy == ANCESTOR_CONTEXT_POLICY else ancestry)
                        walk(member, rng, path, next_chain, next_ancestors)
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
    return TargetInventory(tuple(targets), _canonical(blocked), _canonical(artifact),
                           _canonical({key: json.loads(value) for key, value in specifications.items()}),
                           relationship_policy, _canonical(representation_issues), context_policy)


def render_request(target: SupportTarget, *, bundle: str, model: str,
                   max_tokens: int = 8000) -> dict:
    """Pure draft provider arguments; no client, retry, cache or execution path."""
    if not isinstance(bundle, str) or not bundle.strip():
        raise ValueError("source bundle text is required")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("explicit model is required")
    if type(max_tokens) is not int or max_tokens < 1:
        raise ValueError("max_tokens must be a positive integer")
    payload = target.to_dict()
    context_policy = payload.get("context_policy", CONTEXT_POLICY)
    instrument, system = policy_instrument(payload["policy"], context_policy=context_policy)
    if payload["instrument"] != instrument:
        raise ValueError("target instrument and relationship policy disagree")
    # YAML already carries the complete value and native types. Avoid sending
    # the JSON preview as a second copy of every source/context paragraph.
    payload.pop("value")
    payload["context"]["containing_entity"].pop("value")
    if context_policy == ANCESTOR_CONTEXT_POLICY:
        for ancestor in payload["context"]["ancestors"]:
            ancestor.pop("value")
    return {"model": model, "max_tokens": max_tokens, "temperature": None,
            "system": system, "messages": [{"role": "user", "content": [
                {"type": "text", "text": "# Source documents\n\n" + bundle,
                 "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "# Exact assertion target and untrusted record context\n\n"
                 + _canonical(payload)}]}]}


def request_identity(target: SupportTarget, *, bundle: str, model: str,
                     max_tokens: int = 8000) -> str:
    """All rendered arguments participate; this is not permission to reuse v2."""
    return _digest(render_request(target, bundle=bundle, model=model, max_tokens=max_tokens))
