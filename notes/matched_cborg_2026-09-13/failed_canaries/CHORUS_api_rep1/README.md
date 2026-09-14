# CHORUS API canary — rejected, 2026-09-13

The first v10 generation canary ran through CBORG at commit
`4a084a55b19dde93e6f7acf4ab397268cd68e50c` using registration
`0fbe4d0853b0fbdcef6f4788532420800428aecd069ae8db48fa5a3485495a12`.
It failed full/core schema validation and is excluded from production results.
No later generation or evaluator canary is authorized by this attempt.

Five requests settled at an estimated **$3.291465**, leaving **$196.708535**
of the additional $200 allocation. These are catalogue-based usage estimates,
not a reconciled invoice. No charge is pending or unknown. A repair's
$2.62586250 reservation was refused with $2.129795 left in the $5 attempt
allowance. The runner caught the exception and the controller then admitted
a $0.421260 report request. Issue [#1770](https://github.com/bridge2ai/data-sheets-schema/issues/1770)
tracks that failure to stop; neither monetary cap was exceeded.

The digest omitted nested string-list cardinality. The output uses scalars
for nested external resources, annotation tools and existing-use examples,
where the schemas require lists. Issue [#1771](https://github.com/bridge2ai/data-sheets-schema/issues/1771)
tracks the missing guidance. Its contribution is plausible; a corrected
digest cannot guarantee a future model output will validate.

The full/core pair is consistent and has no duplicate mapping keys. The final
report check found no findings among 25 claims. Receipts mark all eight chunks
reviewed, but only 117 of 118 snippets verify. The mismatched snippet for
`known_limitations[4].limitation_description` starts with
`Current Released Dataset`, which is absent from its cited chunk `c006`.
These checks do not establish semantic support for every generated value.
No formal semantic rating or acceptance was issued.

`audit.json` inventories local byte-for-byte copies of all 22 output artifacts, original
request/response/admission receipts, registration, billing and measured
controller/digest code. Original local paths remain untouched. Only this
summary and the hash inventory are versioned; the raw archive payload remains
local. Its location is outside the corpus so corpus discovery does not count
those copies as accepted D4Ds. All 458 registered pins and 3,241 historical artifacts
verified unchanged after the attempt.

Next: resolve and review #1770/#1771; register a new condition and unused
paths, carrying the spent amount forward; obtain passing checks for that
registration before a retry. Native execution also requires fixes for
[#1768](https://github.com/bridge2ai/data-sheets-schema/issues/1768) and
[#1769](https://github.com/bridge2ai/data-sheets-schema/issues/1769).
