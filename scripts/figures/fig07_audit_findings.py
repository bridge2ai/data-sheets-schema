#!/usr/bin/env python
"""#2298: Phase 3 audit findings and the before/after repair diff, per record.

Record set: every run under data/d4d_concatenated/<method>_core/<label>/intermediate/ that carries a
Phase 3 audit artifact (<PROJECT>_audit.json, {findings: [{severity, record, slot, issue}], summary})
at HEAD. All of these are API-runner runs (the runner writes the intermediates; `method` is the
output directory the run was registered under). An audit counts as accepted when Phase 4a applied it
(<PROJECT>_reconcile_full.yaml exists); at HEAD every audit in the set was applied (2026-09-04c CM4AI
is the one run with no later schema-repair round, so its final record is the reconcile_full output).
An audit that was written but never applied would be drawn and flagged "[not applied]" on its row
label. The `gate_test` label is a runner gate test, not an experiment: listed in the
CSV, not drawn. Rejected/terminal attempts are not in this set: notes/matched_cborg_2026-09-13/
failed_canaries/CHORUS_api_rep1/audit.json is a controller audit with verdict `reject`, and
data/ATTIC/canary_retries/ holds abandoned attempts.

Findings carry no type field, so Panel A classifies each finding's `issue` text by keyword rules
(FINDING_RULES below, first match wins; confirmatory notes and schema-shape/wrong-field defects fall
under "other"). No fresh-context batch audit (integration object with retain/replace/drop/new
dispositions) exists at HEAD, so no disposition hatching is drawn and Panel C is a placeholder.

Panel B diffs the Phase 1 full record (intermediate/<PROJECT>_full.yaml) against the final full record
(data/d4d_concatenated/<method>/<label>/<PROJECT>_d4d.yaml) at leaf-path level; list reindexing counts
as a removal plus an addition. "Caveats added" counts leaf paths ending in `source_caveats` that are
new or changed.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

CONCAT = st.ROOT / "data" / "d4d_concatenated"
MATCHED = st.ROOT / "notes" / "matched_cborg_2026-09-13"

CATEGORIES = ["unsupported claim", "missing supported information", "inconsistent identifier/count",
              "dataset/release/temporal scope error", "other"]
# categorical slots 3+ in fixed order; slots 0-2 stay reserved for the arms across the figure set
CAT_COLOR = {"unsupported claim": st.SERIES[3], "missing supported information": st.SERIES[4],
             "inconsistent identifier/count": st.SERIES[5], "dataset/release/temporal scope error": st.SERIES[6],
             "other": st.INK["axis"]}
CAT_LABEL = {"other": "other (schema shape, wrong field, style, confirmatory notes)"}
# (category, regex on the issue text, lower-cased); first match wins; the confirmatory rule is tested first.
CONFIRMATORY = re.compile(r"^(?:correct\b|supported omission|omission the bundle supports\.?$|not populated\. correct|good\b|well[- ])"
                          r"|\b(?:the omission is correct|is correct\b|correct\.|correct scoping|noted to confirm|no defect"
                          r"|no change (?:is )?(?:needed|required)|supported\.$|omitted\.$)")
FINDING_RULES = [
    ("unsupported claim", re.compile(
        r"not supported|does not support|do not support|unsupported|no source|not stated|not attested|nowhere|"
        r"not (?:in|from) the (?:declared )?bundle|not (?:appear|found|present|given|named) in the bundle|"
        r"(?:bundle|source|passage)s? (?:does|do) not (?:state|give|say|mention|name|supply|provide|establish|attest|support|report|record)|"
        r"over-?assert|infer|composed|paraphras|fabricat|invent|assum|no passage|no evidence|not grounded|"
        r"asserted (?:from|without)|not anchored|weakly anchored|beyond what the (?:bundle|source)")),
    ("missing supported information", re.compile(
        r"\bomission\b|\bomitted\b|\bomits\b|\bmissing\b|not (?:recorded|populated|captured|included|carried|emitted|surfaced)\b|"
        r"left empty|is empty|absent from the (?:record|core|full)|should (?:also )?be (?:recorded|added|populated|carried)|"
        r"could (?:be|have been) (?:recorded|added|populated)|the bundle (?:clearly )?supports (?:recording|populating)|"
        r"folded into|collapsed into|not (?:reflected|represented) in")),
    ("dataset/release/temporal scope error", re.compile(
        r"\bplanned\b|\bplan\b|\bproposal\b|\bproposed\b|\bfuture\b|\banticipated\b|\bnot yet\b|\bwill be\b|"
        r"earlier release|prior release|superseded|current state|in progress|\bas of\b|release (?:date|scope)|"
        r"\bpediatric\b|different (?:distribution|dataset|release|referent)|out of scope|\bscop(?:e|ing)\b|"
        r"\bversion \d|\bv\d\.\d|\bstale\b|\bcurrent\b.*\b(?:release|version)|project-?wide|feasibility")),
    ("inconsistent identifier/count", re.compile(
        r"inconsisten|contradict|mismatch|does not match|do not match|differs from|conflict|duplicate|\bcounts?\b|"
        r"\btotal\b|sums? to|adds? up|\bfigure\b|number of|identifier|\bid\b|\bdoi\b|\burl\b|grant (?:number|id)|"
        r"award number|\bdates?\b|\bbytes?\b|\bsize\b")),
]
SEVERITY_ORDER = ["high", "major", "moderate", "medium", "low", "minor", "info", "unclassified"]


def categorise(issue: str) -> str:
    text = (issue or "").strip().lower()
    if CONFIRMATORY.search(text):
        return "other"
    for cat, rx in FINDING_RULES:
        if rx.search(text):
            return cat
    return "other"


# ----------------------------------------------------------------------------- records
def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def leaves(node, prefix="") -> dict[str, str]:
    """Flatten to {leaf path: canonical value}; empty containers count as a leaf."""
    out = {}
    if isinstance(node, dict):
        if not node:
            out[prefix] = "{}"
        for k, v in node.items():
            out.update(leaves(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(node, list):
        if not node:
            out[prefix] = "[]"
        for i, v in enumerate(node):
            out.update(leaves(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = json.dumps(node, sort_keys=True, default=str)
    return out


def records():
    rows, findings = [], []
    for audit in sorted(CONCAT.glob("*_core/*/intermediate/*_audit.json")):
        core_dir = audit.parents[1]
        method = core_dir.parent.name.replace("_core", "")
        label = core_dir.name
        project = audit.name.replace("_audit.json", "")
        inter = audit.parent
        final = CONCAT / method / label / f"{project}_d4d.yaml"
        full = inter / f"{project}_full.yaml"
        reconcile = inter / f"{project}_reconcile_full.yaml"
        repairs = sorted(inter.glob(f"{project}_repair_full_r*.yaml"))
        prov_path = core_dir / f"{project}_provenance.yaml"
        prov = load_yaml(prov_path) if prov_path.exists() else {}
        doc = json.loads(audit.read_text())
        fl = doc.get("findings", []) if isinstance(doc, dict) else doc
        cats = Counter(); sev = Counter()
        for f in fl:
            c = categorise(f.get("issue", ""))
            cats[c] += 1
            s = str(f.get("severity", "")).strip().lower() or "unclassified"
            sev[s] += 1
            findings.append({"label": label, "project": project, "method": method, "record": f.get("record"),
                             "slot": f.get("slot"), "severity": s, "category": c,
                             "issue_excerpt": str(f.get("issue", ""))[:200]})
        # before/after diff
        diff = {"fields_removed": None, "fields_added": None, "fields_changed": None, "caveats_added": None}
        if full.exists() and final.exists():
            b, a = leaves(load_yaml(full)), leaves(load_yaml(final))
            removed = [k for k in b if k not in a]
            added = [k for k in a if k not in b]
            changed = [k for k in a if k in b and a[k] != b[k]]
            caveats = [k for k in added + changed if k.split(".")[-1].split("[")[0] == "source_caveats"]
            diff = {"fields_removed": len(removed), "fields_added": len(added), "fields_changed": len(changed),
                    "caveats_added": len(caveats), "leaves_before": len(b), "leaves_after": len(a)}
        final_sha = sha(final) if final.exists() else ""
        final_equals = "none"
        if repairs and final_sha == sha(repairs[-1]):
            final_equals = repairs[-1].name
        elif reconcile.exists() and final_sha == sha(reconcile):
            final_equals = reconcile.name
        elif full.exists() and final_sha == sha(full):
            final_equals = full.name
        repair_block = prov.get("repair") or []
        rows.append({
            "label": label, "project": project, "method": method,
            "arm": (prov.get("run") or {}).get("arm", ""), "date": label[:10],
            "audit_artifact": str(audit.relative_to(st.ROOT)),
            "audit_status": ("accepted: applied to the full record (reconcile_full)" if reconcile.exists()
                             else "audit written, never applied (no reconcile_full)"),
            "drawn": label != "gate_test",
            "exclusion": "" if label != "gate_test" else "runner gate test, not an experiment",
            "canonical": "superseded" if prov.get("canonical_superseded_by") else "canonical",
            "findings_total": len(fl), **{f"findings_{c}": cats[c] for c in CATEGORIES},
            **{f"severity_{s}": sev[s] for s in SEVERITY_ORDER},
            "repair_rounds_applied": sum(1 for r in repair_block if r.get("phase") == "repair_full" and r.get("outcome") == "applied"),
            "final_record_equals": final_equals,
            "before_artifact": str(full.relative_to(st.ROOT)) if full.exists() else "",
            "after_artifact": str(final.relative_to(st.ROOT)) if final.exists() else "",
            **diff,
        })
    # runs that exist at HEAD but are not accepted audits, listed for the record
    canary = MATCHED / "failed_canaries" / "CHORUS_api_rep1" / "audit.json"
    if canary.exists():
        c = json.loads(canary.read_text())
        rows.append({"label": "matched_cborg_2026-09-13 CHORUS_api_rep1 (native canary)", "project": "CHORUS",
                     "method": "native (matched_cborg)", "arm": "", "date": c.get("recorded_date", ""),
                     "audit_artifact": str(canary.relative_to(st.ROOT)),
                     "audit_status": f"not accepted: controller audit verdict '{c.get('verdict')}'", "drawn": False,
                     "exclusion": "rejected canary; no Phase 3 findings artifact", "canonical": "",
                     "findings_total": None, **{f"findings_{k}": None for k in CATEGORIES},
                     **{f"severity_{s}": None for s in SEVERITY_ORDER}, "repair_rounds_applied": None,
                     "final_record_equals": "", "before_artifact": "", "after_artifact": "",
                     "fields_removed": None, "fields_added": None, "fields_changed": None, "caveats_added": None,
                     "leaves_before": None, "leaves_after": None})
    return rows, findings


def batch_plan() -> dict:
    """Registered fresh-context batch plan parameters and the series status, read from the notes."""
    readme = (MATCHED / "audit_controls" / "README.md").read_text()
    mp = re.search(r"`max_paths` \(default (\d+)\)", readme)
    mw = re.search(r"`max_workers` \(default (\d+)\)", readme)
    reg = json.loads((MATCHED / "registration.json").read_text())
    return {"max_paths": int(mp.group(1)) if mp else None, "max_workers": int(mw.group(1)) if mw else None,
            "series": reg.get("series"), "status": reg.get("status"), "registered_at": reg.get("registered_at")}


# ----------------------------------------------------------------------------- drawing
def short_label(label: str) -> str:
    return label.replace("claude-opus-5-", "").replace("_rep", " rep").replace("_", " ")


def stacked_barh(ax, y, parts, colors, height=0.72):
    x = 0.0
    for val, col in zip(parts, colors):
        if val <= 0:
            continue
        ax.barh(y, val, left=x, height=height, color=col, zorder=2)
        x += val
        ax.plot([x, x], [y - height / 2, y + height / 2], color=st.INK["surface"], linewidth=1.0, zorder=3)


def main() -> int:
    st.apply()
    rows, findings = records()
    drawn = [r for r in rows if r["drawn"]]
    drawn.sort(key=lambda r: (r["date"], r["label"], st.PROJECTS.index(r["project"]) if r["project"] in st.PROJECTS else 9))
    n = len(drawn)
    plan = batch_plan()

    fig = plt.figure(figsize=(12.6, 0.128 * n + 4.4))
    gs = fig.add_gridspec(2, 5, width_ratios=[2.2, 0.7, 0.7, 0.7, 0.7], height_ratios=[n * 0.128, 1.1],
                          hspace=0.34, wspace=0.18, left=0.2, right=0.985, top=0.92, bottom=0.06)
    ax_a = fig.add_subplot(gs[0, 0])
    ys = list(range(n))
    labels = []
    for y, r in zip(ys, drawn):
        stacked_barh(ax_a, y, [r[f"findings_{c}"] for c in CATEGORIES], [CAT_COLOR[c] for c in CATEGORIES])
        suffix = "" if r["canonical"] == "canonical" else " *"
        flag = "" if r["audit_status"].startswith("accepted") else "  [not applied]"
        labels.append(f'{short_label(r["label"])}  {r["project"].replace("_", "-")}{suffix}{flag}')
        ax_a.text(r["findings_total"] + 1, y, str(r["findings_total"]), va="center", ha="left", fontsize=5.8,
                  color=st.INK["secondary"])
    ax_a.set_yticks(ys); ax_a.set_yticklabels(labels, fontsize=6)
    ax_a.set_ylim(n - 0.5, -0.5)
    ax_a.tick_params(axis="y", length=0)
    ax_a.set_xlim(0, max(r["findings_total"] for r in drawn) + 8)
    ax_a.set_xlabel("Phase 3 audit findings (count; label = total)")
    ax_a.set_title("A  Audit findings per record, by category (keyword-classified)", pad=8)
    st.hairline_grid(ax_a, "x")
    # separators between run labels
    prev = None
    for y, r in zip(ys, drawn):
        if prev is not None and r["label"] != prev:
            ax_a.axhline(y - 0.5, color=st.INK["grid"], linewidth=0.5, zorder=0)
        prev = r["label"]
    handles = [Rectangle((0, 0), 1, 1, facecolor=CAT_COLOR[c], label=CAT_LABEL.get(c, c)) for c in CATEGORIES]
    ax_a.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, -0.038), ncol=1,
                handlelength=1.4, fontsize=7)

    # Panel B: four small multiples sharing the row axis
    metrics = [("fields_removed", "leaf paths\nremoved"), ("fields_added", "leaf paths\nadded"),
               ("fields_changed", "leaf paths\nchanged"), ("caveats_added", "source_caveats\nadded or changed")]
    for mi, (key, title) in enumerate(metrics):
        ax = fig.add_subplot(gs[0, mi + 1], sharey=ax_a)
        vals = [r[key] for r in drawn]
        for y, v in zip(ys, vals):
            if v is None:
                ax.add_patch(Rectangle((0, y - 0.36), 1, 0.72, facecolor=st.INK["surface"], edgecolor=st.INK["muted"],
                                       hatch=st.HATCH, linewidth=0.5))
            else:
                ax.barh(y, v, height=0.72, color=st.SERIES[0], zorder=2)
        vmax = max(v for v in vals if v is not None) if any(v is not None for v in vals) else 1
        ax.set_xlim(0, vmax * 1.08)
        ax.set_title(title, fontsize=7.5, fontweight="normal", pad=4)
        ax.tick_params(axis="y", labelleft=False, length=0)
        ax.tick_params(axis="x", labelsize=6.5)
        st.hairline_grid(ax, "x")
        for sp in ("left",):
            ax.spines[sp].set_visible(False)
        if mi == 0:
            pos = ax.get_position()
            h = fig.get_size_inches()[1] * 72
            fig.text(pos.x0, pos.y1 + 42 / h, "B  Before/after diff: Phase 1 full record vs final full record",
                     fontsize=9.5, fontweight="bold", color=st.INK["primary"], ha="left", va="bottom")
            fig.text(pos.x0, pos.y1 + 30 / h, "leaf-path diff: a list reindex counts as one removal plus one addition, "
                     "so removed and added counts include shifted list items",
                     fontsize=7, color=st.INK["secondary"], ha="left", va="bottom")
    n_no_before = sum(1 for r in drawn if r["fields_removed"] is None)

    # Panel C: placeholder for the batch audit grid
    ax_c = fig.add_subplot(gs[1, :]); ax_c.axis("off")
    ax_c.add_patch(Rectangle((0.0, 0.0), 1.0, 0.86, facecolor=st.INK["surface"], edgecolor=st.INK["muted"],
                             hatch=st.HATCH, linewidth=0.6, transform=ax_c.transAxes, alpha=0.5))
    ax_c.text(0.0, 0.93, "C  Fresh-context batch audit: workers x top-level fields", fontsize=9.5, fontweight="bold",
              color=st.INK["primary"], ha="left", va="bottom", transform=ax_c.transAxes)
    msg = ("No batch audit completed in a separately registered session has an integration record "
           f"at this revision, so no worker assignment or integration row replacement can be drawn. The registered "
           f"fresh-context batch plan defaults are max_workers = {plan['max_workers']} and max_paths = {plan['max_paths']} "
           "(audit_controls/README.md).")
    import textwrap
    ax_c.text(0.02, 0.72, "\n".join(textwrap.wrap(msg, 150)), fontsize=7.5, color=st.INK["secondary"], ha="left",
              va="top", transform=ax_c.transAxes)

    n_accepted = sum(1 for r in drawn if r["audit_status"].startswith("accepted"))
    n_super = sum(1 for r in drawn if r["canonical"] != "canonical")
    note = (f"{n} records drawn: {n_accepted} audits applied to the full record (reconcile_full), {n - n_accepted} written but never applied "
            f"(flagged). * = record later superseded as canonical ({n_super}). No integration object (retain/replace/drop/new) "
            f"exists for any record, so no disposition hatching. {n_no_before} records lack a pre-repair artifact. "
            "Categories are keyword rules over the finding text (see script and CSV), not an audit-declared type. "
            "Panel B diffs leaf paths, not entities: a list reindex counts as one removal plus one addition.")
    fig.text(0.2, ax_c.get_position().y0 - 0.006, "\n".join(textwrap.wrap(note, 170)), fontsize=6.8,
             color=st.INK["secondary"], ha="left", va="top")
    fig.suptitle("Phase 3 audit findings and Phase 4 repair diff per record (API-runner runs with an audit artifact at HEAD)",
                 x=0.01, ha="left", fontsize=11.5, fontweight="bold", y=0.985)
    basis = (f"Record set: {n} API-runner full records with intermediate/<PROJECT>_audit.json at HEAD "
             f"({len(set(r['label'] for r in drawn))} labels, 2026-08-06 to 2026-09-12); gate_test and the rejected native canary listed in the CSV, not drawn")
    st.save(fig, "fig07_audit_findings", {"main": rows, "findings": findings,
                                         "rules": [{"category": c, "regex": rx.pattern} for c, rx in FINDING_RULES]
                                         + [{"category": "other (confirmatory)", "regex": CONFIRMATORY.pattern}]}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
