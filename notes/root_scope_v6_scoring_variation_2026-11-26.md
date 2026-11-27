# Run-to-run variation of the root-scope v6 scorer (2026-11-26)

Each of the 15 records of the series `2026-11-25c_claude-fable-5-2-claudecode-generic-v9`
(5 projects × 3 generation replicates) was scored three times per rubric on the
instrument `2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6`: 90 scorings. This note reports how much the score of one record
moves between scorings, which is the noise term of the `score_gap_v1` selection rule
(issue 6385). It applies nothing and changes no canonical mark.

Reproduce with:

```bash
python3 scripts/adhoc/root_scope_scoring_variation_20261126.py . /tmp/variation.json
```

The per-cell provenance (attempt, points, sha256, path) is
`data/evaluation_repeats/2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6/scorings.tsv`.

## Result

"Combined %" is the mean of the rubric10 percentage (of 50) and the rubric20
percentage (of 88) for one scoring number.

| record | gen rep | rubric10 of 50 (scorings 1/2/3) | rubric20 of 88 (scorings 1/2/3) | combined % per scoring | mean | SD | complete |
|---|---|---|---|---|---|---|---|
| AI_READI | 1 | 45/45/45 | 70/70/70 | 84.8 / 84.8 / 84.8 | 84.8 | 0.00 | yes |
| AI_READI | 2 | 45/45/43 | 68/68/68 | 83.6 / 83.6 / 81.6 | 83.0 | 1.15 | yes |
| AI_READI | 3 | 42/42/42 | 68/66/68 | 80.6 / 79.5 / 80.6 | 80.3 | 0.66 | yes |
| CHORUS | 1 | 28/26/27 | 51/48/51 | 57.0 / 53.3 / 56.0 | 55.4 | 1.92 | yes |
| CHORUS | 2 | 26/27/25 | 55/55/53 | 57.2 / 58.2 / 55.1 | 56.9 | 1.60 | yes |
| CHORUS | 3 | 21/21/21 | 50/50/52 | 49.4 / 49.4 / 50.5 | 49.8 | 0.66 | yes |
| CM4AI | 1 | 32/31/32 | 64/62/62 | 68.4 / 66.2 / 67.2 | 67.3 | 1.07 | yes |
| CM4AI | 2 | 32/30/32 | 61/61/61 | 66.7 / 64.7 / 66.7 | 66.0 | 1.15 | yes |
| CM4AI | 3 | 27/28/27 | 64/59/64 | 63.4 / 61.5 / 63.4 | 62.8 | 1.06 | yes |
| VOICE | 1 | 42/43/43 | 66/68/66 | 79.5 / 81.6 / 80.5 | 80.5 | 1.07 | yes |
| VOICE | 2 | 45/46/47 | 72/72/70 | 85.9 / 86.9 / 86.8 | 86.5 | 0.54 | yes |
| VOICE | 3 | 46/46/46 | 70/70/70 | 85.8 / 85.8 / 85.8 | 85.8 | 0.00 | yes |
| VOICE_PEDIATRIC | 1 | 35/36/30 | 61/61/63 | 69.7 / 70.7 / 65.8 | 68.7 | 2.57 | yes |
| VOICE_PEDIATRIC | 2 | 38/40/39 | 65/63/65 | 74.9 / 75.8 / 75.9 | 75.6 | 0.54 | yes |
| VOICE_PEDIATRIC | 3 | 39/40/37 | 59/63/63 | 72.5 / 75.8 / 72.8 | 73.7 | 1.82 | yes |

- Pooled within-record standard deviation of the combined score: **s = 1.26 points**
  (30 degrees of freedom).
- Threshold of the selection rule: **T = 2 × s × sqrt(2/3) = 2.05 points**.
- Pooled SD by project (6 degrees of freedom each): AI_READI 0.77, CHORUS 1.49,
  CM4AI 1.10, VOICE 0.69, VOICE_PEDIATRIC 1.84.
- Pooled SD by rubric, in percentage points: rubric10 2.33, rubric20 1.53.

## Reading

- The standard deviation of one scoring of a record is about 1.3 points. Under
  `score_gap_v1`, a gap between two 3-scoring means below the threshold of 2.05 points
  does not trigger a change from the current pick. That is a decision threshold. It
  does not show that two such replicates are equivalent, and it is not a resolution
  limit of the instrument.
- The per-project values range from 0.69 to 1.84, a largest-to-smallest variance
  ratio of 7.09. Under Hartley's maximum-ratio test for 5 groups with 6 degrees of
  freedom each, assuming normal and independent scoring scores, the upper 5% point is
  12.11 and the upper-tail probability of the observed ratio is 0.18
  (`scripts/adhoc/check_hartley_fmax_20261126.py` checks both by simulation). The test
  does not reject equal variances, but with 6 degrees of freedom per project that is
  weak evidence and does not establish that the variances are equal. Pooling is a
  working assumption, and the estimate for any one project is rough.
- Rubric10 varies more than rubric20 in percentage terms: its items are binary, so one
  item is 2 percentage points.
- Two records gave the same total on all six scorings; the largest move within one rubric was 6
  rubric10 points (VOICE_PEDIATRIC generation replicate 1, 36 to 30).

## Refused runs and replacements

93 scoring calls produced the 90 cells. Three third-scoring runs were refused, nothing
was published for them, and each was replaced once, on the owner's word, through the
reviewed replacement path (attempt 2). The decision was taken without reading the
refused outputs. Their rows in `scorings.tsv` have `published_attempt` 2 and the
refusal reason.

| Cell (scoring 3) | Why attempt 1 was refused |
|---|---|
| AI_READI generation replicate 3, rubric10 | The output cited two evidence paths the record does not contain; the exact-file validator rejected it. A true refusal. |
| CHORUS generation replicate 1, rubric10 | The runner's session reader misread a child session started without the parent's history. A false refusal (issue 6384). |
| CHORUS generation replicate 2, rubric20 | Same as above. |

Replacement conditions on the output being accepted. If refusal were related to the
score a run would have given, the three replaced cells could be biased; the two
false refusals depend on how the scorer started a helper session, not on the output.

## Limits

- This is variation of one evaluator model on one instrument. It says nothing about
  variation between evaluator models or rubric versions.
- The scores judge how complete and well documented a datasheet is, not whether its
  statements are true.
- Three scorings per record give a rough per-record SD; only the pooled value is used.
- The session-reader defect (issue 6384) could in principle also accept a mismatched
  session. An independent census of all 90 published runs found none: 118 retained
  sessions; 26 runs with a child session, 28 children in all, every one started as a
  fork whose inherited context equals a retained payload owned by its parent; no
  published run with a fresh child; no disagreement between a context and its preceding
  task start among 156 checked. The census does not fix the reader or cover later runs.
