# Cross-read: rubric scores vs review adverse rates (2026-08-30)

The 2026-08-28 rounds were measured twice: label-aware rubric10/20-semantic
evaluations (`data/evaluation_llm/rubric{10,20}_semantic/label_aware/`,
interpreted in `notes/arm_2026-08-28_interpretation.md`) and the
`d4d-review-record` pass (`notes/review_pass_2026-08-30.md`). This note joins
them per record — all 17 records (12 agentic v6, 5 API v7 canaries) have both.

**Question.** Do the two instruments agree per record, and is the claim that
"rubrics reward coverage while reviews penalise unsupported content" true in
the numbers?

## The table

`r10`/`r20` are the rubric normalized percentages. `leaves` is
`populated_leaves` of the full record. `slot adverse` counts non-affirmative
verdicts on the 50 sampled receipted + receiptless slots (weak + misread +
unsupported + inferred + not_in_bundle); `rate` divides by those 50 — the
`slot_reshaped` items some v7 packs also carry (including CHORUS 28b's two
`cannot_tell`) are excluded from both numerator and denominator. This is a
narrower count than the `adverse` column of the review-pass note, which adds
rule and chunk items; per record, slot adverse + rules violated (+1
`missed_content` chunk for 28d) equals that note's `adverse` exactly.
`rules violated` is out of 15 (v6) or 16 (v7), of which 1–2 are
`not_applicable` for some CHORUS records.

| arm | project | rep | r10 | r20 | leaves | slot adverse | rate | rules violated |
|---|---|---|---|---|---|---|---|---|
| v6 | AI_READI | rep1 ✓ | 100.0 | 89.8 | 667 | 2 | 4% | 2 |
| v6 | AI_READI | rep2 | 96.0 | 88.6 | 558 | 1 | 2% | 3 |
| v6 | AI_READI | rep3 | 98.0 | 90.9 | 585 | 9 | 18% | 4 |
| v6 | CHORUS | rep1 | 61.2 | 67.0 | 197 | 9 | 18% | 3 |
| v6 | CHORUS | rep2 | 53.1 | 65.9 | 281 | 3 | 6% | 6 |
| v6 | CHORUS | rep3 ✓ | 61.2 | 68.7 | 205 | 6 | 12% | 3 |
| v6 | CM4AI | rep1 | 86.7 | 83.0 | 765 | 4 | 8% | 0 |
| v6 | CM4AI | rep2 | 88.9 | 87.2 | 493 | 4 | 8% | 5 |
| v6 | CM4AI | rep3 ✓ | 93.3 | 87.2 | 860 | 4 | 8% | 0 |
| v6 | VOICE | rep1 | 98.0 | 90.9 | 617 | 6 | 12% | 3 |
| v6 | VOICE | rep2 | 94.0 | 88.6 | 460 | 5 | 10% | 5 |
| v6 | VOICE | rep3 ✓ | 98.0 | 90.9 | 560 | 2 | 4% | 3 |
| v7 | AI_READI | 28b | 98.0 | 89.8 | 446 | 2 | 4% | 8 |
| v7 | AI_READI | 28c | 98.0 | 90.9 | 434 | 7 | 14% | 7 |
| v7 | AI_READI | 28d | 98.0 | 95.5 | 685 | 4 | 8% | 9 |
| v7 | CHORUS | 28 | 65.3 | 70.5 | 209 | 15 | 30% | 5 |
| v7 | CHORUS | 28b | 63.3 | 68.2 | 195 | 7 | 14% | 6 |

(✓ = the v6 canonical selection.)

## What correlates with what

Spearman rank correlations (all 17; v6-only in parentheses):

| pair | ρ |
|---|---|
| r10 vs r20 | **+0.93** (+0.95) |
| r10 vs populated leaves | **+0.59** (+0.57) |
| r20 vs populated leaves | **+0.58** (+0.50) |
| r10 vs slot adverse rate | −0.32 (−0.23) |
| r20 vs slot adverse rate | −0.20 (−0.09) |
| r20 vs rules violated | +0.16 (−0.08) |
| slot adverse rate vs leaves | −0.43 (−0.27) |

And within project, where the confound of bundle richness is held fixed —
ρ(r20, slot adverse rate):

| project | all records | v6 only |
|---|---|---|
| AI_READI | **+0.81** (n=6) | +1.00 (n=3) |
| CHORUS | +0.60 (n=5) | +0.50 (n=3) |
| CM4AI | undefined — all three rates are 8% | — |
| VOICE | 0.00 (n=3) | 0.00 (n=3) |

Three readings:

1. **The rubrics measure the project, not the record.** Both rubrics
   correlate strongly with each other and with leaf coverage, and their
   variance is almost entirely between projects: every CHORUS record scores
   53–71 and every AI_READI/VOICE record 88–100, whichever arm and whatever
   its review found. Within the v6 replicates of a project the r20 spread is
   ≤4.2 points (across arms AI_READI spans 6.9, but the v7 canaries are not
   replicates of the v6 runs) while the adverse rate spans 2%→18% within
   AI_READI v6 alone.
2. **The pooled rubric-vs-adverse correlation is an artifact of project
   structure, and within project the relation leans the *other way*.** The
   pooled −0.20/−0.32 (95% CI on −0.32 at n=17 is roughly [−0.69, +0.19] —
   compatible with anything from moderate-negative to null) exists because
   CHORUS is both the poorest-documented and the most adverse-prone project.
   Hold the project fixed and the sign flips or vanishes: +0.81 across the
   six AI_READI records, +0.60 across the five CHORUS, 0 for VOICE, flat for
   CM4AI. The flagship pair is the same fact seen record-by-record:
   **AI_READI v6 rep3** has the highest r20 of its triplet (90.9) and the
   worst adverse rate (18%: five inferred, one not in the bundle, three
   weak); **AI_READI v7 28d** has the highest r20 of all seventeen (95.5)
   beside 9 of 16 rules violated, an ungrounded ROR attachment, and the
   pass's only `missed_content` chunk. The mechanism is visible in the
   verdicts: an inferred `data_type` or a plan-as-done sentence *fills a
   rubric sub-element* — unsupported content is coverage to a
   coverage-shaped score. At n=3–6 per project none of this is conclusive;
   the direction is consistent, the magnitudes are not trustworthy.
3. **Rule violations are invisible to the rubrics** (pooled ρ ≈ 0, sign
   unstable across subsets). The v7 canaries average 7.0 violations against
   v6's 3.1 — plan-as-done, Person-ranged strings, absence statements — with
   rubric scores indistinguishable from v6's on the same projects.

So the claim as originally asserted was half right. The rubrics do reward
what the bundle makes possible. But the reviews are not merely orthogonal:
within a project, the records that scored *best* on the rubrics tended to
carry *more* unsupported content, because inference inflates both at once.
The two instruments do not disagree about quality — they answer different
questions, and only the review's question is about grounding.

![r20 vs review adverse rate](figures/cross_read_r20_vs_adverse.png)

(Coincident points — CM4AI r2/r3, AI_READI v6 rep1 / v7 28b — are dodged
+0.45 on the x-axis; ringed markers are the v6 canonical selections.)

## Caveats

- n=17, and only 5 on the v7 side — three of them AI_READI canaries under
  successive instrument fixes, two CHORUS. Arm-level conclusions wait for
  the full v7 fan-out; the within-project findings rest on n=3–6 cells.
- The adverse rate sits on a 50-slot sample per record. Binomial standard
  error is ±2–3 percentage points at the low observed rates (2–8%) and
  ±5–6.5pp toward 18–30%; 4% vs 8% does not separate, 2–4% vs 18% does
  (~2.3σ).
- One reviewer per record, no inter-rater figure; the rubric evaluations are
  single runs of the rubric agents. Both instruments are Claude judging
  Claude.
- The canonical-selection metric is **not** the `leaves` column: selection
  counts core-record slots (AI_READI 82/79/80, CHORUS 47/43/50), and for
  CHORUS the two rank the replicates almost inversely (slots rep3>rep1>rep2;
  leaves rep2>rep3>rep1). What is true — by construction, not by this data —
  is that the criterion (validates → core slots → label) has no view of the
  adverse rate. Under the review-pass note's total-adverse count every
  selected replicate is at or tied for fewest; under this note's slot-adverse
  metric the selection picked the worse-sampled replicate twice (AI_READI
  rep1 at 2 vs rep2 at 1; CHORUS rep3 at 6 vs rep2 at 3), both differences
  inside sampling noise. That is #660's concrete form: nothing enforced even
  the ties.

## What this implies for the instruments (feeds the issue list)

- The rubric agents evaluate documentation quality given the bundle; they do
  not check grounding, and within-project their scores lean *toward*
  inference-heavy records. They should not be read as a correctness signal.
- The review's slot-level adverse rate is the only per-record correctness
  number the pipeline has. If it is to gate or rank anything (e.g. join the
  canonical criterion per #660), it first needs the sampling noise stated
  (±2–6pp depending on rate) and ideally a second reviewer on
  disagreement-prone records.
- The deterministic receipt validator sits between the two: it verifies
  attribution, not support. The three receipt-shaped gaps it could close
  (#804 one-leaf entry receipts, #806 irrelevant-verbatim flags, #807 v7
  never-receipted split) would each move part of the review's judgement into
  the checkable column.
