# U3-D round 9 integration findings, 2026-11-07

Local issue ledger; publication is prohibited in this offline task. These
findings do not authorize a native executable or change of admission policy.

## R9-1: package source inventory

Fixed in D. The stage executable moved to `native_shared_stage/__main__.py`.
Normalize package initializers in the complete source inventory and pin the
actual stage entrypoint in the permission recipe, as already done for the CLI.
The real-package regression checks both retained source rows and the join.

## R9-2: validation bootstrap precedence

The initial full collection enumerated 24,793 tests but failed its final origin
witness. D's preserved worktree FAIRSCAPE copy preceded the exact scratch
gitlink. The D wrapper now removes only that path from the disposable test
bootstrap before inserting the independently verified scratch dependency.
The existing worktree and the strict origin assertion are unchanged.
Collection also imports integration modules that prepend their own preserved
dependency path. The runner now imports the exact scratch regular package
before pytest, preventing that later path insertion from changing its namespace.
Both earlier rejected attempts remain recorded; they are not accepted source
origin evidence.

The inherited C overlay-census helper only permits C's scratch root. D now
checks all 28 actual merged consumer graphs directly, with no overlay or pin
filter. The historical C helper remains unchanged; its D-scratch refusal is
retained as harness evidence, not a production-graph failure.

## R9-3: A preparation has a stale captured-runtime class

The genuine registration canary at `8a8b2652643233ec560f9278a1febc75934c4873`
executed D's `_registration_body` and `command`, and both proposal construction
and `verified_v2_body` succeeded. The public A verifier then failed before its
fixed D entry: `verified -> verify_preparer -> prepare -> spec.instruction`.
`native_shared_render.metadata` refused the runtime capture's exact class.

A's `prepare` holds the ordinarily imported `read_regular`; C's required
classifier scope installs A-verified package modules. The new renderer's
`CapturedArtifact` class therefore differs from the retained reader's class.
This is separate from projection mint identity and from the protected U1 hook.
`tests/test_native_u3d_round9_preparation.py` retains the direct real positive
requirement without a skip, xfail, class substitution or guard exception.

Proposed A-owned repair, **not applied**: in `prepare`, import the current
`native_shared_evidence.read_regular` locally and use it for both runtime
captures. Keep the fixed A interface, loader, public map and exact class checks.
The adjacent `.diff` is a review proposal only. Validate the direct requirement,
the complete registration canary, A's complete core suite and saved mutations
before considering the gate closed.

The completed `round9-registration-r2` cohort at `c852b3e72` has 17 passes,
four call-phase failures and no setup errors. Its genuine A-loaded fixed D entry
executed `rebuild_v2_body`, the real gate census, `_registration_body` and
`command`, producing exactly the original body (JUnit property
`genuine_fixed_entry_equal=True`; source SHA-256
`734aa6b3f33029da04e8f34fc12c3fc5c04ede4cb6a1b9c8438b16fb8cbb5901`).
The positive public-verifier check and all three missing-gate requirements then
fail at R9-3. The latter do not establish their intended missing-gate refusals.
The initial interrupted `round9-registration` has no completion witness and
contributes no counts; it remains untouched.

## R9-4: C callbacks enter a main-thread-only loader on real workers

Pinned `native_control.py` SHA-256
`e53f9627e629f06f40046460dbe43bb7a62c26d3f28bedf41408531bc5374a36`
starts observer/classifier threads. Pinned `run_native_canary.py` SHA-256
`7496a3ddb94ce480332efb7faeb3522f08aa3d3de724f9faa4662575802358e0`
installs C's callbacks. Initialization observation reaches C capture's loader;
classification directly enters `loaded_controls`. Both reach A's unconditional
main-thread refusal. The observer can fail before the first Bash callback.

D's narrow loader scopes preserve historical transport identities, and D
translates a separately loaded C BudgetStop into the transport's exact type.
Neither fixes C's threading mismatch. The diagnostic invokes the real C
classifier body on the real historical worker with minimal state; it proves
the causal refusal, not complete native dispatch acceptance. Existing genuine
lifecycle success requirements remain unmarked. A C-owned scheduling/captured
interface decision is required; do not relax A's process-wide loader guard or
hold its consumer finder across concurrent callbacks.

## Remaining P3 dispositions

P3-1/3/5/6/7 are D repairs and regressions. Incoming A5 addresses P3-2 and
documents the P3-8 single-threaded precondition. P3-4 is partial: D's normal
saved-permission route now loads the real consumer through A; C's separate
protocol projection checks every call. D's pure consumer still uses the raw
pure protocol under A's source-verified scope. It does not obtain C's per-call
projection or add a cached-bytecode tripwire; do not claim those enhancements
complete. No public map, consumer guard or loader was widened in D.

The protected U1 hook, R9-3 and R9-4 are distinct admission gates. A passing
permission parser or graph census does not close them.
