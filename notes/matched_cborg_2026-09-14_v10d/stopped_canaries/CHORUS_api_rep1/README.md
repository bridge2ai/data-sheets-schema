# CHORUS API v10d — stopped at the cumulative attempt cap

This attempt ran from `2026-09-14T08:54:49Z` to
`2026-09-14T09:10:30Z` on reviewed, tested commit
`9a8212489c9184b41a75876af1f6751f6a362735`, registration
`bae17a6d500794231a6b12c83ef5e6540a26bdf29feae83006e83652791c9993`.
It is **incomplete and rejected for expansion**.

Full generation and audit both completed with the registered model and
`end_turn`, costing an estimated $1.879520 and $0.727300. Their total is
**$2.606820**. Reconciliation needed a **$2.828425** reservation for 56,270
counted input tokens (with the registered conservative margin) and its
96,000-token output ceiling. Only **$2.393180** remained under the $5 attempt
cap. The guard refused that request and stopped; no reconciliation, report
or cheaper subsequent request was sent. A reservation is an admission bound,
not a prediction of actual spending.

[audit.json](audit.json) records the two settled response identities and
usage, the unpaid denial and hashes of all **26 unchanged original files**.
Original outputs, requests, responses and denial evidence are preserved in
the frozen worktree and an ignored local archive in the main workspace.
Registration, launch review, billing checkpoint and rejection are retained
locally too. Raw payloads and machine-bound launch files are not published.
Public hashes do not establish independent inspection of those originals.

The initial full/core files have not completed reconciliation and final
reporting/provenance. They are not an accepted final pair, and final-source
acceptance did not run. #1782 and #1783 remain open. Do not repair these
measured originals or reuse them as a completed production replicate.

All **12** requests in the additional allocation are settled, totaling an
estimated **$8.928906**, leaving **$191.071094** of $200. There are no
unresolved charges. The frozen checkpoint also retains this stop event.
The [new cap proposal](../../../matched_cborg_budget_continuation_2026-09-14.md)
requires explicit user approval before any new paid attempt. Related issues:
#1789 for CHORUS admission and #1781 for Kids First.
