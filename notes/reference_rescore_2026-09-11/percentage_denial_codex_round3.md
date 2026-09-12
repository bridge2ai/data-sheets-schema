# Codex Adversarial Review

Target: branch diff against 79cc116099e1b95bdc03a1c2d54b7fbd46bec931
Verdict: needs-attention

Hold 1c78955: delayed validator results can restore revoked validation. Python 3.9.6 imports and targeted reporting/preservation checks passed.

Findings:
- [medium] [P2] Clear pending validators when revoking validation (scripts/reference_rescore.py:343-345)
  Failure resets `validated` but leaves other validators in `calls`. Reproduced with unique, ordered IDs: start V1 → start V2 → V2 fails → V1 returns VALID → proven denial → terminal success. HEAD returns True; the base returns False. V1's delayed result restores attestation without any validator invoked after the contradictory failure. Missing-marker failures behave identically, and batched outcomes change acceptance depending on block order.
  Recommendation: Clear outstanding eligible validator calls on executed errors and missing success markers. Require a validator invoked after revocation to restore success, while preserving the proven-denial exemption.

Next steps:
- Add overlapping-validator and batched-result-order regressions, then rerun focused tests on Python 3.9.
