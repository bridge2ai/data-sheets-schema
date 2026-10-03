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
from data_sheets_schema.semantic_comparison import evaluator_key as shared_evaluator_key


def evaluator_of(doc: dict) -> str:
    """The evaluator an evaluation names: the table's Evaluator column
    (`model.name`), else `model.evaluator_model`, else "unreported"."""
    model = doc.get("model") or {}
    return model.get("name") or model.get("evaluator_model") or "unreported"


def evaluator_key(doc: dict) -> str:
    """The key a discrimination block is measured under, shared with
    arm_comparison (`semantic_comparison.evaluator_key`, #3319)."""
    return shared_evaluator_key(doc) or "unreported"


def evaluator_column(doc: dict) -> str:
    """The table's Evaluator cell: the display name, and the key the
    discrimination blocks name where it differs, so every block's
    "the X evaluations above" names a string a row carries (#3322)."""
    shown, key = evaluator_of(doc), evaluator_key(doc)
    return shown if shown == key else f"{shown} (evaluator {key})"


def report(paths: list[Path], cohort: list[Path] | None = None, *,
           evidence_inputs: dict[Path, Path] | None = None,
           evidence_contexts: dict[Path, Path] | None = None,
           disclosure_policy: str | None = None,
           generation_bindings=None,
           disclosure_root: Path | None = None) -> str:
    """`cohort` names the evaluations the discrimination block measures — one
    rating per record, e.g. the primaries of a set that also holds repeats.
    The table still lists every named evaluation, and the block names those
    its cohort leaves out (#3303). By default it is every named evaluation; a record rated more than once is
    then named and left out of the block rather than having a rating chosen.
    Evaluations by different evaluators are measured in separate blocks, one
    per evaluator, never pooled (#3309)."""
    if not paths:
        raise ValueError("name at least one evaluation")
    disclosure = None
    if disclosure_policy is None:
        if generation_bindings is not None or disclosure_root is not None:
            raise ValueError("generation bindings and disclosure root require an explicit disclosure policy")
    elif disclosure_policy == "declared-v1":
        from data_sheets_schema.model_disclosure import build_report
        disclosure = build_report(paths, bindings=generation_bindings or (), root=disclosure_root)
    else:
        raise ValueError("unknown model disclosure policy")
    inputs = {Path(k).resolve(): Path(v) for k, v in (evidence_inputs or {}).items()}
    contexts = {Path(k).resolve(): Path(v) for k, v in (evidence_contexts or {}).items()}
    named_paths = {path.resolve() for path in paths}
    if set(inputs) - named_paths:
        raise ValueError("evidence inputs name evaluations outside the report")
    if set(contexts) - set(inputs):
        raise ValueError("each evidence context requires an input for the same evaluation")
    documents, rows = [], []
    for path in paths:
        raw = path.read_bytes()
        if disclosure is not None:
            declared = disclosure["rows"][len(documents)]
            if (declared["evaluation_resolved_path"] != str(path.resolve()) or
                    declared["evaluation_sha256"] != hashlib.sha256(raw).hexdigest()):
                raise ValueError(f"{path}: evaluation changed between disclosure and score capture")
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
        if disclosure is not None:
            from data_sheets_schema.semantic_evidence_reporting import markdown_cell
            rows[-1].extend(markdown_cell("unknown" if declared[key] is None else declared[key])
                            for key in ("evaluator_family", "generator", "generator_family",
                                        "same_family", "association_status"))
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
    if disclosure is not None:
        text[-2] += " Evaluator family | Generator | Generator family | Same family | Generation binding |"
        text[-1] += "---|---|---|---|---|"
    for row in rows:
        text.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ")
                                       for cell in row) + " |")
    if any(doc.get("version") in ("3.0", "4.0") or path.resolve() in inputs for path, doc in documents):
        text.extend(["", "## Evaluator evidence and issue taxonomy", "",
                     "Evidence checks below are recomputed from explicitly supplied inputs and caller contexts; "
                     "a missing context means unknown applicability. They do not certify the evaluator's "
                     "semantic interpretation or replace instrument-provenance acceptance.", ""])
        for path, doc in documents:
            if doc.get("version") not in ("3.0", "4.0") and path.resolve() not in inputs:
                continue
            text.extend(_evidence_section(path, doc, inputs.get(path.resolve()), contexts.get(path.resolve())))
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
    if disclosure is not None:
        from data_sheets_schema.model_disclosure import render
        # The shared report retains per-rating hashes, types, reasons and all
        # association checks. Nest its headings without changing its content.
        appendix = render(disclosure).rstrip("\n").splitlines()
        text.extend(["", *("#" + line if line.startswith("#") else line for line in appendix)])
    return "\n".join(text).rstrip("\n") + "\n"



def _evidence_section(path: Path, doc: dict, input_path: Path | None,
                      context_path: Path | None) -> list[str]:
    import yaml
    from data_sheets_schema.evaluation_context import load_context, load_document
    from data_sheets_schema.semantic_evidence import EvidenceValidationError
    from data_sheets_schema.semantic_evidence_reporting import (
        markdown_cell, render_evidence_findings, render_issue_taxonomy,
    )
    from data_sheets_schema.semantic_scope import validate_scope

    lines = [f"### {markdown_cell(path)}", ""]
    if doc.get("version") in ("3.0", "4.0"):
        # Mechanical checks assume the output contract: an unrecognized citation
        # key, for example, must not silently become an absent quotation (#4245).
        from jsonschema import SchemaError, ValidationError, validate
        from data_sheets_schema.resources import resource_path

        try:
            from data_sheets_schema.semantic_instrument import select_semantic_instrument
            selected = select_semantic_instrument(doc["rubric"], doc["version"])
            schema = json.loads(resource_path(selected.schema_path).read_bytes())
            validate(doc, schema)
        except ValidationError as exc:
            location = "/".join(str(part) for part in exc.absolute_path) or "#"
            lines.extend([
                f"Evidence verification: **not established** — invalid v{doc['version'].split('.')[0]} output structure at "
                f"{markdown_cell(location)}: {markdown_cell(exc.message)}.", "",
            ])
            return lines
        except (OSError, ValueError, SchemaError) as exc:
            lines.extend([f"Evidence verification: **not established** — {markdown_cell(exc)}.", ""])
            return lines
    try:
        lines.extend([render_issue_taxonomy(doc).rstrip(), ""])
    except ValueError as exc:
        lines.extend([f"Issue taxonomy: **invalid declaration** — {markdown_cell(exc)}.", ""])
    if doc.get("version") not in ("3.0", "4.0"):
        lines.extend(["Mechanical evidence checks: **not run**; this rating retains its historical contract.", ""])
        return lines
    if input_path is None:
        lines.extend([render_evidence_findings(None).rstrip(), ""])
        return lines
    try:
        document, digest = load_document(input_path)
        context = load_context(context_path)
        lines.extend([f"Input: {markdown_cell(input_path)}; SHA256: {digest}.", ""])
        checked = validate_scope(doc, document=document, input_sha256=digest, expected_context=context)
    except EvidenceValidationError as exc:
        checked = exc.report
    except (OSError, ValueError, yaml.YAMLError) as exc:
        lines.extend([f"Evidence verification: **not established** — {markdown_cell(exc)}.", ""])
        return lines
    lines.extend([render_evidence_findings(checked).rstrip(), ""])
    return lines


def _named_pairs(pairs: list[list[Path]] | None, label: str) -> dict[Path, Path]:
    result = {}
    for evaluation, value in pairs or []:
        key = evaluation.resolve()
        if key in result:
            raise ValueError(f"duplicate {label} for {evaluation}")
        result[key] = value
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluations", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cohort", nargs="+", type=Path,
                        help="the evaluations the discrimination block measures (one rating per "
                             "record); default: every evaluation named")
    parser.add_argument("--evidence-input", nargs=2, action="append", type=Path,
                        metavar=("EVALUATION", "INPUT"),
                        help="recompute structured mechanical evidence for this named rating and input")
    parser.add_argument("--evidence-context", nargs=2, action="append", type=Path,
                        metavar=("EVALUATION", "CONTEXT"),
                        help="independent caller applicability context; omission means unknown")
    parser.add_argument("--model-disclosure", choices=("declared-v1",),
                        help="opt-in per-rating declared families and checked generation evidence")
    parser.add_argument("--generation-binding", nargs=3, action="append", type=Path,
                        metavar=("EVALUATION", "INPUT", "PROVENANCE"),
                        help="explicit generation association; requires --model-disclosure")
    parser.add_argument("--disclosure-root", type=Path,
                        help="root for recorded binding paths; requires --model-disclosure")
    args = parser.parse_args()
    if args.output.resolve() in {p.resolve() for p in args.evaluations}:
        parser.error("output must not replace an evaluation")
    try:
        inputs = _named_pairs(args.evidence_input, "evidence input")
        contexts = _named_pairs(args.evidence_context, "evidence context")
        protected = {p.resolve() for p in [*args.evaluations, *inputs.values(), *contexts.values()]}
        bindings = None
        if args.generation_binding is not None:
            from data_sheets_schema.model_disclosure import GenerationBinding
            bindings = [GenerationBinding(*triple) for triple in args.generation_binding]
            protected.update(p.resolve() for triple in args.generation_binding for p in triple)
        if (args.output.resolve() in protected or args.output.exists()
                and any(args.output.samefile(p) for p in protected if p.exists())):
            parser.error("output must not replace an evaluation, evidence input or context")
        if args.model_disclosure is not None and (args.output.exists() or args.output.is_symlink()):
            parser.error("model disclosure output must be a new file")
        rendered = report(args.evaluations, args.cohort, evidence_inputs=inputs, evidence_contexts=contexts,
                          disclosure_policy=args.model_disclosure, generation_bindings=bindings,
                          disclosure_root=args.disclosure_root)
    except ValueError as exc:
        parser.error(str(exc))
    except OSError as exc:
        if args.model_disclosure is None:
            raise
        parser.error(str(exc))
    if args.model_disclosure is None:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        # Exclusive creation refuses existing files and closes the publication
        # race, including a new symlink/hardlink to any captured input.
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(rendered)
        except OSError as exc:
            parser.error(str(exc))


if __name__ == "__main__":
    main()
