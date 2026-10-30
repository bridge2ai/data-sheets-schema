#!/usr/bin/env python3
"""D68/#5212 review items 1,6,7: import exact f8 before-trees, 2026-10-30.

Input: review capture directory. Output: tests/fixtures/pre_d41 with original
invocations and verified manifests. One case per invocation for canary-first.
Never edits the capture source. CI consumes the plain files, not this script.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("case")
parser.add_argument("--call", type=int, default=2)
args = parser.parse_args()
source = args.source / args.case / f"call-{args.call}"
dest = Path(__file__).resolve().parents[2] / "tests/fixtures/pre_d41" / args.case
manifest = json.loads((source / "before-manifest.json").read_text())
def inventory(root):
    return {str(p.relative_to(root)): {"bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in root.rglob("*") if p.is_file()}
assert inventory(source / "before") == manifest
shutil.copytree(source / "before", dest / "before")
for name in ("invocation.json", "before-manifest.json"):
    shutil.copyfile(source / name, dest / name)
assert inventory(dest / "before") == manifest
print(args.case, len(manifest), "files verified byte-for-byte")
