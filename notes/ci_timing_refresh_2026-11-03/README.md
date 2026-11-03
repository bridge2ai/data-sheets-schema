# BC1+G2 additive CI timings (#5485)

The first section records the initial unscaled commit `6e578a600`; the current
derived weights and their reproduction command are in the follow-up below.

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

## Follow-up: measured-ratio scaling

The lead authorized **local sum × 2.729** for exactly the six local-source files.
Their values are **derived scheduling weights, not measured Linux runtimes**;
the other 629 weights and all original measurement provenance are unchanged.
`source.bc1_g2_measured_ratio_scaling_20261103` records each file's local sum,
multiplier, derived value, and both complete-file comparison totals/artifact hashes.

The comparison files are `test_shared_generation_runtime.py` (1071.593 local,
2924.539 CI seconds; ratio 2.729150899642) and `test_d42_claude_d55.py`
(1238.718 local, 3336.845 CI seconds; ratio 2.693789062563). The larger ratio
rounded to three decimal places is the explicitly requested **2.729**.

| File (`tests/`) | Local sum (s) | Derived weight (s) | PR shard | Main shard |
| --- | ---: | ---: | ---: | ---: |
| test_bc1_audit.py | 8.279 | 22.593391 | 6 | 2 |
| test_bc1_g2_journal.py | 577.396 | 1575.713684 | 6 | 2 |
| test_bc1_registration.py | 1063.186 | 2901.434594 | 3 | 3 |
| test_bc1_runtime.py | 46.966 | 128.170214 | 3 | 4 |
| test_g2_round2.py | 6.471 | 17.659359 | 4 | 4 |
| test_wave7_bc1_formatter_cache.py | 0.194 | 0.529426 | 6 | 2 |

Using the same case-seconds / 4 + 330.553-second formula, the heaviest PR
estimate is **2140.518100 s**, 19.481900 s below 2160. **Main exceeds the
2880-second threshold:** its heaviest estimate is **3045.500046 s**, an excess
of **165.500046 s**. D75's 45/60-minute limits remain unchanged; the decision
is the owner's. These are scheduling estimates, not observed Linux completion.
The journal-before-parse case lands on PR 6/main 2; both long registration
refusal cases land on PR 3/main 3.

Rerun: **61 passed** (48 sharding, 13 timing-update), zero failures/errors/skips;
246.62 pytest / 247.05 supervised seconds. The new-weight canary passed first.
The unchanged runner remains serial outside, at most two nested workers, and
bounded by 3600 seconds. Both plans preserve all 22,364 collected occurrences.

```sh
PYTHONDONTWRITEBYTECODE=1 python scripts/adhoc/scale_ci_timings_bc1g2_20261103.py
PYTHONDONTWRITEBYTECODE=1 python scripts/adhoc/scale_ci_timings_bc1g2_20261103.py --verify-tests
```

`--apply` additionally updates the weights; the default writes scratch evidence.
Current weights SHA256: `a554dc4277711297225ec79ba9b0dee0f83b5d6c98ed900cbff833814f90c499`.
Full tables and the second commit identity are appended to the existing external
report. Follow-up artifacts are in `scratch-bc1g2-timing/measured-ratio-scaling/`,
`scaled-canary/` and `scaled-focused/`; initial evidence is retained unchanged.
