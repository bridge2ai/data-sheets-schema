"""Offline saved native-message acceptance for draft nested support (#4282).

Nothing here executes a request, authenticates a provider, reads a judgement
cache, or changes the readiness of the captured plan. Old planners are readers
of different contracts and remain unchanged.
"""
from __future__ import annotations

from collections import Counter
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import stat

import yaml

from data_sheets_schema import evidence_assertions, support_targets as targets
from data_sheets_schema.duplicate_keys import nesting_exceeds
from data_sheets_schema.support_judge import VERDICTS
from data_sheets_schema.support_plan import canonical, sha256

FORMAT = "nested_support_result_v1"
ADAPTER = "native_message_json_v1"
RESPONSE_FORMAT = "nested_support_response_v1"
MAX_MANIFEST_BYTES = 64_000_000
MAX_ARTIFACT_BYTES = 64_000_000
MAX_CAPTURE_BYTES = 512_000_000
MAX_RESPONSE_BYTES = 8_000_000
MAX_ENVELOPE_BYTES = 12_000_000
MAX_NODES = 2_000_000
MAX_DEPTH = 64
CONTRACT = {
    "format": FORMAT, "adapter": ADAPTER, "response_envelope": RESPONSE_FORMAT, "axis": "grounding_v3",
    "verdicts": list(VERDICTS), "completion": "end_turn",
    "model_match": "exact", "attempt_selection": "one_explicit_attempt_per_target",
    "content": "one_text_block_and_optional_thinking_or_redacted_thinking",
    "required_usage": ["input_tokens", "output_tokens"],
    "limits": {"manifest_bytes": MAX_MANIFEST_BYTES, "artifact_bytes": MAX_ARTIFACT_BYTES,
               "capture_bytes": MAX_CAPTURE_BYTES, "response_bytes": MAX_RESPONSE_BYTES,
               "envelope_bytes": MAX_ENVELOPE_BYTES,
               "nodes": MAX_NODES, "depth": MAX_DEPTH},
}
LIMITATIONS = [
    "Caller-supplied saved bytes do not authenticate a provider call.",
    "Envelope binding hashes are caller declarations; replay rejection is not provider authentication.",
    "Mechanical response acceptance does not establish scientific support accuracy or calibration.",
    "No full-record schema validation or paid-run readiness is established.",
    "Unselected records and fitness responses are not measured by this protocol.",
]
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ATTEMPT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


class ResultError(ValueError):
    """Saved evidence does not meet this explicitly selected offline contract."""


def _require(condition, message):
    if not condition:
        raise ResultError(message)


def _mapping(value, label):
    _require(isinstance(value, dict), f"{label} must be a mapping")
    return value


def _text(value, label):
    _require(isinstance(value, str) and bool(value.strip()), f"{label} must be nonblank text")
    return value


def _integer(value, label, *, positive=False):
    _require(type(value) is int and value >= int(positive), f"{label} must be an integer in range")
    return value


def _read(raw, label, *, limit=MAX_ARTIFACT_BYTES, yaml_allowed=False):
    _require(type(raw) is bytes and 0 < len(raw) <= limit, f"{label} exceeds byte bounds or is empty")
    try:
        text = raw.decode("utf-8")
        if nesting_exceeds(text, yaml.SafeLoader, MAX_DEPTH):
            raise ValueError("depth bound exceeded")
        value = (yaml.load(text, Loader=targets._UniqueLoader) if yaml_allowed
                 else evidence_assertions.load_json(text))
        targets._validate_json(value, max_nodes=MAX_NODES, max_depth=MAX_DEPTH)
        # JSON escapes can encode lone surrogates even when the input bytes
        # decode as UTF-8. Reject them before any normalized result is written.
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, str):
                item.encode("utf-8")
            elif isinstance(item, dict):
                pending.extend(item)
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
    except (ValueError, TypeError, RecursionError, UnicodeError, yaml.YAMLError) as exc:
        raise ResultError(f"{label} is not bounded, duplicate-free structured data") from exc
    return value


def _pin(raw):
    return {"sha256": sha256(raw), "bytes": len(raw)}


def _file(path: Path, limit: int) -> bytes:
    """Read one regular file through one descriptor, refusing final symlinks."""
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        with os.fdopen(os.open(path, flags), "rb") as stream:
            _require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "input must be a regular file")
            raw = stream.read(limit + 1)
    except OSError as exc:
        raise ResultError(f"cannot read evidence file: {path.name}") from exc
    _require(len(raw) <= limit, f"evidence file exceeds {limit}-byte bound")
    return raw


class Capture:
    """One bounded byte snapshot per artifact digest in one checking operation."""
    def __init__(self, root: Path):
        root = Path(root)
        _require(not root.is_symlink() and root.is_dir(), "evidence directory must be a real directory")
        self.root = root.resolve()
        self.blobs = {}
        self.total = 0

    def add(self, raw):
        pin = _pin(raw)
        if pin["sha256"] not in self.blobs:
            _require(self.total + len(raw) <= MAX_CAPTURE_BYTES, "captured evidence exceeds total byte bound")
            self.blobs[pin["sha256"]] = raw
            self.total += len(raw)
        return pin

    def entry(self, name, *, limit=MAX_MANIFEST_BYTES):
        raw = _file(self.root / name, limit)
        self.add(raw)
        return raw

    def get(self, pin, *, limit=MAX_ARTIFACT_BYTES):
        _mapping(pin, "artifact pin")
        digest, length = pin.get("sha256"), pin.get("bytes")
        _require(isinstance(digest, str) and bool(_SHA.fullmatch(digest)), "invalid artifact SHA256")
        _require(type(length) is int and 0 <= length <= limit, "invalid artifact byte length")
        if digest not in self.blobs:
            directory = self.root / "artifacts"
            _require(not directory.is_symlink() and directory.is_dir(), "artifact directory cannot be a symlink")
            self.add(_file(directory / digest, limit))
        _require(digest in self.blobs, "artifact digest differs from its captured bytes")
        raw = self.blobs[digest]
        _require(len(raw) == length, "artifact byte length differs from its pin")
        return raw

    def document(self, pin, label, *, yaml_allowed=False):
        return _mapping(_read(self.get(pin), label, yaml_allowed=yaml_allowed), label)


def _schema(capture, schema):
    """Rebuild specification from captured imports, without ambient file reads."""
    from linkml_runtime.dumpers import json_dumper
    from linkml_runtime.linkml_model.meta import SchemaDefinition
    from data_sheets_schema.schema_snapshot import SchemaSnapshot
    from data_sheets_schema.schema_view import captured_view, version_document

    sources = schema.get("sources")
    _require(isinstance(sources, list) and bool(sources), "schema requires a captured closure")
    rows, by_name, by_path = [], {}, {}
    for source in sources:
        _mapping(source, "schema source")
        name = _text(source.get("import_key"), "schema import key")
        path = Path(_text(source.get("path"), "schema source path"))
        _require(name not in by_name and path not in by_path, "duplicate schema source identity")
        raw = capture.get(source)
        _read(raw, "schema source", yaml_allowed=True)
        by_name[name], by_path[path] = (path, raw), name
        rows.append((name, path, raw))
    snapshot = SchemaSnapshot(tuple(rows), (str(rows[0][1]), sha256(canonical(sources))))
    root_class = _text(schema.get("class"), "schema root class")
    vocabulary = {}
    if schema.get("vocabulary") is not None:
        vocabulary = capture.document(schema["vocabulary"], "vocabulary", yaml_allowed=True).get("vocabularies")
        _require(isinstance(vocabulary, dict), "captured vocabulary has no vocabularies mapping")
    with captured_view(snapshot) as view:
        # Resolve the original logical import keys, never today's LinkML package
        # installation path. Original paths remain opaque lineage metadata.
        def load(imp, from_schema=None):
            parent = by_path[Path((from_schema or view.schema).source_file)]
            name = str(imp)
            if "/" in parent and ":" not in name:
                name = posixpath.normpath(posixpath.join(posixpath.dirname(parent), name))
            _require(name in by_name, "schema import is outside the captured closure")
            path, raw = by_name[name]
            parsed = SchemaDefinition(**version_document(raw))
            parsed.source_file = str(path)
            return parsed
        view.load_import = load
        _require(view.get_class(root_class) is not None, "captured schema has no selected root class")
        classes, enums, pending = {}, {}, [root_class]
        while pending:
            name = pending.pop()
            if name in classes:
                continue
            definition = view.get_class(name)
            pending.extend(str(p) for p in [definition.is_a, *(definition.mixins or [])]
                           if p and view.get_class(str(p)) is not None)
            slots = {}
            classes[name] = {"definition": json.loads(json_dumper.dumps(definition)), "slots": slots}
            for slot in view.class_induced_slots(name):
                rng = str(slot.range) if slot.range else None
                target = view.get_class(rng) if rng else None
                slots[str(slot.name)] = {"definition": json.loads(json_dumper.dumps(slot)),
                    "range_class": bool(target), "inline": bool(target and view.is_inlined(slot))}
                if target:
                    pending.append(rng)
                enum = view.get_enum(rng) if rng else None
                if enum:
                    enums[rng] = json.loads(json_dumper.dumps(enum))
    payload = {"root_class": root_class, "schema_sources": sorted((n, sha256(r)) for n, _, r in rows),
               "classes": classes, "enums": enums, "vocabulary": vocabulary}
    rebuilt = targets.NestedSupportSchema(targets._canonical(payload))
    recorded = capture.get(schema["nested_specification"])
    _require(recorded == rebuilt.payload_json.encode(), "captured specification differs from its schema closure")
    _require(schema.get("nested_specification_sha256") == rebuilt.digest, "nested specification digest conflicts")
    return rebuilt


def _expand(value, capture):
    if isinstance(value, dict):
        if set(value) == {"$text"}:
            return capture.get(value["$text"]).decode("utf-8")
        return {k: _expand(v, capture) for k, v in value.items()}
    return [_expand(v, capture) for v in value] if isinstance(value, list) else value


def _index(rows, label):
    _require(isinstance(rows, list), f"{label} must be a list")
    result = {}
    for row in rows:
        _mapping(row, label)
        key = _text(row.get("id"), f"{label} id")
        _require(key not in result, f"duplicate {label} id")
        result[key] = row
    return result


def _instrument(capture, manifest):
    instrument = _mapping(manifest.get("instruments"), "plan instruments").get(targets.AXIS)
    _require(isinstance(instrument, dict), "nested instrument is missing")
    policy = instrument.get("policy")
    context_policy = instrument.get("context_policy", targets.CONTEXT_POLICY)
    name, system = targets.policy_instrument(policy, context_policy=context_policy)
    _require(instrument.get("name") == name and capture.get(instrument["system"]) == system.encode(),
             "nested instrument differs")
    return policy


def _representation_declarations(manifest, records, planned, policy):
    """Check declared accounting, without claiming unselected record validation."""
    counts = manifest["counts"]
    if policy == targets.POLICY:
        _require("representation_issues" not in manifest and "representation_issue_count" not in counts
                 and all("representation_issues" not in r and "representation_issue_count" not in r
                         for r in records.values()), "strict plan cannot declare scalar-policy representations")
        return
    issues = manifest.get("representation_issues")
    _require(isinstance(issues, list), "representation issues must be a list")
    _integer(counts.get("representation_issue_count"), "representation issue count")
    _require(counts["representation_issue_count"] == len(issues), "representation issue count conflicts")
    seen = set()
    for issue in issues:
        _require(isinstance(issue, dict) and set(issue) == {"record_id", "pointer", "kind", "code", "range"},
                 "invalid representation issue")
        rid, pointer = issue["record_id"], issue["pointer"]
        _require(isinstance(rid, str) and rid in records, "unknown representation record")
        targets.pointer_tokens(pointer)
        _require(issue["kind"] == "relationship_edge" and issue["code"] == "inline_class_requires_mapping",
                 "unknown representation issue kind/code")
        _text(issue["range"], "representation range")
        _require((rid, pointer) not in seen, "duplicate representation issue")
        seen.add((rid, pointer))
        _require(f"{rid}:{targets.AXIS}:relationship_edge:{pointer}" in planned,
                 "representation issue lacks a relationship target")
    for rid, record in records.items():
        expected = [issue for issue in issues if issue["record_id"] == rid]
        _integer(record.get("representation_issue_count"), "record representation issue count")
        _require(record.get("representation_issues") == expected
                 and record["representation_issue_count"] == len(expected),
                 "record representation accounting conflicts")


def _manifest(capture, raw):
    manifest = _mapping(_read(raw, "plan manifest", limit=MAX_MANIFEST_BYTES), "plan manifest")
    _require(manifest.get("format") == "d4d-support-plan-v2" and manifest.get("mode") == "offline_dry_run",
             "only an offline nested plan v2 is eligible")
    _require(manifest.get("value_identity_encoding") == "typed-yaml-v1", "unknown value identity encoding")
    _require(manifest.get("granularity") == "nested_support_and_top_level_fitness", "unknown plan granularity")
    policy = _instrument(capture, manifest)
    readiness = _mapping(manifest.get("readiness"), "plan readiness")
    required = {"independent_empirical_calibration_3343", "context_projection_review_3342",
                "instrument_review_3342", "scientific_control_acceptance",
                "v3_response_and_execution_registration", "provider_transport_registration", "paid_run_authorization"}
    blockers = readiness.get("blockers")
    _require(readiness.get("ready_for_paid_run") is False and isinstance(blockers, list)
             and all(isinstance(x, str) for x in blockers) and required <= set(blockers),
             "draft-plan blockers/readiness cannot be removed by response acceptance")
    records = _index(manifest.get("records"), "record")
    planned = _index(manifest.get("targets"), "target")
    _require(bool(records) and bool(planned), "plan requires records and targets")
    for row in planned.values():
        _require(row.get("record_id") in records, "target refers to an unknown record")
        targets.pointer_tokens(row.get("pointer"))
        axis, kind = row.get("axis"), row.get("kind")
        _require((axis == targets.AXIS and kind in targets.KINDS)
                 or (axis == "fitness" and kind == "top_level_field"), "unknown target axis or kind")
        expected = (f"{row['record_id']}:{axis}:{kind}:{row['pointer']}" if axis == targets.AXIS
                    else f"{row['record_id']}:fitness:{row['pointer']}")
        _require(row["id"] == expected and row.get("propagated") is False
                 and row.get("status") == "planned_not_measured", "target identity/status is inconsistent")
        if axis == targets.AXIS:
            _require(row.get("result_contract") == "unregistered_v3_no_cache_or_executor",
                     "response acceptance cannot replace an unregistered execution contract")
    counts = _mapping(manifest.get("counts"), "plan counts")
    for key, actual in {"records": len(records), "axis_targets": len(planned),
            "by_axis": dict(Counter(t["axis"] for t in planned.values())),
            "support_by_kind": dict(Counter({k: 0 for k in targets.KINDS}) + Counter(
                t["kind"] for t in planned.values() if t["axis"] == targets.AXIS)),
            "fitness_top_level": sum(t["axis"] == "fitness" for t in planned.values())}.items():
        if key == "support_by_kind":
            actual = {k: actual.get(k, 0) for k in targets.KINDS}
        recorded = counts.get(key)
        if isinstance(actual, int):
            _integer(recorded, f"plan {key} count")
        else:
            _mapping(recorded, f"plan {key} counts")
            for n in recorded.values():
                _integer(n, f"plan {key} count")
        _require(counts.get(key) == actual, f"declared plan {key} count differs from target list")
    blocked = manifest.get("blocked_paths")
    _require(isinstance(blocked, list) and counts.get("blocked") == len(blocked), "blocked-path counts conflict")
    _require(all(isinstance(b, dict) and b.get("record_id") in records for b in blocked), "unknown blocked record")
    _integer(counts.get("blocked"), "blocked count")
    for rid, record in records.items():
        listed = [b for b in blocked if b["record_id"] == rid]
        _require(record.get("blocked_paths") == listed and record.get("blocked_count") == len(listed),
                 "per-record blocked paths differ from the plan list")
        _integer(record.get("blocked_count"), "record blocked count")
        _integer(record.get("populated_top_level_fields"), "populated field count")
        _integer(record.get("fitness_top_level_targets"), "record fitness count")
        _require(record["fitness_top_level_targets"] == sum(
            t["record_id"] == rid and t["axis"] == "fitness" for t in planned.values()), "record fitness count conflicts")
    _integer(counts.get("populated_top_level_fields"), "plan populated field count")
    _require(counts["populated_top_level_fields"] == sum(r["populated_top_level_fields"] for r in records.values()),
             "populated field totals conflict")
    for key in ("blocked_by_axis", "blocked_by_cause"):
        for count in _mapping(counts.get(key), key).values():
            _integer(count, key)
    _require(counts.get("blocked_by_axis") == dict(Counter(b.get("axis") for b in blocked))
             and counts.get("blocked_by_cause") == dict(Counter(b.get("code") for b in blocked)),
             "blocked-path category totals conflict")
    _representation_declarations(manifest, records, planned, policy)
    model = _mapping(manifest.get("model"), "model selection")
    _text(model.get("name"), "model")
    if "configuration" in model:
        cfg = _mapping(model["configuration"], "model configuration")
        raw_config = capture.get(cfg["artifact"])
        _require(sha256(raw_config) == cfg.get("sha256"), "model config pin conflicts")
        config = _mapping(_read(raw_config, "model config", yaml_allowed=True), "model config")
        _require(set(config) == {"version", "model"} and type(config["version"]) is int
                 and config["version"] == 1, "unsupported captured model config")
        expected = model.get("generation_model") if config["model"] is None else config["model"]
        basis = "defaults_to_generation_model" if config["model"] is None else "evaluation_config"
        _require(expected == model["name"] and model.get("basis") == basis
                 and type(cfg.get("version")) is int and cfg["version"] == 1,
                 "captured config did not select the declared model/basis")
    else:
        _require(model.get("basis") == "explicit_override", "default model selection lacks its captured config")
    return manifest, records, planned


def _bindings(capture, manifest, records, planned, selections):
    _require(isinstance(selections, list) and bool(selections), "select at least one explicit target/attempt")
    seen_targets, seen_attempts = set(), set()
    for row in selections:
        _require(isinstance(row, dict) and set(row) == {"target_id", "attempt_id"}, "invalid target/attempt selection")
        target_id, attempt_id = row["target_id"], row["attempt_id"]
        _require(isinstance(target_id, str) and target_id in planned, "selected target is not in the plan")
        _require(isinstance(attempt_id, str) and bool(_ATTEMPT.fullmatch(attempt_id)), "invalid explicit attempt id")
        _require(target_id not in seen_targets and attempt_id not in seen_attempts, "duplicate target or attempt selection")
        _require(planned[target_id]["axis"] == targets.AXIS, "fitness cannot be accepted as nested support")
        seen_targets.add(target_id)
        seen_attempts.add(attempt_id)
    schema = _schema(capture, _mapping(manifest.get("schema"), "plan schema"))
    policy = _instrument(capture, manifest)
    context_policy = manifest["instruments"][targets.AXIS].get("context_policy", targets.CONTEXT_POLICY)
    roster = capture.document(manifest["roster"], "roster")
    from data_sheets_schema.support_plan import _roster_records
    groups, pins = _roster_records(canonical(roster))
    chosen_records = {planned[t]["record_id"] for t in seen_targets}
    derived, verified_issues = {}, []
    for rid in sorted(chosen_records):
        record = records[rid]
        kind = record.get("artifact_kind")
        _require(kind == manifest.get("artifact_kind") and kind in ("full", "core", "collection"), "artifact kind conflicts")
        root_class = manifest["schema"]["class"]
        _require(not (kind == "core" and root_class == "Dataset" or kind != "core" and root_class == "CoreDataset"
                      or kind == "collection" and root_class == "Dataset"), "artifact kind and root class conflict")
        record_pin = record["record"]
        source_path = record_pin.get("path")
        _require(source_path in groups, "record is not in captured roster")
        identity, jobs = groups[source_path]
        fields = ("project", "label", "method", "cohort", "generation_rep")
        _require(tuple(record.get(k) for k in fields) == identity, "record identity disagrees with roster")
        expected_id = sha256(canonical({"input": source_path, "identity": identity,
            "artifact_kind": kind, "plan_format": manifest["format"]}))[:24]
        _require(rid == expected_id, "record id differs from its captured identity")
        record_raw = capture.get(record_pin)
        _require(pins.get(source_path) == sha256(record_raw), "record bytes disagree with roster pin")
        _require(record_pin.get("recorded_hashes") == {"sha256": pins[source_path]}, "record original hashes conflict")
        provenance_pin = record["provenance"]
        provenance_path = jobs[0].get("provenance") or (
            f"data/d4d_concatenated/{record['method']}_core/{record['label']}/{record['project']}_provenance.yaml")
        _require(provenance_pin.get("path") == provenance_path, "provenance path differs from roster identity")
        provenance_raw = capture.get(provenance_pin)
        if provenance_path in pins:
            _require(pins[provenance_path] == sha256(provenance_raw)
                     and provenance_pin.get("recorded_hashes") == {"sha256": pins[provenance_path]},
                     "provenance bytes disagree with roster pin")
        provenance = _mapping(_read(provenance_raw, "provenance", yaml_allowed=True), "provenance")
        run = provenance.get("run", {})
        _require(all(run.get(k) == record[k] for k in ("project", "label", "method")), "provenance identity conflicts")
        _require("replicate" not in run or run["replicate"] == record["generation_rep"], "provenance replicate conflicts")
        declared_record = provenance.get("outputs", {}).get(kind, {}).get("path")
        _require(declared_record is None or declared_record == source_path, "provenance names another record artifact")
        bundle_raw = capture.get(record["bundle"])
        inputs = provenance.get("inputs", {})
        _require((inputs.get("bundle_path") or inputs.get("bundle")) == record["bundle"].get("path"), "bundle path conflicts")
        declared = {k: inputs[f"bundle_{k}"] for k in ("md5", "sha256") if inputs.get(f"bundle_{k}")}
        _require(bool(declared) and all(hashlib.new(k, bundle_raw).hexdigest() == v for k, v in declared.items()), "bundle bytes conflict with provenance")
        _require(record["bundle"].get("recorded_hashes") == declared, "bundle original hashes conflict")
        bundle = bundle_raw.decode("utf-8")
        from data_sheets_schema.evaluation_model import same_family_label
        generator = provenance.get("model", {}).get("model")
        _require(record.get("generator") == generator and record.get("same_family") ==
                 same_family_label(manifest["model"]["name"], generator), "generator/family metadata conflicts")
        inventory = targets.inventory_targets(record_raw, schema, artifact_kind=kind,
                                              relationship_policy=policy, context_policy=context_policy)
        expected_inventory = inventory.to_dict()
        expected_inventory["readiness_blockers"].remove("nested_planner_integration_3342")
        _require(canonical(capture.document(record["inventory"], "target inventory")) == canonical(expected_inventory), "inventory differs from captured record/schema")
        in_record = {t["id"]: t for t in planned.values() if t["record_id"] == rid and t["axis"] == targets.AXIS}
        _require(set(in_record) == {f"{rid}:{targets.AXIS}:{t.kind}:{t.pointer}" for t in inventory.targets}, "record target membership differs from its inventory")
        _require(canonical(record.get("support_targets_by_kind")) == canonical(expected_inventory["eligible_by_kind"]), "record target counts conflict")
        expected_blocked = [{"record_id": rid, "axis": targets.AXIS, **b} for b in expected_inventory["blocked"]]
        _require([b for b in manifest["blocked_paths"] if b["record_id"] == rid and b.get("axis") == targets.AXIS] == expected_blocked, "nested blocked paths differ from reconstructed inventory")
        if policy == targets.SCALAR_POLICY:
            issues = [{"record_id": rid, **issue} for issue in expected_inventory["representation_issues"]]
            _require(record["representation_issues"] == issues,
                     "representation issues differ from reconstructed inventory")
            verified_issues.extend(issues)
        for target in inventory.targets:
            tid = f"{rid}:{targets.AXIS}:{target.kind}:{target.pointer}"
            row = in_record[tid]
            payload = target.to_dict()
            _require(all(row.get(k) == payload[k] for k in ("pointer", "kind", "value_sha256", "context_sha256", "specification_ref")), "target value/context/specification conflicts")
            _require(row.get("inventory_artifact") == record["inventory"], "target names another inventory")
            root_slot = targets.pointer_tokens(target.pointer)[0]
            fitness_id = f"{rid}:fitness:/{targets._token(root_slot)}"
            expected_fitness = {**payload["fitness"], "target_id": fitness_id if fitness_id in planned else None,
                                "status": "planned_top_level_only" if fitness_id in planned else "blocked"}
            _require(row.get("fitness_mapping") == expected_fitness, "target fitness mapping conflicts")
            if tid not in seen_targets:
                continue
            _require(capture.get(row["target_artifact"]) == target.payload_json.encode(), "target artifact differs from reconstructed target")
            cap = _integer(row.get("output_token_ceiling"), "output bound", positive=True)
            request = targets.render_request(target, bundle=bundle, model=manifest["model"]["name"], max_tokens=cap)
            request_raw = canonical(request)
            _require(_expand(row["request_recipe"], capture) == request, "request recipe differs from reconstructed request")
            _require(sha256(request_raw) == row.get("request_sha256") and len(request_raw) == row.get("request_bytes"), "request pin conflicts")
            derived[tid] = {"record_id": rid, "target_id": tid, "axis": targets.AXIS,
                "kind": target.kind, "pointer": target.pointer, "artifact_kind": kind,
                "record": _pin(record_raw), "bundle": _pin(bundle_raw),
                "inventory": record["inventory"], "target": row["target_artifact"],
                "specification_sha256": schema.digest, "value_sha256": payload["value_sha256"],
                "context_sha256": payload["context_sha256"], "model": manifest["model"],
                "request": capture.add(request_raw), "max_tokens": cap}
            if policy == targets.SCALAR_POLICY:
                derived[tid].update(policy=policy, representation=payload.get("representation"))
            if context_policy != targets.CONTEXT_POLICY:
                derived[tid]["context_policy"] = context_policy
    bindings = [{**s, "binding": derived[s["target_id"]]} for s in selections]
    accounting = None
    if policy == targets.SCALAR_POLICY:
        by_location = {(issue["record_id"], issue["pointer"]): issue for issue in verified_issues}
        selected_issues = []
        for selection in selections:
            binding = derived[selection["target_id"]]
            issue = by_location.get((binding["record_id"], binding["pointer"]))
            if issue is not None:
                selected_issues.append({**issue, **selection})
        accounting = {"policy": policy, "verified_record_ids": sorted(chosen_records),
            "verified_record_issues": verified_issues, "verified_record_issue_count": len(verified_issues),
            "selected_target_issues": selected_issues, "selected_target_issue_count": len(selected_issues),
            "full_plan_declared_issue_count": manifest["counts"]["representation_issue_count"],
            "unselected_record_evidence": "not_reconstructed"}
    return bindings, accounting


def _descriptor(capture, manifest_raw, selections):
    manifest, records, planned = _manifest(capture, manifest_raw)
    bindings, accounting = _bindings(capture, manifest, records, planned, selections)
    result = {"format": FORMAT, "kind": "acceptance_descriptor", "contract": CONTRACT,
            "plan": capture.add(manifest_raw), "selections": bindings,
            "readiness": manifest["readiness"], "limitations": LIMITATIONS}
    if accounting is not None:
        result["representation_accounting"] = accounting
    context_policy = manifest["instruments"][targets.AXIS].get("context_policy", targets.CONTEXT_POLICY)
    if context_policy != targets.CONTEXT_POLICY:
        result["context_policy"] = context_policy
    return result


def _load_descriptor(capture, raw):
    value = _mapping(_read(raw, "acceptance descriptor", limit=MAX_MANIFEST_BYTES), "acceptance descriptor")
    for selection in value.get("selections", []):
        capture.get(selection["binding"]["request"])
    selections = [{"target_id": s["target_id"], "attempt_id": s["attempt_id"]} for s in value.get("selections", [])]
    expected = _descriptor(capture, capture.get(value["plan"], limit=MAX_MANIFEST_BYTES), selections)
    _require(canonical(value) == canonical(expected), "descriptor differs from reconstructed plan/target bindings")
    return value


def _write_new(output, capture, filename, document, *, protected=()):
    output = Path(output)
    _require(not output.exists() and not output.is_symlink(), "output already exists")
    resolved = output.resolve()
    for path in (capture.root, *(Path(p).resolve() for p in protected)):
        _require(not resolved.is_relative_to(path), "output cannot be inside input evidence")
    _require(output.parent.is_dir(), "output parent must exist")
    output.mkdir()  # Exclusive directory creation; never replace an existing destination.
    artifacts = output / "artifacts"
    artifacts.mkdir()
    for digest, raw in capture.blobs.items():
        with (artifacts / digest).open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    with (output / filename).open("xb") as stream:
        stream.write(canonical(document) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def prepare(plan: Path, output: Path, *, selections: list[dict], protocol: str) -> dict:
    _require(protocol == FORMAT, "explicit nested_support_result_v1 selection is required")
    capture = Capture(plan)
    descriptor = _descriptor(capture, capture.entry("manifest.json"), selections)
    _write_new(output, capture, "descriptor.json", descriptor)
    return descriptor


def package_response(descriptor_raw: bytes, *, attempt_id: str, native_message: bytes) -> bytes:
    """Package explicitly caller-labelled native bytes; no provider proof.

    An external capture harness can write these bytes exclusively. Acceptance
    later verifies the entire descriptor and bindings, rather than trusting
    this convenience function or any normalized response fields.
    """
    _require(type(native_message) is bytes and len(native_message) <= MAX_RESPONSE_BYTES,
             "native response exceeds byte bound")
    value = _mapping(_read(descriptor_raw, "descriptor", limit=MAX_MANIFEST_BYTES), "descriptor")
    _require(value.get("format") == FORMAT and value.get("kind") == "acceptance_descriptor",
             "response packaging requires an explicit acceptance descriptor")
    selected = [s for s in value["selections"] if s["attempt_id"] == attempt_id]
    _require(len(selected) == 1, "attempt is not uniquely selected")
    return canonical({"format": RESPONSE_FORMAT, "descriptor_sha256": sha256(descriptor_raw),
        "target_id": selected[0]["target_id"], "attempt_id": attempt_id,
        "request_sha256": selected[0]["binding"]["request"]["sha256"],
        "message_base64": base64.b64encode(native_message).decode("ascii")}) + b"\n"


def _unpack_response(raw, descriptor_raw, selected):
    try:
        envelope = _mapping(_read(raw, "response envelope", limit=MAX_ENVELOPE_BYTES), "response envelope")
    except ResultError:
        return None, ["response_envelope_not_bounded_strict_json_object"]
    if envelope.get("type") == "message":
        return raw, ["direct_native_message_requires_explicit_binding_envelope"]
    expected = {"format": RESPONSE_FORMAT, "descriptor_sha256": sha256(descriptor_raw),
                "target_id": selected["target_id"], "attempt_id": selected["attempt_id"],
                "request_sha256": selected["binding"]["request"]["sha256"]}
    problems = [f"response_envelope_{k}_conflicts" for k, v in expected.items() if envelope.get(k) != v]
    if set(envelope) != {*expected, "message_base64"}:
        problems.append("response_envelope_keys_differ_from_contract")
    try:
        encoded = envelope.get("message_base64")
        if not isinstance(encoded, str):
            raise ValueError("base64 text required")
        message = base64.b64decode(encoded, validate=True)
        if len(message) > MAX_RESPONSE_BYTES or base64.b64encode(message).decode("ascii") != encoded:
            raise ValueError("noncanonical or oversized native bytes")
    except (ValueError, binascii.Error):
        return None, [*problems, "native_message_base64_invalid_or_oversized"]
    return message, problems


def _assess(raw, binding):
    problems = []
    result = {"status": "rejected", "problems": problems, "verdict": None, "reason": None,
              "model": None, "stop_reason": None, "usage": None, "text": None, "reasoning": []}
    try:
        message = _mapping(_read(raw, "native response", limit=MAX_RESPONSE_BYTES), "native response")
    except ResultError:
        problems.append("response_not_bounded_strict_json_object")
        return result
    result.update(model=message.get("model"), stop_reason=message.get("stop_reason"), usage=message.get("usage"))
    if message.get("type") != "message" or message.get("role") != "assistant":
        problems.append("response_not_assistant_message")
    if message.get("model") != binding["model"]["name"]:
        problems.append("response_model_differs_from_request")
    if message.get("stop_reason") != "end_turn":
        problems.append("response_not_unambiguously_complete")
    usage = message.get("usage")
    if not isinstance(usage, dict):
        problems.append("usage_missing_or_malformed")
    else:
        for key in ("input_tokens", "output_tokens"):
            if type(usage.get(key)) is not int or usage[key] < 0:
                problems.append(f"{key}_not_reported_nonnegative_integer")
        for key in ("cache_read_input_tokens", "cache_creation_input_tokens"):
            if key in usage and usage[key] is not None and (type(usage[key]) is not int or usage[key] < 0):
                problems.append(f"{key}_malformed")
        if "output_tokens_details" in usage and usage["output_tokens_details"] is not None:
            details = usage["output_tokens_details"]
            if not isinstance(details, dict):
                problems.append("output_tokens_details_malformed")
            elif "thinking_tokens" in details and details["thinking_tokens"] is not None and (
                    type(details["thinking_tokens"]) is not int or details["thinking_tokens"] < 0):
                problems.append("thinking_tokens_malformed")
        if type(usage.get("output_tokens")) is int and usage["output_tokens"] > binding["max_tokens"]:
            problems.append("reported_output_exceeds_requested_bound")
    content = message.get("content")
    texts = []
    if not isinstance(content, list):
        problems.append("content_not_a_block_list")
    else:
        for block in content:
            if not isinstance(block, dict):
                problems.append("content_block_not_mapping")
            elif block.get("type") == "text" and isinstance(block.get("text"), str):
                texts.append(block["text"])
            elif block.get("type") == "thinking" and isinstance(block.get("thinking"), str):
                result["reasoning"].append(block)
            elif block.get("type") == "redacted_thinking" and isinstance(block.get("data"), str):
                result["reasoning"].append(block)
            else:
                problems.append("unsupported_or_malformed_content_block")
    if len(texts) != 1:
        problems.append("exactly_one_text_block_required")
    else:
        result["text"] = texts[0]
        try:
            verdict = _mapping(_read(texts[0].encode(), "verdict", limit=MAX_RESPONSE_BYTES), "verdict")
            _require(set(verdict) == {"verdict", "reason"} and verdict["verdict"] in VERDICTS
                     and isinstance(verdict["reason"], str) and bool(verdict["reason"].strip()), "invalid verdict")
        except (ValueError, TypeError):
            problems.append("verdict_not_strict_closed_json_contract")
        else:
            if not problems:
                result.update(status="accepted", verdict=verdict["verdict"], reason=verdict["reason"])
    return result


def _attempt(capture, descriptor_raw, envelope_raw, attempt_id):
    descriptor = _load_descriptor(capture, descriptor_raw)
    matches = [s for s in descriptor["selections"] if s["attempt_id"] == attempt_id]
    _require(len(matches) == 1, "attempt is not uniquely selected in the descriptor")
    selected = matches[0]
    response_raw, problems = _unpack_response(envelope_raw, descriptor_raw, selected)
    assessment = _assess(response_raw if response_raw is not None else b"", selected["binding"])
    if problems:
        assessment.update(status="rejected", verdict=None, reason=None,
                          problems=[*problems, *assessment["problems"]])
    return {"format": FORMAT, "kind": "saved_attempt", "contract": CONTRACT,
        "descriptor": capture.add(descriptor_raw), "response_envelope": capture.add(envelope_raw),
        "response": capture.add(response_raw) if response_raw is not None else None,
        "attempt_id": attempt_id, "target_id": selected["target_id"], "binding": selected["binding"],
        "assessment": assessment, "limitations": LIMITATIONS}


def accept(descriptor: Path, response: Path, output: Path, *, attempt_id: str) -> dict:
    capture = Capture(descriptor)
    descriptor_raw = capture.entry("descriptor.json")
    raw = _file(Path(response), MAX_ENVELOPE_BYTES)
    value = _attempt(capture, descriptor_raw, raw, attempt_id)
    _write_new(output, capture, "result.json", value, protected=(response,))
    return value


def recheck(result: Path) -> dict:
    capture = Capture(result)
    recorded = _mapping(_read(capture.entry("result.json"), "saved result"), "saved result")
    if recorded.get("response") is not None:
        capture.get(recorded["response"], limit=MAX_RESPONSE_BYTES)
    expected = _attempt(capture, capture.get(recorded["descriptor"], limit=MAX_MANIFEST_BYTES),
                        capture.get(recorded["response_envelope"], limit=MAX_ENVELOPE_BYTES), recorded["attempt_id"])
    _require(canonical(recorded) == canonical(expected), "saved result differs from independently reconstructed evidence")
    return expected


def report(descriptor: Path, results: list[Path]) -> dict:
    capture = Capture(descriptor)
    raw = capture.entry("descriptor.json")
    selected = _load_descriptor(capture, raw)
    manifest = _read(capture.get(selected["plan"], limit=MAX_MANIFEST_BYTES), "plan", limit=MAX_MANIFEST_BYTES)
    by_attempt = {}
    for path in results:
        result = recheck(path)
        _require(result["descriptor"] == _pin(raw), "result belongs to another descriptor")
        aid = result["attempt_id"]
        _require(aid not in by_attempt, "duplicate attempt results cannot be selected implicitly")
        by_attempt[aid] = result
    counts = {kind: {"selected": 0, "missing": 0, "rejected": 0, "accepted": 0,
                     "verdicts": {v: 0 for v in VERDICTS}} for kind in targets.KINDS}
    rows = []
    for selection in selected["selections"]:
        result = by_attempt.get(selection["attempt_id"])
        state = result["assessment"]["status"] if result else "missing"
        item = counts[selection["binding"]["kind"]]
        item["selected"] += 1
        item[state] += 1
        if state == "accepted":
            item["verdicts"][result["assessment"]["verdict"]] += 1
        rows.append({"target_id": selection["target_id"], "attempt_id": selection["attempt_id"],
                     "state": state, "response": result["response"] if result else None})
    all_selected = all(row["state"] == "accepted" for row in rows)
    all_planned = {s["target_id"] for s in selected["selections"]} == {
        t["id"] for t in manifest["targets"] if t["axis"] == targets.AXIS}
    report = {"format": FORMAT, "kind": "response_accounting_report", "descriptor": _pin(raw),
        "plan": selected["plan"], "full_plan_declared_counts": manifest["counts"],
        "full_plan_count_basis": "pinned manifest lists; unselected record artifacts are not reconstructed",
        "selected_counts": counts, "rows": rows, "fitness": "separate_and_unscored",
        "all_selected_responses_accepted": all_selected,
        "all_planned_nested_targets_selected": all_planned,
        "all_planned_nested_responses_accepted": all_selected and all_planned,
        "scientific_accuracy": "unverified", "full_record_schema_validation": "not_performed",
        "readiness": selected["readiness"], "limitations": LIMITATIONS}
    if "representation_accounting" in selected:
        report["representation_accounting"] = selected["representation_accounting"]
    if "context_policy" in selected:
        report["context_policy"] = selected["context_policy"]
    return report
