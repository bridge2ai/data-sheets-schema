#!/usr/bin/env python
"""#2292: schematic of the generation arms, the four-phase pipeline, the
deterministic crate route, the evaluation branches, and where hashes bind identity.

Nothing here is measured; every box is a documented step and the CSV names the
file that documents it. Model-call steps are filled; steps that call no model
are outlined. The direct arm is registered but has no accepted run, so it is
drawn hollow and dashed (its first canary completed generation but was disqualified,
notes/claudecode_direct/CHORUS_direct_rep1_2026-09-23_stopped.md). Locks mark hash bindings the provenance modules record.

Sources checked on 2026-09-23 (see BOXES for the per-box file):
- .claude/commands/d4d-full-core.md (the four phases, what each one calls)
- src/data_sheets_schema/api_runner.py (PHASES, PHASE_MAX_TOKENS: which phases are model calls)
- src/data_sheets_schema/runs.py (ARM_BY_METHOD, RUNTIME_KEYS)
- notes/claudecode_direct/README.md and CHORUS_direct_rep1_2026-09-23_stopped.md
- src/data_sheets_schema/derive_core.py, d4d_pair_consistency.py, rocrate_map.py
- src/data_sheets_schema/provenance.py (schema_facts, inputs.bundle_md5/sha256,
  source_manifest md5, prompt sha256, outputs sha256)
- src/data_sheets_schema/evaluation/evaluate_d4d.py (presence, no model client),
  evaluate_d4d_llm.py (instrument_sha256, context_sha256, input_sha256)
- src/data_sheets_schema/evidence_score.py (grounding and fitness axes, schema digest
  and specification sha256 on each judgment)
- notes/matched_cborg_2026-09-13/audit_controls/README.md (native audit continuation,
  fresh-context worker batches, one integration, one terminal evidence check,
  registration sha256)
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Arc

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

FILL_MODEL = st.SEQ[1]          # light blue fill = a model call
EDGE_MODEL = st.SEQ[8]
EDGE_NOMODEL = st.INK["secondary"]
CMD = ".claude/commands/d4d-full-core.md"
RUNNER = "src/data_sheets_schema/api_runner.py"
RUNS = "src/data_sheets_schema/runs.py"
DIRECT = "notes/claudecode_direct/README.md"
AUDITC = "notes/matched_cborg_2026-09-13/audit_controls/README.md"
PROV = "src/data_sheets_schema/provenance.py"

# id, label, model_call, documented_in  (the CSV export)
BOXES = [
    ("arm_api", "API arm: Messages SDK via CBORG; method claudecode_api; runtime 'Claude API (direct)'", "yes", f"{RUNS}; {DIRECT}"),
    ("arm_agentic", "Agentic arm: Claude Code via local proxy to CBORG; method claudecode_agent; runtime 'Claude Code'", "yes", f"{RUNS}; {DIRECT}"),
    ("arm_direct", "Direct arm: Claude Code on the maintainer's subscription, direct to Anthropic; method claudecode_direct; runtime 'Claude Code (direct)'; registered; first canary (CHORUS, 2026-09-23) completed all four phases but was stopped and disqualified (a prescribed provenance command was denied, no provenance record); no accepted run", "yes", f"{RUNS}; {DIRECT}; notes/claudecode_direct/CHORUS_direct_rep1_2026-09-23_stopped.md"),
    ("inputs", "Inputs: source bundle, source manifest, schema, prompt", "no", f"{PROV} (inputs.bundle_md5/bundle_sha256, source_manifest.md5, prompts sha256, schema_facts)"),
    ("phase1", "Phase 1: generate the full record and its coverage receipt", "yes", f"{CMD}; {RUNNER} (PHASES 'full')"),
    ("phase2", "Phase 2: derive the core from the validated full record (derive_core.py)", "no", f"{CMD}; src/data_sheets_schema/derive_core.py; {RUNNER} (PHASES 'core')"),
    ("phase3", "Phase 3: audit the full record against the sources and provenance boundary", "yes", f"{CMD}; {RUNNER} (PHASES 'audit')"),
    ("phase3_native", "Native audit continuation: separately registered session; fresh-context worker batches; one integration step; one terminal source/evidence check", "yes", AUDITC),
    ("phase4_rederive", "Phase 4: re-derive the core (no model)", "no", f"{CMD}; {RUNNER} (PHASES 'reconcile_core', repair_core)"),
    ("phase4_checks", "Phase 4b: deterministic checks (pair checker, validators, receipts)", "no", f"{CMD}; src/data_sheets_schema/d4d_pair_consistency.py"),
    ("phase4_semantic", "Phase 4c: semantic review the pair checker asks for; reconcile the full record", "yes", f"{CMD}; {RUNNER} (PHASES 'reconcile_full')"),
    ("phase4_report", "Phase 4d: reconciliation report and repair", "yes", f"{CMD}; {RUNNER} (PHASES 'report', repair_full)"),
    ("outputs", "Outputs: full record, core record, coverage receipt, audit, report; provenance record", "no", f"{PROV} (outputs.full/core/report sha256)"),
    ("crate_in", "RO-Crate package: ro-crate-metadata.json", "no", "data/ro-crate_packages/README.md; crate_manifest.yaml"),
    ("crate_map", "d4d rocrate map: static mapping table, no inference (rocrate_map.py)", "no", "src/data_sheets_schema/rocrate_map.py; src/data_sheets_schema/cli/rocrate.py"),
    ("crate_out", "rocrate_static_map record and mapping provenance report", "no", "src/data_sheets_schema/cli/rocrate.py (emit-map-arm, method rocrate_static_map)"),
    ("eval_presence", "Presence evaluator: rubric10 / rubric20 field presence", "no", "src/data_sheets_schema/evaluation/evaluate_d4d.py; cli/evaluate.py (presence)"),
    ("eval_semantic", "rubric10 / rubric20 semantic judges", "yes", "src/data_sheets_schema/evaluation/evaluate_d4d_llm.py; judge_contract.py"),
    ("eval_field", "Field-level source-support (grounding) and schema-fitness judgments", "yes", "src/data_sheets_schema/evidence_score.py; fitness_schema.py"),
    ("eval_pair", "Pair consistency check", "no", "src/data_sheets_schema/d4d_pair_consistency.py"),
]
LOCKS = [
    ("inputs", "bundle md5 + sha256; manifest md5; prompt sha256; schema digest md5 + schema sha256", PROV),
    ("outputs", "output hashes (full, core, report)", PROV),
    ("phase3_native", "registration sha256", AUDITC),
    ("eval_semantic", "instrument, context and input sha256", "src/data_sheets_schema/evaluation/evaluate_d4d_llm.py"),
    ("eval_field", "schema digest + specification sha256", "src/data_sheets_schema/evidence_score.py"),
]


def box(ax, x, y, w, h, title, lines=(), model=False, dashed=False, hollow=False, fs=7.6):
    face = FILL_MODEL if (model and not hollow) else st.INK["surface"]
    edge = EDGE_MODEL if model else EDGE_NOMODEL
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.6",
                       facecolor=face, edgecolor=edge, linewidth=0.9,
                       linestyle=(0, (3, 2)) if dashed else "solid", zorder=2)
    ax.add_patch(p)
    ax.text(x + 0.9, y + h - 0.9, title, ha="left", va="top", fontsize=fs, fontweight="bold",
            color=st.INK["primary"], zorder=3)
    for i, ln in enumerate(lines):
        ax.text(x + 0.9, y + h - 0.9 - (i + 1) * 2.05, ln, ha="left", va="top", fontsize=fs - 1.0,
                color=st.INK["secondary"], zorder=3)


def arrow(ax, p, q, rad=0.0, dashed=False):
    a = FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=9, linewidth=0.9,
                        color=st.INK["secondary"], connectionstyle=f"arc3,rad={rad}",
                        linestyle=(0, (3, 2)) if dashed else "solid", zorder=1, shrinkA=0, shrinkB=0)
    ax.add_patch(a)


def lock(ax, x, y, label, s=1.0):
    """A small padlock: body + shackle, in ink, with a short label to the right."""
    ax.add_patch(Rectangle((x, y), 1.3 * s, 1.0 * s, facecolor=st.INK["secondary"], edgecolor="none", zorder=4))
    ax.add_patch(Arc((x + 0.65 * s, y + 1.0 * s), 0.9 * s, 1.2 * s, theta1=0, theta2=180,
                     color=st.INK["secondary"], linewidth=0.9, zorder=4))
    ax.text(x + 1.7 * s, y + 0.5 * s, label, ha="left", va="center", fontsize=6.2, color=st.INK["secondary"], zorder=4)


def main() -> int:
    st.apply()
    fig, ax = plt.subplots(figsize=(13.2, 7.9))
    ax.set_xlim(0, 132); ax.set_ylim(1, 75.5); ax.axis("off")

    # --- arms (left) ------------------------------------------------------
    arms_y = {"api": 66, "agentic": 57, "direct": 48}
    box(ax, 2, arms_y["api"], 24, 7, "API arm", ["Messages SDK via CBORG", "claudecode_api  ·  \"Claude API (direct)\""], model=True)
    box(ax, 2, arms_y["agentic"], 24, 7, "Agentic arm", ["Claude Code via local proxy to CBORG", "claudecode_agent  ·  \"Claude Code\""], model=True)
    box(ax, 2, arms_y["direct"], 24, 7, "Direct arm", ["Claude Code, maintainer's subscription, direct",
                                                     "claudecode_direct  ·  \"Claude Code (direct)\""],
        model=True, dashed=True, hollow=True)
    ax.text(3, 46.4, "registered; first canary (CHORUS, 2026-09-23) completed generation\nbut was disqualified; no accepted run",
            fontsize=6.2, color=st.INK["muted"], ha="left", va="top")
    for k, c in st.ARM_COLOR.items():   # arm swatch: identity by hue plus the label
        yy = arms_y[k]
        ax.add_patch(Rectangle((0.6, yy), 0.9, 7, facecolor=c if k != "direct" else "none",
                               edgecolor=c, linewidth=0.9, hatch=st.HATCH if k == "direct" else None, zorder=3))
    # arms -> inputs node
    for k, yy in arms_y.items():
        arrow(ax, (26, yy + 3.5), (30, 64.5), rad=0.0 if k == "agentic" else (0.15 if k == "api" else -0.15),
              dashed=(k == "direct"))
    box(ax, 30, 61, 14, 7, "Inputs", ["bundle, manifest,", "schema, prompt"], model=False)
    lock(ax, 30.4, 59.0, "bundle md5+sha256 · manifest md5")
    lock(ax, 30.4, 57.0, "prompt sha256 · schema digest md5 + sha256")

    # --- four phases -------------------------------------------------------
    py, ph = 56, 15.5
    box(ax, 47, py, 19, ph, "Phase 1  generate", ["full record", "+ coverage receipt", "(model call)"], model=True)
    box(ax, 68, py, 17, ph, "Phase 2  derive core", ["derive_core.py", "no model:", "shared slots copied,", "resources projected,", "distributions built"], model=False)
    box(ax, 87, py, 19, ph, "Phase 3  source audit", ["full record vs sources", "and provenance boundary", "(model call)"], model=True)
    box(ax, 108, py, 22, ph, "Phase 4  re-derive + check", [], model=False)
    # phase 4 internals: four small boxes
    sub = [("re-derive core", False), ("deterministic checks", False), ("semantic review", True), ("report + repair", True)]
    for i, (t, m) in enumerate(sub):
        yy = py + ph - 5.3 - i * 2.6
        box(ax, 109, yy, 20, 2.4, t, [], model=m, fs=6.6)
    for x0, x1 in ((44, 47), (66, 68), (85, 87), (106, 108)):
        arrow(ax, (x0, py + ph / 2), (x1, py + ph / 2))
    # native audit continuation under phase 3
    box(ax, 87, 37, 19, 15, "Native audit continuation", ["separately registered session", "fresh-context worker batches",
                                                             "one integration step", "one terminal source check", "(model calls)"],
        model=True, dashed=True)
    arrow(ax, (96.5, py), (96.5, 52), dashed=True)
    arrow(ax, (106, 44.5), (118, 44.5), dashed=True); arrow(ax, (118, 44.5), (118, py), dashed=True)
    lock(ax, 107.5, 35.0, "registration sha256")

    # --- outputs -----------------------------------------------------------
    box(ax, 47, 37, 34, 12, "Outputs", ["full record · core record · coverage receipt", "audit · reconciliation report",
                                          "provenance record binds them by hash"], model=False)
    arrow(ax, (119, py), (119, 43), ); arrow(ax, (119, 43), (81, 43))
    lock(ax, 47.4, 35.0, "output hashes (full, core, report)")

    # --- deterministic side route (bottom left) ---------------------------
    box(ax, 2, 20, 18, 9, "RO-Crate package", ["ro-crate-metadata.json", "(4 projects hold one)"], model=False)
    box(ax, 23, 20, 22, 9, "d4d rocrate map", ["static mapping table,", "no inference, no model"], model=False)
    box(ax, 48, 20, 33, 9, "rocrate_static_map record", ["+ mapping provenance report", "(filled / empty / unresolvable / unplaceable)"], model=False)
    arrow(ax, (20, 24.5), (23, 24.5)); arrow(ax, (45, 24.5), (48, 24.5))
    ax.text(2, 31.5, "Deterministic side route", fontsize=8, fontweight="bold", color=st.INK["secondary"])

    # --- evaluation branches (bottom right) -------------------------------
    ax.text(87, 33.4, "Evaluation on the outputs", fontsize=8, fontweight="bold", color=st.INK["secondary"])
    ev = [("presence evaluator (rubric10 / rubric20 presence)", False, None),
          ("rubric10 / rubric20 semantic judges", True, "instrument · context · input sha256"),
          ("field-level source-support + schema-fitness", True, "schema digest + specification sha256"),
          ("pair consistency check", False, None)]
    ey = 27.5
    for i, (t, m, lk) in enumerate(ev):
        yy = ey - i * 6.6
        box(ax, 87, yy, 43, 4.4, t, [], model=m, fs=7.0)
        if lk:
            lock(ax, 87.4, yy - 1.9, lk, s=0.85)
    arrow(ax, (81, 40), (84, 40)); arrow(ax, (84, 40), (84, 20));
    for i in range(4):
        arrow(ax, (84, 27.5 - i * 6.6 + 2.2), (87, 27.5 - i * 6.6 + 2.2))
    arrow(ax, (81, 24.5), (84, 24.5))
    ax.text(84.6, 34.9, "generated + crate-mapped records", fontsize=6.2, color=st.INK["muted"], ha="left", va="bottom")

    # --- legend -----------------------------------------------------------
    lx, ly = 2, 8
    ax.add_patch(FancyBboxPatch((lx, ly), 5, 2.4, boxstyle="round,pad=0,rounding_size=0.5", facecolor=FILL_MODEL, edgecolor=EDGE_MODEL, linewidth=0.9))
    ax.text(lx + 6, ly + 1.2, "model call", va="center", fontsize=7.2, color=st.INK["primary"])
    ax.add_patch(FancyBboxPatch((lx + 16, ly), 5, 2.4, boxstyle="round,pad=0,rounding_size=0.5", facecolor=st.INK["surface"], edgecolor=EDGE_NOMODEL, linewidth=0.9))
    ax.text(lx + 22, ly + 1.2, "no model", va="center", fontsize=7.2, color=st.INK["primary"])
    ax.add_patch(FancyBboxPatch((lx + 31, ly), 5, 2.4, boxstyle="round,pad=0,rounding_size=0.5", facecolor=st.INK["surface"], edgecolor=EDGE_MODEL, linewidth=0.9, linestyle=(0, (3, 2))))
    ax.text(lx + 37, ly + 1.2, "registered / optional path, no accepted run", va="center", fontsize=7.2, color=st.INK["primary"])
    lock(ax, lx, ly - 3.2, "hash binds identity (what the provenance or evaluation record stores)")
    ax.text(lx, ly - 5.6, "Arms: blue = API, orange = agentic, aqua = direct (swatch at the arm box's left edge); Phase 2 and the Phase 4 core re-derivation are pure functions of the full record.",
            fontsize=6.6, color=st.INK["muted"], va="top")

    fig.suptitle("Generation arms, the four-phase full/core pipeline, the deterministic crate route, and the evaluation branches",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=0.985)
    rows = [{"id": i, "label": l, "model_call": m, "documented_in": d} for i, l, m, d in BOXES]
    locks = [{"box_id": b, "hash_binding": l, "documented_in": d} for b, l, d in LOCKS]
    basis = ("Record set: none (schematic of documented steps); every box and lock traces to the file named in fig01_pipeline.csv, "
             "checked 2026-09-23")
    st.save(fig, "fig01_pipeline", {"main": rows, "locks": locks}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
