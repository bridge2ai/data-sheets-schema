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
- Independent engineering review approved the change with no findings;
  [PR #1813](https://github.com/bridge2ai/data-sheets-schema/pull/1813)
  merged as `55327958ecd6e30e3afcf9eae2937f8e6b3a334e`. The feature branch
  and its worktree were removed. Issues #1812, #938, #1203 and #940 closed.
- The [PR run](https://github.com/bridge2ai/data-sheets-schema/actions/runs/34931494738)
  completed in 8:00, compared with 22:32 before sharding. Complete manual
  validation took 9:43 and the
  [post-merge run](https://github.com/bridge2ai/data-sheets-schema/actions/runs/34932451321)
  took 11:21. Each Python version recorded 4,841 passes and 15 skips, with
  all 4,847 original test identities retained and nine added CI guards;
  the 49 offline controls also passed. Full-matrix runner usage increased
  approximately 23–37%, while PR runner usage was essentially unchanged.

## Existing Aurelian pin — approved publication

The separate automatic Dependency Graph run failed to fetch the existing
Aurelian pin `05741290eb26e88e40dc43440940b228db8741cd` (#1814). After explicit
user approval, its exact two local commits were published as the persistent
[archive/data-sheets-schema-0574129 branch](https://github.com/monarch-initiative/aurelian/tree/archive/data-sheets-schema-0574129).
Only that branch was pushed. The parent dependency pin and existing local
checkout stayed unchanged.

The exact remote SHA was verified, and a fresh shallow, sparse checkout of
main `55327958e` successfully initialized its submodules recursively using
upstream objects. The old automatic run cannot be retried through GitHub
Actions; its historical failure is not a successful check. Issue #1814
remains open pending the next automatic Dependency Graph result. Preserve
the archival branch while the parent repository references this commit.
