# R9b validator-repair report refresh

Refs #5157 / #5210. Local implementation on
`codex/5157-r9b-fix-20261027`, based on
`0674193f6d4e1b42a6f3afe6d5475c8635cfbdf2`. Offline only; no provider calls,
outbound GitHub actions, protected-file edits or changes to existing runs.

An internal validator repair changes the final full/core files after the report
was generated. Previously the report refresh could fail or be interrupted before
the repaired hashes were saved. Resume then treated that internal write as
external drift and tried to restart a full-generation phase already sealed by
receipt completion. Merely saving the new hashes would suppress that restart
but lose the outstanding report-refresh obligation when validation was clean.

The selected shared-generation v1/v2 route now records an obligation in the
generation usage ledger and mirrors its immutable checkpoint in progress before
counting or requesting the refresh. The checkpoint binds repaired full/core
SHA-256 and MD5, the preceding report SHA-256, audit SHA-256, completed phases,
generation/input identity and retained repair history. These are process-recovery
checkpoints using fsynced file contents and atomic replacement; no stronger
power-loss ordering or cryptographic authenticity claim is made.

| State | Resume behavior |
| --- | --- |
| `pending` | Verify the complete saved checkpoint and exact repaired bytes; refresh only the report, without repeating the accepted repair or sealed phases. |
| `in_flight` | Call admission occurred but accepted completion is missing. Refuse additional calls and preserve delivery/accounting evidence. |
| `accepted` | Preserve repair history and completed accounting; perform the ordinary final checks. A later valid report regate remains allowed. |

`pending` becomes `in_flight` in the existing `begin_call` transaction, after
context counting and before the request. An interruption before entering
`_regenerate_report` therefore remains safely resumable. A report-refresh count
refusal retains the existing terminal evidence refusal and makes no later call.
Missing/malformed progress, an erased mirror, changed audit or repaired bytes,
and an ambiguous paid response refuse before further generation.

Acceptance follows the real report write and existing source-review checks.
The final report, receipt, lineage, schema and provenance gates are retained.
A clean resume refreshes exactly once. Accepted refresh does not waive validation:
a completed run that remains invalid retains the existing bounded repair-on-resume
behavior. Historical unregistered renderers retain their `refreshed: false`
fallback; they now save the repaired artifact hashes before attempting refresh.
The removal-repair controller remains responsible for its separate protocol.

Both original R9b failure cases from
`scripts/adhoc/review_5157_repair_progress_cases_20261026.py` in the retained
cross-review branch are folded into
`tests/test_download/test_api_runner.py::TestValidatorRepairRefreshCheckpoint`.
The strengthened cases also check exact-once refresh, unchanged original full
snapshot/receipt/generation, preservation of old usage IDs and repair history,
13 corrupted-evidence variants, post-delivery interruption, accepted completion
interruption with and without a later report regate, and a later invalid-run repair.

Validation is run through
`scripts/adhoc/validate_r9b_repair_refresh_20261027.py`, adapted from the retained
E3x source-isolation helper. It requires a clean committed head and `-S -P -B`,
does not execute editable-install `.pth` files, verifies actual project/test
module origins, and captures source inventories before/after plus installed
distribution metadata. That metadata is not a dependency-byte attestation.
External logs, JUnit and fresh fixture outputs are retained; test timings are
functional evidence, not idle-host benchmarks.

Validation results will be recorded after the frozen checks finish. This work
does not establish scientific acceptance or authorize a live generation campaign.
