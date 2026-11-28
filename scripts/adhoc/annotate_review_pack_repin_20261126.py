#!/usr/bin/env python3
"""Add the generator identities to the re-pin table of the review packs, and check it.

Purpose: `notes/release_series_2026-11-25/review_pack_repin.tsv` gives, per record, the
  sha256 of the pack the reviewer read and of the pack that is committed (issue #6379).
  Review 1 of PR #6380 (finding B1, issue #6381) asked that the table also say which
  generator made each. The as-reviewed hashes were read from the commit that held the
  reviewed packs before they were replaced; that commit was never pushed, so they can
  only be reproduced by building each pack in memory with the unfixed generator (main
  at the commit named below) from the worktree the packs were first generated in, which
  is how the review confirmed them.
Inputs (run from the repository root): the table; --method and --config; the two
  generator descriptions.
Outputs: the table rewritten in place with two more columns. Exit status 1, and nothing
  written, if a committed hash in the table is not the sha256 of the pack on disk.
Serves: issue #6379. Date: 2026-11-26.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--table", default="notes/release_series_2026-11-25/review_pack_repin.tsv")
    parser.add_argument("--method", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--reviewed-generator", required=True)
    parser.add_argument("--committed-generator", required=True)
    args = parser.parse_args()

    table = Path(args.table)
    with table.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    core = Path("data/d4d_concatenated") / f"{args.method}_core"
    problems = []
    for row in rows:
        pack = core / f"{args.config}_rep{row['replicate']}" / f"{row['project']}_review_pack.yaml"
        if not pack.is_file() or hashlib.sha256(pack.read_bytes()).hexdigest() != row["pack_sha256_committed"]:
            problems.append(f"{row['project']} rep{row['replicate']}: the committed hash is not the pack on disk")
        row["generator_of_reviewed_pack"] = args.reviewed_generator
        row["generator_of_committed_pack"] = args.committed_generator
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    fields = ["project", "replicate", "pack_sha256_as_reviewed", "pack_sha256_committed",
              "generator_of_reviewed_pack", "generator_of_committed_pack"]
    with table.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows annotated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
