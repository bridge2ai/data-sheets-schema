# Failed canary follow-up — 2026-09-13

The CHORUS API attempt at commit `4a084a55b19dde93e6f7acf4ab397268cd68e50c`
failed schema validation. Its original source registration
`0fbe4d0853b0fbdcef6f4788532420800428aecd069ae8db48fa5a3485495a12`
and output bytes remain historical evidence. The changes here are **not**
retroactive repairs or approval to resume that attempt.

Issue #1770: a denied repair did not latch the experiment controller closed.
The runner caught the exception and later admitted a cheaper report call.
The controller now persists a stopped-attempt event before raising, retains
the denied request without counting it as paid, and checks the stop before
token counting, subsequent admission and declaring a completed attempt.
A recreated controller using the same ledger must also refuse that attempt.

Issue #1771: the schema digest hid `string[]` together with default scalar
strings. Nested list obligations now reach both generation prompts and the
fitness specification. The change applies to ordinary external schemas as
well as neutral and study profiles. The study full digest grows to 44,684
characters, so the compactness guard deliberately moves from 44k to 46k.
All earlier digest-inventory entries are retained; the two new profile
entries are appended.

This changes the generation and fitness instruments. The prior registration
is preserved as historical and deliberately cannot launch against these
changed pins. A fresh registration, independently reviewed first request,
successful CI and an explicit retry decision are required. The previous
attempt's estimated $3.291465 must carry forward: $196.708535 remains of the
additional $200, with the original $5 cumulative limit for each new attempt.
No new paid generation or evaluation accompanies these fixes.

The native controller's separate review findings (#1768, #1769) must also be
resolved before its launch. A passing generation canary will still not imply
acceptance of semantic evaluation or repeatability measurements.
