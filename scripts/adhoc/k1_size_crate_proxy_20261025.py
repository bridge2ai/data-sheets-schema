#!/usr/bin/env python3
"""K1/D04 B conditional crate scenario, 2026-10-25; no provider calls.

Inputs: exact A16 with-crate bundle/chunks and July31 CHORUS final records.
Outputs: sizing JSON with explicit final-record/minimal-receipt proxy caveats.
No CHORUS baseline partition profile is reused or certified for this arm.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--historical-root", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--all-replicates", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    sys.path[:0] = [str(root), str(root / "src")]
    from scripts import offline_sizing as sizing
    from scripts.adhoc.k1_size_requests_20261025 import measure, pin, chorus_files
    sizing.block_network()
    os.chdir(root)
    os.environ.pop("D4D_RECEIPT_FULL_MAX_TOKENS", None)
    modules = sizing.load(root)
    from data_sheets_schema import resources
    if Path(resources.resource_root()[0]).resolve() != root:
        raise RuntimeError("resources did not resolve from the selected root")
    args.workdir = args.workdir.resolve()
    args.workdir.mkdir(parents=True, exist_ok=False)
    original_build = modules.build_registration

    def build(*a, **kw):
        kw["arm"] = "de_novo"
        return original_build(*a, **kw)

    modules.build_registration = build
    original_stage = sizing.stage_run

    def stage(*a, **kw):
        kw["proxy"] = True
        return original_stage(*a, **kw)

    sizing.stage_run = stage
    bundle = root / "data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt"
    chunks = root / "data/preprocessed/chunks/CHORUS_preprocessed_with_crate_chunks.yaml"
    context = root / "data/omission_contexts/chorus_omission_context.json"
    sizing.inputs_for = lambda *a: (bundle, chunks, context, [])
    # A1's stage_run reads a receipt before replacing it with its explicit
    # minimal-receipt proxy. This preserved source receipt is never represented
    # as evidence for the with-crate bytes.
    receipt = chorus_files(args.historical_root.resolve(),
        "2026-10-22a_claude-opus-5-api-generic-v10_rep1")["receipt"]
    rows = []
    for replicate in range(1, 4 if args.all_replicates else 2):
        label = f"2026-07-31_claude-opus-5-api-generic_rep{replicate}"
        full = root / "data/d4d_concatenated/claudecode_agent_crate" / label / "CHORUS_d4d.yaml"
        core = root / "data/d4d_concatenated/claudecode_agent_crate_core" / label / "CHORUS_d4d_core.yaml"
        files = {"original_full": full, "original_core": core, "receipt": receipt,
                 "reconciled_full": full, "completed_core": core, "report": None}
        row = measure(sizing, modules, "CHORUS", label, files, args.workdir / str(replicate))
        row.update(arm="with_crate", generation_arm="de_novo", conditional_decision="D04 B only", proxy=True,
            proxy_basis="July31 final full/core used as phase1 originals; no original phase1/receipt evidence.",
            receipt_basis="Synthetic nothing_relevant receipt for all target chunks; understates real receipt.",
            future_output_basis="Unknown v10 output; one historical crate-final record scenario.",
            target_inputs={"bundle": pin(bundle), "chunks": pin(chunks), "omission_context": pin(context)})
        rows.append(row)
        print(f"CHORUS with-crate proxy {label}: {sizing._summary(row['measurements'])}", flush=True)
    if sizing.loaded_from(root) or sizing.NETWORK_ATTEMPTS:
        raise RuntimeError("sizing origin or network restriction failed")
    report = {"format": "k1_request_sizing_v1", "root_head": sizing._head(root),
              "script": pin(__file__), "rows": rows, "complete": True,
              "network_attempts": list(sizing.NETWORK_ATTEMPTS),
              "scope": "Conditional D04 B historical-proxy estimates; not counts or launch clearance."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
