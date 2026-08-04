# Splitting the `form` class: the rule worked, the instrument couldn't say so

`notes/generic_v2_results.md` closed with a problem it could not fix. Generic-v2
was designed to stop the model collapsing several entities into one object, and
on the axis that was supposed to show it, things got **worse**:

| axis | v1 → v2 |
|---|---|
| substance | 40 → 15 |
| target | 41 → 16 |
| **form** | **50 → 56** |

The manual read of the judge's reasons said the rule had in fact worked and a
different defect had taken the same label. This is that read, done as a
measurement.

## Method: classify the failures already paid for

`FITNESS_SYSTEM` emits `failure: none|form|target|substance`. The obvious way to
add sub-types is to edit that rubric — and the judgement cache is keyed on
`(axis, model, rubric, corpus, schema)` precisely so a changed rubric cannot be
silently compared against an unchanged one. Editing it invalidates **all 1441**
cached fitness judgements and discards a v1/v2 comparison already bought.

The sub-type question does not need the fitness judge re-run. Every cached
entry carries the slot and the full value, which is all the question needs. So a
second, narrower classifier runs over the **106 cached `form` failures** only:

- **106 calls instead of 1441** — 13× less.
- The published fitness numbers are untouched; this is a layer on top, not a
  replacement.
- Each arm is recovered by matching the stored value back against the records —
  the fitness cache keeps no run label. Exact match on canonical JSON, and it
  attributes **50 to v1 and 56 to v2 with nothing left over**, which is the
  published split arriving independently.

Reproduce with no paid call:

```bash
python -m data_sheets_schema.form_defects --offline
```

## Result: two defects moving in opposite directions

| subtype | v1 | v2 |
|---|---|---|
| collapsed cardinality | 34 | **2** |
| hollow object | **0** | **45** |
| both | 8 | 5 |
| other | 8 | 4 |
| **total** | **50** | **56** |

Counting each defect wherever it appears, including `both`:

| defect | v1 → v2 | |
|---|---|---|
| **collapsed cardinality** | **42 → 7** | **−83%** |
| **hollow object** | **8 → 50** | **+42** |

**The rule did what it was written to do.** Collapsed cardinality — several
entities packed into one object — falls by 83%. What the old axis reported as a
12% regression is one defect being all but eliminated and a second appearing in
its place: the model now emits one object per entity, exactly as instructed, and
fills each with free-text `description` while `name`, `id`, `affiliations`,
`start_date` and `end_date` go unused. Correct shape, empty.

## Against the manual read

| subtype | this run | note's manual read |
|---|---|---|
| collapsed cardinality | 34 → 2 | 27 → 0 |
| hollow object | 0 → 45 | 2 → 33 |
| both | 8 → 5 | 4 → 3 |
| other | 8 → 4 | 17 → 20 |

Same story, different boundaries. Both show collapsed cardinality nearly
eliminated and hollow objects appearing from almost nothing. The classifier is
more decisive: 12 in `other` against the manual read's 37, because a human
reading judge reasons in bulk retreats to "unclear" more readily than a judge
asked one question about one value with the schema in front of it.

That the two agree on direction and magnitude while disagreeing on the residual
is the expected shape of agreement between a manual pass and an instrument. The
instrument is the one that can be re-run.

## What this changes

**`form` should not be reported as one number again.** It is two defects with
opposite responses to the same intervention, and any prompt change aimed at one
will look like a regression if the other picks up the slack.

**For the v2 promotion decision:** rule 1 is a success on its own terms and
should not be promoted as written. It moves records from one form failure to
another and leaves the total roughly flat. Promoting it needs a companion
instruction — populate the declared structured fields, do not put the content in
`description` — or it trades a defect for a defect.

**For the next comparison:** the sub-type is now a measurement with a cache and
a test, so the next arm can be compared on collapsed-cardinality and
hollow-object separately without anyone re-reading judge reasons by hand.

## Cost

106 classifier calls, ~7 minutes, cached content-addressed and keyed on rubric
and model. The 1441 fitness judgements were not touched.
