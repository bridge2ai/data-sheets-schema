# Review brief: analysis plan amendment NP1 (native production cells), draft v11

Read-only adversarial review. You did not write this draft. Do not edit it, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to review

`notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md` at commit `890ee25c567e328f9d9c6feac3ffb9053511a781` (file sha256 `c734220397d15307c42154ab8b8fc8e76344fef1549950b190443bdffba0276f`), branch `claude/native-production-amendment-np1-20261112`. Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 890ee25c567e328f9d9c6feac3ffb9053511a781:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`.

It is a new amendment that stands beside the ratified analysis plan. It plans production cells for the native agentic arm. It has 45 lettered items that the owner answers one by one; item (aj) is retired and item (as), whether the canary registers on the version 3 documents, is new. The structure (one reference run, a gate of registration pins, frozen code during production, the canary as a shakedown under two limit sets) has held for three rounds; v11 answers the two v10 reviews with precision fixes to the gate and to the end of the stratum.

- Draft v10 is commit `2f5c66797e8d304d1fcda6d0007ac501f3a27d92`. The diff to v11: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 2f5c66797e8d304d1fcda6d0007ac501f3a27d92 890ee25c567e328f9d9c6feac3ffb9053511a781`.
- The two reviews of v10, in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`: `np1v10_2f5c6679_codex_review_2026-11-13.md` (7 findings) and `np1v10_2f5c6679_claude_review_2026-11-13.md` (15 findings). They were filed as issues 6112 to 6129.
- Source audits the draft relies on: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/np1_floor_source_audit_codex_2026-11-12.md` and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-native-eligibility-audit-20261112.md`.
- **Owner decisions of 2026-11-12 (coordination record, D138 to D145).** Draft v7 records them. Check its quotations of them word for word against STATUS.md, including the owner's three verbatim lines and the lead's reading, which must be marked as the lead's.
- Facts for context: a helper measured the five declared projects' inputs (bundle bytes and chunks: CHORUS 35,920 and 8; VOICE_PEDIATRIC 206,008 and 13; CM4AI 320,799 and 28; VOICE 376,446 and 22; AI_READI 430,393 and 25), and Kids First has no entry, bundle or sources in the source manifest. Issues 5939, 5966, 5967 and 5989 to 5995 are defects of the native route, in various states of repair; the draft lists them as prerequisites with states "per the lead's record", which you need not verify.

## Sources to check it against

- **The ratified plan:** `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`. Read every passage the draft cites.
- **Amendment N1**, draft v12: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`. It is unratified.
- **Owner decisions and their exact words:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (`grep -n` for the decision numbers the draft cites).
- **The native source it cites,** at commit `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`, read with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112 show 5d63d0a77dc43c064cfc2b376355f98009dd5b6e:<path>`. Check statements marked "(audit)" against the source yourself.

## Questions

1. **The v10 findings.** For each finding of the two v10 reviews (use the v11 response table as the list, and check that it leaves none out): resolved, partly resolved or not resolved? One line each, with the v11 line that answers it.
2. **Accuracy.** Is every quotation, line citation and statement about the plan, about N1 v12, about an owner decision and about the source correct? List each that is not.
3. **Authority.** Does each lettered item hold exactly one decision whose "yes" adopts exactly the value given, with the consequence of "no" stated? Is anything presented as decided that is the lead's choice?
4. **The rules that are new or replaced in v11.** Check each for soundness, completeness, undefined cases and any way it could be applied after seeing an outcome it governs:
   - the gate's early shortcut, limited to valid must-equal pins, and its precedence between "not equal" and "cannot decide";
   - item (ar): defects found before any reservation; the boundary fixed when a qualifying defect is filed, with the reviewers' record of whether its repair needs changed must-equal bytes; one scope for an end; restoring host state is not a repair;
   - the gate run on the reference pilot's own packet, another project's and a registered-floor packet before each of its launch words, in addition to the demonstration before the canary, and the demonstration's case list and leaf inventory;
   - the environment manifest's contract (version 3 documents, regeneration and verification of installed files at preparation and dispatch), its deadline, and item (as) on whether the canary registers on version 3;
   - the checkout and interpreter paths held identical across the stratum, and what a move means;
   - the coded word binding the gate's result through the reviews' recorded hashes.
5. **Consistency.** Do the lettered items agree with the body text and with each other? Does the sequence of events work end to end, including the count of first attempts? Is the list of engineering prerequisites complete and consistent wherever it appears?
6. Anything a careful owner would misread or be surprised by later.

## Output

Grade strictly. P1 is for a defect that would make a ratified rule unsound, contradictory or choosable after an outcome. Do not raise as a finding the absence of a branch the draft deliberately removed, unless its absence leaves a case with no rule at all.

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then the table for question 1, then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title`, graded P1 (blocks ratification), P2 (should be fixed before ratification) or P3 (wording), each with the draft's line number, the evidence and the smallest fix. State what you checked and what you did not. Use no at-sign characters. Compute any hash in the command that prints it.
