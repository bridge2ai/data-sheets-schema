# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

Do not ship: the four original cases are fixed and refreshed audits reproduce, but five related parser regressions remain.

Findings:
- [medium] Schema attribution still crosses independent clauses (src/data_sheets_schema/report_claims.py:98-103)
  An errata reason cell saying “The core record says the slot was reviewed, while this slot is not declared in the core schema.” produces no findings. The attribution window crosses “while” and exempts the report’s independent assertion. CoreDataset declares errata, and v6 correctly reports false_schema_claim. With another valid disposition row, this contradiction passes the gate.
  Recommendation: End record attribution at independent clauses, including while/yet clauses, and test attribution separately for each schema predicate.
- [medium] Unlisted column labels hide an adjacent table (src/data_sheets_schema/report_claims.py:780-785)
  After a valid dispositions row, append an Item/Assessment/Action header, its separator, and a row containing backticked errata / Reviewed / Removed. With errata still populated in core, v7 returns one disposition row and no findings; v6 reports removal_not_performed. Only Assessment matches the label whitelist, so the second table remains excluded from the generic removal reader.
  Recommendation: Recognize new headers using structural evidence such as the following separator, while preserving continuation through unsupported data rows.
- [medium] Retention scope still absorbs a neighboring absence predicate (src/data_sheets_schema/report_claims.py:1180-1182)
  “The citation remains in `citation` in the full record and is absent from the core record.” is truthful when citation exists only in full. Nevertheless, v7 emits retention_not_shown with record=both; v6 emits none. The boundary requires recognized retention phrases on both sides, so the absence predicate incorrectly widens the retention scope and triggers regeneration of a truthful report.
  Recommendation: Resolve each retention predicate’s record independently even when neighboring predicates describe absence or removal.
- [medium] Coordinated retention verbs lose their shared negation (src/data_sheets_schema/report_claims.py:1183-1188)
  With errata and keywords absent, “No value remains in `errata` and stays in `keywords`.” now produces one affirmative retention claim and retention_not_shown for keywords; v6 reads zero claims. Splitting at “and” removes the shared subject “No value” before the second predicate’s negation check, turning a truthful negative statement into a contradiction.
  Recommendation: Preserve shared subjects and negation across coordinated verbs; reset negation only when the following clause establishes an independent subject.
- [medium] Active full removals are still canceled by core-absence context (src/data_sheets_schema/report_claims.py:425-427)
  “The full record drops `anomalies`, already absent from the core record.” yields removal_not_recorded when the snapshot contains anomalies and both final records omit it. v6 correctly records this removal. The repair recognizes only passive “removed/dropped from full” forms; the later core-absence predicate still overrides an explicit active full removal.
  Recommendation: Associate active and passive removal predicates with their own records before evaluating absence context; cover drop, omit, and remove forms.

Next steps:
- Add these counterexamples and repair attribution, table boundaries, predicate scope, and shared negation.
- Rerun parser tests and refresh corpus measurements and suppression comparisons after repairs.
