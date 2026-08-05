# generic-v4 analysis plan

Registered before any v4 generation run. The prediction is here rather than in
the prompt because writing it there would instruct the model to produce the
result the run is meant to test.

## What v4 changes

One rule, added to v3's:

> Where a slot's declared range is a scalar, populate it with the identifier of
> the thing it refers to, not with the thing itself. An object placed in a
> string-ranged slot fails validation and loses the reference it was meant to
> record, even where that thing is richly described elsewhere in the record.

## Why

v3 tells the model to populate the fields a class-ranged slot declares. It says
nothing about where structure does *not* belong, and `related_datasets` is
class-ranged while its `target_dataset` is `range: string`.

All three 2026-07-31 VOICE replicates fail validation on `related_datasets`
(#292), by three different routes:

| replicate | failure | status |
|---|---|---|
| rep1 | inline `Dataset` object in `target_dataset` | **this rule** |
| rep2 | `relationship_type: related_to` | no enum equivalent; a real generation failure |
| rep3 | `relationship_type: IsNewVersionOf` | already fixed — `normalise_enum_aliases` is on the write path |

#297 established that LinkML cannot express a string-or-inline-object range, so
the schema cannot refuse an object in `target_dataset`. A prompt rule is the only
available remedy.

## Prediction

Registered in advance, and falsifiable:

1. **Primary.** The inline-object failure in `target_dataset` does not occur in
   any v4 replicate. Measured as `linkml-validate` errors of the form
   `... is not of type 'string' in /related_datasets/*/target_dataset`.
2. **Guard against over-application.** v4 does not reduce the population of
   class-ranged slots relative to v3. A rule about scalars that suppresses
   legitimate object population has traded one defect for another, which is
   exactly what v2's rule 1 did (`notes/form_defect_split_2026-08-03.md`) and
   what v3 exists to repair. Measured as items enumerated per record via
   `data_sheets_schema.enumeration.total_depth`, v4 against v3.
3. **Null result is informative.** If rep1's failure mode does not recur under
   v3 either, the rule is unnecessary and should be retired rather than kept
   because it sounds sensible. v3 must be run to know this.

## What would falsify it

Prediction 1 fails if any v4 replicate places an object in a string-ranged slot.
Prediction 2 fails if v4's mean enumerated depth is materially below v3's — the
same trade v2 made, in the opposite direction.

## Comparison

v3 against v4 isolates this rule. v2 against v4 does **not**: it spans two rule
additions, and `comparable_conditions("generic_v2", "generic_v4")` returns False
for that reason.
