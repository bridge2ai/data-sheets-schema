#!/usr/bin/env python
"""#2294: what the derived core keeps of each full record, and what the pair check says.

Record set: the 24 full records of the frozen CBORG reference rescore
(notes/reference_rescore_2026-09-12_cborg_runtime/manifest.json, jobs[].input):
12 generic-v7 records under claudecode_agent/ and 12 generic-v8 under claudecode_api/,
all carrying `Agent runtime: Claude API (direct)` in their headers. For each one the
core is re-derived here by calling `derive_core.derive_core` (a pure function of the
full record and the two schemas) and compared with the sibling *_core.yaml under
claudecode_agent_core/ and claudecode_api_core/; the CSV records whether they agree.
The pair check is `d4d_pair_consistency.validate_pair_data` on the full record and the
sibling core: no model is called anywhere in this script.

Counts are populated leaf values (scalars that are not None/empty), partitioned by
the derivation rule: leaves under the schema-identical shared slots (copied), under
`resources` (projected by id, full-only nested slots dropped), under full-only slots
(not carried: file_collections and anything else with no core counterpart), and in
the core the constructed leaves (`distributions` built from file_collections, `dialect`
when the files agree, and the two per-record slots).
"""
from __future__ import annotations

import ast
import json
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import Patch, Rectangle

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from scripts.figures import _style as st  # noqa: E402
from data_sheets_schema.derive_core import derive_core  # noqa: E402
from data_sheets_schema.d4d_pair_consistency import load_pair_schema, validate_pair_data  # noqa: E402

MANIFEST = ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime" / "manifest.json"
EMPTY = (None, "", [], {})
COL = {"shared": st.ORDINAL[6], "resources": st.ORDINAL[2], "constructed": st.SERIES[6]}


def leaves(x) -> int:
    if isinstance(x, dict):
        return sum(leaves(v) for v in x.values())
    if isinstance(x, list):
        return sum(leaves(v) for v in x)
    return 0 if x in EMPTY else 1


def sibling(full: str) -> Path:
    return ROOT / (full.replace("claudecode_api/", "claudecode_api_core/")
                   .replace("claudecode_agent/", "claudecode_agent_core/")
                   .replace("_d4d.yaml", "_d4d_core.yaml"))


def partition(full: dict, core: dict, ps) -> dict:
    ident = set(ps.identity_slots)
    per_record = set(ps.per_record_slots)
    out = {"full_shared": 0, "full_resources": 0, "full_only": 0,
           "core_shared": 0, "core_resources": 0, "core_constructed": 0}
    for k, v in full.items():
        n = leaves(v)
        if k in ident:
            out["full_shared"] += n
        elif k in ps.projected_slots:
            out["full_resources"] += n
        else:
            out["full_only"] += n
    for k, v in core.items():
        n = leaves(v)
        if k in ident:
            out["core_shared"] += n
        elif k in ps.projected_slots:
            out["core_resources"] += n
        else:  # distributions, dialect, conforms_to_class, conforms_to_schema
            out["core_constructed"] += n
    out["full_total"] = leaves(full)
    out["core_total"] = leaves(core)
    return out


def pair_facts(report) -> dict:
    sem = [w for w in report.warnings if w.code == "semantic-review-required"]
    matched = unmatched = None
    if sem:
        msg = sem[0].message
        matched = int(msg.split("matches=")[1].split(" ")[0])
        tail = msg.split("unmatched core distributions=")[1].strip()
        parsed = ast.literal_eval(tail)
        unmatched = len(parsed) if isinstance(parsed, (list, tuple)) else int(parsed)
    return {"pair_errors": len(report.errors), "pair_warnings": len(report.warnings),
            "semantic_review_required": bool(sem),
            "distribution_matches": matched, "unmatched_core_distributions": unmatched}


def load():
    m = json.loads(MANIFEST.read_text())
    inputs = sorted({(j["project"], j["cohort"], j["generation_rep"], j["input"]) for j in m["jobs"]})
    ps = load_pair_schema()
    rows = []
    for project, cohort, rep, inp in inputs:
        full = yaml.safe_load((ROOT / inp).read_text())
        sib_path = sibling(inp)
        sib = yaml.safe_load(sib_path.read_text())
        derived = derive_core(full, ps)
        rep_ = validate_pair_data(full, sib, ps)
        row = {"project": project, "cohort": cohort, "generation_rep": rep, "input": inp,
               "core_sibling": str(sib_path.relative_to(ROOT)),
               "derived_equals_sibling": derived == sib,
               "full_top_slots": sum(1 for v in full.values() if v not in EMPTY),
               "core_top_slots": sum(1 for v in derived.values() if v not in EMPTY),
               "distributions": len(derived.get("distributions") or []),
               "dialect_derived": "dialect" in derived}
        row.update(partition(full, derived, ps))
        row.update(pair_facts(rep_))
        rows.append(row)
    return rows, ps


def main() -> int:
    st.apply()
    rows, ps = load()
    order = []
    for proj in st.PROJECTS:
        for cohort in ("v7", "v8"):
            for rep in (1, 2, 3):
                order += [r for r in rows if (r["project"], r["cohort"], r["generation_rep"]) == (proj, cohort, rep)]
    n = len(order)
    fig = plt.figure(figsize=(10.4, 8.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[3.1, 1.25], wspace=0.06)
    ax = fig.add_subplot(gs[0, 0]); axp = fig.add_subplot(gs[0, 1], sharey=ax)

    ys, ylabels, plotted = [], [], []
    y = 0.0
    bh = 0.36
    for i, r in enumerate(order):
        if i and r["project"] != order[i - 1]["project"]:
            y += 0.9
        # full bar (upper), core bar (lower)
        yf, yc = y + bh / 2 + 0.03, y - bh / 2 - 0.03
        x = 0
        for key, c in (("full_shared", COL["shared"]), ("full_resources", COL["resources"])):
            ax.barh(yf, r[key], left=x, height=bh, color=c, edgecolor=st.INK["surface"], linewidth=0.8, zorder=2)
            x += r[key]
        ax.barh(yf, r["full_only"], left=x, height=bh, facecolor="none", edgecolor=st.INK["muted"],
                linewidth=0.6, hatch=st.HATCH, zorder=2)
        x = 0
        for key, c in (("core_shared", COL["shared"]), ("core_resources", COL["resources"]), ("core_constructed", COL["constructed"])):
            ax.barh(yc, r[key], left=x, height=bh, color=c, edgecolor=st.INK["surface"], linewidth=0.8, zorder=2)
            x += r[key]
        ax.text(r["full_total"] + 4, yf, str(r["full_total"]), va="center", fontsize=6.6, color=st.INK["secondary"])
        ax.text(r["core_total"] + 4, yc, str(r["core_total"]), va="center", fontsize=6.6, color=st.INK["secondary"])
        ys.append(y); ylabels.append(f"{r['cohort']} rep {r['generation_rep']}")
        # pair panel: matched distributions filled, unmatched hollow; errors as text
        m = r["distribution_matches"]; u = r["unmatched_core_distributions"]
        if r["semantic_review_required"]:
            axp.barh(y, m, height=bh * 1.4, color=COL["constructed"], zorder=2)
            axp.barh(y, u, left=m, height=bh * 1.4, facecolor="none", edgecolor=COL["constructed"], linewidth=0.8, zorder=2)
            axp.text(m + u + 0.4, y, f"{m} matched" + (f", {u} unmatched" if u else ""), va="center", fontsize=6.4, color=st.INK["secondary"])
        else:
            axp.text(0.4, y, "no distributions (no file_collections)", va="center", fontsize=6.4, color=st.INK["muted"])
        axp.text(-0.6, y, str(r["pair_errors"]), va="center", ha="right", fontsize=6.6,
                 color=st.INK["primary"] if r["pair_errors"] else st.INK["muted"])
        plotted.append({**{k: r[k] for k in r if k not in ("input", "core_sibling")}, "input": r["input"], "core_sibling": r["core_sibling"], "y": round(y, 2)})
        y += 1.0
    ax.set_yticks(ys); ax.set_yticklabels(ylabels)
    ax.invert_yaxis()
    # project labels along the left, one per group
    for proj in st.PROJECTS:
        yy = [p["y"] for p in plotted if p["project"] == proj]
        ax.text(-0.02, (min(yy) + max(yy)) / 2, proj.replace("_", "-"), transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=8, fontweight="bold", color=st.INK["secondary"], rotation=90)
    ax.tick_params(axis="y", pad=34, length=0)
    ax.set_xlabel("populated leaf values in the record")
    ax.set_xlim(0, max(r["full_total"] for r in rows) * 1.12)
    st.hairline_grid(ax, "x")
    ax.set_title("Per record: full record (upper bar) and the derived core (lower bar)", pad=8)
    axp.set_xlabel("core distributions matched to a file collection")
    axp.set_xlim(0, max((r["distribution_matches"] or 0) + (r["unmatched_core_distributions"] or 0) for r in rows) * 1.9)
    axp.tick_params(axis="y", left=False, labelleft=False)
    axp.spines["left"].set_visible(False)
    st.hairline_grid(axp, "x")
    axp.set_title("Pair check: errors | distribution matches", pad=8)
    axp.text(-0.6, -1.15, "errors", ha="right", va="center", fontsize=6.6, color=st.INK["muted"])
    res_n = sum(r["full_resources"] for r in rows)
    dial_n = sum(1 for r in rows if r["dialect_derived"])
    handles = [Patch(color=COL["shared"], label="shared slots (schema-identical in Dataset and CoreDataset): copied to the core"),
               Patch(color=COL["resources"], label=f"resources: projected by id, full-only nested slots dropped ({res_n} leaves in this set)"),
               Patch(facecolor="none", edgecolor=st.INK["muted"], linewidth=0.6, hatch=st.HATCH, label="full-only slots (file_collections and others): not carried"),
               Patch(color=COL["constructed"], label="constructed in the core: distributions from file_collections, dialect, per-record slots"),
               Patch(facecolor="none", edgecolor=COL["constructed"], linewidth=0.8, label="core distribution with no deterministic file-collection match (hollow)")]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, -0.06), ncol=1, fontsize=7.2, handlelength=1.6)
    eq = sum(1 for r in rows if r["derived_equals_sibling"])
    errs = sum(r["pair_errors"] for r in rows)
    sem = sum(1 for r in rows if r["semantic_review_required"])
    note = (f"Cores re-derived here equal the stored sibling core for {eq} of {n} records. The pair check reports "
            f"{errs} errors across the {n} pairs; {sem} of {n} pairs carry the checker's 'semantic-review-required' "
            f"warning (file_collections vs distributions), which Phase 4 answers with a model review not run here. "
            f"Shared slots: {len(ps.identity_slots)}; projected: {', '.join(ps.projected_slots)}; per-record: {', '.join(ps.per_record_slots)}. "
            f"No record in this set has a top-level resources slot; dialect was derived for {dial_n} of {n}.")
    fig.text(0.62, 0.14, textwrap.fill(note, 64), fontsize=6.9, color=st.INK["secondary"], ha="left", va="top")
    fig.suptitle("What the derived core keeps of each full record, and what the deterministic pair check reports",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=0.985)
    fig.subplots_adjust(left=0.13, right=0.99, top=0.915, bottom=0.21)
    basis = (f"Record set: reference rescore 2026-09-12 (CBORG runtime), {n} full records (12 v7 under claudecode_agent/, "
             "12 v8 under claudecode_api/; all API-arm); cores re-derived with derive_core(); pair check without a model")
    st.save(fig, "fig03_full_core", {"main": plotted}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
