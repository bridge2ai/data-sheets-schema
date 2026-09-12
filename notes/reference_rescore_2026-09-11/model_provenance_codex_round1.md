# Codex Adversarial Review

Target: branch diff against 08db9f062171335fe68f1aa3d144545545db555c
Verdict: needs-attention

Block de7f6ee: restoring a missing passed rating creates duplicate receipts and prevents resume/reporting.

Findings:
- [medium] [P2] Preserve receipt uniqueness when restoring a passed rating (scripts/reference_rescore.py:496-498)
  Reproduction: retain a current-registration passed CLI attempt, remove only its published output, then call recover_rating(manifest, source). The missing destination bypasses the existing-receipt guard, and recovery returns passed while creating a second matching receipt. successful_receipt() then raises 'no unique successful receipt', blocking report/remaining; retrying recovery is also refused. Confirmed using the published functions with an in-memory filesystem and successful-validation stubs.
  Recommendation: Check current-registration passed receipts even when the output is absent. Restore validated bytes while reusing the matching receipt, or reject before publication; never create a duplicate pass.

Next steps:
- Add canary and non-canary regression tests for missing-output recovery and receipt uniqueness.
