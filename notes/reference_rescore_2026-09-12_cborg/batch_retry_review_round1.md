# Codex Adversarial Review

Target: branch diff against 5dc745e6a
Verdict: needs-attention

Do not ship: missing reviewed-attempt history bypasses the retry gate.

Findings:
- [medium] [P2] Validate registered retries even when attempt history is missing (scripts/reference_rescore_cborg_batch.py:111-114)
  If the rejected pilot directory is lost or removed, leaving its parent absent or empty, this condition skips verify_reviewed_retry and queues the pilot. Both controller and worker use this path, so after pre-spend approval another paid launch can proceed without the exact failed inventory that approval covers. Reproduced in memory using the committed registration: both missing and empty histories were allowed. The completion audit's later preservation check cannot prevent that spend.
  Recommendation: Always validate jobs listed in reviewed_retries, regardless of directory existence or contents. Reject missing or empty history against the registered inventory and add regression cases for both.

Next steps:
- Fix the missing-history bypass and rerun the offline scheduler checks. HEAD remains da16f9072; no files were edited.


Recorded as #1344. No retry or fill launched; refresh registration and review after closing the missing-history bypass.
