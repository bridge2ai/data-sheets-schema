# Captured rubric association, issue #4639

The existing planners captured `rubric_join_jobs`, but the support/fitness index
did not compare those result declarations with the selected record. The opt-in
index v3 checks that association from captured bytes and retains each primary
job's missing, conflicting or unsupported state in the denominator.

The normal fitness descriptor captures only its own reconstruction inputs.
An explicit `--rubric-plan` therefore supplies missing rubric blobs from the
exact plan named by the descriptor; it cannot substitute another manifest or
follow historical paths. Rechecking the resulting index requires no original
plan directory.

This is an engineering association check, not rubric acceptance, score
extraction or a campaign result. Instrument hashes remain declared identities;
no canonical resource-byte authentication is inferred. Human review, empirical
calibration and paid-run holds remain unchanged. Parents #2929, #3342 and #3343
remain open.

Independent review finding [#4645](https://github.com/bridge2ai/data-sheets-schema/issues/4645)
identified an optional roster output hash that was not compared with captured
result bytes. The correction retains the exact declaration, reports a valid
hash conflict as `mismatched`, and preserves malformed-pin diagnostics alongside
other conflicts. Missing results remain missing. This adds a declared byte
identity check without implying authenticated evaluator execution.

See [the command and state contract](../../docs/top-level-fitness-results.md#captured-rubric-identity-declarations-index-v3).

Validation is pending independent review and the coordinator's serialized test
run. No provider calls, scientific ratings or historical rescoring are included.
