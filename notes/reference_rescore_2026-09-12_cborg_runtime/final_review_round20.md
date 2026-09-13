# Independent final review — round 20

Reviewed committed HEAD `e0a2459bc1688b4293d491f4391cb08ec5a9b2a0`.

# Codex Adversarial Review

Target: branch diff against 5f14512b70c1be785781878dfd8bcdf854ea0231
Verdict: needs-attention

Block on two reproduced reporting failures. Committed evidence and accounting reconcile, 20 targeted regressions pass, and HEAD remains unchanged.

Findings:
- [medium] [P2] Stage qualified reports before replacing published files (notes/reference_rescore_2026-09-12_cborg_runtime/execution_tools/write_completion_summary.py:200-203)
  The public report command writes raw results before attaching qualifications. Injecting persistent ENOSPC at the subsequent results.md write leaves results.json containing 56 completed ratings but none of the eight qualification keys. Rollback also requires writes to the failed storage; its first failure aborts restoration. Thus a publication failure can recreate #1356 and destroy the prior qualified report.
  Recommendation: Render and stage fully qualified outputs before replacing published files. Retain backups that can be restored without rewriting their contents, and test persistent write failures.
- [medium] [P2] Reject blank qualification text before publishing (notes/reference_rescore_2026-09-12_cborg_runtime/execution_tools/write_completion_summary.py:168-170)
  Changing only semantic_review.json's qualification to an empty string in an in-memory fixture makes the public report return success, publish an empty structured interpretation, and remove the original semantic warning from all three Markdown reports. The same succeeds for both narrative qualification files. Evidence bindings remain valid because validation checks cases and hashes but never requires nonblank qualification text.
  Recommendation: Validate every required qualification as a nonblank string before any report write. Add empty and whitespace-only fixtures asserting refusal and byte-identical prior reports.

Next steps:
- Fix these publication guards and rerun the public command regressions; preserve the existing measurements.


## Disposition

The two supported P2 findings are tracked in [#1357](https://github.com/bridge2ai/data-sheets-schema/issues/1357) and [#1358](https://github.com/bridge2ai/data-sheets-schema/issues/1358). The renderer now stages all four fully qualified reports before publication, retains original-file backups until replacements finish, and restores them by rename when possible. If the filesystem also refuses restoration, it retains backups and reports their location. Every required qualification must be a nonblank string before rendering.

This is a post-measurement reporting repair with no new model calls, scoring changes or restamped registrations. Round 20 remains a blocked verdict; a separate independent review must inspect the repaired commit before merge. See [validation](report_publication_validation_1357_1358.md).
