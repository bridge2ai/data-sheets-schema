#!/usr/bin/env python3
"""Score table for choosing one replicate per project (series 2026-11-22b).

Purpose: put the two semantic rubric scores of every replicate beside the numbers the
  selection rule and the receipts give, so the owner can choose one replicate per project.
Inputs:  the 30 evaluation JSON files under
  data/evaluation_llm/rubric{10,20}_semantic/2026-11-22_general_context_v3/, the driver's
  .temp/eval/results.tsv (validator exit per evaluation), and
  notes/final_agentic_2026-11-22/series_2026-11-22b_summary.tsv (receipt coverage).
Outputs: notes/final_agentic_2026-11-22/rubric_scores.tsv and the same table on stdout.
  Scores are read from each file's own overall_score block; nothing is recomputed.
Serves:  selection of the final D4Ds (owner decision 2026-11-22). Date: 2026-11-22.
"""
import csv
import json
import sys
from pathlib import Path

W = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/fast-d4d-20261121")
NOTES = W / "notes/final_agentic_2026-11-22"
PROJECTS = ["AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC"]
# Top-level populated slots as `d4d runs select` counted them in its dry run of 2026-11-22.
SLOTS = {"AI_READI": (64, 65, 62), "CHORUS": (23, 28, 24), "CM4AI": (41, 37, 35),
         "VOICE": (61, 59, 63), "VOICE_PEDIATRIC": (35, 44, 41)}

valid = {}
for row in csv.reader((W / ".temp/eval/results.tsv").open(), delimiter="\t"):
    # columns: project, rep, rubric, total, max, adjusted_max, models, advisor_calls,
    # other_evaluation_touches, session_exit=N, validator_exit=N, start, end
    if len(row) >= 11:
        valid[(row[0], row[1], row[2])] = (row[10] == "validator_exit=0" and row[9] == "session_exit=0",
                                           row[6], row[7])
receipts = {}
for row in csv.DictReader((NOTES / "series_2026-11-22b_summary.tsv").open(), delimiter="\t"):
    receipts[(row["project"], int(row["rep"]))] = row["slots_with_receipt"]


def score(rubric, project, rep):
    path = W / f"data/evaluation_llm/rubric{rubric}_semantic/2026-11-22_general_context_v3/{project}_2026-11-22b_rep{rep}_evaluation.json"
    if not path.is_file():
        return None
    block = json.loads(path.read_text()).get("overall_score") or {}
    return block.get("total_points"), block.get("max_points"), block.get("adjusted_max_points"), \
        block.get("normalized_percentage")


rows, problems = [], 0
for project in PROJECTS:
    for rep in (1, 2, 3):
        r10, r20 = score(10, project, rep), score(20, project, rep)
        ok10 = valid.get((project, f"rep{rep}", "r10"), (False,))[0]
        ok20 = valid.get((project, f"rep{rep}", "r20"), (False,))[0]
        if not (r10 and r20 and ok10 and ok20):
            problems += 1
        fmt = lambda s: "missing" if not s else f"{s[0]}/{s[2] if s[2] is not None else s[1]}"
        pct = lambda s: "" if not s or s[3] is None else f"{s[3]:.1f}"
        both = "" if not (r10 and r20) or r10[3] is None or r20[3] is None else f"{(r10[3] + r20[3]) / 2:.1f}"
        rows.append([project, rep, fmt(r20), pct(r20), fmt(r10), pct(r10), both,
                     SLOTS[project][rep - 1], receipts.get((project, rep), "?"),
                     "yes" if ok10 and ok20 else "NO"])

header = ["project", "rep", "rubric20", "rubric20_pct", "rubric10", "rubric10_pct", "mean_pct",
          "top_level_slots", "values_with_receipt", "both_outputs_validate"]
(NOTES / "rubric_scores.tsv").write_text("\n".join("\t".join(str(c) for c in r) for r in [header] + rows) + "\n")
for r in [header] + rows:
    print("\t".join(str(c) for c in r))
print(f"\n{len(rows) - problems} of {len(rows)} replicates have both evaluations valid")
sys.exit(1 if problems else 0)
