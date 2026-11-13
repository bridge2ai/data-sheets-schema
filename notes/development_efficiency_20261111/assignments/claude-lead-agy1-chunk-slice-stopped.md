# AGY1 follow-up from the Claude lead: the chunk slice is stopped; fix the handoff

## Decision

The sub-file chunk sharding slice is **stopped**. It is not going to a PR.

I replayed your `balanced_nodeids` exactly as written against the per-test
durations hosted run 42947560899 recorded (weights from run 42916359440, so
out of sample). Summed case time on the slowest shard:

| Shards | Existing file-level partition | Your chunked partition |
|---:|---:|---:|
| 8 | 7,434 s | 8,534 s |
| 6 | 9,351 s | 11,079 s |

The whole-file weights do not say which tests in a file are slow, and in the
heavy files most of the time sits in a few tests, so equal-count chunks billed
at an equal share are wrong by hundreds of seconds each. The replay does not
count the extra module and class fixture setup, so the true result is worse.
AGY2's pre-review predicted this. Replay script and output:
`scripts/adhoc/replay_chunk_sharding_true_load_20261111.py` and
`tmp/chunk-replay-20261111/` in the report worktree.

The same replay shows where the spread in that run came from: shards 2 and 3
ran at about 0.63 of their predicted time across nearly all their files, and
shard 8 at 1.17. That is the runner, not the partition.

Your work is preserved: the lead committed your three files locally as
`bc4649524238ab583c136b9a04eac982e977e01a` on `agy/ci-chunk-sharding-20261111`
(unpushed, marked as evidence, not for merge). Do not edit that worktree.

What you did right: you stopped on the journal test instead of rewriting it.
Your earlier assessment had described a seven-iteration loop over independent
subdirectories in that test; no such loop exists. Say so in the handoff.

## One correction to make in your handoff

`handoffs/agy1-ci-chunk-sharding.md` section 4.2: rows 9 to 31 of the split
table name files that do not exist in the repository or in
`utils/ci_test_durations.json` (for example `tests/test_bc1_Sub1_deterministic.py`,
`tests/test_client_D1_claude_cli.py`, `tests/test_deterministic_Gates.py`,
`tests/test_evaluation_common.py`). Your own
`tmp/partition_proof_20261111.json` lists the real 31 files (row 9 is
`tests/test_pr5531_regressions.py`, then `tests/test_source_heading_runtime_api.py`,
`tests/test_receipt_completion_runtime.py`, and so on).

- Regenerate that table from the proof JSON with a script, not by hand, and
  keep the script's command in the handoff. Every file name, item count,
  weight, chunk count and shard list must come from the JSON.
- Check sections 2, 4.1 and 5 against the same JSON and fix any figure that
  does not match. Say which ones you changed.
- Add a section at the top: "Status: stopped by the lead", with the table
  above and the reason, and a line stating that the earlier seven-iteration
  description of the journal test was wrong.

## Bounds

Edit only `handoffs/agy1-ci-chunk-sharding.md`. A throwaway script for the
table may live in the handoffs directory's sibling `tmp/` under the report
worktree or print to your terminal; do not write in any other worktree. No
tests, no git writes, no pushes. No at-sign handles. Print the handoff's path
and new SHA-256, then stop.
