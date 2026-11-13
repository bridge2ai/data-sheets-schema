# Review brief: analysis plan amendment NP1 (native production cells), draft v8

Read-only adversarial review. You did not write this draft. Do not edit it, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to review

`notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md` at commit `756c92b317bbcb3545526c2ea9c6d18bb0cab73d` (file sha256 `be640a7e733bd63f9fe350ee657bf65c8cdf9a013f0227d5582e59b2e00f386a`), branch `claude/native-production-amendment-np1-20261112`. Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 756c92b317bbcb3545526c2ea9c6d18bb0cab73d:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`.

It is a new amendment that stands beside the ratified analysis plan. It plans production cells for the native agentic arm. It has 41 lettered items, (a) to (ao), that the owner answers one by one. Seven drafts tried to say when a pilot's reading survives a change of source, and each left a choice someone makes after seeing a reading. Draft v8 removes the choice: there are no re-run pilots and nobody chooses a production commit. The stratum has one reference run, and every later registration is equal to it by a fixed comparison script or does not belong to the stratum. To stay short, v8 replaces some passages by pointers to draft v7; flag any pointer that carries an operative rule rather than history, background or the record of an answered alternative. Judge whether what remains is sound, not whether a removed branch could be restored.

- Draft v7 is commit `814701f1a39df1d733c199797a3d692d3595ac82`. The diff to v8: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 814701f1a39df1d733c199797a3d692d3595ac82 756c92b317bbcb3545526c2ea9c6d18bb0cab73d`.
- The two reviews of v7, in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`: `np1v7_814701f1_codex_review_2026-11-12.md` (6 findings) and `np1v7_814701f1_claude_review_2026-11-12.md` (15 findings). They were filed as issues 6050 to 6064.
- Source audits the draft relies on: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/np1_floor_source_audit_codex_2026-11-12.md` and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-native-eligibility-audit-20261112.md`.
- **Owner decisions of 2026-11-12 (coordination record, D138 to D145).** Draft v7 records them. Check its quotations of them word for word against STATUS.md, including the owner's three verbatim lines and the lead's reading, which must be marked as the lead's.
- Facts for context: a helper measured the five declared projects' inputs (bundle bytes and chunks: CHORUS 35,920 and 8; VOICE_PEDIATRIC 206,008 and 13; CM4AI 320,799 and 28; VOICE 376,446 and 22; AI_READI 430,393 and 25), and Kids First has no entry, bundle or sources in the source manifest. Issues 5939, 5966, 5967 and 5989 to 5995 are defects of the native route, in various states of repair; the draft lists them as prerequisites with states "per the lead's record", which you need not verify.

## Sources to check it against

- **The ratified plan:** `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`. Read every passage the draft cites.
- **Amendment N1**, draft v12: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`. It is unratified.
- **Owner decisions and their exact words:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (`grep -n` for the decision numbers the draft cites).
- **The native source it cites,** at commit `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`, read with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112 show 5d63d0a77dc43c064cfc2b376355f98009dd5b6e:<path>`. Check statements marked "(audit)" against the source yourself.

## Questions

1. **The v7 findings.** For each finding of the two v7 reviews (use the v8 response table as the list, and check that it leaves none out): resolved, partly resolved or not resolved? One line each, with the v8 line that answers it.
2. **Accuracy.** Is every quotation, line citation and statement about the plan, about N1 v12, about an owner decision and about the source correct? List each that is not.
3. **Authority.** Does each lettered item hold exactly one decision whose "yes" adopts exactly the value given, with the consequence of "no" stated? Is anything presented as decided that is the lead's choice?
4. **The rules that are new or replaced in v8.** Check each for soundness, completeness, undefined cases and any way it could be applied after seeing an outcome it governs:
   - the reference run (item (al)): the first accepted CHORUS pilot attempt under the production limit set whose first coded word followed ratification; everything it pins (source, assets, schema closure, registered values, the Claude Code binary's sha256, its system prompt, the selection-bounds policy) is the stratum's reference; under run-limits alternative A this can be N1's canary, under B it is one further CHORUS pilot. Does any path still let someone choose which run is the reference, or end the stratum, after seeing a reading?
   - the comparison: a script with a data file, pinned in the reference run's packet, not yet written; what it must compare (everything the model reads, including helper output on saved inputs, and the rule-bearing objects), exact permitted locations of identity kinds only, dependent hashes recomputed, limits as content, the permission expectation's embedded source hashes left out; three results, with "cannot decide" a hold; any difference in a rule-bearing object is "not equal" with no reviewer judgment. Is this specified well enough for the script to be written and reviewed against it? Are the two declared differences the draft adds (a project's inputs; the coverage-floor field of the receipt-policy registration) safe, or can they hide a difference that matters?
   - no re-run pilots: a change that is not equal ends the stratum for later registrations and needs a prospective amendment; an equal change stays, with D35's diagnostic canary. Check the second-attempt rules (the AI_READI pilot's second attempt only if equal; the CHORUS reference pilot's second attempt may run on a changed source because no reference exists yet) and what happens if the reference pilot ends without acceptance.
   - the bar on using native results, item (ao): its start, its end, what may and may not be cited, and whether it forbids anything the amendment itself requires.
   - delegated starts: production runs answered by D145, item (am); the additional pilots proposed in item (an).
   - Kids First cut from this amendment, item (c), against D135's words ("if in scope").
   - the run-limits item (ab), still marked answered B (D143) with alternative A written out as the lead's open recommendation: is it clear what the owner is asked and what each answer costs?
   - consequences the owner may not expect: an update of the Claude Code binary or its system prompt after the reference run ends the stratum; every equal change costs a separately authorized diagnostic canary.
5. **Consistency.** Do the 41 items agree with the body text and with each other? Does the sequence of events work end to end, including the count of first attempts? Is the list of engineering prerequisites complete and consistent wherever it appears?
6. Anything a careful owner would misread or be surprised by later.

## Output

Grade strictly. P1 is for a defect that would make a ratified rule unsound, contradictory or choosable after an outcome. Do not raise as a finding the absence of a branch the draft deliberately removed, unless its absence leaves a case with no rule at all.

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then the table for question 1, then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title`, graded P1 (blocks ratification), P2 (should be fixed before ratification) or P3 (wording), each with the draft's line number, the evidence and the smallest fix. State what you checked and what you did not. Use no at-sign characters. Compute any hash in the command that prints it.
