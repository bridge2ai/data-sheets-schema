# Fitness-cache decision for #919 — 2026-09-11

Keep the existing slot-fitness judgements under their recorded instrument.
They will not be reused as shared-instrument reference measurements for v7
and v8. The user's reference rescore covers both **semantic rubric agents**
on 24 full records; those are separate instruments from `evidence_score`'s
slot-fitness judge.

An ignored-file-inclusive audit of the repository's evaluation and judgement
cache directories found 1,441 stored fitness judgements across the four
project caches. Every entry records schema digest
`34d24ff30fb6ad0f10d82af09ddc1fba`, not either of the later generation
digests in #919. This is why generation provenance must not be substituted
for an evaluation's actual cache context. At the current Dataset digest
`a91bad8b8eaf7c34b147ff5970474342`, the real cache loader accepts zero and
rejects all 1,441 on the schema dimension. No API client was initialized and
no new judgement was requested. The companion JSON pins every cache file,
entry count, context, and rejection count.

Any future common-instrument fitness comparison requires fresh judgements
for both cohorts under one explicitly pinned model, system prompt, schema
specification and propagation policy, with its own budget and canary. It is
not a free cache replay, and old fitness numbers must not be compared to the
new semantic rubric percentages as if they were one measurement. Existing
cache bytes remain unchanged. This resolves #919's requested decision without
claiming a fitness rescore occurred.
