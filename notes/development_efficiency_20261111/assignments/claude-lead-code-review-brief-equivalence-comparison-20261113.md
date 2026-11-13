# Review brief: the native equivalence comparison script and its data file (read-only)

Read-only adversarial code review. You wrote none of this code. Do not edit, commit, push or write to GitHub; run no test, no model or provider call, and nothing that executes the Claude Code binary. Read with `git -C <worktree> show` and `git -C <worktree> diff` only; you may read the saved demonstration outputs under `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-equivalence-20261112/`.

## What it is for

The production amendment for the native arm (NP1, draft v8: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show 756c92b317bbcb3545526c2ea9c6d18bb0cab73d:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`, item (al) and the section it summarizes) fixes one reference run per stratum. Every later registration must be **equal** to it by this script, or it does not belong to the stratum; "cannot decide" is a hold. Nobody judges a difference after seeing a result: that is the script's whole purpose. A first review of draft v8 (`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/np1v8_756c92b3_codex_review_2026-11-13.md`, findings P1-1, P1-2 and P2-1) states three requirements the script must meet; read them.

## What to review

Worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-equivalence-comparison-20261112`, commit `e82c36abdb2b25a55b71c2e67552edc7a7c1f8b5` (first implementation `e7b256cc2`, base `6561dac3c3af50cbfce1ba3c8b6ad21d9cd4b834`): `scripts/native_equivalence_compare.py` and `scripts/native_equivalence_compare.json`, and their tests. The author's account: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h3-equivalence-comparison-20261112.md`.

## Questions

1. **Can it say "equal" when what the model reads, or an acceptance rule, differs?** Look for: a permitted location broader than an identity value; a normalization applied by pattern; a dependent hash accepted without recomputation; an artifact or helper output the model reads that is not captured; a rule-bearing object outside the inventory (the inventory is every package module-level object plus captured controller sources plus package data files: is anything that decides acceptance, rendering, helper feedback or selection outside it, for example a non-package script, a `.claude` command or agent file, or a prompt asset read at run time?); a dynamic import; a difference that only appears on inputs other than the fixed CHORUS replay (the v8 review's P1-2).
2. **Can it say "not equal" or "cannot decide" where the amendment needs "equal"?** In particular: the pending-to-registered floor transition between a pilot and a production cell (the v8 review's P1-1: the receipt policy's floor appears in helper output, stage requests and the final result); registration-specific command guidance in the system prompt (P2-1); a project's own inputs; and the author's note that the input adapter pins every candidate test file, so that any change to a test file holds every comparison. For each, say what the script does now and the smallest change that gives the amendment's intended answer without opening a gap.
3. **Is the result reproducible and tamper-evident?** The policy is "frozen" from a candidate baseline: what stops the policy from being regenerated after a pilot's result, and what binds a comparison result to the exact script, data file, trees and inputs it used? Is "cannot decide" ever turned into "equal"?
4. **Containment.** It runs two source trees' production functions in one process with audit hooks. Can code from one tree affect the other's outputs (shared module state, caches, the dependency site directory)? Is anything written outside the output directory?
5. Do the six demonstrations and the 21 tests assert the properties, or only exit codes?

## Output

Verdict first: fit for the amendment's purpose as is, after listed fixes, or not. Then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title` (P1: the script can return "equal" for a registration that differs in what the model reads or in an acceptance rule, or can never return "equal" for a production cell the amendment intends to admit; P2: should be fixed before the script is pinned; P3: minor), each with file and line, a concrete scenario and the smallest fix. Then what you checked and what you did not. Use no at-sign characters.
