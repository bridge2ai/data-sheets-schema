#!/usr/bin/env python3
"""Publish a fresh deterministic label and its immutable evidence manifest."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.deterministic_publication import METHODS, prepare, publish


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=tuple(METHODS), required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--project", action="append", required=True)
    parser.add_argument("--packages-dir", type=Path, default=Path("data/ro-crate_packages"))
    parser.add_argument("--concat-dir", type=Path, default=Path("data/d4d_concatenated"))
    parser.add_argument("--code-commit", required=True)
    args = parser.parse_args(argv)
    prepared = prepare(ROOT, args.packages_dir, args.concat_dir, args.method, args.label, args.project)
    if prepared["code_commit"] != args.code_commit:
        parser.error("expected code commit differs from current producer HEAD")
    manifest = publish(prepared)
    print(json.dumps({"state": manifest["state"], "method": manifest["method"],
                      "label": manifest["label"], "code_commit": manifest["code_commit"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
