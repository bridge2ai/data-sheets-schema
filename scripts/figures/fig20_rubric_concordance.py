#!/usr/bin/env python
"""#2303 idea 9: do rubric10 and rubric20 put the same records in the same order?

Record set: the frozen CBORG reference rescore (notes/reference_rescore_2026-09-12_cborg_runtime).
completion_audit.json binds 56 accepted ratings of 24 full records (4 projects x v7/v8 prompt x
3 generation replicates, all API-arm records). Each record has exactly one primary rubric10 and
one primary rubric20 rating (48 primary ratings); those 24 matched pairs are compared. The 8
rubric10 repeat ratings (two more ratings of each v7 rep-1 record) are left out, because a second
rating of the same bytes would count one record twice. semantic_review.json (issue #1349) is
joined on the rubric20 job id for its Q19 flags: 9 of 24 rubric20 Q19 rationales were marked
`requires_adjudication`.

At run time the script checks every evaluation file against the sha256 recorded in
completion_audit.json, each evaluation's input hash against the record bytes, the review's
manifest hash against manifest.json, the review's evaluation hashes against the audit, and that
the Q19 score in each rubric20 evaluation equals the review's copy of it.

Method. For each primary rating the applicability-adjusted percentage is recomputed as an exact
fraction, total_points / adjusted_max_points (adjusted_max_points = full maximum minus the maximum
of items the evaluator judged not applicable), and checked against the percentage in the file.
Records are ranked within each instrument (rank 1 = highest percentage; tied records share the
average of the ranks they span; ties are decided on the exact fractions, because the files round
the same 43/47 to 91.49 in one place and 91.5 in another). Spearman's rho is the Pearson
correlation of the two average-rank vectors, which is the tie-corrected form. The left panel
plots rubric10 rank against rubric20 rank with the equal-rank diagonal; records that coincide
exactly are drawn side by side (in both panels), which moves them off their true x value, so a
hairline joins each spread group, a tick marks its true rubric10 value, and the note states the
spacing and the true values (all computed at run time). The right panel shows the percentages themselves on their own
instrument axes, with no diagonal, since a rubric10 and a rubric20 percentage are not on a
common scale. Records whose two ranks differ by at least LABEL_MIN_SHIFT places are labelled
(a display rule, not a test). The note also gives Spearman's rho inside each project (n = 6)
and counts record pairs ordered the same way, oppositely, or tied on at least one instrument.

Caveats. The two instruments measure different constructs (rubric10: 50 sub-elements in 10
elements, each scored 0 or 1; rubric20: 20 questions, 17 graded and 3 pass/fail, 88 points), so
concordance does not establish validity against dataset truth, and disagreement does not by itself
identify a defective rubric. No p-value is printed: the 24 records are 8 project x prompt cells of
3 generation replicates, not independent draws, so the overall correlation mixes agreement between
projects with agreement between replicates of one project; the pair counts in the note separate
the two. The ranks are those of the applicability-adjusted percentages; fig14 shows how the
fixed-base ranks differ. Q19 flags
qualify the rubric20 totals of the flagged ratings; the review assigned no replacement scores and
does not certify the unflagged ones. Applicability exclusions are the LLM evaluator's own
decisions (see fig14).
"""
from __future__ import annotations

import hashlib
import json
import sys
import textwrap
from collections import defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

KEY = "fig20_rubric_concordance"
ARCH = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime"
R10, R20 = "rubric10-semantic", "rubric20-semantic"
FLAGGED = "requires_adjudication"
UNFLAGGED = "not_flagged_by_this_inspection"
# categorical slots 4.. in fixed project order (slots 1-3 belong to the arms), as in fig14
PROJECT_COLOR = {p: st.SERIES[3 + i] for i, p in enumerate(st.PROJECTS)}
COND_MARK = {"v7": "o", "v8": "s"}
COND_SIZE = {"o": 7.4, "s": 6.6}
LABEL_MIN_SHIFT = 4                      # label records whose two ranks differ by >= this many places
PCT_TOL = 0.051                          # reported percentages are rounded to 1 or 2 decimals
DODGE_RANK, DODGE_PCT = 0.62, 1.0        # side-by-side spacing for coincident records


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def q19_score(doc: dict) -> int:
    for c in doc["categories"]:
        for q in c["questions"]:
            if q["id"] == 19:
                return q["score"]
    raise KeyError("Q19 missing")


def load():
    manifest_path = ARCH / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    audit = json.loads((ARCH / "completion_audit.json").read_text())
    review = json.loads((ARCH / "semantic_review.json").read_text())
    msha = sha(manifest_path)
    assert audit["manifest_sha256"] == msha and review["manifest_sha256"] == msha, "manifest hash mismatch"
    jobs = {j["id"]: j for j in manifest["jobs"]}
    bound = {r["job_id"]: r for r in audit["ratings"]}
    counts = {"accepted": len(audit["ratings"]),
              "accepted_r10": sum(1 for r in audit["ratings"] if jobs[r["job_id"]]["rubric"] == R10),
              "accepted_r20": sum(1 for r in audit["ratings"] if jobs[r["job_id"]]["rubric"] == R20)}
    recs: dict[str, dict] = {}
    n_repeats = 0
    for r in audit["ratings"]:
        j = jobs[r["job_id"]]
        path = st.ROOT / r["output"]
        assert sha(path) == r["evaluation_sha256"], f"evaluation bytes changed: {r['job_id']}"
        doc = json.loads(path.read_text())
        assert doc["metadata"]["input_sha256"] == sha(st.ROOT / j["input"]), f"input hash mismatch: {r['job_id']}"
        if j["purpose"] != "primary":
            n_repeats += 1
            continue
        o = doc["overall_score"]
        assert o["total_points"] == r["overall_score"]["total_points"], r["job_id"]
        assert o["adjusted_max_points"] == o["max_points"] - o["excluded_max_points"], r["job_id"]
        adj = Fraction(100 * o["total_points"], o["adjusted_max_points"])
        assert abs(float(adj) - o["normalized_percentage"]) < PCT_TOL, f"adjusted % disagrees: {r['job_id']}"
        rec = recs.setdefault(j["input"], {"input": j["input"], "project": j["project"], "cohort": j["cohort"],
                                           "generation_rep": j["generation_rep"]})
        tag = "r10" if j["rubric"] == R10 else "r20"
        assert f"{tag}_job_id" not in rec, f"two primary {tag} ratings for {j['input']}"
        rec.update({f"{tag}_job_id": j["id"], f"{tag}_total_points": o["total_points"],
                    f"{tag}_max_points": o["max_points"], f"{tag}_excluded_max_points": o["excluded_max_points"],
                    f"{tag}_adjusted_max_points": o["adjusted_max_points"], f"_{tag}": adj,
                    f"{tag}_adjusted_pct": round(float(adj), 4),
                    f"{tag}_reported_adjusted_pct": o["normalized_percentage"],
                    f"{tag}_definition_sha256": r["definition_sha256"]})
        if tag == "r20":
            rec["_r20_doc"] = doc
    for rec in recs.values():
        assert "r10_job_id" in rec and "r20_job_id" in rec, f"unmatched record {rec['input']}"
    # join the Q19 review on the rubric20 job id
    by_job = {rec["r20_job_id"]: rec for rec in recs.values()}
    assert len(review["cases"]) == len(by_job), (len(review["cases"]), len(by_job))
    for c in review["cases"]:
        rec = by_job[c["job_id"]]
        b = bound[c["job_id"]]
        assert c["evaluation_sha256"] == b["evaluation_sha256"] and c["output"] == b["output"], c["job_id"]
        assert c["input"] == rec["input"] and c["input_sha256"] == sha(st.ROOT / c["input"]), c["job_id"]
        assert rec["r20_definition_sha256"] == review["definition_sha256"], c["job_id"]
        assert c["status"] in (FLAGGED, UNFLAGGED), c["status"]
        score = q19_score(rec.pop("_r20_doc"))
        assert score == c["q19"]["score"], f"Q19 copy disagrees: {c['job_id']}"
        rec["q19_score"] = score
        rec["q19_max"] = c["q19"]["max_score"]
        rec["q19_review_status"] = c["status"]
        rec["q19_flagged"] = c["status"] == FLAGGED
    n_flag = sum(1 for rec in recs.values() if rec["q19_flagged"])
    assert n_flag == review["ratings_requiring_adjudication"], (n_flag, review["ratings_requiring_adjudication"])
    counts.update({"records": len(recs), "primary": 2 * len(recs), "repeats": n_repeats, "flagged": n_flag,
                   "reviewed": len(review["cases"])})
    return list(recs.values()), counts


def avg_ranks(values: list[Fraction]) -> list[float]:
    """Rank 1 = highest; ties get the mean of the ranks they span."""
    return [sum(1 for w in values if w > v) + (sum(1 for w in values if w == v) + 1) / 2 for v in values]


def pearson(a: list[float], b: list[float]) -> float | None:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sa = sum((x - ma) ** 2 for x in a)
    sb = sum((y - mb) ** 2 for y in b)
    if sa == 0 or sb == 0:
        return None                       # one instrument gives every record the same score
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) ** 0.5


def spearman(recs: list[dict]) -> float | None:
    return pearson(avg_ranks([r["_r10"] for r in recs]), avg_ranks([r["_r20"] for r in recs]))


def order_key(r: dict):
    return (st.PROJECTS.index(r["project"]), r["cohort"], r["generation_rep"])


def short_id(r: dict) -> str:
    return f'{r["project"].replace("_", "-")} {r["cohort"]} r{r["generation_rep"]}'


def pname(p: str) -> str:
    return p.replace("_", "-")


def dodge(recs: list[dict], key_x: str, key_y: str, step: float, out: str, panel: str) -> list[dict]:
    """Records at exactly the same point are spread side by side along x, in fixed order.

    The spread moves markers off their true x value, so each spread group is returned with its
    true x, its y and the extent of the spread; draw_anchors() marks the true value on the plot."""
    groups = defaultdict(list)
    for r in recs:
        groups[(r[key_x], r[key_y])].append(r)
    spread = []
    for (x, y), members in groups.items():
        k = len(members)
        for i, r in enumerate(sorted(members, key=order_key)):
            r[out] = round(float(x) + (i - (k - 1) / 2) * step, 4)
            r[f"{out}_coincident"] = k
        if k > 1:
            px = [r[out] for r in members]
            spread.append({"panel": panel, "true_x": round(float(x), 4), "y": round(float(y), 4),
                           "n_records": k, "spacing": step, "plotted_x_min": min(px), "plotted_x_max": max(px),
                           "max_offset_from_true_x": round(max(abs(p - float(x)) for p in px), 4),
                           "records": "; ".join(short_id(r) for r in sorted(members, key=order_key))})
    return sorted(spread, key=lambda g: (g["true_x"], g["y"]))


def draw_anchors(ax, spread: list[dict]) -> None:
    """Under each spread group: a hairline joining the offset markers and a tick at the true x value.
    Both sit below the markers (zorder 3); the tick is taller than a marker so it shows above and below."""
    tick = max(COND_SIZE.values()) + 4.5
    for g in spread:
        ax.plot([g["plotted_x_min"], g["plotted_x_max"]], [g["y"], g["y"]], color=st.INK["muted"],
                linewidth=0.8, solid_capstyle="butt", zorder=3)
        ax.plot(g["true_x"], g["y"], marker="|", markersize=tick, markeredgewidth=1.0,
                color=st.INK["muted"], linestyle="none", zorder=3)


def draw_points(ax, recs, xkey, ykey):
    for r in sorted(recs, key=order_key):
        m = COND_MARK[r["cohort"]]
        flagged = r["q19_flagged"]
        ax.plot(r[xkey], r[ykey], marker=m, markersize=COND_SIZE[m], linestyle="none",
                markerfacecolor=PROJECT_COLOR[r["project"]],
                markeredgecolor=st.INK["primary"] if flagged else st.INK["surface"],
                markeredgewidth=1.5 if flagged else 0.9, zorder=5 if flagged else 4)


def main() -> int:
    st.apply()
    recs, counts = load()
    assert counts["records"] == 24 and counts["primary"] == 48 and counts["repeats"] == 8, counts
    recs.sort(key=order_key)
    for r, a, b in zip(recs, avg_ranks([r["_r10"] for r in recs]), avg_ranks([r["_r20"] for r in recs])):
        r["r10_rank"], r["r20_rank"] = a, b
        r["rank_difference"] = a - b          # positive: rubric20 places the record higher than rubric10 does
        r["labelled"] = abs(a - b) >= LABEL_MIN_SHIFT
    n = len(recs)
    rho = spearman(recs)

    # pairs: same order, opposite order, tied on at least one instrument
    pair_rows = []
    for p, q in combinations(recs, 2):
        s10 = (p["_r10"] > q["_r10"]) - (p["_r10"] < q["_r10"])
        s20 = (p["_r20"] > q["_r20"]) - (p["_r20"] < q["_r20"])
        kind = "tied_on_at_least_one" if s10 == 0 or s20 == 0 else ("same_order" if s10 == s20 else "opposite_order")
        pair_rows.append({"record_a": short_id(p), "record_b": short_id(q),
                          "same_project": p["project"] == q["project"], "relation": kind})
    pair_summary = []
    for scope in ("all", "within_project", "between_projects"):
        sub = [x for x in pair_rows if scope == "all" or x["same_project"] == (scope == "within_project")]
        pair_summary.append({"scope": scope, "pairs": len(sub),
                             **{k: sum(1 for x in sub if x["relation"] == k)
                                for k in ("same_order", "opposite_order", "tied_on_at_least_one")}})
    ps = {x["scope"]: x for x in pair_summary}

    within = []
    for proj in st.PROJECTS:
        sub = [r for r in recs if r["project"] == proj]
        w = spearman(sub)
        const = [lab for lab, k in (("rubric10", "_r10"), ("rubric20", "_r20")) if len({r[k] for r in sub}) == 1]
        within.append({"project": proj, "n": len(sub), "spearman_rho": None if w is None else round(w, 4) + 0.0,
                       "undefined_because": f"{' and '.join(const)} gives all {len(sub)} records the same score" if w is None else "",
                       "r10_distinct_scores": len({r["_r10"] for r in sub}),
                       "r20_distinct_scores": len({r["_r20"] for r in sub})})

    spread_rank = dodge(recs, "r10_rank", "r20_rank", DODGE_RANK, "x_rank_plotted", "rank")
    spread_pct = dodge(recs, "_r10", "_r20", DODGE_PCT, "x_pct_plotted", "percentage")
    # ranks are a one-to-one function of the exact fractions, so both panels spread the same records
    assert ({r["input"] for r in recs if r["x_rank_plotted_coincident"] > 1}
            == {r["input"] for r in recs if r["x_pct_plotted_coincident"] > 1}), "spread groups differ by panel"

    fig = plt.figure(figsize=(11.0, 7.5))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.0], height_ratios=[5.0, 1.25], wspace=0.2, hspace=0.3,
                          left=0.065, right=0.985, top=0.84, bottom=0.04)
    ax = fig.add_subplot(gs[0, 0])
    axp = fig.add_subplot(gs[0, 1])

    # --- rank vs rank --------------------------------------------------------------------------
    lim = (n + 0.9, 0.1)
    ax.plot([n + 0.9, 0.1], [n + 0.9, 0.1], color=st.INK["axis"], linewidth=0.9, zorder=1)
    ax.text(7.6, 7.0, "equal rank", color=st.INK["muted"], fontsize=7, rotation=45,
            rotation_mode="anchor", ha="center", va="bottom", zorder=2)
    for r in recs:
        r["y_rank_plotted"] = r["r20_rank"]
    draw_anchors(ax, spread_rank)
    draw_points(ax, recs, "x_rank_plotted", "y_rank_plotted")
    ax.set_xlim(*lim); ax.set_ylim(*lim)
    ticks = [1] + list(range(4, n + 1, 4))
    ax.set_xticks(ticks); ax.set_yticks(ticks)
    ax.set_aspect("equal", adjustable="box")
    st.hairline_grid(ax, "both")
    ax.set_xlabel("rubric10 rank (1 = highest applicability-adjusted %)")
    ax.set_ylabel("rubric20 rank (1 = highest applicability-adjusted %)")
    ax.set_title("Rank under each instrument", pad=22)
    rho_txt = f"Spearman ρ = {rho:.2f}, n = {n} records (tie-corrected, average ranks)"
    ax.text(0, 1.015, rho_txt, transform=ax.transAxes, fontsize=7.8, color=st.INK["secondary"],
            ha="left", va="bottom")
    # the largest rank differences: a numeral beside each marker, keyed in the upper-left corner;
    # the run-time check below refuses to draw the key over any record, so no leader line is needed
    labelled = sorted([r for r in recs if r["labelled"]], key=lambda r: (-abs(r["rank_difference"]),) + order_key(r))
    x0, x10, x20, y = n + 0.4, 17.0, 13.8, 1.05
    ax.text(x0, y, f"rank difference ≥ {LABEL_MIN_SHIFT} places", fontsize=7, fontweight="bold",
            color=st.INK["primary"], ha="left", va="center")
    y += 1.2
    for x, t in ((x10, "rubric10"), (x20, "rubric20")):
        ax.text(x, y, t, fontsize=6.8, color=st.INK["secondary"], ha="right", va="center")
    for k, r in enumerate(labelled, 1):
        y += 1.2
        r["label_number"] = k
        ax.text(r["x_rank_plotted"] - 0.62, r["y_rank_plotted"], str(k), fontsize=7, fontweight="bold",
                color=st.INK["primary"], ha="left", va="center", zorder=6)
        ax.text(x0, y, f"{k}  {short_id(r)}", fontsize=6.9, color=st.INK["primary"], ha="left", va="center")
        ax.text(x10, y, f"#{r['r10_rank']:g}", fontsize=6.9, color=st.INK["primary"], ha="right", va="center")
        ax.text(x20, y, f"#{r['r20_rank']:g}", fontsize=6.9, color=st.INK["primary"], ha="right", va="center")
    key_x_min, key_y_max = x20 - 0.5, y + 0.7
    clash = [short_id(r) for r in recs if r["x_rank_plotted"] >= key_x_min - 0.5 and r["y_rank_plotted"] <= key_y_max + 0.5]
    assert not clash, f"rank-difference key would cover records: {clash}"
    ax.add_patch(plt.Rectangle((key_x_min, 0.35), n + 0.9 - key_x_min - 0.05, key_y_max - 0.35,
                               facecolor=st.INK["surface"], edgecolor="none", zorder=2.5))

    # --- percentages ---------------------------------------------------------------------------
    for r in recs:
        r["y_pct_plotted"] = r["r20_adjusted_pct"]
    draw_anchors(axp, spread_pct)
    draw_points(axp, recs, "x_pct_plotted", "y_pct_plotted")
    xs = [float(r["_r10"]) for r in recs]
    ys = [float(r["_r20"]) for r in recs]
    axp.set_xlim(min(xs) - 4, 101.5)
    axp.set_ylim(min(ys) - 3.5, max(ys) + 3.0)
    st.hairline_grid(axp, "both")
    axp.set_xlabel("rubric10 applicability-adjusted % (of 50 points less excluded items)")
    axp.set_ylabel("rubric20 applicability-adjusted % (of 88 points less excluded items)")
    axp.set_title("The percentages being ranked", pad=22)
    axp.text(0, 1.015, "separate instrument scales, so no diagonal is drawn", transform=axp.transAxes,
             fontsize=7.8, color=st.INK["secondary"], ha="left", va="bottom")
    # project names at each cluster, in ink, so identity does not rest on the low-contrast hues
    place = {"AI_READI": "above", "VOICE": "below", "CM4AI": "below", "CHORUS": "below"}
    for proj in st.PROJECTS:
        sub = [r for r in recs if r["project"] == proj]
        cx = sum(r["x_pct_plotted"] for r in sub) / len(sub)
        if place[proj] == "above":
            y, va = max(r["y_pct_plotted"] for r in sub) + 0.9, "bottom"
        else:
            y, va = min(r["y_pct_plotted"] for r in sub) - 1.0, "top"
        cx = min(cx, 100.6)
        axp.text(cx, y, pname(proj), ha="center" if cx < 99 else "right", va=va, fontsize=7.6,
                 fontweight="bold", color=st.INK["primary"])

    # --- legend --------------------------------------------------------------------------------
    h = [Line2D([], [], marker="o", markersize=7, linestyle="none", markerfacecolor=PROJECT_COLOR[p],
                markeredgecolor=st.INK["surface"], label=pname(p)) for p in st.PROJECTS]
    h += [Line2D([], [], marker=COND_MARK[c], markersize=COND_SIZE[COND_MARK[c]], linestyle="none",
                 markerfacecolor=st.INK["muted"], markeredgecolor=st.INK["surface"], label=f"{c} prompt")
          for c in ("v7", "v8")]
    h.append(Line2D([], [], marker="o", markersize=7, linestyle="none", markerfacecolor=st.INK["mid"],
                    markeredgecolor=st.INK["primary"], markeredgewidth=1.5,
                    label=f"dark ring: rubric20 Q19 rationale flagged for adjudication by the targeted Q19 review ({counts['flagged']} of {counts['reviewed']})"))
    fig.legend(handles=h, loc="upper left", bbox_to_anchor=(0.058, 0.945), ncol=len(h), fontsize=7.5,
               handletextpad=0.35, columnspacing=1.1, handlelength=1.2)

    # --- note ------------------------------------------------------------------------------------
    axn = fig.add_subplot(gs[1, :]); axn.axis("off")

    def wtxt(w):
        return (f"{pname(w['project'])} undefined ({w['undefined_because']})" if w["spearman_rho"] is None
                else f"{pname(w['project'])} {w['spearman_rho']:.2f}")
    ties = [x for x in recs if x["x_rank_plotted_coincident"] > 1]

    def max_off(groups):
        return max(g["max_offset_from_true_x"] for g in groups)

    def true_vals(groups, fmt):
        return ", ".join(fmt(v) for v in sorted({g["true_x"] for g in groups}))
    dodge_txt = (f"{len(ties)} records that coincide exactly are spread side by side, up to ±{max_off(spread_rank):g} rank "
                 f"(left) and ±{max_off(spread_pct):g} percentage point (right) from their true x, so those x positions are "
                 f"offsets, not scores; a hairline joins each spread group and a tick marks its true rubric10 value (rank "
                 f"{true_vals(spread_rank, lambda v: f'{v:g}')}; {true_vals(spread_pct, lambda v: f'{round(v, 2):g}%')}). "
                 ) if ties else ""
    cells = defaultdict(int)
    for r in recs:
        cells[(r["project"], r["cohort"])] += 1
    n_cells = len(cells)
    reps_txt = "/".join(str(v) for v in sorted(set(cells.values())))
    lines = [
        f"Ranks are within one instrument; tied records share the average rank. {dodge_txt}"
        f"Labelled: records whose two ranks differ by at least {LABEL_MIN_SHIFT} places (a display rule, not a test).",
        f"Record pairs ({ps['all']['pairs']}): {ps['all']['same_order']} ordered the same way by both instruments, "
        f"{ps['all']['opposite_order']} oppositely, {ps['all']['tied_on_at_least_one']} tied on at least one. Between projects "
        f"({ps['between_projects']['pairs']} pairs): {ps['between_projects']['same_order']} same, "
        f"{ps['between_projects']['opposite_order']} opposite, {ps['between_projects']['tied_on_at_least_one']} tied; within a project "
        f"({ps['within_project']['pairs']} pairs): {ps['within_project']['same_order']} same, "
        f"{ps['within_project']['opposite_order']} opposite, {ps['within_project']['tied_on_at_least_one']} tied. "
        f"Spearman \u03c1 within project (n = 6 each): " + "; ".join(wtxt(w) for w in within) + ".",
        f"No p-value: the {n} records are {n_cells} project \u00d7 prompt cells of {reps_txt} generation replicates, not independent draws, "
        "so the overall \u03c1 mixes agreement between projects with agreement between replicates of one project. The Q19 flag "
        "(semantic_review.json) qualifies the rubric20 total; the review assigned no replacement score and does not certify unflagged ratings.",
        "Caveat: the instruments measure different constructs, so concordance is not validity against dataset truth, "
        "and disagreement alone does not show that either rubric is defective.",
    ]
    axn.text(0.0, 1.0, "\n".join(textwrap.fill(l, 250) for l in lines), transform=axn.transAxes, fontsize=7.0,
             color=st.INK["secondary"], ha="left", va="top", linespacing=1.45)

    fig.suptitle("Do rubric10 and rubric20 order the reference-rescore records the same way?",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=0.985)
    basis = (f"Record set: reference rescore 2026-09-12 (CBORG runtime), {n} API-arm full records, "
             f"{counts['primary']} primary ratings ({n} rubric10 + {n} rubric20) of {counts['accepted']} accepted in "
             f"completion_audit.json; {counts['repeats']} rubric10 repeats excluded; Q19 flags from semantic_review.json "
             f"({counts['flagged']} of {counts['reviewed']})")
    cols = ["input", "project", "cohort", "generation_rep",
            "r10_job_id", "r10_total_points", "r10_max_points", "r10_excluded_max_points", "r10_adjusted_max_points",
            "r10_adjusted_pct", "r10_reported_adjusted_pct", "r10_rank",
            "r20_job_id", "r20_total_points", "r20_max_points", "r20_excluded_max_points", "r20_adjusted_max_points",
            "r20_adjusted_pct", "r20_reported_adjusted_pct", "r20_rank",
            "rank_difference", "labelled", "q19_score", "q19_max", "q19_review_status", "q19_flagged",
            "x_rank_plotted", "y_rank_plotted", "x_rank_plotted_coincident", "x_pct_plotted", "y_pct_plotted",
            "x_pct_plotted_coincident"]
    main_rows = [{k: r.get(k) for k in cols} | {"label_number": r.get("label_number", "")} for r in recs]
    stats = [{"statistic": "spearman_rho_all_records", "value": round(rho, 4), "n": n,
              "note": "Pearson correlation of average ranks (tie-corrected); no p-value, records clustered"}]
    stats += [{"statistic": f"spearman_rho_within_{w['project']}", "value": w["spearman_rho"], "n": w["n"],
               "note": w["undefined_because"] or "descriptive only"} for w in within]
    st.save(fig, KEY, {"main": main_rows, "stats": stats, "pairs": pair_summary, "within_project": within,
                       "spread_groups": spread_rank + spread_pct}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
