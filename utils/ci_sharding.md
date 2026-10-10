# CI test partitioning

Every pull request runs the complete collected suite, including corpus tests,
on six Python 3.12 shards. Main and manual runs use four Python 3.12 shards
and one separate schema/example build. Three additional Python 3.12 jobs run the
complete offline canary, audit/finalization and evaluation suites alongside the
shards. Budget and native transport controls run once in the canary job, with
the same 45-minute job limit and existing test deadlines, rather than sharing
the time left after a full suite shard (#4466). Four more jobs each run one required long offline API case, with the same
45-minute limit (#4517). There are thirteen Python jobs on PRs and twelve on
main/manual runs, plus the aggregate `test` job. The aggregate
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
cores selected by `-n auto`. The subprocess coverage proof exercises this
worker configuration and both partition sizes. Every collected test remains included.

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
produce the same assignment. Every ordinary test in a file remains together; the four separately scheduled
API cases are removed by the explicit lane partition before file balancing.

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

The current snapshot was refreshed from successful four-worker run
[35061852492](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35061852492)
at `44836e190060fe07b262c948dead269d604c4014`: 5,209 cases in 281 files.
After the cache optimization, the old four-shard assignment accumulated 1,219.9,
1,064.8, 1,192.5 and 655.7 case seconds. The six-shard assignment estimates 688.8
per shard. See the [dated review](../notes/ci_efficiency_review_2026-09-15.md).

To update after a successful run, download all of that run's shard artifacts for a
single Python version into a fresh directory. Mixing interpreter versions or
runs is rejected when their test identities duplicate. For example:

```sh
gh run download 35009501429 --repo bridge2ai/data-sheets-schema \
  --dir /tmp/d4d-ci-timing-snapshot
python utils/update_ci_shard_timings.py /tmp/d4d-ci-timing-snapshot \
  --run-id 35009501429 --commit 893e9e941d3ea860c3c0f8861cc1ba64432dd4ae
```

The updater maps JUnit class names to repository test files, retains artifact
hashes and the source run identity, and refuses failed or unmappable cases.
Review and commit the resulting timing snapshot. Refreshing it is optional
for new tests; coverage never depends on a timing entry.


## Required long API cases

The workflow opts into `--ci-lane=ordinary` for the existing shards and one of
four dedicated lanes for each long offline API case. All jobs collect `tests`.
`utils.pytest_shard.API_CASE_LANES` is the single exact node roster for dispatch,
portable completed capture, regated report, and default-layout completion.
`partition_lanes` requires all four exact nodes once before returning singleton
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
separate `tests-py3.12-api-<lane>` artifacts for 14 days, even when a failed test
does not complete JUnit. A hard runner cancellation can still prevent upload.
The aggregate requires the entire four-case matrix to succeed on PR, main and
manual events, as well as the existing jobs. PRs have fourteen required successes
plus the expected schema/example skip; main/manual have thirteen successes.
Across PR, manual and the separate large-files check this is twenty-eight
required successes and one expected skip, without counting unrelated automation.

This change responds to the actual 45-minute PR shard timeout in run37452512623.
All four cases passed concurrently in manual run37452622408; their per-test times
must not be added as wall time. The longest observed case took about 36 minutes,
so isolation reduces job competition without guaranteeing success under any
runner load. Test bodies, runtime deadlines and scientific/provider settings are
unchanged. Validate actual subsequent CI before claiming a speedup or completion.
