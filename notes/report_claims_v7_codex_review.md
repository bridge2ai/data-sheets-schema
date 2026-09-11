# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

Do not ship: four reproduced parser regressions hide contradictions or reject truthful reports. Corpus and audit totals reproduce; snapshot pins, preserved artifact bytes, and all five prior verdicts check out.

Findings:
- [medium] Keep schema attribution within its own sentence (src/data_sheets_schema/report_claims.py:96-103)
  For an `errata` table row, the reason “The core record says the slot was reviewed. This slot is not declared in the core schema.” produces no schema finding under v7. The attribution filter crosses the sentence boundary and exempts the report’s independent assertion. v6 correctly reports the false claim.
  Recommendation: Evaluate attribution separately for each schema assertion, stopping at sentence boundaries and independent clauses.
- [medium] Do not let an unsupported disposition terminate the table (src/data_sheets_schema/report_claims.py:808-810)
  In a Slot/Disposition/Reason table, place `keywords | Retained | Kept`, then `errata | Reviewed | No change needed`, then `distributions | Retained | Kept`. With only keywords populated, v7 reads one row and reports no findings; v6 flags distributions. The Reviewed row is mistaken for a header, silently discarding later claims while leaving enough parsed rows to pass the missing-table gate.
  Recommendation: Require positive evidence of a new header; continue scanning after unsupported dispositions and align the exclusion reader.
- [medium] Preserve full removals followed by core-absence context (src/data_sheets_schema/report_claims.py:434-436)
  The suppression audit loses `anomalies` for CHORUS 2026-08-13 generic rep1, although report line 382 explicitly says “removed from full, was already absent from core”. This helper treats the later core absence as making the entire clause core-only. Reproducing that statement with a populated snapshot and empty final records incorrectly yields removal_not_recorded. Thus the 107 losses include a regression.
  Recommendation: Associate each removal predicate with its own record; a core-absence aside must not cancel an explicit full removal.
- [medium] Resolve retention scope per predicate (src/data_sheets_schema/report_claims.py:1157-1163)
  “The citation remains in `citation` in the full record, and the keywords remain in `keywords` in the core record.” is truthful when citation exists only in full and keywords exist in both. v7 nevertheless flags citation with record=both because scope is inferred from the entire sentence. This triggers a false contradiction for a slot the core schema cannot hold.
  Recommendation: Resolve each retention predicate independently; require a shared both-record assertion before checking both records.

Next steps:
- Add the reproduced counterexamples and repair attribution, predicate scope, and table continuation.
- Recompute the corpus and reassess suppression losses after those fixes.
