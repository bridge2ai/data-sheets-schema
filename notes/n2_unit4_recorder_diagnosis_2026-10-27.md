# Wave 2 recorder diagnosis: measured host gate blocked

2026-10-27. Refs #5149, #5212, #4354. This is an offline measurement-status
report, not a completed causal diagnosis or native launch approval.

Two 60-sample idle-host checks failed before any pytest child was launched.
The historical checkout remained unchanged at
`01969cbed8eed93f420c640c1f1c306e5f58b033` throughout both checks. No recorder
trial, paired comparison or fresh-unit-4 API test is claimed. No timeout was
changed and no purported causal fix was made.

## Measured gate results

The existing reviewed measurement driver was used without modification, in
`--idle-only --idle-seconds 60 --mode idle`. Its thresholds remained mean CPU
15%, peak CPU 35%, maximum one-minute load per logical CPU 0.5, and no foreign
process at or above 5% in the sampled process table. These are the retained
formal gate's requirements, stronger than merely observing no named pytest job.

| Attempt | Samples | Mean CPU | Peak CPU | Max load / logical CPU | Exit | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `idle-check-wave2-20261027` | 60 | 34.5317% | 65.3% | 0.545117 | 3 | `blocked_host_busy` |
| `idle-check-wave2-20261027-r2` | 60 | 65.8317% | 100.0% | 1.938574 | 3 | `blocked_host_busy` |

Both outcomes report `source_unchanged: true`, null child return codes and no
test-child PID. Their source-before/source-after inventories are byte-identical.
The second gate ran without concurrent Codex analysis, Git reads or test jobs.
Other applications and sessions were not stopped. The saved `uptime` before
any trials was 5.06 / 9.92 / 11.19; all raw per-sample loads are also retained.

In the first window, Microsoft Word PID 13131 was reported above the 5% process
threshold in all 60 samples (mean 99.53% when reported), followed in the ranking
by WindowServer and Terminal. That is a process-CPU statistic, not a percentage
of total host capacity or proof of the previous timeout's cause. An `agy`
executable also appears above threshold in eight samples; its name does not
establish that it was running tests. The summaries retain executable basenames
and PIDs only. The original names-only samples contain no argv or environment
values. No claim that all test processes were absent is made from these names.

In the second window, an `rg` process (PID 51543) was the largest reported
competitor, above threshold in 26 samples with a 398.2% peak process-CPU reading.
Its owner is not established by these records. Word remained above threshold
in all 60 samples. This explains why pausing pytest alone does not satisfy the
retained gate; it does not identify the cause of any historical recorder failure.

The raw gate evidence remains at
`/private/tmp/d4d-recorder-measurements-20261026/idle-check-wave2-20261027`
and its `-r2` sibling. The [first verified summary](recorder_wave2_20261027/gate1_summary.json)
and [second verified summary](recorder_wave2_20261027/gate2/gate2_summary.json)
pin every input and their lossless archives; every original file's bytes and
mode are round-trip checked and the originals reread unchanged. Helpers live
in `scripts/adhoc/` on this report's branch. The first summary is reproduced
with its original helper version in commit `ee635a911`; the generalized helper
adds explicit gate/label arguments for the second window.

## Corrections to the delegated test and branch references

An ignored-inclusive search at the historical checkout finds
`tests/test_download/test_api_runner.py`, not `tests/test_api_runner.py`.
That API module uses fake clients or patches the API client factory. It does
not execute the recorder's native subprocess path. The expression `-k "not Live"`
is a name filter, not a network guard; it also excludes some benign mocked
tests containing that word. Passing that module three times would not reproduce
or explain the recorder's 180-second timeout.

The actual preserved recorder test is:

```text
tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion
```

It uses an explicitly synthetic Python peer while executing actual local stage,
receipt and provenance helpers. `tests/fixtures/native_shared_execution/fake_cli.py`
sets 180 seconds for helper subprocesses and invokes the recorder; the registered
test runtime has a 900-second outer deadline. Its launch fixture rejects the
historical launch/auth/provider factories. A clarification about the measured
test scope was requested; the API module and genuine recorder node must remain
distinct evidence even if both are eventually run.

The prompt's unit-4 identity
`15ff3049540a480f685a2cfbd86e2041d2e3bd7f`, and abbreviated `15ff3049`, cannot be
resolved to a commit in the local object store. No network fetch was made.
The actual clean local `codex/n2-4-restack-20261026` remains
`10f0d1a587a2d8230c14b3cdf267d8d1589b6fa0`; final D38 remains
`be0bd05821256212e89e4d011ba6b30a780e299b`. Neither branch was changed for this
measurement. This report does not substitute one identity for the other.

## Three-trial and paired-diagnosis ledger

| Requested recorder trial | Exact intended historical head | Wall time | Peak RSS | Outcome |
| --- | --- | --- | --- | --- |
| 1 | `01969cbed8eed93f420c640c1f1c306e5f58b033` | Not measured | Not measured | Not launched: gate failed |
| 2 | Same unchanged head | Not measured | Not measured | Not launched |
| 3 | Same unchanged head | Not measured | Not measured | Not launched |

The paired parent `d41282871394dd8abe74e11afb0e80c95d149305` and its existing
checkout remain preserved. Neither a test failure nor a hang was observed in
this wave because no test started. Therefore neither the prompt's three-pass
branch nor its failed-trial paired-comparison branch was reached.

For future trials, [the resource wrapper](../scripts/adhoc/time_recorder_python_20261027.sh)
adds macOS `/usr/bin/time -l` around the unchanged measurement worker, retaining
the worker's interpreter and all existing test/runtime limits. This provides
the operating system's reported maximum resident set size in the saved pytest
log, separately from wall time and verdict. It is not a summed simultaneous
process-tree RSS measure. The wrapper was checked only with `--version`; this
is **zero test trials**, not acceptance evidence. The first sandboxed wrapper
check lacked sysctl permission; its authorized read-only retry succeeded and
the version/resource output is retained. Peak RSS is not fabricated for unrun
trials.

## Remaining work and interpretation

Resume measurement only after a qualifying host window, with the measured test
scope and current unit-4 identity resolved. Freeze each baseline and all trial
instrumentation, run three consecutive genuine recorder trials with wall/RSS
and source proofs, then follow any reproduced failure with the declared paired
comparison. Run the corrected API module separately if required. Retain failure,
interruption and during-trial contention evidence rather than counting it as
an idle pass.

Even three passing recorder trials would establish completion under the sampled
conditions, not prove that prior failures were exclusively external contention.
A causal claim needs the matching measurements/comparison; an API-suite pass
cannot supply that evidence. Priority 1 remains blocked by the measured host
gate while independent engineering in Priorities 2 and 3 can proceed. No
scientific acceptance, live-native readiness or launch authorization is granted.
