#!/usr/bin/env python3
"""Purpose: run-to-run variation of the root-scope v6 scorer over up to three scorings of
each of the 15 records of the 2026-11-25c series (plan step 4 of
plan-score-based-replicate-selection-20261126.md). Reads scoring 1 from
data/evaluation_llm/{family}_semantic/label_aware/<instrument>/ and scorings 2 and 3
from data/evaluation_repeats/<instrument>/scoring_rep{2,3}/{family}_semantic/.
Reports per record: the scores per rubric, the combined score per scoring (mean of the
two rubric percentages, pairing scoring k of rubric10 with scoring k of rubric20),
mean and sample SD; then the pooled within-record SD s, the threshold
T = 2*s*sqrt(2/3), and the per-project and per-rubric pooled SDs. Applies nothing.
A cell with no published file (a refused output, plan UPDATE 2026-11-26T05:29Z) is
shown as "nm" (not measured), never as zero: its scoring number has no combined
score, the record is flagged ineligible for score_gap_v1, and the pooled SD uses the
degrees of freedom actually available.
Inputs: worktree root (argv[1]). Outputs: markdown on stdout, JSON to argv[2].
Date: 2026-11-26 (UTC). Lead: Claude lead."""
import json, math, pathlib, re, statistics, sys
root = pathlib.Path(sys.argv[1]); INST = "2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6"
PAT = re.compile(r"^(AI_READI|CHORUS|CM4AI|VOICE_PEDIATRIC|VOICE)_(.+)_rep(\d)_evaluation\.json$")
FAMS, KS, MAXP = ("rubric10", "rubric20"), (1, 2, 3), {"rubric10": 50, "rubric20": 88}
data = {}  # (project, genrep) -> rubric -> {scoring: points}
def load(path, fam, k):
    m = PAT.match(path.name)
    if not m: raise SystemExit(f"unexpected file {path}")
    d = json.loads(path.read_text())
    if d["instrument_id"] != INST or d["version"] != "6.0": raise SystemExit(f"instrument mismatch {path}")
    s = d["overall_score"]
    if s["max_points"] != MAXP[fam]: raise SystemExit(f"unexpected maximum {path}: {s['max_points']}")
    cell = data.setdefault((m.group(1), m.group(3)), {}).setdefault(fam, {})
    if k in cell: raise SystemExit(f"duplicate scoring {path}")
    cell[k] = s["total_points"]
for fam in FAMS:
    for p in sorted((root / "data/evaluation_llm" / f"{fam}_semantic" / "label_aware" / INST).glob("*_evaluation.json")): load(p, fam, 1)
    for k in (2, 3):
        for p in sorted((root / "data/evaluation_repeats" / INST / f"scoring_rep{k}" / f"{fam}_semantic").glob("*_evaluation.json")): load(p, fam, k)
if len(data) != 15: raise SystemExit(f"expected 15 records, found {len(data)}")
rows, missing, ss, dfree, by_proj, by_rub = [], [], 0.0, 0, {}, {f: [0.0, 0] for f in FAMS}
show = lambda pts: "/".join("nm" if x is None else str(x) for x in pts)
print("| record | gen rep | rubric10 of 50 (scorings 1/2/3) | rubric20 of 88 (scorings 1/2/3) | combined % per scoring | mean | SD | complete |\n|---|---|---|---|---|---|---|---|")
for (proj, rep), v in sorted(data.items()):
    pts = {fam: [v.get(fam, {}).get(k) for k in KS] for fam in FAMS}
    for fam in FAMS:
        if pts[fam][0] is None: raise SystemExit(f"first scoring missing {proj} rep{rep} {fam}")
        missing += [{"project": proj, "generation_rep": rep, "rubric": fam, "scoring": k} for k, x in zip(KS, pts[fam]) if x is None]
    pct = {fam: [None if x is None else 100 * x / MAXP[fam] for x in pts[fam]] for fam in FAMS}
    comb = [None if None in (a, b) else (a + b) / 2 for a, b in zip(pct["rubric10"], pct["rubric20"])]
    got = [c for c in comb if c is not None]
    mean = statistics.mean(got); sd = statistics.stdev(got) if len(got) > 1 else None
    if sd is not None:
        d = len(got) - 1; ss += sd * sd * d; dfree += d
        a = by_proj.setdefault(proj, [0.0, 0]); a[0] += sd * sd * d; a[1] += d
    for fam in FAMS:
        g = [x for x in pct[fam] if x is not None]
        if len(g) > 1: by_rub[fam][0] += statistics.variance(g) * (len(g) - 1); by_rub[fam][1] += len(g) - 1
    complete = len(got) == 3
    rows.append({"project": proj, "generation_rep": rep, "rubric10": pts["rubric10"], "rubric20": pts["rubric20"],
                 "combined": comb, "scorings_combined": len(got), "mean": mean, "sd": sd, "complete": complete,
                 "rubric10_mean_pct": statistics.mean(x for x in pct["rubric10"] if x is not None),
                 "rubric20_mean_pct": statistics.mean(x for x in pct["rubric20"] if x is not None)})
    print(f"| {proj} | {rep} | {show(pts['rubric10'])} | {show(pts['rubric20'])} | "
          f"{' / '.join('nm' if c is None else f'{c:.1f}' for c in comb)} | {mean:.1f} | {'nm' if sd is None else f'{sd:.2f}'} | {'yes' if complete else 'no'} |")
s = math.sqrt(ss / dfree); T = 2 * s * math.sqrt(2 / 3)
print(f"\nrecords {len(rows)}; complete (3 scorings on both rubrics) {sum(r['complete'] for r in rows)}; cells not measured {len(missing)}")
for m in missing: print(f"- not measured: {m['project']} generation rep{m['generation_rep']} {m['rubric']} scoring {m['scoring']}")
print(f"pooled within-record SD s = {s:.2f} points ({dfree} df); threshold T = 2*s*sqrt(2/3) = {T:.2f} points (defined for records with 3 scorings)")
print("pooled SD by project: " + "; ".join(f"{p} {math.sqrt(a/b):.2f} ({b} df)" for p, (a, b) in sorted(by_proj.items())))
print("pooled SD by rubric (percentage points): " + "; ".join(f"{f} {math.sqrt(a/b):.2f} ({b} df)" for f, (a, b) in by_rub.items()))
pathlib.Path(sys.argv[2]).write_text(json.dumps({"instrument": INST, "rows": rows, "not_measured": missing, "pooled_sd": s, "df": dfree,
    "threshold": T, "by_project": {p: {"sd": math.sqrt(a / b), "df": b} for p, (a, b) in by_proj.items()},
    "by_rubric": {f: {"sd": math.sqrt(a / b), "df": b} for f, (a, b) in by_rub.items()}}, indent=1))
