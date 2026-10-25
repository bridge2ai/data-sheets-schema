#!/usr/bin/env python3
"""K1 primary sizing authority supplement, 2026-10-25, offline only.

Inputs: retained primary sizing JSON and its seven scratch registrations.
Outputs: exact registrations, validated input/asset pins, and Git source delta.
This is a post-run preservation/check, not retroactive loaded-code attestation.
Serves K1/#5150 provenance without repeating expensive request construction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def validate_pins(value, collected):
    if isinstance(value, dict):
        if {"path", "sha256", "bytes"} <= value.keys():
            actual = pin(value["path"])
            if actual != {key: value[key] for key in actual}:
                raise ValueError(f"changed pin: {value['path']}")
            collected[actual["path"]] = actual
        for child in value.values():
            validate_pins(child, collected)
    elif isinstance(value, list):
        for child in value:
            validate_pins(child, collected)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--measurements", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    report = json.loads(args.measurements.read_bytes())
    rows, collected = [], {}
    for row in report["rows"]:
        source = root / row["measurements"]["inputs"]["original_full"]
        case = source.parent.parent
        path = case / "sizing" / f"{row['project']}_registration.json"
        registration = json.loads(path.read_bytes())
        validate_pins(registration, collected)
        validate_pins(row["source_files"], collected)
        for relative, digest in registration["selection"]["assets"].items():
            asset = pin(root / relative)
            if asset["sha256"] != digest:
                raise ValueError(f"changed registered asset: {relative}")
            collected[asset["path"]] = asset
        rows.append({"project": row["project"], "source_label": row["label"],
                     "registration_pin": pin(path), "registration": registration})
    guarded = ["src/data_sheets_schema", "scripts/build_api_registrations.py",
               "data/omission_contexts", "src/download/prompts", ".claude/commands",
               ".claude/agents", "data/preprocessed", "notes/matched_cborg_2026-09-13/kids_first"]
    delta = subprocess.run(["git", "-C", str(root), "diff", "--name-status", "56c41163f", "--", *guarded],
                           check=True, capture_output=True, text=True).stdout.splitlines()
    if delta != ["A\tsrc/data_sheets_schema/offline_sizing.py"]:
        raise ValueError(f"unexpected production/input tree delta: {delta}")
    out = {"format": "k1_primary_authorities_v1", "source_base": "56c41163f8b64119656b8aa2edef9c97707a3826",
           "initial_helper_commit": "41b90911c", "measurement_pin": pin(args.measurements),
           "script": pin(__file__), "registrations": rows, "current_validated_pins": collected,
           "guarded_git_paths": guarded, "source_delta": delta,
           "scope": "Post-run retained authority preservation and freshness check; not retroactive loaded-code proof."}
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(out, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(f"Preserved {len(rows)} registrations; verified {len(collected)} input/asset paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
