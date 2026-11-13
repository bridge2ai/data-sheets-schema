# Review brief: analysis plan amendment NP1 (native production cells), draft v9

Read-only adversarial review. You did not write this draft. Do not edit it, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to review

`notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md` at commit `7946decac9f53e6f7edc672a4ad0440467c49381` (file sha256 `87f4731b23026507bc1d72a20ba17034270155cad082e60ead2206d121ccf5f9`), branch `claude/native-production-amendment-np1-20261112`. Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 7946decac9f53e6f7edc672a4ad0440467c49381:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`.

It is a new amendment that stands beside the ratified analysis plan. It plans production cells for the native agentic arm. It has lettered items that the owner answers one by one; item (aj) is retired. Draft v9 makes the stratum's gate a comparison of registration pins in which nothing is executed, keeps the owner's run-limits decision B (two limit sets), so the canary is a diagnostic shakedown and never the reference or a floor input, and gives every prerequisite one deadline.

- Draft v8 is commit `756c92b317bbcb3545526c2ea9c6d18bb0cab73d`. The diff to v9: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 756c92b317bbcb3545526c2ea9c6d18bb0cab73d 7946decac9f53e6f7edc672a4ad0440467c49381`.
- The two reviews of v8, in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`: `np1v8_756c92b3_codex_review_2026-11-13.md` (11 findings) and `np1v8_756c92b3_claude_review_2026-11-13.md` (13 findings). They were filed as issues 6075 to 6092.
- Source audits the draft relies on: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/np1_floor_source_audit_codex_2026-11-12.md` and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-native-eligibility-audit-20261112.md`.
- **Owner decisions of 2026-11-12 (coordination record, D138 to D145).** Draft v7 records them. Check its quotations of them word for word against STATUS.md, including the owner's three verbatim lines and the lead's reading, which must be marked as the lead's.
- Facts for context: a helper measured the five declared projects' inputs (bundle bytes and chunks: CHORUS 35,920 and 8; VOICE_PEDIATRIC 206,008 and 13; CM4AI 320,799 and 28; VOICE 376,446 and 22; AI_READI 430,393 and 25), and Kids First has no entry, bundle or sources in the source manifest. Issues 5939, 5966, 5967 and 5989 to 5995 are defects of the native route, in various states of repair; the draft lists them as prerequisites with states "per the lead's record", which you need not verify.

## Sources to check it against

- **The ratified plan:** `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`. Read every passage the draft cites.
- **Amendment N1**, draft v12: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`. It is unratified.
- **Owner decisions and their exact words:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (`grep -n` for the decision numbers the draft cites).
- **The native source it cites,** at commit `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`, read with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112 show 5d63d0a77dc43c064cfc2b376355f98009dd5b6e:<path>`. Check statements marked "(audit)" against the source yourself.

## Questions

1. **The v8 findings.** For each finding of the two v8 reviews (use the v9 response table as the list, and check that it leaves none out): resolved, partly resolved or not resolved? One line each, with the v9 line that answers it.
2. **Accuracy.** Is every quotation, line citation and statement about the plan, about N1 v12, about an owner decision and about the source correct? List each that is not.
3. **Authority.** Does each lettered item hold exactly one decision whose "yes" adopts exactly the value given, with the consequence of "no" stated? Is anything presented as decided that is the lead's choice?
4. **The rules that are new or replaced in v9.** Check each for soundness, completeness, undefined cases and any way it could be applied after seeing an outcome it governs:
   - the gate (item (al), and (ad)): equal if and only if every pinned file, the binary's sha256, the base system-instructions bytes, the selection-bounds rule and every registered value are byte-identical, except a fixed list of per-run fields; the floor transition validated separately; nothing executed; the gate run before each later launch word is asked for. Is the per-run list exact and safe? Can anything the model reads, or any acceptance rule, differ while the gate says equal? Can the gate fail to say equal for a production cell the amendment intends to admit? Note for the selection bounds: the lead has decided that the stratum's bounds rule is a constant (one set of values for every registration, chosen before the canary from the largest declared input); judge whether the text needs to say so.
   - the consequence that production runs on frozen code: after the reference run any change to a pinned file ends the stratum for later registrations; no diagnostic canary arises inside the stratum.
   - B with the CHORUS reference pilot always run, the canary's reading reported and not a floor input, stated as superseding one clause of D109; and whether an unaccepted canary stopping the reference pilot is the right rule.
   - NP1b's checks run on the reference pilot's exact source and repeated by a dated addendum if that source changes; the floor's registration as its own dated amendment.
   - the bar on native results (item (ao)) with its exception for applying the floor arithmetic and the gate, the recorded reason for every change, and its consequence.
   - the prerequisites with one deadline each, including the power check and the short recorder line before the canary.
   - consequences the owner may not expect, including that the reference's pinned Claude Code binary must be kept with automatic updates off.
5. **Consistency.** Do the lettered items agree with the body text and with each other? Does the sequence of events work end to end, including the count of first attempts? Is the list of engineering prerequisites complete and consistent wherever it appears?
6. Anything a careful owner would misread or be surprised by later.

## Output

Grade strictly. P1 is for a defect that would make a ratified rule unsound, contradictory or choosable after an outcome. Do not raise as a finding the absence of a branch the draft deliberately removed, unless its absence leaves a case with no rule at all.

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then the table for question 1, then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title`, graded P1 (blocks ratification), P2 (should be fixed before ratification) or P3 (wording), each with the draft's line number, the evidence and the smallest fix. State what you checked and what you did not. Use no at-sign characters. Compute any hash in the command that prints it.
