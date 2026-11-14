# U4b A4 local review findings, 2026-11-08

Offline findings ledger; no GitHub writes are authorized in this task.

- **A4-F1, P2, replacement proposal authorized.** The first proposed API packet delta selects
  the narrowed resource set for all shared-v1 runs. Historical shared-v1 needs
  the old set, and the constructor does not yet have the sole runtime capture.
  The initial scratch delta is retained as rejected, not offered for installation.
  The smaller correct design is a selection immediately after validated runtime
  binding in `native_execution_registration_v2.prepare`, before first rendering.
  The user approved that alternative scratch-only proposal. No production hook
  or frozen packet is changed; genuine composition, replay and D76 verification
  remain required before applying it and regenerating preparation/registration.
- **A4-F2, instrument limitation, retained.** The unchanged report-total v3
  instrument does not recognize `Findings: 2 high.` as an explicit global severity
  summary. `Audit severity summary: 2 high.` is recognized and must refuse its
  mismatch. Tests preserve both cases: unrecognized language is unavailable,
  never verified consistent. Broadening this shared scoring grammar is deferred;
  no prompt or instrument bytes were changed.
- **A4-F3, test harness interaction, addressed.** The cross-word and inherited
  capture tests patched the shared stdlib subprocess module, so their traps and
  counters also intercepted new local registration-commit Git reads. The shared
  component fixture now gives capture its own Popen/PIPE/DEVNULL proxy. All
  existing capture traps remain strict; the real stdlib Git reader remains
  untouched. An explicit isolation regression verifies both properties.
- **P3-7, instruction conflict, resolved by user ruling.** The brief requests
  subscription/no-key observation, while the cited review requires
  `ANTHROPIC_API_KEY` for the deliberate local scripted-provider observation.
  The producer currently supplies a dummy API key, as does the bound permission
  verifier. The user selected the scripted-provider key source for observation;
  the observation consumer now requires exactly `ANTHROPIC_API_KEY`. Subscription
  quota captures independently retain `none`. Missing/wrong/rehashed evidence
  and the distinct two-route contract have explicit regressions.
- **A4-F4, validation protocol, open.** The monolithic U5 derivation invocation
  exceeded its 3600-second limit: the retained supervisor reports 4338.210798 s,
  deadline termination, forced cleanup, no observed survivors and
  `cleanup_verified: false`. No completed JUnit/worker result exists. Its cause
  is not established. The run is excluded from completed-test counts and retained;
  unchanged smaller invocations replace it without erasing the protocol failure.
- **A4-F5, regression quality, addressed before execution.** Independent review
  found that the rehashed observation-auth test also changed the terminal row's
  whitespace. It now changes only the init row and asserts the terminal's
  original bytes and SHA remain exact, isolating the auth-source refusal.
