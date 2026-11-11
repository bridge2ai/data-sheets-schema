# AGY4 assignment from the Claude lead: implement Option A2, local only

Track: CI efficiency (second priority; never a final-generation prerequisite).

## Lead review of your design

`handoffs/agy4-routing-portable-split.md` is accepted, and Option A2 is the
one to implement: it is the only option that leaves `_DedicatedCaseOutcome`
and the single-process rule exactly as they are. Two notes for the record:

- Your "rebalanced ordinary shards about 21 to 23 minutes" is not measured
  and disagrees with AGY1's own floor (about 25 minutes for the shard holding
  the single 1,416 s pipeline test, 26 to 28 minutes expected). A2's
  predicted 20m23s is under either figure, so the recommendation stands, but
  do not repeat the 21 to 23 minute figure as a result.
- The per-call costs behind the "balanced" split are depth estimates, not
  timings. The hosted run will show the real balance. Say so in the handoff.

## Worktree

The lead has created it for you (do not create worktrees or branches):

- Path: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy4-ci-routing-portable-split-20261111`
- Branch: `agy/ci-routing-portable-split-20261111`, from main `925d726d67cdd03fe28fdeafdde60fa27df57205`
- Sparse checkout: `src tests utils project docs scripts .github .claude config data/preprocessed data/rubric`
  and the root files. If the test needs a path that is not checked out, name
  it in the handoff; do not add it yourself.

AGY1 is editing `utils/pytest_shard.py`, `tests/test_ci_sharding.py` and
possibly `utils/ci_sharding.md` on a different branch for a different
purpose. You edit the same files only where A2 requires (the lane table, its
count and prose). Keep those edits minimal and local so the lead can combine
the two branches; do not reformat or reorder anything else in them.

## Scope: exactly these five files

1. `tests/test_source_heading_runtime_api.py`: split
   `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` into
   the two functions you named, sharing one helper for setup and the
   read-only sandbox. Each function builds its own completed capture: no
   module or session fixture that shares a capture between them. Every one of
   the 21 explicit `recheck_completed` calls in your section 1.3 table must
   still run, under the same monkeypatch guard, with the same assertions and
   the same expected refusal. Call 1 runs in both. Keep the existing name for
   the first function if that lets the `routing-portable` lane target stay
   unchanged; otherwise say why it had to change.
2. `utils/pytest_shard.py`: add the `routing-portable-tamper` lane target and
   update the lane count in the docstring and header text. Nothing else.
3. `.github/workflows/main.yaml`: add the lane to the `api-completion`
   matrix. Nothing else.
4. `tests/test_ci_sharding.py`: whatever pins the lane list or its count.
5. `utils/ci_sharding.md`: the dedicated-lane prose and counts.

No production source under `src/`, no protected file, no timing file.

## Validation, bounded

- Canary, 120 second cap: `--collect-only` on
  `tests/test_source_heading_runtime_api.py` showing both node ids.
- Then `tests/test_ci_sharding.py` once, 600 second cap (it took 234 s on
  this host). **Do not pass `-o tmp_path_retention_policy=none`**, and if you
  pass `--basetemp`, put it outside any git worktree: that file spawns nested
  pytest sessions, the option leaves the parent's temp directory unlocked so
  they delete it, and a base temp inside the worktree changes their rootdir.
  Both produced false failures in the lead's own run today.
- One execution canary through the exact lane command, once, 40 minute cap:
  `python -m pytest tests -v -p no:cacheprovider -p utils.pytest_shard --ci-lane=routing-portable-tamper`
  with the primary checkout's interpreter and `PYTHONPATH=src`. Check the
  host first (`uptime`): if the one-minute load is above 25, wait and report
  instead of starting. If it fails for a reason the sparse checkout explains,
  report that and do not retry. Do not run the other lane locally; the hosted
  run will.
- No full-suite run, no CI trigger.

## Stop conditions and handoff

- Commit locally on the assigned branch if your sandbox allows it. If a git
  write is refused, do not retry: report the file list for the lead to commit.
- No push, no PR, no comments, no merge.
- Preserve failed attempts and logs under the worktree's `tmp/`.
- Write `handoffs/agy4-routing-portable-a2-implementation.md` in this notes
  directory: head commit or dirty file list, file hashes, a table mapping
  each of the 21 original calls (your numbering) to its new function and
  line, every command with its result and duration, and what stays
  unverified until the hosted run. No at-sign handles. Print its path and
  SHA-256 and stop.
