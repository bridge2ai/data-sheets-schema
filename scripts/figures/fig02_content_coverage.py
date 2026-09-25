#!/usr/bin/env python
"""#2293: populated schema content per record, module by module and slot by slot.

Record set: the 24 API-arm full records of the frozen CBORG reference rescore
(notes/reference_rescore_2026-09-12_cborg_runtime/manifest.json, jobs[].input; v7 under
claudecode_agent/, v8 under claudecode_api/), plus the 12 most recent agentic-arm full
records (data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep{1,2,3}),
plus the direct arm: full records under data/d4d_concatenated/claudecode_direct/<label>/
are drawn as a column group only when their <label>_core/<P>_provenance.yaml sibling exists
(the provenance record is the acceptance signal: the first direct-arm canary,
notes/claudecode_direct/CHORUS_direct_rep1_2026-09-23_stopped.md, was disqualified because
no provenance record was written, and its records are not in the corpus). A direct-arm
record without that sibling is drawn blank and labelled "disqualified / not in corpus";
when the directory is absent or empty the group is an explicit "direct: no accepted run" placeholder.

Arm attribution is verified from provenance, not from the directory or cohort: every drawn
record's <method>_core/<label>/<P>_provenance.yaml model.agent_runtime must map through
runs.RUNTIME_KEYS to the arm it is drawn under ("claude api (direct)" -> api, "claude code"
-> agentic, "claude code (direct)" -> direct); a mismatch stops the build.

Slots: class Dataset's induced slots from the merged schema (SchemaView over
data_sheets_schema_all.yaml). Every Dataset slot is declared in the root schema file, so
a slot is attributed to the module whose YAML file (D4D_*.yaml) defines its range class;
slots whose range is a base type or a root-declared class (Dataset, DataSubset) form a
trailing "Base / root" group. `source_caveats` is the caveat channel itself and is not a
row.

States: populated = non-empty value (not None / "" / [] / {}); caveat-only = the slot is
absent (or its value carries nothing but `source_caveats`) but some `source_caveats`
string in the record names the slot as a whole word; empty = absent, not mentioned.
Module cells are the fraction of the module's slots that are populated (caveat-only does
not count). No record = blank with a hairline border.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

sys.path.insert(0, str(st.ROOT / "src"))
from data_sheets_schema.runs import RUNTIME_KEYS  # noqa: E402
from data_sheets_schema.schema_view import shared_view  # noqa: E402

ARCH = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime"
SCHEMA_DIR = st.ROOT / "src" / "data_sheets_schema" / "schema"
MERGED = SCHEMA_DIR / "data_sheets_schema_all.yaml"
AGENTIC_GLOB = "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep*/{project}_d4d.yaml"
DIRECT_DIR = st.ROOT / "data" / "d4d_concatenated" / "claudecode_direct"

MODULES = OrderedDict([
    ("Motivation", "D4D_Motivation.yaml"), ("Composition", "D4D_Composition.yaml"),
    ("Collection", "D4D_Collection.yaml"), ("Preprocessing", "D4D_Preprocessing.yaml"),
    ("Uses", "D4D_Uses.yaml"), ("Distribution", "D4D_Distribution.yaml"),
    ("Maintenance", "D4D_Maintenance.yaml"), ("Ethics", "D4D_Ethics.yaml"),
    ("Human", "D4D_Human.yaml"), ("Data Governance", "D4D_Data_Governance.yaml"),
    ("Variables", "D4D_Variables.yaml"), ("FileCollection", "D4D_FileCollection.yaml"),
])
BASE = "Base / root"
COLOR = {"populated": st.ORDINAL[6], "caveat_only": st.ORDINAL[0], "empty": st.INK["mid"]}
ARMS = [("api", "v7"), ("api", "v8"), ("agentic", "v6"), ("direct", "")]
ARM_TEXT = {("api", "v7"): "API v7", ("api", "v8"): "API v8", ("agentic", "v6"): "agentic v6", ("direct", ""): "direct"}


def provenance_path(full_record: str) -> Path:
    """data/d4d_concatenated/<method>/<label>/<P>_d4d.yaml -> <method>_core/<label>/<P>_provenance.yaml"""
    rel = Path(full_record)
    method, label, name = rel.parts[-3], rel.parts[-2], rel.name
    assert name.endswith("_d4d.yaml"), full_record
    return st.ROOT / "data" / "d4d_concatenated" / f"{method}_core" / label / (name[: -len("_d4d.yaml")] + "_provenance.yaml")


def verify_arm(full_record: str, arm: str) -> str:
    """The runtime key recorded in the provenance file; must equal the arm the column is drawn under."""
    prov = provenance_path(full_record)
    assert prov.exists(), f"no provenance record for {full_record}: {prov}"
    runtime = (yaml.safe_load(prov.read_text()).get("model") or {}).get("agent_runtime")
    key = RUNTIME_KEYS.get(str(runtime).strip().lower())
    assert key == arm, f"{full_record}: provenance agent_runtime {runtime!r} maps to {key!r}, drawn under {arm!r}"
    return str(runtime)


def direct_records(proj: str) -> list[dict]:
    """Direct-arm full records for a project, newest label first; accepted only with a provenance sibling."""
    out = []
    if not DIRECT_DIR.is_dir():
        return out
    for p in sorted(DIRECT_DIR.glob(f"*/{proj}_d4d.yaml"), reverse=True):
        rel = os.path.relpath(p, st.ROOT)
        out.append({"path": rel, "accepted": provenance_path(rel).exists(), "label": p.parent.name})
    return out


def empty(v) -> bool:
    return v is None or v == "" or v == [] or v == {}


def caveat_strings(obj, out: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "source_caveats" and isinstance(v, str):
                out.append(v)
            else:
                caveat_strings(v, out)
    elif isinstance(obj, list):
        for x in obj:
            caveat_strings(x, out)


def only_caveat(v) -> bool:
    if isinstance(v, dict):
        keys = {k for k, x in v.items() if not empty(x)}
        return bool(keys) and keys <= {"source_caveats"}
    if isinstance(v, list) and v:
        return all(only_caveat(x) for x in v)
    return False


def slot_modules() -> OrderedDict[str, list[str]]:
    """module -> ordered list of Dataset slots, attributed by the range class's file."""
    view = shared_view(MERGED)
    cls2file: dict[str, str] = {}
    for f in sorted(SCHEMA_DIR.glob("D4D_*.yaml")):
        for c in (yaml.safe_load(f.read_text()).get("classes") or {}):
            cls2file.setdefault(c, f.name)
    file2mod = {v: k for k, v in MODULES.items()}
    groups: OrderedDict[str, list[str]] = OrderedDict((m, []) for m in MODULES)
    groups[BASE] = []
    for s in view.class_induced_slots("Dataset"):
        if s.name == "source_caveats":
            continue
        groups[file2mod.get(cls2file.get(str(s.range), ""), BASE)].append(s.name)
    return groups


def records():
    """Ordered columns: project > arm > cohort > replicate; None path = placeholder."""
    manifest = json.loads((ARCH / "manifest.json").read_text())
    api = {}
    for j in manifest["jobs"]:
        api[(j["project"], j["cohort"], j["generation_rep"])] = j["input"]
    cols = []
    for proj in st.PROJECTS:
        for arm, cohort in ARMS:
            if arm == "api":
                for rep in (1, 2, 3):
                    cols.append({"project": proj, "arm": arm, "cohort": cohort, "rep": rep, "path": api[(proj, cohort, rep)]})
            elif arm == "agentic":
                paths = sorted(glob.glob(str(st.ROOT / AGENTIC_GLOB.format(project=proj))))
                for rep in (1, 2, 3):
                    hit = [p for p in paths if p.endswith(f"_rep{rep}/{proj}_d4d.yaml")]
                    cols.append({"project": proj, "arm": arm, "cohort": cohort, "rep": rep,
                                 "path": os.path.relpath(hit[0], st.ROOT) if hit else None})
            else:
                found = direct_records(proj)
                if not found:
                    cols.append({"project": proj, "arm": arm, "cohort": "", "rep": None, "path": None, "direct": "no accepted run"})
                for k, d in enumerate(found, 1):
                    m = re.search(r"_rep(\d+)", d["label"])
                    cols.append({"project": proj, "arm": arm, "cohort": "", "rep": int(m.group(1)) if m else k,
                                 "path": d["path"] if d["accepted"] else None,
                                 "direct": "accepted" if d["accepted"] else "disqualified / not in corpus"})
    return cols


def classify(doc: dict, slots: list[str]) -> dict[str, str]:
    cav: list[str] = []
    caveat_strings(doc, cav)
    text = "\n".join(cav)
    out = {}
    for s in slots:
        v = doc.get(s)
        if not empty(v) and not only_caveat(v):
            out[s] = "populated"
        elif re.search(r"\b" + re.escape(s) + r"\b", text) or only_caveat(v):
            out[s] = "caveat_only"
        else:
            out[s] = "empty"
    return out


def main() -> int:
    st.apply()
    groups = slot_modules()
    all_slots = [s for g in groups.values() for s in g]
    cols = records()
    for c in cols:
        if c["path"]:
            doc = yaml.safe_load((st.ROOT / c["path"]).read_text())
            assert isinstance(doc, dict) and doc, c["path"]
            c["runtime"] = verify_arm(c["path"], c["arm"])
            c["state"] = classify(doc, all_slots)
        else:
            c["state"] = None
            c["runtime"] = ""
    n_direct = sum(1 for c in cols if c["arm"] == "direct" and c["path"])
    n_disq = sum(1 for c in cols if c["arm"] == "direct" and c.get("direct", "").startswith("disqualified"))
    n_rec = sum(1 for c in cols if c["path"])
    n_api = sum(1 for c in cols if c["arm"] == "api" and c["path"])
    n_agentic = sum(1 for c in cols if c["arm"] == "agentic" and c["path"])

    # x positions: contiguous within a project, a gap between projects and a half gap between arms
    xs, x = [], 0.0
    prev = None
    for c in cols:
        key = (c["project"], c["arm"], c["cohort"])
        if prev is not None:
            x += 0.9 if prev[0] != key[0] else (0.35 if prev != key else 0.0)
        xs.append(x); x += 1.0; prev = key
    width_total = x

    fig = plt.figure(figsize=(11.0, 13.2))
    gs = fig.add_gridspec(3, 2, height_ratios=[0.9, len(groups) * 0.26, len(all_slots) * 0.088],
                          width_ratios=[1.0, 0.11], hspace=0.09, wspace=0.03,
                          left=0.215, right=0.985, top=0.905, bottom=0.075)
    ax_top = fig.add_subplot(gs[0, 0])
    ax_mod = fig.add_subplot(gs[1, 0], sharex=ax_top)
    ax_right = fig.add_subplot(gs[1, 1], sharey=ax_mod)
    ax_slot = fig.add_subplot(gs[2, 0], sharex=ax_top)
    cmap = LinearSegmentedColormap.from_list("seq", st.SEQ)
    pad = 0.07
    rows_main, rows_mod, rows_rec = [], [], []

    # module panel
    mod_names = list(groups)
    for i, m in enumerate(mod_names):
        for c, x0 in zip(cols, xs):
            if c["state"] is None:
                ax_mod.add_patch(Rectangle((x0 + pad, i + pad), 1 - 2 * pad, 1 - 2 * pad, facecolor=st.INK["surface"],
                                           edgecolor=st.INK["axis"], linewidth=0.4))
                continue
            n_pop = sum(1 for s in groups[m] if c["state"][s] == "populated")
            frac = n_pop / len(groups[m])
            ax_mod.add_patch(Rectangle((x0 + pad, i + pad), 1 - 2 * pad, 1 - 2 * pad, facecolor=cmap(frac)))
            rows_mod.append({"project": c["project"], "arm": c["arm"], "cohort": c["cohort"], "rep": c["rep"],
                             "module": m, "n_slots": len(groups[m]), "n_populated": n_pop, "fraction": round(frac, 4)})
    ax_mod.set_xlim(-0.05, width_total + 0.05); ax_mod.set_ylim(len(mod_names), 0)
    ax_mod.set_yticks([i + 0.5 for i in range(len(mod_names))]); ax_mod.set_yticklabels(mod_names, fontsize=7.5)
    ax_mod.tick_params(axis="both", length=0, labelbottom=False)
    for sp in ax_mod.spines.values():
        sp.set_visible(False)
    ax_mod.set_title("Fraction of each module's Dataset slots populated", pad=9, fontsize=8.5)

    # right marginal: fraction populated per module across all records
    for i, m in enumerate(mod_names):
        vals = [sum(1 for s in groups[m] if c["state"][s] == "populated") / len(groups[m]) for c in cols if c["state"]]
        f = sum(vals) / len(vals)
        ax_right.barh(i + 0.5, f, height=0.62, color=st.SERIES[0], zorder=2)
        ax_right.text(f + 0.03, i + 0.5, f"{f:.2f}", va="center", ha="left", fontsize=6.3, color=st.INK["secondary"])
    ax_right.set_xlim(0, 1.32); ax_right.set_xticks([0, 0.5, 1.0]); ax_right.set_xticklabels(["0", ".5", "1"], fontsize=6.5)
    ax_right.tick_params(axis="y", length=0, labelleft=False); ax_right.tick_params(axis="x", length=2)
    for sp in ("left", "top", "right"):
        ax_right.spines[sp].set_visible(False)
    ax_right.set_title("mean over\nrecords", fontsize=7, pad=3, loc="left", fontweight="normal", color=st.INK["secondary"])

    # top marginal: fraction of all slots populated per record
    for c, x0 in zip(cols, xs):
        if c["state"] is None:
            continue
        f = sum(1 for s in all_slots if c["state"][s] == "populated") / len(all_slots)
        ax_top.bar(x0 + 0.5, f, width=0.7, color=st.SERIES[0], zorder=2)
        rows_rec.append({"project": c["project"], "arm": c["arm"], "cohort": c["cohort"], "rep": c["rep"], "path": c["path"],
                         "n_slots": len(all_slots),
                         "n_populated": sum(1 for s in all_slots if c["state"][s] == "populated"),
                         "n_caveat_only": sum(1 for s in all_slots if c["state"][s] == "caveat_only"),
                         "fraction_populated": round(f, 4)})
    ax_top.set_ylim(0, 1.0); ax_top.set_yticks([0, 0.5, 1.0]); ax_top.set_yticklabels(["0", ".5", "1"], fontsize=6.5)
    ax_top.set_ylabel("fraction of\nall slots", fontsize=7, labelpad=6)
    st.hairline_grid(ax_top); ax_top.tick_params(axis="x", length=0, labelbottom=False); ax_top.spines["bottom"].set_visible(False)
    ax_top.tick_params(axis="y", length=2)

    # column headers: project name, arm strip, replicate numbers
    top_y = 1.02
    first = {}
    for c, x0 in zip(cols, xs):
        first.setdefault(c["project"], [x0, x0]); first[c["project"]][1] = x0 + 1
        key = (c["project"], c["arm"], c["cohort"])
        first.setdefault(key, [x0, x0]); first[key][1] = x0 + 1
    for proj in st.PROJECTS:
        a, b = first[proj]
        ax_top.text((a + b) / 2, 1.42, proj.replace("_", "-"), ha="center", va="bottom", fontsize=8.5, fontweight="bold",
                    color=st.INK["secondary"], transform=ax_top.get_xaxis_transform())
        for arm, cohort in ARMS:
            a, b = first[(proj, arm, cohort)]
            ax_top.add_patch(Rectangle((a + 0.08, 1.24), b - a - 0.16, 0.07, facecolor=st.ARM_COLOR[arm],
                                       transform=ax_top.get_xaxis_transform(), clip_on=False))
            label = ARM_TEXT[(arm, cohort)]
            if arm == "direct":
                for c, x0 in zip(cols, xs):  # name each direct column inside its bar slot unless it is an accepted run
                    if c["project"] == proj and c["arm"] == arm and c["direct"] != "accepted":
                        ax_top.text(x0 + 0.5, 0.5, f'direct: {c["direct"]}', ha="center", va="center", fontsize=5.8,
                                    color=st.INK["secondary"], rotation=90, transform=ax_top.get_xaxis_transform())
                ax_top.text((a + b) / 2, 1.14, label, ha="center", va="center", fontsize=6.5, color=st.INK["secondary"],
                            transform=ax_top.get_xaxis_transform())
            else:
                ax_top.text((a + b) / 2, 1.14, label, ha="center", va="center", fontsize=6.5, color=st.INK["secondary"],
                            transform=ax_top.get_xaxis_transform())
    del top_y

    # slot panel
    y = 0
    sep_rows = []
    for m in mod_names:
        for s in groups[m]:
            for c, x0 in zip(cols, xs):
                if c["state"] is None:
                    ax_slot.add_patch(Rectangle((x0 + pad, y + pad), 1 - 2 * pad, 1 - 2 * pad, facecolor=st.INK["surface"],
                                                edgecolor=st.INK["axis"], linewidth=0.3))
                    state = "no_record"
                else:
                    state = c["state"][s]
                    ax_slot.add_patch(Rectangle((x0 + pad, y + pad), 1 - 2 * pad, 1 - 2 * pad, facecolor=COLOR[state]))
                    if state == "caveat_only":
                        ax_slot.plot(x0 + 0.5, y + 0.5, marker="o", markersize=2.2, color=st.INK["primary"], linestyle="none")
                rows_main.append({"project": c["project"], "arm": c["arm"], "cohort": c["cohort"], "rep": c["rep"],
                                  "path": c["path"] or "", "agent_runtime": c["runtime"], "module": m, "slot": s, "state": state})
            y += 1
        sep_rows.append(y)
    ax_slot.set_ylim(y, 0)
    ax_slot.set_yticks([i + 0.5 for i in range(y)]); ax_slot.set_yticklabels(all_slots, fontsize=6.5)
    ax_slot.tick_params(axis="y", length=0)
    for r in sep_rows[:-1]:
        ax_slot.axhline(r, color=st.INK["axis"], linewidth=0.6, zorder=3)
    y0 = 0
    for m in mod_names:
        n = len(groups[m])
        # one-row groups (Variables, FileCollection) would collide: nudge them apart and shrink
        nudge = 0.0 if n > 1 else (-0.45 if m == "Variables" else 0.45)
        ax_slot.text(-0.175, y0 + n / 2 + nudge, m, ha="right", va="center", fontsize=7 if n > 1 else 6,
                     fontweight="bold", color=st.INK["secondary"], transform=ax_slot.get_yaxis_transform(), clip_on=False)
        y0 += n
    ax_slot.tick_params(axis="y", pad=2)
    for sp in ax_slot.spines.values():
        sp.set_visible(False)
    ax_slot.set_xticks([x0 + 0.5 for c, x0 in zip(cols, xs) if c["rep"]])
    ax_slot.set_xticklabels([str(c["rep"]) for c in cols if c["rep"]], fontsize=6)
    ax_slot.tick_params(axis="x", length=0)
    ax_slot.set_xlabel("generation replicate", fontsize=7.5)
    ax_slot.set_title("Slot state per record", pad=4, fontsize=8.5)
    # vertical separators between projects and arms through both heat panels
    for ax in (ax_mod, ax_slot):
        prev = None
        for c, x0 in zip(cols, xs):
            key = (c["project"], c["arm"], c["cohort"])
            if prev is not None and prev != key:
                ax.axvline(x0 - (0.45 if prev[0] != key[0] else 0.175), color=st.INK["grid"] if prev[0] == key[0] else st.INK["axis"],
                           linewidth=0.6, zorder=0)
            prev = key

    # legend + color scale
    handles = [Patch(facecolor=COLOR["populated"], label="populated (non-empty value)"),
               plt.Line2D([], [], marker="o", markersize=2.5, color=st.INK["primary"], markerfacecolor=st.INK["primary"],
                          linestyle="none", label="caveat-only: slot absent, named in a source_caveats entry"),
               Patch(facecolor=COLOR["empty"], label="empty (slot absent)"),
               Patch(facecolor=st.INK["surface"], edgecolor=st.INK["axis"], linewidth=0.5, label="no record in this set")]
    handles[1] = (Patch(facecolor=COLOR["caveat_only"]), handles[1])
    from matplotlib.legend_handler import HandlerTuple
    leg = fig.legend(handles=handles, labels=[h.get_label() if not isinstance(h, tuple) else h[1].get_label() for h in handles],
                     loc="lower left", bbox_to_anchor=(0.19, 0.008), ncol=2, fontsize=7,
                     handler_map={tuple: HandlerTuple(ndivide=1, pad=0)}, handlelength=1.6, columnspacing=1.6)
    del leg
    cax = fig.add_axes([0.80, 0.017, 0.16, 0.012])
    import numpy as np
    cax.imshow(np.linspace(0, 1, 64)[None, :], aspect="auto", cmap=cmap)
    cax.set_yticks([]); cax.set_xticks([0, 63]); cax.set_xticklabels(["0", "1"], fontsize=6.5); cax.tick_params(length=0, pad=1)
    for sp in cax.spines.values():
        sp.set_visible(False)
    cax.set_title("module fraction populated", fontsize=6.5, pad=2, loc="left", fontweight="normal", color=st.INK["secondary"])
    direct_note = ("registered, no accepted run" if n_direct == 0 and n_disq == 0 else
                   f"{n_direct} accepted run(s), {n_disq} disqualified / not in corpus")
    fig.text(0.19, 0.958, "arm strip: blue = API arm (Messages SDK via CBORG), orange = agentic arm (Claude Code via proxy), "
             f"aqua = direct arm (Claude Code, subscription): {direct_note}; arm of every drawn record verified from its "
             "provenance agent_runtime",
             fontsize=6.8, color=st.INK["secondary"], ha="left", va="bottom")
    fig.suptitle("Populated D4D schema content per record, by module and by Dataset slot",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=0.99)
    basis = (f"Record set: {n_api} API-arm full records (reference rescore 2026-09-12 manifest, v7 + v8) + {n_agentic} agentic-arm "
             f"full records (2026-08-28 claudecode-generic-v6 rep1-3); direct arm: {direct_note}; {len(all_slots)} Dataset slots "
             f"from data_sheets_schema_all.yaml, grouped by the module file defining each slot's range class")
    st.save(fig, "fig02_content_coverage", {"main": rows_main, "modules": rows_mod, "records": rows_rec}, basis)
    print(f"records {n_rec}, slots {len(all_slots)}, groups " + ", ".join(f"{m}={len(g)}" for m, g in groups.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
