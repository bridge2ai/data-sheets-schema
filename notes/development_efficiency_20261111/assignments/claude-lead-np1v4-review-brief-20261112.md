# Review brief: analysis plan amendment NP1 (native production cells), draft v4

Read-only adversarial review. You did not write this draft. Do not edit it, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to review

`notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md` at commit `3284bdef9790f949b6ccc6157c68793c06e8d55a` (file sha256 `1ad5fffe44593f2e5d85efdfc3ea41370b69d34f0586cf518299c7dd6a928c8a`), branch `claude/native-production-amendment-np1-20261112`. Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 3284bdef9790f949b6ccc6157c68793c06e8d55a:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`.

It is a new amendment that stands beside the ratified analysis plan. It plans production cells for the native agentic arm. It has 37 lettered items, (a) to (ak), that the owner answers one by one.

- Draft v3 is commit `27429678f37d5df92e2055fe5fa8e13e7717f871`. The diff to v4: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 27429678f37d5df92e2055fe5fa8e13e7717f871 3284bdef9790f949b6ccc6157c68793c06e8d55a`.
- The two reviews of v3, in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`: `np1v3_27429678_codex_review_2026-11-12.md` (7 findings) and `np1v3_27429678_claude_review_2026-11-12.md` (18 findings). They were filed as issues 5969 to 5988; five findings overlap between the two reports.
- Source audits the draft relies on: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/np1_floor_source_audit_codex_2026-11-12.md` and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-native-eligibility-audit-20261112.md`.
- New facts since v3, for context: a helper measured the five declared projects' inputs (bundle bytes and chunks: CHORUS 35,920 and 8; VOICE_PEDIATRIC 206,008 and 13; CM4AI 320,799 and 28; VOICE 376,446 and 22; AI_READI 430,393 and 25), and Kids First has no entry, bundle or sources in the source manifest. Issues 5939, 5966 and 5967 are open defects of the native route.

## Sources to check it against

- **The ratified plan:** `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`. Read every passage the draft cites.
- **Amendment N1**, draft v12: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`. It is unratified.
- **Owner decisions and their exact words:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (`grep -n` for the decision numbers the draft cites).
- **The native source it cites,** at commit `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`, read with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112 show 5d63d0a77dc43c064cfc2b376355f98009dd5b6e:<path>`. Check statements marked "(audit)" against the source yourself.

## Questions

1. **The v3 findings.** For each finding of the two v3 reviews (use the v4 response table as the list, and check that it leaves none out): resolved, partly resolved or not resolved? One line each, with the v4 line that answers it.
2. **Accuracy.** Is every quotation, line citation and statement about the plan, about N1 v12, about an owner decision and about the source correct? List each that is not.
3. **Authority.** Does each lettered item hold exactly one decision whose "yes" adopts exactly the value given, with the consequence of "no" stated? Is anything presented as decided that is the lead's choice?
4. **The rules that are new or replaced in v4.** Check each for soundness, completeness, undefined cases and any way it could be applied after seeing an outcome it governs:
   - the retention prerequisite, item (n), and the corrected eligibility rule, item (m);
   - the basis item (r), which must be answered before the canary's registration is built, with its default;
   - the floor rule with one reading, item (s), and the floor gating at the final stage only, item (t);
   - the acceptance rows for pilots and production cells, item (u), and the native identities in the acceptance record, item (v);
   - attempts and backstop ends, items (w) and (ab): the canary's fixed runtime terms for every attempt, and the fixed consequences when an attempt ends on the deadline or the guard;
   - the two tests at the event the draft calls NP1b, item (a), and the owner's remaining input there;
   - the pilot's attempts and conclusions, item (f), and the reading of D113, item (h);
   - the canary-first remedy with the replacement pilot, item (ak): the list of items whose answers must be recorded before dispatch, and the replacement pilot's place in the sequence;
   - K_native with the plan's kinds of missingness, item (k).
5. **Consistency.** Do the 37 items agree with the body text and with each other? Does the sequence of events work end to end, including the count of first attempts? Is the list of engineering prerequisites complete and consistent wherever it appears?
6. Anything a careful owner would misread or be surprised by later.

## Output

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then the table for question 1, then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title`, graded P1 (blocks ratification), P2 (should be fixed before ratification) or P3 (wording), each with the draft's line number, the evidence and the smallest fix. State what you checked and what you did not. Use no at-sign characters. Compute any hash in the command that prints it.
