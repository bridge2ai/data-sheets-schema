# Review brief: analysis plan amendment NP1, draft v15, final confirmation pass

This review is read-only and adversarial. You did not write this draft. Do not edit it, commit, push or write to GitHub. Run no test, model or provider call, and touch nothing under `d4d-executions/launch-a21`.

## What to review

The file is `notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md` at commit `d44fe8283a73150541a66f06cc1244caa4bf88ea` (file sha256 `15dbe8ccaaf2d0210f898d626bb92478488b961d236f821d5a33684b3115da8c`), on branch `claude/native-production-amendment-np1-20261112`. Read it with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show d44fe8283a73150541a66f06cc1244caa4bf88ea:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`.

The amendment plans the native agentic arm's production cells beside the ratified analysis plan. It has 45 lettered items, which the owner will answer one by one. Item (aj) is retired, and item (as) is an open owner question.

This is the **final confirmation pass** before the owner's ballot. The structure has held for five rounds:
- one reference run;
- a gate that compares registration pins;
- frozen code during production;
- the canary as a shakedown under two limit sets.

Draft v14 applied the reviewers' own smallest fixes to the two reviews of v13, with a few lead rulings. Draft v15 adds three small lead rulings.

- Draft v13 is commit `668d62c431e9aaee93fc7ba3744f777b26797da3`. See the changes with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 668d62c431e9aaee93fc7ba3744f777b26797da3 d44fe8283a73150541a66f06cc1244caa4bf88ea`. Draft v14 is `bb3eaa8b5ffe2c17b3d16fb21634accf9104648b`.
- The two reviews of v13 are in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`:
  - `np1v13_668d62c4_codex_review_2026-11-13.md` (1 P1);
  - `np1v13_668d62c4_claude_review_2026-11-13.md` (2 P2 and 8 P3).

  They were filed as issues 6173 to 6183.
- The lead's rulings are in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md`, in the entries "Added 2026-11-13T08:28:36Z" and later. The draft quotes them, and the quotations must be exact.

Check against these sources:
- the ratified plan, `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`;
- amendment N1, ratified as draft v12, at `c289eed19e37e227e04dd5e0c4fc077da54184aa`;
- the native source at `5d63d0a77dc43c064cfc2b376355f98009dd5b6e` and at the candidate `7b851213f3492144cfd5b83d6bbd9a8a040e9132`. Read both through `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112 show <commit>:<path>`.

## Questions

1. **The v13 findings.** For each of the 11 findings, is it resolved, partly resolved or not resolved? Give one line each, citing the draft line that answers it.
2. **What v14 and v15 changed.** Is any change unsound or contradictory? Can any be applied after seeing the outcome it governs? Does any leave a case with no rule? Look hardest at these:
   - the floor list's ending branch, now limited to repairs that need changed must-equal values;
   - the launch hold, which now starts at the stop;
   - the interpreter-upgrade and rebuilt-environment results;
   - the frozen-HEAD conditions, including the end of the freeze, other files, added files, and copying out before a restoring checkout;
   - the bytecode rule in the manifest;
   - the later-stratum test, anchored on the first launch word of the CHORUS reference pilot.
3. **Accuracy.** Is every new quotation, line citation and statement about the plan, N1, STATUS and the source correct?

## Scope and output

Raise a finding only for these:
- a v13 finding not resolved;
- a defect in what changed since v13;
- a P1 anywhere.

Do not raise new wording points unless they cause a contradiction or leave a case with no rule.

Start with the verdict: "ratifiable as is", "ratifiable after listed fixes" or "not ratifiable". Then give the table for question 1. Then give the findings, headed `### P1-1: title`, `### P2-1: title` or `### P3-1: title`, each with the draft's line number, the evidence and the smallest fix. Say what you checked and what you did not. Use no at-sign characters. Compute any hash in the command that prints it.
