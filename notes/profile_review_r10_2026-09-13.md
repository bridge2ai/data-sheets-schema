# Profile fallback digest review — 2026-09-13

Follow-up review #1751 found that accepting the historical profile fallback
also requires checking its digest evidence. The digest comparison now uses
the same effective profile as record readers. An omitted/null profile carrying
the opposite current digest is refused; a matching fallback digest and unknown
historical digests retain their established interpretation.

The new tests reproduced two failures with four controls passing. All 122
profile and reconstruction tests pass after correction. Independent review
confirmed the resume comparator was not weakened by the preceding changes.

This corrects instrument validation for both generation arms and all registered
evaluation styles. It changes no rubric or measured artifact; no production
generation, evaluator spawn, scoring or download occurred. No evaluator-quoted
definition SHA or newly scored record set is introduced.

Current source identity for review:

- `src/data_sheets_schema/provenance.py`: SHA256 `5d1ed4618e2fc7d10586f609043eeb6ebc14e92507d796681e206335c751130f`
