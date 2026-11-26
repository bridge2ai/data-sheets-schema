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

Every missing or refused cell is **not measured**, never zero. Compare the
expected roster with the discovered census before inspecting measurements. The
expected roster is the selected source manifest's projects times the union of
replicate labels discovered for this configuration. It is independent of which
projects have score evidence. Any membership difference forces fallback. For an
intentional narrower series, repeat `--score-series-project NAME` once per expected
project on every preview; this explicit roster replaces the manifest's list and
is recorded, together with excluded discovered projects. Do not omit a missing
project implicitly. Inspect every record in the declared series, including
records of other projects. Under the
lead's conservative implementation rulings, an unreadable record or any
not-measured cell makes every project fall back to the current policy. Keep the
record, usable paired count and exact reason visible; never silently remove it
from the noise estimate.

An accepted replacement counts once under its scoring number. Its attempt-2
manifest must name exactly one retained refusal, and every matching refusal must
be accounted for by exactly one accepted cell. Every matching run whose
receipt is not accepted counts in that accounting, including an unfinished run
with a saved plan and no receipt. Undeclared replacements or an additional
attempt force fallback. Never open the refused evaluation. Retain refused plan
and receipt hashes, plus a bounded path-free reason; disclose replacements from
every project contributing to pooled spread.

The registered threshold compares means of three scorings. A fourth scoring
forces fallback rather than being ignored. Percentages use each rubric's
`max_points` from the accepted published files. Require one maximum per rubric
across every measured cell of the entire series, with `adjusted_max_points` equal
to it, and one applicability context across the project's candidates and rubrics.
No instrument-specific maximum is assumed. Otherwise retain the
recorded fallback reason. These checks implement the lead's rulings without
editing steps 1–8 of the registered rule.

## 2. Run the series variation report

```bash
poetry run d4d runs score-variation --method "$METHOD" --config "$CONFIG" \
  --score-instrument "$INSTRUMENT" \
  --score-receipts "$BASELINE_RECEIPTS" --score-receipts "$REPEAT_RECEIPTS"
```

Report pooled within-record `s`, its degrees of freedom, and the per-project and
per-rubric values. Pool the whole series, not only the project being selected.
A pool with fewer than two usable records, zero pooled spread, or incompatible
instrument bytes cannot support a score switch; report its fallback reason.
When the series is incomplete, registered `s` and `T` remain null with the
reason. Separately named `partial_variation` diagnostics never authorize selection.
The canonical score-policy block stores the full series census once.
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
and the deciding rule or fallback reason. The historical `margin_over_runner_up`
continues to describe the policy pick's coverage margin. The separate
`selected_coverage_margin_over_best_other` describes the selected score-policy
record against the best other coverage contender, which can be negative. Retain
per-cell points, maximum,
attempt, publication and receipt hashes, and repository-relative publication
paths so the decision can be re-derived. Report any highest-mean tie and the
conservative tie rule. A score switch requires a gap strictly
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
`ruling` and `authorization_reference` strings, with no other fields; `label` must
name a candidate and `slot` must occur in that candidate’s evidence table. Use
portable references rather than absolute machine paths.
Preview again with `--score-owner-rulings path/to/owner-rulings.json` to include
those rulings in the proposed `canonical.score_policy.owner_rulings` record.
Each ruling is printed and retained; it never changes the arithmetic. If the owner
wants another selection, resolve that decision explicitly rather than expecting
the rulings file to veto a score result.
A score-policy mark requires the owner's separate nonempty text through
`--score-owner-authorization TEXT`; the CLI records the text and refuses a mark
without it. This text prevents an accidental mark and records the asserted
authorization; it is not proof of authorization or a signature tied to a pick.
The option guard is checked before any write. Ordinary previews need
no authorization text, and this skill does not supply one.
After an authorized mark, verify the persisted selection, its score-policy
record, unchanged review policy and owner rulings, and that every replicate remains.
