---
name: d4d-select-replicate
description: Preview canonical replicate selection from repeated rubric evaluations, scorer variation and sibling content-review evidence; record a selection only after the owner's explicit ruling.
---

# Select one replicate from repeated evaluations

Read the registered [score selection policy](../../../notes/score_selection_policy_2026-11-26.md)
and [review selection policy](../../../notes/review_selection_policy_2026-09-11.md).
Use the existing records and one named scorer instrument. This skill authorizes
no generation, scoring, replacement attempt or inspection of refused outputs.

Run from the repository checkout containing the published evaluations and records.
Set `CONFIG`, `INSTRUMENT`, `METHOD` and `PROJECT` from the requested series.
Set `BASELINE_RECEIPTS` and `REPEAT_RECEIPTS` to the retained scorer run roots;
the repeat root must include its export manifests. Receipt roots prove acceptance,
measured input identity, output-schema binding and published attempt number;
published score files alone do not prove those facts.

## 1. Check completeness before comparing scores

For every candidate, inventory scoring numbers 1, 2 and 3 for both rubric families.
Read the accepted publication paths only after checking the corresponding receipt
is `VALIDATED_AND_PUBLISHED` and its hashes bind the saved plan and publication.
Repeat exports must also have an `EXPORTED_VALIDATED_REPEAT` manifest.
Verify that all scorings use the same instrument and unchanged measured inputs.
Keep invalid generation records visible; they cannot win selection.

Every missing or refused cell is **not measured**, never zero. A missing cell in
any valid candidate means policy fallback for that project's selection. Do not
drop the candidate, mix instruments or silently retry. An accepted replacement
counts once under its scoring number; list its attempt-2 designation and the
retained refusal reason without opening the refused evaluation.

## 2. Run the series variation report

```bash
poetry run d4d runs score-variation --method "$METHOD" --config "$CONFIG" \
  --score-instrument "$INSTRUMENT" \
  --score-receipts "$BASELINE_RECEIPTS" --score-receipts "$REPEAT_RECEIPTS"
```

Report pooled within-record `s`, its degrees of freedom, and the per-project and
per-rubric values. Pool the whole series, not only the project being selected.
If per-project spread differs strongly, show it to the owner before applying the
rule. No numerical heterogeneity cutoff is registered; do not invent one.

## 3. Show the evidence and both picks for each project

```bash
poetry run d4d runs select --method "$METHOD" --project "$PROJECT" --config "$CONFIG" \
  --score-policy score_gap_v1 --score-instrument "$INSTRUMENT" \
  --score-receipts "$BASELINE_RECEIPTS" --score-receipts "$REPEAT_RECEIPTS"
```

For every replicate, show validity, slot coverage, receipt coverage, presence
evaluations, each scoring's points/maximum and attempt, rubric means/spreads, and
content-review verdict counts. Keep absent columns explicitly not measured.
Show the current validity/coverage/label pick, the score-policy pick, `T`, the gap,
and the deciding rule or fallback reason. A score switch requires a gap strictly
greater than `T` and no reversal on either rubric. Do not rewrite the rule.

## 4. Compare every charged content finding across siblings

For each charged finding in any candidate, identify its exact slot and show that
slot's value in every sibling replicate side by side, including absence. Retain
the finding's source and reviewer verdict. Distinguish different wording from
different content; do not replace this comparison with adverse-count totals.
The same value carried by siblings cannot count against just one replicate.
A finding counts against a replicate only where the siblings differ and the
owner rules on it. Content-review counts never become an automatic veto or tie-break.

## 5. Obtain and retain the owner's ruling

Leave every canonical mark unchanged until the owner explicitly authorizes the
concrete selection after seeing the evidence and sibling comparisons.
Record each adjudicated finding in a JSON list with nonempty `label`, `slot`,
`ruling` and `authorization_reference` strings; `label` must name a candidate.
Preview again with `--score-owner-rulings path/to/owner-rulings.json` to include
those rulings in the proposed `canonical.score_policy.owner_rulings` record.
This records the judgment without changing the registered score rule.
After an authorized mark, verify the persisted selection, its score-policy
record, unchanged review policy and owner rulings, and that every replicate remains.
