#!/usr/bin/env python
"""Idea 5 (#2303 exploration): the observed generation design and its gaps. Which run families
(prompt condition or other label-named configuration) have full records for which project, under
which recorded runtime, and which of those records are in the reference rescore or have lost a
canonical mark.

Record set: every full record (<PROJECT>_d4d.yaml) in a run-label directory that
`data_sheets_schema.runs.discover` enumerates under data/d4d_concatenated/ (method directories
claudecode_agent, claudecode_api, claudecode_agent_crate, claudecode_agent_crate_only,
claudecode_agent_healthsheet, claudecode_agent_merged, rocrate_static_map and rocrate_mapped at the
time of writing; `_core` directories are the sibling core records and are not counted). The
`gate_test` label is a runner gate test and is excluded (listed in the records CSV, not drawn).
Not drawn, but counted in the figure note: the flat legacy directories that hold YAML files without
run labels (claudecode/, claudecode_assistant/, curated/, fairscape_reverse/, gpt5/), backup copies
of a full record (<PROJECT>_d4d.yaml.<suffix>) at the top of a method directory, and archived
records under data/ATTIC/d4d_concatenated_archived/ (including three `.superseded-*` earlier
copies of 2026-08-06 schema2 run directories). The direct arm's method directory (claudecode_direct/) does not exist,
so the direct runtime has zero records; the figure says so rather than omitting it.

Method.
- Row = run family, parsed from the label by a heuristic: drop the date prefix (with any
  same-day letter suffix, e.g. 2026-09-04g), the `_repN` replicate marker, the model token (claude-opus-5) and a leading runtime token
  (`api-` / `claudecode-`). Runtime is read from provenance, not from the label; the label's runtime
  token is compared with it and disagreements are exported. Rows are grouped by method directory
  (arm, per runs.ARM_BY_METHOD); baseline rows pool claudecode_agent/ and claudecode_api/.
- Column = project, from the record file name (VOICE_PEDIATRIC is its own column).
- Bubble area = number of full records in the cell for one runtime class (visible fill area: the
  marker path is widened by the surface-coloured edge width, and legend keys use the same path and
  edge, so a key of n records draws the same disc as a plotted n-record bubble). Runtime class is
  model.agent_runtime in the sibling <method>_core/<label>/<PROJECT>_provenance.yaml mapped through
  runs.RUNTIME_KEYS (api / agentic / direct). A method in runs.DETERMINISTIC, or a provenance record
  with record_mode `derived` and no runtime, is "no generation runtime". A missing or unreadable
  provenance file, or a runtime string outside RUNTIME_KEYS, is drawn as "runtime unknown".
- Ring = the cell holds records that are inputs of the frozen reference rescore
  (notes/reference_rescore_2026-09-12_cborg_runtime/manifest.json, jobs[].input).
- Hatched core = records whose provenance carries `canonical_superseded_by`, the pointer
  `d4d runs select` writes when it displaces a record's canonical mark (src/data_sheets_schema/cli/
  runs.py). Superseded means "no longer the canonical pick", not invalid; the record is kept.
- A dagger on a row label marks families where some records' hashed prompt names a different
  registered condition than the label claims (runs.prompt_condition_mismatch, #420).

Caveats. The counts are an archive: they include reruns, canaries and single-project repairs, and
different families were run for different projects and runtimes. They are not balanced experimental
sample sizes, and a larger bubble does not mean a better-supported condition. The family parse is a
heuristic over labels; the exported records CSV carries the raw label, the hashed-prompt condition
and the header Mode for every record.
"""
from __future__ import annotations

import json
import re
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.legend_handler import HandlerBase
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

sys.path.insert(0, str(st.ROOT / "src"))
from data_sheets_schema import runs as R  # noqa: E402

CONCAT = st.ROOT / "data" / "d4d_concatenated"
ATTIC = st.ROOT / "data" / "ATTIC" / "d4d_concatenated_archived"
REFERENCE = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime" / "manifest.json"
EXCLUDED_LABELS = {"gate_test": "runner gate test, not an experiment"}

PROJECT_ORDER = ["AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC"]
PROJECT_LABEL = {"AI_READI": "AI-READI", "CHORUS": "CHORUS", "CM4AI": "CM4AI", "VOICE": "VOICE",
                 "VOICE_PEDIATRIC": "VOICE\npediatric"}

# Groups in drawing order: key, heading, method directories, panel (0 = left, 1 = right).
GROUPS = [
    ("baseline", "Baseline inputs", ("claudecode_agent", "claudecode_api", "claudecode_direct"), 0),
    ("de_novo", "De novo crate arm", ("claudecode_agent_crate",), 1),
    ("crate_only", "Crate-only arm", ("claudecode_agent_crate_only",), 1),
    ("healthsheet_only", "Healthsheet-only arm", ("claudecode_agent_healthsheet",), 1),
    ("merged", "Merged unions (investigation artifacts)", ("claudecode_agent_merged",), 1),
    ("deterministic_ours", "Deterministic map, ours", ("rocrate_static_map",), 1),
    ("deterministic_upstream", "Deterministic map, upstream", ("rocrate_mapped",), 1),
]
OTHER_GROUP = ("other", "Other method directories", (), 1)

# Runtime classes in fixed order; the three arms own SERIES[0..2].
CLASSES = ["api", "agentic", "direct", "none", "unknown"]
CLASS_COLOR = {"api": st.ARM_COLOR["api"], "agentic": st.ARM_COLOR["agentic"],
               "direct": st.ARM_COLOR["direct"], "none": st.SERIES[3], "unknown": st.INK["muted"]}

# One bubble edge for plotted bubbles and every filled legend key, so a key of n records has the
# same visible diameter as a plotted n-record bubble; and one size for the open "no record" ring.
BUBBLE_EDGE_PT = 0.8
ABSENT_S = 10

DATE_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})(?P<suffix>[a-z]?)_(?P<rest>.+)$")
MODEL_RE = re.compile(r"^(?P<model>claude-(?:opus|sonnet|haiku)-[\d.]+)(?:-|$)")
RUNTIME_TOKEN_RE = re.compile(r"^(?P<token>api|claudecode)-")


class Disc:
    """Legend handle: a muted bubble with a hatched core, radii in points."""

    def __init__(self, outer_pt: float, core_pt: float, label: str):
        self.outer_pt, self.core_pt, self.label = outer_pt, core_pt, label

    def get_label(self) -> str:
        return self.label


class HandlerDisc(HandlerBase):
    def create_artists(self, legend, orig, xdescent, ydescent, width, height, fontsize, trans):
        cx, cy = 0.5 * width - xdescent, 0.5 * height - ydescent
        outer = Circle((cx, cy), orig.outer_pt, facecolor=st.INK["muted"], edgecolor=st.INK["surface"],
                       linewidth=BUBBLE_EDGE_PT, transform=trans)
        core = Circle((cx, cy), orig.core_pt, facecolor="none", edgecolor=st.INK["primary"],
                      hatch="//////", linewidth=0.7, transform=trans)
        return [outer, core]


def parse_label(label: str) -> dict[str, str]:
    """Heuristic family parse; every stripped token is returned so the CSV can show it."""
    m = R.REPLICATE_RE.match(label)
    config = m.group("config") if m else label
    d = DATE_RE.match(config)
    date, suffix, rest = (d.group("date"), d.group("suffix"), d.group("rest")) if d else ("", "", config)
    mm = MODEL_RE.match(rest)
    model = mm.group("model") if mm else ""
    rest = rest[mm.end():] if mm else rest
    rt = RUNTIME_TOKEN_RE.match(rest)
    token = rt.group("token") if rt else ""
    family = rest[rt.end():] if rt else rest
    return {"date": date, "date_suffix": suffix, "model_token": model, "runtime_token": token,
            "family": family, "replicate": m.group("replicate") if m else ""}


def header_mode(path: Path) -> str:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("#"):
                break
            if line.lstrip("#").strip().startswith("Mode:"):
                return line.split(":", 1)[1].strip()
    return ""


def group_of(method: str):
    for g in GROUPS:
        if method in g[2]:
            return g
    return OTHER_GROUP


def load_records() -> list[dict]:
    reference = {str(st.ROOT / j["input"]) for j in json.loads(REFERENCE.read_text())["jobs"]}
    records = []
    for run in R.discover(CONCAT):
        if run.is_core:
            continue
        for path in sorted(run.path.glob("*_d4d.yaml")):
            project = path.name[: -len("_d4d.yaml")]
            prov_path = CONCAT / f"{run.method}_core" / run.label / f"{project}_provenance.yaml"
            prov, prov_state = {}, "missing"
            if prov_path.exists():
                try:
                    prov = yaml.safe_load(prov_path.read_text(encoding="utf-8")) or {}
                    prov_state = "read" if isinstance(prov, dict) else "unreadable"
                    prov = prov if isinstance(prov, dict) else {}
                except (yaml.YAMLError, OSError, UnicodeDecodeError):
                    prov_state = "unreadable"
            model = prov.get("model") if isinstance(prov.get("model"), dict) else {}
            rt_string = model.get("agent_runtime") if isinstance(model.get("agent_runtime"), str) else ""
            rt_key = R.runtime_of(prov) if prov else None
            if rt_key:
                cls, basis = rt_key, "model.agent_runtime via runs.RUNTIME_KEYS"
            elif run.method in R.DETERMINISTIC:
                cls, basis = "none", "method in runs.DETERMINISTIC (no model call)"
            elif prov_state == "read" and prov.get("record_mode") == "derived" and not rt_string:
                cls, basis = "none", "provenance record_mode derived, no runtime"
            else:
                cls = "unknown"
                basis = {"missing": "provenance file missing", "unreadable": "provenance unreadable"}.get(
                    prov_state, f"runtime string {rt_string!r} not in RUNTIME_KEYS" if rt_string
                    else "provenance has no model.agent_runtime")
            parsed = parse_label(run.label)
            g = group_of(run.method)
            label_cond = R.condition_from_label(run.label) or ""
            hashed_cond = "" if run.method in R.DETERMINISTIC else (
                R.condition_of(run.method, run.label, project, CONCAT) or "")
            mismatch = "" if run.method in R.DETERMINISTIC else (
                R.prompt_condition_mismatch(run.method, run.label, project, CONCAT) or "")
            token_key = {"api": "api", "claudecode": "agentic"}.get(parsed["runtime_token"], "")
            sup = prov.get("canonical_superseded_by")
            records.append({
                "group": g[0], "method": run.method, "label": run.label, "project": project,
                **parsed,
                "excluded": EXCLUDED_LABELS.get(run.label, ""),
                "runtime_class": cls, "runtime_basis": basis, "agent_runtime": rt_string,
                "provenance": prov_state, "record_mode": str(prov.get("record_mode") or ""),
                "label_runtime_disagrees": bool(token_key and rt_key and token_key != rt_key),
                "reference_rescore": str(path) in reference,
                "canonical_now": "canonical" in prov,
                "superseded_by": (sup or {}).get("label", "") if isinstance(sup, dict) else "",
                "label_condition": label_cond, "hashed_prompt_condition": hashed_cond,
                "condition_mismatch": mismatch, "header_mode": header_mode(path),
                "path": str(path.relative_to(st.ROOT)),
            })
    missing_ref = reference - {str(st.ROOT / r["path"]) for r in records}
    if missing_ref:
        raise SystemExit(f"reference inputs outside the enumerated record set: {sorted(missing_ref)}")
    return records


def not_drawn_notes() -> dict:
    flat = {d.name: len(list(d.glob("*.yaml"))) for d in sorted(CONCAT.iterdir())
            if d.is_dir() and any(d.glob("*.yaml"))}
    # Backup copies of a full record (<PROJECT>_d4d.yaml.<suffix>) sitting at the top of a
    # method directory, outside any run label: not records, but record-like, so the note counts them.
    backups = {d.name: len([p for p in d.glob("*_d4d.yaml.*") if p.is_file()])
               for d in sorted(CONCAT.iterdir()) if d.is_dir() and d.name not in flat}
    backups = {k: v for k, v in backups.items() if v}
    attic = sorted(ATTIC.rglob("*_d4d.yaml")) if ATTIC.is_dir() else []
    attic_sup = [p for p in attic if ".superseded" in str(p.relative_to(ATTIC))]
    return {"flat": flat, "backups": backups, "attic_total": len(attic), "attic_superseded": len(attic_sup),
            "direct_dir_exists": (CONCAT / "claudecode_direct").is_dir()}


def build_rows(records):
    """Ordered panel lines: ('header', group) or ('row', group, family)."""
    drawn = [r for r in records if not r["excluded"]]
    by_row = defaultdict(list)
    for r in drawn:
        by_row[(r["group"], r["family"])].append(r)
    order = [g for g in GROUPS] + ([OTHER_GROUP] if any(r["group"] == "other" for r in drawn) else [])
    panels = {0: [], 1: []}
    for g in order:
        fams = sorted({f for (gk, f) in by_row if gk == g[0]},
                      key=lambda f: (min(r["date"] for r in by_row[(g[0], f)]), f))
        if not fams:
            continue
        panels[g[3]].append(("header", g))
        for f in fams:
            panels[g[3]].append(("row", g, f))
    return by_row, panels


def row_label(group_key, family, recs) -> str:
    if family:
        text = family
    else:
        text = "(label names model only)"
    if any(r["condition_mismatch"] for r in recs):
        text += " †"
    return text


def main() -> int:
    st.apply()
    records = load_records()
    notes = not_drawn_notes()
    drawn = [r for r in records if not r["excluded"]]
    by_row, panels = build_rows(records)
    n_lines = max(len(p) for p in panels.values())
    max_n = max(Counter((r["group"], r["family"], r["project"], r["runtime_class"]) for r in drawn).values())

    fig = plt.figure(figsize=(13.0, 8.4))
    top, bottom = 0.895, 0.235
    axes = [fig.add_axes([0.135, bottom, 0.325, top - bottom]), fig.add_axes([0.63, bottom, 0.325, top - bottom])]
    pitch_pt = (top - bottom) * fig.get_figheight() * 72 / n_lines
    unit = (0.9 * pitch_pt) ** 2 / max_n           # pt^2 per record: the largest bubble fills 90% of a row
    ring_pad = 3.2

    def ms(n):
        """Visible fill diameter (pt) of an n-record bubble: visible area = n * unit."""
        return (n * unit) ** 0.5

    def path_d(n):
        """Marker path diameter (pt) for an n-record bubble. The surface-coloured edge is centred on
        the path and hides BUBBLE_EDGE_PT/2 of fill on each side, so the path is widened by one edge
        width to keep the visible fill area proportional to the count at every size."""
        return ms(n) + BUBBLE_EDGE_PT

    cells, row_meta = [], []
    for pi, ax in enumerate(axes):
        lines = panels[pi]
        yt, yl = [], []
        for y, line in enumerate(lines):
            if line[0] == "header":
                g = line[1]
                present = sorted({r["method"] for r in drawn if r["group"] == g[0]})
                absent = [m for m in g[2] if m not in present and not (CONCAT / m).is_dir()]
                head = f"{g[1]}  ·  " + ", ".join(f"{m}/" for m in present)
                if absent:
                    head += "  (" + ", ".join(f"{m}/ absent" for m in absent) + ")"
                ax.text(-0.5, y + 0.12, head, ha="left", va="center", fontsize=7.6, fontweight="bold",
                        color=st.INK["secondary"], zorder=2,
                        bbox=dict(facecolor=st.INK["surface"], edgecolor="none", pad=0.8))
                if y:
                    ax.axhline(y - 0.5, color=st.INK["grid"], linewidth=0.6, zorder=0)
                continue
            _, g, fam = line
            recs = by_row[(g[0], fam)]
            yt.append(y); yl.append(row_label(g[0], fam, recs))
            labels = sorted({r["label"] for r in recs})
            row_meta.append({
                "panel": pi, "group": g[0], "family": fam, "row_label": yl[-1], "y": y,
                "records": len(recs), "labels": len(labels),
                "first_date": min(r["date"] for r in recs), "last_date": max(r["date"] for r in recs),
                "methods": ";".join(sorted({r["method"] for r in recs})),
                "runtime_classes": ";".join(c for c in CLASSES if any(r["runtime_class"] == c for r in recs)),
                "label_conditions": ";".join(sorted({r["label_condition"] or "none" for r in recs})),
                "hashed_prompt_conditions": ";".join(sorted({r["hashed_prompt_condition"] or "none" for r in recs})),
                "condition_mismatch_records": sum(1 for r in recs if r["condition_mismatch"]),
                "header_modes": ";".join(sorted({r["header_mode"] or "none" for r in recs})),
                "superseded": sum(1 for r in recs if r["superseded_by"]),
                "reference_rescore": sum(1 for r in recs if r["reference_rescore"]),
            })
            ax.text(5.05, y, str(len(recs)), ha="right", va="center", fontsize=7.2, color=st.INK["secondary"])
            ax.text(5.55, y, str(len(labels)), ha="right", va="center", fontsize=7.2, color=st.INK["secondary"])
            for j, proj in enumerate(PROJECT_ORDER):
                here = [r for r in recs if r["project"] == proj]
                present = [c for c in CLASSES if any(r["runtime_class"] == c for r in here)]
                if not present:
                    ax.scatter([j], [y], s=ABSENT_S, facecolors="none", edgecolors=st.INK["axis"], linewidths=0.7, zorder=2)
                    cells.append({"panel": pi, "group": g[0], "family": fam, "project": proj,
                                  "runtime_class": "no record", "records": 0, "superseded": 0,
                                  "reference_rescore": 0, "canonical_now": 0, "x": j, "y": y, "labels": ""})
                    continue
                offs = [-0.1] if len(present) == 1 else [-0.32 + 0.52 * k / (len(present) - 1) for k in range(len(present))]
                for c, dx in zip(present, offs):
                    sub = [r for r in here if r["runtime_class"] == c]
                    n = len(sub)
                    k_sup = sum(1 for r in sub if r["superseded_by"])
                    k_ref = sum(1 for r in sub if r["reference_rescore"])
                    d = path_d(n)
                    x = j + dx
                    ax.scatter([x], [y], s=d ** 2, color=CLASS_COLOR[c], edgecolors=st.INK["surface"],
                               linewidths=BUBBLE_EDGE_PT, zorder=3)
                    if k_sup:
                        ax.scatter([x], [y], s=k_sup * unit, facecolors="none", edgecolors=st.INK["primary"],
                                   hatch="//////", linewidths=0.7, zorder=4)
                    pad = 0.0
                    if k_ref:
                        ax.scatter([x], [y], s=(d + ring_pad) ** 2, facecolors="none",
                                   edgecolors=st.INK["primary"], linewidths=1.3, zorder=5)
                        pad = ring_pad / 2
                    ax.annotate(str(n), (x, y), xytext=(d / 2 + pad + 1.8, 0), textcoords="offset points",
                                ha="left", va="center", fontsize=6.6, color=st.INK["secondary"], zorder=6)
                    cells.append({"panel": pi, "group": g[0], "family": fam, "project": proj,
                                  "runtime_class": c, "records": n, "superseded": k_sup,
                                  "reference_rescore": k_ref, "canonical_now": sum(1 for r in sub if r["canonical_now"]),
                                  "x": round(x, 3), "y": y, "labels": ";".join(sorted({r["label"] for r in sub}))})
        ax.set_ylim(n_lines - 0.5, -0.9)
        ax.set_xlim(-0.55, 5.7)
        ax.set_yticks(yt); ax.set_yticklabels(yl)
        for t in ax.get_yticklabels():
            t.set_color(st.INK["primary"])
        ax.set_xticks(range(len(PROJECT_ORDER)))
        ax.set_xticklabels([PROJECT_LABEL[p] for p in PROJECT_ORDER])
        ax.xaxis.tick_top()
        ax.tick_params(axis="both", length=0)
        for t in ax.get_xticklabels():
            t.set_color(st.INK["secondary"]); t.set_fontweight("bold")
        for side in ("left", "bottom", "top", "right"):
            ax.spines[side].set_visible(False)
        # cell separators over the occupied rows only, so a bubble pair reads as one cell
        ax.vlines([j - 0.5 for j in range(len(PROJECT_ORDER) + 1)], -0.5, len(lines) - 0.5,
                  color=st.INK["grid"], linewidth=0.5, zorder=0)
        ax.text(5.05, -1.35, "records", ha="right", va="bottom", fontsize=7, color=st.INK["muted"], clip_on=False)
        ax.text(5.55, -1.35, "labels", ha="right", va="bottom", fontsize=7, color=st.INK["muted"], clip_on=False)

    # ---- legend (bubble classes, size key, rings, hatch, absence) ----
    cls_n = Counter(r["runtime_class"] for r in drawn)
    rt_strings = defaultdict(set)
    for r in drawn:
        if r["agent_runtime"]:
            rt_strings[r["runtime_class"]].add(r["agent_runtime"])
    inv = defaultdict(list)
    for s_, k_ in R.RUNTIME_KEYS.items():
        inv[k_].append(s_)

    def rt_name(k):
        seen = sorted(rt_strings.get(k) or [])
        if seen:
            return "agent_runtime " + " / ".join(f'"{v}"' for v in seen)
        return "RUNTIME_KEYS entry " + " / ".join(f'"{v}"' for v in inv[k])

    def bubble_key(n, color, label):
        """Legend marker drawn exactly like a plotted bubble of n records: Line2D markersize m and
        scatter s=m**2 share one path, and the surface-coloured edge matches BUBBLE_EDGE_PT."""
        return Line2D([], [], marker="o", linestyle="none", markersize=path_d(n), color=color,
                      markeredgewidth=BUBBLE_EDGE_PT, markeredgecolor=st.INK["surface"], label=label)

    def plural(n, word):
        return f"{n} {word}" + ("" if n == 1 else "s")
    unknown_basis = Counter(r["runtime_basis"] for r in drawn if r["runtime_class"] == "unknown")
    none_basis = Counter(r["runtime_basis"] for r in drawn if r["runtime_class"] == "none")
    h1 = [
        bubble_key(3, CLASS_COLOR["api"], f"api runtime (API arm), {rt_name('api')}: {cls_n['api']} records"),
        bubble_key(3, CLASS_COLOR["agentic"],
                   f"agentic runtime (agentic arm), {rt_name('agentic')}: {cls_n['agentic']} records"),
        Line2D([], [], marker="o", linestyle="none", markersize=path_d(3), markerfacecolor="none",
               markeredgecolor=CLASS_COLOR["direct"], markeredgewidth=1.2,
               label=f"direct runtime (direct arm: Claude Code on subscription), {rt_name('direct')}: "
                     f"{cls_n['direct']} records"
                     + ("" if notes["direct_dir_exists"] else ", claudecode_direct/ absent")),
        bubble_key(3, CLASS_COLOR["none"],
                   f"no generation runtime (deterministic map or merge-derived): {cls_n['none']} records"),
        bubble_key(3, CLASS_COLOR["unknown"],
                   f"runtime unknown ({'; '.join(unknown_basis) if len(unknown_basis) == 1 else '; '.join(f'{b}: {n}' for b, n in unknown_basis.items()) or 'none'}): "
                   f"{plural(cls_n['unknown'], 'record')}"),
    ]
    ref_cells = [c for c in cells if c["reference_rescore"]]
    ref_ks = sorted({c["reference_rescore"] for c in ref_cells})
    ref_txt = f"{ref_ks[0]}" if len(ref_ks) == 1 else f"{ref_ks[0]}–{ref_ks[-1]}"
    n_ref = sum(1 for r in drawn if r["reference_rescore"])
    n_sup = sum(1 for r in drawn if r["superseded_by"])
    h2 = [
        bubble_key(1, st.INK["muted"], "1 full record"),
        bubble_key(5, st.INK["muted"], "5 full records"),
        bubble_key(max_n, st.INK["muted"], f"{max_n} full records (largest cell); area proportional to count"),
        Line2D([], [], marker="o", linestyle="none", markersize=path_d(3) + ring_pad, markerfacecolor="none",
               markeredgecolor=st.INK["primary"], markeredgewidth=1.3,
               label=f"ring: cell holds reference-rescore inputs ({n_ref} records, {ref_txt} per ringed cell)"),
        Disc(path_d(4) / 2, ms(2) / 2,
             label=f"hatched core: records whose canonical mark was superseded\n(provenance canonical_superseded_by; {n_sup} records), same area scale"),
        Line2D([], [], marker="o", linestyle="none", markersize=ABSENT_S ** 0.5, markerfacecolor="none",
               markeredgecolor=st.INK["axis"], markeredgewidth=0.7, label="no full record for this project and family"),
    ]
    # Fill legend: in the left panel's unused lower rows when there are enough of them, else the bottom band.
    spare = n_lines - len(panels[0])
    band_top = bottom - 0.02                          # top of the bottom band (size legend and note)
    if spare >= 5:
        y0 = fig.transFigure.inverted().transform(axes[0].transData.transform((0, len(panels[0]) + 0.1)))[1]
        leg1_anchor, leg2_anchor, note_x = (0.012, y0), (0.012, band_top), 0.555
    else:
        leg1_anchor, leg2_anchor, note_x = (0.012, band_top), (0.36, band_top), 0.64
    leg1 = fig.legend(handles=h1, loc="upper left", bbox_to_anchor=leg1_anchor, ncol=1, fontsize=7.2,
                      handletextpad=0.5, labelspacing=0.55, borderaxespad=0, title="Fill: runtime class from provenance",
                      title_fontsize=7.4, alignment="left")
    leg2 = fig.legend(handles=h2, handler_map={Disc: HandlerDisc()}, loc="upper left", bbox_to_anchor=leg2_anchor, ncol=2, columnspacing=1.6, fontsize=7.2,
                      handletextpad=0.5, labelspacing=0.45, handleheight=path_d(max_n) / 7.2 + 0.1, handlelength=2.4, borderaxespad=0, title="Size, ring, hatch",
                      title_fontsize=7.4, alignment="left")
    for leg in (leg1, leg2):
        leg.get_title().set_color(st.INK["secondary"]); leg.get_title().set_fontweight("bold")

    # ---- note ----
    mismatch = [r for r in drawn if r["condition_mismatch"]]
    mm_labels = sorted({r["label"] for r in mismatch})
    mm_claim = sorted({r["label_condition"] for r in mismatch})
    mm_hash = sorted({r["hashed_prompt_condition"] for r in mismatch})
    implied = sorted({(r["family"], r["hashed_prompt_condition"]) for r in drawn
                      if not r["label_condition"] and r["hashed_prompt_condition"]})
    no_token = sorted({r["header_mode"] for r in drawn if r["group"] == "baseline" and not r["family"]})
    disagree = sum(1 for r in drawn if r["label_runtime_disagrees"])
    excluded = [r for r in records if r["excluded"]]
    flat = notes["flat"]
    mm_configs = defaultdict(list)
    for lab in mm_labels:
        m_ = R.REPLICATE_RE.match(lab)
        mm_configs[m_.group("config") if m_ else lab].append(f"rep{m_.group('replicate')}" if m_ else "")
    mm_txt = "; ".join(f"{c} {', '.join(r for r in reps if r)}".strip() for c, reps in mm_configs.items())
    paras = [
        "Counts are an archive of every full record on disk (reruns, canaries and single-project repairs "
        "included), not balanced experimental sample sizes; a bigger bubble is not a better-supported condition.",
        "Rows are run families parsed from labels (heuristic: date, replicate, model and runtime tokens removed)"
        + (f"; '(label names model only)' records carry header Mode '{'; '.join(no_token)}'." if no_token else "."),
        f"\u2020 {len(mismatch)} records ({mm_txt}) are labelled {'/'.join(mm_claim)} but hash the "
        f"{'/'.join(mm_hash)} prompt file (#420)."
        + (" Families naming no registered condition whose records hash one: "
           + ", ".join(f"{f} hashes {c}" for f, c in implied) + "." if implied else ""),
        f"Label runtime token contradicts the provenance runtime in {disagree} records. Excluded: "
        f"{', '.join(sorted({r['label'] for r in excluded}))} ({len(excluded)} record).",
        f"Not drawn: {sum(flat.values())} YAML files in {len(flat)} flat directories without run labels "
        f"({', '.join(f'{k}/' for k in flat)}); "
        + "".join(f"{n} backup {'copy' if n == 1 else 'copies'} of a full record (*_d4d.yaml.*) at the top of "
                  f"{k}/, outside any run label; " for k, n in notes["backups"].items())
        + f"{notes['attic_total']} archived full records in "
        f"data/ATTIC, {notes['attic_superseded']} of them in .superseded-* copies.",
    ]
    note = "\n".join(textwrap.fill(p_, 140 if note_x < 0.6 else 110) for p_ in paras)
    fig.text(note_x, band_top, note, fontsize=6.8, color=st.INK["secondary"], ha="left", va="top", linespacing=1.4)

    fig.suptitle("Which generation conditions have full records: run family × project, by recorded runtime",
                 x=0.012, ha="left", fontsize=11, fontweight="bold", y=0.985)
    n_by_method = Counter(r["method"] for r in drawn)
    basis = (f"Record set: {len(drawn)} full records in runs.discover() label directories under data/d4d_concatenated "
             f"({', '.join(f'{m} {n}' for m, n in sorted(n_by_method.items()))}), gate_test excluded; runtime from "
             "<method>_core provenance; reference = reference_rescore_2026-09-12 manifest inputs")
    rec_rows = [{k: v for k, v in r.items()} for r in records]
    st.save(fig, "fig16_design_coverage", {"main": cells, "rows": row_meta, "records": rec_rows}, basis)
    print(f"records drawn {len(drawn)}, excluded {len(excluded)}, reference {n_ref}, superseded {n_sup}, "
          f"classes {dict(cls_n)}, none-basis {dict(none_basis)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
