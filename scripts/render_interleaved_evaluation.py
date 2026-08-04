#!/usr/bin/env python3
"""
Render an interleaved HTML view of a D4D YAML next to its rubric10-semantic
and rubric20-semantic evaluation feedback.

For each top-level YAML field, attach:
  - rubric10 sub-element evaluations whose `evidence` mentions the field
  - rubric20 question evaluations whose `evidence` mentions the field
  - `issues_detected` entries whose `fields_involved` lists the field

Anything that couldn't be mapped to a visible field is shown at the bottom.

Usage:
  python scripts/render_interleaved_evaluation.py \
      --yaml data/d4d_concatenated/claudecode_agent/AI_READI_d4d.yaml \
      --r10  data/evaluation_llm/rubric10_semantic/concatenated/AI_READI_claudecode_agent_evaluation.json \
      --r20  data/evaluation_llm/rubric20_semantic/concatenated/AI_READI_claudecode_agent_evaluation.json \
      --out  data/d4d_html/concatenated/claudecode_agent/AI_READI_d4d_interleaved.html
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

import yaml
from data_sheets_schema.constants import RUBRIC20_MAX_SCORE


SEVERITY_COLOR = {
    "high": "#c0392b",
    "warning": "#e67e22",
    "medium": "#e67e22",
    "low": "#f1c40f",
    "info": "#3498db",
}


def _text(v) -> str:
    """Coerce anything (str/dict/list/None/number) to a displayable string."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float, bool)):
        return str(v)
    if isinstance(v, dict):
        return "; ".join(f"{k}: {_text(val)}" for k, val in v.items() if val not in (None, "", [], {}))
    if isinstance(v, (list, tuple)):
        return "; ".join(_text(x) for x in v if x not in (None, ""))
    return str(v)


def load_yaml_ordered(path: Path):
    """Load YAML preserving top-level key order."""
    with path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"Expected mapping at top of {path}, got {type(data).__name__}")
    return data


def yaml_block(key, value) -> str:
    """Serialize a single top-level field back to a YAML snippet."""
    dumped = yaml.safe_dump(
        {key: value},
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )
    return dumped.rstrip("\n")


def collect_field_tokens(evidence, known_fields: set) -> set:
    """Pick out which top-level field names appear in the evidence text."""
    text = _text(evidence)
    if not text:
        return set()
    matched = set()
    for f in known_fields:
        if re.search(rf"\b{re.escape(f)}\b", text):
            matched.add(f)
    return matched


def index_rubric10(eval_data: dict, known_fields: set):
    """Return list of (field_name | None, annotation_dict) for rubric10 sub-elements."""
    items = []
    elements = eval_data.get("element_scores", eval_data.get("elements", [])) or []
    for el in elements:
        el_id = el.get("id")
        el_name = el.get("name", "")
        for sub in el.get("sub_elements", []) or []:
            ev = sub.get("evidence", "") or ""
            fields = collect_field_tokens(ev, known_fields)
            ann = {
                "kind": "r10",
                "label": f"R10 {el_id}.{el_name}",
                "sub_name": sub.get("name", ""),
                "score": sub.get("score"),
                "max": 1,
                "evidence": ev,
                "quality_note": sub.get("quality_note", "") or "",
                "semantic_validation": sub.get("semantic_validation", "") or "",
            }
            if not fields:
                items.append((None, ann))
            else:
                for f in fields:
                    items.append((f, ann))
    return items


def index_rubric20(eval_data: dict, known_fields: set):
    """Return list of (field_name | None, annotation_dict) for rubric20 questions."""
    items = []
    categories = eval_data.get("categories", []) or []
    for cat in categories:
        cat_name = cat.get("name", "")
        for q in cat.get("questions", []) or []:
            ev = q.get("evidence", "") or ""
            fields = collect_field_tokens(ev, known_fields)
            sc = q.get("semantic_checks", {}) or {}
            ann = {
                "kind": "r20",
                "label": f"R20 Q{q.get('id')} ({cat_name})",
                "sub_name": q.get("name", ""),
                "score": q.get("score"),
                "max": q.get("max_score"),
                "score_label": q.get("score_label", "") or "",
                "evidence": ev,
                "quality_note": q.get("quality_note", "") or "",
                "correctness": sc.get("correctness", "") or "",
                "consistency": sc.get("consistency", "") or "",
            }
            if not fields:
                items.append((None, ann))
            else:
                for f in fields:
                    items.append((f, ann))
    return items


def index_issues(eval_data: dict, known_fields: set, rubric_label: str):
    """Return list of (field_name | None, issue_dict). One per (issue × field)."""
    items = []
    issues = ((eval_data.get("semantic_analysis") or {}).get("issues_detected")) or []
    for iss in issues:
        ann = {
            "kind": "issue",
            "rubric": rubric_label,
            "type": iss.get("type", ""),
            "severity": (iss.get("severity") or "info").lower(),
            "description": iss.get("description", "") or "",
            "recommendation": iss.get("recommendation", "") or "",
            "fields_involved": iss.get("fields_involved", []) or [],
        }
        # split dotted field paths and keep top-level
        tops = set()
        for fv in ann["fields_involved"]:
            top = str(fv).split(".")[0].strip()
            if top in known_fields:
                tops.add(top)
        if not tops:
            items.append((None, ann))
        else:
            for f in tops:
                items.append((f, ann))
    return items


def build_field_map(annotations):
    """Group annotations by field. Returns dict[field] -> list[ann], plus unmatched list."""
    by_field, unmatched = {}, []
    seen_unmatched = set()
    for field, ann in annotations:
        if field is None:
            # de-dup unmatched (same ann object may appear multiple times if it had 0 fields)
            key = (ann.get("kind"), ann.get("label", ""), ann.get("sub_name", ""),
                   ann.get("type", ""), ann.get("description", "")[:80])
            if key in seen_unmatched:
                continue
            seen_unmatched.add(key)
            unmatched.append(ann)
        else:
            by_field.setdefault(field, []).append(ann)
    return by_field, unmatched


# ──────────────────── HTML rendering ────────────────────


def _row(label, value):
    s = _text(value)
    if not s:
        return ""
    return f'<div class="ann-row"><span class="ann-k">{label}</span><span class="ann-v">{html.escape(s)}</span></div>'


def render_annotation(ann) -> str:
    if ann["kind"] == "r10":
        score = ann["score"]
        badge = "✓" if score == 1 else "✗"
        badge_color = "#27ae60" if score == 1 else "#c0392b"
        return f"""
<div class="ann ann-r10">
  <div class="ann-head">
    <span class="badge" style="background:{badge_color};">{badge} {score}/1</span>
    <span class="ann-label">{html.escape(_text(ann["label"]))}</span>
    <span class="ann-sub">{html.escape(_text(ann["sub_name"]))}</span>
  </div>
  <div class="ann-body">
    {_row("evidence", ann.get("evidence"))}
    {_row("quality", ann.get("quality_note"))}
    {_row("semantic", ann.get("semantic_validation"))}
  </div>
</div>
""".strip()
    if ann["kind"] == "r20":
        score, mx = ann["score"], ann["max"]
        pct = (score / mx) if (isinstance(score, (int, float)) and isinstance(mx, (int, float)) and mx) else None
        if pct is None:
            badge_color = "#7f8c8d"
        elif pct >= 0.8:
            badge_color = "#27ae60"
        elif pct >= 0.5:
            badge_color = "#f39c12"
        else:
            badge_color = "#c0392b"
        return f"""
<div class="ann ann-r20">
  <div class="ann-head">
    <span class="badge" style="background:{badge_color};">{score}/{mx}</span>
    <span class="ann-label">{html.escape(_text(ann["label"]))}</span>
    <span class="ann-sub">{html.escape(_text(ann["sub_name"]))}</span>
  </div>
  <div class="ann-body">
    {_row("level", ann.get("score_label"))}
    {_row("evidence", ann.get("evidence"))}
    {_row("quality", ann.get("quality_note"))}
    {_row("correctness", ann.get("correctness"))}
    {_row("consistency", ann.get("consistency"))}
  </div>
</div>
""".strip()
    if ann["kind"] == "issue":
        sev = _text(ann.get("severity")) or "info"
        color = SEVERITY_COLOR.get(sev, "#7f8c8d")
        fields_str = ", ".join(html.escape(_text(f)) for f in ann.get("fields_involved", []))
        return f"""
<div class="ann ann-issue" style="border-left-color:{color};">
  <div class="ann-head">
    <span class="badge" style="background:{color};">⚠ {html.escape(sev)}</span>
    <span class="ann-label">{html.escape(_text(ann.get("rubric")))} · {html.escape(_text(ann.get("type")))}</span>
  </div>
  <div class="ann-body">
    {_row("issue", ann.get("description"))}
    {('<div class="ann-row"><span class="ann-k">fields</span><span class="ann-v">' + fields_str + '</span></div>') if fields_str else ''}
    {_row("fix", ann.get("recommendation"))}
  </div>
</div>
""".strip()
    return ""


CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
       margin: 0; padding: 0; background: #f5f5f7; color: #222; line-height: 1.45; }
.wrap { max-width: 1500px; margin: 0 auto; padding: 24px; }
h1 { font-size: 1.6em; margin: 0 0 4px 0; }
h2 { font-size: 1.2em; margin: 24px 0 10px 0; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 6px; }
h3 { font-size: 1.0em; margin: 14px 0 6px 0; color: #34495e; }
.meta { color: #555; margin-bottom: 14px; font-size: 0.92em; }
.scorecard { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px,1fr));
             gap: 12px; margin: 14px 0 24px 0; }
.score { background: white; border-radius: 8px; padding: 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.score .num { font-size: 1.9em; font-weight: 700; color: #2c3e50; }
.score .lbl { color: #777; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.04em; }
.score .pct { color: #16a085; font-weight: 600; margin-left: 6px; }

.sw { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
.sw .col { background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.sw .col ul { padding-left: 18px; margin: 4px 0 0 0; }
.sw .col li { margin: 4px 0; }
.sw .strengths h3 { color: #27ae60; }
.sw .weaknesses h3 { color: #c0392b; }

.field { background: white; border-radius: 8px; padding: 0; margin: 14px 0;
         box-shadow: 0 1px 3px rgba(0,0,0,0.06); display: grid;
         grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 0; overflow: hidden; }
.field .yaml { background: #fbfcfe; padding: 14px 16px; border-right: 1px solid #ecedef; min-width: 0; }
.field .yaml pre { margin: 0; font-family: 'SF Mono', 'Menlo', 'Monaco', monospace;
                   font-size: 0.84em; white-space: pre-wrap; word-break: break-word;
                   color: #2c3e50; }
.field .yaml .field-name { font-size: 0.85em; color: #999; text-transform: uppercase;
                           letter-spacing: 0.04em; margin-bottom: 6px; font-weight: 600; }
.field .anns { padding: 14px 16px; background: white; min-width: 0; }
.field .anns.empty { color: #aaa; font-style: italic; font-size: 0.85em; }

.ann { background: #f7f8fa; border-left: 4px solid #3498db; padding: 10px 12px;
       margin-bottom: 8px; border-radius: 0 6px 6px 0; font-size: 0.85em; }
.ann-r10 { border-left-color: #9b59b6; }
.ann-r20 { border-left-color: #16a085; }
.ann-issue { border-left-color: #e67e22; }
.ann-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 4px; }
.badge { color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.78em; font-weight: 600; white-space: nowrap; }
.ann-label { font-weight: 600; color: #555; }
.ann-sub { color: #666; }
.ann-body { color: #444; }
.ann-row { display: grid; grid-template-columns: 90px 1fr; gap: 8px; margin-top: 4px; }
.ann-k { font-size: 0.85em; color: #888; text-transform: uppercase; letter-spacing: 0.04em; }
.ann-v { word-break: break-word; }

.unmatched { background: white; border-radius: 8px; padding: 14px 16px; margin: 16px 0;
             box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.recs { background: white; border-radius: 8px; padding: 14px 16px; margin: 16px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.recs ol { margin: 8px 0 0 0; padding-left: 22px; }
.recs li { margin: 6px 0; }
.legend { font-size: 0.8em; color: #777; margin-top: 6px; }
.legend .key { display: inline-block; width: 12px; height: 12px; border-radius: 2px; vertical-align: middle; margin-right: 4px; }
"""


def render_html(yaml_data: dict, r10: dict, r20: dict, source_paths: dict) -> str:
    known_fields = set(yaml_data.keys())
    items_r10 = index_rubric10(r10, known_fields)
    items_r20 = index_rubric20(r20, known_fields)
    items_iss_r10 = index_issues(r10, known_fields, "R10")
    items_iss_r20 = index_issues(r20, known_fields, "R20")
    all_items = items_r10 + items_r20 + items_iss_r10 + items_iss_r20

    by_field, unmatched = build_field_map(all_items)

    # summary
    r10_total = (r10.get("summary_scores") or r10.get("overall_score") or {}).get("total_score") or \
                (r10.get("overall_score") or {}).get("total_points")
    r10_max = (r10.get("summary_scores") or r10.get("overall_score") or {}).get("total_max_score") or \
              (r10.get("overall_score") or {}).get("max_points") or 50
    r10_pct = (r10.get("summary_scores") or r10.get("overall_score") or {}).get("overall_percentage") or \
              (r10.get("overall_score") or {}).get("percentage")

    r20_total = (r20.get("overall_score") or {}).get("total_points") or \
                (r20.get("summary_scores") or {}).get("total_score")
    r20_max = (r20.get("overall_score") or {}).get("max_points") or \
              (r20.get("summary_scores") or {}).get("total_max_score") or RUBRIC20_MAX_SCORE
    r20_pct = (r20.get("overall_score") or {}).get("percentage") or \
              (r20.get("summary_scores") or {}).get("overall_percentage")

    project = r10.get("project") or r20.get("project") or "Unknown"
    method = r10.get("method") or r20.get("method") or "Unknown"
    model = (r10.get("model", {}) or {}).get("name") or (r20.get("model", {}) or {}).get("name") or ""

    # assessment lists (prefer R20, fallback R10)
    r20_assess = r20.get("assessment", {}) or {}
    r10_assess = r10.get("assessment", {}) or {}
    strengths = r20_assess.get("strengths") or r10_assess.get("strengths") or []
    weaknesses = r20_assess.get("weaknesses") or r10_assess.get("weaknesses") or []

    def _as_list(x):
        if isinstance(x, list): return x
        if isinstance(x, dict): return [f"{k}: {_text(v)}" for k, v in x.items()]
        if x in (None, ""): return []
        return [x]

    recs = []
    for r in _as_list(r10.get("recommendations") or r10_assess.get("recommendations")):
        recs.append(("R10", r))
    for r in _as_list(r20.get("recommendations") or r20_assess.get("recommendations")):
        recs.append(("R20", r))

    # Render
    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Interleaved D4D Evaluation — {html.escape(project)} ({html.escape(method)})</title>
<style>{CSS}</style></head><body><div class="wrap">""")

    parts.append(f"""
<h1>Interleaved Semantic Evaluation</h1>
<div class="meta">
  Project: <b>{html.escape(project)}</b> &middot; Method: <b>{html.escape(method)}</b><br>
  YAML: <code>{html.escape(source_paths.get('yaml',''))}</code><br>
  R10 JSON: <code>{html.escape(source_paths.get('r10',''))}</code><br>
  R20 JSON: <code>{html.escape(source_paths.get('r20',''))}</code><br>
  Model: <code>{html.escape(model)}</code>
</div>
""")

    def _fmt_pct(p):
        if p is None: return ""
        try: return f"({float(p):.1f}%)"
        except Exception: return ""

    parts.append('<div class="scorecard">')
    parts.append(f'<div class="score"><div class="lbl">Rubric10 (semantic)</div>'
                 f'<div class="num">{r10_total}/{r10_max} <span class="pct">{_fmt_pct(r10_pct)}</span></div></div>')
    parts.append(f'<div class="score"><div class="lbl">Rubric20 (semantic)</div>'
                 f'<div class="num">{r20_total}/{r20_max} <span class="pct">{_fmt_pct(r20_pct)}</span></div></div>')
    cc10 = (r10.get("semantic_analysis") or {}).get("consistency_checks", {}) or {}
    cc20 = (r20.get("semantic_analysis") or {}).get("consistency_checks", {}) or {}
    def _cc_len(d, k):
        v = d.get(k)
        if isinstance(v, list): return len(v)
        if isinstance(v, int): return v
        return 0
    parts.append(f'<div class="score"><div class="lbl">Consistency checks (R10/R20)</div>'
                 f'<div class="num">{_cc_len(cc10,"passed")+_cc_len(cc20,"passed")} <span class="pct">pass</span> · '
                 f'{_cc_len(cc10,"failed")+_cc_len(cc20,"failed")} fail · '
                 f'{_cc_len(cc10,"warnings")+_cc_len(cc20,"warnings")} warn</div></div>')
    parts.append(f'<div class="score"><div class="lbl">Mapped feedback / fields</div>'
                 f'<div class="num">{sum(len(v) for v in by_field.values())} <span class="pct">across {len(by_field)} fields</span></div></div>')
    parts.append('</div>')
    parts.append('<div class="legend">'
                 '<span class="key" style="background:#9b59b6;"></span>R10 sub-element '
                 '<span class="key" style="background:#16a085;"></span>R20 question '
                 '<span class="key" style="background:#e67e22;"></span>Semantic issue'
                 '</div>')

    if strengths or weaknesses:
        parts.append('<div class="sw">')
        if strengths:
            parts.append('<div class="col strengths"><h3>Strengths</h3><ul>'
                         + "".join(f"<li>{html.escape(_text(s))}</li>" for s in strengths)
                         + '</ul></div>')
        if weaknesses:
            parts.append('<div class="col weaknesses"><h3>Weaknesses</h3><ul>'
                         + "".join(f"<li>{html.escape(_text(s))}</li>" for s in weaknesses)
                         + '</ul></div>')
        parts.append('</div>')

    parts.append('<h2>Field-by-field</h2>')
    for key, value in yaml_data.items():
        block = yaml_block(key, value)
        anns = by_field.get(key, [])
        # sort: issues first by severity, then r10, then r20
        sev_order = {"high": 0, "warning": 1, "medium": 1, "low": 2, "info": 3}
        def _sortkey(a):
            if a["kind"] == "issue":
                return (0, sev_order.get(a.get("severity",""), 4), a.get("type",""))
            if a["kind"] == "r10":
                return (1, 0, a.get("label",""))
            return (2, 0, a.get("label",""))
        anns_sorted = sorted(anns, key=_sortkey)

        anns_html = "".join(render_annotation(a) for a in anns_sorted) if anns_sorted else \
                    '<span>no field-level feedback matched</span>'
        cls_anns = "anns" if anns_sorted else "anns empty"
        parts.append(f"""
<div class="field" id="field-{html.escape(str(key))}">
  <div class="yaml">
    <div class="field-name">{html.escape(str(key))}</div>
    <pre>{html.escape(block)}</pre>
  </div>
  <div class="{cls_anns}">{anns_html}</div>
</div>
""")

    if unmatched:
        parts.append('<h2>Unmatched feedback</h2>')
        parts.append('<div class="unmatched">'
                     '<div style="color:#777;font-size:0.88em;margin-bottom:8px;">Feedback that referenced multiple fields or no specific field.</div>'
                     + "".join(render_annotation(a) for a in unmatched)
                     + '</div>')

    if recs:
        parts.append('<h2>Recommendations</h2>')
        parts.append('<div class="recs"><ol>')
        for rub, r in recs:
            parts.append(f'<li><b style="color:#9b59b6;">{rub}</b> &middot; {html.escape(_text(r))}</li>')
        parts.append('</ol></div>')

    parts.append('</div></body></html>')
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaml", required=True, type=Path)
    ap.add_argument("--r10", required=True, type=Path)
    ap.add_argument("--r20", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    if not args.yaml.exists():
        sys.exit(f"YAML not found: {args.yaml}")
    if not args.r10.exists():
        sys.exit(f"R10 JSON not found: {args.r10}")
    if not args.r20.exists():
        sys.exit(f"R20 JSON not found: {args.r20}")

    yaml_data = load_yaml_ordered(args.yaml)
    with args.r10.open() as f: r10 = json.load(f)
    with args.r20.open() as f: r20 = json.load(f)

    repo_root = Path(__file__).resolve().parent.parent
    def _rel(p):
        try: return str(p.resolve().relative_to(repo_root))
        except ValueError: return str(p)

    sources = {
        "yaml": _rel(args.yaml),
        "r10": _rel(args.r10),
        "r20": _rel(args.r20),
    }

    out_html = render_html(yaml_data, r10, r20, sources)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(out_html, encoding="utf-8")
    print(f"Wrote {args.out} ({args.out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
