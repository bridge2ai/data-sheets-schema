# CHORUS API v10h — stopped at audit format validation

The explicitly approved attempt stopped on 2026-09-15 at 01:06:50 UTC for
**$2.485500**, below its $13.34 cap. Both requests settled. The additional
allocation has spent **$21.822599 across 29 requests**, leaving **$178.177401**.
All **24 original files** and their verified backup remain unchanged. No
reconciliation, report, later canary, evaluator or production job ran.

The complete audit response is valid JSON with 16 findings, but `summary`
is an object; the existing contract requires a non-empty string. The gate
correctly stopped. The prompt omitted that type, and the diagnostic
incorrectly suggested prose instead of a record. [#1805](https://github.com/bridge2ai/data-sheets-schema/issues/1805)
clarifies the contract and reports the actual shape failure. The original
response is not coerced or repaired. The generated full/core pair is an
unfinished, pre-reconciliation artifact and has no scientific acceptance.
The auditor's 16 entries remain unadjudicated model judgments.

The [format and accounting review](audit.json) retains every original hash
and both request-level usage, price and admission records. Costs were
independently recomputed. It is not a semantic score or source review.

Separately, [#1804](https://github.com/bridge2ai/data-sheets-schema/issues/1804)
removes the native templates' unsupported zero-temperature assertion. Four
retained offline native request bodies omit temperature; they do not prove
the provider's effective setting or any future scientific request's effort.
Renderer 7 records unknown temperature and retains prior renderer replay.
No native scientific generation has run in this sequence.

Another paid whole attempt requires explicit approval, a new condition and
reviewed registration. The completed approval is used. All original v7/v8,
historical v9 and rejected or stopped conditions remain preserved.
