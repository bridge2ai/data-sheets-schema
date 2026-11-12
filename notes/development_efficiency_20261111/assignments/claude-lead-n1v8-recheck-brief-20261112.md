# Re-check brief: analysis plan amendment N1, draft v8

Read-only narrow re-check. Do not edit the draft, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to re-check

- Draft v8: `notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md` at commit `98adf23eb96661af33690d6b5593809d8b02a623` (file sha256 `bde0459309ec1d24be35d6098b6ba2dccd962e35c3943f9a4d99688abc2819e7`). Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 98adf23eb96661af33690d6b5593809d8b02a623:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`, not from a working copy.
- Against draft v7 at commit `2fb0503757db041e009f21dd02a1d57a45a75a88`. The diff: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 2fb0503757db041e009f21dd02a1d57a45a75a88 98adf23eb96661af33690d6b5593809d8b02a623`.

## The two v7 reviews v8 says it responds to

Both are in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`:

- `n1v7_2fb05037_claude_review_2026-11-12.md` (7 P2, 8 P3);
- `n1v7_2fb05037_codex_review_2026-11-12.md` (4 P2, 1 P3).

## New owner decisions v8 takes in

In `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md`, search `D135`, `D136`, `D137`. The owner answered "1 yes 2 yes 3 yes" to three numbered questions; the record quotes each question.

## Questions

1. For every finding of both v7 reviews: is it resolved, partly resolved or not resolved in v8? One line each, with the v8 line that answers it. Say where a fix differs from the "smallest fix" the review proposed and whether the difference matters.
2. Does v8 state the owner's new decisions exactly, and claim nothing more for them than the record supports?
3. Did the v8 changes introduce anything new that is wrong, unsupported, inconsistent with the rest of the file, or that weakens a protection? Check in particular: the lettered items (a) to (ac) against the body, including that every value marked `[proposed]` has a letter; the new items N1.9 items 10 and 11 and the added clean checks in N1.4(B) row 4; the 45 s threshold for re-ratifying the margin; the limits on the delegated start; the statement of what a yes and a no to item (y) do.
4. Is the header's account of what v7 and v8 changed complete against the two diffs?

## Output

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then the table for question 1, then any new findings numbered and graded P1, P2 or P3 with the v8 line number, the evidence and the smallest fix. State what you checked and what you did not. Use no at-sign characters.
