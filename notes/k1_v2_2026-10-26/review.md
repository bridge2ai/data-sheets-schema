# K1 v2 review and decision handoff

This is offline engineering evidence for the 2026-10-25 orchestration queue,
prepared on 2026-10-26 UTC. It does not authorize a budget, provider request,
registration, retry, source trim, or scientific acceptance. AGY owns publication
and issue filing; Claude reviews the delivery before any merge request.

## Independent review and corrections

An independent read-only reviewer examined the component, measurement, ledger
comparison and cost helpers and their tests. The reviewer did not edit or run
the implementations. Findings addressed:

1. **Real nested JSON retained a trailing newline.** The initial component
   parser incorrectly refused the production representation. It now preserves
   exactly the known optional newline while refusing noncanonical formatting.
   A production-shaped regression and an invalid-format mutation cover it.
2. **Report claims needed stable evidence authority.** The synthesis now refuses
   changed ledger-audit bytes before reusing the reviewed timing/count narrative;
   the specific historical `budgeted_cborg._prepare` TTL guard is separately
   pinned. A changed-audit test verifies refusal.
3. **Cache and registration wording needed narrower scope.** Only worker input
   billing changes in the cache scenario. Omission/integration, output charges,
   context and aggregate input stay fixed. Offline scratch registrations are
   disclosed; no live registration or current provider claim is made.
4. **Kids First's builder allowance is not actual typed construction.** Its
   planner-only proxy allowance is labelled separately from the actual-context
   typed refusal. Campaign total and typed cost remain unknown.

The primary preview's payload joins, carries, context reserves, subtotal and
cache arithmetic were independently checked. The preview remains historical:
its table used the less precise “Actual / max workers” label corrected in the
final report. Its exact generating helper bytes are retained as
`scripts/adhoc/k1_v2_cost_report_preview_20261026.py` (SHA256
`e994ceeeba0d10f5f4dc8f9463ab1ba75351bd6740750ab9bab685607183276b`).
Use the final helper and report for decisions.

## Follow-up findings for AGY and Claude

- **Integration overflow, related to #5155 and D35:** primary AI-READI exceeds
  1M even at expected size; VOICE also crosses after its output reserve. Decide
  a bounded integration/carry design before A21. Cache and a larger aggregate
  budget alone do not solve an individual context overflow.
- **Broader D33 exposure, related to #5157:** at-cap report, regate and reconcile
  exposures are not confined to Kids First; CM4AI also has at-cap exposure under
  A17. Preserve fail-closed admission; do not trim evidence implicitly.
- **D06 cache proposal is still a proposal:** the shared content is after a
  varying worker-schema block on today's wire. Reordering requires a reviewed
  implementation before D35. Recorded worker cache reads were zero; do not
  count hypothetical savings as observed or guaranteed.
- **Kids First actual context:** the AI-READI record proxy lacks the explicitly
  supplied vocabulary required by the actual neutral context. Keep typed
  sizing/cost unknown until an admissible record/context pairing exists.
- **D41 evidence distinction, related to #5138/#5142:** original-ledger numeric
  agreement does not authenticate edited admissions, response pins or outcomes.
  Both historical canaries remain evidence-only.

## Reproduction and scope

The source composition is A16 `56c41163f` plus exact A17 partitioning
`8285172d0` and inherited sizing module `4c52b8e6f`. The #5155 allowance uses
only the exact cached pure sizing declarations from `502d5ce3f`; the complete
later A17/D39 launch stack is not installed. All source identities, helper
hashes, inputs, retained record pins, conformance edits and payload pins are in
the measurement JSON. Source and network invariants are checked at completion.

Raw canonical payloads, staged copies, `.partial` checkpoints and logs remain
in this owned worktree; originals and prior K1 evidence remain unchanged. The
large scratch payloads are not added to Git. Final measurement JSON and helper
sources suffice to inspect the arithmetic; rebuilding the actual payloads also
requires the pinned historical files at the documented launch-base paths.

## Completion

All twenty scenarios completed in three serial processes with exit 0: seven
A17 primary constructions, six alternate large-project A17 replicates, and
seven primary constructions using prior K1 coarse limits under A17. Every
source/origin/network invariant passed. The final report was independently
reviewed against these exact measurements; no unresolved review blocker remains.

The first combined regression run gave **48 passed, 3 failed** in 0.19 s. The
failures exposed the historical whole-root helper's intentional dependency on
A16's two-field inventory, whereas A17 has a three-field inventory and splits
lists. The three tests now load an exact, SHA-checked A16 source fixture under
a separate module name. Their assertions are unchanged; production and new A17
tests continue to use A17. Independent review verified both the original Git
source hash and the isolation. The final combined run gave **51 passed in
0.15 s**, exit 0. Both runs' logs and JUnit files are retained here. This is a
focused accounting/planning gate, not a full repository suite or launch gate.

Final known fifteen-run subtotal: **$813.20 + $10.86** ordinary partial-usage
scenario under A17, versus **$651.10 + $10.13** under prior K1 coarse limits.
All three AI-READI retained replicates and VOICE replicates 1/3 exceed expected
integration context. CM4AI's measured exposures are at cap. Kids First and the
optional crate arm remain excluded from this known subtotal.

Final report SHA256:
`df237a0d93c0281f0a1e4957d4b56fbb93859d956a9bd8a04031c87b1d391a21`.
Final cost-model JSON SHA256:
`7aa0e09d5c581612bfed474db7aeaea7f424318510c242992a6f7ed6af450b88`.
The publication commit/head is logged separately in the coordination STATUS.
