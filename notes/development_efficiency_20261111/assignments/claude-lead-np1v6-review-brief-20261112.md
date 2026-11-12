# Review brief: analysis plan amendment NP1 (native production cells), draft v6

Read-only adversarial review. You did not write this draft. Do not edit it, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to review

`notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md` at commit `83fba736819501f6470c36f9765c94990e684d7f` (file sha256 `90521f3e67729d9332843789e64524919225be9b47d16ae7858bccf1af7fc0a6`), branch `claude/native-production-amendment-np1-20261112`. Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 83fba736819501f6470c36f9765c94990e684d7f:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`.

It is a new amendment that stands beside the ratified analysis plan. It plans production cells for the native agentic arm. It has 37 lettered items, (a) to (ak), that the owner answers one by one. Draft v5 cut the contingency branches earlier drafts had invented; draft v6 applies the small fixes both v5 reviews asked for and rewrites one item, the runtime terms. Judge whether what remains is sound, not whether a removed branch could be restored.

- Draft v5 is commit `1e860410d782580954e2e4f684407c10e2574b2a`. The diff to v6: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 1e860410d782580954e2e4f684407c10e2574b2a 83fba736819501f6470c36f9765c94990e684d7f`.
- The two reviews of v5, in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`: `np1v5_1e860410_codex_review_2026-11-12.md` (5 findings) and `np1v5_1e860410_claude_review_2026-11-12.md` (10 findings). They were filed as issues 6017 to 6029; two findings overlap between the two reports.
- Source audits the draft relies on: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/np1_floor_source_audit_codex_2026-11-12.md` and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-native-eligibility-audit-20261112.md`.
- **Owner decisions made after v6 was started, for context only (coordination record, D138 to D145, 2026-11-12):** amendment N1, draft v12, is ratified; the owner answered three of this amendment's items in advance: the floor's basis is at-receipt, rejected and stopped runs keep their records, and the runtime terms are alternative B; and delegated starts are allowed for production runs, each run still needing its own word. The draft does not yet record these; review the text as written, and say where an advance answer makes a written alternative moot or leaves the text inconsistent with it.
- Facts for context: a helper measured the five declared projects' inputs (bundle bytes and chunks: CHORUS 35,920 and 8; VOICE_PEDIATRIC 206,008 and 13; CM4AI 320,799 and 28; VOICE 376,446 and 22; AI_READI 430,393 and 25), and Kids First has no entry, bundle or sources in the source manifest. Issues 5939, 5966, 5967 and 5989 to 5995 are defects of the native route, in various states of repair; the draft lists them as prerequisites with states "per the lead's record", which you need not verify.

## Sources to check it against

- **The ratified plan:** `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`. Read every passage the draft cites.
- **Amendment N1**, draft v12: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`. It is unratified.
- **Owner decisions and their exact words:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (`grep -n` for the decision numbers the draft cites).
- **The native source it cites,** at commit `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`, read with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112 show 5d63d0a77dc43c064cfc2b376355f98009dd5b6e:<path>`. Check statements marked "(audit)" against the source yourself.

## Questions

1. **The v5 findings.** For each finding of the two v5 reviews (use the v6 response table as the list, and check that it leaves none out): resolved, partly resolved or not resolved? One line each, with the v6 line that answers it.
2. **Accuracy.** Is every quotation, line citation and statement about the plan, about N1 v12, about an owner decision and about the source correct? List each that is not.
3. **Authority.** Does each lettered item hold exactly one decision whose "yes" adopts exactly the value given, with the consequence of "no" stated? Is anything presented as decided that is the lead's choice?
4. **The rules that are new or replaced in v6.** Check each for soundness, completeness, undefined cases and any way it could be applied after seeing an outcome it governs:
   - the canary-first item: two conditions (ratified before the canary's first coded word, judged once and irrevocably; production registers the source and assets the canary ran), what happens when the second fails (a replacement pilot on the production source, the reason recorded first, the canary's reading always reported beside it), and its fixed "no";
   - the "no" convention as its own item, with the table that names, per item, the first registration that waits for a redraft;
   - the pilot table after the change that a pilot with no further word stays pending and the floor then has no value;
   - the canary read by the plan's precedence for this amendment's purposes, with N1.5 governing only N1's attempt accounting;
   - the runtime-terms item: alternative B (two registered sets: the canary's $90 and 21,600 s; one production set of $400 and 43,200 s, the source accepting exactly those two), with A and C as written alternatives; the claim that the canary can remain CHORUS's pilot although its registered limits differ; the conformance check that the terms reach nothing the model reads; and whether the admission bounds argued in N1 for a 21,600 s run can be applied unchanged to a 43,200 s run;
   - "an attempt whose final authoritative floor assessment remains failed";
   - Kids First: its bundle exists in the repository under `notes/matched_cborg_2026-09-13/kids_first/` but the source manifest declares no such project, so it fails the inputs test (check both facts at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`).
5. **Consistency.** Do the 37 items agree with the body text and with each other? Does the sequence of events work end to end, including the count of first attempts? Is the list of engineering prerequisites complete and consistent wherever it appears?
6. Anything a careful owner would misread or be surprised by later.

## Output

Grade strictly. P1 is for a defect that would make a ratified rule unsound, contradictory or choosable after an outcome. Do not raise as a finding the absence of a branch the draft deliberately removed, unless its absence leaves a case with no rule at all.

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then the table for question 1, then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title`, graded P1 (blocks ratification), P2 (should be fixed before ratification) or P3 (wording), each with the draft's line number, the evidence and the smallest fix. State what you checked and what you did not. Use no at-sign characters. Compute any hash in the command that prints it.
