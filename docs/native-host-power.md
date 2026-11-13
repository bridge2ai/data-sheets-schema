# Local host power and suspension observations

Issue 6046 adds a read-only, bounded local probe before the launch sequence
claims its word or starts any native command. AC power must be positively
reported. Battery and unknown power refuse. Battery percentage and lid state
are recorded; a closed lid does not refuse AC operation. This check does not
replace the owner's confirmation or prevent a later unplug or lid sleep.
Issue 6170 repeats the positive-AC check after launch verification, immediately
before dispatch, using only the bounded power-source query (no later lid query).
Battery or unknown readings refuse, including after an AC sequence start.

All declared child deadlines start immediately before `Popen`, after admission.
macOS uses `mach_continuous_time` converted with `mach_timebase_info`; the installed
Apple SDK's `usr/include/mach/mach_time.h` describes it as "like mach_absolute_time,
but advances during sleep" (available since macOS 10.12). Linux uses
`clock_gettime_ns(CLOCK_BOOTTIME)`. Unsupported clocks refuse; there is no fallback
to adjustable time of day or suspension-excluding monotonic time. The controller
checks expiry on resume even when the child exited during suspension. The
900-second synthetic, 21,600-second canary and 43,200-second production declarations
are unchanged. This deadline applies through child output drainage; admission
and subsequent final evidence publication are outside its measured interval.

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
No-sleep requires recognized, ordered, matched sleep/wake events bracketing the
requested interval. Unparsed sleep-like events, unmatched events and incomplete
coverage yield unknown while retaining any positive intervals that were parsed.

These local sidecars are supplemental host observations, not model inputs or
an amendment to the closed captured-generation pool. They do not grant
acceptance, change runtime gate decisions, or authenticate the OS clock/log.
A host sleep remains a host event; its acceptance disposition is for the owner.
Retain the sidecars with the attempt for that review. Do not rewrite consumed
attempts to add them retroactively.
`host-controller-timing.jsonl` adds execute-child entry, dispatch origin and
deadline, callback-response delivery, tool-result intake and model turn frames.
Tool identifiers and command digests join these rows to the existing transcript
and control journal. Helper durations span controller delivery to result intake;
they include runtime/transport scheduling and are not subprocess CPU time. Model
turn rows timestamp received assistant/user/result frames (and message start/stop
frames when provided), not unobservable provider-side token generation. Missing
endpoints remain missing, including a helper still unsettled at deadline. No
registered document kind or version changes. Timing writes are bounded and
observation failures cannot change execution decisions.
Start, stage and end observation failures retain a separate observation-error
diagnostic when possible, falling back to stderr. They cannot replace a launch
failure, skip final publication or undo an already published journal stage.

The offline proof runner uses the same positive-AC check and clock/event
recorder around each cohort. Its report distinguishes a stale observation after
recorded sleep from an ordinary freshness refusal. No power settings are changed
and no power assertion is acquired by this probe.
