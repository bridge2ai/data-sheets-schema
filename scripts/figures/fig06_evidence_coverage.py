#!/usr/bin/env python
"""#2297: evidence coverage for the reference rescore records.

Record set: the 24 reference-rescore records (notes/reference_rescore_2026-09-12_cborg_runtime
manifest.json jobs[].input), API-arm full records, 4 projects x v7/v8 x 3 replicates.

Artifacts read per record (all under data/d4d_concatenated/<method>_core/<label>/):
- <PROJECT>_coverage_receipt.yaml  - the run's coverage receipt (bundle_md5 + one closed entry per
  chunk: extracted [{slot, snippet}], redundant_with, nothing_relevant, duplicate_of);
- <PROJECT>_provenance.yaml        - `receipts` block (chunk totals by status, populated slots with /
  without a receipt) written by `d4d receipts check`, and `repo.commit` for the run;
- the chunk manifest as it stood at the run's commit (git show <commit>:data/preprocessed/chunks/
  <PROJECT>_chunks.yaml), which maps chunk id -> source document (`source`), keyed by bundle_md5;
- data/preprocessed/source_manifest.yaml, which maps the document file to its id and source_type.

Panel A: chunk dispositions per run (bar length = manifest chunk count). The API arm reads the whole
bundle from context, so "partially opened" is not observable here: a chunk is either receipted with a
closed status or has no entry. Panel B: receipted fields by schema module x source document, per
project, mean over the 6 runs of that project; only receipt slots that still resolve in the final
record are counted. Panel C: populated slots by receipt status after audit/repair (from provenance).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

ARCH = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime"
CONCAT = st.ROOT / "data" / "d4d_concatenated"
SCHEMA_DIR = st.ROOT / "src" / "data_sheets_schema" / "schema"
SOURCE_MANIFEST = st.ROOT / "data" / "preprocessed" / "source_manifest.yaml"

DISPOSITIONS = ["extracted", "redundant_with", "nothing_relevant", "duplicate_of"]
DISP_LABEL = {"extracted": "extracted (slot + verbatim snippet)", "redundant_with": "redundant with another chunk",
              "nothing_relevant": "nothing relevant (reason given)", "duplicate_of": "duplicate of another chunk",
              "no_entry": "no receipt entry (unreviewed)"}
DISP_COLOR = {"extracted": st.ORDINAL[8], "redundant_with": st.ORDINAL[5], "nothing_relevant": st.ORDINAL[2],
              "duplicate_of": st.ORDINAL[0]}
SUPPORT = ["with_receipt", "added_after_receipt", "never_receipted", "exempt"]
SUPPORT_LABEL = {"with_receipt": "receipted (snippet attested in the bundle)",
                 "added_after_receipt": "added after the receipt (audit/repair), no receipt",
                 "never_receipted": "populated, never receipted",
                 "exempt": "exempt (commentary, own identifiers)"}
SUPPORT_COLOR = {"with_receipt": st.SERIES[0], "added_after_receipt": st.SERIES[3],
                 "never_receipted": st.SERIES[1], "exempt": st.INK["axis"]}
MODULE_ORDER = ["Metadata (Information)", "Motivation", "Composition", "Collection", "Preprocessing", "Uses",
                "Distribution", "Data governance", "Maintenance", "Ethics", "Human", "Variables",
                "FileCollection", "Dataset (top level)"]
TYPE_ORDER = ["RO-Crate", "structured metadata", "data resource", "documentation", "license", "DUA", "IRB",
              "publication", "preprint", "white paper", "NIH project page", "tutorial",
              "historical data release", "historical documentation", "bundle preamble"]
COHORTS = ["v7", "v8"]


# ----------------------------------------------------------------------------- loading
def records():
    manifest = json.loads((ARCH / "manifest.json").read_text())
    out = []
    for inp in sorted({j["input"] for j in manifest["jobs"]}):
        parts = Path(inp).parts
        method, label, fname = parts[2], parts[3], parts[4]
        project = fname.replace("_d4d.yaml", "")
        cohort = re.search(r"-(v\d+)_rep", label).group(1)
        rep = int(re.search(r"_rep(\d+)$", label).group(1))
        core = CONCAT / f"{method}_core" / label
        out.append({"input": inp, "method": method, "label": label, "project": project, "cohort": cohort,
                    "rep": rep, "core": core,
                    "receipt_path": core / f"{project}_coverage_receipt.yaml",
                    "provenance_path": core / f"{project}_provenance.yaml"})
    return out


def chunk_manifest_at(commit: str, project: str) -> tuple[dict, str]:
    rel = f"data/preprocessed/chunks/{project}_chunks.yaml"
    try:
        text = subprocess.check_output(["git", "show", f"{commit}:{rel}"], cwd=st.ROOT, text=True,
                                       stderr=subprocess.DEVNULL)
        return yaml.safe_load(text), f"{rel}@{commit[:10]}"
    except subprocess.CalledProcessError:
        return yaml.safe_load((st.ROOT / rel).read_text()), f"{rel}@HEAD (run commit unavailable)"


def slot_modules() -> dict[str, str]:
    """Top-level Dataset attribute -> schema module, derived from the merged schema and the module files."""
    merged = yaml.safe_load((SCHEMA_DIR / "data_sheets_schema_all.yaml").read_text())
    cls_mod, slot_mod = {}, {}
    for f in sorted(SCHEMA_DIR.glob("*.yaml")):
        if f.name.endswith("_all.yaml"):
            continue
        s = yaml.safe_load(f.read_text()) or {}
        for cn in (s.get("classes") or {}):
            cls_mod.setdefault(cn, f.name)
        for sn in (s.get("slots") or {}):
            slot_mod.setdefault(sn, f.name)

    def pretty(fname: str | None) -> str:
        if fname is None:
            return "Dataset (top level)"
        if fname == "data_sheets_schema.yaml":
            return "Dataset (top level)"
        name = fname.replace("D4D_", "").replace(".yaml", "").replace("_", " ")
        return {"Base import": "Metadata (Information)"}.get(name, name)

    out = {}
    ds = merged["classes"]["Dataset"]
    for n, v in (ds.get("attributes") or {}).items():
        rng = (v or {}).get("range")
        out[n] = pretty(cls_mod.get(rng) or slot_mod.get(n))
    for s in merged["classes"]["Information"]["slots"]:
        out.setdefault(s, pretty(slot_mod.get(s)))
    return out


def source_docs() -> dict[str, dict[str, dict]]:
    m = yaml.safe_load(SOURCE_MANIFEST.read_text())
    out = {}
    for project in st.PROJECTS:
        docs = {}
        for d in m["projects"][project]:
            docs[d["processed_file"]] = {"id": d["id"], "source_type": d["source_type"]}
        docs["<preamble>"] = {"id": "bundle preamble", "source_type": "bundle preamble"}
        out[project] = docs
    return out


PATH_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def resolves(record: dict, path: str) -> bool:
    """True if a receipt slot path (e.g. creators[0].affiliations[1].name) names a non-empty value."""
    node = record
    for m in PATH_TOKEN.finditer(path):
        key, idx = m.group(1), m.group(2)
        if key is not None:
            if not isinstance(node, dict) or key not in node:
                return False
            node = node[key]
        else:
            i = int(idx)
            if not isinstance(node, list) or i >= len(node):
                return False
            node = node[i]
    return node not in (None, "", [], {})


# ----------------------------------------------------------------------------- analysis
def analyse():
    mods = slot_modules()
    docs = source_docs()
    rows, support_rows, attr_long = [], [], []
    for r in records():
        receipt = yaml.safe_load(r["receipt_path"].read_text())
        prov = yaml.safe_load(r["provenance_path"].read_text())
        manifest, manifest_ref = chunk_manifest_at(prov["repo"]["commit"], r["project"])
        md5_ok = receipt["bundle_md5"] == manifest["bundle_md5"] == prov["inputs"]["bundle_md5"]
        by_id = {c["id"]: c for c in manifest["chunks"]}
        entries = {e["id"]: e for e in receipt["chunks"]}
        counts = Counter()
        for cid in by_id:
            e = entries.get(cid)
            counts[e["status"] if e and e.get("status") in DISPOSITIONS else "no_entry"] += 1
        extra = sorted(set(entries) - set(by_id))
        pr = prov["receipts"]
        # cross-check the receipt file against the provenance receipts block
        assert pr["chunks"]["total"] == manifest["chunk_count"], r["label"]
        for d in DISPOSITIONS:
            assert pr["chunks"]["by_status"][d] == counts[d], (r["label"], r["project"], d)
        final = yaml.safe_load(Path(st.ROOT / r["input"]).read_text())
        cited, unresolved = Counter(), 0
        seen = set()
        for cid, e in entries.items():
            if e.get("status") != "extracted" or cid not in by_id:
                continue
            src = by_id[cid]["source"]
            doc = docs[r["project"]].get(src, {"id": src, "source_type": "not in manifest"})
            for x in e.get("extracted") or []:
                slot = str(x.get("slot", "")).strip()
                if not slot:
                    continue
                if not resolves(final, slot):
                    unresolved += 1
                    continue
                key = (slot, doc["id"])
                if key in seen:           # one field cited twice from the same document counts once
                    continue
                seen.add(key)
                top = PATH_TOKEN.match(slot).group(1)
                cited[(mods.get(top, "Dataset (top level)"), doc["id"], doc["source_type"])] += 1
        for (module, doc_id, stype), n in sorted(cited.items()):
            attr_long.append({"label": r["label"], "project": r["project"], "cohort": r["cohort"], "rep": r["rep"],
                              "module": module, "document_id": doc_id, "source_type": stype, "fields": n})
        sl = pr["slots"]
        assert sl["with_receipt"] + sl["added_after_receipt"] + sl["never_receipted"] + sl["exempt"] == sl["populated"], r["label"]
        base = {"label": r["label"], "method": r["method"], "project": r["project"], "cohort": r["cohort"], "rep": r["rep"]}
        rows.append({**base, "chunk_count": manifest["chunk_count"], **{d: counts[d] for d in DISPOSITIONS},
                     "no_entry": counts["no_entry"], "receipt_entries_not_in_manifest": len(extra),
                     "provenance_reviewed": pr["chunks"]["reviewed"], "bundle_md5": receipt["bundle_md5"],
                     "md5_receipt_manifest_provenance_agree": md5_ok, "chunk_manifest": manifest_ref,
                     "receipt_snippets_total": pr["snippets"]["total"], "receipt_snippets_verified": pr["snippets"]["verified"],
                     "receipt_slots_cited": sum(cited.values()), "receipt_slots_unresolved_in_final": unresolved,
                     "receipt": str(r["receipt_path"].relative_to(st.ROOT)),
                     "provenance": str(r["provenance_path"].relative_to(st.ROOT))})
        support_rows.append({**base, "populated": sl["populated"], **{k: sl[k] for k in SUPPORT},
                             "receiptable": sl["receiptable"], "value_changed_after_receipt": sl["value_changed_after_receipt_count"]})
    return rows, support_rows, attr_long


# ----------------------------------------------------------------------------- drawing
def row_layout(rows):
    """y position per record, grouped project > cohort > replicate, with group gaps."""
    ys, y = {}, 0.0
    ticks, labels, headers = [], [], []
    for proj in st.PROJECTS:
        headers.append((y - 0.8, proj.replace("_", "-")))
        for cohort in COHORTS:
            for rep in (1, 2, 3):
                key = (proj, cohort, rep)
                if any((r["project"], r["cohort"], r["rep"]) == key for r in rows):
                    ys[key] = y
                    ticks.append(y); labels.append(f"{cohort} rep {rep}")
                    y += 1.0
            y += 0.35
        y += 1.0
    return ys, ticks, labels, headers, y


def stacked_barh(ax, y, parts, colors, height=0.72, gap=0.12):
    """Horizontal stack with a surface gap between segments (drawn as a surface-colored separator)."""
    x = 0.0
    for val, col in zip(parts, colors):
        if val <= 0:
            continue
        ax.barh(y, val, left=x, height=height, color=col, zorder=2)
        x += val
        ax.plot([x, x], [y - height / 2, y + height / 2], color=st.INK["surface"], linewidth=1.2, zorder=3)


def draw_panel_a(ax, rows, ys, ticks, labels, headers):
    for r in rows:
        y = ys[(r["project"], r["cohort"], r["rep"])]
        stacked_barh(ax, y, [r[d] for d in DISPOSITIONS], [DISP_COLOR[d] for d in DISPOSITIONS])
        if r["no_entry"]:
            left = sum(r[d] for d in DISPOSITIONS)
            ax.add_patch(Rectangle((left, y - 0.36), r["no_entry"], 0.72, facecolor=st.INK["surface"],
                                   edgecolor=st.INK["muted"], hatch=st.HATCH, linewidth=0.6, zorder=2))
        ax.text(r["chunk_count"] + 0.4, y, f'{r["extracted"]}/{r["chunk_count"]}', va="center", ha="left",
                fontsize=6.5, color=st.INK["secondary"])
    ax.set_yticks(ticks); ax.set_yticklabels(labels)
    ax.invert_yaxis()
    for y, text in headers:
        ax.text(-0.5, y, text, ha="right", va="center", fontsize=8, fontweight="bold", color=st.INK["secondary"],
                clip_on=False)
    ax.set_xlim(0, 31.5)
    ax.set_xlabel("source chunks in the bundle (manifest chunk count = bar length)")
    ax.set_title("A  Coverage receipt per run: chunk dispositions", pad=8)
    st.hairline_grid(ax, "x")
    ax.tick_params(axis="y", length=0)
    handles = [Rectangle((0, 0), 1, 1, facecolor=DISP_COLOR[d], label=DISP_LABEL[d]) for d in DISPOSITIONS]
    handles.append(Rectangle((0, 0), 1, 1, facecolor=st.INK["surface"], edgecolor=st.INK["muted"], hatch=st.HATCH,
                             linewidth=0.6, label=DISP_LABEL["no_entry"] + " - none in this set"))
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, -0.09), ncol=1, handlelength=1.4)


def draw_panel_c(ax, support_rows, ys, ticks, labels, headers):
    for r in support_rows:
        y = ys[(r["project"], r["cohort"], r["rep"])]
        stacked_barh(ax, y, [r[k] for k in SUPPORT], [SUPPORT_COLOR[k] for k in SUPPORT])
        ax.text(r["populated"] + 6, y, f'{100 * r["with_receipt"] / r["populated"]:.0f}%', va="center", ha="left",
                fontsize=6.5, color=st.INK["secondary"])
    ax.set_yticks(ticks); ax.set_yticklabels(labels)
    ax.invert_yaxis()
    for y, text in headers:
        ax.text(-8, y, text, ha="right", va="center", fontsize=8, fontweight="bold", color=st.INK["secondary"],
                clip_on=False)
    ax.set_xlim(0, 640)
    ax.set_xlabel("populated slots in the final record (label: share receipted)")
    ax.set_title("C  Slot support status after audit and repair (receipt check on the final record)", pad=8)
    st.hairline_grid(ax, "x")
    ax.tick_params(axis="y", length=0)
    handles = [Rectangle((0, 0), 1, 1, facecolor=SUPPORT_COLOR[k], label=SUPPORT_LABEL[k]) for k in SUPPORT]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, -0.09), ncol=1, handlelength=1.4)


def draw_panel_b(fig, gs_row, attr_long, rows):
    n_runs = Counter(r["project"] for r in rows)
    per_project = {}
    for p in st.PROJECTS:
        cell = defaultdict(float)
        col_type = {}
        for a in attr_long:
            if a["project"] != p:
                continue
            cell[(a["module"], a["document_id"])] += a["fields"]
            col_type[a["document_id"]] = a["source_type"]
        # every manifest document gets a column, cited or not
        for d in source_docs()[p].values():
            col_type.setdefault(d["id"], d["source_type"])
        cols = sorted(col_type, key=lambda d: (TYPE_ORDER.index(col_type[d]) if col_type[d] in TYPE_ORDER else 99, d))
        per_project[p] = (cell, cols, col_type)
    modules = [m for m in MODULE_ORDER if any(m == k[0] for p in st.PROJECTS for k in per_project[p][0])]
    widths = [len(per_project[p][1]) for p in st.PROJECTS]
    sub = gs_row.subgridspec(1, len(st.PROJECTS) + 1, width_ratios=widths + [1.2], wspace=0.06)
    vmax = max(v / n_runs[p] for p in st.PROJECTS for v in per_project[p][0].values())
    table = []
    axes = []
    for pi, p in enumerate(st.PROJECTS):
        cell, cols, col_type = per_project[p]
        ax = fig.add_subplot(sub[0, pi]); axes.append(ax)
        for mi, m in enumerate(modules):
            for ci, c in enumerate(cols):
                v = cell.get((m, c), 0.0) / n_runs[p]
                if v > 0:
                    k = min(len(st.SEQ) - 1, int(round((v / vmax) * (len(st.SEQ) - 1))))
                    color = st.SEQ[max(k, 1)]
                else:
                    color = st.INK["mid"]
                ax.add_patch(Rectangle((ci + 0.04, mi + 0.04), 0.92, 0.92, facecolor=color, edgecolor="none"))
                if v > 0:
                    txt = f"{v:.0f}" if v >= 9.5 else f"{v:.1f}"
                    ax.text(ci + 0.5, mi + 0.5, txt, ha="center", va="center", fontsize=5.6,
                            color=st.INK["surface"] if k >= 7 else st.INK["primary"])
                table.append({"project": p, "module": m, "document_id": c, "source_type": col_type[c],
                              "mean_fields_per_run": round(v, 2), "total_fields": int(cell.get((m, c), 0)),
                              "n_runs": n_runs[p]})
        ax.set_xlim(0, len(cols)); ax.set_ylim(len(modules), 0)
        ax.set_xticks([i + 0.5 for i in range(len(cols))])
        ax.set_xticklabels(cols, rotation=90, fontsize=6, color=st.INK["secondary"])
        ax.set_yticks([i + 0.5 for i in range(len(modules))])
        ax.set_yticklabels(modules if pi == 0 else [], fontsize=7)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        # source_type group bands above the columns
        start = 0
        while start < len(cols):
            t = col_type[cols[start]]
            end = start
            while end + 1 < len(cols) and col_type[cols[end + 1]] == t:
                end += 1
            ax.plot([start + 0.1, end + 0.9], [-0.35, -0.35], color=st.INK["muted"], linewidth=1, clip_on=False)
            ax.text((start + end + 1) / 2, -0.55, t, ha="center", va="bottom", fontsize=5.8, color=st.INK["secondary"],
                    rotation=90, clip_on=False)
            start = end + 1
        ax.set_title(f'{p.replace("_", "-")}  (n = {n_runs[p]} runs)', fontsize=8, pad=92)
    # scale key
    axk = fig.add_subplot(sub[0, len(st.PROJECTS)]); axk.axis("off")
    steps = [1, 3, 5, 7, 9, 11, 12]
    for i, k in enumerate(steps):
        axk.add_patch(Rectangle((0.15, 0.92 - i * 0.075), 0.25, 0.065, facecolor=st.SEQ[k], edgecolor="none",
                                transform=axk.transAxes))
        axk.text(0.46, 0.92 - i * 0.075 + 0.03, f"{vmax * k / (len(st.SEQ) - 1):.0f}", va="center", fontsize=6,
                 color=st.INK["secondary"], transform=axk.transAxes)
    axk.add_patch(Rectangle((0.15, 0.92 - len(steps) * 0.075), 0.25, 0.065, facecolor=st.INK["mid"], edgecolor="none",
                            transform=axk.transAxes))
    axk.text(0.46, 0.92 - len(steps) * 0.075 + 0.03, "0 (no field cites it)", va="center", fontsize=6,
             color=st.INK["secondary"], transform=axk.transAxes)
    axk.text(0.0, 1.0, "mean receipted\nfields per run", va="bottom", fontsize=6.5, color=st.INK["secondary"],
             transform=axk.transAxes)
    return table, axes


def main() -> int:
    st.apply()
    rows, support_rows, attr_long = analyse()
    fig = plt.figure(figsize=(12.4, 16.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.25], hspace=0.95, wspace=0.42, top=0.95, bottom=0.12,
                          left=0.09, right=0.98)
    ys, ticks, labels, headers, _ = row_layout(rows)
    ax_a = fig.add_subplot(gs[0, 0]); draw_panel_a(ax_a, rows, ys, ticks, labels, headers)
    ax_c = fig.add_subplot(gs[0, 1]); draw_panel_c(ax_c, support_rows, ys, ticks, labels, headers)
    table, b_axes = draw_panel_b(fig, gs[1, :], attr_long, rows)
    n_md5 = sum(1 for r in rows if not r["md5_receipt_manifest_provenance_agree"])
    unresolved = sum(r["receipt_slots_unresolved_in_final"] for r in rows)
    cited = sum(r["receipt_slots_cited"] for r in rows)
    note = (f"All {len(rows)} runs have a receipt whose bundle_md5 matches the run's provenance and the chunk manifest at "
            f"the run's commit ({n_md5} disagreements); every manifest chunk has a receipt entry. The API arm holds the whole "
            "bundle in context, so 'partially opened' is not an observable state here and the receipt is the run's own "
            "closed declaration per chunk; the receipt check verifies snippets against the bundle, not that a snippet "
            f"supports its value. Panel B counts {cited} receipt slots that resolve in the final records; {unresolved} receipt "
            "slots no longer resolve after audit/repair and are excluded (listed in the CSV).")
    y_note = ax_a.get_position().y0 - 0.105
    fig.text(0.09, y_note, "\n".join(_wrap(note, 200)), fontsize=7, color=st.INK["secondary"], ha="left", va="top")
    y_b = b_axes[0].get_position().y1 + 100 / (16.4 * 72)
    fig.text(0.09, y_b, "B  Receipted fields by schema module (rows) and source document (columns, grouped by manifest "
             "source_type), per project;\n    cell = mean over that project's runs of distinct record fields whose receipt "
             "snippet sits in a chunk of that document", fontsize=9.5, fontweight="bold", color=st.INK["primary"],
             ha="left", va="bottom")
    fig.suptitle("Evidence coverage of the reference rescore records: receipts, attribution to source documents, and slot support",
                 x=0.01, ha="left", fontsize=11.5, fontweight="bold", y=0.995)
    basis = (f"Record set: reference rescore 2026-09-12 (CBORG runtime), {len(rows)} API-arm full records "
             f"(4 projects x v7/v8 x 3 replicates); receipts, provenance receipts blocks, chunk manifests at run commits, source_manifest.yaml")
    st.save(fig, "fig06_evidence_coverage", {"main": rows, "support": support_rows, "attribution": table,
                                            "attribution_by_record": attr_long}, basis)
    return 0


def _wrap(text: str, width: int) -> list[str]:
    import textwrap
    return textwrap.wrap(text, width)


if __name__ == "__main__":
    raise SystemExit(main())
