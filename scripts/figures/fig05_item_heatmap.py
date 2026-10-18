#!/usr/bin/env python
"""#2296: item-level score heatmaps for the reference rescore, rubric10 and rubric20.

Record set: the frozen CBORG reference rescore (notes/reference_rescore_2026-09-12_cborg_runtime):
24 API-arm full records (4 projects x v7/v8 x 3 generation replicates) and the 56 accepted
ratings bound in completion_audit.json (32 rubric10 files, 24 rubric20 files). Columns are
project > cohort > replicate; each cell shows rating 1 of the record. For the v7 rep 1
records rubric10 has three ratings of the same bytes: a dot marks cells where the three
ratings disagree (score or applicability).

Rows: rubric10 = the 50 sub-elements in data/rubric/rubric10.txt order (ids E1.1..E10.5,
matched to the evaluation JSON by element id and sub-element position, names checked);
rubric20 = the 20 questions in data/rubric/rubric20.txt order (Q1..Q20, matched by id).

Not applicable: rubric10 sub-element with `applicable: false` (score null; the count is
checked against overall_score.sub_elements_not_applicable), rubric20 question with
`applicable: false` (checked against overall_score.questions_not_applicable). Hatched.
Missing/unknown = blank with a hairline border. Pass/fail questions carry a ring.
Row marginal: mean score / item max over records where the item applies. Column marginal:
overall_score.normalized_percentage (applicability-adjusted), rating 1; repeat ratings as ticks.
"""
from __future__ import annotations

import json
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import Patch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

ARCH = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime"
COHORTS = ["v7", "v8"]
R10_COLORS = {0: st.ORDINAL[0], 1: st.ORDINAL[7]}
R20_COLORS = {0: st.ORDINAL[0], 1: st.ORDINAL[1], 2: st.ORDINAL[3], 3: st.ORDINAL[5], 4: st.ORDINAL[7], 5: st.ORDINAL[9]}
PF_COLORS = {0: st.ORDINAL[0], 1: st.ORDINAL[9]}


def rubric_rows():
    r10 = yaml.safe_load((st.ROOT / "data/rubric/rubric10.txt").read_text())["d4d_complex_proxy_rubric"]["rubric"]
    rows10 = []
    for e in r10:
        for k, s in enumerate(e["sub_elements"]):
            rows10.append({"group_id": e["id"], "group": e["name"], "item_id": s["item_id"], "name": s["name"], "pos": k,
                           "max": 1, "kind": "binary"})
    r20 = yaml.safe_load((st.ROOT / "data/rubric/rubric20.txt").read_text())["d4d_evaluation_rubric"]["rubric"]
    rows20 = [{"group_id": None, "group": None, "item_id": q["item_id"], "qid": q["id"], "name": q["name"],
               "max": 1 if q["score_type"] == "pass_fail" else 5, "kind": q["score_type"]} for q in r20]
    return rows10, rows20


def load_ratings():
    manifest = json.loads((ARCH / "manifest.json").read_text())
    audit = json.loads((ARCH / "completion_audit.json").read_text())
    jobs = {j["id"]: j for j in manifest["jobs"]}
    out = []
    for r in audit["ratings"]:
        j = jobs[r["job_id"]]
        doc = json.loads((st.ROOT / r["output"]).read_text())
        assert doc["overall_score"]["total_points"] == r["overall_score"]["total_points"], r["job_id"]
        out.append({"job": j, "doc": doc})
    return out


def cells_r10(doc, rows10):
    """item_id -> (score or None, applicable) with structural checks against the rubric file."""
    out = {}
    n_na = 0
    for e, group in zip(doc["elements"], {r["group_id"]: r["group"] for r in rows10}.items()):
        assert e["id"] == group[0] and e["name"] == group[1], (e["id"], e["name"])
        subs = [r for r in rows10 if r["group_id"] == e["id"]]
        assert len(e["sub_elements"]) == len(subs)
        for s, r in zip(e["sub_elements"], subs):
            assert s["name"] == r["name"], (r["item_id"], s["name"])
            na = s.get("applicable") is False
            n_na += na
            assert not (na and s["score"] is not None)
            out[r["item_id"]] = (None if na else s["score"], not na)
    assert n_na == doc["overall_score"]["sub_elements_not_applicable"], doc["d4d_file"]
    return out


def cells_r20(doc, rows20):
    qs = [q for c in doc["categories"] for q in c["questions"]]
    out = {}
    n_na = 0
    for q, r in zip(qs, rows20):
        assert q["id"] == r["qid"] and q["name"] == r["name"], (q["id"], q["name"])
        na = not q["applicable"]
        n_na += na
        out[r["item_id"]] = (None if na else q["score"], not na)
    assert n_na == doc["overall_score"]["questions_not_applicable"], doc["d4d_file"]
    cats = [(c["name"], len(c["questions"])) for c in doc["categories"]]
    return out, cats


def draw_panel(ax, ax_top, ax_right, rows, cols, xs, primary, repeats, colors, kind, groups, export, rubric):
    pad = 0.08
    for i, r in enumerate(rows):
        vals = []
        for c, x0 in zip(cols, xs):
            key = (c["project"], c["cohort"], c["rep"])
            cell = primary.get(key)
            state, score = "missing", None
            if cell is None:
                ax.add_patch(Rectangle((x0 + pad, i + pad), 1 - 2 * pad, 1 - 2 * pad, facecolor=st.INK["surface"],
                                       edgecolor=st.INK["axis"], linewidth=0.4))
            else:
                score, applicable = cell["cells"][r["item_id"]]
                if not applicable:
                    state = "not_applicable"
                    ax.add_patch(Rectangle((x0 + pad, i + pad), 1 - 2 * pad, 1 - 2 * pad, facecolor=st.INK["surface"],
                                           edgecolor=st.INK["axis"], linewidth=0.4, hatch=st.HATCH))
                else:
                    state = "scored"
                    cmap = PF_COLORS if r["kind"] == "pass_fail" else colors
                    ax.add_patch(Rectangle((x0 + pad, i + pad), 1 - 2 * pad, 1 - 2 * pad, facecolor=cmap[score]))
                    vals.append(score / r["max"])
                    if r["kind"] == "pass_fail":
                        ax.plot(x0 + 0.5, i + 0.5, marker="o", markersize=3.2, markerfacecolor="none",
                                markeredgecolor=st.INK["surface"] if score else st.INK["primary"], markeredgewidth=0.8, linestyle="none")
            disagree = ""
            reps = repeats.get(key, [])
            if reps:
                seen = {cell["cells"][r["item_id"]]} | {rp["cells"][r["item_id"]] for rp in reps}
                if len(seen) > 1:
                    disagree = "yes"
                    ax.plot(x0 + 0.5, i + 0.5, marker="o", markersize=2.6, color=st.INK["primary"],
                            markeredgecolor=st.INK["surface"], markeredgewidth=0.6, linestyle="none", zorder=5)
                else:
                    disagree = "no"
            export.append({"rubric": rubric, "item_id": r["item_id"], "group": r["group"] or "", "item": r["name"],
                           "project": c["project"], "cohort": c["cohort"], "generation_rep": c["rep"], "rating": 1,
                           "score": "" if score is None else score, "item_max": r["max"], "score_type": r["kind"],
                           "state": state, "repeat_ratings_disagree": disagree})
        # row marginal: mean score / item max where applicable
        if vals:
            m = sum(vals) / len(vals)
            ax_right.barh(i + 0.5, m, height=0.62, color=st.SERIES[0], zorder=2)
    ax.set_xlim(xs[0] - 0.05, xs[-1] + 1.05); ax.set_ylim(len(rows), 0)
    ax.set_yticks([i + 0.5 for i in range(len(rows))])
    ax.set_yticklabels([f'{r["item_id"]}  {r["name"]}' for r in rows], fontsize=6.5)
    ax.tick_params(axis="y", length=0, pad=2)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks([x0 + 0.5 for x0 in xs]); ax.set_xticklabels([str(c["rep"]) for c in cols], fontsize=6)
    ax.tick_params(axis="x", length=0)
    # group separators and labels
    y0 = 0
    for name, n in groups:
        if y0:
            ax.axhline(y0, color=st.INK["axis"], linewidth=0.6, zorder=3)
        ax.text(-0.57, y0 + n / 2, textwrap.fill(name, 26), ha="right", va="center", fontsize=6.5, fontweight="bold",
                color=st.INK["secondary"], transform=ax.get_yaxis_transform(), clip_on=False, linespacing=1.0)
        y0 += n
    prev = None
    for c, x0 in zip(cols, xs):
        key = (c["project"], c["cohort"])
        if prev is not None and prev != key:
            ax.axvline(x0 - (0.35 if prev[0] != key[0] else 0.125),
                       color=st.INK["axis"] if prev[0] != key[0] else st.INK["grid"], linewidth=0.6, zorder=0)
        prev = key
    ax_right.set_xlim(0, 1.0); ax_right.set_xticks([0, 0.5, 1]); ax_right.set_xticklabels(["0", ".5", "1"], fontsize=6.5)
    ax_right.tick_params(axis="y", length=0, labelleft=False); ax_right.tick_params(axis="x", length=2)
    for sp in ("left", "top", "right"):
        ax_right.spines[sp].set_visible(False)
    st.hairline_grid(ax_right, "x")
    # column marginal: adjusted percentage
    for c, x0 in zip(cols, xs):
        key = (c["project"], c["cohort"], c["rep"])
        cell = primary.get(key)
        if cell is None:
            continue
        ax_top.bar(x0 + 0.5, cell["adjusted_pct"], width=0.7, color=st.SERIES[0], zorder=2)
        for rp in repeats.get(key, []):
            ax_top.plot(x0 + 0.5, rp["adjusted_pct"], marker="_", markersize=6, color=st.INK["primary"],
                        markeredgewidth=0.9, linestyle="none", zorder=3)
    ax_top.set_ylim(0, 100); ax_top.set_yticks([0, 50, 100]); ax_top.tick_params(axis="y", labelsize=6.5, length=2)
    ax_top.set_ylabel("adjusted %", fontsize=7, labelpad=4)
    st.hairline_grid(ax_top); ax_top.tick_params(axis="x", length=0, labelbottom=False); ax_top.spines["bottom"].set_visible(False)


def main() -> int:
    st.apply()
    rows10, rows20 = rubric_rows()
    ratings = load_ratings()
    primary = {"rubric10-semantic": {}, "rubric20-semantic": {}}
    repeats = {"rubric10-semantic": defaultdict(list), "rubric20-semantic": defaultdict(list)}
    cats20 = None
    for r in ratings:
        j, doc = r["job"], r["doc"]
        if j["rubric"] == "rubric10-semantic":
            cells = cells_r10(doc, rows10)
        else:
            cells, cats20 = cells_r20(doc, rows20)
        entry = {"cells": cells, "adjusted_pct": doc["overall_score"]["normalized_percentage"], "rating": j["rating"],
                 "job_id": j["id"]}
        key = (j["project"], j["cohort"], j["generation_rep"])
        if j["rating"] == 1:
            assert key not in primary[j["rubric"]]
            primary[j["rubric"]][key] = entry
        else:
            repeats[j["rubric"]][key].append(entry)
    n_records = len({r["job"]["input"] for r in ratings})
    assert n_records == 24 and len(ratings) == 56, (n_records, len(ratings))

    cols, xs, x = [], [], 0.0
    for pi, proj in enumerate(st.PROJECTS):
        for ci, cohort in enumerate(COHORTS):
            for rep in (1, 2, 3):
                cols.append({"project": proj, "cohort": cohort, "rep": rep}); xs.append(x); x += 1.0
            x += 0.25
        x += 0.45

    fig = plt.figure(figsize=(10.4, 12.6))
    gs = fig.add_gridspec(5, 2, height_ratios=[1.0, len(rows10) * 0.155, 0.85, 1.0, len(rows20) * 0.155],
                          width_ratios=[1.0, 0.13], hspace=0.06, wspace=0.03, left=0.43, right=0.985, top=0.925, bottom=0.095)
    ax10_top = fig.add_subplot(gs[0, 0]); ax10 = fig.add_subplot(gs[1, 0], sharex=ax10_top); ax10_r = fig.add_subplot(gs[1, 1], sharey=ax10)
    ax20_top = fig.add_subplot(gs[3, 0]); ax20 = fig.add_subplot(gs[4, 0], sharex=ax20_top); ax20_r = fig.add_subplot(gs[4, 1], sharey=ax20)
    export = []
    groups10 = [(f'E{e}  {name}', 5) for e, name in {r["group_id"]: r["group"] for r in rows10}.items()]
    draw_panel(ax10, ax10_top, ax10_r, rows10, cols, xs, primary["rubric10-semantic"], repeats["rubric10-semantic"],
               R10_COLORS, "binary", groups10, export, "rubric10-semantic")
    draw_panel(ax20, ax20_top, ax20_r, rows20, cols, xs, primary["rubric20-semantic"], repeats["rubric20-semantic"],
               R20_COLORS, "numeric", cats20, export, "rubric20-semantic")
    for r in rows10:
        r["group"] = r["group"]  # exported via export rows already
    for ax_top, title in ((ax10_top, "rubric10: 50 sub-elements, binary score"), (ax20_top, "rubric20: 20 questions, 0-5 or pass/fail")):
        ax_top.text(0.0, 1.52, title, transform=ax_top.transAxes, ha="left", va="bottom", fontsize=8.5, fontweight="bold")
    ax10_r.set_title("mean score\n/ item max", fontsize=6.8, pad=3, loc="left", fontweight="normal", color=st.INK["secondary"])
    ax20_r.set_title("mean score\n/ item max", fontsize=6.8, pad=3, loc="left", fontweight="normal", color=st.INK["secondary"])
    ax20.set_xlabel("generation replicate", fontsize=7.5)
    # column headers over each panel's marginal
    for ax_top in (ax10_top, ax20_top):
        first = {}
        for c, x0 in zip(cols, xs):
            first.setdefault(c["project"], [x0, x0]); first[c["project"]][1] = x0 + 1
            first.setdefault((c["project"], c["cohort"]), [x0, x0]); first[(c["project"], c["cohort"])][1] = x0 + 1
        for proj in st.PROJECTS:
            a, b = first[proj]
            ax_top.text((a + b) / 2, 1.30, proj.replace("_", "-"), ha="center", va="bottom", fontsize=8, fontweight="bold",
                        color=st.INK["secondary"], transform=ax_top.get_xaxis_transform())
            for cohort in COHORTS:
                a, b = first[(proj, cohort)]
                ax_top.text((a + b) / 2, 1.10, cohort, ha="center", va="center", fontsize=6.8, color=st.INK["secondary"],
                            transform=ax_top.get_xaxis_transform())
    # legend, built by hand
    h = [Patch(facecolor=R10_COLORS[0], label="rubric10 score 0"), Patch(facecolor=R10_COLORS[1], label="rubric10 score 1")]
    h += [Patch(facecolor=R20_COLORS[k], label=f"rubric20 score {k}") for k in range(6)]
    fig.legend(handles=h, loc="lower left", bbox_to_anchor=(0.04, 0.040), ncol=8, fontsize=6.6, handlelength=1.4, columnspacing=1.0,
               handletextpad=0.5)
    h2 = [plt.Line2D([], [], marker="o", markersize=3.2, markerfacecolor="none", markeredgecolor=st.INK["primary"], linestyle="none",
                     label="ring: pass/fail question (1 = pass, 0 = fail)"),
          plt.Line2D([], [], marker="o", markersize=2.6, color=st.INK["primary"], linestyle="none",
                     label="dot: the three ratings of this record disagree (rubric10, v7 rep 1)"),
          Patch(facecolor=st.INK["surface"], edgecolor=st.INK["axis"], linewidth=0.5, hatch=st.HATCH, label="not applicable (excluded from the adjusted denominator)"),
          Patch(facecolor=st.INK["surface"], edgecolor=st.INK["axis"], linewidth=0.5, label="no rating"),
          plt.Line2D([], [], marker="_", markersize=6, color=st.INK["primary"], linestyle="none", label="tick: repeat rating's adjusted %")]
    fig.legend(handles=h2, loc="lower left", bbox_to_anchor=(0.04, 0.012), ncol=3, fontsize=6.6, handlelength=1.4, columnspacing=1.2,
               handletextpad=0.5)
    fig.suptitle("Item-level scores per record in the reference rescore, rubric10 and rubric20",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=0.99)
    n_disagree = sum(1 for e in export if e["repeat_ratings_disagree"] == "yes")
    n_na10 = sum(1 for e in export if e["rubric"] == "rubric10-semantic" and e["state"] == "not_applicable")
    n_na20 = sum(1 for e in export if e["rubric"] == "rubric20-semantic" and e["state"] == "not_applicable")
    basis = (f"Record set: reference rescore 2026-09-12 (CBORG runtime), {n_records} API-arm full records, {len(ratings)} accepted "
             f"ratings (32 rubric10, 24 rubric20); cells = rating 1; N/A cells: {n_na10} rubric10, {n_na20} rubric20; "
             f"repeat-rating disagreements: {n_disagree} of {4 * 50} rubric10 cells")
    st.save(fig, "fig05_item_heatmap", {"main": export}, basis)
    print(f"disagreements {n_disagree}, N/A rubric10 {n_na10}, rubric20 {n_na20}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
