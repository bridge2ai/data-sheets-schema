# Context for the Codex helper sessions, 2026-11-12 (after the restart)

From the Claude lead. Read this once, then your own assignment file. The lead is the Claude Code session in `data-sheets-schema`; it assigns, reviews, commits other workers' reviewed work, publishes, and brings decisions to the owner. You report to the lead by writing a handoff file. You do not direct other helpers.

## The goal

The owner directed on 2026-11-12 (decision D134): "the native agentic is the main result"; the API route is for comparison only. The target is the first native CHORUS canary, then native production runs. Nothing may launch without the owner's word.

## Where things are

Short names used below:

- `P` = `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema` (the primary checkout; its `main` is stale and dirty: **never switch, reset, clean or pull there**).
- `E` = `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions` (all worktrees and scratch directories).
- `R` = `E/codex-development-efficiency-20261111` (the report worktree: assignments, handoffs and helper scripts; branch `codex/native-efficiency-results-20261111`).
- Assignments: `R/notes/development_efficiency_20261111/assignments/`. Handoffs: `R/notes/development_efficiency_20261111/handoffs/`. Helper scripts: `R/scripts/adhoc/`.
- The coordination record with every owner decision: `P/notes/coordination/STATUS.md` (read it with `grep -n`; do not edit it).

The native code:

- **The candidate:** worktree `E/codex-native-main-integration-20261112`, branch `codex/native-main-integration-20261112`, head `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`. It is the native stack merged with main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`, plus the 1200-second freshness commit and the latest-capture enforcement. Unpublished. Helper 1 owns this worktree.
- **CI-portability fixes:** worktree `E/agy-native-ci-collection-20261112`, branch `agy/native-ci-collection-5875-20261112`, head `ab07c81fe` (two commits on top of the merge `b11931410305`).
- **Launch sequence draft:** worktree `E/agy-native-launch-sequence-20261112`, two new uncommitted files.
- **Amendment N1** (the canary's plan amendment), draft v10: commit `127cc0bd69d73fcd21d94978bf5e0ee60e0e950c` on `claude/native-amendment-n1-v7-20261112`. Read it with `git -C P show <commit>:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`.

What to read for background (all in the handoffs directory):

- `codex-native-critical-path-20261112.md`: the gates from today's source to the first canary.
- `codex-native-packets-g07-20261112.md`: the state of the candidate, with findings G07-F1 to G07-F6.
- `lead-ci-run-42976790438-failures-20261112.json`: the first full CI run on the native stack (152 distinct failing test ids, two shards out of time).
- `agy4-native-ci-portability-20261112.md` and `agy1-native-ci-shard-time-20261112.md`: host-layout fixes, the import-origin diagnosis, and shard timing.

## Rules for every helper

- **No push, no pull request, no GitHub write of any kind.** The lead publishes.
- **No provider, model or native-binary call,** no `cpu-monitoring` diagnostic, no private-composition arming unless your assignment says so.
- **The four protected files stay equal to main on every branch:** `src/data_sheets_schema/shared_generation.py`, `src/data_sheets_schema/api_runner.py`, `src/download/prompts/canonical_hashes.yaml`, `tests/utils/run_spec_boundary_contracts.json`. Do not rotate prompt pins.
- **Work only in the worktree your assignment names.** Create a new worktree under `E` when told to (`git -C P worktree add -b <branch> E/<name> <commit>`). Never work under `/tmp`. Never switch branches in an existing worktree. Stay out of `E/launch-a21`.
- **Tests:** use the runner the candidate carries, `scripts/adhoc/run_native_g07_tests_20261112.py` (see its `--help`; it builds an isolated environment and denies network), or an equivalent isolated environment. The primary checkout's `.venv` gives false failures ("foreign project package namespace"). Put `--basetemp` and all outputs in a scratch directory of your own beside the worktrees (`E/scratch-<your-task>-20261112/`), never inside a source tree and never in the system temporary directory. At most two xdist workers. Never pass `-o tmp_path_retention_policy=none`.
- **Commits:** commit your own work locally on your own branch, one concern per commit, with a message that says what changed and why. Do not amend or rebase commits that exist already.
- **A failure is a finding.** Never turn a failing assertion into a pass, never weaken a production check to make a test pass, and say plainly what you did not verify.
- **If a task needs a design decision, stop there** and report the choice with your recommendation.

## The handoff

Write it to the path your assignment names. Put the answer first. Every number comes from saved command output, every hash is computed in the command that prints it, and every table is produced by a script from a data file where the assignment asks for data. Use no at-sign characters. When you finish, print the handoff path and its SHA-256 and stop.
