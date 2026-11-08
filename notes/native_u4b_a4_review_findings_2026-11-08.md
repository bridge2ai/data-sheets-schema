# U4b A4 local review findings, 2026-11-08

Offline findings ledger; no GitHub writes are authorized in this task.

- **A4-F1, P2, pending lead ruling.** The first proposed API packet delta selects
  the narrowed resource set for all shared-v1 runs. Historical shared-v1 needs
  the old set, and the constructor does not yet have the sole runtime capture.
  The initial scratch delta is retained as rejected, not offered for installation.
  The smaller correct design is a selection immediately after validated runtime
  binding in `native_execution_registration_v2.prepare`, before first rendering.
  That differs from the requested API packet revision, so scope clarification is
  pending. No production hook or frozen packet has been changed.
- **A4-F2, instrument limitation, retained.** The unchanged report-total v3
  instrument does not recognize `Findings: 2 high.` as an explicit global severity
  summary. `Audit severity summary: 2 high.` is recognized and must refuse its
  mismatch. Tests preserve both cases: unrecognized language is unavailable,
  never verified consistent. Broadening this shared scoring grammar is deferred;
  no prompt or instrument bytes were changed.
- **A4-F3, test harness interaction, addressed.** The cross-word no-process trap
  also trapped the new local registration-commit Git reads. It now permits only
  that offline Git invocation and continues to trap native/capture dispatch.
- **P3-7, instruction conflict, pending lead ruling.** The brief requests
  subscription/no-key observation, while the cited review requires
  `ANTHROPIC_API_KEY` for the deliberate local scripted-provider observation.
  The producer currently supplies a dummy API key, as does the bound permission
  verifier. Subscription quota captures independently require `none`. No auth
  route or observation check is silently changed while the ruling is pending.
