"""Check complete value coverage and declared source scope, not semantic entailment.

Opt-in evidence protocol v3 uses this alongside its existing quotation checks.
Protocol v5 enables v2's exact registered metadata declarations separately from
bundle evidence, without expanding the record-metadata coverage exemptions.
The source/status classifications remain judgments for independent review.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path

INSTRUMENT = "source_review v1 (#1815, #1782)"
PROVENANCE_INSTRUMENT = "source_review v2 (#2169)"
STATUSES = {"fact", "planned", "in_progress", "applied", "instruction", "capability"}
CLAIM_KEYS = {"text", "verdict", "attributed_to", "claim_status", "source_status", "evidence", "reason"}
INVENTORY_HEADER = "# Required source-review inventory\n\n"


def _text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def inventory(raw: str, artifact: str) -> dict:
    """Enumerate every populated scalar, including zero/false, from exact bytes."""
    from data_sheets_schema.evidence_assertions import load_record
    if artifact not in {"original_full", "final_full"}:
        raise ValueError("source review requires original_full or final_full")
    record = load_record(raw)
    values = []

    def walk(value, path, ancestors=frozenset()):
        if isinstance(value, (dict, list)):
            if id(value) in ancestors:
                raise ValueError("cyclic record cannot establish source-review coverage")
            ancestors = ancestors | {id(value)}
            items = value.items() if isinstance(value, dict) else enumerate(value)
            for key, child in items:
                if isinstance(value, dict) and not isinstance(key, str):
                    raise ValueError("record keys must be strings")
                token = str(key).replace("~", "~0").replace("/", "~1")
                walk(child, path + "/" + token, ancestors)
        elif value is not None and value != "":
            text = _text(value)
            metadata = (path in {"/conforms_to_schema", "/conforms_to_class"}
                        or (path.endswith("/id") and path != "/id"
                            and isinstance(record.get("id"), str) and record["id"].strip()
                            and isinstance(value, str) and value.startswith(record["id"] + "#")))
            values.append({"path": path, "text": text, "record_metadata_allowed": bool(metadata),
                           "whole_value_required": not isinstance(value, str)})

    walk(record, "")
    return {"artifact": artifact, "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "values": values}


def check(review, *, raw: str, artifact: str, chunks: dict, audit_findings=None,
          protocol_version: int = 3, source_manifest_raw: bytes | str | None = None,
          project: str | None = None) -> dict:
    """Require coverage and reject declared attribution/status contradictions."""
    from data_sheets_schema.evidence_assertions import check_assertions, _fold
    if type(protocol_version) is not int or protocol_version not in (3, 4, 5):
        raise ValueError("unsupported source-review protocol version")
    if protocol_version != 5 and (source_manifest_raw is not None or project is not None):
        raise ValueError("registered provenance authority requires evidence protocol 5")
    authority = None
    if protocol_version == 5 and source_manifest_raw is not None:
        from data_sheets_schema.source_metadata import projection
        authority = projection(source_manifest_raw, project)
    required = inventory(raw, artifact)
    expected = {row["path"]: row for row in required["values"]}
    findings, seen, revisions = [], set(), set()
    claims_checked = 0

    def problem(detail, **fields):
        findings.append({"kind": "source_review_contract", "detail": detail, **fields})

    if (not isinstance(review, dict) or set(review) != {"artifact", "sha256", "values"}
            or review.get("artifact") != artifact or review.get("sha256") != required["sha256"]
            or not isinstance(review.get("values"), list)):
        problem("source_review must bind this exact artifact and enumerate its values")
    else:
        for row in review["values"]:
            try:
                if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                    raise ValueError("source-review value must name a JSON Pointer path")
                path = row["path"]
                if path not in expected or path in seen:
                    raise ValueError("unknown or duplicate source-review value path")
                seen.add(path)
                if set(row) == {"path", "metadata_reason"}:
                    if (not expected[path]["record_metadata_allowed"]
                            or not isinstance(row["metadata_reason"], str) or not row["metadata_reason"].strip()):
                        raise ValueError("only declared record metadata can omit source claims")
                    continue
                if set(row) != {"path", "claims"} or not isinstance(row["claims"], list) or not row["claims"]:
                    raise ValueError("every factual value needs a nonempty claims array")
                text = _fold(expected[path]["text"])
                covered = set()
                for index, claim in enumerate(row["claims"]):
                    if not isinstance(claim, dict) or set(claim) != CLAIM_KEYS:
                        raise ValueError("claim must contain text, verdict, attributed_to, claim_status, source_status, evidence and reason")
                    quote = claim["text"]
                    if not isinstance(quote, str) or not quote.strip() or _fold(quote) not in text:
                        raise ValueError("claim text must quote this value, retaining case and punctuation")
                    quote = _fold(quote)
                    if expected[path]["whole_value_required"] and quote != text:
                        raise ValueError("a numeric, boolean or date claim must quote its complete scalar value")
                    start = text.find(quote)
                    while start >= 0:
                        covered.update(range(start, start + len(quote)))
                        start = text.find(quote, start + 1)
                    if not isinstance(claim["reason"], str) or not claim["reason"].strip():
                        raise ValueError("every claim needs a source-scope explanation")
                    if claim["verdict"] not in {"supported", "revise"}:
                        raise ValueError("claim verdict must be supported or revise")
                    if (claim["claim_status"] not in STATUSES
                            or claim["source_status"] not in STATUSES | {"unstated"}):
                        raise ValueError("unknown declared claim/source status")
                    attributed = claim["attributed_to"]
                    if (not isinstance(attributed, list) or any(not isinstance(s, str) for s in attributed)
                            or len(set(attributed)) != len(attributed)
                            or any(s == "<preamble>" or s not in {c["source"] for c in chunks.values()} for s in attributed)):
                        raise ValueError("attributed_to must list distinct named source documents, or be empty")
                    evidence = claim["evidence"]
                    provenance = (protocol_version == 5 and isinstance(evidence, list)
                                  and any(isinstance(e, dict) and "provenance" in e for e in evidence))
                    if provenance:
                        from data_sheets_schema.source_metadata import check_assertion
                        if attributed:
                            raise ValueError("a provenance-only clause cannot attribute its facts to bundle documents")
                        if claim["claim_status"] != "fact" or claim["source_status"] != "fact":
                            raise ValueError("registered provenance establishes only declared metadata facts")
                        # Each entry must be the exact provenance form; mixed
                        # bundle evidence cannot turn metadata into dataset facts.
                        for entry in evidence:
                            check_assertion(entry, authority=authority)
                        errors = []
                    else:
                        if (not isinstance(evidence, list)
                                or any(not isinstance(e, dict) or set(e) != {"source", "chunk", "quote"} for e in evidence)):
                            raise ValueError("claim evidence must contain only source/chunk/quote assertions")
                        errors = check_assertions(evidence, artifacts={}, chunks=chunks)
                    findings.extend({**error, "source_review_path": path, "claim": index} for error in errors)
                    claims_checked += 1
                    if claim["verdict"] == "revise":
                        revisions.add(path)
                        if artifact == "final_full":
                            problem("final source review still rejects a retained claim", path=path, claim=index)
                    else:
                        if not evidence:
                            raise ValueError("a supported claim needs source evidence")
                        if claim["claim_status"] != claim["source_status"]:
                            problem("declared source status does not support the claim's status", path=path, claim=index)
                        if not provenance and set(attributed) - {e["source"] for e in evidence}:
                            problem("a claimed document attribution lacks evidence from that document", path=path, claim=index)
                if any(not char.isspace() and i not in covered for i, char in enumerate(text)):
                    problem("source review omits part of the value's text", path=path)
            except (ValueError, TypeError, KeyError) as exc:
                problem(str(exc), path=row.get("path") if isinstance(row, dict) else None)
    for path in sorted(expected.keys() - seen):
        problem("populated value was not source reviewed", path=path)
    if artifact == "original_full":
        linked = set()
        for finding in audit_findings or []:
            if not isinstance(finding, dict) or "review_paths" not in finding:
                continue
            paths = finding["review_paths"]
            if (not isinstance(paths, list) or not paths
                    or any(not isinstance(path, str) or path not in revisions for path in paths)):
                problem("audit review_paths must name values with revise judgments")
            else:
                linked.update(paths)
        for path in sorted(revisions - linked):
            problem("a revise judgment lacks a linked audit finding", path=path)
    return {"instrument": PROVENANCE_INSTRUMENT if protocol_version == 5 else INSTRUMENT,
            "artifact": artifact, "sha256": required["sha256"],
            "values_required": len(expected), "values_reviewed": len(seen),
            "claims_checked": claims_checked, "findings": findings,
            "scope": "Coverage and declared evidence/scope consistency only; semantic classifications and entailment require independent review."}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print the exact source-review inventory; read only.")
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--artifact", choices=("original_full", "final_full"), required=True)
    args = parser.parse_args(argv)
    print(json.dumps(inventory(args.record.read_bytes().decode("utf-8"), args.artifact), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
