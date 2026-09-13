# Interrupted report recovery validation — #1360

The round-21 failure sequence was reproduced with temporary synthetic files: the first report replacement succeeds, the second fails with ENOSPC, and cancellation interrupts rollback. The original implementation could then delete the only remaining backup of the first report.

Publication now shares an explicit cleanup state with its context. Cleanup is safe before publication begins; it becomes unsafe before the first replacement and stays unsafe until publication or complete rollback is confirmed. Rollback catches cancellation as well as ordinary filesystem errors, continues recovering the remaining reports, and reports failed recovery with its retained backup path. An unexpected exception while recovery remains unconfirmed also preserves that directory.

The exact ENOSPC-then-cancellation regression covers both KeyboardInterrupt and SystemExit immediately after the first rollback rename. It verifies the location-bearing error and that every original report is either restored or still available in a retained backup. Ordinary successful publication and fully completed rollback still remove staging.

Validation on the corrected code: **47 reporting/publication tests passed with two parallel workers** in 6.88 seconds. These include all public qualification guards and the real-filesystem persistent-write, partial-publication, interruption and backup-retention checks. The broader 293-test runner/control suite passed before this recovery-only correction. Python 3.9 syntax parsing and `git diff --check` passed. All **981 inventoried measurement files** retain their hashes; this repair does not change any report content, scoring input, instrument, registration, receipt, accepted evaluation or prior score.

The [round-21 review](final_review_round21.md) remains blocked on the now-addressed finding. A new independent review and CI must pass before merge. No model calls were made for this repair.
