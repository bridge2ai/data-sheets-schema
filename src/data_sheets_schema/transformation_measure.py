"""D105/D123: v5's offline transformation receipt plus a leaf diagnostic.

Inputs are saved full/core mappings. The existing v5 emitter and verifier retain
their identity and behavior, including their documented historical limitations.
The supplementary leaf ledger is not an instrument. It annotates the existing
declarative projection; it does not build a third projected record. No input,
v4 receipt block or admission gate is changed. Revised 2026-11-09.
"""
from __future__ import annotations

import copy
from contextlib import ExitStack
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

from . import d4d_pair_consistency as pair
from . import derive_core as derivation
from . import transformation_receipts as legacy
from . import resources
from . import schema_snapshot
from . import schema_view
from . import transformation_measure_io as record_io
from .schema_snapshot import capture_schema
from .schema_view import captured_view


INSTRUMENT = legacy.TRANSFORMATION_RECEIPT_INSTRUMENT
DIAGNOSTIC_FORMAT = "d105-full-to-core-leaf-lineage-v1"
_MAX_DEPTH = 200
_MAX_NODES = 1_000_000


def _child(path: str, key: str | int) -> str:
    """RFC 6901; the empty string denotes the document root."""
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _typed(value: Any, active: set[int], remaining: list[int], depth: int = 0) -> Any:
    """A type-sensitive encoding; YAML dates are distinct from text and numbers.

    This is a semantic digest, not a serialization or raw-file hash. Floats
    retain their exact finite representation; bool never aliases int. Public
    input validation has already refused aliases, cycles and excessive inputs.
    """
    remaining[0] -= 1
    if remaining[0] < 0 or depth > _MAX_DEPTH:
        raise ValueError("transformation input exceeds the structural bound")
    kind = type(value)
    if value is None:
        return ["null"]
    if kind is bool:
        return ["bool", value]
    if kind is int:
        return ["int", str(value)]
    if kind is float:
        if not math.isfinite(value):
            raise ValueError("transformation input contains a nonfinite float")
        return ["float", value.hex()]
    if kind is str:
        return ["str", value]
    if kind is dt.datetime:
        return ["datetime", value.isoformat(), value.fold]
    if kind is dt.date:
        return ["date", value.isoformat()]
    if kind not in (dict, list):
        raise ValueError("unsupported transformation input type: " + kind.__name__)
    marker = id(value)
    if marker in active:
        raise ValueError("transformation input contains a cycle")
    active.add(marker)
    try:
        if kind is list:
            return ["list", [_typed(v, active, remaining, depth + 1) for v in value]]
        # LinkML's deterministic projection uses SlotDefinitionName (a str
        # subclass) for some keys; they retain ordinary string-key semantics.
        if any(not isinstance(key, str) for key in value):
            raise ValueError("transformation mappings require string keys")
        return ["dict", [[key, _typed(value[key], active, remaining, depth + 1)]
                         for key in sorted(value)]]
    finally:
        active.remove(marker)


def _canonical(value: Any) -> bytes:
    return json.dumps(_typed(value, set(), [_MAX_NODES]), ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _leaves(value: Any, path: str = "") -> dict[str, Any]:
    """Scalar and empty-container leaves, after structural validation."""
    if type(value) is dict and value:
        result: dict[str, Any] = {}
        for key in sorted(value):
            result.update(_leaves(value[key], _child(path, key)))
        return result
    if type(value) is list and value:
        result = {}
        for index, item in enumerate(value):
            result.update(_leaves(item, _child(path, index)))
        return result
    return {path: value}


def _resolve(document: Any, pointer: str) -> Any:
    value = document
    if pointer:
        for token in pointer[1:].split("/"):
            key = token.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if type(value) is list else value[key]
    return value


def _containers(document: Any, pointer: str) -> tuple[type, ...]:
    """Bind pointer coordinates to their parent shapes (list versus mapping).

    RFC6901 alone cannot distinguish a list index from the same numeric key in
    a mapping. Equal leaf values at those coordinates are not a copied result.
    """
    value, shapes = document, []
    if pointer:
        for token in pointer[1:].split("/"):
            shapes.append(type(value))
            key = token.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if type(value) is list else value[key]
    return tuple(shapes)


def _distribution_source(path: str, prefix: str) -> str:
    """Decode only the existing v5 collection/file provenance grammar."""
    match = re.fullmatch(r"file_collections\[(\d+)\](?:\.resources\[(\d+)\])?(?:\.(.+))?", path)
    if match is None:
        raise ValueError("unsupported v5 distribution source path")
    collection, file, slot = match.groups()
    result = _child(_child(prefix, "file_collections"), int(collection))
    if file is not None:
        result = _child(_child(result, "resources"), int(file))
    return _child(result, slot) if slot is not None else result


class _Annotations:
    """Annotate an already derived record; never construct projected values."""

    def __init__(self, full: dict, expected: dict, schema: Any, specification: Any):
        self.full, self.expected = full, expected
        self.schema, self.specification = schema, specification
        self.expected_leaves = _leaves(expected)
        self.rows: dict[str, dict[str, Any]] = {}
        self.used: dict[str, set[str]] = {}

    def record(self, target: str, rule: str, operation: str, sources: list[str], used: set[str]) -> None:
        if target not in self.expected_leaves or target in self.rows:
            raise ValueError("diagnostic annotation is duplicated or is not an expected leaf")
        for source in sources:
            _resolve(self.full, source)
        self.rows[target] = {"rule": rule, "operation": operation, "source_paths": sources}
        self.used[target] = used

    def copied(self, source: str, target: str, *, rule: str = "copied",
               operation: str = "identity_projection") -> None:
        value = _resolve(self.expected, target)
        if _canonical(value) != _canonical(_resolve(self.full, source)):
            raise ValueError("diagnostic source does not equal the existing projected value")
        for suffix in _leaves(value):
            source_leaf = source + suffix
            self.record(target + suffix, rule, operation, [source_leaf], {source_leaf})

    def resources(self, source: str, target: str) -> None:
        originals, projected = _resolve(self.full, source), _resolve(self.expected, target)
        if type(originals) is not list or type(projected) is not list:
            raise ValueError("projected resources require lists")
        selected = [(index, item) for index, item in enumerate(originals) if type(item) is dict]
        if len(selected) != len(projected):
            raise ValueError("resource annotation differs from existing projection")
        if not projected:
            self.record(target, "copied" if not originals else "normalised",
                        "empty_resource_list_projection", [source], {source} if not originals else set())
        for target_index, (source_index, original) in enumerate(selected):
            source_item, target_item = _child(source, source_index), _child(target, target_index)
            expected_item = projected[target_index]
            if type(expected_item) is not dict:
                raise ValueError("projected resource is not a mapping")
            if not expected_item:
                self.record(target_item, "copied" if not original else "normalised",
                            "empty_resource_projection", [source_item], {source_item} if not original else set())
            for key in self.schema.identity_slots:
                if key in expected_item:
                    self.copied(_child(source_item, key), _child(target_item, key))
            if "resources" in expected_item:
                self.resources(_child(source_item, "resources"), _child(target_item, "resources"))

    def distributions(self, source: dict, expected: dict, source_prefix: str, target_prefix: str) -> None:
        """Use v5's own local projection and provenance, fixing no v1 output.

        The separate local prefixes prevent the historical nested-index defect
        from becoming an affirmative claim in this supplementary diagnostic.
        """
        classes = self.specification.class_derivations
        projected, provenance, _ = legacy._project_distributions_from_spec(
            source.get("file_collections"), classes["CoreDistributionFromCollection"],
            classes["CoreDistributionFromFile"])
        if projected:
            if _canonical(projected) != _canonical(expected.get("distributions")):
                raise ValueError("v5 local distribution projection differs from expected output")
            for entry in provenance:
                match = re.fullmatch(r"distributions\[(\d+)\]", entry["target_path"])
                if match is None:
                    raise ValueError("unsupported v5 distribution target path")
                target_item = _child(_child(target_prefix, "distributions"), int(match.group(1)))
                target_value = _resolve(self.expected, target_item)
                if set(entry["slot_sources"]) != set(target_value):
                    raise ValueError("v5 distribution provenance does not cover its slots")
                for slot, source_path in entry["slot_sources"].items():
                    renamed = slot == "bytes" and source_path.endswith(".total_bytes")
                    self.copied(_distribution_source(source_path, source_prefix), _child(target_item, slot),
                                rule="normalised" if renamed else "copied",
                                operation="rename_total_bytes_to_bytes" if renamed else entry["rule"])
        elif "distributions" in expected:
            raise ValueError("unexplained expected distributions")
        source_resources = source.get("resources") or []
        if type(source_resources) is not list:
            raise ValueError("nested resources must be a list")
        # v5 intentionally takes nested distributions from the last source
        # resource with that string id. Ordinary resource copies were annotated
        # separately using their original positional source.
        by_id = {item.get("id"): (index, item) for index, item in enumerate(source_resources)
                 if type(item) is dict and type(item.get("id")) is str}
        for index, item in enumerate(expected.get("resources") or []):
            if type(item) is dict and item.get("id") in by_id:
                original_index, original = by_id[item["id"]]
                self.distributions(original, item,
                    _child(_child(source_prefix, "resources"), original_index),
                    _child(_child(target_prefix, "resources"), index))

    def annotate(self, receipt: dict) -> None:
        for slot in self.schema.identity_slots:
            if slot in self.expected:
                self.copied(_child("", slot), _child("", slot))
        if "resources" in self.expected:
            self.resources("/resources", "/resources")
        self.distributions(self.full, self.expected, "", "")
        for row in receipt["slot_derivations"]:
            if row["rule"] == "consensus_dialect" and row["target_path"] == "dialect":
                contributors = [_distribution_source(path, "") for path in row["source_path"]]
                for suffix in _leaves(self.expected["dialect"]):
                    sources = [source + suffix for source in contributors]
                    self.record("/dialect" + suffix, "normalised",
                                "consensus_of_present_truthy_file_dialects", sources, set(sources))
            elif row["rule"] == "constant":
                target = _child("", row["target_path"])
                if _canonical(_resolve(self.expected, target)) != _canonical(row["value"]):
                    raise ValueError("v5 constant differs from its expected output")
                self.record(target, "synthesised", "target_schema_constant", [], set())
        if set(self.rows) != set(self.expected_leaves):
            raise ValueError("diagnostic does not annotate exactly the existing expected leaves")


def _alignment(observed: Any, expected: Any) -> tuple[dict, dict]:
    """Align list objects by unique id, retaining exact whole-object checks.

    A missing/ambiguous id grants only positional exact-object comparison. An
    altered object blocks claims for all descendants, including equal-valued
    siblings. Relocation alone is recorded; it does not make ordered core records
    equal or change v5's primary verification result.
    """
    mappings: dict[str, dict[str, Any]] = {}
    blocked: dict[str, str] = {}

    def walk(actual: Any, wanted: Any, actual_path: str, expected_path: str) -> None:
        if type(actual) is dict and type(wanted) is dict:
            for key, child in actual.items():
                if key in wanted:
                    walk(child, wanted[key], _child(actual_path, key), _child(expected_path, key))
        elif type(actual) is list and type(wanted) is list:
            def ids(items):
                result: dict[str, list[int]] = {}
                for index, item in enumerate(items):
                    if type(item) is dict and type(item.get("id")) is str and item["id"]:
                        result.setdefault(item["id"], []).append(index)
                return result
            actual_ids, expected_ids = ids(actual), ids(wanted)
            for index, item in enumerate(actual):
                target_path = _child(actual_path, index)
                selected_index = index if index < len(wanted) else None
                method = "position"
                if type(item) is dict:
                    identifier = item.get("id")
                    if (type(identifier) is str and identifier and len(actual_ids[identifier]) == 1
                            and len(expected_ids.get(identifier, [])) == 1):
                        selected_index = expected_ids[identifier][0]
                        method = "unique_id"
                    elif (type(identifier) is str and identifier and len(actual_ids[identifier]) == 1
                          and identifier not in expected_ids):
                        selected_index = None
                        method = "unknown_id"
                    else:
                        method = "positional_exact_object"
                selected_path = _child(expected_path, selected_index) if selected_index is not None else None
                mappings[target_path] = {"expected_path": selected_path, "alignment": method}
                if type(item) is dict and (selected_index is None
                        or _canonical(item) != _canonical(wanted[selected_index])):
                    blocked[target_path] = "list entry is not the complete expected object"
                if selected_index is not None:
                    walk(item, wanted[selected_index], target_path, selected_path)
    walk(observed, expected, "", "")
    return mappings, blocked


def _aligned_path(path: str, mappings: dict) -> tuple[str | None, dict | None, str | None]:
    applicable = [prefix for prefix in mappings if path == prefix or path.startswith(prefix + "/")]
    if not applicable:
        return path, None, None
    prefix = max(applicable, key=len)
    selected = mappings[prefix]
    wanted = selected["expected_path"]
    return (wanted + path[len(prefix):] if wanted is not None else None), selected, prefix


def _bytes_identity(path: Path, content: bytes) -> dict[str, str]:
    try:
        display = path.relative_to(legacy.REPO_ROOT).as_posix()
    except ValueError:
        display = str(path)
    return {"path": display, "sha256": hashlib.sha256(content).hexdigest()}


def _file_identity(path: Path) -> dict[str, str]:
    path = path.resolve(strict=True)
    return _bytes_identity(path, path.read_bytes())


def _basis(schema: Any, specification: Any, specification_sha: str,
           snapshots: dict, selected_root: dict) -> dict[str, Any]:
    schemas = {}
    for name, snapshot in snapshots.items():
        members = [{"import_name": str(identifier), **_bytes_identity(path, raw)}
                   for identifier, path, raw in snapshot.sources]
        _, root_path, root_bytes = snapshot.sources[0]
        schemas[name] = {**_bytes_identity(root_path, root_bytes), "captured_closure": members}
    return {
        "selected_resource_root": selected_root,
        "specification": {"id": specification.id,
                          "path": legacy.DEFAULT_MAPPING_PATH.relative_to(legacy.REPO_ROOT).as_posix(),
                          "sha256": specification_sha,
                          "source_schema": specification.source_schema,
                          "target_schema": specification.target_schema},
        "schemas": schemas,
        "derivation_sources": {
            "derive_core": _file_identity(Path(derivation.__file__)),
            "pair_consistency": _file_identity(Path(pair.__file__)),
            "transformation_receipts": _file_identity(Path(legacy.__file__)),
            "transformation_measure": _file_identity(Path(__file__)),
            "transformation_measure_io": _file_identity(Path(record_io.__file__)),
            "schema_snapshot": _file_identity(Path(schema_snapshot.__file__)),
            "schema_view": _file_identity(Path(schema_view.__file__)),
            "resources": _file_identity(Path(resources.__file__)),
        },
        "semantics": {
            "identity_slots": list(schema.identity_slots),
            "projected_slots": list(schema.projected_slots),
            "distribution_slots": derivation._distribution_slots(schema),
            "leaf_definition": "scalars and empty mappings/lists; RFC6901 paths",
            "comparison": "typed semantic equality, including YAML date/datetime; no value-search attribution",
            "dropped_basis": "full leaves unused by the expected deterministic projection, not observed-core corruption",
            "primary": "existing v5 emitter and verifier, unchanged; secondary and non-gating",
            "diagnostic_scope": "annotations of the existing declarative output, not a separate instrument",
            "rule_correspondence": {
                "identity_copy": "copied",
                "projected_by_id": "copied retained leaves; normalised empty structural projections",
                "collection_to_distribution": "copied, except total_bytes to bytes is normalised",
                "file_to_distribution": "copied",
                "consensus_dialect": "normalised",
                "constant": "synthesised",
                "omitted_full_leaf": "dropped diagnostic only",
            },
            "known_limits": [
                "The unchanged v1 receipt can name a wrong nested target index after resource filtering (D105-R4/P3-7); its verification does not independently validate those path coordinates.",
                "The unchanged v1 value comparison uses Python equality and can accept bool/int or int/float equality; the leaf diagnostic uses type-sensitive equality and may therefore disagree.",
                "List-object lineage is withheld after any descendant differs; unique-id relocation is reported but does not make ordered records equal.",
            ],
        },
    }


def _selected_paths(pair_schema: Any) -> tuple[dict, dict]:
    """Follow pipeline resource selection, refusing mixed checkouts/fixtures."""
    code_root = legacy.REPO_ROOT.resolve(strict=True)
    current_checkout = resources.checkout_at(Path.cwd())
    if current_checkout is not None and current_checkout.resolve() != code_root:
        raise ValueError(f"transformation measurement refused: working-directory checkout {current_checkout} "
                         f"differs from code checkout {code_root}")
    selected_root, kind = resources.resource_root()
    if kind != "checkout" or selected_root.resolve() != code_root:
        raise ValueError("transformation measurement requires a checkout with dev dependencies; "
                         "resource root differs from the loaded code checkout")
    if pair_schema is None:
        requested = {"full": pair.DEFAULT_FULL_SCHEMA, "core": pair.DEFAULT_CORE_SCHEMA}
    else:
        requested = {"full": getattr(pair_schema.full_view.schema, "source_file", None),
                     "core": getattr(pair_schema.core_view.schema, "source_file", None)}
        if not all(requested.values()):
            raise ValueError("selected schemas require local source paths")
    paths = {name: resources.resource_path(path).resolve(strict=True) for name, path in requested.items()}
    for name, path in paths.items():
        if not path.is_relative_to(code_root):
            raise ValueError(f"transformation measurement refused: {name} schema {path} "
                             f"is outside the code checkout {code_root}")
    return paths, {"path": str(selected_root.resolve()), "kind": kind, "code_checkout": str(code_root)}


def measure(full: dict, core: dict, *, pair_schema=None) -> dict[str, Any]:
    """Measure saved outputs without altering either input or any v4 counter.

    A mismatch is a reportable observation, never an admission gate. Inputs with
    ambiguous/unsupported structure are refused rather than assigned invented
    provenance. Input digests are typed semantic hashes; the caller may add
    separate raw-file identities without substituting them for these hashes.

    An optional PairSchema selects its source paths only. Fresh captured views
    are authoritative, so a previously loaded or mutated view cannot be used
    while the report hashes different bytes on disk.
    """
    # File-only YAML syntax evidence (e.g. duplicate keys before construction)
    # cannot be recovered here. These same structural/value checks apply to
    # direct callers; the strict file reader adds its syntax/raw-byte checks.
    record_io.validate_record(full)
    record_io.validate_record(core)
    _digest(full), _digest(core)
    paths, selected_root = _selected_paths(pair_schema)
    snapshots = {name: capture_schema(path, strict=True) for name, path in paths.items()}
    with ExitStack() as stack:
        views = {name: stack.enter_context(captured_view(snapshot))
                 for name, snapshot in snapshots.items()}
        schema = pair.pair_schema_from_views(views["full"], views["core"])
        return _measure_captured(full, core, schema, snapshots, selected_root)


def _measure_captured(full: dict, core: dict, schema: Any, snapshots: dict,
                      selected_root: dict) -> dict[str, Any]:
    """Use one immutable schema closure for computation and reported identity."""
    full_digest, core_digest = _digest(full), _digest(core)
    specification, _, specification_sha = legacy.load_transformation_spec()
    checked = legacy.validate_spec_against_pair_schema(specification, schema)
    if checked.get("valid") is not True:
        raise ValueError("unsupported transformation specification: " + str(checked))
    basis = _basis(schema, specification, specification_sha, snapshots, selected_root)
    # D123: these genuine existing functions define the primary result. No
    # diagnostic result changes their receipt, identity or verification flags.
    receipt = legacy.emit_transformation_receipt(full, core, pair_schema=schema)
    verification = legacy.verify_transformation_receipt(receipt, full, core, pair_schema=schema)
    if (receipt.get("instrument") != INSTRUMENT or verification.get("instrument") != INSTRUMENT):
        raise ValueError("v5 transformation instrument identity differs between emitter and verifier")
    verification_result = {key: value for key, value in verification.items() if key != "instrument"}
    expected = legacy.derive_core_declarative(full, pair_schema=schema)
    trace = _Annotations(full, expected, schema, specification)
    trace.annotate(receipt)
    expected_leaves, observed_leaves = _leaves(expected), _leaves(core)
    full_leaves = _leaves(full)
    used = set().union(*trace.used.values())
    if not used <= set(full_leaves):
        raise ValueError("transformation lineage names a nonleaf consumed source")
    mappings, blocked = _alignment(core, expected)
    rows = []
    represented = set()
    for path, value in sorted(observed_leaves.items()):
        row: dict[str, Any] = {"target_path": path, "value_digest": _digest(value)}
        expected_path, selection, object_path = _aligned_path(path, mappings)
        if selection is not None:
            row["alignment"] = selection["alignment"]
        if expected_path is not None:
            row["expected_path"] = expected_path
            if expected_path in expected_leaves:
                represented.add(expected_path)
        if (selection is not None and selection["expected_path"] is not None
                and selection["expected_path"] != object_path):
            row["moved_from"] = selection["expected_path"]
        invalid_entry = any(path == prefix or path.startswith(prefix + "/") for prefix in blocked)
        if invalid_entry:
            row.update(status="entry_mismatched", rule=None, operation=None, source_paths=[],
                       reason="list entry is not the complete expected object")
            if expected_path in expected_leaves:
                row.update(expected_value_digest=_digest(expected_leaves[expected_path]),
                           expected_lineage=copy.deepcopy(trace.rows[expected_path]))
        elif expected_path not in expected_leaves:
            row.update(status="unattributed", rule=None, operation=None, source_paths=[])
        elif (_canonical(value) != _canonical(expected_leaves[expected_path])
              or _containers(core, path) != _containers(expected, expected_path)):
            row.update(status="mismatched", rule=None, operation=None, source_paths=[],
                       expected_value_digest=_digest(expected_leaves[expected_path]),
                       expected_lineage=copy.deepcopy(trace.rows[expected_path]))
        else:
            row.update(status="matched", **copy.deepcopy(trace.rows[expected_path]))
        rows.append(row)
    dropped = [{"source_path": path, "rule": "dropped",
                "operation": "not_selected_by_full_to_core_projection", "value_digest": _digest(value)}
               for path, value in sorted(full_leaves.items()) if path not in used]
    missing = [{"target_path": path, "status": "missing", "expected_value_digest": _digest(value),
                "expected_lineage": copy.deepcopy(trace.rows[path])}
               for path, value in sorted(expected_leaves.items()) if path not in represented]
    counts = {"core_leaves": len(rows),
              **{status: sum(row["status"] == status for row in rows)
                 for status in ("matched", "mismatched", "unattributed", "entry_mismatched")},
              **{rule: sum(row["rule"] == rule for row in rows)
                 for rule in ("copied", "normalised", "synthesised")},
              "dropped_full_leaves": len(dropped), "missing_core_leaves": len(missing)}
    # Retained basis files and original arguments must remain stable throughout
    # observation; there is no implicit reload or rewrite of selected artifacts.
    if (_digest(full) != full_digest or _digest(core) != core_digest
            or _basis(schema, specification, specification_sha, snapshots, selected_root) != basis
            or any(path.read_bytes() != raw for snapshot in snapshots.values()
                   for _, path, raw in snapshot.sources)
            or hashlib.sha256(legacy.DEFAULT_MAPPING_PATH.read_bytes()).hexdigest() != specification_sha):
        raise ValueError("transformation inputs or derivation basis changed during observation")
    return {**receipt,
            "verification_result": verification_result,
            "scope": {"secondary": True, "gating": False, "primary_receipt_instrument": "v4"},
            "basis": basis,
            "diagnostic": {
                "format": DIAGNOSTIC_FORMAT, "not_an_instrument": True,
                "input_digests": {"full": full_digest, "core": core_digest, "expected_core": _digest(expected)},
                "matches_derived_core": _canonical(core) == _canonical(expected),
                "core_leaves": rows, "dropped_full_leaves": dropped,
                "missing_core_leaves": missing, "counts": counts}}
