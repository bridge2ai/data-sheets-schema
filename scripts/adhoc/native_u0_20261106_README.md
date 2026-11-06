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

Actual launch `canary-neutral-01` stopped before its first host sample: executing
the setuid `/bin/ps` from inside the sandbox raised `PermissionError(EPERM)`.
No pytest worker or synthetic peer launched. Source inventories matched and the
wrapper released its own lock after explicit no-child cleanup evidence.

Measurement blocker **U0-R2** remains open. `probe_native_u0_ps_20261106.py`
retains an exact unprivileged copy of `/bin/ps` and its sandbox result; this copy
was killed with return code -9, with no rows. The signal's cause is unproven.
`probe_native_u0_psutil_20261106.py` recorded incomplete process visibility under
the same network denial. Neither probe is a formal gate, and neither fallback
is installed in the driver. The next tooling repair must establish a complete
host observation path under unchanged network denial before repeating the
unchanged neutral canary. No timing, phase, stack or cache evidence was obtained.

## Protocol amendment: separate host observer

The appended ruling in `notes/coordination/2026-11-06-codex-native-u0.md`
authorizes the unchanged `/bin/ps` plus `sysctl` host observer outside the
sandbox. `native_u0_host_observer_20261106.py` is a separate wrapper-owned
process using the same minimal environment. It reads host counters and writes
only an exclusive JSONL sample file; it makes no network calls. Driver and
all test descendants stay in the network-denied sandbox. Both wrapper and
driver check EPERM on local bind. The profile also denies test-side writes to
the host file, and the driver verifies write-open refusal without writing.
Plans retain both PIDs, commands, sampler and profile hashes and this ruling.

CPU is primed before observations. The driver validates file identity, PID,
sequence, timestamp, freshness and bounded rows, and takes 60 distinct samples
over at least 60 seconds. Samples before reader startup do not count. The host
observer and its visible sampling children are excluded as measurement
instrumentation; all gate thresholds remain unchanged. Original `/bin/ps`
fields are retained; `sysctl vm.loadavg` supplies the load text at its native
precision. No fallback, copied/signed binary or partial process roster is used.

Local review finding **U0-R3**, fixed before launch: an abnormal observer exit
could leave a sampling child while allowing unlock. Release now additionally
requires normal requested observer termination and same-inode terminal
evidence with matching PID/sample count and unchanged `/bin/ps` hash. Normal
SIGTERM targets the observer only, letting a bounded active sample finish.
Unexpected/forced termination or missing proof retains the lock. The amended
tooling suite passes 92 tests; the standalone observer smoke check persisted
three samples. These are tooling checks, not a neutral recorder canary.

## Protocol amendment 2: one CPU-profile diagnostic

The second appended ruling permits one unchanged neutral path with recorder
CPU profiling without waiting for the quiet-host gate. Explicit `cpu-profile`
mode retains the lock, sandbox, minimal environment, source proofs, observer
and cleanup. It records the gate as deferred and all wall timing as contended;
software test outcomes are separate from timing eligibility. The strict gate
remains required for any later 180-second timing claim.

`prepare_native_u0_cpu_copy_20261106.py` creates a separate committed diagnostic
descendant of the failed head. It inserts a hash-bound profiler bootstrap into
`cli/__init__.py` after its docstring and before eager command imports, keeping
every original byte in order. This placement captures imports that the original
`__main__.py` proposal missed. Fresh fixture registrations bind the diagnostic
HEAD naturally; no source-identity guard or release pin is changed. Both helper
files and the closed config are bound by hashes in the package bootstrap and
the driver's complete source inventory. The original frozen trees stay intact.

`native_recorder_cpu_profile_20261106.py` uses CPU-timed cProfile plus per-phase
getrusage, peak RSS, existing cache counters and the 170-second stack watchdog.
It saves atomic rolling profiles every five seconds and retained initial,
150/170-second and final profiles. Full phase-boundary dumps are throttled;
all selected phase resource events remain. Inclusive CPU totals overlap and
include observer/checkpoint overhead. A GIL-held C call can delay checkpoints;
active-phase rusage and checkpoint age must be checked before interpreting a
partial profile. Recorder-local readback is observed; final parent-process
readback is outside this bootstrap.

Review findings before the run: U0-R4 removed two generator functions from
phase monitoring (they remain cProfile-visible, with resumption-count caveats);
U0-R5 bounded phase checkpoint cost; U0-R6 made preparation reject Git
replacement objects and require committed helper blobs and an exact parent.
Frozen-source eligibility audit: 42 ordinary targets, none missing/invalid.
Synthetic profiling canary: one pass with parsed saved partial/final profiles
and preserved return/refusal behavior. Focused tooling suite: 115 passed.
