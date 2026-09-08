#!/usr/bin/env python3
"""Write the evaluation hash manifest that `tests/test_evaluation_coverage.py` reads.

The archive convention says a superseded evaluation is copied, byte-identical,
into a `superseded_*/` directory before the replacement is written at the
canonical path. Nothing enforced that: the AI_READI and CHORUS controls were
overwritten during the 2026-09-08 rescores with no archived predecessor, and an
ignore-independent search finds no copy of either (#1084).

The manifest records, per live evaluation, the hash it currently has and the
hashes it has had before. Regenerate it whenever an evaluation is rescored,
after archiving the file being replaced, and read the diff: a `sha256` that
moves with nothing added to `archived` is an unarchived overwrite, stated in
the diff rather than invisible.

    python scripts/evaluation_manifest.py            # report drift
    python scripts/evaluation_manifest.py --write    # rewrite the manifest
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "data" / "evaluation_manifest.json"
RUBRICS = ("rubric10_semantic", "rubric20_semantic")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def live_and_archived():
    """Return {"rubric/name": live_hash} and {"rubric/name": {archived hashes}}."""
    live, archived = {}, {}
    for rubric in RUBRICS:
        base = ROOT / "data" / "evaluation_llm" / rubric / "label_aware"
        if not base.exists():
            continue
        for p in sorted(base.glob("*_evaluation.json")):
            live[f"{rubric}/{p.name}"] = sha256(p)
        for d in sorted(base.glob("superseded_*")):
            for p in sorted(d.glob("*_evaluation.json")):
                archived.setdefault(f"{rubric}/{p.name}", set()).add(sha256(p))
    return live, archived


def build(previous):
    live, archived = live_and_archived()
    out = {}
    for key, digest in sorted(live.items()):
        was = previous.get(key, {})
        history = set(was.get("archived", []))
        old = was.get("sha256")
        if old and old != digest and old in archived.get(key, set()):
            history.add(old)
        out[key] = {"sha256": digest, "archived": sorted(history)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    previous = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    current = build(previous)
    if args.write:
        MANIFEST.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n")
        print(f"wrote {MANIFEST.relative_to(ROOT)}: {len(current)} evaluations")
        return
    moved = [k for k, v in current.items()
             if previous.get(k, {}).get("sha256") not in (None, v["sha256"])]
    added = sorted(set(current) - set(previous))
    removed = sorted(set(previous) - set(current))
    print(f"{len(current)} live evaluations; {len(moved)} moved, "
          f"{len(added)} added, {len(removed)} removed")
    for k in moved + added + removed:
        print("  " + k)


if __name__ == "__main__":
    main()
