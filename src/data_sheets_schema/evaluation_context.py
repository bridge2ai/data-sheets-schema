"""Explicit applicability and evidence scope for reusable D4D evaluations.

Missing scoring fields never prove non-applicability. Unknown context stays
in the denominator, with its uncertainty recorded separately.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
PREDICATES = frozenset({
    "human_subjects", "regulated_access", "shared_dataset", "ml_training_dataset",
    "data_collection", "data_processing", "processing_software",
})
COLLECTION_POLICY = "minimum_per_item_across_all_resource_datasets_v1"
CONTEXT_VERSION = "d4d-evaluation-context-1"


def identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


def normalize_context(value: dict | None) -> dict[str, dict]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("evaluation context must be a mapping of named predicates")
    unknown = set(value) - PREDICATES
    if unknown:
        raise ValueError(f"unknown applicability predicates: {', '.join(sorted(map(str, unknown)))}")
    result = {}
    for key, declaration in value.items():
        if declaration is None or isinstance(declaration, bool):
            result[key] = {"value": declaration, "evidence": "Explicit caller declaration"}
            continue
        if not isinstance(declaration, dict) or set(declaration) - {"value", "evidence"}:
            raise ValueError(f"{key} must be a boolean, null, or a value/evidence mapping")
        if "value" not in declaration or (
                declaration["value"] is not None and not isinstance(declaration["value"], bool)):
            raise ValueError(f"{key}.value must be a boolean or null")
        evidence = declaration.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError(f"{key}.evidence must explain the declaration")
        result[key] = dict(declaration)
    return result


def load_context(path: Path | None) -> dict[str, dict]:
    return normalize_context(yaml.safe_load(path.read_bytes()) if path is not None else None)


@dataclass(frozen=True)
class Applicability:
    value: bool | None
    evidence: str

    @property
    def applicable(self) -> bool:
        return self.value is not False

    @property
    def status(self) -> str:
        return "unknown" if self.value is None else "applicable" if self.value else "not_applicable"


def applicability(rule: Any, context: dict[str, dict]) -> Applicability:
    if rule is None or rule == "always":
        return Applicability(True, "This item applies to every dataset")
    if isinstance(rule, str):
        if rule not in PREDICATES:
            raise ValueError(f"unknown applicability predicate: {rule}")
        declared = context.get(rule)
        if declared is None:
            return Applicability(None, f"{rule}: not declared; retained in the denominator")
        return Applicability(declared["value"], f"{rule}: {declared['evidence']}")
    if not isinstance(rule, dict) or len(rule) != 1 or next(iter(rule)) not in {"all", "any"}:
        raise ValueError("applies_to must be a named predicate or an all/any expression")
    operator, children = next(iter(rule.items()))
    if not isinstance(children, list) or not children:
        raise ValueError("all/any applicability expressions require at least one predicate")
    decisions = [applicability(child, context) for child in children]
    values = [decision.value for decision in decisions]
    if operator == "all":
        value = False if False in values else True if all(v is True for v in values) else None
    else:
        value = True if True in values else False if all(v is False for v in values) else None
    return Applicability(value, f"{operator}: " + "; ".join(d.evidence for d in decisions))


def unwrap_document(data: Any) -> dict:
    if not isinstance(data, dict):
        raise ValueError("a D4D evaluation input must be a mapping")
    wrappers = {"Dataset", "CoreDataset", "DatasetCollection", "CoreDatasetCollection"} & set(data)
    if wrappers:
        if len(wrappers) != 1 or len(data) != 1:
            raise ValueError("a class-wrapped D4D must contain exactly one dataset or collection")
        wrapper = next(iter(wrappers))
        data = data[wrapper]
        if not isinstance(data, dict):
            raise ValueError("a D4D class wrapper must contain a mapping")
        if wrapper.endswith("Collection") and not data.get("resources"):
            raise ValueError("a D4D collection must contain resource datasets")
    return data


def load_document(path: Path) -> tuple[dict, str]:
    raw = Path(path).read_bytes()
    return unwrap_document(yaml.safe_load(raw)), hashlib.sha256(raw).hexdigest()


def dataset_units(data: dict, prefix: str = "#") -> list[tuple[str, dict]]:
    """Every terminal dataset, retaining paths and never inheriting a sibling."""
    if "resources" not in data:
        return [(prefix, data)]
    resources = data["resources"]
    if not isinstance(resources, list) or not resources:
        raise ValueError(f"{prefix}/resources must contain dataset mappings")
    units = []
    for index, child in enumerate(resources):
        if not isinstance(child, dict):
            raise ValueError(f"{prefix}/resources/{index} is not a dataset mapping")
        units.extend(dataset_units(unwrap_document(child), f"{prefix}/resources/{index}"))
    return units


# These are representations of the same dataset/distribution properties in
# full and Core D4Ds. Dataset identity never falls back to a file's identity.
FIELD_ALIASES = {
    "format": ("distributions.format", "distribution_formats.format", "file_collections.resources.format"),
    "encoding": ("distributions.encoding", "file_collections.resources.encoding"),
    "media_type": ("distributions.media_type", "distribution_formats.media_type"),
    "compression": ("distributions.compression", "file_collections.compression"),
    "distribution_formats": ("distributions",),
    "total_size_bytes": ("distributions.bytes",),
    "file_collections.total_bytes": ("distributions.bytes",),
    "file_collections.compression": ("distributions.compression",),
    "conforms_to": ("distributions.conforms_to", "distributions.conforms_to_standard"),
}


def field_values(data: dict, field: str) -> list[tuple[str, Any]]:
    """Traverse lists in dot paths and report the exact evidence locations."""
    def walk(node, parts, pointer):
        if isinstance(node, list):
            return [entry for index, child in enumerate(node)
                    for entry in walk(child, parts, f"{pointer}/{index}")]
        if not parts:
            return [(pointer, node)]
        if not isinstance(node, dict) or parts[0] not in node:
            return []
        key = parts[0]
        escaped = key.replace("~", "~0").replace("/", "~1")
        return walk(node[key], parts[1:], f"{pointer}/{escaped}")

    found = []
    seen = set()
    for candidate in (field, *FIELD_ALIASES.get(field, ())):
        for pointer, value in walk(data, candidate.split("."), ""):
            if field == "distribution_formats" and candidate == "distributions":
                if not isinstance(value, dict) or not any(value.get(k) for k in ("format", "media_type")):
                    continue
            if pointer not in seen:
                found.append((pointer, value))
                seen.add(pointer)
    return found


def context_digest(context: dict[str, dict]) -> str:
    raw = json.dumps({"version": CONTEXT_VERSION, "predicates": context}, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()
