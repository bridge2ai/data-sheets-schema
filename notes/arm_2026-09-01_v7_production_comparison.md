# v7 API production arm (2026-09-01): completion and 12-vs-12 comparison

Status of this note: receipts and rubric sections final; the review
section carries 1 of 12 reviews (the other 11 agents are suspended at a
session-usage reset and resume tonight) and is finalized when they land.
The registered matrix (#838/#849) completed 12/12 with zero failed runs:
four production canaries (CM4AI retained under #877's off-by-one
interpretation; VOICE and CHORUS passed outright; AI_READI retained under
the #891 exposure-adjusted revision after four attempts whose failures
were bookkeeping-class only) and eight fill records in one resumed sweep.

## Receipts, matched 12-vs-12 (the like-for-like grounding measurement)

| | v6 agentic (12) | v7 API production (12) |
|---|---|---|
| snippets verified | 3,400/3,400 (100%) | 1,596/1,733 (92.1%) |
| mismatched | 0 | **1** |
| unattesting (below floors) | 0 | 4 |
| adjacent / elsewhere | 0 / 0 | 112 (6.5%) / 20 |
| off-by-one + addressing slips | 0 | 3 |
| leaf coverage | 2,820/5,846 (48.2%) | 1,391/3,917 (35.5%) |
| populated leaves | 6,248 | 4,474 |

Reading: the agentic arm attests more (higher coverage, more populated
leaves) and attributes perfectly; the API arm's support holds almost
everywhere (1 real misquote in ~1,700 snippets) but its attribution is
noisier (6.5% wrong-chunk, echoing #873's marker arithmetic) and its
receipts cover a third of the record rather than half. Both arms are
essentially fabrication-free at the snippet level.

## Rubrics (label-aware semantic, same evaluator family)

| AI_READI | rep1 | 49/50 (98.0%) | 82/88 (93.2%) |
| AI_READI | rep2 | 50/50 (100.0%) | 81/88 (92.0%) |
| AI_READI | rep3 | 50/50 (100.0%) | 80/88 (90.9%) |
| CHORUS | rep1 | 31/49 (63.3%) | 65/88 (73.9%) |
| CHORUS | rep2 | 29/49 (59.2%) | 59/88 (67.0%) |
| CHORUS | rep3 | 29/49 (59.2%) | 63/88 (71.6%) |
| CM4AI | rep1 | 41/45 (91.1%) | 72/88 (81.8%) |
| CM4AI | rep2 | 43/45 (95.6%) | 77/88 (87.5%) |
| CM4AI | rep3 | 42/45 (93.3%) | 76/88 (86.4%) |
| VOICE | rep1 | 49/50 (98.0%) | 77/88 (87.5%) |
| VOICE | rep2 | 49/50 (98.0%) | 79/88 (89.8%) |
| VOICE | rep3 | 47/50 (94.0%) | 79/88 (89.8%) |

Project means, rubric20, v7 production vs v6 agentic: AI_READI 92.0 vs
89.8 (+2.2) · CHORUS 70.8 vs 67.2 (+3.6) · CM4AI 85.2 vs 85.8 (−0.6) ·
VOICE 89.0 vs 90.1 (−1.1). The receipt condition on the API arm did not
cost rubric quality; per the cross-read (#815) these numbers measure the
projects and the records' coverage, not grounding — the review pass is
the grounding instrument.

## Canonical selection (dry run; executed after the review pass)

AI_READI rep2 (81 slots), CHORUS rep1 (53), CM4AI rep2 (73), VOICE rep2
(82) — thin margins throughout, per the criterion's own caveat.

## Review pass (1 of 12; in progress)

CHORUS rep1: 70/70 answered · 11 adverse · 0 cannot_tell — rule-15
(111/179 receiptless incl. phase-1 values), four weak receipts (incl. the
CTP-deid bare-repo-name exemplar), four inferred values, rule-01/06.
Remaining 11 reviews resume after the session-usage reset; the adverse
table, the v6-vs-v7 adverse comparison, and the cross-read update follow.

## Rubric-flagged items for the review pass

- AI_READI (all reps): WUSTL-vs-UW PI/licensor affiliation conflict
  (declared in caveats; tier-1 source followed).
- AI_READI rep3: source_caveats byte-sum self-inconsistency (claims a sum
  4.6MB over the total; the recorded values sum 0.4MB under — 5,017,200
  apart).
- VOICE rep3: `at_risk_groups_included: false` despite dementia and
  psychiatric cohorts.
- VOICE rep1: DPIA absent entirely where siblings carry an honest "not
  conducted".
