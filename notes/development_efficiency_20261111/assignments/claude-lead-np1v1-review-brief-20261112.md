# Review brief: analysis plan amendment NP1 (native production cells), draft v1

Read-only adversarial review. You did not write this draft. Do not edit it, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to review

`notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md` at commit `b98b285d0fb75e5a86340980db377ac89aa93b9b` (file sha256 `79948599629f0ef5ee93ca5530b7bbbba03caa41448b22b054dd3d12c1759297`, 248 lines), branch `claude/native-production-amendment-np1-20261112`. Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show b98b285d0fb75e5a86340980db377ac89aa93b9b:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`.

It is a new amendment that stands beside the ratified analysis plan. It plans production cells for the native agentic arm, which the plan leaves unplanned, after the owner directed that the native arm is the main result and chose the scope.

## Sources to check it against

- **The ratified plan:** `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1` (2,559 lines; the draft cites it by line number). Read every passage the draft cites, and the sections it says carry over unchanged.
- **Amendment N1** (the native canary's amendment), which NP1 builds on. NP1 cites N1's draft v7 section numbers. N1 is now at draft v8: `git show 98adf23eb96661af33690d6b5593809d8b02a623:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`. It is unratified and will change again in small ways.
- **Owner decisions and their exact words:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (use `grep -n` for `D07`, `D22`, `D25`, `D35`, `D36`, `D56`, `D64`, `D65`, `D71`, `D91`, `D105`, `D107`, `D109`, `D113`, `D134`, `D135`). The plan's own decision table also records several of them.
- **The native source it cites,** at commit `1a137b58860416a31618de44173180d021dfcc61`: `src/data_sheets_schema/native_shared_receipts.py`, `native_shared_contract.py`, `native_shared_phase.py`, `native_attempt_supervisor.py`.

## Questions

1. **Accuracy.** Is every quotation, line citation and statement about the plan, about N1, about an owner decision and about the source correct? List each one that is not, with the line in the draft and the line in the source. Check N1 references against N1 v8 and say which have moved.
2. **Authority.** Does the draft claim more for D134 or D135 than their recorded words support? Is anything presented as decided that is the lead's choice, or missing its `[proposed]` mark or its lettered item? Does each lettered item hold exactly one decision whose "yes" adopts exactly the value given?
3. **The science.** Is the account of what a comparison of native v10 cells with v8 API records can and cannot support correct and complete against the plan's estimands, predictions, analysis sets, tolerances and missingness rules? Does anything it carries over "unchanged" in fact depend on something the native arm does not have? Is anything claimed that the plan's own rules exclude? Is the proposed floor rule well defined, prospective and free of any value observed on the outcome it governs?
4. **Prospectiveness and leaks.** The plan requires that no rule is chosen after an outcome it governs. Does anything in the draft depend on, or could it have been shaped by, a v10 quality value? Is the header's statement of what the lead had in view adequate?
5. **Consistency and gaps.** Does the order of events work end to end: can every step be carried out with what the earlier steps produce? Are the attempt limits, cause classes and stop-loss coherent with the plan and with N1? What does the draft leave undefined that a registration would need?
6. **The API arm.** Is the proposed comparison set coherent with the plan's scope rule and with what a matched contrast requires? Does the draft make any API item a prerequisite for native production, or silently change an API-arm rule?
7. Anything a careful owner would misread or be surprised by later.

## Output

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then findings numbered and graded P1 (blocks ratification), P2 (should be fixed before ratification) or P3 (wording), each with the draft's line number, the evidence and the smallest fix. State what you checked and what you did not. Use no at-sign characters.
