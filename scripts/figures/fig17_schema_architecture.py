#!/usr/bin/env python
"""Idea 6 of the #2303 exploration: the D4D schema's conceptual architecture, drawn
from the schema itself, as two slide-sized figures from one script.

- fig17_schema_architecture (overview): all classes grouped by declaring file, with
  Dataset's class-valued slots and the is_a DatasetProperty links aggregated per file.
- fig17_schema_architecture_b (detail): class-level view of the slots that continue past
  Dataset's direct targets.

Both are sized so their bare render fits the #2303 deck's slide image box (about
12.4 x 5.97 in) at close to 1:1, keeping the smallest text near 7.4 pt on the slide.

Method
- Classes, their attributes, slot ranges and is_a parents come from the merged schema
  src/data_sheets_schema/schema/data_sheets_schema_all.yaml (gen-linkml output, which
  materializes every class's induced attributes, inherited ones included).
- The merged file stamps every class with the root schema's id, so it cannot say which
  file declares a class. The declaring module comes from a SchemaView over the source
  root data_sheets_schema.yaml and its imports (data_sheets_schema.schema_view.shared_view,
  SchemaView.in_schema). The script refuses to draw unless the two views agree on the
  class set, every class's induced slot names and ranges, and every is_a parent.
- A class-valued slot is an attribute whose range is a class (no slot in this schema uses
  any_of / exactly_one_of, which the script checks). Reachability is a breadth-first
  walk from Dataset over the induced class-valued slots, limited to depth 2. The script
  also takes a third step and reports what it adds (in the current schema, nothing: the
  closure ends at depth 2).
- Node area is proportional to the class's induced attribute count (all attributes a
  record of that class may carry, inherited ones included).
- Overview: every class, grouped by declaring file (files in the root schema's import
  order, classes in declaration order). Dataset's own class-valued slots (solid) and the
  is_a links to DatasetProperty (dashed) are aggregated per file as branch counts; the
  remaining is_a links and the slots with both ends in the root file are listed in the
  root and Base boxes, and the Base box states its zero Dataset-slot count.
- Detail: at class level, every class-valued slot declared on a reachable class other
  than Dataset (DataSubset declares none; it inherits Dataset's), the Dataset slots that
  lead to the classes those slots touch, DatasetProperty.used_software once where declared
  (65 classes inherit it), and Dataset's is_a lineage as dashed arrows. Every other node
  names its declaring file and is_a parent under its name. Columns are depth from Dataset;
  rows follow two deterministic barycenter passes (ties broken by file and declaration
  order), a layout heuristic that affects position only.
- The _edges CSV records, for all 217 induced class-valued slots and 74 is_a links, where
  each one appears in the two figures; the script asserts that none is left unaccounted for.
- The commit stamp in the shared footer does not cover the schema directory, so the basis
  states whether git reports uncommitted changes under src/data_sheets_schema/schema.

Record set: the current working-tree schema (version read from the merged file); no
generated D4D record is read.

Caveats
- Capability, not use: a class drawn here may be empty in every generated record.
- One schema version (the working tree); no historical versions.
- The schema directory holds 25 YAML files: the root and its 13 imported modules are
  drawn; the 2 generated merged files and 9 files the root does not import (among them
  the core exchange schema and the generation-record, telemetry, evaluation-summary,
  inventory and release-history schemas) are not. The _files CSV lists each file and its
  role, counted at run time.
- Enum-valued and type-valued slots are not drawn as edges; they are included in each
  node's attribute count, and enum-valued slots are counted separately in the main CSV.
"""
from __future__ import annotations

import math
import subprocess
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import yaml
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.path import Path as MPath
from matplotlib.textpath import TextPath

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402
from data_sheets_schema.schema_view import shared_view  # noqa: E402

SCHEMA_DIR = st.ROOT / "src" / "data_sheets_schema" / "schema"
ROOT_SCHEMA = SCHEMA_DIR / "data_sheets_schema.yaml"
MERGED = SCHEMA_DIR / "data_sheets_schema_all.yaml"
START = "Dataset"
MAX_DEPTH = 2
BASE_PARENT = "DatasetProperty"        # the is_a parent aggregated in the overview
A_KEY = "fig17_schema_architecture"
B_KEY = "fig17_schema_architecture_b"

# Figure geometry (inches). The bare render keeps the panel axes, the legend band and the
# panel title and drops the suptitle band and the footer band, so its size is about
# (FIG_W - 2 * SIDE_IN + 0.2) x (LEG_IN + GAP_IN + panel height + panel title + 0.2).
FIG_W, FIG_H = 12.3, 6.65
SIDE_IN, FOOT_IN, GAP_IN, TOP_IN = 0.06, 0.46, 0.07, 0.66
DECK_BOX_IN = (0.93 * 13.333, (0.875 - 0.079) * 7.5)   # build_deck.py image box, 2 record-set lines
FOOTER_PT = 6.5                                         # _style.footer font size

DEPTH_COLOR = {0: st.ORDINAL[-1], 1: st.ORDINAL[5], 2: st.ORDINAL[1]}
DEPTH_LABEL = {0: "Dataset (start)", 1: "depth 1: range of a Dataset slot",
               2: "depth 2: reached through one intermediate class"}
UNREACH_LABEL = "not reachable from Dataset through class-valued slots (at any depth)"
SIZE_K = 1.7                           # diameter (pt) = SIZE_K * sqrt(attributes)
FS_NODE, FS_META, FS_EDGE, FS_HEAD, FS_NOTE, FS_LEG, FS_COUNT = 8.2, 7.4, 7.6, 8.4, 7.5, 7.6, 8.2
FS_PANEL, FS_SUP = 9.2, 11.0
LEG_TOP_PT, NOTE_LH = 36.5, FS_NOTE * 1.24    # legend key rows above the note; note line height (pt)
LEG_W_PT = (FIG_W - 2 * SIDE_IN) * 72
EDGE_INK = st.INK["secondary"]
ISA_INK = st.INK["muted"]
BOX_FILL = st.INK["mid"]
DASH = (0, (3.2, 2.0))
BEND_ZONE = 64.0                       # detail figure: room (pt) for runs to bend into column 2


# ---------------------------------------------------------------- measurement
_FP: dict = {}


def text_w(s: str, size: float, weight: str = "normal") -> float:
    """Width of a single-line string in points, from the glyph outlines."""
    key = (size, weight)
    if key not in _FP:
        _FP[key] = FontProperties(family=plt.rcParams["font.sans-serif"], size=size, weight=weight)
    if not s:
        return 0.0
    return TextPath((0, 0), s, size=size, prop=_FP[key]).get_extents().width


def wrap_w(s: str, size: float, width: float, weight: str = "normal") -> list[str]:
    """Greedy word wrap to a measured width in points."""
    lines, cur = [], ""
    for w in s.split(" "):
        t = w if not cur else cur + " " + w
        if not cur or text_w(t, size, weight) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def radius(n_attrs: int) -> float:
    return 0.5 * SIZE_K * math.sqrt(max(n_attrs, 1))


# ---------------------------------------------------------------- schema
def load():
    merged = yaml.load(MERGED.read_text(), Loader=yaml.CSafeLoader)
    classes = merged["classes"]
    sv = shared_view(ROOT_SCHEMA)
    by_name = {}
    for imp in sv.imports_closure():
        sch = sv.schema_map.get(imp)
        if sch is not None and not imp.startswith("linkml:"):
            by_name[sch.name] = Path(sch.source_file).resolve()
    module = {c: by_name[sv.in_schema(c)].name for c in sv.all_classes()}
    for p in set(module.values()):
        assert (SCHEMA_DIR / p).exists(), p
    # the merged file must describe the same schema as the sources
    assert set(module) == set(classes), set(module) ^ set(classes)
    for c in classes:
        ind = {s.name: s.range for s in sv.class_induced_slots(c)}
        mat = {s: (d or {}).get("range") for s, d in (classes[c].get("attributes") or {}).items()}
        assert ind == mat, (c, set(ind.items()) ^ set(mat.items()))
        assert sv.get_class(c).is_a == classes[c].get("is_a"), c
        for d in (classes[c].get("attributes") or {}).values():
            for key in ("any_of", "exactly_one_of", "all_of", "none_of"):
                assert not d.get(key), (c, key)
    direct = {c: set(sv.class_slots(c, direct=True)) for c in classes}
    ancestors = {c: sv.class_ancestors(c, reflexive=False) for c in classes}
    order = [ROOT_SCHEMA.name] + [f"{i}.yaml" for i in sv.schema.imports if not i.startswith("linkml:")]
    decl_order = {}
    for imp in [i for i in sv.imports_closure() if not i.startswith("linkml:")]:
        for i, c in enumerate(sv.schema_map[imp].classes):
            decl_order[c] = i
    yaml_files = sorted(p.name for p in SCHEMA_DIR.glob("*.yaml"))
    return merged, classes, module, direct, ancestors, order, decl_order, yaml_files


def schema_dir_changes() -> list[str] | None:
    """Lines of `git status --porcelain` under the schema directory (untracked included);
    None when git cannot be asked. Read-only: --no-optional-locks skips the index refresh."""
    try:
        out = subprocess.check_output(
            ["git", "--no-optional-locks", "status", "--porcelain", "--",
             str(SCHEMA_DIR.relative_to(st.ROOT))], cwd=st.ROOT, text=True)
    except Exception:  # pragma: no cover
        return None
    return [x for x in out.splitlines() if x.strip()]


def slot_edges(classes, direct, ancestors):
    """Every induced class-valued slot: (source, slot, target, declared_on)."""
    out = []
    for c, cd in classes.items():
        for s, d in (cd.get("attributes") or {}).items():
            r = d.get("range")
            if r not in classes:
                continue
            if s in direct[c]:
                owner = c
            else:
                owner = next((a for a in ancestors[c] if s in direct[a]), "?")
            out.append({"source": c, "slot": s, "target": r, "declared_on": owner})
    return out


def depths(edges, limit):
    adj = defaultdict(list)
    for e in edges:
        adj[e["source"]].append(e["target"])
    depth = {START: 0}
    q = deque([START])
    while q:
        c = q.popleft()
        if depth[c] >= limit:
            continue
        for t in adj[c]:
            if t not in depth:
                depth[t] = depth[c] + 1
                q.append(t)
    return depth


# ---------------------------------------------------------------- drawing helpers
def node(ax, x, y, n_attrs, depth, z=4):
    d = 2 * radius(n_attrs)
    if depth is None:
        ax.scatter([x], [y], s=d * d, facecolors=st.INK["surface"], edgecolors=st.INK["muted"],
                   linewidths=1.0, zorder=z)
    else:
        ax.scatter([x], [y], s=d * d, c=DEPTH_COLOR[depth], edgecolors=st.INK["surface"],
                   linewidths=0.8, zorder=z)


def arrow(ax, p, q, dashed=False, head=True, rad=0.0, lw=0.8, color=None, hollow=False,
          shrink_a=0.0, shrink_b=0.0, z=2):
    color = color or (ISA_INK if dashed else EDGE_INK)
    style = "-|>" if head else "-"
    a = FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=7.0, linewidth=lw,
                        color=color, linestyle=DASH if dashed else "-",
                        connectionstyle=f"arc3,rad={rad}", shrinkA=shrink_a, shrinkB=shrink_b,
                        zorder=z)
    if hollow:
        a.set_facecolor(st.INK["surface"])
        a.set_edgecolor(color)
    ax.add_patch(a)
    return a


def box(ax, x, y, w, h):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=3.5",
                                facecolor=BOX_FILL, edgecolor="none", zorder=0))


def short(module_file: str) -> str:
    return module_file.replace(".yaml", "")


def wrap_note(note: str) -> list[str]:
    return wrap_w(note, FS_NOTE, LEG_W_PT - 6)


def new_figure(n_note: int):
    """Figure with the panel axes above a legend band sized for `n_note` note lines."""
    LEG_IN = (LEG_TOP_PT + n_note * NOTE_LH + 3) / 72
    fig = plt.figure(figsize=(FIG_W, FIG_H))
    x0, w = SIDE_IN / FIG_W, (FIG_W - 2 * SIDE_IN) / FIG_W
    y_ax = (FOOT_IN + LEG_IN + GAP_IN) / FIG_H
    ax = fig.add_axes([x0, y_ax, w, 1 - y_ax - TOP_IN / FIG_H])
    axl = fig.add_axes([x0, FOOT_IN / FIG_H, w, LEG_IN / FIG_H])
    W, H = w * FIG_W * 72, (1 - y_ax - TOP_IN / FIG_H) * FIG_H * 72
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    LW, LH = w * FIG_W * 72, LEG_IN * 72
    axl.set_xlim(0, LW); axl.set_ylim(0, LH); axl.axis("off")
    return fig, ax, W, H, axl, LW, LH


def suptitle(fig, text):
    """Suptitle at the largest size up to FS_SUP that fits the figure width on one line."""
    avail = (FIG_W - 0.2) * 72
    size = FS_SUP
    while text_w(text, size, "bold") > avail and size > 9.0:
        size -= 0.25
    assert text_w(text, size, "bold") <= avail, ("suptitle too long", text)
    fig.suptitle(text, x=SIDE_IN / FIG_W + 0.002, ha="left", fontsize=size, fontweight="bold",
                 y=1 - 0.10 / FIG_H, va="top")
    return size


def legend_band(axl, LW, LH, arrows, note):
    """Depth colors, node-size key, the figure's line kinds, then the note (wrapped)."""
    y1, y2 = LH - 7.5, LH - 24.5
    x = 2.0
    for dpt in (0, 1, 2):
        node(axl, x + 5, y1, 30, dpt)
        axl.text(x + 12, y1, DEPTH_LABEL[dpt], fontsize=FS_LEG, va="center", color=st.INK["primary"])
        x += 24 + text_w(DEPTH_LABEL[dpt], FS_LEG)
    node(axl, x + 5, y1, 30, None)
    axl.text(x + 12, y1, UNREACH_LABEL, fontsize=FS_LEG, va="center", color=st.INK["primary"])
    row1 = x + 12 + text_w(UNREACH_LABEL, FS_LEG)
    x = 2.0
    t = "node area = induced attributes (inherited included):"
    axl.text(x, y2, t, fontsize=FS_LEG, va="center", color=st.INK["primary"])
    x += text_w(t, FS_LEG) + 8
    for n in (10, 30, 100):
        r = radius(n)
        node(axl, x + r, y2, n, 1)
        axl.text(x + 2 * r + 3, y2, str(n), fontsize=FS_LEG, va="center", color=st.INK["primary"])
        x += 2 * r + 8 + text_w(str(n), FS_LEG) + 8
    x += 8
    for dashed, label in arrows:
        arrow(axl, (x, y2), (x + 26, y2), dashed=dashed, hollow=dashed, lw=0.9)
        axl.text(x + 31, y2, label, fontsize=FS_LEG, va="center", color=st.INK["primary"])
        x += 31 + text_w(label, FS_LEG) + 16
    row2 = x - 16
    assert max(row1, row2) <= LW, ("legend rows overflow", row1, row2, LW)
    lines = wrap_note(note)
    y = LH - LEG_TOP_PT
    for line in lines:
        axl.text(2, y, line, fontsize=FS_NOTE, va="top", ha="left", color=st.INK["secondary"])
        y -= NOTE_LH
    assert y > -1, ("note overflows the legend band", len(lines))
    return len(lines)


# ---------------------------------------------------------------- overview (all classes)
def panel_a(ax, W, H, classes, module, order, decl_order, depth, n_attr, slot_e, isa, positions):
    root, base = order[0], order[1]
    middle = [m for m in order if m not in (root, base)]
    members = defaultdict(list)
    for c in classes:
        members[module[c]].append(c)
    for m in members:
        members[m].sort(key=lambda c: decl_order[c])
    # Dataset's class-valued slots by the range's file; is_a DatasetProperty by the subclass's file
    per_mod = Counter(module[e["target"]] for e in slot_e if e["source"] == START and e["declared_on"] == START)
    per_isa = Counter(module[c] for c, p in isa if p == BASE_PARENT)

    pad, head_h, gap1, gap2 = 3.8, 13.0, 38.0, 40.0
    item_gap, row_min = 8.0, 12.0

    def item_w(c):
        return 2 * radius(n_attr[c]) + 2.5 + text_w(c, FS_NODE)

    def mid_name(m):                      # the D4D_ prefix is stated once in the legend note
        return short(m).replace("D4D_", "", 1)

    # notes: links with both ends in the root file, and is_a links into the base file
    # other than the aggregated DatasetProperty fan
    root_slots = defaultdict(list)
    for e in slot_e:
        if e["declared_on"] == e["source"] and module[e["source"]] == root and module[e["target"]] == root:
            root_slots[(e["source"], e["target"])].append(e["slot"])
    by_target = defaultdict(list)
    for (src, tgt), v in sorted(root_slots.items()):
        by_target[tgt] += [f"{src}.{x}" for x in v]
    root_notes = ["Slots within this file: " + "; ".join(
        f"{', '.join(v)} (range {t})" for t, v in by_target.items())]
    root_isa = [(c, p) for c, p in isa if module[c] == root and module[p] == root]
    if root_isa:
        root_notes.append("is_a within this file: " + "; ".join(f"{c} is_a {p}" for c, p in root_isa))
    base_notes = [f"Dataset slots into this file: {per_mod.get(base, 0)}"]
    for p in members[base]:
        if p == BASE_PARENT:
            continue
        kids = [c for c, q in isa if q == p]
        if kids:
            base_notes.append(f"is_a children of {p}: {', '.join(kids)}")
    isolated = [c for c in members[base] if c not in depth
                and not any(q == c or k == c for k, q in isa)
                and not any(e["source"] == c or e["target"] == c for e in slot_e)]
    for c in isolated:
        base_notes.append(f"{c}: no class-valued slot or is_a link in either direction")

    def side_w(m, notes, floor):
        longest_token = max(text_w(tok, FS_NOTE) for n in notes for tok in n.split(" "))
        return max(max(item_w(c) for c in members[m]) + 2 * pad, longest_token + 2 * pad + 2,
                   text_w(short(m), FS_HEAD, "bold") + 2 * pad, floor)

    root_w = side_w(root, root_notes, 112)
    base_w = side_w(base, base_notes, 128)
    mx0, mx1 = root_w + gap1, W - base_w - gap2
    head_col = max(text_w(mid_name(m), FS_HEAD, "bold") + 4 + text_w(f"({len(members[m])})", FS_HEAD)
                   for m in middle) + 9
    flow = mx1 - mx0 - 2 * pad - head_col

    # flow each middle module's classes into rows to the right of its name
    layout = {}
    for m in middle:
        rows, cur, x = [], [], 0.0
        for c in members[m]:
            w = item_w(c)
            if cur and x + w > flow:
                rows.append(cur); cur, x = [], 0.0
            cur.append((c, x)); x += w + item_gap
        rows.append(cur)
        rh = [max(row_min, max(2 * radius(n_attr[c]) for c, _ in r) + 3) for r in rows]
        layout[m] = (rows, rh, 2 * pad + sum(rh))
    total = sum(v[2] for v in layout.values())
    gap = (H - total) / (len(middle) - 1)
    if gap < 2.5:
        print(f"warning: overview middle stack overflows by {2.5 * (len(middle) - 1) - (H - total):.0f} pt")
    y_top = H
    centers = {}
    for m in middle:
        rows, rh, h = layout[m]
        y0 = y_top - h
        box(ax, mx0, y0, mx1 - mx0, h)
        yh = y_top - pad - rh[0] / 2
        ax.text(mx0 + pad, yh, mid_name(m), fontsize=FS_HEAD, fontweight="bold",
                color=st.INK["primary"], va="center", ha="left", zorder=5)
        ax.text(mx0 + pad + text_w(mid_name(m), FS_HEAD, "bold") + 4, yh, f"({len(members[m])})",
                fontsize=FS_HEAD, color=st.INK["muted"], va="center", ha="left", zorder=5)
        yy = y_top - pad
        for r, h_r in zip(rows, rh):
            yc = yy - h_r / 2
            for c, x in r:
                rr = radius(n_attr[c])
                cx = mx0 + pad + head_col + x + rr
                node(ax, cx, yc, n_attr[c], depth.get(c))
                ax.text(cx + rr + 2.5, yc, c, fontsize=FS_NODE, va="center", ha="left",
                        color=st.INK["primary"] if c in depth else st.INK["secondary"], zorder=5)
                positions[c] = (cx, yc)
            yy -= h_r
        centers[m] = y0 + h / 2
        y_top = y0 - gap

    # root file (left) and base file (right), vertically centered on the middle stack
    y_mid = (max(centers.values()) + min(centers.values())) / 2

    def stack(m, x0, w, anchor, notes):
        cs = members[m]
        rh = [max(15.0, 2 * radius(n_attr[c]) + 4) for c in cs]
        note_lines = []
        for n in notes:
            note_lines += wrap_w(n, FS_NOTE, w - 2 * pad)
            note_lines.append("")
        note_lines = note_lines[:-1]
        lh = FS_NOTE * 1.22
        note_h = len(note_lines) * lh + (4 if note_lines else 0)
        h = pad + head_h + sum(rh) + note_h + pad
        # place so that `anchor` class sits at y_mid
        off = pad + head_h + sum(rh[:cs.index(anchor)]) + rh[cs.index(anchor)] / 2
        y_top = min(H, max(h, y_mid + off))
        y0 = y_top - h
        assert y0 >= -0.5, (m, "side box taller than the panel", h, H)
        box(ax, x0, y0, w, h)
        ax.text(x0 + pad, y_top - pad - head_h / 2 + 1, short(m), fontsize=FS_HEAD, fontweight="bold",
                color=st.INK["primary"], va="center", ha="left", zorder=5)
        ys = {}
        yy = y_top - pad - head_h
        for c, h_r in zip(cs, rh):
            yc = yy - h_r / 2
            rr = radius(n_attr[c])
            cx = x0 + pad + rr
            node(ax, cx, yc, n_attr[c], depth.get(c))
            ax.text(cx + rr + 2.5, yc, c, fontsize=FS_NODE, va="center", ha="left",
                    color=st.INK["primary"] if c in depth else st.INK["secondary"], zorder=5)
            positions[c] = (cx, yc)
            ys[c] = (cx, yc, rr)
            yy -= h_r
        yy -= 4
        for line in note_lines:
            ax.text(x0 + pad, yy, line, fontsize=FS_NOTE, color=st.INK["secondary"], va="top", ha="left", zorder=5)
            yy -= lh
        return ys

    rys = stack(root, 0, root_w, START, root_notes)
    bys = stack(base, W - base_w, base_w, BASE_PARENT, base_notes)

    # solid bus: Dataset's class-valued slots, aggregated by the file declaring the range
    dx, dy, dr = rys[START]
    x_bus = root_w + gap1 * 0.40
    x_start = dx + dr + 2.5 + text_w(START, FS_NODE) + 3
    arrow(ax, (x_start, dy), (x_bus, dy), head=False, lw=0.9)
    ys_branch = [centers[m] for m in middle if per_mod.get(m)]
    ax.plot([x_bus, x_bus], [min(ys_branch + [dy]), max(ys_branch + [dy])], color=EDGE_INK, lw=0.9,
            solid_capstyle="butt", zorder=2)
    for m in middle:
        n = per_mod.get(m, 0)
        if not n:
            ax.text(mx0 - 3, centers[m], "0", fontsize=FS_COUNT, color=st.INK["muted"], ha="right", va="center")
            continue
        arrow(ax, (x_bus, centers[m]), (mx0, centers[m]), lw=0.9)
        ax.text((x_bus + mx0) / 2 - 1.5, centers[m] + 1.2, str(n), fontsize=FS_COUNT,
                color=st.INK["primary"], ha="center", va="bottom", zorder=6)

    # dashed bus: is_a DatasetProperty, aggregated by the file declaring the subclass
    bx, by, br = bys[BASE_PARENT]
    x_bus2 = mx1 + gap2 * 0.58
    ys2 = [centers[m] for m in middle if per_isa.get(m)]
    ax.plot([x_bus2, x_bus2], [min(ys2 + [by]), max(ys2 + [by])], color=ISA_INK, lw=0.9,
            linestyle=DASH, zorder=2)
    for m in middle:
        n = per_isa.get(m, 0)
        if not n:
            ax.text(mx1 + 3, centers[m], "0", fontsize=FS_COUNT, color=st.INK["muted"], ha="left", va="center")
            continue
        ax.plot([mx1, x_bus2], [centers[m], centers[m]], color=ISA_INK, lw=0.9, linestyle=DASH, zorder=2)
        ax.text((mx1 + x_bus2) / 2 + 0.5, centers[m] + 1.2, str(n), fontsize=FS_COUNT,
                color=st.INK["primary"], ha="center", va="bottom", zorder=6)
    arrow(ax, (x_bus2, by), (bx, by), dashed=True, hollow=True, shrink_b=br + 1, lw=0.9)

    n_cls = len(classes)
    n_slots = sum(per_mod.get(m, 0) for m in middle)
    ax.set_title(f"All {n_cls} classes by declaring file; branches count {n_slots} Dataset slots into each module "
                 f"(solid) and {sum(per_isa.values())} is_a {BASE_PARENT} links from it (dashed)",
                 fontsize=FS_PANEL, pad=5)
    agg = [{"module_file": m, "classes": len(members[m]),
            "depth0": sum(1 for c in members[m] if depth.get(c) == 0),
            "depth1": sum(1 for c in members[m] if depth.get(c) == 1),
            "depth2": sum(1 for c in members[m] if depth.get(c) == 2),
            "not_reachable": sum(1 for c in members[m] if c not in depth),
            "dataset_slots_into_file": per_mod.get(m, 0),
            "isa_datasetproperty_in_file": per_isa.get(m, 0),
            "induced_attributes_total": sum(n_attr[c] for c in members[m]),
            "overview_position": "left" if m == root else "right" if m == base else "middle",
            "overview_label": short(m) if m in (root, base) else f"{mid_name(m)} ({len(members[m])})"}
           for m in order]
    return agg, gap


# ---------------------------------------------------------------- detail (class level)
def panel_b(ax, W, H, classes, module, decl_order, order, depth, n_attr, slot_e, isa, parent, positions):
    mod_rank = {m: i for i, m in enumerate(order)}

    # nested slots: declared on a class other than Dataset, drawn at class level
    nested = [e for e in slot_e if e["declared_on"] == e["source"] and e["source"] != START
              and (e["source"] in depth or e["target"] in depth)]
    # keep only those whose source is reachable, or which are the declaring edge of an
    # inherited slot that reachable classes carry (DatasetProperty.used_software)
    inherited_from = Counter(e["declared_on"] for e in slot_e if e["declared_on"] != e["source"]
                             and e["source"] in depth and e["declared_on"] not in depth)
    nested = [e for e in nested if e["source"] in depth or inherited_from.get(e["source"])]
    carriers = {e["declared_on"]: sorted({x["source"] for x in slot_e if x["declared_on"] == e["declared_on"]
                                          and x["slot"] == e["slot"] and x["source"] != e["declared_on"]})
                for e in nested if e["source"] not in depth}
    shown = {START}
    for e in nested:
        shown |= {e["source"], e["target"]}
    # Dataset's children by is_a (DataSubset)
    shown |= {c for c, p in isa if p == START}
    col = {c: depth.get(c) for c in shown}
    l1 = [c for c in shown if col[c] == 1]
    unreach = [c for c in shown if col[c] is None]          # declaring parents (DatasetProperty)
    l2 = [c for c in shown if col[c] == 2]

    # Column order (deterministic, two barycenter passes): classes joined by a same-column
    # slot stay together; column 2 is ordered by the mean row of its sources, then column 1
    # by the mean rank of its column-2 targets (ties: file order, declaration order);
    # classes with no column-2 target first, unreachable declaring parents last.
    intra = [(e["source"], e["target"]) for e in nested if col.get(e["source"]) == 1 and col.get(e["target"]) == 1]
    comp = {c: c for c in l1}

    def find(c):
        while comp[c] != c:
            c = comp[c]
        return c
    for a, b in intra:
        comp[find(a)] = find(b)
    groups = defaultdict(list)
    for c in l1:
        groups[find(c)].append(c)
    src_first = {a for a, _ in intra}

    tgt2 = defaultdict(list)
    for e in nested:
        if col.get(e["target"]) == 2 and col.get(e["source"]) != 2:
            tgt2[e["source"]].append(e["target"])

    def order_l1(rank2):
        def gkey(g):
            ts = [rank2[t] for c in g for t in tgt2.get(c, []) if t in rank2]
            first = min((mod_rank[module[c]], decl_order[c]) for c in g)
            return (sum(ts) / len(ts) if ts else -1.0, first)
        out = []
        for g in sorted(groups.values(), key=gkey):
            out += sorted(g, key=lambda c: (c not in src_first, mod_rank[module[c]], decl_order[c]))
        return out + sorted(unreach, key=lambda c: (mod_rank[module[c]], decl_order[c]))

    def order_l2(l1o):
        row = {c: i for i, c in enumerate(l1o)}
        bc = {}
        for c in l2:
            rs = [row[s] for s, ts in tgt2.items() if c in ts]
            bc[c] = sum(rs) / len(rs)
        return {c: i for i, c in enumerate(sorted(l2, key=lambda c: (bc[c], mod_rank[module[c]], decl_order[c])))}

    l1_order = order_l1({})                         # pass 0: file order
    for _ in range(2):
        l1_order = order_l1(order_l2(l1_order))

    top, bottom = H - 10, 16
    step = (top - bottom) / (len(l1_order) - 1)
    ypos = {c: top - i * step for i, c in enumerate(l1_order)}
    xpos: dict = {}

    def meta(c):                     # one line: declaring file (D4D_ prefix dropped) and is_a parent
        m = short(module[c]).replace("D4D_", "", 1)
        return f"{m} · is_a {parent[c]}" if parent.get(c) else m

    def lab_w(c):
        return max(text_w(c, FS_NODE), text_w(meta(c), FS_META))

    lineage, p = [], parent.get(START)
    while p:
        lineage.append(p); p = parent.get(p)
    r0 = radius(n_attr[START])

    pair = defaultdict(list)
    for e in nested:
        pair[(e["source"], e["target"])].append(e["slot"])

    def label_of(s, names):
        lab = ", ".join(names)
        if s in carriers:
            lab += f" (declared here; inherited by {len(carriers[s])} classes)"
        return lab

    # rows first (they do not depend on x): Dataset between its first and last reachable
    # target, depth-2 classes at the barycenter of their sources (then spaced), lineage above
    reach = [c for c in l1_order if c in depth]
    ypos[START] = (ypos[reach[0]] + ypos[reach[-1]]) / 2
    srcs = defaultdict(list)
    for e in nested:
        if col.get(e["target"]) == 2 and col.get(e["source"]) != 2:
            srcs[e["target"]].append(ypos[e["source"]])
    bary = {c: sum(srcs[c]) / len(srcs[c]) for c in l2}
    l2_order = sorted(l2, key=lambda c: (-bary[c], mod_rank[module[c]], decl_order[c]))
    min_gap = 30.0
    ys = [bary[c] for c in l2_order]
    for i in range(1, len(ys)):
        ys[i] = min(ys[i], ys[i - 1] - min_gap)
    shift = max(0.0, bottom - ys[-1])
    ys = [y + shift for y in ys]
    for c, y in zip(l2_order, ys):
        ypos[c] = y
    lineage_step = min(56.0, (H - 12 - ypos[START]) / max(len(lineage), 1))
    for i, c in enumerate(lineage, 1):          # Dataset's is_a lineage, above it
        ypos[c] = ypos[START] + lineage_step * i

    def block(c):                   # node radius + gap + label block, measured from the node center
        return radius(n_attr[c]) + 3 + lab_w(c) + 2.5

    # columns: Dataset's column fits its label; column 2 fits its labels and any same-column
    # arc (bulge 0.25 x chord for rad 0.5) with the slot name at the apex
    x0 = max(lab_w(c) + radius(n_attr[c]) for c in [START] + lineage) + 8
    right = [block(c) for c in l2]
    for (s, t), names in pair.items():
        if col.get(s) == 2 and col.get(t) == 2:
            right.append(max(block(s), block(t)) + 0.25 * abs(ypos[s] - ypos[t]) + 3
                         + text_w(label_of(s, names), FS_EDGE))
    x2 = W - max(right) - 4
    # column 1 sits as far right as its label blocks, outgoing slot names and a bend zone allow
    run_w = defaultdict(float)
    for (s, t), names in pair.items():
        if col.get(s) != col.get(t):
            run_w[s] = max(run_w[s], text_w(label_of(s, names), FS_EDGE))
    x1 = min(x2 - block(c) - (run_w[c] + 12 if run_w[c] else 0) - BEND_ZONE for c in l1_order)
    assert x1 - x0 > 150, (x0, x1, x2)
    xpos = {c: x1 for c in l1_order}
    xpos.update({c: x2 for c in l2_order})
    xpos[START] = x0
    for c in lineage:
        xpos[c] = x0

    def draw_node(c, left=False):
        r = radius(n_attr[c])
        node(ax, xpos[c], ypos[c], n_attr[c], col.get(c) if c in col else None)
        xt, ha = (xpos[c] - r - 3, "right") if left else (xpos[c] + r + 3, "left")
        ax.text(xt, ypos[c], c, fontsize=FS_NODE, ha=ha, va="center",
                color=st.INK["primary"] if c in depth else st.INK["secondary"], zorder=5)
        ax.text(xt, ypos[c] - 9.4, meta(c), fontsize=FS_META, ha=ha, va="center",
                color=st.INK["muted"], zorder=5)
        positions[c] = (xpos[c], ypos[c], meta(c))

    for c in l1_order + l2_order:
        draw_node(c)
    for c in [START] + lineage:
        draw_node(c, left=True)

    def out_pt(c):      # right end of the label block, at the name's height
        return (xpos[c] + radius(n_attr[c]) + 3 + lab_w(c) + 2.5, ypos[c])

    def in_pt(c):
        return (xpos[c] - radius(n_attr[c]) - 1.5, ypos[c])

    drawn, lines = [], []
    # Dataset -> classes shown: S-curve out of Dataset, then a straight run carrying the slot name
    d_slots = defaultdict(list)
    for e in slot_e:
        if e["source"] == START and e["declared_on"] == START and e["target"] in shown:
            d_slots[e["target"]].append(e["slot"])
    xs = x0 + r0 + 1
    xm = x0 + 0.40 * (x1 - x0)
    for t, names in d_slots.items():
        if t == START:
            continue
        q = in_pt(t)
        c1, c2 = (xs + 0.55 * (xm - xs), ypos[START]), (xs + 0.45 * (xm - xs), q[1])
        path = MPath([(xs, ypos[START]), c1, c2, (xm, q[1]), q],
                     [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.LINETO])
        ax.add_patch(FancyArrowPatch(path=path, arrowstyle="-|>", mutation_scale=7.0, linewidth=0.8,
                                     color=EDGE_INK, zorder=2))
        lab = ", ".join(names)
        ax.text(q[0] - 4, q[1] + 1.4, lab, fontsize=FS_EDGE, color=st.INK["secondary"],
                ha="right", va="bottom", zorder=6)
        assert q[0] - 4 - text_w(lab, FS_EDGE) > xm, ("Dataset slot label runs into the fan", t)
        drawn += [(START, s, t) for s in names]
        lines.append({"kind": "class-valued slot", "source": START, "slots": lab, "target": t,
                      "declared_on": START, "n_slots": len(names), "line_label": lab})
    # slots whose range is Dataset itself: a loop under the node
    selfs = d_slots.get(START, [])
    if selfs:
        arrow(ax, (x0 - 5.5, ypos[START] - r0 + 1.5), (x0 + 5.5, ypos[START] - r0 + 1.5), rad=1.9, lw=0.8)
        lab = ", ".join(selfs)
        ax.text(x0 + 10, ypos[START] - r0 - 18, lab + "\n(range: Dataset itself)",
                fontsize=FS_EDGE, color=st.INK["secondary"], ha="right", va="top", linespacing=1.2)
        drawn += [(START, s, START) for s in selfs]
        lines.append({"kind": "class-valued slot", "source": START, "slots": lab, "target": START,
                      "declared_on": START, "n_slots": len(selfs), "line_label": lab + " (range: Dataset itself)"})
    # slots declared on the other classes
    out_rank = defaultdict(list)
    for (s, t) in pair:
        if col.get(s) != col.get(t):
            out_rank[s].append(t)
    bend_x = max(out_pt(s)[0] + text_w(label_of(s, names), FS_EDGE) + 10
                 for (s, t), names in pair.items() if col.get(s) != col.get(t))
    for (s, t), names in pair.items():
        label = label_of(s, names)
        if col.get(s) == col.get(t):
            # same column: arc on the right, label end to label end
            p, q = out_pt(s), out_pt(t)
            rad = -0.5 if ypos[s] > ypos[t] else 0.5
            arrow(ax, p, q, rad=rad, shrink_a=0, shrink_b=1)
            apex = max(p[0], q[0]) + 0.25 * abs(p[1] - q[1]) + 3
            ax.text(apex, (p[1] + q[1]) / 2, label, fontsize=FS_EDGE, color=st.INK["secondary"],
                    ha="left", va="center", zorder=6)
        else:
            # straight run carrying the slot name, then a late bend into the target
            sibs = sorted(out_rank[s], key=lambda c: -ypos[c])
            k = len(sibs)
            upper = (k == 1) or t == sibs[0]
            dy = 0.0 if k == 1 else (2.5 if upper else -2.5)
            p, q = out_pt(s), in_pt(t)
            p = (p[0], p[1] + dy)
            lw = text_w(label, FS_EDGE)
            xr = min(bend_x, q[0] - 22)         # every run bends right of every slot name
            assert xr >= p[0] + lw + 4, ("slot label longer than its straight run", s, t)
            xb = xr + 0.5 * (q[0] - xr)
            path = MPath([p, (xr, p[1]), (xb, p[1]), (xb, q[1]), q],
                         [MPath.MOVETO, MPath.LINETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4])
            ax.add_patch(FancyArrowPatch(path=path, arrowstyle="-|>", mutation_scale=7.0, linewidth=0.8,
                                         color=EDGE_INK, zorder=2))
            ax.text(p[0] + 3, p[1] + (1.4 if upper else -1.4), label, fontsize=FS_EDGE,
                    color=st.INK["secondary"], ha="left", va="bottom" if upper else "top", zorder=6)
        drawn += [(s, n, t) for n in names]
        lines.append({"kind": "class-valued slot", "source": s, "slots": ", ".join(names), "target": t,
                      "declared_on": s, "n_slots": len(names), "line_label": label})
    # is_a: Dataset's lineage (other parents are named under each node)
    chain = [START] + lineage
    for a, b in zip(chain, chain[1:]):
        arrow(ax, (xpos[a], ypos[a]), (xpos[b], ypos[b]), dashed=True, hollow=True,
              shrink_a=radius(n_attr[a]) + 1, shrink_b=radius(n_attr[b]) + 1)
        lines.append({"kind": "is_a", "source": a, "slots": "", "target": b, "declared_on": a,
                      "n_slots": 0, "line_label": ""})

    ax.set_title("Class-level detail: the slots that continue past Dataset's direct targets, "
                 "with each class's declaring file and is_a parent under its name", fontsize=FS_PANEL, pad=5)
    return {"shown": shown | set(lineage), "drawn": set(drawn), "l1": l1_order, "l2": l2_order,
            "lineage": lineage, "carriers": carriers, "nested": nested, "col": col, "lines": lines,
            "row_step": step}


# ---------------------------------------------------------------- main
def main() -> int:
    st.apply()
    merged, classes, module, direct, ancestors, order, decl_order, yaml_files = load()
    slot_e = slot_edges(classes, direct, ancestors)
    depth = depths(slot_e, MAX_DEPTH)
    depth3 = depths(slot_e, MAX_DEPTH + 1)
    added_at_3 = sorted(set(depth3) - set(depth))
    n_attr = {c: len(classes[c].get("attributes") or {}) for c in classes}
    isa = [(c, classes[c]["is_a"]) for c in classes if classes[c].get("is_a")]
    parent = dict(isa)
    n_enums = len(merged.get("enums") or {})
    version = merged.get("version")
    imported = set(order)
    generated = {p for p in yaml_files if p.endswith("_all.yaml")}
    not_imported = [p for p in yaml_files if p not in imported and p not in generated]
    changes = schema_dir_changes()
    n_ds = sum(1 for e in slot_e if e["source"] == START and e["declared_on"] == START)
    n_reach = len(depth)
    third = ("a third step reaches no further class" if not added_at_3
             else f"{len(added_at_3)} more classes at depth 3, not drawn")

    # ------------------------------------------------------------ overview figure
    note_a = (f"Current schema capability (v{version}), not demonstrated use: a class drawn here may be empty in every "
              f"generated record. Walk from Dataset limited to depth {MAX_DEPTH}; {third}. Middle boxes are the "
              f"D4D_<name>.yaml modules, (n) = classes declared in the file. Slot names are drawn at class level in "
              f"{B_KEY} and listed in the _edges CSV.")
    pos_a: dict = {}
    fig_a, ax_a, W, H, axl_a, LW, LH = new_figure(len(wrap_note(note_a)))
    agg, a_gap = panel_a(ax_a, W, H, classes, module, order, decl_order, depth, n_attr, slot_e, isa, pos_a)
    n_files_hit = sum(1 for a in agg[1:] if a["dataset_slots_into_file"])
    legend_band(axl_a, LW, LH, [(False, "Dataset's class-valued slots, counted per range file"),
                                (True, f"is_a {BASE_PARENT}, counted per subclass file")], note_a)
    sup_a = suptitle(fig_a, f"D4D schema architecture: Dataset's {n_ds} class-valued slots reach {n_files_hit} of the "
                            f"{len(order) - 1} imported modules directly; "
                            f"{n_reach} of {len(classes)} classes lie within two steps of Dataset")

    # ------------------------------------------------------------ detail figure
    n_note_b = 3                   # the note's length depends on what the detail view leaves out
    for _ in range(3):
        pos_b: dict = {}
        fig_b, ax_b, W, H, axl_b, LW, LH = new_figure(n_note_b)
        b = panel_b(ax_b, W, H, classes, module, decl_order, order, depth, n_attr, slot_e, isa, parent, pos_b)
        shown_b, drawn_b, col_b = b["shown"], b["drawn"], b["col"]
        n_inh = sum(1 for e in slot_e if e["declared_on"] != e["source"])
        inh_by = Counter(e["declared_on"] for e in slot_e if e["declared_on"] != e["source"])
        inh_txt = " and ".join(f"{n} of {o}'s" for o, n in sorted(inh_by.items(), key=lambda kv: -kv[1]))
        declared = [e for e in slot_e if e["declared_on"] == e["source"]]
        ds_not_b = [e for e in declared if e["source"] == START and (e["source"], e["slot"], e["target"]) not in drawn_b]
        # the rule stated in the note: a Dataset slot is left out exactly when its range is not otherwise in this view
        declaring = {e["source"] for e in declared}
        nested_ends = {x for e in b["nested"] for x in (e["source"], e["target"])}
        dataset_kids = {c for c, p in isa if p == START}
        for e in [e for e in declared if e["source"] == START]:
            t = e["target"]
            elsewhere = t in declaring and t in depth or t in nested_ends or t in dataset_kids or t == START
            assert elsewhere == ((START, e["slot"], t) in drawn_b), (e, elsewhere)
        not_b_other = [f"{e['source']}.{e['slot']}" for e in declared
                       if e["source"] != START and (e["source"], e["slot"], e["target"]) not in drawn_b]
        # depth-2 classes and the declared slots that lead into them from outside column 2
        d2 = sorted(c for c, v in depth.items() if v == 2)
        to2 = [e for e in b["nested"] if depth.get(e["target"]) == 2 and depth.get(e["source"]) != 2]
        for e in slot_e:            # every induced step into depth 2 is one of these declared slots (or an inherited copy)
            if depth.get(e["source"]) == 1 and depth.get(e["target"]) == 2:
                assert any(x["source"] == e["declared_on"] and x["slot"] == e["slot"] for x in to2), e
        to2_src = sorted({e["source"] for e in to2})
        note_b = (f"Current schema capability (v{version}), not demonstrated use. File names under the classes drop "
                  f"the D4D_ prefix. Not drawn: {n_inh} inherited slot copies ({inh_txt}); the "
                  f"{len(ds_not_b)} Dataset slots whose range is not otherwise in this view (it declares no class-valued "
                  f"slot, is the range of no slot drawn here, and is not an is_a child of Dataset; all {n_ds} are counted "
                  f"in {A_KEY})"
                  + (f"; and {', '.join(not_b_other)} (unreachable source; listed in {A_KEY})" if not_b_other else "")
                  + ".")
        if len(wrap_note(note_b)) == n_note_b:
            break
        plt.close(fig_b)
        n_note_b = len(wrap_note(note_b))
    else:
        raise SystemExit("detail note line count did not settle")
    legend_band(axl_b, LW, LH, [(False, "class-valued slot (range is a class); slot name on the line"),
                                (True, "is_a (points to the parent)")], note_b)
    sup_b = suptitle(fig_b, f"D4D schema detail: {len(d2)} classes lie two steps from Dataset, reached through "
                            f"{len(to2)} slots declared on {len(to2_src)} classes other than Dataset")

    # ------------------------------------------------------------ tables
    rows = []
    for c in sorted(classes, key=lambda c: (order.index(module[c]), decl_order[c])):
        cv_ind = [e for e in slot_e if e["source"] == c]
        pa = pos_a.get(c); pb = pos_b.get(c)
        attrs = classes[c].get("attributes") or {}
        rows.append({
            "class": c, "module_file": module[c],
            "depth_from_dataset": depth[c] if c in depth else "not reachable",
            "induced_attributes": n_attr[c], "declared_slots": len(direct[c]),
            "class_valued_slots_induced": len(cv_ind),
            "class_valued_slots_declared": sum(1 for e in cv_ind if e["declared_on"] == c),
            "enum_valued_slots_induced": sum(1 for d in attrs.values() if (d or {}).get("range") in (merged.get("enums") or {})),
            "is_a": parent.get(c, ""),
            "overview_x_pt": round(pa[0], 1) if pa else "", "overview_y_pt": round(pa[1], 1) if pa else "",
            "in_detail_figure": "yes" if c in shown_b else "no",
            "detail_x_pt": round(pb[0], 1) if pb else "", "detail_y_pt": round(pb[1], 1) if pb else "",
        })
    edges = []
    root_f, base_f = order[0], order[1]
    middle_f = set(order[2:])
    for e in slot_e:
        inherited = e["declared_on"] != e["source"]
        key = (e["source"], e["slot"], e["target"])
        where = []
        if not inherited and e["source"] == START and module[e["target"]] in middle_f:
            where.append(f"{A_KEY} (counted on the solid branch to the range's file)")
        if not inherited and module[e["source"]] == root_f and module[e["target"]] == root_f:
            where.append(f"{A_KEY} (root file note)")
        if key in drawn_b:
            where.append(f"{B_KEY} (named line)")
        if inherited and e["declared_on"] in b["carriers"]:
            where.append(f"{B_KEY} (drawn once on {e['declared_on']}; this is an inherited copy)")
        elif inherited:
            where.append(f"not drawn (inherited copy of {e['declared_on']}.{e['slot']})")
        edges.append({"kind": "class-valued slot", "source": e["source"], "slot": e["slot"], "target": e["target"],
                      "declared_on": e["declared_on"], "inherited": "yes" if inherited else "no",
                      "source_file": module[e["source"]], "target_file": module[e["target"]],
                      "source_depth": depth.get(e["source"], "not reachable"),
                      "target_depth": depth.get(e["target"], "not reachable"),
                      "drawn": "; ".join(where) or "not drawn"})
    chain = [START] + b["lineage"]
    lineage_pairs = set(zip(chain, chain[1:]))
    for c, p in isa:
        where = []
        if p == BASE_PARENT:
            where.append(f"{A_KEY} (counted on the dashed branch)")
        elif module[p] == base_f:
            where.append(f"{A_KEY} (Base file note)")
        elif module[p] == root_f and module[c] == root_f:
            where.append(f"{A_KEY} (root file note)")
        if (c, p) in lineage_pairs:
            where.append(f"{B_KEY} (dashed line)")
        elif c in shown_b:
            where.append(f"{B_KEY} (parent named under the node)")
        edges.append({"kind": "is_a", "source": c, "slot": "", "target": p, "declared_on": c, "inherited": "no",
                      "source_file": module[c], "target_file": module[p],
                      "source_depth": depth.get(c, "not reachable"), "target_depth": depth.get(p, "not reachable"),
                      "drawn": "; ".join(where) or "not drawn"})
    undrawn = [x for x in edges if x["drawn"] == "not drawn"]
    assert not undrawn, undrawn
    files = [{"yaml_file": p,
              "role": ("root schema" if p == order[0] else "imported by the root" if p in imported
                       else "generated merged schema" if p in generated else "not imported by the root"),
              "drawn": "yes" if p in imported else "no",
              "classes_declared": sum(1 for c in classes if module[c] == p) if p in imported else ""}
             for p in yaml_files]
    schema_state = ("unknown (git status failed)" if changes is None
                    else "clean" if not changes else f"{len(changes)} uncommitted change(s)")
    summary = [{"quantity": k, "value": v} for k, v in [
        ("schema_version", version), ("classes_merged", len(classes)), ("enums_merged", n_enums),
        ("yaml_files_in_schema_dir", len(yaml_files)), ("local_modules_imported_by_root", len(order) - 1),
        ("files_not_imported_by_root", len(not_imported)), ("generated_merged_files", len(generated)),
        ("schema_dir_git_status", schema_state),
        ("class_valued_slots_induced", len(slot_e)), ("class_valued_slots_declared", len(slot_e) - n_inh),
        ("dataset_class_valued_slots", n_ds), ("imported_files_reached_by_dataset_slots", n_files_hit),
        ("max_depth", MAX_DEPTH), ("reachable_classes_incl_dataset", n_reach),
        ("depth1_classes", sum(1 for v in depth.values() if v == 1)),
        ("depth2_classes", len(d2)),
        ("classes_added_at_depth3", len(added_at_3)),
        ("not_reachable_classes", len(classes) - n_reach),
        ("isa_links", len(isa)), ("isa_datasetproperty", sum(1 for _, p in isa if p == BASE_PARENT)),
        ("detail_classes", len(shown_b)), ("detail_slots_named_on_lines", len(drawn_b)),
        ("detail_dataset_slots_drawn", n_ds - len(ds_not_b)), ("detail_dataset_slots_not_drawn", len(ds_not_b)),
        ("detail_slots_into_depth2", len(to2)), ("detail_classes_declaring_slots_into_depth2", len(to2_src)),
        ("inherited_slot_copies_not_drawn_in_detail", n_inh),
    ]]
    basis = (f"Record set: current working-tree D4D schema v{version}, data_sheets_schema_all.yaml "
             f"({len(classes)} classes, {n_enums} enums: attributes, ranges, is_a) with declaring files from a "
             f"SchemaView over data_sheets_schema.yaml and its {len(order) - 1} imported modules (the two views "
             f"agree); {len(not_imported)} other schema-directory YAML files not imported, not drawn; no generated "
             f"D4D record read; schema directory "
             + ("state unknown (git status failed)" if changes is None
                else "clean in git" if not changes else "has uncommitted changes")
             + ". Current schema capability, not demonstrated use")
    # the shared footer is one fig.text; wrap it so the titled SVG stays at figure width
    basis_wrapped = "\n".join(wrap_w(basis, FOOTER_PT, (FIG_W - 0.3) * 72 - 150))
    assert len(basis_wrapped.split("\n")) * FOOTER_PT * 1.25 < FOOT_IN * 72 - 4, "footer taller than its band"

    nodes_b = [{"class": c, "module_file": module[c], "depth_from_dataset": depth.get(c, "not reachable"),
                "column": ("0 (Dataset and its is_a lineage)" if c == START or c in b["lineage"]
                           else "2" if col_b.get(c) == 2 else "1"),
                "role": ("start" if c == START else "is_a lineage of Dataset (not reachable)" if c in b["lineage"]
                         else "declaring parent of an inherited slot (not reachable)" if c not in depth
                         else "reachable"),
                "induced_attributes": n_attr[c], "is_a": parent.get(c, ""), "label_under_name": pos_b[c][2],
                "x_pt": round(pos_b[c][0], 1), "y_pt": round(pos_b[c][1], 1)}
               for c in [START] + b["lineage"] + b["l1"] + b["l2"]]
    fig_rows = [{"figure": A_KEY, "suptitle_pt": sup_a, "middle_box_gap_pt": round(a_gap, 1)},
                {"figure": B_KEY, "suptitle_pt": sup_b, "row_step_pt": round(b["row_step"], 1)}]
    st.save(fig_a, A_KEY, {"main": rows, "edges": edges, "modules": agg, "files": files, "summary": summary},
            basis_wrapped)
    st.save(fig_b, B_KEY, {"main": nodes_b, "edges": b["lines"]}, basis_wrapped)

    # expected slide scale in the #2303 deck (build_deck.py fits the bare PNG into its image box)
    from PIL import Image
    for key in (A_KEY, B_KEY):
        with Image.open(st.BARE / f"{key}.png") as im:
            w_px, h_px = im.size
            dpi = im.info.get("dpi", (300, 300))[0]
        w_in, h_in = w_px / dpi, h_px / dpi
        scale = min(DECK_BOX_IN[0] / w_in, DECK_BOX_IN[1] / h_in)
        print(f"{key}: bare {w_in:.2f} x {h_in:.2f} in; deck scale {scale:.3f}; smallest text on the slide "
              f"{min(FS_META, FS_NOTE, FS_EDGE, FS_LEG) * scale:.2f} pt")
    print(fig_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
