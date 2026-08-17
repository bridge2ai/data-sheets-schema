"""Validate and synchronize paired full and core D4D records.

Phase 4 of the agentic D4D workflow uses the LinkML schemas to derive which
root slots have identical value structures. Those slots must have deeply equal
YAML content in the full and core records. Slots with different ranges, such as
``resources``, are compared as schema-compatible projections.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml
from linkml_runtime.linkml_model.meta import SlotDefinition
from linkml_runtime.utils.schemaview import SchemaView


DEFAULT_FULL_SCHEMA = Path(
    "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
)
DEFAULT_CORE_SCHEMA = Path(
    "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"
)
FULL_CLASS = "Dataset"
CORE_CLASS = "CoreDataset"
PHASE4_HEADER = "# Phase 4 reconciliation: completed"


#: Annotation marking a slot as describing *the record* rather than the dataset
#: (#499). Such a slot's correct value necessarily differs between a full and a
#: core record — `conforms_to_class` is `Dataset` in one and `CoreDataset` in
#: the other — so strict identity makes it unrepresentable: any honest value
#: fails the pair check, and `--sync-core` would copy full's value into core and
#: write a false claim about what the core record instantiates.
#:
#: Read from the schema rather than hardcoded here, so the category is visible
#: where the slots are defined and a new one is covered by declaring it. A
#: hardcoded name list is the hand-maintained-list problem #431 removed.
PER_RECORD_ANNOTATION = "d4d:perRecord"


@dataclass(frozen=True)
class PairSchema:
    """Schema-derived rules for comparing a full/core pair."""

    full_view: SchemaView
    core_view: SchemaView
    identity_slots: Tuple[str, ...]
    projected_slots: Tuple[str, ...]
    per_record_slots: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsistencyIssue:
    """One full/core consistency problem."""

    code: str
    path: str
    message: str


@dataclass
class PairConsistencyReport:
    """Result of validating one full/core pair."""

    identity_slots: Tuple[str, ...]
    projected_slots: Tuple[str, ...]
    per_record_slots: Tuple[str, ...] = ()
    errors: List[ConsistencyIssue] = field(default_factory=list)
    warnings: List[ConsistencyIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "identity_slot_count": len(self.identity_slots),
            "identity_slots": list(self.identity_slots),
            "projected_slots": list(self.projected_slots),
            # Named, not merely excluded (#499). An exemption nobody is told
            # about reads as a slot that was checked and agreed, which is the
            # opposite of what happened.
            "per_record_slots": list(self.per_record_slots),
            "errors": [asdict(issue) for issue in self.errors],
            "warnings": [asdict(issue) for issue in self.warnings],
        }


def _normalized_bool(value: Optional[bool]) -> bool:
    return bool(value)


def _slot_value_signature(slot: SlotDefinition) -> Tuple[Any, ...]:
    """Return properties that determine a slot's YAML value structure."""

    return (
        slot.range,
        _normalized_bool(slot.multivalued),
        _normalized_bool(slot.required),
        slot.minimum_cardinality,
        slot.maximum_cardinality,
        _normalized_bool(slot.inlined_as_list),
    )


def _is_per_record(slot: SlotDefinition) -> bool:
    """Is this slot annotated as describing the record rather than the dataset?

    Subscript access, not `.get`: LinkML surfaces `annotations` as a
    `jsonasobj2.JsonObj`, which has no `.get`. The first version of this called
    it inside `except AttributeError: return False`, so every slot silently
    read as unmarked and the annotation did nothing — a check that cannot fail
    is worse than no check, because the schema then claims a guarantee that is
    not enforced. The except clause here is narrow and re-raises nothing else.

    Tolerant about the value's form, because it may arrive as an `Annotation`
    object, a plain string or a bool depending on how the schema was loaded.
    Anything falsy or the literal string `false` is not a marking — present and
    set to false must not silently mean the same as present and set to true.
    """
    annotations = getattr(slot, "annotations", None)
    if annotations is None:
        return False
    try:
        entry = annotations[PER_RECORD_ANNOTATION]
    except (KeyError, TypeError):
        return False
    if entry is None:
        return False
    value = getattr(entry, "value", entry)
    if isinstance(value, str):
        return value.strip().lower() not in ("", "false", "no", "0")
    return bool(value)


def load_pair_schema(
    full_schema: Path = DEFAULT_FULL_SCHEMA,
    core_schema: Path = DEFAULT_CORE_SCHEMA,
) -> PairSchema:
    """Load schemas and derive strict-identity versus projected shared slots."""

    full_view = SchemaView(str(full_schema))
    core_view = SchemaView(str(core_schema))
    full_slots = {
        slot.name: slot for slot in full_view.class_induced_slots(FULL_CLASS)
    }
    core_slots = {
        slot.name: slot for slot in core_view.class_induced_slots(CORE_CLASS)
    }

    identity_slots = []
    projected_slots = []
    per_record_slots = []
    for name in sorted(full_slots.keys() & core_slots.keys()):
        # Checked before the signature comparison, because a per-record slot
        # has an *identical* signature — that is precisely why it fell into
        # strict identity and became unrepresentable. Signature equality is
        # the right test for whether two slots hold the same shape, and the
        # wrong test for whether they hold the same fact.
        if _is_per_record(full_slots[name]) or _is_per_record(core_slots[name]):
            per_record_slots.append(name)
        elif _slot_value_signature(full_slots[name]) == _slot_value_signature(
            core_slots[name]
        ):
            identity_slots.append(name)
        else:
            projected_slots.append(name)

    return PairSchema(
        full_view=full_view,
        core_view=core_view,
        identity_slots=tuple(identity_slots),
        projected_slots=tuple(projected_slots),
        per_record_slots=tuple(per_record_slots),
    )


def _first_difference(
    full_value: Any, core_value: Any, path: str
) -> Optional[Tuple[str, str]]:
    """Return the first deep difference, preserving list-order significance."""

    if type(full_value) is not type(core_value):
        return (
            path,
            f"type differs: full={type(full_value).__name__}, "
            f"core={type(core_value).__name__}",
        )

    if isinstance(full_value, Mapping):
        full_keys = set(full_value)
        core_keys = set(core_value)
        if full_keys != core_keys:
            missing_core = sorted(full_keys - core_keys)
            missing_full = sorted(core_keys - full_keys)
            return (
                path,
                "mapping keys differ: "
                f"missing from core={missing_core}, missing from full={missing_full}",
            )
        for key in full_value:
            difference = _first_difference(
                full_value[key], core_value[key], f"{path}.{key}"
            )
            if difference:
                return difference
        return None

    if isinstance(full_value, list):
        if len(full_value) != len(core_value):
            return (
                path,
                f"list length differs: full={len(full_value)}, "
                f"core={len(core_value)}",
            )
        for index, (full_item, core_item) in enumerate(
            zip(full_value, core_value)
        ):
            difference = _first_difference(
                full_item, core_item, f"{path}[{index}]"
            )
            if difference:
                return difference
        return None

    if full_value != core_value:
        return (
            path,
            f"value differs: full={full_value!r}, core={core_value!r}",
        )
    return None


def _append_identity_errors(
    report: PairConsistencyReport,
    full_data: Mapping[str, Any],
    core_data: Mapping[str, Any],
    slots: Iterable[str],
    path: str = "$",
    schema_moved: bool = False,
    slot_existed=None,
) -> None:
    """Compare the slots a full/core pair must state identically.

    `schema_moved` says the pair was generated against a schema that is no
    longer the current one. Presence is then a **warning** rather than an
    error (#520): a slot added after the pair was written is absent from core
    because it could not have been present, which is a fact about the schema's
    history and not a defect in the record.

    Content disagreement stays an error either way. Two records asserting
    different values for one slot were wrong when they were written and are
    wrong now — no schema change excuses that.

    Scoped by the recorded schema digest rather than by a date, so it rests on
    what the run actually consumed rather than on a cutoff someone maintains.
    Adding `related_datasets` to core made 70 historical pairs report this,
    all correctly and none actionably; back-filling them would have made a
    2026-07-28 record assert content no run of that date produced.
    """
    for slot in slots:
        full_present = slot in full_data
        core_present = slot in core_data
        slot_path = f"{path}.{slot}"
        if full_present != core_present:
            present_in = "full" if full_present else "core"
            # Per slot where the ledger can answer, broad where it cannot
            # (#580). `schema_moved` alone downgrades *every* presence mismatch
            # whenever the digest differs at all, so an unrelated schema edit
            # suppressed real defects. The ledger records which slots each
            # digest had, so a slot that demonstrably existed at the run's
            # digest stays an error; one that did not is genuinely excused; and
            # an unrecorded digest falls back to the old behaviour rather than
            # guessing.
            excused = schema_moved
            if schema_moved and slot_existed is not None:
                existed = slot_existed(slot)
                if existed is True:
                    excused = False
            issue = ConsistencyIssue(
                code="shared-slot-presence",
                path=slot_path,
                message=(
                    "schema-identical slot is present only in "
                    f"{present_in}; it must be present in both or neither"
                    + (" — but this pair predates the current schema, so the "
                       "slot may not have existed when it was written"
                       if excused else "")
                ),
            )
            (report.warnings if excused else report.errors).append(issue)
            continue
        if not full_present:
            continue

        difference = _first_difference(
            full_data[slot], core_data[slot], slot_path
        )
        if difference:
            difference_path, message = difference
            report.errors.append(
                ConsistencyIssue(
                    code="shared-slot-content",
                    path=difference_path,
                    message=message,
                )
            )


def _index_by_id(
    items: Sequence[Any], path: str, report: PairConsistencyReport
) -> Dict[str, Mapping[str, Any]]:
    indexed: Dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        if not isinstance(item, Mapping):
            report.errors.append(
                ConsistencyIssue(
                    code="projected-item-type",
                    path=item_path,
                    message="projected resource must be a mapping",
                )
            )
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            report.errors.append(
                ConsistencyIssue(
                    code="projected-item-id",
                    path=f"{item_path}.id",
                    message="projected resource requires a non-empty string id",
                )
            )
            continue
        if item_id in indexed:
            report.errors.append(
                ConsistencyIssue(
                    code="projected-item-duplicate",
                    path=f"{item_path}.id",
                    message=f"duplicate resource id: {item_id}",
                )
            )
            continue
        indexed[item_id] = item
    return indexed


def _append_resource_projection_errors(
    report: PairConsistencyReport,
    full_resources: Any,
    core_resources: Any,
    identity_slots: Iterable[str],
    path: str = "$.resources",
) -> None:
    if not isinstance(full_resources, list) or not isinstance(
        core_resources, list
    ):
        report.errors.append(
            ConsistencyIssue(
                code="resource-projection-type",
                path=path,
                message="full and core resources must both be lists",
            )
        )
        return

    full_by_id = _index_by_id(full_resources, f"{path}.full", report)
    core_by_id = _index_by_id(core_resources, f"{path}.core", report)
    full_ids = set(full_by_id)
    core_ids = set(core_by_id)
    if full_ids != core_ids:
        report.errors.append(
            ConsistencyIssue(
                code="resource-projection-coverage",
                path=path,
                message=(
                    "resource ids differ: "
                    f"missing from core={sorted(full_ids - core_ids)}, "
                    f"missing from full={sorted(core_ids - full_ids)}"
                ),
            )
        )

    for item_id in sorted(full_ids & core_ids):
        full_item = full_by_id[item_id]
        core_item = core_by_id[item_id]
        item_path = f"{path}[id={item_id!r}]"
        _append_identity_errors(
            report,
            full_item,
            core_item,
            identity_slots,
            path=item_path,
        )

        full_nested = full_item.get("resources")
        core_nested = core_item.get("resources")
        if (full_nested is None) != (core_nested is None):
            report.errors.append(
                ConsistencyIssue(
                    code="resource-projection-presence",
                    path=f"{item_path}.resources",
                    message=(
                        "nested resources are present in only one projected "
                        "resource"
                    ),
                )
            )
        elif full_nested is not None:
            _append_resource_projection_errors(
                report,
                full_nested,
                core_nested,
                identity_slots,
                path=f"{item_path}.resources",
            )


def _nested_resources(
    collections: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Every `File` nested under a collection's `resources` (#401).

    Flattened across collections rather than searched per collection, because
    a core distribution names the file, not the collection it sits in — and
    `_related_match` already refuses an ambiguous match, so two files sharing
    an id anywhere in the record are reported rather than silently resolved to
    whichever came first.
    """
    out: list[Mapping[str, Any]] = []
    for collection in collections:
        resources = collection.get("resources")
        if not isinstance(resources, list):
            continue
        out.extend(item for item in resources if isinstance(item, Mapping))
    return out


def _related_match(
    distribution: Mapping[str, Any],
    collections: Sequence[Mapping[str, Any]],
) -> Tuple[Optional[Mapping[str, Any]], Optional[str]]:
    for key in ("id", "path", "name"):
        value = distribution.get(key)
        if value in (None, ""):
            continue
        matches = [item for item in collections if item.get(key) == value]
        if len(matches) == 1:
            return matches[0], key
        if len(matches) > 1:
            return None, f"ambiguous {key}"
    return None, None


def _append_distribution_relation_issues(
    report: PairConsistencyReport,
    full_data: Mapping[str, Any],
    core_data: Mapping[str, Any],
) -> None:
    collections = full_data.get("file_collections")
    distributions = core_data.get("distributions")
    if not collections and not distributions:
        return
    if not isinstance(collections, list) or not collections:
        report.errors.append(
            ConsistencyIssue(
                code="distribution-relation-presence",
                path="$.file_collections",
                message=(
                    "core distributions exist without full file_collections"
                ),
            )
        )
        return
    if not isinstance(distributions, list) or not distributions:
        report.errors.append(
            ConsistencyIssue(
                code="distribution-relation-presence",
                path="$.distributions",
                message=(
                    "full file_collections exist without core distributions"
                ),
            )
        )
        return

    mapping_collections = [
        item for item in collections if isinstance(item, Mapping)
    ]
    nested_files = _nested_resources(mapping_collections)
    matched = 0
    matched_nested = 0
    unmatched = []
    for index, distribution in enumerate(distributions):
        if not isinstance(distribution, Mapping):
            report.errors.append(
                ConsistencyIssue(
                    code="distribution-item-type",
                    path=f"$.distributions[{index}]",
                    message="distribution must be a mapping",
                )
            )
            continue
        collection, match_basis = _related_match(
            distribution, mapping_collections
        )
        level = "collection"
        if collection is None and match_basis is None:
            # Only on a *clean* miss. `_related_match` returns
            # (None, "ambiguous <key>") when two collections share an
            # identifier, which is a data defect; descending past it and
            # finding one nested file would report a tidy resource-level match
            # and delete the ambiguity from the output (#474). That would make
            # the defect less visible than before this change, inverting what
            # #401 is for.
            #
            # Descend into each collection's nested `resources` (#401).
            # `FileCollection` is collection-level — total_bytes, file_count,
            # collection_type — while `CoreDistribution` is file-level — bytes,
            # hash, md5, sha256, path, media_type. So a core record that
            # enumerates one distribution per *file* is doing the correct
            # thing, and matching only at the top level reported all 12 of
            # VOICE_PEDIATRIC's as unmatched when every one matched a nested
            # File by id, with name, path and bytes agreeing and zero conflicts.
            collection, match_basis = _related_match(distribution, nested_files)
            level = "resource"
        if collection is None:
            unmatched.append(index)
            continue
        matched += 1
        if level == "resource":
            matched_nested += 1
        relation_path = f"$.distributions[{index}]"
        for field_name in ("path", "compression"):
            if (
                field_name in distribution
                and field_name in collection
                and distribution[field_name] != collection[field_name]
            ):
                report.errors.append(
                    ConsistencyIssue(
                        code="distribution-related-content",
                        path=f"{relation_path}.{field_name}",
                        message=(
                            f"value conflicts with matched file_collection "
                            f"({match_basis}): full={collection[field_name]!r}, "
                            f"core={distribution[field_name]!r}"
                        ),
                    )
                )
        # A collection carries `total_bytes`; a nested File carries `bytes`.
        # Comparing a file-level size against a collection total would be a
        # category error, so the counterpart field follows the match level.
        size_field = "total_bytes" if level == "collection" else "bytes"
        if (
            "bytes" in distribution
            and size_field in collection
            and distribution["bytes"] != collection[size_field]
        ):
            report.errors.append(
                ConsistencyIssue(
                    code="distribution-related-content",
                    path=f"{relation_path}.bytes",
                    message=(
                        "value conflicts with matched "
                        f"file_collection.{size_field}: "
                        f"full={collection[size_field]!r}, "
                        f"core={distribution['bytes']!r}"
                    ),
                )
            )

    at_collection = matched - matched_nested
    report.warnings.append(
        ConsistencyIssue(
            code="semantic-review-required",
            path="$.file_collections <-> $.distributions",
            message=(
                "Phase 4 must semantically review related distribution "
                f"content; deterministic matches={matched} "
                f"({at_collection} at collection level, "
                f"{matched_nested} at nested resource level), "
                f"unmatched core distributions={unmatched}"
            ),
        )
    )


def _slot_resolver(run_digest: str | None):
    """A callable(slot) -> bool|None over the digest ledger, or None."""
    if not run_digest:
        return None
    from data_sheets_schema import schema_digest

    def existed(slot: str):
        return schema_digest.slot_existed_at(run_digest, CORE_CLASS, slot)
    return existed


def validate_pair_data(
    full_data: Mapping[str, Any],
    core_data: Mapping[str, Any],
    pair_schema: PairSchema,
    schema_moved: bool = False,
    run_digest: str | None = None,
) -> PairConsistencyReport:
    """Validate strict shared content and schema-related projections.

    `run_digest` is the schema digest the pair was generated against. Given
    one, a presence mismatch is excused only for slots the digest ledger shows
    did not exist then; without one, `schema_moved` applies broadly as before
    (#580).
    """

    report = PairConsistencyReport(
        identity_slots=pair_schema.identity_slots,
        projected_slots=pair_schema.projected_slots,
        per_record_slots=pair_schema.per_record_slots,
    )
    _append_identity_errors(
        report,
        full_data,
        core_data,
        pair_schema.identity_slots,
        schema_moved=schema_moved,
        slot_existed=_slot_resolver(run_digest),
    )

    if "resources" in pair_schema.projected_slots:
        full_present = "resources" in full_data
        core_present = "resources" in core_data
        if full_present != core_present:
            report.errors.append(
                ConsistencyIssue(
                    code="resource-projection-presence",
                    path="$.resources",
                    message=(
                        "resources must be represented in both records when "
                        "present in either record"
                    ),
                )
            )
        elif full_present:
            _append_resource_projection_errors(
                report,
                full_data["resources"],
                core_data["resources"],
                pair_schema.identity_slots,
            )

    _append_distribution_relation_issues(report, full_data, core_data)
    return report


def _project_resource(
    full_item: Mapping[str, Any],
    existing_core_item: Optional[Mapping[str, Any]],
    identity_slots: Iterable[str],
) -> Dict[str, Any]:
    allowed = set(identity_slots)
    projected: Dict[str, Any] = {}
    for key, value in full_item.items():
        if key in allowed:
            projected[key] = copy.deepcopy(value)
        elif key == "resources" and isinstance(value, list):
            existing_nested = {}
            if existing_core_item and isinstance(
                existing_core_item.get("resources"), list
            ):
                existing_nested = {
                    item.get("id"): item
                    for item in existing_core_item["resources"]
                    if isinstance(item, Mapping) and isinstance(item.get("id"), str)
                }
            projected["resources"] = [
                _project_resource(
                    item,
                    existing_nested.get(item.get("id")),
                    identity_slots,
                )
                for item in value
                if isinstance(item, Mapping)
            ]

    if existing_core_item:
        for core_only_slot in ("dialect", "distributions"):
            if core_only_slot in existing_core_item:
                projected[core_only_slot] = copy.deepcopy(
                    existing_core_item[core_only_slot]
                )
    return projected


def synchronize_core_data(
    full_data: Mapping[str, Any],
    core_data: Mapping[str, Any],
    pair_schema: PairSchema,
) -> Dict[str, Any]:
    """Copy schema-identical values from a source-audited full record to core."""

    synchronized = copy.deepcopy(dict(core_data))
    for slot in pair_schema.identity_slots:
        if slot in full_data:
            synchronized[slot] = copy.deepcopy(full_data[slot])
        else:
            synchronized.pop(slot, None)

    if "resources" in pair_schema.projected_slots:
        if "resources" not in full_data:
            synchronized.pop("resources", None)
        else:
            existing_resources = {
                item.get("id"): item
                for item in synchronized.get("resources", [])
                if isinstance(item, Mapping) and isinstance(item.get("id"), str)
            }
            synchronized["resources"] = [
                _project_resource(
                    item,
                    existing_resources.get(item.get("id")),
                    pair_schema.identity_slots,
                )
                for item in full_data["resources"]
                if isinstance(item, Mapping)
            ]
    return synchronized


def pair_predates_current_schema(core_path: Path) -> bool:
    """Was this pair generated against a schema that has since moved? (#520)

    Read from the core record's own provenance — the `schema.digest_md5` the
    run recorded — rather than from a date or a hand-maintained list of when
    each slot arrived. A run states which schema it saw; that is the evidence,
    and it is the same field #517's straddle check reads.

    Absent provenance returns False, which is the strict reading: a pair that
    cannot show it predates the schema is held to the current one. Silence is
    not a licence.
    """
    from data_sheets_schema import schema_digest

    provenance = core_path.parent / f"{core_path.name.split('_d4d')[0]}_provenance.yaml"
    if not provenance.exists():
        return False
    try:
        data = yaml.safe_load(provenance.read_text(encoding="utf-8")) or {}
    except Exception:                                          # noqa: BLE001
        return False
    recorded = (data.get("schema") or {}).get("digest_md5")
    if not recorded:
        return False
    live = schema_digest.fingerprint(schema_digest.digest_text(FULL_CLASS))
    return recorded != live


def _load_yaml_mapping(path: Path) -> Dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return loaded


def _read_comment_header(path: Path) -> List[str]:
    header = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            header.append(line)
            continue
        if not line.strip() and header:
            header.append(line)
            continue
        break
    return header


def _write_synchronized_core(
    path: Path, core_data: Mapping[str, Any]
) -> None:
    header = _read_comment_header(path)
    if PHASE4_HEADER not in header:
        header.append(PHASE4_HEADER)
    body = yaml.safe_dump(
        dict(core_data),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=100,
    ).rstrip()
    path.write_text("\n".join(header + [body, ""]), encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Phase 4 consistency between a full D4D and D4D-core pair."
        )
    )
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument(
        "--full-schema", type=Path, default=DEFAULT_FULL_SCHEMA
    )
    parser.add_argument(
        "--core-schema", type=Path, default=DEFAULT_CORE_SCHEMA
    )
    parser.add_argument(
        "--sync-core",
        action="store_true",
        help=(
            "Copy schema-identical slots and projected resources from full to "
            "core before validation. Use only after the full record passes the "
            "Phase 3 source audit."
        ),
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    pair_schema = load_pair_schema(args.full_schema, args.core_schema)
    full_data = _load_yaml_mapping(args.full)
    core_data = _load_yaml_mapping(args.core)

    if args.sync_core:
        core_data = synchronize_core_data(full_data, core_data, pair_schema)
        _write_synchronized_core(args.core, core_data)

    report = validate_pair_data(
        full_data, core_data, pair_schema,
        schema_moved=pair_predates_current_schema(args.core))
    if args.as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        status = "PASS" if report.passed else "FAIL"
        print(
            f"{status}: {len(report.identity_slots)} schema-identical slots; "
            f"projected slots={list(report.projected_slots)}; "
            f"per-record slots (exempt, must differ)="
            f"{list(report.per_record_slots)}"
        )
        for issue in report.errors:
            print(f"ERROR [{issue.code}] {issue.path}: {issue.message}")
        for issue in report.warnings:
            print(f"WARNING [{issue.code}] {issue.path}: {issue.message}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
