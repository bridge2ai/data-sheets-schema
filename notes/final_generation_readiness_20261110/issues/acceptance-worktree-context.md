The first G2 focused cohort produced 22 passes and 2 failures in 10.37 seconds. `test_provenance_reads_both_declarations` read schema version 3.0.0, while the G2 source declarations and regenerated artifacts are 3.2.1. The release-history test compared unrelated schema hashes.

Evidence is retained in `d4d-executions/scratch-g2-2975-20261110/focused-pytest.log` and its JUnit file. The likely cause is invoking absolute test paths from the dirty primary checkout: setting PYTHONPATH alone does not override the resource resolver's current-checkout preference.

Verify and record the current directory, imported module paths and resolved schema paths. Run acceptance from the intended isolated worktree with worktree-first imports. Recheck the failed prerequisites before dependent checks; do not change schema versions/history or production resolvers to satisfy a wrong-environment invocation. This is a test-execution provenance finding, not an established schema defect.
