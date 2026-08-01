# generic-v2: results, against the plan registered before the runs

Companion to `notes/generic_v2_analysis_plan.md`. Every number below comes from
the same fitness rubric, model and schema as the v1 baseline — the judgement
cache is keyed on `(axis, model, rubric, corpus, schema)` and the context
fingerprint was verified identical (`fitness / google/claude-opus-5-high /
6c5b10778ade / '' / 34d24ff30fb6ad0f10d82af09ddc1fba`) before any scoring ran.

Method check: recomputing v1's failure table from the cache reproduces the
pre-registered table exactly — form 50, substance 40, target 41, total 131, and
37/36/39/19 by project. So the procedure here is the one that produced the
baseline, not a re-implementation of it.

Arms: v1 = `2026-07-28_claude-opus-5-generic_rep{1,2,3}`, v2 =
`2026-07-31_claude-opus-5-generic-v2_rep{1,2,3}`. 12 records each, 4 projects.
797 v2 slot values judged, 0 unscored.

## Headline

| class | AI_READI | CHORUS | CM4AI | VOICE | total |
|---|---|---|---|---|---|
| form | 14 → 16 | 12 → 15 | 16 → 11 | 8 → 14 | **50 → 56** |
| substance | 17 → 3 | 12 → 9 | 5 → 2 | 6 → 1 | **40 → 15** |
| target | 6 → 2 | 12 → 5 | 18 → 7 | 5 → 2 | **41 → 16** |
| **total** | 37 → 21 | 36 → 29 | 39 → 20 | 19 → 17 | **131 → 87** |

Total defective fields fall 34%. Failures fall in all four projects, so the
"failures fall only in one project" condition is not met.

## The form result is the opposite of what the aggregate says

The plan predicted form would fall by more than half in every project, on the
reasoning that it is the most mechanical of the three. The aggregate *rose*,
50 → 56, which by the plan's stated inference means "the rule did not land, and
the others are unlikely to have".

That inference is wrong, and the aggregate is hiding why. Classifying each form
judgement by what the judge actually objected to:

| form sub-type | v1 | v2 |
|---|---|---|
| collapsed cardinality — several entities in one object | **27** | **0** |
| hollow object — one object per entity, but all content in free-text `description` | 2 | 33 |
| both | 4 | 3 |
| other | 17 | 20 |

The defect the rule targeted is **eliminated: 27 → 0**. What replaced it is a
different failure wearing the same label — the model now emits one object per
entity, exactly as instructed, and fills each with a free-text `description`
while `name`, `id`, `affiliations`, `start_date`, `end_date` go unused. The
judge's own words: "Correct topic and cardinality, but all entries collapse
dates into free-text descriptions"; "Correct creators listed as Creator
objects, but all data crammed into free-text description".

`collection_timeframes` newly fails form in all four projects; `creators`,
`distribution_formats` and `distribution_dates` in three. This is systematic,
not sampling noise.

So the rule did what it said. The instrument could not show it, because one
`form` class covers two distinct defects and the rule moved records from one to
the other. **Any future comparison on this axis should split them.**

## Substance and target moved most, having been predicted to move least

- **substance 40 → 15 (−62%)**, predicted to fall "but by less" than form.
- **target 41 → 16 (−61%)**, predicted "least likely to move" on the grounds
  that choosing between neighbouring fields requires judgement an instruction
  may not supply. It supplied it.

The predicted ordering (form > substance > target) is inverted by the results
(target ≈ substance > form-as-aggregate).

## How much of the substance drop is omission rather than repair

The plan flagged this: the substance rule *instructs* omission ("omit the slot
instead"), so a fall in substance failures should partly appear as a fall in
slot count, and that is the correct response, not a defect.

Of 22 slots that failed substance in v1: **9 omitted in v2, 9 repaired**, 4 still
failing.

| project | v1 substance slots | now absent | repaired |
|---|---|---|---|
| AI_READI | 8 | 6 | 2 |
| CHORUS | 8 | 2 | 3 |
| CM4AI | 3 | 0 | 2 |
| VOICE | 3 | 1 | 2 |

AI_READI is mostly omission. Slot counts, mean per project:

| project | v1 | v2 | Δ |
|---|---|---|---|
| AI_READI | 78.7 | 69.7 | −9.0 (−11%) |
| CHORUS | 54.7 | 48.7 | −6.0 (−11%) |
| CM4AI | 64.0 | 69.7 | +5.7 (+9%) |
| VOICE | 76.7 | 77.7 | +1.0 (+1%) |

Totals 822 → 797, −3%. The plan's condition was "total slot counts fall
*sharply* while failures fall". Across the corpus they do not. For AI_READI and
CHORUS individually they fall 11% while failures fall 43% and 19%, and for
AI_READI the substance drop is three-quarters omission. **That project is where
the "bought correctness by suppressing content" reading has force, and it should
not be waved away by the corpus-level −3%.** CM4AI and VOICE moved the other
way, which is why the aggregate is flat.

## Mean fitness barely moves

| project | v1 | v2 | Δ |
|---|---|---|---|
| AI_READI | 0.884 | 0.898 | +0.014 |
| CHORUS | 0.840 | 0.821 | −0.019 |
| CM4AI | 0.861 | 0.902 | +0.041 |
| VOICE | 0.910 | 0.897 | −0.013 |

A 34% fall in defective fields with mean fitness flat to ±0.04 is consistent:
fitness averages ~800 values per arm, failures are the tail. Mean fitness is
the wrong statistic for this intervention and should not be reported as the
result.

**Unresolved discrepancy.** These v1 means differ slightly from the plan's
baseline table (0.901 / 0.847 / 0.850 / 0.912) although the failure counts
reproduce exactly. The denominator used for the baseline means is evidently not
the one used here. Failure counts are unaffected; the mean-fitness column should
be treated as internally consistent but not comparable to the plan's table until
that is run down.

## Verdict

The three rules landed. Two of them (substance, target) cut their target defect
by ~60% and were the two predicted least likely to work. The third eliminated
its target defect entirely and was scored as a regression because the class it
is measured in contains a second defect it did not address.

Not established: that the records are *better*. Fitness measures agreement with
the schema specification, not truth (#177, no gold standard). AI-READI in
particular achieved part of its improvement by dropping six fields.

## Next

1. Split `form` into cardinality and structural-population before any further
   comparison on this axis; the current class cannot measure what v2 changed.
2. A fourth rule aimed at hollow objects — populate the object's own slots, not
   just its description — is the obvious follow-on, and now has a clean
   before/after target of 33.
3. Settle the mean-fitness denominator discrepancy.
4. n=3 per project. The direction is consistent across all four projects and
   the mechanism check (27 → 0) is not a marginal count, but magnitudes per
   project rest on three records each.
