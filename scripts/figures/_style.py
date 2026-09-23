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
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:  # pragma: no cover
        return "unknown"


def footer(fig, basis: str) -> None:
    """One line at the bottom-left stating the record set and repository state."""
    fig.text(0.01, 0.005, f"{basis}  |  data-sheets-schema {commit()}",
             fontsize=6.5, color=INK["muted"], ha="left", va="bottom")


def save(fig, stem: str, tables: dict[str, list[dict]] | None = None, basis: str = "") -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
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
    return svg


def hairline_grid(ax, axis: str = "y") -> None:
    ax.grid(True, axis=axis, color=INK["grid"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
