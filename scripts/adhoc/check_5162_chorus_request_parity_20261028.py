"""Build offline CHORUS shared-v1 request bytes for #5162, 2026-10-28.

Inputs: current checkout resources and a fixed synthetic intermediate record.
Outputs: canonical request bodies and hashes below an external --output path.
No execution, provider/count calls, scientific judgments, or run-directory writes.
Use the same --authority-path before/after so path spelling is held constant.
Comparison reports literal parity separately from parity with only the typed
binding's source-dependent registration fingerprint held fixed. No other bytes
are removed or normalized, and the original complete bodies remain on disk.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts import build_api_registrations as builder
from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema import receipt_completion as rc, typed_audit as typed
from data_sheets_schema import typed_audit_runtime as runtime, evidence_assertions
from tests.test_source_review import review_for


def denied(*args, **kwargs):
    raise AssertionError("offline request parity: network forbidden")


def compare_body(before, after, before_reg, after_reg):
    if before == after:
        return {"identical": True, "fixed_registration_identical": True}
    # The fingerprint is itself model-visible. Report the literal mismatch;
    # this second comparison isolates payload behavior from source identity.
    updated = json.loads(after)
    bindings = [part for message in updated["messages"] for part in message["content"]
                if part.get("text", "").startswith(runtime.BINDING_HEADER)]
    if len(bindings) != 1:
        raise AssertionError("unexpected request drift outside a typed binding")
    part = bindings[0]
    binding = json.loads(part["text"][len(runtime.BINDING_HEADER):])
    assert binding["registration_sha256"] == sg.sha(after_reg)
    binding["registration_sha256"] = sg.sha(before_reg)
    part["text"] = runtime.BINDING_HEADER + sg.canonical(binding).decode()
    assert sg.canonical(updated) == before, "request drift exceeds the registration fingerprint"
    return {"identical": False, "fixed_registration_identical": True,
            "changed_field": "typed binding.registration_sha256"}


def requests(authority_path, *, canary=False):
    reg = builder.build_registration(
        "CHORUS", "codex-5162ci-parity", partition="chorus",
        registration_path=authority_path, write_to_disk=False,
    )
    authority_path.parent.mkdir(parents=True, exist_ok=True)
    authority_path.write_bytes(sg.canonical(reg))
    assert authority_path.read_bytes() == sg.canonical(reg)
    inputs = reg["inputs"]
    spec = api.RunSpec(
        **reg["run"], condition="generic_v10", condition_stated=True,
        bundle=Path(inputs["bundle"]["path"]),
        chunk_manifest=Path(inputs["chunk_manifest"]["path"]),
        manifest=Path(inputs["source_manifest"]["path"]),
        profile=inputs["profile"]["name"], profile_basis=inputs["profile"]["basis"],
        runtime=api.RUNTIME, provider=reg["runtime"]["provider"],
        out_dir=authority_path.parent / "unused-output",
        render_version=25, shared_generation_version=1,
        shared_generation_registration=sg.canonical(reg).decode(),
        api_playbook_version=2, receipt_completion_version=2,
        receipt_completion_registration=sg.canonical(reg["receipt"]).decode(),
    )
    settings = api._model_settings("generic_v10")
    spec.bind_api_header_values(settings)
    full = api.build_phase(spec, "full", carry={})
    bodies = {"full": rc.request_payload(full, settings, {"max_output_tokens":
        api.phase_max_tokens(spec, "full", api.DEFAULT_MAX_TOKENS, model=settings["name"])})}
    if canary:
        return reg, bodies

    captured = sg.capture(spec)
    record = b"id: urn:synthetic:parity\nname: Synthetic parity fixture\n"
    bundle = captured.raw(inputs["bundle"]["path"])
    manifest = captured.raw(inputs["chunk_manifest"]["path"])
    chunks, _ = evidence_assertions.source_chunks_from_bytes(bundle, manifest)
    receipt = sg.canonical({"bundle_md5": hashlib.md5(bundle).hexdigest(), "chunks": [
        {"id": key, "status": "nothing_relevant", "reason": "Offline fixture only."} for key in chunks]})
    carry = {"Original full record": record.decode(), "Original core record": record.decode(),
             "Completed full record": record.decode(), "Completed core record": record.decode(),
             "Reconciled full record": record.decode(), "Audit findings": '{"findings": []}'}
    for phase in ("reconcile_full", "report"):
        request = api.build_phase(spec, phase, carry=carry)
        bodies[phase] = rc.request_payload(request, settings, {"max_output_tokens":
            api.phase_max_tokens(spec, "report" if phase == "report_regate" else phase,
                                 api.DEFAULT_MAX_TOKENS, model=settings["name"])})
    request = deepcopy(request)
    api._append_regate(request, spec, "Fixed offline report.", [{"kind": "synthetic", "detail": "Parity fixture."}])
    bodies["report_regate"] = rc.request_payload(request, settings, {"max_output_tokens":
        api.phase_max_tokens(spec, "report", api.DEFAULT_MAX_TOKENS, model=settings["name"])})
    receipt_inputs = {
        "record": record.decode(), "receipt": receipt.decode(),
        "manifest": manifest.decode(), "bundle": bundle.decode(),
        "schema": rc.schema_capture(spec), "max_output_tokens": reg["receipt"]["max_output_tokens"],
        "policy": rc.policy_identity(version=2), "registration": rc.registration_identity(spec),
        "transcript": {"system": full.system, "cached_blocks": full.cached_blocks,
                       "messages": full.messages, "response": record.decode()},
    }
    request, _ = rc.build_request(receipt_inputs)
    bodies[rc.PHASE] = rc.request_payload(request, settings, reg["receipt"])
    packet = runtime._prepare_packet_bytes(spec, captured,
        {"original_full": record, "original_core": record}, receipt)
    omission_request = typed.omission_wire_request(packet, derivations=runtime._derivations(spec))
    omission = sg.canonical({"format": "omission_inventory_v1",
        "request_sha256": omission_request["request_sha256"], "chunks": [
            {"chunk": row["chunk"], "status": "no_omission", "reason": "Offline fixture only.", "candidates": []}
            for row in omission_request["payload"]["chunks"]]})
    review = review_for(record.decode(), chunks=chunks)
    workers = {}
    for stage in runtime.roster(packet):
        _, payload, inner = runtime._build_request_bytes(
            spec, captured, packet, stage, workers, omission, settings,
            generation="fixed-offline-parity-generation", receipt_carry="Fixed offline receipt carry.")
        key = stage["phase"] + ("-" + stage["worker_id"] if "worker_id" in stage else "")
        bodies[key] = payload
        if stage["phase"] == runtime.WORKER_PHASE:
            paths = json.loads(inner["payload"]["stage"])["assignment"]["paths"]
            selected = deepcopy(review)
            selected["values"] = [row for row in selected["values"] if row["path"] in paths]
            workers[stage["worker_id"]] = typed.capture_response(inner, sg.canonical({
                "findings": [], "summary": "Offline structural fixture only.", "source_review": selected}))
    bodies["omission-inner"] = omission_request
    return reg, bodies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--authority-path", required=True, type=Path)
    parser.add_argument("--canary", action="store_true")
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args()
    for path in (args.output, args.authority_path):
        if path.resolve().is_relative_to(ROOT):
            parser.error("outputs and nominal authority path must be outside the checkout")
    socket.socket.connect = denied
    socket.create_connection = denied
    socket.getaddrinfo = denied
    api.provider_identity = lambda: {"provider": None, "base_url": None, "key_env": None}
    reg, bodies = requests(args.authority_path, canary=args.canary)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "registration.json").write_bytes(sg.canonical(reg))
    rows = {}
    for name, body in bodies.items():
        raw = sg.canonical(body)
        target = args.output / (name + ".json")
        target.write_bytes(raw)
        assert target.read_bytes() == raw and raw
        rows[name] = {"bytes": len(raw), "sha256": sg.sha(raw)}
        if args.compare:
            rows[name].update(compare_body((args.compare / target.name).read_bytes(), raw,
                (args.compare / "registration.json").read_bytes(), sg.canonical(reg)))
    (args.output / "manifest.json").write_bytes(sg.canonical(rows))
    print(json.dumps(rows, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
