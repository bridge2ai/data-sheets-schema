# Review brief: analysis plan amendment NP1 (native production cells), draft v7

Read-only adversarial review. You did not write this draft. Do not edit it, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to review

`notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md` at commit `814701f1a39df1d733c199797a3d692d3595ac82` (file sha256 `a10b5963c18e7ce25b441e88892b0931344bcd9f7e265058de226183f442a4de`), branch `claude/native-production-amendment-np1-20261112`. Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 814701f1a39df1d733c199797a3d692d3595ac82:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`.

It is a new amendment that stands beside the ratified analysis plan. It plans production cells for the native agentic arm. It has 39 lettered items, (a) to (am), that the owner answers one by one. Draft v5 cut the contingency branches earlier drafts had invented; draft v7 answers the two v6 reviews, replaces the rule for which pilot reading counts by one fixed comparison, and records the owner's decisions of 2026-11-12. Judge whether what remains is sound, not whether a removed branch could be restored.

- Draft v6 is commit `83fba736819501f6470c36f9765c94990e684d7f`. The diff to v7: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 83fba736819501f6470c36f9765c94990e684d7f 814701f1a39df1d733c199797a3d692d3595ac82`.
- The two reviews of v6, in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`: `np1v6_83fba736_codex_review_2026-11-12.md` (6 findings) and `np1v6_83fba736_claude_review_2026-11-12.md` (11 findings). They were filed as issues 6032 to 6045.
- Source audits the draft relies on: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/np1_floor_source_audit_codex_2026-11-12.md` and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-native-eligibility-audit-20261112.md`.
- **Owner decisions of 2026-11-12 (coordination record, D138 to D145).** Draft v7 records them. Check its quotations of them word for word against STATUS.md, including the owner's three verbatim lines and the lead's reading, which must be marked as the lead's.
- Facts for context: a helper measured the five declared projects' inputs (bundle bytes and chunks: CHORUS 35,920 and 8; VOICE_PEDIATRIC 206,008 and 13; CM4AI 320,799 and 28; VOICE 376,446 and 22; AI_READI 430,393 and 25), and Kids First has no entry, bundle or sources in the source manifest. Issues 5939, 5966, 5967 and 5989 to 5995 are defects of the native route, in various states of repair; the draft lists them as prerequisites with states "per the lead's record", which you need not verify.

## Sources to check it against

- **The ratified plan:** `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`. Read every passage the draft cites.
- **Amendment N1**, draft v12: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`. It is unratified.
- **Owner decisions and their exact words:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (`grep -n` for the decision numbers the draft cites).
- **The native source it cites,** at commit `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`, read with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112 show 5d63d0a77dc43c064cfc2b376355f98009dd5b6e:<path>`. Check statements marked "(audit)" against the source yourself.

## Questions

1. **The v6 findings.** For each finding of the two v6 reviews (use the v7 response table as the list, and check that it leaves none out): resolved, partly resolved or not resolved? One line each, with the v7 line that answers it.
2. **Accuracy.** Is every quotation, line citation and statement about the plan, about N1 v12, about an owner decision and about the source correct? List each that is not.
3. **Authority.** Does each lettered item hold exactly one decision whose "yes" adopts exactly the value given, with the consequence of "no" stated? Is anything presented as decided that is the lead's choice?
4. **The rules that are new or replaced in v7.** Check each for soundness, completeness, undefined cases and any way it could be applied after seeing an outcome it governs:
   - the pinned production source and the equivalence test, item (al): the source is pinned once at the floor's registration; each pilot is compared with it; equivalent stands with no replacement permitted; not equivalent is re-run once, the reason recorded first and both readings reported; a later failing change is a new stratum that never moves the floor or K_native. Is the test's first part (model-facing bytes apart from a closed list of identity fields) well defined and is the list right against the source? Is its second part (acceptance and attempt rules the same, by a written comparison both reviewers confirm) a real constraint or a judgment someone can steer? What happens on a second needed re-run?
   - the canary-first item reduced to its first condition, judged once at the canary's first coded word;
   - the run limits as a declared transfer assumption, and the check of the two limit sets before the canary's first coded word;
   - the three items answered in advance (the basis in D140's form, retention, the runtime terms) and the new item for delegated starts of production runs: do they say exactly what the owner's decisions D140, D141, D143 and D145 say, no more?
   - the "floor is not registered" cases that replace "no value", and the definition of a floor failure;
   - Kids First in scope if the inputs test passes on its own tracked manifest, with the test not yet run;
   - the bar on using native results in any change or redraft from the canary's first coded word to the end of production;
   - the blind review of a stopped canary attempt before the event the draft calls NP1b;
   - the count of first attempts and re-runs.
5. **Consistency.** Do the 39 items agree with the body text and with each other? Does the sequence of events work end to end, including the count of first attempts? Is the list of engineering prerequisites complete and consistent wherever it appears?
6. Anything a careful owner would misread or be surprised by later.

## Output

Grade strictly. P1 is for a defect that would make a ratified rule unsound, contradictory or choosable after an outcome. Do not raise as a finding the absence of a branch the draft deliberately removed, unless its absence leaves a case with no rule at all.

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then the table for question 1, then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title`, graded P1 (blocks ratification), P2 (should be fixed before ratification) or P3 (wording), each with the draft's line number, the evidence and the smallest fix. State what you checked and what you did not. Use no at-sign characters. Compute any hash in the command that prints it.
