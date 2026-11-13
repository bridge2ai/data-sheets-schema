# Re-check brief: analysis plan amendment N1, draft v9

Read-only narrow re-check. Do not edit the draft, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to re-check

- Draft v9: `notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md` at commit `cc00b677737c8bd2e4afda8a67f89e0f87352c8e` (file sha256 `0893d635a49b89a3d756657e5ea7e2bb04fe74363e0d9e54d1d2323d6f563b66`). Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show cc00b677737c8bd2e4afda8a67f89e0f87352c8e:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`.
- Against draft v8 at commit `98adf23eb96661af33690d6b5593809d8b02a623`. The diff: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 98adf23eb96661af33690d6b5593809d8b02a623 cc00b677737c8bd2e4afda8a67f89e0f87352c8e`.

## The two v8 re-checks v9 says it responds to

Both are in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`:

- `n1v8_98adf23e_claude_recheck_2026-11-12.md` (5 new P2, 7 new P3; 2 of its v7 findings partly resolved);
- `n1v8_98adf23e_codex_recheck_2026-11-12.md` (3 new P2, 1 new P3; 4 of the v7 findings partly resolved).

## Records

- Owner decisions: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (search `D135`, `D136`, `D137`, `D125`, `D92`, `D109`).
- The plan's floor section: `git show 7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1:notes/generic_v10_analysis_plan.md`, section 8 (about lines 1115 to 1163).
- The CI inventory v9 cites: `git show 67274cb2eab87c9ff18cc6b1dc0970301059b845:notes/development_efficiency_20261111/handoffs/lead-ci-run-42976790438-failures-20261112.json` (key `jobs`).
- Native source at `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b`, as before.

## Questions

1. For every new finding of both v8 re-checks, and for the findings they marked partly resolved: resolved, partly resolved or not resolved in v9? One line each, with the v9 line that answers it.
2. The margin. v9 proposes 300 s in place of 90 s and treats the margin as open. Does the text state D136 exactly? Is the reasoning for 300 supported by the sources it uses, and is the arithmetic consistent everywhere (age 1200, margin 300, latest reservation 900, the half-margin rule)? Does any place still depend on 90 or 1110?
3. Did the v9 changes introduce anything new that is wrong, unsupported, inconsistent with the rest of the file, or that weakens a protection? Check in particular: the new items (ad), (ae) and (af) and that every `[proposed]` value has a letter; the stand-down rule and its "no monitoring" clause against N1.3's D12 row and D43; the 30-minute limit on the direction; the sentence that the floor rule for native replicates is ratified before this canary launches, against the plan's section 8 and D109; N1.9 items 4 and 10 and the matching clean check.
4. Is the header's account of what v8 and v9 changed complete against the diffs?

## Output

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then the table for question 1, then any new findings numbered and graded P1, P2 or P3 with the v9 line number, the evidence and the smallest fix. Say plainly if nothing of substance remains. State what you checked and what you did not. Use no at-sign characters.
