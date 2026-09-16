# CI efficiency follow-up — 2026-09-15

Issues: #1868, #1869. Starting commit: `f8c13691605e58829b8287b267726699732e8c04`.

## Measured baseline

Successful PR runs [35059976717](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35059976717)
and [35058408781](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35058408781)
took 8:00 and 7:40. They each ran all 5,200 collected cases on four Python 3.12
shards, plus 85 offline canary controls. The four suite steps in the first run
took 380, 362, 395 and 346 seconds. Poetry installation cost 13–18 seconds per
job despite an existing project-environment cache. The documentation job spent
14 seconds installing Poetry and 29 installing dependencies out of its 69 seconds.

The usage-ledger module accounted for 377 cumulative case seconds. Inspection
found that writing one output record cleared every parsed YAML document,
including unchanged schemas. A local profiled integration test spent 7.9
seconds in four parse-cache misses; profiling overhead means this is diagnostic,
not a wall-time prediction.

## Plan and coverage contract

1. Retain all collected tests on every PR, including the corpus, all existing
   Python 3.10/3.11/3.12 main/manual lanes, the separate schema/example builds,
   offline canary controls, full agent-definition history, and fail-closed `test` gate.
2. Use up to four logical CPU workers within each existing shard. GitHub's
   [standard public Linux runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
   supplies four CPUs; [xdist `auto`](https://pytest-xdist.readthedocs.io/en/stable/distribution.html)
   selected two physical cores in the measured runs. Verify actual runner
   behavior and elapsed time before accepting the change.
3. Share a Linux setup action across tests, builds and both documentation
   workflows. Cache Poetry 2.4.3 separately from the project, key environments
   by exact Python version and dependency inputs, and always install the
   current checkout. Preserve serialized documentation publication.
4. Invalidate parsed YAML for the written file and aliases without evicting
   unrelated schemas. Preserve bounded storage, deep-copy returns, read errors,
   same-timestamp invalidation, atomic replacement and concurrent invalidation.
   Keep the original parser and real integration paths.
5. Skip runner allocation for automatic events without an assistant mention;
   retain the existing actor authorization and manual lookup. Cancel superseded
   large-file checks for the same PR.
6. Compare JUnit identities and measured runner/wall time, review the final
   diff adversarially, address findings, merge after required checks pass,
   and delete the feature branch.

No downloads, model calls or scientific ratings are part of this work. Existing
canary worktrees, source bundles, prompts, schemas and measured outputs remain
unchanged. The package cache change must preserve validation and serialization.

## Validation and results

- The 151 unchanged usage-ledger, resume and profile tests passed before the
  cache change in 466.71 seconds on local Python 3.13.
- Both new regression probes failed against the original code: unrelated
  schema eviction and stale reads after same-metadata atomic replacement.
  All 28 cache, invalidation and digest tests pass after the change.
- All 20 partition and aggregate-gate checks pass, including the subprocess
  proof of complete, disjoint test coverage under the new worker setting.
- Workflow actionlint and diff whitespace checks pass.
- The local after comparison and real Actions measurements are pending.
