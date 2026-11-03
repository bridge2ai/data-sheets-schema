"""Invented BC1 packets exercise complete captured-byte replay, offline only."""
from copy import deepcopy
import hashlib
import json

import pytest

from data_sheets_schema import audit_batches as b, audit_omissions as om
from data_sheets_schema import bc1_audit as bc, bc1_codec as codec, bc1_context
from data_sheets_schema.chunking import manifest_from_bytes
from data_sheets_schema.schema_snapshot import capture_schema


@pytest.fixture
def supplied(tmp_path):
    root = tmp_path / "schema.yaml"
    root.write_text("""id: https://example.test/bc1
name: bc1
prefixes: {linkml: 'https://w3id.org/linkml/'}
imports: [linkml:types]
default_range: string
classes:
  Dataset:
    attributes:
      name: {}
      description: {}
      title: {}
      missing: {}
""")
    snapshot = capture_schema(root, strict=True)
    bundle = b"Preamble\nFILE: manual.txt\nPATH: manual.txt\nExample. Complete description. Exact title. Proposed missing value.\n"
    manifest = manifest_from_bytes(bundle, "invented")
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": row["id"], "status": "nothing_relevant"} for row in manifest["chunks"]]}
    context = {"format": "omission_context_v1", "root_class": "Dataset", "scopes": [
        {"owner": "", "referent": "Example", "release": "1", "scope": "This invented release."}],
        "source_policy": {"priority": ["manual.txt"], "basis": "Invented fixture."}, "vocabulary": {}}
    context_raw = b.canonical_bytes(context)
    selection = {"bounded_carry": {"version": 1, "fan_in": 2, "contract": {
        "protocol": bc.PROTOCOL, "version": 1, "audit": bc.contract_identity(), "context": bc1_context.contract_identity()}},
        "inputs": {"profile": {"name": "neutral", "basis": "Explicit invented offline fixture.", "vocabulary": None},
                   "context": {"sha256": hashlib.sha256(context_raw).hexdigest(), "bytes": len(context_raw)},
                   "full_schema": bc1_context._schema_pin(snapshot)}}
    return dict(selection=selection, original_full=b"name: Example\ndescription: Complete description\ntitle: Exact title\n",
        bundle=bundle, manifest=b.canonical_bytes(manifest), receipt=b.canonical_bytes(receipt),
        context=context_raw, schema_snapshot=snapshot, max_output_tokens=4000, max_paths=1)


@pytest.fixture
def packet(supplied):
    return bc.prepare(**supplied)


def deliveries(packet, *, omission_count=0, revise=False):
    request = bc.omission_request(packet)
    chunk = next(row for row in request["payload"]["chunks"] if row["source"] == "manual.txt")
    quote = {"source": "manual.txt", "chunk": chunk["chunk"], "quote": "Example. Complete description. Exact title. Proposed missing value."}
    rows = [{"chunk": row["chunk"], "status": "no_omission", "reason": "No candidate.", "candidates": []}
            for row in request["payload"]["chunks"]]
    if omission_count:
        next(row for row in rows if row["chunk"] == chunk["chunk"]).update(status="omission", candidates=[
            {"id": f"candidate-{i}", "kind": "omission", "source": "manual.txt", "quote": quote["quote"],
             "target": {"owner": "", "slot_chain": ["missing"]}, "missing_information": "Proposed missing value.",
             "scope_basis": "Source states this invented release."} for i in range(omission_count)])
    omission = b.canonical_bytes({"format": "omission_inventory_v1", "request_sha256": request["request_sha256"], "chunks": rows})
    workers = {}
    for worker in packet["plan"]["workers"]:
        values = [{"path": row["path"], "claims": [{"text": row["text"], "verdict": "supported",
            "attributed_to": [], "claim_status": "fact", "source_status": "fact", "evidence": [quote], "reason": "Source states the complete value."}]}
            for row in packet["plan"]["inventory"]["values"] if row["path"] in worker["paths"]]
        findings = []
        if revise and worker == packet["plan"]["workers"][0]:
            values[0]["claims"][0]["verdict"] = "revise"
            findings = [{"severity": "low", "record": "full", "slot": values[0]["path"][1:],
                "issue": "A proposed correction requiring judgment.", "review_paths": [values[0]["path"]], "evidence": [quote]}]
        audit = {"findings": findings, "summary": "Worker-authored review.", "source_review": {
            "artifact": "original_full", "sha256": packet["plan"]["original_full_sha256"], "values": values}}
        raw = codec.encode_candidate(audit, dictionary=packet["dictionary"])
        workers[worker["id"]] = bc.capture_response(bc.worker_request(packet, worker["id"]), raw)
    return workers, omission, quote


def stage_delta(packet, request, *, quote, omissions=()):
    p = request["payload"]
    concerns = codec.decode_candidate(p["concern_packet"].encode(), dictionary=packet["dictionary"], max_bytes=codec.CARRY_BYTES)
    delta = {"kind": "bc1_stage_delta_v1", "stage_id": p["stage_id"],
        "prior_state_sha256": p["prior_state_sha256"], "current_row_index_sha256": p["current_row_index_sha256"],
        "retain_other_rows_from_index_sha256": p["current_row_index_sha256"], "row_replacements": [],
        "finding_decisions": [{"id": row["id"], "previous_sha256": row["sha256"], "action": "retain",
                               "reason": "Explicit model retention.", "evidence": []} for row in concerns["findings"]],
        "new_findings": [], "summary": "Explicit model global review." if p["stage"] == "final" else "Explicit model staged review.",
        "omission_dispositions": []}
    if p["stage"] == "final" and omissions:
        delta["omission_dispositions"] = [{"candidate_id": c["id"], "action": "retain", "reason": "Retain for review.", "evidence": []} for c in omissions]
        delta["new_findings"] = [{"severity": "medium", "record": "full", "slot": "missing", "kind": "omission",
            "omission_candidates": [c["id"] for c in omissions], "issue": "Proposed missing value.", "evidence": [quote]}]
    return delta


def save_delta(packet, request, delta):
    return bc.capture_response(request, codec.encode_candidate(delta, dictionary=packet["dictionary"], max_bytes=codec.INTEGRATION_BYTES))


def finish(packet, workers, omission, quote, mutate=None):
    state = bc.start(packet, workers, omission)
    stages = []
    for group in [*packet["groups"], {"id": "final"}]:
        request = bc.stage_request(packet, state, group["id"])
        delta = stage_delta(packet, request, quote=quote, omissions=state["omission_check"]["declared_candidates"])
        if mutate:
            mutate(group["id"], request, delta)
        saved = save_delta(packet, request, delta)
        state = bc.apply_transition(packet, state, request, saved)
        stages.append(saved)
    return bc.assemble(packet, workers, omission, stages), state


@pytest.mark.parametrize("fan_in", [1, 2])
def test_complete_replay_width_all_groups_and_final(supplied, fan_in):
    supplied["selection"]["bounded_carry"]["fan_in"] = fan_in
    packet = bc.prepare(**supplied, fan_in=fan_in)
    workers, omission, quote = deliveries(packet, omission_count=1)
    assembly, state = finish(packet, workers, omission, quote)
    check = bc.check(assembly)
    assert check["passed"] and check["independently_reconstructed"]
    assert check["scientific_support"] == check["novelty"] == check["exhaustive_recall"] == "unverified"
    assert check["omission_counts"]["retained"] == 1
    assert len(packet["groups"]) == (len(workers) + fan_in - 1) // fan_in
    assert len(bc.roster(packet)) == len(workers) + 1 + len(packet["groups"]) + 1
    audit = json.loads(bc.audit_bytes(assembly))
    assert len(audit["source_review"]["values"]) == 3
    assert len(state["stages"]) == len(packet["groups"]) + 1
    assert bc.replay(packet, workers, omission,
        [bc.typed._unblob(blob, bc.typed.MAX_SAVED_RESPONSE_BYTES) for blob in state["stages"]]) == state
    projection = bc.project(assembly)
    assert projection["source_review"] == []
    assert projection["excluded_unchanged_rows"]["supported_count"] == 3
    assert len(assembly["lineage"]["excluded_unchanged_rows"]) == 3


def test_missing_final_or_reordered_stage_cannot_seal(packet):
    workers, omission, quote = deliveries(packet)
    state = bc.start(packet, workers, omission)
    with pytest.raises(ValueError, match="order"):
        bc.stage_request(packet, state, "final")
    with pytest.raises(ValueError, match="complete preplanned"):
        bc.assemble(packet, workers, omission, [])


def test_raw_and_host_state_tampering_cannot_be_repinned(packet):
    workers, omission, quote = deliveries(packet)
    state = bc.start(packet, workers, omission)
    changed = deepcopy(state)
    changed["summary"] = "controller invented support"
    changed = bc._seal({k: v for k, v in changed.items() if k != "sha256"})
    with pytest.raises(ValueError, match="independent"):
        bc.stage_request(packet, changed, packet["groups"][0]["id"])
    request = bc.stage_request(packet, state, packet["groups"][0]["id"])
    delta = stage_delta(packet, request, quote=quote)
    saved = save_delta(packet, request, delta)
    changed_request = deepcopy(request)
    changed_request["payload"]["record_digest"]["row_count"] += 1
    changed_request["request_sha256"] = bc._sha(bc._json(changed_request["payload"]))
    with pytest.raises(ValueError, match="changed"):
        bc.apply_transition(packet, state, changed_request, saved)


@pytest.mark.parametrize("field", ["prior_state_sha256", "current_row_index_sha256", "retain_other_rows_from_index_sha256"])
def test_stage_binding_is_causal(packet, field):
    workers, omission, quote = deliveries(packet)
    state = bc.start(packet, workers, omission)
    request = bc.stage_request(packet, state, packet["groups"][0]["id"])
    delta = stage_delta(packet, request, quote=quote)
    delta[field] = "0" * 64
    with pytest.raises(ValueError, match="binding"):
        bc.apply_transition(packet, state, request, save_delta(packet, request, delta))


def test_changed_supported_row_and_dropped_predecessor_survive(packet):
    workers, omission, quote = deliveries(packet, revise=True)
    def modify(stage_id, request, delta):
        if stage_id != packet["groups"][0]["id"]:
            return
        concerns = codec.decode_candidate(request["payload"]["concern_packet"].encode(), dictionary=packet["dictionary"], max_bytes=codec.CARRY_BYTES)
        row = deepcopy(concerns["source_review"][0])
        row["claims"][0]["verdict"] = "supported"
        delta["row_replacements"] = [{"path": row["path"], "current_row_index_sha256": delta["current_row_index_sha256"],
            "row": row, "reason": "Model corrected prior judgment.", "evidence": [quote]}]
        delta["finding_decisions"][0].update(action="drop", reason="Model finds original concern unsupported.", evidence=[quote])
    assembly, _ = finish(packet, workers, omission, quote, modify)
    projection = assembly["projection"]
    assert len(projection["source_review"]) == 1
    assert projection["source_review"][0]["claims"][0]["verdict"] == "supported"
    assert projection["row_decisions"][0]["predecessor"]["claims"][0]["verdict"] == "revise"
    assert projection["finding_decisions"][0]["decision"]["action"] == "drop"
    assert projection["finding_decisions"][0]["predecessor"]["issue"]


def test_unseen_row_replacement_uses_full_current_index_and_explicit_evidence(packet):
    workers, omission, quote = deliveries(packet)
    def modify(stage_id, request, delta):
        if stage_id != "final":
            return
        row = {
            "path": "/name", "claims": [{"text": "Example", "verdict": "supported", "attributed_to": [],
                "claim_status": "fact", "source_status": "fact", "evidence": [quote], "reason": "Explicit reconsideration."}]}
        delta["row_replacements"] = [{"path": "/name", "current_row_index_sha256": delta["current_row_index_sha256"],
            "row": row, "reason": "Final model reviewed an earlier omitted row.", "evidence": [quote]}]
    assembly, _ = finish(packet, workers, omission, quote, modify)
    assert assembly["lineage"]["row_history"][0]["predecessor"]["path"] == "/name"
    assert assembly["projection"]["source_review"][0]["path"] == "/name"


def test_missing_finding_decision_and_bad_literal_evidence_refuse(packet):
    workers, omission, quote = deliveries(packet, revise=True)
    state = bc.start(packet, workers, omission)
    request = bc.stage_request(packet, state, packet["groups"][0]["id"])
    delta = stage_delta(packet, request, quote=quote)
    delta["finding_decisions"] = []
    with pytest.raises(ValueError, match="every incoming"):
        bc.apply_transition(packet, state, request, save_delta(packet, request, delta))
    delta = stage_delta(packet, request, quote=quote)
    delta["finding_decisions"][0]["evidence"] = [{**quote, "quote": "absent invented source wording"}]
    with pytest.raises(ValueError, match="evidence"):
        bc.apply_transition(packet, state, request, save_delta(packet, request, delta))


def test_open_concern_cap_is_separate_and_no_partial_request_returned(packet):
    workers, omission, quote = deliveries(packet, omission_count=33)
    state = bc.start(packet, workers, omission)
    with pytest.raises(ValueError, match="concern count"):
        bc.stage_request(packet, state, packet["groups"][0]["id"])


def test_neutral_policy_and_selection_are_captured_not_ambient(packet):
    changed = deepcopy(packet)
    changed["term_policy"]["profile"]["basis"] = "edited"
    changed = bc._seal({k: v for k, v in changed.items() if k != "sha256"})
    with pytest.raises(ValueError, match="derivation"):
        bc.omission_request(changed)
    changed = deepcopy(packet)
    changed["selection"]["bounded_carry"]["contract"]["audit"]["max_open_concerns"] = 999
    with pytest.raises(ValueError, match="contract"):
        bc.omission_request(changed)


def test_terminal_checks_real_worker_source_evidence_after_structural_pass(packet):
    workers, omission, quote = deliveries(packet)
    identity = next(iter(workers))
    request = bc.worker_request(packet, identity)
    saved = json.loads(workers[identity])
    inner = bc.typed._unblob(saved["response"], codec.WORKER_BYTES)
    worker = codec.decode_candidate(inner, dictionary=packet["dictionary"])
    worker["source_review"]["values"][0]["claims"][0]["evidence"][0]["quote"] = "This statement is absent from the source."
    workers[identity] = bc.capture_response(request, codec.encode_candidate(worker, dictionary=packet["dictionary"]))
    assert bc.check_worker(packet, identity, workers[identity])["passed"]
    with pytest.raises(ValueError, match="terminal literal evidence"):
        finish(packet, workers, omission, quote)


def test_saved_worker_cannot_be_replayed_under_another_assignment(packet):
    workers, omission, quote = deliveries(packet)
    first, second = list(workers)[:2]
    workers[second] = workers[first]
    with pytest.raises(ValueError, match="does not bind"):
        bc.start(packet, workers, omission)


def test_legacy_typed_packet_cannot_be_misread_as_bc1(packet):
    changed = deepcopy(packet)
    changed["kind"] = "typed_audit_packet_v1"
    with pytest.raises(ValueError, match="protocol"):
        bc.omission_request(changed)


def test_actual_stage_and_hypothetical_renderer_share_exact_wire(packet):
    workers, omission, quote = deliveries(packet)
    state = bc.start(packet, workers, omission)
    request = bc.stage_request(packet, state, packet["groups"][0]["id"])
    p = request["payload"]
    rendered = bc.render_stage_request(packet, stage_id=p["stage_id"], new_workers=p["new_workers"],
        concern_packet=p["concern_packet"].encode(), record_digest=p["record_digest"],
        prior_state_sha256=p["prior_state_sha256"], current_row_index_sha256=p["current_row_index_sha256"])
    assert rendered == request
    assert all(json.loads(raw)["format"] == codec.FORMAT for raw in p["new_workers"].values())
    assert "original_full" in p["shared_context"] and "bundle" in p["shared_context"]


def test_omission_dispositions_only_at_final_and_exact_once(packet):
    workers, omission, quote = deliveries(packet, omission_count=1)
    state = bc.start(packet, workers, omission)
    request = bc.stage_request(packet, state, packet["groups"][0]["id"])
    delta = stage_delta(packet, request, quote=quote)
    delta["omission_dispositions"] = [{"candidate_id": "candidate-0", "action": "retain", "reason": "too early", "evidence": []}]
    with pytest.raises(ValueError, match="final stage"):
        bc.apply_transition(packet, state, request, save_delta(packet, request, delta))
    def duplicate(stage_id, request, delta):
        if stage_id == "final":
            delta["omission_dispositions"] *= 2
    with pytest.raises(ValueError, match="duplicate"):
        finish(packet, workers, omission, quote, duplicate)


def test_downstream_projection_is_self_contained_and_bounded(packet):
    workers, omission, quote = deliveries(packet)
    state = bc.start(packet, workers, omission)
    state["finding_history"] = [{"full_retained_history": "literal long history " * 1000}] * 20
    # This is a pure sizing/cap fixture, not an accepted state or model decision.
    decoded, encoded, _ = bc._projection(packet, state)
    assert len(bc._json(decoded)) > codec.CARRY_BYTES
    assert len(encoded) < codec.CARRY_BYTES
    state["complete"] = True
    decoded, encoded, _ = bc._projection(packet, state)
    empty = bc.downstream_contract()["dictionary"]
    assert codec.decode_candidate(encoded, dictionary=empty, max_bytes=codec.CARRY_BYTES) == decoded
    assert len(encoded) < codec.CARRY_BYTES
    state["finding_history"] = [{"full_retained_history": str(i) + "x" * 20000} for i in range(20)]
    with pytest.raises(ValueError, match="byte bound"):
        bc._projection(packet, state)
