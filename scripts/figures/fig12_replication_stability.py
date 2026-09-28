#!/usr/bin/env python
"""Exploratory: which top-level Dataset slot values survive replication?

Record set: the 24 API-arm full records of the frozen CBORG reference rescore
(notes/reference_rescore_2026-09-12_cborg_runtime/manifest.json, distinct jobs[].input).
They form 8 groups (4 projects x v7/v8 prompt) of 3 generation replicates
(jobs[].generation_rep 1-3). v7 records sit under claudecode_agent/, v8 under claudecode_api/;
the v8 groups come from two run labels (2026-09-04f and 2026-09-04g), which the CSV records.
The arm of every record is verified from its <method>_core/<label>/<P>_provenance.yaml
model.agent_runtime (fig02_content_coverage.verify_arm); a mismatch stops the build.

Rows: class Dataset's induced slots from the merged schema, attributed to modules exactly as
in fig02_content_coverage.slot_modules() (the module whose D4D_*.yaml file defines the slot's
range class; base-type or root-class ranges form "Base / root"). `source_caveats` is not a row.
A block that mixes slot kinds is split by kind. Slot kind:
  nested       the range is a schema class (an object or a list of objects);
  list         multivalued with a type or enum range (a list of plain values);
  long text    single-valued string whose median length over the observed values in the
               24 records exceeds LONG_TEXT_CHARS characters (a heuristic threshold);
  scalar       any other single-valued type or enum slot (numbers, booleans, dates, short strings,
               and slots never observed).

Comparison, per slot and group: a replicate "has" the slot when its value is not None / "" / []
/ {} (fig02's `empty`). Present values are canonicalized as YAML with mapping keys sorted, after
collapsing every whitespace run inside strings to one space and stripping the ends. List order is
kept (an order-insensitive comparison is exported as `identical_ignoring_list_order`). States:
  identical      present in all three, all three canonical forms equal;
  two_agree      present in all three, exactly two canonical forms equal;
  all_differ     present in all three, three distinct canonical forms;
  intermittent   present in one or two of the three (the cell shows how many);
  absent         present in none of the three.
Identifier alignment of nested entities was not used: only a minority of nested list items
carry an `id` (the count is printed at run time), so items are compared in record order.

Caveats (also in the figure): textual difference is not necessarily factual difference
(paraphrase, reordering and added detail all count as differences, and whole-value comparison
means one changed sub-field makes a nested slot differ); three replicates per group describe
these 24 records and cannot estimate the reliability of the generation process.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
import textwrap
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import Patch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402
from scripts.figures import fig02_content_coverage as f02  # noqa: E402  (slot attribution, arm check, emptiness)

from data_sheets_schema.schema_view import shared_view  # noqa: E402  (fig02 put src/ on sys.path)

ARCH = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime"
COHORTS = ["v7", "v8"]
REPS = (1, 2, 3)
LONG_TEXT_CHARS = 100
KIND_ORDER = ["scalar", "long text", "list", "nested"]
KIND_LABEL = {"scalar": "scalar", "long text": "long text", "list": "list of values", "nested": "nested"}
STATES = ["identical", "two_agree", "all_differ", "intermittent", "absent"]
STATE_LABEL = {
    "identical": "identical in all three replicates",
    "two_agree": "present in all three; two identical, one differs",
    "all_differ": "present in all three; all three differ",
    "intermittent": "present in only one or two replicates (digit = how many)",
    "absent": "absent in all three replicates",
}
COLOR = {"identical": st.ORDINAL[9], "two_agree": st.ORDINAL[5], "all_differ": st.ORDINAL[1],
         "intermittent": st.SERIES[3], "absent": st.INK["mid"]}


# ---------------------------------------------------------------- comparison
def _norm(v):
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, str):
        return re.sub(r"\s+", " ", v).strip()
    return v


def canon(v) -> str:
    return yaml.safe_dump(_norm(v), sort_keys=True, allow_unicode=True, width=10**9)


def canon_unordered(v) -> str:
    def srt(x):
        if isinstance(x, dict):
            return {k: srt(y) for k, y in x.items()}
        if isinstance(x, list):
            return sorted((srt(y) for y in x), key=lambda y: yaml.safe_dump(y, sort_keys=True, width=10**9))
        return x
    return yaml.safe_dump(srt(_norm(v)), sort_keys=True, allow_unicode=True, width=10**9)


def compare(vals: list) -> dict:
    present = [not f02.empty(v) for v in vals]
    n = sum(present)
    out = {"n_present": n, "n_distinct": "", "identical_ignoring_list_order": ""}
    if n == 3:
        forms = [canon(v) for v in vals]
        k = len(set(forms))
        out["n_distinct"] = k
        out["state"] = {1: "identical", 2: "two_agree", 3: "all_differ"}[k]
        out["identical_ignoring_list_order"] = len({canon_unordered(v) for v in vals}) == 1
    elif n == 0:
        out["state"] = "absent"
    else:
        out["state"] = "intermittent"
    for r, v, p in zip(REPS, vals, present):
        out[f"rep{r}_present"] = p
        out[f"rep{r}_canonical_chars"] = len(canon(v)) if p else ""
        out[f"rep{r}_items"] = len(v) if p and isinstance(v, list) else ""
    return out


# ---------------------------------------------------------------- inputs
def groups() -> OrderedDict:
    """(project, cohort) -> {rep: input path}, from the frozen manifest."""
    manifest = json.loads((ARCH / "manifest.json").read_text())
    g: dict = defaultdict(dict)
    for j in manifest["jobs"]:
        key, rep = (j["project"], j["cohort"]), j["generation_rep"]
        assert g[key].get(rep, j["input"]) == j["input"], f"two inputs for {key} rep {rep}"
        g[key][rep] = j["input"]
    out = OrderedDict()
    for p in st.PROJECTS:
        for c in COHORTS:
            assert sorted(g[(p, c)]) == list(REPS), (p, c, sorted(g[(p, c)]))
            out[(p, c)] = g[(p, c)]
    assert len(g) == len(out), sorted(set(g) - set(out))
    return out


def slot_kinds(slots: list[str], docs: list[dict]) -> tuple[dict, dict]:
    view = shared_view(f02.MERGED)
    induced = {s.name: s for s in view.class_induced_slots("Dataset")}
    kinds, med = {}, {}
    for s in slots:
        sd = induced[s]
        lens = [len(d[s]) for d in docs if isinstance(d.get(s), str) and d[s]]
        med[s] = statistics.median(lens) if lens else ""
        if view.get_class(str(sd.range)) is not None:
            kinds[s] = "nested"
        elif sd.multivalued:
            kinds[s] = "list"
        elif str(sd.range) == "string" and lens and med[s] > LONG_TEXT_CHARS:
            kinds[s] = "long text"
        else:
            kinds[s] = "scalar"
    return kinds, med


def blocks(mods: OrderedDict, kinds: dict) -> list[tuple[str, str, list[str]]]:
    """(module, block label, slots); a module mixing kinds is split into one block per kind."""
    out = []
    for m, slots in mods.items():
        present = [k for k in KIND_ORDER if any(kinds[s] == k for s in slots)]
        if len(present) == 1:
            out.append((m, m, list(slots)))
        else:
            for k in present:
                out.append((m, f"{m}: {KIND_LABEL[k]}", [s for s in slots if kinds[s] == k]))
    return out


# ---------------------------------------------------------------- figure
def main() -> int:
    st.apply()
    grp = groups()
    docs = {}
    for key, reps in grp.items():
        for r, path in reps.items():
            f02.verify_arm(path, "api")
            d = yaml.safe_load((st.ROOT / path).read_text())
            assert isinstance(d, dict) and d, path
            docs[(key, r)] = d
    mods = f02.slot_modules()
    all_slots = [s for v in mods.values() for s in v]
    extra = sorted({k for d in docs.values() for k in d if k not in all_slots})
    assert set(extra) <= {"source_caveats"}, f"top-level keys that are not Dataset slots: {extra}"
    kinds, med = slot_kinds(all_slots, list(docs.values()))
    blk = blocks(mods, kinds)
    order = [(m, b, s) for m, b, ss in blk for s in ss]
    assert len(order) == len(all_slots) == len(set(s for _, _, s in order))
    n_slots, cols = len(order), list(grp)

    # nested items carrying an id (why identifier alignment was not used)
    n_items = n_with_id = 0
    for d in docs.values():
        for s in all_slots:
            v = d.get(s)
            if kinds[s] == "nested" and isinstance(v, list):
                n_items += sum(1 for x in v if isinstance(x, dict))
                n_with_id += sum(1 for x in v if isinstance(x, dict) and x.get("id"))

    cell = {}
    rows_main = []
    for (proj, coh) in cols:
        for m, b, s in order:
            res = compare([docs[((proj, coh), r)].get(s) for r in REPS])
            cell[(s, (proj, coh))] = res
            rows_main.append({"project": proj, "cohort": coh, "module": m, "block": b, "slot": s, "kind": kinds[s],
                              **{k: res[k] for k in ("state", "n_present", "n_distinct", "identical_ignoring_list_order")},
                              **{f"rep{r}_{x}": res[f"rep{r}_{x}"] for r in REPS for x in ("present", "canonical_chars", "items")},
                              **{f"rep{r}_input": grp[(proj, coh)][r] for r in REPS}})
    order_flips = sum(1 for r in rows_main if r["state"] in ("two_agree", "all_differ") and r["identical_ignoring_list_order"] is True)

    # ---- layout
    gap_proj = 0.35
    xs = []
    for i, (proj, coh) in enumerate(cols):
        xs.append(i + gap_proj * (i // 2))
    x_max = xs[-1] + 1
    row_h = 0.108
    fig = plt.figure(figsize=(9.8, 16.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.35, n_slots * row_h], width_ratios=[1.0, 0.27],
                          left=0.285, right=0.975, top=0.898, bottom=0.135, hspace=0.035, wspace=0.05)
    ax_top = fig.add_subplot(gs[0, 0])
    ax = fig.add_subplot(gs[1, 0], sharex=ax_top)
    ax_right = fig.add_subplot(gs[1, 1], sharey=ax)
    pad = 0.06

    # ---- matrix
    y = 0
    block_edges = []
    for m, b, ss in blk:
        for s in ss:
            for key, x0 in zip(cols, xs):
                res = cell[(s, key)]
                ax.add_patch(Rectangle((x0 + pad, y + pad), 1 - 2 * pad, 1 - 2 * pad, facecolor=COLOR[res["state"]], linewidth=0))
                if res["state"] == "intermittent":
                    ax.text(x0 + 0.5, y + 0.53, str(res["n_present"]), ha="center", va="center", fontsize=5.6,
                            color=st.INK["primary"])
            y += 1
        block_edges.append((b, y - len(ss), y))
    ax.set_xlim(-0.05, x_max + 0.05)
    ax.set_ylim(n_slots, 0)
    ax.set_yticks([i + 0.5 for i in range(n_slots)])
    ax.set_yticklabels([s for _, _, s in order], fontsize=6.3)
    ax.tick_params(axis="y", length=0, pad=2)
    for sp in ax.spines.values():
        sp.set_visible(False)
    for _, a, b in block_edges[:-1]:
        ax.axhline(b, color=st.INK["axis"], linewidth=0.6, zorder=3)
        ax_right.axhline(b, color=st.INK["grid"], linewidth=0.6, zorder=0)
    for b, a, e in block_edges:
        n = e - a
        ax.text(-0.285, a + n / 2, b, ha="right", va="center", fontsize=7 if n > 1 else 6.3, fontweight="bold",
                color=st.INK["secondary"], transform=ax.get_yaxis_transform(), clip_on=False)
    ax.set_xticks([x0 + 0.5 for x0 in xs])
    ax.set_xticklabels([coh for _, coh in cols], fontsize=7)
    ax.tick_params(axis="x", length=0, pad=2)
    for i in range(0, len(cols), 2):
        ax.text((xs[i] + xs[i + 1] + 1) / 2, n_slots + 2.3, cols[i][0].replace("_", "-"), ha="center", va="top",
                fontsize=7.5, fontweight="bold", color=st.INK["secondary"], clip_on=False)

    # ---- right marginal: per slot, groups (of 8) in each state
    rows_slot = []
    for i, (m, b, s) in enumerate(order):
        cnt = Counter(cell[(s, key)]["state"] for key in cols)
        left = 0
        for state in STATES:
            if cnt[state]:
                ax_right.barh(i + 0.5, cnt[state], left=left, height=0.78, color=COLOR[state],
                              edgecolor=st.INK["surface"], linewidth=0.6, zorder=2)
                left += cnt[state]
        rows_slot.append({"module": m, "block": b, "slot": s, "kind": kinds[s],
                          "median_observed_string_chars": med[s], "n_groups": len(cols),
                          **{f"groups_{state}": cnt[state] for state in STATES}})
    ax_right.set_xlim(0, len(cols))
    ax_right.set_xticks([0, 4, 8])
    ax_right.tick_params(axis="y", length=0, labelleft=False)
    ax_right.tick_params(axis="x", length=2, labelsize=6.5, pad=1)
    for sp in ("left", "top", "right"):
        ax_right.spines[sp].set_visible(False)
    ax_right.set_xlabel(f"groups (of {len(cols)}) per state", fontsize=7)
    ax_right.xaxis.set_label_position("bottom")

    # ---- top marginal: per group, slots (of n) in each state
    rows_group = []
    for (proj, coh), x0 in zip(cols, xs):
        cnt = Counter(cell[(s, (proj, coh))]["state"] for _, _, s in order)
        bottom = 0
        for state in STATES:
            if cnt[state]:
                ax_top.bar(x0 + 0.5, cnt[state], bottom=bottom, width=0.72, color=COLOR[state],
                           edgecolor=st.INK["surface"], linewidth=0.8, zorder=2)
                bottom += cnt[state]
        n_all3 = cnt["identical"] + cnt["two_agree"] + cnt["all_differ"]
        ax_top.text(x0 + 0.5, n_slots + 2, f'{cnt["identical"]} of {n_all3}', ha="center", va="bottom",
                    fontsize=6.4, color=st.INK["primary"])
        labels = sorted({re.sub(r"_rep\d+$", "", Path(grp[(proj, coh)][r]).parent.name) for r in REPS})
        rows_group.append({"project": proj, "cohort": coh, "run_labels": "; ".join(labels), "n_slots": n_slots,
                           **{f"slots_{state}": cnt[state] for state in STATES},
                           "slots_present_in_all_three": n_all3,
                           "fraction_identical_of_present_in_all_three": round(cnt["identical"] / n_all3, 4) if n_all3 else ""})
    ax_top.set_ylim(0, n_slots)
    ax_top.set_yticks([0, 25, 50, 75, n_slots])
    ax_top.tick_params(axis="y", length=2, labelsize=6.5)
    ax_top.tick_params(axis="x", length=0, labelbottom=False)
    ax_top.spines["bottom"].set_visible(False)
    ax_top.set_ylabel(f"slots (of {n_slots})\nper state", fontsize=7, labelpad=4)
    st.hairline_grid(ax_top)
    ax_top.text(-0.285, n_slots + 2, "identical / present in all three:", ha="right", va="bottom", fontsize=6.4,
                color=st.INK["secondary"], transform=ax_top.get_yaxis_transform(), clip_on=False)
    # column headers: arm strip, project, cohort
    tr = ax_top.get_xaxis_transform()
    ax_top.add_patch(Rectangle((xs[0] + 0.05, 1.37), x_max - 0.1, 0.04, facecolor=st.ARM_COLOR["api"], transform=tr, clip_on=False))
    ax_top.text(xs[0], 1.43, "API arm (Messages SDK via CBORG); every record's arm verified from its provenance agent_runtime",
                ha="left", va="bottom", fontsize=6.6, color=st.INK["secondary"], transform=tr)
    for i in range(0, len(cols), 2):
        ax_top.text((xs[i] + xs[i + 1] + 1) / 2, 1.28, cols[i][0].replace("_", "-"), ha="center", va="center",
                    fontsize=8.2, fontweight="bold", color=st.INK["secondary"], transform=tr)
    for (proj, coh), x0 in zip(cols, xs):
        ax_top.text(x0 + 0.5, 1.175, coh, ha="center", va="center", fontsize=7, color=st.INK["secondary"], transform=tr)

    # ---- legend + notes
    handles = [Patch(facecolor=COLOR[s], label=STATE_LABEL[s]) for s in STATES]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.012, 0.078), ncol=2, fontsize=7,
               handlelength=1.6, columnspacing=1.8, handletextpad=0.6)
    n_nested_mod = sum(len(v) for m, v in mods.items() if m != f02.BASE)
    assert all(kinds[s] == "nested" for m, v in mods.items() if m != f02.BASE for s in v), "a module slot is not nested"
    notes = [
        (f"Comparison: each slot's whole value, as key-sorted YAML with whitespace runs collapsed; list order counts "
         f"(ignoring order would make {order_flips} differing cell{'' if order_flips == 1 else 's'} identical). Nested entities are not aligned by "
         f"identifier: {n_with_id} of {n_items} nested list items carry an id. "
         f"All {n_nested_mod} slots in the {len(mods) - 1} D4D module blocks are nested (class-valued); Base / root is split by kind. "
         f"Heuristic: long text = single-valued string slot whose median observed length exceeds {LONG_TEXT_CHARS} characters."),
        ("Caveats: textual difference is not necessarily factual difference (paraphrase, reordering or one changed "
         f"sub-field makes a value differ). Three replicates per group describe these {len(docs)} records only and cannot "
         "estimate the reliability of the generation process."),
    ]
    yy = 0.07
    for t in notes:
        wrapped = textwrap.fill(t, 190)
        fig.text(0.012, yy, wrapped, fontsize=6.6, color=st.INK["secondary"], ha="left", va="top")
        yy -= 0.0085 * (wrapped.count("\n") + 1) + 0.004
    fig.suptitle("Which Dataset slot values are identical across three generation replicates?",
                 x=0.012, ha="left", fontsize=11, fontweight="bold", y=0.975)
    fig.text(0.012, 0.955, f"Reference rescore records, {len(st.PROJECTS)} projects x {len(COHORTS)} prompt conditions x "
             f"{len(REPS)} replicates; one column per project-prompt group, one row per top-level Dataset slot, grouped by schema module",
             fontsize=7.5, color=st.INK["secondary"], ha="left", va="bottom")

    by_label = {c: defaultdict(list) for c in COHORTS}
    for g in rows_group:
        for lab in g["run_labels"].split("; "):
            by_label[g["cohort"]][lab.split("_")[0]].append(g["project"])
    label_text = ", ".join(
        f"{c} " + "; ".join(lab if len(ps) == len(st.PROJECTS) else f"{lab} ({', '.join(ps)})" for lab, ps in sorted(by_label[c].items()))
        for c in COHORTS)
    basis = (f"Record set: {len(docs)} API-arm full records of the reference rescore 2026-09-12 manifest (jobs[].input); "
             f"{len(cols)} project x prompt groups x {len(REPS)} generation replicates; run labels {label_text}\n"
             f"{n_slots} top-level Dataset slots from data_sheets_schema_all.yaml, module attribution from fig02 "
             f"(source_caveats excluded)")
    st.save(fig, "fig12_replication_stability", {"main": rows_main, "groups": rows_group, "slots": rows_slot}, basis)
    tot = Counter(r["state"] for r in rows_main)
    print(f"records {len(docs)}, groups {len(cols)}, slots {n_slots}, cells {len(rows_main)}: " +
          ", ".join(f"{s}={tot[s]}" for s in STATES) + f"; nested items {n_items}, with id {n_with_id}; order flips {order_flips}")
    print("kinds:", dict(Counter(kinds.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
