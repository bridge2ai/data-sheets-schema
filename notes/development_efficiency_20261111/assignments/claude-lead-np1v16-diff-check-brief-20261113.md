# Check brief: amendment NP1, draft v16, a diff-only check before the owner's ballot

Read-only. Do not edit, commit, push or write to GitHub. Run no test, model or provider call.

**What to check.** In `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema`, the diff `git diff d44fe8283a73150541a66f06cc1244caa4bf88ea dcbbdc417dfd6c0f92712bcb38f565742cd794ef -- notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`, from draft v15 to draft v16. The v16 file's sha256 is `fe441027d8709ab35f456e23ed7ba3faddbc99f8ad75faf7b8361e8492ee43c6`.

**What it should do.** Apply exactly the five rulings in the coordination record `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md`, entry "Added 2026-11-13T09:10:05Z". Those rulings answer three findings of the final reviews of v15:
- `np1v15_d44fe828_codex_review_2026-11-13.md`, P2-1;
- `np1v15_d44fe828_claude_review_2026-11-13.md`, P2-1 and P3-1.

Both reviews are in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`.

**Questions.**
1. Is each of the five rulings applied, completely and only as stated? Give one line each, with the draft line.
2. Does the diff introduce any contradiction with the rest of v16, or leave a case with no rule? Look hardest at these:
   - the launch hold, now from the end of every attempt until its acceptance or the classification of its stop or rejection;
   - the moved-checkout results on version 3;
   - the environment rule that replaces the fallback.
3. Are the new quotations of STATUS exact?

**Output.** Give the verdict first: "applied as ruled" or "defects found". Then list any defects, each with the line, the evidence and the smallest fix. Raise nothing outside the diff unless it contradicts the diff. Use no at-sign characters. Compute any hash in the command that prints it.
