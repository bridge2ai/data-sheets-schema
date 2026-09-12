# Codex Adversarial Review

Target: branch diff against 2544c2913bb6f4531670cef863392abdbfc65fe1
Verdict: needs-attention

Hold for two P2 audit/reporting defects. The 22 accepted outputs reconcile with their receipts; the remaining 34 jobs are intentionally pending.

Findings:
- [medium] [P2] Account for interrupted attempts without receipts (notes/reference_rescore_2026-09-11/execution_tools/audit_registered_results.py:26-30)
  The audit silently skips attempts lacking receipt.json. The runner writes that receipt only after subprocess work, so interruption can leave an attempted session invisible to call, exclusion, and cost accounting. After a successful retry, --complete can pass despite this unresolved evidence. An in-memory reproduction confirmed the silent omission; this is a failure-path defect, not an observed missing published receipt.
  Recommendation: Report unreceipted attempt directories as unresolved and reject --complete while any remain. Add an interrupted-attempt regression.
- [medium] [P2] Leave singleton applicability stability unmeasured (notes/reference_rescore_2026-09-11/results.json:53-57)
  The newly populated AI_READI row reports applicability_stable=true with only 1/3 ratings. report_results produces this positive flag whenever a singleton signature exists, although neither repeated rating has occurred. Consumers therefore receive a stability claim unsupported by repeated observations.
  Recommendation: Keep stability null/unmeasured until the registered repeated ratings support it. Correct the generator, cover partial cohorts, and regenerate both reports without changing scoring judgments.

Next steps:
- Fix both defects and add offline regressions before publishing the next checkpoint.
