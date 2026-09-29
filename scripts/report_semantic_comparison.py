#!/usr/bin/env python3
"""Report explicit semantic evaluations with both score bases (#829).

This reads only the named evaluations, keeps every measurement, and does not
choose winners. Existing evaluation and generation files are never rewritten.
It ends with the item-discrimination block (#2927), which withholds a
within-project order wherever a project has too few distinct totals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from data_sheets_schema.semantic_comparison import (
    comparison_warnings, discrimination, excluded_items, render_discrimination, score_bases,
)


def report(paths: list[Path], cohort: list[Path] | None = None) -> str:
    """`cohort` names the evaluations the discrimination block measures — one
    rating per record, e.g. the primaries of a set that also holds repeats.
    By default it is every named evaluation; a record rated more than once is
    then named and left out of the block rather than having a rating chosen."""
    if not paths:
        raise ValueError("name at least one evaluation")
    documents, rows = [], []
    for path in paths:
        raw = path.read_bytes()
        doc = json.loads(raw)
        if doc.get("rubric") not in ("rubric10-semantic", "rubric20-semantic"):
            raise ValueError(f"{path}: expected a semantic rubric evaluation")
        bases = score_bases(doc, 50 if doc["rubric"] == "rubric10-semantic" else 88)
        exclusions = excluded_items(doc)
        metadata = doc.get("metadata") or {}
        fixed, adjusted = bases.labels()
        documents.append((path, doc))
        rows.append([
            str(path), doc.get("project", "unknown"), doc["rubric"],
            fixed, adjusted,
            ", ".join(exclusions) if exclusions else ("unreported" if exclusions is None else "none"),
            (doc.get("model") or {}).get("name", "unreported"),
            metadata.get("instrument_sha256", "unreported"),
            hashlib.sha256(raw).hexdigest(),
        ])
    text = ["# Semantic comparison: both score bases", "",
            "Fixed percentages use the full rubric maximum. N/A-adjusted percentages use the applicable maximum. "
            "Neither alone establishes comparable applicability or evaluator reliability. "
            "These are individual measurements; this report does not rank runs or average different instruments.", ""]
    warnings = comparison_warnings([doc for _path, doc in documents])
    text.extend(f"- {warning}" for warning in warnings)
    if warnings:
        text.append("")
    text.extend([
        "| Evaluation | Project | Rubric | Fixed base | N/A-adjusted base | Excluded items | Evaluator | Instrument SHA256 | Evaluation SHA256 |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        text.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ")
                                       for cell in row) + " |")
    if cohort is None:
        measured = [doc for _path, doc in documents]
    else:
        named = {path.resolve(): doc for path, doc in documents}
        outside = [str(path) for path in cohort if path.resolve() not in named]
        if outside:
            raise ValueError(f"cohort names evaluations the report does not: {outside}")
        measured = [named[path.resolve()] for path in cohort]
    text.append("")
    text.extend(render_discrimination(discrimination(measured)))
    return "\n".join(text).rstrip("\n") + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluations", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cohort", nargs="+", type=Path,
                        help="the evaluations the discrimination block measures (one rating per "
                             "record); default: every evaluation named")
    args = parser.parse_args()
    if args.output.resolve() in {p.resolve() for p in args.evaluations}:
        parser.error("output must not replace an evaluation")
    rendered = report(args.evaluations, args.cohort)
    args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
