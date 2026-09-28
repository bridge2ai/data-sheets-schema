#!/usr/bin/env python
"""Sole-source dependence: how much of each reference-rescore record is cited to one source document only.

Record set: the 24 reference-rescore records (notes/reference_rescore_2026-09-12_cborg_runtime
manifest.json jobs[].input): API-arm full records (agent runtime "Claude API (direct)" via CBORG),
4 projects x v7/v8 prompt x 3 generation replicates. The record list, the path joins and the
receipted-field rule are taken from scripts/figures/fig06_evidence_coverage.py by import.

Method, per record:
1. Read the run's coverage receipt (data/d4d_concatenated/<method>_core/<label>/<PROJECT>_coverage_receipt.yaml)
   and the chunk manifest as it stood at the run's commit (git show <provenance repo.commit>:
   data/preprocessed/chunks/<PROJECT>_chunks.yaml). The manifest text is checked byte-for-byte
   against the sha256 the provenance recorded, and the bundle_md5 of receipt, manifest and
   provenance must agree; a run that fails either check stops the script.
2. Every `extracted` receipt entry gives (field path, snippet) for one chunk; the chunk manifest maps
   the chunk to its source file and data/preprocessed/source_manifest.yaml maps the file to a
   document id and source_type. A field path is kept only if it still names a non-empty value in the
   final record (fig06's `resolves`); paths dropped by audit/repair are counted and excluded.
3. For each kept field path, the set of documents whose chunks cite it. A sole-source path of D is
   one whose citing set is exactly {D}, i.e. one that would lose every citation if D's receipt
   entries were deleted. Sole-source share of D = (# kept field paths cited by D only) /
   (# kept field paths in the record). Shares are kept unrounded; medians are taken over the
   unrounded shares and values are rounded only when written to CSV.
4. Plot per project: one row per source document (all manifest documents, grouped by source_type),
   one dot per run (circle v7, square v8) in a fixed lane per run (v7 above the row center, v8
   below, replicates 1-3 moving outward), and a vertical bar, drawn under the dots, at the median
   of the project's 6 runs. The lane step is checked to be at least one marker diameter, so equal
   values never overlap. A hollow dot marks a run in which no kept field path cites that document
   at all (share 0 by absence); a filled dot at 0 means the document is cited but never as the
   only source.

A dagger marks a document that another document's chunk was declared `redundant_with` in at least
one run. The receipt itemizes no fields for redundant chunks, so the redundant document may carry
some of the same fields and the marked document's sole-source share may overstate dependence.

Caveats: this is citation dependence inside the generating model's own receipts, not verified factual
support (the receipt check verifies that snippets occur in the bundle, not that they support the
value) and not a regeneration experiment without the document. Field paths are counted at receipt
path granularity (e.g. funders[0] and funders[0].notes are two paths), not by value or importance.
The bundle preamble chunk is not a source document; any field cited from it is counted separately.
"""
from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
import textwrap
from collections import defaultdict
from pathlib import Path
from statistics import median

import matplotlib.pyplot as plt
import yaml
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402
from scripts.figures import fig06_evidence_coverage as f6  # noqa: E402

STEM = "fig19_source_dependence"
COHORTS = f6.COHORTS
MARK = {"v7": "o", "v8": "s"}               # same cohort shapes as fig04
PREAMBLE = "<preamble>"
# Replicate lanes, in row units. Lane of (cohort, rep): sign * (LANE_GAP + (rep - 1) * LANE_STEP),
# v7 above the row center (sign -1, y axis is inverted), v8 below (+1).
ROW_IN = 0.42                               # inches per document row
LANE_GAP, LANE_STEP = 0.09, 0.14            # half-gap between cohorts; step between replicates
MS = 3.4                                    # marker size (pt)
EDGE_FILLED, EDGE_HOLLOW = 0.4, 0.8         # surface ring on filled markers; outline of hollow markers
MEDIAN_HALF, MEDIAN_LW = 0.46, 1.2          # median bar half-height (rows) and width (pt)
CSV_DP = 6                                  # decimals for shares in the exported CSVs (export only)


def lane(cohort: str, rep: int) -> float:
    return (-1 if cohort == "v7" else 1) * (LANE_GAP + (rep - 1) * LANE_STEP)


def check_lane_geometry() -> str:
    """Stop if two adjacent lanes are closer than one marker diameter (incl. edge): tied values would overlap."""
    pt_per_row = ROW_IN * 72
    glyph = MS + max(EDGE_FILLED, EDGE_HOLLOW)
    step_pt, gap_pt = LANE_STEP * pt_per_row, 2 * LANE_GAP * pt_per_row
    outer = (LANE_GAP + 2 * LANE_STEP) * pt_per_row + glyph / 2
    between_rows = pt_per_row - 2 * outer
    if min(step_pt, gap_pt) < glyph or between_rows <= 0:
        raise SystemExit(f"lane geometry: step {step_pt:.2f} pt, cohort gap {gap_pt:.2f} pt, glyph {glyph:.2f} pt, "
                         f"gap between rows {between_rows:.2f} pt")
    return (f"lane geometry: replicate step {step_pt:.2f} pt, cohort gap {gap_pt:.2f} pt >= marker {glyph:.2f} pt; "
            f"{between_rows:.2f} pt clear between adjacent rows' outer markers")


# ----------------------------------------------------------------------------- loading
def verified_manifest(commit: str, project: str, prov: dict) -> tuple[dict, str]:
    """Chunk manifest at the run's commit via fig06's loader, then checked against the provenance sha256."""
    manifest, ref = f6.chunk_manifest_at(commit, project)
    if "@HEAD" in ref:
        raise SystemExit(f"{project} {commit[:10]}: chunk manifest not available at the run commit")
    rel = f"data/preprocessed/chunks/{project}_chunks.yaml"
    raw = subprocess.check_output(["git", "show", f"{commit}:{rel}"], cwd=st.ROOT)
    if hashlib.sha256(raw).hexdigest() != prov["inputs"]["chunks"]["sha256"]:
        raise SystemExit(f"{project} {commit[:10]}: chunk manifest sha256 differs from provenance")
    return manifest, ref


def analyse():
    docs = f6.source_docs()                  # project -> processed_file -> {id, source_type}
    per_record, per_doc = [], []
    for r in f6.records():
        receipt = yaml.safe_load(r["receipt_path"].read_text())
        prov = yaml.safe_load(r["provenance_path"].read_text())
        manifest, ref = verified_manifest(prov["repo"]["commit"], r["project"], prov)
        if not (receipt["bundle_md5"] == manifest["bundle_md5"] == prov["inputs"]["bundle_md5"]):
            raise SystemExit(f'{r["label"]} {r["project"]}: bundle_md5 disagreement')
        chunk_doc = {c["id"]: docs[r["project"]].get(c["source"], {"id": c["source"], "source_type": "not in manifest"})["id"]
                     for c in manifest["chunks"]}
        final = yaml.safe_load((st.ROOT / r["input"]).read_text())
        citing = defaultdict(set)            # field path -> documents citing it
        entries = unresolved = 0
        redundancy_targets = set()           # documents another document's chunk declared itself redundant with
        for e in receipt["chunks"]:
            if e.get("status") == "redundant_with":
                own = chunk_doc[e["id"]]
                redundancy_targets |= {chunk_doc[t] for t in e.get("chunks") or [] if chunk_doc[t] != own}
            if e.get("status") != "extracted" or e["id"] not in chunk_doc:
                continue
            for x in e.get("extracted") or []:
                slot = str(x.get("slot", "")).strip()
                if not slot:
                    continue
                entries += 1
                if not f6.resolves(final, slot):
                    unresolved += 1
                    continue
                citing[slot].add(chunk_doc[e["id"]])
        n = len(citing)
        n_single = sum(1 for s in citing.values() if len(s) == 1)
        preamble_id = docs[r["project"]][PREAMBLE]["id"]
        base = {"label": r["label"], "method": r["method"], "project": r["project"], "cohort": r["cohort"], "rep": r["rep"]}
        per_record.append({**base, "receipt_extracted_entries": entries, "entries_unresolved_in_final": unresolved,
                           "receipted_field_paths": n, "paths_with_one_citing_document": n_single,
                           "share_with_one_citing_document": n_single / n,
                           "paths_cited_by_preamble": sum(1 for s in citing.values() if preamble_id in s),
                           "doc_path_pairs": sum(len(s) for s in citing.values()),
                           "chunk_manifest": ref, "commit": prov["repo"]["commit"]})
        for f, d in docs[r["project"]].items():
            if f == PREAMBLE and not any(preamble_id in s for s in citing.values()):
                continue                     # the preamble is not a source document; kept only if cited
            cited_any = sum(1 for s in citing.values() if d["id"] in s)
            sole = sum(1 for s in citing.values() if s == {d["id"]})
            per_doc.append({**base, "document_id": d["id"], "source_type": d["source_type"], "processed_file": f,
                            "field_paths_citing": cited_any, "field_paths_sole_source": sole,
                            "receipted_field_paths": n, "sole_source_share": sole / n,
                            "cited_in_run": cited_any > 0,
                            "redundant_chunk_of_other_document_points_here": d["id"] in redundancy_targets})
    return per_record, per_doc


def crosscheck_fig06(per_record) -> str:
    """Compare document-field pair counts with fig06's CSV (same join), if that CSV is present."""
    path = st.OUT / "fig06_evidence_coverage.csv"
    if not path.exists():
        return "fig06 CSV absent; cross-check skipped"
    ref = {(row["label"], row["project"]): row for row in csv.DictReader(path.open())}
    bad = [r["label"] + " " + r["project"] for r in per_record
           if int(ref[(r["label"], r["project"])]["receipt_slots_cited"]) != r["doc_path_pairs"]
           or int(ref[(r["label"], r["project"])]["receipt_slots_unresolved_in_final"]) != r["entries_unresolved_in_final"]]
    if bad:
        raise SystemExit(f"document-field pair counts differ from fig06 for {bad}")
    return f"doc-field pairs and unresolved counts agree with fig06 CSV for {len(per_record)} of {len(per_record)} records"


# ----------------------------------------------------------------------------- drawing
def doc_order(per_doc, project):
    """Documents grouped by source_type (fig06 order), then by descending median share."""
    rows = [d for d in per_doc if d["project"] == project]
    ids = {}
    for d in rows:
        ids.setdefault(d["document_id"], d["source_type"])
    med = {i: median(d["sole_source_share"] for d in rows if d["document_id"] == i) for i in ids}
    tkey = lambda t: f6.TYPE_ORDER.index(t) if t in f6.TYPE_ORDER else len(f6.TYPE_ORDER)
    order = sorted(ids, key=lambda i: (tkey(ids[i]), -med[i], i))
    return order, ids, med


def draw_panel(fig, rect, per_doc, per_record, project, xmax, n_runs_total):
    ax = fig.add_axes(rect)
    order, types, med = doc_order(per_doc, project)
    rows = [d for d in per_doc if d["project"] == project]
    recs = [r for r in per_record if r["project"] == project]
    flagged = {d["document_id"] for d in rows if d["redundant_chunk_of_other_document_points_here"]}
    plotted = []
    for yi, doc in enumerate(order):
        pts = [d for d in rows if d["document_id"] == doc]
        for d in pts:
            # one fixed lane per run (see lane()), so equal values stay visible and separate
            dy = lane(d["cohort"], d["rep"])
            filled = d["cited_in_run"]
            ax.plot(d["sole_source_share"] * 100, yi + dy, marker=MARK[d["cohort"]], markersize=MS, linestyle="none",
                    markerfacecolor=st.ARM_COLOR["api"] if filled else st.INK["surface"],
                    markeredgecolor=st.INK["surface"] if filled else st.ARM_COLOR["api"],
                    markeredgewidth=EDGE_FILLED if filled else EDGE_HOLLOW, zorder=4 if filled else 4.5)
            plotted.append({**d, "median_share_of_project_runs": med[doc], "y_row": yi, "y_lane_offset": round(dy, 3)})
        m = med[doc] * 100
        # median bar under the markers, so a marker sitting on it still reads as filled or hollow
        ax.plot([m, m], [yi - MEDIAN_HALF, yi + MEDIAN_HALF], color=st.INK["primary"], linewidth=MEDIAN_LW,
                solid_capstyle="butt", zorder=3)
    top = max(order, key=lambda i: med[i])     # named in the panel header instead of an in-plot label
    # group separators and source_type labels (placed after the tick labels are measured)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{d} †" if d in flagged else d for d in order], fontsize=7, color=st.INK["primary"])
    ax.set_ylim(len(order) - 0.5, -0.5)
    ax.set_xlim(-1.2, xmax)
    ax.set_xticks(range(0, int(xmax) + 1, 10))
    ax.set_xticklabels([f"{t}%" for t in range(0, int(xmax) + 1, 10)])
    ax.set_xlabel("share of the run's receipted field paths cited by this document only", fontsize=7.5)
    st.hairline_grid(ax, "x")
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    groups, start = [], 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and types[order[end + 1]] == types[order[start]]:
            end += 1
        groups.append((start, end, types[order[start]]))
        start = end + 1
    for s, e, _ in groups[1:]:
        ax.axhline(s - 0.5, color=st.INK["axis"], linewidth=0.6, zorder=1)
    single = [r["share_with_one_citing_document"] * 100 for r in recs]
    paths = [r["receipted_field_paths"] for r in recs]
    header = (project.replace("_", "-"),
              f"{len(recs)} runs; {min(paths)}\u2013{max(paths)} receipted field paths per run, "
              f"{min(single):.0f}\u2013{max(single):.0f}% of them cited by exactly one document",
              f"highest median sole-source share: {top}, {med[top] * 100:.0f}% of a run's receipted field paths")
    return ax, groups, plotted, header


def place_type_labels(fig, ax, groups) -> float:
    """Source-type labels in a column left of the document tick labels, with a bracket per group.
    Returns the left edge of the leftmost type label, in figure pixels."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bbox = ax.get_window_extent(renderer)
    labels_x0 = min(t.get_window_extent(renderer).x0 for t in ax.get_yticklabels())
    x_br = (labels_x0 - 10 - bbox.x0) / bbox.width      # bracket 10 px left of the widest document label
    left = bbox.x0
    for s, e, t in groups:
        ax.plot([x_br, x_br], [s - 0.32, e + 0.32], transform=ax.get_yaxis_transform(), color=st.INK["muted"],
                linewidth=0.8, clip_on=False, solid_capstyle="butt")
        txt = ax.text(x_br - 6 / bbox.width, (s + e) / 2, t, transform=ax.get_yaxis_transform(), ha="right",
                      va="center", fontsize=6.8, color=st.INK["secondary"], clip_on=False)
        left = min(left, txt.get_window_extent(renderer).x0)
    return left


def main() -> int:
    st.apply()
    per_record, per_doc = analyse()
    check = crosscheck_fig06(per_record)
    print(check)
    print(check_lane_geometry())
    xmax = (int(max(d["sole_source_share"] for d in per_doc) * 10) + 1) * 10 + 2
    n_rows = {p: len({d["document_id"] for d in per_doc if d["project"] == p}) for p in st.PROJECTS}

    layout = {0: ["AI_READI", "CHORUS"], 1: ["CM4AI", "VOICE"]}
    rh = ROW_IN                                 # inches per document row
    head, foot, gap = 0.66, 0.52, 0.16          # header band above, x-axis band below, gap between panels (in)
    col_h = {c: sum(n_rows[p] * rh + head + foot for p in ps) + gap * (len(ps) - 1) for c, ps in layout.items()}
    W = 13.2
    H = 0.55 + max(col_h.values()) + 0.35       # suptitle band + tallest column + footer band
    left_cols = [3.0, 9.55]                     # axes left edge (in) per column
    aw = 3.4                                    # axes width (in)
    fig = plt.figure(figsize=(W, H))
    plotted, axes = [], {}
    bottoms = {}
    for col, projects in layout.items():
        y = H - 0.55
        for p in projects:
            h = n_rows[p] * rh
            y -= head
            rect = [left_cols[col] / W, (y - h) / H, aw / W, h / H]
            ax, groups, pts, header = draw_panel(fig, rect, per_doc, per_record, p, xmax, len(per_record))
            axes[p] = (ax, groups, header, col)
            plotted += pts
            y -= h + foot + gap
        bottoms[col] = y + gap
    col_left = {}
    for p, (ax, groups, header, col) in axes.items():
        col_left[col] = min(col_left.get(col, 1e9), place_type_labels(fig, ax, groups))
    for p, (ax, groups, header, col) in axes.items():
        x = col_left[col] / fig.dpi / W
        y1 = ax.get_position().y1
        fig.text(x, y1 + 0.42 / H, header[0], fontsize=9.5, fontweight="bold", color=st.INK["primary"], ha="left", va="bottom")
        fig.text(x, y1 + 0.24 / H, header[1], fontsize=7.4, color=st.INK["secondary"], ha="left", va="bottom")
        fig.text(x, y1 + 0.08 / H, header[2], fontsize=7.4, color=st.INK["secondary"], ha="left", va="bottom")

    # legend + notes in the free space under the left column
    y_leg = bottoms[0] - 0.05
    x_left = col_left[0] / fig.dpi / W - 0.004
    hollow = lambda m: Line2D([], [], marker=m, markerfacecolor=st.INK["surface"], markeredgecolor=st.ARM_COLOR["api"],
                              markeredgewidth=1.0, linestyle="none", markersize=5)
    h = [Line2D([], [], marker="o", color=st.ARM_COLOR["api"], markeredgecolor=st.INK["surface"], linestyle="none",
                markersize=5, label="v7 prompt, one run (lanes above the row center, replicates 1–3 outward)"),
         Line2D([], [], marker="s", color=st.ARM_COLOR["api"], markeredgecolor=st.INK["surface"], linestyle="none",
                markersize=5, label="v8 prompt, one run (lanes below the row center, replicates 1–3 outward)"),
         (hollow("o"), hollow("s")),
         Line2D([], [], marker="|", color=st.INK["primary"], linestyle="none", markersize=10, markeredgewidth=MEDIAN_LW,
                label="median of the project's 6 runs")]
    labels = [h[0].get_label(), h[1].get_label(),
              "hollow (circle or square): no receipted field path cites the document in that run", h[3].get_label()]
    leg = fig.legend(handles=h, labels=labels, handler_map={tuple: HandlerTuple(ndivide=None, pad=0.3)},
               loc="upper left", bbox_to_anchor=(x_left, y_leg / H), ncol=1, handletextpad=0.5, handlelength=2.2,
               fontsize=7.4, title=f"{st.ARM_LABEL['api']}; rows grouped by source_type from source_manifest.yaml",
               title_fontsize=7.4, alignment="left", labelspacing=0.45)
    n_flag_docs = len({(d["project"], d["document_id"]) for d in per_doc if d["redundant_chunk_of_other_document_points_here"]})
    n_flag_runs = len({(d["label"], d["project"]) for d in per_doc if d["redundant_chunk_of_other_document_points_here"]})
    unresolved = sum(r["entries_unresolved_in_final"] for r in per_record)
    entries = sum(r["receipt_extracted_entries"] for r in per_record)
    preamble = sum(r["paths_cited_by_preamble"] for r in per_record)
    note = (f"† {n_flag_docs} documents: in {n_flag_runs} of {len(per_record)} runs a chunk of another document was declared "
            "redundant_with a chunk of this document. Receipts itemize no fields for redundant chunks, so these shares may "
            "overstate dependence. A filled dot at 0% is a document cited in that run but never as the only source. "
            "A sole-source path is one that would lose every citation if this document's receipt entries were deleted; "
            "this measures citation dependence in the run's own coverage receipt, not verified factual support, and is "
            "not a regeneration experiment. "
            f"{unresolved} of {entries} receipt field entries no longer resolve in the final record after audit/repair and are "
            f"excluded; {preamble} kept paths cite the bundle preamble. Chunk manifests read at each run's commit, sha256-matched to provenance.")
    fig.canvas.draw()                          # place the note under the legend's measured bottom edge
    leg_bottom = leg.get_window_extent(fig.canvas.get_renderer()).y0 / fig.dpi
    fig.text(x_left + 0.004, (leg_bottom - 0.10) / H, "\n".join(textwrap.wrap(note, 132)), fontsize=6.9,
             color=st.INK["secondary"], ha="left", va="top")

    fig.suptitle("Which source documents are the only cited source for a record's fields? Sole-source share per document, reference rescore records",
                 x=0.012, ha="left", fontsize=11, fontweight="bold", y=0.985)
    basis = (f"Record set: reference rescore 2026-09-12 (CBORG runtime), {len(per_record)} API-arm full records "
             "(4 projects x v7/v8 x 3 replicates); coverage receipts, chunk manifests at run commits (sha256 = provenance), "
             "source_manifest.yaml; receipt field paths resolving in the final record")
    order_cols = ["label", "method", "project", "cohort", "rep", "document_id", "source_type", "processed_file",
                  "field_paths_citing", "field_paths_sole_source", "receipted_field_paths", "sole_source_share",
                  "median_share_of_project_runs", "cited_in_run", "redundant_chunk_of_other_document_points_here", "y_row",
                  "y_lane_offset"]
    rnd = lambda v: round(v, CSV_DP) if isinstance(v, float) else v   # rounding happens only here, on export
    main_rows = [{k: rnd(p[k]) for k in order_cols} for p in plotted]
    medians = []
    for p in st.PROJECTS:
        order, types, med = doc_order(per_doc, p)
        for d in order:
            vals = [x["sole_source_share"] for x in per_doc if x["project"] == p and x["document_id"] == d]
            medians.append({"project": p, "document_id": d, "source_type": types[d], "n_runs": len(vals),
                            "median_sole_source_share": rnd(med[d]), "min": rnd(min(vals)), "max": rnd(max(vals)),
                            "runs_cited": sum(1 for x in per_doc if x["project"] == p and x["document_id"] == d and x["cited_in_run"]),
                            "runs_flagged_redundancy_target": sum(1 for x in per_doc if x["project"] == p and x["document_id"] == d
                                                                  and x["redundant_chunk_of_other_document_points_here"])})
    st.save(fig, STEM, {"main": main_rows, "medians": medians, "records": [{k: rnd(v) for k, v in r.items()} for r in per_record]}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
