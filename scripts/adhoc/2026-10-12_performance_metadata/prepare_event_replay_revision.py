#!/usr/bin/env python3
"""Freeze the root-approved retention-cap-only event replay successor.

Purpose: preserve01 and bind02 raising the event bound to131,072.
Inputs: --root owned checkout, --prior frozen01 package, --output new package.
Outputs: before/after source, patch, documentation and freeze.json.
Issue: bridge2ai/data-sheets-schema#5015; no PR yet. Date: 2026-10-12.
Only stdlib metadata/source reads and external artifact writes; no imports/tests.
"""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = ("src/data_sheets_schema/audit_omissions.py", "src/data_sheets_schema/typed_audit.py",
             "tests/test_schema_event_replay.py")
    contents = []
    for rel in paths:
        old = (args.prior / "after" / rel).read_bytes()
        new = (args.root / rel).read_bytes()
        expected = old.replace(b"MAX_SCHEMA_EVENTS = 65_536", b"MAX_SCHEMA_EVENTS = 131_072", 1) if rel == paths[0] else old
        if new != expected:
            raise RuntimeError("unexpected successor source delta: " + rel)
        ast.parse(new.decode(), feature_version=(3, 9))
        contents.append(((args.prior / "before" / rel).read_bytes(), new))
    args.output.mkdir(parents=True, exist_ok=False)
    patch = []
    for rel, (old, new) in zip(paths, contents):
        for directory, raw in (("before", old), ("after", new)):
            target = args.output / directory / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        patch.extend(difflib.unified_diff(old.decode().splitlines(True), new.decode().splitlines(True),
                                        fromfile="a/" + rel if old else "/dev/null", tofile="b/" + rel))
    (args.output / "change.patch").write_text("".join(patch))
    for name in ("design.md", "README.md"):
        text = (args.prior / name).read_text().replace("65,536", "131,072")
        text += "\nSuccessor02 changes only the event-retention default, following root/reviewer agreement. The prior44-case module is unchanged. Root reported126 focused cases passed on01 (10.19s); this is predecessor evidence, not an executed02 result. No parser/cache contract changed.\n"
        (args.output / name).write_text(text)
    files = [pin(path) for path in sorted(args.output.rglob("*")) if path.is_file()]
    result = {"kind": "schema_event_replay_successor02", "helper": pin(Path(__file__).resolve()),
              "prior": pin(args.prior / "freeze.json"), "source": [pin(args.root / rel) for rel in paths],
              "files": files, "executed": False, "test_cases": 44,
              "change": "65,536 to131,072 retained events; same8M character cap and fallback"}
    target = args.output / "freeze.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(pin(target)))


if __name__ == "__main__":
    main()
