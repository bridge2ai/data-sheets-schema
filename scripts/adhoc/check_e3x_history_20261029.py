"""E3x F1-F12, 2026-10-29: verify history blob sizes and protected paths.

Inputs: baseline SHA and optional head (default HEAD), real checkout cwd.
Outputs: JSON on stdout; nonzero for blobs over 1,000,000 bytes or forbidden edits.
No network or writes. Includes all reachable new objects, not just the final tree.
"""
import json
import subprocess
import sys


def git(*args, **kwargs):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True, **kwargs).stdout


base, head = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "HEAD"
objects = git("rev-list", "--objects", head, "^" + base)
sizes = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize) %(rest)", input=objects)
blobs = []
for line in sizes.splitlines():
    fields = line.split(" ", 3)
    if fields[1] == "blob":
        blobs.append({"sha": fields[0], "bytes": int(fields[2]), "path": fields[3] if len(fields) > 3 else ""})
paths = git("diff", "--name-only", base, head).splitlines()
forbidden = [p for p in paths if p.startswith("data/") or p.endswith(("shared_generation.py", "canonical_hashes.yaml", "STATUS.md"))
             or p == "scripts/build_api_registrations.py" or "/decisions/" in p]
large = [b for b in blobs if b["bytes"] > 1_000_000]
print(json.dumps({"base": git("rev-parse", base).strip(), "head": git("rev-parse", head).strip(),
                  "new_blobs": len(blobs), "largest_blobs": sorted(blobs, key=lambda b: b["bytes"], reverse=True)[:5],
                  "blobs_over_1MB": large, "forbidden_paths": forbidden, "changed_paths": paths}, indent=2))
raise SystemExit(bool(large or forbidden))
