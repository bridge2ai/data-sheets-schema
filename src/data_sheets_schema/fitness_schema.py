"""Explicit, value-independent fitness specifications (#2183).

The audit helper remains unchanged. Its pure declaration rules are reused here,
with a separate traversal over *declared* inline classes, never a judged value.
One immutable snapshot supplies both instrument identity and sent slot text.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
from pathlib import Path

import yaml

from data_sheets_schema import schema_digest
from data_sheets_schema.profiles import Profile
from data_sheets_schema.schema_snapshot import capture_schema
from data_sheets_schema.schema_view import shared_view
from data_sheets_schema.schema_semantics import (
    SemanticGuidanceError, _json, _metadata, _plain, _reject_expressions,
    _check_pattern, _CONSTRAINTS, _BRANCHES, _SLOT_EXPRESSIONS,
    _ENUM_EXPRESSIONS, MAX_CLASSES, MAX_SLOTS, MAX_DEPTH,
)

GUIDANCE = "nested_semantics_v1"
SELECTOR = "fitness_schema_guidance"
MAX_SPEC_BYTES = 524_288
MAX_SNAPSHOT_BYTES = 16_777_216
SCOPE = 'Schema instructions for field fitness, not dataset facts or source evidence. All declared child fields are shown; optional fields need not be invented. Each inline_classes entry maps field names through slot_definition_refs to exact slot_definitions. Resolve these references to read the complete declarations. Reference ranges take references, not inline objects. Schema prose, notes and examples remain guidance only.'


def validate_selection(mapping, *, style=None):
    """Missing means legacy. A supplied selector must be exact and applicable."""
    if SELECTOR not in mapping:
        return None
    if type(mapping[SELECTOR]) is not str or mapping[SELECTOR] != GUIDANCE:
        raise ValueError("unsupported fitness schema guidance")
    if style is not None and style not in ("fitness", "subtype"):
        raise ValueError("fitness schema guidance applies only to fitness/subtype")
    return GUIDANCE


def validate_manifest_selection(manifest):
    selected = validate_selection(manifest)
    for job in manifest.get("evaluation_jobs", []):
        actual = validate_selection(job, style=job.get("style", ""))
        expected = selected if job.get("style") in ("fitness", "subtype") else None
        if actual != expected:
            raise ValueError("manifest/job fitness schema guidance mismatch")
    return selected


@dataclass(frozen=True)
class FitnessSchemaSnapshot:
    class_name: str
    schema_path: str
    profile_name: str
    profile_identity: str
    sources: tuple[tuple[Path, str], ...]
    profile_sources: tuple[tuple[Path, str], ...]
    schema: str
    specification: str
    specifications: tuple[tuple[str, str], ...]

    def spec(self, slot):
        for name, text in self.specifications:
            if name == slot:
                return text
        raise ValueError("unknown slot for captured fitness schema")

    def as_tuple(self):
        # Additive adapter for the existing scorer's snapshot interface.
        return self.schema, self, None, self.specification

    def instrument(self):
        return {SELECTOR: GUIDANCE, "schema": self.schema,
                "specification": self.specification}

    def assert_context(self, class_name, schema_path, profile):
        selected = schema_path if schema_path is not None else schema_digest.CLASS_SCHEMA.get(class_name)
        if (profile is None or self.class_name != class_name
                or self.profile_name != profile.name or self.profile_identity != _profile_identity(profile)
                or selected is None
                or self.schema_path != str(schema_digest.resolve_schema(Path(selected)))):
            raise ValueError("fitness schema snapshot context mismatch")
        expected_pin = profile.pin_path
        if tuple(p for p, _ in self.profile_sources) != (() if expected_pin is None else (expected_pin,)):
            raise ValueError("fitness schema snapshot profile mismatch")
        return self


def _profile_identity(profile):
    if type(profile) is not Profile:
        raise SemanticGuidanceError("explicit_profile_definition_required")
    def plain(value):
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {k: plain(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [plain(v) for v in value]
        return _plain(value)
    return _json({f.name: plain(getattr(profile, f.name)) for f in fields(profile)})


def _pool_slots(classes):
    """Only exact canonical declaration equality permits a shared definition."""
    values = sorted({_json(slot) for cls in classes.values() for slot in cls["slots"].values()})
    refs = {value: f"slot_{i:04d}" for i, value in enumerate(values, 1)}
    import json
    definitions = {refs[value]: json.loads(value) for value in values}
    pooled = {name: {**{k: v for k, v in cls.items() if k != "slots"},
                     "slot_definition_refs": {key: refs[_json(slot)] for key, slot in cls["slots"].items()}}
              for name, cls in classes.items()}
    return pooled, definitions


class _SchemaLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen = set()
        for key, _ in node.value:
            if key.tag != "tag:yaml.org,2002:str":
                raise SemanticGuidanceError("schema_keys_must_be_strings_no_merges")
            name = self.construct_object(key, deep=deep)
            if name in seen:
                raise SemanticGuidanceError("duplicate_schema_key")
            seen.add(name)
        return super().construct_mapping(node, deep=deep)


def _declarations(sv, vocabulary, class_name):
    # Declaration projection follows the frozen audit helper. Unlike its
    # occupied-record traversal, every declared inline child is included, even
    # if a supplied value is empty, malformed, or lacks the required children.
    definitions = {}
    slots_by_class = {}
    meanings = {}
    slot_ancestry = {}
    def meaning(name, active=()):
        if len(active) > MAX_DEPTH:
            raise SemanticGuidanceError("schema_class_ancestry_bound")
        if name in active:
            raise SemanticGuidanceError("cyclic_class_ancestry")
        if name in meanings:
            return meanings[name]
        cls = sv.get_class(name)
        if cls is None:
            raise SemanticGuidanceError("unknown_schema_class")
        _reject_expressions(cls, _BRANCHES, "unsupported_schema_class_branch")
        if getattr(cls, "rules", None):
            raise SemanticGuidanceError("unsupported_conditional_class_rules")
        parents = ([str(cls.is_a)] if cls.is_a else []) + [str(m) for m in cls.mixins]
        ancestors = {}
        for parent in parents:
            item = meaning(parent, (*active, name))
            ancestors[parent] = {k: v for k, v in item.items() if k != "ancestors"}
            ancestors.update({x["name"]: x for x in item["ancestors"]})
        item = {"name": name, "description": str(cls.description) if cls.description is not None else None,
                **_metadata(cls, ("notes", "abstract", "mixin", "class_uri", "unique_keys",
                                  "slot_names_unique", "represents_relationship")), "ancestors": [ancestors[k] for k in sorted(ancestors)]}
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
        if len(active) > MAX_DEPTH:
            raise SemanticGuidanceError("schema_type_ancestry_bound")
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

    pending = [class_name]
    count = 0
    while pending:
        name = pending.pop()
        if name in definitions:
            continue
        declared = slots(name)
        count += len(declared)
        if count > MAX_SLOTS:
            raise SemanticGuidanceError("schema_slot_bound")
        definitions[name] = {**meaning(name), "slots": {
            key: guidance(s, name) for key, s in sorted(declared.items())}}
        for item in definitions[name]["slots"].values():
            if item["representation"] == "inline_object":
                pending.append(item["range"])
    return definitions


def capture(class_name="Dataset", schema_path=None, *, profile):
    """Capture complete class-scoped specifications without reading any value.

    Cyclic inline graphs are finite named definitions. Reference ranges expose
    their role but are not presented as required inline objects. Unsupported
    schema expressions refuse the instrument before a judge is constructed.
    """
    if profile is None:
        raise SemanticGuidanceError("explicit_profile_required")
    profile_identity = _profile_identity(profile)
    selected = schema_path if schema_path is not None else schema_digest.CLASS_SCHEMA.get(class_name)
    if selected is None:
        raise SemanticGuidanceError("explicit_schema_required")
    path = schema_digest.resolve_schema(Path(selected))
    captured = capture_schema(path, strict=True)
    documents = []
    for _, _, raw in captured.sources:
        documents.append(yaml.load(raw, Loader=_SchemaLoader))
    sv = shared_view(path, snapshot=captured)
    vocabulary_path = profile.pin_path
    vocabulary_raw = vocabulary_path.read_bytes() if vocabulary_path is not None else b""
    if vocabulary_raw:
        yaml.load(vocabulary_raw, Loader=_SchemaLoader)
    vocabulary = schema_digest.vocabularies(content=vocabulary_raw, profile=profile)
    definitions = _declarations(sv, vocabulary, str(class_name))
    sources = tuple((source, hashlib.sha256(raw).hexdigest()) for _, source, raw in captured.sources)
    profile_sources = (() if vocabulary_path is None else
                       ((vocabulary_path, hashlib.sha256(vocabulary_raw).hexdigest()),))
    logical_sources = []
    for index, ((name, _, _), (_, digest), doc) in enumerate(zip(captured.sources, sources, documents)):
        # Exact content binds import directives. Local authority retains paths;
        # relocating the same relative-import graph must not change the judge.
        logical = ("root" if index == 0 else
                   "import:" + (str(doc.get("id") or doc.get("name"))
                                if Path(str(name)).is_absolute() else str(name)))
        logical_sources.append({"role": logical, "id": str(doc.get("id") or ""),
                                "name": str(doc.get("name") or ""), "sha256": digest})
    semantic_profile = {"name": profile.name,
                        "tracks_digest_pin": profile.tracks_digest_pin,
                        "vocabulary_sha256": hashlib.sha256(vocabulary_raw).hexdigest() if profile_sources else None}
    identity = {"format": GUIDANCE, "class": str(class_name),
                "schema_digest_basis": "legacy_shape_with_declared_schema_id_v1",
                "schema_sources": sorted(logical_sources, key=_json),
                "profile": profile.name,
                "profile_configuration_sha256": hashlib.sha256(_json(semantic_profile).encode()).hexdigest(),
                "profile_vocabulary_sha256": semantic_profile["vocabulary_sha256"],
                "namespaces": {str(k): str(v) for k, v in sorted(sv.namespaces().items())},
                "default_prefix": str(sv.schema.default_prefix) if sv.schema.default_prefix is not None else None,
                "default_range": str(sv.schema.default_range) if sv.schema.default_range is not None else None}
    root = definitions[str(class_name)]
    specifications = []
    for slot, declared in sorted(root["slots"].items()):
        reachable = {}
        pending = [declared["range"]] if declared["representation"] == "inline_object" else []
        while pending:
            name = pending.pop()
            if name in reachable:
                continue
            reachable[name] = definitions[name]
            pending.extend(s["range"] for s in definitions[name]["slots"].values()
                           if s["representation"] == "inline_object")
        pooled, slot_definitions = _pool_slots(reachable)
        guide = {**identity, "scope": SCOPE,
                 "root_class": {k: v for k, v in root.items() if k != "slots"},
                 "slot": declared, "inline_classes": pooled, "slot_definitions": slot_definitions}
        text = _json(guide) + "\n"
        if len(text.encode("utf-8")) > MAX_SPEC_BYTES:
            raise SemanticGuidanceError("fitness_specification_byte_bound")
        specifications.append((slot, text))
    encoded = _json({**identity, "specifications": specifications}).encode("utf-8")
    if len(encoded) > MAX_SNAPSHOT_BYTES:
        raise SemanticGuidanceError("fitness_snapshot_byte_bound")
    # Selected-mode schema identity uses the familiar legacy shape but an
    # explicit stable display role. This is NOT the historical generation
    # digest for arbitrary path-named schemas. The old function is unchanged.
    generation = schema_digest._build_uncached(str(class_name), path, snapshot=captured)
    generation.schema_path = "captured schema " + str(sv.schema.id)
    schema = schema_digest.fingerprint(schema_digest.render(generation, vocabulary=vocabulary))
    return FitnessSchemaSnapshot(str(class_name), str(path), str(profile.name), profile_identity, sources,
                                 profile_sources, schema, hashlib.sha256(encoded).hexdigest(),
                                 tuple(specifications))


def selected_snapshot(schema_guidance, schema_snapshot, class_name, schema_path, profile):
    if schema_guidance is None:
        if schema_snapshot is not None:
            raise ValueError("fitness schema snapshot requires explicit guidance selection")
        return None
    validate_selection({SELECTOR: schema_guidance})
    if schema_snapshot is None:
        schema_snapshot = capture(class_name, schema_path, profile=profile)
    if type(schema_snapshot) is not FitnessSchemaSnapshot:
        raise ValueError("invalid fitness schema snapshot")
    return schema_snapshot.assert_context(class_name, schema_path, profile)
