# Local host power and suspension observations

Issue 6046 adds a read-only, bounded local probe before the launch sequence
claims its word or starts any native command. AC power must be positively
reported. Battery and unknown power refuse. Battery percentage and lid state
are recorded; a closed lid does not refuse AC operation. This check does not
replace the owner's confirmation or prevent a later unplug or lid sleep.

The exclusive `sequence-start.json` contains the reading even on power refusal.
The sequence source changes at its import and its one start-evidence call.
No runtime, registration, review-bundle or owner-term kind/version changes.
New source bytes still require new source pins and reviewed registration.
Guard v1 is unchanged.

The controller retains supplemental `host-clock-start.json`, one
`host-clock-stage-<journal-sha256>.json` per published stage journal, and
`host-clock-end.json` in its attempt directory. End observation runs after the
existing keep-awake cleanup, before final publication. `host-observation.json`
records the clocks, wall-minus-monotonic differences and bounded local pmset
sleep/wake events intersecting that interval. DarkWake closes a sleep interval;
subsequent maintenance sleep opens another. A wall-clock discontinuity alone
cannot distinguish sleep from a clock adjustment. An unavailable system log is
unknown, never evidence of no sleep.

These local sidecars are supplemental host observations, not model inputs or
an amendment to the closed captured-generation pool. They do not grant
acceptance, change runtime gate decisions, or authenticate the OS clock/log.
A host sleep remains a host event; its acceptance disposition is for the owner.
Retain the sidecars with the attempt for that review. Do not rewrite consumed
attempts to add them retroactively.

The offline proof runner uses the same positive-AC check and clock/event
recorder around each cohort. Its report distinguishes a stale observation after
recorded sleep from an ordinary freshness refusal. No power settings are changed
and no power assertion is acquired by this probe.
