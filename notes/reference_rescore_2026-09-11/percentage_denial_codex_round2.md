# Codex Adversarial Review

Target: branch diff against 79cc116099e1b95bdc03a1c2d54b7fbd46bec931
Verdict: needs-attention

Hold 335b152d5ea9033309e1617467229b8fb9a0d33d: two attestation bypasses remain. Python 3.9.6 imports, 42 tracked attestation cases and 16 in-memory reporting/audit scenarios passed. Full-suite and retained-candidate replays were not run.

Findings:
- [medium] [P2] Reject duplicate mutation IDs before clearing pending writes (scripts/reference_rescore.py:322-326)
  A synthetic stream containing Write(w,A), Write(w,B), result(w), successful exact validation, result(w), proven denial, then terminal success returns True at HEAD versus False at base. The pending set collapses both writes; the first result removes w, so the second write can finish after validation without revoking it. Using distinct write IDs correctly returns False. Ambiguous mutation evidence can therefore pass the candidate gate.
  Recommendation: Require unique, ordered use/result evidence for potentially mutating calls before applying denial exemptions. Add the overlapping duplicate-write regression.
- [medium] [P2] Revoke attestation when a separate validator reports failure (scripts/reference_rescore.py:335-342)
  Successful exact validation followed by a separate, uniquely identified validator returning is_error=True with an INVALID result, then a proven denial, returns True at HEAD versus False at base. Both validators satisfy the new uniqueness/order checks, but consuming the failed result never clears validated. The denial therefore preserves attestation despite contradictory executed validation evidence.
  Recommendation: Invalidate attestation on an executed validator failure or missing success marker, preserving the exemption for proven nonexecution denials. Add conflict regressions using distinct validator IDs.

Next steps:
- Fix both evidence-handling gaps and rerun focused tests on Python 3.9, followed by the authorized retained-candidate replays.
