"""Offline omission_inventory_v1 preparation and saved-response checks (#4260).

No provider, runtime, cache, record mutation or semantic certification. Execute
``python -m data_sheets_schema.audit_omissions --help`` for the offline interface.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from data_sheets_schema import evidence_assertions as evidence
from data_sheets_schema.duplicate_keys import nesting_exceeds
from data_sheets_schema.support_targets import _UniqueLoader, _validate_json, pointer_tokens

FORMAT = "omission_inventory_v1"
ASSETS = Path(__file__).with_name("omission_inventory_v1")
ASSET_SHA256 = {
    "context.schema.json": "4cb51a481905d272d24726dddd22ab91ed3e3ce1e6a23f37d50d2f1cefa9c2c8",
    "policy.md": "0b197cf8bafe1f3df53f3c23922e9e38d514cca42979b90282022b8bef4c0b0d",
    "response.schema.json": "90d9e0fcb50b391c9345b0150af2a43f7c3581673b89f35069a70f57046e6d07",
}
MAX_INPUT_BYTES = 8_000_000
MAX_SCHEMA_BYTES = 16_000_000
MAX_RESPONSE_BYTES = 8_000_000
MAX_NODES = 200_000
MAX_DEPTH = 64
LIMITATIONS = [
    "Scientific support, applicability, novelty and exhaustive recall are unverified.",
    "Chunk coverage and matching quotations are declaration/identity checks only.",
    "Full record schema validation is not performed; target structure is checked.",
    "No record, receipt, audit, runtime state or terminal outcome is changed.",
]


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _asset(name: str) -> bytes:
    raw = (ASSETS / name).read_bytes()
    if _sha(raw) != ASSET_SHA256[name]:
        raise ValueError(f"frozen omission policy/schema changed: {name}; use a new protocol version")
    return raw


def _read(raw: bytes, label: str, *, json_only: bool = False, limit: int = MAX_INPUT_BYTES):
    if type(raw) is not bytes or not raw or len(raw) > limit:
        raise ValueError(f"{label} must be nonempty bytes within the {limit}-byte bound")
    try:
        text = raw.decode("utf-8")
        if nesting_exceeds(text, yaml.SafeLoader, MAX_DEPTH):
            raise ValueError("depth bound exceeded")
        value = evidence.load_json(text) if json_only else yaml.load(text, Loader=_UniqueLoader)
        _validate_json(value, max_nodes=MAX_NODES, max_depth=MAX_DEPTH)
        return value
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, yaml.YAMLError) as exc:
        raise ValueError(f"{label} cannot be read safely ({type(exc).__name__})") from exc


def _mapping(raw, label, **kwargs):
    value = _read(raw, label, **kwargs)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _shape(value, schema):
    return list(Draft202012Validator(schema).iter_errors(value))


def _schema(path: Path) -> dict:
    """Capture and validate each file once before constructing a schema view."""
    from linkml_runtime.dumpers import json_dumper
    from data_sheets_schema.schema_snapshot import capture_schema
    from data_sheets_schema.schema_view import captured_view
    total = 0

    def read(selected):
        nonlocal total
        raw = _file(selected, MAX_INPUT_BYTES)
        total += len(raw)
        if total > MAX_SCHEMA_BYTES:
            raise ValueError("schema closure exceeds byte bound")
        _mapping(raw, "schema")
        return raw

    captured = capture_schema(path.absolute(), read_bytes=read, strict=True)
    with captured_view(captured) as view:
        if view.get_class("Dataset") is None:
            raise ValueError("selected schema has no Dataset class")
        classes, enums, pending = {}, {}, ["Dataset"]
        while pending:
            name = pending.pop()
            if name in classes:
                continue
            definition = json.loads(json_dumper.dumps(view.get_class(name)))
            slots = {}
            classes[name] = {"definition": {k: v for k, v in definition.items()
                            if k not in {"attributes", "slot_usage", "slots"}}, "slots": slots}
            pending.extend(str(p) for p in [definition.get("is_a"), *definition.get("mixins", [])] if p)
            for slot in view.class_induced_slots(name):
                raw = json.loads(json_dumper.dumps(slot))
                target = view.get_class(slot.range) if slot.range else None
                slots[str(slot.name)] = {"definition": raw, "inline": bool(target and view.is_inlined(slot)),
                                         "range_class": bool(target)}
                if target:
                    pending.append(str(slot.range))
                enum = view.get_enum(slot.range) if slot.range else None
                if enum:
                    enums[str(slot.range)] = json.loads(json_dumper.dumps(enum))
    return {"root_class": "Dataset", "classes": classes, "enums": enums,
            "sources": [{"name": name, "sha256": _sha(raw)} for name, _path, raw in captured.sources]}


def _class(catalog, name):
    """Do not guess through conditional or polymorphic schema constructs."""
    pending, seen = [name], set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        definition = catalog["classes"][current]["definition"]
        if any(definition.get(k) for k in ("rules", "any_of", "all_of", "exactly_one_of", "none_of")):
            raise ValueError("unsupported conditional class constraints")
        pending.extend(str(p) for p in [definition.get("is_a"), *definition.get("mixins", [])] if p)
    return catalog["classes"][name]


def _slot(catalog, name, field, vocabulary):
    slot = _class(catalog, name)["slots"].get(field)
    if slot is None:
        raise ValueError("undeclared slot in this owning class")
    definition = slot["definition"]
    if any(definition.get(k) for k in ("any_of", "all_of", "exactly_one_of", "none_of", "designates_type")):
        raise ValueError("unsupported slot constraints or type discriminator")
    if any(str(v) not in vocabulary for v in definition.get("values_from", [])):
        raise ValueError("missing explicitly supplied vocabulary")
    return slot


def _owners(document, catalog, vocabulary):
    owners = {}

    def walk(value, name, path, depth=0):
        if depth > MAX_DEPTH:
            raise ValueError("owner traversal depth exceeded")
        _class(catalog, name)
        owners[path] = name
        for field, item in value.items():
            slot = _slot(catalog, name, field, vocabulary)
            if item is None:
                continue
            definition = slot["definition"]
            many = bool(definition.get("multivalued"))
            if many != isinstance(item, list):
                raise ValueError(f"record cardinality prevents unambiguous owner traversal at {path!r}")
            pointer = path + "/" + field.replace("~", "~0").replace("/", "~1")
            members = [(x, pointer + f"/{i}") for i, x in enumerate(item)] if many else [(item, pointer)]
            for member, at in members:
                if slot["inline"]:
                    if not isinstance(member, dict):
                        raise ValueError("inline class member must be a mapping")
                    walk(member, definition["range"], at, depth + 1)
                elif isinstance(member, (dict, list)):
                    raise ValueError("scalar/reference slot contains an object")
    walk(document, "Dataset", "")
    return owners


def _target(target, payload):
    owner, chain = target["owner"], target["slot_chain"]
    pointer_tokens(owner)
    if owner not in payload["owner_classes"]:
        raise ValueError("target owner is not an existing typed mapping")
    if owner not in {s["owner"] for s in payload["context"]["scopes"]}:
        raise ValueError("target owner has no explicit scope context")
    name = payload["owner_classes"][owner]
    for i, field in enumerate(chain):
        slot = _slot(payload["schema"], name, field, payload["context"]["vocabulary"])
        if i < len(chain) - 1:
            if not slot["inline"]:
                raise ValueError("target chain traverses a scalar or non-inline reference")
            name = slot["definition"]["range"]
            if _dataset_range(payload["schema"], name):
                raise ValueError("nested Dataset needs its own existing owner and explicit scope")
    return True


def _dataset_range(catalog, name):
    """Dataset scope boundaries include inherited and mixed-in definitions."""
    pending, seen = [name], set()
    while pending:
        current = pending.pop()
        if current == "Dataset":
            return True
        if current in seen:
            continue
        seen.add(current)
        definition = catalog["classes"][current]["definition"]
        pending.extend(str(p) for p in [definition.get("is_a"), *definition.get("mixins", [])] if p)
    return False


@dataclass(frozen=True)
class Prepared:
    """Immutable captured request; returned mappings are private copies."""
    payload_json: str

    def request(self) -> dict:
        payload = json.loads(self.payload_json)
        return {"format": FORMAT, "request_sha256": _sha(self.payload_json.encode()),
                "payload": payload, "limitations": list(LIMITATIONS)}

    def check(self, response: bytes, *, saved_request: dict | None = None) -> dict:
        request = self.request()
        if saved_request is not None and _json(saved_request) != _json(request):
            raise ValueError("saved request differs from the recaptured inputs/contract/limits")
        payload = request["payload"]
        expected = {c["chunk"]: c for c in payload["chunks"]}
        problems, candidates = [], []
        seen, ids = set(), set()

        def problem(code, at, detail):
            problems.append({"code": code, "at": at, "detail": detail})

        try:
            parsed = _mapping(response, "response", json_only=True, limit=MAX_RESPONSE_BYTES)
        except ValueError:
            parsed = {}
            problem("response_parse", "", "Response is not a bounded strict JSON mapping")
        errors = _shape(parsed, payload["response_schema"])
        for error in errors:
            problem("response_shape", "/".join(map(str, error.absolute_path)), str(error.validator))
        if not errors:
            if parsed["request_sha256"] != request["request_sha256"]:
                problem("request_identity", "request_sha256", "Response names a different request")
            for index, row in enumerate(parsed["chunks"]):
                at = f"chunks/{index}"
                chunk = row["chunk"]
                if chunk not in expected or chunk in seen:
                    problem("chunk_coverage", at, "Unknown or duplicate chunk")
                seen.add(chunk)
                for number, candidate in enumerate(row["candidates"]):
                    here = f"{at}/candidates/{number}"
                    if candidate["id"] in ids:
                        problem("candidate_identity", here, "Duplicate candidate id")
                    ids.add(candidate["id"])
                    try:
                        _target(candidate["target"], payload)
                    except (ValueError, KeyError) as exc:
                        problem("target_schema", here, str(exc))
                    assertions = evidence.check_assertions([
                        {"source": candidate["source"], "chunk": chunk, "quote": candidate["quote"]}],
                        artifacts={}, chunks={k: {"source": v["source"], "text": v["text"]}
                                              for k, v in expected.items()})
                    for item in assertions:
                        problem(item["kind"], here, item["detail"])
                    candidates.append({"chunk": chunk, **candidate})
        missing = sorted(set(expected) - seen)
        if missing:
            problem("missing_chunks", "chunks", "Some canonical chunks have no valid-shaped row")
        complete = not problems
        return {"format": FORMAT, "request_sha256": request["request_sha256"],
                "response_sha256": _sha(response), "protocol_complete": complete,
                "scientific_support": "unverified", "novelty": "unverified", "exhaustive_recall": "unverified",
                "limitations": list(LIMITATIONS), "missing_chunks": missing,
                "counts": {"expected_chunks": len(expected), "declared_unique_chunks": len(seen) if not errors else None,
                           "declared_omission_chunks": sum(r["status"] == "omission" for r in parsed.get("chunks", [])) if not errors else None,
                           "declared_candidates": len(candidates) if not errors else None,
                           "prior_negative_chunks": sum(c["prior_receipt_status"] in {"nothing_relevant", "redundant_with"}
                                                        for c in expected.values())},
                "declared_candidates": candidates, "problem_count": len(problems),
                "problems": problems[:50], "problems_truncated": len(problems) > 50}


def prepare(*, record: bytes, bundle: bytes, manifest: bytes, receipt: bytes,
            context: bytes, schema_path: Path, max_output_tokens: int,
            max_request_bytes: int = 32_000_000) -> Prepared:
    """Read schema once, capture input bytes, render no transport-specific call."""
    if any(type(n) is not int or n < 1 for n in (max_output_tokens, max_request_bytes)):
        raise ValueError("request/output limits must be explicit positive integers")
    policy = _asset("policy.md").decode("utf-8")
    response_schema = json.loads(_asset("response.schema.json"))
    context_schema = json.loads(_asset("context.schema.json"))
    document = _mapping(record, "record")
    receipt_doc = _mapping(receipt, "receipt")
    _mapping(manifest, "manifest")
    context_doc = _mapping(context, "context", json_only=True)
    if _shape(context_doc, context_schema):
        raise ValueError("context does not satisfy omission_context_v1")
    if type(bundle) is not bytes or not bundle or len(bundle) > MAX_INPUT_BYTES:
        raise ValueError("bundle must be nonempty bytes within the input bound")
    try:
        chunks, _pins = evidence.source_chunks_from_bytes(bundle, manifest)
    except (ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
        raise ValueError("invalid canonical chunk manifest/bundle binding") from exc
    if not chunks or len(chunks) > response_schema["properties"]["chunks"]["maxItems"]:
        raise ValueError("canonical chunk count is outside the response contract")
    if receipt_doc.get("bundle_md5") != hashlib.md5(bundle).hexdigest():
        raise ValueError("receipt does not name the captured bundle")
    entries = receipt_doc.get("chunks")
    if not isinstance(entries, list):
        raise ValueError("receipt chunks must be a list")
    prior = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise ValueError("receipt entries must name chunks")
        key = entry["id"]
        if key not in chunks or key in prior:
            raise ValueError("receipt contains unknown or duplicate chunk ids")
        status = entry.get("status")
        if status not in {"extracted", "nothing_relevant", "redundant_with", "duplicate_of"}:
            raise ValueError("receipt contains an unknown chunk status")
        prior[key] = status
    try:
        catalog = _schema(Path(schema_path))
    except (KeyError, TypeError, AttributeError, RecursionError, yaml.YAMLError) as exc:
        raise ValueError("selected schema cannot be captured unambiguously") from exc
    owners = _owners(document, catalog, context_doc["vocabulary"])
    scopes = [s["owner"] for s in context_doc["scopes"]]
    if "" not in scopes or len(scopes) != len(set(scopes)) or any(s not in owners for s in scopes):
        raise ValueError("scopes must include root once and name distinct existing typed owners")
    payload = {"policy": policy, "response_schema": response_schema,
               "contract_sha256": dict(ASSET_SHA256), "context": context_doc,
               "record_yaml": record.decode("utf-8"), "receipt_yaml": receipt.decode("utf-8"),
               "schema": catalog, "owner_classes": owners,
               "chunks": [{"chunk": key, **value, "prior_receipt_status": prior.get(key, "unreviewed")}
                          for key, value in chunks.items()],
               "input_sha256": {k: _sha(v) for k, v in {"record": record, "bundle": bundle,
                                "manifest": manifest, "receipt": receipt, "context": context}.items()},
               "limits": {"max_output_tokens": max_output_tokens, "max_request_bytes": max_request_bytes,
                          "max_input_bytes": MAX_INPUT_BYTES, "max_response_bytes": MAX_RESPONSE_BYTES,
                          "max_schema_bytes": MAX_SCHEMA_BYTES, "max_nodes": MAX_NODES, "max_depth": MAX_DEPTH}}
    encoded = _json(payload)
    if len(_json(Prepared(encoded).request()).encode()) > max_request_bytes:
        raise ValueError("complete request exceeds max_request_bytes; no partial request returned")
    return Prepared(encoded)


def _file(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("input file exceeds byte bound")
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("record", "bundle", "manifest", "receipt", "context", "schema"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--max-output-tokens", type=int, required=True)
    parser.add_argument("--max-request-bytes", type=int, default=32_000_000)
    parser.add_argument("--response", type=Path)
    parser.add_argument("--request", type=Path, help="Saved request, required with --response")
    parser.add_argument("--output", type=Path, required=True, help="New file only; existing paths are refused")
    args = parser.parse_args()
    if bool(args.response) != bool(args.request):
        parser.error("--response and --request must be supplied together")
    try:
        prepared = prepare(**{n: _file(getattr(args, n), MAX_INPUT_BYTES) for n in
                               ("record", "bundle", "manifest", "receipt", "context")},
                           schema_path=args.schema, max_output_tokens=args.max_output_tokens,
                           max_request_bytes=args.max_request_bytes)
        result = prepared.check(_file(args.response, MAX_RESPONSE_BYTES),
                 saved_request=_mapping(_file(args.request, args.max_request_bytes), "saved request", json_only=True,
                                        limit=args.max_request_bytes)) if args.response else prepared.request()
        # O_EXCL refuses symlinks/hardlinks and existing destinations. No input
        # can be overwritten even if the output spelling differs from its path.
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(_json(result) + "\n")
    except (OSError, ValueError, TypeError, RecursionError, yaml.YAMLError) as exc:
        parser.exit(2, f"omission inventory refused: {exc}\n")
    if args.response and not result["protocol_complete"]:
        parser.exit(1)


if __name__ == "__main__":
    main()
