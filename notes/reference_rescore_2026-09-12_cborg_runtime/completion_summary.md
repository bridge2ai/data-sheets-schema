# CBORG reference rescore completion — 2026-09-12

**Semantic inspection — Q19:** 9 of 24 original Q19 rationales require adjudication because they add representation or field-placement requirements despite the frozen text-or-graph rule. Their containing recorded totals are qualified. No original score, candidate or rationale is edited and no replacement score is assigned. Unflagged cases are not certified correct; other substantive completeness concerns remain unadjudicated. Do not use small differences in these qualified totals to select generation runs. See the [24-rating inspection](semantic_review.md).

**Execution boundary:** Five accepted ratings precede the validator-status permission extension and 51 follow it. Scoring prompts, definitions and inputs are unchanged, but execution permissions differ. Cohort comparisons and repeat panels spanning this boundary do not isolate permission effects; small differences cannot be attributed solely to generation version or evaluator variability. Repeat panels spanning it: AI_READI, CHORUS. See [the dated registration](validator_status_registration.json).

**Execution deadline:** Seventeen accepted ratings precede the execution deadline increase from 900 to 1800 seconds; 39 follow it. Scoring prompts, definitions, inputs and the $5 CLI cap are unchanged. This execution boundary can affect completion/selection, so cohort and repeat comparisons do not isolate generation-version or evaluator effects. See [the deadline registration](deadline_registration_1351.json).

**Incomplete cost accounting:** 2 retained interrupted evaluator sessions have unknown cost. The known terminal CLI subtotal excludes their unreported usage; total expenditure is unknown. CLI estimates are not reconciled CBORG charges. Measurement/session completion does not imply complete cost accounting.

**Evaluation prose:** Evaluation narratives describe model judgments about the supplied documentation and are not verified facts about the underlying datasets. The CHORUS retry canary overstates missing license information as absence of a governing license and alleges conflation despite an explicit software/data distinction in the input. Keep its original score and prose, and do not repeat those statements as dataset facts. Other narrative claims remain unadjudicated. See [the original statements and interpretation](canary_narrative_qualification.json).

**CM4AI pilot judgments:** The CM4AI retry pilot overlooks the explicit per-deposit scope of release version numbers when reducing Q13 and qualifying Q19. Its containing total and related version-consistency findings require semantic adjudication. Additional narrative claims overstate the impossibility of participant-related documentation for cell-line work, credit donor age for both lines where the cited text supplies only one, and undercount creator entries. Keep all original scores and prose; do not repeat these statements as verified dataset facts or use small differences in the qualified total to select a generation run. No replacement scores are assigned. See [the original statements and input evidence](cm4ai_pilot_narrative_qualification_1355.json).

**Evaluation timing:** Execution times and condition boundaries use launcher receipt started_at/completed_at, with original receipt hashes recorded in results.json. Model-written evaluation_timestamp values remain unchanged and are not independently verified, including values inside the recorded interval. Of 56 accepted ratings, 23 metadata timestamps lie outside their session intervals and 0 cannot be compared as timezone-aware timestamps. An interval mismatch alone does not establish fabrication; approximations and timezone errors can also cause it.

**Measured code archive:** The public report command was repaired after all measurements completed. Verification uses the exact archived adapter and scheduler bytes recorded by the unchanged manifest and registration, not the updated reporting commands. See [the preservation record](report_dispatch_preservation_1356.json).

Completed **56 accepted ratings** of the 24 existing v7/v8 D4Ds: 48 primary ratings across both semantic rubrics and eight additional rubric10 ratings. All original scores remain unchanged; this provider condition is separate from the earlier reference run.

The [completion audit](completion_audit.json) accounts for 63 evaluator CLI sessions, including 7 retained excluded attempts in this completed condition. The separate preliminary condition used 4 sessions and $10.26736050, retaining one accepted canary and three excluded attempts; none is pooled into these 56 ratings. All 259 prior evaluations retain their hashes, all 56 accepted outputs match their original successful Writes, and peak completed-session concurrency was 4. The known terminal CLI subtotal is **$161.39939450**; it excludes the two unpriced interrupted sessions and is not a complete expenditure total. A session may contain multiple model/tool turns; this is not a count of HTTP requests or a reconciled invoice. Review-tool usage is outside this figure.

The audit separately retains 1 verified local pre-launch failure(s). These stopped at the registered CLI version guard before evaluator exec, produced no model-session cost record and are not counted as evaluator sessions.

The runtime trace identifies `claude-opus-5`, requested through CBORG as `claude-opus-5[1m]` at high effort with temperature unspecified. Definitions, inputs, complete prompts and schemas are pinned by the [manifest](manifest.json). Every accepted rating passed identity, check-echo, arithmetic, schema and original-output checks. All rubric10 headings match the source rubric.

Rubric10 definition: `66ad623121272099bf94535ae5be2163a5f5005fe895d2bf2bf04c4f90e34864`. Rubric20 definition: `9d08b5f3d7a3e9828a6c6cbd59a0eacf302979399067ff5aa70480d95a0e7dd3`.

## Repeated ratings

Three independent rubric10 ratings cover one v7 record per project. These descriptive ranges and sample standard deviations do not estimate population uncertainty. Rubric20 repeatability is unmeasured. Generation-replicate spread is reported separately in [results.md](results.md); small score differences do not establish a preferred generation run.

| Project | Fixed percentages | Adjusted percentages | Fixed SD | Adjusted SD | Adjusted range | Stable applicability |
|---|---|---|---|---|---|---|
| AI_READI | [98.0, 98.0, 98.0] | [98.0, 98.0, 98.0] | 0.0000 | 0.0000 | 0.0000 | True |
| CHORUS | [68.0, 70.0, 68.0] | [68.0, 70.0, 68.0] | 1.1547 | 1.1547 | 2.0000 | True |
| CM4AI | [86.0, 86.0, 86.0] | [91.48936170212765, 91.48936170212765, 91.48936170212765] | 0.0000 | 0.0000 | 0.0000 | True |
| VOICE | [98.0, 98.0, 96.0] | [98.0, 98.0, 96.0] | 1.1547 | 1.1547 | 2.0000 | True |

## Primary recorded totals

Q19 inspection flags qualify the affected rubric20 totals; no scores were edited or adjudicated by this report.

| Record | Rubric10 | Rubric20 |
|---|---|---|
| AI_READI v7 rep1 | 49/50 | 82/88 |
| AI_READI v7 rep2 | 49/50 | 83/88 |
| AI_READI v7 rep3 | 49/50 | 85/88 |
| AI_READI v8 rep1 | 49/50 | 82/88 [Q19 inspection](semantic_review.md) |
| AI_READI v8 rep2 | 49/50 | 82/88 |
| AI_READI v8 rep3 | 49/50 | 83/88 [Q19 inspection](semantic_review.md) |
| CHORUS v7 rep1 | 34/50 | 66/88 [Q19 inspection](semantic_review.md) |
| CHORUS v7 rep2 | 30/50 | 64/88 |
| CHORUS v7 rep3 | 33/50 | 67/88 |
| CHORUS v8 rep1 | 34/50 | 67/88 [Q19 inspection](semantic_review.md) |
| CHORUS v8 rep2 | 36/50 | 68/88 [Q19 inspection](semantic_review.md) |
| CHORUS v8 rep3 | 33/50 | 65/88 |
| CM4AI v7 rep1 | 43/50 | 75/88 |
| CM4AI v7 rep2 | 43/50 | 64/88 [Q19 inspection](semantic_review.md) |
| CM4AI v7 rep3 | 42/50 | 79/88 |
| CM4AI v8 rep1 | 39/50 | 70/88 [Q19 inspection](semantic_review.md) |
| CM4AI v8 rep2 | 41/50 | 64/88 [Q19 inspection](semantic_review.md) |
| CM4AI v8 rep3 | 40/50 | 69/88 [Q19 inspection](semantic_review.md) |
| VOICE v7 rep1 | 49/50 | 81/88 |
| VOICE v7 rep2 | 49/50 | 80/88 |
| VOICE v7 rep3 | 48/50 | 82/88 |
| VOICE v8 rep1 | 49/50 | 78/88 |
| VOICE v8 rep2 | 48/50 | 77/88 |
| VOICE v8 rep3 | 48/50 | 80/88 |

## Separate v9 generation canary

Exactly one CHORUS v9 full/core pair was generated from the existing source bundle and passed the registered gates. It made 6 native API requests, with a catalogue-rate usage estimate of $3.30811950. The [generation review](../cborg_canaries_2026-09-12/v9_canary_review.md) retains the source checks and limits. This is one canary, not a completed v9 manuscript cohort; no downloads or additional v9 generation occurred.
