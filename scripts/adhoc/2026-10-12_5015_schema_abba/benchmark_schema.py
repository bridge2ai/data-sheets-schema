#!/usr/bin/env python3
"""Compare four real schema admissions in old/new/new/old order.

Purpose: measure #5015 checked-event replay without cProfile or pipeline cost.
Inputs: --root owned checkout, adjacent/--pins manifest, pinned merged schema.
Outputs: new external --output directory with summary.json and input manifest.
Issue: bridge2ai/data-sheets-schema#5015; no PR yet. Date: 2026-10-12.
Root alone executes this script; imports/capture stay outside measured windows.
"""
import argparse
import ast
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time
import traceback


SCHEMA = "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
FILES = (SCHEMA, "src/data_sheets_schema/api_runner.py",
         "src/data_sheets_schema/audit_omissions.py", "src/data_sheets_schema/typed_audit.py",
         "src/data_sheets_schema/schema_snapshot.py", "src/data_sheets_schema/schema_view.py",
         "src/data_sheets_schema/duplicate_keys.py", "src/data_sheets_schema/support_targets.py")


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--pins", type=Path, default=Path(__file__).with_name("input-pins.json"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if root == output or root in output.parents:
        parser.error("output must be outside the checkout")
    configuration = json.loads(args.pins.read_text())
    expected = configuration["files"]
    if [row["path"] for row in expected] != [str(root / rel) for rel in FILES]:
        parser.error("manifest does not bind the exact source/schema file set")
    before = [pin(root / rel) for rel in FILES]
    if before != expected:
        parser.error("input pins differ from current files")
    api = ast.parse((root / "src/data_sheets_schema/api_runner.py").read_text())
    declared = [ast.literal_eval(node.value) for node in api.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "FULL_SCHEMA_PATH" for target in node.targets)]
    if declared != [SCHEMA]:
        parser.error("target differs from actual FULL_SCHEMA_PATH")
    output.mkdir(parents=True, exist_ok=False)
    (output / "input-pins.json").write_text(args.pins.read_text())
    os.chdir(root)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root / "src"))
    from data_sheets_schema import audit_omissions as omissions, schema_snapshot, schema_view
    import yaml
    for module in (omissions, schema_snapshot, schema_view):
        wanted = root / "src" / (module.__name__.replace(".", "/") + ".py")
        if Path(module.__file__).resolve() != wanted:
            raise RuntimeError("unexpected project origin: " + module.__name__)
    captured = schema_snapshot.capture_schema(root / SCHEMA, strict=True)
    if captured.sources[0][1] != root / SCHEMA or hashlib.sha256(captured.sources[0][2]).hexdigest() != before[0]["sha256"]:
        raise RuntimeError("captured root differs from pinned merged schema")
    current = omissions._schema_yaml

    def original_yaml(text):
        # Literal original depth-then-load operation; no admitted-result cache.
        if omissions.nesting_exceeds(text, yaml.SafeLoader, omissions.MAX_DEPTH):
            raise ValueError("depth bound exceeded")
        return yaml.load(text, Loader=omissions._UniqueLoader)

    rows, reference, error = [], None, None
    load_before = list(os.getloadavg())
    restored = False
    try:
        for position, variant in enumerate(("old", "new", "new", "old"), 1):
            if [pin(root / rel) for rel in FILES] != before:
                raise RuntimeError("source changed between admissions")
            omissions._schema_yaml = original_yaml if variant == "old" else current
            load = list(os.getloadavg())
            rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            wall, cpu = time.perf_counter_ns(), time.thread_time_ns()
            try:
                result = omissions._schema(root / SCHEMA, schema_snapshot=captured)
            finally:
                wall_ns, cpu_ns = time.perf_counter_ns() - wall, time.thread_time_ns() - cpu
            encoded = json.dumps(result, sort_keys=True, ensure_ascii=False,
                                 separators=(",", ":"), allow_nan=False).encode()
            if reference is None:
                reference = encoded
            rows.append({"position": position, "variant": variant,
                         "wall_seconds": wall_ns / 1e9, "thread_cpu_seconds": cpu_ns / 1e9,
                         "catalog_bytes": len(encoded), "catalog_sha256": hashlib.sha256(encoded).hexdigest(),
                         "catalog_equal": encoded == reference, "load_before": load,
                         "maxrss_before": rss_before, "maxrss_after": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
            if encoded != reference:
                raise RuntimeError("catalog differs between old and new admission")
    except Exception:
        error = traceback.format_exc()
    finally:
        omissions._schema_yaml = current
        restored = omissions._schema_yaml is current
    after = [pin(root / rel) for rel in FILES]
    summary = {"kind": "schema_admission_abba_v1", "root": str(root), "driver": pin(Path(__file__).resolve()),
               "executable": sys.executable, "python": sys.version, "platform": platform.platform(),
               "packages": {name: metadata.version(name) for name in ("PyYAML", "linkml", "linkml-runtime")},
               "cpu_count": os.cpu_count(), "load_before": load_before, "load_after": list(os.getloadavg()),
               "source_before": before, "source_after": after, "source_preserved": before == after,
               "captured_sources": [{"name": name, "path": str(path), "bytes": len(raw),
                                     "sha256": hashlib.sha256(raw).hexdigest()} for name, path, raw in captured.sources],
               "calls": rows, "error": error, "restored": restored,
               "passed": error is None and restored and before == after and len(rows) == 4,
               "limitations": ["four serial calls, not a statistical significance or pipeline-speed claim",
                               "imports, initial capture, pin checks and result encoding excluded from timing",
                               "only _schema_yaml binding changes; every _schema admission remains fresh",
                               "no branch-count instrumentation; retention fallback is not separately counted",
                               "maxrss is process high-water, bytes on macOS/KiB on Linux, not per-call allocation"]}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in ("passed", "source_preserved", "restored", "error")}))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
