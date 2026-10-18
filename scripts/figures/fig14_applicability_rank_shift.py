#!/usr/bin/env python
"""How much does excluding non-applicable rubric items change the ordering of records?

Method. For every primary rating in the reference rescore, two percentages are
recomputed from the points in the evaluation file:

- fixed base: total_points / max_points (50 for rubric10, 88 for rubric20), so an
  item the evaluator judged not applicable counts as 0 of its full maximum;
- applicability-adjusted: total_points / adjusted_max_points, where
  adjusted_max_points = max_points - the maximum of every excluded item.

Records are ranked separately within each instrument under each convention (rank
1 = highest percentage; tied records share the average of the ranks they span;
ties are decided on exact fractions, not on the rounded percentages in the files,
which round the same 43/47 to 91.49 in one file and 91.5 in another). One
slopegraph per instrument joins each record's fixed-base rank to its adjusted
rank. Records tied at an end are drawn side by side at that rank, so none is
hidden under another. Records with at least one excluded item are labelled with
their percentage-point uplift (adjusted minus fixed), and each such group of
records carries the item codes it excluded.

Excluded items are read from the item level of each evaluation file (rubric10
sub-elements, rubric20 questions) where `applicable` is false or
`applicability_status` is "not_applicable". The item-level list is used because
the summary field `excluded_item_ids` is missing, null, or spelled differently
(E4.3 / 4.3 / E4.S3) across files. Items that carry no applicability flag at all
(many rubric10 sub-elements) count as applicable; the reconciliation below shows
that no exclusion is hidden among them. The script checks that the excluded items'
maxima add up to `excluded_max_points` for every rating, that the item scores add
up to `total_points`, and that the reported percentages agree with the
recomputed ones to within rounding.

Record set: the frozen CBORG reference rescore
(notes/reference_rescore_2026-09-12_cborg_runtime). completion_audit.json binds 56
accepted ratings (32 rubric10, 24 rubric20) of 24 full records (4 projects x v7/v8
prompt x 3 generation replicates). The 48 primary ratings (24 per instrument) are
ranked. The 8 rubric10 repeat ratings (two more ratings of each rep-1 v7 record)
are not ranked, because a second rating of the same bytes would count one record
twice; they are exported separately with a check of whether their exclusions
match the primary rating's. Each evaluation file is checked against the sha256
recorded in completion_audit.json, and its input hash against the record bytes.

Caveats. The figure measures how sensitive the ordering is to a scoring
convention. It does not test whether any individual applicability decision was
justified: the exclusions are the LLM evaluator's own recorded decisions, and the
same project can receive different decisions across ratings (exported in the
`_consistency` table). Ranks are within one instrument; rubric10 and rubric20
ranks are not comparable with each other.
"""
from __future__ import annotations

import hashlib
import json
import sys
import textwrap
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

KEY = "fig14_applicability_rank_shift"
ARCH = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime"
RUBRICS = [("rubric10-semantic", "rubric10"), ("rubric20-semantic", "rubric20")]
# categorical slots 4.. in fixed project order (slots 1-3 belong to the arms)
PROJECT_COLOR = {p: st.SERIES[3 + i] for i, p in enumerate(st.PROJECTS)}
# shape repeats the project so identity never rests on hue alone (yellow and pink are low-contrast)
PROJECT_MARK = dict(zip(st.PROJECTS, ["o", "s", "D", "^"]))
PROJECT_MARKSIZE = {"o": 5.0, "s": 4.6, "D": 4.2, "^": 5.2}
SHARED_LINE = st.INK["muted"]           # a segment drawn by records of more than one project
GAP, DX = 0.045, 0.062                  # strip offset from the rank axis, and spacing of tied dots
PCT_TOL = 0.051                         # reported percentages are rounded to 1 or 2 decimals


def pct(f: Fraction) -> float:
    return float(f)


def excluded_items(doc: dict, rubric: str) -> list[dict]:
    out = []
    if rubric.startswith("rubric10"):
        for e in doc["elements"]:
            for i, s in enumerate(e["sub_elements"], 1):
                if s.get("applicable") is False or s.get("applicability_status") == "not_applicable":
                    out.append({"code": f'{e["id"]}.{i}', "name": s["name"], "max": 1})
    else:
        for c in doc["categories"]:
            for q in c["questions"]:
                if q.get("applicable") is False or q.get("applicability_status") == "not_applicable":
                    out.append({"code": f'Q{q["id"]}', "name": q["name"], "max": q["max_score"]})
    return out


def item_scores(doc: dict, rubric: str) -> tuple[int, int, dict[str, int | None]]:
    """(sum of item scores, sum of item maxima, {code: score}) from the item level."""
    scores = {}
    if rubric.startswith("rubric10"):
        mx = 0
        for e in doc["elements"]:
            for i, s in enumerate(e["sub_elements"], 1):
                scores[f'{e["id"]}.{i}'] = s["score"]
                mx += 1
    else:
        mx = 0
        for c in doc["categories"]:
            for q in c["questions"]:
                scores[f'Q{q["id"]}'] = q["score"]
                mx += q["max_score"]
    return sum(v or 0 for v in scores.values()), mx, scores


def load() -> list[dict]:
    manifest = json.loads((ARCH / "manifest.json").read_text())
    audit = json.loads((ARCH / "completion_audit.json").read_text())
    jobs = {j["id"]: j for j in manifest["jobs"]}
    rows = []
    for r in audit["ratings"]:
        j = jobs[r["job_id"]]
        path = st.ROOT / r["output"]
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == r["evaluation_sha256"], f"evaluation bytes changed: {r['job_id']}"
        doc = json.loads(raw)
        in_hash = hashlib.sha256((st.ROOT / j["input"]).read_bytes()).hexdigest()
        assert doc["metadata"]["input_sha256"] == in_hash, f"input hash mismatch: {r['job_id']}"
        o = doc["overall_score"]
        assert o["total_points"] == r["overall_score"]["total_points"], r["job_id"]
        rubric = j["rubric"]
        exc = excluded_items(doc, rubric)
        tot, mx, scores = item_scores(doc, rubric)
        assert tot == o["total_points"] and mx == o["max_points"], f"item sums disagree: {r['job_id']}"
        assert sum(e["max"] for e in exc) == o["excluded_max_points"], f"excluded items disagree: {r['job_id']}"
        assert o["adjusted_max_points"] == o["max_points"] - o["excluded_max_points"], r["job_id"]
        fixed = Fraction(100 * o["total_points"], o["max_points"])
        adj = Fraction(100 * o["total_points"], o["adjusted_max_points"])
        assert abs(pct(fixed) - o["fixed_percentage"]) < PCT_TOL, f"fixed % disagrees: {r['job_id']}"
        assert abs(pct(adj) - o["normalized_percentage"]) < PCT_TOL, f"adjusted % disagrees: {r['job_id']}"
        rows.append({
            "job_id": j["id"], "rubric": rubric, "purpose": j["purpose"], "rating": j["rating"],
            "project": j["project"], "cohort": j["cohort"], "generation_rep": j["generation_rep"],
            "input": j["input"], "evaluation": r["output"],
            "total_points": o["total_points"], "max_points": o["max_points"],
            "excluded_max_points": o["excluded_max_points"], "adjusted_max_points": o["adjusted_max_points"],
            "_fixed": fixed, "_adj": adj, "_exc": exc, "_scores": scores,
            "reported_fixed_pct": o["fixed_percentage"], "reported_adjusted_pct": o["normalized_percentage"],
        })
    return rows


def avg_ranks(values: list[Fraction]) -> list[float]:
    """Rank 1 = highest; ties get the mean of the ranks they span."""
    return [sum(1 for w in values if w > v) + (sum(1 for w in values if w == v) + 1) / 2 for v in values]


def fmt_rank(r: float) -> str:
    return f"{r:g}"


def item_order(code: str) -> tuple:
    return tuple(int(x) for x in code.lstrip("Q").split("."))


def short_id(r: dict) -> str:
    return f'{r["cohort"]} r{r["generation_rep"]}'


def order_key(r: dict):
    return (st.PROJECTS.index(r["project"]), r["cohort"], r["generation_rep"])


def draw_panel(ax, rows: list[dict], title: str, max_points: int):
    n = len(rows)
    # strips: records sharing a rank at one end sit side by side, in fixed project order
    for side, key in (("left", "fixed_rank"), ("right", "adjusted_rank")):
        groups = defaultdict(list)
        for r in rows:
            groups[r[key]].append(r)
        for rank, members in groups.items():
            for k, r in enumerate(sorted(members, key=order_key)):
                x = -GAP - k * DX if side == "left" else 1 + GAP + k * DX
                r[f"x_{side}"] = round(x, 4)
                r[f"strip_size_{side}"] = len(members)
                m = PROJECT_MARK[r["project"]]
                ax.plot(x, rank, marker=m, markersize=PROJECT_MARKSIZE[m], color=PROJECT_COLOR[r["project"]],
                        markeredgecolor=st.INK["surface"], markeredgewidth=0.7, linestyle="none", zorder=4)
    # lines: one per record; a segment drawn by more than one project is shown neutral
    segs = defaultdict(list)
    for r in rows:
        segs[(r["fixed_rank"], r["adjusted_rank"])].append(r)
    for (y0, y1), members in segs.items():
        projects = {r["project"] for r in members}
        color = PROJECT_COLOR[next(iter(projects))] if len(projects) == 1 else SHARED_LINE
        emph = any(r["n_excluded_items"] for r in members)
        for r in members:
            r["line_color"] = color
        ax.plot([0, 1], [y0, y1], color=color, linewidth=2.0 if emph else 1.1,
                solid_capstyle="round", zorder=3 if emph else 2)
    # labels for records with at least one excluded item, grouped by project and excluded set
    lab = [r for r in rows if r["n_excluded_items"]]
    right_extent = {}
    for r in rows:
        right_extent[r["adjusted_rank"]] = max(right_extent.get(r["adjusted_rank"], 0), r["strip_size_right"])

    def clear_x(y_lo, y_hi):
        k = max([c for rk, c in right_extent.items() if y_lo - 1.3 <= rk <= y_hi + 1.3] or [0])
        return 1 + GAP + max(k - 1, 0) * DX + 0.11

    groups = defaultdict(list)
    for r in lab:
        groups[(r["project"], r["excluded_codes"])].append(r)
    for (proj, codes), members in groups.items():
        by_pos = defaultdict(list)
        for r in members:
            by_pos[(r["adjusted_rank"], r["fixed_rank"], r["uplift_pp_display"])].append(r)
        ys = sorted({p[0] for p in by_pos})
        x_lab = clear_x(ys[0] - 1.6, ys[-1])
        all_same = all(ya == yf for ya, yf, _ in by_pos)
        for (ya, yf, up), rs in sorted(by_pos.items()):
            ids = ", ".join(short_id(r) for r in sorted(rs, key=order_key))
            move = "" if all_same else f", rank {fmt_rank(yf)} to {fmt_rank(ya)}"
            ax.text(x_lab, ya, f"{ids}   +{up} pp{move}", ha="left", va="center", fontsize=7,
                    color=st.INK["primary"], zorder=5)
        head = f"{proj.replace('_', '-')}: excluded {codes.replace(';', ',')}" + (f"; {'rank' if len(members) == 1 else 'ranks'} unchanged" if all_same else "")
        ax.text(x_lab, ys[0] - 1.25, head, ha="left", va="center", fontsize=7, fontweight="bold",
                color=st.INK["primary"], zorder=5)
    ax.set_ylim(n + 0.9, -0.4)
    ticks = [1] + [t for t in range(4, n + 1, 4)]
    ax.set_yticks(ticks)
    st.hairline_grid(ax, "y")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["rank by\nfixed-base %", "rank by applicability-\nadjusted %"], color=st.INK["secondary"])
    ax.tick_params(axis="x", length=0, pad=4)
    ax.spines["bottom"].set_visible(False)
    ax.set_xlim(-0.66, 3.0)
    for x in (0, 1):
        ax.axvline(x, color=st.INK["axis"], linewidth=0.8, zorder=1)
    n_exc = sum(1 for r in rows if r["n_excluded_items"])
    moved = [r for r in rows if r["rank_change"] != 0]
    big = max((abs(r["rank_change"]) for r in moved), default=0)
    sub = (f"{n_exc} of {n} ratings exclude at least one item; "
           + (f"{len(moved)} of {n} records change rank (largest move {big:g} places)" if moved
              else f"no record changes rank"))
    ax.set_title(f"{title} ({max_points}-point fixed base)", pad=20)
    ax.text(0, 1.012, sub, transform=ax.transAxes, fontsize=7.5, color=st.INK["secondary"], ha="left", va="bottom")
    return {"n_ratings": n, "n_with_exclusions": n_exc, "n_rank_changed": len(moved), "largest_rank_move": big}


def main() -> int:
    st.apply()
    rows = load()
    prim = [r for r in rows if r["purpose"] == "primary"]
    reps = [r for r in rows if r["purpose"] != "primary"]
    records = {r["input"] for r in rows}
    n_total = {rb: sum(1 for r in rows if r["rubric"] == rb) for rb, _ in RUBRICS}
    assert len(records) == 24 and {len(prim), len(reps)} == {48, 8}, (len(records), len(prim), len(reps))
    for r in rows:
        r["n_excluded_items"] = len(r["_exc"])
        r["excluded_codes"] = "; ".join(e["code"] for e in r["_exc"])
        r["excluded_names"] = "; ".join(e["name"] for e in r["_exc"])
        r["fixed_pct"] = round(pct(r["_fixed"]), 4)
        r["adjusted_pct"] = round(pct(r["_adj"]), 4)
        r["uplift_pp"] = round(pct(r["_adj"] - r["_fixed"]), 4)
        r["uplift_pp_display"] = f'{pct(r["_adj"] - r["_fixed"]):.1f}'

    fig = plt.figure(figsize=(11.0, 7.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[5.0, 1.25], hspace=0.22, wspace=0.08,
                          left=0.06, right=0.99, top=0.83, bottom=0.035)
    main_rows, summary = [], []
    item_names, item_max = {}, {}
    for i, (rubric, title) in enumerate(RUBRICS):
        ax = fig.add_subplot(gs[0, i])
        sub = sorted([r for r in prim if r["rubric"] == rubric], key=order_key)
        fr = avg_ranks([r["_fixed"] for r in sub])
        ar = avg_ranks([r["_adj"] for r in sub])
        for r, a, b in zip(sub, fr, ar):
            r["fixed_rank"], r["adjusted_rank"] = a, b
            r["rank_change"] = a - b          # positive = moves toward rank 1 once exclusions leave the base
            for e in r["_exc"]:
                item_names[(title, e["code"])] = e["name"]
                item_max[(rubric, e["code"])] = e["max"]
        s = draw_panel(ax, sub, title, sub[0]["max_points"])
        summary.append({"rubric": rubric, **s})
        if i == 0:
            ax.set_ylabel("rank within instrument (1 = highest percentage)")
        else:
            ax.set_yticklabels([])
        main_rows += sub

    # exclusion consistency: for each excluded item, how the same project's other ratings treated it
    consistency = []
    for (title, code), name in sorted(item_names.items(), key=lambda kv: (kv[0][0], item_order(kv[0][1]))):
        rubric = f"{title}-semantic"
        for proj in st.PROJECTS:
            pr = [r for r in prim if r["rubric"] == rubric and r["project"] == proj]
            exc = [r for r in pr if code in r["excluded_codes"].split("; ")]
            if not exc:
                continue
            scored = [r for r in pr if r not in exc]
            consistency.append({
                "rubric": rubric, "item": code, "item_name": name, "project": proj,
                "primary_ratings": len(pr), "excluded_in": len(exc),
                "scored_as_applicable_in": len(scored),
                "scores_where_applicable": "; ".join(str(r["_scores"][code]) for r in sorted(scored, key=order_key)),
                "excluded_ratings": "; ".join(short_id(r) for r in sorted(exc, key=order_key)),
            })
    # repeats: not ranked, exclusions compared with their primary rating
    by_job = {(r["rubric"], r["input"]): r for r in prim}
    rep_rows = []
    for r in sorted(reps, key=lambda r: (order_key(r), r["rating"])):
        p = by_job[(r["rubric"], r["input"])]
        rep_rows.append({k: r[k] for k in ("job_id", "rubric", "project", "cohort", "generation_rep", "rating",
                                           "total_points", "max_points", "excluded_max_points", "adjusted_max_points",
                                           "fixed_pct", "adjusted_pct", "uplift_pp", "n_excluded_items", "excluded_codes")}
                        | {"primary_job_id": p["job_id"], "primary_excluded_codes": p["excluded_codes"],
                           "exclusions_match_primary": r["excluded_codes"] == p["excluded_codes"]})
    n_match = sum(1 for r in rep_rows if r["exclusions_match_primary"])

    # legend
    handles = [plt.Line2D([], [], marker=PROJECT_MARK[p], markersize=PROJECT_MARKSIZE[PROJECT_MARK[p]] + 0.6,
                          color=PROJECT_COLOR[p], linewidth=1.1, label=p.replace("_", "-")) for p in st.PROJECTS]
    shared = any(r["line_color"] == SHARED_LINE for r in main_rows)
    if shared:
        handles.append(plt.Line2D([], [], color=SHARED_LINE, linewidth=1.1,
                                  label="line shared by tied records of several projects (dots show which)"))
    handles.append(plt.Line2D([], [], color=st.INK["secondary"], linewidth=2.0,
                              label="thick line: rating with at least one item excluded"))
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.055, 0.958), ncol=len(handles),
               handlelength=1.8, columnspacing=1.3, handletextpad=0.5, fontsize=7.5)

    # note panel: definitions, item names, consistency and repeats (all computed above)
    axn = fig.add_subplot(gs[1, :]); axn.axis("off")
    names = "; ".join(f"{t} {c} {n}" for (t, c), n in sorted(item_names.items(), key=lambda kv: (kv[0][0], item_order(kv[0][1]))))
    # items excluded in exactly the same ratings of a project are reported together
    grouped = defaultdict(list)
    for c in consistency:
        grouped[(c["rubric"], c["project"], c["excluded_ratings"], c["primary_ratings"])].append(c)
    parts = []
    for (rubric, proj, _, n_pr), cs in grouped.items():
        codes = ", ".join(c["item"] for c in cs)
        part = f'{rubric.split("-")[0]} {codes} excluded in {cs[0]["excluded_in"]} of {n_pr} {proj.replace("_", "-")} ratings'
        if cs[0]["scored_as_applicable_in"]:
            sc = [int(v) for c in cs for v in c["scores_where_applicable"].split("; ")]
            mx = {item_max[(rubric, c["item"])] for c in cs}
            part += (f', but scored as applicable ({min(sc)} to {max(sc)} of {"/".join(map(str, sorted(mx)))} points) '
                     f'in the other {cs[0]["scored_as_applicable_in"]}')
        parts.append(part)
    cons = "; ".join(parts)
    rep_conds = sorted({f'{r["rubric"].split("-")[0]} {short_id(r)}' for r in reps})
    lines = [
        "Fixed base: points / full instrument maximum, an excluded item counting 0. Adjusted: points / maximum of the items the "
        "evaluator judged applicable. Uplift = adjusted minus fixed percentage. Tied records share the average rank and sit side by side.",
        f"Excluded items: {names}.",
        f"Exclusions are the LLM evaluator's own recorded decisions: {cons}.",
        f"Not ranked: {len(reps)} repeat ratings of the same record bytes ({', '.join(rep_conds)} records); "
        f"their excluded items match the primary rating in {n_match} of {len(reps)}.",
        "Caveat: this shows how sensitive the ordering is to the scoring convention, not whether each exclusion was justified.",
    ]
    txt = "\n".join(textwrap.fill(l, 262) for l in lines)
    axn.text(0.0, 1.0, txt, fontsize=7.0, color=st.INK["secondary"], ha="left", va="top", linespacing=1.45,
             transform=axn.transAxes)

    fig.suptitle("Rank shift when non-applicable rubric items leave the denominator, per instrument",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=0.992)
    basis = (f"Record set: reference rescore 2026-09-12 (CBORG runtime), {len(records)} full records; "
             f"{len(prim)} primary ratings ranked ({sum(1 for r in prim if r['rubric'].startswith('rubric10'))} rubric10, "
             f"{sum(1 for r in prim if r['rubric'].startswith('rubric20'))} rubric20) of {len(rows)} accepted in completion_audit.json "
             f"({n_total['rubric10-semantic']} rubric10, {n_total['rubric20-semantic']} rubric20); "
             "percentages recomputed from evaluation-file points, exclusions from item-level applicability")
    cols = ["job_id", "rubric", "project", "cohort", "generation_rep", "rating", "input", "evaluation",
            "total_points", "max_points", "excluded_max_points", "adjusted_max_points",
            "fixed_pct", "adjusted_pct", "uplift_pp", "reported_fixed_pct", "reported_adjusted_pct",
            "fixed_rank", "adjusted_rank", "rank_change", "n_excluded_items", "excluded_codes", "excluded_names",
            "x_left", "x_right", "strip_size_left", "strip_size_right", "line_color"]
    st.save(fig, KEY, {"main": [{k: r[k] for k in cols} for r in main_rows],
                       "summary": summary, "consistency": consistency, "repeats": rep_rows}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
