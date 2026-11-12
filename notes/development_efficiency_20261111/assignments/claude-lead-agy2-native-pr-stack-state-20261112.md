# Assignment to AGY2: the state of the open native pull requests, as data

From the Claude lead, 2026-11-12. Read-only on GitHub and on disk.

## Why

The owner directed on 2026-11-12 (D134): the native agentic arm is the main result. The native code sits in a stack of open pull requests, none merged. To plan the landing order the lead needs their exact state, collected mechanically.

## What I need

For each of these pull requests in `bridge2ai/data-sheets-schema`: 5839, 5840, 5841, 5851, 5852, 5853, 5855, 5857, 5858, 5866, 5871, 5542, 4659.

1. Number, title, draft or ready, head branch, head commit, base branch.
2. The stack edge: which other pull request in the list has this one's base branch as its head branch.
3. `mergeable` and `mergeStateStatus` as GitHub reports them now.
4. Count of changed files, and whether the head commit of this pull request is an ancestor of the head of another one in the list (which would make it contained in that one). Use `git merge-base --is-ancestor` on fetched commits in a scratch clone or with `git fetch` into the report worktree's object store. Do not check anything out in any existing worktree.
5. The workflow runs on the head commit: workflow name, run id, status and conclusion. Say `none` when no run exists for that head.
6. Whether the pull request changes any of the four protected files of D127: `src/data_sheets_schema/shared_generation.py`, `src/data_sheets_schema/api_runner.py`, `src/download/prompts/canonical_hashes.yaml`, `tests/utils/run_spec_boundary_contracts.json`.
7. Whether the head already contains main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`.

## Deliverables (in the report worktree `codex-development-efficiency-20261111`)

- `scripts/adhoc/native_pr_stack_state_20261112.py` (or `.sh`): collects the above with `gh` and `git` and writes the JSON. Header comment with purpose, inputs, outputs, date.
- `notes/development_efficiency_20261111/handoffs/agy2-native-pr-stack-state-20261112.json`
- `notes/development_efficiency_20261111/handoffs/agy2-native-pr-stack-state-20261112.md`: the tables printed by the script from the JSON, and the command. No row written by hand. No interpretation beyond one line per pull request on what the data says.

## Rules

- GitHub reads only: no comment, review, label, rerun, cancel, close, edit or push.
- No test run, no checkout or branch switch in any existing worktree, nothing in `d4d-executions/launch-a21`.
- Every number and name comes from the script's output. Every path in backticks must exist.
- No at-sign characters.
- Stop when the three files are written. Print their paths and SHA-256.
