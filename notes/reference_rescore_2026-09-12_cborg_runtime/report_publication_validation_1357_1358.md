# Publication and CI repair validation — #1357, #1358, #1359

Round 20 reproduced two reporting failures after all measurements had completed: persistent disk-full errors defeated byte-write rollback, and blank qualifications removed manuscript warnings. The following repair changes reporting and CI only. It makes no model calls and does not alter any measured input, definition, prompt, registration, receipt or score.

The renderer routes only the four report destinations into a temporary staging directory. Manifest and receipt reads retain their original locations. Every required qualification is checked as a nonblank string before rendering. The unchanged frozen reporter can therefore generate raw intermediate summaries only inside staging; all four final files are fully qualified before any published path is replaced.

Publication uses the existing condition lock. It hard-links the previous reports as backups, then replaces completed files by rename. Failures restore original inodes by rename, without content writes to the failed storage. Destinations enter the recovery list before replacement so an interruption immediately after a successful rename is covered. If the filesystem also refuses recovery, the backups remain on disk and the error reports their location. This does not promise an atomic four-file snapshot to concurrent readers or recovery after arbitrary filesystem corruption.

Validation:

- **293 focused tests passed with two parallel pytest workers**, including the runner, audit, CBORG adapter, scheduler, deadline and validator-status suites, plus 45 reporting/publication checks. Two existing dateutil deprecation warnings were reported.
- Public-command regressions retain all eight qualifications and reject missing, mismatched, empty, whitespace-only and null narrative/semantic warnings. Empty or whitespace-only cost, permission, deadline and measured-code warnings are also refused. All previous report bytes remain intact on refusal.
- Persistent ENOSPC at early and late staging writes leaves every published report unchanged. Real-filesystem tests demonstrate publication after content writes are disabled, recovery from each partial-publication position using original inodes, interruption immediately after rename, backup-creation failure, and retention of all backups when rollback renames also fail.
- The actual public `report` command completed successfully. `results.json` is identical to the preceding qualified output except for `reported_at`; all three Markdown reports are byte-identical. The entire **981-file measurement inventory** retains its hashes.
- Python 3.9 syntax parsing and `git diff --check` passed for the changed source and tests.

The preceding commit's CI run [34730104720](https://github.com/bridge2ai/data-sheets-schema/actions/runs/34730104720) reported seven preamble-verification failures while 3,660 tests passed. Both CI lanes used shallow checkouts, omitting the previous agent definitions needed to establish the strict check-echo discriminator. Under #1359, both lanes now request full Git history; the production verifier remains unchanged.

A local reproduction used two tiny repositories containing the actual previous and current public rubric definitions. A depth-one clone correctly refused both challenges. After a local `fetch --unshallow`, both generated preambles exactly matched the frozen manifest. No remote network or model calls were made. See [the reproduction result](ci_history_validation_1359.json).

The manifest, scheduler registration, original 56 accepted Writes, 259 prior evaluations and 63-session accounting remain unchanged. Nine Q19 qualifications, both execution boundaries, source-bound narrative qualifications, all 56 timestamp bindings and two unpriced interruptions remain in every applicable report. A new independent review and CI must pass before merge.
