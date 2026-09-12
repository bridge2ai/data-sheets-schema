# Qualified-report rebuild validation

Recorded 2026-09-12T16:29:19.700526+00:00 for #1338.

- Five regressions pass in tests/test_reference_qualification.py: missing errata, malformed errata, a late rebuild exception, a keyboard interruption after writes, and a qualification failure that must restore prior reports and prior file absence.
- The missing- and malformed-errata regressions both fail against the published old helper at 691d1c05219118cc926522c0c3c1a389f5e1961c: it invokes the reporter and overwrites caveats before discovering the metadata failure.
- The corrected --rebuild command succeeds on the complete registered cohort. All four derived reports retain their qualifications. Applying qualification again is byte-idempotent.
- All 857 files in semantic_errata_preservation.json remain unchanged, including 56 accepted measurements, 202 prior evaluations, 565 attempt files and 34 pinned files.
- All JSON report content, including numerical statistics and semantic qualification metadata, matches 691d1c052 except the report-generation timestamp. The frozen runner and instrument are unchanged.
- No evaluator call, score rewrite or D4D generation occurred during the correction.

The helper validates errata, input/output hashes and completion/Write evidence before any report overwrite. It snapshots the four managed derived reports and restores their previous bytes or prior absence after a caught rebuild or qualification exception. The transaction covers ordinary Python exceptions and keyboard interruption; it does not claim recovery from process termination that cannot run exception handlers or unrecoverable filesystem failure.

Validation commands (repository root): python -m pytest -q tests/test_reference_qualification.py; python notes/reference_rescore_2026-09-11/execution_tools/qualify_reference_results.py --rebuild.
