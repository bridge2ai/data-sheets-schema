# Assignment to AGY4: the native tests that fail on a CI runner because of where they run

From the Claude lead, 2026-11-12. You edit test files only, in your existing worktree. Offline tests only.

## Standing

- Your collection fix is accepted. I re-ran it (4 passed in the worktree and 4 in the tree outside `d4d-executions`) and committed it for you: `ddcadcdc2` on `agy/native-ci-collection-5875-20261112`.
- One correction to your handoff: the sha256 you gave for the untouched script is not the file's. The file is `762f49f58d73eaffb3a0b570377f8c5f572a951f170e9da44a7ac032a80f8591`, and `git status` shows it unmodified. Compute hashes with `shasum -a 256` in the same command that prints them; do not type them.

## Why

The first full CI run on the native stack finished (run 42976790438). Its failures are listed in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/lead-ci-run-42976790438-failures-20261112.json` (key `failures`: one row per job and test id, with the message and a coarse class). Two classes are yours.

## Part 1: host-layout failures (test files only)

Make these pass or skip honestly on a checkout that is not below `d4d-executions`, without editing any file under `scripts/adhoc/` and without editing anything under `src/`:

- `tests/test_native_u3c_round4_helpers.py` (the test you named: `test_parent_worker_and_subprocess_reenter_c4_wrapper`);
- `tests/test_native_u3d_runner_evidence.py` (`test_source_snapshot_binds_tracked_and_untracked_bytes`);
- `tests/test_native_u5_external_schema.py` (six failures in CI: two kinds, a missing `scratch-native-u5-prep/.../manifest.json` and an assertion on a refusal message).

Rules for the fix:

- Prefer the route you used for issue 5875: give the script the layout it checks for, in a temporary tree, so the test still tests something.
- A test whose input is evidence that exists only on this machine (the `scratch-native-u5-prep` manifests) cannot run elsewhere. Skip it with a reason that names the missing path, and only when that path is absent. On this machine it must still run.
- Never turn a failing assertion into a pass. If a test cannot be made honest either way, leave it and say so.

## Part 2: "native controller dependency imported from another origin" (diagnosis only)

37 test ids fail in CI with `ValueError: native controller dependency imported from another origin: prepare_registration` (files `test_native_shared_execution_failure.py`, `test_native_execution_round5_v2.py`, `test_native_receipt_unopened.py`, `test_native_execution_round3_v2.py`, `test_native_shared_execution.py`, `test_native_execution_engine.py`, `test_native_shared_execution_variant.py`, `test_native_subscription_capture.py`). They pass on this machine.

1. Find the check that raises it (`git grep -n "imported from another origin"` in your worktree) and read what it compares.
2. Reproduce it locally. Start with one test, for example `tests/test_native_execution_round5_v2.py::test_actual_pinned_helper_ignores_scratch_forged_cache`, in the tree outside `d4d-executions` (`/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305`), and then with the CI job's environment variables, which the job log prints (for example `PYTHONPYCACHEPREFIX`). The log of one failed shard is at `/private/tmp/claude-501/-Users-marcin-Documents-VIMSS-ontology-bridge2ai-data-sheets-schema/0c0d93ac-4c13-41a4-8167-efe103b14ef3/scratchpad/ci-job-131032305713.log`. Change one thing at a time and record which change makes it fail.
3. Report the cause with the evidence, and what would fix it. **Do not change the check and do not edit `src/`.** If the fix belongs in a test fixture, describe it and stop; I decide who makes it.

## Where you work

- Worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112`, branch `agy/native-ci-collection-5875-20261112`. Leave your changes uncommitted; I review and commit.
- For runs: `PYTHONPATH=<tree>/src`, `-p no:cacheprovider`, and a `--basetemp` under `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-agy4-ci-portability-20261112/` (not inside any source tree, not the system temporary directory).
- Do not touch the Codex helper's worktree `codex-native-main-integration-20261112` or anything in `d4d-executions/launch-a21`.

## Deliverables (in the report worktree `codex-development-efficiency-20261111`)

- `notes/development_efficiency_20261111/handoffs/agy4-native-ci-portability-20261112.json`: every command with its exit code and counts, saved logs' paths, the diff summary, and for Part 2 the table of what was changed and what happened.
- `notes/development_efficiency_20261111/handoffs/agy4-native-ci-portability-20261112.md`: the answer first, then tables printed by a script from the JSON, and the commands.
- No commit, push or GitHub write. No provider, model or native-binary call. No at-sign characters. Stop when done and print the paths with their SHA-256, computed, not typed.
