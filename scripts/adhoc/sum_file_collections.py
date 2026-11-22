"""Sum file_collections counts/sizes and compare with the record's stated totals.

Purpose: Phase 4 unprompted semantic review (total_file_count / total_size_bytes
against the entries beneath them) for a native D4D run.
Inputs: path to a full D4D record (YAML).
Outputs: JSON on stdout with per-collection figures, sums and differences (read-only).
Run: AI_READI 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1 (generic-v9 native run).
Date: 2026-11-21
"""
from __future__ import annotations

import json
import sys

import yaml


def main(path: str) -> None:
    rec = yaml.safe_load(open(path))
    rows = []
    for fc in rec.get("file_collections", []):
        rows.append({"id": fc["id"], "file_count": fc.get("file_count"),
                     "total_bytes": fc.get("total_bytes"),
                     "file_entries": len(fc.get("resources", []))})
    counted = [r for r in rows if r["file_count"] is not None]
    sized = [r for r in rows if r["total_bytes"] is not None]
    sum_files = sum(r["file_count"] for r in counted)
    sum_bytes = sum(r["total_bytes"] for r in sized)
    out = {
        "collections": rows,
        "sum_file_count_over_collections_with_count": sum_files,
        "stated_total_file_count": rec.get("total_file_count"),
        "file_count_difference": rec.get("total_file_count", 0) - sum_files,
        "root_metadata_file_entries": sum(r["file_entries"] for r in rows if r["file_count"] is None),
        "sum_total_bytes_over_collections_with_size": sum_bytes,
        "stated_total_size_bytes": rec.get("total_size_bytes"),
        "bytes_difference": rec.get("total_size_bytes", 0) - sum_bytes,
    }
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
