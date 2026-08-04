# The recorded semantic evaluations cannot go in the manuscript as they stand

The semantic rubric agents are cited in `publication_summary_2026-07-22_fable-5.md`
and `three_way_comparison_2026-07-22.md`. Auditing what is actually on disk
turned up three independent problems, and every recorded evaluation has at least
one of them.

## What is on disk

| set | files | recorded dates |
|---|---|---|
| `rubric10_semantic` | 36 | 2025-12-10 (12), 2026-05-13/14 (8), 2026-07-22 (16) |
| `rubric20_semantic` | 24 | 2026-05-13/14 (8), 2026-07-22 (16) |

## Problem 1 — ungrounded scoring (#162)

Both agents were asked whether a description suits "the claimed dataset type
**and program of origin**". No `program` or `project` slot exists anywhere in
the D4D schema, so the inference falls back to the filename, the invocation
context or prior knowledge — and the agents promise temperature 0.0 with
"same file → same score".

**Fixed in the prompts on 2026-07-22** (`0e19e85f`), which restricted the
inference to quoted values in `keywords`, `publisher` or `funders` and forbade
the filename explicitly. `tests/test_evaluation/test_semantic_agent_grounding.py`
now pins that, including the premise — if the schema ever gains a `program`
slot the test fails and the workaround can go.

**The records predate or straddle the fix.** 8 rubric20 records and 20 rubric10
records are from before it. The 16 dated 2026-07-22 fall on the same day as the
commit and cannot be placed either side of it from the data alone.

## Problem 2 — wrong denominator

All 24 `rubric20_semantic` records carry `max_points: 84`. The rubric's own
questions define 88 — 17 numeric at 5 plus 3 pass/fail — and the presence path
has always used 88. So every semantic percentage is computed against a maximum
the rubric does not have, and is roughly 4.8% high.

`rubric10_semantic` is unaffected: 50 throughout, which is what rubric10 defines.

## Problem 3 — a split project name

Three `rubric10_semantic` records carry `project: "AI"` and
`method: "READI_claudecode"`. `AI_READI` was split on its underscore.

The parsing bug was fixed in `69aa303d` on **2025-12-08**; these records are
dated **2025-12-10**, two days later. So the fix did not cover the path that
produced them, or they were generated from a stale copy. Either way three
records attribute their scores to a project and a method that do not exist.

## What follows

**Every recorded semantic evaluation is affected by at least one of the three.**
Nothing here is recoverable by rescaling: the denominator could be corrected
arithmetically, but a score produced under an ungrounded prompt is not a score
of the record, it is a score of the record plus its filename.

So if semantic results appear in the manuscript, **they need re-running** under
the corrected prompts, against 88, with project names parsed correctly. That is
60 evaluations across the two rubrics.

The alternative is to drop the semantic path from reported results and say why.
That is a decision about the paper rather than the code, and it is cheaper.

## What is safe to keep

The **presence** and **fitness** paths are untouched by all three problems:
presence has always scored rubric20 against 88, fitness has its own rubric and
cache keyed on `(axis, model, rubric, corpus, schema)`, and neither reads a
`program` field. The agreement and form-defect measurements likewise.
