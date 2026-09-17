# PR #2017 continuation review — 2026-09-17

The last Opus workflow ended because all three reviewers exhausted their
credits. Its empty findings lists are not completed reviews. Codex resumed
review of controls head `ff049dd884772bc4bb7813bfd29b46cfde540b01` against
`8d1cbb96ea01bb7ffde13a1c57b834266d97073c`, including the round-5 changes,
controller exits and the registration's acceptance claims.

Two reproduced controller findings are fixed:

- #2042: a controller interrupt or unexpected exception during token
  counting let shutdown record `native admission is closed` first. All
  controller-originated exceptions now use the existing locked pre-close
  record, preserving proxy and ledger causes. Regression tests use the
  real proxy, a synthetic child and fake counting; both interrupt and
  unexpected-error cases failed before the fix.
- #2043: `str.splitlines()` split valid Unicode separators inside JSON
  strings. The controller now reads physical UTF-8 JSONL lines. A complete
  synthetic run containing literal NEL, line and paragraph separators
  failed before the fix and passes afterward.

The recovered baseline runs passed 5,278 fast tests, 12 corpus tests and
109 offline tests. The updated controller, native proxy and receipt suite
passes 114 tests, with 10 API cases skipped because they exercise native-only
behavior. No provider generation or token-count requests were made.

The four README acceptance criteria retain their actual enforcement:

| Criterion | Evidence and decision |
| --- | --- |
| Receipt written after each chunk, before the next read | Independent review of original tool history; final receipt coverage alone is insufficient. |
| Strict receipt check passed before core derivation | Independent review of command order and tool results; the controller's final receipt check does not establish this ordering. |
| No denied prescribed command; forbidden denials listed | Controller classification from a single readable result line on completed and stopped paths. Missing/ambiguous result lines explicitly defer to tool-history review. |
| Stop reason and source, with durable ledger entry | Ledger/proxy/controller precedence, locked pre-close controller stops and non-raising diagnostics. A reported ledger-write failure is not accepted as a durable entry. |

Acceptance still requires independent source review of unchanged full/core
artifacts, evidence, provenance and report. Software test success is not
scientific acceptance. Hard termination or storage failure cannot guarantee
a final receipt; such an incomplete attempt remains unaccepted.

#2035 remains a documented scope limitation of the existing native overlay:
the `--manifest *` and `-c *` permissions are broader than the instructed
command roster. #2041 item 1 remains coupled to any future narrowing of those
permissions; its read-scope and public-transform items are fixed. Neither
permission policy is silently changed by this continuation.

#2044 tracks correction of the private, unexecuted launch-preparation draft.
The registration must pin these final controls, pass its own review and CI,
and remain unlaunched until the maintainer's separate launch instruction.
