#!/usr/bin/env python
"""#2302: taxonomy of the issues the semantic rubric evaluators raised on the reference rescore.

Record set: the 56 accepted ratings of the frozen CBORG reference rescore
(notes/reference_rescore_2026-09-12_cborg_runtime/completion_audit.json): 32 rubric10 and
24 rubric20 ratings over 24 API-arm full records. Issues are `semantic_analysis.issues_detected`
entries (type, severity, description); consistency checks are the evaluator's own
passed/failed/warnings counts. Coding is deterministic: the rules in
scripts/figures/issue_codes.csv are tried in file order on the lower-cased `type` + description,
the first match wins, and an issue matching no rule is counted as `other` rather than dropped.
The number of issues matching two or more rules is reported on the figure, and the CSV keeps
the full description, the winning rule's matched span and every other matching code, so each
coding can be reproduced and challenged.

Panels A, B and D count primary ratings only (one rating per record and rubric, 24 each), so
the two rubrics are comparable and the eight rubric10 repeat ratings of CHORUS v7 rep1 do not
count that record several times. Panel C shows every accepted rating.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

ARCH = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime"
CODES = Path(__file__).with_name("issue_codes.csv")
RUBRICS = [("rubric10-semantic", "rubric10"), ("rubric20-semantic", "rubric20")]
RUBRIC_COLOR = {"rubric10-semantic": st.SERIES[6], "rubric20-semantic": st.SERIES[5]}   # fixed slots 7 (violet) and 6 (green)
SEVERITIES = ["low", "medium", "high"]
SEV_HATCH = {"low": None, "medium": "//", "high": "////"}      # hatch density carries severity; fill stays at full strength
TYPES = ["completeness", "consistency", "content_accuracy", "correctness", "semantic_understanding"]
CHECK_COLOR = {"passed": st.STATUS["good"], "warnings": st.STATUS["warning"], "failed": st.STATUS["critical"]}


def load_codes() -> list[tuple[str, str, re.Pattern | None]]:
    out = []
    with CODES.open() as fh:
        for row in csv.DictReader(fh):
            rule = row["rule"].strip()
            out.append((row["code"], row["label"], re.compile(rule, re.I) if rule else None))
    return out


def code_issue(codes, issue_type: str, description: str) -> tuple[str, str, list[str]]:
    """(winning code, matched span of the winning rule, every matching code in rule order)."""
    text = f"{issue_type or ''} {description or ''}".lower()
    matches = []
    for code, _label, rx in codes:
        if rx is None:
            continue
        m = rx.search(text)
        if m:
            matches.append((code, m.group(0)))
    if not matches:
        return "other", "", []
    return matches[0][0], matches[0][1], [c for c, _ in matches]


def load():
    manifest = json.loads((ARCH / "manifest.json").read_text())
    audit = json.loads((ARCH / "completion_audit.json").read_text())
    jobs = {j["id"]: j for j in manifest["jobs"]}
    codes = load_codes()
    issues, checks = [], []
    for r in audit["ratings"]:
        j = jobs[r["job_id"]]
        doc = json.loads((st.ROOT / r["output"]).read_text())
        sa = doc["semantic_analysis"]
        for it in sa.get("issues_detected") or []:
            code, span, all_codes = code_issue(codes, it.get("type"), it.get("description"))
            issues.append({
                "job_id": j["id"], "rubric": j["rubric"], "project": j["project"], "cohort": j["cohort"],
                "generation_rep": j["generation_rep"], "rating": j["rating"], "purpose": j["purpose"],
                "type": it.get("type"), "severity": it.get("severity"),
                "code": code, "matched_span": span, "all_matching_codes": "|".join(all_codes),
                "n_matching_rules": len(all_codes),
                "description": it.get("description") or "",
            })
        cc = sa.get("consistency_checks") or {}
        checks.append({"job_id": j["id"], "rubric": j["rubric"], "project": j["project"], "cohort": j["cohort"],
                       "generation_rep": j["generation_rep"], "rating": j["rating"], "purpose": j["purpose"],
                       "passed": int(cc.get("passed") or 0), "failed": int(cc.get("failed") or 0),
                       "warnings": int(cc.get("warnings") or 0),
                       "n_issues": len(sa.get("issues_detected") or []),
                       "n_weaknesses": len(doc.get("assessment", {}).get("weaknesses") or []),
                       "n_correctness_validations": len(sa.get("correctness_validations") or {})})
    return manifest, audit, codes, issues, checks


def hbar_segments(ax, y, segs, color, height):
    """Stacked horizontal bar with a surface gap between segments; segs = [(value, hatch)]."""
    x0 = 0.0
    for val, hatch in segs:
        if val <= 0:
            continue
        ax.barh(y, val, left=x0, height=height, color=color, edgecolor=st.INK["surface"], linewidth=1.2, hatch=hatch, zorder=3)
        x0 += val


def main() -> int:
    st.apply()
    manifest, audit, codes, issues, checks = load()
    code_order = [c for c, _, _ in codes]
    labels = {c: l for c, l, _ in codes}
    n_ratings = len(checks)
    primary = [i for i in issues if i["purpose"] == "primary"]
    n_primary = {rub: sum(1 for c in checks if c["rubric"] == rub and c["purpose"] == "primary") for rub, _ in RUBRICS}
    by_code_rub_sev = Counter((i["code"], i["rubric"], i["severity"]) for i in primary)
    by_code_rub_proj = Counter((i["code"], i["rubric"], i["project"]) for i in primary)
    by_type_rub = Counter((i["type"], i["rubric"]) for i in primary)
    n_other = sum(1 for i in issues if i["code"] == "other")
    n_multi = sum(1 for i in issues if i["n_matching_rules"] >= 2)

    fig = plt.figure(figsize=(12.4, 12.2))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.35, 0.6, 1.0], height_ratios=[1.35, 1.0], hspace=0.5, wspace=0.3,
                          top=0.87, bottom=0.06, left=0.17, right=0.98)

    # ---- (A) counts per category, split by rubric, stacked by severity (primary ratings) ----
    axA = fig.add_subplot(gs[0, 0])
    order = code_order
    for k, code in enumerate(order):
        base = (len(order) - 1 - k) * 1.0
        for ri, (rub, _) in enumerate(RUBRICS):
            y = base + (0.19 if ri == 0 else -0.19)
            segs = [(by_code_rub_sev.get((code, rub, s), 0), SEV_HATCH[s]) for s in SEVERITIES]
            hbar_segments(axA, y, segs, RUBRIC_COLOR[rub], 0.34)
            tot = sum(v for v, _ in segs)
            if tot:
                axA.text(tot + 0.8, y, str(tot), va="center", ha="left", fontsize=7, color=st.INK["secondary"])
    axA.set_yticks([(len(order) - 1 - k) for k in range(len(order))])
    axA.set_yticklabels([textwrap.shorten(labels[c], 44, placeholder="...") for c in order])
    axA.set_ylim(-0.7, len(order) - 0.3)
    axA.set_xlabel("issues detected in primary ratings (count)")
    axA.set_title("A  Categories by rubric and severity (primary ratings)", pad=8)
    st.hairline_grid(axA, "x")
    axA.tick_params(axis="y", length=0)
    handles = []
    for rub, name in RUBRICS:
        handles.append(Patch(facecolor=RUBRIC_COLOR[rub], label=f"{name}, primary ratings (n={n_primary[rub]})"))
    for s in SEVERITIES:
        handles.append(Patch(facecolor=st.INK["secondary"], edgecolor=st.INK["surface"], hatch=SEV_HATCH[s], linewidth=1.0,
                             label=f"severity {s}" + (" (no hatch)" if SEV_HATCH[s] is None else f" (hatch {SEV_HATCH[s]})")))
    axA.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, -0.09), ncol=2, fontsize=7.2, handlelength=1.6, handleheight=1.1,
               columnspacing=1.2)

    # ---- (E) evaluator-declared type split (primary ratings) ----
    axE = fig.add_subplot(gs[0, 1])
    for k, t in enumerate(TYPES):
        base = len(TYPES) - 1 - k
        for ri, (rub, _) in enumerate(RUBRICS):
            y = base + (0.19 if ri == 0 else -0.19)
            v = by_type_rub.get((t, rub), 0)
            axE.barh(y, v, height=0.34, color=RUBRIC_COLOR[rub], zorder=3)
            if v:
                axE.text(v + 1.5, y, str(v), va="center", ha="left", fontsize=7, color=st.INK["secondary"])
    axE.set_yticks([len(TYPES) - 1 - k for k in range(len(TYPES))])
    axE.set_yticklabels([t.replace("_", " ") for t in TYPES], fontsize=7.5)
    axE.set_ylim(-0.7, len(TYPES) - 0.3)
    axE.set_xlim(0, max(by_type_rub.values()) * 1.3)
    axE.tick_params(axis="y", length=0)
    axE.set_xlabel("issues (count)")
    axE.set_title("B  Evaluator type\n(primary ratings)", pad=8, fontsize=9)
    st.hairline_grid(axE, "x")

    # ---- (C) consistency-check outcomes per rating (all accepted ratings) ----
    axC = fig.add_subplot(gs[0, 2])
    checks_sorted = sorted(checks, key=lambda c: (c["rubric"], st.PROJECTS.index(c["project"]), c["cohort"], c["generation_rep"], c["rating"]))
    sep = []
    x = 0.0
    prev = None
    for c in checks_sorted:
        key = (c["rubric"], c["project"])
        if prev is not None and key != prev:
            x += 0.9 if key[0] == prev[0] else 1.8
            if key[0] != prev[0]:
                sep.append(x - 0.9)
        prev = key
        c["_x"] = x
        x += 1.0
    for c in checks_sorted:
        bottom = 0
        for part in ("passed", "warnings", "failed"):
            v = c[part]
            if v:
                axC.bar(c["_x"], v, bottom=bottom, width=0.78, color=CHECK_COLOR[part], edgecolor=st.INK["surface"], linewidth=1.0, zorder=3)
                bottom += v
    groups = defaultdict(list)
    for c in checks_sorted:
        groups[(c["rubric"], c["project"])].append(c["_x"])
    ymax = max(c["passed"] + c["warnings"] + c["failed"] for c in checks) + 6
    axC.set_xticks([(min(gx) + max(gx)) / 2 for gx in groups.values()])
    axC.set_xticklabels([proj.replace("_", "-") for (_, proj) in groups], rotation=45, ha="right", fontsize=7)
    for rub, name in RUBRICS:
        gx = [c["_x"] for c in checks_sorted if c["rubric"] == rub]
        axC.text((min(gx) + max(gx)) / 2, ymax - 1.2, name, ha="center", va="bottom", fontsize=8, fontweight="bold", color=st.INK["secondary"])
    for s_ in sep:
        axC.axvline(s_, color=st.INK["grid"], linewidth=0.6, zorder=0)
    axC.tick_params(axis="x", length=0)
    axC.set_ylim(0, ymax + 2)
    axC.set_ylabel("consistency checks reported by the rating")
    axC.set_xlabel(f"one bar per accepted rating ({n_ratings}), grouped by rubric and project")
    axC.set_title("C  Consistency-check outcomes per rating", pad=8)
    st.hairline_grid(axC)
    axC.legend(handles=[Patch(facecolor=CHECK_COLOR[k], label=k) for k in ("passed", "warnings", "failed")],
               loc="upper left", bbox_to_anchor=(0.0, -0.2), fontsize=7.2, ncol=3)

    # ---- (B) per-project small multiples (primary ratings) ----
    gsB = gs[1, :].subgridspec(1, 4, wspace=0.12)
    xmax = max(by_code_rub_proj.values()) + 2
    for pi, proj in enumerate(st.PROJECTS):
        ax = fig.add_subplot(gsB[0, pi])
        for k, code in enumerate(order):
            base = (len(order) - 1 - k)
            for ri, (rub, _) in enumerate(RUBRICS):
                y = base + (0.19 if ri == 0 else -0.19)
                v = by_code_rub_proj.get((code, rub, proj), 0)
                ax.barh(y, v, height=0.34, color=RUBRIC_COLOR[rub], zorder=3)
        ax.set_yticks([(len(order) - 1 - k) for k in range(len(order))])
        if pi == 0:
            ax.set_yticklabels([textwrap.shorten(labels[c], 40, placeholder="...") for c in order], fontsize=6.8)
        else:
            ax.set_yticklabels([])
        ax.set_ylim(-0.7, len(order) - 0.3)
        ax.set_xlim(0, xmax)
        n_r10 = sum(1 for c in checks if c["project"] == proj and c["rubric"] == RUBRICS[0][0] and c["purpose"] == "primary")
        n_r20 = sum(1 for c in checks if c["project"] == proj and c["rubric"] == RUBRICS[1][0] and c["purpose"] == "primary")
        ax.set_title(f"{proj.replace('_', '-')}  ({n_r10} r10 + {n_r20} r20 primary)", fontsize=8.5, pad=6)
        ax.tick_params(axis="y", length=0)
        st.hairline_grid(ax, "x")
        if pi == 1:
            ax.set_xlabel("issues detected in primary ratings (count), same category rows as panel A; rubric10 upper bar, rubric20 lower bar", loc="left")
    fig.text(0.17, 0.395, "D  Issue categories per project (primary ratings)", fontsize=9.5, fontweight="bold", ha="left", va="bottom")

    n_primary_issues = len(primary)
    note = (f"{len(issues)} issues from {n_ratings} accepted ratings ({n_primary_issues} from the {sum(n_primary.values())} primary ratings drawn in A, B and D); "
            f"{n_other} coded other (no rule matched); {n_multi} of {len(issues)} issues match 2+ rules, first rule wins. Rules are keyword/regex matches on "
            "type + description in the order listed in issue_codes.csv; the CSV keeps the matched span and every other matching code.")
    fig.text(0.17, 0.955, textwrap.fill(note, 150), fontsize=7.2, color=st.INK["secondary"], ha="left", va="top")
    fig.suptitle("Issues raised by the semantic rubric evaluators on the reference rescore, coded by a fixed keyword table",
                 x=0.17, ha="left", fontsize=11, fontweight="bold", y=0.985)

    evaluator = manifest["transport"]["runtime_model_identifier"]
    basis = (f"Record set: reference rescore 2026-09-12 (CBORG runtime), {n_ratings} accepted ratings "
             f"({n_primary[RUBRICS[0][0]]}+{n_primary[RUBRICS[1][0]]} primary drawn in A/B/E, all in C) over 24 API-arm full records; evaluator {evaluator}; issues from "
             "semantic_analysis.issues_detected, checks from semantic_analysis.consistency_checks; codes in scripts/figures/issue_codes.csv")
    category_rows = [{"code": c, "label": labels[c], "rubric": rub, "severity": s, "count_primary": by_code_rub_sev.get((c, rub, s), 0),
                      "count_all": sum(1 for i in issues if i["code"] == c and i["rubric"] == rub and i["severity"] == s)}
                     for c in order for rub, _ in RUBRICS for s in SEVERITIES]
    type_rows = [{"type": t, "rubric": rub, "count_primary": by_type_rub.get((t, rub), 0)} for t in TYPES for rub, _ in RUBRICS]
    st.save(fig, "fig11_issue_taxonomy", {"main": issues, "categories": category_rows, "types": type_rows,
                                          "checks": [{k: v for k, v in c.items() if k != "_x"} for c in checks]}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
