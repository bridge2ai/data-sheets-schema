# CI optimization — 2026-09-15

Issue: #1812. Base: `147825e7610a75059891eb44817e3fe0def95999`.

The latest green PR run (34928794066) used two pytest workers and took
1,298.20 seconds for 4,832 passes and 15 skips. Setup took less than a minute;
the offline canary controls added 24 and 25 passing tests. The previous PR
run took 1,128.86 seconds to find a single stale assertion.

## Plan and coverage contract

1. Keep the complete pytest collection, including the committed corpus, on
   every PR. Split it deterministically across four jobs, with no test-file
   allowlist and no marker exclusion. Prove union/disjointness, parameterized
   and skipped test handling, xdist behavior, invalid arguments, and failure
   propagation on synthetic subprocess tests.
2. Keep the entire Python 3.10/3.11/3.12 main/manual test matrix. Run schema and
   example builds in separate jobs so their writes cannot change the inputs
   the Python tests inspect. Give each build its own timed step.
3. Keep the stable `test` aggregate; every applicable shard/build must succeed.
   Run the 49 independent offline canary controls once on Python 3.12.
4. Cancel superseded runs of the same PR. Main/manual runs have unique groups.
   Preserve JUnit files with per-test timings for 14 days.
5. Address measured redundant CLI work (#938), keeping process smoke tests
   where the boundary matters and fresh execution for tests which edit inputs.
6. Run an adversarial engineering review, address findings, verify real GitHub
   test totals and timing, merge, and delete the working branch.

## Scope and remaining questions

Scientific generation/evaluation code and pinned inputs are outside this
change. The frozen v10j worktree stays unchanged. This work needs no model
requests or CBORG spend. Sharding trades modest extra checkout/setup work for
shorter wall time; actual Actions timings must establish the improvement.

The Python `^3.9` declaration still differs from the existing 3.10–3.12 matrix
(#949). Resolving supported Python versions is separate from retaining and
accelerating the current coverage. The tracked merged-schema mtime behavior
in `make full-schema` (#939) still exists in build jobs, but can no longer
repair the committed input before the independently running pytest gate.

## Validation

- The same nine corpus CLI assertions passed before and after: 131.70 seconds
  before, 86.68 seconds after, on local Python 3.13 (34% less wall time).
  These are local measurements, not an estimate of complete Actions savings.
- 62 other affected schema/telemetry/prompt tests passed in 34.39 seconds.
- Eight synthetic partition/exit-status tests passed in 9.17 seconds; the
  aggregate-gate test separately passed all 48 dependency/event combinations.
- actionlint 1.7.7 accepted the workflow; `git diff --check` passed.
- Final independent review and complete GitHub timings/test totals will be
  recorded on #1812 and the pull request.
