# generic-v3 analysis plan

Registered before any v3 generation run. The prediction is here rather than in
the prompt because writing it there would instruct the model to produce the
result the run is meant to test.

## What v3 changes

One rule, added to v2's three:

> When a slot's declared range is a class, populate the fields that class
> declares. Placing the content in a free-text field such as `description` while
> the declared fields — a name, an identifier, dates, affiliations — stay empty
> produces an object of the correct shape holding none of the structure it
> exists to carry. Where the evidence answers a declared field, populate that
> field rather than restating it in prose.

## Why

v2's rule 1 worked and traded one defect for another. Splitting the fitness
`form` class (`notes/form_defect_split_2026-08-03.md`) measured, over the 106
form failures already judged:

| defect | v1 → v2 |
|---|---|
| collapsed cardinality | 42 → 7 |
| hollow object | 8 → 50 |

The reported `form` total moved 50 → 56 and hid both.

## The comparison

**v2 against v3**, not v1 against v3. The two differ on one axis (`base`), and
only that pairing isolates the companion rule. v1 against v3 would measure four
rules at once.

Same four projects, three replicates, same model and settings as the v1 and v2
series. The label carries `generic-v3`.

## Prediction, registered

1. **Hollow objects fall.** This is the rule's own target and the only outcome
   that would make it worth promoting.
2. **Collapsed cardinality does not return.** v2's rule 1 is still present and
   unchanged, so its effect should persist. If collapsed cardinality rises again
   the two rules interact, and the companion is not additive.
3. **The `form` total falls**, because it is now the sum of two things both
   predicted to be low. This is the outcome the unsplit axis could not show for
   v2 and is the reason the split had to come first.
4. **Substance and target stay flat** against v2. Nothing in the new rule
   addresses either. Movement there is a signal that adding any fourth rule
   changes behaviour diffusely rather than at the point it names — which would
   itself be worth knowing, and would weaken the case that these rules compose.

## What would count as failure

- Hollow objects flat or up: the rule is not doing what it says.
- Collapsed cardinality returning: the rules are not additive, and rule 1 plus
  the companion needs rewriting as a single instruction rather than two.
- A new form sub-type appearing in `other`: the same exchange happening again
  one level down. `other` is now measured, so this is visible rather than
  inferred — it was 8 → 4 across v1 → v2.

## How it will be measured

Fitness scoring as before, then `python -m data_sheets_schema.form_defects` for
the sub-type breakdown. The fitness rubric is **not** edited, so the v1 and v2
judgements stay valid and the three arms remain comparable; the sub-type
classifier's rubric is likewise unchanged, so its cached labels stay valid too.
Both caches are keyed on their rubric, so an edit to either invalidates rather
than silently mixes.

## Cost

Twelve generations (four projects x three replicates), then fitness scoring of
the new records and sub-type classification of whatever form failures they
produce. Not yet run, and not to be run without a decision to spend it.
