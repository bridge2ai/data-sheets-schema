# Review brief: helper 2's admission bound and pre-dispatch timing, and the controller pin rotation, on the native candidate at e52db7e82

Read-only review. Do not edit, commit, push or write to GitHub. Run no test, no model or provider call, no native binary, no probe. Do not run anything inside a live worktree; read Git objects (`git show`, `git diff`) in the repository below. Compute any hash in the command that prints it. Use no at-sign characters in your report.

## Where

Repository: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema` (read its objects only; do not switch, reset or touch its working tree).

The candidate for draft PR 5968 is commit `e52db7e82856755c04eac8eb36a7f0abe2b6d5f8` (branch `codex/native-main-integration-20261112`). Its previous reviewed state is `fc00ce6544b002dc0e726cb196cb5939c8283092`. Since then it gained four commits:

1. `bca7924c9`: merge of helper 2's host-power branch at `9faacc252`. Its new code since the last review is `git diff a2db8ab6b 9faacc252` (18 files, about 825 lines added): a separate admission bound (`native_admission_timer.py`), pre-dispatch timing observation (`native_pre_dispatch_timing.py`), and changes to `native_execution_orchestration.py`, `native_shared_execution_orchestration.py`, `native_shared_registration_orchestration.py`, `native_subscription_capture.py` and `notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py`, plus tests. Everything before `a2db8ab6b` on that branch was reviewed earlier and is out of scope, except where the new code changes how it behaves.
2. `51593ed84`: merge of the run-limits branch at `6c62fa27f`. New since the last review: `git diff 0df39c077 6c62fa27f` (documentation and its generator only).
3. `52f342fcf`: merge of the helper-cache branch at `9d743c877` (two runner scripts under `scripts/adhoc/`).
4. `e52db7e82`: the controller pin rotation and the specificity scanner's matching pin (`git show e52db7e82`).

Helper 2's own account of the work, which is a claim to check, not evidence: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-pins-admission-20261113.md`.

## The rules the code must keep

- The attempt deadline is 21,600 seconds of wall time from dispatch (amendment N1, issue 6170). Its origin is taken just before the child process starts, after the power recheck, on a clock that counts sleep.
- A capture may be at most 1,200 seconds old at reservation, with a 300-second pre-reservation margin. Neither may be relaxed, re-timestamped or worked around.
- The new admission bound is 900 seconds, from entry to `execute_child` to the dispatch origin. It must spend none of the child's 900, 21,600 or 43,200 seconds. When it expires, the child is not dispatched, and the failure is published with its own reason.
- The timing observation is a diagnostic. It must never be read for admission or launch, must not change any pinned or registered bytes, and its failure must not change an outcome.
- The four protected files and guard v1 do not change.

## Questions

1. **Admission bound.** Is it correct and fail-closed? Look at the periodic alarm, the exception that bypasses broad `except Exception` handlers, exclusive signal ownership and its restoration (including on every exit path and in a thread that is not the main thread), and the synchronous check at dispatch. Can an expired bound still dispatch the child? Can a non-expired bound refuse because of the alarm itself, for example an alarm landing inside cleanup, publication or a lock? Is the dispatch origin of the 21,600-second deadline unchanged?
2. **Timing observation.** Where is the `host-pre-dispatch-<registration-sha256>.jsonl` file written? Does any closed file-tree check, file policy, capture census or guard now see an unexpected file? Can its buffering, its disabling on a failed or contended write, or its synchronous I/O change an admission result, a capture's freshness or a reservation? Is it read anywhere that decides anything?
3. **Capture and orchestration changes.** In `native_subscription_capture.py` and the orchestration modules, did any check move, disappear, get weaker or change order? Compare old and new control flow, not only the added lines.
4. **`run_native_canary.py`.** Apart from the timing hooks, does its behaviour change?
5. **Pin rotation.** Recompute the hashes. Do both source manifests' module hashes match the bytes at `e52db7e82` and at their `source_commit`? Do the three pinning constants match the manifests' bytes? Is the scanner change correct: overrides added to the integrated summary, with the base summary left as the earlier contract? Is anything else that pins these files (tests, evidence, other summaries) now stale or wrong? Historical evidence files are not to be restamped.
6. **Tests.** Do the new tests prove what their names claim, or can any pass without exercising the behaviour (vacuous assertions, mocks that replace the unit under test)?
7. **Documentation.** Does `docs/native-run-limits.md` (generated) state the clocks and limits as the code implements them?

## Output

Write your report to the file named in your task. Verdict first: "integrate as is", "integrate after fixes" or "do not integrate". Then each finding as a heading `### P1 — title`, `### P2 — title` or `### P3 — title` (P1: a run could launch, spend or be accepted wrongly, or evidence could be false; P2: a real defect with a bounded effect; P3: clarity, tests, docs). For each finding, give the file and line at `e52db7e82`, the evidence, a concrete failure scenario and the smallest fix. Then say what you checked and what you did not. Raise nothing outside this scope unless the new code makes it worse.
