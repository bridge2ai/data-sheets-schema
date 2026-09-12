# Codex Adversarial Review

Target: branch diff against b3f5b7f5d15bb9cea9ed784675b55d949e593e4f
Verdict: needs-attention

Do not ship yet: evaluator validation receipts can attest an earlier output version instead of the published bytes.

Findings:
- [medium] [P2] Bind validator success to the final output write (scripts/reference_rescore.py:243-248)
  The first matching success returns immediately. Write(A) → validate(A) → Write(B) is therefore accepted, even if B’s subsequent validation fails; an in-memory replay confirmed this. Recovery checks that the candidate matches the last successful Write (lines 496–518), but never connects that write to validation. A schema-valid B can consequently be published with an incorrect exact-output evaluator attestation. The runner’s separate validation does not establish that the evaluator validated B.
  Recommendation: Require a matched validator call after the final successful output write, bound to the candidate bytes. Add regressions for a later write with no revalidation and with failed revalidation.

Next steps:
- Fix final-output attestation and rerun the focused offline tests.
