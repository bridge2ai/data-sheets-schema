# Lead review of native latency plan v2

Reviewed 2026-11-10 UTC. Input:
`native_latency_implementation_plan_2026-11-10_v2.md`, SHA-256
`57ccd828662d6076e4edbf444446fe828fc5999be135fc46e3fd1b841858da53`.

**Verdict: substantially improved; three bounded corrections required before
implementation assignment.** Read-only lead review with an independent check.
No source changes, tests, or live calls. The earlier invented observer hot spot,
broad verification-result cache, and incorrect public node names are corrected.

## NL-9 — P2: WP3 proposes an ordering change already present

Plan line 86 proposes moving registration/bundle validation, capture activation,
authority and reservation construction, and slot binding before `capture_now`.
All are already before `capture_now` in
`tests/utils/native_synthetic_evidence.py:121–144` of the native worktree.
This cannot supply new savings. Remove it as an implementation step; preserve
the current timing semantics. The separate fixture-derivation scope remains
a proposed experiment requiring its own equivalence/refusal tests.

## NL-10 — P1: A timing pass does not close the structural U3K-F1 requirement

Lines 87–91 and 133 make further structural work conditional on exceeding
210 seconds. The retained K report's `Unmet structural requirement U3K-F1`
section explicitly says a successful public measurement does not close the gap:
four full shared-registration verifications still occur after capture acceptance
and before reservation, each delegating to full execution/preparer verification.

Keep two separate acceptance gates: the measured freshness margin, and
source-supported closure of the required cheap postacceptance-check contract.
Leave F1 open if the latter is unproven, even when timing passes. This does not
mandate the proposed snapshot architecture; any justified design must preserve
the existing live byte/identity, clock, journal, one-use and refusal guarantees.

## NL-11 — P2: WP1 must compare equal completed work

Lines 55–62 propose replacing the legacy observer with a monitoring observer
for a matched diagnostic. Explicitly require matching reached boundaries. The
observers can themselves alter whether freshness fails or reservation is reached;
whole-run ratios across those different paths would not isolate overhead.
If outcomes diverge, compare only identical completed prefixes, and separately
report the different outcomes and later work. Label the result as relative cost
of two observer implementations, not absolute zero-observer overhead.

Retain the proposed observer-equivalence canary across reloaded code objects,
forbidden entries, injected refusals, and captured arguments. A faster observer
that misses those behaviors is not accepted.

## Revision scope

Preserve v1 and v2 unchanged. Write a v3 document correcting only the three
items above and their dependent summaries/acceptance tables. Do not add broad
new research, speedup predictions, API changes or test runs. Include a short
NL-9/10/11 disposition table. No implementation is authorized; the lead checks v3.

The GitHub integrator should record NL-9 through NL-11 as proposed-plan review
issues, checking duplicates first. Do not close earlier issues merely because
the worker says they are addressed; closure follows accepted revised evidence.
