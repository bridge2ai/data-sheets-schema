"""Shared palette, matplotlib style, and save helper for the #2303 figure set.

Palette: the dataviz reference instance (validated with its validator on
2026-09-23: 8 categorical slots pass the adjacent gates in light mode; the first
three pass all-pairs; aqua/yellow/magenta need direct labels for contrast).
Color rules used throughout the set:
- categorical hues in fixed slot order, never cycled; arms own slots 1-3;
- sequential = one blue hue, light->dark; diverging = blue <-> red with gray mid;
- status colors are reserved for state and always carry a label;
- text wears ink tokens, never the series color.
"""
from __future__ import annotations

import csv
import os
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notes" / "figures" / "set_2303"

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
       "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
ORDINAL = SEQ[3:]                      # start at step 250 so the light end clears 2:1
DIVERGING = {"neg": "#e34948", "mid": "#f0efec", "pos": "#2a78d6"}
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781",
       "grid": "#e1e0d9", "axis": "#c3c2b7", "surface": "#fcfcfb", "mid": "#f0efec"}
ARM_COLOR = {"api": SERIES[0], "agentic": SERIES[1], "direct": SERIES[2]}
ARM_LABEL = {"api": "API arm (Messages SDK via CBORG)",
             "agentic": "Agentic arm (Claude Code via proxy)",
             "direct": "Direct arm (Claude Code, subscription)"}
PROJECTS = ["AI_READI", "CHORUS", "CM4AI", "VOICE"]
HATCH = "////"                          # the one texture, 45 degrees


def apply() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 8.5, "axes.titlesize": 9.5, "axes.labelsize": 8.5,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
        "axes.edgecolor": INK["axis"], "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": INK["muted"], "ytick.color": INK["muted"],
        "axes.labelcolor": INK["secondary"], "text.color": INK["primary"],
        "axes.titlecolor": INK["primary"], "axes.titleweight": "bold", "axes.titlelocation": "left",
        "grid.color": INK["grid"], "grid.linewidth": 0.6, "axes.grid": False,
        "figure.facecolor": INK["surface"], "axes.facecolor": INK["surface"],
        "savefig.facecolor": INK["surface"],
        "svg.fonttype": "none",          # keep text as text in the SVG
        "legend.frameon": False,
        "lines.linewidth": 2, "lines.markersize": 6,
        "patch.linewidth": 0,
    })


def commit() -> str:
    """Short HEAD, with "-dirty" appended when scripts/figures or the data tree has uncommitted changes."""
    try:
        head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no", "--", "scripts/figures", "data", "notes/reference_rescore_2026-09-12_cborg_runtime", "notes/claudecode_direct", "notes/matched_cborg_2026-09-13"],
                                        cwd=ROOT, text=True).strip()
        return head + ("-dirty" if dirty else "")
    except Exception:  # pragma: no cover
        return "unknown"


def footer(fig, basis: str) -> None:
    """One line at the bottom-left stating the record set and repository state."""
    fig.text(0.01, 0.005, f"{basis}  |  data-sheets-schema {commit()}",
             fontsize=6.5, color=INK["muted"], ha="left", va="bottom")


BARE = OUT / "bare"
BARE_MAX_MEGAPIXELS = 20.0            # Google Docs refuses inline images above 25 MP
BARE_MAX_DPI = 300


def save_bare(fig, stem: str) -> None:
    """Title-free, footer-free SVG and PNG for embedding in a document whose legend
    carries the title and record set. Called before the footer is drawn."""
    BARE.mkdir(parents=True, exist_ok=True)
    sup = getattr(fig, "_suptitle", None)
    visible = sup.get_visible() if sup is not None else None
    if sup is not None:
        sup.set_visible(False)
    try:
        fig.savefig(BARE / f"{stem}.svg", format="svg", bbox_inches="tight", pad_inches=0.1)
        w, h = fig.get_size_inches()
        dpi = int(min(BARE_MAX_DPI, (BARE_MAX_MEGAPIXELS * 1e6 / (w * h)) ** 0.5))
        fig.savefig(BARE / f"{stem}.png", format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.1)
    finally:
        if sup is not None:
            sup.set_visible(visible)


def save(fig, stem: str, tables: dict[str, list[dict]] | None = None, basis: str = "") -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    save_bare(fig, stem)
    if basis:
        footer(fig, basis)
    svg = OUT / f"{stem}.svg"
    fig.savefig(svg, format="svg", bbox_inches="tight", pad_inches=0.15)
    preview = os.environ.get("FIG_PREVIEW_DIR")
    if preview:
        Path(preview).mkdir(parents=True, exist_ok=True)
        fig.savefig(Path(preview) / f"{stem}.png", dpi=110, bbox_inches="tight", pad_inches=0.15)
    for name, rows in (tables or {}).items():
        if not rows:
            continue
        path = OUT / (f"{stem}.csv" if name == "main" else f"{stem}_{name}.csv")
        keys = list(rows[0].keys())
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
    print(f"wrote {svg.relative_to(ROOT)}")
    plt.close(fig)
    return svg


def hairline_grid(ax, axis: str = "y") -> None:
    ax.grid(True, axis=axis, color=INK["grid"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
