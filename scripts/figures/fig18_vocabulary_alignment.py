#!/usr/bin/env python
"""Vocabulary alignment and structural friction: where D4D reuses external vocabularies,
where it mints its own terms, and where the structural mapping records a type conflict.

Record sets (two tables, never summed; they overlap in subject matter):

  A. src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv, the
     dated "comprehensive" SSSOM table (header `# Date:`; one row per D4D slot name, every
     subject written `Dataset.<slot>` even when the slot belongs to a nested class). Read with
     the csv module after dropping `#` header lines, because 34 cells are quoted multi-line
     strings. The current schema's slot names that the table does not list are added as an
     explicit "not in table" column, so they are shown and not silently dropped.
  B. data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv, the structural SSSOM
     table (D4D class/slot -> property of the FAIRSCAPE example RO-Crate). Every row is
     classified; the rows that are not plain exactMatch (the type-incompatible ones and the
     composition-path ones) are listed in full, grouped only where every column except the
     class and path agrees.

Panel A: rows are schema modules, columns are target vocabularies split by predicate and
mapping status; bubble area is the number of distinct slot names. Each slot name has exactly
one row in the comprehensive table, so it lands in exactly one column.

Target vocabulary: from `object_source` (namespace URI), falling back to the `object_id`
prefix when the source is empty or recorded as "unknown" (one row: `rdf:ID`). The two must
agree where both exist, or the script stops. Rows without an object form the "no target"
group, split by `mapping_status` (free_text / recommended / unmapped).

Module attribution (a documented rule, not a property of the table): the files are the root
schema data_sheets_schema.yaml and the modules it imports (D4D_Base_import + 12 topical
modules). For each slot name, in order:
  1. an induced slot of class Dataset (current schema, SchemaView) whose range is a class or
     enum declared in one of those files -> that file;
  2. otherwise a top-level `slots:` declaration in exactly one file -> that file, even when
     other files declare the same name as a class attribute (currently download_url, format,
     media_type: top-level in D4D_Base_import, attributes in D4D_Distribution; the list is
     computed at run time and printed in the figure note);
  3. otherwise a class `attributes:` declaration in exactly one file -> that file;
  4. otherwise declared in several files -> an explicit "several modules" row (the files are
     listed in the slots CSV);
  5. otherwise "not in current schema" (drawn if it ever occurs).
The slots CSV lists every declaring file per slot name, so each override can be checked.

Panel B: `type_compatible` is the generator's own rule-based check
(src/semantic_exchange/generate_structural_mapping.py, `_validate_type_compatibility`:
cardinality and a few literal/relationship heuristics), and composition-path rows are written
with `type_compatible=True` by construction rather than checked. Both are labeled as such.
Composition-path rows are also written with `d4d_range=None, d4d_multivalued=False`, which
`to_sssom_row` serializes as "string" / "False": placeholders, not schema data. The figure
labels them as generator defaults and prints the current schema's range and cardinality
(SchemaView, looked up at run time along the path) beside them; both go to the CSVs.

Caveat: these are mapping assertions, not tested interoperability. Nothing here round-trips a
record through RO-Crate. Every plotted number is computed from the files at run time and
exported to CSV.
"""
from __future__ import annotations

import csv
import io
import math
import re
import subprocess
import sys
import textwrap
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

sys.path.insert(0, str(st.ROOT / "src"))
from data_sheets_schema.schema_view import shared_view  # noqa: E402

KEY = "fig18_vocabulary_alignment"
COMP = st.ROOT / "src" / "data_sheets_schema" / "semantic_exchange" / "d4d_rocrate_sssom_comprehensive.tsv"
STRUCT = st.ROOT / "data" / "semantic_exchange" / "d4d_rocrate_structural_mapping.sssom.tsv"
SCHEMA_DIR = st.ROOT / "src" / "data_sheets_schema" / "schema"
ROOT_SCHEMA = SCHEMA_DIR / "data_sheets_schema.yaml"

# target vocabulary: (label, namespace URI, CURIE prefix), fixed order
VOCABS = [
    ("schema.org", "https://schema.org/", "schema"),
    ("Croissant RAI", "http://mlcommons.org/croissant/RAI/", "rai"),
    ("FAIRSCAPE EVI", "https://w3id.org/EVI#", "evi"),
    ("DCAT", "https://www.w3.org/ns/dcat#", "dcat"),
    ("PROV-O", "http://www.w3.org/ns/prov#", "prov"),
    ("RDF", "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdf"),
    ("D4D namespace (D4D-only)", "https://w3id.org/bridge2ai/data-sheets-schema/", "d4d"),
]
NO_TARGET = "no target recorded"
NOT_IN_TABLE = "not in table"
PRED_ORDER = ["skos:exactMatch", "skos:closeMatch", "skos:relatedMatch", "skos:narrowMatch",
              "skos:broadMatch", "semapv:UnmappableProperty", "semapv:UnmappedProperty", "(absent)"]
STATUS_ORDER = ["mapped", "novel_d4d", "recommended", "free_text", "unmapped", "(absent)"]
PRED_SHORT = {"skos:exactMatch": "exact", "skos:closeMatch": "close", "skos:relatedMatch": "related",
              "skos:narrowMatch": "narrow", "skos:broadMatch": "broad"}
# predicates own categorical slots 4-8 (slots 1-3 belong to the arms), in fixed order
PRED_COLOR = {"skos:exactMatch": st.SERIES[3], "skos:closeMatch": st.SERIES[4],
              "skos:relatedMatch": st.SERIES[5], "skos:narrowMatch": st.SERIES[6],
              "skos:broadMatch": st.SERIES[7]}
MODULE_LABEL = {"data_sheets_schema": "Root (Dataset, DataSubset)", "D4D_Base_import": "Base (shared slots)",
                "D4D_Data_Governance": "Data Governance"}
SEVERAL = "several modules"
NOTE_WRAP = 41                         # characters per line of the panel A side notes
ABSENT_MOD = "not in current schema"


# ---------------------------------------------------------------- inputs
def read_sssom(path: Path) -> tuple[list[dict], dict[str, str]]:
    """Rows of an SSSOM TSV (csv module: quoted multi-line cells) plus `# key: value` header lines."""
    text = path.read_text()
    header, body = {}, []
    for line in text.splitlines(keepends=True):
        if line.startswith("#") and not body:
            m = re.match(r"#\s*([^:]+):\s*(.*)", line)
            if m:
                header[m.group(1).strip()] = m.group(2).strip()
            continue
        body.append(line)
    rows = list(csv.DictReader(io.StringIO("".join(body)), delimiter="\t"))
    return rows, header


def git_last_date(path: Path) -> str:
    try:
        return subprocess.check_output(["git", "log", "-1", "--format=%ad", "--date=short", "--", str(path.relative_to(st.ROOT))],
                                       cwd=st.ROOT, text=True).strip() or "uncommitted"
    except Exception:  # pragma: no cover
        return "unknown"


def vocabulary(row: dict) -> str:
    obj, src = row["object_id"].strip(), row["object_source"].strip()
    if not obj:
        assert not src, row
        return NO_TARGET
    prefix = obj.split(":", 1)[0] if ":" in obj else ""
    by_src = next((v for v, uri, _ in VOCABS if src == uri), None)
    by_pfx = next((v for v, _, p in VOCABS if prefix == p), None)
    if by_src and by_pfx:
        assert by_src == by_pfx, (row["d4d_schema_path"], src, obj)
    return by_src or by_pfx or f"other ({prefix or src})"


# ---------------------------------------------------------------- module attribution
def module_attribution():
    root_doc = yaml.safe_load(ROOT_SCHEMA.read_text())
    files = ["data_sheets_schema"] + [i for i in root_doc["imports"] if not i.startswith("linkml:")]
    docs = {f: (yaml.safe_load((SCHEMA_DIR / f"{f}.yaml").read_text()) or {}) for f in files}
    owner, top, attr = defaultdict(set), defaultdict(set), defaultdict(set)
    for f, d in docs.items():
        for kind in ("classes", "enums"):
            for c in (d.get(kind) or {}):
                owner[c].add(f)
        for c, cd in (d.get("classes") or {}).items():
            for a in ((cd or {}).get("attributes") or {}):
                attr[a].add(f)
        for s in (d.get("slots") or {}):
            top[s].add(f)
    dup = {c: fs for c, fs in owner.items() if len(fs) > 1}
    assert not dup, f"class/enum declared in several root-reachable files: {dup}"
    view = shared_view(ROOT_SCHEMA)
    ds_range = {s.name: str(s.range) for s in view.class_induced_slots("Dataset")}
    names = set(top) | set(attr)

    def attribute(slot: str) -> tuple[str, str, str, str]:
        """(module, rule, declaring files if several, every declaring file)."""
        every = "; ".join(sorted(top.get(slot, set()) | attr.get(slot, set())))
        rng = ds_range.get(slot)
        if rng in owner:
            return next(iter(owner[rng])), "Dataset slot; file declaring its range " + rng, "", every
        if len(top.get(slot, ())) == 1:
            return next(iter(top[slot])), "top-level slot declaration", "", every
        if len(attr.get(slot, ())) == 1:
            return next(iter(attr[slot])), "class attribute declaration", "", every
        if every:
            return SEVERAL, "declared in several files", every, every
        return ABSENT_MOD, "not declared in the current schema", "", every
    return files, names, attribute


# ---------------------------------------------------------------- panel A data
def panel_a():
    rows, header = read_sssom(COMP)
    files, names, attribute = module_attribution()
    paths = [r["d4d_schema_path"] for r in rows]
    assert len(paths) == len(set(paths)), "duplicate subject paths in comprehensive table"
    assert all(p.startswith("Dataset.") for p in paths)
    slot_rows = []
    for r in rows:
        slot = r["d4d_schema_path"].split(".", 1)[1]
        mod, rule, several, every = attribute(slot)
        slot_rows.append({"slot": slot, "subject_path": r["d4d_schema_path"], "module_file": mod,
                          "attribution_rule": rule, "declaring_files_if_several": several,
                          "all_declaring_files": every,
                          "vocabulary": vocabulary(r), "predicate_id": r["predicate_id"],
                          "mapping_status": r["mapping_status"], "mapping_justification": r["mapping_justification"],
                          "confidence": r["confidence"], "object_id": r["object_id"], "object_source": r["object_source"],
                          "in_comprehensive_table": True})
    in_table = {s["slot"] for s in slot_rows}
    for slot in sorted(names - in_table):
        mod, rule, several, every = attribute(slot)
        slot_rows.append({"slot": slot, "subject_path": "", "module_file": mod, "attribution_rule": rule,
                          "declaring_files_if_several": several, "all_declaring_files": every,
                          "vocabulary": NOT_IN_TABLE,
                          "predicate_id": "(absent)", "mapping_status": "(absent)", "mapping_justification": "",
                          "confidence": "", "object_id": "", "object_source": "", "in_comprehensive_table": False})
    not_in_schema = sorted(in_table - names)
    # columns: (vocabulary, predicate, status) in fixed order, only combinations that occur
    vorder = [v for v, _, _ in VOCABS] + sorted({s["vocabulary"] for s in slot_rows if s["vocabulary"].startswith("other")}) + [NO_TARGET, NOT_IN_TABLE]
    combos = {(s["vocabulary"], s["predicate_id"], s["mapping_status"]) for s in slot_rows}
    for v, p, m in combos:
        assert p in PRED_ORDER and m in STATUS_ORDER, (v, p, m)
    cols = sorted(combos, key=lambda c: (vorder.index(c[0]), PRED_ORDER.index(c[1]), STATUS_ORDER.index(c[2])))
    mods = [f for f in files if f != "data_sheets_schema"] + ["data_sheets_schema"]
    present_mods = {s["module_file"] for s in slot_rows}
    mods = [m for m in mods if m in present_mods] + [m for m in (SEVERAL, ABSENT_MOD) if m in present_mods]
    # names declared in more than one file that a single-file rule still assigned (the note lists them)
    overrides = OrderedDict()
    for rule in ("top-level slot declaration", "class attribute declaration"):
        overrides[rule] = sorted(s["slot"] for s in slot_rows
                                 if s["attribution_rule"] == rule and ";" in s["all_declaring_files"])
    return rows, header, slot_rows, cols, mods, not_in_schema, overrides


def col_label(c) -> str:
    v, p, m = c
    if v == NOT_IN_TABLE:
        return "no table row"
    if p == "semapv:UnmappableProperty":
        return "free text"
    if p == "semapv:UnmappedProperty":
        return "suggested, no target" if m == "recommended" else "unmapped"
    lab = PRED_SHORT[p]
    if m == "recommended":
        return f"{lab} (suggested)"
    if m == "novel_d4d":
        return f"{lab} (novel term)"
    if v.startswith("D4D"):
        return f"{lab} (mapped)"
    return lab


GROUP_HEADER = {"Croissant RAI": "Croissant\nRAI", "FAIRSCAPE EVI": "FAIRSCAPE\nEVI", "RDF": "RDF*",
                "D4D namespace (D4D-only)": "D4D-only\nnamespace", NO_TARGET: "no target\nrecorded",
                NOT_IN_TABLE: "absent\nfrom table"}


def marker_style(c) -> dict:
    """Filled = curated (mapped / novel), hollow ring = suggested; gray = no target; square = no table row."""
    v, p, m = c
    if v == NOT_IN_TABLE:
        return dict(marker="s", facecolor="none", edgecolor=st.INK["secondary"], linewidth=1.2)
    if p == "semapv:UnmappableProperty":
        return dict(marker="o", facecolor=st.INK["axis"], edgecolor=st.INK["surface"], linewidth=0.8)
    if p == "semapv:UnmappedProperty":
        if m == "recommended":
            return dict(marker="o", facecolor="none", edgecolor=st.INK["muted"], linewidth=1.4)
        return dict(marker="o", facecolor=st.INK["muted"], edgecolor=st.INK["surface"], linewidth=0.8)
    color = PRED_COLOR[p]
    if m == "recommended":
        return dict(marker="o", facecolor="none", edgecolor=color, linewidth=1.6)
    return dict(marker="o", facecolor=color, edgecolor=st.INK["surface"], linewidth=0.8)


# ---------------------------------------------------------------- panel B data
def schema_path_shape(view, cls: str, path: str) -> tuple[str, bool, bool]:
    """Walk a dotted slot path from class `cls` in the current schema:
    (range of the last slot, last slot multivalued, any slot on the path multivalued)."""
    cur, any_mv, rng, mv = cls, False, "", False
    for seg in path.split("."):
        s = view.induced_slot(seg, cur)
        rng, mv = str(s.range), bool(s.multivalued)
        any_mv = any_mv or mv
        cur = rng
    return rng, mv, any_mv


def card(mv) -> str:
    return "multivalued" if mv in (True, "True") else "single-valued"


def panel_b():
    rows, _ = read_sssom(STRUCT)
    view = shared_view(ROOT_SCHEMA)
    classified = []
    for r in rows:
        tc = r["type_compatible"].strip()
        assert tc in ("True", "False"), r["subject_id"]
        if tc == "False":
            cls = "type_compatible False (flagged)"
        elif r["composition_path"].strip():
            cls = "composition path (True by construction)"
        else:
            cls = "direct, type_compatible True"
        rec = {**{k: r[k] for k in ("subject_id", "subject_category", "subject_label", "predicate_id",
                                     "object_id", "confidence", "mapping_justification", "d4d_subject_range",
                                     "subject_multivalued", "rocrate_value_type", "type_compatible",
                                     "composition_path", "warnings")}, "structural_class": cls}
        # The panel B table shows the 20 non-direct rows; for those, the current schema's range and
        # cardinality are looked up so the written values (placeholders on composition rows) can be
        # compared with it. Direct rows are not looked up here.
        if cls.startswith("direct"):
            rec.update(schema_lookup="not looked up (direct row)", schema_range_current="",
                       schema_multivalued_current="", schema_path_has_multivalued_slot="",
                       written_values_are="")
        else:
            srng, smv, sany = schema_path_shape(view, r["subject_category"], r["subject_label"])
            rec.update(schema_lookup="current schema (SchemaView), along subject_label from subject_category",
                       schema_range_current=srng, schema_multivalued_current=str(smv),
                       schema_path_has_multivalued_slot=str(sany),
                       written_values_are=("generator default (range None -> 'string', multivalued False)"
                                           if r["composition_path"].strip() else "from the schema slot"))
        classified.append(rec)
    summary = Counter((c["structural_class"], c["predicate_id"]) for c in classified)
    # group the non-direct rows where every column except class and path agrees
    groups = OrderedDict()
    for c in classified:
        if c["structural_class"].startswith("direct"):
            continue
        root = c["subject_label"].split(".", 1)[0]
        k = (c["structural_class"], root, c["predicate_id"], c["object_id"], c["confidence"], c["mapping_justification"],
             c["d4d_subject_range"], c["subject_multivalued"], c["rocrate_value_type"], c["type_compatible"], c["warnings"])
        g = groups.setdefault(k, {"classes": [], "paths": [], "n_rows": 0, "root_schema": set()})
        if c["subject_category"] not in g["classes"]:
            g["classes"].append(c["subject_category"])
        if c["composition_path"] and c["composition_path"] not in g["paths"]:
            g["paths"].append(c["composition_path"])
        g["n_rows"] += 1
        srng, smv, _ = schema_path_shape(view, c["subject_category"], root)
        g["root_schema"].add((srng, smv))
    for k, g in groups.items():
        assert len(g["root_schema"]) == 1, (k[1], g["root_schema"])   # same shape on every class in the group
        g["root_schema"] = next(iter(g["root_schema"]))
    return rows, classified, summary, groups


# ---------------------------------------------------------------- draw
SEG_ORDER = ["type_compatible False (flagged)", "composition path (True by construction)", "direct, type_compatible True"]


def draw_panel_a(fig, ax, slot_rows, cols, mods, n_comp, comp_date, not_in_schema, overrides):
    cell = Counter((s["module_file"], (s["vocabulary"], s["predicate_id"], s["mapping_status"])) for s in slot_rows)
    cell_slots = defaultdict(list)
    for s in slot_rows:
        cell_slots[(s["module_file"], (s["vocabulary"], s["predicate_id"], s["mapping_status"]))].append(s["slot"])
    maxc = max(cell.values())
    ncol, nrow = len(cols), len(mods)
    DMAX = 24.0                                      # points, diameter of the largest bubble
    k_area = DMAX ** 2 / maxc                        # scatter `s` is area in pt^2, so area is proportional to count
    rows = []
    for yi, mod in enumerate(mods):
        for xi, c in enumerate(cols):
            n = cell.get((mod, c), 0)
            if not n:
                continue
            ms = marker_style(c)
            # scatter `s` is the marker's bounding-box area: a circle fills pi/4 of it, a square all
            # of it, so squares are scaled by pi/4 to give equal counts equal drawn area
            area = k_area * n * (math.pi / 4 if ms["marker"] == "s" else 1.0)
            ax.scatter([xi], [yi], s=area, marker=ms["marker"], facecolors=ms["facecolor"],
                       edgecolors=ms["edgecolor"], linewidths=ms["linewidth"], zorder=3)
            d = area ** 0.5                          # diameter (circle) or side (square), points
            if d >= 14:
                dark_fill = ms["facecolor"] in (st.SERIES[5], st.SERIES[6], st.INK["muted"])
                ax.text(xi, yi, str(n), ha="center", va="center", fontsize=6.6, zorder=4,
                        color=st.INK["surface"] if dark_fill else st.INK["primary"])
            else:
                ax.annotate(str(n), (xi, yi), xytext=(d / 2 + 1.5, 0), textcoords="offset points",
                            ha="left", va="center", fontsize=6.2, color=st.INK["secondary"], zorder=4)
            rows.append({"module_file": mod, "module": MODULE_LABEL.get(mod, mod.replace("D4D_", "")),
                         "vocabulary": c[0], "predicate_id": c[1], "mapping_status": c[2], "column": col_label(c),
                         "distinct_slots": n, "x": xi, "y": yi, "marker": ms["marker"],
                         "marker_s_pt2": round(area, 3), "slots": "; ".join(sorted(cell_slots[(mod, c)]))})
    # totals row: every slot name sits in exactly one cell, so a column total is a count of distinct slot names
    col_tot = Counter((s["vocabulary"], s["predicate_id"], s["mapping_status"]) for s in slot_rows)
    for xi, c in enumerate(cols):
        ax.text(xi, nrow, str(col_tot[c]), ha="center", va="center", fontsize=6.8, color=st.INK["secondary"])
        rows.append({"module_file": "(all)", "module": "column total", "vocabulary": c[0], "predicate_id": c[1],
                     "mapping_status": c[2], "column": col_label(c), "distinct_slots": col_tot[c], "x": xi, "y": nrow,
                     "marker": "", "marker_s_pt2": "", "slots": ""})
    row_tot = Counter(s["module_file"] for s in slot_rows)
    row_in = Counter(s["module_file"] for s in slot_rows if s["in_comprehensive_table"])
    ylabels = []
    for m in mods:
        extra = row_tot[m] - row_in[m]
        ylabels.append(f"{MODULE_LABEL.get(m, m.replace('D4D_', ''))}  ({row_in[m]}" + (f" + {extra})" if extra else ")"))
    n_in, n_out = sum(row_in.values()), sum(row_tot.values()) - sum(row_in.values())
    ylabels.append(f"all modules  ({n_in} + {n_out})")
    ax.set_yticks(range(nrow + 1)); ax.set_yticklabels(ylabels, fontsize=7.8, color=st.INK["primary"])
    ax.get_yticklabels()[-1].set_color(st.INK["secondary"]); ax.get_yticklabels()[-1].set_style("italic")
    ax.set_xticks(range(ncol)); ax.set_xticklabels([col_label(c) for c in cols], rotation=90, fontsize=7.0,
                                                   color=st.INK["secondary"])
    ax.set_xlim(-0.6, ncol - 0.4); ax.set_ylim(nrow + 0.5, -0.5)
    ax.tick_params(length=0, pad=4)
    for sp in ax.spines.values():
        sp.set_visible(False)
    for yi in range(nrow + 1):
        ax.axhline(yi - 0.5, color=st.INK["grid"] if yi < nrow else st.INK["axis"], linewidth=0.5 if yi < nrow else 0.8, zorder=0)
    groups_x = OrderedDict()
    for xi, c in enumerate(cols):
        groups_x.setdefault(c[0], []).append(xi)
    for v, xs in groups_x.items():
        x0, x1 = min(xs) - 0.42, max(xs) + 0.42
        if min(xs) > 0:
            ax.axvline(min(xs) - 0.5, color=st.INK["axis"], linewidth=0.7, zorder=0)
        ax.text((x0 + x1) / 2, -0.78, GROUP_HEADER.get(v, v), ha="center", va="bottom", fontsize=7.3,
                fontweight="bold", color=st.INK["primary"], clip_on=False, linespacing=1.05)
        ax.plot([x0, x1], [-0.62, -0.62], color=st.INK["axis"], linewidth=0.8, clip_on=False)
    ax.annotate(f"A   Schema module x target vocabulary: distinct D4D slot names, comprehensive mapping table "
                f"({n_comp} rows, header date {comp_date})", xy=(0.01, 1.0), xycoords=("figure fraction", "axes fraction"),
                xytext=(0, 40), textcoords="offset points", fontsize=9.3, fontweight="bold", color=st.INK["primary"],
                ha="left", va="bottom")
    # legends to the right
    lx = 1.02
    lh = [Line2D([], [], marker="o", linestyle="none", markersize=7, markerfacecolor=PRED_COLOR[p],
                 markeredgecolor=st.INK["surface"], label=f"skos:{PRED_SHORT[p]}Match")
          for p in PRED_ORDER[:5] if any(c[1] == p for c in cols)]
    absent_preds = [p for p in PRED_ORDER[:5] if not any(c[1] == p for c in cols)]
    lh += [Line2D([], [], marker="o", linestyle="none", markersize=7, markerfacecolor="none",
                  markeredgecolor=st.INK["secondary"], markeredgewidth=1.4, label="hollow ring: suggested\n(mapping_status recommended)"),
           Line2D([], [], marker="o", linestyle="none", markersize=7, markerfacecolor=st.INK["axis"],
                  markeredgecolor=st.INK["surface"], label="free text, no URI needed\n(unmappable)"),
           Line2D([], [], marker="o", linestyle="none", markersize=7, markerfacecolor=st.INK["muted"],
                  markeredgecolor=st.INK["surface"], label="unmapped, needs research"),
           Line2D([], [], marker="s", linestyle="none", markersize=7, markerfacecolor="none",
                  markeredgecolor=st.INK["secondary"], markeredgewidth=1.2, label="slot in current schema,\nno row in the table")]
    leg1 = ax.legend(handles=lh, loc="upper left", bbox_to_anchor=(lx, 1.0), title="color: predicate\nfill: curated / suggested",
                     title_fontsize=7.6, fontsize=7.2, handletextpad=0.5, labelspacing=0.8, alignment="left")
    leg1.get_title().set_color(st.INK["secondary"])
    ax.add_artist(leg1)
    sizes = [n for n in (1, 5, 10, 20, 40) if n <= maxc]
    sh = [Line2D([], [], marker="o", linestyle="none", markersize=(k_area * n) ** 0.5, markerfacecolor=st.INK["axis"],
                 markeredgecolor=st.INK["surface"], label=f"{n} slot name{'s' if n > 1 else ''}") for n in sizes]
    leg2 = ax.legend(handles=sh, loc="upper left", bbox_to_anchor=(lx, 0.585), title="area: distinct slot names",
                     title_fontsize=7.6, fontsize=7.2, labelspacing=1.2, borderpad=0.6, handletextpad=1.0, alignment="left")
    leg2.get_title().set_color(st.INK["secondary"])
    note = ""
    if absent_preds:
        note += "; ".join("skos:" + PRED_SHORT[p] + "Match" for p in absent_preds) + ": no rows asserted.\n\n"
    note += textwrap.fill("* RDF: object_source is recorded as 'unknown'; the vocabulary is read from the rdf: "
                          "prefix of rdf:ID.", NOTE_WRAP) + "\n\n"
    note += textwrap.fill("Row labels: slot names with a table row (+ current schema slot names without one).", NOTE_WRAP) + "\n\n"
    top_wins = overrides.get("top-level slot declaration") or []
    attr_wins = overrides.get("class attribute declaration") or []
    rule_txt = ("Module attribution is a rule-based heuristic, in order: (1) for a Dataset slot, the file declaring "
                "its range; (2) otherwise the one file with a top-level slots: declaration, which wins over class "
                "attributes in other files")
    rule_txt += f" ({', '.join(top_wins)})" if top_wins else ""
    rule_txt += "; (3) otherwise the one file declaring it as a class attribute"
    rule_txt += f" ({', '.join(attr_wins)} also have top-level declarations in several files)" if attr_wins else ""
    rule_txt += "; (4) names still ambiguous form their own row. Declaring files are listed in the slots CSV."
    note += textwrap.fill(rule_txt, NOTE_WRAP) + "\n\n"
    note += textwrap.fill(f"{len(not_in_schema)} table slot names are not in the current schema." if not_in_schema
                          else "Every table slot name is in the current schema.", NOTE_WRAP)
    ax.text(lx + 0.005, 0.385, note, transform=ax.transAxes, fontsize=6.7, color=st.INK["secondary"],
            ha="left", va="top", linespacing=1.25)
    return rows


def draw_panel_b(fig, axb, axt, classified, summary, groups, n_struct, struct_date):
    seg = OrderedDict()
    for cls in SEG_ORDER[::-1]:
        for p in PRED_ORDER:
            if summary.get((cls, p)):
                seg[(cls, p)] = summary[(cls, p)]
    assert sum(seg.values()) == n_struct
    x = 0
    bar_rows = []
    for (cls, p), n in seg.items():
        flagged = cls.startswith("type_compatible False")
        color = st.STATUS["serious"] if flagged else PRED_COLOR.get(p, st.INK["muted"])
        axb.barh(0, n, left=x, height=0.62, color=color, edgecolor=st.INK["surface"], linewidth=1.5)
        lab = f"{n} rows  {p.replace('skos:', '')}, {cls}"
        if n >= 0.4 * n_struct:
            axb.text(x + n / 2, 0, lab, ha="center", va="center", fontsize=7.3, color=st.INK["primary"])
        else:
            above = flagged
            axb.annotate(lab, (x + n / 2, 0.31 if above else -0.31), xytext=(x - 3, 0.95 if above else -0.95),
                         ha="right", va="bottom" if above else "top", fontsize=7.3, color=st.INK["primary"],
                         arrowprops=dict(arrowstyle="-", color=st.INK["muted"], lw=0.6, shrinkA=0, shrinkB=0),
                         annotation_clip=False)
        bar_rows.append({"structural_class": cls, "predicate_id": p, "rows": n, "left": x})
        x += n
    axb.set_xlim(0, n_struct); axb.set_ylim(-0.5, 0.5)
    axb.set_yticks([]); axb.set_xticks([0, n_struct]); axb.tick_params(axis="x", labelsize=7)
    axb.spines["left"].set_visible(False)
    axb.set_xlabel("structural mapping rows", fontsize=7.4, labelpad=1)
    axb.annotate(f"B   Structural mapping table (D4D class / slot mapped to a property of the FAIRSCAPE example RO-Crate): "
                 f"all {n_struct} rows, file last changed {struct_date}", xy=(0.01, 1.0),
                 xycoords=("figure fraction", "axes fraction"), xytext=(0, 34), textcoords="offset points",
                 fontsize=9.3, fontweight="bold", color=st.INK["primary"], ha="left", va="bottom")

    axt.axis("off")
    head = ["D4D subject (classes)", "D4D range, cardinality\nas written (current schema)", "predicate, confidence,\njustification",
            "RO-Crate object\n(value type)", "composition path", "type_compatible\n(generator heuristic)", "warning"]
    order = sorted(groups.items(), key=lambda kv: (SEG_ORDER.index(kv[0][0]), kv[0][1]))
    cells, table_rows = [], []
    for k, g in order:
        cls, root, pred, obj, conf, just, rng, mv, vt, tc, warn = k
        paths = g["paths"]
        if paths:
            rest = [p[len(root):] for p in paths if p != root and p.startswith(root + ".")]
            other = [p for p in paths if p != root and not p.startswith(root + ".")]
            path_txt = ", ".join(([root] if root in paths else []) + rest + other)
            path_txt = textwrap.fill(path_txt, 44)
        else:
            path_txt = "none recorded"
        n_paths = len(paths)
        subj = root + (f" + {n_paths - 1} nested paths" if n_paths > 1 else "")
        subj += f"\n{', '.join(g['classes'])}; {g['n_rows']} rows"
        tc_txt = "False (flagged)" if tc == "False" else ("True, set by construction" if paths else "True")
        srng, smv = g["root_schema"]
        if paths:
            # composition rows carry the generator's placeholders, not the slot's range/cardinality
            rng_txt = (f"not recorded: generator\ndefault \"{rng}, {card(mv)}\"\n"
                       f"({root} in schema:\n{srng}, {card(smv)})")
        elif (srng, str(smv)) == (rng, mv):
            rng_txt = f"{rng}, {card(mv)}\n(schema agrees)"
        else:
            rng_txt = f"{rng}, {card(mv)}\n(schema: {srng}, {card(smv)})"
        cells.append([subj, rng_txt,
                      f"{pred.replace('skos:', '')} {conf},\n{just.replace('semapv:', '')}", f"{obj}\n({vt})",
                      path_txt, tc_txt, textwrap.fill(warn, 34) if warn else "none"])
        table_rows.append({"structural_class": cls, "subject_root": root, "classes": "; ".join(g["classes"]),
                           "predicate_id": pred, "object_id": obj, "confidence": conf, "mapping_justification": just,
                           "d4d_subject_range": rng, "subject_multivalued": mv,
                           "written_range_cardinality_are": ("generator default (range None -> 'string', multivalued "
                                                             "False), not schema data" if paths else "from the schema slot"),
                           "schema_range_current": srng, "schema_multivalued_current": str(smv),
                           "schema_lookup": f"current schema (SchemaView): slot {root} on {', '.join(g['classes'])}",
                           "rocrate_value_type": vt,
                           "type_compatible": tc, "composition_paths": "; ".join(paths), "warnings": warn,
                           "rows": g["n_rows"]})
    tbl = axt.table(cellText=cells, colLabels=head, loc="upper left", cellLoc="left", colLoc="left",
                    bbox=[0.0, 0.0, 1.0, 1.0], colWidths=[0.155, 0.135, 0.12, 0.12, 0.2, 0.11, 0.16])
    tbl.auto_set_font_size(False); tbl.set_fontsize(7.0)
    for (r, c), cl in tbl.get_celld().items():
        cl.set_edgecolor(st.INK["grid"]); cl.set_linewidth(0.5)
        cl.PAD = 0.04
        cl.get_text().set_color(st.INK["primary"] if r else st.INK["secondary"])
        if r == 0:
            cl.get_text().set_fontweight("bold")
        elif c == 5 and cells[r - 1][5].startswith("False"):
            cl.set_facecolor(st.STATUS["serious"])
    n_flag = sum(g["n_rows"] for k, g in groups.items() if k[0].startswith("type_compatible False"))
    n_comp = sum(g["n_rows"] for k, g in groups.items() if k[0].startswith("composition"))
    note = (f"All {n_flag} rows flagged type_compatible False and all {n_comp} composition-path rows, grouped where only "
            f"the class (and path) differ; the other {n_struct - n_flag - n_comp} rows are listed in the CSV. "
            f"type_compatible is the generator's rule-based check (cardinality / literal-vs-relationship), and "
            f"composition-path rows are written True without a check.")
    comp_groups = [(k, g) for k, g in groups.items() if g["paths"]]
    written = {(k[6], k[7]) for k, _ in comp_groups}
    if comp_groups:
        assert len(written) == 1, written
        w_rng, w_mv = next(iter(written))
        note += (f" They also carry the generator's range and cardinality defaults (\"{w_rng}\", {card(w_mv)}) "
                 f"instead of the slot's, and its cardinality check was never applied to them")
        # compare each composition root's schema shape with the shape of the flagged cardinality rows
        flag_shapes = {(k[7], k[8]) for k, _ in groups.items()
                       if k[0].startswith("type_compatible False") and "Cardinality mismatch" in k[10]}
        flag_roots = [k[1] for k, _ in groups.items()
                      if k[0].startswith("type_compatible False") and "Cardinality mismatch" in k[10]]
        parts = []
        for k, g in comp_groups:
            srng, smv = g["root_schema"]
            same = (str(smv), k[8]) in flag_shapes
            parts.append(f"in the current schema {k[1]} is {srng}, {card(smv)}, mapped to a {k[8]} value"
                         + (f": the shape that got {' and '.join(flag_roots)} flagged" if same else ""))
        note += ": " + "; ".join(parts) + "."
    axt.text(0.0, 1.03, textwrap.fill(note, 205), transform=axt.transAxes, fontsize=7.2,
             color=st.INK["secondary"], ha="left", va="bottom", wrap=False)
    return bar_rows, table_rows


def main() -> int:
    st.apply()
    comp_rows, comp_header, slot_rows, cols, mods, not_in_schema, overrides = panel_a()
    s_rows, classified, summary, groups = panel_b()
    n_comp, n_struct = len(comp_rows), len(s_rows)
    declared_total = comp_header.get("Total attributes")
    if declared_total is not None:
        assert int(declared_total) == n_comp, (declared_total, n_comp)
    comp_date = comp_header.get("Date", "?")[:10]
    struct_date = git_last_date(STRUCT)
    n_absent = sum(1 for s in slot_rows if not s["in_comprehensive_table"])
    n_imports = len(module_attribution()[0]) - 1

    fig = plt.figure(figsize=(11.6, 13.0))
    gsa = fig.add_gridspec(1, 1, left=0.175, right=0.79, top=0.878, bottom=0.43)
    gsb = fig.add_gridspec(2, 1, height_ratios=[0.3, 2.0], hspace=0.9, left=0.035, right=0.975, top=0.292, bottom=0.035)
    ax = fig.add_subplot(gsa[0])
    main_rows = draw_panel_a(fig, ax, slot_rows, cols, mods, n_comp, comp_date, not_in_schema, overrides)
    axb, axt = fig.add_subplot(gsb[0]), fig.add_subplot(gsb[1])
    bar_rows, table_rows = draw_panel_b(fig, axb, axt, classified, summary, groups, n_struct, struct_date)

    fig.suptitle("Where D4D reuses external vocabularies, mints its own terms, and meets structural friction",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=0.985)
    fig.text(0.01, 0.962, textwrap.fill(
        "Mapping assertions only, not tested interoperability: no record was round-tripped through RO-Crate. "
        f"Panel A counts distinct slot names in the comprehensive table ({n_comp} rows); panel B counts rows of the "
        f"structural table ({n_struct} rows). The two tables overlap and are not summed.", 175),
        fontsize=7.6, color=st.INK["secondary"], ha="left", va="top")
    basis = (f"Record sets: d4d_rocrate_sssom_comprehensive.tsv ({n_comp} rows, header date {comp_date}) + {n_absent} "
             f"current-schema slot names absent from it; d4d_rocrate_structural_mapping.sssom.tsv ({n_struct} rows); "
             f"modules = root schema + its {n_imports} imports")
    st.save(fig, KEY, {"main": main_rows, "slots": slot_rows, "structural_rows": classified,
                       "structural_summary": bar_rows, "structural_groups": table_rows}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
