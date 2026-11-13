# Review brief: analysis plan amendment NP1 (native production cells), draft v3

Read-only adversarial review. You did not write this draft. Do not edit it, do not commit, push or write to GitHub, and run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to review

`notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md` at commit `27429678f37d5df92e2055fe5fa8e13e7717f871` (file sha256 `2160b96c6a98bd13636547b7395f41bcac7b016ba17d6f93614af4526f07c9c8`), branch `claude/native-production-amendment-np1-20261112`. Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 27429678f37d5df92e2055fe5fa8e13e7717f871:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`.

It is a new amendment that stands beside the ratified analysis plan. It plans production cells for the native agentic arm, which the plan leaves unplanned, after the owner directed that the native arm is the main result and chose the scope. It has 32 lettered items, (a) to (af), that the owner answers one by one.

- Draft v2 is commit `c515160aee3330429a46e4819b885e2d974adee5`. The diff to v3: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff c515160aee3330429a46e4819b885e2d974adee5 27429678f37d5df92e2055fe5fa8e13e7717f871`.
- The two reviews of v2, in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`: `np1v2_c515160a_codex_review_2026-11-12.md` (7 findings) and `np1v2_c515160a_claude_review_2026-11-12.md` (22 findings). They were filed as issues 5940 to 5964; four findings overlap between the two reports.
- Two source audits that v3 relies on: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/np1_floor_source_audit_codex_2026-11-12.md` (the receipt floor) and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-native-eligibility-audit-20261112.md` (what the source saves for the eligibility rule). Issue 5939 is the pending-floor defect.

## Sources to check it against

- **The ratified plan:** `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1` (2,559 lines; the draft cites it by line number). Read every passage the draft cites, and the sections it says carry over unchanged.
- **Amendment N1** (the native canary's amendment), which NP1 builds on, draft v12: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`. It is unratified.
- **Owner decisions and their exact words:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (use `grep -n` for `D07`, `D22`, `D25`, `D35`, `D36`, `D37`, `D56`, `D64`, `D65`, `D71`, `D91`, `D105`, `D107`, `D109`, `D113`, `D131`, `D134`, `D135`). The plan's own decision table also records several of them.
- **The native source it cites,** at commit `5d63d0a77dc43c064cfc2b376355f98009dd5b6e` (in the worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112`; read with `git -C <that worktree> show 5d63d0a77dc43c064cfc2b376355f98009dd5b6e:<path>`): `src/data_sheets_schema/native_shared_receipts.py`, `native_shared_contract.py`, `native_shared_phase.py`, `native_shared_render.py`, `native_shared_gates.py`, `receipts.py`, `cli/receipts.py`, `native_attempt_supervisor.py`, and `src/download/prompts/native_shared_receipt_policy_v1.md`. The draft marks statements about lines its author did not read as "(audit)": check those against the source yourself.

## Questions

1. **The v2 findings.** For each finding of the two v2 reviews (use the v3 response table as the list, and check that it leaves none out): resolved, partly resolved or not resolved in v3? One line each, with the v3 line that answers it.
2. **Accuracy.** Is every quotation, line citation and statement about the plan, about N1 v12, about an owner decision and about the source correct? List each one that is not, with the line in the draft and the line in the source.
3. **Authority.** Does the draft claim more for any owner decision than its recorded words support? Is anything presented as decided that is the lead's choice, or missing its `[proposed]` mark or its lettered item? Does each lettered item hold exactly one decision whose "yes" adopts exactly the value given, and is the consequence of "no" stated wherever it is not obvious?
4. **The new rules of v3.** Check each for soundness, completeness and unintended consequences:
   - the eligibility rule restated on the end state the source saves, item (l), and the limits it names;
   - K_native fixed once at the floor's registration, item (j), with fit settled at the event the draft calls NP1b;
   - the floor basis, item (p): the at-receipt basis of D37, with the final-record basis as the "no" branch; and what is said about a registered floor being visible to the model while a pending one is not;
   - the pending-floor defect as a prerequisite of any pilot;
   - the per-project runtime terms, item (x): the cost-ratio proxy, the factor of 2 and the flag at twice the canary's deadline;
   - the remedy when the canary's word comes before this amendment is ratified, item (af);
   - the rule-level pilot rejection, item (g), and the reading of D113 it rests on;
   - production on shared-v1 with later BC1 parity as a new stratum, item (aa).
5. **Prospectiveness.** The plan requires that no rule is chosen after an outcome it governs. Does anything in the draft depend on, or could it have been shaped by, a v10 quality value? Can any party choose a floor, a scope or a count after seeing an outcome it governs?
6. **Consistency and gaps.** Does the order of events work end to end? Are the attempt limits, cause classes and stop-loss coherent with the plan and with N1 v12? Do the 32 items agree with the body text and with each other? What does the draft leave undefined that a registration would need?
7. Anything a careful owner would misread or be surprised by later.

## Output

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then the table for question 1, then findings numbered and graded P1 (blocks ratification), P2 (should be fixed before ratification) or P3 (wording), each with the draft's line number, the evidence and the smallest fix. Head each finding with a line of the form `### P1-1: title`, `### P2-3: title`, `### P3-2: title`. State what you checked and what you did not. Use no at-sign characters. Compute any hash in the command that prints it.
