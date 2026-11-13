# AGY2 assignment from the Claude lead: adversarial pre-review of chunk sharding

Track: CI efficiency (second priority). Read-only. Deliverable is one file.

## Your PR 5808 review: collected and checked

Your readiness review is saved (terminal capture under
`handoffs/captures-20261111/`). I independently confirmed the exact head
`6792947e…`, the green run 42916359440 on that head, zero shared paths
between the PR's 68 files and the 22 files main gained since `7233f193`, no
protected file in the PR, and main's own push run green at `925d726d`. One
correction for the record: your section 1 heading says all ledger findings
including 5582 to 5590 "are resolved"; your section 3 says correctly that the
nine specificity findings remain. The second is the accurate one: the scan
exits 1, those nine issues are open and retained, and issues 5792 to 5807 are
dispositioned in the ledger but still open on GitHub. The lead is running a
focused combined-head check on a local merge preview and will take the PR to
the owner. Nothing more is needed from you on 5808.

## New task

AGY1 is implementing the change it recommended: deterministic sub-file chunk
partitioning in `utils/pytest_shard.py` for multi-item files whose weight
exceeds a threshold, plus parametrizing the seven-iteration loop in
`tests/test_bc1_g2_journal.py`. Its assignment is
`assignments/claude-lead-agy1-ci-chunk-sharding.md`; read it first.

Before that diff exists, find what would make it wrong. Read the current
source on main `925d726d` (a sparse checkout of exactly that tree plus PR
5808 is at
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111`;
read only, do not write there). Answer, with file and line evidence:

1. **Fixture multiplication.** For each file the committed weights put above
   300 seconds, list its module-scoped and class-scoped fixtures and whether
   any is expensive enough that running it in more shards erases the gain.
   The workflow already runs `-n logical --maxprocesses=4 --dist load
   --maxschedchunk=1`, so say what splitting adds beyond what xdist already
   does inside one shard.
2. **Order and shared state.** Does any of those files depend on the order of
   its tests, on module globals mutated by an earlier test, or on a class
   that must stay together? Contiguous chunks in collection order are the
   proposal; say where a chunk boundary would be unsafe.
3. **Determinism across shards.** Each shard job collects independently. What
   could make two shards compute different assignments (collection order,
   parametrize ids that embed paths or times, platform-dependent collection,
   the fallback median for files without a weight)? What must the pure
   function hash or sort on to be safe?
4. **The dedicated lanes.** `partition_lanes` and `_DedicatedCaseOutcome`
   require each of the seven targets exactly once and alone. Confirm chunking
   cannot re-admit a dedicated target into an ordinary shard or change what a
   dedicated lane collects.
5. **The journal test.** Read `test_every_bc1_response_is_journaled_before_parse`
   and say whether its seven iterations are independent, or what state or
   closing assertion couples them.
6. **Existing tests that pin the current behaviour** in
   `tests/test_ci_sharding.py`, `tests/test_ci_timing_update.py` and
   `utils/ci_sharding.md`: which would have to change, and whether changing
   them weakens a guarantee.

## Bounds and handoff

- Read-only: no edits, no tests, no CI triggers, no pushes, no comments.
- Write `handoffs/agy2-ci-chunk-design-review.md` in this notes directory:
  numbered findings, each with evidence and the smallest design constraint
  that answers it, and a clear list of anything that should stop the slice.
  No at-sign handles. Print its path and SHA-256 and stop.
- Later, when AGY1's diff is frozen, the lead will ask you to review that
  exact diff against your own findings. Do not start that until asked.
