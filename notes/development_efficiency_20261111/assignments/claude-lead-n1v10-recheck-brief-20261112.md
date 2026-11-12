# Re-check brief: analysis plan amendment N1, draft v10

Read-only narrow re-check. Do not edit the draft, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to re-check

- Draft v10: `notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md` at commit `127cc0bd69d73fcd21d94978bf5e0ee60e0e950c` (file sha256 `e50777af1aa70b73ec9ab041f0d23c581cbcb56f35d3cb615221ae44f333489f`). Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 127cc0bd69d73fcd21d94978bf5e0ee60e0e950c:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`.
- Against draft v9 at commit `cc00b677737c8bd2e4afda8a67f89e0f87352c8e`. The diff: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff cc00b677737c8bd2e4afda8a67f89e0f87352c8e 127cc0bd69d73fcd21d94978bf5e0ee60e0e950c`.

## The two v9 re-checks v10 says it responds to

Both are in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`:

- `n1v9_cc00b677_claude_recheck_2026-11-12.md` (2 new P2, 6 new P3);
- `n1v9_cc00b677_codex_recheck_2026-11-12.md` (2 new P2, 2 new P3).

## Records

- Owner decisions: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (search `D135`, `D136`, `D137`, `D125`, `D92`, `D109`, `D43`). Under D136 the record now also carries a correction by the lead about the margin.
- The plan's floor section: `git show 7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1:notes/generic_v10_analysis_plan.md`, section 8.
- Native source at `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b`, as before.

## Questions

1. For every new finding of both v9 re-checks: resolved, partly resolved or not resolved in v10? One line each, with the v10 line that answers it.
2. Did the v10 changes introduce anything new that is wrong, unsupported, inconsistent with the rest of the file, or that weakens a protection? Check in particular: item (ah) and the paragraph it adopts (is the existing authority stated exactly, and is the proposal marked and checkable); the adjusted total of item (ab) and the host condition; the new refusal of a direction to a session that started a reviewer; the 30-minute check; the script's bytes in the launch packet; the split of the reviewer-independence item into (ae) and (ag); N1.7's new entries.
3. Every value marked `[proposed]` has a lettered item among (a) to (ah), and each letter is one decision. Is that so?
4. Is the header's account of what v9 and v10 changed complete against the diffs?
5. Stepping back: is anything of substance left that should stop an owner from ratifying this text? Say plainly if nothing is.

## Output

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then the table for question 1, then any new findings numbered and graded P1, P2 or P3 with the v10 line number, the evidence and the smallest fix. State what you checked and what you did not. Use no at-sign characters. Compute any hash in the command that prints it.
