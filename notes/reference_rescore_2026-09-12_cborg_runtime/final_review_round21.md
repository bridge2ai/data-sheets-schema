# Independent final review — round 21

Reviewed committed HEAD `3902d6b523711e5d4a6ea08803536526dc4aea37`.

# Codex Adversarial Review

Target: branch diff against e0a2459bc1688b4293d491f4391cb08ec5a9b2a0
Verdict: needs-attention

Block on one reproduced P2 recovery failure. Public evidence reconciles and HEAD is unchanged. Failure probes used in-memory fixtures.

Findings:
- [medium] [P2] Retain backups when rollback is interrupted (notes/reference_rescore_2026-09-12_cborg_runtime/execution_tools/write_completion_summary.py:84-90)
  Reproduced with the committed functions: publish results.json, fail the second publication rename with ENOSPC, then raise one KeyboardInterrupt immediately after the first rollback rename. Rollback catches only OSError, so cancellation escapes without setting retain. The finally block deletes staging, including the last link to the original results.json inode, leaving its replacement published without a recovery backup or location-bearing error. The added interruption test covers publication, not rollback.
  Recommendation: Retain backups once publication begins until publication or complete rollback is confirmed. Surface interrupted recovery with the retained backup path, and add an ENOSPC-then-KeyboardInterrupt regression.

Next steps:
- Fix interrupted recovery and rerun the focused reporting/publication suite with two workers.


## Disposition

The supported P2 is tracked in [#1360](https://github.com/bridge2ai/data-sheets-schema/issues/1360). Cleanup is now permitted only before publication starts or after publication or complete rollback is explicitly confirmed. Interrupted rollback retains recovery files and identifies their location. The regression injects ENOSPC at the second publication rename and then cancellation immediately after the first rollback rename.

This correction affects reporting recovery only. All 981 inventoried measurement files, original instrument and registration hashes, 56 accepted outputs and manuscript qualifications remain unchanged. Round 21 remains a blocked verdict; a separate independent review must inspect the corrected commit before merge.
