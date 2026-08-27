#!/usr/bin/env python
"""Consolidated cross-arm comparison: one table, one set of figures, regenerated
from the provenance records rather than transcribed.

Why a script and not a table: every hand-made arm table in notes/ has needed
a review round to correct a copied baseline or a mis-summed cell (#655,
#676). The numbers here are read from the records at run time, so the table
cannot drift from the data it describes, and the same bases apply to every
arm.

Bases, stated once and printed into the output:

- **pair errors, report findings, grounding** come from each record's own
  blocks. Pair consistency is a deterministic artifact check. Grounding is
  measured against the record's declared bundle — for every arm shown, the
  record's `inputs.bundle_md5` still matches the bundle on disk, and the
  block was written either by the run or by `backfill-checks` against that
  same bundle (the record's `recorded_by` says which).
- **form metrics** (British spellings, undeclared prefixes, organisational
  fragments, GC label variants) are recomputed live from the artifacts with
  the current instrument (`grounding.form_facts`), so the basis does not
  depend on when each record was last backfilled. As of this writing the
  stored `form` blocks agree with the live recompute on every field for all
  36 records (they were all re-backfilled under instrument v2.1 on
  2026-08-22); the recompute is what keeps that true after the next
  instrument change. **GC label variants are anachronistic for the v4 and
  22c arms**: the manifest `naming:` declaration they are counted against
  was decided 2026-08-22, after the v4 arm ran and the day the 22c arm did.
- **rubric scores** come from `data/evaluation_llm/rubric{10,20}_semantic/
  label_aware/`, matched by label, and only exist for canonical (or
  would-be canonical) records. Applicability (N/A) is itself evaluator
  output, so adjusted maxima can differ between evaluations of comparable
  records; points and adjusted maximum are both shown.
- **spend is deliberately absent**: `api_usage` (billed input/output) and
  `run_observed` (cache-inclusive runner totals) are different quantities and
  must never sit in one column (#400).

Usage:
    poetry run python scripts/arm_comparison.py            # writes md + png
    poetry run python scripts/arm_comparison.py --no-figures
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
# form_facts → declared_naming() reads the manifest cwd-relative (#673); run
# from anywhere else and every GC count silently becomes 0.
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.grounding import form_facts  # noqa: E402
CONCAT = ROOT / "data" / "d4d_concatenated"
EVAL_DIRS = {
    "rubric10": ROOT / "data" / "evaluation_llm" / "rubric10_semantic" / "label_aware",
    "rubric20": ROOT / "data" / "evaluation_llm" / "rubric20_semantic" / "label_aware",
}
RUBRIC_MAX = {"rubric10": 50, "rubric20": 88}
OUT_MD = ROOT / "notes" / "arm_comparison.md"
OUT_FIG = ROOT / "notes" / "figures"

PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE")
METHOD = "claudecode_agent"

# (key, display, label prefix, runtime, role). `role` says how the arm is
# shown: "worst" collapses replicates to the per-project worst (the canary
# gate's baseline convention), "reps" shows all three.
ARMS = (
    ("v4", "v4 API (2026-08-13)", "2026-08-13_claude-opus-5-api-generic-v4",
     "Claude API via CBORG", "worst"),
    ("v5api", "v5 API (2026-08-22c)", "2026-08-22c_claude-opus-5-api-generic-v5",
     "Claude API via CBORG", "reps"),
    ("v5agentic", "v5 agentic (2026-08-24)",
     "2026-08-24_claude-opus-5-claudecode-generic-v5", "Claude Code", "reps"),
)

# metric key -> (display, source, higher-is-worse, caveat)
METRICS: dict[str, tuple[str, str, bool, str]] = {
    "ungrounded": ("ungrounded identifiers", "record", True,
                   "grounding.distinct.absent as measured against the bundle the run saw"),
    "orgfrag": ("organisational fragments", "live", True, ""),
    "undeclared": ("undeclared prefixes", "live", True,
                   "classification v2.1 (#671): ark: and registered URN NIDs excluded"),
    "british": ("British spellings", "live", True,
                "instrument v2.1 (#653). Coupled with pair errors on the API arm: a "
                "full/core spelling split counts once per shared slot in both (#675)"),
    "pair": ("pair errors", "record", True,
             "deterministic artifact check, comparable across arms; the procedures "
             "that reduce it differ by runtime (#689) and it is coupled with British "
             "spellings (#675)"),
    "report": ("report findings", "record", True,
               "claims_checked counts backticked removal claims only; false-schema-claim "
               "findings come from a separate scan that counts nothing. A 0 with "
               "claims_checked 0 is therefore unmeasured on the removal form, not held "
               "(#684) — shown as 0ᵘ; any finding > 0 is measured"),
    "minted": ("minted fragments (reported)", "record", False,
               "reported-only; every fragment hangs off an attested base wherever "
               "ungrounded is 0. Appetite varies 3→130 within one project (#685)"),
    "gc": ("GC label variants (reported)", "live", True,
           "reported-only; counted against the manifest naming declaration decided "
           "2026-08-22, so anachronistic for the v4 arm and same-day for 22c. For VOICE "
           "the count is the dataset's own PhysioNet title, lawful under the "
           "proper-noun carve-out (#674)"),
}


def load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def run_metrics(prefix: str, rep: int, project: str) -> dict[str, Any] | None:
    label = f"{prefix}_rep{rep}"
    core_dir = CONCAT / f"{METHOD}_core" / label
    full = CONCAT / METHOD / label / f"{project}_d4d.yaml"
    core = core_dir / f"{project}_d4d_core.yaml"
    prov = core_dir / f"{project}_provenance.yaml"
    if not (full.exists() and core.exists() and prov.exists()):
        return None
    rec = load(prov)
    pc = rec.get("pair_consistency") or {}
    rc = rec.get("report_claims") or {}
    g = (rec.get("grounding") or {}).get("distinct") or {}

    # Live form recomputation under the current instrument.
    form = form_facts(full, core)

    def form_get(*keys: str) -> int | None:
        for k in keys:
            if form.get(k) is not None:
                v = form[k]
                return sum(v.values()) if isinstance(v, dict) else int(v)
        return None

    return {
        "label": label,
        "ungrounded": g.get("absent"),
        "minted": g.get("minted_fragment"),
        "pair": pc.get("errors"),
        "report": len(rc.get("findings") or []) if rc else None,
        "claims_checked": rc.get("claims_checked"),
        "british": form_get("british_spellings"),
        "undeclared": form_get("undeclared_prefix_occurrences", "undeclared_prefixes"),
        "orgfrag": form_get("organisational_fragments"),
        "gc": form_get("gc_label_variant_occurrences", "gc_label_variants"),
        "runtime": (rec.get("model") or {}).get("agent_runtime"),
    }


def rubric_scores(prefix: str, project: str, rubric: str = "rubric10") -> list[dict[str, Any]]:
    out = []
    evals = EVAL_DIRS[rubric]
    if not evals.exists():
        return out
    for path in sorted(evals.glob(f"{project}_*_evaluation.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        if str(d.get("label", "")).startswith(prefix):
            s = d.get("overall_score") or {}
            out.append({"label": d["label"], "total": s.get("total_points"),
                        "max": s.get("max_points"),
                        "adjusted_max": s.get("adjusted_max_points"),
                        "pct": s.get("normalized_percentage"),
                        "evaluator": (d.get("model") or {}).get("evaluator_model"),
                        "file": path.name})
    return out


def collect() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """arm -> project -> [rep metrics]"""
    data: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for key, _disp, prefix, _rt, _role in ARMS:
        data[key] = {}
        for p in PROJECTS:
            reps = [m for rep in (1, 2, 3) if (m := run_metrics(prefix, rep, p))]
            data[key][p] = reps
    return data


def fmt(m: dict[str, Any], metric: str) -> str:
    v = m.get(metric)
    if v is None:
        return "–"
    # A finding is evidence the checker parsed something; only a 0 with zero
    # parsed claims is unmeasured rather than held (#684).
    if metric == "report" and v == 0 and (m.get("claims_checked") or 0) == 0:
        return f"{v}ᵘ"
    return str(v)


def worst(reps: list[dict[str, Any]], metric: str) -> str:
    """Per-project collapse for the baseline column: the worst value where
    the metric has a direction, the max (labelled as such in the header) for
    reported-only metrics that do not."""
    vals = [r[metric] for r in reps if r.get(metric) is not None]
    if not vals:
        return "–"
    w = max(vals)
    if metric == "report" and w == 0 and all((r.get("claims_checked") or 0) == 0 for r in reps):
        return f"{w}ᵘ"
    return str(w)


def write_markdown(data, scores) -> None:
    lines = ["# Cross-arm comparison (regenerated)", "",
             f"Generated by `scripts/arm_comparison.py` from the provenance records under "
             f"`data/d4d_concatenated/`; do not edit by hand — re-run the script.", "",
             "## Bases", "",
             "- pair errors, report findings, grounding: each record's own blocks. Pair "
             "is a deterministic artifact check; grounding is against the record's "
             "declared bundle, whose md5 still matches disk for every arm shown "
             "(`recorded_by` says whether the run or backfill-checks wrote it).",
             "- British spellings, undeclared prefixes, organisational fragments, GC "
             "label variants: **recomputed live** from the artifacts under the current "
             "instrument (`grounding.form_facts`), so the basis does not depend on when "
             "a record was last backfilled. Stored `form` blocks are not read (today "
             "they agree with the recompute on all 36 records). GC variants are counted "
             "against a naming declaration decided 2026-08-22 — anachronistic for v4.",
             "- rubric scores: `data/evaluation_llm/rubric{10,20}_semantic/label_aware/`, "
             "same evaluator for every arm shown; N/A exclusions are evaluator "
             "judgements, so adjusted maxima can differ between comparable records.",
             "- spend: absent by design — `api_usage` and `run_observed` are different "
             "quantities (#400).", "",
             "Arms: " + "; ".join(f"**{d}** — `{pfx}_rep{{1,2,3}}`, {rt}"
                                   + (" (shown as per-project worst; max for reported-only metrics)" if role == "worst" else "")
                                   for _k, d, pfx, rt, role in ARMS), ""]

    lines += ["## Deterministic metrics — three replicates per cell", "",
              "| metric | project | " + " | ".join(d for _k, d, *_ in ARMS) + " |",
              "|---|---|" + "|".join("---" for _ in ARMS) + "|"]
    for mk, (disp, _src, _hiw, _cav) in METRICS.items():
        for p in PROJECTS:
            cells = []
            for key, _d, _pfx, _rt, role in ARMS:
                reps = data[key][p]
                cells.append(worst(reps, mk) if role == "worst"
                             else ",".join(fmt(r, mk) for r in reps) or "–")
            lines.append(f"| {disp} | {p} | " + " | ".join(cells) + " |")
    lines += ["", "ᵘ = unmeasured: the report-claims checker parsed zero claims (#684).", ""]

    lines += ["## Per-metric caveats (attached, not footnoted elsewhere)", ""]
    for mk, (disp, src, _hiw, cav) in METRICS.items():
        basis = "record block" if src == "record" else "live recompute, current instrument"
        lines.append(f"- **{disp}** — {basis}." + (f" {cav}." if cav else ""))
    lines.append("")

    for rubric, rscores in scores.items():
        lines += [f"## {rubric.capitalize()}-semantic scores (canonical / would-be canonical records only)", "",
                  "| project | " + " | ".join(d for _k, d, *_ in ARMS) + " |",
                  "|---|" + "|".join("---" for _ in ARMS) + "|"]
        for p in PROJECTS:
            cells = []
            for key, _d, pfx, _rt, _role in ARMS:
                ss = rscores[key][p]
                cells.append("; ".join(
                    f"{s['total']}/{s['adjusted_max'] or s['max']} ({s['pct']}%, {s['label'].rsplit('_', 1)[-1]})"
                    for s in ss) or "–")
            lines.append(f"| {p} | " + " | ".join(cells) + " |")
        lines.append("")
    evaluators = sorted({s["evaluator"] for rs in scores.values() for arm in rs.values() for ss in arm.values() for s in ss if s.get("evaluator")})
    lines += [f"Evaluator model(s) recorded: {', '.join(evaluators) or 'none'}. "
              "Scores are shown as points / adjusted maximum after N/A exclusions; "
              "raw points are comparable within a rubric, percentages are "
              "denominator-sensitive. No gold standard exists (#177); the rubrics are "
              "not domain-neutral (#627); rubric20's N/A convention is #155's.", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_MD.relative_to(ROOT)}")


def write_figures(data, scores) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUT_FIG.mkdir(parents=True, exist_ok=True)
    colors = {"v4": "#9e9e9e", "v5api": "#4e79a7", "v5agentic": "#f28e2b"}

    # One figure per metric: 4 project panels, bars per arm (worst) or per rep.
    for mk, (disp, _src, _hiw, cav) in METRICS.items():
        fig, axes = plt.subplots(1, len(PROJECTS), figsize=(13, 3.4), sharey=True)
        for ax, p in zip(axes, PROJECTS):
            xs, hs, cs, labels = [], [], [], []
            x = 0
            for key, d, _pfx, _rt, role in ARMS:
                reps = data[key][p]
                if role == "worst":
                    vals = [r[mk] for r in reps if r.get(mk) is not None]
                    if vals:
                        xs.append(x); hs.append(max(vals)); cs.append(colors[key]); labels.append("worst")
                        x += 1
                else:
                    for r in reps:
                        if r.get(mk) is None:
                            continue
                        xs.append(x); hs.append(r[mk]); cs.append(colors[key])
                        labels.append(r["label"].rsplit("_", 1)[-1] + ("ᵘ" if mk == "report" and r[mk] == 0 and not r.get("claims_checked") else ""))
                        x += 1
                x += 0.6
            ax.bar(xs, hs, color=cs, width=0.8)
            ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=7, rotation=60)
            ax.set_title(p, fontsize=10)
            ax.spines[["top", "right"]].set_visible(False)
        handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k]) for k, *_ in ARMS]
        fig.legend(handles, [d for _k, d, *_ in ARMS], loc="upper right", fontsize=8, ncol=3, frameon=False)
        fig.suptitle(disp, x=0.02, ha="left", fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, 0.9))
        out = OUT_FIG / f"arm_comparison_{mk}.png"
        fig.savefig(out, dpi=150); plt.close(fig)
        print(f"wrote {out.relative_to(ROOT)}")

    for rubric, rscores in scores.items():
        _rubric_figure(rubric, rscores, colors)


def _rubric_figure(rubric, scores, colors) -> None:
    import matplotlib.pyplot as plt
    # Rubric scores: raw points per project per arm (canonicals only).
    fig, ax = plt.subplots(figsize=(8, 3.6))
    arm_keys = [k for k, *_ in ARMS if any(scores[k][p] for p in PROJECTS)]
    if not arm_keys:
        plt.close(fig); return
    absent = [d for k, d, *_ in ARMS if k not in arm_keys]
    for k in arm_keys:
        for p in PROJECTS:
            if len(scores[k][p]) > 1:
                print(f"warning: {len(scores[k][p])} evaluations match {k}/{p}; "
                      f"figure shows the first by filename", file=sys.stderr)
    width = 0.8 / max(1, len(arm_keys))
    for i, key in enumerate(arm_keys):
        vals = [(scores[key][p][0]["total"] if scores[key][p] else 0) for p in PROJECTS]
        xs = [j + i * width for j in range(len(PROJECTS))]
        ax.bar(xs, vals, width=width, color=colors[key],
               label=dict((k, d) for k, d, *_ in ARMS)[key])
        # Points are drawn against the unadjusted maximum; where an evaluation
        # excluded N/A questions its adjusted maximum is written on the bar so
        # the visual height is not read as a percentage (#696 review).
        for x, p, v in zip(xs, PROJECTS, vals):
            if scores[key][p]:
                s0 = scores[key][p][0]
                adj = s0.get("adjusted_max") or s0.get("max")
                ax.text(x, v + 0.5, f"{v}/{adj}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks([j + width * (len(arm_keys) - 1) / 2 for j in range(len(PROJECTS))])
    ax.set_xticklabels(PROJECTS); ax.set_ylim(0, RUBRIC_MAX[rubric] * 1.08)
    ax.set_ylabel(f"{rubric}-semantic points (axis: unadjusted max {RUBRIC_MAX[rubric]})")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=len(arm_keys))
    ax.set_title(f"{rubric.capitalize()}-semantic, canonical records (same evaluator model)"
                 + (f" — no evaluations exist for: {', '.join(absent)}" if absent else ""),
                 fontsize=9, loc="left")
    fig.tight_layout()
    out = OUT_FIG / f"arm_comparison_{rubric}.png"
    fig.savefig(out, dpi=150); plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()
    data = collect()
    scores = {rubric: {key: {p: rubric_scores(pfx, p, rubric) for p in PROJECTS}
                       for key, _d, pfx, *_ in ARMS} for rubric in EVAL_DIRS}
    missing = [(k, p) for k in data for p in PROJECTS if not data[k][p]]
    if missing:
        print(f"note: no complete runs for {missing}", file=sys.stderr)
    write_markdown(data, scores)
    if not args.no_figures:
        write_figures(data, scores)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
