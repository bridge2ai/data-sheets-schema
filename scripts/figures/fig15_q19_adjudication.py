#!/usr/bin/env python
"""#2303 idea 4: where the rubric20 Q19 provenance rationales were flagged for adjudication.

Record set: notes/reference_rescore_2026-09-12_cborg_runtime/semantic_review.json (issue
#1349), the targeted inspection of all 24 accepted rubric20 Q19 ratings in the frozen CBORG
reference rescore: 4 projects x v7/v8 prompt x 3 generation replicates, one primary rating
each, every record an API-arm record (read from its `Agent runtime` header). The review's own
fields give, per case, the job id, the evaluation and input paths with their SHA-256, a
`status` (`requires_adjudication` or `not_flagged_by_this_inspection`), a free-text
`assessment`, and a copy of the original Q19 object. At run time the script checks the review's
manifest hash, the file-level flag count, every evaluation/input hash, the job's manifest entry
and that the Q19 score in the evaluation JSON equals the review's copy.

Method. The review has no structured concern field, so concern types are coded from the
`assessment` prose by the fixed keyword rules in CONCERNS below (a heuristic, labelled as such
on the figure). The prose is split into sentences; for the concern columns, sentences that only
describe the input record (beginning "The input", "Its own input", ..., or beginning "It" right
after such a sentence) are set aside because they report what the record contains rather than a
concern. For each case and concern:
  * "stated limit" (filled circle) - some matching sentence carries a limit cue (withholds,
    blocked, reserves, requires, stated reason, limiting, remaining concerns, asks for, ...) and
    no negation/acceptance cue (does not,
    despite, without, accepts, informational, may be, remain unadjudicated, ...);
  * "named" (open circle) - the concern is named, but not in a sentence of that kind;
  * "not named" (small dash) - no matching sentence.
Two further columns code the reviewer's own statements rather than the rationale's concerns:
input evidence the rationale overlooked, and an explicit disclaimer that the inspection does not
certify or adjudicate the rest. The rules, the cue lists and every matched sentence are exported
to CSV so each mark can be reproduced and challenged. The side dot plot is the original Q19 score
(of 5) read from the evaluation JSON. Two count rows give the filled marks per column among flagged
and unflagged ratings. The three quoted evidence examples are chosen by a fixed rule
(evidence_examples) and quoted verbatim except for a space inserted where the source runs a word
into a number ("records4/5"). The frozen text-or-graph rule is quoted from the rubric20
definition at the manifest's definition_commit (read-only `git show`, hash-checked).

Outputs (st.save): fig15_q19_adjudication.csv (one row per rating: identifiers, status, Q19 score,
per-concern state), _cells.csv (rating x concern, with sentence counts), _sentences.csv (every
matched sentence with its cues and exclusion), _column_counts.csv, _rules.csv, _evidence.csv and
_checks.csv (the run-time verifications above).

Caveats. The review assigns no replacement scores; flagged ratings keep their original Q19 and
their totals are only qualified. "Not flagged" means not flagged by this targeted inspection,
not certified correct, and is drawn in neutral gray rather than a "good" status color. Keyword
coding reads the reviewer's wording, so it cannot show whether a concern was justified.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

ARCH = st.ROOT / "notes" / "reference_rescore_2026-09-12_cborg_runtime"
REVIEW = ARCH / "semantic_review.json"
FLAGGED = "requires_adjudication"
UNFLAGGED = "not_flagged_by_this_inspection"

# (key, column label, group, rule). Groups: "rep" = representation demands attributed to the
# original rationale; "other" = other substantive concerns the review names; "review" = the
# reviewer's own statements. Rules are case-insensitive regular expressions over one sentence.
CONCERNS = [
    ("empty_field", "empty\nderivation\nfield", "rep",
     r"was_derived_from|parent_datasets|was_generated_by|derivation fields?|dedicated[- ]fields?|"
     r"designated (?:graph )?fields|provenance fields|structured derivation"),
    ("graph", "graph or\nPROV\nexpression", "rep",
     r"(?<!or-)\bgraph\b|PROV-O|\bPROV\b|serializ|addressable|\bRDF\b"),
    ("machine", "machine-\nreadable or\ntraversable", "rep",
     r"machine[- ]?(?:readab|actionab|travers)|mechanical|machine cannot|human-readable"),
    ("scattered", "links\nspread across\nfields", "rep",
     r"scattered|spans sections|across (?:four |unrelated )?(?:fields|sections)|matching prose|for their placement"),
    ("version", "version\naccess or\nerrata", "other",
     r"version access|errata|unversioned|versioning|non-monotonic"),
    ("missing", "missingness\nor QC", "other",
     r"missingness|missing[- ]data|QC gaps|coverage"),
    ("granularity", "artifact-\nlevel\ngranularity", "other",
     r"granularit|artifact-level|source-to-artifact|source-to-output|specific released|particular released|"
     r"released archive|released file|file-by-file|per-artifact|released-artifact|feature-file|variable-level"),
    ("overlooked", "input\nevidence\noverlooked", "review", r"overlook"),
    ("disclaimer", "certification\ndisclaimed", "review", r"certif|not adjudicat|unadjudicated"),
]
GROUP_LABEL = {"rep": "Representation demands attributed to the rationale",
               "other": "Other concerns named",
               "review": "Reviewer's own statements"}
LIMIT_CUE = (r"withh[oe]ld|withholds|withholding|blocked|reserves|stated reason|limiting|\brequires?\b|"
             r"\brequired\b|\brequiring\b|penaliz|short of|falls short|\bdeduction\b|\badds? (?:a|the)\b|"
             r"\bremaining concerns?\b|\basks for\b")
NEGATION_CUE = (r"\bdoes not\b|\bdo not\b|\bnot a deduction\b|\bwithout\b|\bdespite\b|\binformational\b|"
                r"\baccepts?\b|\baccepted\b|\bneither\b|\bno requirement\b|\bnot clearly\b|"
                r"rather than (?:imposing|an explicit)|\bcould apply\b|\bmay be\b|\bmay still\b|"
                r"\bremains? (?:unadjudicated|independent|matters)\b|\bnot adjudicated\b")
INPUT_SENTENCE = r"^(?:The|Its own|The own|Its) input\b"
INPUT_CONTINUATION = r"^It\b"               # "It ..." right after an input sentence
# used only to choose the quoted evidence examples, never to code a cell
WITHHOLD_CUE = r"withh[oe]ld|withholds|withholding|blocked|reserves|stated reason"
NO_DEDUCTION_CUE = r"informational|not a deduction|does not deduct|without reducing|do not reduce|without penalizing"
SENTENCE_SPLIT = r"(?<=[.;])\s+(?=[A-Z])"
FROZEN_RULE = r"Provenance may be represented as text OR as W3C PROV-O graphs\.[^.\n]*\."


def flat(label: str) -> str:
    """Column label on one line (a hyphen at a line break joins the word)."""
    return label.replace("-\n", "-").replace("\n", " ")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def header_fields(path: Path) -> dict[str, str]:
    out = {}
    with path.open() as fh:
        for line in fh:
            if not line.startswith("#"):
                break
            m = re.match(r"#\s*([^:]+):\s*(.*)", line)
            if m:
                out[m.group(1).strip()] = m.group(2).strip()
    return out


def find_q19(doc):
    """The item with id 19 in an evaluation JSON, wherever the instrument nests it."""
    hits = []

    def walk(x):
        if isinstance(x, dict):
            if x.get("id") == 19 and "score" in x and "max_score" in x:
                hits.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(doc)
    assert len(hits) == 1, f"expected one Q19 item, found {len(hits)}"
    return hits[0]


def frozen_rule(manifest) -> tuple[str, str]:
    """Quote the text-or-graph sentence from the rubric20 definition at the frozen commit (read-only)."""
    inst = manifest["instruments"]["rubric20-semantic"]
    try:
        blob = subprocess.check_output(["git", "show", f'{manifest["definition_commit"]}:{inst["definition"]}'],
                                       cwd=st.ROOT, stderr=subprocess.DEVNULL)
    except Exception:
        return "", "frozen definition not readable from git"
    if hashlib.sha256(blob).hexdigest() != inst["definition_sha256"]:
        return "", "frozen definition hash mismatch"
    m = re.search(FROZEN_RULE, blob.decode())
    return (m.group(0), "verified against definition_sha256") if m else ("", "rule sentence not found")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(SENTENCE_SPLIT, text) if s.strip()]


def display(s: str) -> str:
    """Whitespace-only normalization for quoting: the source prose runs some numbers into words."""
    return re.sub(r"\b(awards|records|withholds|withholding|assign|assigning|assigns|replacement|that)(\d)", r"\1 \2", s)


def input_sentences(ss: list[str]) -> list[bool]:
    """A sentence describes the input record if it begins "The input", "Its own input", ... or if it
    begins "It" and directly follows such a sentence (pronoun continuation)."""
    out, prev = [], False
    for s in ss:
        cur = bool(re.match(INPUT_SENTENCE, s)) or (prev and bool(re.match(INPUT_CONTINUATION, s)))
        out.append(cur)
        prev = cur
    return out


def code_case(assessment: str):
    ss = sentences(assessment)
    is_input_all = input_sentences(ss)
    states, hits = {}, []
    for key, _label, group, rule in CONCERNS:
        rx = re.compile(rule, re.I)
        n_named = n_limit = 0
        for s, s_input in zip(ss, is_input_all):
            m = rx.search(s)
            if not m:
                continue
            # input-description sentences are set aside for concern columns only; a reviewer's
            # disclaimer may begin "The input does not ... so ... are not certified"
            is_input = group != "review" and s_input
            lim = bool(re.search(LIMIT_CUE, s, re.I))
            neg = bool(re.search(NEGATION_CUE, s, re.I))
            limit_here = group != "review" and lim and not neg and not is_input
            hits.append({"concern": key, "matched": m.group(0), "limit_cue": lim, "negation_cue": neg,
                         "input_description_excluded": is_input, "counts_as_stated_limit": limit_here,
                         "sentence": s})
            if is_input:
                continue
            n_named += 1
            n_limit += limit_here
        if group == "review":
            states[key] = "stated" if n_named else "not named"
        else:
            states[key] = "stated limit" if n_limit else ("named" if n_named else "not named")
    return states, hits


def load():
    review = json.loads(REVIEW.read_text())
    manifest = json.loads((ARCH / "manifest.json").read_text())
    checks = [{"check": "review manifest_sha256 equals manifest.json", "value": review["manifest_sha256"] == sha256(ARCH / "manifest.json")},
              {"check": "review definition_sha256 equals rubric20 definition_sha256",
               "value": review["definition_sha256"] == manifest["instruments"]["rubric20-semantic"]["definition_sha256"]}]
    jobs = {j["id"]: j for j in manifest["jobs"]}
    rows, cells, sents = [], [], []
    for c in review["cases"]:
        out, inp = st.ROOT / c["output"], st.ROOT / c["input"]
        assert sha256(out) == c["evaluation_sha256"], c["job_id"]
        assert sha256(inp) == c["input_sha256"], c["job_id"]
        job = jobs[c["job_id"]]
        assert job["input"] == c["input"] and job["rubric"] == "rubric20-semantic", c["job_id"]
        q_eval = find_q19(json.loads(out.read_text()))
        assert (q_eval["score"], q_eval["max_score"]) == (c["q19"]["score"], c["q19"]["max_score"]), c["job_id"]
        assert c["status"] in (FLAGGED, UNFLAGGED), c["status"]
        states, hits = code_case(c["assessment"])
        runtime = header_fields(inp).get("Agent runtime", "")
        row = {"job_id": c["job_id"], "project": job["project"], "cohort": job["cohort"],
               "generation_rep": job["generation_rep"], "rating": job["rating"], "purpose": job["purpose"],
               "agent_runtime_header": runtime, "status": c["status"], "flagged": c["status"] == FLAGGED,
               "q19_score": q_eval["score"], "q19_max": q_eval["max_score"],
               "q19_score_label": c["q19"]["score_label"],
               **{f"concern_{k}": states[k] for k, *_ in CONCERNS}}
        rows.append(row)
        for k, label, group, _ in CONCERNS:
            ks = [h for h in hits if h["concern"] == k]
            cells.append({"job_id": c["job_id"], "status": c["status"], "concern": k, "concern_label": flat(label),
                          "group": group, "state": states[k],
                          "sentences_matched": sum(not h["input_description_excluded"] for h in ks),
                          "sentences_stated_limit": sum(h["counts_as_stated_limit"] for h in ks),
                          "input_description_sentences_excluded": sum(h["input_description_excluded"] for h in ks)})
        for h in hits:
            sents.append({"job_id": c["job_id"], "status": c["status"], **h})
    n_flag = sum(r["flagged"] for r in rows)
    n_api = sum("Claude API" in r["agent_runtime_header"] for r in rows)
    assert n_api == len(rows), f"{n_api} of {len(rows)} inputs carry a Claude API runtime header"
    checks += [{"check": "cases", "value": len(rows)},
               {"check": "cases with status requires_adjudication", "value": n_flag},
               {"check": "file-level ratings_requiring_adjudication", "value": review["ratings_requiring_adjudication"]},
               {"check": "evaluation and input SHA-256 match for every case", "value": True},
               {"check": "Q19 score in evaluation JSON equals review copy for every case", "value": True},
               {"check": "records with an API runtime header", "value": n_api}]
    assert n_flag == review["ratings_requiring_adjudication"]
    order = {p: i for i, p in enumerate(st.PROJECTS)}
    rows.sort(key=lambda r: (order.get(r["project"], 99), r["cohort"], r["generation_rep"]))
    return review, manifest, rows, cells, sents, checks


def evidence_examples(rows, sents, n_flagged_examples: int = 2):
    """Deterministic choice of quotes that describe the original rationale's own reasoning.
    Flagged: walk the representation concerns in column order; for each, take the shortest
    stated-limit sentence in a flagged case that also carries a withholding cue (WITHHOLD_CUE), is
    not already used and comes from a case not already quoted. Not flagged: the shortest
    representation sentence in an unflagged case carrying an explicit no-deduction cue (NO_DEDUCTION_CUE)."""
    status = {r["job_id"]: r["status"] for r in rows}
    rep_keys = [k for k, _l, g, _r in CONCERNS if g == "rep"]
    used, jobs, out = set(), set(), []
    for k in rep_keys:
        cand = sorted({(len(h["sentence"]), h["job_id"], h["sentence"]) for h in sents
                       if h["concern"] == k and h["counts_as_stated_limit"] and status[h["job_id"]] == FLAGGED
                       and re.search(WITHHOLD_CUE, h["sentence"], re.I)
                       and h["sentence"] not in used and h["job_id"] not in jobs})
        if cand:
            _, jid, s = cand[0]
            used.add(s); jobs.add(jid)
            out.append({"kind": "flagged; named as the score limit", "concern": k, "job_id": jid, "sentence": s})
        if len(out) == n_flagged_examples:
            break
    cand = sorted({(len(h["sentence"]), h["job_id"], h["sentence"], h["concern"]) for h in sents
                   if h["concern"] in rep_keys and not h["input_description_excluded"]
                   and re.search(NO_DEDUCTION_CUE, h["sentence"], re.I) and status[h["job_id"]] == UNFLAGGED})
    if cand:
        _, jid, s, k = cand[0]
        out.append({"kind": "not flagged; named, not a limit", "concern": k, "job_id": jid, "sentence": s})
    return out


def row_label(r) -> str:
    return f'{r["cohort"]}  rep {r["generation_rep"]}'


def main() -> int:
    st.apply()
    review, manifest, rows, cells, sents, checks = load()
    rule_text, rule_check = frozen_rule(manifest)
    checks.append({"check": "frozen text-or-graph rule quoted from definition_commit", "value": rule_check})
    n = len(rows)
    n_flag = sum(r["flagged"] for r in rows)
    n_unflag = n - n_flag
    n_api = sum("Claude API" in r["agent_runtime_header"] for r in rows)   # asserted == n in load()
    keys = [k for k, *_ in CONCERNS]
    groups = [g for _k, _l, g, _r in CONCERNS]
    rep_keys = [k for k, g in zip(keys, groups) if g == "rep"]

    # ---- geometry, in inches: matrix x data units ARE inches; y data units are rows
    COL0, COL_STEP, GROUP_GAP = 2.15, 0.66, 0.30
    xs, x = [], COL0
    for i, g in enumerate(groups):
        if i and g != groups[i - 1]:
            x += GROUP_GAP
        xs.append(x)
        x += COL_STEP
    x_last = xs[-1]
    X_PROJ, X_STATUS, X_LABEL, X_OUT0 = 0.88, 1.02, 1.19, 1.13
    MAT_W = x_last + 0.42
    DOT_X0, DOT_W = MAT_W + 0.45, 1.35
    W = DOT_X0 + DOT_W + 0.25
    ROW_IN, TOP_IN = 0.215, 1.50
    Y_TOP, Y_BOT = -0.7, n + 2.0
    mat_h_in = (Y_BOT - Y_TOP) * ROW_IN
    LEG_IN = TOP_IN + mat_h_in + 0.18
    EV_IN = LEG_IN + 1.08
    H = EV_IN + 2.62
    fy = lambda inch: 1.0 - inch / H               # noqa: E731  inches from top -> figure fraction
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, fy(TOP_IN + mat_h_in), MAT_W / W, mat_h_in / H])
    axd = fig.add_axes([DOT_X0 / W, fy(TOP_IN + mat_h_in), DOT_W / W, mat_h_in / H], sharey=ax)
    ax.set_xlim(0, MAT_W)
    ax.set_ylim(Y_BOT, Y_TOP)
    ax.axis("off")

    y_of = {r["job_id"]: i for i, r in enumerate(rows)}
    y_cnt = [n + 0.45, n + 1.45]
    flag_color = st.STATUS["warning"]

    # column guides
    for xc in xs:
        ax.plot([xc, xc], [-0.45, n - 0.55], color=st.INK["grid"], linewidth=0.5, zorder=0)
    # project labels and separators
    for pi, proj in enumerate(st.PROJECTS):
        idx = [y_of[r["job_id"]] for r in rows if r["project"] == proj]
        if not idx:
            continue
        y0, y1 = min(idx), max(idx)
        ax.text(X_PROJ, (y0 + y1) / 2, proj.replace("_", "-"), ha="right", va="center", fontsize=8.5,
                fontweight="bold", color=st.INK["secondary"])
        if pi:
            ax.plot([0.15, x_last + 0.36], [y0 - 0.5, y0 - 0.5], color=st.INK["axis"], linewidth=0.7, zorder=1)
            axd.axhline(y0 - 0.5, color=st.INK["axis"], linewidth=0.7, zorder=1)
    # rows
    for r in rows:
        y = y_of[r["job_id"]]
        ax.text(X_LABEL, y, row_label(r), ha="left", va="center", fontsize=7.6, color=st.INK["primary"])
        if r["flagged"]:
            ax.plot(X_STATUS, y, marker="s", markersize=6.2, color=flag_color, markeredgecolor=st.INK["secondary"],
                    markeredgewidth=0.6, linestyle="none", zorder=4)
            ax.add_patch(FancyBboxPatch((X_OUT0, y - 0.41), x_last + 0.30 - X_OUT0, 0.82,
                                        boxstyle="round,pad=0,rounding_size=0.08", fill=False,
                                        edgecolor=flag_color, linewidth=1.5, zorder=2))
        else:
            ax.plot(X_STATUS, y, marker="s", markersize=5.6, markerfacecolor="none", markeredgecolor=st.INK["muted"],
                    markeredgewidth=0.8, linestyle="none", zorder=4)
        for k, xc, g in zip(keys, xs, groups):
            state = r[f"concern_{k}"]
            if state in ("stated limit", "stated"):
                ax.plot(xc, y, marker="o" if g != "review" else "s", markersize=6.4 if g != "review" else 5.8,
                        color=st.INK["primary"], markeredgecolor=st.INK["surface"], markeredgewidth=0.8,
                        linestyle="none", zorder=5)
            elif state == "named":
                ax.plot(xc, y, marker="o", markersize=6.0, markerfacecolor=st.INK["surface"],
                        markeredgecolor=st.INK["secondary"], markeredgewidth=1.1, linestyle="none", zorder=5)
            else:
                ax.plot([xc - 0.07, xc + 0.07], [y, y], color=st.INK["axis"], linewidth=1.0, zorder=3)

    # column headers and group headers
    for (_k, label, _g, _r), xc in zip(CONCERNS, xs):
        ax.text(xc, -0.8, label, ha="center", va="bottom", fontsize=7.0, color=st.INK["secondary"], linespacing=1.05)
    for g in dict.fromkeys(groups):
        gx = [xc for xc, gg in zip(xs, groups) if gg == g]
        yh = -2.75
        ax.plot([min(gx) - 0.28, max(gx) + 0.28], [yh + 0.12, yh + 0.12], color=st.INK["axis"], linewidth=0.8, clip_on=False)
        width_chars = int((max(gx) - min(gx) + 0.6) * 11.5)
        ax.text((min(gx) + max(gx)) / 2, yh - 0.1, textwrap.fill(GROUP_LABEL[g], max(width_chars, 14)), ha="center",
                va="bottom", fontsize=7.4, color=st.INK["primary"], fontweight="bold", clip_on=False, linespacing=1.05)
    ax.text(X_LABEL - 0.05, -0.8, "rating\n(prompt,\nreplicate)", ha="left", va="bottom", fontsize=7.0,
            color=st.INK["secondary"], linespacing=1.05)
    ax.text((min(xs[:len(rep_keys)]) + x_last) / 2, -4.55,
            "Concerns coded from the review's prose by keyword rules (heuristic)", ha="center", va="bottom",
            fontsize=7.4, color=st.INK["secondary"], style="italic", clip_on=False)

    # count rows
    counts = []
    for k, label, g, _ in CONCERNS:
        filled = ("stated",) if g == "review" else ("stated limit",)
        counts.append({"concern": k, "concern_label": flat(label), "group": g,
                       "filled_mark_flagged": sum(1 for r in rows if r["flagged"] and r[f"concern_{k}"] in filled),
                       "filled_mark_not_flagged": sum(1 for r in rows if not r["flagged"] and r[f"concern_{k}"] in filled),
                       "named_any_flagged": sum(1 for r in rows if r["flagged"] and r[f"concern_{k}"] != "not named"),
                       "named_any_not_flagged": sum(1 for r in rows if not r["flagged"] and r[f"concern_{k}"] != "not named"),
                       "flagged_ratings": n_flag, "not_flagged_ratings": n_unflag})
    by_key = {c["concern"]: c for c in counts}
    ax.plot([0.15, x_last + 0.36], [n - 0.15, n - 0.15], color=st.INK["axis"], linewidth=0.7)
    for yc, lab, fld in ((y_cnt[0], f"filled marks, flagged (of {n_flag})", "filled_mark_flagged"),
                         (y_cnt[1], f"filled marks, not flagged (of {n_unflag})", "filled_mark_not_flagged")):
        ax.text(COL0 - 0.3, yc, lab, ha="right", va="center", fontsize=7.0, color=st.INK["secondary"])
        for c, xc in zip(counts, xs):
            ax.text(xc, yc, str(c[fld]), ha="center", va="center", fontsize=7.6, color=st.INK["primary"])

    # side dot plot: original Q19 score
    for r in rows:
        axd.plot(r["q19_score"], y_of[r["job_id"]], marker="o", markersize=6.2, color=st.ARM_COLOR["api"],
                 markeredgecolor=st.INK["surface"], markeredgewidth=0.9, linestyle="none", zorder=4)
    q_max = max(r["q19_max"] for r in rows)
    q_min = min(r["q19_score"] for r in rows)
    axd.set_xlim(q_min - 0.6, q_max + 0.4)
    axd.set_xticks(range(q_min, q_max + 1))
    for side in ("left", "right", "bottom", "top"):
        axd.spines[side].set_visible(False)
    axd.tick_params(axis="y", left=False, labelleft=False)
    for v in range(q_min, q_max + 1):
        axd.plot([v, v], [-0.45, n - 0.55], color=st.INK["grid"], linewidth=0.6, zorder=0)
    axd.xaxis.set_ticks_position("top")
    axd.xaxis.set_label_position("top")
    axd.tick_params(axis="x", length=0, pad=2)
    axd.set_xlabel(f"original Q19 score\n(of {q_max}; no replacement)", fontsize=7.2, color=st.INK["secondary"], labelpad=5)
    score_dist = {}
    for yc, flag in ((y_cnt[0], True), (y_cnt[1], False)):
        sc = [r["q19_score"] for r in rows if r["flagged"] == flag]
        dist = ", ".join(f"{sc.count(v)} at {v}" for v in sorted(set(sc), reverse=True))
        score_dist["flagged" if flag else "not_flagged"] = dist
        axd.text(q_min - 0.55, yc, dist, ha="left", va="center", fontsize=7.0, color=st.INK["primary"])

    # legend
    leg_h = [
        Line2D([], [], marker="s", markersize=6.2, color=flag_color, markeredgecolor=st.INK["secondary"], markeredgewidth=0.6,
               linestyle="none", label=f"requires adjudication ({n_flag}); row outlined"),
        Line2D([], [], marker="s", markersize=5.6, markerfacecolor="none", markeredgecolor=st.INK["muted"], linestyle="none",
               label=f"not flagged by this inspection ({n_unflag}); not certified correct"),
        Line2D([], [], marker="o", markersize=6.4, color=st.INK["primary"], markeredgecolor=st.INK["surface"], linestyle="none",
               label="named as the rationale's score limit (limit cue, no negation cue)"),
        Line2D([], [], marker="o", markersize=6.0, markerfacecolor=st.INK["surface"], markeredgecolor=st.INK["secondary"],
               markeredgewidth=1.1, linestyle="none", label="named, not as a score limit (accepted, negated or left open)"),
        Line2D([], [], color=st.INK["axis"], linewidth=1.0, label="not named in the review's assessment"),
        Line2D([], [], marker="s", markersize=5.8, color=st.INK["primary"], markeredgecolor=st.INK["surface"], linestyle="none",
               label="stated by the reviewer"),
        Line2D([], [], marker="o", markersize=6.2, color=st.ARM_COLOR["api"], markeredgecolor=st.INK["surface"], linestyle="none",
               label="original Q19 score (API-arm record)"),
    ]
    fig.legend(handles=leg_h, loc="upper left", bbox_to_anchor=(0.25 / W, fy(LEG_IN)), ncol=2, fontsize=7.3,
               handletextpad=0.5, columnspacing=1.8, labelspacing=0.55, borderaxespad=0, borderpad=0,
               title="Status comes from the review's own field; concern marks are a keyword heuristic over its prose",
               title_fontsize=7.5, alignment="left")

    # evidence examples and caveat
    ev = evidence_examples(rows, sents)
    label_of = {k: flat(l) for k, l, *_ in CONCERNS}
    x0 = 0.25 / W
    fig.text(x0, fy(EV_IN), "Short evidence examples (sentences quoted from the review's assessments; chosen by a fixed rule)",
             fontsize=7.8, fontweight="bold", color=st.INK["primary"], ha="left", va="top")
    yy = EV_IN + 0.22
    wrap_chars = int((W - 0.9) / 0.058)            # ~0.058 in per character at 7 pt
    for e in ev:
        r = next(r for r in rows if r["job_id"] == e["job_id"])
        who = f'{r["project"].replace("_", "-")} {r["cohort"]} rep {r["generation_rep"]}: {e["kind"]} ({label_of[e["concern"]]})'
        body = textwrap.wrap(f"“{display(e['sentence'])}”", wrap_chars)
        fig.text(x0, fy(yy), who, fontsize=7.0, color=st.INK["secondary"], ha="left", va="top", fontweight="bold")
        fig.text(x0 + 0.12 / W, fy(yy + 0.15), "\n".join(body), fontsize=7.0, color=st.INK["primary"],
                 ha="left", va="top", linespacing=1.15)
        yy += 0.17 + 0.125 * len(body) + 0.12
    rep_any = {flag: sum(1 for r in rows if r["flagged"] == flag and any(r[f"concern_{k}"] == "stated limit" for k in rep_keys))
               for flag in (True, False)}
    checks.append({"check": "ratings with >=1 filled representation mark, flagged", "value": f"{rep_any[True]} of {n_flag}"})
    checks.append({"check": "ratings with >=1 filled representation mark, not flagged", "value": f"{rep_any[False]} of {n_unflag}"})
    other_keys = [k for k, g in zip(keys, groups) if g == "other"]
    unflag = [r for r in rows if not r["flagged"]]
    u_other = [r for r in unflag if any(r[f"concern_{k}"] == "stated limit" for k in other_keys)]
    u_below = [r for r in unflag if r["q19_score"] < r["q19_max"]]
    u_other_below = [r for r in u_other if r["q19_score"] < r["q19_max"]]
    checks.append({"check": "not-flagged ratings with >=1 filled other-concern mark",
                   "value": f"{len(u_other)} of {n_unflag}: " + "; ".join(
                       f'{r["job_id"]} ({", ".join(k for k in other_keys if r[f"concern_{k}"] == "stated limit")})'
                       for r in u_other)})
    checks.append({"check": "not-flagged ratings scored below max that carry a filled other-concern mark",
                   "value": f"{len(u_other_below)} of {len(u_below)}"})
    checks.append({"check": "Q19 score distribution, flagged", "value": score_dist["flagged"]})
    checks.append({"check": "Q19 score distribution, not flagged", "value": score_dist["not_flagged"]})
    disc = by_key["disclaimer"]["named_any_flagged"] + by_key["disclaimer"]["named_any_not_flagged"]
    caveat = ("" if not rule_text else f"Frozen rubric20 Q19 rule: “{rule_text}” ") + (
        f"The review assigns no replacement scores: the {n_flag} flagged ratings keep their original Q19 score and their "
        "recorded totals are only qualified. 'Not flagged' means not flagged by this targeted inspection, not certified "
        f"correct; {disc} of {n} assessments carry an explicit disclaimer of certification or adjudication. Concern marks "
        "are a keyword heuristic over the reviewer's wording (rules, cue lists and every matched sentence are exported "
        "to CSV), so they show what the reviewer named, not whether a concern was justified. At least one filled "
        f"representation mark appears in {rep_any[True]} of {n_flag} flagged and {rep_any[False]} of {n_unflag} unflagged "
        f"ratings, and {len(u_other_below)} of the {len(u_below)} unflagged ratings scored below {q_max} carry a filled "
        "mark in an other-concern column; because the heuristic reads the same prose the reviewer used to decide, this "
        "is a consistency check on the coding, not independent validation. Limit cues are phrase-bound, so a reason for "
        "withholding a point worded without one is drawn as an open circle.")
    fig.text(x0, fy(yy + 0.02), "\n".join(textwrap.wrap(caveat, int((W - 0.9) / 0.050))), fontsize=6.9,
             color=st.INK["secondary"], ha="left", va="top", linespacing=1.2)

    fig.suptitle(f"Which rubric20 Q19 provenance rationales need adjudication? Targeted review of the {n} "
                 "reference-rescore ratings", x=0.25 / W, ha="left", fontsize=11, fontweight="bold", y=fy(0.12), va="top")
    basis = (f"Record set: semantic_review.json (issue #{review['issue']}), {n} accepted rubric20 Q19 ratings of the "
             f"reference rescore 2026-09-12 (CBORG runtime), {n_api} of {n} with a Claude API runtime header (API arm), "
             f"{n_flag} flagged; concerns keyword-coded (heuristic)")
    rules = ([{"kind": "concern", "key": k, "label": flat(l), "group": g, "regex": rx} for k, l, g, rx in CONCERNS]
             + [{"kind": "cue", "key": "limit", "label": "limit cue", "group": "", "regex": LIMIT_CUE},
                {"kind": "cue", "key": "negation", "label": "negation/acceptance cue (overrides the limit cue)", "group": "", "regex": NEGATION_CUE},
                {"kind": "exclusion", "key": "input_sentence", "label": "sentence describes the input record (concern columns only)", "group": "", "regex": INPUT_SENTENCE},
                {"kind": "exclusion", "key": "input_continuation", "label": "also excluded when it directly follows an input sentence", "group": "", "regex": INPUT_CONTINUATION},
                {"kind": "splitter", "key": "sentence_split", "label": "sentence boundary", "group": "", "regex": SENTENCE_SPLIT},
                {"kind": "example_choice", "key": "withhold", "label": "flagged example must carry this cue", "group": "", "regex": WITHHOLD_CUE},
                {"kind": "example_choice", "key": "no_deduction", "label": "unflagged example must carry this cue", "group": "", "regex": NO_DEDUCTION_CUE}])
    st.save(fig, "fig15_q19_adjudication",
            {"main": rows, "cells": cells, "sentences": sents, "column_counts": counts, "rules": rules,
             "evidence": [{"job_id": e["job_id"], "kind": e["kind"], "concern": e["concern"], "sentence": e["sentence"],
                           "quoted_as": display(e["sentence"])} for e in ev],
             "checks": checks},
            basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
