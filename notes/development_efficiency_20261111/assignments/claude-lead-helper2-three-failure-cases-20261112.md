# Assignment to Codex helper 2: the three failure cases that did not pass, then a second set of run limits on a separate branch

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This follows `claude-lead-helper2-helper-cache-home-20261112.md`; do it after that one's repair and re-canary.

## Standing

Your failure-case results are read: 14 of 17 passed, each at the point the test intends. The offline timing of the binary's hash (about 0.2 s for 323,702,464 bytes, binary not executed) is noted. Three cases did not pass. Amendment N1.4(A) item 6 needs all seventeen.

## Case A, two ids: `test_v2_saved_failure_rechecks_runtime_and_cleanup_after_successful_read[keep-awake.json]` and `[runtime-observation.json]`

Both stopped before reservation with `ValueError: subscription observation is stale or future-dated`, so neither reached the readback it tests. Your note says the saved log shows a wall-time discrepancy. The lead's network was down for part of that period and the machine may have slept.

1. Establish the cause from saved evidence: the observation's recorded time, the time admission read it, the registered age limit, and what the wall clock and the monotonic clock say in the log. Say whether the host slept or paused, if the log can show it.
2. Rerun the two ids alone. If they pass, record both outcomes and keep the failed logs; do not relabel the first run.
3. Whether or not they pass: say whether the fixture's observation can go stale merely because the test is slow on a loaded host (how many seconds of slack it has against the 1200-second age and the 90-second margin), and if the slack is small, propose the smallest fixture change that keeps the freshness check real. Do not weaken the production check.

## Case B, one id: `test_saved_readback_revalidates_consumed_v2_approvals[review-independent v2 approval]`

It expected the refusal `review independence, roles or decision differs` and got `coded word differs from exact review/registration/probe bytes`. The refusal happened, with another reason first.

1. Find which commit changed the first refusal: run or read the same id at the candidate's base before your bundle version 3 commit (`cf53497ae`) and after it.
2. Decide which is right against amendment N1, draft v12, and the bundle's design: if the launch word binds the review's bytes, a changed review decision is correctly refused at the word first, and the test's expected reason is what has to change, to the reason a reader of the saved failure will actually see, with a second assertion that the review check itself still refuses when the word is made consistent with the changed review. If instead the order of checks was changed by accident, restore it.
3. One commit, on your branch `codex/native-launch-sequence-20261112` or the cache branch, whichever carries the code concerned; say which.

## Case C, prepared on a separate local branch: a second registered set of run limits (a decision is pending)

Added by the lead before this file was delivered. Do it after cases A and B.

**Why.** The source fixes two backstops for every non-synthetic run: the guard (`native_u4b_runtime.py`, `_profile`: `result['budget_guard_usd'] != '90'` refuses; the binary is started with `--max-budget-usd 90`, decision D110) and the deadline (`native_u4b_policy.py`: `N1_DEADLINE_SECONDS = 21600`, checked by `validate_runtime_terms`). Both were chosen for the CHORUS canary. The analysis plan's own estimates per run at API prices (`notes/generic_v10_analysis_plan.md` at main, lines 369 to 374) are about $37 for CHORUS, $83 for CM4AI, $96 for VOICE_PEDIATRIC, $105 for VOICE and $162 for AI_READI. On that proxy a $90 guard is expected to stop three of the five production projects. The lead is asking the owner to choose; the lead's recommendation is two registered sets of limits.

**Prepare it, to be taken or dropped,** on a local branch `codex/native-production-run-limits-20261112` from the candidate's head:

1. The source accepts exactly two registered sets and nothing else: the canary's (guard `"90"`, deadline 21,600 s) and one production set (guard `"400"`, deadline 43,200 s). A registration declares one of them whole; a mixed pair refuses. No project is named in code, and nothing infers the set from the project, the bundle or the label: the registration says which, and the review bundle and the owner's word already pin the registration.
2. Find every place that assumes the single value: the two validators above, the 86,400 s ceiling in `native_shared_runtime_values.py`, the launch argument construction, the freshness and margin arithmetic that speaks of "a run of up to 21,600 s", the keep-awake acquisition, the attempt supervisor's timers, the synthetic profile, the registration builder and its tests, and any document that records the terms (runtime declaration, registration, review bundle, owner terms). List each with its line and say whether it changes. If a registered document's kind or version must change, stop there and propose.
3. Say what a 12-hour run changes operationally that a 6-hour run does not: usage windows crossed, the validity of the subscription observation at dispatch against a longer run, keep-awake, and anything in amendment N1, draft v12, that states 6 hours as a property of every native run and would then be wrong for production runs.
4. Tests: each set accepted whole; a mixed pair, a third value and a missing value refused; the canary's set unchanged in every derived identity (show the canary's registration bytes are identical before and after the change for the same inputs).

The values $400 and 43,200 s are the lead's proposal and may change with the owner's answer: keep them in one place.

## Bounds

As before. Offline; no provider, model or native-binary execution; nothing pushed; no GitHub write; protected files equal to main on every branch.

## Handoff

Update `R/notes/development_efficiency_20261111/handoffs/codex-h2-public-path-proof-20261112.md` and its JSON: the cause of case A with the times, the rerun's result, the slack figure; case B's commit and what changed; the count of the seventeen that now pass; and for case C the branch head, the list of places that assumed one value, and whether any registered document's version has to move.
