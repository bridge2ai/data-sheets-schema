#!/usr/bin/env python3
"""Tabulate the semantic rubric scores of the 2026-11-25c release series.

Purpose: write the score table that the selection note of the series quotes.
Inputs: --evaluations-root, a directory that holds
  rubric{10,20}_semantic/label_aware/<INSTRUMENT>/<PROJECT>_<LABEL>_evaluation.json
  (the layout under data/evaluation_llm/; the 30 files are in PR #6372, not in the
  PR this script is committed in), and --instrument.
Outputs: a TSV on stdout, one row per evaluation file: project, replicate, rubric,
  total_points, max_points, percent, instrument, sha256 of the file.
  Exit status 1 if the number of files is not --expect.
Serves: the selection PR of release series 2026-11-25c. Date: 2026-11-26.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

NAME = re.compile(r"^(?P<project>[A-Z0-9_]+?)_(?P<label>\d{4}-\d{2}-\d{2}[a-z]?_.+_rep(?P<rep>\d+))_evaluation\.json$")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--evaluations-root", required=True)
    parser.add_argument("--instrument", required=True)
    parser.add_argument("--expect", type=int, default=30, help="number of files expected (default 30)")
    args = parser.parse_args()

    rows = []
    for rubric in ("rubric10", "rubric20"):
        directory = Path(args.evaluations_root) / f"{rubric}_semantic" / "label_aware" / args.instrument
        for path in sorted(directory.glob("*_evaluation.json")):
            match = NAME.match(path.name)
            if not match:
                print(f"unexpected file name: {path.name}", file=sys.stderr)
                return 1
            raw = path.read_bytes()
            score = json.loads(raw)["overall_score"]
            rows.append((
                match["project"], int(match["rep"]), rubric,
                score["total_points"], score["max_points"],
                f"{100 * score['total_points'] / score['max_points']:.1f}",
                args.instrument, hashlib.sha256(raw).hexdigest(),
            ))
    rows.sort()
    print("project\treplicate\trubric\ttotal_points\tmax_points\tpercent\tinstrument\tsha256")
    for row in rows:
        print("\t".join(str(value) for value in row))
    if len(rows) != args.expect:
        print(f"expected {args.expect} files, found {len(rows)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
