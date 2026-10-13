#!/usr/bin/env python3
# Purpose: attribute one real captured-schema admission, excluding imports.
# Inputs: adjacent input-pins.json, owned checkout and --output external path.
# Outputs: schema.prof, functions.txt, functions.json, summary.json.
# Issue: bridge2ai/data-sheets-schema#5015; no PR yet. Date: 2026-10-12.
# Migration: header only; historical input pins require a new revision to rerun.
"""Profile one real schema admission; imports and capture are outside the window."""
import argparse
import ast
import cProfile
import hashlib
from importlib import metadata
import io
import json
import os
from pathlib import Path
import pstats
import sys
import time
import traceback


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(Path(__file__).with_name("input-pins.json").read_text())
    root = Path(config["root"]).resolve()
    output = args.output.resolve()
    if output.is_relative_to(root):
        parser.error("profile output must be outside the checkout")
    output.mkdir(parents=True, exist_ok=False)

    def pins():
        return [{"path": row["path"], "bytes": len(raw), "sha256": digest(raw)}
                for row in config["files"] for raw in [(root / row["path"]).read_bytes()]]

    before = pins()
    if before != config["files"]:
        raise RuntimeError("source/schema pins changed before profiling")
    schema = root / config["schema"]
    module = ast.parse((root / "src/data_sheets_schema/api_runner.py").read_text())
    declared = [ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "FULL_SCHEMA_PATH" for target in node.targets)]
    if declared != [config["schema"]]:
        raise RuntimeError("target differs from actual FULL_SCHEMA_PATH")
    os.chdir(root)
    sys.path.insert(0, str(root / "src"))
    sys.dont_write_bytecode = True
    sys.pycache_prefix = str(output / "unused-pycache")
    from data_sheets_schema import audit_omissions as omissions, schema_snapshot, schema_view
    for loaded in (omissions, schema_snapshot, schema_view):
        expected = root / "src" / (loaded.__name__.replace(".", "/") + ".py")
        if Path(loaded.__file__).resolve() != expected:
            raise RuntimeError(f"unexpected module origin: {loaded.__name__}")
    # This warms only the normal capture metadata, as the real runtime does.
    captured = schema_snapshot.capture_schema(schema, strict=True)
    source_rows = [{"name": str(name), "path": str(path), "bytes": len(raw), "sha256": digest(raw)}
                   for name, path, raw in captured.sources]
    if captured.sources[0][1] != schema or digest(captured.sources[0][2]) != config["schema_sha256"]:
        raise RuntimeError("captured root differs from pinned merged schema")
    profiler = cProfile.Profile()
    result = None
    error = None
    wall_start, cpu_start = time.perf_counter_ns(), time.thread_time_ns()
    try:
        # Exactly one call, with the literal default no-catalog-cache behavior.
        result = profiler.runcall(omissions._schema, schema, schema_snapshot=captured)
    except Exception:
        error = traceback.format_exc()
    wall_ns, cpu_ns = time.perf_counter_ns() - wall_start, time.thread_time_ns() - cpu_start
    profiler.dump_stats(str(output / "schema.prof"))
    text = io.StringIO()
    stats = pstats.Stats(profiler, stream=text).sort_stats("cumulative")
    stats.print_stats(50)
    stats.print_stats("audit_omissions|schema_snapshot|schema_view|duplicate_keys|support_targets|yaml/")
    (output / "functions.txt").write_text(text.getvalue())
    rows = []
    for (filename, line, name), (primitive, calls, own, cumulative, callers) in stats.stats.items():
        rows.append({"file": filename, "line": line, "name": name, "primitive_calls": primitive,
                     "calls": calls, "self_seconds": own, "cumulative_seconds": cumulative,
                     "callers": [{"file": key[0], "line": key[1], "name": key[2], "counts_times": value}
                                 for key, value in sorted(callers.items())]})
    rows.sort(key=lambda row: row["cumulative_seconds"], reverse=True)
    (output / "functions.json").write_text(json.dumps(rows, indent=2) + "\n")
    after = pins()
    encoded = None if result is None else json.dumps(result, sort_keys=True, ensure_ascii=False,
                                                     separators=(",", ":"), allow_nan=False).encode()
    summary = {"kind": "one_schema_admission_profile", "root": str(root),
               "executable": sys.executable, "python": sys.version, "schema": str(schema),
               "packages": {name: metadata.version(name) for name in ("PyYAML", "linkml", "linkml-runtime")},
               "measured_calls": 1, "catalog_cache": None, "wall_seconds": wall_ns / 1e9,
               "thread_cpu_seconds": cpu_ns / 1e9, "error": error, "source_before": before,
               "source_after": after, "source_preserved": before == after,
               "captured_sources": source_rows, "catalog_bytes": None if encoded is None else len(encoded),
               "catalog_sha256": None if encoded is None else digest(encoded),
               "limits": ["cProfile attribution, not an uninstrumented timing comparison",
                          "imports and initial schema capture excluded; fresh admission replay included",
                          "cumulative function times overlap; no full pipeline executed"]}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in ("measured_calls", "wall_seconds", "thread_cpu_seconds", "error", "source_preserved")}))
    return 1 if error is not None or before != after else 0


if __name__ == "__main__":
    raise SystemExit(main())
