# CHORUS API v10m stopped outcome — 2026-09-15

The registered CHORUS API canary stopped at 19:29:02 UTC after three requests.
It began at 19:13:07 UTC on reviewed commit
`5fb6210279a8d09195b37b8d21c7d272a1be34f2`, under registration SHA256
`6ffee52ce4a7ea2d855098c6aaff71880b7e27b3b2aa654ca360c727d5d44129`.
The audit and reconciliation were completed, but the relationship evidence
gate refused the result before final core derivation and reporting.

All 26 declared quotation assertions passed. The audit requested deletion of
`/instances/2/data_substrate`, and the reconciled full record removed it while
preserving the instance type, count and topic. The v1 checker could not follow
the anonymous indexed ancestor: `indexed relationship member or ancestor has
no usable stable identity`. This is the general schema-object limitation
tracked in [#1839](https://github.com/bridge2ai/data-sheets-schema/issues/1839).
It must be resolved without using list position as identity or inventing an ID.

No final report or accepted full/core pair was produced. The full output is a
reconciled candidate; the core still represents the original full record.
Neither is admitted to evaluation or manuscript comparison. The run remains
stopped; a later checker replay cannot turn it into a completed generation.
Original audit judgments still need independent source review, including
whether partial availability and interleaved table cells were characterized
too broadly. Literal evidence checks do not decide those questions.

| Request | Settled charge |
| --- | ---: |
| Full generation | $1.579565 |
| Audit | $0.911170 |
| Reconciliation | $0.407659 |
| Attempt total | **$2.898394** |

All three responses have complete usage accounting. The cumulative ledger
contains 45 settled charges totaling **$34.565632**, leaving **$165.434368**
from the additional $200. There are no unresolved charges. The earlier
interrupted request remains separately reconciled at the user-confirmed
$0.267175, without fabricating final token usage.

Thirty new original files were copied with SHA256 verification to the local
immutable attempt archive. All 362 prior original files remain unchanged,
bringing the preserved total to 392. Request, response, admission, progress,
result and snapshot evidence remain alongside the stopped outputs. Raw model
payloads and machine-bound executable registrations remain local.

The proposed correction introduces opt-in evidence protocol/checker v2 and
renderer 11, preserving v1 and prior rendering bytes. It matches anonymous
ancestors by unique unchanged structured content, checks each declared
removal, and validates action preconditions before a reconciliation request.
A read-only engineering replay on these originals checks all 26 assertions
and the removal without findings. That replay is not source acceptance,
regeneration, a completed report, or permission to resume this stopped run.

Next: finish independent review and required CI for #1839, then register any
new attempt as a separate condition with updated accounting, explicit caps,
fresh review and the existing sequential gates. No further paid request is
running. CHORUS native, Kids First and evaluation remain gated on accepted
generation originals. Preserve both arms and all planned evaluation styles;
keep disputed historical judgments separate from new matched comparisons.
