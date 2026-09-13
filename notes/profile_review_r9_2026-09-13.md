# Recovered profile review — 2026-09-13

This follow-up to the profile stage resolves the remaining findings in the
recovered Claude/Codex round-8 report: #1740, #1741, #1742, #1743, #1744 and
#1745, alongside the interrupted-resume fixture correction #1749.

Historical records with no explicit profile are compared under the same
fallback used by record readers. Backfill checks the proposed specification
against recorded digest evidence before reporting success or writing. Explicit
malformed profiles and malformed mapping/date fields get a named CLI error.
Damaged identity pins are not described as historical instruments unless they
carry evidence of that history. Null observations still compare with themselves;
changed observations and incomplete file/profile pins remain refused.

The subset-compatibility fixture now omits optional render metadata instead of
an original file-identity field. It still exercises the real interrupted API
resume, retains the input and instrument pins, and checks phase/accounting reuse.

Validation: the six recovered fixes initially reproduced 22 failures with four
controls passing. The broader profile, ledger and interrupted-resume suite passed
204 tests with one outdated fixture failure; after correcting that fixture, all
36 profile-review and interrupted-resume tests passed. Earlier #1733/#1734 checks
remain in the suite. These tests use synthetic records and an offline client.

Condition boundary: the current agentic workflow comment now uses generic
clinical-cohort and imaging-study examples. Its bytes change at this boundary;
archived instructions and measured outputs remain intact. API and agentic arms
remain in the registered plan, together with presence/completeness checks, both
semantic rubrics, API judging, deterministic validation, pair review, report
claims and receipt checks. This follow-up runs no production generation, rescore,
evaluator spawn or download, so there is no new evaluator-quoted definition SHA
or newly scored record set. The existing v7/v8 results and their instrument
attributions are preserved.

Current source identities for the next review:

- `.github/workflows/d4d_assistant_create.md`: SHA256 `01ef46b7e35f36ee0df4fc0ba472a6d3faa55f8ce02850715acdccba1a7e1273`
- `src/data_sheets_schema/cli/provenance.py`: SHA256 `79931948c6c8af77cf1a216f6121334655f86e57ab788f6551bac175c27cddee`
- `src/data_sheets_schema/cli/runs.py`: SHA256 `cf90c7ae43ad2ddb876a7f15fdebf2047e036fe787793736dd01ba267f7b5683`
- `src/data_sheets_schema/provenance.py`: SHA256 `1723cea76f2aae6c63d8ccda46a4b6fff26d59d33dedcdcd87432d03e4dd02df`
- `src/data_sheets_schema/usage_ledger.py`: SHA256 `ff525befba9d8867d2a4f345c7423e8d8849227d63abcba6d5af37a21dca7016`
