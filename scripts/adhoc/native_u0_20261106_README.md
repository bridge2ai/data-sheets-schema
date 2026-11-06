# U0 offline recorder tooling — 2026-11-06

D92 authorizes this diagnosis, not a production recorder fix. These helpers
are on `codex/native-u0-diag-20261106`, based on M7
`8bc90e93d736d464f98e9eedffee45f0ad8e5d3f`.

Recovered measurement/observer tools and tests originate at
`bacb63b87be8ae43a416f258a72cffe0ba58eeae`. Corrections add the delivery head,
physical dependency bootstrap without `.pth`, explicit disabled plugin
autoload, OS network denial, a minimal environment, durable observer output,
quiet-lock ownership and conservative cleanup verification. They do not edit
the selected neutral test, synthetic peer, helper 180-second limit or registered
900-second attempt limit. The environment is intentionally stricter than the
historical one; dependency metadata is not a reconstruction of historical bytes.

`prepare_native_u0_sources_20261106.py` creates new detached sparse worktrees and
archives of all tracked root files and src/scripts/tests/utils/.claude/notes
assets at failed `01969cbed8eed93f420c640c1f1c306e5f58b033`, original
`d41282871394dd8abe74e11afb0e80c95d149305` and delivery
`be0bd05821256212e89e4d011ba6b30a780e299b`. Other roots, corpus data/docs and
submodule contents are excluded. Real Git object access remains available for
native source authority. The fixture synthesizes its case inputs.

The only measured node is:

```
tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion
```

At the failed head, test lines 37–43 create `ordinary-python-test-peer` from
`sys.executable` plus the exact committed fake CLI; line 47 sets 900 seconds.
Lines 107–114 patch runtime observation and refuse auth/direct/API/provider
factories. `fake_cli.py:77` invokes local helpers with timeout 180. No real native
binary is selected. The supervisor itself is real Python software. Verify the
persisted executable/hash and final publication after a passing canary.

Run `native_u0_run_20261106.py` using the existing venv Python with `-S -P -B`.
Supply explicit `--python`, `--driver`, `--tree`, `--output`, `--trial`,
`--target current` and `--driver-seconds 1800`. Output must be a new trial under
an existing external evidence parent. The wrapper acquires the protocol lock,
verifies denied local socket binding under its saved sandbox profile, allows
the other sessions time to pause, and runs the 60-sample host gate before any
trial. The outer 1800-second watchdog is censoring, not a fixture-limit change.

If cleanup is uncertain, the lock stays and the wrapper fails. Inspect retained
PID/creation-time evidence before terminating only trial-owned processes or
releasing the lock. Never delete another owner's or changed lock. A failed
host gate is zero trials. A pass requires persisted output/readback evidence,
the exact JUnit node, source equality and an uncontaminated measured window.

`run_native_u0_tool_tests_20261106.py` runs only tooling tests, with optional
single-test canary. `summarize_native_u0_20261106.py` reads saved gate, source,
wrapper and completion evidence without importing production code or rerunning
acceptance. Both retain fresh external artifacts. All actual trial processes
inherit `(deny network*)` and frozen-source write denial.

Read-only review finding **U0-R1**: an exited pytest worker can leave its synthetic
peer in another process session. A positive outer-driver exit is not cleanup
proof. The wrapper therefore requires explicit saved driver cleanup verification
before releasing the quiet lock. Abnormal worker exits, forced/uncertain cleanup,
missing evidence or surviving observed descendants retain the lock. This finding
is recorded locally because the brief forbids GitHub operations.

Diagnostic observer injection remains separate from unchanged baseline mode.
The native authority requires committed consumed source; do not inject the
bootstrap into a frozen baseline or bypass that check. No production fix is
part of this tooling delivery.
