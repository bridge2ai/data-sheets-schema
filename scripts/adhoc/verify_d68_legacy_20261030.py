#!/usr/bin/env python3
"""D68/#5212 review item 1: read-only completed-run verifier, 2026-10-30.
Inputs: provenance path, evidence root, original recorded root. Output: JSON
on stdout only. No client, launch, repair, run-directory write or spending.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from data_sheets_schema.latch_journal import verify_completed_legacy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("record", type=Path)
parser.add_argument("--evidence-root", required=True, type=Path)
parser.add_argument("--recorded-root", required=True, type=Path)
args = parser.parse_args()
print(json.dumps(verify_completed_legacy(args.record, evidence_root=args.evidence_root,
                                        recorded_root=args.recorded_root), indent=2))
