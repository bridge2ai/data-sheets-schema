#!/usr/bin/env python3
"""K1/A17 planning sensitivity, 2026-10-25: historical records in, JSON out.

Uses production ordered whole-root packing, without request construction or
provider access. Reports per-record minima and a bound envelope that plans every
listed staged record. Future output and unknown proxy-project records remain
outside that guarantee. Serves #5112/#5155 and K1's six-project budget model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--historical-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    sys.path[:0] = [str(root), str(root / "src")]
    from scripts import offline_sizing as sizing
    from scripts.adhoc.k1_size_requests_20261025 import planning_bounds, chorus_files, pin
    sizing.block_network()
    os.chdir(root)
    modules = sizing.load(root)
    from data_sheets_schema import resources
    if Path(resources.resource_root()[0]).resolve() != root:
        raise RuntimeError("resources did not resolve from the selected root")
    projects = {}
    for project in sizing.PROJECTS:
        record_project = sizing.PROXY.get(project, project)
        sources = [(label, sizing.run_files(root, record_project, label)["original_full"])
                   for label in sizing.RUNS[record_project]]
        if project == "CHORUS":
            sources = [(label, chorus_files(args.historical_root.resolve(), label)["original_full"])
                       for label in ("2026-10-22a_claude-opus-5-api-generic-v10_rep1",
                                     "2026-10-20a_claude-opus-5-api-generic-v10_rep1")] + sources
        rows, texts = [], []
        for label, path in sources:
            text = modules.api.normalise_record_text(path.read_text(encoding="utf-8"), phase="full")
            text, edits, unfixable = sizing.conform_record(text, modules.api.FULL_SCHEMA_PATH)
            bounds = planning_bounds(modules.audit_batches, text)
            fixed = {"max_paths": 80, "max_inventory_bytes": 12288, "max_workers": 4}
            try:
                plan = modules.audit_batches.make_plan(text, **fixed, version=2)
                fixed_result = {"status": "plans", "actual_workers": len(plan["workers"])}
            except modules.audit_batches.AuditBatchError as exc:
                fixed_result = {"status": "refused", "reason": str(exc)}
            rows.append({"label": label, "source": pin(path), "record_proxy_for": sizing.PROXY.get(project),
                "staged_bytes": len(text.encode()), "staged_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "conformance_edits": edits, "unfixable": unfixable, "planning": bounds,
                "chorus_bounds_test": fixed_result})
            texts.append(text)
        limits = {key: max(row["planning"]["componentwise_minimum"][key] for row in rows)
                  for key in ("max_paths", "max_inventory_bytes")}
        plans = [modules.audit_batches.make_plan(text, **limits, max_workers=4096, version=2)
                 for text in texts]
        limits["max_workers"] = max(len(plan["workers"]) for plan in plans)
        for text in texts:
            modules.audit_batches.make_plan(text, **limits, version=2)
        projects[project] = {"rows": rows, "known_record_envelope": limits,
                             "envelope_worker_counts": [len(plan["workers"]) for plan in plans]}
        print(f"{project}: {len(rows)} records, envelope {limits}", flush=True)
    if sizing.loaded_from(root) or sizing.NETWORK_ATTEMPTS:
        raise RuntimeError("sizing origin or network restriction failed")
    report = {"format": "k1_plan_sensitivity_v1", "root_head": sizing._head(root),
              "script": pin(__file__), "source_helper": pin(sizing.__file__),
              "full_schema": pin(modules.api.FULL_SCHEMA_PATH), "projects": projects,
              "network_attempts": list(sizing.NETWORK_ATTEMPTS),
              "scope": "Known staged records only; proxy records do not establish future project bounds."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
