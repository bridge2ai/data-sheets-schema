# Assignment to Codex helper 1 (the resumed native-integration session): the scanner pin, then integrating the finished fixes

From the Claude lead, 2026-11-12, after the restart. You keep your worktree `E/codex-native-main-integration-20261112`. Short names are defined in `claude-lead-helper-context-20261112.md` beside this file; its rules apply.

## Standing

- Your G07 handoff is accepted (`handoffs/codex-native-packets-g07-20261112.md`, SHA-256 `da22641d5b13d3b78d076debe5d6a30d02282b2eed1261b04607f5d12e89fd8b`). The lead independently hashed the four post-images and diffed the API post-image against the D127-approved one: two lines, as you reported.
- **The owner has not yet answered** on the API post-image `830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881`. Until the lead tells you otherwise, the four protected files stay equal to main on the branch.
- **Correction to what I told you:** D136 settles the freshness age, 1200 s. The margin is open again: amendment N1 draft v10 proposes 300 s in place of 90 s, and the owner has not answered. Do not change the margin constant yet.
- The agy workers are out of usage. Two fresh Codex helpers take the other lanes: helper 2 has your findings G07-F6, G07-F4 and G07-F5 in its own worktree; helper 3 has the import-origin failures and shard time. Do not do their work.

## Part A: the scanner's authority source pin (your finding G07-F1)

The complete scan exits 2 because `src/data_sheets_schema/native_execution_authority_v2.py` (`b2189db8…5558`) differs from the scanner's pinned source (`bfdb5c86…511a`). 96 scanner tests and 44 retained CI failures hang on it, and no D128 comparison can be made until it is resolved.

1. **Explain the drift.** Which commit moved the authority module's bytes away from the pin, what changed in it, and why the pin did not follow. Say whether the same stale pin was present on `1a137b588604` and on `382f0dfd1ce8`.
2. **Decide what is right:** the scanner's derivation for the new bytes. Read the changed module against what the scanner derives from it. If the derived meaning is unchanged and only the source hash moved, say so and show it. If the meaning changed, say what changed.
3. **Prepare the scanner update** as its own commit on your branch: the smallest change to the scanner's pin or derivation that is correct for the current bytes, with the tests that prove it. No blind pin bump: the commit message states what was verified. The scanner lives under `.claude/skills/d4d-generation-specificity-audit/`; it is not one of the four protected files, but treat it with the same care and keep the change reviewable on its own.
4. **Then produce the complete scan arrays and the D128-form comparison** on the integrated head, in a scratch composition with the four packets applied: exact matches, line relocations, field changes, additions, removals and the violation objects, each itemised, with what D128 already covers and what is new. This is what the owner will be asked to dispose of.
5. Re-run the scanner cohort and report which of the 96 negatives clear.

## Part B: integrate the finished fixes (after Part A's commit exists)

Cherry-pick onto your branch, in this order, and report any conflict instead of resolving it by guesswork:

1. `ddcadcdc2` and `ab07c81fe` from `agy/native-ci-collection-5875-20261112` (test-only: the collection fix for issue 5875 and three host-layout test files).
2. Helper 2's commits, when the lead tells you they are reviewed.

After each cherry-pick run the touched test files.

## Bounds

As in the context file. In addition: no `cpu-monitoring` diagnostic and no private-composition arming beyond what your G07 test runner already does for offline cohorts, with the configuration restored and the restoration recorded as before.

## Deliverables (in `R`)

- `notes/development_efficiency_20261111/handoffs/codex-h1-scanner-pin-20261112.json` and `.md`: the answer first (is the scan complete now, what the comparison shows, what the owner has to dispose of), then tables made from the JSON by a script under `scripts/adhoc/`.
- A short owner-facing section in the `.md`, in plain language: what the scanner checks, what differs from the comparison the owner approved in D128, and what approving it means.
- Write a first version when Part A step 3 is committed, and update it as parts finish.
