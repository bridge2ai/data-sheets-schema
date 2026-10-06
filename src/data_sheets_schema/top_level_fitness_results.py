"""Versioned, captured-only fitness results; no provider or legacy-cache use.

The original plan/request is reconstructed. Mechanical acceptance never
establishes scientific scoring eligibility, calibration or paid-run readiness.
"""
from __future__ import annotations

import base64
import binascii
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import posixpath

from data_sheets_schema import evidence_score, schema_digest, support_judge
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema import support_targets as targets
from data_sheets_schema.support_plan import canonical, sha256, value_identity

FORMAT = "top_level_fitness_result_v1"
RESPONSE_FORMAT = "top_level_fitness_response_v1"
INDEX_FORMAT = "top_level_fitness_index_v1"
MAX_DOCUMENT_BYTES = saved.MAX_MANIFEST_BYTES
FAILURES = ("none", "form", "target", "substance")
CONTRACT = {
    "format": FORMAT, "adapter": saved.ADAPTER, "response_envelope": RESPONSE_FORMAT,
    "axis": "fitness", "kind": "fitness_top_level", "completion": "end_turn",
    "model_match": "exact", "attempt_selection": "one_explicit_attempt_per_target",
    "request_instrument": "captured_plan_legacy_top_level_fitness",
    "content": "one_text_block_and_optional_thinking_or_redacted_thinking",
    "output_keys": ["fitness", "failure", "reason"], "fitness_range": [0, 1],
    "failures": list(FAILURES), "reason_words": "1_to_24_whitespace_delimited",
    "required_usage": ["input_tokens", "output_tokens"],
    "limits": {**saved.CONTRACT["limits"], "document_bytes": MAX_DOCUMENT_BYTES},
}
LIMITATIONS = [
    "Caller-labelled response bytes do not authenticate provider execution.",
    "Mechanical fitness acceptance is not scientific scoring eligibility or calibration.",
    "Top-level fitness is not support and is not propagated to nested targets or other records.",
    "Legacy fitness caches and July entries are not consumed by this versioned contract.",
    "Original draft readiness and scientific/paid-run blockers remain unchanged.",
]
ResultError = saved.ResultError
_require = saved._require


def _schema(capture, schema):
    """Reproduce both original inventories with only captured logical imports."""
    from linkml_runtime.linkml_model.meta import SchemaDefinition
    from data_sheets_schema.schema_snapshot import SchemaSnapshot
    from data_sheets_schema.schema_view import captured_view, version_document

    sources = schema.get("sources")
    _require(isinstance(sources, list) and bool(sources), "schema requires a captured closure")
    rows, by_name, by_path = [], {}, {}
    for source in sources:
        saved._mapping(source, "schema source")
        name = saved._text(source.get("import_key"), "schema import key")
        spelling = saved._text(source.get("path"), "schema logical path")
        _require(spelling.startswith("/") and posixpath.normpath(spelling) == spelling
                 and not spelling.startswith("//"), "schema path must be canonical absolute lineage")
        path = Path(spelling)
        _require(name not in by_name and path not in by_path, "duplicate schema source identity")
        raw = capture.get(source)
        saved._mapping(saved._read(raw, "schema source", yaml_allowed=True), "schema source")
        by_name[name], by_path[path] = (path, raw), name
        rows.append((name, path, raw))
    root_class = saved._text(schema.get("class"), "schema root class")
    saved._text(schema.get("profile"), "schema profile")
    _require(schema.get("profile_basis") == "explicit", "schema profile must remain explicit")
    vocabulary = {}
    if schema.get("vocabulary") is None:
        _require(schema.get("vocabulary_basis") == "explicit_profile_without_vocabulary"
                 and schema.get("vocabulary_path") is None, "missing vocabulary basis conflicts")
    else:
        _require(schema.get("vocabulary_basis") in {"explicit_vocabulary_override", "explicit_profile_pin"},
                 "unknown captured vocabulary basis")
        saved._text(schema.get("vocabulary_path"), "vocabulary lineage path")
        vocabulary = capture.document(schema["vocabulary"], "vocabulary", yaml_allowed=True).get("vocabularies")
        _require(isinstance(vocabulary, dict) and all(
            isinstance(k, str) and bool(k) and isinstance(v, dict) and bool(v)
            and all(isinstance(a, str) and isinstance(b, str) for a, b in v.items())
            for k, v in vocabulary.items()), "invalid captured vocabulary")
    _require(schema.get("vocabulary_names") == sorted(vocabulary), "vocabulary names conflict")
    snapshot = SchemaSnapshot(tuple(rows), (str(rows[0][1]), sha256(canonical(sources))))
    with captured_view(snapshot) as view:
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
        _require(view.get_class(root_class) is not None, "captured schema has no selected class")
        generation = schema_digest._build_from_view(root_class, rows[0][1], view)
        inventory = schema_digest._build_from_view(root_class, rows[0][1], view, complete=True)
        specifications = {slot.name: evidence_score._render_slot_spec(slot.name, inventory, vocabulary)
                          for slot in inventory.slots}
        raw = json.dumps({"class": root_class, "slots": specifications}, sort_keys=True).encode()
        digest = schema_digest.fingerprint(schema_digest.render(generation, vocabulary=vocabulary))
    _require(capture.get(schema["fitness_specifications"]) == raw,
             "fitness specifications differ from the captured schema closure")
    _require(schema.get("generation_digest") == digest, "generation digest differs from captured schema")
    return specifications, digest


def _record(capture, manifest, record, rid, groups, pins):
    """The roster/provenance join, independent of eligible support targets."""
    from data_sheets_schema.evaluation_model import same_family_label
    kind = record.get("artifact_kind")
    cls = manifest["schema"]["class"]
    _require(kind == manifest.get("artifact_kind") and kind in {"full", "core", "collection"},
             "artifact kind conflicts")
    _require(not (kind == "core" and cls == "Dataset" or kind != "core" and cls == "CoreDataset"
                  or kind == "collection" and cls == "Dataset"), "artifact kind and class conflict")
    source = record["record"].get("path")
    _require(source in groups, "record is not in captured roster")
    identity, jobs = groups[source]
    saved._integer(record.get("generation_rep"), "record replicate", positive=True)
    _require(tuple(record.get(k) for k in ("project", "label", "method", "cohort", "generation_rep")) == identity,
             "record identity disagrees with roster")
    _require(not any("artifact_kind" in job and job["artifact_kind"] != kind for job in jobs),
             "roster artifact kind conflicts")
    expected_id = sha256(canonical({"input": source, "identity": identity,
                                   "artifact_kind": kind, "plan_format": manifest["format"]}))[:24]
    _require(rid == expected_id, "record id differs from captured identity")
    raw = capture.get(record["record"])
    _require(pins.get(source) == sha256(raw)
             and record["record"].get("recorded_hashes") == {"sha256": pins[source]},
             "record bytes disagree with roster pin")
    document = saved._mapping(saved._read(raw, "record", yaml_allowed=True), "record")
    provenance_pin = record["provenance"]
    provenance_path = jobs[0].get("provenance") or (
        f"data/d4d_concatenated/{record['method']}_core/{record['label']}/{record['project']}_provenance.yaml")
    _require(provenance_pin.get("path") == provenance_path, "provenance path differs from roster")
    provenance_raw = capture.get(provenance_pin)
    if provenance_path in pins:
        _require(pins[provenance_path] == sha256(provenance_raw)
                 and provenance_pin.get("recorded_hashes") == {"sha256": pins[provenance_path]},
                 "provenance bytes disagree with roster")
    else:
        _require(provenance_pin.get("recorded_hashes") == {}
                 and provenance_pin.get("basis") == "captured_current_unpinned_by_roster",
                 "unpinned provenance must retain its captured-snapshot basis")
    provenance = saved._mapping(saved._read(provenance_raw, "provenance", yaml_allowed=True), "provenance")
    run = saved._mapping(provenance.get("run"), "provenance run")
    _require(all(run.get(k) == record[k] for k in ("project", "label", "method")), "provenance identity conflicts")
    _require("replicate" not in run or (type(run["replicate"]) is int
             and run["replicate"] == record["generation_rep"]), "provenance replicate conflicts")
    declared = provenance.get("outputs", {}).get(kind, {}).get("path")
    _require(declared is None or declared == source, "provenance names another record")
    bundle = capture.get(record["bundle"])
    inputs = saved._mapping(provenance.get("inputs"), "provenance inputs")
    _require((inputs.get("bundle_path") or inputs.get("bundle")) == record["bundle"].get("path"),
             "bundle path conflicts")
    hashes = {k: inputs[f"bundle_{k}"] for k in ("md5", "sha256") if inputs.get(f"bundle_{k}")}
    _require(bool(hashes) and all(hashlib.new(k, bundle).hexdigest() == v for k, v in hashes.items())
             and record["bundle"].get("recorded_hashes") == hashes, "bundle hashes conflict")
    generator = provenance.get("model", {}).get("model")
    _require(record.get("generator") == generator and record.get("same_family") ==
             same_family_label(manifest["model"]["name"], generator), "generator/family metadata conflicts")
    return document, raw, provenance_raw, bundle


def _descriptor(capture, manifest_raw, selections):
    from data_sheets_schema.support_plan import _roster_records
    manifest, records, planned = saved._manifest(capture, manifest_raw)
    _require(isinstance(selections, list) and bool(selections), "select at least one target/attempt")
    seen, attempts = set(), set()
    for selection in selections:
        _require(isinstance(selection, dict) and set(selection) == {"target_id", "attempt_id"},
                 "invalid target/attempt selection")
        tid, aid = selection["target_id"], selection["attempt_id"]
        _require(isinstance(tid, str) and tid in planned and planned[tid]["axis"] == "fitness",
                 "only planned top-level fitness targets are eligible")
        _require(isinstance(aid, str) and bool(saved._ATTEMPT.fullmatch(aid)), "invalid attempt id")
        _require(tid not in seen and aid not in attempts, "duplicate target or attempt")
        seen.add(tid)
        attempts.add(aid)
    specifications, digest = _schema(capture, saved._mapping(manifest.get("schema"), "plan schema"))
    instrument = manifest.get("instruments", {}).get("fitness")
    _require(isinstance(instrument, dict) and instrument.get("name") == "LLMSlotFitnessScorer"
             and instrument.get("granularity") == "top_level_field"
             and capture.get(instrument["system"]) == evidence_score.FITNESS_SYSTEM.encode(), "fitness instrument differs")
    groups, pins = _roster_records(capture.get(manifest["roster"]))
    derived = {}
    for rid in sorted({planned[tid]["record_id"] for tid in seen}):
        record = records[rid]
        document, raw, provenance, bundle = _record(capture, manifest, record, rid, groups, pins)
        populated = sorted(k for k, v in document.items() if support_judge.populated(v))
        eligible = [k for k in populated if k in specifications]
        expected_ids = {f"{rid}:fitness:/{targets._token(k)}" for k in eligible}
        rows = {tid: row for tid, row in planned.items() if row["record_id"] == rid and row["axis"] == "fitness"}
        _require(set(rows) == expected_ids and record["fitness_top_level_targets"] == len(eligible),
                 "fitness target membership differs from captured record/schema")
        _require(record["populated_top_level_fields"] == len(populated), "populated field count differs")
        blocked = [{"record_id": rid, "axis": "fitness", "pointer": "/" + targets._token(k),
                    "code": "unknown_top_level_slot"} for k in sorted(set(populated) - specifications.keys())]
        _require([b for b in manifest["blocked_paths"] if b["record_id"] == rid and b["axis"] == "fitness"] == blocked,
                 "fitness blocked paths differ from reconstructed record")
        for tid, row in rows.items():
            tokens = targets.pointer_tokens(row["pointer"])
            _require(len(tokens) == 1 and tokens[0] in eligible, "fitness requires one top-level pointer")
            slot, value = tokens[0], document[tokens[0]]
            _require(row.get("result_contract") == "legacy_top_level_fitness"
                     and row.get("specification_artifact") == manifest["schema"]["fitness_specifications"],
                     "fitness plan instrument/specification differs")
            value_sha = sha256(value_identity(value))
            _require(row.get("value_sha256") == value_sha, "fitness value identity conflicts")
            context = evidence_score.JudgementContext(axis="fitness", model=manifest["model"]["name"],
                rubric=evidence_score.digest_of(evidence_score.FITNESS_SYSTEM), corpus="", schema=digest,
                specification=manifest["schema"]["fitness_specifications"]["sha256"]).as_entry()
            _require(row.get("judgement_context") == context, "fitness judgement context conflicts")
            if tid not in seen:
                continue
            cap = saved._integer(row.get("output_token_ceiling"), "output bound", positive=True)
            request = evidence_score.fitness_request_arguments(model=manifest["model"]["name"],
                max_tokens=cap, slot=slot, value=value, specification=specifications[slot])
            request_raw = canonical(request)
            _require(saved._expand(row["request_recipe"], capture) == request
                     and row.get("request_sha256") == sha256(request_raw)
                     and row.get("request_bytes") == len(request_raw), "fitness request differs from reconstruction")
            derived[tid] = {"record_id": rid, "target_id": tid, "axis": "fitness", "kind": "fitness_top_level",
                "pointer": row["pointer"], "artifact_kind": record["artifact_kind"], "record": saved._pin(raw),
                "provenance": saved._pin(provenance), "bundle": saved._pin(bundle),
                "schema_sources": manifest["schema"]["sources"],
                "specification": manifest["schema"]["fitness_specifications"], "value_sha256": value_sha,
                "context": context, "context_sha256": sha256(canonical(context)), "instrument": instrument,
                "model": manifest["model"], "request": capture.add(request_raw), "max_tokens": cap}
    return {"format": FORMAT, "kind": "acceptance_descriptor", "contract": json.loads(canonical(CONTRACT)),
            "plan": capture.add(manifest_raw),
            "selections": [{**s, "binding": derived[s["target_id"]]} for s in selections],
            "readiness": manifest["readiness"], "limitations": list(LIMITATIONS)}


def _load_descriptor(capture, raw):
    value = saved._mapping(saved._read(raw, "fitness descriptor", limit=saved.MAX_MANIFEST_BYTES), "descriptor")
    for selection in value.get("selections", []):
        capture.get(selection["binding"]["request"])
    selections = [{"target_id": s["target_id"], "attempt_id": s["attempt_id"]} for s in value.get("selections", [])]
    expected = _descriptor(capture, capture.get(value["plan"], limit=saved.MAX_MANIFEST_BYTES), selections)
    _require(canonical(value) == canonical(expected), "fitness descriptor differs from reconstructed bindings")
    return expected


def prepare(plan: Path, output: Path, *, selections: list[dict], protocol: str) -> dict:
    _require(protocol == FORMAT, "explicit top_level_fitness_result_v1 selection required")
    capture = saved.Capture(plan)
    value = _descriptor(capture, capture.entry("manifest.json"), selections)
    _write_document(output, capture, "descriptor.json", value)
    return value


def _write_document(output, capture, filename, document, *, protected=()):
    _require(len(canonical(document)) + 1 <= MAX_DOCUMENT_BYTES, "fitness document exceeds byte bound")
    saved._write_new(output, capture, filename, document, protected=protected)


def package_response(descriptor_raw: bytes, *, attempt_id: str, native_message: bytes) -> bytes:
    _require(type(native_message) is bytes and len(native_message) <= saved.MAX_RESPONSE_BYTES,
             "native response exceeds byte bound")
    descriptor = saved._mapping(saved._read(descriptor_raw, "descriptor"), "descriptor")
    _require(descriptor.get("format") == FORMAT and descriptor.get("kind") == "acceptance_descriptor",
             "explicit fitness descriptor required")
    matches = [s for s in descriptor["selections"] if s["attempt_id"] == attempt_id]
    _require(len(matches) == 1, "attempt is not uniquely selected")
    return canonical({"format": RESPONSE_FORMAT, "descriptor_sha256": sha256(descriptor_raw),
        "target_id": matches[0]["target_id"], "attempt_id": attempt_id,
        "request_sha256": matches[0]["binding"]["request"]["sha256"],
        "message_base64": base64.b64encode(native_message).decode("ascii")}) + b"\n"


def _unpack(raw, descriptor_raw, selection):
    try:
        envelope = saved._mapping(saved._read(raw, "fitness response envelope", limit=saved.MAX_ENVELOPE_BYTES), "envelope")
        expected = {"format": RESPONSE_FORMAT, "descriptor_sha256": sha256(descriptor_raw),
                    "target_id": selection["target_id"], "attempt_id": selection["attempt_id"],
                    "request_sha256": selection["binding"]["request"]["sha256"]}
        problems = [f"response_envelope_{k}_conflicts" for k, v in expected.items() if envelope.get(k) != v]
        if set(envelope) != {*expected, "message_base64"}:
            problems.append("response_envelope_keys_differ_from_contract")
        encoded = envelope.get("message_base64")
        _require(isinstance(encoded, str), "base64 text required")
        message = base64.b64decode(encoded, validate=True)
        _require(len(message) <= saved.MAX_RESPONSE_BYTES and base64.b64encode(message).decode("ascii") == encoded,
                 "noncanonical or oversized native bytes")
        return message, problems
    except (ValueError, TypeError, binascii.Error):
        return None, ["response_envelope_not_bounded_strict_contract"]


def _assess(raw, binding):
    problems = []
    result = {"status": "rejected", "problems": problems, "fitness": None, "failure": None, "reason": None,
              "model": None, "stop_reason": None, "usage": None, "text": None, "reasoning": []}
    try:
        message = saved._mapping(saved._read(raw, "native fitness response", limit=saved.MAX_RESPONSE_BYTES), "response")
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
        details = usage.get("output_tokens_details")
        if details is not None:
            if not isinstance(details, dict):
                problems.append("output_tokens_details_malformed")
            elif details.get("thinking_tokens") is not None and (type(details["thinking_tokens"]) is not int
                                                                  or details["thinking_tokens"] < 0):
                problems.append("thinking_tokens_malformed")
        if type(usage.get("output_tokens")) is int and usage["output_tokens"] > binding["max_tokens"]:
            problems.append("reported_output_exceeds_requested_bound")
    texts = []
    if not isinstance(message.get("content"), list):
        problems.append("content_not_a_block_list")
    else:
        for block in message["content"]:
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
            score = saved._mapping(saved._read(texts[0].encode(), "fitness", limit=saved.MAX_RESPONSE_BYTES), "fitness")
            _require(set(score) == {"fitness", "failure", "reason"}, "fitness keys differ")
            _require(type(score["fitness"]) in (int, float) and math.isfinite(score["fitness"])
                     and 0 <= score["fitness"] <= 1, "fitness must be a finite score in range")
            _require(isinstance(score["failure"], str) and score["failure"] in FAILURES, "unknown failure")
            _require(isinstance(score["reason"], str) and 0 < len(score["reason"].split()) < 25, "invalid reason")
        except (ValueError, TypeError, OverflowError):
            problems.append("fitness_not_strict_closed_json_contract")
        else:
            if not problems:
                result.update(status="accepted", fitness=score["fitness"], failure=score["failure"], reason=score["reason"])
    return result


def _attempt(capture, descriptor_raw, envelope_raw, attempt_id):
    descriptor = _load_descriptor(capture, descriptor_raw)
    matches = [s for s in descriptor["selections"] if s["attempt_id"] == attempt_id]
    _require(len(matches) == 1, "attempt is not uniquely selected")
    selected = matches[0]
    response, problems = _unpack(envelope_raw, descriptor_raw, selected)
    assessment = _assess(response if response is not None else b"", selected["binding"])
    if problems:
        assessment.update(status="rejected", fitness=None, failure=None, reason=None,
                          problems=[*problems, *assessment["problems"]])
    return {"format": FORMAT, "kind": "saved_attempt", "contract": json.loads(canonical(CONTRACT)),
            "descriptor": capture.add(descriptor_raw), "response_envelope": capture.add(envelope_raw),
            "response": capture.add(response) if response is not None else None,
            "attempt_id": attempt_id, "target_id": selected["target_id"], "binding": selected["binding"],
            "assessment": assessment, "scientific_scoring_eligible": False,
            "approval_basis": "caller_labelled_saved_bytes", "limitations": list(LIMITATIONS)}


def accept(descriptor: Path, response: Path, output: Path, *, attempt_id: str) -> dict:
    capture = saved.Capture(descriptor)
    value = _attempt(capture, capture.entry("descriptor.json"),
                     saved._file(response, saved.MAX_ENVELOPE_BYTES), attempt_id)
    _write_document(output, capture, "result.json", value, protected=(response,))
    return value


def _recheck_captured(capture, raw):
    recorded = saved._mapping(saved._read(raw, "saved fitness result"), "result")
    if recorded.get("response") is not None:
        capture.get(recorded["response"], limit=saved.MAX_RESPONSE_BYTES)
    expected = _attempt(capture, capture.get(recorded["descriptor"], limit=saved.MAX_MANIFEST_BYTES),
                        capture.get(recorded["response_envelope"], limit=saved.MAX_ENVELOPE_BYTES), recorded["attempt_id"])
    _require(canonical(recorded) == canonical(expected), "saved fitness result differs from reconstructed evidence")
    return expected


def recheck(result: Path) -> dict:
    capture = saved.Capture(result)
    return _recheck_captured(capture, capture.entry("result.json"))


def _support(capture, raw):
    recorded = saved._mapping(saved._read(raw, "saved support result"), "support result")
    if recorded.get("response") is not None:
        capture.get(recorded["response"], limit=saved.MAX_RESPONSE_BYTES)
    expected = saved._attempt(capture, capture.get(recorded["descriptor"], limit=saved.MAX_MANIFEST_BYTES),
                             capture.get(recorded["response_envelope"], limit=saved.MAX_ENVELOPE_BYTES), recorded["attempt_id"])
    _require(canonical(recorded) == canonical(expected), "support result differs from reconstructed evidence")
    return expected


def _execution(capture, descriptor_raw, descriptor, supplied):
    """One fixed captured ledger; never infer dispatch from response text."""
    from data_sheets_schema import nested_support_execution as executor

    _require(type(supplied) is dict and set(supplied) == {"ledger", "saved_report"},
             "execution index input requires the closed captured ledger")
    ledger = supplied["ledger"]
    _require(type(ledger) is dict and ledger.get("format") == "top_level_fitness_execution_v1",
             "fitness index requires the explicit top-level fitness execution protocol")
    report = executor.recheck_captured(capture, ledger)
    registration = saved._mapping(saved._read(capture.get(ledger["registration"],
        limit=executor.MAX_REGISTRATION_BYTES), "execution registration"), "registration")
    _require(registration["format"] == "top_level_fitness_execution_v1"
             and registration["descriptor"] == saved._pin(descriptor_raw),
             "execution belongs to another fitness descriptor")
    selections, requests = descriptor["selections"], registration["requests"]
    _require(len(requests) == len(selections), "execution selected request count differs")
    for selection, request in zip(selections, requests):
        _require(request["target_id"] == selection["target_id"]
                 and request["attempt_id"] == selection["attempt_id"]
                 and request["kind"] == "fitness_top_level"
                 and request["planned_request"] == selection["binding"]["request"]
                 and request["max_tokens"] == selection["binding"]["max_tokens"],
                 "execution selected request differs from fitness binding")
    _require(type(report["rows"]) is list and len(report["rows"]) <= len(selections),
             "execution rows exceed selected fitness attempts")
    rows = {}
    for selection, row in zip(selections, report["rows"]):
        _require(row["target_id"] == selection["target_id"] and row["attempt_id"] == selection["attempt_id"]
                 and row["kind"] == "fitness_top_level"
                 and row["status"] in {"accepted", "failed", "spent_unknown"},
                 "execution row is not a known selected fitness attempt")
        result = row.get("saved_result")
        if result is not None:
            result = _recheck_captured(capture, canonical(result))
            _require(result["descriptor"] == saved._pin(descriptor_raw)
                     and result["attempt_id"] == selection["attempt_id"]
                     and result["target_id"] == selection["target_id"], "execution fitness result differs")
        _require(row["status"] != "accepted" or result is not None and result["assessment"]["status"] == "accepted",
                 "accepted execution lacks a strict accepted fitness response")
        rows[selection["attempt_id"]] = (row, result)
    if supplied["saved_report"] is not None:
        _require(capture.get(supplied["saved_report"], limit=saved.MAX_MANIFEST_BYTES) == canonical(report),
                 "saved execution report differs from captured reconstruction")
    _require(report["scientific_eligibility"] is False, "execution does not establish scientific eligibility")
    return rows, {**supplied, "report": report}, registration["declaration"]


def _index(capture, descriptor_raw, result_pins, support_pins, execution=None):
    descriptor = _load_descriptor(capture, descriptor_raw)
    by_attempt, pins = {}, {}
    for pin in result_pins:
        result = _recheck_captured(capture, capture.get(pin))
        _require(result["descriptor"] == saved._pin(descriptor_raw), "fitness result belongs to another descriptor")
        aid = result["attempt_id"]
        _require(aid not in by_attempt, "duplicate fitness attempt")
        by_attempt[aid], pins[aid] = result, pin
    execution_rows, execution_value, declaration = {}, None, None
    if execution is not None:
        execution_rows, execution_value, declaration = _execution(capture, descriptor_raw, descriptor, execution)
        for aid, result in by_attempt.items():
            _require(aid in execution_rows and execution_rows[aid][1] is not None
                     and canonical(result) == canonical(execution_rows[aid][1]),
                     "supplied fitness result differs from its actual execution ledger")
    rows, records = [], {}
    counts = {"selected": 0, "missing": 0, "rejected": 0, "accepted": 0}
    for selection in descriptor["selections"]:
        binding = selection["binding"]
        result = by_attempt.get(selection["attempt_id"])
        state = result["assessment"]["status"] if result else "missing"
        dispatch, spent = "unknown", None
        if execution is not None:
            actual = execution_rows.get(selection["attempt_id"])
            dispatch = actual[0]["status"] if actual else "not_started"
            spent = dispatch != "not_started"
            result = actual[1] if actual else None
            # A valid score in a failed HTTP body remains raw evidence only.
            state = "accepted" if dispatch == "accepted" else "rejected" if dispatch == "failed" else "missing"
        counts["selected"] += 1
        counts[state] += 1
        records[binding["record_id"]] = binding["record"]
        rows.append({"target_id": selection["target_id"], "attempt_id": selection["attempt_id"],
                     "record_id": binding["record_id"], "record": binding["record"], "pointer": binding["pointer"],
                     "request": binding["request"], "state": state, "result": pins.get(selection["attempt_id"]),
                     "assessment": result["assessment"] if result else None,
                     "dispatch_state": dispatch, "spent": spent})
    support_rows, support_seen = [], set()
    for pin in support_pins:
        result = _support(capture, capture.get(pin))
        other = saved._load_descriptor(capture, capture.get(result["descriptor"]))
        binding = result["binding"]
        _require(other["plan"] == descriptor["plan"] and records.get(binding["record_id"]) == binding["record"],
                 "support/fitness join requires the same plan and exact record")
        identity = (result["descriptor"]["sha256"], result["attempt_id"])
        _require(identity not in support_seen, "duplicate support attempt")
        support_seen.add(identity)
        support_rows.append({"record_id": binding["record_id"], "target_id": result["target_id"],
            "attempt_id": result["attempt_id"], "kind": binding["kind"], "pointer": binding["pointer"],
            "state": result["assessment"]["status"], "assessment": result["assessment"], "result": pin,
            "fitness_target_links": [r["target_id"] for r in rows if r["record_id"] == binding["record_id"]
                                     and targets.pointer_tokens(r["pointer"])[0] == targets.pointer_tokens(binding["pointer"])[0]],
            "fitness_propagated": False})
    support_counts = {kind: dict(Counter(row["state"] for row in support_rows if row["kind"] == kind))
                      for kind in targets.KINDS}
    value = {"format": INDEX_FORMAT, "descriptor": capture.add(descriptor_raw), "plan": descriptor["plan"],
        "result_artifacts": result_pins, "support_result_artifacts": support_pins,
        "fitness_rows": rows, "support_rows": support_rows,
        "strata": {"fitness_top_level": counts, **support_counts},
        "support_count_basis": "supplied independently rechecked attempts only",
        "execution": None, "mode": "caller_saved", "approval_basis": "caller_labelled_saved_bytes",
        "scientific_scoring_eligible": False, "readiness": descriptor["readiness"], "limitations": list(LIMITATIONS)}
    if execution is not None:
        value.update(execution=execution_value, mode=declaration["purpose"],
            approval_basis="captured_execution_declarations_not_scientific_validation",
            decision_references=declaration["decisions"],
            fitness_state_basis="accepted_requires_both_transport_and_strict_response")
    return value


def _copy(into, source):
    for raw in source.blobs.values():
        into.add(raw)


def build_index(descriptor: Path, results: list[Path], output: Path, *, execution=None, support_results=()) -> dict:
    capture = saved.Capture(descriptor)
    descriptor_raw = capture.entry("descriptor.json")
    result_pins, support_pins = [], []
    for paths, selected, checker in ((results, result_pins, _recheck_captured),
                                     (support_results, support_pins, _support)):
        for path in paths:
            other = saved.Capture(path)
            raw = other.entry("result.json")
            checker(other, raw)
            _copy(capture, other)
            selected.append(capture.add(raw))
    execution_input = None
    if execution is not None:
        from data_sheets_schema import nested_support_execution as executor
        other, ledger = executor.capture_run(Path(execution))
        report_path = Path(execution) / "report.json"
        report_pin = other.add(saved._file(report_path, saved.MAX_MANIFEST_BYTES)) if report_path.exists() or report_path.is_symlink() else None
        _copy(capture, other)
        execution_input = {"ledger": ledger, "saved_report": report_pin}
    value = _index(capture, descriptor_raw, result_pins, support_pins, execution_input)
    protected = (*results, *support_results, *((execution,) if execution is not None else ()))
    _write_document(output, capture, "index.json", value, protected=protected)
    return value


def recheck_index(index: Path) -> dict:
    capture = saved.Capture(index)
    recorded = saved._mapping(saved._read(capture.entry("index.json"), "fitness index"), "index")
    execution = recorded.get("execution")
    execution_input = ({"ledger": execution["ledger"], "saved_report": execution["saved_report"]}
                       if execution is not None else None)
    expected = _index(capture, capture.get(recorded["descriptor"], limit=saved.MAX_MANIFEST_BYTES),
                      recorded["result_artifacts"], recorded["support_result_artifacts"], execution_input)
    _require(canonical(recorded) == canonical(expected), "fitness index differs from reconstructed evidence")
    return expected
