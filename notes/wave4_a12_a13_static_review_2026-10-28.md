# Independent downstream review: #5154 and #5158

Date: 2026-10-28. Read-only static review; no tests, provider calls, GitHub operations or owner-worktree edits. The exact local Git objects, not the transcribed long SHAs in the merge packet, define this review:

| Item | Exact head | Comparison base |
|---|---|---|
| #5154 / A12 | `f58482df84276b3509893455f753f6af068fb321` | `a0e28d8821c69e2d4fe1b75b14e3c2a2140ae4d5` |
| #5158 / A13 | `148c869dde865915221db847b2e89f15f319b365` | `f58482df84276b3509893455f753f6af068fb321` |

The A12 original review, A13 F1 review, D37 saved-result review, stack-round-two review, current production diffs and their tests were read. No fresh passing-test claim is made here. The earlier 74-test and 904-test statements remain attributed historical reports, not this review's measurements.

## One remaining code finding

**F1 — low, #5154: direct registration-builder callers still write draft context before rejecting invalid partition bounds.**

At this head, `scripts/build_api_registrations.py:450–461` calls `build_draft_context(..., write_to_disk=write_to_disk)` before `resolve_audit_limits(...)` at line 510. With valid source/bundle/chunk inputs, no existing context, `synthesize_draft_context=True`, `write_to_disk=True`, and absent or invalid partition bounds, the direct library API creates a context and its directory before raising. The CLI's all-project precheck prevents this on that route; it does not guard library calls. This is the remaining library half of original A12 finding F4.

Move bounds resolution immediately after validating the arm, before any context synthesis. Add a direct-library regression that selects temporary inputs and a new output directory, requests synthesis with invalid bounds, and verifies neither the context nor output directory was created. Valid explicit/profile bounds should still produce the same registration. This is a preparation-side-effect defect, not a provider-admission bypass.

## #5154 integration requirements

- Retain the new #5122 schema-closure/routing-artifact checks and explicit-worktree resource authority while merging the builder changes. A12 predates those fixes.
- A12 intentionally requires partition bounds. The new Wave 4 CHORUS fixtures, unchanged independent review cases, and copied-script CLI commands currently assume the earlier defaults; adapt them with `partition="chorus"` / `--partition chorus`, retaining their actual authority assertions. Cases using another project need explicit synthetic partition bounds. This is test adaptation to the intended public contract.
- The raised shared-generation-1 report/reconcile caps and all report regeneration readout aliases agree in the diff; historical renderers and route clamping remain separate. Registration inference uses the ledger's SHA-verified raw registration. The CHORUS profile is restricted to baseline and the CLI prevalidates all projects before writing. Aggregate output/call allowances are derived; aggregate input remains a separately sized launch requirement.

## #5158 assessment

No new merge-blocking defect was found in the reviewed code. D37 evaluates the phase-1 snapshot's own `with_receipt_at_receipt / receiptable_at_receipt` counters, retaining final-record counters beside the result. Missing snapshot counters and zero eligible leaves fail closed; moved, rewritten, and repeated values no longer decide the floor through the retired D32 attribution heuristic. A basis-less registration retains its prior result shape and calculation.

Saved-result compatibility projects away only jointly absent parser-envelope fields and jointly absent snapshot counter pairs in both saved blocks. Present, incomplete or changed fields still compare against recomputation, and saved result bytes are returned unchanged. The tests include both saved CHORUS fixtures and mutations of counters, receipts and metadata. This supports retaining the compatibility implementation, subject to fresh integrated validation.

Receipt coverage is not semantic source support or final-record completeness. The old instrument-4 wording and any scientific floor applicability decisions stay explicitly documented; the v5 follow-up must retain snapshot counters. Neither a passing floor nor merging this code authorizes a generation run.

## Merge versus launch

Merge #5095 with its reviewed follow-up, then #5154 with F1 addressed and integrated tests, then #5158 with its own integrated receipt suites. Preserve original ancestry through merge commits. The old merge-packet long SHA strings for A12/A13 are inaccurate; use the exact objects above and current remote verification by the orchestrator.

Launch remains a separate decision: registered per-project partitions and input budgets, report admission, bounded carry/context fit, scientific decisions, canary registration and the native recorder timing/real-binary path still require their respective acceptance evidence. These launch prerequisites alone are not defects in the two reviewed code patches.
