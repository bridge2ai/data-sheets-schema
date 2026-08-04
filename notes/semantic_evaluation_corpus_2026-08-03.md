# The recorded evaluations score records that are no longer in the study

**The finding that matters is Problem 4 below: the evaluation targets are gone.**
Not one of the 24 `rubric20_semantic` records points at a file that still
exists, and the same is true of both published summaries across all four
rubrics — not only the semantic ones (#286).

The other three problems are real and were found first, which is why they are
numbered first. They are worth less than they look: correcting a denominator on
a score of an archived record produces a corrected number about nothing.

Auditing what is actually on disk turned up **four** problems. Every recorded
semantic evaluation has at least one of the first three, and all of them have
the fourth.

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

**The records predate the fix, except where they don't.** 8 rubric20 records and
20 rubric10 records are from before it. The 16 dated 2026-07-22 *can* be placed:
`run_manifest_2026-07-22_fable-5.json` records `git_head` as `0e19e85f`, which is
the grounding-fix commit itself, so those were produced with the fix in place.

An earlier version of this note said they could not be placed from the data
alone. The manifest was the data, and it had not been read.

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

## Problem 4 — and it subsumes the other three: the targets are gone

| set | files | target still on disk | target gone |
|---|---|---|---|
| `rubric20_semantic` | 24 | **0** | 24 |
| `rubric10_semantic` | 36 | 9 | 27 |

They point at the `2026-04-10_sonnet-4.6` label — archived as unattestable by
`d4d runs archive --unattested` — and at flat pre-run-label paths removed when
outputs moved into dated run directories.

This is not confined to the semantic path. Both published summaries have it
across all four rubrics: `publication_summary_2026-07-22_fable-5.md`, titled
"D4D Publication Summary", scored the archived label, and
`three_way_comparison_2026-07-22.md` says so in its own header. Filed as #286.

The records themselves survive under
`data/ATTIC/d4d_concatenated_archived/claudecode_agent/2026-04-10_sonnet-4.6/`,
so the evaluations remain traceable to their inputs. It is a framing problem,
not data loss.

**It changes what the other three problems are worth.** Correcting a denominator
on a score of an archived record produces a corrected number about nothing.

## What follows

**Every recorded semantic evaluation is affected by at least one of the three,
and all of them by the fourth.**
Nothing here is recoverable by rescaling: the denominator could be corrected
arithmetically, but a score produced under an ungrounded prompt is not a score
of the record, it is a score of the record plus its filename.

So if semantic results appear in the manuscript, they need **generating against
the current corpus** — not re-running, because there is nothing to re-run
against. How many is a scoping decision rather than a count read off disk;
options and a recommendation are in #287.

The alternative is to drop the semantic path from reported results and say why.
That is a decision about the paper rather than the code, and it is cheaper.

## What is safe to keep

**Fitness is clean on all four.** Its 106 form failures attribute exactly to the
current 2026-07-28 and 2026-07-31 runs — 50 to v1, 56 to v2, nothing
unattributed (#271) — so its targets are live. It has its own rubric, a cache
keyed on `(axis, model, rubric, corpus, schema)`, and reads no `program` field.
The agreement and form-defect measurements likewise.

**Presence is clean on problems 1-3 and shares problem 4 in part.** It has
always scored rubric20 against 88 and reads no `program` field, but 8 of its 19
recorded targets are gone, every one in the flat pre-run-label layout. So
presence figures can be cited on their method and not on their coverage: eight
of them describe files that are not there (#289).

An earlier version of this section said presence and fitness were both
"untouched by all three problems". That was written before problem 4 existed and
did not survive it.
