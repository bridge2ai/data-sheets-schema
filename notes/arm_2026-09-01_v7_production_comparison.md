# v7 API production arm (2026-09-01): completion and 12-vs-12 comparison

Status of this note: final — receipts, rubrics, the complete 12/12
review pass, and the executed canonical selection.
The registered matrix (#838/#849) completed 12/12 with zero failed runs:
four production canaries (CM4AI retained under #877's off-by-one
interpretation; VOICE and CHORUS passed outright; AI_READI retained on
its fourth attempt under the #891 exposure-adjusted revision — attempt
4's remaining gate failures were instrument/bookkeeping-class per the
canary basis, while attempts 1–3, archived under `data/ATTIC/
canary_retries/`, included failures their own READMEs call genuine)
and eight fill records in one resumed sweep. "12/12 zero failed runs"
counts the production matrix as registered: retried canary attempts are
archived, not counted.

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

| project | rep | rubric10 | rubric20 |
|---|---|---|---|
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

## Canonical selection (executed 2026-09-03)

AI_READI rep2 (81 slots), CHORUS rep1 (53, tie with rep3 broken by
label — arbitrary on this criterion), CM4AI rep2 (73), VOICE rep2 (82) —
thin margins throughout, per the criterion's own caveat. Executing the
v7 selection demoted the four v6 canonical marks to `canonical_history`
(the tool keeps one live mark per project; every demotion records what
replaced it and nothing moved or was deleted). Per #660 the criterion
has no view of the review's adverse counts — and this arm shows the two
rankings **anti-agreeing in three of four projects**: the slot criterion
picked the most-adverse replicate for AI_READI (rep2 at 12 vs 9/9) and
VOICE (rep2 at 7, over rep1 at 2 — the record this note calls the
cleanest of either arm), and the tied-most for CHORUS (rep1 at 11 vs
rep3's 9); only CM4AI's pick sits mid-ranking (rep2 at 11 between 9 and
15). Under the v6 selection the picks were at or tied for fewest
adverse; here the coverage criterion actively opposes the grounding
instrument. That is #660's concrete form at its sharpest so far, and an
argument for joining the adverse count into the criterion.

## Review pass (12 of 12, complete)

One `d4d-review-record` agent per record, all checks passed `--strict`,
review blocks written into every provenance record. `slot adv` counts
non-affirmative verdicts on the 50 sampled receipted+receiptless slots
(same construction as the cross-read note); `rules` is violated/16.

| record | items | slot adv | rules | total adverse | cannot_tell |
|---|---|---|---|---|---|
| AI_READI rep1 | 78/78 | 6/50 (12%) | 3 | 9 | 0 |
| AI_READI rep2 | 74/74 | 8/50 (16%) | 4 | 12 | 2 |
| AI_READI rep3 | 77/77 | 3/50 (6%) | 6 | 9 | 3 |
| CHORUS rep1 ✓ | 70/70 | 8/50 (16%) | 3 | 11 | 0 |
| CHORUS rep2 | 80/80 | 7/50 (14%) | 4 | 11 | 0 |
| CHORUS rep3 | 76/76 | 5/50 (10%) | 4 | 9 | 0 |
| CM4AI rep1 | 83/83 | 6/50 (12%) | 3 | 9 | 0 |
| CM4AI rep2 ✓ | 78/78 | 7/50 (14%) | 3 | 11 | 0 |
| CM4AI rep3 | 82/82 | 8/50 (16%) | 7 | 15 | 0 |
| VOICE rep1 | 71/71 | 0/50 (0%) | 2 | 2 | 0 |
| VOICE rep2 ✓ | 74/74 | 4/50 (8%) | 3 | 7 | 0 |
| VOICE rep3 | 71/71 | 3/50 (6%) | 2 | 5 | 1 |

(✓ = the executed v7 canonical selection; AI_READI rep2 is also ✓.)

**v6-vs-v7 adverse comparison.** v7 production: slot adverse 65/600
(10.8%), rules violated 44/192 (mean 3.7/16). v6 agentic (cross-read
note): 55/600 (9.2%), 37 violations (mean 3.1/15). The +1.6pp slot
difference is inside the sampling noise the cross-read states (±2–3pp at
these rates); the rule means are close. The headline is what production
did to the exploratory v7 canaries' rule discipline: the Aug-28 cohort
averaged **7.0** violations against production's **3.7** — the plan-as-
done, Person-ranged-string and absence-statement failures that marked
the canaries mostly did not recur, consistent with those records being
generated under successive instrument fixes rather than the frozen
configuration. VOICE rep1 at 0/50 slot adverse and 2 violations is the
cleanest record of either arm.

**Recurring findings with structure (issue candidates):**

1. **Stale receipt paths after reconciliation** — confirmed independently
   by five reviewers (AI_READI rep1 variables[22–26] off by one;
   AI_READI rep3 slot-029 unsupported purely from the v1.0.0 insertion;
   CM4AI rep1 external_resources[8]→[7]; CM4AI rep2 slots 013/028 after
   the MassIVE split; CM4AI rep3 creators[38] after nine insertions).
   Receipts describe the `full`-phase record (#742) while the pack
   samples the reconciled one, so list insertions/reorders shift receipts
   onto wrong entries and manufacture `unsupported` verdicts for
   bundle-attested values. Proposed fix (rv2-AI_READI-r3): key the
   claims join to entry identity rather than list index.
2. **rule-15 coverage degree, violated in 8 of 12 records** (followed
   for AI_READI rep2/rep3 and VOICE rep2/rep3, whose reviewers credited
   the receipts as compliant) — every receipt is well-formed with all
   chunks reviewed, but per the provenance receipts blocks coverage runs
   48–208 of 142–508 receiptable slots per record; sampled receiptless
   values are overwhelmingly bundle-supplied (large creator rosters
   especially). Zero `not_in_bundle` verdicts anywhere in the arm: the
   gap is coverage degree, not fabrication.
3. **Reconcile over-flattening class-ranged slots** — CM4AI rep2's §2.4
   flattened valid Person objects citing the v4 scalar rule (emails and
   ORCIDs present in bundle, discarded); all three CM4AI reps leave
   `Grant.grant_number` empty with award numbers in notes because the
   reconcile schema digest carries no key list for Grant.
4. **Unforced identifier mints** — CM4AI rep3's twelve `#creator-*`/
   `#grant-*` fragments naming real persons and NIH awards that nothing
   references (rule-11/14); pack `id_slots` also classifies constructed
   `file_collections[*].id` fragments as minted:false (AI_READI rep1).
5. **Scope leak survivals** — VOICE rep2 carries one pediatric-methods
   clause in an adult-referent slot (the #441 class; reconciliation
   caught three others); CM4AI rep3 reads Oct-2025 archive channel
   details as current June-2026 instances while withdrawing the protein
   count on exactly that ground.

**Rubric flags adjudicated by the reviews:** the AI_READI rep3 byte-sum
flag is confirmed and worse than self-inconsistency — the claimed sum is
wrong in value and direction (states +4,597,586 over; attested values
sum 419,614 under) while the copied inputs are correct, a miscomputation
presented as sourced fact. AI_READI rep3 also has the arm's only
report/record contradiction (`extension_mechanism` claimed retained,
absent from both records) and `is_sample: true` receipted by the very
passage denying it.

## Rubric-flagged items (as handed to the review pass; adjudications above)

- AI_READI (all reps): WUSTL-vs-UW PI/licensor affiliation conflict
  (declared in caveats; tier-1 source followed).
- AI_READI rep3: source_caveats byte-sum self-inconsistency (claims a sum
  4.6MB over the total; the recorded values sum 0.4MB under — 5,017,200
  apart).
- VOICE rep3: `at_risk_groups_included: false` despite dementia and
  psychiatric cohorts.
- VOICE rep1: DPIA absent entirely where siblings carry an honest "not
  conducted".
