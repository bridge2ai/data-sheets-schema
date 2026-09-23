#!/usr/bin/env python
"""#2300: the deterministic crate mapping per project, its fidelity, and how its filled
fields overlap with one generated record per project.

Panels A and B are parsed from the mapper's own reports,
data/ro-crate_packages/<P>/processed/<P>_crate_mapping_provenance.md (the Outcome
table and the two Fidelity tables), written by `d4d rocrate map` (rocrate_map.py,
no model). Panel C compares the top-level Dataset slots populated in
<P>_crate_mapped_d4d.yaml with those populated in the generic-v8 rep 1 full record
of the same project from the reference rescore set (manifest jobs with cohort v8,
generation_rep 1). Where both hold a value, "agree" means the YAML-serialised values
are identical after whitespace normalisation; anything else is "differ". Nested
values (lists of objects) rarely serialise identically, so "differ" is a ceiling on
disagreement, not a judgement of fact. Projects with a crate package but no mapper
output are drawn as an explicit placeholder.
"""
from __future__ import annotations

import json
import re
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.figures import _style as st  # noqa: E402

PKG = ROOT / "data" / "ro-crate_packages"
MANIFEST = ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime" / "manifest.json"
STATUSES = ["filled", "empty", "unresolvable", "unplaceable"]
STATUS_COL = {"filled": st.SEQ[8], "empty": st.SEQ[3], "unresolvable": None, "unplaceable": None}
LOSS = ["none", "minimal", "moderate", "high"]
LOSS_COL = dict(zip(LOSS, [st.ORDINAL[0], st.ORDINAL[3], st.ORDINAL[6], st.ORDINAL[9]]))
MAPTYPES = ["exactMatch", "closeMatch", "relatedMatch", "narrowMatch"]
MAP_COL = {"exactMatch": st.SERIES[6], "closeMatch": st.SERIES[3], "relatedMatch": st.SERIES[4], "narrowMatch": st.SERIES[5]}  # non-blue slots, so the ramp beside them stays unambiguous
EMPTY = (None, "", [], {})


def parse_report(path: Path) -> dict:
    text = path.read_text()
    out = {"outcome": {}, "loss": {}, "maptype": {}, "rows_applied": None}
    m = re.search(r"\((\d+) rows applied\)", text)
    if m:
        out["rows_applied"] = int(m.group(1))
    section = None
    for line in text.splitlines():
        if line.startswith("## Outcome"):
            section = "outcome"; continue
        if line.startswith("## Fidelity"):
            section = "fidelity"; continue
        if line.startswith("## Per-field"):
            section = None; continue
        if section and line.startswith("|") and not line.startswith("|--") and not line.startswith("|---"):
            cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
            if section == "outcome" and cells[0] in STATUSES:
                out["outcome"][cells[0]] = int(cells[1])
            elif section == "fidelity" and cells[0] in LOSS:
                out["loss"][cells[0]] = int(cells[1])
            elif section == "fidelity" and cells[0] in MAPTYPES:
                out["maptype"][cells[0]] = int(cells[1])
    return out


def norm(v) -> str:
    return re.sub(r"\s+", " ", yaml.safe_dump(v, sort_keys=True, allow_unicode=True)).strip()


def generated_v8_rep1() -> dict[str, str]:
    m = json.loads(MANIFEST.read_text())
    out = {}
    for j in m["jobs"]:
        if j["cohort"] == "v8" and j["generation_rep"] == 1:
            out.setdefault(j["project"], j["input"])
    return out


def overlap(project: str, mapped: Path, gen: Path) -> tuple[dict, list[dict]]:
    crate = yaml.safe_load(mapped.read_text())
    full = yaml.safe_load(gen.read_text())
    ck = {k for k, v in crate.items() if v not in EMPTY}
    gk = {k for k, v in full.items() if v not in EMPTY}
    detail, counts = [], {"both_agree": 0, "both_differ": 0, "crate_only": 0, "generated_only": 0}
    for k in sorted(ck | gk):
        if k in ck and k in gk:
            agree = norm(crate[k]) == norm(full[k])
            state = "both_agree" if agree else "both_differ"
        elif k in ck:
            state = "crate_only"
        else:
            state = "generated_only"
        counts[state] += 1
        detail.append({"project": project, "slot": k, "state": state})
    return counts, detail


def main() -> int:
    st.apply()
    gen = generated_v8_rep1()
    per_project, detail, panel_rows = {}, [], []
    for p in st.PROJECTS:
        rep = PKG / p / "processed" / f"{p}_crate_mapping_provenance.md"
        mapped = PKG / p / "processed" / f"{p}_crate_mapped_d4d.yaml"
        has_pkg = (PKG / p).is_dir()
        if rep.exists() and mapped.exists():
            info = parse_report(rep)
            counts, det = overlap(p, mapped, ROOT / gen[p])
            detail += det
            per_project[p] = {"status": "mapped", **info, "overlap": counts, "generated": gen[p]}
        else:
            per_project[p] = {"status": "crate package present, no mapper output" if has_pkg else "no crate package",
                              "outcome": {}, "loss": {}, "maptype": {}, "overlap": {}, "generated": gen.get(p)}
        panel_rows.append({"project": p, "status": per_project[p]["status"], "rows_applied": per_project[p].get("rows_applied"),
                           **{f"outcome_{s}": per_project[p]["outcome"].get(s) for s in STATUSES},
                           **{f"loss_{s}": per_project[p]["loss"].get(s, 0 if per_project[p]["outcome"] else None) for s in LOSS},
                           **{f"maptype_{s}": per_project[p]["maptype"].get(s, 0 if per_project[p]["outcome"] else None) for s in MAPTYPES},
                           **{f"overlap_{s}": per_project[p]["overlap"].get(s) for s in ("both_agree", "both_differ", "crate_only", "generated_only")},
                           "generated_record": per_project[p]["generated"]})

    fig = plt.figure(figsize=(10.8, 8.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05], hspace=0.62, wspace=0.28)
    axA = fig.add_subplot(gs[0, 0]); axB = fig.add_subplot(gs[0, 1]); axC = fig.add_subplot(gs[1, :])
    xs = range(len(st.PROJECTS))
    labels = [p.replace("_", "-") for p in st.PROJECTS]
    bw = 0.5

    # --- A: mapping outcomes ------------------------------------------------
    for i, p in enumerate(st.PROJECTS):
        d = per_project[p]
        if not d["outcome"]:
            axA.bar(i, 1, width=bw, facecolor="none", edgecolor=st.INK["muted"], linewidth=0.6, hatch=st.HATCH, transform=axA.get_xaxis_transform(), zorder=1)
            axA.text(i, 0.5, textwrap.fill(d["status"], 16), ha="center", va="center", fontsize=6.6, color=st.INK["secondary"],
                     transform=axA.get_xaxis_transform(), zorder=3, bbox=dict(facecolor=st.INK["surface"], edgecolor="none", pad=2))
            continue
        base = 0
        for s in STATUSES:
            v = d["outcome"].get(s, 0)
            if s in ("filled", "empty"):
                axA.bar(i, v, bottom=base, width=bw, color=STATUS_COL[s], edgecolor=st.INK["surface"], linewidth=0.8, zorder=2)
            else:
                axA.bar(i, v, bottom=base, width=bw, facecolor="none", edgecolor=st.INK["secondary"],
                        linewidth=0.6, hatch=st.HATCH if s == "unplaceable" else None, zorder=2)
            if v >= 8:
                axA.text(i, base + v / 2, str(v), ha="center", va="center", fontsize=6.6,
                         color=st.INK["surface"] if s == "filled" else st.INK["primary"])
            base += v
        axA.text(i, base + 2, f"{base} rows", ha="center", va="bottom", fontsize=6.6, color=st.INK["secondary"])
    axA.set_xticks(list(xs)); axA.set_xticklabels(labels)
    axA.set_ylabel("mapping-table rows"); axA.set_ylim(0, 160)
    st.hairline_grid(axA); axA.tick_params(axis="x", length=0)
    axA.set_title("A  Outcome of every mapping-table row", pad=6)
    axA.legend(handles=[Patch(color=STATUS_COL["filled"], label="filled: path resolved, value placed"),
                        Patch(color=STATUS_COL["empty"], label="empty: path valid, no value in the crate"),
                        Patch(facecolor="none", edgecolor=st.INK["secondary"], linewidth=0.8, label="unresolvable: table declares no crate path"),
                        Patch(facecolor="none", edgecolor=st.INK["secondary"], linewidth=0.8, hatch=st.HATCH, label="unplaceable: no route into a Dataset record")],
               loc="upper left", bbox_to_anchor=(0, -0.16), fontsize=6.8, ncol=1, handlelength=1.4)

    # --- B: fidelity of filled fields (loss level, and mapping type) -------
    mapped = [p for p in st.PROJECTS if per_project[p]["outcome"]]
    for i, p in enumerate(st.PROJECTS):
        d = per_project[p]
        if not d["outcome"]:
            axB.bar(i, 1, width=bw + 0.2, facecolor="none", edgecolor=st.INK["muted"], linewidth=0.6, hatch=st.HATCH, transform=axB.get_xaxis_transform(), zorder=1)
            axB.text(i, 0.5, textwrap.fill(d["status"], 16), ha="center", va="center", fontsize=6.6, color=st.INK["secondary"],
                     transform=axB.get_xaxis_transform(), zorder=3, bbox=dict(facecolor=st.INK["surface"], edgecolor="none", pad=2))
            continue
        base = 0
        for s in LOSS:  # ordered: one hue, light -> dark
            v = d["loss"].get(s, 0)
            axB.bar(i - 0.17, v, bottom=base, width=0.3, color=LOSS_COL[s], edgecolor=st.INK["surface"], linewidth=0.8, zorder=2)
            if v >= 6:
                axB.text(i - 0.17, base + v / 2, str(v), ha="center", va="center", fontsize=6.4,
                         color=st.INK["surface"] if s in ("moderate", "high") else st.INK["primary"])
            base += v
        base = 0
        for s in MAPTYPES:
            v = d["maptype"].get(s, 0)
            axB.bar(i + 0.17, v, bottom=base, width=0.3, color=MAP_COL[s], edgecolor=st.INK["surface"], linewidth=0.8, zorder=2)
            if v >= 6:
                axB.text(i + 0.17, base + v / 2, str(v), ha="center", va="center", fontsize=6.4,
                         color=st.INK["surface"] if s in ("exactMatch", "narrowMatch") else st.INK["primary"])
            base += v
        axB.text(i - 0.17, sum(d["loss"].values()) + 1, "loss", ha="center", va="bottom", fontsize=6, color=st.INK["muted"])
        axB.text(i + 0.17, sum(d["maptype"].values()) + 1, "type", ha="center", va="bottom", fontsize=6, color=st.INK["muted"])
    axB.set_xticks(list(xs)); axB.set_xticklabels(labels)
    axB.set_ylabel("filled fields"); axB.set_ylim(0, 60)
    st.hairline_grid(axB); axB.tick_params(axis="x", length=0)
    axB.set_title("B  Filled fields by declared information loss (ordered) and by mapping type", pad=6)
    axB.legend(handles=[Patch(color=LOSS_COL[s], label=f"loss: {s}") for s in LOSS] +
                       [Patch(color=MAP_COL[s], label=f"type: {s}") for s in MAPTYPES],
               loc="upper left", bbox_to_anchor=(0, -0.16), fontsize=6.8, ncol=2, handlelength=1.4)

    # --- C: overlap with a generated record --------------------------------
    OV = [("both_agree", "both populated, values agree", st.SEQ[9], None),
          ("both_differ", "both populated, values differ", st.SEQ[4], None),
          ("crate_only", "crate-mapped only", st.SERIES[4], None),
          ("generated_only", "generated only", st.SERIES[3], None)]
    for i, p in enumerate(st.PROJECTS):
        d = per_project[p]
        if not d["overlap"]:
            axC.barh(i, 1, height=bw, facecolor="none", edgecolor=st.INK["muted"], linewidth=0.6, hatch=st.HATCH, transform=axC.get_yaxis_transform(), zorder=1)
            axC.text(0.5, i, d["status"] + ("; generated v8 rep 1 record exists" if d["generated"] else ""), ha="center", va="center",
                     fontsize=6.8, color=st.INK["secondary"], transform=axC.get_yaxis_transform(), zorder=3, bbox=dict(facecolor=st.INK["surface"], edgecolor="none", pad=2))
            continue
        base = 0
        for key, _, c, _ in OV:
            v = d["overlap"][key]
            axC.barh(i, v, left=base, height=bw, color=c, edgecolor=st.INK["surface"], linewidth=0.8, zorder=2)
            if v >= 3:
                axC.text(base + v / 2, i, str(v), ha="center", va="center", fontsize=6.8,
                         color=st.INK["surface"] if key == "both_agree" else st.INK["primary"])
            base += v
        axC.text(base + 0.8, i, f"{base} populated top-level slots in either", va="center", fontsize=6.6, color=st.INK["secondary"])
    axC.set_yticks(list(xs)); axC.set_yticklabels(labels); axC.invert_yaxis()
    axC.set_xlabel("top-level Dataset slots populated in the crate-mapped record and/or the generated v8 rep 1 record")
    axC.set_xlim(0, 110)
    st.hairline_grid(axC, "x"); axC.tick_params(axis="y", length=0)
    axC.set_title("C  Populated top-level slots: crate-mapped record vs generated record (generic-v8, rep 1, API arm)", pad=6)
    axC.legend(handles=[Patch(color=c, label=l) for _, l, c, _ in OV], loc="upper left", bbox_to_anchor=(0, -0.2), ncol=4, fontsize=6.8, handlelength=1.4)

    fig.suptitle("Deterministic crate mapping per project: outcomes, fidelity, and overlap with a generated record",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=0.985)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.17)
    basis = ("Record set: crate mapping reports under data/ro-crate_packages/<P>/processed/ (" + ", ".join(mapped) +
             "); generated records = reference rescore 2026-09-12 v8 rep 1 (claudecode_api/2026-09-04f and 04g); value agreement = normalised YAML equality")
    st.save(fig, "fig09_crate_vs_generation", {"main": panel_rows, "overlap_slots": detail}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
