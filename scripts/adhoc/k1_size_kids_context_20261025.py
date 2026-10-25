#!/usr/bin/env python3
"""K1 current Kids First context rerun, 2026-10-25; JSON sizing output only.

The recovered A1 helper predates the committed Kids First omission context and
synthesizes a draft. Reuse its production request builders but stage the exact
A16 context instead. The AI_READI record and minimal receipt remain explicit
proxies. No provider access, source edits, or launch authorization.
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
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    sys.path[:0] = [str(root), str(root / "src")]
    from scripts import offline_sizing as sizing
    from scripts.adhoc.k1_size_requests_20261025 import measure, pin
    sizing.block_network()
    os.chdir(root)
    os.environ.pop("D4D_RECEIPT_FULL_MAX_TOKENS", None)
    modules = sizing.load(root)
    from data_sheets_schema import resources
    if Path(resources.resource_root()[0]).resolve() != root:
        raise RuntimeError("resources did not resolve from selected root")
    context = root / "data/omission_contexts/kids_first_omission_context.json"
    context_pin = pin(context)

    def retain_current_context(project, *, source_manifest_path, context_path, write_to_disk):
        if project != "KIDS_FIRST" or not write_to_disk:
            raise AssertionError("unexpected context staging request")
        if pin(context) != context_pin:
            raise RuntimeError("current context changed")
        Path(context_path).write_bytes(context.read_bytes())
        return json.loads(context.read_bytes())

    modules.build_draft_context = retain_current_context
    label = sizing.RUNS["AI_READI"][0]
    row = measure(sizing, modules, "KIDS_FIRST", label,
                  sizing.run_files(root, "AI_READI", label), args.workdir.resolve())
    row.update(context_basis="Exact committed A16 Kids First omission context; replaces inherited A1 draft.",
               omission_context=context_pin,
               replaces="KIDS_FIRST row in request-sizing-primary.json (which used inherited draft context)")
    if pin(context) != context_pin or sizing.loaded_from(root) or sizing.NETWORK_ATTEMPTS:
        raise RuntimeError("context, module origin, or network restriction changed")
    report = {"format": "k1_request_sizing_v1", "root_head": sizing._head(root),
              "script": pin(__file__), "rows": [row], "complete": True,
              "network_attempts": list(sizing.NETWORK_ATTEMPTS),
              "scope": "Actual context with historical record/minimal-receipt proxies; offline estimate only."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(sizing._summary(row["measurements"]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
