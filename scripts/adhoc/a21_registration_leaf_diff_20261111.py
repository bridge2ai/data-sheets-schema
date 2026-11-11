#!/usr/bin/env python3
"""Leaf-by-leaf comparison of two A21 registration packets.

Purpose: step 1.5 of the A21 rebuild runbook (the lead's own mechanical part
  of the re-review). Flattens the registration, sizing record and roster of
  the old (M4) and new packets to JSON-pointer leaves and reports every leaf
  that was added, removed or changed. After substituting the two labels, a
  changed leaf is classified only by rules that can be checked from the files
  themselves: a sha256 that equals the bytes of a named repository file at the
  new commit, the commit id, the registration/sizing/roster cross-hashes, or
  "other" (to be explained by a reader). Nothing is classified by guesswork.
Inputs: --old-dir, --new-dir (packet directories), --old-label, --new-label,
  --repo (a checkout whose object store holds both commits), --old-commit,
  --new-commit.
Outputs: one JSON file (--output) and a short text summary on stdout. Reads
  only; writes only --output.
Serves: owner decision D131 (2026-11-11); the A21 CHORUS re-canary.
Date: 2026-11-11
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def flatten(node, pointer=""):
    """Yield (json pointer, scalar) for every leaf; empty containers are leaves."""
    if isinstance(node, dict):
        if not node:
            yield pointer, {}
        for key in node:
            yield from flatten(node[key], f"{pointer}/{key}")
    elif isinstance(node, list):
        if not node:
            yield pointer, []
        for index, item in enumerate(node):
            yield from flatten(item, f"{pointer}/{index}")
    else:
        yield pointer, node


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha256(repo: Path, commit: str, path: str) -> str | None:
    proc = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"],
                          capture_output=True)
    if proc.returncode != 0:
        return None
    return hashlib.sha256(proc.stdout).hexdigest()


def tracked_hashes(repo: Path, commit: str) -> dict[str, list[str]]:
    """sha256 of every tracked blob under the paths a registration can pin."""
    listing = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", commit, "--",
         "src", ".claude", ".github", "data/preprocessed", "data/omission_contexts",
         "config", "scripts"],
        capture_output=True, text=True, check=True).stdout.splitlines()
    out: dict[str, list[str]] = {}
    for path in listing:
        digest = git_blob_sha256(repo, commit, path)
        if digest:
            out.setdefault(digest, []).append(path)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-dir", required=True, type=Path)
    ap.add_argument("--new-dir", required=True, type=Path)
    ap.add_argument("--old-label", required=True)
    ap.add_argument("--new-label", required=True)
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--old-commit", required=True)
    ap.add_argument("--new-commit", required=True)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    names = {
        "registration": "registration_chorus_{label}.json",
        "sizing": "registration_chorus_{label}.sizing.json",
        "roster": "roster_{label}.json",
    }
    old_files = {k: args.old_dir / v.format(label=args.old_label) for k, v in names.items()}
    new_files = {k: args.new_dir / v.format(label=args.new_label) for k, v in names.items()}
    file_hashes = {
        "old": {k: sha256_file(p) for k, p in old_files.items()},
        "new": {k: sha256_file(p) for k, p in new_files.items()},
    }
    file_bytes = {
        "old": {k: p.stat().st_size for k, p in old_files.items()},
        "new": {k: p.stat().st_size for k, p in new_files.items()},
    }
    new_blob = tracked_hashes(args.repo, args.new_commit)
    old_blob = tracked_hashes(args.repo, args.old_commit)
    old_packet_hashes = {v: k for k, v in file_hashes["old"].items()}
    new_packet_hashes = {v: k for k, v in file_hashes["new"].items()}

    def norm_old(value):
        """Old value with the old label rewritten to the new one."""
        if isinstance(value, str):
            return value.replace(args.old_label, args.new_label)
        return value

    report = {"inputs": {
        "old_dir": str(args.old_dir), "new_dir": str(args.new_dir),
        "old_label": args.old_label, "new_label": args.new_label,
        "old_commit": args.old_commit, "new_commit": args.new_commit,
        "file_sha256": file_hashes, "file_bytes": file_bytes}, "documents": {}}

    for kind in names:
        old = dict(flatten(json.loads(old_files[kind].read_text())))
        new = dict(flatten(json.loads(new_files[kind].read_text())))
        added = sorted(set(new) - set(old))
        removed = sorted(set(old) - set(new))
        rows = []
        counts: dict[str, int] = {}
        for pointer in sorted(set(old) & set(new)):
            a, b = old[pointer], new[pointer]
            if a == b:
                continue
            if norm_old(a) == b:
                cls = "label_only"
            elif isinstance(b, str) and HEX40.match(b) and b == args.new_commit and a == args.old_commit:
                cls = "commit"
            elif isinstance(b, str) and HEX64.match(b) and b in new_packet_hashes \
                    and isinstance(a, str) and a in old_packet_hashes \
                    and old_packet_hashes[a] == new_packet_hashes[b]:
                cls = f"packet_cross_hash:{new_packet_hashes[b]}"
            elif isinstance(b, str) and HEX64.match(b) and b in new_blob \
                    and isinstance(a, str) and a in old_blob \
                    and set(old_blob[a]) & set(new_blob[b]):
                shared = sorted(set(old_blob[a]) & set(new_blob[b]))
                cls = "file_bytes:" + ",".join(shared)
            else:
                cls = "other"
            counts[cls] = counts.get(cls, 0) + 1
            rows.append({"pointer": pointer, "old": a, "new": b, "class": cls})
        report["documents"][kind] = {
            "leaves_old": len(old), "leaves_new": len(new),
            "equal": len(set(old) & set(new)) - len(rows),
            "changed": len(rows), "changed_by_class": dict(sorted(counts.items())),
            "added": [{"pointer": p, "new": new[p]} for p in added],
            "removed": [{"pointer": p, "old": old[p]} for p in removed],
            "rows": rows,
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    for kind, doc in report["documents"].items():
        print(f"{kind}: {doc['leaves_old']} -> {doc['leaves_new']} leaves; "
              f"equal {doc['equal']}, changed {doc['changed']}, "
              f"added {len(doc['added'])}, removed {len(doc['removed'])}")
        for cls, n in doc["changed_by_class"].items():
            print(f"    {n:4d}  {cls}")
    print(f"wrote {args.output} sha256={sha256_file(args.output)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
