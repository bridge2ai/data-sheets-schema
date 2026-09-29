#!/usr/bin/env python3
"""Report explicit semantic evaluations with both score bases (#829).

This reads only the named evaluations, keeps every measurement, and does not
choose winners. Existing evaluation and generation files are never rewritten.
It ends with the item-discrimination block (#2927), one per evaluator (#3309), which withholds a
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


def evaluator_of(doc: dict) -> str:
    """The evaluator an evaluation names: the table's Evaluator column
    (`model.name`), else `model.evaluator_model`, else "unreported"."""
    model = doc.get("model") or {}
    return model.get("name") or model.get("evaluator_model") or "unreported"


def evaluator_key(doc: dict) -> str:
    """The evaluator a discrimination block is keyed on: `model.evaluator_model`,
    as arm_comparison keys it, else `model.model_id`, else the display name.
    `model.name` is a display label — one committed evaluation says
    "Opus 5 (1M context)" where its evaluator_model says "claude-opus-5[1m]" —
    so keying on it splits one evaluator into two (#3319)."""
    model = doc.get("model") or {}
    return (model.get("evaluator_model") or model.get("model_id") or model.get("name")
            or "unreported")


def evaluator_column(doc: dict) -> str:
    """The table's Evaluator cell: the display name, and the key the
    discrimination blocks name where it differs, so every block's
    "the X evaluations above" names a string a row carries (#3322)."""
    shown, key = evaluator_of(doc), evaluator_key(doc)
    return shown if shown == key else f"{shown} (evaluator {key})"


def report(paths: list[Path], cohort: list[Path] | None = None) -> str:
    """`cohort` names the evaluations the discrimination block measures — one
    rating per record, e.g. the primaries of a set that also holds repeats.
    The table still lists every named evaluation, and the block names those
    its cohort leaves out (#3303). By default it is every named evaluation; a record rated more than once is
    then named and left out of the block rather than having a rating chosen.
    Evaluations by different evaluators are measured in separate blocks, one
    per evaluator, never pooled (#3309)."""
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
            evaluator_column(doc),
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
        measured, left_out = [doc for _path, doc in documents], []
    else:
        named = {path.resolve(): doc for path, doc in documents}
        outside = [str(path) for path in cohort if path.resolve() not in named]
        if outside:
            raise ValueError(f"cohort names evaluations the report does not: {outside}")
        measured = [named[path.resolve()] for path in cohort]
        # The table lists every evaluation; name the ones the block does not
        # measure rather than say it measured "the evaluations above" (#3303).
        in_cohort = {path.resolve() for path in cohort}
        left_out = [str(path) for path, _doc in documents if path.resolve() not in in_cohort]
    text.append("")
    # An evaluator is an instrument (#1058): pooling two counts their offset
    # as distinct totals and can lift a project past the gate that each
    # evaluator alone would withhold. Measure each evaluator apart, as
    # arm_comparison does (#3309); one evaluator keeps the unscoped block.
    by_evaluator: dict[str, list[dict]] = {}
    for doc in measured:
        by_evaluator.setdefault(evaluator_key(doc), []).append(doc)
    if len(by_evaluator) <= 1:
        text.extend(render_discrimination(discrimination(measured), left_out=left_out))
    else:
        evaluator_by_path = {str(path): evaluator_key(doc) for path, doc in documents}
        for evaluator in sorted(by_evaluator):
            text.extend(render_discrimination(
                discrimination(by_evaluator[evaluator]), scope=f", {evaluator} evaluations",
                left_out=[name for name in left_out if evaluator_by_path[name] == evaluator],
                evaluator=evaluator))
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
