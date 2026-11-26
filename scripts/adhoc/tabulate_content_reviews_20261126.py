#!/usr/bin/env python3
"""Tabulate the content reviews (d4d-review-record) of one record series.

Purpose: one manifest row per reviewed record, with the identities that say which
  pack, which review file and which reviewer definition each review rests on, so that
  "every replicate of a project was reviewed on the same definition" can be checked
  from a file. The review block that `d4d review check --write` puts into a provenance
  record holds the pack and review hashes but has no field for the definition.
Inputs (run from the repository root): --method and --config (label prefix); the
  provenance records `data/d4d_concatenated/<method>_core/<label>/<P>_provenance.yaml`,
  the `<P>_review.yaml` and `<P>_review_pack.yaml` beside them; --definition, the
  reviewer definition file the reviews were given.
Outputs: a TSV on stdout. Exit status 1 if a record has a pack but no written review
  block, if a recorded hash does not match the file on disk, if the review file names
  another pack than the block, or (with --expect) if the number of rows differs.
Serves: release series 2026-11-25c, the owner's request of 2026-11-26 to review all 15
  records. Date: 2026-11-26.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--method", required=True)
    parser.add_argument("--config", required=True, help="label prefix of the series")
    parser.add_argument("--definition", default=".claude/agents/d4d-review-record.md")
    parser.add_argument("--expect", type=int, help="number of reviewed records expected")
    args = parser.parse_args()

    definition = Path(args.definition)
    definition_sha = sha256(definition)
    commit = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", str(definition)], capture_output=True, text=True
    ).stdout.strip() or "unknown"
    core = Path("data/d4d_concatenated") / f"{args.method}_core"
    rows, problems = [], []
    for directory in sorted(core.glob(f"{args.config}*")):
        replicate = re.search(r"_rep(\d+)$", directory.name)
        for provenance in sorted(directory.glob("*_provenance.yaml")):
            project = provenance.name[: -len("_provenance.yaml")]
            where = f"{project} {directory.name}"
            pack = directory / f"{project}_review_pack.yaml"
            review = directory / f"{project}_review.yaml"
            block = (yaml.safe_load(provenance.read_text()) or {}).get("review")
            if not block:
                if pack.exists() or review.exists():
                    problems.append(f"{where}: a pack or review file exists but the provenance has no review block")
                continue
            artifacts = block.get("artifacts", {})
            for name, path in (("pack", pack), ("review", review)):
                recorded = artifacts.get(name, {}).get("sha256")
                if not path.is_file():
                    problems.append(f"{where}: {path.name} is missing")
                elif recorded != sha256(path):
                    problems.append(f"{where}: the recorded {name} sha256 is not the file's")
            named = (yaml.safe_load(review.read_text()) or {}).get("pack_sha256") if review.is_file() else None
            if named != artifacts.get("pack", {}).get("sha256"):
                problems.append(f"{where}: the review file names another pack than the block")
            reviewer = block.get("reviewer", {})
            rows.append((
                project, replicate.group(1) if replicate else "", directory.name,
                block.get("items_total"), block.get("items_answered"), block.get("adverse"), block.get("cannot_tell"),
                json.dumps(block.get("by_kind", {}), sort_keys=True, separators=(",", ":")),
                " ".join(str(reviewer.get("reviewer", "")).split()), " ".join(str(reviewer.get("model", "")).split()),
                reviewer.get("reviewed_at", ""),
                artifacts.get("pack", {}).get("sha256", ""), artifacts.get("review", {}).get("sha256", ""),
                str(definition), definition_sha, commit,
            ))
    print("\t".join((
        "project", "replicate", "label", "items_total", "items_answered", "adverse", "cannot_tell", "verdicts_by_kind",
        "reviewer_as_reported", "reviewer_model_as_reported", "reviewed_at", "pack_sha256", "review_sha256",
        "definition_path", "definition_sha256", "definition_last_commit",
    )))
    for row in rows:
        print("\t".join("" if value is None else str(value) for value in row))
    if args.expect is not None and len(rows) != args.expect:
        problems.append(f"expected {args.expect} reviewed records, found {len(rows)}")
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
