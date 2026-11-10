"""Captured, explicitly selected BC1 schema and neutral term policy.

BC1 / 2026-10-27. No evaluation-context lookup, vocabulary injection, ontology
membership inference, or ambient profile selection occurs here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

LEGACY_FORMAT = "bc1_neutral_term_policy_v1"
FORMAT = "bc1_neutral_term_policy_v2"
TERM_SOURCES_ANNOTATION = "d4d:termSources"
TERM_SOURCE_FORMS_ANNOTATION = "d4d:termSourceIdentifierForms"
SCHEMA_HEADER = "\n\nBC1 COMPLETE CAPTURED SCHEMA CONTEXT\n"
FALLBACK = {("Instance", "data_topic"): ("GO", "MeSH", "EFO", "NCIT")}
_IRI = {
    "GO": ("http://purl.obolibrary.org/obo/GO_", "https://purl.obolibrary.org/obo/GO_"),
    "EFO": ("http://www.ebi.ac.uk/efo/EFO_", "https://www.ebi.ac.uk/efo/EFO_",
            "http://purl.obolibrary.org/obo/EFO_", "https://purl.obolibrary.org/obo/EFO_"),
    "NCIT": ("http://purl.obolibrary.org/obo/NCIT_", "https://purl.obolibrary.org/obo/NCIT_"),
    "MeSH": ("http://id.nlm.nih.gov/mesh/", "https://id.nlm.nih.gov/mesh/",
             "http://purl.bioontology.org/ontology/MESH/", "https://purl.bioontology.org/ontology/MESH/"),
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def contract_identity(version: int = 2) -> dict:
    """Semantic contract; source bytes are separately closed by BC1 selection."""
    if type(version) is not int or version not in (1, 2):
        raise ValueError("BC1 context contract version must be 1 or 2")
    if version == 1:
        return {"format": LEGACY_FORMAT, "schema_context": "complete_dataset_and_core_reachable_schema_v1",
                "request_shape": "D59: catalog once; no domain_of; bundle once in chunks; A14 downstream",
                "annotation": TERM_SOURCES_ANNOTATION,
                "fallback": [{"class": cls, "slot": slot, "sources": list(sources)}
                             for (cls, slot), sources in sorted(FALLBACK.items())],
                "iri_prefixes": {name: list(values) for name, values in sorted(_IRI.items())},
                "limitations": "Identifier source syntax only; membership and scientific support remain unverified."}
    return {"format": FORMAT, "schema_context": "complete_dataset_and_core_reachable_schema_v1",
            "request_shape": "D59: catalog once; no domain_of; bundle once in chunks; A14 downstream",
            "annotation": TERM_SOURCES_ANNOTATION,
            "forms_annotation": TERM_SOURCE_FORMS_ANNOTATION,
            "fallback": [],
            "limitations": "Identifier source syntax only; membership and scientific support remain unverified."}


def _annotation_value(annotations: Any, key: str, *, contract_version: int = 2) -> Any:
    if not isinstance(annotations, dict) or key not in annotations:
        return None
    annotation = annotations.get(key)
    if contract_version == 1 and isinstance(annotation, dict):
        return annotation.get("value")
    if isinstance(annotation, dict) and "value" in annotation and set(annotation) <= {"tag", "value", "annotations", "extensions"}:
        return annotation.get("value")
    return annotation


def _parse_identifier_forms(raw_forms: Any, *, declared_labels: list[str], cls: str, slot: str) -> dict:
    from . import audit_omissions as om
    if not isinstance(raw_forms, str) or not raw_forms.strip():
        raise ValueError(f"BC1 term-source identifier forms on {cls}.{slot} must be a JSON string")
    if any(unicodedata.category(c) in {"Cc", "Cf", "Zl", "Zp"} and c not in "\n\r\t" for c in raw_forms):
        raise ValueError(f"BC1 term-source identifier forms on {cls}.{slot} contain control characters")
    doc = om._mapping(raw_forms.encode("utf-8"), "BC1 term-source identifier forms", json_only=True)
    if type(doc) is not dict or set(doc) != {"version", "sources"}:
        raise ValueError(f"BC1 term-source identifier forms on {cls}.{slot} require exact version and sources keys")
    if type(doc["version"]) is not int or doc["version"] != 1:
        raise ValueError(f"BC1 term-source identifier forms on {cls}.{slot} require version 1")
    return _validate_identifier_form_entries(doc["sources"], declared_labels=declared_labels, cls=cls, slot=slot)


def _validate_identifier_form_entries(entries: Any, *, declared_labels: list[str], cls: str, slot: str) -> dict:
    if type(entries) is not list or not entries:
        raise ValueError(f"BC1 term-source identifier forms on {cls}.{slot} require a nonempty sources list")
    seen_ids: set[str] = set()
    seen_labels: set[str] = set()
    normalized_sources: list[dict] = []
    all_curies: list[tuple[str, str, str, str]] = []
    all_iris: list[tuple[str, str]] = []
    for entry in entries:
        if type(entry) is not dict or set(entry) != {"id", "label", "curies", "iri_bases"}:
            raise ValueError(f"BC1 term-source identifier form entry on {cls}.{slot} has invalid keys")
        source_id = entry["id"]
        label = entry["label"]
        curies = entry["curies"]
        iri_bases = entry["iri_bases"]
        if (type(source_id) is not str or not source_id or source_id != source_id.strip()
                or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id)):
            raise ValueError(f"BC1 term-source identifier form on {cls}.{slot} has invalid id {source_id!r}")
        if source_id in seen_ids:
            raise ValueError(f"BC1 duplicate term-source id {source_id!r} on {cls}.{slot}")
        seen_ids.add(source_id)
        if (type(label) is not str or not label or label != label.strip()
                or any(unicodedata.category(c) in {"Cc", "Cf", "Zl", "Zp"} for c in label)):
            raise ValueError(f"BC1 term-source identifier form on {cls}.{slot} has invalid label {label!r}")
        if label in seen_labels:
            raise ValueError(f"BC1 duplicate term-source label {label!r} on {cls}.{slot}")
        seen_labels.add(label)
        if type(curies) is not list or type(iri_bases) is not list or (not curies and not iri_bases):
            raise ValueError(f"BC1 term source {label!r} on {cls}.{slot} requires nonempty curies or iri_bases lists")
        normalized_curies: list[dict[str, str]] = []
        for c in curies:
            if type(c) is not dict or set(c) != {"prefix", "local_prefix"}:
                raise ValueError(f"BC1 term source {label!r} on {cls}.{slot} has invalid curie declaration")
            prefix, local_prefix = c["prefix"], c["local_prefix"]
            if (type(prefix) is not str or not prefix
                    or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9._-]*", prefix)
                    or prefix.lower() in {"http", "https"}):
                raise ValueError(f"BC1 term source {label!r} on {cls}.{slot} has invalid CURIE prefix {prefix!r}")
            if (type(local_prefix) is not str or ":" in local_prefix
                    or any(ch.isspace() or unicodedata.category(ch) in {"Cc", "Cf", "Zl", "Zp"} for ch in local_prefix)):
                raise ValueError(f"BC1 term source {label!r} on {cls}.{slot} has invalid CURIE local_prefix {local_prefix!r}")
            for _other_id, other_prefix, other_local, _other_head in all_curies:
                if prefix == other_prefix and (local_prefix.startswith(other_local) or other_local.startswith(local_prefix)):
                    raise ValueError(f"BC1 conflicting CURIE identifier forms on {cls}.{slot}: "
                                     f"{prefix}:{local_prefix} and {other_prefix}:{other_local}")
            all_curies.append((source_id, prefix, local_prefix, f"{prefix}:{local_prefix}"))
            normalized_curies.append({"prefix": prefix, "local_prefix": local_prefix})
        normalized_iris: list[str] = []
        for base in iri_bases:
            if (type(base) is not str or not base or base != base.strip()
                    or any(ch.isspace() or unicodedata.category(ch) in {"Cc", "Cf", "Zl", "Zp"} for ch in base)
                    # D98/#5555: retain the designed http(s), nonempty-path
                    # rule; extending the scheme set needs an owner decision.
                    or not re.fullmatch(r"https?://[^/]+/.+", base)):
                raise ValueError(f"BC1 term source {label!r} on {cls}.{slot} has invalid IRI base {base!r}")
            for _other_id, other_base in all_iris:
                if base.startswith(other_base) or other_base.startswith(base):
                    raise ValueError(f"BC1 conflicting IRI base declarations on {cls}.{slot}: {base!r} and {other_base!r}")
            all_iris.append((source_id, base))
            normalized_iris.append(base)
        normalized_sources.append({
            "id": source_id, "label": label,
            "curies": normalized_curies, "iri_bases": normalized_iris,
        })
    declared_set = set(declared_labels)
    missing = sorted(declared_set - seen_labels)
    if missing:
        raise ValueError(f"BC1 term source {missing[0]!r} has no accepted identifier form")
    undeclared = sorted(seen_labels - declared_set)
    if undeclared:
        raise ValueError(f"BC1 term-source identifier forms on {cls}.{slot} declare undeclared label {undeclared[0]!r}")
    return {
        "identifier_forms": normalized_sources,
        "curie_prefixes": sorted({head for _sid, _p, _lp, head in all_curies}),
        "iri_prefixes": sorted({base for _sid, base in all_iris}),
    }


def _sources(catalog: dict, *, contract_version: int = 2) -> dict:
    if type(contract_version) is not int or contract_version not in (1, 2):
        raise ValueError("BC1 context contract version must be 1 or 2")
    result = {}
    for cls, row in sorted(catalog["classes"].items()):
        for slot, info in sorted(row["slots"].items()):
            annotations = info["definition"].get("annotations") or {}
            annotation = _annotation_value(annotations, TERM_SOURCES_ANNOTATION,
                                           contract_version=contract_version)
            forms_annotation = _annotation_value(annotations, TERM_SOURCE_FORMS_ANNOTATION)
            if annotation is not None:
                if not isinstance(annotation, str) or not annotation.strip():
                    raise ValueError("BC1 term-source annotation requires explicit source names")
                # schema_digest.term_sources_of preserves the declared display
                # text (it does not tokenize it). Only comma/semicolon delimit
                # labels; an Oxford-list conjunction belongs to the last item.
                if any(unicodedata.category(c) in {"Cc", "Cf", "Zl", "Zp"} for c in annotation):
                    raise ValueError("BC1 term-source annotation has unsupported source syntax")
                names = [v.strip() for v in re.split(r",|;", annotation)]
                if len(names) > 1 and names[-1].startswith("and "):
                    names[-1] = names[-1][4:].strip()
                if any(not v for v in names) or (contract_version == 2 and len(names) != len(set(names))):
                    raise ValueError("BC1 term-source annotation has unsupported source syntax")
                basis = "schema_annotation"
            elif contract_version == 1:
                names = list(FALLBACK.get((cls, slot), ()))
                basis = "declared_schema_digest_fallback"
            else:
                if forms_annotation is not None:
                    raise ValueError(f"BC1 slot {cls}.{slot} declares {TERM_SOURCE_FORMS_ANNOTATION} without {TERM_SOURCES_ANNOTATION}")
                names = []
                basis = "schema_annotation"
            if names:
                entry = {"sources": sorted(set(names)), "basis": basis}
                if contract_version == 2 and forms_annotation is not None:
                    entry.update(_parse_identifier_forms(
                        forms_annotation, declared_labels=entry["sources"], cls=cls, slot=slot))
                result.setdefault(cls, {})[slot] = entry
    return result


def _schema_prefixes(schema_snapshot) -> dict[str, str]:
    from . import audit_omissions as om
    prefixes: dict[str, str] = {}
    for _name, _path, raw in schema_snapshot.sources:
        doc = om._mapping(raw, "BC1 schema", _schema_events=True)
        raw_prefixes = doc.get("prefixes") or {}
        if not isinstance(raw_prefixes, dict):
            raise ValueError("BC1 schema prefixes must be a mapping")
        for key, value in raw_prefixes.items():
            ref = value.get("prefix_reference") if isinstance(value, dict) else value
            if not isinstance(key, str) or not key or not isinstance(ref, str) or not ref:
                raise ValueError(f"BC1 schema prefix {key!r} has an invalid reference")
            if key in prefixes and prefixes[key] != ref:
                raise ValueError(f"BC1 schema closure has conflicting prefix declaration for {key!r}")
            prefixes[key] = ref
    return prefixes


def _schema_pin(snapshot) -> dict:
    return {"root": str(snapshot.sources[0][1]), "sources": [
        {"path": str(path), "sha256": _sha(raw), "bytes": len(raw)}
        for _name, path, raw in snapshot.sources]}


def _selected_contract_version(selection: dict, explicit: int | None = None) -> int:
    if explicit is not None:
        if type(explicit) is not int or explicit not in (1, 2):
            raise ValueError("BC1 context contract version must be 1 or 2")
        return explicit
    contract = selection.get("bounded_carry", {}).get("contract")
    if isinstance(contract, dict):
        ctx = contract.get("context")
        if isinstance(ctx, dict) and ctx.get("format") == LEGACY_FORMAT:
            return 1
    return 2


def derive_term_policy(*, selection: dict, context_raw: bytes, schema_snapshot,
                       contract_version: int | None = None) -> dict | None:
    """Derive only from the complete captured registration and captured bytes."""
    from . import audit_omissions as om
    from .profiles import profile_named
    if (type(selection) is not dict or type(selection.get("bounded_carry")) is not dict
            or type(selection["bounded_carry"].get("version")) is not int
            or selection["bounded_carry"]["version"] != 1):
        raise ValueError("BC1 context requires explicit bounded_carry.version 1")
    version = _selected_contract_version(selection, contract_version)
    inputs = selection.get("inputs", {})
    profile = inputs.get("profile", {})
    if (set(profile) != {"name", "basis", "vocabulary"}
            or not isinstance(profile["name"], str) or not profile["name"].strip()
            or not isinstance(profile["basis"], str) or not profile["basis"].strip()):
        raise ValueError("BC1 requires the explicit captured profile authority")
    declared_pin = profile_named(profile["name"]).pin_path
    vocabulary = profile["vocabulary"]
    if ((declared_pin is None) != (vocabulary is None)
            or (vocabulary is not None and (not isinstance(vocabulary, dict)
                or vocabulary.get("path") != str(Path(declared_pin).absolute())
                or not vocabulary.get("sha256")))):
        raise ValueError(f"BC1 profile {profile['name']!r} vocabulary pin differs from its declared profile")
    pin = inputs.get("context", {})
    if pin.get("sha256") != _sha(context_raw) or pin.get("bytes") != len(context_raw):
        raise ValueError("BC1 omission context differs from its registered byte pin")
    if inputs.get("full_schema") != _schema_pin(schema_snapshot):
        raise ValueError("BC1 schema differs from its registered closure")
    context = om._mapping(context_raw, "BC1 omission context", json_only=True)
    if om._shape(context, json.loads(om._asset("context.schema.json"))):
        raise ValueError("BC1 requires authentic omission_context_v1, not evaluation rationale")
    catalog = om._schema(schema_snapshot.sources[0][1], schema_snapshot=schema_snapshot)
    if profile["vocabulary"] is not None:
        if not isinstance(profile["vocabulary"], dict) or not profile["vocabulary"].get("sha256"):
            raise ValueError("BC1 profile is missing its declared vocabulary pin")
        required = {str(name) for cls in catalog["classes"].values() for slot in cls["slots"].values()
                    for name in slot["definition"].get("values_from", [])}
        if required - set(context["vocabulary"]):
            raise ValueError("BC1 context is missing a declared pinned vocabulary")
        return None
    if context["vocabulary"] != {}:
        raise ValueError("BC1 neutral context may not inject an undeclared vocabulary")
    sources = _sources(catalog, contract_version=version)
    schema_prefixes = _schema_prefixes(schema_snapshot) if version == 2 else None
    _require_identifier_forms(sources, schema_prefixes=schema_prefixes, contract_version=version)
    policy = {"format": FORMAT if version == 2 else LEGACY_FORMAT, "profile": profile,
              "context_sha256": _sha(context_raw),
              "context_canonical_sha256": _sha(_canonical(context)),
              "schema_catalog_sha256": _sha(_canonical(catalog)),
              "schema_sources": catalog["sources"], "external_terms": sources,
              "contract": contract_identity(version)}
    validate_term_policy(policy, catalog=catalog, context=context, schema_snapshot=schema_snapshot)
    return policy


def validate_term_policy(policy: dict, *, catalog: dict, context: dict, schema_snapshot=None) -> None:
    """Check captured policy shape/derivation; never consult current files."""
    keys = {"format", "profile", "context_sha256", "context_canonical_sha256",
            "schema_catalog_sha256", "schema_sources", "external_terms", "contract"}
    if type(policy) is not dict or set(policy) != keys or policy["format"] not in {FORMAT, LEGACY_FORMAT}:
        raise ValueError("invalid BC1 term policy")
    version = 2 if policy["format"] == FORMAT else 1
    profile = policy["profile"]
    if (type(profile) is not dict or set(profile) != {"name", "basis", "vocabulary"}
            or not isinstance(profile["name"], str) or not profile["name"].strip()
            or profile["vocabulary"] is not None
            or not isinstance(profile["basis"], str) or not profile["basis"].strip()
            or context.get("vocabulary") != {}):
        raise ValueError("BC1 policy is not an explicit neutral authority")
    if (not isinstance(policy["context_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", policy["context_sha256"])
            or policy["context_canonical_sha256"] != _sha(_canonical(context))
            or policy["schema_catalog_sha256"] != _sha(_canonical(catalog))
            or policy["schema_sources"] != catalog["sources"]
            or policy["external_terms"] != _sources(catalog, contract_version=version)
            or policy["contract"] != contract_identity(version)):
        raise ValueError("BC1 term policy differs from its captured schema/context derivation")
    schema_prefixes = _schema_prefixes(schema_snapshot) if (version == 2 and schema_snapshot is not None) else None
    _require_identifier_forms(policy["external_terms"], schema_prefixes=schema_prefixes, contract_version=version)


def _curie_prefixes(source: str) -> tuple[str, ...]:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9._-]*", source):
        return ()
    return (source, "MESH") if source == "MeSH" else (source,)


def _require_identifier_forms(terms: dict, *, schema_prefixes: dict[str, str] | None = None,
                              contract_version: int = 2) -> None:
    if type(contract_version) is not int or contract_version not in (1, 2):
        raise ValueError("BC1 context contract version must be 1 or 2")
    if contract_version == 1:
        for slots in terms.values():
            for declaration in slots.values():
                for source in declaration["sources"]:
                    if not _curie_prefixes(source) and not _IRI.get(source):
                        raise ValueError(f"BC1 term source {source!r} has no accepted identifier form")
        return
    for cls, slots in sorted(terms.items()):
        if not isinstance(slots, dict):
            raise ValueError("invalid BC1 term policy")
        for slot, declaration in sorted(slots.items()):
            if not isinstance(declaration, dict):
                raise ValueError("invalid BC1 term policy")
            sources = declaration.get("sources")
            if not isinstance(sources, list) or not sources:
                raise ValueError(f"BC1 slot {cls}.{slot} has no declared sources")
            forms = declaration.get("identifier_forms")
            if not isinstance(forms, list) or not forms:
                raise ValueError(f"BC1 term source {sources[0]!r} has no accepted identifier form")
            validated = _validate_identifier_form_entries(forms, declared_labels=sources, cls=cls, slot=slot)
            if (declaration.get("identifier_forms") != validated["identifier_forms"]
                    or declaration.get("curie_prefixes") != validated["curie_prefixes"]
                    or declaration.get("iri_prefixes") != validated["iri_prefixes"]):
                raise ValueError(f"BC1 slot {cls}.{slot} identifier form prefixes differ from declared forms")
            if schema_prefixes is not None:
                for item in forms:
                    iri_bases = set(item.get("iri_bases", []))
                    for c in item.get("curies", []):
                        prefix = c["prefix"]
                        local_prefix = c["local_prefix"]
                        if prefix not in schema_prefixes:
                            # Annotation forms are self-contained; schema prefixes
                            # only constrain expansions when independently declared.
                            continue
                        expanded = schema_prefixes[prefix] + local_prefix
                        if iri_bases and expanded not in iri_bases:
                            raise ValueError(f"BC1 term-source CURIE prefix {prefix!r} on {cls}.{slot} "
                                             f"expands to {expanded!r}, which is not in declared iri_bases")


def permits_unbound_slot(policy: dict, cls: str, field: str) -> bool:
    return bool(policy["external_terms"].get(cls, {}).get(field, {}).get("sources"))


def validate_term_value(value: Any, *, policy: dict, cls: str, field: str) -> None:
    """Accept source syntax only. Null is preserved as an absent assertion."""
    if value is None:
        return
    if type(policy) is not dict or not isinstance(policy.get("external_terms"), dict):
        raise ValueError("invalid BC1 term policy")
    if (not isinstance(value, str) or not value or value != value.strip()
            or any(c.isspace() or (policy.get("format") != LEGACY_FORMAT
                   and unicodedata.category(c) in {"Cc", "Cf", "Zl", "Zp"}) for c in value)):
        raise ValueError("BC1 controlled term requires a declared external source identifier")
    declaration = policy["external_terms"].get(cls, {}).get(field) or {}
    fmt = policy.get("format")
    if fmt == LEGACY_FORMAT:
        for source in declaration.get("sources", []):
            prefixes = _curie_prefixes(source)
            if any(value.startswith(prefix + ":") and len(value) > len(prefix) + 1 for prefix in prefixes):
                return
            if any(value.startswith(prefix) and len(value) > len(prefix) for prefix in _IRI.get(source, ())):
                return
        raise ValueError("BC1 controlled term names an undeclared vocabulary or external term source")
    if fmt != FORMAT:
        raise ValueError("invalid BC1 term policy")
    if not declaration:
        raise ValueError("BC1 controlled term names an undeclared vocabulary or external term source")
    _require_identifier_forms({cls: {field: declaration}}, contract_version=2)
    for prefix in declaration.get("curie_prefixes", ()):
        if value.startswith(prefix) and len(value) > len(prefix):
            return
    for prefix in declaration.get("iri_prefixes", ()):
        if value.startswith(prefix) and len(value) > len(prefix):
            return
    raise ValueError("BC1 controlled term names an undeclared vocabulary or external term source")


def _core_catalog(snapshot):
    """Capture CoreDataset semantics without assuming that it imports Dataset."""
    from pathlib import Path
    from .schema_snapshot import SchemaSnapshot, _capture_schema
    from .schema_view import captured_view
    from linkml_runtime.dumpers import json_dumper
    from . import audit_omissions as om
    if type(snapshot) is not SchemaSnapshot or not isinstance(snapshot.sources, tuple) or not snapshot.sources:
        raise ValueError("BC1 complete schema context requires an immutable core schema closure")
    frozen = {}
    total = 0
    for name, path, raw in snapshot.sources:
        if (not isinstance(name, str) or not name or not isinstance(path, Path) or not path.is_absolute()
                or ".." in path.parts or path in frozen or type(raw) is not bytes):
            raise ValueError("BC1 core schema has an invalid captured source")
        total += len(raw)
        if total > om.MAX_SCHEMA_BYTES:
            raise ValueError("BC1 core schema closure exceeds its byte bound")
        om._mapping(raw, "BC1 core schema", _schema_events=True)
        frozen[path] = raw

    def read(path):
        if path not in frozen:
            raise ValueError("BC1 core schema import is outside its captured closure")
        return frozen[path]

    replay = _capture_schema(snapshot.sources[0][1], read, strict=True)
    if replay.sources != snapshot.sources:
        raise ValueError("BC1 core schema snapshot is not its exact import closure")
    classes, enums, pending = {}, {}, ["CoreDataset"]
    with captured_view(replay) as view:
        while pending:
            name = pending.pop()
            if name in classes:
                continue
            cls = view.get_class(name)
            if cls is None:
                raise ValueError("BC1 captured core schema is missing class " + name)
            definition = json.loads(json_dumper.dumps(cls))
            slots = {}
            classes[name] = {"definition": {k: v for k, v in definition.items()
                if k not in {"attributes", "slot_usage", "slots"}}, "slots": slots}
            pending.extend(str(parent) for parent in [definition.get("is_a"), *definition.get("mixins", [])] if parent)
            for slot in view.class_induced_slots(name):
                raw = json.loads(json_dumper.dumps(slot))
                target = view.get_class(slot.range) if slot.range else None
                slots[str(slot.name)] = {"definition": raw, "inline": bool(target and view.is_inlined(slot)),
                                         "range_class": bool(target)}
                if target:
                    pending.append(str(slot.range))
                enum = view.get_enum(slot.range) if slot.range else None
                if enum:
                    enums[str(slot.range)] = json.loads(json_dumper.dumps(enum))
    return {"root_class": "CoreDataset", "classes": classes, "enums": enums,
            "sources": [{"name": name, "sha256": _sha(raw)} for name, _path, raw in replay.sources]}


def schema_context(captured, record: str | None, *, assigned_paths=None) -> str:
    """Full reachable definitions, exact input text and structural owner roles.

    Assignment pins scope; it never deletes descriptions, conditional semantics,
    unoccupied reachable classes, false/null/list values or source text.
    """
    from . import audit_omissions as om
    catalog = model_catalog(om._schema(captured.full_schema.sources[0][1], schema_snapshot=captured.full_schema))
    core_catalog = model_catalog(_core_catalog(captured.core_schema))
    owners = []
    if record is not None:
        document = om._mapping(record.encode("utf-8"), "BC1 whole record")

        def walk(value, cls, pointer, depth=0):
            if depth > om.MAX_DEPTH:
                raise ValueError("BC1 schema owner traversal depth exceeded")
            if not isinstance(value, dict):
                return
            owners.append({"path": pointer, "class": cls})
            slots = catalog["classes"][cls]["slots"]
            for field, child in value.items():
                info = slots.get(field)
                if info is None or not info["inline"]:
                    continue
                target = info["definition"]["range"]
                at = pointer + "/" + field.replace("~", "~0").replace("/", "~1")
                if isinstance(child, list):
                    for index, member in enumerate(child):
                        walk(member, target, at + "/" + str(index), depth + 1)
                else:
                    walk(child, target, at, depth + 1)
        walk(document, "Dataset", "")
    if assigned_paths is not None and (not isinstance(assigned_paths, (tuple, list))
            or any(not isinstance(p, str) for p in assigned_paths)):
        raise ValueError("BC1 assigned paths must be an explicit string sequence")
    return SCHEMA_HEADER + _canonical({"format": "bc1_complete_schema_context_v1",
        "schema": _schema_pin(captured.full_schema), "catalog": catalog,
        "core_schema": _schema_pin(captured.core_schema), "core_catalog": core_catalog,
        "record_yaml": record, "owners": owners,
        "assigned_paths": None if assigned_paths is None else list(assigned_paths),
        "scope": "Captured schema semantics and source record; no applicability or scientific-support verdict."}).decode("utf-8")


def model_catalog(value):
    """D59: omit the redundant inverse class index, without mutating host evidence."""
    result = deepcopy(value)
    for cls in result["classes"].values():
        for slot in cls["slots"].values():
            slot["definition"].pop("domain_of", None)
    return result


def downstream_schema_context(spec, record=None):
    """D59: use the unchanged A14 renderer on freshly checked captured inputs.

    The protected shared-generation public wrapper selects the complete BC1
    context. Call its existing A14 implementation explicitly for these phases.

    RunSpec boundary: validated-caller

    RunSpec precondition: The guarded request builder or validated transport checker
    supplies the same D76-admitted selection and its matching record, when present.
    Captured schema authority is rechecked before A14 formatting; this helper does
    not admit independent execution.
    """
    from . import shared_generation as shared
    captured = shared.assert_current(spec)
    return shared.memo(spec, 'bc1_downstream_a14',
        [_canonical(_schema_pin(captured.full_schema)),
         *[raw for _name, _path, raw in captured.full_schema.sources], _canonical(record)],
        lambda: shared._schema_context(captured, record))


def model_request(inner, schema_text):
    """One catalog and one bundle on the wire; original checked request stays host-side."""
    if not schema_text.startswith(SCHEMA_HEADER):
        raise ValueError("BC1 typed request requires its complete captured schema context")
    catalog = json.loads(schema_text[len(SCHEMA_HEADER):])["catalog"]
    projected = deepcopy(inner)
    payload = projected["payload"]
    shared = payload.get("shared_context", payload)
    if model_catalog(shared["schema"]) != catalog:
        raise ValueError("BC1 duplicate schema differs from the captured catalog")
    shared["schema"] = {"ref": "schema_context.catalog", "sha256": _sha(_canonical(catalog))}
    if "shared_context" in payload:
        del shared["bundle"]
        shared["bundle_ref"] = {"ref": "payload.dictionary.chunks",
                                "dictionary_sha256": payload["dictionary"]["sha256"]}
    # request_sha256 continues to identify the complete host request checked by
    # the response validator. The outer binding separately pins this model view.
    return projected


def generation_context(captured) -> str:
    """The same complete source authority for pure sizing and live BC1 calls."""
    from . import shared_generation as shared
    inputs = captured.document()["inputs"]
    context = inputs["context"]
    profile = deepcopy(inputs["profile"])
    vocabulary = profile["vocabulary"]
    if vocabulary is not None:
        profile["vocabulary"] = {"identity": vocabulary,
            "raw_text": captured.raw(vocabulary["path"]).decode("utf-8")}
    return shared.GENERATION_CONTEXT_HEADER + shared.canonical({
        "context": {"identity": context, "raw_json": captured.raw(context["path"]).decode("utf-8")},
        "profile": profile, "source_manifest": inputs["source_manifest"],
        "scope": "Caller-declared generation scope, source policy and vocabulary; "
                 "not a scientific applicability or support verdict."}).decode("utf-8")
