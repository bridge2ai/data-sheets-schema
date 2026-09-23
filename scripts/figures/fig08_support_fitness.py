#!/usr/bin/env python
"""#2299: field-level support (grounding) and fitness verdicts, per record and per schema module.

The verdict caches under data/evaluation_llm/judgement_cache/ are keyed by (slot, canonical JSON
value), not by record, so records are joined to verdicts by exact slot value. Which records the
caches were built for is established by that join:

- fitness (`<project>_fitness.jsonl`, 1,441 entries, axis=fitness): the July 2026 Claude Code
  records 2026-07-28_claude-opus-5-generic rep1-3 (v1) and 2026-07-31_claude-opus-5-generic-v2
  rep1-3 (v2), all four projects; nearly every populated slot matches.
- support (`CM4AI.jsonl`, 116 legacy entries with `supported`, no axis/rubric/corpus fields):
  the CM4AI v1 replicates under evidence_score.build_plan's stable/divergent partition, i.e.
  slots populated identically-by-presence in all three replicates were judged once on rep1's
  value and propagated; all 78 planned judgements are in the cache.
- the 24 reference-rescore records (2026-09 v7/v8) match only a handful of slots each; they are
  not drawn, and the join counts are exported (`_reference_join.csv`). This agrees with
  notes/fitness_cache_decision_2026-09-11.md: the caches carry an older schema digest and are not
  reference measurements.

Binary verdicts: fit = the judge's own `failure == "none"`; supported = `supported >= 0.75`
(the grounding rubric's 1.0 = stated directly, 0.5 = implied or partial, 0.0 = unsupported).
"""
from __future__ import annotations

import hashlib
import json
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import Patch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from scripts.figures import _style as st  # noqa: E402
from data_sheets_schema.evidence_score import build_plan, load_record  # noqa: E402

CACHE = st.ROOT / "data" / "evaluation_llm" / "judgement_cache"
SCHEMA_DIR = st.ROOT / "src" / "data_sheets_schema" / "schema"
ARCH = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime"
COHORTS = [("v1", "2026-07-28_claude-opus-5-generic"), ("v2", "2026-07-31_claude-opus-5-generic-v2")]
COHORT_NAME = {"v1": "generic (v1)", "v2": "generic-v2"}
SUPPORT_COHORT = "v1"                  # the only cohort with grounding judgements (CM4AI)
SUPPORT_THRESHOLD = 0.75
ARM = "direct"                         # Claude Code runtime, provider Anthropic (read from provenance below)
FIT, UNFIT = st.ARM_COLOR[ARM], st.STATUS["serious"]
NOVERDICT = st.INK["axis"]


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def record_path(project: str, cohort_label: str, rep: int) -> Path:
    return st.ROOT / "data" / "d4d_concatenated" / "claudecode_agent" / f"{cohort_label}_rep{rep}" / f"{project}_d4d.yaml"


def provenance_model(project: str, cohort_label: str, rep: int) -> dict:
    p = st.ROOT / "data" / "d4d_concatenated" / "claudecode_agent_core" / f"{cohort_label}_rep{rep}" / f"{project}_provenance.yaml"
    if not p.exists():
        return {}
    return (yaml.safe_load(p.read_text()) or {}).get("model") or {}


def load_caches():
    fitness, contexts = {}, Counter()
    for project in st.PROJECTS:
        fitness[project] = {}
        for line in (CACHE / f"{project}_fitness.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            fitness[project][(e["slot"], e["value"])] = e
            contexts[(e.get("axis"), e.get("model"), e.get("rubric"), e.get("schema"))] += 1
    support, support_ctx = {}, Counter()
    for line in (CACHE / "CM4AI.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        support[(e["slot"], e["value"])] = e
        support_ctx[(e.get("axis"), e.get("model"), e.get("rubric"), e.get("corpus"))] += 1
    return fitness, contexts, support, support_ctx


def module_map():
    """Slot -> schema module. A slot declared at top level in exactly one D4D_*.yaml module owns
    it; otherwise the module that declares the slot's range class (from the current merged
    schema) does; otherwise it is left unattributed. The July records were generated under an
    older schema digest, so slots absent from the current Dataset class are marked as such."""
    declared, classes = defaultdict(set), {}
    for f in sorted(SCHEMA_DIR.glob("D4D_*.yaml")):
        mod = f.stem[4:]
        d = yaml.safe_load(f.read_text()) or {}
        for s in (d.get("slots") or {}):
            declared[s].add(mod)
        for c in (d.get("classes") or {}):
            classes.setdefault(c, mod)
    ranges, in_dataset = {}, set()
    try:
        from data_sheets_schema.schema_view import shared_view
        sv = shared_view(SCHEMA_DIR / "data_sheets_schema.yaml")
        for s in sv.class_induced_slots("Dataset"):
            in_dataset.add(s.name)
            ranges[s.name] = s.range
    except Exception as exc:  # pragma: no cover - the figure still renders, with a coarser attribution
        print(f"schema view unavailable ({exc}); range-based attribution skipped", file=sys.stderr)

    def module_of(slot: str) -> str:
        mods = declared.get(slot, set())
        if len(mods) == 1:
            return next(iter(mods))
        rng = ranges.get(slot)
        if rng in classes:
            return classes[rng]
        if slot in in_dataset or mods:
            return "Core/other"
        return "not in current Dataset"
    return module_of


def join_records(fitness, support):
    rows, cells = [], {}
    runtime = Counter()
    for project in st.PROJECTS:
        for cohort, label in COHORTS:
            recs = {rep: load_record(record_path(project, label, rep)) for rep in (1, 2, 3)}
            plan = build_plan(project, {f"rep{r}": v for r, v in recs.items()}, representative_label="rep1") if (project == "CM4AI" and cohort == SUPPORT_COHORT) else None
            for rep, rec in recs.items():
                m = provenance_model(project, label, rep)
                runtime[(m.get("agent_runtime"), m.get("provider"), m.get("model"))] += 1
                cell = {"project": project, "cohort": cohort, "rep": rep, "label": f"{label}_rep{rep}", "slots": len(rec),
                        "fit": 0, "unfit": 0, "no_fitness": 0, "both": Counter(), "support_judged": 0, "no_support": 0}
                for slot, value in rec.items():
                    key = (slot, canonical(value))
                    f = fitness[project].get(key)
                    row = {"project": project, "cohort": cohort, "rep": rep, "label": cell["label"], "slot": slot,
                           "value_sha256_12": hashlib.sha256(key[1].encode()).hexdigest()[:12],
                           "fitness_judged": f is not None, "fitness": None if f is None else f["fitness"],
                           "failure": None if f is None else f["failure"], "fit": None if f is None else (f["failure"] == "none"),
                           "support_judged": False, "supported": None, "supported_bool": None, "support_source": ""}
                    if f is None:
                        cell["no_fitness"] += 1
                    elif row["fit"]:
                        cell["fit"] += 1
                    else:
                        cell["unfit"] += 1
                    if plan is not None:
                        src_rep = plan.representative.get(slot, f"rep{rep}")
                        s = support.get((slot, canonical(recs[int(src_rep[3:])].get(slot))))
                        if s is not None:
                            row.update(support_judged=True, supported=s["supported"], supported_bool=s["supported"] >= SUPPORT_THRESHOLD,
                                       support_source=("propagated from rep1" if src_rep != f"rep{rep}" else "judged on this replicate"))
                            cell["support_judged"] += 1
                            if f is not None:
                                cell["both"][(row["supported_bool"], row["fit"])] += 1
                        else:
                            cell["no_support"] += 1
                    rows.append(row)
                cells[(project, cohort, rep)] = cell
    return rows, cells, runtime


def reference_join(fitness, support):
    manifest = json.loads((ARCH / "manifest.json").read_text())
    out = []
    for j in sorted({(x["project"], x["cohort"], x["generation_rep"], x["input"]) for x in manifest["jobs"]}):
        project, cohort, rep, inp = j
        rec = load_record(st.ROOT / inp)
        keys = {(s, canonical(v)) for s, v in rec.items()}
        out.append({"project": project, "cohort": cohort, "generation_rep": rep, "input": inp, "slots": len(rec),
                    "fitness_matched": sum(1 for k in keys if k in fitness[project]),
                    "support_matched": sum(1 for k in keys if k in support) if project == "CM4AI" else 0})
    return out


def draw_cell(ax, cell, wmax):
    """One record. Lengths share one scale (slots / wmax); area of the mosaic = slots judged on both axes."""
    ax.set_xlim(0, 1.06); ax.set_ylim(0, 1); ax.axis("off")
    h = 0.34
    if cell["support_judged"]:
        both = cell["both"]; n = sum(both.values())
        w = n / wmax
        n_sup = both[(True, True)] + both[(True, False)]
        n_uns = n - n_sup
        x0 = 0.0
        for supported, nn in ((True, n_sup), (False, n_uns)):
            if nn == 0:
                continue
            cw = w * nn / n
            fit_n = both[(supported, True)]
            for is_fit, y0, hh in ((True, 0.32, h * fit_n / nn), (False, 0.32 + h * fit_n / nn, h * (nn - fit_n) / nn)):
                if hh <= 0:
                    continue
                ax.add_patch(Rectangle((x0, y0), cw, hh, facecolor=FIT if is_fit else UNFIT,
                                       edgecolor=st.INK["surface"], linewidth=1.0, hatch=None if supported else st.HATCH, zorder=2))
            x0 += cw + 0.01
        ax.text(0, 0.72, f"both axes: {n} slots", fontsize=6.4, color=st.INK["secondary"], va="bottom")
        ax.text(0, 0.22, f"unsupported {n_uns}, unfit {both[(True, False)] + both[(False, False)]}, no fitness verdict {cell['no_fitness']}",
                fontsize=5.8, color=st.INK["muted"], va="top")
    else:
        n = cell["fit"] + cell["unfit"]
        w = n / wmax
        ax.add_patch(Rectangle((0, 0.5), w * cell["fit"] / max(n, 1), h, facecolor=FIT, edgecolor=st.INK["surface"], linewidth=1.0, zorder=2))
        ax.add_patch(Rectangle((w * cell["fit"] / max(n, 1) , 0.5), w * cell["unfit"] / max(n, 1), h, facecolor=UNFIT, edgecolor=st.INK["surface"], linewidth=1.0, zorder=2))
        if cell["no_fitness"]:
            ax.add_patch(Rectangle((w + 0.012, 0.5), cell["no_fitness"] / wmax, h, facecolor="none", edgecolor=NOVERDICT, hatch=st.HATCH, linewidth=0.8, zorder=2))
        ax.add_patch(Rectangle((0, 0.08), max(w, 0.02), h * 0.75, facecolor="none", edgecolor=NOVERDICT, linestyle=(0, (2, 2)), linewidth=0.8, zorder=2))
        ax.text(0.03, 0.08 + h * 0.375, "support: not judged", fontsize=5.8, color=st.INK["muted"], va="center")
        ax.text(0, 0.88, f"fitness: {n} slots judged, {cell['unfit']} unfit" + (f", {cell['no_fitness']} no verdict" if cell["no_fitness"] else ""),
                fontsize=6.4, color=st.INK["secondary"], va="bottom")


def main() -> int:
    st.apply()
    fitness, fit_ctx, support, sup_ctx = load_caches()
    rows, cells, runtime = join_records(fitness, support)
    module_of = module_map()
    for r in rows:
        r["module"] = module_of(r["slot"])
    ref = reference_join(fitness, support)
    wmax = max(c["slots"] for c in cells.values())
    n_records = len(cells)
    n_fit_judged = sum(1 for r in rows if r["fitness_judged"])
    n_sup_judged = sum(1 for r in rows if r["support_judged"])
    n_partial = sum(1 for r in rows if r["support_judged"] and 0.5 <= r["supported"] < SUPPORT_THRESHOLD)
    (fit_axis, fit_model, fit_rubric, fit_schema), = [k for k, _ in fit_ctx.most_common(1)]
    (sup_axis, sup_model, sup_rubric, sup_corpus), = [k for k, _ in sup_ctx.most_common(1)]

    fig = plt.figure(figsize=(12.4, 13.0))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.35, 1.0], hspace=0.16, top=0.92, bottom=0.115, left=0.06, right=0.98)

    # ---- (A) per-record grid ----
    gsA = gs[0].subgridspec(len(st.PROJECTS), 6, hspace=0.25, wspace=0.12)
    for pi, project in enumerate(st.PROJECTS):
        for ci, (cohort, _label) in enumerate(COHORTS):
            for rep in (1, 2, 3):
                ax = fig.add_subplot(gsA[pi, ci * 3 + rep - 1])
                draw_cell(ax, cells[(project, cohort, rep)], wmax)
                if pi == 0:
                    ax.set_title(f"{COHORT_NAME[cohort]} rep{rep}", fontsize=8, pad=2, loc="left")
                if ci == 0 and rep == 1:
                    ax.text(-0.04, 0.5, project.replace("_", "-"), transform=ax.transAxes, rotation=90, ha="right", va="center",
                            fontsize=8.5, fontweight="bold", color=st.INK["secondary"])
    fig.text(0.06, 0.935, "A  Per record: fitness verdicts for every matched slot; support x fitness mosaic where both axes were judged (CM4AI v1)",
             fontsize=9.5, fontweight="bold", ha="left", va="bottom")
    handles = [Patch(facecolor=FIT, label="fit (judge failure = none)"),
               Patch(facecolor=UNFIT, label="unfit (failure = form, target or substance)"),
               Patch(facecolor=FIT, hatch=st.HATCH, edgecolor=st.INK["surface"], label=f"hatched column: unsupported (supported < {SUPPORT_THRESHOLD})"),
               Patch(facecolor="none", edgecolor=NOVERDICT, hatch=st.HATCH, label="populated slot with no cached fitness verdict"),
               Patch(facecolor="none", edgecolor=NOVERDICT, linestyle=(0, (2, 2)), label="axis not judged for this record")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.06, 0.985), ncol=3, fontsize=7, frameon=False, handlelength=1.6)

    # ---- (B) per schema module ----
    axB = fig.add_subplot(gs[1])
    mods = Counter(r["module"] for r in rows if r["fitness_judged"])
    order = [m for m, _ in mods.most_common()]
    fit_by = Counter((r["module"], r["fit"]) for r in rows if r["fitness_judged"])
    sup_by = Counter((r["module"], r["supported_bool"]) for r in rows if r["support_judged"])
    module_rows = []
    for k, mod in enumerate(order):
        y = len(order) - 1 - k
        f_ok, f_no = fit_by[(mod, True)], fit_by[(mod, False)]
        s_ok, s_no = sup_by[(mod, True)], sup_by[(mod, False)]
        axB.barh(y + 0.19, f_ok, height=0.34, color=FIT, edgecolor=st.INK["surface"], linewidth=1.0, zorder=3)
        axB.barh(y + 0.19, f_no, left=f_ok, height=0.34, color=UNFIT, edgecolor=st.INK["surface"], linewidth=1.0, zorder=3)
        axB.text(f_ok + f_no + 3, y + 0.19, f"{f_no} unfit of {f_ok + f_no}", va="center", fontsize=6.6, color=st.INK["secondary"])
        if s_ok + s_no:
            axB.barh(y - 0.19, s_ok, height=0.34, color=FIT, edgecolor=st.INK["surface"], linewidth=1.0, zorder=3)
            axB.barh(y - 0.19, s_no, left=s_ok, height=0.34, color=FIT, hatch=st.HATCH, edgecolor=st.INK["surface"], linewidth=1.0, zorder=3)
            axB.text(s_ok + s_no + 3, y - 0.19, f"{s_no} unsupported of {s_ok + s_no} (CM4AI v1)", va="center", fontsize=6.6, color=st.INK["secondary"])
        else:
            axB.add_patch(Rectangle((0, y - 0.36), 6, 0.34, facecolor="none", edgecolor=NOVERDICT, linestyle=(0, (2, 2)), linewidth=0.8, zorder=3))
            axB.text(9, y - 0.19, "support not judged", va="center", fontsize=6.6, color=st.INK["muted"])
        module_rows.append({"module": mod, "fit": f_ok, "unfit": f_no, "supported": s_ok, "unsupported": s_no})
    axB.set_yticks([len(order) - 1 - k for k in range(len(order))]); axB.set_yticklabels(order, fontsize=7.5)
    axB.set_ylim(-0.7, len(order) - 0.3)
    axB.tick_params(axis="y", length=0)
    axB.set_xlabel(f"slot verdicts (upper bar: fitness over all {n_records} records; lower bar: support over the 3 CM4AI v1 records)")
    axB.set_title("B  Verdicts per schema module (slot attributed by declaring module, else by the module declaring its range class)", pad=8)
    st.hairline_grid(axB, "x")

    (rt, prov, model), = [k for k, _ in runtime.most_common(1)]
    note = (f"Record set: {n_records} Claude Code full records (agent runtime {rt}, provider {prov}, model {model}), 4 projects x v1/v2 x 3 replicates, "
            f"generated 2026-07-28 and 2026-07-31; {n_fit_judged} slot fitness verdicts and {n_sup_judged} support verdicts matched by (slot, canonical JSON value). "
            f"Evaluator for both axes: {fit_model}. Fitness cache context: axis={fit_axis}, rubric digest {fit_rubric}, schema digest {fit_schema}. "
            f"Support cache: legacy entries without axis/rubric/corpus fields (axis={sup_axis}, rubric={sup_rubric}, corpus={sup_corpus}); "
            f"stable slots judged once on rep1 and propagated (evidence_score.build_plan); {n_partial} partial (0.5-0.74) judgements counted unsupported. "
            f"Reference-rescore records (2026-09 v7/v8) match only {min(r['fitness_matched'] for r in ref)}-{max(r['fitness_matched'] for r in ref)} "
            f"fitness slots each and are not drawn (see _reference_join.csv).")
    fig.text(0.06, 0.022, textwrap.fill(note, 200), fontsize=6.6, color=st.INK["secondary"], ha="left", va="bottom")
    fig.suptitle("Field-level support and fitness verdicts from the judgement caches, per record and per schema module",
                 x=0.06, ha="left", fontsize=11, fontweight="bold", y=0.998)
    basis = (f"Record set: {n_records} July-2026 Claude Code records matched to data/evaluation_llm/judgement_cache (fitness all projects; support CM4AI v1 only); "
             "verdict thresholds fit=failure none, supported>=0.75; join by exact slot value")
    st.save(fig, "fig08_support_fitness", {"main": rows, "records": [{k: v for k, v in c.items() if k != "both"} | {"both_axes": sum(c["both"].values())} for c in cells.values()],
                                           "modules": module_rows, "reference_join": ref}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
