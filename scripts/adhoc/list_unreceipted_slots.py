"""List populated record leaves that no coverage-receipt snippet covers.

Purpose: diagnostic for a native D4D run's Phase 1 receipt correction loop.
Calls the repository's own receipt validator (data_sheets_schema.receipts.block_for)
and prints the `slots` block, including the untruncated uncovered-leaf list.
Inputs: --full <full record yaml> --receipt <coverage receipt yaml>
        --bundle <bundle txt> --chunk-manifest <chunks yaml>
Outputs: JSON on stdout (read-only; writes nothing).
Run: AI_READI 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1 (generic-v9 native run).
Date: 2026-11-21
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from data_sheets_schema import receipts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--chunk-manifest", type=Path, required=True)
    a = ap.parse_args()
    block = receipts.block_for(a.full, a.receipt, a.bundle, None, True, manifest=a.chunk_manifest)
    slots = block.get("slots", {})
    receipt = receipts.load_receipt(a.receipt)
    manifest = yaml.safe_load(a.chunk_manifest.read_text())
    lines = a.bundle.read_text().splitlines()
    texts = {c["id"]: "\n".join(lines[c["lines"][0] - 1:c["lines"][1]]) for c in manifest["chunks"]}
    full = yaml.safe_load(a.full.read_text())
    uncovered = receipts.uncovered_receiptable_leaves(receipt, manifest, texts, full)
    out = {k: v for k, v in slots.items() if k != "without_receipt"}
    out["uncovered_all"] = uncovered
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
