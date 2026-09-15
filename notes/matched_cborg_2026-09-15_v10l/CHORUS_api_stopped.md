# CHORUS API v10l — stopped at the audit evidence gate

The approved attempt started at 18:10:00 UTC on 2026-09-15 and stopped at
18:21:01 after its second generation request. The initial full D4D, derived
core, receipt and audit were produced. Every one of the nine audit findings
omitted the required evidence array. The strict gate recorded nine contract
failures and zero checked assertions, then stopped before reconciliation or
report generation. There is no accepted output or completed final pair.

All **25 original files** are preserved unchanged, bringing the historical
attempt inventory to 362 files. The frozen launch commit is
`37903a5c0b36d8f6c692b9f711144e7d62fecd59`; registration SHA256 is
`4bb2333f8adb69016d63e88b4176fe9d8f0e7e983ef8f8e1ea386631b3f3b3fa`.
The [machine-readable outcome](CHORUS_api_stopped.json) records the artifact
hashes and accounting. The stopped identity must not be resumed or edited into
acceptance. No agentic canary or evaluation has launched.

Both requests have complete usage accounting. Their cost at the registered
rates is **$2.008425**, taking budget-accounted spending to **$31.667238** and
leaving **$168.332762** of the additional $200. No request charge remains
unresolved. The earlier v10k charge remains separately reconciled at the
user-confirmed $0.267175; that confirmation was not reused for this attempt.

Inspection of the actual audit request found two different format instructions.
Its shared protocol required an evidence array on every finding. Its final
phase message still defined a finding as `{severity, record, slot, issue}` and
directed quotations into prose. The response followed that legacy shape.
The final message also referred to a supplied core although this audit request
carried only the full record. These inconsistencies are verified; prompt
wording is not established as the sole cause of the response omission.

[Issue #1834](https://github.com/bridge2ai/data-sheets-schema/issues/1834) tracks
the correction: explicit renderer-10 contracts in the API's final audit,
reconciliation, report and report-recheck instructions, and the same contracts
in the native instruction. Renderer 9 and older defaults remain reproducible.
The evidence checker and its refusal behavior remain in force. A subsequent
attempt requires a distinct registration and budget calculation; it cannot
reuse the stopped attempt's launch receipt.

After the correction passes review and CI, continue the
[matched generation and evaluation plan](../matched_cborg_reconciled_retry_2026-09-15.md).
API acceptance still gates native CHORUS, then both Kids First canaries and
the separately registered evaluation styles and repeat ratings.
