"""Read-only inventory; includes ignored files and never selects by score.

Run with the registered checkout's Python and PYTHONPATH=src. The source root
is explicit so ignored artifacts in the working corpus are included too.
Outputs are new registration evidence, not edited historical provenance.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import yaml

from data_sheets_schema import provenance, runs
from data_sheets_schema.duplicate_keys import duplicate_keys_in


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mapping(path):
    try:
        value = json.loads(path.read_bytes()) if path.suffix == ".json" else yaml.safe_load(path.read_bytes())
        return (value, None) if isinstance(value, dict) else ({}, "not a mapping")
    except (ValueError, yaml.YAMLError, UnicodeDecodeError) as exc:
        return {}, f"{type(exc).__name__}: {exc}"


def inventory(root):
    root = root.resolve()
    corpus = root / "data/d4d_concatenated"
    evaluation_roots = sorted(p for p in (root / "data").glob("evaluation*") if p.is_dir())
    roots = [corpus, *evaluation_roots]
    pins = {}
    for directory in roots:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                if not path.resolve().is_relative_to(root):
                    raise ValueError(f"artifact points outside source root: {path}")
                pins[str(path.relative_to(root))] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    rows = []
    for path in sorted(corpus.rglob("*.yaml")):
        suffix = next((s for s in ("_d4d_core.yaml", "_d4d.yaml") if path.name.endswith(s)), None)
        if suffix is None:
            continue
        relative = path.relative_to(corpus)
        if len(relative.parts) not in (2, 3):
            # Snapshots/archives remain in preservation pins; they are not
            # silently promoted to independent generation records.
            continue
        project = path.name[:-len(suffix)]
        method = relative.parts[0]
        label = relative.parts[1] if len(relative.parts) == 3 else None
        record, parse_error = mapping(path)
        duplicates = None
        if parse_error is None:
            duplicates = duplicate_keys_in(path)
        pp = provenance.record_path_for(project, method, label, corpus) if label else None
        p, provenance_error = mapping(pp) if pp and pp.is_file() else ({}, "no provenance file at the canonical path")
        model = p.get("model") or {}
        model = model if isinstance(model, dict) else {}
        source = p.get("inputs") or {}
        source = source if isinstance(source, dict) else {}
        declared_run = p.get("run") or {}
        declared_run = declared_run if isinstance(declared_run, dict) else {}
        header = provenance.parse_header(path)
        runtime = runs.runtime_of(p)
        rows.append({
            "path": str(path.relative_to(root)), **pins[str(path.relative_to(root))],
            "project_from_filename": project, "method_directory": method, "label": label,
            "input_arm": runs.ARM_BY_METHOD.get(method, "unclassified"),
            "variant": "core" if suffix == "_d4d_core.yaml" else "full",
            "declared_run": declared_run, "runtime_from_provenance": runtime,
            "runtime_header_only": header.get("Agent runtime") if runtime is None else None,
            "model": model.get("model"), "provider": model.get("provider"),
            "provenance_path": str(pp.relative_to(root)) if pp and pp.is_file() else None,
            "provenance_error": provenance_error, "record_parse_error": parse_error,
            "duplicate_keys": duplicates, "source": source,
            "generation_schema": p.get("schema"),
            "stored_validation": p.get("validation"), "stored_canary": p.get("canary"),
            "new_condition_eligibility": "historical reference only; not a new matched measurement",
        })
    evaluations = []
    for directory in evaluation_roots:
        for path in sorted(directory.rglob("*_evaluation.json")):
            value, error = mapping(path)
            model = value.get("model") or {}
            meta = value.get("metadata") or {}
            evaluations.append({
                "path": str(path.relative_to(root)), **pins[str(path.relative_to(root))],
                "rubric": value.get("rubric"), "version": value.get("version"),
                "project": value.get("project"), "method": value.get("method"),
                "input_name": value.get("d4d_file"), "model": model, "metadata": meta,
                "parse_error": error,
                "acceptance": "not inferred from a filename; join to the registered original receipt",
            })
    grouped = Counter((r["input_arm"], r["runtime_from_provenance"] or "unrecorded",
                       r["variant"]) for r in rows)
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(root), "ignored_files_included": True,
        "scope": [str(p.relative_to(root)) for p in roots],
        "interpretation": "Stored validation is historical evidence, not a current revalidation. Snapshots and aggregate evaluations are preserved but not counted as independent records/ratings. No score-based selection.",
        "generation_records": rows, "individual_evaluation_files": evaluations,
        "preservation_files": pins,
        "summary": {
            "generation_records": len(rows), "individual_evaluation_files": len(evaluations),
            "preservation_files": len(pins),
            "record_parse_errors": sum(r["record_parse_error"] is not None for r in rows),
            "records_with_duplicate_keys": sum(bool(r["duplicate_keys"]) for r in rows),
            "cells": [{"input_arm": arm, "runtime": runtime, "variant": variant, "count": n}
                      for (arm, runtime, variant), n in sorted(grouped.items())],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.source_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # A registration snapshot is immutable once created.
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
