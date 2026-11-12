# Native WP1 diagnostic handoff

Prepared by the lead on 2026-11-10 UTC. This handoff becomes active when the
lead explicitly dispatches it after reviewing the final U3-M report. Until
then, native Codex retains its current U3-M assignment and amended gating.

## Objective and scope

Implement and measure only WP1 of
`native_latency_implementation_plan_2026-11-10_v3.md` (SHA-256
`fbe0bd80d622576bc4c5305e1a7ef7de857ced28f9a3a8016035b7bde79e3467`).
Compare the legacy consumer observer against a monitoring observer on equal
completed work. This measures relative observer cost; it is not a comparison
of live native and API generation.

Use the existing owned native branch and worktree after U3-M has stopped and
restored its private configuration. Freeze fresh source, interpreter, helper
and composition identities for this diagnostic; do not reuse an interim
U3-M manifest as though it covered changed test/helper bytes. Preserve all
earlier evidence and report current collection counts rather than copying
historical counts from the plan.

Changes are limited to the named test observer, diagnostic/canary tests and
their measurement/validation helpers. Do not change production verification,
cache semantics, schema/prompt/scanner bytes, freshness windows, clocks,
protected packet files, one-use guarantees or public-completion counters.
No provider/native executable, account, push, merge or GitHub operation.

## Implementation checks from the read-only readiness pass

Paths and line positions below were inspected at the U3-M source current during
monitoring. Recheck them at the final source identity before editing.

1. `tests/utils/native_shared_consumer_scope.py:30` matches filename basename
   plus code name, records requested existing locals, appends before raising,
   prioritizes `forbid=True` over `refuse`, and restores the prior profile hook.
   Preserve that complete behavior. The metrics observer's repository-root
   filter is narrower and must not silently replace the consumer matcher.
2. Extend `tests/test_native_u3k_profile.py:31` to compare both implementations.
   Existing coverage of dynamically compiled code at line 51 proves the metrics
   observer, not consumer-observer equivalence. Exercise real verified loading
   through `loaded_consumer`, reloaded code, forbidden entries, injected
   refusals, recorded arguments and exception ordering.
3. Verify callback-frame identity before reading locals. Cover repeated scope
   entry and a previously disabled non-target code object becoming a target
   in a subsequent scope. Disabled monitoring events must not hide later calls.
4. The metrics Recorder reserves a free monitoring slot from 3/4. The second
   observer must not replace or release its slot. Cover occupied IDs,
   initialization failure, normal/refusal cleanup and subsequent reuse; verify
   the Recorder still works afterward.
5. Both comparison arms use control profiling. Keep the forced-cProfile CPU
   witness separate: the legacy observer expects the previous hook to be
   callable. Keep the legacy default behavior available to existing tests.
6. Add an explicit consumer-observer arm selector. The current runner's
   control/cProfile selection does not select the two proposed consumer arms.
   Use the same diagnostic node, fixture construction and one worker for both.
   Correct the diagnostic's existing "no launch_case profile observer" wording
   when it is wrapped by the selected observer.
7. Preserve the exact pre-reservation stop and verify no attempt or evidence
   directory is created. Compare identical completed prefixes if freshness
   causes the arms to diverge. Report later work/outcomes separately and check
   for unfinished metrics rows/stacks after observer exceptions.
8. Enforce the actual bounds explicitly: the old selector's 3290-second outer
   timeout does not implement WP1's limits. Use at most 60 seconds for the
   equivalence canary and 900 seconds per arm, without modifying production
   deadlines. Record the measured interpreter; the package's Python 3.9 floor
   does not imply that every interpreter supports this experimental observer.

## Execution and stopping point

Run the equivalence canary first. Only if it passes, run the two serial bounded
arms with fresh labels and unchanged correctness checks. Coordinate a quiet
local measurement window with the lead. Do not start failure-path cohorts,
once-only public completion tests, full CI or later work packages.

Stop on an equivalence, source/origin, cleanup or tool-ID failure and retain the
failed evidence. Otherwise report matched-prefix wall/CPU measurements,
reached boundaries, outcomes and exact identities. Do not extrapolate a total
generation speedup from a pre-reservation measurement. Restore any private
configuration byte-for-byte, commit only the scoped local changes, append one
STATUS handoff, and stop for independent review.
