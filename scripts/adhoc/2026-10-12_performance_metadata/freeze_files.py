#!/usr/bin/env python3
"""Pin explicit files or compare documented helper migrations without imports.

Purpose: reproducible static evidence manifests for the performance work.
Inputs: --file paths and/or --pair ORIGINAL MIGRATED, --note, --issue.
Output: a new --output JSON manifest (existing output is never overwritten).
Issue: bridge2ai/data-sheets-schema#5015. Date: 2026-10-12.
No project imports, tests, benchmarks or source mutations are performed.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def pin(path):
    path = Path(path).absolute()
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--pair", nargs=2, action="append", default=[])
    parser.add_argument("--note", action="append", default=[])
    parser.add_argument("--issue", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    files = [pin(path) for path in args.file]
    pairs = []
    for original, migrated in args.pair:
        old, new = Path(original), Path(migrated)
        row = {"original": pin(old), "migrated": pin(new),
               "bytes_equal": old.read_bytes() == new.read_bytes()}
        if old.suffix == new.suffix == ".py":
            old_ast = ast.parse(old.read_text(), feature_version=(3, 9))
            new_ast = ast.parse(new.read_text(), feature_version=(3, 9))
            row["python39_ast_equal"] = ast.dump(old_ast) == ast.dump(new_ast)
        pairs.append(row)
    expected = files + [row[key] for row in pairs for key in ("original", "migrated")]
    if any(pin(row["path"]) != row for row in expected):
        raise RuntimeError("input changed while metadata was captured")
    output = {"kind": "explicit_performance_file_manifest", "issue": args.issue,
              "date": "2026-10-12", "helper": pin(__file__), "files": files,
              "pairs": pairs, "notes": args.note, "project_runtime_executed": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2)
        stream.write("\n")
    print(json.dumps(pin(args.output)))


if __name__ == "__main__":
    main()
