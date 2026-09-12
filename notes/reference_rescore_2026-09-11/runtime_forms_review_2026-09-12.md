# Reference runner follow-up — 2026-09-12

The first post-canary attempt, `AI_READI_v7_rep1_r10_rating1`, ran from
08:05:41Z to 08:14:10Z and remains incomplete. The evaluator placed the correct
run label in `metadata.label`, which the schema supports, but the runner only
read the top-level label. Its three attempts to invoke the validator were
denied: two appended an extra shell command, and the third used the absolute
path to its own validator. That last form needed its own permission prefix.
The batch stopped immediately; no other fill rating started.

The retained draft is not a reference score. Its evaluator never successfully
validated it, so host validation or relabeling cannot retroactively accept it.
A fresh independent retry is required. The CLI reports $2.430136 for this
attempt, bringing the two actual evaluator sessions to $4.6505785. Recovery
receipts refer to the original CHORUS call and do not represent additional
model calls or spend.

## Review and fixes

| Issue | Reproduced finding | Resolution |
|---|---|---|
| #1307 | Correct metadata labels and own absolute validator commands were rejected. | Accept matching labels in either supported location, reject conflicts, and allow the evaluator's own absolute validator script. |
| #1308 | Ambiguous current-registration receipts could be mistaken for a new amendment. | Refuse revalidation if any passed receipt already names the current registration. |
| #1309 | The real validator prints the actual output argument; tests had supplied a relative success line for absolute commands. | Bind each tool result to the exact output argument and test all supported forms with real validator stdout. |
| #1310 | Overlapping revalidations could publish duplicate passing receipts; an existing acceptance would still unlock the fill. | Serialize canary execution, recovery and acceptance, and require receipt uniqueness when resuming. |
| #1312 | A validation of an earlier output version could attest a later rewrite. | Scan the complete ordered transcript; potentially mutating calls invalidate old evidence, and validation must follow their completion. |

The first Codex plugin review of `bcba3b083` found #1309 and #1310. Its full
follow-up at `54847f8cf` found #1312; that report is retained in
`runtime_forms_codex_round2.md`. The final review of the #1312 delta at
`1134e5e7e094bdd3333fbe6b5553fb24e6545e7d` approved it with no concrete P1/P2
findings. It checked 201,600 in-memory call/result orderings; its report is
`runtime_forms_codex_round3.md`. The local focused suite passed 101 tests,
including the semantic schemas, real validator path forms, ambiguous receipts,
overlapping recovery/acceptance and failed or absent final revalidation.

The real CHORUS transcript still passes the revised gate, and the real failed
AI_READI transcript remains rejected. Review has not measured repeatability or
independently endorsed every rubric judgment.

## Registered boundary and preserved evidence

The runner-only amendment pins commit
`1134e5e7e094bdd3333fbe6b5553fb24e6545e7d` and manifest SHA256
`ed077e16f93635c571c8cc7992c696880b1e727ff766450ef03e52e43cbfb480`.
The prior manifest and acceptance are preserved under
`registrations/manifest-before-runtime-forms.json` and
`registrations/canary-acceptance-before-runtime-forms.json`.

Both definitions, rubric texts, schemas, all 24 inputs, all 202 prior
evaluations, the 56 planned ratings, model, effort and $5 attempt cap are
unchanged. The complete `job_prompt` source matches the prior pinned runner;
both saved attempt prompts match the current rendering byte for byte.
`runtime_forms_registration.json` records hashes for all twelve pre-existing
attempt files and the new canary receipt and acceptance.

Offline revalidation at 09:00:35Z used the original CHORUS attempt. It preserved
the already published output without opening it for writing and created one
passing receipt under the amended registration. Its SHA256 remains
`017f888bdccf12a04b62917e8fa08c39263cf45a5533fb349ca9eb075335199f`; its score
remains 35/50 (70%), with no excluded items. Acceptance was recorded separately
after reviewing the unchanged evidence and verifying receipt uniqueness. The
evaluator-quoted rubric10 definition remains
`66ad623121272099bf94535ae5be2163a5f5005fe895d2bf2bf04c4f90e34864`.

At this boundary, **1/56 ratings are accepted**, and the failed AI_READI draft
is excluded. No new D4D generation or source download occurred. The reference
cohort remains the existing v7/v8 records; a v9 generation condition is separate.
