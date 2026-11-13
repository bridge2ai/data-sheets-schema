# AGY2 assignment from the Claude lead: size the shard-count option, read-only

Track: CI efficiency (second priority). Read-only. Deliverable is one file.

## Your pre-review: confirmed, and the slice is stopped

Your main finding stands. I replayed AGY1's function exactly as it was
written (threshold 300 s, `k = min(count, total, ceil(estimate / 300))`,
which is not the `round(w / 500)` formula your tables used) against the
per-test durations of run 42947560899: the slowest of eight shards goes from
7,434 s of case time to 8,534 s, and of six from 9,351 s to 11,079 s. The
slice is stopped and kept as an unpushed evidence commit. Two notes:

- Your blocker 4 does not apply to the code as written: it keys owners by
  node id and skips repeats, so both occurrences of a colliding id land on
  one shard. The concern was right for the design; the implementation
  happened to satisfy it.
- Your in-sample figures for run 42916359440 compare against a partition
  that balances by construction on that run. The out-of-sample run is the
  comparison that carries weight. It agrees with you anyway.

## What the replay shows instead

In run 42947560899 shards 2 and 3 ran at about 0.63 of their predicted time
across nearly all their files, shard 1 at 1.00 and shard 8 at 1.17. The
spread is mostly the runner each shard landed on. No static partition fixes
that. The lever that does scale is the number of shards. Replaying the
existing file-level `balanced_files`, unchanged, on that run's per-test
durations:

| Ordinary shards | Mean case time | Slowest shard | Rough wall (3.8 busy workers + 100 s) |
|---:|---:|---:|---:|
| 6 | 7,523 s | 9,351 s | 42.7 min |
| 8 | 5,642 s | 7,434 s | 34.3 min |
| 10 | 4,514 s | 5,484 s | 25.7 min |
| 12 | 3,761 s | 4,951 s | 23.4 min |

The eight-shard row reproduces the observed 33m08s within a minute, so the
model is not far off. The longest single test in that run is 1,416.6 s
(`test_public_bc1_pipeline_multiple_groups_final_and_completed_replay`), so
no shard holding it finishes under about 25 minutes whatever the count.

Shard counts are an owner decision: D81 (STATUS.md line 526) set eight on
pull requests and six on main, and D75 set the 45 and 60 minute limits. The
lead will put a change to the owner as an option. Your job is to make that
option concrete and to find what would make it wrong.

## Questions

1. **Concurrency.** From the saved run responses (the PR run 42947560899
   under `tmp/ci-observed-42947560899/` and the main run 42953302794 under
   `tmp/ci-main-42953302794/` in the report worktree): how many jobs did each
   run start, when did each start relative to the run's creation, and was any
   job queued? What is the peak number running at once? Does anything in the
   repository or its notes record the account's concurrent-job limit? If not,
   say "unverified" and state what count would start to queue under each
   plausible limit. Fetch nothing.
2. **What pins 8 and 6.** Every place a change to 10 on pull requests (and,
   separately, 8 on main) would have to edit: the workflow matrix and
   denominators, tests that pin them, `utils/ci_sharding.md`, any helper that
   assumes eight artifacts (`utils/update_ci_shard_timings.py`, the timing
   refresh and analysis scripts, the aggregate job). File and line each.
3. **Cost per added shard.** From the saved job step timings: setup,
   checkout, environment restore, collection, upload. What does each extra
   shard add in runner time, and does the 4-worker full-tree collection
   (about 69 s in shard 8's log) get paid again per shard?
4. **Does the timing file still work?** `utils/ci_test_durations.json` holds
   whole-file weights from an eight-shard run. Is anything in it or in the
   refresh tool specific to the shard count?
5. **Limits and headroom.** With D75's limits unchanged, what margin do 10
   and 8 leave, using the replay table above and the slowest-runner factor
   observed (1.17) as well as a pessimistic one you justify from the saved
   runs?
6. **What would make the table above misleading?** The per-test durations
   were recorded on particular runners, so a test's time already carries its
   runner's speed. Say how that biases the replay at other shard counts, and
   anything else you find.

## Bounds and handoff

- Read-only: no edits, no tests, no CI triggers, no network reads, no pushes,
  no comments. Do not propose changing the shard counts yourself; describe
  the option and its costs.
- Write `handoffs/agy2-shard-count-option.md` in this notes directory:
  numbered answers with file and line evidence, then one table of the
  options (8/6 as now, 10/6, 10/8, 12/8) with expected slowest-shard wall,
  added jobs, added runner minutes and what is unverified. No at-sign
  handles. Print its path and SHA-256 and stop.
- After that, the lead will ask you to review AGY4's frozen diff for the
  `routing-portable` lane split. Do not start it until asked.
