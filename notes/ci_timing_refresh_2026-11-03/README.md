# BC1+G2 additive CI timings (#5485)

Parent `0ff5c9ba7665eb51b69e597c391cb1ae6a07c44c`; offline, 2026-11-03.
Fresh collection: 22,364 cases, 635 files; 22,360 ordinary cases and four
dedicated API cases. The 28 missing weights exactly match the collected files
added since `ddfd45c3b`. All 607 prior weights and their provenance are preserved.

The additions total 2,047.331 case-seconds: 19 files from BC1+G2 CI run
41707437114, three G1 files from run 41700664435, and six files from round-2
local **with** mode (macOS Python 3.13, two workers). Each file uses one source
with exactly its current collected case multiset; the 0.001-second floor remains.
Local times are unscaled. Per-file values, sources, artifacts and outcomes live
in `utils/ci_test_durations.json` → `source.bc1_g2_additions_20261103`.

[input-manifest.json](input-manifest.json) pins 23 XMLs, saved CI metadata,
the collection and original timing snapshot. The helper checks all hashes before
producing a result. These are lead-supplied saved inputs, verified offline;
no independent online provenance or successful whole-run claim is made.

| Plan | Case-seconds by shard | Estimated job seconds by shard | Heaviest margin below 80% limit |
| --- | --- | --- | --- |
| PR / six | 6749.257, 6749.257, 6749.257, 6749.257, 6749.257, 6749.257 | 2017.867, 2017.867, 2017.867, 2017.867, 2017.867, 2017.867 | 142.133 s below 2160 s |
| Main / four | 10123.886, 10123.885, 10123.886, 10123.885 | 2861.524, 2861.524, 2861.524, 2861.524 | 18.476 s below 2880 s |

Job estimates use file-weight sum / four CI workers + 330.553 seconds, the
largest observed job-wall-minus-JUnit-case-sum/4 allowance among completed
BC1+G2 shards 2, 3, 4 and 6. This includes observed setup/scheduling overhead;
it is not an exact xdist simulation. Main's margin is narrow. Local measurements
may understate CI: `test_shared_generation_runtime.py` totals 1071.593 local vs
2924.539 CI seconds (2.729×). No factor is applied. Actual CI remains unverified.

All slow `test_bc1_registration.py` cases land on **PR shard 5 / main shard 1**.
The two completed-run refusal cases take 473.733 and 457.549 local seconds;
the completed sizing/revalidation case takes 118.836. The slowest added case,
journal-before-parse, takes 568.115 seconds. Profile repeated full sizing and
pipeline reconstruction without weakening boundary/journal checks; the external
report records two issue candidates for the lead. No online issue action here.

Validation: **61 passed** (48 sharding, 13 timing-update), no failures/errors/skips,
252.62 pytest seconds / 253.07 supervised seconds. Outer pytest is serial,
nested xdist is capped at two, with a 3600-second process-group deadline.
The one-case canary persisted all four shard XMLs and their complete 64-case union.
Exact reproduction, both full collection multisets, preserved old values/source,
and altered-XML refusal with unchanged output all pass. Tests/workflows unchanged.

Reproduce from the repository root with the saved sibling evidence directories:

```sh
PYTHONDONTWRITEBYTECODE=1 python scripts/adhoc/refresh_ci_timings_bc1g2_20261103.py refresh
PYTHONDONTWRITEBYTECODE=1 python scripts/adhoc/refresh_ci_timings_bc1g2_20261103.py verify
```

Use the existing project dependency environment. `refresh` writes scratch only;
`--apply` additionally writes the weights. `run --label NEW-LABEL -- PYTEST-ARGS`
uses a fresh scratch evidence directory. No installations or network are needed.

Full report: sibling `plans/reviews/bc1_g2_ci_timing_2026-11-03.md`.
Raw logs, JUnit, all per-file source-coverage checks, assignments and verification:
sibling `scratch-bc1g2-timing/` (`measurement.json`, `verification.json`,
`collection/`, `canary/`, `focused/`). The saved XML inputs are read-only.
