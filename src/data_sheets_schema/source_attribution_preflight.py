"""Opt-in, read-only final-source-review preflight (#2427).

This is a draft diagnostic, not terminal admission or permission to resume a
stopped attempt. It never translates source IDs, edits evidence, or invokes a
model. Historical evidence/source-review checkers remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

INSTRUMENT = "source_attribution_preflight v1 (#2427)"
SCOPE = (
    "Final source-review contract and declared evidence consistency only. "
    "Report-wide assertions, removal obligations and terminal admission remain "
    "unchecked here; semantic support requires independent review. A result "
    "does not authorize continuation after a controller or terminal stop."
)
VOCABULARY = "chunk_manifest.chunks[].source filenames; never source_manifest source_id values"


def _base():
    return {"instrument": INSTRUMENT, "stage": "nonterminal_final_report_draft",
            "terminal_evidence_required": True, "scope": SCOPE}


def _authority(protocol_version, source_manifest_raw, project):
    if type(protocol_version) is not int or protocol_version not in (3, 4, 5, 6, 7):
        raise ValueError("preflight requires an explicit evidence protocol version from 3 through 7")
    if (source_manifest_raw is None) != (project is None):
        raise ValueError("source manifest and project must be selected together")
    if source_manifest_raw is None:
        return None
    if protocol_version < 5:
        raise ValueError("source-manifest authority requires evidence protocol 5 or later")
    from data_sheets_schema.source_metadata import projection
    return projection(source_manifest_raw, project)


def attribution_diagnostics(review, filenames: list[str], authority=None) -> tuple[list[dict], dict]:
    """Explain every attribution occurrence, without correcting any candidate.

    The existing source-review checker is authoritative for contract findings.
    This supplementary walk continues after a bad claim, so a row containing
    multiple mistakes does not hide all but its first attribution problem.
    """
    allowed = set(filenames)
    ids = {row["source_id"]: row["source"] for row in (authority or {}).get("sources", [])}
    problems = []
    counts = {"claims_examined": 0, "attribution_items_examined": 0}
    rows = review.get("values") if isinstance(review, dict) else None
    if not isinstance(rows, list):
        return problems, counts
    for row_index, row in enumerate(rows):
        claims = row.get("claims") if isinstance(row, dict) else None
        if not isinstance(claims, list):
            continue
        for claim_index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                continue
            counts["claims_examined"] += 1
            where = f"/source_review/values/{row_index}/claims/{claim_index}/attributed_to"
            location = {"location": where, "record_path": row.get("path"),
                        "claim": claim_index, "expected_vocabulary": VOCABULARY}
            attributed = claim.get("attributed_to")
            if not isinstance(attributed, list):
                problems.append({**location, "code": "attribution_array_required",
                                 "received": attributed, "expected": "a list of distinct filenames, or []"})
                continue
            evidence = claim.get("evidence")
            provenance = isinstance(evidence, list) and any(
                isinstance(entry, dict) and "provenance" in entry for entry in evidence)
            if attributed and provenance:
                problems.append({**location, "code": "provenance_attribution_must_be_empty",
                                 "received": attributed, "expected": []})
            seen = set()
            for index, value in enumerate(attributed):
                counts["attribution_items_examined"] += 1
                detail = {**location, "location": where + f"/{index}", "received": value}
                if not isinstance(value, str):
                    problems.append({**detail, "code": "attribution_filename_required"})
                    continue
                if value in seen:
                    problems.append({**detail, "code": "duplicate_attribution"})
                seen.add(value)
                # A literal filename remains valid even if an ID has the same
                # spelling. Never reinterpret valid document vocabulary as IDs.
                if value in allowed:
                    continue
                if value in ids:
                    filename = ids[value]
                    problems.append({**detail, "code": "source_id_used_as_filename",
                                     "registered_filename": filename,
                                     "registered_filename_in_bundle": filename in allowed,
                                     "expected": filename if filename in allowed else None,
                                     "note": "Review the attribution; no automatic replacement or evidence inference."})
                else:
                    problems.append({**detail, "code": "unknown_source_filename"})
    return problems, counts


def check_bytes(*, report_raw: bytes, record_raw: bytes, bundle_raw: bytes,
                chunk_manifest_raw: bytes, protocol_version: int,
                source_manifest_raw: bytes | None = None, project: str | None = None) -> dict:
    """Preflight explicitly selected snapshots; do not discover ambient inputs."""
    from data_sheets_schema import evidence_assertions as evidence, source_review
    inputs = {"report": report_raw, "final_full": record_raw, "bundle": bundle_raw,
              "chunk_manifest": chunk_manifest_raw}
    if source_manifest_raw is not None:
        inputs["source_manifest"] = source_manifest_raw
    if any(type(raw) is not bytes for raw in inputs.values()):
        raise ValueError("preflight inputs must be captured bytes")
    authority = _authority(protocol_version, source_manifest_raw, project)
    chunks, _ = evidence.source_chunks_from_bytes(bundle_raw, chunk_manifest_raw)
    payload = evidence.report_payload(report_raw.decode("utf-8"), protocol_version=protocol_version)
    review = payload["source_review"]
    kwargs = ({"source_manifest_raw": source_manifest_raw, "project": project}
              if source_manifest_raw is not None else {})
    checked = source_review.check(review, raw=record_raw.decode("utf-8"), artifact="final_full",
                                  chunks=chunks, protocol_version=protocol_version, **kwargs)
    filenames = sorted({chunk["source"] for chunk in chunks.values()} - {"<preamble>"})
    diagnostics, counts = attribution_diagnostics(review, filenames, authority)
    # Strict JSON output is also a check against non-finite candidate values.
    # Historical parser behavior is preserved; this new tool refuses such input.
    result = {**_base(), "checked": True, "passed": not checked["findings"],
              "protocol_version": protocol_version,
              "input_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in inputs.items()},
              "project": project, "expected_vocabulary": VOCABULARY,
              "expected_filenames": filenames, "source_review": checked,
              "attribution_diagnostics": diagnostics, "counts": counts}
    json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
    return result


def check_files(*, report: Path, record: Path, bundle: Path, chunk_manifest: Path,
                protocol_version: int, source_manifest: Path | None = None,
                project: str | None = None) -> dict:
    """Read each named file once; hashes and checks use those captured bytes."""
    if (source_manifest is None) != (project is None):
        raise ValueError("source manifest and project must be selected together")
    paths = {"report": report, "record": record, "bundle": bundle,
             "chunk_manifest": chunk_manifest}
    if source_manifest is not None:
        paths["source_manifest"] = source_manifest
    captured = {name + "_raw": path.read_bytes() for name, path in paths.items()}
    return check_bytes(**captured, protocol_version=protocol_version, project=project)


def file_result(**kwargs) -> dict:
    """CLI result including a distinct unusable-input state."""
    try:
        return check_files(**kwargs)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, RecursionError, yaml.YAMLError) as exc:
        return {**_base(), "checked": False, "passed": False,
                "reason": f"{type(exc).__name__}: {exc}"}


def exit_status(result: dict) -> int:
    return 2 if not result["checked"] else int(not result["passed"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("report", "record", "bundle", "chunk-manifest"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--protocol-version", type=int, choices=(3, 4, 5, 6, 7), required=True)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--project")
    result = file_result(**vars(parser.parse_args(argv)))
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return exit_status(result)


if __name__ == "__main__":
    raise SystemExit(main())
