# U3-D Round 10 integration ledger — 2026-11-08

Offline authority forbids GitHub issue/PR publication. Review findings are
retained here for later filing. No guard or source pin is waived.

The clean starting head was 59d2982cf, a descendant of the brief's c852b3e72,
with Round 9 completion and fixture repairs already recorded. Both descendants
were preserved. C7 was merged first (177ee0da3), then A6 (c41fc684c), both
with `--no-ff`. No manual conflict resolutions were needed. The capture
orchestration overlap retains D's `final_receipts` requirement alongside C's
preloading. The A runner overlap retains D's quiet-window pause/resume logic
and adopts A6's default scratch/error labels; D's wrapper overrides the scratch
root before execution. Protected files are unchanged.

## R10-1: public lifecycle fixture expires during source reconstruction

At d16664f01 both public synthetic-peer tests reach the real subscription
pre-dispatch check, then refuse their invented observation as stale. The full
lifecycle cohort completes in 837.38 s: three passes, three failures, no errors.
Use an explicit synthetic clock anchored to the invented observation only in
the positive public-launch helper. All real file, binding, freshness and
pre-dispatch predicates still run. Dedicated stale/future tests retain their
own clocks. No real-time acceptance is claimed by this software fixture.

## R10-2: saved-pool fixture leaves insufficient finalization reserve

The 33 MB selected evidence limit leaves only 1 MB beyond the unchanged 32 MB
reserve, insufficient for the merged registration/capture. Increase only the
fixture's selected limit to 64 MB, below the unchanged 512 MB hard ceiling.
The exact-limit success, limit-plus-one refusal, complete-member accounting
and no-ambient-I/O assertions remain unchanged.

The failing baseline is retained in `scratch-native-u3d/round10-lifecycle-1`.
Neither fix is considered validated until its actual assertion runs.

## R10-3: callback deferred utility dependency was not preloaded

The public correction canary at 89f700641 crosses admission and dispatch, then
fails at a real observer callback with `native callback cannot load module
data_sheets_schema.source_metadata`. The guard correctly refuses; R9-4 is not
fully closed by the C7 classifier-only canary. Retained run: round10-public-canary,
1 failure in 1427.01 supervised seconds, source/origin/cleanup checks passing.

Preload the reviewed deferred pure utility dependencies on the main thread and
include them in the existing source-identity checks. A's loader and graph rule
remain unchanged. A focused regression invokes typed source authority and
source-review inventory first in each real historical worker, before computing
an expected result on the main thread. Public execution still needs rechecking.

The initial merge-overlap wording above was corrected on read-only review:
the A-runner overlap is D's quiet-window logic, not its already-shared root lookup.

## R10-4: obsolete R9 diagnostic expects loading from an unadmitted worker

The first complete D/C cohort at 1688dd357 has 721 passes and two failures:
the protected U1 hook and the old R9 blocker diagnostic. C7 now refuses the
unadmitted classifier before loading, with `native callback requires
main-thread preloading at admission`. Update the negative test's name,
description and exact error; preserve its actual historical worker and
ValueError assertion. The independent positive worker cases pass in this run.
