# Packaging final-review corrections — 2026-09-13

The completed Codex round-7 review of packaging parent 53359f583 found #1747
and #1748. Both are corrected in this follow-up.

Repair convergence now records the prior artifact's readability before
replacing it. Turning four parser diagnostics into five structured findings
can proceed to a second repair; the established non-convergence stop still
applies within one finding class. A synthetic streamed client exercises the
actual repair controller and records both attempts.

Installed provenance reads the real distribution RECORD and reports deleted
shipped METADATA, WHEEL, entry points, licenses and arbitrary nested metadata
as changed. Only the named installer files (RECORD, INSTALLER, REQUESTED and
direct_url.json), root .pth and bytecode caches retain the bookkeeping rule.
No caller repository or live environment is used as replacement evidence.

Validation: six regressions failed before correction and four controls passed.
After correction, 97 resource/package checks passed with one unrelated skip,
including fresh-wheel tests enabled with D4D_INSTALL_TESTS=1. Twelve focused
repair/metadata checks also passed, including existing convergence controls.
All mutable fixtures and wheel installs are temporary; the shared environment
and measured corpus are preserved.

Both generation arms and all evaluation styles remain in the registered plan.
This changes repair behavior and installed software evidence, not rubric text.
No new production generation, score, evaluator spawn or source download ran;
there are no newly scored records or evaluator-quoted definition hashes.

Source identities:

- `src/data_sheets_schema/api_runner.py`: SHA256 `fcba891a630e0312999ec0c1a548fbb0b86d18d4d53fd45b8b845c476b4d86de`
- `src/data_sheets_schema/provenance.py`: SHA256 `e0ebb57a6d60502b3d5132dd4456716f53d7b9a1ae208975f231e87ab8656dd8`
