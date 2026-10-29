# Independent review record: Wave7 #5212 / #5162 fixture repairs

The orchestrator (`/root`) independently read the implementation diff from the
original tested head `fc3417be63b55c579c48df13fb54ae33437a3977` through
`67d9024aca93c24432b7f0f65a3c1d7a313995ec` before post-fix validation.

The reviewer approved the F1/F3 changes: both omission identity and chunk roster
come from the public selected-wire exporter; the form fixture explicitly starts
fresh accounting before creating outputs. Existing assertions are preserved.
The reviewer also verified that production, protected files and `tests/conftest.py`
are unchanged across that diff. This is a bounded code review, not a claim that
the full composed branch has passed its suite.

For F2, `/root/wave4_a23_review` independently inspected the failed trace and all
three counterfactual helpers. The orchestrator approved this **design**, pending
the actual implementation diff and focused validation: each helper captures only
the specification's previously observed monitor head, restores it with its owned
baseline files after each case's assertions, and leaves append observation active
during the case. No trusted head may be recomputed from mutable disk. Negative
cases must exclude stale `resume journal head:` refusals; the missing-core-index
case must distinguish portable-reader success from API latch refusal.

Parent-control and post-fix results, final reviewed heads, and the remaining
publication/launch limits belong in the integration report. No GitHub review,
push, merge, provider call or scientific acceptance is implied by this record.

At 2026-10-29 06:44 UTC the orchestrator also approved the actual F2 diff in
`tests/test_shared_generation_runtime.py` and
`tests/test_shared_generation_completed_replay.py`: per-spec checkpoint
restoration follows assertions and file restoration; other monitor keys remain
untouched; negative assertions exclude stale-head refusals; and portable-reader
success remains distinct from API index refusal. Production and conftest files
are unchanged, and `git diff --check` passed. Focused validation follows this
review; no post-fix test result is asserted here.

The targeted run then disproved the newly added blanket core-row refusal:
deterministic core entries have no usage ID and are not delivered-snapshot
latches. The orchestrator independently confirmed the production policy and
approved correcting the test hypothesis; the failed run and correction are
retained in the issue-ready record. `/root/wave4_a23_review` independently reviewed
the actual correction at `fc0552e9ec873d77da501e435d22b8818cb8535a` against
`503f9c0d5`: it proves a unique unlatched core row and a one-row removal, restores
the original API-positive check alongside portable readback, and preserves
latched-snapshot/whole-index refusal, no-call/no-write traps, stale-head exclusions
and saved monitor restoration. No blocker was found for targeted rerun; no
production edit was involved.
