# R4/R6 follow-up: separate read-only review, 2026-10-29

Scope: `e8e033bf6..3997aff96`, production, tests, launcher, proof script and
README. This was a separate adversarial pass after the implementation commits;
the review commands only read the diff and files. No additional finding.

- **R4:** the two-line production change modifies only the reported-kind set
  for a selected instrument other than 5. Finding creation, its payload,
  instrument authority, coverage and the v5 branch are unchanged. The
  pre-existing version validator limits callers to versions 3, 4 and 5.
- **Causality:** the identical five tests ran before and after the source fix.
  All three historical-instrument cases failed specifically at the gated-count
  assertion before the fix; both v5 controls passed. All five then passed.
  The v3 test copies the reviewer's corpus example to pytest scratch, prepends
  the marker there, and exercises the real CLI and its strict exit status.
  It checks 115/129 coverage. The v4 cases use validated registration selection
  and a snapshot; both strict and canary findings floors are asserted.
- **R6:** every invocation extracts the exact A13 commit with `git archive`
  under `$TMPDIR`, then verifies seven measured source files against git.
  The CHORUS inputs come from pinned local commit `5457b71b4`, including the
  second saved result for 10-20a. The one-record canaries use the same launcher
  and persistence path as the full replay, and run again on every invocation.
  The full proof compares fresh base/head bytes and checks the committed
  historical hashes. It no longer consumes a prior review's temporary tree,
  JSON baselines or bare clone. An ignore-independent search of the proof
  script confirmed that the old temporary-directory reference is absent.
- **Boundaries:** no production changes address R1–R3 or R5. R2 qualifies the
  README's worker-lifetime claim. The existing R6 routing-worker omission is
  retained in `issue_r6_unpinned_regex_worker.md`; the protected pin inventory
  remains unchanged. GitHub filing and PR publication are deferred by the
  explicit offline/no-gh instruction.

The selected acceptance run and the completed inertness outputs are recorded
separately in `validation.json`; this source review does not substitute for
either execution check or for an independent human merge decision.

Supplemental R6 portability review found the macOS TMPDIR spelling discrepancy
described in `issue_r6_tmpdir_spelling.md`. It was corrected before either
CHORUS probe ran. The assertion checks actual import identity before changing
its displayed path spelling. The corpus and report probes are unchanged, and
their completed/in-flight measurements remain valid.

The final read-only pass also inspected the follow-up validation helper and
completed ledgers: 899 passed / 19 skipped, no timing retries, all four
inertness comparisons equal, no protected-path changes, and no further finding.
