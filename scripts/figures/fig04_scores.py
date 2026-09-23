#!/usr/bin/env python
"""#2295: rubric10 / rubric20 score distributions for the reference rescore, with the
spread from generation replicates and from repeated ratings of fixed record bytes
shown separately, and a procedure table per condition underneath.

Record set: the frozen CBORG reference rescore (notes/reference_rescore_2026-09-12_cborg_runtime):
24 API-arm full records (4 projects x v7/v8 x 3 generation replicates), 56 accepted ratings.
Scores are read from completion_audit.json (the accepted bindings) and cross-checked
against the evaluation JSON files. Nothing is pooled across instruments.
"""
from __future__ import annotations

import json
import re
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

ARCH = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime"
RUBRICS = [("rubric10-semantic", "rubric10 (50 points)"), ("rubric20-semantic", "rubric20 (88 points)")]
COHORTS = ["v7", "v8"]
MARK = {"v7": "o", "v8": "s"}


def header_fields(path: Path) -> dict[str, str]:
    out = {}
    with path.open() as fh:
        for line in fh:
            if not line.startswith("#"):
                break
            m = re.match(r"#\s*([^:]+):\s*(.*)", line)
            if m:
                out[m.group(1).strip()] = m.group(2).strip()
    return out


def load():
    manifest = json.loads((ARCH / "manifest.json").read_text())
    audit = json.loads((ARCH / "completion_audit.json").read_text())
    jobs = {j["id"]: j for j in manifest["jobs"]}
    rows = []
    for r in audit["ratings"]:
        j = jobs[r["job_id"]]
        out = st.ROOT / r["output"]
        doc = json.loads(out.read_text())
        o = doc["overall_score"]
        assert o["total_points"] == r["overall_score"]["total_points"], r["job_id"]
        rows.append({
            "job_id": j["id"], "project": j["project"], "cohort": j["cohort"], "label": j["label"],
            "generation_rep": j["generation_rep"], "rating": j["rating"], "purpose": j["purpose"],
            "rubric": j["rubric"], "instrument_version": doc.get("version"),
            "total_points": o["total_points"], "max_points": o["max_points"],
            "adjusted_max_points": o["adjusted_max_points"], "fixed_pct": o["fixed_percentage"],
            "adjusted_pct": o["normalized_percentage"], "input": j["input"],
        })
    return manifest, audit, rows


def procedure_table(manifest, rows):
    """One column per cohort; values read from record headers and the manifest."""
    cols = {}
    for c in COHORTS:
        inputs = sorted({r["input"] for r in rows if r["cohort"] == c})
        hdrs = [header_fields(st.ROOT / p) for p in inputs]
        def uniq(key):
            vals = sorted({h.get(key, "?") for h in hdrs})
            return vals[0] if len(vals) == 1 else " / ".join(vals)
        versions = sorted({str(r["instrument_version"]) for r in rows if r["cohort"] == c})
        cols[c] = {
            "generation runtime": uniq("Agent runtime"),
            "generation provider": uniq("Provider"),
            "generation model": uniq("Model"),
            "prompt": re.sub(r".*generic-", "generic-", uniq("Mode")),
            "generation temperature": uniq("Temperature"),
            "evaluator requested": manifest["requested_model"],
            "evaluator identified": manifest["transport"]["runtime_model_identifier"],
            "evaluator effort / temp.": f'{manifest["effort"]} / {manifest["temperature"] if manifest["temperature"] is not None else "unspecified"}',
            "instrument versions": ", ".join(versions),
            "denominators": "50 (rubric10), 88 (rubric20)",
        }
    return cols


def main() -> int:
    st.apply()
    manifest, audit, rows = load()
    n_ratings = len(rows)
    n_records = len({r["input"] for r in rows})
    fig = plt.figure(figsize=(9.2, 7.0))
    gs = fig.add_gridspec(2, 2, height_ratios=[3.2, 1.7], hspace=0.78, wspace=0.18)
    axes = [fig.add_subplot(gs[0, i]) for i in range(2)]
    plotted = []
    for ax, (rubric, title) in zip(axes, RUBRICS):
        sub = [r for r in rows if r["rubric"] == rubric]
        by_key = defaultdict(list)
        for r in sub:
            by_key[(r["project"], r["cohort"], r["generation_rep"])].append(r)
        xt, xl = [], []
        for pi, proj in enumerate(st.PROJECTS):
            for ci, cohort in enumerate(COHORTS):
                x0 = pi * 2.6 + ci * 1.0
                xt.append(x0); xl.append(cohort)
                for rep in (1, 2, 3):
                    ratings = by_key.get((proj, cohort, rep), [])
                    if not ratings:
                        continue
                    x = x0 + (rep - 2) * 0.22
                    primary = [r for r in ratings if r["purpose"] == "primary"]
                    repeats = [r for r in ratings if r["purpose"] != "primary"]
                    y = primary[0]["adjusted_pct"] if primary else ratings[0]["adjusted_pct"]
                    if repeats:  # whisker spans all ratings of the same record bytes
                        ys = [r["adjusted_pct"] for r in ratings]
                        ax.plot([x, x], [min(ys), max(ys)], color=st.ARM_COLOR["api"], linewidth=1.4,
                                solid_capstyle="round", zorder=2, alpha=0.9)
                        for r in repeats:
                            ax.plot(x, r["adjusted_pct"], marker="_", markersize=7, color=st.ARM_COLOR["api"],
                                    markeredgewidth=1.2, linestyle="none", zorder=3)
                    ax.plot(x, y, marker=MARK[cohort], markersize=6.5, color=st.ARM_COLOR["api"],
                            markeredgecolor=st.INK["surface"], markeredgewidth=1, linestyle="none", zorder=4)
                    if abs(primary[0]["fixed_pct"] - y) > 1e-9 if primary else False:
                        ax.plot(x, primary[0]["fixed_pct"], marker=MARK[cohort], markersize=6.5,
                                markerfacecolor="none", markeredgecolor=st.ARM_COLOR["api"], linestyle="none", zorder=4)
                    for r in ratings:
                        plotted.append({**{k: r[k] for k in ("job_id", "project", "cohort", "generation_rep", "rating",
                                                              "purpose", "rubric", "instrument_version", "total_points",
                                                              "max_points", "adjusted_max_points", "fixed_pct", "adjusted_pct")},
                                        "x": round(x, 3)})
            ax.text(pi * 2.6 + 0.5, 101.5, proj.replace("_", "-"), ha="center", va="bottom", fontsize=8.5,
                    color=st.INK["secondary"], fontweight="bold")
        ax.set_xticks(xt); ax.set_xticklabels(xl)
        ax.set_ylim(40, 104); ax.set_yticks(range(40, 101, 10))
        ax.set_ylabel("applicability-adjusted score (%)" if rubric.startswith("rubric10") else "")
        ax.set_title(title, pad=16)
        st.hairline_grid(ax)
        ax.tick_params(axis="x", length=0)
        for pi in range(1, len(st.PROJECTS)):
            ax.axvline(pi * 2.6 - 0.8, color=st.INK["grid"], linewidth=0.6, zorder=0)
    # legend built by hand so identity is never color-alone
    h = [plt.Line2D([], [], marker="o", color=st.ARM_COLOR["api"], linestyle="none", markersize=6.5, label="v7 prompt, one generation replicate"),
         plt.Line2D([], [], marker="s", color=st.ARM_COLOR["api"], linestyle="none", markersize=6.5, label="v8 prompt, one generation replicate"),
         plt.Line2D([], [], marker="_", color=st.ARM_COLOR["api"], linestyle="-", linewidth=1.4, markersize=7, label="repeated ratings of the same record bytes (rubric10, v7 rep 1)"),
         plt.Line2D([], [], marker="o", markerfacecolor="none", markeredgecolor=st.ARM_COLOR["api"], linestyle="none", markersize=6.5, label="fixed-base percentage, where it differs from adjusted")]
    axes[0].legend(handles=h, loc="upper left", bbox_to_anchor=(-0.02, -0.09), ncol=1, handletextpad=0.6)
    fixed_differs = sum(1 for r in rows if abs(r["fixed_pct"] - r["adjusted_pct"]) > 1e-9)
    note = ("All ratings in this cohort are API-arm records; agentic and direct arms have no ratings under a "
            "compatible instrument yet and are not drawn. Fixed-base and adjusted percentages coincide for "
            f"{n_ratings - fixed_differs} of {n_ratings} ratings (no item excluded); hollow markers would show the fixed base where they differ.")
    fig.text(0.53, 0.415, textwrap.fill(note, 88), fontsize=7.2, color=st.INK["secondary"], ha="left", va="top")
    # procedure table
    axt = fig.add_subplot(gs[1, :]); axt.axis("off")
    cols = procedure_table(manifest, rows)
    keys = list(next(iter(cols.values())).keys())
    cell = [[k] + [cols[c][k] for c in COHORTS] for k in keys]
    tbl = axt.table(cellText=cell, colLabels=["procedure characteristic"] + [f"{c} condition" for c in COHORTS],
                    loc="upper left", cellLoc="left", colLoc="left", bbox=[0.0, 0.0, 1.0, 1.0])
    tbl.auto_set_font_size(False); tbl.set_fontsize(7.2)
    for (r, c), cl in tbl.get_celld().items():
        cl.set_edgecolor(st.INK["grid"]); cl.set_linewidth(0.5)
        cl.get_text().set_color(st.INK["primary"] if r else st.INK["secondary"])
        if r == 0:
            cl.get_text().set_fontweight("bold")
        if c == 0:
            cl.set_width(0.24)
    fig.suptitle("Reference rescore scores by project and prompt condition, with replicate and repeat spread",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=0.985)
    basis = (f"Record set: reference rescore 2026-09-12 (CBORG runtime), {n_records} API-arm full records, "
             f"{n_ratings} accepted ratings; scores from completion_audit.json cross-checked with evaluation files")
    st.save(fig, "fig04_scores", {"main": plotted, "procedure": [{"characteristic": k, **{c: cols[c][k] for c in COHORTS}} for k in keys]}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
