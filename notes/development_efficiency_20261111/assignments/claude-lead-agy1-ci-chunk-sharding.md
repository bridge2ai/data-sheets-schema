# AGY1 assignment from the Claude lead: sub-file chunk sharding, local slice

Track: CI efficiency (second priority; never a final-generation prerequisite).

## Lead review of your bottleneck assessment

Collected (terminal capture under `handoffs/captures-20261111/`) and accepted
as the basis for one implementation slice. Two things I am holding you to:

- Your own limit: on pull requests the gain from this slice alone is capped
  at about 1m30s, because the dedicated `routing-portable` lane sits at
  31m38s. AGY4 is separately designing that lane's split. Report this slice's
  expected effect on main (six shards) and on pull requests separately, and
  claim nothing for pull requests beyond the cap.
- `utils/pytest_shard.py` keeps a file together on purpose: its docstring
  says this "avoids multiplying its module/class fixture setup". Chunking a
  file across shards gives up that property for the files it splits. The
  implementation must make that cost visible and bounded, not ignore it.

## Worktree

The lead has created it for you (do not create worktrees or branches):

- Path: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111`
- Branch: `agy/ci-chunk-sharding-20261111`, from main `925d726d67cdd03fe28fdeafdde60fa27df57205`
- Sparse checkout: `src tests utils project docs scripts .github .claude` and
  the root files. No `data/`, no `notes/` (the disk has about 12 GB free).

## Scope: exactly these three files

1. `utils/pytest_shard.py`: a **pure function** that maps the collected
   ordinary node ids, a shard total and the weights to an owner shard per
   node id, splitting a file only when it has more than one collected item
   and its estimate exceeds a named threshold. Contiguous chunks in
   collection order. Deterministic: same inputs, same assignment, on every
   shard's own collection. The seven dedicated lane targets stay out of the
   ordinary shards exactly as now. No new timing schema, no change to
   `utils/ci_test_durations.json`, no workflow edit, no change to shard
   counts (8 on pull requests, 6 on main).
2. `tests/test_bc1_g2_journal.py`: turn the seven-iteration loop in
   `test_every_bc1_response_is_journaled_before_parse` into seven
   parametrized cases, only if each iteration is already independent (its own
   `tmp_path` subdirectory, a fresh spec, no assertion after the loop that
   needs all seven). If any cross-iteration state exists, stop and report it
   instead of changing the test's meaning.
3. `tests/test_ci_sharding.py`: unit coverage for the pure function. For
   totals 6 and 8: every node id is owned by exactly one shard; a file under
   the threshold is never split; a one-item file is never split; the result
   does not depend on the order shards are computed in; the dedicated targets
   never appear.

## Validation, bounded

- First one tiny canary: a single new unit node, 30 second cap. Inspect it.
- Then `tests/test_ci_sharding.py` once, 300 second cap:
  `PYTHONPATH=src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/pytest -q -p no:cacheprovider tests/test_ci_sharding.py`
- A partition proof on a real roster, in one process and without re-collecting
  per shard: the lead's collect-only log of the full suite will be at
  `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111/tmp/combined-head-20261111/collect2.log`
  (the earlier `collect.log` beside it has 16 collection errors from the
  sparse checkout and 22,222 node ids; either is a usable roster for a
  partition property, but say which you used and its count; if neither ends
  with a collected count, say so and use the unit tests only). Read it; do
  not write in that worktree. Feed its node ids to the pure function for totals 6 and 8 and
  assert union equals input, pairwise disjoint. Save the helper under
  `scripts/adhoc/` with the usual header.
- For the journal test: `--collect-only` on that one file to show seven
  items, and one parametrized case run once, 600 second cap. Do not run the
  other six locally; hosted CI will.
- No full-suite run, no CI trigger.

## Stop conditions and handoff

- Commit locally on the assigned branch if your sandbox allows it. If a git
  write is refused, do not retry or look for a bypass: leave the tree as it
  is and report the exact file list for the lead to commit.
- No push, no PR, no comments, no merge. The lead reviews the frozen diff,
  AGY2 reviews it adversarially, findings become issues, and only then is one
  hosted CI run spent on it.
- Preserve failed attempts and their logs under the worktree's `tmp/`.
- Write `handoffs/agy1-ci-chunk-sharding.md` in this notes directory: head
  commit or dirty file list, file hashes, the threshold you chose and why,
  which files the current weights would split and into how many chunks for
  totals 6 and 8, the predicted per-shard loads before and after from the
  committed weights (a prediction, not a measurement), every command with its
  result, and what stays unverified. No at-sign handles. Then stop.
