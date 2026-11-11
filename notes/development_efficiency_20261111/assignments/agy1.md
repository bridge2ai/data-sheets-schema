# E2 — implement the CI timing refresh

User authorized reducing development/test/CI time. Create an isolated sparse branch/worktree from7233f193ad named agy/ci-timing-refresh-20261111 (sibling d4d-executions/agy-ci-timing-refresh-20261111). Own utils/ci_test_durations.json and a small provenance helper/report only; no workflow, sharder, schema, prompt or protected-file changes.

Successful run42916359440 at6792947ea contains eight ordinary-shard JUnit artifacts. All18 jobs started within2–3s; shard5 test step36m00s, shard8 34m09s, shortest shard4 20m13s; dedicated routing-portable28m20s. Bulk timing weights still predate merged BC1 speedups. Use actual same-run XML records, not local-to-CI scaling or whole-job durations as case weights. Inspect the existing update_ci_shard_timings.py and its tests before designing anything new. Retain repeat-JUnit/case handling and complete collection.

Save any helper under scripts/adhoc and raw downloaded evidence in durable repo-local ignored scratch; one artifact first, inspect it, then the remaining seven small artifacts. No new environment. Prepare source and exact focused-test/check commands before requesting lead runtime slot. Independently downloading/reading small evidence is allowed now; no pytest/import-heavy profiling until grant. Compare old/new predicted assignment from the same measured data; label estimates as estimates. Do not change shard counts or remove tests to manufacture savings.

Commit locally, report exact SHA, source run/artifact identities, changed files, XML coverage, candidate validation commands and limitations in lead handoffs/agy1.md. No push, PR, merge or cleanup; lead will integrate after read-only review. Keep the report concise and make the concrete change, not another proposal-only document.
