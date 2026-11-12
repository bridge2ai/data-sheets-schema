# Review brief: analysis plan amendment NP1 (native production cells), draft v5

Read-only adversarial review. You did not write this draft. Do not edit it, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to review

`notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md` at commit `1e860410d782580954e2e4f684407c10e2574b2a` (file sha256 `5484377a813cf9ce356b3af047bf9198cf13aa2ab17925a42feb554b5f288682`), branch `claude/native-production-amendment-np1-20261112`. Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 1e860410d782580954e2e4f684407c10e2574b2a:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`.

It is a new amendment that stands beside the ratified analysis plan. It plans production cells for the native agentic arm. It has 36 lettered items, (a) to (aj), that the owner answers one by one. Draft v5 was written to cut contingency branches that earlier drafts had invented and that each review round found defects in; judge whether what remains is sound, not whether a removed branch could be restored.

- Draft v4 is commit `3284bdef9790f949b6ccc6157c68793c06e8d55a`. The diff to v5: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 3284bdef9790f949b6ccc6157c68793c06e8d55a 1e860410d782580954e2e4f684407c10e2574b2a`.
- The two reviews of v4, in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`: `np1v4_3284bdef_codex_review_2026-11-12.md` (9 findings) and `np1v4_3284bdef_claude_review_2026-11-12.md` (16 findings). They were filed as issues 5996 to 6014; six findings overlap between the two reports.
- Source audits the draft relies on: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/np1_floor_source_audit_codex_2026-11-12.md` and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-native-eligibility-audit-20261112.md`.
- Facts for context: a helper measured the five declared projects' inputs (bundle bytes and chunks: CHORUS 35,920 and 8; VOICE_PEDIATRIC 206,008 and 13; CM4AI 320,799 and 28; VOICE 376,446 and 22; AI_READI 430,393 and 25), and Kids First has no entry, bundle or sources in the source manifest. Issues 5939, 5966, 5967 and 5989 to 5995 are defects of the native route, in various states of repair; the draft lists them as prerequisites with states "per the lead's record", which you need not verify.

## Sources to check it against

- **The ratified plan:** `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`. Read every passage the draft cites.
- **Amendment N1**, draft v12: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`. It is unratified.
- **Owner decisions and their exact words:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (`grep -n` for the decision numbers the draft cites).
- **The native source it cites,** at commit `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`, read with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112 show 5d63d0a77dc43c064cfc2b376355f98009dd5b6e:<path>`. Check statements marked "(audit)" against the source yourself.

## Questions

1. **The v4 findings.** For each finding of the two v4 reviews (use the v5 response table as the list, and check that it leaves none out): resolved, partly resolved or not resolved? One line each, with the v5 line that answers it.
2. **Accuracy.** Is every quotation, line citation and statement about the plan, about N1 v12, about an owner decision and about the source correct? List each that is not.
3. **Authority.** Does each lettered item hold exactly one decision whose "yes" adopts exactly the value given, with the consequence of "no" stated? Is anything presented as decided that is the lead's choice?
4. **The rules that are new or replaced in v5.** Check each for soundness, completeness, undefined cases and any way it could be applied after seeing an outcome it governs:
   - the canary-first condition on the whole document (ratified by sha256 with every answer before the canary's first registration commit, unchanged up to the floor's registration; otherwise a replacement CHORUS pilot), and every timing clause it qualifies;
   - the single outcome table for every pilot (the canary, the AI_READI pilot, the replacement pilot), including what happens when the owner gives no further word;
   - the one inputs test that decides scope, and "not planned" as distinct from missing;
   - deadline and guard ends left to the plan's existing cause classes, precedence and next actions, with the termination mechanism recorded separately; and the two proposed readings under the cause-class item (what counts as a stopped attempt's final records; which attempts the blind review reads);
   - the runtime-terms item reduced to the canary's registered terms;
   - the convention for "no" answers and the written alternatives that were kept;
   - the conditional statement of what a floor failure leaves;
   - the count of first attempts.
5. **Consistency.** Do the 36 items agree with the body text and with each other? Does the sequence of events work end to end, including the count of first attempts? Is the list of engineering prerequisites complete and consistent wherever it appears?
6. Anything a careful owner would misread or be surprised by later.

## Output

Grade strictly. P1 is for a defect that would make a ratified rule unsound, contradictory or choosable after an outcome. Do not raise as a finding the absence of a branch the draft deliberately removed, unless its absence leaves a case with no rule at all.

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then the table for question 1, then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title`, graded P1 (blocks ratification), P2 (should be fixed before ratification) or P3 (wording), each with the draft's line number, the evidence and the smallest fix. State what you checked and what you did not. Use no at-sign characters. Compute any hash in the command that prints it.
