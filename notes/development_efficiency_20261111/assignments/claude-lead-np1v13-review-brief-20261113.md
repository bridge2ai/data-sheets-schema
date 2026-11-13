# Review brief: analysis plan amendment NP1 (native production cells), draft v13, confirmation pass

This is a read-only adversarial review. You did not write this draft. Do not edit it, commit, push or write to GitHub. Run no test, model or provider call. Do not touch anything under `d4d-executions/launch-a21`.

## What to review

The file is `notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md` at commit `668d62c431e9aaee93fc7ba3744f777b26797da3` (file sha256 `db0905e5fcb9c14e13b13e772cc184bb7bce95d9617eee3faf222dd70a5a3869`), on branch `claude/native-production-amendment-np1-20261112`. Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 668d62c431e9aaee93fc7ba3744f777b26797da3:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`.

It is a new amendment that stands beside the ratified analysis plan. It plans the production cells for the native agentic arm. It has 45 lettered items that the owner answers one by one. Item (aj) is retired, and item (as) is an open owner question.

The structure has held for four rounds:
- one reference run;
- a gate that compares registration pins;
- frozen code during production;
- the canary as a shakedown under two limit sets.

Drafts v12 and v13 answer the two reviews of v11 with precision fixes. **This round is a confirmation pass.** Raise defects in what changed since v11 and in how the v11 findings were answered. Raise a P1 anywhere.

- Draft v11 is commit `890ee25c567e328f9d9c6feac3ffb9053511a781`. See the changes with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 890ee25c567e328f9d9c6feac3ffb9053511a781 668d62c431e9aaee93fc7ba3744f777b26797da3`. Draft v12 is `56f0c060e02e752d2ca1284fc4e091c219e0230c`.
- The two reviews of v11 are in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`:
  - `np1v11_890ee25c_codex_review_2026-11-13.md` (4 findings);
  - `np1v11_890ee25c_claude_review_2026-11-13.md` (9 findings).

  They were filed as issues 6130 to 6138, keyed to the Claude review's numbering, with the Codex findings appended.
- The lead's rulings for v12 and v13 are in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md`. Read the entries "Added 2026-11-13T06:48:36Z" and "Added 2026-11-13T07:14:52Z". The draft quotes them, and the quotations must be exact.

## Sources to check it against

- **The ratified plan:** `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`.
- **Amendment N1**, ratified as draft v12 (owner decision D138): `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`.
- **The native source** the new statements cite:
  - At `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`, read with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112 show 5d63d0a77dc43c064cfc2b376355f98009dd5b6e:<path>`.
  - At the candidate `7b851213f3492144cfd5b83d6bbd9a8a040e9132`, read the same way.

  Check the statements marked "(audit)" yourself.

## Questions

1. **The v11 findings.** For each of the 13 findings of the two v11 reviews, is it resolved, partly resolved or not resolved? Give one line each, with the draft line that answers it.
2. **What v12 and v13 changed.** Is each change sound and complete? Is it consistent with the rest of the draft? Could it be applied after seeing an outcome it governs? In particular, check:
   - the holds while a defect or an unknown stop is classified, and the withdrawal of registrations that were made but not launched;
   - the gate results under the stated precedence: a wrong or missing floor basis, a valid different floor value, a changed interpreter on version 2 (`python_sha256`) and on version 3 (the manifest pin as a shortcut pin), and a moved checkout, interpreter path or commit;
   - the per-run paths of the files each registration writes for itself (the floor's registration, the selection, the environment manifest), with their content still judged as the precedence says;
   - the packets for other projects and for a registered floor before the reference pilot's launch words, and the probe rules (i) and (ii);
   - the exploratory test, now scoped to strata after the reference run, and the rule for later strata;
   - `source_commit` as must-equal, the frozen HEAD, and restoration;
   - the prerequisite states moved out of the ratified text. Does any rule still need a state that is now gone?
3. **Accuracy.** Is every new quotation, line citation and statement about the plan, N1, STATUS and the source correct? List each that is not.
4. **Contradictions.** Did v12 or v13 introduce any contradiction, or a case with no rule?

## Output

Grade strictly. P1 is for a defect that would make a ratified rule unsound or contradictory, or let a rule be chosen after the outcome it governs.

Start the report with the verdict: ratifiable as is, ratifiable after listed fixes, or not ratifiable. Then give the table for question 1. Then give the findings, headed `### P1-1: title`, `### P2-1: title` and `### P3-1: title`. P1 blocks ratification, P2 should be fixed before ratification, and P3 is wording. Give each finding the draft's line number, the evidence and the smallest fix. State what you checked and what you did not. Use no at-sign characters. Compute any hash in the command that prints it.
