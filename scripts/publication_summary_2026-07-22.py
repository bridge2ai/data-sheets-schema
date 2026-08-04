#!/usr/bin/env python3
"""Deterministic publication summary for the 2026-07-22 D4D eval rerun.

HISTORICAL. The evaluations this reads scored
`data/d4d_concatenated/claudecode_agent/2026-04-10_sonnet-4.6/` and the flat
pre-run-label layout. That label was archived as unattestable, so the summaries
this produces describe records the study has excluded (#286). Re-pointing it at
the current corpus means re-running the evaluations, not re-running this.

Reads every *_evaluation.json under
data/evaluation_llm/{rubric10,rubric20,rubric10_semantic,rubric20_semantic}/concatenated/
(skipping _archive_* subdirs) and emits:

  data/evaluation_llm/publication_summary_2026-07-22.md   (headline table)
  data/evaluation_llm/publication_summary_2026-07-22.tsv  (long format)
  {rubric}/concatenated/summary_report.md                 (per-rubric table)
  {rubric}/concatenated/scores_summary.txt                (per-rubric plain text)
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EVAL = BASE / "data" / "evaluation_llm"
RUBRICS = ["rubric10", "rubric20", "rubric10_semantic", "rubric20_semantic"]
PROJECTS = ["AI_READI", "CHORUS", "CM4AI", "VOICE"]
RUN_DATE = "2026-07-22"


def load_rubric(rubric):
    """Return {(project, method): overall_score_dict} for one rubric dir."""
    out = {}
    d = EVAL / rubric / "concatenated"
    for f in sorted(d.glob("*_evaluation.json")):
        if "_archive_" in f.parts:
            continue
        data = json.loads(f.read_text())
        project = data.get("project")
        method = data.get("method")
        if project and method:
            out[(project, method)] = data.get("overall_score", {})
    return out


def pick_pct(score):
    """Prefer normalized_percentage (rubric20-semantic), else percentage."""
    return score.get("normalized_percentage", score.get("percentage"))


def per_rubric_report(rubric, scores):
    methods = sorted({m for (_, m) in scores.keys()})
    lines = [
        f"# {rubric} Evaluation Summary (Publication Run {RUN_DATE})",
        "",
        f"Rubric: `{rubric}` | Run: `{RUN_DATE}` | Model: `claude-sonnet-4-5-20250929`",
        "",
        "## Overall Scores by Method × Project",
        "",
    ]

    header = ["Method"] + PROJECTS + ["Mean"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for m in methods:
        row = [f"`{m}`"]
        pcts = []
        for p in PROJECTS:
            s = scores.get((p, m))
            if s is None:
                row.append("—")
                continue
            pts, mx, pct = s.get("total_points"), s.get("max_points"), pick_pct(s)
            row.append(f"{pts}/{mx} ({pct:.1f}%)" if pct is not None else "—")
            if pct is not None:
                pcts.append(pct)
        mean = f"{sum(pcts)/len(pcts):.1f}%" if pcts else "—"
        row.append(mean)
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    txt = [f"# {rubric} scores — publication run {RUN_DATE}", ""]
    for m in methods:
        txt.append(f"[{m}]")
        for p in PROJECTS:
            s = scores.get((p, m))
            if s is None:
                txt.append(f"  {p:10} —")
                continue
            pts, mx, pct = s.get("total_points"), s.get("max_points"), pick_pct(s)
            pct_str = f"{pct:.1f}%" if pct is not None else "—"
            txt.append(f"  {p:10} {pts}/{mx}  ({pct_str})")
        txt.append("")
    return "\n".join(lines) + "\n", "\n".join(txt) + "\n"


def publication_table(all_scores):
    """Headline table: rows = projects, columns = 4 rubrics × 2 variants."""
    lines = [
        f"# D4D Publication Summary — Rerun {RUN_DATE}",
        "",
        "Final claudecode_agent scores across the four rubrics for both full D4D and",
        "D4D-core outputs, per Grand Challenge project. All 32 evaluations produced by",
        "the four `d4d-rubric*` agents at git commit `0e19e85f` (PR #154 merged).",
        "",
        "Input D4D file hashes and agent-prompt hashes: see `run_manifest_2026-07-22.json`.",
        "",
        "## Overall scores (percent)",
        "",
    ]
    header = ["Project"]
    for r in RUBRICS:
        header += [f"{r} full", f"{r} core"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")

    col_totals = {(r, v): [] for r in RUBRICS for v in ("full", "core")}
    for p in PROJECTS:
        row = [p]
        for r in RUBRICS:
            for variant, method in (("full", "claudecode_agent"),
                                    ("core", "claudecode_agent_core")):
                s = all_scores[r].get((p, method))
                if s is None:
                    row.append("—")
                    continue
                pct = pick_pct(s)
                row.append(f"{pct:.1f}" if pct is not None else "—")
                if pct is not None:
                    col_totals[(r, variant)].append(pct)
        lines.append("| " + " | ".join(row) + " |")

    mean_row = ["**Mean**"]
    for r in RUBRICS:
        for v in ("full", "core"):
            xs = col_totals[(r, v)]
            mean_row.append(f"**{sum(xs)/len(xs):.1f}**" if xs else "—")
    lines.append("| " + " | ".join(mean_row) + " |")
    lines.append("")

    lines += ["## Raw points (total / max)", ""]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for p in PROJECTS:
        row = [p]
        for r in RUBRICS:
            for variant, method in (("full", "claudecode_agent"),
                                    ("core", "claudecode_agent_core")):
                s = all_scores[r].get((p, method))
                if s is None:
                    row.append("—")
                    continue
                pts, mx = s.get("total_points"), s.get("max_points")
                row.append(f"{pts}/{mx}")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def publication_tsv(all_scores):
    rows = [["run_date", "rubric", "project", "d4d_variant", "method",
             "total_points", "max_points", "percentage", "normalized_percentage"]]
    for r in RUBRICS:
        for p in PROJECTS:
            for variant, method in (("full", "claudecode_agent"),
                                    ("core", "claudecode_agent_core")):
                s = all_scores[r].get((p, method), {})
                rows.append([
                    RUN_DATE, r, p, variant, method,
                    str(s.get("total_points", "")),
                    str(s.get("max_points", "")),
                    f"{s.get('percentage', ''):.2f}" if s.get('percentage') is not None else "",
                    f"{s.get('normalized_percentage', ''):.2f}"
                    if s.get('normalized_percentage') is not None else "",
                ])
    return "\n".join("\t".join(r) for r in rows) + "\n"


def main():
    all_scores = {r: load_rubric(r) for r in RUBRICS}

    for r in RUBRICS:
        md, txt = per_rubric_report(r, all_scores[r])
        out_dir = EVAL / r / "concatenated"
        (out_dir / "summary_report.md").write_text(md)
        (out_dir / "scores_summary.txt").write_text(txt)
        print(f"wrote {out_dir}/summary_report.md, scores_summary.txt")

    md_path = EVAL / f"publication_summary_{RUN_DATE}.md"
    tsv_path = EVAL / f"publication_summary_{RUN_DATE}.tsv"
    md_path.write_text(publication_table(all_scores))
    tsv_path.write_text(publication_tsv(all_scores))
    print(f"wrote {md_path}\nwrote {tsv_path}")

    print("\n=== Headline table ===")
    print(publication_table(all_scores))


if __name__ == "__main__":
    main()
