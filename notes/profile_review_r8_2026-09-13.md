# Profile review follow-up — 2026-09-13

This resolves #1733 and #1734 on top of the profile stage. File identity
entries retain their path and hash keys, including explicit null values
that record an unused input or a missing file. Removing a hash from a
present entry, or part of a profile identity, refuses a resume. The original
bundle/source-manifest/chunk keys remain mandatory; the documented legacy
omission of the entire profile remains comparable. Usage ledgers, phase
reuse and snapshot activation all apply the same comparison.

Strict run audits report malformed prompts, request blocks and render
specifications with the record label and project, continue to other records,
and exit unsuccessfully even when every selected record is malformed.

The initial regressions reproduced 16 failures with four controls passing.
The corrected profile and usage-ledger suite passed 161 tests. After
integrating profile compatibility commit b1d04ab0, 35 focused checks passed,
including null-input compatibility and malformed-only audit selections.

Both agentic and API generation arms use these guards. Presence, semantic
rubrics, API judging, deterministic checks and pair review remain in the
registered plan. No production generation, rescore, evaluator spawn or source
download occurred in this follow-up; there is no newly quoted evaluator
definition SHA. Existing instrument text and measurements are preserved.

Source identities for review:

- `src/data_sheets_schema/usage_ledger.py`: SHA256 `f5e1b43620614d72bce008973f4588d53734042eecbe0e6fe191190f45c17af1`
- `src/data_sheets_schema/cli/runs.py`: SHA256 `b0beb0ba3d42031fc79aeffb029022e505294236ed5012ee475b70af5aa45236`
