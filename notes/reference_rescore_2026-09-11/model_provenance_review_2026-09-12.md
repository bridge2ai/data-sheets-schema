# Model provenance recovery — 2026-09-12

The fill paused at ten accepted ratings after AI_READI v8 rep1 rubric10 placed
`evaluator_model` in schema-supported metadata. Its model name, runtime trace,
complete prompt, instrument hashes, final Write and evaluator-side validation
were valid. The old runner only accepted the declaration inside `model`.
The original incomplete receipt and all candidate bytes remain preserved.

## Review and resolution

#1314 permits either declaration location while attesting every non-null
declaration against the runtime. A selector alias requires explicit successful
CLI `modelUsage` evidence for its canonical model and context window. Conflicts
and arbitrary aliases remain rejected. Generic offline recovery requires the
current accepted canary and unchanged full prompts, instruments, inputs,
schemas, cohort, execution settings and budget. It binds the candidate to the
original last successful Write and requires validation after the final mutation.
Previously published ratings are checked without opening them for writing.

The first Codex plugin review found #1316: a missing output bypassed the guard
against duplicate current-registration receipts. The guard now applies even
when the output is absent. Isolated regression tests reproduced the defect
before the fix and cover both recovery entry points and non-canary ratings.
No real score file was removed. The follow-up review approved code commit
`6edf543f5eede63d984126760d46f6356c9f1d7d` with no blocking P1/P2 findings.
Both reports are retained in `model_provenance_codex_round1.md` and
`model_provenance_codex_round2.md`. The focused suite passed 117 tests.

## Registration and real evidence

The runner-only amendment has manifest SHA256
`5e57093644d0a3485a9d1229a2087c8a5472578b33346213f4df6618686aa4e9`.
The superseded manifest and acceptance are archived under `registrations/`.
Both rubric definitions, all 24 input records, all 202 prior evaluations and
the complete `job_prompt` source remain byte-identical. The registration file
records nineteen retained attempt-file hashes and the existing canary hash.

Offline recovery revalidated the original CHORUS canary, preserving its
35/50 score and bytes. Acceptance was recorded separately after checking its
unique passing receipt, runtime, check-echo and quoted definition SHA256
`66ad623121272099bf94535ae5be2163a5f5005fe895d2bf2bf04c4f90e34864`.
The unchanged AI_READI v8 rep1 rubric10 candidate then passed generic recovery;
its evaluation SHA256 is
`a520c48326b07c23b93de15690c9bddf5630e238ff27e883292a9ee4f6afa232`.
No additional model call or score edit occurred.

The provisional real-evidence audit also checked the ten accepted ratings on
results PR #1313 against the revised validator. All passed. The original
AI_READI v7 draft that never completed evaluator-side validation still fails
and remains excluded. This fix PR carries two current-registration passing
receipts; the other nine previously accepted ratings on #1313 require offline
revalidation under the same amendment before new calls resume.

Repeatability is still unmeasured. These checks establish execution and
instrument provenance, not independent endorsement of every rubric judgment.
No D4D generation or source download occurred.
