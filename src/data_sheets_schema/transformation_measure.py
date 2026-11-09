"""D105: offline, secondary full-to-core leaf lineage, 2026-11-09.

Inputs are saved full/core mappings. No record, receipt block or admission gate
is changed. The existing LinkML-Map specification and transformation instrument
are retained as the basis; this additive instrument traces individual leaves.
The old receipt's aggregate path_map is not evidence for these paths: source and
target resource indexes can differ. The untouched derive_core function remains
the expected-output oracle, independently compared with the tracing projection.
"""
from __future__ import annotations

import copy
from contextlib import ExitStack
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from . import d4d_pair_consistency as pair
from . import derive_core as derivation
from . import transformation_receipts as legacy
from .schema_snapshot import capture_schema
from .schema_view import captured_view


INSTRUMENT = "d105-full-to-core-leaf-transformation-v1"
_MAX_DEPTH = 200
_MAX_NODES = 1_000_000


def _child(path: str, key: str | int) -> str:
    """RFC 6901; the empty string denotes the document root."""
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _typed(value: Any, active: set[int], remaining: list[int], depth: int = 0) -> Any:
    """A type-sensitive encoding; YAML dates are distinct from text and numbers.

    This is a semantic digest, not a serialization or raw-file hash. Floats
    retain their exact finite representation; bool never aliases int. Shared
    YAML aliases are allowed, cycles and excessive expansions are refused.
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


class _Trace:
    def __init__(self, full: dict[str, Any], schema: Any):
        self.full = full
        self.schema = schema
        self.rows: dict[str, dict[str, Any]] = {}
        self.used: dict[str, set[str]] = {}

    def forget(self, target: str) -> None:
        for path in list(self.rows):
            if path == target or path.startswith(target + "/"):
                del self.rows[path]
                del self.used[path]

    def record(self, target: str, rule: str, operation: str, sources: list[str],
               used: set[str]) -> None:
        self.rows[target] = {"rule": rule, "operation": operation,
                             "source_paths": sources}
        self.used[target] = used

    def copied(self, value: Any, source: str, target: str, *,
               rule: str = "copied", operation: str = "identity_projection") -> Any:
        self.forget(target)
        for suffix, leaf in _leaves(value).items():
            source_leaf, target_leaf = source + suffix, target + suffix
            if _canonical(_resolve(self.full, source_leaf)) != _canonical(leaf):
                raise ValueError("transformation trace source does not match its value")
            self.record(target_leaf, rule, operation, [source_leaf], {source_leaf})
        return copy.deepcopy(value)

    def resources(self, value: Any, source: str, target: str) -> list[dict[str, Any]]:
        if type(value) is not list:
            raise ValueError("projected resources must be a list")
        self.forget(target)
        result = []
        allowed = set(self.schema.identity_slots)
        for source_index, item in enumerate(value):
            if type(item) is not dict:
                continue
            source_item = _child(source, source_index)
            target_item = _child(target, len(result))
            projected = {}
            for key, child in item.items():
                if key in allowed:
                    projected[key] = self.copied(child, _child(source_item, key),
                                                 _child(target_item, key))
                elif key == "resources" and type(child) is list:
                    projected[key] = self.resources(child, _child(source_item, key),
                                                     _child(target_item, key))
            if not projected:
                # The source container explains a structural projection, but
                # its discarded descendants are not thereby copied/consumed.
                used = {source_item} if not item else set()
                self.record(target_item, "copied" if not item else "normalised",
                            "empty_resource_projection", [source_item], used)
            result.append(projected)
        if not result:
            self.record(target, "copied" if not value else "normalised",
                        "empty_resource_list_projection", [source],
                        {source} if not value else set())
        return result

    def distributions(self, items: Any, source: str, target: str,
                      slots: dict[str, list[str]]) -> list[dict[str, Any]] | None:
        if type(items) is not list:
            return None
        out: list[dict[str, Any]] = []
        for index, item in enumerate(items):
            if type(item) is not dict:
                continue
            source_item = _child(source, index)
            target_item = _child(target, len(out))
            entry = {key: self.copied(item[key], _child(source_item, key),
                                     _child(target_item, key),
                                     operation="collection_to_distribution")
                     for key in slots["collection"] if key in item}
            if "bytes" not in entry and item.get("total_bytes") is not None:
                entry["bytes"] = self.copied(item["total_bytes"],
                    _child(source_item, "total_bytes"), _child(target_item, "bytes"),
                    rule="normalised", operation="rename_total_bytes_to_bytes")
            if entry:
                out.append(entry)
            children = item.get("resources") or []
            # Malformed containers are outside this observer's admitted domain;
            # do not guess source coordinates from iteration over dict/string.
            if type(children) is not list:
                raise ValueError("FileCollection resources must be a list")
            for file_index, child in enumerate(children):
                if type(child) is not dict:
                    continue
                source_file = _child(_child(source_item, "resources"), file_index)
                target_file = _child(target, len(out))
                projected = {key: self.copied(child[key], _child(source_file, key),
                    _child(target_file, key), operation="file_to_distribution")
                    for key in slots["file"] if key in child}
                if projected:
                    out.append(projected)
        return out or None

    def add_distributions(self, node: dict[str, Any], source: dict[str, Any],
                          source_path: str, target_path: str,
                          slots: dict[str, list[str]]) -> None:
        target_distributions = _child(target_path, "distributions")
        # This slot is core-only in the validated mapping. Never silently
        # overwrite an existing traced slot on an unsupported future schema.
        if "distributions" in node:
            raise ValueError("unexpected preexisting distributions in projection")
        distributions = self.distributions(source.get("file_collections"),
            _child(source_path, "file_collections"), target_distributions, slots)
        if distributions:
            node["distributions"] = distributions
            # Adding a child replaces an earlier empty-resource leaf.
            if target_path in self.rows:
                del self.rows[target_path]
                del self.used[target_path]
        source_resources = source.get("resources") or []
        if type(source_resources) is not list:
            raise ValueError("nested resources must be a list")
        # Deliberately mirror derive_core: repeated string ids select the LAST
        # source resource for nested distributions; ordinary copied fields retain
        # their original positions. These are two different provenance routes.
        by_id = {item.get("id"): (index, item)
                 for index, item in enumerate(source_resources)
                 if type(item) is dict and type(item.get("id")) is str}
        for target_index, resource in enumerate(node.get("resources") or []):
            if type(resource) is dict and resource.get("id") in by_id:
                source_index, original = by_id[resource["id"]]
                self.add_distributions(resource, original,
                    _child(_child(source_path, "resources"), source_index),
                    _child(_child(target_path, "resources"), target_index), slots)

    def build(self) -> dict[str, Any]:
        core = {slot: self.copied(self.full[slot], _child("", slot), _child("", slot))
                for slot in self.schema.identity_slots if slot in self.full}
        if "resources" in self.schema.projected_slots and "resources" in self.full:
            core["resources"] = self.resources(self.full["resources"], "/resources", "/resources")
        self.add_distributions(core, self.full, "", "", derivation._distribution_slots(self.schema))
        dialects: list[tuple[str, Any]] = []
        collections = self.full.get("file_collections") or []
        if type(collections) is not list:
            raise ValueError("file_collections must be a list")
        for index, collection in enumerate(collections):
            if type(collection) is not dict:
                continue
            files = collection.get("resources") or []
            if type(files) is not list:
                raise ValueError("FileCollection resources must be a list")
            for file_index, file in enumerate(files):
                if type(file) is dict and file.get("dialect"):
                    path = _child(_child(_child(_child("", "file_collections"), index),
                                         "resources"), file_index)
                    dialects.append((_child(path, "dialect"), file["dialect"]))
        if dialects and all(value == dialects[0][1] for _, value in dialects):
            value = dialects[0][1]
            self.forget("/dialect")
            core["dialect"] = copy.deepcopy(value)
            for suffix in _leaves(value):
                sources = [source + suffix for source, _ in dialects]
                # Validate every claimed leaf; Python consensus may consider
                # bool/int equivalent, which is why this is a named normalising
                # operation rather than a claim of byte/type-identical copying.
                for source in sources:
                    _resolve(self.full, source)
                self.record("/dialect" + suffix, "normalised",
                            "consensus_of_present_truthy_file_dialects", sources, set(sources))
        for key, value in (("conforms_to_class", derivation.CORE_CLASS),
                           ("conforms_to_schema", derivation.CORE_SCHEMA_REL)):
            target = _child("", key)
            self.forget(target)
            core[key] = value
            self.record(target, "synthesised", "target_schema_constant", [], set())
        return core


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
           snapshots: dict) -> dict[str, Any]:
    schemas = {}
    for name, snapshot in snapshots.items():
        members = [{"import_name": str(identifier), **_bytes_identity(path, raw)}
                   for identifier, path, raw in snapshot.sources]
        _, root_path, root_bytes = snapshot.sources[0]
        schemas[name] = {**_bytes_identity(root_path, root_bytes), "captured_closure": members}
    return {
        "instrument": legacy.TRANSFORMATION_RECEIPT_INSTRUMENT,
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
        },
        "semantics": {
            "identity_slots": list(schema.identity_slots),
            "projected_slots": list(schema.projected_slots),
            "distribution_slots": derivation._distribution_slots(schema),
            "leaf_definition": "scalars and empty mappings/lists; RFC6901 paths",
            "comparison": "typed semantic equality, including YAML date/datetime; no value-search attribution",
            "dropped_basis": "full leaves unused by the expected deterministic projection, not observed-core corruption",
            "legacy_receipt_scope": "mapping/instrument basis only; aggregate v1 paths are not asserted as leaf lineage",
        },
    }


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
    if type(full) is not dict or type(core) is not dict:
        raise ValueError("transformation measurement requires full/core mappings")
    # Refuse pathological payloads before constructing schema views.
    _digest(full), _digest(core)
    if pair_schema is None:
        paths = {"full": legacy.REPO_ROOT / pair.DEFAULT_FULL_SCHEMA,
                 "core": legacy.REPO_ROOT / pair.DEFAULT_CORE_SCHEMA}
    else:
        paths = {"full": getattr(pair_schema.full_view.schema, "source_file", None),
                 "core": getattr(pair_schema.core_view.schema, "source_file", None)}
        if not all(paths.values()):
            raise ValueError("selected schemas require local source paths")
    snapshots = {name: capture_schema(path, strict=True) for name, path in paths.items()}
    with ExitStack() as stack:
        views = {name: stack.enter_context(captured_view(snapshot))
                 for name, snapshot in snapshots.items()}
        schema = pair.pair_schema_from_views(views["full"], views["core"])
        return _measure_captured(full, core, schema, snapshots)


def _measure_captured(full: dict, core: dict, schema: Any, snapshots: dict) -> dict[str, Any]:
    """Use one immutable schema closure for computation and reported identity."""
    full_digest, core_digest = _digest(full), _digest(core)
    specification, _, specification_sha = legacy.load_transformation_spec()
    checked = legacy.validate_spec_against_pair_schema(specification, schema)
    if checked.get("valid") is not True:
        raise ValueError("unsupported transformation specification: " + str(checked))
    basis = _basis(schema, specification, specification_sha, snapshots)
    expected = derivation.derive_core(full, schema)
    trace = _Trace(full, schema)
    traced = trace.build()
    if _canonical(traced) != _canonical(expected):
        raise ValueError("transformation lineage projection differs from derive_core")
    expected_leaves, observed_leaves = _leaves(expected), _leaves(core)
    if set(trace.rows) != set(expected_leaves):
        raise ValueError("transformation lineage does not cover exactly the expected leaves")
    full_leaves = _leaves(full)
    used = set().union(*trace.used.values())
    if not used <= set(full_leaves):
        raise ValueError("transformation lineage names a nonleaf consumed source")
    rows = []
    for path, value in sorted(observed_leaves.items()):
        row: dict[str, Any] = {"target_path": path, "value_digest": _digest(value)}
        if path not in expected_leaves:
            row.update(status="unattributed", rule=None, operation=None, source_paths=[])
        elif (_canonical(value) != _canonical(expected_leaves[path])
              or _containers(core, path) != _containers(expected, path)):
            row.update(status="mismatched", rule=None, operation=None, source_paths=[],
                       expected_value_digest=_digest(expected_leaves[path]),
                       expected_lineage=copy.deepcopy(trace.rows[path]))
        else:
            row.update(status="matched", **copy.deepcopy(trace.rows[path]))
        rows.append(row)
    dropped = [{"source_path": path, "rule": "dropped",
                "operation": "not_selected_by_full_to_core_projection", "value_digest": _digest(value)}
               for path, value in sorted(full_leaves.items()) if path not in used]
    missing = [{"target_path": path, "status": "missing", "expected_value_digest": _digest(value),
                "expected_lineage": copy.deepcopy(trace.rows[path])}
               for path, value in sorted(expected_leaves.items()) if path not in observed_leaves]
    counts = {"core_leaves": len(rows),
              **{status: sum(row["status"] == status for row in rows)
                 for status in ("matched", "mismatched", "unattributed")},
              **{rule: sum(row["rule"] == rule for row in rows)
                 for rule in ("copied", "normalised", "synthesised")},
              "dropped_full_leaves": len(dropped), "missing_core_leaves": len(missing)}
    # Retained basis files and original arguments must remain stable throughout
    # observation; there is no implicit reload or rewrite of selected artifacts.
    if (_digest(full) != full_digest or _digest(core) != core_digest
            or _basis(schema, specification, specification_sha, snapshots) != basis
            or any(path.read_bytes() != raw for snapshot in snapshots.values()
                   for _, path, raw in snapshot.sources)
            or hashlib.sha256(legacy.DEFAULT_MAPPING_PATH.read_bytes()).hexdigest() != specification_sha):
        raise ValueError("transformation inputs or derivation basis changed during observation")
    return {"instrument": INSTRUMENT,
            "scope": {"secondary": True, "gating": False, "primary_receipt_instrument": "v4"},
            "basis": basis,
            "input_digests": {"full": full_digest, "core": core_digest, "expected_core": _digest(expected)},
            "matches_derived_core": _canonical(core) == _canonical(expected),
            "core_leaves": rows, "dropped_full_leaves": dropped,
            "missing_core_leaves": missing, "counts": counts}
