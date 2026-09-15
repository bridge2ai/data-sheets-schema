# CHORUS API v10i — rejected after independent review

The single approved attempt completed for **$4.069292** across five settled
CBORG requests. All **38 original files** are preserved. Schema, full/core
pair, exact core derivation and live provenance checks passed, but the
unchanged audit/report prevent acceptance:

- #1807: accurate omitted-temperature metadata is treated as an unresolved
  zero-temperature defect. The saved full/core headers agree with the actual
  request, which carries no temperature parameter.
- #1808: five fields absent before and after are reported as removed. The
  original v7 checker returned no findings; a separate v8 recomputation
  detects all five without replacing that stored v7 measurement.
- #1808: one source-backed addition is incorrectly included in a grouped
  claim of relocation from the original record.

The original audit summary is a non-empty string and its 12 findings
(5 medium, 7 low) are counted correctly. Those counts describe model
judgments, including the disputed metadata judgment; they do not endorse it.
Receipts verify all 110 snippets and cover 8/8 chunks, with 51/91 receiptable
final values carrying a receipt. Coverage gaps and changed values remain
visible and were also inspected against the complete frozen sources.

No native/Kids First canary or evaluator launched. The $200 allocation has
spent **$25.891891**, leaving **$174.108109**. No charge is unresolved and no
whole-attempt retry is authorized by this result. Costs are token-price
estimates. See [preservation and accounting metadata](audit.json).
