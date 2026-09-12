# Codex Adversarial Review

Target: branch diff against 2544c2913bb6f4531670cef863392abdbfc65fe1
Verdict: needs-attention

Hold 102232165 for two P2 accounting defects reproduced in memory. HEAD and origin match the supplied commit; a fresh public-ref check was network-blocked.

Findings:
- [medium] [P2] Validate recovery references before excluding their sessions (scripts/audit_reference_rescore.py:39-42)
  Recovery receipts are silently skipped based only on three fields; recovered_from and its evidence hashes are never checked. If a post-checkpoint original is lost and a successful retry supplies a different output, the retained recovery receipt does not expose the missing session. An in-memory regression with 56 current ratings and nonempty preservation records produced completion with 56 calls and no unresolved attempts despite a dangling recovery reference, omitting the lost session and its cost.
  Recommendation: Resolve each recovery reference to the same job's original attempt and verify its receipt/transcript hashes. Mark missing or mismatched evidence unresolved. Add a regression covering a lost original followed by a successful retry.
- [medium] [P2] Handle malformed interrupted artifacts per attempt (scripts/audit_reference_rescore.py:77-79)
  A timeout can leave an incomplete receipt with truncated JSONL; the existing quota-failure test also produces plain-text stdout. Inventory admits these sources, but unconditional JSON parsing aborts even an interim audit. The truncated-stream reproduction raised JSONDecodeError despite a successful retry. Interrupted receipt writes likewise crash inventory at line 31. One retained failure therefore prevents subsequent accounting reports.
  Recommendation: Handle malformed receipts and streams per attempt, preserve their evidence, and report unresolved outcome/cost while blocking completion where necessary. Add torn-receipt, truncated-stream, and non-JSON failure-output regressions.

Next steps:
- Fix both accounting paths and add the regressions, then perform the planned runner-pin amendment and offline revalidation before new model calls.
