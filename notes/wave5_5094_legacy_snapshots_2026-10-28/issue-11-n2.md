# Local issue draft 11 / N2: ambiguous legacy audit inventory raises during resume

Source: Issue 11/N2 in the lead's `2026-10-28-issues-from-pr5094-review.md`. This identifier is a draft label, not a newly filed GitHub issue number. No GitHub write was performed.

The carry-less `api_runner.report_audit_totals_block` in #5094's round-two head `3f202bd3e320672fed8a49b0c4b82ef7e124a43f` propagates `UsageLedgerError` from `snapshot_store.read_latest` for a legitimate legacy record with two audit snapshots but no phase/generation ownership. `_current_report_audit_totals` then cannot preserve a previously checked result.

The committed VOICE v4 record (`2026-08-13_claude-opus-5-api-generic-v4_rep1`) reproduces this. Its first audit has 21 findings, second audit and report have 18; the saved inventory cannot identify a current audit. The retained baseline canary at `dfd0b9d4b0932cf6990971db6d70d39109e404af` records the exact exception: `portable phase snapshots have ambiguous generation ownership; restore their index`.

Acceptance: catch only snapshot `UsageLedgerError` in saved-audit resolution, return an ordinary unchecked block with its reason, preserve any checked prior, and keep explicit live carry and strict owner checks intact. Do not choose an audit by filename order or change historical records.

Locally addressed by `94484d0a9fab8c47f54ffe732b5393fe0c502bbe`; tested at `de56f9dd7efc9009704dec2e24cc3378dbb24f32`. The identical real-record canary now passes, as does the 100-case focused suite. Baseline failure and fixed evidence are retained under `validation/` in this packet. Publication and issue-state decisions remain with the lead.
