# CI test partitioning

Every pull request runs the complete collected suite, including corpus tests,
on twelve Python 3.12 shards. Main and manual runs use eight Python 3.12 shards
(D147, which replaced D81's eight and six) and one separate schema/example build. Three additional Python 3.12 jobs run the
complete offline canary, audit/finalization and evaluation suites alongside the
shards. Budget and native transport controls run once in the canary job, with
the same 45-minute job limit and existing test deadlines, rather than sharing
the time left after a full suite shard (#4466). Four more jobs each run one required long offline API case, with the same
45-minute limit (#4517). Three run the SG2 root launches; twenty run native
cases (three public-path launches and seventeen failures), with the same limit.
Ordinary shards retain D75's 45-minute PR and 60-minute main/manual limits.
There are 25 + 17 = 42 Python jobs on PRs (12 + 4 + 3 + 20 + 3)
and 21 + 17 = 38 on main/manual runs (8 + 4 + 3 + 20 + 3),
plus the aggregate `test` job. The aggregate
requires every applicable job to succeed; failure, cancellation or an unexpected
skip in any offline lane also fails it. Package metadata still permits Python
3.9 and newer; this CI configuration does not independently check compatibility
on other interpreters.

The offline jobs retain their existing pytest arguments and `PYTHONPATH`, full
checkout history, FAIRSCAPE submodule initialization and cached project setup.
They upload `budget.xml` and `native.xml` as `tests-py3.12-offline-canary`, and
`audit-controls.xml` and `evaluation-controls.xml` under separate
`tests-py3.12-offline-audit` and `tests-py3.12-offline-evaluation` artifacts, all
with the same 14-day retention. Core shard artifacts and the `pytest.xml` files used
for scheduling estimates are unchanged. Extra jobs add setup and runner demand;
compare complete PR/main timings and total runner time before claiming a speedup.

Each shard uses `-n logical --maxprocesses=4 --dist load --maxschedchunk=1`: up to four
workers on the standard public Linux runner, rather than the two physical
cores selected by `-n auto`. The subprocess coverage proof uses two workers with this scheduling policy and
both partition sizes. Every collected test remains included.

Within a shard, files with the largest estimated time per collected case run
first. A stable sort keeps the existing order within each file. Small xdist
scheduling chunks distribute those checks as workers become available, so a
single worker does not retain a long queue while the others finish. The timing
file still controls only scheduling, never collection or test outcomes.

Tests, schema/example builds and both documentation workflows share
`.github/actions/setup-project`. Poetry 2.4.3 has its own cached environment;
the project environment is keyed by exact Python version, runner architecture,
the lockfile, project metadata and setup action. Every job still installs the
current checkout on cache hits. A cold cache may take longer; use recorded
Actions timings to assess both cold and warm runs.

The workflow supplies `--ci-shard-timings=utils/ci_test_durations.json` to the
pytest partition plugin. It assigns the actual collected file set using
largest estimated durations first, placing each file on the least loaded
shard. Sorted file paths and shard indices break ties, so all xdist workers
produce the same assignment. Every ordinary test in a file remains together; the ten separately scheduled
API, SG2 and native public-path cases are removed by the explicit lane partition before file balancing.

Timings are scheduling hints. They cannot select or omit tests. Newly collected
files use the median duration of known collected files (one second if none are
known), and entries for removed files are ignored. Malformed explicitly supplied
timing data produces a pytest usage error. Without the timing option, the
existing SHA-256 file partition remains available.

The first timing snapshot comes from successful run
[35009501429](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35009501429)
at `893e9e941d3ea860c3c0f8861cc1ba64432dd4ae`: 4,964 recorded cases in 277 files.
Recorded case times sum to 887.1, 471.5, 999.5 and 431.2 seconds under the hash
partition, compared with approximately 697.3 seconds per weighted shard.
These are estimates of test work, not wall-clock predictions; fixture reuse,
runner load and changed tests can affect the actual result.

The latest complete refresh uses successful PR run
[42916359440](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42916359440)
at `6792947ea6558d10c85106065b023cb57838835a`: all eight ordinary-shard
JUnit artifacts, with 23,270 testcase occurrences in 676 files (23,222 passes
and 48 skips). The two PR5808 readiness files are included in the measurements;
the base main checkout has 674 of these measured files. Obsolete entries are
ignored by the scheduler, and genuinely new collected files retain its median
fallback. The dedicated cases stay in their lanes.

The [refresh helper](../scripts/adhoc/refresh_ci_timings_42916359440_20261111.py)
uses the existing updater and preserves the prior weights and provenance. Its
new source block distinguishes locally computed XML hashes from API-reported
archive digests. Replaying this run's measured work with the previous weights
assigns approximately 4,514–8,125 case-seconds per PR shard; the refreshed
assignment is approximately 6,390 per shard. These sums overlap across workers
and do not predict wall time. A subsequent CI run must establish the observed
effect on completion time. Shard counts, test collection and required checks
are unchanged.

The November 4 snapshot uses PR run
[41438863804](https://github.com/bridge2ai/data-sheets-schema/actions/runs/41438863804)
at `80fbca8b746ac411bbe96ea9de8543a6f3a7b821`: 21,882 ordinary testcase
occurrences in 607 files. Five shards supplied completed JUnit files. Shard 4
was cancelled at the job deadline with 3,975 passes, 11 skips and one case
without a completed result. Its available timings are estimates from consecutive
result timestamps on each worker, including setup, prior teardown and scheduling
delay. The one unfinished case uses its completed local JUnit duration, 200.986
seconds; `source.supplement` identifies that case and hashes both supplemental
inputs. This mixed snapshot is not evidence that the cancelled CI run passed.

The [round-8 refresh helper](../scripts/adhoc/refresh_pr5212_ci_timings_20261102.py)
checks each input's node multiset against the plugin's old partition and passes
the observations through the unchanged timing updater. It adds 32 previously
unweighted files and retains any unmeasured old entries. The resulting six-way
partition has about 6,408 case-seconds per shard; the four-way partition has
about 9,612. These totals overlap across four workers. A simple scheduling model
with an empirical startup/overhead allowance projects about 29.4 and 42.8 minutes
respectively, below 80% of the existing limits. These are estimates, particularly
for the incomplete shard; subsequent CI must establish actual completion times.
The [collection checker](../scripts/adhoc/check_pr5212_ci_partition_20261102.py)
verifies both real layouts without executing full shards. Tests, lanes, deadlines
and the partition algorithm are unchanged.

The preceding snapshot comes from successful main run
[41148135309](https://github.com/bridge2ai/data-sheets-schema/actions/runs/41148135309)
at `4c07980399d47d77b64c9f2bff7a50bfc5cc6ddf`: 20,801 testcase occurrences in
575 files, including 51 files absent from the previous snapshot. Recorded case
times sum to 27,148.941 seconds. The four core XML hashes, saved archive digests,
run provenance and occurrence counts are recorded in the
[refresh evidence](../notes/ci_timing_refresh_2026-10-31/timing-refresh.json).
Report admission now has a 2,697.097-second weight, and the API-runner weight is
2,988.490 seconds. For the collected main ordinary lane, the refreshed assignment
estimates about 6,787.2 case-seconds per four-way shard or 4,524.8 per six-way
shard. These are scheduling estimates, not wall-time predictions. The
[offline comparison](../notes/ci_timing_refresh_2026-10-31/README.md) also adds
the ten v5 test files from #5364 using the median fallback. Tests, lane boundaries,
deadlines and gates are unchanged; CI runtime improvement remains unmeasured.

An earlier snapshot comes from successful run
[38158491197](https://github.com/bridge2ai/data-sheets-schema/actions/runs/38158491197)
at `df2aa6c663c8d5712e3bd51885a6806f00982d79`: 18,848 testcase occurrences in
524 files, including 243 files absent from the previous snapshot. One legitimate
parameter-label collision contributes both occurrences and both durations. The
four core artifact hashes and source provenance are recorded in the
[refresh evidence](../notes/agent_performance_2026-10-12/timing-refresh.json).
Recorded case times sum to 22,354.104 seconds. The six-shard weighted assignment
estimates about 3,726 case seconds per shard; these totals overlap across workers
and are not wall-clock predictions. Tests added or changed after this run may
have different costs. The prior 5,209-case/281-file snapshot and earlier optimization
are documented in the [dated review](../notes/ci_efficiency_review_2026-09-15.md).

To update after a successful run, download all of that run's shard artifacts for a
single Python version into a fresh directory. Verify the completed run, commit,
interpreter and complete artifact roster against GitHub's metadata, and retain
the archive/XML hashes with the refresh evidence. For example:

```sh
gh run download 35009501429 --repo bridge2ai/data-sheets-schema \
  --dir /tmp/d4d-ci-timing-snapshot
python utils/update_ci_shard_timings.py /tmp/d4d-ci-timing-snapshot \
  --run-id 35009501429 --commit 893e9e941d3ea860c3c0f8861cc1ba64432dd4ae
```

The updater maps JUnit class names to repository test files, retains artifact
hashes and the supplied source run identity, and refuses failed or unmappable
cases. Parameterized cases can share a JUnit label within one artifact; each
occurrence contributes its recorded time and counts toward `source.test_cases`
(#5020). A label appearing in different artifacts, repeated resolved input paths,
or copied XML bytes is rejected. Do not deduplicate or rename downloaded records.

The run ID and commit arguments are caller-supplied labels, not authentication.
Duplicate checks do not detect disjoint XML files mixed from different runs or
interpreters, so the external provenance check above remains necessary. Offline
lane XML is retained separately and is not included in this core refresh: the
updater reads only files named `pytest.xml`.

Review and commit the resulting timing snapshot. Refreshing it is optional for
new tests; coverage never depends on a timing entry.


## Required long API, SG2 and native cases

The workflow opts into `--ci-lane=ordinary` for the existing shards and one of
twenty-seven dedicated lanes for long offline API, SG2 and native cases. All jobs collect `tests`.
`utils.pytest_shard.API_CASE_LANES` is the single exact node roster for dispatch,
portable completed capture, regated report, and default-layout completion.
`DEDICATED_CASE_LANES` combines that roster with `SG2_CASE_LANES` and
`NATIVE_CASE_LANES` (three public-path and seventeen failure cases).
`partition_lanes` requires all twenty-seven exact nodes once before returning singleton
case lanes and the complete ordinary complement. A missing, renamed or repeated dedicated
target fails collection. Ordinary parameter IDs may collide: every occurrence
is retained, with its original order and one owning shard, and coverage is
compared as a multiset rather than a mapping. Newly added tests stay ordinary automatically, including
new tests in the same API file. Timing data cannot select or omit a case.

No `--ci-lane` means the original full/default or file-sharded behavior. The
ordinary lane requires a shard; dedicated lanes forbid shard/timing flags and
multiple workers. Each dedicated case must pass setup, call and teardown without
skip or xfail (including non-strict XPASS). Collection alone cannot pass a case
lane. The existing skip and failure behavior of ordinary tests is unchanged.

Dedicated jobs preserve checkout history, submodule setup, the Python 3.12 project
environment and bytecode prefix. They retain JUnit plus streamed text output in
separate `tests-py3.12-api-<lane>`, `-sg2-<lane>` and `-native-<lane>` artifacts for 14 days, even when a failed test
does not complete JUnit. A hard runner cancellation can still prevent upload.
The aggregate requires the entire API, SG2 and native matrices to succeed on PR, main and
manual events, as well as the existing jobs. PRs have 25 + 17 = 42 Python jobs
(12 ordinary + 4 API + 3 SG2 + 20 native + 3 offline), plus the expected
schema/example skip. Main/manual have 21 + 17 = 38 Python jobs
(8 ordinary + 4 API + 3 SG2 + 20 native + 3 offline), plus the schema/example build.
Across PR, manual and the separate large-files check this is 42 + 38 + 1 + 1
= 82 required job successes and one expected skip, excluding aggregate checks
and unrelated automation.

## Native cases (#6191, 2026-11-13)

`NATIVE_FAILURE_CASE_LANES` isolates all seventeen cases in
`tests/test_native_shared_execution_failure.py` as `native-failure-01` through
`native-failure-17`. Each builds the expensive native fixture.
`NATIVE_CASE_LANES` puts the three public-path cases first, then these failure
cases, in the existing `native-public-completion` matrix. Display names are
`Python 3.12 / native case <lane>` and match the v2 launch-evidence roster.
The aggregate dependency list and its exhaustive truth-table size are unchanged.
The failure file has no ordinary cases; its retained historical weight is ignored
by ordinary partitioning. Isolation does not fix failures within those tests.

`NATIVE_PUBLIC_CASE_LANES` names three tests that each drive one complete
synthetic native launch: capture, guard preparation, admission, reservation,
dispatch and the completion gates. In ordinary shards beside xdist workers they
missed the 900-second capture-to-reservation window (the 1,200-second maximum
capture age less the 300-second margin) and starved their shard: shard 4 of run
43394245660 was cancelled at 45.4 minutes. Alone on
the lead's macOS host at load average 31, capture to reservation took 246 s and
the whole test 512 s. Each case now runs in its own job and one process, like
the API and SG2 cases. Their files' other tests stay in the ordinary shards;
the files' timing weights still include the moved case until the next timing
refresh.

This change responds to the actual 45-minute PR shard timeout in run37452512623.
All four cases passed concurrently in manual run37452622408; their per-test times
must not be added as wall time. The longest observed case took about 36 minutes,
so isolation reduces job competition without guaranteeing success under any
runner load. Test bodies, runtime deadlines and scientific/provider settings are
unchanged. Validate actual subsequent CI before claiming a speedup or completion.

## SG2 isolation and #5213 CI refresh (2026-11-05)

Three additional 45-minute jobs select exactly `sg2-none`, `sg2-conventional`
and `sg2-explicit`. Each runs one root-launch registration case, subject to the
same no-skip/no-xfail/no-collection-only outcome gate as the API lanes. Their
`tests-py3.12-sg2-<lane>` artifacts retain JUnit and streamed output for 14 days.
The aggregate requires both dedicated matrices; D81's 8/6 ordinary shards and
D75's 45/60-minute limits are unchanged.

`refresh_5213_weights_ci_20261105.py` uses retained run 41990198212 artifacts.
Of 25 local-override files, 18 have CI JUnit sums (the lead's 14 counted only
files whose previous weights exceeded one second). Seven unmeasured files use
local time times 2.1033. Registration first subtracts its three original local
SG2 durations because these cases now have dedicated jobs. All 635 other weights
and historical provenance remain unchanged. The new provenance records input
hashes and every before/after value. These estimates do not turn the cancelled
shard into successful-run evidence. Predict ordinary loads as case-seconds / 4;
use 0.92 for the historical main-weight sensitivity and do not multiply newly
CI-measured or already-scaled weights by 2.1 again. Single-case duration and
setup/scheduling overhead can dominate that idealized average.
