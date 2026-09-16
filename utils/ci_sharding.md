# CI test partitioning

Every pull request runs the complete collected suite, including corpus tests,
on four Python 3.12 shards. Main and manual runs retain the wider interpreter
matrix and separate schema/example builds. The aggregate `test` check still
requires every applicable job to succeed.

Each shard uses `-n logical --maxprocesses=4 --dist worksteal`: up to four
workers on the standard public Linux runner, rather than the two physical
cores selected by `-n auto`. The subprocess coverage proof exercises this
worker configuration. The number of shards and the collected tests are unchanged.

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
produce the same assignment. Every test in a file remains together.

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

To update after a successful run, download that run's four artifacts for a
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
