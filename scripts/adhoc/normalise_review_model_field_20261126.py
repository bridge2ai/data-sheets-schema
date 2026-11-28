#!/usr/bin/env python3
"""Reduce the `model` field of a series' review files to the bare model id.

Purpose: `tests/test_reviewer_basis.py` (#1058, #1097) requires that every review of one
  arm and pass names the same reviewer model, as a string that the checked-in manifest
  `tests/data/reviewer_basis.json` declares. The 15 reviews of release series 2026-11-25c
  were asked by their launcher to say what they were, and 11 of them wrote the model id
  followed by a description in the `model` field ("<id> (… as stated by the runtime
  environment)" and the like), so one reviewer read as eleven. This rewrites that one
  line to the bare id and keeps what each review wrote in a table.
Inputs (run from the repository root): --method, --config (label prefix), --model (the
  bare id every field must begin with).
Outputs: with --apply, the `model:` line of each review file whose value is longer than
  the id; and `--table`, one row per review with the field as the review wrote it.
  Without --apply, a report. Exit status 1, and nothing written, if a review's `model`
  does not begin with the id followed by the end, a space, '(' or ','; if its `model:`
  line is not a single top-level line; or if the rewritten file would differ from the
  original in anything but the value of `model`.
  Afterwards run `d4d review check --write` for each changed record.
Serves: PR #6382 (the CI failure of tests/test_reviewer_basis.py). Date: 2026-11-26.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--method", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--table", default="notes/release_series_2026-11-25/review_model_field_as_written.tsv")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    core = Path("data/d4d_concatenated") / f"{args.method}_core"
    plan, rows, problems = [], [], []
    for review in sorted(core.glob(f"{args.config}*/*_review.yaml")):
        project = review.name[: -len("_review.yaml")]
        replicate = re.search(r"_rep(\d+)$", review.parent.name).group(1)
        where = f"{project} rep{replicate}"
        text = review.read_text(encoding="utf-8")
        document = yaml.safe_load(text)
        written = document.get("model")
        if not isinstance(written, str) or not re.match(re.escape(args.model) + r"(?:$|[ (,])", written):
            problems.append(f"{where}: model does not begin with the id")
            continue
        rows.append((project, replicate, " ".join(written.split())))
        if written == args.model:
            continue
        lines = text.split("\n")
        at = [index for index, line in enumerate(lines) if line.startswith("model:")]
        if len(at) != 1 or (at[0] + 1 < len(lines) and lines[at[0] + 1][:1] in (" ", "\t")):
            problems.append(f"{where}: the model line is not one top-level line")
            continue
        lines[at[0]] = f"model: {args.model}"
        new_text = "\n".join(lines)
        rewritten = yaml.safe_load(new_text)
        if rewritten.get("model") != args.model or {k: v for k, v in rewritten.items() if k != "model"} != {
            k: v for k, v in document.items() if k != "model"
        }:
            problems.append(f"{where}: the rewrite would change more than the model value")
            continue
        plan.append((where, review, new_text))
        print(f"{where}: model field reduced to the id")

    for problem in problems:
        print(f"PROBLEM {problem}", file=sys.stderr)
    if problems:
        print("nothing written", file=sys.stderr)
        return 1
    if args.apply:
        table = Path(args.table)
        if not table.exists():                       # the first run records what the reviews wrote; a rerun must not overwrite it
            table.write_text("project\treplicate\tmodel_field_as_written\n" + "".join("\t".join(row) + "\n" for row in rows), encoding="utf-8")
        for _where, review, new_text in plan:
            review.write_text(new_text, encoding="utf-8")
        print(f"applied to {len(plan)} review file(s) of {len(rows)}")
    else:
        print(f"dry run: {len(plan)} of {len(rows)} review file(s) would change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
