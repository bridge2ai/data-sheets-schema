#!/usr/bin/env python3
"""Report explicit semantic evaluations with both score bases (#829).

This reads only the named evaluations, keeps every measurement, and does not
choose winners. Existing evaluation and generation files are never rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from data_sheets_schema.semantic_comparison import (
    comparison_warnings, excluded_items, score_bases,
)


def report(paths: list[Path]) -> str:
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
        documents.append(doc)
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
    warnings = comparison_warnings(documents)
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
    return "\n".join(text) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluations", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.resolve() in {p.resolve() for p in args.evaluations}:
        parser.error("output must not replace an evaluation")
    rendered = report(args.evaluations)
    args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
