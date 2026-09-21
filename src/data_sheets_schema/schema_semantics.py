"""Versioned, schema-only guidance for the structure occupied by a record.

This is deliberately separate from schema_digest and the fitness instrument.
Record values select no wording: only object paths and declared slot names are
rendered. The record's bytes (or a typed parsed representation) are hash-bound.
No source evidence is read and no scientific or schema-validity verdict is made.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml

from data_sheets_schema import schema_digest
from data_sheets_schema.schema_snapshot import SchemaSnapshot, capture_schema
from data_sheets_schema.schema_view import shared_view

FORMAT = "occupied_schema_semantics_v1"
MAX_INPUT_BYTES = 4_000_000
MAX_RENDER_BYTES = 262_144
MAX_PAIR_RENDER_BYTES = 524_288
MAX_NODES = 20_000
MAX_DEPTH = 64
MAX_CONTEXTS = 4_000
MAX_CLASSES = 256
MAX_SLOTS = 4_096


class SemanticGuidanceError(ValueError):
    """Unsupported or ambiguous input; messages never quote record values."""


class _RecordLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen = set()
        for key, _ in node.value:
            if key.tag != "tag:yaml.org,2002:str":
                raise SemanticGuidanceError("record_keys_must_be_strings_no_merges")
            name = self.construct_object(key, deep=deep)
            if name in seen:
                raise SemanticGuidanceError("duplicate_record_key")
            seen.add(name)
        return super().construct_mapping(node, deep=deep)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def _pointer(parent: str, key: str | int) -> str:
    return parent + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _record(raw: str | bytes | dict) -> tuple[dict, dict]:
    if type(raw) in (str, bytes):
        try:
            data = raw.encode("utf-8") if type(raw) is str else raw
            if len(data) > MAX_INPUT_BYTES:
                raise SemanticGuidanceError("record_byte_bound")
            text = data.decode("utf-8")
            value = yaml.load(text, Loader=_RecordLoader)
        except SemanticGuidanceError:
            raise
        except (UnicodeError, yaml.YAMLError, RecursionError):
            raise SemanticGuidanceError("invalid_record_yaml") from None
        binding = {"kind": "exact_record_bytes", "sha256": hashlib.sha256(data).hexdigest()}
    elif type(raw) is dict:
        value, binding = raw, None
    else:
        raise SemanticGuidanceError("record_must_be_yaml_or_mapping")
    if type(value) is not dict:
        raise SemanticGuidanceError("record_root_must_be_mapping")
    active: set[int] = set()
    count = 0

    def typed(obj, depth=0):
        nonlocal count
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise SemanticGuidanceError("record_structure_bound")
        typ = type(obj)
        if typ in (dict, list):
            if id(obj) in active:
                raise SemanticGuidanceError("cyclic_record")
            active.add(id(obj))
            try:
                if typ is dict:
                    if any(type(k) is not str for k in obj):
                        raise SemanticGuidanceError("record_keys_must_be_strings")
                    return ["mapping", [[k, typed(v, depth + 1)] for k, v in sorted(obj.items())]]
                return ["list", [typed(v, depth + 1) for v in obj]]
            finally:
                active.remove(id(obj))
        if typ in (str, int, bool) or obj is None:
            return [typ.__name__, obj]
        if typ is float and math.isfinite(obj):
            return ["float", obj.hex()]
        if typ in (datetime.date, datetime.datetime):
            return [typ.__name__, obj.isoformat()]
        raise SemanticGuidanceError("unsupported_record_scalar")

    try:
        encoded = _json(typed(value)).encode("utf-8")
    except (UnicodeError, RecursionError):
        raise SemanticGuidanceError("invalid_record_structure") from None
    if len(encoded) > MAX_INPUT_BYTES:
        raise SemanticGuidanceError("record_byte_bound")
    return value, binding or {"kind": "typed_parsed_record", "sha256": hashlib.sha256(encoded).hexdigest()}


# These are schema declarations, never copied from a record. Descriptions stay
# verbatim; presentation does not turn examples within schema prose into facts.
_CONSTRAINTS = (
    "identifier", "key", "recommended", "pattern", "minimum_value",
    "maximum_value", "minimum_cardinality", "maximum_cardinality",
    "exact_cardinality", "equals_string", "equals_string_in", "equals_number", "equals_expression",
    "implicit_prefix", "ifabsent", "readonly", "unit", "structured_pattern",
    "value_presence", "list_elements_unique", "list_elements_ordered",
    "designates_type", "role", "relational_role",
)
_BRANCHES = ("any_of", "all_of", "exactly_one_of", "none_of", "range_expression", "union_of")
_SLOT_EXPRESSIONS = _BRANCHES + ("array", "enum_range", "bindings", "has_member", "all_members", "path_rule", "apply_to")
_ENUM_EXPRESSIONS = ("is_a", "mixins", "inherits", "include", "minus", "matches",
                     "reachable_from", "values_from", "code_set", "code_set_tag",
                     "code_set_version", "pv_formula", "concepts")


def _metadata(obj, fields):
    return {key: _plain(value) for key in fields
            if (value := getattr(obj, key, None)) is not None and value != [] and value != {}}


def _reject_expressions(obj, fields, code):
    if any(getattr(obj, field, None) for field in fields):
        raise SemanticGuidanceError(code)


def _check_pattern(obj):
    pattern = getattr(obj, "structured_pattern", None)
    if pattern is not None and getattr(pattern, "interpolated", False):
        # Settings expansion is not part of this version; syntax alone would
        # silently lose the captured schema's interpolated constraint.
        raise SemanticGuidanceError("unsupported_interpolated_schema_pattern")


def _plain(value):
    """Schema metadata to JSON, with no silent stringification of objects."""
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if isinstance(value, (str, int)):
        return str(value) if isinstance(value, str) else int(value)
    if isinstance(value, (list, tuple)):
        return [_plain(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items() if v is not None}
    import dataclasses
    if dataclasses.is_dataclass(value):
        return {f.name: _plain(v) for f in dataclasses.fields(value)
                if (v := getattr(value, f.name)) is not None and v != [] and v != {}}
    raise SemanticGuidanceError("unsupported_schema_declaration")


def build_record(record_text: str | bytes | dict, class_name: str,
                 schema_path: Path | str | None = None, *, profile=None,
                 snapshot: SchemaSnapshot | None = None) -> dict:
    """Build guidance from one exact schema capture and explicit profile.

    Only occupied slots plus required siblings are included. Repeated object
    classes share one semantic definition; their actual pointer contexts remain
    distinct. Empty/null slots still receive their declared meaning. References
    receive their class meaning but are never traversed as inline objects.

    This initial version rejects keyed object collections and range-expression
    branches: guessing a class or exposing record-derived dictionary keys would
    violate its boundary. Bounds fail closed rather than truncate meanings.
    """
    if profile is None:
        raise SemanticGuidanceError("explicit_profile_required")
    record, binding = _record(record_text)
    selected = schema_path if schema_path is not None else schema_digest.CLASS_SCHEMA.get(class_name)
    if selected is None:
        raise SemanticGuidanceError("explicit_schema_required")
    path = schema_digest.resolve_schema(Path(selected))
    captured = capture_schema(path, strict=True) if snapshot is None else snapshot
    if not captured.sources or captured.sources[0][1].resolve() != path.resolve():
        raise SemanticGuidanceError("schema_snapshot_root_mismatch")
    closure = []
    for name, source, data in captured.sources:
        if not isinstance(data, bytes):
            raise SemanticGuidanceError("incomplete_schema_snapshot")
        closure.append({"name": str(name), "path": str(source),
                        "sha256": hashlib.sha256(data).hexdigest()})
    if snapshot is not None:
        frozen = {source: data for _, source, data in captured.sources}
        if len(frozen) != len(captured.sources):
            raise SemanticGuidanceError("duplicate_schema_snapshot_source")
        try:
            verified = capture_schema(path, content=captured.sources[0][2],
                                      read_bytes=lambda source: frozen[source], strict=True)
        except (KeyError, OSError, ValueError, TypeError, yaml.YAMLError):
            raise SemanticGuidanceError("invalid_schema_snapshot_closure") from None
        if verified != captured:
            raise SemanticGuidanceError("schema_snapshot_identity_mismatch")
    sv = shared_view(path, snapshot=captured)
    from data_sheets_schema.profiles import vocabulary_bytes
    vocabulary_raw = vocabulary_bytes(profile)
    vocabulary = schema_digest.vocabularies(content=vocabulary_raw, profile=profile)
    definitions: dict[str, dict] = {}
    slots_by_class = {}
    meanings = {}
    slot_ancestry = {}
    contexts = []
    total_slots = 0

    def meaning(name, active=()):
        if name in active:
            raise SemanticGuidanceError("cyclic_class_ancestry")
        if name in meanings:
            return meanings[name]
        cls = sv.get_class(name)
        if cls is None:
            raise SemanticGuidanceError("unknown_schema_class")
        if getattr(cls, "rules", None):
            raise SemanticGuidanceError("unsupported_conditional_class_rules")
        parents = ([str(cls.is_a)] if cls.is_a else []) + [str(m) for m in cls.mixins]
        ancestors = {}
        for parent in parents:
            item = meaning(parent, (*active, name))
            ancestors[parent] = {k: v for k, v in item.items() if k != "ancestors"}
            ancestors.update({x["name"]: x for x in item["ancestors"]})
        item = {"name": name, "description": str(cls.description) if cls.description is not None else None,
                **_metadata(cls, ("notes",)), "ancestors": [ancestors[k] for k in sorted(ancestors)]}
        meanings[name] = item
        if len(meanings) > MAX_CLASSES:
            raise SemanticGuidanceError("schema_class_bound")
        return item

    def slots(name):
        if name not in slots_by_class:
            meaning(name)  # Reject inheritance cycles before LinkML induction.
            # Slot ancestry can cycle independently of class ancestry. Inspect
            # the same raw declaration LinkML selects, before it induces slots.
            for key in sv.class_slots(name):
                slot_lineage(raw_slot(key, name))
            slots_by_class[name] = {str(s.name): s for s in sv.class_induced_slots(name)}
        return slots_by_class[name]

    def raw_slot(key, owner):
        for parent in sv.class_ancestors(owner):
            cls = sv.get_class(parent)
            if key in cls.attributes:
                return cls.attributes[key]
        selected = sv.get_slot(key, attributes=False)
        if selected is None:
            raise SemanticGuidanceError("unknown_schema_slot")
        return selected

    def slot_lineage(slot, active=()):
        name = str(slot.name)
        if name in active:
            raise SemanticGuidanceError("cyclic_slot_ancestry")
        if len(active) > MAX_DEPTH:
            raise SemanticGuidanceError("schema_slot_ancestry_bound")
        parents = ([str(slot.is_a)] if slot.is_a else []) + [str(m) for m in slot.mixins]
        ancestors = {}
        for parent in parents:
            declaration = sv.get_slot(parent, attributes=False)
            if declaration is None:
                raise SemanticGuidanceError("unknown_slot_ancestor")
            if parent not in slot_ancestry:
                inherited = slot_lineage(declaration, (*active, name))
                slot_ancestry[parent] = (declaration, inherited)
                if len(slot_ancestry) > MAX_SLOTS:
                    raise SemanticGuidanceError("schema_slot_ancestry_bound")
            declaration, inherited = slot_ancestry[parent]
            ancestors[parent] = declaration
            ancestors.update(inherited)
        return ancestors

    def type_meaning(name, active=()):
        if name in active:
            raise SemanticGuidanceError("cyclic_type_ancestry")
        typ = sv.get_type(name)
        if typ is None:
            raise SemanticGuidanceError("unknown_schema_type")
        _reject_expressions(typ, _BRANCHES, "unsupported_schema_type_branch")
        _check_pattern(typ)
        result = {"name": name, **{k: _plain(v) for k in
                  ("description", "notes", "typeof", "base", "uri", "repr", "pattern", "minimum_value", "maximum_value",
                   "equals_string", "equals_string_in", "equals_number", "structured_pattern", "unit", "implicit_prefix")
                  if (v := getattr(typ, k, None)) is not None and v != [] and v != {}}}
        if typ.typeof:
            result["parent"] = type_meaning(str(typ.typeof), (*active, name))
        return result

    def enum_meaning(enum):
        # Local permissible values are complete only for a static enum. Do not
        # silently display them as the meaning of an inherited/dynamic set.
        _reject_expressions(enum, _ENUM_EXPRESSIONS, "unsupported_schema_enum_expression")
        return {"description": str(enum.description) if enum.description is not None else None,
                **_metadata(enum, ("notes", "enum_uri")),
                "permissible_values": {str(k): _plain(v) for k, v in sorted((enum.permissible_values or {}).items())}}

    def slot_metadata(s, owner):
        _check_pattern(s)
        item = _metadata(s, ("notes",))
        constraints = _metadata(s, _CONSTRAINTS)
        if constraints:
            item["constraints"] = constraints
        names = [str(v) for v in (s.values_from or [])]
        ts = schema_digest.term_sources_of(s) or schema_digest.TERM_SOURCES.get((owner, str(s.name)))
        if names or ts:
            item["vocabulary"] = {"values_from": names, "term_sources": ts,
                                  "pinned_terms": {n: _plain(vocabulary[n]) for n in names if n in vocabulary},
                                  "unresolved_vocabularies": [n for n in names if n not in vocabulary]}
        return item

    def guidance(s, owner):
        _reject_expressions(s, _SLOT_EXPRESSIONS, "unsupported_schema_range_branch")
        raw = raw_slot(str(s.name), owner)
        if (s.is_a != raw.is_a or list(s.mixins) != list(raw.mixins)):
            # Contextual descriptions/constraints are induced normally. A
            # contextual ancestry override requires its own resolution policy;
            # this version must not label the raw ancestry as the effective one.
            raise SemanticGuidanceError("unsupported_contextual_slot_ancestry")
        rng = str(s.range) if s.range else None
        cls = sv.get_class(rng) if rng else None
        enum = sv.get_enum(rng) if rng else None
        typ = sv.get_type(rng) if rng else None
        if sum(x is not None for x in (cls, enum, typ)) != 1:
            raise SemanticGuidanceError("unknown_or_ambiguous_schema_range")
        item = {"name": str(s.name), "description": str(s.description) if s.description is not None else None,
                "range": rng, "required": bool(s.required), "multivalued": bool(s.multivalued),
                "representation": "inline_object" if cls and sv.is_inlined(s) else "reference" if cls else "scalar"}
        if cls:
            item["range_class"] = meaning(rng)
            item["inlined_as_list"] = bool(s.inlined_as_list)
        if typ:
            item["range_type"] = type_meaning(rng)
        if enum:
            item["enum"] = enum_meaning(enum)
        item.update(slot_metadata(s, owner))
        # An induced slot does not inherit a parent slot's description. Keep
        # all declared ancestor meanings/obligations alongside the contextual
        # induced slot rather than inventing an override or dropping a role.
        ancestors = slot_lineage(raw)
        for declaration in (raw, *ancestors.values()):
            _reject_expressions(declaration, _SLOT_EXPRESSIONS, "unsupported_schema_range_branch")
        if ancestors:
            item.update(_metadata(raw, ("is_a", "mixins")))
            item["slot_ancestors"] = []
            for name, ancestor in sorted(ancestors.items()):
                declared = {"name": name, "description": str(ancestor.description) if ancestor.description is not None else None,
                            **_metadata(ancestor, ("is_a", "mixins", "range", "required", "multivalued", "inlined", "inlined_as_list")),
                            **slot_metadata(ancestor, owner)}
                if ancestor.range:
                    inherited_range = str(ancestor.range)
                    inherited_class, inherited_type, inherited_enum = (sv.get_class(inherited_range), sv.get_type(inherited_range), sv.get_enum(inherited_range))
                    if sum(x is not None for x in (inherited_class, inherited_type, inherited_enum)) != 1:
                        raise SemanticGuidanceError("unknown_or_ambiguous_schema_range")
                    if inherited_class: declared["range_class"] = meaning(inherited_range)
                    if inherited_type: declared["range_type"] = type_meaning(inherited_range)
                    if inherited_enum: declared["enum"] = enum_meaning(inherited_enum)
                item["slot_ancestors"].append(declared)
        return item

    def visit(obj, name, pointer="", depth=0):
        nonlocal total_slots
        if depth > MAX_DEPTH or len(contexts) >= MAX_CONTEXTS:
            raise SemanticGuidanceError("schema_context_bound")
        if type(obj) is not dict:
            raise SemanticGuidanceError("inline_object_must_be_mapping")
        declared = slots(name)
        if any(key not in declared for key in obj):
            raise SemanticGuidanceError("unknown_record_slot")
        if name not in definitions:
            definitions[name] = {**meaning(name), "slots": {}}
        chosen = set(obj) | {key for key, s in declared.items() if s.required}
        contexts.append({"path": pointer, "class": name, "occupied_slots": sorted(obj)})
        for key in sorted(chosen):
            if key not in definitions[name]["slots"]:
                total_slots += 1
                if total_slots > MAX_SLOTS:
                    raise SemanticGuidanceError("schema_slot_bound")
                definitions[name]["slots"][key] = guidance(declared[key], name)
            if key not in obj or obj[key] is None:
                continue
            s = declared[key]
            item = definitions[name]["slots"][key]
            value = obj[key]
            at = _pointer(pointer, key)
            if s.multivalued:
                if type(value) is not list:
                    raise SemanticGuidanceError("multivalued_slot_requires_list")
                members = [(v, _pointer(at, i)) for i, v in enumerate(value)]
            else:
                if type(value) is list:
                    raise SemanticGuidanceError("single_slot_has_list")
                members = [(value, at)]
            for member, where in members:
                if member is None:
                    continue
                if item["representation"] == "inline_object":
                    visit(member, item["range"], where, depth + 1)
                elif type(member) in (dict, list):
                    raise SemanticGuidanceError("scalar_or_reference_has_object")

    visit(record, str(class_name))
    result = {"format": FORMAT, "scope": "Schema guidance only; no record facts or scientific verdict. Descriptions and examples are schema instructions, not dataset evidence.",
              "record_binding": binding, "schema": {"root_class": str(class_name), "sources": closure,
                  "namespaces": {str(k): str(v) for k, v in sorted(sv.namespaces().items())},
                  "default_prefix": str(sv.schema.default_prefix) if sv.schema.default_prefix is not None else None,
                  "default_range": str(sv.schema.default_range) if sv.schema.default_range is not None else None},
              "profile": str(profile.name),
              "profile_vocabulary_sha256": hashlib.sha256(vocabulary_raw).hexdigest() if vocabulary_raw else None,
              "coverage": "occupied slots and required siblings; complete descriptions, no truncation",
              "contexts": contexts, "classes": definitions,
              "counts": {"object_contexts": len(contexts), "classes": len(definitions), "slot_definitions": total_slots}}
    try:
        size = len(_json(result).encode("utf-8"))
    except (UnicodeError, RecursionError, TypeError, ValueError):
        raise SemanticGuidanceError("unrenderable_schema_guidance") from None
    if size + 1 > MAX_RENDER_BYTES:
        raise SemanticGuidanceError("guidance_byte_bound")
    return result


def render_record(record_text: str | bytes | dict, class_name: str,
                  schema_path: Path | str | None = None, *, profile=None,
                  snapshot: SchemaSnapshot | None = None) -> str:
    """Canonical JSON; no truncation and no changes to legacy instruments."""
    return _json(build_record(record_text, class_name, schema_path,
                              profile=profile, snapshot=snapshot)) + "\n"


def render_pair(full_text: str | bytes | dict, core_text: str | bytes | dict, *,
                schema_paths: tuple[Path | str, Path | str] | None = None,
                profile=None,
                snapshots: tuple[SchemaSnapshot | None, SchemaSnapshot | None] | None = None) -> str:
    """Pool only byte-identical class definitions from the two original views.

    Every per-record field is preserved, except ``classes`` is represented by
    its explicit class-name-to-definition-ID mapping. Resolving those mappings
    reconstructs each build_record result exactly. Same names do not establish
    equality; different contextual meanings remain separate definitions.
    """
    if schema_paths is not None and (not isinstance(schema_paths, (tuple, list)) or len(schema_paths) != 2):
        raise SemanticGuidanceError("pair_requires_two_schema_paths")
    if snapshots is not None and (not isinstance(snapshots, (tuple, list)) or len(snapshots) != 2):
        raise SemanticGuidanceError("pair_requires_two_snapshots")
    paths = (None, None) if schema_paths is None else schema_paths
    captures = (None, None) if snapshots is None else snapshots
    records = {
        "original_full": build_record(full_text, "Dataset", paths[0], profile=profile, snapshot=captures[0]),
        "original_core": build_record(core_text, "CoreDataset", paths[1], profile=profile, snapshot=captures[1]),
    }
    unique = sorted({_json(definition) for record in records.values()
                     for definition in record["classes"].values()})
    identifiers = {value: f"class_{i:04d}" for i, value in enumerate(unique, 1)}
    definitions = {identifiers[value]: json.loads(value) for value in unique}
    for record in records.values():
        record["class_definition_refs"] = {
            name: identifiers[_json(definition)] for name, definition in record.pop("classes").items()}
    result = {
        "format": "occupied_schema_semantics_pair_v1",
        "scope": "Schema guidance only, not source evidence or scientific acceptance. Each record's class_definition_refs maps schema class names to exact entries in definitions. Resolve those references to read its class and slot meanings, interpreting CURIEs under that record's schema.namespaces and default_prefix. Even shared definition bytes can have different namespace interpretations across records. Same-named classes may have different definitions across records. No meaning is omitted or merged by similarity.",
        "records": records,
        "definitions": definitions,
    }
    text = _json(result) + "\n"
    if len(text.encode("utf-8")) > MAX_PAIR_RENDER_BYTES:
        raise SemanticGuidanceError("pair_guidance_byte_bound")
    return text
