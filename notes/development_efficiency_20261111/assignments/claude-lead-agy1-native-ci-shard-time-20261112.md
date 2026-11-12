# Assignment to AGY1: why two CI shards ran out of time with the native tests, as data

From the Claude lead, 2026-11-12. Read-only on GitHub and on the repositories. No test run.

## Why

The owner directed on 2026-11-12 (D134): the native agentic arm is the main result. The first full CI run on the native stack finished: run 42976790438 on head `1a137b58860416a31618de44173180d021dfcc61`. Shards 5 and 8 were cancelled at the 45-minute job limit, and shards 1, 2 and 4 took 37 to 42 minutes. The native tests are not in main's timing weights, so the shards are unbalanced. You did the shard partition work on 2026-11-11 and know how the weights are used.

The job list with durations is in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/lead-ci-run-42976790438-failures-20261112.json` (key `jobs`).

## What I need

1. **Measured time per test file in that run.** Use the run's uploaded artifacts if it has per-shard JUnit XML (`gh run download 42976790438` into a new directory under `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/`), otherwise the job logs. For the two cancelled shards say exactly what is available and what is not.
2. **Which files have no weight.** Compare the test files that ran with the weights file the CI partition reads at that head (find it from `.github/workflows/` at the commit with `git show`; do not guess its name). List the native test files with no weight, with their measured seconds.
3. **Where the time went.** Per shard: measured total, the sum for native test files, and the ten slowest files.
4. **What partition would fit.** Using the partition code as it is at that head (read it with `git show`; if it can be imported from an exported copy without running tests, do that in a copy outside every worktree), compute the predicted shard totals if the measured native times were added to the weights, for the current shard count and for one and two more shards. Report the largest predicted shard for each. Do not edit the weights file or the workflow.

## Deliverables (in the report worktree `codex-development-efficiency-20261111`)

- `scripts/adhoc/native_ci_shard_time_20261112.py`: does the extraction and the prediction and writes the JSON. Header comment with purpose, inputs, outputs, date.
- `notes/development_efficiency_20261111/handoffs/agy1-native-ci-shard-time-20261112.json`
- `notes/development_efficiency_20261111/handoffs/agy1-native-ci-shard-time-20261112.md`: the answer first (does a re-weighting alone fit 45 minutes, or are more shards needed, on this one run's evidence), then the tables printed by the script, and the command. Say plainly that one run is one measurement.

## Rules

- GitHub reads only. No rerun, cancel, comment or push. No test run. No checkout or branch switch in any existing worktree. Nothing in `d4d-executions/launch-a21`.
- Every number comes from the script's output; every hash is computed in the command that prints it. Every path in backticks must exist.
- No at-sign characters. Stop when the three files are written and print their paths and SHA-256.
