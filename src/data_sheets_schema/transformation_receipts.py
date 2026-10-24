"""Declarative transformation receipts via LinkML-Map (`linkml-map`, Slide 8).

Provides declarative schema-to-schema (`Dataset` -> `CoreDataset`,
`FileCollection` -> `CoreDistribution`, `File` -> `CoreDistribution`)
projection and verifiable transformation receipts grounded in
`linkml_mappings/full-to-core-mapping.yaml` (`TransformationSpecification`).

Why we load `TransformationSpecification` directly from
`linkml_map.datamodel.transformer_model`:
Top-level `import linkml_map` eagerly imports `linkml_map.functions.unit_conversion`,
which instantiates `ucumvert.PintUcumRegistry()` at import time and raises
`KeyError: 'millimeter_Hg'` under Python 3.13 / Pint 0.24+. Importing
`TransformationSpecification` from `linkml_map.datamodel.transformer_model`
validates the LinkML-Map specification cleanly on Python 3.13 without
triggering `ucumvert`.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any, Mapping

import yaml


def _load_transformation_specification_cls() -> Any:
    """Import `TransformationSpecification` from `linkml_map.datamodel.transformer_model`
    without triggering `linkml_map/__init__.py`'s eager `ucumvert` import on Python 3.13."""
    mod_name = "linkml_map.datamodel.transformer_model"
    if mod_name in sys.modules:
        return sys.modules[mod_name].TransformationSpecification
    spec = importlib.util.find_spec("linkml_map")
    if spec is None or not spec.submodule_search_locations:
        raise ImportError("linkml_map is not installed")
    pkg_dir = Path(next(iter(spec.submodule_search_locations)))
    if "linkml_map" not in sys.modules:
        pkg = types.ModuleType("linkml_map")
        pkg.__path__ = [str(pkg_dir)]
        sys.modules["linkml_map"] = pkg
    if "linkml_map.datamodel" not in sys.modules:
        dm_pkg = types.ModuleType("linkml_map.datamodel")
        dm_pkg.__path__ = [str(pkg_dir / "datamodel")]
        sys.modules["linkml_map.datamodel"] = dm_pkg
    tm_path = pkg_dir / "datamodel" / "transformer_model.py"
    tm_spec = importlib.util.spec_from_file_location(mod_name, tm_path)
    if tm_spec is None or tm_spec.loader is None:
        raise ImportError(f"Cannot load {mod_name} from {tm_path}")
    tm_mod = importlib.util.module_from_spec(tm_spec)
    sys.modules[mod_name] = tm_mod
    tm_spec.loader.exec_module(tm_mod)
    return tm_mod.TransformationSpecification


TransformationSpecification = _load_transformation_specification_cls()

from data_sheets_schema.d4d_pair_consistency import load_pair_schema, synchronize_core_data
from data_sheets_schema.derive_core import (
    CORE_CLASS,
    CORE_SCHEMA_REL,
    _distribution_slots,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAPPING_PATH = REPO_ROOT / "linkml_mappings" / "full-to-core-mapping.yaml"

TRANSFORMATION_RECEIPT_INSTRUMENT = (
    "v1 (linkml-map transformation receipt): declarative Dataset -> CoreDataset "
    "and FileCollection/File -> CoreDistribution projection verified against "
    "linkml_mappings/full-to-core-mapping.yaml (TransformationSpecification)"
)


def _canonical_sha256(data: Any) -> str:
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_transformation_spec(
    spec_path: Path | None = None,
) -> tuple[TransformationSpecification, dict[str, Any], str]:
    """Load and validate the LinkML-Map `TransformationSpecification` YAML.

    Returns `(spec_model, raw_dict, sha256_hex)`.
    """
    path = spec_path or DEFAULT_MAPPING_PATH
    raw_bytes = path.read_bytes()
    sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
    raw_dict = yaml.safe_load(raw_bytes.decode("utf-8"))
    if not isinstance(raw_dict, dict):
        raise ValueError(f"{path}: transformation specification must be a YAML mapping")
    spec_dict = copy.deepcopy(raw_dict)
    class_derivs = spec_dict.get("class_derivations")
    if isinstance(class_derivs, dict):
        for c_name, c_spec in class_derivs.items():
            if isinstance(c_spec, dict):
                c_spec.setdefault("name", c_name)
                slot_derivs = c_spec.get("slot_derivations")
                if isinstance(slot_derivs, dict):
                    for s_name, s_spec in slot_derivs.items():
                        if isinstance(s_spec, dict):
                            s_spec.setdefault("name", s_name)
    spec = TransformationSpecification(**spec_dict)
    return spec, raw_dict, sha256_hex


def validate_spec_against_pair_schema(
    spec: TransformationSpecification | None = None,
    pair_schema: Any = None,
) -> dict[str, Any]:
    """Verify that `full-to-core-mapping.yaml` declares the exact shared slots
    induced by `Dataset` / `CoreDataset`, `FileCollection` / `CoreDistribution`,
    and `File` / `CoreDistribution`."""
    if spec is None:
        spec, _, _ = load_transformation_spec()
    ps = pair_schema or load_pair_schema()
    dist_slots = _distribution_slots(ps)

    cd = spec.class_derivations.get("CoreDataset")
    cd_coll = spec.class_derivations.get("CoreDistributionFromCollection")
    cd_file = spec.class_derivations.get("CoreDistributionFromFile")
    if cd is None or cd_coll is None or cd_file is None:
        return {
            "valid": False,
            "reason": "missing required class_derivations (CoreDataset, CoreDistributionFromCollection, CoreDistributionFromFile)",
        }

    declared_identity = {
        name
        for name, sd in cd.slot_derivations.items()
        if sd.populated_from == name and sd.expr is None
    }
    expected_identity = set(ps.identity_slots)

    declared_coll = {
        name
        for name, sd in cd_coll.slot_derivations.items()
        if sd.populated_from == name
    }
    expected_coll = set(dist_slots["collection"])

    declared_file = {
        name
        for name, sd in cd_file.slot_derivations.items()
        if sd.populated_from == name
    }
    expected_file = set(dist_slots["file"])

    missing_identity = sorted(expected_identity - declared_identity)
    extra_identity = sorted(declared_identity - expected_identity)
    missing_coll = sorted(expected_coll - declared_coll)
    extra_coll = sorted(declared_coll - expected_coll)
    missing_file = sorted(expected_file - declared_file)
    extra_file = sorted(declared_file - expected_file)

    valid = not any((
        missing_identity,
        extra_identity,
        missing_coll,
        extra_coll,
        missing_file,
        extra_file,
    ))
    return {
        "valid": valid,
        "identity_slots_count": len(declared_identity),
        "collection_slots_count": len(declared_coll),
        "file_slots_count": len(declared_file),
        "missing_identity": missing_identity,
        "extra_identity": extra_identity,
        "missing_collection": missing_coll,
        "extra_collection": extra_coll,
        "missing_file": missing_file,
        "extra_file": extra_file,
    }


def _project_distributions_from_spec(
    items: Any,
    coll_deriv: Any,
    file_deriv: Any,
    prefix: str = "",
) -> tuple[list[dict[str, Any]] | None, list[dict[str, Any]], dict[str, str]]:
    """Project `file_collections` to `distributions` using the LinkML-Map
    `CoreDistributionFromCollection` and `CoreDistributionFromFile` slot
    derivations, returning `(distributions, provenance_entries, path_map)`."""
    if not isinstance(items, list):
        return None, [], {}
    out: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    pmap: dict[str, str] = {f"{prefix}file_collections": f"{prefix}distributions"}

    coll_slots = sorted(
        name for name, sd in coll_deriv.slot_derivations.items() if sd.populated_from == name
    )
    file_slots = sorted(
        name for name, sd in file_deriv.slot_derivations.items() if sd.populated_from == name
    )

    for i, item in enumerate(items):
        if not isinstance(item, Mapping):
            continue
        entry: dict[str, Any] = {}
        copied_from: dict[str, str] = {}
        for k in coll_slots:
            if k in item:
                entry[k] = copy.deepcopy(item[k])
                copied_from[k] = f"{prefix}file_collections[{i}].{k}"
        if "bytes" not in entry and item.get("total_bytes") is not None:
            entry["bytes"] = copy.deepcopy(item["total_bytes"])
            copied_from["bytes"] = f"{prefix}file_collections[{i}].total_bytes"
        if entry:
            dist_idx = len(out)
            out.append(entry)
            if isinstance(item.get("id"), str):
                pmap[f"{prefix}file_collections[{i}]"] = f"{prefix}distributions[{dist_idx}]"
            provenance.append({
                "target_path": f"{prefix}distributions[{dist_idx}]",
                "source_path": f"{prefix}file_collections[{i}]",
                "class_derivation": "CoreDistributionFromCollection",
                "rule": "collection_to_distribution",
                "slot_sources": copied_from,
            })
        for k_idx, f in enumerate(item.get("resources") or []):
            if not isinstance(f, Mapping):
                continue
            fe: dict[str, Any] = {}
            f_copied: dict[str, str] = {}
            for slot_name in file_slots:
                if slot_name in f:
                    fe[slot_name] = copy.deepcopy(f[slot_name])
                    f_copied[slot_name] = f"{prefix}file_collections[{i}].resources[{k_idx}].{slot_name}"
            if fe:
                f_dist_idx = len(out)
                out.append(fe)
                if isinstance(f.get("id"), str):
                    pmap[f"{prefix}file_collections[{i}].resources[{k_idx}]"] = (
                        f"{prefix}distributions[{f_dist_idx}]"
                    )
                provenance.append({
                    "target_path": f"{prefix}distributions[{f_dist_idx}]",
                    "source_path": f"{prefix}file_collections[{i}].resources[{k_idx}]",
                    "class_derivation": "CoreDistributionFromFile",
                    "rule": "file_to_distribution",
                    "slot_sources": f_copied,
                })
    return (out or None), provenance, pmap


def _derive_core_and_receipt(
    full: Mapping[str, Any],
    *,
    spec_path: Path | None = None,
    pair_schema: Any = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Execute the LinkML-Map `TransformationSpecification` on `full` to
    produce `(core_record, transformation_receipt)`."""
    spec, _raw_spec, spec_sha256 = load_transformation_spec(spec_path)
    ps = pair_schema or load_pair_schema()
    cd = spec.class_derivations["CoreDataset"]
    cd_coll = spec.class_derivations["CoreDistributionFromCollection"]
    cd_file = spec.class_derivations["CoreDistributionFromFile"]

    # 1. Shared identity slots & recursive resources projection
    core = synchronize_core_data(full, {}, ps)
    slot_derivations: list[dict[str, Any]] = []
    counts = {
        "identity_copied": 0,
        "resources_projected": 0,
        "distributions_from_collections": 0,
        "distributions_from_files": 0,
        "dialect_derived": 0,
        "constants_set": 0,
    }

    for slot_name, sd in cd.slot_derivations.items():
        if sd.populated_from == slot_name and sd.expr is None:
            if slot_name in core:
                counts["identity_copied"] += 1
                slot_derivations.append({
                    "target_path": slot_name,
                    "source_path": slot_name,
                    "class_derivation": "CoreDataset",
                    "rule": "identity_copy",
                })

    if "resources" in core and isinstance(core.get("resources"), list):
        counts["resources_projected"] = len(core["resources"])
        slot_derivations.append({
            "target_path": "resources",
            "source_path": "resources",
            "class_derivation": "CoreDataset",
            "rule": "projected_by_id",
        })

    # 2. Distributions projection (top-level and nested resources)
    path_map: dict[str, str] = {}

    def _walk_distributions(
        node: dict[str, Any],
        source: Mapping[str, Any],
        prefix: str,
    ) -> None:
        dists, dist_prov, local_pmap = _project_distributions_from_spec(
            source.get("file_collections"), cd_coll, cd_file, prefix=prefix
        )
        path_map.update(local_pmap)
        if dists:
            node["distributions"] = dists
            for dp in dist_prov:
                if dp["rule"] == "collection_to_distribution":
                    counts["distributions_from_collections"] += 1
                else:
                    counts["distributions_from_files"] += 1
                slot_derivations.append(dp)
        full_res = {
            r.get("id"): (idx, r)
            for idx, r in enumerate(source.get("resources") or [])
            if isinstance(r, Mapping) and isinstance(r.get("id"), str)
        }
        for cr_idx, res in enumerate(node.get("resources") or []):
            if isinstance(res, dict) and res.get("id") in full_res:
                r_idx, orig_res = full_res[res["id"]]
                if cr_idx != r_idx:
                    path_map[f"{prefix}resources[{r_idx}]"] = f"{prefix}resources[{cr_idx}]"
                _walk_distributions(res, orig_res, f"{prefix}resources[{r_idx}].")

    _walk_distributions(core, full, "")

    # 3. Consensus dialect derivation
    dialects: list[Any] = []
    dialect_sources: list[str] = []
    for i, coll in enumerate(full.get("file_collections") or []):
        if isinstance(coll, Mapping):
            for k, f in enumerate(coll.get("resources") or []):
                if isinstance(f, Mapping) and f.get("dialect"):
                    dialects.append(f["dialect"])
                    dialect_sources.append(f"file_collections[{i}].resources[{k}].dialect")
    if dialects and all(d == dialects[0] for d in dialects):
        core["dialect"] = copy.deepcopy(dialects[0])
        counts["dialect_derived"] = 1
        slot_derivations.append({
            "target_path": "dialect",
            "source_path": dialect_sources,
            "class_derivation": "CoreDataset",
            "rule": "consensus_dialect",
        })

    # 4. Target schema/class constants from specification
    core["conforms_to_class"] = (
        str(cd.slot_derivations["conforms_to_class"].expr or "").strip("'\"") or CORE_CLASS
    )
    core["conforms_to_schema"] = (
        str(cd.slot_derivations["conforms_to_schema"].expr or "").strip("'\"") or CORE_SCHEMA_REL
    )
    counts["constants_set"] = 2
    for const_slot in ("conforms_to_class", "conforms_to_schema"):
        slot_derivations.append({
            "target_path": const_slot,
            "source_path": None,
            "class_derivation": "CoreDataset",
            "rule": "constant",
            "value": core[const_slot],
        })

    order = [s.name for s in ps.core_view.class_induced_slots(CORE_CLASS)]
    ordered_core = (
        {k: core[k] for k in order if k in core}
        | {k: v for k, v in core.items() if k not in order}
    )

    spec_file = spec_path or DEFAULT_MAPPING_PATH
    try:
        rel_spec = str(spec_file.relative_to(REPO_ROOT))
    except ValueError:
        rel_spec = str(spec_file)

    receipt = {
        "instrument": TRANSFORMATION_RECEIPT_INSTRUMENT,
        "specification": {
            "id": spec.id,
            "path": rel_spec,
            "sha256": spec_sha256,
            "source_schema": spec.source_schema,
            "target_schema": spec.target_schema,
        },
        "source_digest": _canonical_sha256(dict(full)),
        "target_digest": _canonical_sha256(ordered_core),
        "counts": counts,
        "path_map": path_map,
        "slot_derivations": slot_derivations,
    }
    return ordered_core, receipt


def derive_core_declarative(
    full: Mapping[str, Any],
    *,
    spec_path: Path | None = None,
    pair_schema: Any = None,
) -> dict[str, Any]:
    """Execute the LinkML-Map `TransformationSpecification` on `full` to
    produce `core_record` (matching `derive_core.derive_core`)."""
    core, _receipt = _derive_core_and_receipt(
        full, spec_path=spec_path, pair_schema=pair_schema
    )
    return core


def emit_transformation_receipt(
    full: Mapping[str, Any],
    core: Mapping[str, Any] | None = None,
    *,
    spec_path: Path | None = None,
    pair_schema: Any = None,
) -> dict[str, Any]:
    """Emit a LinkML-Map transformation receipt for `full` -> `core`."""
    derived_core, receipt = _derive_core_and_receipt(
        full, spec_path=spec_path, pair_schema=pair_schema
    )
    if core is not None:
        receipt["target_digest"] = _canonical_sha256(dict(core))
        matches = dict(core) == derived_core
        receipt["matches_derived_core"] = matches
    else:
        matches = True
        receipt["matches_derived_core"] = True
    receipt["verification"] = {
        "verified": matches,
        "mismatched": 0 if matches else 1,
    }
    return receipt


def verify_transformation_receipt(
    arg1: Mapping[str, Any],
    arg2: Mapping[str, Any],
    arg3: Mapping[str, Any],
    *,
    spec_path: Path | None = None,
    pair_schema: Any = None,
) -> dict[str, Any]:
    """Deterministically verify a transformation receipt against `full`, `core`,
    and the LinkML-Map `TransformationSpecification`.

    Accepts either `(receipt, full, core)` or `(full, core, receipt)`.
    """
    if "specification" in arg1 and "slot_derivations" in arg1:
        receipt, full, core = arg1, arg2, arg3
    else:
        full, core, receipt = arg1, arg2, arg3
    findings: list[dict[str, Any]] = []
    spec, _raw_spec, spec_sha256 = load_transformation_spec(spec_path)
    ps = pair_schema or load_pair_schema()

    spec_check = validate_spec_against_pair_schema(spec, ps)
    if not spec_check["valid"]:
        findings.append({
            "kind": "transformation_spec_schema_drift",
            "detail": spec_check,
        })

    rec_spec = receipt.get("specification") or {}
    if rec_spec.get("sha256") != spec_sha256:
        findings.append({
            "kind": "transformation_spec_sha256_mismatch",
            "expected": spec_sha256,
            "actual": rec_spec.get("sha256"),
        })

    expected_source_digest = _canonical_sha256(dict(full))
    if receipt.get("source_digest") != expected_source_digest:
        findings.append({
            "kind": "transformation_source_digest_mismatch",
            "expected": expected_source_digest,
            "actual": receipt.get("source_digest"),
        })

    expected_target_digest = _canonical_sha256(dict(core))
    if receipt.get("target_digest") != expected_target_digest:
        findings.append({
            "kind": "transformation_target_digest_mismatch",
            "expected": expected_target_digest,
            "actual": receipt.get("target_digest"),
        })

    derived_core, expected_receipt = _derive_core_and_receipt(
        full, spec_path=spec_path, pair_schema=ps
    )
    if dict(core) != derived_core:
        differing_keys = sorted(
            k for k in set(core.keys()) | set(derived_core.keys())
            if core.get(k) != derived_core.get(k)
        )
        findings.append({
            "kind": "transformation_value_mismatch",
            "differing_slots": differing_keys,
        })

    if receipt.get("path_map") != expected_receipt["path_map"]:
        findings.append({
            "kind": "transformation_path_map_mismatch",
            "expected": expected_receipt["path_map"],
            "actual": receipt.get("path_map"),
        })

    if receipt.get("slot_derivations") != expected_receipt["slot_derivations"]:
        findings.append({
            "kind": "transformation_slot_derivations_mismatch",
            "expected_count": len(expected_receipt["slot_derivations"]),
            "actual_count": len(receipt.get("slot_derivations") or []),
        })

    return {
        "checked": True,
        "verified": len(findings) == 0,
        "mismatched": len(findings),
        "instrument": TRANSFORMATION_RECEIPT_INSTRUMENT,
        "findings": findings,
        "derivations_verified": len(expected_receipt["slot_derivations"]) if not findings else 0,
    }
