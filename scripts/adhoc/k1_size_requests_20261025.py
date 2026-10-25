#!/usr/bin/env python3
"""K1 offline stage sizing, 2026-10-25; inputs: A16 tree/historical records.

Outputs: pinned per-record plans and A1 stage estimates in a new JSON file.
Serves K1/#5112/#5150/#5155/#5157. No provider or token-count endpoint is used.
The inherited A1 helper supplies production builders and explicit synthetic
carry assumptions; this adds exact indivisible-root planning bounds and current
CHORUS originals. All synthetic files stay in the requested scratch directory.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def planning_bounds(batches, text):
    """Exact minima for whole-root packing, then lexicographic four-worker fit.

    There is no single joint minimum across paths, bytes and workers. First
    minimize each per-worker bound independently over indivisible roots, then
    use the worker count that greedy production packing actually needs. The
    separate four-worker point minimizes paths, then bytes, for that worker cap.
    """
    inventory, roots = batches._inventory(text)
    grouped = {root: [] for root in roots}
    for row in inventory["values"]:
        root = batches._pointer(batches._tokens(row["path"])[:1])
        grouped[root].append(row)
    rows = [{"root": root, "paths": len(grouped[root]),
             "inventory_bytes": len(batches.canonical_bytes(sorted(
                 grouped[root], key=lambda row: row["path"].encode("utf-8"))))}
            for root in roots]
    paths = max([1, *(r["paths"] for r in rows)])
    byte_count = max([len(batches.canonical_bytes([])), *(r["inventory_bytes"] for r in rows)])
    unlimited_workers = max(1, len(roots))
    smallest = batches.make_plan(text, max_paths=paths, max_inventory_bytes=byte_count,
                                 max_workers=unlimited_workers, version=2)
    limits = {"max_paths": paths, "max_inventory_bytes": byte_count,
              "max_workers": len(smallest["workers"])}
    minimal_plan = batches.make_plan(text, **limits, version=2)
    total_paths = len(inventory["values"])
    total_bytes = len(batches.canonical_bytes(inventory["values"]))

    def fits(p, b):
        try:
            return batches.make_plan(text, max_paths=p, max_inventory_bytes=b,
                                     max_workers=4, version=2)
        except batches.AuditBatchError:
            return None

    # Monotone capacity search: the production ordered greedy partition cannot
    # need more workers when either per-worker capacity grows.
    low, high = paths, max(paths, total_paths)
    while low < high:
        mid = (low + high) // 2
        if fits(mid, total_bytes) is None:
            low = mid + 1
        else:
            high = mid
    four_paths = low
    low, high = byte_count, max(byte_count, total_bytes)
    while low < high:
        mid = (low + high) // 2
        if fits(four_paths, mid) is None:
            low = mid + 1
        else:
            high = mid
    four = fits(four_paths, low)
    if four is None:
        raise AssertionError("four-worker bound failed after monotone search")
    return {"inventory_path_count": total_paths, "inventory_bytes": total_bytes,
            "indivisible_roots": rows, "componentwise_minimum": limits,
            "minimum_plan": minimal_plan,
            "four_worker_lexicographic_point": {
                "limits": {"max_paths": four_paths, "max_inventory_bytes": low, "max_workers": 4},
                "actual_workers": len(four["workers"]), "plan_sha256": four["sha256"]},
            "limits_scope": "Exact for this staged record only; future output is unknown."}


def chorus_files(base, label):
    core = base / "data/d4d_concatenated/claudecode_api_core" / label
    full = base / "data/d4d_concatenated/claudecode_api" / label
    pick = lambda *paths: next((p for p in paths if p.is_file()), None)
    return {"original_full": core / "intermediate/CHORUS_full.yaml",
            "original_core": core / "intermediate/CHORUS_core.yaml",
            "receipt": core / "CHORUS_coverage_receipt.yaml",
            "reconciled_full": pick(core / "intermediate/CHORUS_reconcile_full.yaml", full / "CHORUS_d4d.yaml"),
            "completed_core": pick(core / "intermediate/CHORUS_reconcile_core.yaml", core / "CHORUS_d4d_core.yaml"),
            "report": pick(core / "intermediate/CHORUS_report.md")}


def measure(sizing, modules, project, label, source_files, workdir, *, required_chorus=False):
    workdir.mkdir(parents=True, exist_ok=False)
    copied = workdir / "source_records"
    copied.mkdir()
    pins, selected_files = {}, {}
    for role, path in source_files.items():
        if path is None:
            selected_files[role] = None
            continue
        pins[role] = pin(path)
        selected_files[role] = copied / f"{role}{path.suffix}"
        shutil.copyfile(path, selected_files[role])
        if pin(selected_files[role])["sha256"] != pins[role]["sha256"]:
            raise AssertionError("source copy changed")
    raw = selected_files["original_full"].read_text(encoding="utf-8")
    text = modules.api.normalise_record_text(raw, phase="full")
    text, edits, unfixable = sizing.conform_record(text, modules.api.FULL_SCHEMA_PATH)
    bounds = planning_bounds(modules.audit_batches, text)
    limits = ({"max_paths": 80, "max_inventory_bytes": 12288, "max_workers": 4}
              if required_chorus else bounds["componentwise_minimum"])
    # A1's full builder is reused without changing any production module.
    # It expects root-relative artifact names; exact source copies above satisfy
    # that convention while their read-only original authority remains pinned.
    old_files = sizing.run_files
    sizing.run_files = lambda root, record_project, selected_label: selected_files
    try:
        measured = sizing.size_one(modules, project, label, limits, workdir / "sizing")
    finally:
        sizing.run_files = old_files
    unchanged = all(pin(Path(value["path"])) == value for value in pins.values())
    if not unchanged:
        raise RuntimeError("a source artifact changed during sizing")
    return {"project": project, "label": label, "record_proxy_for": sizing.PROXY.get(project),
            "source_files": pins, "source_files_unchanged": unchanged,
            "staged_record_bytes": len(text.encode("utf-8")),
            "staged_record_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "staged_record_conformance_edits": edits, "staged_record_unfixable": unfixable,
            "planning": bounds, "selected_limits": limits, "measurements": measured}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--historical-root", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--all-replicates", action="store_true")
    parser.add_argument("--projects", nargs="+")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    sys.path[:0] = [str(root), str(root / "src")]
    from scripts import offline_sizing as sizing
    sizing.block_network()
    os.chdir(root)
    os.environ.pop("D4D_RECEIPT_FULL_MAX_TOKENS", None)
    modules = sizing.load(root)
    args.workdir = args.workdir.resolve()
    args.workdir.mkdir(parents=True, exist_ok=False)
    rows = []
    for project in args.projects or sizing.PROJECTS:
        if project == "CHORUS":
            labels = ["2026-10-22a_claude-opus-5-api-generic-v10_rep1",
                      "2026-10-20a_claude-opus-5-api-generic-v10_rep1"]
            files = [(label, chorus_files(args.historical_root.resolve(), label)) for label in labels]
        else:
            record_project = sizing.PROXY.get(project, project)
            labels = sizing.RUNS[record_project]
            files = [(label, sizing.run_files(root, record_project, label))
                     for label in (labels if args.all_replicates else labels[:1])]
        for index, (label, selected) in enumerate(files):
            row = measure(sizing, modules, project, label, selected,
                          args.workdir / f"{project}_{index}", required_chorus=project == "CHORUS")
            rows.append(row)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            # Atomic incremental checkpoint lets the budget work consume each
            # completed project without a second expensive construction sweep.
            report = {"format": "k1_request_sizing_v1", "root_head": sizing._head(root),
                      "root_dirty_paths": sizing._dirty(root), "script": pin(__file__),
                      "source_helper": pin(sizing.__file__), "rows": rows,
                      "network_attempts": list(sizing.NETWORK_ATTEMPTS),
                      "complete": False, "scope": "Offline estimates, not counts or launch clearance."}
            temp = args.out.with_suffix(args.out.suffix + ".partial")
            temp.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            print(f"{project} {label}: {sizing._summary(row['measurements'])}", flush=True)
    if sizing.loaded_from(root) or sizing.NETWORK_ATTEMPTS:
        raise RuntimeError("sizing origin or network restriction failed")
    report["complete"] = True
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
