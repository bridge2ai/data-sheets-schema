# Assignment to Codex helper 2: fixes from the review of the run-limit and power branches

From the Claude lead, 2026-11-13T07:13:39Z (the file's write time). Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. **Do this after `claude-lead-helper2-6094-timing-20261113.md`**, because the timing table informs item 4.

## The review

An independent Codex CLI review (`E/plans/reviews/native_run_limits_power_31fc33c1_7c1d972a_codex_review_2026-11-13.md`) reached these verdicts:

- Case C (`31fc33c1c`): **integrate after listed fixes**. The pair validator itself is correct.
- Host power (`7c1d972a1`): **integrate after listed fixes**.
- The cache merge already on the candidate (`f7f8e8bff`): **integrate**.

Its six findings are issues #6167 to #6172. Fix them as follows. Use one commit per issue, and name the issue in each commit message.

1. **#6167, power: supplemental evidence must not break failure publication.** Handle observation failures at the start, stage and end boundaries:
   - keep the first launch error;
   - let normal final failure publication run;
   - do not report a committed stage as unpublished because its clock sidecar failed;
   - keep an explicit observation-error diagnostic.

   Add tests for start, stage and end persistence failures, including an end failure after a launch failure that was already caught.
2. **#6168, power: "no sleep" only from adequate evidence.** Return "unknown" when sleep-like records cannot be parsed, or when the log's coverage of the interval cannot be established. Return no-sleep only from a recognized log that covers the interval. Keep clock divergence as separate evidence. Add tests for: timestamped but unrecognized lines, incomplete coverage, DarkWake, and unmatched events.
3. **#6169, Case C: a refusal test that fails without the pair check.** Start from the valid provisional document of the acceptance test and confirm that it passes. Then mutate only the pair, and assert the pair-specific refusal message for values the generic validator accepts.
4. **#6170, the attempt deadline.** The ratified N1 says: "**Deadline** [proposed]: 21,600 s (6 h) of wall time from dispatch." Today the child's timer uses `time.monotonic()` and starts at `execute_child` entry, before launch verification. The lead's ruling is to implement the ratified rule for every registered deadline: canary, production and the synthetic profile's.
   - The origin is the moment of child dispatch.
   - The clock keeps counting while the host sleeps.
   - Say which clock you use on macOS and show from the platform's own documentation or an offline measurement that it counts suspension. Do not rely on the wall-clock time of day, which can be adjusted.
   - Add simulated-sleep tests.

   **Also recheck AC power immediately before dispatch**, with the same fail-closed rule as at sequence start. A laptop unplugged between sequence start and dispatch must not launch.
5. **#6171, docs.** Update `docs/native-run-limits.md` and its generator for the candidate: the 300-second margin (`57bcc018b`) and the recorder's environment specification with its digest (`c577c0eff`).
6. **#6172, public repository.** Committed runners must not carry personal home paths: derive them locally at run time. Replace the real `pmset` excerpt with a synthetic fixture, clearly labelled as such, that keeps the relevant syntax and interval lengths. This includes `scripts/adhoc/run_cache_gaps_tests_20261113.py`, which is already on the candidate: fix it with a follow-up commit on your cache branch.

7. **(Added by the lead at 2026-11-13T07:30:05Z, after your #6094 timing handoff.)** The saved runs did not record the endpoints your timing table needed. Add them as diagnostics that change no runtime decision:
   - the `execute_child` entry;
   - child dispatch;
   - each helper call's start and end, from the controller's side;
   - each turn boundary of the model.

   Write them in a sidecar beside the existing clock sidecars, unless your item 4 already records them. If they can only go into a registered document by changing its kind or version, stop and propose. The lead will arrange the quiet-host run once items 4 and 7 are on the candidate.

## Integration

Merge the published candidate head (`git fetch origin`; at least `f7f8e8bff6ea14006957d8631f66346d91bcddcd`) into each branch with `git merge --no-ff`. Do not rebase. Resolve conflicts and keep the candidate's 300-second margin, recorder digest, trusted-entry and journal-start changes, and helper-cache repairs. Run every touched test file whole, in a CI-like export outside every `d4d-executions` path. Do not run the 30-minute public completion tests; the lead arranges any such run.

## Bounds and handoff

As before: offline only. No real-binary execution, probe, capture or reservation. Nothing pushed, no GitHub write, and the protected files stay unchanged. Write the handoff to `R/notes/development_efficiency_20261111/handoffs/codex-h2-run-limits-power-fixes-20261113.md` with its JSON, answer first. Give the branch heads, one line per issue with its commit and the test that proves it, and which clock you chose for item 4, with your evidence.
