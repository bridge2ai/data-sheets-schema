#!/usr/bin/env python3
"""Independent lead check of which files the M4 A21 registration pins have moved.

Purpose: AGY2's handoff on the A21 pinned closure lists file names in prose.
  This walks the M4 registration and its sizing record itself, pairs every
  repository path with the sha256 pinned beside it, and hashes that path's
  bytes at two commits with `git show`. It does not import project code and
  does not use AGY2's script, so it can confirm or contradict AGY2's JSON.
Inputs: the two M4 JSON files under d4d-executions/plans/ (read-only), the
  primary repository's object store (read-only), two commit ids.
Output: JSON on stdout: every (path, pinned sha256) pair and whether the
  bytes at the base commit and at the target commit match the pin.
Limits: finds pins by shape (a "path" beside a "sha256", or a mapping whose
  keys are repository paths and whose values are 64-hex strings). A hash
  pinned under a key that is not a path is out of its reach and is counted
  separately as "hex leaves not paired with a path".
Serves: review of the A21 rebuild runbook (lead transfer 2026-11-11).
Date: 2026-11-11.
"""
import hashlib, json, re, subprocess, sys
from pathlib import Path

REPO, BASE, TARGET = sys.argv[1], sys.argv[2], sys.argv[3]
FILES = [Path(p) for p in sys.argv[4:]]
HEX = re.compile(r"^[0-9a-f]{64}$")
PATHLIKE = re.compile(r"^[A-Za-z0-9_.\-]+(/[A-Za-z0-9_.\- ]+)+\.[A-Za-z0-9]+$")

def blob_sha(commit, path):
    out = subprocess.run(["git", "-C", REPO, "show", f"{commit}:{path}"], capture_output=True)
    return hashlib.sha256(out.stdout).hexdigest() if out.returncode == 0 else None

pairs, hex_leaves = {}, 0
def walk(node, pointer, source):
    global hex_leaves
    if isinstance(node, dict):
        p, s = node.get("path"), node.get("sha256")
        if isinstance(p, str) and isinstance(s, str) and HEX.match(s):
            pairs.setdefault((p, s), []).append(f"{source}#{pointer}")
        for k, v in node.items():
            if isinstance(v, str) and HEX.match(v):
                hex_leaves += 1
                if PATHLIKE.match(k):
                    pairs.setdefault((k, v), []).append(f"{source}#{pointer}/{k}")
            walk(v, f"{pointer}/{k}", source)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{pointer}/{i}", source)

for f in FILES:
    walk(json.loads(f.read_text()), "", f.name.split("_2026")[0] + (".sizing" if ".sizing" in f.name else ""))

root = Path(REPO).resolve()
rows = []
for (path, pinned), where in sorted(pairs.items()):
    rel = path
    if path.startswith("/"):
        m = re.search(r"/(src|data|\.claude|\.github|notes|scripts|tests|utils|config|project)/", path)
        rel = path[m.start() + 1:] if m else path
    base, target = blob_sha(BASE, rel), blob_sha(TARGET, rel)
    rows.append({"path": rel, "pinned": pinned, "pointers": len(where),
                 "base_matches_pin": base == pinned, "target_matches_pin": target == pinned,
                 "in_git_at_target": target is not None, "target_sha256": target})
unique_paths = sorted({r["path"] for r in rows})
moved = sorted({r["path"] for r in rows if r["in_git_at_target"] and not r["target_matches_pin"]})
print(json.dumps({
    "base": BASE, "target": TARGET,
    "hex_leaves_seen": hex_leaves, "path_sha_pairs": len(rows), "unique_paths": len(unique_paths),
    "pins_matching_base_bytes": sum(r["base_matches_pin"] for r in rows),
    "pins_not_matching_base_bytes": [r["path"] for r in rows if not r["base_matches_pin"]],
    "moved_at_target": moved,
    "not_in_git_at_target": sorted({r["path"] for r in rows if not r["in_git_at_target"]}),
    "rows": rows}, indent=1))
