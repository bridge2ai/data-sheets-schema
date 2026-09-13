# Public reporting repair validation — #1356

The round-19 reviewer reproduced a successful public `report` command replacing qualified results with raw summaries. The repair was made after all 56 ratings completed, with no new model calls and no scoring or instrument changes.

The adapter now dispatches `audit` and `report` to the dated completion helpers. Public collection actions are refused, and the scheduler permits only plan inspection for this completed condition. The exact measured adapter and scheduler remain in `registrations/report_dispatch_before_1356/`, alongside the pre-repair reports and audit. The original manifest and scheduler registration hashes are unchanged; audit checks explicitly resolve the historical code files to their verified archives. File digests continue to hash actual bytes.

Validation on the repaired working tree:

- **267 focused tests passed** across `test_cborg_completed_reporting.py`, the CBORG adapter, scheduler, deadline and validator-status suites, and the original reference runner and audit suites. One existing dateutil deprecation warning was reported.
- The public report regression invokes the qualified renderer with the real retained evidence and intercepts the four report outputs in memory. It verifies all eight qualification banners and structured metadata, refuses missing or mismatched qualifications, and restores all four prior reports after a failure following the raw intermediate write. No on-disk report is changed by these tests.
- Archive tests reject modified measured bytes or a different manifest borrowing the historical code binding. Public collection commands cannot start new attempts for this completed condition. The historical worker signal test uses an unfinished temporary condition and still verifies signal unblocking before preflight.
- Both actual public commands completed successfully offline: `python scripts/reference_rescore_cborg.py audit`, then `python scripts/reference_rescore_cborg.py report`. The audit is verified; the renderer reports 56 original measurements and all 24 Q19 inspections, including nine qualified totals.
- All **972 files** in the pre-repair measurement inventory retain their hashes, resolving the original adapter path explicitly to its measured archive. The expanded inventory contains **981 files**. All 259 prior evaluations and 56 accepted original outputs remain unchanged.
- The manifest remains `c6a637ddc84b3ced1db9ee18fdeff63a90e25c5ffb981a23be3fd25707308ee2`; the scheduler registration remains `b0a02133382c51cd8ebaa480917bd1c8920f3c7cfece11deea0392c6d9f0cbad`. Accounting remains 63 evaluator sessions, seven exclusions, two unpriced interruptions and a known terminal CLI subtotal of $161.39939450. Full expenditure remains unknown.
- Python 3.9 syntax parsing passed for the changed adapter, scheduler, completion helpers and test modules. `git diff --check` passed.

The [round-19 review](final_review_round19.md) remains blocked on the now-addressed finding. A separate independent review and CI must pass on the repaired commit before merge. This validation does not certify semantic gold scores, underlying model weights or the unpriced provider charges.
