"""Deterministic check of reconciliation report finding totals against structured audit (#4766).

Compares the human-written reconciliation report's stated finding total and
per-severity subtotals against the structured audit (`intermediate/{P}_audit.json`
via `audit_counts`).

Reports that state no finding total are recorded as stating none (`no_total_stated`),
never as consistent. Reports whose stated numbers disagree with the structured audit
(or state conflicting totals within the same report) produce mismatches /
contradictions triggering `report_regate`. Missing or malformed audits are recorded
as not checked with reason.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Version 1: initial deterministic extraction and comparison (#4766).
# Version 2: accept inline/parenthetical/bullet/labelled/table 'N findings: ...'
# total statements unless introduced by a subset marker (deferred, retained,
# rejected, resolved, applied, left, withdrawn, of which, including); count
# 'major'/'minor' only directly before 'finding(s)' or 'severity'; when no overall
# total is stated, extract per-severity subtotals only from a non-subset audit/finding
# summary clause (#5094 R4 F9, F10, Round 2 N2).
INSTRUMENT_VERSION = 2

NUM_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

CANONICAL_SEVERITY = {
    "high": "high", "critical": "high", "major": "high",
    "medium": "medium", "moderate": "medium",
    "low": "low", "minor": "low",
    "info": "info", "informational": "info", "confirmation": "info", "confirmations": "info",
}

WORD_OR_DIGIT = r"(?:\d+|[a-zA-Z]+(?:-[a-zA-Z]+)?)"

# Patterns matching the overall finding total statement in reports.
# Ordered by specificity; patterns 0..8 are explicit total statements,
# while pattern 9 is the isolated-phrase fallback.
TOTAL_PATTERNS = [
    # 1. Header/table: **Findings received:** 31 or | Audit findings | 38 or **Audit findings addressed:** 16
    re.compile(
        r"(?:\bfindings\s+received\b|\baudit\s+findings(?:\s+addressed)?\b)[^:\d|\n]*[:|][*\s]*(" + WORD_OR_DIGIT + r")\b",
        re.I,
    ),
    # 2. Scope: against the 24 audit findings / against the 24 findings
    re.compile(
        r"\bagainst\s+the\s+(" + WORD_OR_DIGIT + r")\s+(?:audit\s+)?findings\b",
        re.I,
    ),
    # 3. Audit input header: **Audit input:** Phase 3 source/provenance audit, 52 findings / **Audit input:** 17 findings
    re.compile(
        r"\baudit\s+input\b[^:\d\n]*:[^.\n]*?\b(" + WORD_OR_DIGIT + r")\s+findings\b",
        re.I,
    ),
    # 4. Sentence: (audit / Phase 3 / it) returned/yielded/produced/identified 25 findings
    re.compile(
        r"\b(?:audit|phase\s+\d+|it)\b[^.\n]*?\b(?:returned|produced|yielded|identified|raised)\s+(?:\*\*)?(" + WORD_OR_DIGIT + r")(?:\*\*)?\s+findings\b",
        re.I,
    ),
    # 5. Participle: returning/yielding/producing 23 findings
    re.compile(
        r"\b(?:returning|yielding|producing)\s+(?:\*\*)?(" + WORD_OR_DIGIT + r")(?:\*\*)?\s+findings\b",
        re.I,
    ),
    # 6. Sentence or clause: N findings were returned / raised / received / produced / identified
    re.compile(
        r"\b(" + WORD_OR_DIGIT + r")\s+findings\s+were\s+(?:returned|raised|produced|identified|received)\b"
        r"(?!\s+(?:for\s+the\s+record\s+without|against\s+the\s+core\s+record|on\s+|about\s+|concerning\s+|specifically\b|without\s+recommending|left\b|addressed\b|withdrawn\b|rejected\b))",
        re.I,
    ),
    # 7. Inline, parenthetical, bullet, labelled, em-dash, or table-cell count with severity
    # breakdown: N findings: H high, M medium... (supports bolding around N findings or
    # severity list; subset prefixes like 'Deferred items (3 findings: ...)' are filtered out
    # in _collect_pattern_matches via SUBSET_PREFIX_RE).
    re.compile(
        r"(?:\*\*)?\b(" + WORD_OR_DIGIT + r")(?:\*\*)?\s+(?:audit\s+)?findings(?:\*\*)?\s*:\s*(?:\*\*)?"
        r"(?:(?:\d+|[a-zA-Z]+)(?:\*\*)?\s+(?:high|medium|moderate|low|major|minor|critical|info|informational))",
        re.I | re.M,
    ),
    # 8. N findings against the (full|core|paired) record
    re.compile(
        r"\b(" + WORD_OR_DIGIT + r")\s+findings\s+against\s+the\b",
        re.I,
    ),
    # 9. N findings, none critical / none of them high
    re.compile(
        r"\b(" + WORD_OR_DIGIT + r")\s+findings\s*,\s*(?:none|no\b)",
        re.I,
    ),
    # 10. Synthetic/simple fallback: report stating "twelve findings" or "N findings" as isolated phrase,
    # ignoring subset counts (e.g., "Six findings were deliberately left as-is").
    re.compile(
        r"(?:^|[.!?]\s+|report\s+saying\s+[\"']?)(?:\*\*)?(" + WORD_OR_DIGIT + r")(?:\*\*)?\s+findings\b(?!\s+(?:were\s+(?:\w+\s+)?(?:left|acted|addressed|remediated|withdrawn|rejected|accepted|retained|raised\s+(?:for\s+the\s+record\s+without|against\s+the\s+core\s+record|on\s+|about\s+|concerning\s+|specifically\b|without\s+recommending))|produced\s+(?:edits|changes)|cluster|fall|concerned|apply|relate))",
        re.I | re.M,
    ),
]

EXPLICIT_TOTAL_PATTERNS = TOTAL_PATTERNS[:-1]
FALLBACK_TOTAL_PATTERNS = TOTAL_PATTERNS[-1:]

SEV_PATTERN = re.compile(
    r"(?<![.\d])\b(" + WORD_OR_DIGIT + r")\s+"
    r"(?:severity\s+(high|critical|major|medium|moderate|low|minor|info|informational|confirmations?)"
    r"|(high|critical|medium|moderate|low|info|informational|confirmations?)"
    r"|(major|minor)(?=[-\s]+severity\b|\s+findings?\b|\s*(?:[,.;:()]|\band\b|\bor\b|$)))\b"
    r"(?!\s*/\s*(?:high|critical|major|medium|moderate|low|minor|info|informational)\b)"
    r"(?!\s+(?:and|or)\s+(?:high|critical|major|medium|moderate|low|minor|info|informational)\b)"
    r"(?!(?:[-\s]+severity)?\s+pairs?\b)",
    re.I,
)

ZERO_SEV_PATTERNS = [
    re.compile(
        r"\b(?:no|none\s+of\s+them|none\s+at|none)\s+"
        r"(?:severity\s+(high|critical|major|medium|moderate|low|minor)"
        r"|(high|critical|medium|moderate|low)"
        r"|(major|minor)(?=[-\s]+severity\b|\s+findings?\b))\b",
        re.I,
    ),
    re.compile(r"\b(high|critical|major|medium|moderate|low|minor)\s*:\s*0\b", re.I),
    re.compile(r"\bno\s+(?:high-severity|critical|major-severity|medium-severity|low-severity)\s+defects?\b", re.I),
]


def parse_number(text: str) -> int | None:
    """Parse integer digits or written number words into an int."""
    if not text:
        return None
    s = text.strip().lower()
    if s.isdigit():
        return int(s)
    if s in NUM_WORDS:
        return NUM_WORDS[s]
    if "-" in s:
        parts = s.split("-")
        if len(parts) == 2 and parts[0] in NUM_WORDS and parts[1] in NUM_WORDS:
            return NUM_WORDS[parts[0]] + NUM_WORDS[parts[1]]
    if " " in s:
        parts = s.split()
        if len(parts) == 2 and parts[0] in NUM_WORDS and parts[1] in NUM_WORDS:
            return NUM_WORDS[parts[0]] + NUM_WORDS[parts[1]]
    return None


SUBSET_PREFIX_RE = re.compile(
    r"\b(?:deferred|retained|rejected|resolved|applied|left|withdrawn|of\s+which|including|subset)\b"
    r"(?![^(\n]*\b(?:audit|summary|totals?)\b)"
    r"(?:\s+[\w*-]+){0,4}\s*(?:[:(\[—–|-]\s*)?$",
    re.I,
)

SUBSET_CLAUSE_RE = re.compile(
    r"\b(?:deferred|retained|rejected|resolved|applied|left|withdrawn|of\s+which|including|subset)\b",
    re.I,
)


def _collect_pattern_matches(
    report_text: str, patterns: list[re.Pattern[str]]
) -> list[tuple[int, int, int, int]]:
    """Return non-overlapping (start, end, pattern_idx, value) matches across patterns."""
    collected: list[tuple[int, int, int, int]] = []
    for pat_idx, pat in enumerate(patterns):
        for m in pat.finditer(report_text):
            n = parse_number(m.group(1))
            if n is None:
                continue
            s, e = m.start(), m.end()
            line_start = report_text.rfind("\n", 0, s)
            sent_start = max(
                report_text.rfind(". ", 0, s),
                report_text.rfind(".\n", 0, s),
            )
            prefix_start = max(
                line_start + 1 if line_start != -1 else 0,
                sent_start + 2 if sent_start != -1 else 0,
            )
            prefix = report_text[prefix_start:s]
            if SUBSET_PREFIX_RE.search(prefix):
                continue
            if any(not (e <= cs or s >= ce) for cs, ce, _, _ in collected):
                continue
            collected.append((s, e, pat_idx, n))
    return collected


def _extract_sevs_from_snippet(snippet: str) -> dict[str, int]:
    """Extract per-severity subtotals from a text snippet."""
    sevs: dict[str, int] = {}
    for m in SEV_PATTERN.finditer(snippet):
        # Ignore individual finding citations like 'finding 1, high'
        prefix = snippet[max(0, m.start() - 15):m.start()]
        if re.search(r"\bfinding\s*$", prefix, re.I):
            continue
        n = parse_number(m.group(1))
        sev_raw = (m.group(2) or m.group(3) or m.group(4) or "").lower()
        sev = CANONICAL_SEVERITY.get(sev_raw, sev_raw)
        if n is not None and sev and sev not in sevs:
            sevs[sev] = n

    for zpat in ZERO_SEV_PATTERNS:
        for m in zpat.finditer(snippet):
            raw = next((g for g in m.groups() if g), "") if m.groups() else ""
            if not raw:
                matched_text = m.group(0).lower()
                for k in ["high", "critical", "major", "medium", "moderate", "low", "minor"]:
                    if k in matched_text:
                        raw = k
                        break
            sev = CANONICAL_SEVERITY.get(raw.lower(), raw.lower())
            if sev and sev not in sevs:
                sevs[sev] = 0

    return sevs


def _extract_totals_detailed(
    report_text: str,
) -> tuple[int | None, list[int], dict[str, int]]:
    """Extract primary stated total, all distinct stated totals, and per-severity subtotals."""
    matches = _collect_pattern_matches(report_text, EXPLICIT_TOTAL_PATTERNS)
    if not matches:
        matches = _collect_pattern_matches(report_text, FALLBACK_TOTAL_PATTERNS)

    stated_total: int | None = None
    matched_pos: tuple[int, int] | None = None
    distinct_totals: list[int] = []

    if matches:
        # Primary match is the earliest statement in document order (tie-broken by pattern specificity)
        ordered_matches = sorted(matches, key=lambda item: (item[0], item[2]))
        primary = ordered_matches[0]
        stated_total = primary[3]
        matched_pos = (primary[0], primary[1])
        # Distinct totals in document order
        for _, _, _, val in ordered_matches:
            if val not in distinct_totals:
                distinct_totals.append(val)

    # Look for severity statements near the total statement if found.
    # When no overall total is stated, extract subtotals only from a single sentence/line
    # that states two or more per-severity counts together (never isolated prose mentions).
    sevs: dict[str, int] = {}
    if matched_pos:
        line_start = report_text.rfind("\n", 0, matched_pos[0])
        sent_start = max(
            report_text.rfind(". ", 0, matched_pos[0]),
            report_text.rfind(".\n", 0, matched_pos[0]),
        )
        boundary = max(
            line_start + 1 if line_start != -1 else 0,
            sent_start + 2 if sent_start != -1 else 0,
        )
        start = max(boundary, matched_pos[0] - 100)
        end = min(len(report_text), matched_pos[1] + 300)
        sevs = _extract_sevs_from_snippet(report_text[start:end])
    else:
        for clause in re.split(r"(?:[.!?\n]+)", report_text[:1500]):
            if SUBSET_CLAUSE_RE.search(clause):
                continue
            if not re.search(r"\b(?:findings?|audit|summary|totals?)\b", clause, re.I):
                continue
            clause_sevs = _extract_sevs_from_snippet(clause)
            if len(clause_sevs) >= 3 or (
                len(clause_sevs) >= 2
                and re.search(r"\b(?:audit|summary|totals?)\b|\bfindings\s*:", clause, re.I)
            ):
                sevs = clause_sevs
                break

    return stated_total, distinct_totals, sevs


def extract_report_audit_totals(report_text: str) -> tuple[int | None, dict[str, int]]:
    """Extract stated total finding count and stated per-severity subtotals from report text."""
    stated_total, _, sevs = _extract_totals_detailed(report_text)
    return stated_total, sevs


def check_report_audit_totals(
    report: str | Path | None,
    audit: str | Path | dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare written report's stated finding totals against structured audit counts.

    Returns a dict with:
      checked: bool
      instrument_version: int
      stated_total: int | None
      stated_totals: list[int]
      stated_by_severity: dict[str, int]
      computed_total: int | None
      computed_by_severity: dict[str, int]
      mismatches: list[dict[str, Any]]
      findings: list[dict[str, Any]] (alias of mismatches for gate integration)
      status: 'consistent' | 'mismatch' | 'no_total_stated' | 'not_checked'
      reason: str | None
    """
    from data_sheets_schema.api_runner import _audit_shape_problem, audit_counts

    # 1. Resolve report text
    if report is None:
        return {
            "checked": False,
            "instrument_version": INSTRUMENT_VERSION,
            "reason": "no reconciliation report",
            "stated_total": None,
            "stated_totals": [],
            "stated_by_severity": {},
            "computed_total": None,
            "computed_by_severity": {},
            "mismatches": [],
            "findings": [],
            "status": "not_checked",
        }

    if isinstance(report, Path):
        if not report.exists():
            return {
                "checked": False,
                "instrument_version": INSTRUMENT_VERSION,
                "reason": f"report file {report} does not exist",
                "stated_total": None,
                "stated_totals": [],
                "stated_by_severity": {},
                "computed_total": None,
                "computed_by_severity": {},
                "mismatches": [],
                "findings": [],
                "status": "not_checked",
            }
        report_text = report.read_text(encoding="utf-8")
    else:
        report_str = str(report)
        if "\n" not in report_str and len(report_str) < 260 and Path(report_str).is_file():
            report_text = Path(report_str).read_text(encoding="utf-8")
        else:
            report_text = report_str

    stated_total, stated_totals, stated_by_severity = _extract_totals_detailed(report_text)

    # 2. Resolve audit text & counts
    if audit is None:
        return {
            "checked": False,
            "instrument_version": INSTRUMENT_VERSION,
            "reason": "missing audit",
            "stated_total": stated_total,
            "stated_totals": stated_totals,
            "stated_by_severity": stated_by_severity,
            "computed_total": None,
            "computed_by_severity": {},
            "mismatches": [],
            "findings": [],
            "status": "not_checked",
        }

    if isinstance(audit, Path):
        if not audit.exists():
            return {
                "checked": False,
                "instrument_version": INSTRUMENT_VERSION,
                "reason": f"audit file {audit} does not exist",
                "stated_total": stated_total,
                "stated_totals": stated_totals,
                "stated_by_severity": stated_by_severity,
                "computed_total": None,
                "computed_by_severity": {},
                "mismatches": [],
                "findings": [],
                "status": "not_checked",
            }
        audit_str = audit.read_text(encoding="utf-8")
    elif isinstance(audit, dict):
        audit_str = json.dumps(audit)
    else:
        audit_str = str(audit)

    computed = audit_counts(audit_str)
    if computed is None:
        raw_audit = audit_str.strip() if audit_str else ""
        if not raw_audit:
            audit_reason = "missing audit"
        else:
            try:
                parsed_audit = json.loads(raw_audit)
            except (ValueError, TypeError):
                audit_reason = "malformed audit JSON"
            else:
                if not isinstance(parsed_audit, dict):
                    audit_reason = "audit JSON must be an object"
                else:
                    audit_reason = _audit_shape_problem(parsed_audit) or "malformed audit"
        return {
            "checked": False,
            "instrument_version": INSTRUMENT_VERSION,
            "reason": audit_reason,
            "stated_total": stated_total,
            "stated_totals": stated_totals,
            "stated_by_severity": stated_by_severity,
            "computed_total": None,
            "computed_by_severity": {},
            "mismatches": [],
            "findings": [],
            "status": "not_checked",
        }

    computed_total = computed["total"]
    computed_by_severity = computed["by_severity"]

    # 3. Compare stated numbers (total and per-severity subtotals) against computed counts
    mismatches: list[dict[str, Any]] = []
    if stated_total is not None and stated_total != computed_total:
        mismatches.append({
            "kind": "finding_total_mismatch",
            "record": "report",
            "detail": f"report states {stated_total} findings; structured audit has {computed_total}",
            "stated": stated_total,
            "computed": computed_total,
        })

    if len(stated_totals) > 1:
        mismatches.append({
            "kind": "finding_total_contradiction",
            "record": "report",
            "detail": (
                f"report states conflicting finding totals ({', '.join(str(x) for x in stated_totals)}); "
                f"structured audit has {computed_total}"
            ),
            "stated_totals": stated_totals,
            "computed": computed_total,
        })

    # Canonicalize computed severity counts for comparison
    computed_canonical: dict[str, int] = {}
    for k, v in computed_by_severity.items():
        ck = CANONICAL_SEVERITY.get(k.lower(), k.lower())
        computed_canonical[ck] = computed_canonical.get(ck, 0) + v

    for sev, count in stated_by_severity.items():
        c_count = computed_canonical.get(sev, 0)
        if count != c_count:
            mismatches.append({
                "kind": "finding_severity_mismatch",
                "record": "report",
                "severity": sev,
                "detail": f"report states {count} {sev} findings; structured audit has {c_count}",
                "stated": count,
                "computed": c_count,
            })

    if mismatches:
        status = "mismatch"
    elif stated_total is None:
        status = "no_total_stated"
    else:
        status = "consistent"

    return {
        "checked": True,
        "instrument_version": INSTRUMENT_VERSION,
        "reason": None,
        "stated_total": stated_total,
        "stated_totals": stated_totals,
        "stated_by_severity": stated_by_severity,
        "computed_total": computed_total,
        "computed_by_severity": computed_by_severity,
        "mismatches": mismatches,
        "findings": list(mismatches),
        "status": status,
    }
