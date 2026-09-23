#!/usr/bin/env python
"""#2301: generation tokens, wall time and cost per record for the reference rescore records.

Record set: the 24 API-arm full records of the frozen CBORG reference rescore
(notes/reference_rescore_2026-09-12_cborg_runtime/manifest.json jobs[].input), i.e. 4 projects
x v7/v8 x 3 generation replicates. Per-phase usage is read from each record's
`<project>_provenance.yaml` (api_usage rows) in the sibling `_core` directory that
api_runner writes. No settled USD figure exists for any generation record: the only
per-record cost the repository can state is a catalogue estimate (usage x CBORG list prices
observed 2026-09-14, the same formula the v9 canary review used), which is not an invoice
and is drawn hollow. Native (agentic/direct) ledgers exist only under ignored local draft
directories and are not part of the record set; those arms are drawn as explicit
"not recorded" placeholders. The one native-arm source is the outcome note of the first
direct-arm canary (notes/claudecode_direct/CHORUS_direct_rep1_2026-09-23_stopped.md): that
attempt was disqualified (no provenance record) and is not in the corpus, so its runtime's own
terminal accounting is drawn as a separately labelled estimate, never pooled with anything
settled. Nothing is summed across providers or subscriptions. Prices are the CBORG catalogue
rate for the google route of claude-opus-5; provenance does not record which upstream route
served a request, and the amazon route lists higher rates.
"""
from __future__ import annotations

import json
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import Patch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

ARCH = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime"
CATALOGUE = st.ROOT / "notes" / "matched_cborg_2026-09-13" / "model_catalogue.json"
CATALOGUE_MODEL = "claude-opus-5"           # the route string the provenance records name; same list prices as google/claude-opus-5
ALT_CATALOGUE_MODEL = "amazon/claude-opus-5"  # the other upstream route CBORG lists; provenance does not say which route served a request
PHASES = ["full", "full_readdress", "audit", "reconcile_full", "report", "repair_full", "report_after_repair", "report_regate"]
PHASE_SHORT = {"full": "full", "full_readdress": "full\nreaddress", "audit": "audit", "reconcile_full": "reconcile",
               "report": "report", "repair_full": "repair", "report_after_repair": "report\nafter repair", "report_regate": "report\nregate"}
MARK = {"v7": "o", "v8": "s"}
DIRECT_NOTE = st.ROOT / "notes" / "claudecode_direct" / "CHORUS_direct_rep1_2026-09-23_stopped.md"


def direct_canary() -> dict | None:
    """The first direct-arm canary (2026-09-23, CHORUS): disqualified, no provenance record, not in
    the corpus. The outcome note carries the runtime's own terminal accounting; the figures are
    parsed from that note rather than retyped, and the point is drawn only as a labelled,
    hatched "runtime estimate", never pooled with anything settled."""
    import re
    from datetime import datetime
    if not DIRECT_NOTE.exists():
        return None
    text = DIRECT_NOTE.read_text()
    def grab(pattern, numeric=False):
        m = re.search(pattern, text)
        if not m:
            raise RuntimeError(f"direct canary note lacks {pattern!r}")
        return m.group(1).replace(",", "") if numeric else m.group(1)
    started = datetime.fromisoformat(grab(r"Started (\S+), finished"))
    finished = datetime.fromisoformat(grab(r"finished (\S+)\."))
    return {
        "project": "CHORUS", "cohort": "direct-v1", "generation_rep": 1,
        "label": grab(r"label `([^`]+)`"), "arm": "direct", "runtime": grab(r"runtime `([^`]+)`"),
        "provider": grab(r"provider `([^`]+)`"), "model": grab(r"model `([^`]+)`"),
        "usd_runtime_estimate": float(grab(r"estimate \$([0-9.]+)", numeric=True)),
        "input_tokens": int(grab(r"`inputTokens` ([0-9,]+)", numeric=True)), "output_tokens": int(grab(r"`outputTokens` ([0-9,]+)", numeric=True)),
        "thinking_tokens": int(grab(r"\(thinking ([0-9,]+)\)", numeric=True)), "cache_read": int(grab(r"cache read ([0-9,]+)", numeric=True)),
        "cache_write": int(grab(r"cache creation ([0-9,]+)", numeric=True)), "turns": int(grab(r"([0-9]+) turns", numeric=True)),
        "minutes": int(grab(r"([0-9]+) minutes", numeric=True)), "seconds": (finished - started).total_seconds(),
        "status": "disqualified canary: no provenance record, not in corpus",
    }


def provenance_path(record_input: str) -> Path:
    p = record_input.replace("/claudecode_agent/", "/claudecode_agent_core/").replace("/claudecode_api/", "/claudecode_api_core/")
    return st.ROOT / p.replace("_d4d.yaml", "_provenance.yaml")


def load():
    manifest = json.loads((ARCH / "manifest.json").read_text())
    audit = json.loads((ARCH / "completion_audit.json").read_text())
    cat = json.loads(CATALOGUE.read_text())
    prices = next(m for m in cat["models"] if m["model"] == CATALOGUE_MODEL)["capabilities"]
    alt_prices = next(m for m in cat["models"] if m["model"] == ALT_CATALOGUE_MODEL)["capabilities"]
    jobs = {j["id"]: j for j in manifest["jobs"]}
    r20 = {}
    for r in audit["ratings"]:
        j = jobs[r["job_id"]]
        if j["rubric"] == "rubric20-semantic":
            doc = json.loads((st.ROOT / r["output"]).read_text())
            r20[j["input"]] = doc["overall_score"]["normalized_percentage"]
    records = {}
    for j in manifest["jobs"]:
        if j["input"] in records:
            continue
        prov = yaml.safe_load(provenance_path(j["input"]).read_text())
        rows = prov.get("api_usage") or []
        phases = defaultdict(lambda: {"in": 0, "out": 0, "seconds": None, "attempts": 0, "timed_attempts": 0})
        for u in rows:
            ph = phases[u["phase"]]
            ph["in"] += (u.get("input_tokens") or 0) + (u.get("cache_read") or 0) + (u.get("cache_write") or 0)
            ph["out"] += u.get("output_tokens") or 0
            ph["attempts"] += 1
            if u.get("seconds") is not None:
                ph["seconds"] = (ph["seconds"] or 0.0) + float(u["seconds"])
                ph["timed_attempts"] += 1
        usd = sum((u.get("input_tokens") or 0) * prices["input_cost_per_token"]
                  + (u.get("output_tokens") or 0) * prices["output_cost_per_token"]
                  + (u.get("cache_write") or 0) * prices["cache_creation_input_token_cost"]
                  + (u.get("cache_read") or 0) * prices["cache_read_input_token_cost"] for u in rows)
        skipped = prov.get("phases_skipped") or []
        complete = not skipped          # a resumed run skips phases already on disk and records no usage for them
        records[j["input"]] = {
            "project": j["project"], "cohort": j["cohort"], "generation_rep": j["generation_rep"], "label": j["label"],
            "arm": "api", "runtime": prov["model"].get("agent_runtime"), "provider": prov["model"].get("provider"),
            "model": prov["model"].get("model"), "input": j["input"], "phases": dict(phases),
            "usage_rows": len(rows), "phases_skipped": ",".join(skipped), "usage_complete": complete,
            "usd_catalogue_estimate": usd if complete else None,
            "usd_partial_estimate": usd if not complete else None,
            "rubric20_adjusted_pct": r20.get(j["input"]),
        }
    return manifest, audit, prices, alt_prices, records


def main() -> int:
    st.apply()
    manifest, audit, prices, alt_prices, records = load()
    n_ratings = len(audit["ratings"])
    canary = direct_canary()
    recs = sorted(records.values(), key=lambda r: (st.PROJECTS.index(r["project"]), r["cohort"], r["generation_rep"]))
    n = len(recs)
    blue = st.ARM_COLOR["api"]

    fig = plt.figure(figsize=(11.6, 13.4))
    gs = fig.add_gridspec(4, 2, height_ratios=[1.25, 1.0, 1.0, 1.15], hspace=0.62, wspace=0.25, top=0.94, bottom=0.04)

    # ---- (A) tokens in/out per phase, one panel per arm ----
    gsA = gs[0, :].subgridspec(1, 3, width_ratios=[3.2, 1, 1], wspace=0.12)
    axA = fig.add_subplot(gsA[0, 0])
    phase_rows = []
    for pi, ph in enumerate(PHASES):
        ins = [r["phases"][ph]["in"] for r in recs if ph in r["phases"]]
        outs = [r["phases"][ph]["out"] for r in recs if ph in r["phases"]]
        for r in recs:
            if ph in r["phases"]:
                p = r["phases"][ph]
                phase_rows.append({"project": r["project"], "cohort": r["cohort"], "generation_rep": r["generation_rep"],
                                   "label": r["label"], "arm": r["arm"], "phase": ph, "attempts": p["attempts"],
                                   "tokens_in_incl_cache": p["in"], "tokens_out_incl_thinking": p["out"],
                                   "seconds": None if p["seconds"] is None else round(p["seconds"], 1),
                                   "timed_attempts": p["timed_attempts"]})
        for k, (vals, dx, col) in enumerate(((ins, -0.2, blue), (outs, 0.2, st.SEQ[4]))):
            if not vals:
                continue
            mean = sum(vals) / len(vals)
            axA.bar(pi + dx, mean, width=0.36, color=col, zorder=2)
            xs = [pi + dx + (i % 5 - 2) * 0.035 for i in range(len(vals))]
            axA.plot(xs, vals, linestyle="none", marker="o", markersize=3.2, color=st.INK["secondary"],
                     markeredgecolor=st.INK["surface"], markeredgewidth=0.6, zorder=3, alpha=0.85)
        axA.text(pi, -0.045, f"n={len(ins)}", transform=axA.get_xaxis_transform(), ha="center", va="top",
                 fontsize=6.4, color=st.INK["muted"])
    axA.set_xticks(range(len(PHASES)))
    axA.set_xticklabels([PHASE_SHORT[p] for p in PHASES], fontsize=7.2)
    axA.tick_params(axis="x", pad=20, length=0)
    axA.set_ylabel("tokens per record (bar = mean, dots = records)")
    axA.set_title(f"A  {st.ARM_LABEL['api']}: tokens per phase, {n} records", pad=8)
    st.hairline_grid(axA)
    axA.legend(handles=[Patch(facecolor=blue, label="input tokens incl. cache read and cache write"),
                        Patch(facecolor=st.SEQ[4], label="output tokens incl. thinking"),
                        plt.Line2D([], [], marker="o", linestyle="none", color=st.INK["secondary"], markersize=3.2, label="one record (attempts summed)")],
               loc="upper right", fontsize=7)
    for k, arm in enumerate(("agentic", "direct")):
        ax = fig.add_subplot(gsA[0, k + 1], sharey=axA)
        ax.text(0.5, 0.5, "not recorded\nper phase", transform=ax.transAxes, ha="center", va="center", fontsize=7.5, color=st.INK["secondary"])
        ax.set_xlim(-0.8, 0.8); ax.set_xticks([]); ax.tick_params(labelleft=False)
        ax.set_title(st.ARM_LABEL[arm].replace(" (", "\n("), fontsize=8, pad=8)
        sub = "0 records in set"
        if arm == "direct" and canary is not None:
            sub = "0 records in set;\n1 disqualified canary,\nwhole-run totals only (C)"
        ax.text(0, -0.045, sub, transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=6.4, color=st.INK["muted"])
        st.hairline_grid(ax)

    # ---- (B) wall time per phase ----
    axB = fig.add_subplot(gs[1, :])
    for pi, ph in enumerate(PHASES):
        vals = [r["phases"][ph]["seconds"] / 60 for r in recs if ph in r["phases"] and r["phases"][ph]["seconds"] is not None]
        untimed = sum(1 for r in recs if ph in r["phases"] and r["phases"][ph]["seconds"] is None)
        absent = sum(1 for r in recs if ph not in r["phases"])
        if vals:
            xs = [pi + (i % 7 - 3) * 0.06 for i in range(len(vals))]
            axB.plot(xs, vals, linestyle="none", marker="o", markersize=4, color=blue,
                     markeredgecolor=st.INK["surface"], markeredgewidth=0.7, zorder=3, alpha=0.9)
            med = sorted(vals)[len(vals) // 2]
            axB.plot([pi - 0.3, pi + 0.3], [med, med], color=st.INK["primary"], linewidth=1.2, zorder=4)
        note = f"timed {len(vals)}"
        if untimed:
            note += f"\nno timing {untimed}"
        if absent:
            note += f"\nphase absent {absent}"
        axB.text(pi, -0.045, note, transform=axB.get_xaxis_transform(), ha="center", va="top", fontsize=6.2, color=st.INK["muted"])
    axB.set_yscale("log")
    axB.set_xticks(range(len(PHASES)))
    axB.set_xticklabels([PHASE_SHORT[p] for p in PHASES], fontsize=7.2)
    axB.tick_params(axis="x", pad=26, length=0)
    axB.set_ylabel("wall time per phase (minutes, log)")
    axB.set_title("B  Wall time per phase from api_usage `seconds` (API arm only; agentic and direct arms: not recorded)", pad=8)
    st.hairline_grid(axB)
    axB.legend(handles=[plt.Line2D([], [], marker="o", linestyle="none", color=blue, markersize=4, label="one record, attempts summed"),
                        plt.Line2D([], [], color=st.INK["primary"], linewidth=1.2, label="median of timed records")],
               loc="upper right", fontsize=7)

    # ---- (C) USD per record ----
    axC = fig.add_subplot(gs[2, 0])
    xt, xl = [], []
    main_rows = []
    for i, r in enumerate(recs):
        pi = st.PROJECTS.index(r["project"])
        x = pi * 7 + (0 if r["cohort"] == "v7" else 3) + (r["generation_rep"] - 1)
        r["_x"] = x
        est = r["usd_catalogue_estimate"]
        if est is not None:
            axC.plot(x, est, marker=MARK[r["cohort"]], markersize=6.5, markerfacecolor="none", markeredgecolor=blue,
                     markeredgewidth=1.2, linestyle="none", zorder=3)
        else:
            axC.plot(x, r["usd_partial_estimate"], marker=MARK[r["cohort"]], markersize=6.5, markerfacecolor=st.INK["mid"],
                     markeredgecolor=st.INK["muted"], markeredgewidth=1.0, linestyle="none", zorder=3)
            axC.annotate("resumed run: earlier\nphases unrecorded", (x, r["usd_partial_estimate"]), xytext=(8, 10),
                         textcoords="offset points", fontsize=6.2, color=st.INK["secondary"], va="bottom",
                         arrowprops={"arrowstyle": "-", "color": st.INK["axis"], "linewidth": 0.6})
        main_rows.append({
            "project": r["project"], "cohort": r["cohort"], "generation_rep": r["generation_rep"], "label": r["label"],
            "arm": r["arm"], "runtime": r["runtime"], "provider": r["provider"], "model": r["model"],
            "usage_rows": r["usage_rows"], "usage_complete": r["usage_complete"], "phases_skipped": r["phases_skipped"],
            "tokens_in_incl_cache_total": sum(p["in"] for p in r["phases"].values()),
            "tokens_out_incl_thinking_total": sum(p["out"] for p in r["phases"].values()),
            "seconds_recorded_total": round(sum(p["seconds"] for p in r["phases"].values() if p["seconds"] is not None), 1),
            "status": "reference record" if r["usage_complete"] else "reference record, resumed run",
            "usd_settled": None,
            "usd_runtime_estimate": None,
            "usd_catalogue_estimate": None if est is None else round(est, 4),
            "usd_partial_estimate": None if r["usd_partial_estimate"] is None else round(r["usd_partial_estimate"], 4),
            "cost_basis": ("catalogue estimate: recorded api_usage tokens x CBORG list prices for route claude-opus-5 observed 2026-09-14; not an invoice, not settled"
                           if est is not None else
                           "partial catalogue estimate only: resumed run, api_usage lacks the skipped phases; not settled"),
            "rubric20_adjusted_pct": r["rubric20_adjusted_pct"],
        })
    for pi, proj in enumerate(st.PROJECTS):
        xt.append(pi * 7 + 2.5); xl.append(proj.replace("_", "-"))
        axC.text(pi * 7 + 1, -0.02, "v7", transform=axC.get_xaxis_transform(), ha="center", va="top", fontsize=6.6, color=st.INK["muted"])
        axC.text(pi * 7 + 4, -0.02, "v8", transform=axC.get_xaxis_transform(), ha="center", va="top", fontsize=6.6, color=st.INK["muted"])
        if pi:
            axC.axvline(pi * 7 - 0.75, color=st.INK["grid"], linewidth=0.6, zorder=0)
    ymax = max(v for v in (r["usd_catalogue_estimate"] or r["usd_partial_estimate"] for r in recs))
    if canary is not None:
        xc = len(st.PROJECTS) * 7 + 0.5
        axC.axvline(xc - 1.75, color=st.INK["grid"], linewidth=0.6, zorder=0)
        axC.plot(xc, canary["usd_runtime_estimate"], marker="D", markersize=8, markerfacecolor="none",
                 markeredgecolor=st.ARM_COLOR["direct"], markeredgewidth=1.2, linestyle="none", zorder=3)
        axC.annotate("disqualified canary,\nruntime estimate", (xc, canary["usd_runtime_estimate"]), xytext=(-9, 0),
                     textcoords="offset points", fontsize=6.2, color=st.INK["secondary"], ha="right", va="center")
        xt.append(xc); xl.append("direct\ncanary")
        ymax = max(ymax, canary["usd_runtime_estimate"])
        main_rows.append({
            "project": canary["project"], "cohort": canary["cohort"], "generation_rep": canary["generation_rep"], "label": canary["label"],
            "arm": canary["arm"], "runtime": canary["runtime"], "provider": canary["provider"], "model": canary["model"],
            "usage_rows": 0, "usage_complete": False, "phases_skipped": "",
            "tokens_in_incl_cache_total": canary["input_tokens"] + canary["cache_read"] + canary["cache_write"],
            "tokens_out_incl_thinking_total": canary["output_tokens"],
            "seconds_recorded_total": round(canary["seconds"], 1),
            "status": canary["status"],
            "usd_settled": None,
            "usd_runtime_estimate": canary["usd_runtime_estimate"],
            "usd_catalogue_estimate": None, "usd_partial_estimate": None,
            "cost_basis": "runtime terminal accounting (estimate)",
            "rubric20_adjusted_pct": None,
        })
    axC.set_xticks(xt); axC.set_xticklabels(xl, fontsize=7.5); axC.tick_params(axis="x", length=0, pad=14)
    axC.set_yscale("log"); axC.set_ylim(1, ymax * 2.2)
    axC.set_yticks([1, 2, 5, 10, 20, 50]); axC.set_yticklabels(["1", "2", "5", "10", "20", "50"])
    axC.set_ylabel("USD per record (log; all values unsettled)")
    axC.set_title("C  Cost per record (no settled figure; hollow = catalogue estimate)", pad=8)
    st.hairline_grid(axC)
    axC.legend(handles=[plt.Line2D([], [], marker="o", markerfacecolor="none", markeredgecolor=blue, linestyle="none", markersize=6.5, label="v7 record, API arm, catalogue estimate (unsettled)"),
                        plt.Line2D([], [], marker="s", markerfacecolor="none", markeredgecolor=blue, linestyle="none", markersize=6.5, label="v8 record, API arm, catalogue estimate (unsettled)"),
                        plt.Line2D([], [], marker="o", markerfacecolor=st.INK["mid"], markeredgecolor=st.INK["muted"], linestyle="none", markersize=6.5, label="partial estimate (usage record incomplete)"),
                        plt.Line2D([], [], marker="D", markerfacecolor="none", markeredgecolor=st.ARM_COLOR["direct"], linestyle="none", markersize=7, label="direct-arm canary, runtime estimate (disqualified, not in corpus)")],
               loc="upper left", bbox_to_anchor=(0.0, -0.2), fontsize=6.4, ncol=2)

    # ---- (D) rubric20 adjusted % vs USD ----
    axD = fig.add_subplot(gs[2, 1])
    drawn = 0
    for r in recs:
        if r["usd_catalogue_estimate"] is None or r["rubric20_adjusted_pct"] is None:
            continue
        axD.plot(r["usd_catalogue_estimate"], r["rubric20_adjusted_pct"], marker=MARK[r["cohort"]], markersize=6.5,
                 markerfacecolor="none", markeredgecolor=blue, markeredgewidth=1.2, linestyle="none", zorder=3)
        drawn += 1
    omitted = n - drawn
    axD.set_xlabel("USD per record (catalogue estimate, unsettled)")
    axD.set_ylabel("rubric20 applicability-adjusted score (%)")
    axD.set_title(f"D  rubric20 score vs estimated cost ({drawn} records; {omitted} omitted, usage incomplete)", pad=8)
    if canary is not None:
        axD.text(1.0, -0.37, "direct-arm canary not drawn: no rating (not in corpus)", transform=axD.transAxes, fontsize=6.6,
                 color=st.INK["secondary"], ha="right", va="top")
    axD.set_xlim(left=0)
    st.hairline_grid(axD, "both")
    axD.legend(handles=[plt.Line2D([], [], marker="o", markerfacecolor="none", markeredgecolor=blue, linestyle="none", markersize=6.5, label="v7, API arm"),
                        plt.Line2D([], [], marker="s", markerfacecolor="none", markeredgecolor=blue, linestyle="none", markersize=6.5, label="v8, API arm")],
               loc="lower right", fontsize=7)
    axD.text(1.0, -0.3, "no record has a settled charge; hollow markers are estimates", transform=axD.transAxes, fontsize=6.6,
             color=st.INK["secondary"], ha="right", va="top")

    # ---- cost basis table ----
    axT = fig.add_subplot(gs[3, :]); axT.axis("off")
    eval_cost = audit["known_terminal_cli_cost_usd"]
    n_partial = sum(1 for r in recs if not r["usage_complete"])
    basis_rows = [
        [f"API arm generation ({n} records)", "LBL CBORG (proxy), claude-opus-5",
         f"catalogue estimate only: api_usage tokens x google-route list prices (in {prices['input_cost_per_token']*1e6:g}, out {prices['output_cost_per_token']*1e6:g}, "
         f"cache write {prices['cache_creation_input_token_cost']*1e6:g}, cache read {prices['cache_read_input_token_cost']*1e6:g} USD per 1M tokens); provenance does not "
         f"record the upstream route, and the amazon route lists in {alt_prices['input_cost_per_token']*1e6:g} / out {alt_prices['output_cost_per_token']*1e6:g}; "
         f"not an invoice; {n_partial} resumed record{'s' if n_partial != 1 else ''} partial"],
        ["Agentic arm generation", "Claude Code via proxy", "0 records in this set; no ledger outside ignored local drafts; drawn as not recorded"],
        ["Direct arm generation", "Claude Code, subscription",
         ("0 records in this set; subscription usage carries no per-record charge; drawn as not recorded" if canary is None else
          f"0 records in this set; 1 disqualified canary ({canary['project']}, 2026-09-23, no provenance record, not in corpus): runtime terminal "
          f"accounting estimate {canary['usd_runtime_estimate']:.2f} USD, {canary['minutes']} min, {canary['turns']} turns "
          f"(token totals in the CSV); subscription, not a charge; never pooled")],
        [f"Reference rescore evaluation ({n_ratings} ratings)", "LBL CBORG, claude-opus-5 CLI sessions",
         f"known terminal CLI subtotal {eval_cost:.2f} USD over {audit['actual_model_calls']} sessions; {audit['attempts_without_reported_cost']} interrupted sessions unpriced; "
         "total unknown; not per record; not reconciled with CBORG"],
    ]
    wrapped = [[textwrap.fill(a, 28), textwrap.fill(b, 30), textwrap.fill(c, 100)] for a, b, c in basis_rows]
    tbl = axT.table(cellText=wrapped, colLabels=["cost basis", "provider / route", "what the repository can state"],
                    loc="upper left", cellLoc="left", colLoc="left", bbox=[0.0, 0.0, 1.0, 1.0])
    tbl.auto_set_font_size(False); tbl.set_fontsize(6.9)
    for (r_, c_), cl in tbl.get_celld().items():
        cl.set_edgecolor(st.INK["grid"]); cl.set_linewidth(0.5)
        cl.get_text().set_color(st.INK["primary"] if r_ else st.INK["secondary"])
        if r_ == 0:
            cl.get_text().set_fontweight("bold")
        if c_ == 0:
            cl.set_width(0.22)
        elif c_ == 1:
            cl.set_width(0.2)
        else:
            cl.set_width(0.58)
    fig.suptitle("Generation tokens, wall time and cost per record for the reference rescore records (API arm), plus one disqualified direct-arm canary (runtime estimate)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=0.992)
    basis = (f"Record set: reference rescore 2026-09-12 (CBORG runtime), {n} API-arm full records, {n_ratings} ratings; usage from <project>_provenance.yaml api_usage; "
             "catalogue prices from notes/matched_cborg_2026-09-13/model_catalogue.json; evaluation cost from completion_audit.json; no native ledgers in set; "
             "one native-arm source: the direct canary note notes/claudecode_direct/CHORUS_direct_rep1_2026-09-23_stopped.md (disqualified, not in corpus)")
    st.save(fig, "fig10_cost_latency", {"main": main_rows, "phases": phase_rows,
                                        "cost_basis": [{"cost_basis": a, "provider": b, "statement": c} for a, b, c in basis_rows]}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
