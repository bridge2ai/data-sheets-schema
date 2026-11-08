# U3-D Round 10 integration ledger — 2026-11-08

Offline authority forbids GitHub issue/PR publication. Review findings are
retained here for later filing. No guard or source pin is waived.

The clean starting head was 59d2982cf, a descendant of the brief's c852b3e72,
with Round 9 completion and fixture repairs already recorded. Both descendants
were preserved. C7 was merged first (177ee0da3), then A6 (c41fc684c), both
with `--no-ff`. No manual conflict resolutions were needed. The capture
orchestration overlap retains D's `final_receipts` requirement alongside C's
preloading. The A runner overlap retains D's enclosing-execution-root lookup
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
