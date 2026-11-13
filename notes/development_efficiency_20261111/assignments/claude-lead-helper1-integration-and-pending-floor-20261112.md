# Assignment to Codex helper 1: integrate the reviewed fixes, then repair the pending receipt floor

From the Claude lead, 2026-11-12. You keep your worktree `E/codex-native-main-integration-20261112` (head `df0122254cc7c9fe10470ee9eabc26c71a411a14` when the lead looked at 19:28Z). Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file.

## Standing

Your scanner handoff is accepted (`handoffs/codex-h1-scanner-pin-20261112.md`, SHA-256 `e859b7657651563caba0a3a3ef8dad075e872c550a539a3351729369cf03877e`). The D128-form comparison goes to the owner as you wrote it. The lead's rulings on your open findings:

- **H1-F2 (temporary layout):** no change. The copied-helper fixtures need a temporary directory outside every `d4d-executions` path, which your sandbox does not offer. The lead ran those files outside the sandbox, in the worktree and in a tree outside `d4d-executions`: they pass or skip as designed. Record your nine negatives as environment-scope and leave the fixtures.
- **H1-F5 (two ambiguous-alias tests):** your recommendation is accepted. Main's precision behaviour stands. Replace the two old unconditional-refusal expectations as you proposed: first add the positive witnesses with both target modules materialised, keep the negatives for unresolved alternatives and ambiguous `-m` operands. One commit, tests only.
- **H1-F6 (retained known-gap fixtures):** classify each fixture from your two audits. Where the scanner now reports a violation that the fixture recorded as a known gap, the fixture's expectation is updated to what the scanner reports, in its own commit per fixture, with the evidence that the extra violations are the ones the fixture describes. Where you cannot show that, leave the fixture failing and say why. No xfail, no deletion.

- **Your public-home finding** (`handoffs/codex-h1-public-home-finding-20261112.json`): accepted as evidence. Helper 2 saw the same refusal independently and owns both repairs (the helper cache location, and the missing failed readback when runtime revalidation fails), on `codex/native-helper-cache-home-20261112`. Do not work on them; the lead will give you the commits to integrate when they are reviewed.

The owner has not yet answered on the API post-image hash or the margin. The four protected files stay equal to main on the branch.

## Part 1: integrate the reviewed commits (do this first)

Cherry-pick onto your branch, in this order. Report a conflict instead of resolving it by guesswork, and run the touched test files after each group.

1. From `codex/native-observer-alias-20261112` (helper 2, reviewed): `91fcdab3311c65ba8591836db75e241b78cf10ac`, `37a4aa5d0ab07ed270ef6211f35e7a377e2472b6`, `789778427d029ccc2d66b1b926c8921ceef79556`. **Already on your branch** as `6846d8404`, `1cd226427` and `df0122254` (`git cherry` shows all three as equivalent); nothing to do for this group.
2. From `codex/native-launch-sequence-20261112` (helper 2, reviewed): `d07eccefb59938f8b625498247259f17e5c155ec`, `34b46c3132ab7a5cab4f9bdf7634d38c77321369`, `e936cbb83d091cfab5c2e8b85bdd4c08a1b6b1e0`, `cf53497ae2ebfba1da9c64995590115c48437f77`, and its repair `d2efa55014e131f92733bf2c3a90c0830214dc89` (added by the lead at 19:14Z: helper 2's first public completion run showed that `cf53497ae` imported the verifier bootstrap from inside the verified consumer; never take `cf53497ae` without this repair). If helper 2 adds further repair commits on that branch while you work, take the branch's head at the time and record it.
3. From `agy/native-ci-collection-5875-20261112` (helper 3, reviewed): `f25230fe1e56c5ad264cf77242f623be0ee6e4d1` and `01c9b7b86` (resolve the short hash and record the full one).

Helper 2 is running the public completion tests in its own scratch composition with these commits and the packets; you do not need to repeat that.

## Part 2: a pending receipt floor must not block a pilot (a defect; required)

**The rule.** The owner decided (D109) that the canary's coverage floor stays `{state: pending, mode: diagnostic_pilot}`: "The canary counts as "accepted" when every other acceptance row holds. Its policy-v1 floor reading is reported, not gated." Amendment N1.4(B) row 0 says the receipts gate uses the structural floors only, so the pending floor does not block it, and row 5 says the pending reading is kept and labelled, never a pass.

**The source does the opposite.** Two independent readings at `5d63d0a77` agree (`E/plans/reviews/np1_floor_source_audit_codex_2026-11-12.md`, question 1, and `E/plans/reviews/np1v2_c515160a_claude_review_2026-11-12.md`, finding P2-8): the native route's final receipt command is `receipts check … --strict` (`native_shared_render.py`), which exits 1 for a pending coverage floor (`cli/receipts.py`, about lines 303 to 322, through `canary.receipt_floors`); `final_receipts` must pass before draft, final evidence and recorder (`native_shared_phase.py`); and the independent receipts gate applies the same floors (`native_shared_gates.py`, about lines 152 to 177). So no pilot with a pending floor can reach `completed_pending_independent_review`. The model-facing policy asset says the same: "A pending floor remains a diagnostic pilot and cannot satisfy strict completion."

1. **Confirm it** with the smallest offline reproduction you can: a native final receipt check under a pending registration, and what the phase rules and the gate then do. If a public completion test already runs under a pending floor and passes, say which and why the reading is wrong.
2. **Fix it on the native route only,** as its own commit with tests: under a pending floor the structural receipt floors still gate, and the coverage floor is reported with `state: pending`, `passed: False`, and does not fail the final strict check or the receipts gate. A registered floor keeps gating exactly as now. Nothing changes for the API arm's use of the same command; show that with a test.
3. **The policy asset** `src/download/prompts/native_shared_receipt_policy_v1.md` is model-facing and pinned, and its sentence contradicts D109. Do **not** edit it yet. Report the exact sentence, the smallest rewording that states D109's rule, and every pin and derived identity that would move, including the entry in the protected `canonical_hashes.yaml`. The lead takes the wording and the changed packet to the owner.
4. Add a test that a pending-floor run reaches completion through the public path in a scratch composition, or say exactly what stops it next.

## Part 3: prepare, do not commit to the branch, the registered floor's basis (a decision is pending)

The same audit, question 3: the plan's floor is measured on the at-receipt snapshot (decision D37: coverage of the phase-1 record under the completed receipt, so that deleting unreceipted values cannot raise it). The native final-stage block already carries those counters (`slots.with_receipt_at_receipt`, `slots.receiptable_at_receipt`, from `receipts.py` about lines 2497 to 2513), but `native_shared_receipts.floor()` reads only the final-record counters, and the native registration has no basis field. The lead is asking the owner which basis the native production floor uses.

Say what the change to the at-receipt basis would take: where a basis is declared (the registration, as the API arm's `basis: receipted_part` does, or fixed in code), what `floor()` and the gate read, which sentence of the policy asset changes, which tests and pins move, and whether a pilot's pending reading should also carry the at-receipt counters. Write it as a proposal in your handoff. Implement it only on a separate local branch from your head, named `codex/native-floor-basis-d37-20261112`, so that it can be taken or dropped.

## Then the two test rulings above (H1-F5 and H1-F6)

## Bounds

As in the context file. No `cpu-monitoring` diagnostic. Scratch compositions for offline cohorts as you have been doing, with the private configuration restored and recorded.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h1-integration-and-pending-floor-20261112.md` with its JSON. Answer first: what is integrated, whether the pending-floor defect is confirmed and fixed, the asset sentence and what moving it costs, and the basis proposal. Write a first version when Part 1 is done, and update it as parts finish.
