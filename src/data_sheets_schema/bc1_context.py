"""Captured, explicitly selected BC1 schema and neutral term policy.

BC1 / 2026-10-27. No evaluation-context lookup, vocabulary injection, ontology
membership inference, or ambient profile selection occurs here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any

FORMAT = "bc1_neutral_term_policy_v1"
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


def contract_identity() -> dict:
    """Semantic contract; source bytes are separately closed by BC1 selection."""
    return {"format": FORMAT, "schema_context": "complete_dataset_and_core_reachable_schema_v1",
            "annotation": "d4d:termSources",
            "fallback": [{"class": cls, "slot": slot, "sources": list(sources)}
                         for (cls, slot), sources in sorted(FALLBACK.items())],
            "iri_prefixes": {name: list(values) for name, values in sorted(_IRI.items())},
            "limitations": "Identifier source syntax only; membership and scientific support remain unverified."}


def _sources(catalog: dict) -> dict:
    result = {}
    for cls, row in sorted(catalog["classes"].items()):
        for slot, info in sorted(row["slots"].items()):
            annotations = info["definition"].get("annotations") or {}
            annotation = annotations.get("d4d:termSources")
            if isinstance(annotation, dict):
                annotation = annotation.get("value")
            if annotation is not None:
                if not isinstance(annotation, str) or not annotation.strip():
                    raise ValueError("BC1 term-source annotation requires explicit source names")
                names = [v.strip() for v in re.split(r",|;|\s+and\s+", annotation)]
                if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", v) for v in names):
                    raise ValueError("BC1 term-source annotation has unsupported source syntax")
                basis = "schema_annotation"
            else:
                names = list(FALLBACK.get((cls, slot), ()))
                basis = "declared_schema_digest_fallback"
            if names:
                result.setdefault(cls, {})[slot] = {"sources": sorted(set(names)), "basis": basis}
    return result


def _schema_pin(snapshot) -> dict:
    return {"root": str(snapshot.sources[0][1]), "sources": [
        {"path": str(path), "sha256": _sha(raw), "bytes": len(raw)}
        for _name, path, raw in snapshot.sources]}


def derive_term_policy(*, selection: dict, context_raw: bytes, schema_snapshot) -> dict | None:
    """Derive only from the complete captured registration and captured bytes."""
    from . import audit_omissions as om
    if (type(selection) is not dict or type(selection.get("bounded_carry")) is not dict
            or type(selection["bounded_carry"].get("version")) is not int
            or selection["bounded_carry"]["version"] != 1):
        raise ValueError("BC1 context requires explicit bounded_carry.version 1")
    inputs = selection.get("inputs", {})
    profile = inputs.get("profile", {})
    if set(profile) != {"name", "basis", "vocabulary"} or not isinstance(profile["basis"], str) or not profile["basis"].strip():
        raise ValueError("BC1 requires the explicit captured profile authority")
    pin = inputs.get("context", {})
    if pin.get("sha256") != _sha(context_raw) or pin.get("bytes") != len(context_raw):
        raise ValueError("BC1 omission context differs from its registered byte pin")
    if inputs.get("full_schema") != _schema_pin(schema_snapshot):
        raise ValueError("BC1 schema differs from its registered closure")
    context = om._mapping(context_raw, "BC1 omission context", json_only=True)
    if om._shape(context, json.loads(om._asset("context.schema.json"))):
        raise ValueError("BC1 requires authentic omission_context_v1, not evaluation rationale")
    catalog = om._schema(schema_snapshot.sources[0][1], schema_snapshot=schema_snapshot)
    if profile["name"] == "bridge2ai":
        if not isinstance(profile["vocabulary"], dict) or not profile["vocabulary"].get("sha256"):
            raise ValueError("BC1 bridge2ai profile is missing its declared vocabulary pin")
        required = {str(name) for cls in catalog["classes"].values() for slot in cls["slots"].values()
                    for name in slot["definition"].get("values_from", [])}
        if required - set(context["vocabulary"]):
            raise ValueError("BC1 bridge2ai context is missing a declared pinned vocabulary")
        return None
    if profile["name"] != "neutral" or profile["vocabulary"] is not None:
        raise ValueError("BC1 neutral policy requires explicit neutral profile without a vocabulary pin")
    if context["vocabulary"] != {}:
        raise ValueError("BC1 neutral context may not inject an undeclared vocabulary")
    policy = {"format": FORMAT, "profile": profile,
              "context_sha256": _sha(context_raw),
              "context_canonical_sha256": _sha(_canonical(context)),
              "schema_catalog_sha256": _sha(_canonical(catalog)),
              "schema_sources": catalog["sources"], "external_terms": _sources(catalog),
              "contract": contract_identity()}
    validate_term_policy(policy, catalog=catalog, context=context)
    return policy


def validate_term_policy(policy: dict, *, catalog: dict, context: dict) -> None:
    """Check captured policy shape/derivation; never consult current files."""
    keys = {"format", "profile", "context_sha256", "context_canonical_sha256",
            "schema_catalog_sha256", "schema_sources", "external_terms", "contract"}
    if type(policy) is not dict or set(policy) != keys or policy["format"] != FORMAT:
        raise ValueError("invalid BC1 term policy")
    profile = policy["profile"]
    if (type(profile) is not dict or set(profile) != {"name", "basis", "vocabulary"}
            or profile["name"] != "neutral" or profile["vocabulary"] is not None
            or not isinstance(profile["basis"], str) or not profile["basis"].strip()
            or context.get("vocabulary") != {}):
        raise ValueError("BC1 policy is not an explicit neutral authority")
    if (not isinstance(policy["context_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", policy["context_sha256"])
            or policy["context_canonical_sha256"] != _sha(_canonical(context))
            or policy["schema_catalog_sha256"] != _sha(_canonical(catalog))
            or policy["schema_sources"] != catalog["sources"]
            or policy["external_terms"] != _sources(catalog)
            or policy["contract"] != contract_identity()):
        raise ValueError("BC1 term policy differs from its captured schema/context derivation")


def permits_unbound_slot(policy: dict, cls: str, field: str) -> bool:
    return bool(policy["external_terms"].get(cls, {}).get(field, {}).get("sources"))


def validate_term_value(value: Any, *, policy: dict, cls: str, field: str) -> None:
    """Accept source syntax only. Null is preserved as an absent assertion."""
    if value is None:
        return
    if not isinstance(value, str) or not value or value != value.strip() or any(c.isspace() for c in value):
        raise ValueError("BC1 controlled term requires a declared external source identifier")
    sources = policy["external_terms"].get(cls, {}).get(field, {}).get("sources", [])
    for source in sources:
        prefixes = (source, "MESH") if source == "MeSH" else (source,)
        if any(value.startswith(prefix + ":") and len(value) > len(prefix) + 1 for prefix in prefixes):
            return
        if any(value.startswith(prefix) and len(value) > len(prefix) for prefix in _IRI.get(source, ())):
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
    catalog = om._schema(captured.full_schema.sources[0][1], schema_snapshot=captured.full_schema)
    core_catalog = _core_catalog(captured.core_schema)
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
