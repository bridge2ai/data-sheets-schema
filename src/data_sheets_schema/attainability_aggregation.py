"""Explicit source-item aggregation and captured reporting (#3046).

No route policy is installed by this module. Declared readings are not
scientific authentication; historical ratings and default reports are untouched.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
from dataclasses import dataclass, fields
from pathlib import Path

import jsonschema
import yaml
from referencing import Registry

from data_sheets_schema import attainability as at
from data_sheets_schema.evaluation_context import context_digest, normalize_context, unwrap_document
from data_sheets_schema.judge_contract import evaluation_contract
from data_sheets_schema.semantic_comparison import score_bases

MIB = 1_048_576
BASIS = "known_applicable_supported_points_v1"
STATUSES = frozenset(at.STATUSES)
SUPPORT = {"supported", "partly_supported"}
LIMITATIONS = (
    "Declared source readings and scope decisions are not authenticated scientific judgments.",
    "This supported-item basis does not change historical fixed or N/A-adjusted scores.",
    "Partial coverage is not a proven source ceiling or permission to rank unlike cohorts.",
)
SOURCE_PATHS = (
    "src/data_sheets_schema/attainability_aggregation.py",
    "src/data_sheets_schema/attainability.py",
    "src/data_sheets_schema/chunking.py",
    "src/data_sheets_schema/duplicate_keys.py",
    "src/data_sheets_schema/evaluation_context.py",
    "src/data_sheets_schema/judge_contract.py",
    "src/data_sheets_schema/semantic_comparison.py",
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path, raw):
    return {"path": str(path), "sha256": sha(raw), "bytes": len(raw)}


# Approved module imports establish the implementation identity once. Pure
# captured recheck never consults these source paths or an original input path.
_SOURCE_FILES = tuple((p, Path(__file__).parent / p.removeprefix("src/data_sheets_schema/"))
                      for p in SOURCE_PATHS)
_IMPLEMENTATION_RAW = tuple((p, actual.read_bytes()) for p, actual in _SOURCE_FILES)
_IMPLEMENTATION = tuple(pin(p, raw) for p, raw in _IMPLEMENTATION_RAW)

# An explicit Registry has no retrieval callback. jsonschema retains its
# packaged meta-schemas and the current in-memory schema resources, but cannot
# fall back to its default URL opener for any dialect's reference keywords.
_NO_RETRIEVAL = Registry()


def _output_validator(schema):
    validator = jsonschema.validators.validator_for(schema)
    meta = jsonschema.validators.validator_for(validator.META_SCHEMA, default=validator)
    # The same validators, format checker and SchemaError conversion used by
    # check_schema, with retrieval disabled at this boundary as well.
    for error in meta(validator.META_SCHEMA, format_checker=meta.FORMAT_CHECKER,
                      registry=_NO_RETRIEVAL).iter_errors(schema):
        raise jsonschema.SchemaError.create_from(error)
    return validator(schema, registry=_NO_RETRIEVAL)


@dataclass(frozen=True)
class Limits:
    rows: int = 256
    blobs: int = 2048
    references: int = 8192
    decoded_bytes: int = 256 * MIB
    encoded_bytes: int = 384 * MIB
    metadata_bytes: int = 16 * MIB
    selection_bytes: int = 8 * MIB
    bundle_bytes: int = 64 * MIB
    record_bytes: int = 16 * MIB
    document_bytes: int = 4 * MIB
    source_bytes: int = 8 * MIB
    depth: int = 64
    nodes: int = 1_000_000
    dependency_depth: int = 8
    policies: int = 32
    predecessors: int = 8
    entries: int = 4096
    routes: int = 32
    snippets: int = 128

    def __post_init__(self):
        for f in fields(self):
            value = getattr(self, f.name)
            if type(value) is not int or not 0 < value <= f.default:
                raise ValueError(f"invalid or increased aggregation limit: {f.name}")


DEFAULT_LIMITS = Limits()


def _object(value, keys, label):
    if type(value) is not dict or set(value) != set(keys.split()):
        raise ValueError(f"{label}: expected exactly {keys}")
    return value


def _string(value, label):
    if type(value) is not str or not value.strip() or "\0" in value:
        raise ValueError(f"{label}: expected a nonempty name without NUL")
    return value


def _digest(value, label):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{label}: expected SHA256")
    return value


def _pin(value, label="pin", bundle=False):
    _object(value, "path sha256 bytes" + (" md5" if bundle else ""), label)
    _string(value["path"], label + " path")
    _digest(value["sha256"], label)
    if type(value["bytes"]) is not int or value["bytes"] < 0:
        raise ValueError(f"{label}: invalid byte count")
    if bundle and (type(value["md5"]) is not str or len(value["md5"]) != 32 or
                   any(c not in "0123456789abcdef" for c in value["md5"])):
        raise ValueError(f"{label}: invalid MD5")
    return value


def _list(value, maximum, label):
    if type(value) is not list or len(value) > maximum:
        raise ValueError(f"{label}: expected a bounded list")
    return value


def _version(doc, name):
    if doc.get("format") != name or type(doc.get("version")) is not int or doc["version"] != 1:
        raise ValueError(f"expected {name} version 1")


def _json_depth(text, limit):
    depth = 0
    string = escaped = False
    for char in text:
        if string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                string = False
        elif char == '"':
            string = True
        elif char in "[{":
            depth += 1
            if depth > limit:
                raise ValueError("aggregation JSON depth limit exceeded")
        elif char in "]}":
            depth -= 1


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _tree(value, limits, *, yaml_keys=False):
    """Bound materialized JSON metadata before recursive encoding."""
    work = [(value, 1, False)]
    active = set()
    nodes = 0
    while work:
        obj, depth, leaving = work.pop()
        if leaving:
            active.remove(id(obj))
            continue
        nodes += 1
        if nodes > limits.nodes or depth > limits.depth:
            raise ValueError("aggregation metadata node/depth limit exceeded")
        if type(obj) in (dict, list):
            if id(obj) in active:
                raise ValueError("cyclic aggregation metadata")
            active.add(id(obj))
            work.append((obj, depth, True))
            if type(obj) is dict:
                # Existing rubric YAML uses integer scoring keys. Those raw
                # source mappings are inspected, never emitted as JSON metadata.
                if any(type(k) is not str and not (yaml_keys and type(k) is int) for k in obj):
                    raise ValueError("aggregation metadata keys must be strings")
                work.extend((v, depth + 1, False) for v in obj.values())
            else:
                work.extend((v, depth + 1, False) for v in obj)
        elif obj is not None and type(obj) not in (str, bool, int, float):
            raise ValueError("aggregation metadata must be JSON values")
        elif type(obj) is float and not math.isfinite(obj):
            raise ValueError("nonfinite aggregation metadata")
    return nodes


def canonical(value, limits=DEFAULT_LIMITS):
    _tree(value, limits)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _json(raw, limits, cap):
    if type(raw) is not bytes or len(raw) > cap:
        raise ValueError("aggregation JSON byte limit exceeded")
    text = raw.decode("utf-8")
    _json_depth(text, limits.depth)
    value = json.loads(text, object_pairs_hook=_pairs,
                       parse_constant=lambda v: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    _tree(value, limits)
    return value


def _yaml(raw, limits):
    from data_sheets_schema.duplicate_keys import find_duplicate_keys, describe
    text = raw.decode("utf-8")
    # Bound new opt-in YAML before recursive construction; the public v1
    # validator keeps its own unchanged parsing/error order.
    depth = nodes = 0
    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        nodes += 1
        if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
            depth += 1
        if depth > limits.depth or nodes > limits.nodes:
            raise ValueError("aggregation YAML node/depth limit exceeded")
        if isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
            depth -= 1
    duplicate = find_duplicate_keys(text)
    if duplicate:
        raise ValueError(describe(duplicate))
    value = yaml.safe_load(text)
    _tree(value, limits, yaml_keys=True)
    return value


def _decision(value):
    _object(value, "kind actor reference recorded_at rationale", "decision")
    if value["kind"] not in ("declared_curator", "declared_judge"):
        raise ValueError("decision is a declaration, not an approval flag")
    for key in ("actor", "reference", "recorded_at", "rationale"):
        _string(value[key], "decision " + key)


def _reason(code, detail):
    return {"code": code, "detail": detail}


class _Reader:
    """Fixed disk-capture or raw-closure reader; never an injected resolver."""
    def __init__(self, limits, *, root=None, blobs=None):
        self.limits, self.root = limits, root
        self.blobs = {} if blobs is None else blobs
        self.used, self.paths = set(), set()
        self.references = self.metadata_nodes = self.metadata_bytes = 0

    def cap(self, role):
        if role == "bundle":
            return self.limits.bundle_bytes
        if role in ("evaluation", "input"):
            return self.limits.record_bytes
        if role == "selection":
            return self.limits.selection_bytes
        return self.limits.document_bytes if role in (
            "document", "policy", "adjudication", "context", "rubric") else self.limits.source_bytes

    def raw(self, identity, role):
        _pin(identity, role, bundle=role == "bundle")
        self.references += 1
        if self.references > self.limits.references or identity["bytes"] > self.cap(role):
            raise ValueError("aggregation reference/role byte limit exceeded")
        digest = identity["sha256"]
        path = Path(identity["path"])
        if self.root is not None and not path.is_absolute():
            path = self.root / path
        self.paths.add(path)
        if self.root is not None:
            with path.open("rb") as stream:
                raw = stream.read(self.cap(role) + 1)
            if digest in self.blobs and self.blobs[digest] != raw:
                raise ValueError("conflicting captured bytes")
            self.blobs[digest] = raw
        else:
            if digest not in self.blobs:
                raise ValueError("captured closure is missing required bytes")
            raw = self.blobs[digest]
        if len(raw) != identity["bytes"] or sha(raw) != digest:
            raise ValueError(f"{role}: captured pin mismatch")
        if role == "bundle" and hashlib.md5(raw).hexdigest() != identity["md5"]:
            raise ValueError("bundle MD5 mismatch")
        self.used.add(digest)
        if len(self.used) > self.limits.blobs or sum(len(self.blobs[k]) for k in self.used) > self.limits.decoded_bytes:
            raise ValueError("aggregation captured blob budget exceeded")
        return raw

    def declared_rubric(self, identity):
        # v1 rubric identities contain no byte count. The actual captured raw
        # blob supplies length, while its original path and SHA remain exact.
        _object(identity, "path sha256", "v1 rubric")
        _string(identity["path"], "v1 rubric path"); _digest(identity["sha256"], "v1 rubric")
        if self.root is not None:
            p = Path(identity["path"])
            p = p if p.is_absolute() else self.root / p
            with p.open("rb") as stream:
                raw = stream.read(self.limits.document_bytes + 1)
            count = len(raw)
        else:
            raw = self.blobs.get(identity["sha256"])
            if raw is None:
                raise ValueError("captured closure is missing v1 rubric")
            count = len(raw)
        return self.raw({**identity, "bytes": count}, "rubric")

    def account(self, value):
        self.metadata_nodes += _tree(value, self.limits)
        self.metadata_bytes += len(canonical(value, self.limits))
        if self.metadata_nodes > self.limits.nodes or self.metadata_bytes > self.limits.metadata_bytes:
            raise ValueError("aggregation total metadata budget exceeded")
        return value

    def yaml(self, identity, role):
        return self.account(_yaml(self.raw(identity, role), self.limits))

    def json(self, identity, role):
        raw = self.raw(identity, role)
        value = _json(raw, self.limits, self.cap(role))
        return self.account(value)


def roster(rubric_raw, rubric, limits=DEFAULT_LIMITS):
    doc = _yaml(rubric_raw, limits)
    names = at.rubric_items(rubric_raw, rubric)
    result = []
    if rubric == "rubric10":
        entries = [(f"E{e['id']}.{n}", item, 1) for e in doc["d4d_complex_proxy_rubric"]["rubric"]
                   for n, item in enumerate(e["sub_elements"], 1)]
    elif rubric == "rubric20":
        entries = [(f"Q{i['id']}", i, 1 if i["score_type"] == "pass_fail" else 5)
                   for i in doc["d4d_evaluation_rubric"]["rubric"]]
    else:
        raise ValueError("unknown rubric")
    for key, item, maximum in entries:
        result.append({"item_id": key, "name": names[key], "maximum": maximum,
                       "applies_to": item.get("applies_to")})
    if len(names) != len(result) or not result or len(result) > 70:
        raise ValueError("duplicate or excessive rubric roster")
    return result


def roster_digest(rubric, identity, items):
    return sha(canonical({"rubric": rubric, "rubric_source": identity, "items": items}))


def _policy(reader, identity):
    p = reader.json(identity, "policy")
    _object(p, "format version state rubric rubric_source scoring_contract roster_sha256 items denominator_rule partial_interpretation decision", "policy")
    _version(p, "d4d-attainability-item-policy")
    if p["state"] not in ("draft", "declared") or p["denominator_rule"] != BASIS or p["partial_interpretation"] != "positive_lower_bound_not_explicit_absence_v1":
        raise ValueError("unsupported aggregation policy")
    if p["state"] == "draft":
        if p["decision"] is not None:
            raise ValueError("draft policy cannot carry a declaration")
    else:
        _decision(p["decision"])
    contract = p["scoring_contract"]
    _object(contract, "kind definition output_schema semantic_version evaluator_contract_sources", "scoring contract")
    if contract["kind"] != "semantic-agent":
        raise ValueError("unsupported scoring contract kind")
    _string(contract["semantic_version"], "semantic version")
    reader.raw(contract["definition"], "source")
    schema = reader.json(contract["output_schema"], "source")
    # Remote reference resolution is never an authority in captured recheck.
    stack = [schema]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for keyword in ("$ref", "$dynamicRef", "$recursiveRef"):
                if keyword in node and (type(node[keyword]) is not str or not node[keyword].startswith("#")):
                    raise ValueError("captured output schema requires local references")
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    deps = _list(contract["evaluator_contract_sources"], 64, "scoring sources")
    if len({d.get("path") for d in deps if isinstance(d, dict)}) != len(deps):
        raise ValueError("duplicate scoring source identity")
    for source in deps:
        reader.raw(source, "source")
    raw = reader.raw(p["rubric_source"], "rubric")
    items = roster(raw, p["rubric"], reader.limits)
    if p["roster_sha256"] != roster_digest(p["rubric"], p["rubric_source"], items):
        raise ValueError("policy roster digest mismatch")
    rules = _list(p["items"], len(items), "policy items")
    if len(rules) != len(items):
        raise ValueError("policy must contain the full pinned item roster")
    for expected, rule in zip(items, rules):
        _object(rule, "item_id maximum applies_to rule routes alternatives_complete justification", "policy item")
        if any(not at.identical(rule[k], expected[k]) for k in ("item_id", "maximum", "applies_to")):
            raise ValueError("policy item roster/maxima/applicability mismatch")
        _string(rule["justification"], "policy justification")
        routes = _list(rule["routes"], reader.limits.routes, "policy routes")
        if any(type(x) is not str or not x.strip() for x in routes) or len(set(routes)) != len(routes):
            raise ValueError("duplicate or invalid routes")
        if type(rule["alternatives_complete"]) is not bool:
            raise ValueError("route completeness must be boolean")
        if rule["rule"] == "whole_item_only":
            if routes or rule["alternatives_complete"]:
                raise ValueError("whole-item policy cannot declare alternatives")
        elif rule["rule"] != "any_sufficient" or not routes:
            raise ValueError("unsupported route rule")
    # This implementation can reconstruct this fixed scope/applicability
    # algorithm only. Retain another historical implementation, but do not
    # execute it or silently substitute today's contract for it.
    known = dict(_IMPLEMENTATION_RAW)
    required = ("src/data_sheets_schema/evaluation_context.py",
                "src/data_sheets_schema/judge_contract.py")
    source_ids = {d["path"]: d["sha256"] for d in deps}
    supported = contract["semantic_version"] == "3.0" and all(
        source_ids.get(path) == sha(known[path]) for path in required)
    return p, items, raw, schema, supported


def _source_document(reader, identity, bundle):
    raw = reader.raw(identity, "document")
    # Decode only to capture the explicitly declared artifacts. All v1 semantic
    # validation remains in the single shared validator, never copied here.
    doc = reader.account(_yaml(raw, reader.limits))
    if type(doc) is not dict or not at.identical(doc.get("bundle"), bundle):
        raise ValueError("source document bundle mismatch")
    entries = _list(doc.get("entries"), reader.limits.entries, "source entries")
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("evidence"), dict):
            _list(entry["evidence"].get("snippets"), reader.limits.snippets, "source snippets")
    rb = doc.get("rubrics")
    if type(rb) is not dict:
        raise ValueError("source document rubrics must be an object")
    sources = [(bundle["path"], reader.raw(bundle, "bundle"))]
    for declared in rb.values():
        sources.append((declared["path"], reader.declared_rubric(declared)))
    problems, checked = at._validate_captured_text(raw.decode("utf-8"),
        captured=at._CapturedAttainabilityBytes(tuple(sources)))
    if problems or checked is None:
        raise ValueError("invalid captured v1 attainability: " + "; ".join(problems))
    return checked


def entry_ref(document_sha, entry):
    return {"document_sha256": document_sha, "rubric": entry["rubric"], "item_id": entry["item_id"],
            "route": entry["route"], "entry_sha256": sha(canonical({
                "format": "d4d-attainability-entry-identity", "version": 1, "entry": entry}))}


def _ref_order(r):
    return (r["document_sha256"], r["rubric"], r["item_id"], r["route"] is not None, r["route"] or "")


def _adjudications(reader, row, policy, checked, roster_ids):
    if row["adjudication"] is None:
        return {}, []
    a = reader.json(row["adjudication"], "adjudication")
    _object(a, "format version policy source_document predecessor_documents bundle rubric chunk_rule_sha256 resolutions", "adjudication")
    _version(a, "d4d-attainability-adjudication")
    for key, expected in (("policy", row["policy"]), ("source_document", row["source_document"]),
                          ("bundle", row["bundle"]), ("rubric", policy["rubric_source"])):
        if not at.identical(a[key], expected):
            raise ValueError("adjudication identity mismatch: " + key)
    if a["chunk_rule_sha256"] != sha(canonical(checked.document["chunk_rule"])):
        raise ValueError("adjudication chunk rule mismatch")
    prior = _list(a["predecessor_documents"], reader.limits.predecessors, "predecessors")
    if len({p.get("sha256") for p in prior if type(p) is dict}) != len(prior):
        raise ValueError("duplicate predecessor document")
    documents = [(row["source_document"]["sha256"], checked)]
    for p in prior:
        if p["sha256"] == row["source_document"]["sha256"]:
            raise ValueError("current document is not its own predecessor")
        before = _source_document(reader, p, row["bundle"])
        if not at.identical(before.document["chunk_rule"], checked.document["chunk_rule"]) or not at.identical(before.document["rubrics"], checked.document["rubrics"]):
            raise ValueError("predecessor rubric/chunk identities differ")
        documents.append((p["sha256"], before))
    _, lines = at._lines_by_chunk(reader.raw(row["bundle"], "bundle").decode("utf-8"), checked.document["chunk_rule"])
    chunks = {}
    for n, (chunk, _) in lines.items():
        chunks.setdefault(chunk, [n, n])[1] = n
    resolutions = {}
    for resolution in _list(a["resolutions"], len(roster_ids), "resolutions"):
        _object(resolution, "item_id route scope_entries scope_sha256 resolved_status evidence decision", "resolution")
        key = resolution["item_id"]
        if key not in roster_ids or key in resolutions or resolution["route"] is not None:
            raise ValueError("unknown/duplicate/non-whole-item adjudication")
        expected = sorted([entry_ref(h, e) for h, d in documents for e in d.document["entries"]
                           if e["rubric"] == policy["rubric"] and e["item_id"] == key], key=_ref_order)
        if not at.identical(resolution["scope_entries"], expected) or resolution["scope_sha256"] != sha(canonical(expected)):
            raise ValueError("adjudication scoped entries changed or incomplete")
        if resolution["resolved_status"] not in STATUSES:
            raise ValueError("invalid adjudicated support status")
        _decision(resolution["decision"])
        evidence = _list(resolution["evidence"], reader.limits.snippets, "resolution snippets")
        if resolution["resolved_status"] in SUPPORT and not evidence:
            raise ValueError("supported adjudication requires source evidence")
        for snip in evidence:
            problems = at._snippet_problems(snip, lines, chunks)
            if problems:
                raise ValueError("adjudication evidence: " + "; ".join(problems))
        resolutions[key] = resolution
    return resolutions, documents[1:]


def combine(whole, routes):
    if (whole == "not_stated_in_source" and routes in SUPPORT) or (routes == "not_stated_in_source" and whole in SUPPORT):
        return "conflict"
    for state in ("supported", "partly_supported", "not_stated_in_source"):
        if state in (whole, routes):
            return state
    return "unknown"


def _item_support(entries, rule, declared, resolution):
    whole = next((e["status"] for e in entries if e["route"] is None), "unknown")
    named = {e["route"]: e["status"] for e in entries if e["route"] is not None}
    unknown = sorted(set(named) - set(rule["routes"]))
    reasons = []
    route_state = "unknown"
    state = "none"
    if not declared:
        initial = final = "unknown"; state = "policy_unavailable"
        reasons.append(_reason("draft_policy", "No declared route/item policy selected"))
    elif unknown:
        initial = final = "unknown"; state = "unregistered_routes"
        reasons.append(_reason("unregistered_route", "Unregistered item-wide routes: " + ", ".join(unknown)))
    else:
        values = list(named.values())
        if "supported" in values:
            route_state = "supported"
        elif "partly_supported" in values:
            route_state = "partly_supported"
        elif rule["routes"] and rule["alternatives_complete"] and all(named.get(r) == "not_stated_in_source" for r in rule["routes"]):
            route_state = "not_stated_in_source"
        elif rule["routes"]:
            code = "route_missing" if set(rule["routes"]) - set(named) else "route_unknown" if "unknown" in values else "incomplete_alternatives"
            reasons.append(_reason(code, "Registered alternatives do not establish absence"))
        if not entries:
            reasons.append(_reason("missing_source_entry", "No source reading for this item"))
        initial = final = combine(whole, route_state)
        if initial == "conflict":
            state = "conflict"
        if resolution is not None:
            final = resolution["resolved_status"]; state = "adjudicated"
    return whole, route_state, initial, final, state, reasons


def _evaluation_items(doc, rubric, expected):
    rows = []
    if rubric == "rubric10":
        for group in doc.get("elements", []):
            for pos, item in enumerate(group.get("sub_elements", []), 1):
                key = f"E{group['id']}.{pos}"
                if item.get("item_id", key) != key:
                    raise ValueError("evaluation item position/identity mismatch")
                rows.append((key, item))
    else:
        categories = doc.get("categories", [])
        if isinstance(categories, dict):
            categories = list(categories.values())
        for item in [q for c in categories for q in c.get("questions", [])] + doc.get("questions", []):
            rows.append((f"Q{item['id']}", item))
    if {k for k, _ in rows} - set(expected) or len({k for k, _ in rows}) != len(rows):
        raise ValueError("evaluation contains unknown or duplicate item identities")
    return dict(rows)


def _row(reader, row):
    _object(row, "evaluation evaluated_input generation_provenance bundle source_document policy adjudication context scope_binding", "selection row")
    p, roster_items, rubric_raw, schema, supported_contract = _policy(reader, row["policy"])
    checked = _source_document(reader, row["source_document"], row["bundle"])
    if checked.document["rubrics"].get(p["rubric"]) != {k: p["rubric_source"][k] for k in ("path", "sha256")}:
        raise ValueError("policy/source rubric mismatch")
    doc = reader.json(row["evaluation"], "evaluation")
    input_raw = reader.raw(row["evaluated_input"], "input")
    provenance = reader.yaml(row["generation_provenance"], "source")
    if type(doc) is not dict or type(provenance) is not dict:
        raise ValueError("evaluation/provenance must be objects")
    unavailable = ([_reason("draft_policy", "Policy has no selected declaration")]
                   if p["state"] == "draft" else [])
    inputs = provenance.get("inputs") or {}
    if type(inputs) is not dict:
        raise ValueError("provenance inputs must be an object")
    for key, expected in (("bundle_path", row["bundle"]["path"]),
                          ("bundle_md5", row["bundle"]["md5"])):
        if inputs.get(key) is None:
            unavailable.append(_reason("identity_unrecorded", "Generation provenance does not record inputs." + key))
        elif inputs[key] != expected:
            raise ValueError("generation provenance does not bind the selected source bundle")
    if inputs.get("bundle_sha256") not in (None, row["bundle"]["sha256"]):
        raise ValueError("generation provenance bundle SHA mismatch")
    # Current generation outputs are descriptions, not hash authority. Its
    # post-run validation.artifacts owns integrity; older pinned outputs are
    # retained too. Check every recorded hash, never create one from a path.
    output_hash = False
    for section in (provenance.get("outputs"),
                    (provenance.get("validation") or {}).get("artifacts")):
        if section is None:
            continue
        if type(section) is not dict:
            raise ValueError("provenance artifacts must be an object")
        full = section.get("full")
        if full is None:
            continue
        if type(full) is not dict:
            raise ValueError("provenance full artifact must be an object")
        for algorithm in ("sha256", "md5"):
            value = full.get(algorithm)
            if value is not None:
                if value != hashlib.new(algorithm, input_raw).hexdigest():
                    raise ValueError("generation provenance evaluated input hash mismatch")
                output_hash = True
    if not output_hash:
        unavailable.append(_reason("identity_unrecorded", "Generation provenance has no evaluated-input hash"))
    raw_context = None if row["context"] is None else reader.yaml(row["context"], "context")
    context = normalize_context(raw_context) if supported_contract else raw_context
    context_identity = context_digest(context) if supported_contract else None
    contract = (evaluation_contract(p["rubric"], _yaml(rubric_raw, reader.limits), context,
                                   unwrap_document(_yaml(input_raw, reader.limits))) if supported_contract else None)
    if contract is None:
        unavailable.append(_reason("unsupported_historical_contract", "Captured scope/applicability implementation is not supported"))
    scope = row["scope_binding"]
    scope_hash = None
    if scope is not None:
        _object(scope, "evaluation_scope_sha256 declaration decision", "scope binding")
        _digest(scope["evaluation_scope_sha256"], "scope digest")
        if scope["declaration"] != "source_readings_cover_selected_subject_scope":
            raise ValueError("source scope coverage must be explicitly declared")
        _decision(scope["decision"])
    if scope is None or doc.get("evaluation_scope") is None or contract is None:
        unavailable.append(_reason("scope_unknown", "Original source/evaluation subject scope cannot be established"))
    else:
        scope_hash = sha(canonical(contract["scope"]))
        if scope["evaluation_scope_sha256"] != scope_hash or not at.identical(doc["evaluation_scope"], contract["scope"]):
            raise ValueError("evaluation/source scope identity mismatch")
    metadata = doc.get("metadata", {})
    if type(metadata) is not dict:
        raise ValueError("evaluation metadata must be an object")
    for key, expected in (("input_sha256", row["evaluated_input"]["sha256"]),
                          ("rubric_sha256", p["rubric_source"]["sha256"]),
                          ("instrument_sha256", p["scoring_contract"]["definition"]["sha256"])) + (
                          (("context_sha256", context_identity),) if supported_contract else ()):
        if metadata.get(key) is None:
            unavailable.append(_reason("identity_unrecorded", "Evaluation does not record " + key))
        elif metadata[key] != expected:
            raise ValueError("mismatched evaluation identity: " + key)
    if doc.get("rubric") != p["rubric"] + "-semantic":
        raise ValueError("evaluation rubric does not match policy")
    if doc.get("version") is None:
        unavailable.append(_reason("identity_unrecorded", "Evaluation does not record its contract version"))
    elif doc["version"] != p["scoring_contract"]["semantic_version"]:
        raise ValueError("evaluation contract version mismatch")
    if "applicability_context" not in doc:
        unavailable.append(_reason("identity_unrecorded", "Evaluation does not record its applicability context"))
    elif supported_contract and not at.identical(doc["applicability_context"], context):
        raise ValueError("evaluation context mismatch")
    keys = [i["item_id"] for i in roster_items]
    items = _evaluation_items(doc, p["rubric"], keys)
    if set(items) != set(keys):
        unavailable.append(_reason("evaluation_unusable", "Evaluation lacks the complete recorded item roster"))
    # A missing eligible score makes the whole third basis unavailable, not a
    # smaller denominator. Historical totals remain the recorded measurement.
    for key, assessment in items.items():
        if contract is not None and contract["items"][key]["applicable"] and assessment.get("score") is None:
            unavailable.append(_reason("score_missing", "No recorded applicable item score: " + key))
        if "applicable" not in assessment or "applicability_status" not in assessment:
            unavailable.append(_reason("identity_unrecorded", "Missing original item applicability: " + key))
    validator = _output_validator(schema)
    if not unavailable:
        validator.validate(doc)
    resolutions, prior = _adjudications(reader, row, p, checked, keys)
    result_items, excluded, eligible, findings = [], [], [], []
    attained = 0
    for declared, rule in zip(roster_items, p["items"]):
        key = declared["item_id"]; assessment = items.get(key, {})
        applicable = (contract["items"][key] if contract is not None else
            {"applicable": True, "status": "unknown", "evidence": "Historical applicability implementation unavailable"})
        if contract is not None and (("applicable" in assessment and assessment["applicable"] is not applicable["applicable"])
                or ("applicability_status" in assessment and assessment["applicability_status"] != applicable["status"])):
            raise ValueError("item applicability contradicts independent context: " + key)
        score = assessment.get("score")
        if score is not None and (type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= declared["maximum"]):
            raise ValueError("item score is not a valid recorded number: " + key)
        if contract is not None and not applicable["applicable"] and score is not None:
            raise ValueError("non-null inapplicable item score: " + key)
        if "max_score" in assessment and not at.identical(assessment["max_score"], declared["maximum"]):
            raise ValueError("evaluation item maximum disagrees with pinned rubric: " + key)
        entries = [e for e in checked.document["entries"] if e["rubric"] == p["rubric"] and e["item_id"] == key]
        resolution = resolutions.get(key)
        whole, routes, initial, final, state, reasons = _item_support(entries, rule, p["state"] == "declared", resolution)
        refs = sorted([entry_ref(row["source_document"]["sha256"], e) for e in entries], key=_ref_order)
        exclude = []
        if applicable["status"] != "applicable":
            exclude.append(_reason("not_applicable" if applicable["status"] == "not_applicable" else "applicability_unknown", applicable["evidence"]))
        if final != "supported":
            exclude.append(_reason({"partly_supported": "partly_supported", "not_stated_in_source": "source_absent", "unknown": "source_unknown", "conflict": "source_conflict"}[final], "Source item status is " + final))
        if unavailable:
            exclude.extend(unavailable)
        is_eligible = not exclude
        if is_eligible:
            eligible.append(key); attained += score
        else:
            excluded.append({"item_id": key, "reasons": exclude + reasons})
        if not unavailable and final == "not_stated_in_source" and score is not None and score > 0:
            findings.append({"item_id": key, "score": score, "applicability": applicable["status"], "entry_refs": refs})
        result_items.append({"item_id": key, "maximum": declared["maximum"], "input_entries": refs,
            "route_status": routes, "whole_status": whole, "initial_status": initial, "final_status": final,
            "resolution_state": state, "resolution_sha256": sha(canonical(resolution)) if resolution is not None else None,
            "predecessor_evidence": "retained" if prior else "unavailable" if any(e["method"] == "curator" for e in entries) else "not_claimed",
            "applicability": applicable["status"], "applicability_evidence": applicable["evidence"],
            "recorded_score": score, "eligible": is_eligible, "reasons": reasons + exclude})
    maximum = sum(i["maximum"] for i in roster_items)
    historical = score_bases(doc, maximum)
    numeric_total = sum(i["recorded_score"] or 0 for i in result_items)
    adjusted = sum(i["maximum"] for i in result_items if i["applicability"] != "not_applicable")
    if not unavailable and (historical.total != numeric_total or historical.fixed_max != maximum or historical.adjusted_max != adjusted):
        raise ValueError("historical score bases disagree with recorded full item roster")
    cap = sum(i["maximum"] for i in result_items if i["eligible"])
    reasons = list(unavailable) if unavailable else [] if eligible else [_reason("zero_eligible_items", "No known-applicable supported item maximum")]
    unresolved = any(i["final_status"] in ("unknown", "conflict", "partly_supported") or i["applicability"] == "unknown" for i in result_items)
    signature = {"rubric": p["rubric_source"], "contract": p["scoring_contract"], "policy": row["policy"],
                 "bundle": row["bundle"], "scope": scope_hash, "context": context_identity,
                 "eligible": [[i["item_id"], i["maximum"]] for i in result_items if i["eligible"]]}
    return {"evaluation": row["evaluation"], "input": row["evaluated_input"], "provenance": row["generation_provenance"],
        "bundle": row["bundle"], "document": row["source_document"], "policy": row["policy"],
        "adjudication": row["adjudication"], "context": row["context"], "instrument": p["scoring_contract"],
        "scope_sha256": scope_hash, "state": "unavailable" if not eligible else "partial_coverage" if unresolved else "available",
        "reasons": reasons, "historical_bases": {"total": historical.total, "fixed_max": historical.fixed_max,
            "adjusted_max": historical.adjusted_max, "fixed_percentage": historical.fixed_percentage,
            "adjusted_percentage": historical.adjusted_percentage},
        "source_inventory": result_items,
        "basis": {"rule": BASIS, "eligible_item_ids": eligible, "excluded": excluded, "full_maximum": maximum,
            "attained": attained if eligible else None, "attainable": None if unavailable else cap, "percentage": 100 * attained / cap if cap else None,
            "eligible_signature_sha256": sha(canonical(signature))},
        "absent_positive_scores": findings, "reading_authentication": "not_verified",
        "scientific_validation": "not_established_by_aggregation"}


def _derive(reader, selection_pin):
    # Closed protocol dependency paths have four levels at most: selection ->
    # adjudication -> predecessor -> rubric. No recursive user-defined links.
    if reader.limits.dependency_depth < 4:
        raise ValueError("aggregation dependency depth limit exceeded")
    selection = reader.json(selection_pin, "selection")
    _object(selection, "format version rows", "selection")
    _version(selection, "d4d-attainability-report-selection")
    rows = _list(selection["rows"], reader.limits.rows, "selected evaluations")
    if not rows:
        raise ValueError("select at least one evaluation")
    hashes = [r.get("evaluation", {}).get("sha256") for r in rows if isinstance(r, dict)]
    if len(hashes) != len(rows) or len(set(hashes)) != len(rows):
        raise ValueError("duplicate or malformed selected evaluation")
    policies = {r.get("policy", {}).get("sha256") for r in rows}
    if len(policies) > reader.limits.policies:
        raise ValueError("policy count limit exceeded")
    result = {"format": "d4d-attainability-report", "version": 1, "selection": selection_pin,
            "implementation": [dict(p) for p in _IMPLEMENTATION], "limitations": list(LIMITATIONS),
            "rows": [_row(reader, r) for r in rows]}
    # Charge every derived field, including repeated route/reason/entry text,
    # to the same aggregate metadata budget as the parsed inputs. Both initial
    # capture and pure recheck enter here before returning a successful result.
    return reader.account(result)


def capture(selection_path, *, limits=DEFAULT_LIMITS):
    """Read an explicit selection once into a complete retained raw closure."""
    if type(limits) is not Limits:
        raise TypeError("expected fixed aggregation Limits")
    path = Path(selection_path).absolute()
    with path.open("rb") as stream:
        raw = stream.read(limits.selection_bytes + 1)
    if len(raw) > limits.selection_bytes:
        raise ValueError("selection byte limit exceeded")
    selected = pin(str(path), raw)
    reader = _Reader(limits, root=path.parent)
    reader.blobs[selected["sha256"]] = raw
    _derive(reader, selected)
    for identity, (_, source) in zip(_IMPLEMENTATION, _IMPLEMENTATION_RAW):
        reader.blobs[identity["sha256"]] = source
        reader.used.add(identity["sha256"])
    if len(reader.used) > limits.blobs or sum(len(reader.blobs[k]) for k in reader.used) > limits.decoded_bytes:
        raise ValueError("captured closure including implementation exceeds budget")
    closure = {"format": "d4d-attainability-capture", "version": 1, "selection": selected,
        "implementation": [dict(p) for p in _IMPLEMENTATION], "blobs": [
            {"sha256": h, "bytes": len(reader.blobs[h]), "content_base64": base64.b64encode(reader.blobs[h]).decode("ascii")}
            for h in sorted(reader.used)]}
    if len(canonical(closure, limits)) > limits.encoded_bytes:
        raise ValueError("encoded capture limit exceeded")
    return closure


def recheck_captured(closure, *, limits=DEFAULT_LIMITS):
    """Pure replay: no original paths, current files, Git, network or scoring."""
    if type(limits) is not Limits:
        raise TypeError("expected fixed aggregation Limits")
    if type(closure) is bytes:
        closure = _json(closure, limits, limits.encoded_bytes)
    _object(closure, "format version selection implementation blobs", "captured closure")
    _version(closure, "d4d-attainability-capture")
    if not at.identical(closure["implementation"], list(_IMPLEMENTATION)):
        raise ValueError("captured implementation identity differs")
    if len(canonical(closure, limits)) > limits.encoded_bytes:
        raise ValueError("encoded capture limit exceeded")
    blobs, size = {}, 0
    for entry in _list(closure["blobs"], limits.blobs, "captured blobs"):
        _object(entry, "sha256 bytes content_base64", "captured blob")
        _digest(entry["sha256"], "blob")
        if type(entry["bytes"]) is not int or not 0 <= entry["bytes"] <= limits.bundle_bytes:
            raise ValueError("captured blob byte limit exceeded")
        text = entry["content_base64"]
        if type(text) is not str or len(text) != 4 * ((entry["bytes"] + 2) // 3):
            raise ValueError("captured encoded length mismatch")
        raw = base64.b64decode(text, validate=True)
        if len(raw) != entry["bytes"] or sha(raw) != entry["sha256"] or entry["sha256"] in blobs:
            raise ValueError("captured blob mismatch or duplicate")
        blobs[entry["sha256"]] = raw; size += len(raw)
        if size > limits.decoded_bytes:
            raise ValueError("captured decoded byte limit exceeded")
    reader = _Reader(limits, blobs=blobs)
    result = _derive(reader, closure["selection"])
    for identity, (_, expected) in zip(_IMPLEMENTATION, _IMPLEMENTATION_RAW):
        if reader.raw(identity, "source") != expected:
            raise ValueError("captured implementation bytes differ")
    if reader.used != set(blobs):
        raise ValueError("captured closure contains unrelated blobs")
    _tree(result, limits)
    return result


def prepare_report(selection_path, evaluations):
    """Bind a capture to the actual report's already-read evaluation bytes."""
    closure = capture(selection_path)
    result = recheck_captured(closure)
    prepared = {"capture": closure, "report": result}
    bind_report(prepared, evaluations)
    return prepared


def bind_report(prepared, evaluations):
    result = recheck_captured(prepared["capture"])
    if not at.identical(result, prepared["report"]):
        raise ValueError("attainability report differs from captured derivation")
    by_digest = {}
    for path, raw in evaluations:
        digest = sha(raw)
        if digest in by_digest:
            # The same evaluation may occur under several arm labels; it is
            # one input only when both its original path and bytes agree.
            if by_digest[digest] != (Path(path).absolute(), raw):
                raise ValueError("report aliases duplicate evaluation bytes")
        by_digest[digest] = (Path(path).absolute(), raw)
    root = Path(prepared["capture"]["selection"]["path"]).parent
    selected = set()
    for row in result["rows"]:
        identity = row["evaluation"]
        declared = Path(identity["path"])
        declared = declared if declared.is_absolute() else root / declared
        actual = by_digest.get(identity["sha256"])
        if actual is None or declared.absolute() != actual[0] or len(actual[1]) != identity["bytes"]:
            raise ValueError("attainability selection is outside or differs from the actual report cohort")
        selected.add(identity["sha256"])
    return [str(p) for h, (p, _) in by_digest.items() if h not in selected]


def render(prepared, *, unselected=()):
    result = recheck_captured(prepared["capture"])
    if not at.identical(result, prepared["report"]):
        raise ValueError("attainability report differs from its captured derivation")
    def cell(v):
        return str(v).replace("|", "\\|").replace("\n", " ").replace("`", "'")
    lines = ["", "## Source-supported item basis (#3046)", "",
             "Explicit known-applicable supported points; partial coverage is not a source ceiling. "
             "The original fixed and N/A-adjusted bases are unchanged. Declared readings are not authenticated scientific judgments.", "",
             "| Evaluation | State | Attained / attainable | Eligible items | Exclusions | Policy SHA256 |",
             "|---|---|---|---|---|---|"]
    for row in result["rows"]:
        b = row["basis"]
        ratio = "unavailable" if b["percentage"] is None else f"{b['attained']:g}/{b['attainable']} ({b['percentage']:.1f}%)"
        excluded = "; ".join(x["item_id"] + ": " + ",".join(r["code"] for r in x["reasons"]) for x in b["excluded"])
        lines.append("| " + " | ".join(cell(v) for v in (row["evaluation"]["path"], row["state"], ratio,
            ", ".join(b["eligible_item_ids"]) or "none", excluded, row["policy"]["sha256"])) + " |")
    for name in unselected:
        lines.append("| " + cell(name) + " | unavailable | unavailable | none | no explicit source selection | none |")
    return "\n".join(lines) + "\n"


def protected_paths(prepared):
    """Derive the actual consulted path roster through the fixed captured reader.

    No generic scan of JSON/YAML pin-like objects and no ambient source reads.
    This includes v1-only rubric identities and all predecessor sources.
    """
    recheck_captured(prepared["capture"])
    closure = prepared["capture"]
    reader = _Reader(DEFAULT_LIMITS, blobs={b["sha256"]: base64.b64decode(b["content_base64"], validate=True)
                                          for b in closure["blobs"]})
    _derive(reader, closure["selection"])
    root = Path(closure["selection"]["path"]).parent
    return {p if p.is_absolute() else root / p for p in reader.paths} | {
        actual for _, actual in _SOURCE_FILES}


def write_new(path, raw, protected=()):
    path = Path(path)
    if path.exists() or path.is_symlink() or any(path.resolve() == Path(p).resolve() for p in protected):
        raise ValueError("attainability output must be a new file outside all inputs")
    with path.open("xb") as stream:
        stream.write(raw)


def save_sidecar(output, prepared):
    path = Path(str(output) + ".attainability.json")
    write_new(path, canonical(prepared) + b"\n", protected_paths(prepared))
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        closure = capture(args.selection)
        prepared = {"capture": closure, "report": recheck_captured(closure)}
        write_new(args.output, canonical(prepared) + b"\n", protected_paths(prepared))
    except (ValueError, OSError, yaml.YAMLError, jsonschema.ValidationError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
