# Assignment to AGY4: make the native test suite collectable on a CI runner (issue 5875)

From the Claude lead, 2026-11-12. This one edits one test file in a worktree the lead made for you, and runs offline tests.

## Why

The owner directed on 2026-11-12 (D134): the native agentic arm is the main result. The first full CI run of the native stack failed every job at collection (issue 5875):

```
ERROR collecting tests/test_native_u3c_test_driver.py
scripts/adhoc/run_native_u3a_tests_20261107.py:34: in execution_root
    raise RuntimeError("source must be below the canonical d4d-executions root")
```

The test loads that script at import time. The script computes `EXECUTIONS = execution_root(ROOT)` at module level and raises unless a parent directory is named `d4d-executions` and contains `plans/`. A GitHub runner checks out under `/home/runner/work/...`, so pytest stops for the whole suite.

The lead reproduced it on the merged candidate with `scripts/adhoc/simulate_ci_collection_outside_executions_20261112.sh` (report worktree). Its log is `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305.collect.log`. The three `fairscape_models.rocrate` errors in that log come from the primary repository's virtual environment, not from the code; CI does not have them. Ignore them.

## Where you work

- Worktree: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112`
- Branch: `agy/native-ci-collection-5875-20261112`, at the merged candidate `b11931410305569aba30b0f593193ae894bd0dc7`.
- Edit only in this worktree. The Codex helper is working in `codex-native-main-integration-20261112`; do not touch it.

## Part 1: the fix

Make `tests/test_native_u3c_test_driver.py` collect and pass on any checkout path.

- **Do not edit `scripts/adhoc/run_native_u3a_tests_20261107.py`.** Retained evidence refers to its bytes.
- **Preferred:** load the script from a temporary copy that sits in a temporary directory tree satisfying its layout check (a resolved directory named `d4d-executions` with a `plans/` directory, and the copy at the same relative depth as the original), built in a module-scoped fixture, not at import time. The four tests then run everywhere and can never touch the real quiet-window lock.
- **Fallback, only if the preferred route cannot keep all four tests meaningful:** skip the module with a stated reason when the layout is absent. Say why you fell back.
- No other file changes unless a test needs it; say so if one does.

## Part 2: prove it

1. In your worktree: run `tests/test_native_u3c_test_driver.py` (4 tests). Use `PYTHONPATH=<worktree>/src`, `--basetemp` inside the worktree, and `-p no:cacheprovider`.
2. Outside the root: copy your changed test file into the exported tree `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305/tests/` and run the same four tests there, then `pytest --collect-only -q tests` there. Expected: the four pass, and the collection error for this file is gone. The three fairscape errors may remain.
3. **Run-time dependence on the layout.** 78 files under `tests` mention `d4d-executions`. With a script, list each file and each line that mentions it, and classify the line mechanically as: inside a string that is only compared or printed, a path that is opened or resolved, or an import-time statement. Do not run those 78 files. This list tells the lead what CI may still trip over.

## Deliverables

- The changed test file in your worktree, uncommitted (the lead reviews and commits).
- In the report worktree `codex-development-efficiency-20261111`:
  - `scripts/adhoc/native_tests_layout_dependence_20261112.py` for step 3, with a header comment;
  - `notes/development_efficiency_20261111/handoffs/agy4-native-ci-collection-fix-20261112.json`: the commands you ran with exit codes and counts, the diff summary, and step 3's data;
  - `notes/development_efficiency_20261111/handoffs/agy4-native-ci-collection-fix-20261112.md`: the answer first (which route, do the four tests pass in both places, is collection clean of this error), then tables printed by the script from the JSON, and the commands.

## Rules

- No commit, push or GitHub write. No provider, model or native-binary call. No private-composition arming. Nothing in `d4d-executions/launch-a21`.
- Every number in the handoff comes from command output you saved. Every path in backticks must exist.
- No at-sign characters in the handoff files.
- Stop when done. Print the paths and SHA-256.
