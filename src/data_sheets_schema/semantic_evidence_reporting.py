"""Report mechanical findings and evaluator-declared issue taxonomy (#2920).

This module never treats a model-written acceptance flag as evidence. Finding
reports must come from the deterministic checker on the rating and its input.
Taxonomy counts describe what the evaluator declared, not verified semantics.
Legacy prose can be classified only by an explicit caller-supplied function;
new-contract issues never fall back to that function.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import html
import re
from typing import Callable

from data_sheets_schema.semantic_evidence import (
    EvidenceReport, ISSUE_CATEGORIES, ISSUE_TYPES,
)


def findings_to_dict(report: EvidenceReport) -> dict:
    """Copy a computed report into JSON-compatible values without rating writes."""
    return {"passed": report.passed, "findings": [asdict(f) for f in report.findings]}


def markdown_cell(value: object) -> str:
    """Escape untrusted labels as literal Markdown table/paragraph text."""
    text = html.escape(str(value), quote=False)
    text = re.sub(r"([\\`*_{}\[\]()])", r"\\\1", text)
    return text.replace("|", "&#124;").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def render_evidence_findings(report: EvidenceReport | None) -> str:
    if report is None:
        return "Evaluator evidence: **not checked**; no authoritative input was supplied.\n"
    lines = [f"Mechanical evidence findings: {len(report.errors)} error(s), "
             f"{len(report.warnings)} warning(s). Scores are unchanged.", ""]
    if report.findings:
        lines.extend([
            "| Severity | Code | Item | Resource | Input path | Issue index | Finding |",
            "|---|---|---|---|---|---|---|",
        ])
        for finding in report.findings:
            values = (finding.severity, finding.code, finding.item_id, finding.unit,
                      finding.path, finding.issue, finding.message)
            lines.append("| " + " | ".join(markdown_cell(v) if v is not None else "—"
                                           for v in values) + " |")
    else:
        lines.append("No mechanical evidence findings.")
    lines.extend(["", "These checks do not establish semantic correctness."])
    return "\n".join(lines) + "\n"


def issue_taxonomy(result: dict, *, legacy_classifier: Callable[[dict], str] | None = None) -> dict:
    """Count recorded v3 categories/links, or explicitly label legacy coding.

    A legacy classifier receives a private copy of each issue. Without one,
    old issues remain unclassified and their deduction effects are unknown.
    Malformed v3 declarations raise instead of silently invoking a regex.
    This checks declaration shapes, not whether links actually justify scores;
    acceptance must also run the semantic scope and evidence validators.
    """
    version = result.get("version")
    structured = version == "3.0"
    if not structured and version not in (None, "1.0", "1.1", "1.2", "2.0"):
        raise ValueError(f"unsupported semantic taxonomy version: {version!r}")
    analysis = result.get("semantic_analysis") or {}
    if not isinstance(analysis, dict):
        raise ValueError("semantic_analysis must be an object")
    recorded = "issues_detected" in analysis
    issues = analysis.get("issues_detected", [])
    if not isinstance(issues, list) or structured and not recorded:
        raise ValueError("issues_detected must be a recorded list for v3")
    basis = ("evaluator_declared_v3" if structured else
             "legacy_caller_classification" if legacy_classifier else "legacy_unstructured")
    entries = []
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            raise ValueError(f"issue {index}: expected an object")
        if structured:
            category, kind = issue.get("category"), issue.get("type")
            severity, effect = issue.get("severity"), issue.get("score_effect")
            ids = issue.get("item_ids")
            if not isinstance(category, str) or category not in ISSUE_CATEGORIES:
                raise ValueError(f"issue {index}: unknown or missing category")
            if not isinstance(kind, str) or kind not in ISSUE_TYPES:
                raise ValueError(f"issue {index}: unknown or missing type")
            if severity not in ("low", "medium", "high"):
                raise ValueError(f"issue {index}: invalid severity")
            if effect not in ("lowered", "noted_only"):
                raise ValueError(f"issue {index}: invalid score_effect")
            if (not isinstance(ids, list) or any(not isinstance(i, str) or not i for i in ids)
                    or len(set(ids)) != len(ids) or effect == "lowered" and not ids
                    or effect == "noted_only" and ids):
                raise ValueError(f"issue {index}: invalid item_ids")
            ids = list(ids)
        else:
            category = legacy_classifier(deepcopy(issue)) if legacy_classifier else None
            if category is not None and (not isinstance(category, str) or not category.strip()):
                raise ValueError(f"issue {index}: legacy classifier must return a nonempty category")
            kind, severity = issue.get("type"), issue.get("severity")
            ids, effect = None, None
        entries.append({"index": index, "category": category, "type": kind,
                        "severity": severity, "item_ids": ids, "score_effect": effect})
    categories = Counter(e["category"] for e in entries if e["category"] is not None)
    items = Counter(item for e in entries for item in e["item_ids"] or [])
    return {"basis": basis, "issues_recorded": recorded, "issues": entries,
            "category_counts": dict(sorted(categories.items())), "item_counts": dict(sorted(items.items())),
            "high_severity_lowered": sum(e["severity"] == "high" and e["score_effect"] == "lowered"
                                         for e in entries) if structured else None}


def render_issue_taxonomy(result: dict) -> str:
    taxonomy = issue_taxonomy(result)
    if taxonomy["basis"] != "evaluator_declared_v3":
        return ("Issue taxonomy: legacy, unstructured; categories and deduction links are "
                "not inferred from prose.\n")
    lines = ["Issue taxonomy: **evaluator-declared v3**; categories and deduction links "
             "come directly from the rating. This is not a semantic adjudication.", "",
             f"High-severity issues declared to lower scores: {taxonomy['high_severity_lowered']}.", ""]
    if taxonomy["issues"]:
        lines.extend(["| Issue index | Category | Type | Severity | Score effect | Item IDs |",
                      "|---|---|---|---|---|---|"])
        for entry in taxonomy["issues"]:
            values = [entry[k] for k in ("index", "category", "type", "severity", "score_effect")]
            values.append(", ".join(entry["item_ids"]) or "none")
            lines.append("| " + " | ".join(markdown_cell(v) for v in values) + " |")
    else:
        lines.append("No issues declared.")
    return "\n".join(lines) + "\n"
