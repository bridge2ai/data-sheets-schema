"""Explicit output-format guidance for a separately selected batch renderer.

This is documentation, not a replacement validator or scientific instrument.
The existing audit_grammar/audit_batches checkers remain authoritative. JSON
Schema describes local JSON shapes; the accompanying rules describe registered
identities and links that cannot be inferred from those shapes alone. No files,
scientific validators or providers are accessed.
"""
from __future__ import annotations

from copy import deepcopy
import json

from . import audit_batches, audit_grammar


FORMAT = "audit_batch_output_format_v1"
STAGES = frozenset({"worker", "integration"})


def _stage(stage):
    if stage not in STAGES:
        raise ValueError("unknown audit batch output stage")


def _ref(name):
    return {"$ref": "#/$defs/" + name}


def _array(item, minimum=0):
    return {"type": "array", "items": item, "minItems": minimum}


def _object(properties, optional=()):
    return {"type": "object", "properties": properties,
            "required": [k for k in properties if k not in optional],
            "additionalProperties": False}


def _definitions():
    definitions = {
        "text": {"type": "string", "pattern": r"\S"},
        "digest": {"type": "string", "pattern": r"^[0-9a-f]{64}(?![\s\S])"},
        "pointer": {"type": "string", "pattern": r"^/(?![\s\S]*~(?![01]))"},
        "status": {"enum": sorted(audit_grammar.STATUSES)},
        "source_status": {"enum": sorted(audit_grammar.STATUSES | {"unstated"})},
    }
    definitions["document"] = _object({k: _ref("text") for k in ("source", "chunk", "quote")})
    definitions["artifact"] = _object({
        "artifact": {"enum": ["original_full", "original_core"]},
        "path": {"anyOf": [_ref("pointer"), {"const": "@header"}]},
        "op": {"enum": ["contains", "lacks"]}, "quote": _ref("text")})
    definitions["assertion"] = {"oneOf": [_ref("document"), _ref("artifact")]}
    provenance = _object({
        "provenance": {"const": "source_manifest"}, "sha256": _ref("digest"),
        "source_id": _ref("text"), "source": _ref("text"),
        "field": {"enum": sorted(audit_grammar.METADATA_FIELDS)}, "value": {}})
    provenance["allOf"] = [
        {"if": {"properties": {"field": {"const": "effective_priority"}}},
         "then": {"properties": {"value": {"type": "integer", "minimum": 1}}}},
        {"if": {"properties": {"field": {"const": "priority_basis"}}},
         "then": {"properties": {"value": {"enum": ["source_override", "source_type", "unranked"]}}}},
        {"if": {"properties": {"field": {"enum": ["source_type", "captured_at", "superseded_by"]}}},
         "then": {"properties": {"value": _ref("text")}}},
    ]
    definitions["provenance"] = provenance
    claim = _object({
        "text": _ref("text"), "verdict": {"enum": ["supported", "revise"]},
        "attributed_to": {**_array(_ref("text")), "uniqueItems": True},
        "claim_status": _ref("status"), "source_status": _ref("source_status"),
        "evidence": {"anyOf": [_array(_ref("document")), _array(_ref("provenance"))]},
        "reason": _ref("text")})
    claim["allOf"] = [
        {"if": {"properties": {"verdict": {"const": "supported"}}},
         "then": {"properties": {"evidence": {"minItems": 1}}}},
        {"if": {"properties": {"evidence": {"minItems": 1, "items": _ref("provenance")}}},
         "then": {"properties": {"attributed_to": {"maxItems": 0},
                                  "claim_status": {"const": "fact"},
                                  "source_status": {"const": "fact"}}}},
    ] + [
        {"if": {"properties": {"verdict": {"const": "supported"}, "claim_status": {"const": status}}},
         "then": {"properties": {"source_status": {"const": status}}}}
        for status in sorted(audit_grammar.STATUSES)
    ]
    definitions["claim"] = claim
    definitions["row"] = {"oneOf": [
        _object({"path": _ref("pointer"), "claims": _array(_ref("claim"), 1)}),
        _object({"path": _ref("pointer"), "metadata_reason": _ref("text")}),
    ]}
    definitions["removal"] = {"oneOf": [
        _object({"path": _ref("pointer"), "identity": {
            "allOf": [_ref("pointer"), {"pattern": "/(" + "|".join(sorted(audit_grammar.IDENTITY_FIELDS)) + r")(?![\s\S])"}]}},
                optional=("identity",)),
        _object({"path": _ref("pointer"), "match": {"const": "anonymous_structure_v1"},
                 "original_full_sha256": _ref("digest")}),
    ]}
    definitions["finding"] = _object({
        "severity": {"enum": ["high", "medium", "low"]},
        "record": {"enum": ["full", "core", "both"]},
        "slot": _ref("text"), "issue": _ref("text"),
        "evidence": _array(_ref("assertion"), 1),
        "review_paths": _array(_ref("pointer"), 1), "remove_relationship": _ref("removal")},
        optional=("review_paths", "remove_relationship"))
    return definitions


def schema(stage: str) -> dict:
    """Return fresh strict JSON-shape guidance; registered link rules are separate."""
    _stage(stage)
    if stage == "worker":
        result = _object({
            "findings": _array(_ref("finding")), "summary": _ref("text"),
            "source_review": _object({"artifact": {"const": "original_full"},
                "sha256": _ref("digest"), "values": _array(_ref("row"))})})
    else:
        decision = _object({"id": _ref("text"), "previous_sha256": _ref("digest"),
            "action": {"enum": ["retain", "replace", "drop"]}, "reason": _ref("text"),
            "evidence": _array(_ref("assertion")), "findings": _array(_ref("finding"), 1)},
            optional=("findings",))
        decision["allOf"] = [
            {"if": {"properties": {"action": {"const": "replace"}}},
             "then": {"required": ["findings"]}, "else": {"not": {"required": ["findings"]}}},
            {"if": {"properties": {"action": {"enum": ["replace", "drop"]}}},
             "then": {"properties": {"evidence": {"minItems": 1}}}},
        ]
        result = _object({
            "kind": {"const": "audit_integration_v1"},
            "proposal_index_sha256": _ref("digest"),
            "retain_other_rows_from_index_sha256": _ref("digest"),
            "row_replacements": _array(_object({
                "path": _ref("pointer"), "previous_sha256": _ref("digest"),
                "row": _ref("row"), "reason": _ref("text"),
                "evidence": _array(_ref("assertion"), 1)})),
            "finding_decisions": _array(decision),
            "new_findings": _array(_ref("finding")), "summary": _ref("text")})
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **result,
            "$defs": _definitions()}


COMMON_RULES = (
    "Emit one strict UTF-8 JSON object, without Markdown fences, duplicate keys, nonfinite numbers or trailing text. Do not add keys beyond the chosen object variant. Blank strings are invalid where text is required; JSON null is not an empty array or omitted optional property.",
    "Draft parts are concatenated as raw UTF-8 bytes in their registered order, with no inserted comma, newline or other separator. The combined bytes must be exactly one complete JSON object, not one object or array per part. Preserve commas, brackets and string escaping across boundaries; do not restart or repeat an enclosing object in a later part. Each individual part must be valid UTF-8 and obey the registered size limit. Never append commentary or code fences.",
    "Every source-review path occurs once. A row has path and nonempty claims, OR path and metadata_reason, never both. The metadata variant is scientifically permitted only for an inventory value marked record_metadata_allowed.",
    "Each claim has exactly text, verdict, attributed_to, claim_status, source_status, evidence and reason. attributed_to is an array of distinct nonblank source filenames, not a string. A supported claim has nonempty evidence and equal claim_status/source_status. source_status=unstated is available only with revise. These are declaration rules, not authority to change a scientific judgment.",
    "Claim evidence contains document assertions OR provenance assertions, never a mixture or original-artifact assertions. Provenance assertions require empty attributed_to and fact/fact statuses. effective_priority is a positive JSON integer: do not write 2.0, true or a quoted numeral. Findings and integration decisions use document/artifact assertions, not provenance assertions.",
    "Every path with any revise claim must be linked by at least one final finding's review_paths. Each listed review_path must contain at least one revise claim. Supporting-only and metadata-only rows do not belong in review_paths. An omission finding may omit review_paths; do not invent a populated path for an omission.",
    "Finding record uses full/core/both; artifact uses original_full/original_core. severity uses high/medium/low. summary is one nonblank string, not a counts object; any stated counts must match final findings. The scientific protocol governs which affected records and evidence are actually available.",
    "remove_relationship is one object. Use path with optional identity, OR path/match=anonymous_structure_v1/original_full_sha256; never mix modes. Identity is a relative JSON Pointer ending in an allowed identifier field. The path-only form's scientific admissibility and every removal's exact identity are governed by the selected protocol; a grammar pass does not approve removal.",
    "Paths are JSON Pointers starting with /; escape ~ as ~0 and / within a key as ~1. @header is permitted only for artifact evidence paths. Digests are 64 lowercase hex characters. Copy the exact registered digest/identity; never copy an example's digest or invent one.",
    "A shape pass does not establish literal coverage, source quotation accuracy, complete clauses, status correctness, attribution, entailment or scientific acceptance. Preserve the assigned scientific review and the selected two-round/seal/terminal-check workflow.",
)
WORKER_RULES = (
    "source_review.artifact is exactly original_full; source_review.sha256 equals the complete original-full inventory digest, not a digest of this worker's subset.",
    "source_review.values contains exactly this worker's assigned paths, once each, including zero/false and all clauses. It is an array of row objects, not a pointer-keyed mapping. Empty values is permitted only for an assigned empty inventory. The full original remains available as context.",
    "Every removal's top-level owner belongs to this worker's assigned roots. Source/finding evidence can cite context outside the assignment; review_paths must link this worker's revised rows. Other workers' judgments are not inputs.",
)
INTEGRATION_RULES = (
    "Return an integration delta, not a complete audit object: exactly kind, proposal_index_sha256, retain_other_rows_from_index_sha256, row_replacements, finding_decisions, new_findings and summary. Both index digests equal the exact supplied worker index.sha256, not the plan hash or a raw index-file hash.",
    "Before final decisions, successfully Read every complete canonical worker row, including retained rows, and assess complete findings. Retention binds all unchanged rows to the exact reviewed index; it does not authorize retaining unread rows.",
    "row_replacements may be empty. Each replacement path is an existing indexed path, occurs once, and matches row.path. previous_sha256 is that indexed row's canonical-object sha256. Supply a complete replacement row, a reason and nonempty document/artifact evidence. Never add/delete a row, change its path or submit a partial patch.",
    "finding_decisions contains exactly one entry for every index.findings id, no others. Copy each id and its own canonical-object sha256 into previous_sha256. retain keeps the complete old finding and may use empty evidence; drop removes it and requires nonempty evidence; replace requires nonempty evidence AND a nonempty findings array of complete replacement findings (a split is allowed). findings must be absent for retain/drop, not null or an empty array.",
    "new_findings is an array, possibly empty, of complete independently authored findings. The final summary is model-authored. After all explicit decisions, every revise row must still link to a final finding and every review_path must still have a revise claim. Replacing or dropping a concern must not orphan a revised row; change the complete row explicitly only when scientifically justified.",
    "All final removals must have top-level roots in the full plan. No two final removals may be identical or stand in an ancestor/descendant relation. Resolve any overlap explicitly through finding decisions; the assembler will not infer a repair or discard a finding.",
)


def synthetic_examples() -> dict:
    """Fresh, self-contained grammar fixtures; never evidence for a real record."""
    original = "alpha: Example alpha.\nbeta: Example beta.\ngamma: Example gamma.\n"
    plan = audit_batches.make_plan(original)
    evidence = [{"source": "example.txt", "chunk": "c001", "quote": "Illustrative source statement."}]
    rows, findings = [], []
    for key in ("alpha", "beta", "gamma"):
        rows.append({"path": "/" + key, "claims": [{"text": f"Example {key}.",
            "verdict": "revise", "attributed_to": [], "claim_status": "fact", "source_status": "unstated",
            "evidence": [], "reason": "An illustrative claim requiring scientific review."}]})
        findings.append({"severity": "medium", "record": "full", "slot": key,
            "issue": "An illustrative concern about this claim.", "review_paths": ["/" + key],
            "evidence": deepcopy(evidence)})
    worker = {"findings": findings, "summary": "3 illustrative findings: 3 medium.", "source_review": {
        "artifact": "original_full", "sha256": plan["original_full_sha256"], "values": rows}}
    proposals = {plan["workers"][0]["id"]: audit_batches.canonical_bytes(worker)}
    index = audit_batches.build_index(plan, proposals)
    replacement_row = deepcopy(rows[2])
    replacement_row["claims"][0].update(verdict="supported", source_status="fact", evidence=deepcopy(evidence),
        reason="The fictional integration review establishes this fictional claim.")
    replacement_finding = deepcopy(findings[1])
    replacement_finding["issue"] = "The fictional integration review restates this concern precisely."
    decisions = []
    for old, action in zip(index["findings"], ("retain", "replace", "drop")):
        decision = {"id": old["id"], "previous_sha256": old["sha256"], "action": action,
            "reason": "An explicit fictional integration disposition.",
            "evidence": [] if action == "retain" else deepcopy(evidence)}
        if action == "replace":
            decision["findings"] = [replacement_finding]
        decisions.append(decision)
    integration = {"kind": "audit_integration_v1", "proposal_index_sha256": index["sha256"],
        "retain_other_rows_from_index_sha256": index["sha256"],
        "row_replacements": [{"path": "/gamma", "previous_sha256": index["rows"][2]["sha256"],
            "row": replacement_row, "reason": "A fictional source review justifies this complete row change.",
            "evidence": deepcopy(evidence)}],
        "finding_decisions": decisions, "new_findings": [], "summary": "2 illustrative findings: 2 medium."}
    return {"original_full": original, "plan": plan, "worker": worker, "index": index,
            "integration": integration}


def contract(stage: str) -> dict:
    """Return deterministic documentation with a fresh schema and synthetic example."""
    _stage(stage)
    examples = synthetic_examples()
    example = {"warning": "Invented grammar fixture only. Do not copy any fact, path, source, digest or judgment into your run.",
               "original_full": examples["original_full"], "proposal": examples[stage]}
    if stage == "integration":
        example["worker_proposals"] = [{"id": examples["plan"]["workers"][0]["id"],
                                        "proposal": examples["worker"]}]
        example["worker_index"] = examples["index"]
    return {"format": FORMAT, "stage": stage,
            "authority": "Documentation of existing source-blind grammar, not a new validator or scientific acceptance rule.",
            "json_schema": schema(stage),
            "additional_rules": list(COMMON_RULES + (WORKER_RULES if stage == "worker" else INTEGRATION_RULES)),
            "synthetic_example": example}


def render(stage: str) -> str:
    """Render the exact role-specific output contract for explicit opt-in wiring."""
    return ("# Exact registered batch output format\n\n"
            "Use the following closed-key JSON schema together with its identity/link rules. "
            "The schema and invented example describe syntax; the selected scientific protocol "
            "and actual inputs govern judgments. Follow the registered output commands.\n\n"
            + json.dumps(contract(stage), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
