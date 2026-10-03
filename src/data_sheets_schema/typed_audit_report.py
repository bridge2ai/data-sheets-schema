"""Report explicitly selected typed assemblies after captured-byte reconstruction.

Counts describe declarations, not independently established omissions or recall.
No provider, cohort discovery, legacy classifier, or figure defaults are used.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile

from . import audit_batches, audit_grammar, audit_omissions, typed_audit

FORMAT = "checked_typed_audit_report_v1"
MAX_ASSEMBLIES = 64
MAX_SELECTED_BYTES = 320_000_000
LIMITATIONS = [
    "Kinds are audit-declared; missing kind remains untyped, without prose classification.",
    "Scientific support, applicability, novelty and exhaustive recall are unverified.",
    "Caller-selected assemblies are not an inferred cohort or independent observations.",
    "Hashes bind captured content and declared associations, not provider authentication.",
    "This report does not integrate fig07, register a condition, execute or repair records.",
]


def _identity(blob):
    return {key: blob[key] for key in ("sha256", "bytes")}


def _inner(blob):
    """An envelope already verified by typed_audit.check; no file is reread."""
    return json.loads(typed_audit._unblob(blob, typed_audit.MAX_SAVED_RESPONSE_BYTES))


def _worker_identity(blob):
    inner = _inner(blob)
    return {"saved_response": _identity(blob), "response": _identity(inner["response"]),
            "request_sha256": inner["request_sha256"]}


def _entry(raw: bytes, source: str, selection_index: int):
    assembly = typed_audit._bounded_json(raw, "assembly", typed_audit.MAX_ASSEMBLY_BYTES)
    acceptance = typed_audit.check(assembly)
    # check reconstructs and compares the complete assembly, then returns only
    # acceptance. Extract from this same parsed object, never reread its path.
    packet, lineage = assembly["packet"], assembly["lineage"]
    audit = audit_grammar._load(typed_audit._unblob(assembly["audit"], audit_grammar.MAX_BYTES))
    identity = {
        "assembly_sha256": assembly["sha256"], "packet_sha256": packet["sha256"],
        "typed_index_sha256": assembly["index"]["sha256"],
        "inputs": {key: _identity(blob) for key, blob in packet["inputs"].items()},
        "schema_sources": [{"name": row["name"], "path": row["path"],
                            **_identity(row["content"])} for row in packet["schema_sources"]],
        "schema_sources_sha256": lineage["schema_sources_sha256"],
        "omission_contract_sha256": packet["omission_request"]["payload"]["contract_sha256"],
        "audit": _identity(assembly["audit"]),
        "omission_response": _identity(assembly["omission_response"]),
        "omission_request_sha256": packet["omission_request"]["request_sha256"],
        "integration_saved_response": _identity(assembly["integration_response"]),
        "integration_response": _identity(_inner(assembly["integration_response"])["response"]),
        "integration_request_sha256": assembly["index"]["integration_request"]["request_sha256"],
        "workers": {key: _worker_identity(blob) for key, blob in assembly["workers"].items()},
    }
    findings = [{"final_finding_ordinal": ordinal,
                 "classification_basis": "audit_declared_kind" if "kind" in finding else "untyped",
                 "declared_kind": finding.get("kind"), "finding": finding,
                 "lineage": lineage["findings"][ordinal]}
                for ordinal, finding in enumerate(audit["findings"])]
    counts = {"findings": sum(acceptance["finding_counts"].values()),
              "findings_by_declared_kind": acceptance["finding_counts"],
              "candidates": acceptance["omission_counts"]["declared_candidates"],
              "retained_candidates": acceptance["omission_counts"]["retained"],
              "dropped_candidates": acceptance["omission_counts"]["dropped"],
              "chunk_declarations": acceptance["omission_counts"]}
    return {"selection_index": selection_index,
            "source": {"path": source, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
            "identity": identity, "protocol": packet["protocol"], "acceptance": acceptance,
            "counts": counts, "findings": findings,
            "candidates": lineage["omission_candidates"], "lineage": lineage}


def build_report(assemblies):
    """Consume ordered (source spelling, exact raw bytes) pairs once.

    Source names are caller-provided provenance only, never method/project labels.
    Repeated canonical assemblies are refused even if their raw whitespace differs.
    The returned object owns its parsed data; no input mappings are accepted.
    """
    records, seen, total = [], set(), 0
    for index, (source, raw) in enumerate(assemblies):
        if index >= MAX_ASSEMBLIES:
            raise ValueError("too many selected assemblies")
        if type(source) is not str or not source.strip() or type(raw) is not bytes:
            raise ValueError("assemblies require a nonblank source spelling and raw bytes")
        total += len(raw)
        if total > MAX_SELECTED_BYTES:
            raise ValueError("selected assembly bytes exceed report bound")
        row = _entry(raw, source, index)
        identity = row["identity"]["assembly_sha256"]
        if identity in seen:
            raise ValueError("duplicate canonical assembly in selection")
        seen.add(identity)
        records.append(row)
    if not records:
        raise ValueError("select at least one typed assembly")
    return {"format": FORMAT, "selection_basis": "explicit caller-supplied ordered assemblies",
            "assembly_count": len(records), "limitations": list(LIMITATIONS), "assemblies": records}


def read_report(paths):
    """Read each selected assembly once; embedded authorities are never reopened."""
    return build_report((str(Path(path).absolute()), audit_omissions._file(Path(path), typed_audit.MAX_ASSEMBLY_BYTES))
                        for path in paths)


CSV_FIELDS = ["report_format", "row_type", "selection_index", "assembly_path", "assembly_raw_sha256", "assembly_raw_bytes", "assembly_sha256",
              "packet_sha256", "final_finding_ordinal", "classification_basis", "declared_kind",
              "severity", "record_scope", "candidate_id", "disposition", "findings", "candidates",
              "retained_candidates", "dropped_candidates", "scientific_support", "novelty", "exhaustive_recall",
              "protocol_json", "acceptance_json", "identity_json", "counts_json", "finding_json", "candidate_json", "lineage_json", "limitations_json"]


def _json_cell(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def csv_bytes(report):
    """Long-form export: one assembly row even for zero findings, plus detail rows.

    Assembly rows carry all identities and full source lineage. Detail rows join
    by selection_index/assembly_sha256; counts occur only on assembly rows so they
    are not multiplied by the number of findings or candidates.
    """
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in report["assemblies"]:
        common = {"report_format": report["format"], "selection_index": row["selection_index"], "assembly_path": row["source"]["path"],
                  "assembly_raw_sha256": row["source"]["sha256"],
                  "assembly_raw_bytes": row["source"]["bytes"],
                  **{key: row["identity"][key] for key in ("assembly_sha256", "packet_sha256")},
                  **{key: row["acceptance"][key] for key in ("scientific_support", "novelty", "exhaustive_recall")}}
        writer.writerow({**common, "row_type": "assembly",
                         **{key: row["counts"][key] for key in ("findings", "candidates", "retained_candidates", "dropped_candidates")},
                         "protocol_json": _json_cell(row["protocol"]), "acceptance_json": _json_cell(row["acceptance"]),
                         "identity_json": _json_cell(row["identity"]), "counts_json": _json_cell(row["counts"]),
                         "lineage_json": _json_cell(row["lineage"]), "limitations_json": _json_cell(report["limitations"])})
        for finding in row["findings"]:
            writer.writerow({**common, "row_type": "finding", **{key: finding[key] for key in
                             ("final_finding_ordinal", "classification_basis", "declared_kind")},
                             "severity": finding["finding"]["severity"], "record_scope": finding["finding"]["record"],
                             "finding_json": _json_cell(finding["finding"]), "lineage_json": _json_cell(finding["lineage"])})
        for candidate in row["candidates"]:
            writer.writerow({**common, "row_type": "candidate", "candidate_id": candidate["candidate"]["id"],
                             "disposition": candidate["disposition"]["action"],
                             "final_finding_ordinal": candidate["final_finding_ordinal"],
                             "candidate_json": _json_cell(candidate)})
    return stream.getvalue().encode("utf-8")


def write_report(paths, output, *, format="json"):
    """Check all inputs, then publish one fresh report without overwriting aliases.

    Staging and an exclusive hardlink prevent partial writes from looking like a
    completed destination. Only the newly created private staging file is removed.
    """
    if format not in ("json", "csv"):
        raise ValueError("report format must be json or csv")
    output = Path(output)
    if os.path.lexists(output):
        raise ValueError("report destination must be new")
    report = read_report(paths)
    protected = [Path(row["source"]["path"]) for row in report["assemblies"]]
    protected.extend(Path(schema["path"]) for row in report["assemblies"] for schema in row["identity"]["schema_sources"])
    # Existing aliases are also refused atomically by link below. Protect named
    # captured schema paths even if those historical files are now absent.
    if output.resolve() in {path.resolve() for path in protected}:
        raise ValueError("report destination aliases a selected source or captured schema authority")
    raw = audit_batches.canonical_bytes(report) if format == "json" else csv_bytes(report)
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".typed-audit-report-", delete=True) as stage:
        stage.write(raw)
        stage.flush()
        os.fsync(stage.fileno())
        os.link(stage.name, output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assembly", type=Path, action="append", required=True,
                        help="Saved typed assembly; repeat explicitly in the desired order")
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    parser.add_argument("--output", type=Path, required=True, help="Fresh destination only")
    args = parser.parse_args()
    try:
        write_report(args.assembly, args.output, format=args.format)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(2, f"typed audit report refused: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
