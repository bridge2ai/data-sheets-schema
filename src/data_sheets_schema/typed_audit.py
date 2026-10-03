"""Offline typed audit packets and independent saved-response checking (#4280).

No provider, execution registration, record repair or semantic certification.
Every operation derives its authorities from bounded captured bytes. A packet's
hash is a content identity, not an assertion of its author's trustworthiness.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path

import yaml

from . import audit_batches as batches, audit_batch_format as output_format
from . import audit_grammar, audit_omissions as omissions, audit_protocol
from . import evidence_assertions as evidence
from .schema_snapshot import SchemaSnapshot, capture_schema

PACKET = "typed_audit_packet_v1"
ASSEMBLY = "typed_audit_assembly_v1"
MAX_PACKET_BYTES = 96_000_000
MAX_ASSEMBLY_BYTES = 160_000_000
MAX_SCHEMA_FILES = 256
MAX_SAVED_RESPONSE_BYTES = 3_000_000
LIMITATIONS = [
    "Scientific support, applicability, novelty and exhaustive recall are unverified.",
    "Acceptance covers captured identities, declared coverage and literal source-evidence checks only.",
    "This offline packet does not register or execute a live audit or repair records.",
    "Input limits include the existing 4000000-byte original and 2097152-byte audit response bounds.",
]
_REQUIRED = {"original_full", "bundle", "manifest", "receipt", "context"}
_OPTIONAL = {"original_core", "source_manifest"}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(value):
    return batches.canonical_bytes(value)


def _exact(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"invalid {label} fields")


def _blob(raw, limit=omissions.MAX_INPUT_BYTES):
    if type(raw) is not bytes or not raw or len(raw) > limit:
        raise ValueError("captured input must be nonempty bytes within its bound")
    return {"sha256": _sha(raw), "bytes": len(raw), "base64": base64.b64encode(raw).decode("ascii")}


def _unblob(value, limit=omissions.MAX_INPUT_BYTES):
    _exact(value, {"sha256", "bytes", "base64"}, "captured byte blob")
    if (type(value["bytes"]) is not int or not 0 < value["bytes"] <= limit
            or type(value["base64"]) is not str or len(value["base64"]) > (limit + 2) // 3 * 4):
        raise ValueError("captured byte bound exceeded")
    try:
        raw = base64.b64decode(value["base64"], validate=True)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid captured base64") from exc
    if _blob(raw, limit) != value:
        raise ValueError("captured byte identity mismatch")
    return raw


def _seal(value):
    return {**value, "sha256": _sha(_json(value))}


def _bounded_json(raw, label, limit):
    return omissions._mapping(raw, label, json_only=True, limit=limit)


def _snapshot_rows(snapshot):
    # LinkML import names may be URIorCURIE subclasses. Their captured JSON
    # representation is a string; normalize before optional strict cache keys.
    return [{"name": str(name), "path": str(path), "content": _blob(raw)}
            for name, path, raw in snapshot.sources]


def _snapshot(rows):
    if type(rows) is not list or not 0 < len(rows) <= MAX_SCHEMA_FILES:
        raise ValueError("invalid schema closure roster")
    sources = []
    total = 0
    for row in rows:
        _exact(row, {"name", "path", "content"}, "schema source")
        if type(row["path"]) is not str or not row["path"]:
            raise ValueError("invalid logical schema path")
        raw = _unblob(row["content"])
        total += len(raw)
        if total > omissions.MAX_SCHEMA_BYTES:
            raise ValueError("schema closure exceeds byte bound")
        sources.append((row["name"], Path(row["path"]), raw))
    # captured_view does not use a shared cache. This key identifies exactly
    # these persisted bytes/paths; the omission API rederives import closure.
    return SchemaSnapshot(tuple(sources), (str(sources[0][1]), _sha(_json(rows))))


def _capture(path):
    total = 0

    def read(selected):
        nonlocal total
        raw = omissions._file(selected, omissions.MAX_INPUT_BYTES)
        total += len(raw)
        if total > omissions.MAX_SCHEMA_BYTES:
            raise ValueError("schema closure exceeds byte bound")
        omissions._mapping(raw, "schema")
        return raw

    snapshot = capture_schema(path.absolute(), read_bytes=read, strict=True)
    if len(snapshot.sources) > MAX_SCHEMA_FILES:
        raise ValueError("schema file count exceeds bound")
    return snapshot


def _source_authority(raw, project):
    """Bound YAML representation before the released provenance projection.

    Provenance permits exact integer priority-tier keys. The record-only loader
    would reject them. Count mapping keys and alias occurrences without expanding
    aliases into constructed values; projection retains its own duplicate, merge,
    finite-value and exact-typed authority rules.
    """
    from .source_metadata import _Loader, projection
    try:
        text = raw.decode("utf-8")
        if omissions.nesting_exceeds(text, _Loader, omissions.MAX_DEPTH):
            raise ValueError("source manifest depth bound exceeded")
        pending = [(yaml.compose(text, Loader=_Loader), 0, frozenset())]
        count = 0
        while pending:
            node, depth, ancestors = pending.pop()
            count += 1
            if count > omissions.MAX_NODES or depth > omissions.MAX_DEPTH:
                raise ValueError("source manifest node/depth bound exceeded")
            if id(node) in ancestors:
                raise ValueError("source manifest cannot contain cycles")
            if isinstance(node, yaml.MappingNode):
                children = [child for pair in node.value for child in pair]
            elif isinstance(node, yaml.SequenceNode):
                children = node.value
            else:
                continue
            if count + len(pending) + len(children) > omissions.MAX_NODES:
                raise ValueError("source manifest node bound exceeded")
            ancestors = ancestors | {id(node)}
            pending.extend((child, depth + 1, ancestors) for child in children)
        return projection(raw, project)
    except (yaml.YAMLError, RecursionError) as exc:
        raise ValueError("source manifest cannot be read safely") from exc



class DerivationCache:
    """Bounded, caller-owned pure packet derivations; never response verdicts.

    Each hit returns decoded private objects, including a NEW frozen Prepared.
    Final independent checks should receive a fresh instance, so their first
    derivation is independent of any earlier preparation or runtime cache.
    """
    def __init__(self, *, max_entries=8, max_bytes=64_000_000):
        if (type(max_entries) is not int or not 0 < max_entries <= 32
                or type(max_bytes) is not int or not 0 < max_bytes <= 128_000_000):
            raise ValueError('derivation cache requires bounded positive integer limits')
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self._rows, self._bytes = {}, 0

    def _derive(self, inputs, schema_rows, project, limits):
        def exact_json(value):
            if type(value) is dict:
                if any(type(key) is not str for key in value):
                    raise ValueError('derivation cache keys require exact string mapping keys')
                for item in value.values():
                    exact_json(item)
            elif type(value) is list:
                for item in value:
                    exact_json(item)
            elif type(value) not in (str, int, float, bool, type(None)):
                raise ValueError('derivation cache keys require exact JSON types')
        selected = [inputs, schema_rows, project, limits]
        exact_json(selected)
        # These bytes are checked on every lookup, not merely when cached.
        assets = {name: _sha(omissions._asset(name)) for name in omissions.ASSET_SHA256}
        identity = _json([selected, assets])
        key = (len(identity), _sha(identity))
        encoded = self._rows.get(key)
        if encoded is None:
            derived, raw, prepared = _derive(inputs, schema_rows, project, limits)
            encoded = _json({'derived': derived, 'raw': {name: _blob(value) for name, value in raw.items()},
                             'prepared_payload_json': prepared.payload_json})
            if len(encoded) <= self.max_bytes:
                while self._rows and (len(self._rows) >= self.max_entries or self._bytes + len(encoded) > self.max_bytes):
                    self._bytes -= len(self._rows.pop(next(iter(self._rows))))
                self._rows[key] = encoded
                self._bytes += len(encoded)
        value = json.loads(encoded)
        return value['derived'], {name: _unblob(blob) for name, blob in value['raw'].items()}, omissions.Prepared(value['prepared_payload_json'])


def _derive(inputs, schema_rows, project, limits, *, derivations=None):
    if derivations is not None:
        if type(derivations) is not DerivationCache:
            raise ValueError('derivations must be an explicit DerivationCache')
        return derivations._derive(inputs, schema_rows, project, limits)
    return _derive_uncached(inputs, schema_rows, project, limits)

def _derive_uncached(inputs, schema_rows, project, limits):
    if type(inputs) is not dict or not _REQUIRED <= set(inputs) <= _REQUIRED | _OPTIONAL:
        raise ValueError("captured input roster differs from protocol")
    raw = {key: _unblob(value) for key, value in inputs.items()}
    for key in ("original_full", "original_core"):
        if key in raw:
            omissions._mapping(raw[key], key)
    if ("source_manifest" in raw) != (project is not None):
        raise ValueError("source manifest and explicit project must be captured together")
    authority = None
    if "source_manifest" in raw:
        authority = _source_authority(raw["source_manifest"], project)
    _exact(limits, {"max_paths", "max_inventory_bytes", "max_workers", "max_output_tokens", "max_request_bytes"}, "limits")
    snapshot = _snapshot(schema_rows)
    prepared = omissions.prepare(record=raw["original_full"], bundle=raw["bundle"],
        manifest=raw["manifest"], receipt=raw["receipt"], context=raw["context"],
        schema_path=snapshot.sources[0][1], schema_snapshot=snapshot,
        max_output_tokens=limits["max_output_tokens"], max_request_bytes=limits["max_request_bytes"])
    plan = batches.make_plan(raw["original_full"].decode("utf-8"), version=2,
        **{k: limits[k] for k in ("max_paths", "max_inventory_bytes", "max_workers")})
    contracts = {stage: {"contract": output_format.contract(stage, version=2),
                         "rendered": output_format.render(stage, version=2),
                         "saved_response": {"kind": f"typed_audit_{stage}_response_v1",
                             "required_fields": ["kind", "packet_sha256", "request_sha256", "response",
                                                 "worker_id" if stage == "worker" else "typed_index_sha256"],
                             "response_encoding": "Exact UTF-8 inner JSON bytes as base64, sha256 and bytes.",
                             "authority": "A declared request/response association, not provider authentication."}}
                 for stage in ("worker", "integration")}
    shared = _json({"protocol": audit_protocol.select(audit_protocol.TYPED),
        "original_full": raw["original_full"].decode("utf-8"),
        "original_core": raw.get("original_core", b"").decode("utf-8") or None,
        "bundle": raw["bundle"].decode("utf-8"), "manifest": raw["manifest"].decode("utf-8"),
        "receipt": raw["receipt"].decode("utf-8"), "context": prepared.request()["payload"]["context"],
        "schema": prepared.request()["payload"]["schema"], "registered_provenance": authority}).decode("utf-8")
    workers = {worker["id"]: _json({"stage": "worker", "shared_context_sha256": _sha(shared.encode()),
        "plan_sha256": plan["sha256"], "assignment": worker, "inventory": plan["inventory"],
        "output_contract": contracts["worker"]}).decode("utf-8") for worker in plan["workers"]}
    for tail in workers.values():
        if len((shared + tail).encode()) > limits["max_request_bytes"]:
            raise ValueError("complete worker request exceeds max_request_bytes")
    return {"plan": plan, "omission_request": prepared.request(), "contracts": contracts,
            "requests": {"assembly_rule": "shared_context UTF-8 bytes followed by the selected stage UTF-8 bytes",
                         "shared_context": shared, "workers": workers},
            "registered_provenance": authority}, raw, prepared


def prepare(*, protocol, original_full, bundle, manifest, receipt, context, schema_path,
            max_output_tokens, original_core=None, source_manifest=None, project=None,
            max_request_bytes=32_000_000, max_paths=96, max_inventory_bytes=16384, max_workers=16,
            schema_snapshot=None, derivations=None):
    """Capture a new packet; no saved response or self-reported success is trusted."""
    if audit_protocol.select(protocol)["protocol"] != audit_protocol.TYPED:
        raise ValueError("this consumer requires explicitly selected typed_audit_protocol_v1")
    inputs = {key: _blob(value) for key, value in dict(original_full=original_full,
        bundle=bundle, manifest=manifest, receipt=receipt, context=context,
        original_core=original_core, source_manifest=source_manifest).items() if value is not None}
    if schema_snapshot is not None:
        # The omission constructor independently verifies exact transitive
        # closure/root identity from these bytes, with no ambient import reads.
        omissions._schema(Path(schema_path), schema_snapshot=schema_snapshot)
        rows = _snapshot_rows(schema_snapshot)
    else:
        rows = _snapshot_rows(_capture(Path(schema_path)))
    limits = dict(max_output_tokens=max_output_tokens, max_request_bytes=max_request_bytes,
                  max_paths=max_paths, max_inventory_bytes=max_inventory_bytes, max_workers=max_workers)
    derived, _, _ = _derive(inputs, rows, project, limits, derivations=derivations)
    packet = _seal(dict(kind=PACKET, protocol=audit_protocol.select(protocol), inputs=inputs,
        schema_sources=rows, project=project, limits=limits, **derived, limitations=list(LIMITATIONS)))
    _bounded_json(_json(packet), "packet", MAX_PACKET_BYTES)
    for worker in packet["plan"]["workers"]:
        worker_request(packet, worker["id"], derivations=derivations)
    return packet


def _open(packet, *, derivations=None):
    _exact(packet, {"kind", "protocol", "inputs", "schema_sources", "project", "limits", "plan",
        "omission_request", "contracts", "requests", "registered_provenance", "limitations", "sha256"}, "packet")
    if len(_json(packet)) > MAX_PACKET_BYTES or packet["kind"] != PACKET or _json(packet["protocol"]) != _json(audit_protocol.select(audit_protocol.TYPED)):
        raise ValueError("packet protocol/size mismatch")
    derived, raw, prepared = _derive(packet["inputs"], packet["schema_sources"], packet["project"], packet["limits"], derivations=derivations)
    expected = _seal({**{key: packet[key] for key in ("kind", "protocol", "inputs", "schema_sources", "project", "limits")},
                      **derived, "limitations": list(LIMITATIONS)})
    if _json(packet) != _json(expected):
        raise ValueError("packet request/plan/contract/input identity mismatch")
    return raw, prepared


def _omission_findings(findings, candidates=None):
    for finding in findings:
        if finding.get("kind") == "omission":
            refs = finding.get("omission_candidates")
            if finding["record"] != "full" or not refs:
                raise ValueError("every omission finding needs full-only captured candidate references")
            if candidates is not None and not set(refs) <= candidates:
                raise ValueError("finding references an unknown omission candidate")


def worker_request(packet, worker_id, *, derivations=None):
    """Export a request after packet sealing; identity hashes its exact payload."""
    _open(packet, derivations=derivations)
    if type(worker_id) is not str or worker_id not in packet["requests"]["workers"]:
        raise ValueError("unknown worker request")
    payload = {"packet_sha256": packet["sha256"], "worker_id": worker_id,
        "shared_context": packet["requests"]["shared_context"],
        "stage": packet["requests"]["workers"][worker_id]}
    request = {"kind": "typed_audit_worker_request_v1", "payload": payload,
               "request_sha256": _sha(_json(payload))}
    if len(_json(request)) > packet["limits"]["max_request_bytes"]:
        raise ValueError("complete worker request exceeds max_request_bytes")
    return request


def capture_response(request, response):
    """Declare saved bytes' association with an exported request, without authentication.

    Rewrapping old bytes is a new caller provenance claim. The consumer cannot
    establish that a provider read a request; it does reject unchanged prior
    envelopes against different packets or integration inputs.
    """
    if type(request) is not dict:
        raise ValueError("saved response requires an exported request")
    if request.get("kind") == "typed_audit_worker_request_v1":
        _exact(request, {"kind", "payload", "request_sha256"}, "worker request")
        payload = request["payload"]
        _exact(payload, {"packet_sha256", "worker_id", "shared_context", "stage"}, "worker payload")
        selected, identity = request, {"worker_id": payload["worker_id"]}
        stage = "worker"
    elif request.get("kind") == "typed_audit_index_v1":
        _exact(request, {"kind", "packet_sha256", "index", "omission_check", "integration_request", "sha256"}, "typed index")
        if request != _seal({key: value for key, value in request.items() if key != "sha256"}):
            raise ValueError("typed index identity mismatch")
        selected = request["integration_request"]
        _exact(selected, {"kind", "payload", "request_sha256"}, "integration request")
        if selected["kind"] != "typed_audit_integration_request_v1":
            raise ValueError("integration request kind mismatch")
        payload = selected["payload"]
        _exact(payload, {"stage", "packet_sha256", "shared_context", "proposal_index", "workers",
                         "omission_response", "omission_check", "output_contract"}, "integration payload")
        if payload["stage"] != "integration":
            raise ValueError("integration request stage mismatch")
        if payload.get("packet_sha256") != request["packet_sha256"]:
            raise ValueError("integration request packet mismatch")
        identity, stage = {"typed_index_sha256": request["sha256"]}, "integration"
    else:
        raise ValueError("unsupported exported request kind")
    if selected["request_sha256"] != _sha(_json(payload)):
        raise ValueError("exported request payload identity mismatch")
    return _json({"kind": f"typed_audit_{stage}_response_v1", "packet_sha256": payload["packet_sha256"],
                  "request_sha256": selected["request_sha256"], **identity,
                  "response": _blob(response, audit_grammar.MAX_BYTES)})


def _unwrap(saved, request):
    value = _bounded_json(saved, "saved response envelope", MAX_SAVED_RESPONSE_BYTES)
    raw = _unblob(value.get("response"), audit_grammar.MAX_BYTES)
    if _json(value) != capture_response(request, raw):
        raise ValueError("saved response envelope does not bind this exact packet/request/index")
    return raw


def _workers(packet, workers, *, derivations=None):
    if type(workers) is not dict:
        raise ValueError("saved workers must have an explicit id roster")
    return {key: _unwrap(raw, worker_request(packet, key, derivations=derivations)) for key, raw in workers.items()}


def check_worker(packet, worker_id, response, *, derivations=None):
    """Structural worker check; global omission/source acceptance occurs later."""
    raw = _unwrap(response, worker_request(packet, worker_id, derivations=derivations))
    report = batches.check_worker(raw, packet["plan"], worker_id, version=2)
    if report["passed"]:
        try:
            _omission_findings(audit_grammar._load(raw)["findings"])
        except ValueError as exc:
            report = {**report, "passed": False, "error_count": 1,
                      "errors": [{"code": "omission_reference_contract", "path": "/findings", "detail": str(exc)}]}
    return {"packet_sha256": packet["sha256"], "response_sha256": _sha(response),
            "inner_response_sha256": _sha(raw),
            "worker_id": worker_id, "grammar": report, "passed": report["passed"],
            "acceptance_scope": "worker structure only; source evidence and candidate membership not yet checked"}


def _index(packet, workers):
    index = batches.build_index(packet["plan"], workers, version=2)
    for response in workers.values():
        _omission_findings(audit_grammar._load(response)["findings"])
    return index


def index(packet, workers, omission_response, *, derivations=None):
    """Bind workers and complete omission response; render the integration tail."""
    _, prepared = _open(packet, derivations=derivations)
    report = prepared.check(omission_response, saved_request=packet["omission_request"])
    if not report["protocol_complete"]:
        raise ValueError("omission response does not satisfy complete captured inventory")
    inner_workers = _workers(packet, workers, derivations=derivations)
    result = _index(packet, inner_workers)
    candidates = {row["id"] for row in report["declared_candidates"]}
    for raw in inner_workers.values():
        _omission_findings(audit_grammar._load(raw)["findings"], candidates)
    payload = {"stage": "integration", "packet_sha256": packet["sha256"],
        "shared_context": packet["requests"]["shared_context"],
        "proposal_index": result, "workers": {key: raw.decode("utf-8") for key, raw in workers.items()},
        "omission_response": omission_response.decode("utf-8"), "omission_check": report,
        "output_contract": packet["contracts"]["integration"]}
    request = {"kind": "typed_audit_integration_request_v1", "payload": payload,
               "request_sha256": _sha(_json(payload))}
    result = _seal({"kind": "typed_audit_index_v1", "packet_sha256": packet["sha256"],
                   "index": result, "omission_check": report, "integration_request": request})
    if len(_json(result)) > packet["limits"]["max_request_bytes"]:
        raise ValueError("complete integration request exceeds max_request_bytes")
    return result


def _account(audit, delta, candidates):
    by_id = {candidate["id"]: candidate for candidate in candidates}
    decisions = {row["candidate_id"]: row for row in delta["omission_dispositions"]}
    if set(decisions) != set(by_id):
        raise ValueError("omission dispositions must cover the exact captured candidate roster")
    links = {}
    _omission_findings(audit["findings"], set(by_id))
    for ordinal, finding in enumerate(audit["findings"]):
        for identity in finding.get("omission_candidates", []):
            if identity in links or decisions[identity]["action"] != "retain":
                raise ValueError("omission candidate linked twice or linked after drop")
            links[identity] = ordinal
    if set(links) != {identity for identity, row in decisions.items() if row["action"] == "retain"}:
        raise ValueError("retained omission candidate has no final finding")
    return [{"candidate": row, "candidate_sha256": batches.object_sha256(row),
             "disposition": decisions[row["id"]], "disposition_sha256": batches.object_sha256(decisions[row["id"]]),
             "final_finding_ordinal": links.get(row["id"])} for row in candidates]


def _result(packet, workers, omission_response, integration_response, *, derivations=None):
    raw, _ = _open(packet, derivations=derivations)
    bound_index = index(packet, workers, omission_response, derivations=derivations)
    inner_integration = _unwrap(integration_response, bound_index)
    audit_raw, lineage = batches.assemble(packet["plan"], _workers(packet, workers, derivations=derivations), inner_integration, version=2)
    audit, delta = audit_grammar._load(audit_raw), audit_grammar._load(inner_integration)
    # Check candidates in replaced/dropped proposal entry paths too. The final
    # exact-once allocation is separate from proposal membership.
    candidate_rows = bound_index["omission_check"]["declared_candidates"]
    ids = {row["id"] for row in candidate_rows}
    for decision in delta["finding_decisions"]:
        _omission_findings(decision.get("findings", []), ids)
    _omission_findings(delta["new_findings"], ids)
    accounting = _account(audit, delta, candidate_rows)
    artifacts = {key: raw[key].decode("utf-8") for key in ("original_full", "original_core") if key in raw}
    chunks, _ = evidence.source_chunks_from_bytes(raw["bundle"], raw["manifest"])
    checked = evidence.check_audit(audit, artifacts=artifacts, chunks=chunks, protocol_version=7,
        source_manifest_raw=raw.get("source_manifest"), project=packet["project"])
    decision_problems = evidence.check_assertions(lineage["decision_assertions"], artifacts=artifacts, chunks=chunks)
    problems = checked["findings"] + decision_problems
    lineage = {**lineage, "packet_sha256": packet["sha256"], "typed_index_sha256": bound_index["sha256"],
        "omission_request_sha256": packet["omission_request"]["request_sha256"],
        "omission_response_sha256": _sha(omission_response), "omission_candidates": accounting,
        "integration_saved_response_sha256": _sha(integration_response),
        "input_sha256": {key: item["sha256"] for key, item in packet["inputs"].items()},
        "schema_sources_sha256": _sha(_json(packet["schema_sources"]))}
    counts = Counter(f.get("kind", "untyped") for f in audit["findings"])
    report = {"kind": "typed_audit_acceptance_v1", "protocol": packet["protocol"],
        "packet_sha256": packet["sha256"], "passed": not problems,
        "acceptance_scope": "captured identity, declaration coverage and literal source-evidence checks",
        "scientific_support": "unverified", "novelty": "unverified", "exhaustive_recall": "unverified",
        "finding_counts": {kind: counts[kind] for kind in sorted(audit_protocol.KINDS | {"untyped"})},
        "omission_counts": {**bound_index["omission_check"]["counts"],
            "retained": sum(row["disposition"]["action"] == "retain" for row in accounting),
            "dropped": sum(row["disposition"]["action"] == "drop" for row in accounting)},
        "source_review": {key: value for key, value in checked["source_review_original"].items() if key != "findings"},
        "revised_rows": sum(any(claim["verdict"] == "revise" for claim in row.get("claims", []))
                            for row in audit["source_review"]["values"]),
        "assertions_checked": checked["assertions_checked"] + len(lineage["decision_assertions"]),
        "problem_count": len(problems), "problems": problems[:50], "problems_truncated": len(problems) > 50,
        "limitations": list(LIMITATIONS)}
    return bound_index, audit_raw, lineage, report


def check_integration(packet, workers, omission_response, integration_response, *, derivations=None):
    """Run real terminal checks; malformed identity/coverage raises ValueError."""
    return _result(packet, workers, omission_response, integration_response, derivations=derivations)[3]


def assemble(packet, workers, omission_response, integration_response, *, derivations=None):
    """Seal a new self-contained assembly only when mechanical checks pass."""
    bound_index, audit_raw, lineage, report = _result(packet, workers, omission_response, integration_response, derivations=derivations)
    if not report["passed"]:
        raise ValueError("source-evidence acceptance failed; use check-integration for bounded diagnostics")
    result = _seal({"kind": ASSEMBLY, "packet": packet,
        "workers": {key: _blob(raw, MAX_SAVED_RESPONSE_BYTES) for key, raw in workers.items()},
        "omission_response": _blob(omission_response, omissions.MAX_RESPONSE_BYTES),
        "integration_response": _blob(integration_response, MAX_SAVED_RESPONSE_BYTES),
        "index": bound_index, "audit": _blob(audit_raw, audit_grammar.MAX_BYTES),
        "lineage": lineage, "acceptance": report})
    _bounded_json(_json(result), "assembly", MAX_ASSEMBLY_BYTES)
    return result


def check(assembly, *, derivations=None):
    """Rebuild independently from captured original/response bytes, not reports."""
    _exact(assembly, {"kind", "packet", "workers", "omission_response", "integration_response", "index",
                      "audit", "lineage", "acceptance", "sha256"}, "assembly")
    if assembly["kind"] != ASSEMBLY or type(assembly["workers"]) is not dict:
        raise ValueError("assembly kind or worker roster invalid")
    if len(_json(assembly)) > MAX_ASSEMBLY_BYTES:
        raise ValueError("assembly exceeds byte bound")
    expected = assemble(assembly["packet"], {key: _unblob(value, MAX_SAVED_RESPONSE_BYTES) for key, value in assembly["workers"].items()},
        _unblob(assembly["omission_response"], omissions.MAX_RESPONSE_BYTES),
        _unblob(assembly["integration_response"], MAX_SAVED_RESPONSE_BYTES), derivations=derivations)
    if _json(assembly) != _json(expected):
        raise ValueError("saved assembly differs from independent captured-byte reconstruction")
    return {**expected["acceptance"], "assembly_sha256": expected["sha256"], "independently_reconstructed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "request", "capture-response", "check-worker", "index", "check-integration", "assemble", "check"):
        sub = commands.add_parser(name)
        sub.add_argument("--output", required=True, type=Path, help="New file only; existing paths refused")
        if name == "prepare":
            sub.add_argument("--protocol", required=True, choices=[audit_protocol.TYPED])
            for field in ("original-full", "bundle", "manifest", "receipt", "context", "schema"):
                sub.add_argument(f"--{field}", required=True, type=Path)
            for field in ("original-core", "source-manifest"):
                sub.add_argument(f"--{field}", type=Path)
            sub.add_argument("--project")
            sub.add_argument("--max-output-tokens", required=True, type=int)
            for field, default in (("max-request-bytes", 32_000_000), ("max-paths", 96),
                                   ("max-inventory-bytes", 16384), ("max-workers", 16)):
                sub.add_argument(f"--{field}", type=int, default=default)
        elif name == "capture-response":
            sub.add_argument("--request", required=True, type=Path)
            sub.add_argument("--response", required=True, type=Path, help="Raw inner JSON; saved envelope captures these exact bytes")
        elif name == "check":
            sub.add_argument("--assembly", required=True, type=Path)
        else:
            sub.add_argument("--packet", required=True, type=Path)
            if name in {"request", "check-worker"}:
                sub.add_argument("--worker-id", required=True)
                if name == "check-worker":
                    sub.add_argument("--response", required=True, type=Path)
            else:
                sub.add_argument("--worker", required=True, action="append", help="ID=PATH; one per assigned worker")
                sub.add_argument("--omission-response", required=True, type=Path)
                if name in {"check-integration", "assemble"}:
                    sub.add_argument("--integration-response", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            supplied = {key: omissions._file(getattr(args, key), omissions.MAX_INPUT_BYTES)
                        for key in _REQUIRED | _OPTIONAL if getattr(args, key, None) is not None}
            result = prepare(protocol=args.protocol, schema_path=args.schema, project=args.project,
                **supplied, **{key: getattr(args, key) for key in ("max_output_tokens", "max_request_bytes",
                                                          "max_paths", "max_inventory_bytes", "max_workers")})
        elif args.command == "capture-response":
            result = _bounded_json(capture_response(
                _bounded_json(omissions._file(args.request, MAX_PACKET_BYTES), "exported request", MAX_PACKET_BYTES),
                omissions._file(args.response, audit_grammar.MAX_BYTES)), "saved response", MAX_SAVED_RESPONSE_BYTES)
        elif args.command == "check":
            result = check(_bounded_json(omissions._file(args.assembly, MAX_ASSEMBLY_BYTES), "assembly", MAX_ASSEMBLY_BYTES))
        else:
            packet = _bounded_json(omissions._file(args.packet, MAX_PACKET_BYTES), "packet", MAX_PACKET_BYTES)
            if args.command == "request":
                result = worker_request(packet, args.worker_id)
            elif args.command == "check-worker":
                result = check_worker(packet, args.worker_id, omissions._file(args.response, MAX_SAVED_RESPONSE_BYTES))
            else:
                workers = {}
                for item in args.worker:
                    key, separator, path = item.partition("=")
                    if not key or not separator or not path or key in workers:
                        raise ValueError("workers must have distinct ID=PATH declarations")
                    workers[key] = omissions._file(Path(path), MAX_SAVED_RESPONSE_BYTES)
                omission_raw = omissions._file(args.omission_response, omissions.MAX_RESPONSE_BYTES)
                if args.command == "index":
                    result = index(packet, workers, omission_raw)
                else:
                    integration = omissions._file(args.integration_response, MAX_SAVED_RESPONSE_BYTES)
                    result = (assemble if args.command == "assemble" else check_integration)(packet, workers, omission_raw, integration)
        # Exclusive creation refuses existing paths, symlinks (even dangling),
        # and hardlink aliases. No existing input/output is ever rewritten.
        with args.output.open("xb") as stream:
            stream.write(_json(result))
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(2, f"typed audit refused: {type(exc).__name__}: {exc}\n")
    if result.get("passed") is False:
        parser.exit(1)


if __name__ == "__main__":
    main()
