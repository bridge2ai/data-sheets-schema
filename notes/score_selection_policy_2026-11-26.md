# Rubric scores and canonical selection: the `score_gap_v1` rule (2026-11-26)

This note registers a rule that lets `d4d runs select` prefer a replicate on its
repeated rubric scores, but only when the difference is larger than the run-to-run
variation of the scorer. It is committed before the variation of the scorer on the
first series it will be previewed on has been computed. Until it is implemented and
selected with `--score-policy score_gap_v1`, selection is unchanged: validity, then
slot coverage, then label.

It does not change the review policy. Content-review adverse counts stay
report-only under `reported_only_pending_calibration_v1 (#835)`; see
[the review policy note](review_selection_policy_2026-09-11.md). Rubric scores are a
different measurement and had no selection policy before this one.

## The rule

1. **Candidates.** The replicates of one project and configuration that pass
   validity, exactly as today. Validity always comes first; an invalid replicate
   never wins on score.
2. **Eligibility.** Every candidate needs at least 3 scorings per rubric, all on the
   same instrument id and the same measured inputs (composed definition, output
   schema, evidence authority, scope declaration, record bytes). If any candidate
   lacks them, the rule does not apply to that project: selection falls back to the
   current policy and records the reason.
3. **Score of one scoring.** The mean of the rubric10 percentage and the rubric20
   percentage, with equal weight. Scoring number k of one rubric is paired with
   scoring number k of the other.
4. **Score of a replicate.** The mean over its scorings.
5. **Noise.** The pooled within-record standard deviation `s` of the scoring score
   over all records of the series that have at least 2 scorings, with the degrees of
   freedom stated. A pooled value is used because the standard deviation of 3 runs of
   one record is too unstable to gate on.
6. **Threshold.** `T = 2 × s × sqrt(2/3)`, about two standard errors of a difference
   between two means of 3 runs.
7. **Decision.** Let P be the current policy's pick and H the candidate with the
   highest mean. H is selected in place of P only when both hold:
   - `mean(H) − mean(P) > T`;
   - H's mean is at least P's mean on each rubric separately, so one rubric cannot
     carry the decision alone.

   In every other case P is selected.
8. **Record.** The `canonical` block gains `score_policy: score_gap_v1` with the
   instrument id; each candidate's per-rubric means and spreads; `s`, its degrees of
   freedom, `T` and the gap; which rule decided (`score_gap` or `policy_fallback`);
   and the fallback reason. `review_policy` is recorded as before.

## Scorings that were refused

1. A scoring run whose receipt is not VALIDATED_AND_PUBLISHED is not a measurement,
   whatever reason the runner or the validator gave. Nothing is published for it and
   its run directory is kept.
2. Its cell (record × rubric × scoring number) is reported as not measured, never as
   zero and never dropped silently.
3. No retry happens by itself. One replacement attempt per refused cell is allowed,
   only on the owner's word and through a reviewed path; it is recorded as attempt 2
   beside the refused attempt 1. If attempt 2 is refused, the cell stays not measured.
4. The decision to replace is taken without reading the refused output's scores.
5. A project with a not-measured cell in any candidate falls back under step 2.

## Content-review findings

No automatic veto. In the first series reviewed in full, the same value was charged
in one replicate and passed in a sibling replicate carrying the identical value, so
adverse counts are not comparable between replicates. The operator skill therefore
shows each charged finding beside the same slot's value in the sibling replicates. A
finding counts against a replicate only where the siblings do not carry the same
value, and only by the owner's ruling, which the selection block records. The rule
never applies a finding by itself.

## What was known when this was registered

Stated so that a reader can judge how far the rule was fixed in advance.

- The rule's text (steps 1 to 8) was written in the lead's plan file on 2026-11-26
  before any second or third scoring existed. That file is local working state, not a
  commit; this note is the first committed form.
- Known at this commit: the single first scorings of the 15 records of the series
  `2026-11-25c_claude-fable-5-2-claudecode-generic-v9` on the instrument
  `2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6`. On those alone the rule
  would change none of the five current picks.
- Also known: one repeat scoring's total, from the repeat canary (31 of 50 against 32
  of 50 on the first scoring of the same record).
- The second and third scorings have run, but no other repeat total has been read and
  no spread, `s` or `T` has been computed. The variation report runs after this
  commit.
- Three repeat runs were refused and replaced under the rule above; the decisions
  were taken without reading the refused outputs.

Correction, 2026-11-26 (issue 6387): when this note was committed at 06:21:57Z, the three replacements had been authorized and started; one had been published (06:18:23Z) and two were still running (they were published at 06:23:13Z and 06:24:37Z). The variation report was saved at 06:24:58Z, after this commit. This note is the first committed form of the rule; it was not committed before the second and third scorings existed.

## Owner decisions

The owner asked on 2026-11-26 for a plan to select the best replicate from the
evaluations, required that the approach also be a skill, and then asked for the
selection rule to be built as soon as possible. The plan's recommendations are
adopted on that word; this is the lead's reading, and each remains the owner's to
change:

1. a clear score gap outranks slot coverage;
2. the combined score is the equal-weight mean of the two rubric percentages, with
   the per-rubric no-reversal condition;
3. the threshold is two standard errors;
4. on the series named above the rule is run as a preview only, and no canonical mark
   changes without the owner's word;
5. content-review findings are handled as described above.

## Limits

- The scores are one evaluator model's rubric judgement of how complete and well
  documented a datasheet is. They are not a check that its statements are true. The
  rule therefore only chooses among replicates that already pass validity.
- Run-to-run variation of the scorer is the only noise the rule measures. It does not
  measure variation between evaluator models or between rubric versions.
- Ambiguous rubric anchors may raise run-to-run spread, increasing `T`. Repeated
  scoring does not detect or remove systematic evaluator preferences for particular
  record features or replicates.
- The rule is defined for one instrument at a time. Scores from different instruments
  are never mixed, and a series scored on another instrument needs its own `s`.
- Pooling assumes that spread is similar across projects. The variation report states
  the pooled spread per project; if they differ strongly, the rule is not used until
  the owner has seen that.
- Replaced cells condition on the output being accepted. If refusal were related to
  the score a run would have given, replacement could bias the mean. Every replaced
  cell is therefore listed with its refusal reason.

## What would count against the rule

- A pick that changes when the same records are scored three more times on the same
  instrument.
- A per-project spread several times the pooled value.
- Evidence that the higher-scored replicate carries more values contradicted by its
  sources than the policy pick, judged on slots where the replicates differ.

Any of these is reported to the owner, and the rule stays a preview until resolved.
