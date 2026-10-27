"""Explicit BC1 staged audit and independent captured-byte replay, D44/D45.

The complete host audit is authoritative. Model projections intentionally omit
untouched supporting/metadata review rows; they are a changed review procedure,
not a claim of scientific equivalence. No provider or filesystem writes occur.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib

from . import audit_batches as batches, audit_batch_format, audit_grammar
from . import audit_omissions as omissions, audit_protocol, evidence_assertions as evidence
from . import typed_audit as typed, bc1_codec as codec

PROTOCOL = "bc1_typed_audit_v1"
PACKET = "bc1_audit_packet_v1"
ASSEMBLY = "bc1_audit_assembly_v1"
STATE = "bc1_audit_state_v1"
MAX_WORKERS = 32
MAX_OPEN_CONCERNS = 32
MAX_STATE_BYTES = 160_000_000
LIMITATIONS = [
    "Mechanical identity, declaration coverage and literal evidence only; scientific support, novelty and exhaustive recall remain unverified.",
    "Later stages see complete new workers and all concerns/history, but not untouched earlier supporting/metadata review rows.",
    "Hashes and coverage counts are bookkeeping, never a model-review or scientific-support certificate.",
    "Required carry overflow terminates; no truncation, regrouping or extra paid attempt is authorized.",
]


def _json(value):
    return codec.canonical(value)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _seal(value):
    return {**value, "sha256": _sha(_json(value))}


def _exact(value, keys, name):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError("invalid BC1 " + name + " fields")


def _bound(value, limit=MAX_STATE_BYTES):
    if len(_json(value)) > limit:
        raise ValueError("BC1 saved state byte bound exceeded")
    return value


def contract_identity():
    return {"protocol": PROTOCOL, "packet": PACKET, "assembly": ASSEMBLY,
            "codec": codec.FORMAT, "stage_delta": "bc1_stage_delta_v1",
            "concern_packet": "ConcernPacketV1", "record_digest": "RecordDigestV1",
            "worker_visible_bytes": codec.WORKER_BYTES,
            "integration_visible_bytes": codec.INTEGRATION_BYTES,
            "concern_carry_bytes": codec.CARRY_BYTES,
            "max_decoded_audit_bytes": codec.MAX_DECODED_BYTES,
            "max_decoded_concern_bytes": codec.MAX_DECODED_BYTES,
            "max_open_concerns": MAX_OPEN_CONCERNS, "max_workers": MAX_WORKERS,
            "open_concern_counting": "active findings plus unresolved omission candidates; no controller merging or resolution",
            "fan_in_widths": [1, 2], "final_cross_group_calls": 1,
            "grammar_version": 2, "evidence_protocol_version": 7,
            "instruction_sha256": {"codec": _sha(_json(codec.contract())),
                "worker": _sha(_json(audit_batch_format.contract("worker", version=2))),
                "group": _sha(_json(_stage_contract(False))),
                "final": _sha(_json(_stage_contract(True))),
                "downstream": _sha(_json(downstream_contract()))},
            "downstream_projection": "self_contained_codec_with_empty_dictionary_within_262144_bytes",
            "omission_contract_sha256": dict(omissions.ASSET_SHA256)}


def _selection(selection, fan_in):
    from .bc1_context import contract_identity as context_contract
    if type(selection) is not dict or type(selection.get("bounded_carry")) is not dict:
        raise ValueError("BC1 requires an explicit captured registration selection")
    chosen = selection["bounded_carry"]
    if set(chosen) != {"version", "fan_in", "contract"}:
        raise ValueError("BC1 selection requires exact version, fan_in and contract")
    if type(chosen.get("version")) is not int or chosen["version"] != 1:
        raise ValueError("BC1 version must be explicitly selected")
    if type(fan_in) is not int or fan_in not in (1, 2) or chosen.get("fan_in") != fan_in:
        raise ValueError("BC1 fan-in width must match captured selection")
    contract = chosen["contract"]
    if (type(contract) is not dict or contract.get("protocol") != PROTOCOL
            or type(contract.get("version")) is not int or contract["version"] != 1
            or contract.get("audit") != contract_identity()
            or contract.get("context") != context_contract()):
        raise ValueError("BC1 selected audit/context contract mismatch")


def _derive(inputs, schema_rows, selection, project, limits):
    from .bc1_context import derive_term_policy
    required = {"original_full", "bundle", "manifest", "receipt", "context"}
    if type(inputs) is not dict or not required <= set(inputs) <= required | {"original_core", "source_manifest"}:
        raise ValueError("BC1 input roster mismatch")
    raw = {key: typed._unblob(value) for key, value in inputs.items()}
    snapshot = typed._snapshot(schema_rows)
    _exact(limits, {"max_paths", "max_inventory_bytes", "max_workers", "max_output_tokens", "max_request_bytes", "fan_in"}, "limits")
    if any(type(n) is not int or n < 1 for n in limits.values()) or limits["max_workers"] > MAX_WORKERS:
        raise ValueError("invalid BC1 integer limits")
    if limits["max_output_tokens"] > 64_000:
        raise ValueError("BC1 output-token reserve exceeds contract")
    _selection(selection, limits["fan_in"])
    for key in ("original_full", "original_core"):
        if key in raw:
            omissions._mapping(raw[key], key)
    if ("source_manifest" in raw) != (project is not None):
        raise ValueError("source manifest and explicit project must be captured together")
    authority = typed._source_authority(raw["source_manifest"], project) if project is not None else None
    policy = derive_term_policy(selection=selection, context_raw=raw["context"], schema_snapshot=snapshot)
    prepared = omissions.prepare(record=raw["original_full"], bundle=raw["bundle"], manifest=raw["manifest"],
        receipt=raw["receipt"], context=raw["context"], schema_path=snapshot.sources[0][1], schema_snapshot=snapshot,
        max_output_tokens=limits["max_output_tokens"], max_request_bytes=limits["max_request_bytes"], term_policy=policy)
    omission_request = prepared.request()
    catalog = omission_request["payload"]["schema"]
    chunks, _ = evidence.source_chunks_from_bytes(raw["bundle"], raw["manifest"])
    slots = {name for row in catalog["classes"].values() for name in row["slots"]}
    dictionary = codec.build_dictionary(chunks=chunks, slots=slots, classes=catalog["classes"])
    plan = batches.make_plan(raw["original_full"].decode("utf-8"), version=2,
        **{k: limits[k] for k in ("max_paths", "max_inventory_bytes", "max_workers")})
    ids = [worker["id"] for worker in plan["workers"]]
    groups = [{"id": f"group-{i // limits['fan_in'] + 1:04d}", "workers": ids[i:i + limits["fan_in"]]}
              for i in range(0, len(ids), limits["fan_in"])]
    return {"plan": plan, "groups": groups, "term_policy": policy, "dictionary": dictionary,
            "omission_request": omission_request, "registered_provenance": authority,
            "contract": contract_identity(), "limitations": list(LIMITATIONS)}, raw, prepared


def prepare(*, selection, original_full, bundle, manifest, receipt, context,
            schema_path=None, schema_snapshot=None, original_core=None,
            source_manifest=None, project=None, max_paths=96, max_inventory_bytes=16384,
            max_workers=32, max_output_tokens=64000, max_request_bytes=32_000_000, fan_in=2):
    """Capture a separate BC1 packet; legacy typed packet semantics are untouched."""
    if schema_snapshot is None:
        if schema_path is None:
            raise ValueError("explicit captured schema required")
        schema_snapshot = typed._capture(schema_path)
    inputs = {key: typed._blob(raw) for key, raw in dict(original_full=original_full,
        original_core=original_core, bundle=bundle, manifest=manifest, receipt=receipt,
        context=context, source_manifest=source_manifest).items() if raw is not None}
    schema_rows = typed._snapshot_rows(schema_snapshot)
    limits = dict(max_paths=max_paths, max_inventory_bytes=max_inventory_bytes, max_workers=max_workers,
                  max_output_tokens=max_output_tokens, max_request_bytes=max_request_bytes, fan_in=fan_in)
    derived, _, _ = _derive(inputs, schema_rows, selection, project, limits)
    packet = _seal({"kind": PACKET, "protocol": PROTOCOL, "selection": deepcopy(selection),
        "inputs": inputs, "schema_sources": schema_rows, "project": project, "limits": limits, **derived})
    _bound(packet, typed.MAX_PACKET_BYTES)
    return packet


def _open(packet):
    _exact(packet, {"kind", "protocol", "selection", "inputs", "schema_sources", "project", "limits",
        "plan", "groups", "term_policy", "dictionary", "omission_request", "registered_provenance",
        "contract", "limitations", "sha256"}, "packet")
    _bound(packet, typed.MAX_PACKET_BYTES)
    if packet["kind"] != PACKET or packet["protocol"] != PROTOCOL:
        raise ValueError("BC1 packet protocol mismatch")
    derived, raw, prepared = _derive(packet["inputs"], packet["schema_sources"], packet["selection"], packet["project"], packet["limits"])
    expected = _seal({**{key: packet[key] for key in ("kind", "protocol", "selection", "inputs", "schema_sources", "project", "limits")}, **derived})
    if _json(expected) != _json(packet):
        raise ValueError("BC1 packet differs from captured-byte derivation")
    return raw, prepared


def roster(packet):
    _open(packet)
    return ([{"phase": "bc1_worker", "worker_id": w["id"]} for w in packet["plan"]["workers"]]
        + [{"phase": "bc1_omission"}]
        + [{"phase": "bc1_integration", "stage_id": g["id"], "worker_ids": list(g["workers"])} for g in packet["groups"]]
        + [{"phase": "bc1_final", "stage_id": "final", "worker_ids": []}])


def _shared(packet, raw, prepared):
    payload = prepared.request()["payload"]
    return {"original_full": raw["original_full"].decode("utf-8"),
        "original_core": raw.get("original_core", b"").decode("utf-8") or None,
        "bundle": raw["bundle"].decode("utf-8"), "manifest": raw["manifest"].decode("utf-8"),
        "receipt": raw["receipt"].decode("utf-8"), "context": payload["context"],
        "schema": payload["schema"], "term_policy": packet["term_policy"],
        "registered_provenance": packet["registered_provenance"]}


def _request(packet, kind, payload):
    result = {"kind": kind, "payload": payload, "request_sha256": _sha(_json(payload))}
    if len(_json(result)) > packet["limits"]["max_request_bytes"]:
        raise ValueError("complete BC1 request exceeds max_request_bytes")
    return result


def worker_request(packet, worker_id):
    raw, prepared = _open(packet)
    return _worker_request(packet, worker_id, raw, prepared)


def _worker_request(packet, worker_id, raw, prepared):
    """Format using this operation's already verified captured authorities."""
    worker = next((w for w in packet["plan"]["workers"] if w["id"] == worker_id), None)
    if worker is None:
        raise ValueError("unknown BC1 worker")
    return _request(packet, "bc1_worker_request_v1", {"packet_sha256": packet["sha256"], "stage": "worker",
        "worker_id": worker_id, "assignment": worker, "inventory": packet["plan"]["inventory"],
        "shared_context": _shared(packet, raw, prepared), "dictionary": packet["dictionary"],
        "codec_contract": codec.contract(), "output_contract": audit_batch_format.contract("worker", version=2),
        "visible_output_bytes": codec.WORKER_BYTES})


def omission_request(packet):
    _open(packet)
    return deepcopy(packet["omission_request"])


def capture_response(request, response):
    _exact(request, {"kind", "payload", "request_sha256"}, "request")
    payload = request["payload"]
    if request["kind"] not in ("bc1_worker_request_v1", "bc1_stage_request_v1") or _sha(_json(payload)) != request["request_sha256"]:
        raise ValueError("BC1 request identity mismatch")
    limit = codec.WORKER_BYTES if request["kind"] == "bc1_worker_request_v1" else codec.INTEGRATION_BYTES
    # Save even invalid complete delivery; checks, not capture, interpret it.
    blob = typed._blob(response, limit)
    return _json({"kind": "bc1_saved_response_v1", "packet_sha256": payload["packet_sha256"],
        "request_sha256": request["request_sha256"], "response": blob})


def _unwrap(request, saved):
    value = codec.load(saved, byte_limit=typed.MAX_SAVED_RESPONSE_BYTES)
    _exact(value, {"kind", "packet_sha256", "request_sha256", "response"}, "saved response")
    raw = typed._unblob(value["response"], codec.INTEGRATION_BYTES)
    if _json(value) != capture_response(request, raw):
        raise ValueError("BC1 saved response does not bind this request")
    limit = codec.WORKER_BYTES if request["kind"] == "bc1_worker_request_v1" else codec.INTEGRATION_BYTES
    decoded = codec.decode_candidate(raw, dictionary=request["payload"]["dictionary"], max_bytes=limit)
    return raw, decoded


def check_worker(packet, worker_id, response):
    request = worker_request(packet, worker_id)
    raw, value = _unwrap(request, response)
    report = batches.check_worker(_json(value), packet["plan"], worker_id, version=2)
    if report["passed"]:
        typed._omission_findings(value["findings"])
    return {"passed": report["passed"], "grammar": report, "worker_id": worker_id,
        "response_sha256": _sha(response), "inner_response_sha256": _sha(raw),
        "decoded_sha256": _sha(_json(value)), "acceptance_scope": "worker structure only; scientific support unverified"}


def _base(packet, workers, omission_raw, *, opened=None):
    raw, prepared = _open(packet) if opened is None else opened
    expected = {w["id"] for w in packet["plan"]["workers"]}
    if type(workers) is not dict or set(workers) != expected:
        raise ValueError("BC1 worker roster mismatch")
    omission_check = prepared.check(omission_raw, saved_request=packet["omission_request"])
    if not omission_check["protocol_complete"]:
        raise ValueError("BC1 omission inventory incomplete")
    candidates = {row["id"] for row in omission_check["declared_candidates"]}
    values = {}
    for worker in packet["plan"]["workers"]:
        key = worker["id"]
        request = _worker_request(packet, key, raw, prepared)
        _, value = _unwrap(request, workers[key])
        report = batches.check_worker(_json(value), packet["plan"], key, version=2)
        if not report["passed"]:
            raise ValueError("BC1 worker structure invalid")
        typed._omission_findings(value["findings"], candidates)
        values[key] = value
    return {"kind": STATE, "packet_sha256": packet["sha256"],
        "workers": {key: typed._blob(value, typed.MAX_SAVED_RESPONSE_BYTES) for key, value in workers.items()},
        "omission": typed._blob(omission_raw, omissions.MAX_RESPONSE_BYTES), "omission_check": omission_check,
        "worker_values": values, "processed_workers": [], "rows": {}, "findings": {},
        "row_history": [], "finding_history": [], "stage_commitments": [],
        "omission_dispositions": [], "stages": [], "summary": None, "complete": False}


def start(packet, workers, omission_response):
    return _bound(_seal(_base(packet, workers, omission_response)))


def _incoming(packet, state):
    number = len(state["stages"])
    if state["complete"] or number > len(packet["groups"]):
        raise ValueError("BC1 stage sequence is already complete")
    final = number == len(packet["groups"])
    group = {"id": "final", "workers": []} if final else packet["groups"][number]
    current = deepcopy(state)
    for key in group["workers"]:
        if key in current["processed_workers"]:
            raise ValueError("BC1 worker reused")
        value = current["worker_values"][key]
        for row in value["source_review"]["values"]:
            if row["path"] in current["rows"]:
                raise ValueError("BC1 duplicate worker row")
            current["rows"][row["path"]] = deepcopy(row)
        for ordinal, finding in enumerate(value["findings"]):
            current["findings"][f"worker:{key}:{ordinal:04d}"] = deepcopy(finding)
        current["processed_workers"].append(key)
    return group, current, final


def _row_index(state):
    return [{"path": path, "sha256": batches.object_sha256(state["rows"][path])} for path in sorted(state["rows"])]


def _projection(packet, state):
    changed = {row["path"] for row in state["row_history"]}
    included, excluded = [], []
    for path in sorted(state["rows"]):
        row = state["rows"][path]
        if path in changed or any(c["verdict"] == "revise" for c in row.get("claims", [])):
            included.append(deepcopy(row))
        else:
            excluded.append({"path": path, "row_sha256": batches.object_sha256(row),
                             "kind": "metadata" if "metadata_reason" in row else "supported"})
    candidates = state["omission_check"]["declared_candidates"]
    open_count = len(state["findings"]) + (0 if state["complete"] else len(candidates))
    if open_count > MAX_OPEN_CONCERNS:
        raise ValueError("BC1 open concern count exceeds32; no truncation")
    value = {"format": "ConcernPacketV1", "packet_sha256": packet["sha256"],
        "original_full_sha256": packet["plan"]["original_full_sha256"],
        "current_row_index_sha256": batches.object_sha256(_row_index(state)),
        "processed_workers": list(state["processed_workers"]), "summary": state["summary"],
        "findings": [{"id": key, "sha256": batches.object_sha256(finding), "finding": deepcopy(finding)}
                     for key, finding in state["findings"].items()],
        "source_review": included, "row_decisions": deepcopy(state["row_history"]),
        "finding_decisions": deepcopy(state["finding_history"]),
        "omission_candidates": deepcopy(candidates), "omission_dispositions": deepcopy(state["omission_dispositions"]),
        "stage_commitments": deepcopy(state["stage_commitments"]), "open_concerns": open_count,
        "excluded_unchanged_rows": {"count": len(excluded),
            "supported_count": sum(row["kind"] == "supported" for row in excluded),
            "metadata_count": sum(row["kind"] == "metadata" for row in excluded),
            "roster_sha256": batches.object_sha256(excluded)}}
    dictionary = codec.build_dictionary(chunks={}) if state["complete"] else packet["dictionary"]
    encoded = codec.encode_candidate(value, dictionary=dictionary, max_bytes=codec.CARRY_BYTES)
    return value, encoded, excluded


def _record_digest(packet, state):
    return render_record_digest(packet, row_count=len(state["rows"]),
        current_row_index_sha256=batches.object_sha256(_row_index(state)),
        processed_workers=state["processed_workers"])


def render_record_digest(packet, *, row_count, current_row_index_sha256, processed_workers):
    """Pure exact digest shape; hypothetical sizing values confer no coverage."""
    return {"format": "RecordDigestV1", "original_full_sha256": packet["plan"]["original_full_sha256"],
        "original_core_sha256": packet["inputs"].get("original_core", {}).get("sha256"),
        "plan_sha256": packet["plan"]["sha256"], "row_count": row_count,
        "current_row_index_sha256": current_row_index_sha256,
        "processed_workers": list(processed_workers),
        "all_workers": [w["id"] for w in packet["plan"]["workers"]],
        "authority": "Bookkeeping only. Complete original records, source bundle and schema accompany this digest; hashes do not establish support or rereview."}


def _stage_contract(final):
    schema = deepcopy(audit_batch_format.schema("integration", version=2))
    # Reuse the exact claim/finding/assertion definitions, with a distinct delta.
    props = schema["properties"]
    del props["proposal_index_sha256"]
    props["kind"] = {"const": "bc1_stage_delta_v1"}
    props["stage_id"] = {"type": "string"}
    props["prior_state_sha256"] = {"$ref": "#/$defs/digest"}
    props["current_row_index_sha256"] = {"$ref": "#/$defs/digest"}
    replacement = props["row_replacements"]["items"]
    del replacement["properties"]["previous_sha256"]
    replacement["properties"]["current_row_index_sha256"] = {"$ref": "#/$defs/digest"}
    replacement["required"] = list(replacement["properties"])
    schema["required"] = list(props)
    return {"schema": schema, "rules": [*audit_batch_format.COMMON_RULES, *audit_batch_format.TYPED_RULES,
        "Author a complete BC1 codec candidate whose decoded value matches this delta schema. Copy the exact stage, state and index identities.",
        "Read every complete newly assigned worker row and all claims, all inherited concerns and their complete decision/predecessor histories, and the accompanying original records/source/schema.",
        "Explicitly retain, drop or replace every incoming finding once. Preserve status, attribution, qualifications and removal identities. Drops/replacements need literal evidence and reasons. New judgments must be model-authored.",
        "retain_other_rows_from_index_sha256 explicitly commits preservation of every unreplaced row in the current host index. It does not claim rereview of omitted earlier supporting/metadata rows.",
        "A row replacement names its path and the current complete row-index hash; the controller resolves the exact old row and retains it in history. Supply the entire replacement row, reason and evidence.",
        "Every revise path must link to a retained/new finding. A supporting-only path must not be linked. Reconsider cross-field conflicts using the complete original record, including omitted earlier reviews.",
        ("This is the separately registered final global consistency review. Decide every omission candidate exactly once, retaining it in exactly one final full-record finding or explicitly dropping it with evidence."
         if final else "Omission dispositions must be empty at this intermediate stage. The final stage alone owns their exact-once allocation."),
        "Every required concern and decision survives into carry. If complete content does not fit, refuse; never omit, summarize, regroup or infer supported judgments from hashes."]}


def _stage_request(packet, state, raw, prepared):
    group, current, final = _incoming(packet, state)
    _, projection, _ = _projection(packet, current)
    new_workers = {}
    for key in group["workers"]:
        saved = codec.load(typed._unblob(state["workers"][key], typed.MAX_SAVED_RESPONSE_BYTES), byte_limit=typed.MAX_SAVED_RESPONSE_BYTES)
        new_workers[key] = typed._unblob(saved["response"], codec.WORKER_BYTES).decode("utf-8")
    return _render_stage_request(packet, raw, prepared, stage_id=group["id"],
        new_workers=new_workers, concern_packet=projection, record_digest=_record_digest(packet, current),
        prior_state_sha256=state["sha256"], current_row_index_sha256=batches.object_sha256(_row_index(current)))


def _render_stage_request(packet, raw, prepared, *, stage_id, new_workers, concern_packet,
                          record_digest, prior_state_sha256, current_row_index_sha256):
    final = stage_id == "final"
    if not final and stage_id not in {g["id"] for g in packet["groups"]}:
        raise ValueError("unknown BC1 stage")
    if type(concern_packet) is not bytes or len(concern_packet) > codec.CARRY_BYTES:
        raise ValueError("BC1 concern carry byte bound exceeded")
    return _request(packet, "bc1_stage_request_v1", {"packet_sha256": packet["sha256"],
        "stage": "final" if final else "group", "stage_id": stage_id,
        "prior_state_sha256": prior_state_sha256, "current_row_index_sha256": current_row_index_sha256,
        "new_workers": deepcopy(new_workers),
        "concern_packet": concern_packet.decode("utf-8"), "record_digest": deepcopy(record_digest),
        "shared_context": _shared(packet, raw, prepared), "dictionary": packet["dictionary"],
        "codec_contract": codec.contract(), "output_contract": _stage_contract(final),
        "visible_output_bytes": codec.INTEGRATION_BYTES})


def render_stage_request(packet, *, stage_id, new_workers, concern_packet, record_digest,
                         prior_state_sha256, current_row_index_sha256):
    """Exact pure renderer, also for explicitly hypothetical sizing arguments.

    This neither verifies a stage transition nor authorizes dispatch. Runtime
    must use stage_request, whose arguments derive from independently replayed
    actual deliveries. Placeholder arguments remain hypothetical size scenarios.
    """
    raw, prepared = _open(packet)
    return _render_stage_request(packet, raw, prepared, stage_id=stage_id, new_workers=new_workers,
        concern_packet=concern_packet, record_digest=record_digest,
        prior_state_sha256=prior_state_sha256, current_row_index_sha256=current_row_index_sha256)


def _assertion_report(packet, raw, assertions):
    chunks, _ = evidence.source_chunks_from_bytes(raw["bundle"], raw["manifest"])
    artifacts = {k: raw[k].decode("utf-8") for k in ("original_full", "original_core") if k in raw}
    return evidence.check_assertions(assertions, artifacts=artifacts, chunks=chunks)


def _apply(packet, state, request, saved, raw):
    _, delta = _unwrap(request, saved)
    keys = {"kind", "stage_id", "prior_state_sha256", "current_row_index_sha256",
        "retain_other_rows_from_index_sha256", "row_replacements", "finding_decisions",
        "new_findings", "summary", "omission_dispositions"}
    _exact(delta, keys, "stage delta")
    group, current, final = _incoming(packet, state)
    index_sha = batches.object_sha256(_row_index(current))
    if (delta["kind"] != "bc1_stage_delta_v1" or delta["stage_id"] != group["id"]
            or delta["prior_state_sha256"] != state["sha256"]
            or delta["current_row_index_sha256"] != index_sha
            or delta["retain_other_rows_from_index_sha256"] != index_sha):
        raise ValueError("BC1 stage/state/index binding mismatch")
    g = audit_grammar._Grammar(version=2)
    g.text(delta["summary"], "/summary")
    for field in ("row_replacements", "finding_decisions", "new_findings", "omission_dispositions"):
        if not g.array(delta[field], "/" + field):
            raise ValueError("BC1 stage list required")
    assertions, seen_rows, seen_findings = [], set(), set()
    inventory = {row["path"]: row for row in packet["plan"]["inventory"]["values"]}
    for ordinal, replacement in enumerate(delta["row_replacements"]):
        _exact(replacement, {"path", "current_row_index_sha256", "row", "reason", "evidence"}, "row replacement")
        path = replacement["path"]
        if type(path) is not str or path not in current["rows"] or path in seen_rows or replacement["current_row_index_sha256"] != index_sha:
            raise ValueError("BC1 unknown, duplicate or stale row replacement")
        seen_rows.add(path)
        row = replacement["row"]
        g.review({"artifact": "original_full", "sha256": packet["plan"]["original_full_sha256"], "values": [row]}, "/row")
        if type(row) is not dict or row.get("path") != path:
            raise ValueError("BC1 replacement row path mismatch")
        if "metadata_reason" in row and not inventory[path]["record_metadata_allowed"]:
            raise ValueError("BC1 metadata row not allowed")
        g.text(replacement["reason"], "/reason")
        batches._assertions(g, replacement["evidence"], "/evidence", nonempty=True)
        assertions.extend(replacement["evidence"])
        previous = current["rows"][path]
        current["row_history"].append({"stage": group["id"], "ordinal": ordinal, "path": path,
            "predecessor": deepcopy(previous), "previous_sha256": batches.object_sha256(previous),
            "decision": deepcopy(replacement), "row_sha256": batches.object_sha256(row)})
        current["rows"][path] = deepcopy(row)
    active = {}
    for ordinal, decision in enumerate(delta["finding_decisions"]):
        if type(decision) is not dict:
            raise ValueError("BC1 finding decision object required")
        action = decision.get("action")
        _exact(decision, {"id", "previous_sha256", "action", "reason", "evidence"} | ({"findings"} if action == "replace" else set()), "finding decision")
        identity = decision["id"]
        if type(identity) is not str or identity not in current["findings"] or identity in seen_findings:
            raise ValueError("BC1 finding decision roster mismatch")
        seen_findings.add(identity)
        previous = current["findings"][identity]
        if decision["previous_sha256"] != batches.object_sha256(previous) or action not in {"retain", "drop", "replace"}:
            raise ValueError("BC1 finding decision predecessor/action mismatch")
        g.text(decision["reason"], "/reason")
        batches._assertions(g, decision["evidence"], "/evidence", nonempty=action != "retain")
        assertions.extend(decision["evidence"])
        if action == "retain":
            chosen = [(identity, previous)]
        elif action == "drop":
            chosen = []
        else:
            if type(decision["findings"]) is not list or not decision["findings"]:
                raise ValueError("BC1 replacement findings required")
            chosen = [(f"stage:{group['id']}:replace:{ordinal:04d}:{i:04d}", finding)
                      for i, finding in enumerate(decision["findings"])]
        for key, finding in chosen:
            g.finding(finding, "/finding")
            active[key] = deepcopy(finding)
        current["finding_history"].append({"stage": group["id"], "ordinal": ordinal,
            "predecessor_id": identity, "predecessor": deepcopy(previous),
            "decision": deepcopy(decision), "result_ids": [key for key, _ in chosen]})
    if seen_findings != set(current["findings"]):
        raise ValueError("BC1 every incoming finding needs an explicit decision")
    for ordinal, finding in enumerate(delta["new_findings"]):
        g.finding(finding, "/new_findings")
        identity = f"stage:{group['id']}:new:{ordinal:04d}"
        active[identity] = deepcopy(finding)
        current["finding_history"].append({"stage": group["id"], "ordinal": ordinal,
            "predecessor_id": None, "predecessor": None,
            "decision": {"action": "new", "finding": deepcopy(finding)}, "result_ids": [identity]})
    if not final and delta["omission_dispositions"]:
        raise ValueError("BC1 omissions belong exclusively to the final stage")
    for disposition in delta["omission_dispositions"]:
        _exact(disposition, {"candidate_id", "action", "reason", "evidence"}, "omission disposition")
        g.text(disposition["candidate_id"], "/candidate_id")
        g.enum(disposition["action"], {"retain", "drop"}, "/action")
        g.text(disposition["reason"], "/reason")
        batches._assertions(g, disposition["evidence"], "/evidence", nonempty=disposition["action"] != "retain")
        assertions.extend(disposition["evidence"])
    if not g.result()["passed"]:
        raise ValueError("BC1 stage grammar failed")
    if _assertion_report(packet, raw, assertions):
        raise ValueError("BC1 stage decision evidence failed")
    ids = {row["id"] for row in state["omission_check"]["declared_candidates"]}
    typed._omission_findings(list(active.values()), ids)
    # Also validate replaced proposals even if their children are later dropped.
    for decision in delta["finding_decisions"]:
        typed._omission_findings(decision.get("findings", []), ids)
    current.update(findings=active, omission_dispositions=deepcopy(delta["omission_dispositions"]),
                   summary=delta["summary"], complete=final)
    audit = _audit(packet, current)
    if not audit_grammar.check(_json(audit), version=2)["passed"] or batches._removal_errors(audit, packet["plan"]):
        raise ValueError("BC1 assembled intermediate grammar/removal failed")
    if final:
        dispositions = delta["omission_dispositions"]
        if len({d["candidate_id"] for d in dispositions}) != len(dispositions):
            raise ValueError("BC1 duplicate final omission disposition")
        typed._account(audit, delta, state["omission_check"]["declared_candidates"])
    current["stage_commitments"].append({"stage": group["id"], "workers": list(group["workers"]),
        "prior_state_sha256": state["sha256"], "current_row_index_sha256": index_sha,
        "retain_other_rows_from_index_sha256": delta["retain_other_rows_from_index_sha256"],
        "request_sha256": request["request_sha256"], "saved_response_sha256": _sha(saved),
        "decoded_delta_sha256": batches.object_sha256(delta)})
    current["stages"].append(typed._blob(saved, typed.MAX_SAVED_RESPONSE_BYTES))
    current.pop("sha256", None)
    _projection(packet, current)  # Bound the result before any next dispatch.
    return _bound(_seal(current))


def _audit(packet, state):
    ordered = [row["path"] for row in packet["plan"]["inventory"]["values"]]
    return {"summary": state["summary"], "findings": list(state["findings"].values()),
        "source_review": {"artifact": "original_full", "sha256": packet["plan"]["original_full_sha256"],
            "values": [state["rows"][path] for path in ordered if path in state["rows"]]}}


def _replay(packet, state):
    if type(state) is not dict or state.get("kind") != STATE:
        raise ValueError("BC1 state kind mismatch")
    _bound(state)
    workers = {key: typed._unblob(value, typed.MAX_SAVED_RESPONSE_BYTES) for key, value in state["workers"].items()}
    omission = typed._unblob(state["omission"], omissions.MAX_RESPONSE_BYTES)
    raw, prepared = _open(packet)
    saved_stages = [typed._unblob(blob, typed.MAX_SAVED_RESPONSE_BYTES) for blob in state["stages"]]
    expected = _replay_deliveries(packet, workers, omission, saved_stages, raw, prepared)
    if _json(expected) != _json(state):
        raise ValueError("BC1 state differs from independent response replay")
    return expected, raw, prepared


def _replay_deliveries(packet, workers, omission, stages, raw, prepared):
    if type(stages) is not list or len(stages) > len(packet["groups"]) + 1:
        raise ValueError("BC1 saved stage roster exceeds the fixed plan")
    state = _seal(_base(packet, workers, omission, opened=(raw, prepared)))
    for saved in stages:
        request = _stage_request(packet, state, raw, prepared)
        state = _apply(packet, state, request, saved, raw)
    return state


def replay(packet, workers, omission_response, stages):
    """Replay every supplied raw stage once, from newly verified authorities.

    No caller-supplied derived state or cache is trusted. Runtime uses this to
    reconstruct a prefix without repeatedly rechecking every shorter prefix.
    """
    raw, prepared = _open(packet)
    return _replay_deliveries(packet, workers, omission_response, stages, raw, prepared)


def stage_request(packet, state, stage_id):
    verified, raw, prepared = _replay(packet, state)
    request = _stage_request(packet, verified, raw, prepared)
    if request["payload"]["stage_id"] != stage_id:
        raise ValueError("BC1 stage order mismatch")
    return request


def apply_transition(packet, state, request, saved):
    verified, raw, prepared = _replay(packet, state)
    expected = _stage_request(packet, verified, raw, prepared)
    if _json(request) != _json(expected):
        raise ValueError("BC1 request changed after construction")
    return _apply(packet, verified, request, saved, raw)


def check_transition(packet, state, request, saved):
    result = apply_transition(packet, state, request, saved)
    return {"passed": True, "state_sha256": result["sha256"], "scientific_support": "unverified"}


def concern_packet(packet, state):
    verified, _, _ = _replay(packet, state)
    return _projection(packet, verified)[0]


def record_digest(packet, state):
    verified, _, _ = _replay(packet, state)
    return _record_digest(packet, verified)


def _terminal(packet, state, raw):
    if not state["complete"] or len(state["stages"]) != len(packet["groups"]) + 1:
        raise ValueError("BC1 final cross-group review is missing")
    if set(state["rows"]) != {row["path"] for row in packet["plan"]["inventory"]["values"]}:
        raise ValueError("BC1 final full-row roster incomplete")
    audit = _audit(packet, state)
    audit_raw = _json(audit)
    if not audit_grammar.check(audit_raw, version=2)["passed"] or batches._removal_errors(audit, packet["plan"]):
        raise ValueError("BC1 terminal grammar/removal failed")
    chunks, _ = evidence.source_chunks_from_bytes(raw["bundle"], raw["manifest"])
    artifacts = {k: raw[k].decode("utf-8") for k in ("original_full", "original_core") if k in raw}
    checked = evidence.check_audit(audit, artifacts=artifacts, chunks=chunks, protocol_version=7,
        source_manifest_raw=raw.get("source_manifest"), project=packet["project"])
    assertions = [e for row in state["row_history"] for e in row["decision"]["evidence"]]
    assertions += [e for row in state["finding_history"] for e in row["decision"].get("evidence", [])]
    assertions += [e for row in state["omission_dispositions"] for e in row["evidence"]]
    problems = checked["findings"] + evidence.check_assertions(assertions, artifacts=artifacts, chunks=chunks)
    accounting = typed._account(audit, {"omission_dispositions": state["omission_dispositions"]}, state["omission_check"]["declared_candidates"])
    counts = Counter(f.get("kind", "untyped") for f in audit["findings"])
    report = {"kind": "bc1_acceptance_v1", "passed": not problems, "packet_sha256": packet["sha256"],
        "acceptance_scope": "captured identity, full declared coverage and literal evidence; staged model access differs from legacy",
        "scientific_support": "unverified", "novelty": "unverified", "exhaustive_recall": "unverified",
        "finding_counts": {kind: counts[kind] for kind in sorted(audit_protocol.KINDS | {"untyped"})},
        "omission_counts": {**state["omission_check"]["counts"],
            "retained": sum(row["disposition"]["action"] == "retain" for row in accounting),
            "dropped": sum(row["disposition"]["action"] == "drop" for row in accounting)},
        "source_review": {k: v for k, v in checked["source_review_original"].items() if k != "findings"},
        "revised_rows": sum(any(c["verdict"] == "revise" for c in row.get("claims", [])) for row in audit["source_review"]["values"]),
        "assertions_checked": checked["assertions_checked"] + len(assertions),
        "problem_count": len(problems), "problems": problems[:50], "problems_truncated": len(problems) > 50,
        "limitations": list(LIMITATIONS)}
    projection, _, excluded = _projection(packet, state)
    lineage = {"kind": "bc1_lineage_v1", "packet_sha256": packet["sha256"],
        "audit_sha256": _sha(audit_raw), "row_index": _row_index(state),
        "row_history": state["row_history"], "finding_history": state["finding_history"],
        "stage_commitments": state["stage_commitments"], "omission_candidates": accounting,
        "excluded_unchanged_rows": excluded, "decision_assertions": assertions}
    return audit_raw, lineage, report, projection


def assemble(packet, workers, omission_response, stages):
    if type(stages) is not list or len(stages) != len(packet["groups"]) + 1:
        raise ValueError("BC1 complete preplanned stage roster required")
    raw, prepared = _open(packet)
    state = _replay_deliveries(packet, workers, omission_response, stages, raw, prepared)
    audit_raw, lineage, report, projection = _terminal(packet, state, raw)
    if not report["passed"]:
        raise ValueError("BC1 terminal literal evidence failed")
    return _bound(_seal({"kind": ASSEMBLY, "packet": deepcopy(packet),
        "workers": deepcopy(state["workers"]), "omission_response": deepcopy(state["omission"]),
        "stages": deepcopy(state["stages"]), "audit": typed._blob(audit_raw, codec.MAX_DECODED_BYTES),
        "lineage": lineage, "acceptance": report, "projection": projection}))


def check(assembly):
    _exact(assembly, {"kind", "packet", "workers", "omission_response", "stages", "audit", "lineage", "acceptance", "projection", "sha256"}, "assembly")
    _bound(assembly)
    if assembly["kind"] != ASSEMBLY:
        raise ValueError("BC1 assembly kind mismatch")
    expected = assemble(assembly["packet"],
        {k: typed._unblob(v, typed.MAX_SAVED_RESPONSE_BYTES) for k, v in assembly["workers"].items()},
        typed._unblob(assembly["omission_response"], omissions.MAX_RESPONSE_BYTES),
        [typed._unblob(v, typed.MAX_SAVED_RESPONSE_BYTES) for v in assembly["stages"]])
    if _json(expected) != _json(assembly):
        raise ValueError("BC1 assembly differs from independent captured-byte replay")
    return {**expected["acceptance"], "assembly_sha256": expected["sha256"], "independently_reconstructed": True}


def audit_bytes(assembly):
    check(assembly)
    return typed._unblob(assembly["audit"], codec.MAX_DECODED_BYTES)


def project(assembly):
    check(assembly)
    return deepcopy(assembly["projection"])


def downstream_contract():
    return {"format": "bc1_downstream_contract_v1", "codec": codec.contract(),
        "dictionary": codec.build_dictionary(chunks={}),
        "rules": [
            "The Audit findings model input is a self-contained bc1_codec_v1 candidate. Resolve its local strings table, literal escapes and intrinsic sha256_b64 tags exactly. The empty dictionary supplied here means no external chunk, slot, class or span references are permitted.",
            "This is a deterministic projection of a separately retained complete machine audit. It preserves every final finding, revised or ever-changed row, complete predecessor/decision history, omission candidate and disposition. Untouched supported/metadata review rows are intentionally omitted; their counts and full-roster hash are bookkeeping, not evidence of support or rereview.",
            "Use the complete accompanying source bundle, schema and original/current records. Reconciliation must inspect every occurrence, not only listed paths. Report writing must freshly review every populated final-full value, including unchanged and mixed-status lists, and emit the complete source_review and Evidence assertions appendix.",
            "Keep original_full/original_core distinct from final_full/final_core. Preserve all changes, qualifications and dispositions. Do not infer support from omitted rows, copied text or hashes. Missing/unrecognized projection data never means zero findings; refuse unresolved references or missing required content.",
        ]}


def project_bytes(assembly):
    """Verified self-contained model projection; complete audit stays separate."""
    check(assembly)
    return codec.encode_candidate(assembly["projection"], dictionary=codec.build_dictionary(chunks={}),
                                  max_bytes=codec.CARRY_BYTES)
